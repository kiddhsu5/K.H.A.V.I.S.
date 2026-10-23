#!/usr/bin/env python3
"""Public status page for ``khavis.example.com``.

A tiny stdlib-only HTTP server that renders live pool health. Serves
``/`` (HTML), ``/dashboard`` (operator view), ``/wall`` (personal-dev
wall), ``/pgp.txt`` (security contact key), ``/api/dashboard`` and
``/healthz`` (JSON). No auth, no write paths — a billboard, not a
control panel.

Run with the project venv so ``core.registry`` imports resolve::

    /root/khavis-bot/.venv/bin/python -m scripts.status_server --port 80

Cloudflare terminates TLS at the edge; the origin serves plain HTTP on
``:80`` *and* HTTPS with a throwaway self-signed cert on ``:443``. Both
on purpose: ``bot.example.com`` already shares this zone, so we must
not force a zone-wide SSL-mode change. Serving both ports means the
record works whether the zone (or a per-hostname Configuration Rule) is
set to ``Flexible`` (edge -> :80) or ``Full`` (edge -> :443; Cloudflare
accepts a self-signed origin cert outside strict mode).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BRAND = "#0EA5E9"  # sky-500 — the project's single accent colour
GENERATED_AT_FORMAT = "%Y-%m-%d %H:%M:%S UTC"


def _pgp_bytes() -> bytes:
    """Serve ``deploy/pgp.txt`` (security contact public key)."""
    candidates = [
        Path(__file__).resolve().parent.parent / "deploy" / "pgp.txt",
        Path("/root/khavis-bot/deploy/pgp.txt"),
    ]
    for p in candidates:
        try:
            return p.read_bytes()
        except OSError:
            continue
    return b"# PGP key not installed\n"


# This page is public. health_check() reports ``key_present=`` and raw
# exception text, and exceptions can embed request headers — so scrub
# anything credential-shaped before it is rendered or serialised.
_SECRET_PATTERNS = (
    re.compile(r"\bkey_present=\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{8,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*\S{6,}"),
    re.compile(r"\b[A-Za-z0-9_\-]{40,}\b"),
)


def _redact(text: str) -> str:
    """Strip credential-shaped substrings from a public-facing string."""
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[redacted]", text)
    return text


# (rows, monotonic timestamp). Served stale and refreshed in the
# background once older than CACHE_TTL.
CACHE_TTL = 30.0
_HEALTH_CACHE: tuple[list[dict[str, object]] | None, float] = (None, 0.0)
_CACHE_LOCK = threading.Lock()
_REFRESHING = False
_PLUG_CACHE: list | None = None  # registry snapshot; see _load_plugins()
WARMING_DETAIL = "warming up — first sweep in progress"


def cache_state() -> dict[str, object]:
    """How stale is what we are about to serve? Surfaced on ``/healthz``.

    Operators staring at a 522-shaped problem need to tell "the router is
    down" apart from "you are looking at placeholder rows".
    """
    rows, cached_at = _HEALTH_CACHE
    with _CACHE_LOCK:
        warming = _REFRESHING or rows is None
    return {
        "age_s": None if rows is None else round(time.monotonic() - cached_at, 3),
        "warming": warming,
    }


def pool_health() -> list[dict[str, object]]:
    """Return one row per registered pool. Never raises, and never blocks.

    Stale-while-revalidate. A sweep costs as long as the slowest
    unreachable endpoint (a home-LAN Ollama burns its whole connect
    timeout — ~20s here), so a TTL-expiry must never land on a visitor.

    The cold path must not block either, which is the whole point of this
    function. Cloudflare gives up on an origin after ~15s and answers 522,
    so a first request that waits out a 20s sweep turns *everyone* who
    loads the page right after a restart into a 522 — including the
    uptime check that would otherwise tell us the service is fine. Serve
    placeholder rows immediately and let the sweep fill them in.
    """
    global _HEALTH_CACHE  # noqa: PLW0603 - module-level memo is intended

    rows, cached_at = _HEALTH_CACHE
    if rows is not None:
        if (time.monotonic() - cached_at) >= CACHE_TTL:
            _kick_refresh()
        return rows

    _kick_refresh()
    return _placeholder_rows()


def _placeholder_rows() -> list[dict[str, object]]:
    """Rows for a sweep that has not landed yet. ``ok`` is None, not False.

    None keeps the page honest: the pools are not down, we simply have not
    looked yet. ``False`` would light the summary red and make an operator
    chase a phantom outage.

    Reads ``_PLUG_CACHE`` and never calls ``_load_plugins()``. Discovery is
    cheap but *importing* it is not: it pulls in every provider SDK and
    takes ~12s cold, mostly ``google.generativeai``. Calling it here would
    put that cost straight back on the request we just worked so hard not
    to block.
    """
    plugs = _PLUG_CACHE
    if not plugs:
        return [
            {
                "name": "…",
                "provider_id": "",
                "models": [],
                "capabilities": [],
                "ok": None,
                "detail": WARMING_DETAIL,
            }
        ]
    return [
        {
            "name": getattr(p, "name", "?"),
            "provider_id": getattr(p, "provider_id", ""),
            "models": list(
                getattr(p, "models", None) or ([p.model] if getattr(p, "model", None) else [])
            ),
            "capabilities": list(getattr(p, "capabilities", None) or []),
            "ok": None,
            "detail": WARMING_DETAIL,
        }
        for p in plugs
    ]


def _kick_refresh() -> None:
    """Start one background resweep. No-op if one is already running."""
    global _REFRESHING  # noqa: PLW0603 - module-level flag is intended

    with _CACHE_LOCK:
        if _REFRESHING:
            return
        _REFRESHING = True

    def run() -> None:
        global _REFRESHING, _HEALTH_CACHE  # noqa: PLW0603
        try:
            _HEALTH_CACHE = (_probe_all_pools(), time.monotonic())
        except Exception as exc:  # noqa: BLE001 - never kill the refresher
            print(f"health refresh failed: {exc!r}", file=sys.stderr, flush=True)
        finally:
            with _CACHE_LOCK:
                _REFRESHING = False

    threading.Thread(target=run, daemon=True, name="khavis-health-refresh").start()


def warm_cache() -> None:
    """Fill the plugin and health caches before anyone asks.

    Two slow steps, both off the request path: importing every provider
    SDK (~12s) and then sweeping their health (~20s if an endpoint is
    dead). Failures must not stop the listeners from binding — this runs
    after bind precisely so a warm-up problem can only cost us fresh data,
    not the page.
    """

    def run() -> None:
        try:
            _load_plugins()
        except Exception as exc:  # noqa: BLE001 - warm-up is best-effort
            print(f"warm-up: plugin load failed: {exc!r}", file=sys.stderr, flush=True)
        try:
            _kick_refresh()
        except Exception as exc:  # noqa: BLE001 - warm-up is best-effort
            print(f"warm-up: sweep failed: {exc!r}", file=sys.stderr, flush=True)

    threading.Thread(target=run, daemon=True, name="khavis-warm").start()


def _load_plugins() -> list:
    """Discover the registry once and memo the plugin objects.

    Separated from ``_probe_all_pools`` so the cold path can name the pools
    without paying for their health probes. Discovery is sub-millisecond and
    the YAML parse is single-digit milliseconds — cheap enough for a request
    — but we memo anyway because this runs behind every placeholder render.
    """
    global _PLUG_CACHE  # noqa: PLW0603 - module-level memo is intended

    if _PLUG_CACHE is not None:
        return _PLUG_CACHE

    from core.env import load_env  # noqa: PLC0415 - lazy
    from core.registry import PluginRegistry  # noqa: PLC0415 - lazy

    load_env(PROJECT_ROOT / ".env")
    reg = PluginRegistry(PROJECT_ROOT).discover()
    reg.apply_pools_config(PROJECT_ROOT / "config" / "pools.yaml")
    _PLUG_CACHE = list(reg.all())
    return _PLUG_CACHE


def _probe_all_pools() -> list[dict[str, object]]:
    try:
        plugs = _load_plugins()
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "name": "registry",
                "ok": False,
                "detail": _redact(f"import failed: {exc!r}"),
                "models": [],
                "capabilities": [],
                "provider_id": "",
            }
        ]
    return _probe_plugins(plugs)


def _probe_plugins(plugs: list) -> list[dict[str, object]]:
    """Run every plugin's health_check concurrently.

    Wall time should track the slowest probe, not the sum of all of them.
    """

    def probe(plug) -> dict[str, object]:  # noqa: ANN001 - plugin type is ProviderPlugin
        try:
            h = plug.health_check()
            ok = bool(h.get("ok"))
            detail = str(h.get("detail", ""))
        except Exception as exc:  # noqa: BLE001
            ok = False
            detail = f"{type(exc).__name__}: {exc}"
        return {
            "name": plug.name,
            "provider_id": plug.provider_id,
            "models": list(plug.list_models()),
            "capabilities": list(plug.capabilities),
            "ok": ok,
            "detail": _redact(detail),
        }

    if not plugs:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugs)) as pool:
        return list(pool.map(probe, plugs))


def bot_health() -> dict[str, object]:
    """Is the Telegram dispatch bot or workbench service alive on this box?"""
    for unit in ("khavis-bot", "khavis-workbench"):
        try:
            out = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            ).stdout.strip()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": _redact(repr(exc))}
        if out == "active":
            return {"ok": True, "detail": f"systemd {unit}: active"}
    return {"ok": False, "detail": f"systemd khavis-bot: {out or 'inactive'}"}


def render_html(
    rows: list[dict[str, object]],
    bot: dict[str, object],
    cache: dict[str, object] | None = None,
) -> str:
    # ``ok is True`` rather than truthiness: a warming row is ``None`` and
    # must not be counted as either healthy or down.
    ok_n = sum(1 for r in rows if r.get("ok") is True)
    warming_n = sum(1 for r in rows if r.get("ok") is None)
    total = len(rows)
    bot_ok = bool(bot.get("ok"))
    cache = cache or {"age_s": None, "warming": False}

    def row_html(r: dict[str, object]) -> str:
        mark = "🟢" if r.get("ok") is True else ("🟡" if r.get("ok") is None else "🔴")
        caps = ", ".join(str(c) for c in r.get("capabilities", []))  # type: ignore[arg-type]
        models = ", ".join(str(m) for m in r.get("models", []))  # type: ignore[arg-type]
        return (
            "<tr>"
            f"<td>{mark}</td>"
            f"<td><code>{html.escape(str(r.get('name')))}</code></td>"
            f"<td>{html.escape(str(r.get('provider_id')))}</td>"
            f"<td class='small'>{html.escape(models)}</td>"
            f"<td class='small'>{html.escape(caps)}</td>"
            f"<td class='small detail'>{html.escape(str(r.get('detail')))}</td>"
            "</tr>"
        )

    body_rows = "\n".join(row_html(r) for r in rows)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>K.H.A.V.I.S. · status</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
         margin: 0 auto; max-width: 62rem; padding: 2rem 1.25rem 4rem;
         line-height: 1.55; }}
  h1 {{ font-size: 1.6rem; margin-bottom: .2rem; }}
  h1 span {{ color: {BRAND}; }}
  .sub {{ opacity: .75; margin-top: 0; }}
  .badges {{ display: flex; gap: .5rem; flex-wrap: wrap; margin: 1.25rem 0 1.75rem; }}
  .badge {{ border: 1px solid color-mix(in srgb, {BRAND} 45%, transparent);
            color: {BRAND}; border-radius: 999px; padding: .25rem .7rem;
            font-size: .8rem; font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .9rem; }}
  th, td {{ text-align: left; padding: .5rem .55rem;
            border-bottom: 1px solid color-mix(in srgb, currentColor 14%, transparent);
            vertical-align: top; }}
  th {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .04em;
        opacity: .65; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
          font-size: .85em; }}
  .small {{ font-size: .78rem; opacity: .8; }}
  .detail {{ max-width: 22rem; word-break: break-word; }}
  .summary {{ margin: 1rem 0 1.5rem; font-size: 1.05rem; }}
  footer {{ margin-top: 2.5rem; font-size: .78rem; opacity: .6; }}
  a {{ color: {BRAND}; }}
</style>
</head>
<body>
  <h1><span>K.H.A.V.I.S.</span> · status</h1>
  <p class="sub">Unified interface for 12 LLM pools with smart routing and zero quota interruption.</p>

  <div class="badges">
    <span class="badge">Apache 2.0</span>
    <span class="badge">Free forever</span>
    <span class="badge">Zero markup</span>
    <span class="badge">Self-hosted BYOK</span>
  </div>

  <div style="margin: 1.25rem 0;">
    <a href="/workbench" style="display:inline-flex; align-items:center; gap:0.5rem; padding:0.65rem 1.25rem; background:linear-gradient(135deg, #0EA5E9, #0D9488); color:#ffffff; border-radius:10px; text-decoration:none; font-weight:700; font-size:0.95rem; box-shadow:0 4px 14px rgba(14,165,233,0.35);">
      <span>🚀 開啟統一智慧工作台 (Unified Workbench)</span>
    </a>
  </div>

  <p class="summary">
    {"🟢" if bot_ok else "🔴"} <strong>Telegram dispatch bot</strong> — {html.escape(str(bot.get("detail")))}
    <br>
    {"🟢" if ok_n == total and total else "🟡"} <strong>{ok_n} / {total}</strong> LLM pools healthy
    {"<br>🟡 <strong>" + str(warming_n) + " warming up</strong> — first sweep still running, refresh in a moment" if warming_n else ""}
  </p>

  <table>
    <thead>
      <tr><th></th><th>Pool</th><th>Provider</th><th>Models</th><th>Capabilities</th><th>Detail</th></tr>
    </thead>
    <tbody>
{body_rows}
    </tbody>
  </table>

  <footer>
    <p>
      <a href="https://github.com/kiddhsu5/K.H.A.V.I.S.">github.com/kiddhsu5/K.H.A.V.I.S.</a>
      · <a href="/healthz">/healthz</a>
      · rendered {time.strftime(GENERATED_AT_FORMAT, time.gmtime())}
      · cache age {"n/a" if cache.get("age_s") is None else str(cache.get("age_s")) + "s"}{" · refreshing" if cache.get("warming") else ""}
    </p>
  </footer>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "khavis-status/1.0"

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/pgp.txt":
            self._send(200, _pgp_bytes(), "text/plain; charset=utf-8")
            return
        allowed = (
            "/",
            "/healthz",
            "/dashboard",
            "/wall",
            "/workbench",
            "/work",
            "/workbench-c",
            "/workbench-legacy",
            "/api/dashboard",
            "/api/quota",
            "/api/alerts",
            "/api/workbench/history",
            "/api/workbench/artifacts",
            "/api/workbench/artifacts/read",
            "/api/workbench/agents",
            "/api/workbench/models",
            "/api/workbench/workspace",
            "/api/workbench/setup",
        )
        if path not in allowed:
            self._send(404, b'{"error":"not found"}', "application/json")
            return
        rows = pool_health()
        bot = bot_health()
        cache = cache_state()
        if path == "/healthz":
            payload = {
                # None rows are "not looked at yet", not "down" — do not
                # fold them into ok, or a warm-up looks like an outage.
                "ok": all(r.get("ok") is True for r in rows) and bool(bot.get("ok")),
                "cache": cache,
                "bot": bot,
                "pools": rows,
                "generated_at": time.strftime(GENERATED_AT_FORMAT, time.gmtime()),
            }
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/dashboard":
            from bot import history as bot_history  # noqa: PLC0415
            from web.dashboard import api_payload, public_history  # noqa: PLC0415

            # Public endpoint: never ship prompts / chat ids (api_payload
            # re-applies the same filter; this keeps the intent obvious here).
            payload = api_payload(
                pools=rows,
                bot=bot,
                cache=cache,
                history=public_history(bot_history.tail(50)),
            )
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/quota":
            from core.quota_tracker import get_quota_tracker  # noqa: PLC0415

            snaps = get_quota_tracker().all_snapshots()
            payload = {"quotas": snaps, "pools": rows, "generated_at": time.time()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/history":
            from bot import history as bot_history  # noqa: PLC0415

            raw_items = bot_history.tail(200)
            formatted: list[dict[str, object]] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                ts_val = item.get("ts")
                ts_str = (
                    str(item.get("dispatched_at"))
                    if item.get("dispatched_at")
                    else (
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts_val)))
                        if isinstance(ts_val, (int, float))
                        else "剛剛"
                    )
                )
                prompt_text = str(item.get("prompt") or "").strip()
                if not prompt_text:
                    phase_name = str(item.get("phase") or item.get("kind") or "pipeline")
                    prompt_text = f"系統協同流水線執行 ({phase_name})"
                src = str(
                    item.get("consensus_source")
                    or item.get("backend")
                    or (",".join(item.get("backends", [])) if isinstance(item.get("backends"), list) else "")
                    or item.get("phase")
                    or "K.H.A.V.I.S. Pipeline"
                )
                raw_backends = item.get("backends")
                backends = (
                    [str(b) for b in raw_backends]
                    if isinstance(raw_backends, list)
                    else ([str(raw_backends)] if raw_backends else [])
                )
                formatted.append(
                    {
                        "prompt": _redact(prompt_text),
                        "consensus_source": src,
                        "dispatched_at": ts_str,
                        "ok": bool(item.get("ok", True)),
                        "latency_ms": item.get("latency_ms"),
                        # 分組維度 + 重讀成果用（見 module docstring）
                        "backends": backends,
                        "collab_mode": str(item.get("collab_mode") or ""),
                        "project": str(item.get("project") or ""),
                        "thread": str(item.get("thread") or ""),
                        "step": int(item.get("step") or 0) or 1,
                        # ts 是記錄的唯一識別：舊紀錄的 handle 只到秒，
                        # 同秒的兩筆任務會被誤併成同一個對話串。
                        "ts": float(item.get("ts") or 0.0),
                        "consensus": _redact(str(item.get("consensus") or ""))[:2000],
                    }
                )
            self._send(
                200,
                json.dumps({"ok": True, "history": formatted}, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/alerts":
            from core.alerting import get_alert_manager  # noqa: PLC0415

            alerts = get_alert_manager().recent_alerts()
            payload = {"alerts": alerts, "generated_at": time.time()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path in ("/workbench", "/work", "/workbench-c"):
            # 現行介面 = 選項 C（任務卡片流）。/workbench-c 保留為別名。
            from web.workbench_c import render_workbench_html_c  # noqa: PLC0415

            self._send(200, render_workbench_html_c().encode(), "text/html; charset=utf-8")
            return
        if path == "/workbench-legacy":
            # 改版前的拓撲式介面，保留作為回退路徑。
            from web.workbench import render_workbench_html  # noqa: PLC0415

            self._send(200, render_workbench_html().encode(), "text/html; charset=utf-8")
            return
        if path == "/api/workbench/artifacts":
            from web.workbench import list_deliverable_artifacts  # noqa: PLC0415

            payload = {"ok": True, "artifacts": list_deliverable_artifacts()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/artifacts/read":
            from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

            from web.workbench import read_artifact_content  # noqa: PLC0415

            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            target_file = qs.get("path", [""])[0]
            res = read_artifact_content(target_file)
            self._send(
                200,
                json.dumps(res, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/agents":
            from web.workbench import get_agent_fleet_status  # noqa: PLC0415

            payload = {"ok": True, "agents": get_agent_fleet_status()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/models":
            from web.workbench import get_workbench_models_config  # noqa: PLC0415

            payload = {"ok": True, **get_workbench_models_config()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/workspace":
            from urllib.parse import parse_qs, urlparse  # noqa: PLC0415

            from core.workspace_manager import get_workspace_status  # noqa: PLC0415

            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            proj = qs.get("project", [""])[0] or None
            payload = get_workspace_status(proj)
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path == "/api/workbench/setup":
            from web.workbench import get_setup_wizard_status  # noqa: PLC0415

            payload = {"ok": True, **get_setup_wizard_status()}
            self._send(
                200,
                json.dumps(payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return
        if path in ("/dashboard", "/wall"):
            from bot import history as bot_history  # noqa: PLC0415
            from web.dashboard import (  # noqa: PLC0415
                public_history,
                render_dashboard_html,
                render_wall_html,
            )

            if path == "/wall":
                body = render_wall_html()
            else:
                body = render_dashboard_html(
                    pools=rows,
                    bot=bot,
                    cache=cache,
                    history=public_history(bot_history.tail(50)),
                )
            self._send(200, body.encode(), "text/html; charset=utf-8")
            return
        self._send(200, render_html(rows, bot, cache).encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/workbench/models":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_body)
            except Exception:  # noqa: BLE001
                payload = {}

            from web.workbench import update_workbench_models_config  # noqa: PLC0415

            try:
                updated = update_workbench_models_config(payload if isinstance(payload, dict) else {})
            except ValueError as exc:
                self._send(
                    400,
                    json.dumps({"ok": False, "detail": str(exc)}, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8",
                )
                return

            self._send(
                200,
                json.dumps({"ok": True, **updated}, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return

        if path == "/api/workbench/workspace":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_body)
            except Exception:  # noqa: BLE001
                payload = {}

            from core.workspace_manager import configure_workspace  # noqa: PLC0415

            res = configure_workspace(payload if isinstance(payload, dict) else {})
            self._send(
                200 if res.get("ok", True) else 400,
                json.dumps(res, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return

        if path == "/api/workbench/agents/custom":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_body)
            except Exception:  # noqa: BLE001
                payload = {}
            payload = payload if isinstance(payload, dict) else {}

            from core.custom_agents import (  # noqa: PLC0415
                delete_custom_agent,
                enrich_custom_agent_status,
                load_custom_agents,
                register_or_update_custom_agent,
            )

            action = str(payload.get("action") or "upsert").strip().lower()
            try:
                if action == "delete":
                    agent_id = str(payload.get("id") or "").strip()
                    delete_custom_agent(agent_id)
                    custom_list = [enrich_custom_agent_status(a) for a in load_custom_agents()]
                    self._send(
                        200,
                        json.dumps({"ok": True, "deleted": True, "custom_agents": custom_list}, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8",
                    )
                    return

                entry = register_or_update_custom_agent(payload)
                custom_list = [enrich_custom_agent_status(a) for a in load_custom_agents()]
                self._send(
                    200,
                    json.dumps(
                        {
                            "ok": True,
                            "agent": enrich_custom_agent_status(entry),
                            "custom_agents": custom_list,
                        },
                        ensure_ascii=False,
                    ).encode(),
                    "application/json; charset=utf-8",
                )
            except ValueError as exc:
                self._send(
                    400,
                    json.dumps({"ok": False, "detail": str(exc)}, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8",
                )
            return

        if path == "/api/workbench/setup":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_body)
            except Exception:  # noqa: BLE001
                payload = {}

            from web.workbench import update_setup_wizard_config  # noqa: PLC0415

            res = update_setup_wizard_config(payload if isinstance(payload, dict) else {})
            self._send(
                200,
                json.dumps(res, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return

        if path == "/api/workbench/dispatch":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_body)
            except Exception:  # noqa: BLE001
                payload = {}

            prompt = str(payload.get("prompt") or "").strip()
            raw_agents = payload.get("agents") or payload.get("targets") or payload.get("agent") or ["khavis"]
            agents = [str(raw_agents)] if isinstance(raw_agents, str) else [str(a) for a in raw_agents]
            capability = payload.get("capability") or None
            raw_models = payload.get("agent_models")
            agent_models = raw_models if isinstance(raw_models, dict) else {}
            isolation_mode = str(payload.get("isolation_mode") or "").strip().lower() or None
            project_name = str(payload.get("project") or payload.get("project_id") or "").strip() or None
            collab_mode = str(payload.get("collab_mode") or "auto_loop").strip().lower()
            previous_context = (
                payload.get("previous_context")
                if isinstance(payload.get("previous_context"), dict)
                else None
            )
            # 對話串識別：前端在每輪帶上 thread id；第一輪沒有前例時由後端產生。
            _prev_ctx = previous_context if isinstance(previous_context, dict) else {}
            thread_id = str(_prev_ctx.get("thread") or "").strip() or f"t{int(time.time() * 1000)}"
            try:
                thread_step = int(_prev_ctx.get("step") or 0) + 1
            except (TypeError, ValueError):
                thread_step = 1

            if not prompt:
                self._send(
                    400,
                    json.dumps({"ok": False, "detail": "Prompt cannot be empty"}).encode(),
                    "application/json; charset=utf-8",
                )
                return

            from bot import history as bot_history  # noqa: PLC0415
            from bot.backends import (  # noqa: PLC0415
                AntigravityBackend,
                ClaudeBackend,
                CodexBackend,
                CustomAgentBackend,
                KhavisBackend,
                MinimaxBackend,
                ZcodeBackend,
            )
            from bot.dispatch import DispatchRouter  # noqa: PLC0415
            from bot.models import BackendName  # noqa: PLC0415
            from core.collab_orchestrator import run_collaborative_workflow  # noqa: PLC0415
            from core.custom_agents import load_custom_agents  # noqa: PLC0415
            from core.env import load_env  # noqa: PLC0415
            from core.workspace_manager import (  # noqa: PLC0415
                load_workspace_config,
                prepare_agent_cwd,
            )

            load_env(PROJECT_ROOT / ".env")
            ws_cfg = load_workspace_config()
            eff_mode = isolation_mode if isolation_mode in ("shared", "worktree") else str(ws_cfg.get("isolation_mode", "shared"))
            eff_project = project_name or str(ws_cfg.get("active_project", "shared-app"))

            agent_cwds: dict[str, Path] = {}
            all_known_ids = {"claude", "codex", "antigravity", "minimax", "zcode", *(str(a) for a in agents)}
            for aid in all_known_ids:
                if aid == "khavis":
                    continue
                agent_cwds[aid] = prepare_agent_cwd(aid, isolation_mode=eff_mode, project_name=eff_project)

            shared_dir = prepare_agent_cwd("shared", isolation_mode="shared", project_name=eff_project)

            backends: dict[BackendName, Any] = {
                "claude": ClaudeBackend(
                    model=str(agent_models.get("claude") or "").strip(),
                    cwd=str(agent_cwds.get("claude", shared_dir)),
                ),
                "codex": CodexBackend(
                    model=str(agent_models.get("codex") or "").strip(),
                    cwd=str(agent_cwds.get("codex", shared_dir)),
                ),
                "antigravity": AntigravityBackend(
                    model=str(agent_models.get("antigravity") or "").strip(),
                    cwd=str(agent_cwds.get("antigravity", shared_dir)),
                ),
                "minimax": MinimaxBackend(
                    model=str(agent_models.get("minimax") or "").strip(),
                    cwd=str(agent_cwds.get("minimax", shared_dir)),
                ),
                "zcode": ZcodeBackend(
                    model=str(agent_models.get("zcode") or "").strip(),
                    cwd=str(agent_cwds.get("zcode", shared_dir)),
                ),
                "khavis": KhavisBackend(),
            }

            for custom_cfg in load_custom_agents():
                cid = str(custom_cfg.get("id") or "").strip()
                if not cid:
                    continue
                c_cwd = agent_cwds.get(cid) or prepare_agent_cwd(cid, isolation_mode=eff_mode, project_name=eff_project)
                agent_cwds[cid] = c_cwd
                backends[cid] = CustomAgentBackend(
                    custom_cfg,
                    model=str(agent_models.get(cid) or custom_cfg.get("default_model") or "").strip(),
                    cwd=str(c_cwd),
                )

            router = DispatchRouter(backends)

            import asyncio  # noqa: PLC0415

            t0 = time.perf_counter()
            loop = asyncio.new_event_loop()
            try:
                orch = loop.run_until_complete(
                    run_collaborative_workflow(
                        router=router,
                        backends=backends,
                        agents=agents,
                        prompt=prompt,
                        capability=capability,
                        shared_dir=shared_dir,
                        agent_cwds=agent_cwds,
                        collab_mode=collab_mode,
                        previous_context=previous_context,
                    )
                )
            finally:
                loop.close()
            total_ms = int((time.perf_counter() - t0) * 1000)

            results_dump = orch["results"]
            bot_history.record(
                {
                    "ts": time.time(),
                    "kind": "workbench",
                    "prompt": prompt,
                    "backends": list(agents),
                    "collab_mode": orch["collab_mode"],
                    "consensus_source": orch["consensus_source"] or ", ".join(str(a) for a in agents),
                    "project": eff_project,
                    "isolation_mode": eff_mode,
                    "thread": thread_id,
                    "step": thread_step,
                    "consensus": str(orch.get("consensus") or ""),
                    "dispatched_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "ok": any(r.get("ok") for r in results_dump),
                    "latency_ms": total_ms,
                }
            )

            res_payload = {
                "ok": True,
                "thread": thread_id,
                "step": thread_step,
                "collab_mode": orch["collab_mode"],
                "consensus": orch["consensus"],
                "consensus_source": orch["consensus_source"],
                "critique_summary": orch["critique_summary"],
                "collaboration_steps": orch["collaboration_steps"],
                "next_actions": orch["next_actions"],
                "isolation_mode": eff_mode,
                "project": eff_project,
                "shared_dir": str(shared_dir),
                "shared_changed_files": orch["shared_changed_files"],
                "shared_diff": orch["shared_diff"],
                "results": results_dump,
            }
            self._send(
                200,
                json.dumps(res_payload, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )
            return

        self._send(
            404,
            json.dumps({"ok": False, "detail": "Not found"}).encode(),
            "application/json; charset=utf-8",
        )

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


def resolve_cert_paths(cert_path: Path, key_path: Path) -> tuple[Path, Path]:
    """Prefer the requested location; fall back to a temp dir if it is not creatable.

    Under systemd the unit declares ``CacheDirectory=khavis-status`` so the
    directory already exists and is writable. A bare manual run may not have
    that, and ``ProtectSystem=``-style lockdown is not the only reason a
    ``/etc/...`` default would fail to create — so degrade instead of dying.
    """
    try:
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        return cert_path, key_path
    except OSError as exc:
        import tempfile  # noqa: PLC0415 - only on the fallback path

        fallback = Path(tempfile.mkdtemp(prefix="khavis-status-"))
        print(
            f"cert dir {cert_path.parent} not usable ({exc!r}); using {fallback}",
            file=sys.stderr,
            flush=True,
        )
        return fallback / cert_path.name, fallback / key_path.name


def ensure_self_signed_cert(cert_path: Path, key_path: Path) -> bool:
    """Create a throwaway self-signed cert if neither file exists yet.

    Returns True when a cert is available. The private key never leaves
    the box and is worthless to an attacker who already has root on it —
    its only job is to satisfy Cloudflare outside ``Full (strict)``.
    """
    if cert_path.exists() and key_path.exists():
        return True
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-days",
        "825",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-subj",
        "/CN=khavis.example.com",
        "-addext",
        "subjectAltName=DNS:khavis.example.com,DNS:localhost",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"cert bootstrap failed: {exc!r}", file=sys.stderr, flush=True)
        return False
    key_path.chmod(0o600)
    return True


def primary_ipv4() -> str | None:
    """Outbound IPv4 of this host, without touching DNS.

    A UDP ``connect()`` picks a local address from the routing table and
    sends no packets. Deliberately not ``getaddrinfo(gethostname())`` —
    on a host with a ``.local`` name that blocks on mDNS for seconds and
    would stall service startup.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 53))
        addr = s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
    return None if not addr or addr.startswith("127.") else addr


def candidate_hosts(preferred: str) -> list[str]:
    """Bind addresses to try, most preferred first.

    A wildcard bind conflicts with *any* socket already holding that port
    on a specific address. On this box ``tailscaled`` holds 443 on the
    Tailscale IP, so ``0.0.0.0:443`` is EADDRINUSE even though the public
    path is completely free — falling back to a concrete unicast address
    sidesteps the clash without disturbing whatever else is running.
    """
    hosts = [preferred]
    if preferred not in ("0.0.0.0", "::", ""):
        return hosts
    addr = primary_ipv4()
    if addr is not None and addr not in hosts:
        hosts.append(addr)
    hosts.append("127.0.0.1")
    return hosts


class _Listener(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` that binds without a reverse-DNS lookup.

    ``http.server.HTTPServer.server_bind`` ends with ``socket.getfqdn(host)``.
    On a wildcard bind that resolves quickly, but on a concrete unicast
    address with no PTR record it blocks on the resolver timeout. Measured on
    the deploy host: **10.014 s** between "listening on http://0.0.0.0:80" and
    "listening on https://172.17.0.106:443" — the :443 fallback address after
    ``tailscaled`` claimed ``*:443``.

    That would only be a slow start if ``main()`` did not build every listener
    before starting any ``serve_forever``. The :80 socket is already in the
    ``LISTEN`` state by then, so connections queue in the kernel backlog with
    nobody accepting them and every visitor times out. Same class of trap as
    ``primary_ipv4()`` above: no DNS on the startup path. ``server_name`` is
    only used for CGI and log decoration, so the bare hostname is enough.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        _host, port = self.server_address[:2]
        self.server_name = socket.gethostname()
        self.server_port = port


class _TLSServer(_Listener):
    """HTTPS server that performs the TLS handshake in the *worker* thread.

    Two traps this avoids, both hit in production:

    1. Wrapping the listening socket —

           srv.socket = ctx.wrap_socket(srv.socket, server_side=True)

       — looks shorter but drops the only reference to the original socket
       object, whose ``__del__`` closes the shared file descriptor.

    2. Wrapping in ``get_request()`` — which is the obvious place — is just
       as bad in a different way: ``socketserver`` calls ``get_request()``
       from ``serve_forever``'s own thread, *before* ``process_request()``
       spawns a worker. A handshake there therefore blocks accept for up to
       the handshake timeout, the backlog (5) fills, and callers see Cloudflare
       525 / timeouts while the process looks idle.

    ``process_request_thread`` is the first thing that already runs on a
    fresh thread, so the handshake belongs there.
    """

    def __init__(self, addr: tuple[str, int], handler, ctx: ssl.SSLContext) -> None:
        self._ctx = ctx
        super().__init__(addr, handler)

    def process_request_thread(self, request, client_address) -> None:  # noqa: ANN001
        # Cap the handshake so half-open TLS attempts cannot pin a thread.
        request.settimeout(10)
        try:
            request = self._ctx.wrap_socket(request, server_side=True)
        except (ssl.SSLError, OSError):
            # Scanners sending plain HTTP to the HTTPS port land here. Just
            # drop them — a traceback per probe is noise, and shutdown_request
            # closes the socket.
            self.shutdown_request(request)
            return
        request.settimeout(None)
        super().process_request_thread(request, client_address)


def start_listener(
    label: str,
    host: str,
    port: int,
    wrap_ssl: ssl.SSLContext | None = None,
) -> tuple[str, ThreadingHTTPServer, threading.Thread] | None:
    """Bind one listener, trying ``candidate_hosts`` in order.

    ``serve_forever`` is started here, not later by ``main()``. A socket is
    already in the ``LISTEN`` state the moment ``__init__`` returns, so any
    work that happens between bind and serve — generating a cert, resolving
    a fallback address — costs every visitor a timeout while connections pile
    up in the kernel backlog. Binding must mean serving.

    Returns None when nothing bound — a dead :443 must not take :80 down
    with it, and vice versa.
    """
    errors: list[str] = []
    for addr in candidate_hosts(host):
        try:
            srv: ThreadingHTTPServer
            if wrap_ssl is not None:
                srv = _TLSServer((addr, port), Handler, wrap_ssl)
            else:
                srv = _Listener((addr, port), Handler)
        except OSError as exc:
            errors.append(f"{addr}:{port} -> {exc.strerror or exc}")
            continue
        note = " (self-signed)" if wrap_ssl is not None else ""
        print(f"khavis-status listening on {label}://{addr}:{port}{note}", flush=True)
        thread = threading.Thread(target=srv.serve_forever, daemon=True, name=f"khavis-{label}")
        thread.start()
        return (f"{label}://{addr}", srv, thread)
    print(
        f"khavis-status: could not bind {label}:{port} — {'; '.join(errors)}",
        file=sys.stderr,
        flush=True,
    )
    return None


def main() -> None:
    parser = argparse.ArgumentParser(prog="khavis-status")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--port", type=int, default=80, help="plain HTTP (Cloudflare SSL mode Flexible)"
    )
    parser.add_argument(
        "--tls-port",
        type=int,
        default=443,
        help="HTTPS with self-signed cert (Cloudflare SSL mode Full)",
    )
    parser.add_argument("--cert", type=Path, default=Path("/var/cache/khavis-status/cert.pem"))
    parser.add_argument("--key", type=Path, default=Path("/var/cache/khavis-status/key.pem"))
    args = parser.parse_args()
    cert_path, key_path = resolve_cert_paths(args.cert, args.key)

    started: list[tuple[str, ThreadingHTTPServer, threading.Thread]] = []

    http = start_listener("http", args.host, args.port)
    if http is not None:
        started.append(http)

    if args.tls_port and ensure_self_signed_cert(cert_path, key_path):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_path), str(key_path))
        https = start_listener("https", args.host, args.tls_port, wrap_ssl=ctx)
        if https is not None:
            started.append(https)

    if not started:
        raise SystemExit("khavis-status: no listener could be bound; refusing to idle")

    # Fill the health cache before the first visitor arrives. Without this
    # the very first request pays for the sweep; see pool_health().
    warm_cache()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        for _name, srv, _t in started:
            srv.shutdown()


if __name__ == "__main__":
    main()
