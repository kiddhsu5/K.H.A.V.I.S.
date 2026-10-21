"""K.H.A.V.I.S. Unified Graphical Web Workbench (全域圖形化智慧指揮工作台).

Provides a graphical, interactive, single-page command console to:
1. Visually orchestrate 5 Tencent Cloud CLI Agents (Claude Code [MiniMax-M3.1-Flash], Codex [GLM 5.3 FlashX], Antigravity [AGY], MiniMax Code [MiniMax-M3.1], zcode [GLM 5.3 FlashX]) + K.H.A.V.I.S. Multi-Agent Team via an interactive SVG Topology Canvas.
2. Monitor real-time quotas, 429 breakers & dynamic reset timers with SVG radial gauges.
3. Track execution progress via a graphical 7-Role LangGraph DAG visualizer and latency bar charts.
4. Safely browse, preview, copy, and download whitelisted deliverables and artifacts.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AGENT_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "claude": {
        "env": "CLAUDE_DISPATCH_MODEL",
        "default": "MiniMax-M3.1-Flash",
        "label": "Claude Code",
        "options": [
            "MiniMax-M3.1-Flash",
            "MiniMax-M3.1",
            "glm-5.3-flashx",
            "glm-5.3",
            "claude-sonnet-5",
            "claude-haiku-4-5-20251001",
        ],
    },
    "codex": {
        "env": "CODEX_DISPATCH_MODEL",
        "default": "glm-5.3-flashx",
        "label": "OpenAI Codex",
        "options": [
            "glm-5.3-flashx",
            "glm-5.3",
            "codegeex-4",
            "MiniMax-M3.1-Flash",
            "MiniMax-M3.1",
            "gpt-5-mini",
            "gpt-5-codex",
        ],
    },
    "antigravity": {
        "env": "ANTIGRAVITY_DISPATCH_MODEL",
        "default": "antigravity-pro",
        "label": "Antigravity (AGY)",
        "options": [
            "antigravity-pro",
            "antigravity-flash",
            "antigravity-ultra",
            "MiniMax-M3.1-Flash",
            "glm-5.3-flashx",
        ],
    },
    "minimax": {
        "env": "MINIMAX_DISPATCH_MODEL",
        "default": "MiniMax-M3.1",
        "label": "MiniMax Code",
        "options": [
            "MiniMax-M3.1",
            "MiniMax-M3.1-Flash",
            "MiniMax-Text-01",
        ],
    },
    "zcode": {
        "env": "ZCODE_DISPATCH_MODEL",
        "default": "glm-5.3-flashx",
        "label": "Zhipu zcode",
        "options": [
            "glm-5.3-flashx",
            "glm-5.3",
            "codegeex-4",
            "glm-4-plus",
        ],
    },
}

_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._:\-/]{1,80}$")


def _read_env_file_vars(env_path: Path) -> dict[str, str]:
    """Read key=value pairs from .env without overwriting existing process overrides unless needed."""
    result: dict[str, str] = {}
    if not env_path.is_file():
        return result
    try:
        for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            if k:
                result[k] = v
    except OSError:
        pass
    return result


def get_workbench_models_config() -> dict[str, Any]:
    """Return current active models, defaults, and available options for each adjustable Agent."""
    from core.custom_agents import load_custom_agents  # noqa: PLC0415

    env_file_vars = _read_env_file_vars(PROJECT_ROOT / ".env")
    models: dict[str, str] = {}
    defaults: dict[str, str] = {}
    options: dict[str, list[str]] = {}

    for agent_id, spec in AGENT_MODEL_SPECS.items():
        env_key = spec["env"]
        default_val = spec["default"]
        current = (
            os.environ.get(env_key, "").strip()
            or env_file_vars.get(env_key, "").strip()
            or default_val
        )
        os.environ[env_key] = current
        models[agent_id] = current
        defaults[agent_id] = default_val
        opts = list(spec["options"])
        if current not in opts:
            opts.insert(0, current)
        options[agent_id] = opts

    for ca in load_custom_agents():
        cid = str(ca.get("id") or "")
        if not cid:
            continue
        cmodel = str(ca.get("model") or "MiniMax-M3.1-Flash")
        models[cid] = cmodel
        defaults[cid] = str(ca.get("default_model") or cmodel)
        copts = list(ca.get("options") or [cmodel])
        if cmodel not in copts:
            copts.insert(0, cmodel)
        options[cid] = copts

    return {
        "models": models,
        "defaults": defaults,
        "options": options,
    }


def _persist_env_updates(updates_by_env: dict[str, str]) -> None:
    if not updates_by_env:
        return
    env_path = PROJECT_ROOT / ".env"
    lines: list[str] = []
    if env_path.is_file():
        try:
            lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []

    seen_keys: set[str] = set()
    new_lines: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        check_line = stripped[len("export ") :].strip() if stripped.startswith("export ") else stripped
        if check_line and not check_line.startswith("#") and "=" in check_line:
            k, _, _ = check_line.partition("=")
            k = k.strip()
            if k in updates_by_env:
                new_lines.append(f"{k}={updates_by_env[k]}")
                seen_keys.add(k)
                continue
        new_lines.append(raw)

    for k, v in updates_by_env.items():
        if k not in seen_keys:
            new_lines.append(f"{k}={v}")

    try:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def update_workbench_models_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Update active Agent models in os.environ / custom_agents.json and persist to '.env'."""
    from core.custom_agents import load_custom_agents, save_custom_agents  # noqa: PLC0415

    reset = bool(payload.get("reset"))
    incoming = payload.get("models") if isinstance(payload.get("models"), dict) else payload

    updates_by_env: dict[str, str] = {}
    if reset:
        for spec in AGENT_MODEL_SPECS.values():
            env_key = spec["env"]
            default_val = spec["default"]
            os.environ[env_key] = default_val
            updates_by_env[env_key] = default_val
    elif isinstance(incoming, dict):
        for agent_id, spec in AGENT_MODEL_SPECS.items():
            if agent_id not in incoming:
                continue
            raw_val = str(incoming.get(agent_id) or "").strip()
            if not raw_val:
                raw_val = spec["default"]
            if not _MODEL_NAME_RE.match(raw_val):
                raise ValueError(f"Invalid model name for {agent_id}: {raw_val!r}")
            env_key = spec["env"]
            os.environ[env_key] = raw_val
            updates_by_env[env_key] = raw_val

        custom_list = load_custom_agents()
        custom_changed = False
        for ca in custom_list:
            cid = str(ca.get("id") or "")
            if cid and cid in incoming:
                raw_val = str(incoming.get(cid) or "").strip()
                if raw_val and _MODEL_NAME_RE.match(raw_val):
                    ca["model"] = raw_val
                    opts = list(ca.get("options") or [])
                    if raw_val not in opts:
                        opts.insert(0, raw_val)
                    ca["options"] = opts
                    custom_changed = True
        if custom_changed:
            save_custom_agents(custom_list)

    _persist_env_updates(updates_by_env)
    return get_workbench_models_config()


BYOK_PROVIDER_SPECS = [
    {
        "env": "MINIMAX_API_KEY",
        "label": "MiniMax Token Plan API Key",
        "agents": "Claude Code (預設 MiniMax-M3.1-Flash) / MiniMax Code",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "default_base_url": "https://api.minimax.cn/anthropic",
    },
    {
        "env": "ZHIPUAI_API_KEY",
        "label": "智譜 GLM Coding Plan API Key",
        "agents": "OpenAI Codex (預設 glm-5.3-flashx) / Zhipu zcode",
        "base_url_env": "OPENAI_BASE_URL",
        "default_base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
    },
    {
        "env": "OPENAI_API_KEY",
        "label": "OpenAI GPT GO Platform API Key",
        "agents": "K.H.A.V.I.S. Planner / Judge / GPT-5-Codex",
        "base_url_env": "",
        "default_base_url": "https://api.openai.com/v1",
    },
    {
        "env": "ANTIGRAVITY_API_KEY",
        "label": "Google Antigravity (AGY) API Key",
        "agents": "Antigravity CLI (agy / antigravity-pro)",
        "base_url_env": "",
        "default_base_url": "https://generativelanguage.googleapis.com",
    },
    {
        "env": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram 指揮官 Bot Token",
        "agents": "Telegram 遠端雙向派工通知",
        "base_url_env": "",
        "default_base_url": "",
    },
]


def _mask_secret(val: str) -> str:
    val = (val or "").strip()
    if not val:
        return ""
    if len(val) <= 8:
        return "••••" + val[-2:]
    return f"{val[:4]}••••••••{val[-4:]}"


def get_setup_wizard_status() -> dict[str, Any]:
    """Return BYOK credential health (masked), active workspace info, and one-liner install commands."""
    from core.workspace_manager import get_workspace_status  # noqa: PLC0415

    env_vars = _read_env_file_vars(PROJECT_ROOT / ".env")
    providers: list[dict[str, Any]] = []
    for spec in BYOK_PROVIDER_SPECS:
        k = spec["env"]
        raw_val = os.environ.get(k, "").strip() or env_vars.get(k, "").strip()
        if not raw_val and k == "ANTIGRAVITY_API_KEY":
            raw_val = os.environ.get("GOOGLE_API_KEY", "").strip() or env_vars.get("GOOGLE_API_KEY", "").strip()
        if not raw_val and k == "ZHIPUAI_API_KEY":
            raw_val = os.environ.get("GLM_API_KEY", "").strip() or env_vars.get("GLM_API_KEY", "").strip()

        providers.append(
            {
                "env": k,
                "label": spec["label"],
                "agents": spec["agents"],
                "configured": bool(raw_val),
                "masked": _mask_secret(raw_val) if raw_val else "未設定 (點此輸入)",
                "default_base_url": spec["default_base_url"],
            }
        )

    ws = get_workspace_status()
    models_cfg = get_workbench_models_config()
    env_template_lines = [
        "# K.H.A.V.I.S. 快速部署與 BYOK 環境變數配置 (.env)",
        f"CLAUDE_DISPATCH_MODEL={models_cfg['models'].get('claude', 'MiniMax-M3.1-Flash')}",
        f"CODEX_DISPATCH_MODEL={models_cfg['models'].get('codex', 'glm-5.3-flashx')}",
        f"ANTIGRAVITY_DISPATCH_MODEL={models_cfg['models'].get('antigravity', 'antigravity-pro')}",
        f"MINIMAX_DISPATCH_MODEL={models_cfg['models'].get('minimax', 'MiniMax-M3.1')}",
        f"ZCODE_DISPATCH_MODEL={models_cfg['models'].get('zcode', 'glm-5.3-flashx')}",
        f"KHAVIS_ACTIVE_PROJECT={ws['active_project']}",
        f"KHAVIS_ISOLATION_MODE={ws['isolation_mode']}",
        "",
        "# 填入您的訂閱方案金鑰 (BYOK):",
        "MINIMAX_API_KEY=your_minimax_token_plan_key",
        "ZHIPUAI_API_KEY=your_glm_coding_plan_key",
        "OPENAI_API_KEY=your_openai_api_key",
        "ANTIGRAVITY_API_KEY=your_antigravity_key",
        "TELEGRAM_BOT_TOKEN=your_telegram_bot_token",
    ]
    return {
        "ok": True,
        "providers": providers,
        "cli_tools": get_agent_fleet_status(),
        "workspace": {
            "active_project": ws["active_project"],
            "active_path": ws["active_path"],
            "isolation_mode": ws["isolation_mode"],
        },
        "models": models_cfg["models"],
        "quick_commands": {
            "local_wizard": "bash scripts/quick_setup_wizard.sh",
            "agent_wrappers": "sudo bash scripts/setup_tencent_agents.sh",
            "docker_up": "docker compose -f deploy/docker-compose.all-in-one.yml up -d --build",
        },
        "deploy_commands": {
            "local_wizard": "bash scripts/quick_setup_wizard.sh",
            "agent_wrappers": "sudo bash scripts/setup_tencent_agents.sh",
            "docker_up": "docker compose -f deploy/docker-compose.all-in-one.yml up -d --build",
        },
        "env_template": "\n".join(env_template_lines),
    }


def update_setup_wizard_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Save non-empty BYOK keys or workspace defaults from the Setup Wizard into os.environ & .env."""
    allowed_env_keys = {spec["env"] for spec in BYOK_PROVIDER_SPECS} | {
        "KHAVIS_ACTIVE_PROJECT",
        "KHAVIS_ISOLATION_MODE",
        "OLLAMA_BASE_URL",
    }
    incoming = payload.get("keys") if isinstance(payload.get("keys"), dict) else payload
    updates: dict[str, str] = {}
    if isinstance(incoming, dict):
        for k, v in incoming.items():
            if k not in allowed_env_keys:
                continue
            val = str(v or "").strip()
            if not val or "••••" in val:
                continue
            if "\n" in val or "\r" in val:
                continue
            os.environ[k] = val
            updates[k] = val
            if k == "ZHIPUAI_API_KEY":
                os.environ["GLM_API_KEY"] = val
                updates["GLM_API_KEY"] = val
            elif k == "ANTIGRAVITY_API_KEY":
                os.environ["GOOGLE_API_KEY"] = val
                updates["GOOGLE_API_KEY"] = val

    _persist_env_updates(updates)
    return get_setup_wizard_status()


def get_agent_fleet_status() -> list[dict[str, Any]]:
    """Probe the 5 CLI agents on Tencent Cloud, K.H.A.V.I.S. team, and any user-defined Custom Agents."""
    from core.custom_agents import enrich_custom_agent_status, load_custom_agents  # noqa: PLC0415

    cfg = get_workbench_models_config()
    active_models = cfg["models"]
    model_options = cfg["options"]
    default_models = cfg["defaults"]

    agents = [
        {
            "id": "claude",
            "name": "Claude Code",
            "binary": "claude",
            "model": active_models["claude"],
            "default_model": default_models["claude"],
            "options": model_options["claude"],
            "adjustable": True,
            "custom": False,
            "plan": f"Dynamic Routing ({active_models['claude']})",
            "desc": f"Anthropic Claude Code CLI (當前綁定 {active_models['claude']} 驅動)",
            "tier": "Tier-1",
            "icon": "fa-terminal",
            "color": "#10B981",
        },
        {
            "id": "codex",
            "name": "OpenAI Codex",
            "binary": "codex",
            "model": active_models["codex"],
            "default_model": default_models["codex"],
            "options": model_options["codex"],
            "adjustable": True,
            "custom": False,
            "plan": f"Dynamic Routing ({active_models['codex']})",
            "desc": f"OpenAI Codex CLI (當前綁定 {active_models['codex']} 驅動)",
            "tier": "Tier-1",
            "icon": "fa-code",
            "color": "#6366F1",
        },
        {
            "id": "antigravity",
            "name": "Antigravity",
            "binary": "antigravity",
            "model": active_models["antigravity"],
            "default_model": default_models["antigravity"],
            "options": model_options["antigravity"],
            "adjustable": True,
            "custom": False,
            "plan": f"Antigravity AI Pro ({active_models['antigravity']})",
            "desc": f"Google Antigravity Agentic CLI (當前綁定 {active_models['antigravity']})",
            "tier": "Tier-1",
            "icon": "fa-rocket",
            "color": "#0EA5E9",
        },
        {
            "id": "minimax",
            "name": "MiniMax Code",
            "binary": "minimax",
            "model": active_models["minimax"],
            "default_model": default_models["minimax"],
            "options": model_options["minimax"],
            "adjustable": True,
            "custom": False,
            "plan": f"MiniMax Token Plan ({active_models['minimax']})",
            "desc": f"MiniMax Code CLI (當前綁定 {active_models['minimax']})",
            "tier": "Tier-2",
            "icon": "fa-microchip",
            "color": "#14B8A6",
        },
        {
            "id": "zcode",
            "name": "Zhipu zcode",
            "binary": "zcode",
            "model": active_models["zcode"],
            "default_model": default_models["zcode"],
            "options": model_options["zcode"],
            "adjustable": True,
            "custom": False,
            "plan": f"GLM Coding Plan ({active_models['zcode']})",
            "desc": f"智譜 GLM 專屬代碼 CLI (當前綁定 {active_models['zcode']})",
            "tier": "Tier-2",
            "icon": "fa-bolt",
            "color": "#F59E0B",
        },
        {
            "id": "khavis",
            "name": "K.H.A.V.I.S. Team",
            "binary": "internal",
            "model": "LangGraph 7-Role",
            "default_model": "LangGraph 7-Role",
            "options": ["LangGraph 7-Role"],
            "adjustable": False,
            "custom": False,
            "plan": "全付費方案容錯 + Ollama 兜底",
            "desc": "LangGraph 7 角色異質多 Agent 協同流水線 (Planner/Coder/Debater/Verifier)",
            "tier": "Master",
            "icon": "fa-sitemap",
            "color": "#38BDF8",
        },
    ]

    for a in agents:
        if a["id"] == "khavis":
            a["installed"] = True
            a["path"] = "internal://langgraph/7-roles"
            a["version"] = "v0.4.0 (LangGraph 7 Roles)"
            a["status"] = "ready"
            continue

        binary_path = shutil.which(a["binary"])
        if not binary_path and a["id"] == "antigravity":
            binary_path = shutil.which("agy")
        if not binary_path and a["id"] == "minimax":
            binary_path = shutil.which("mcode")

        a["installed"] = bool(binary_path)
        a["path"] = binary_path or "Not in PATH"
        if binary_path:
            a["status"] = "ready"
            a["version"] = "Installed (CLI Ready)"
        else:
            a["status"] = "mock_ready"
            a["version"] = "Adapter Standby (Simulated on Host)"

    for custom_raw in load_custom_agents():
        agents.append(enrich_custom_agent_status(custom_raw))

    return agents


def list_deliverable_artifacts() -> list[dict[str, Any]]:
    """Scan workspace for delivered documents, presentations, and code artifacts."""
    artifacts: list[dict[str, Any]] = []

    # Key generated files in khavis
    scan_targets = [
        ("scripts/quick_setup_wizard.sh", "開源/團隊快速部署與 BYOK 精靈腳本", "script", "fa-magic"),
        ("core/workspace_manager.py", "共用專案資料夾與 Git Worktree 管理模組", "code", "fa-code-branch"),
        ("core/custom_agents.py", "用戶自訂 Agent 動態擴充註冊表模組", "code", "fa-plug"),
        ("outputs/e2e_collaborative_code.py", "跨模型多 Agent 協同代碼產出", "code", "fa-code"),
        ("scripts/e2e_multiagent_code_dispatch.py", "多 Agent 並發協同派工腳本", "script", "fa-project-diagram"),
        ("scripts/stress_test_failover_alerts.py", "端到端壓力測試腳本", "script", "fa-bolt"),
        ("docker-compose.yml", "一體化 Docker Compose 部署配置", "config", "fa-cubes"),
        ("deploy/docker-compose.all-in-one.yml", "全服務部署編排 (All-in-One)", "config", "fa-server"),
        ("core/quota_tracker.py", "主動額度與速率限制追蹤模組", "code", "fa-tachometer-alt"),
        ("core/escalation.py", "多 Agent 自動派工與升級模組", "code", "fa-users-cog"),
        ("core/alerting.py", "Webhook 即時防抖警報模組", "code", "fa-bell"),
        ("web/dashboard.py", "實時配額與派工儀表板", "web", "fa-chart-pie"),
        ("README.zh-TW.md", "K.H.A.V.I.S. 繁體中文架構與使用指南", "doc", "fa-book"),
    ]

    for rel_path, title, cat, icon in scan_targets:
        p = PROJECT_ROOT / rel_path
        if p.exists():
            st = p.stat()
            size_kb = max(1, round(st.st_size / 1024, 1))
            artifacts.append(
                {
                    "name": title,
                    "rel_path": rel_path,
                    "path": str(p),
                    "type": cat,
                    "size": f"{size_kb} KB",
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                    "icon": icon,
                    "badge": cat.upper(),
                }
            )

    return artifacts


_BLOCKED_SUFFIXES = {".env", ".pem", ".key", ".sec", ".ses", ".p12", ".pfx", ".sqlite", ".db"}


def read_artifact_content(rel_or_abs_path: str) -> dict[str, Any]:
    """Safely read content of a whitelisted artifact or shared workspace file for browser preview."""
    from core.workspace_manager import get_workspace_root  # noqa: PLC0415

    raw = (rel_or_abs_path or "").strip()
    if not raw:
        return {"ok": False, "error": "Empty artifact path"}

    target_path = Path(raw)
    if not target_path.is_absolute():
        target_path = (PROJECT_ROOT / target_path).resolve()
    else:
        target_path = target_path.resolve()

    if any(part.startswith(".") for part in target_path.parts) or target_path.suffix.lower() in _BLOCKED_SUFFIXES:
        return {"ok": False, "error": "Access denied: protected or hidden resource"}

    allowed_items = list_deliverable_artifacts()
    allowed_paths = {Path(item["path"]).resolve() for item in allowed_items if "path" in item}
    ws_root = get_workspace_root()
    is_allowed = (
        target_path in allowed_paths
        or target_path.is_relative_to(ws_root)
        or any(ap.is_dir() and target_path.is_relative_to(ap) for ap in allowed_paths)
    )
    if not is_allowed:
        return {"ok": False, "error": "Access denied: artifact is not in the deliverable whitelist"}

    if not target_path.exists():
        return {"ok": False, "error": "File not found"}

    if target_path.is_dir():
        files = sorted(
            f for f in target_path.rglob("*")
            if f.is_file() and not any(p.startswith(".") for p in f.parts)
        )
        summary_lines = [
            f"# 簡報/產物目錄預覽: {target_path.name}",
            f"# 路徑: {target_path}",
            f"# 包含檔案數: {len(files)}",
            "=" * 72,
        ]
        for f in files[:10]:
            rel_name = f.relative_to(target_path)
            summary_lines.append(f"\n--- [{rel_name}] ({f.stat().st_size} bytes) ---")
            if f.suffix.lower() in {".html", ".md", ".txt", ".json", ".py"}:
                snippet = f.read_text(encoding="utf-8", errors="replace")[:2000]
                summary_lines.append(snippet)
        joined = "\n".join(summary_lines)
        return {
            "ok": True,
            "filename": target_path.name,
            "path": str(target_path),
            "size": len(joined),
            "content": joined,
            "ext": ".dir",
        }

    if not target_path.is_file():
        return {"ok": False, "error": "File not found"}

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "filename": target_path.name,
            "path": str(target_path),
            "size": len(content),
            "content": content,
            "ext": target_path.suffix.lower(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def render_workbench_html() -> str:
    """Generate the graphical, interactive dark/light SPA Workbench."""
    return """<!DOCTYPE html>
<html lang="zh-Hant" class="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K.H.A.V.I.S. · 圖形化智慧指揮工作台 (Unified Graphical Workbench)</title>

  <!-- Fonts & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#F0F9FF',
              500: '#0EA5E9',
              600: '#0284C7',
              700: '#0369A1',
            },
            dark: {
              bg: '#070B14',
              surface: '#0F1626',
              card: '#162033',
              border: 'rgba(255, 255, 255, 0.08)',
            }
          },
          fontFamily: {
            sans: ['Inter', 'Noto Sans TC', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }
        }
      }
    }
  </script>

  <style>
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(156, 163, 175, 0.3); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(156, 163, 175, 0.5); }

    .glass-panel {
      background: rgba(15, 22, 38, 0.85);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .bg-grid-pattern {
      background-image: radial-gradient(rgba(56, 189, 248, 0.12) 1px, transparent 1px);
      background-size: 22px 22px;
    }

    @keyframes flowDash {
      to { stroke-dashoffset: -40; }
    }
    .flow-line-active {
      stroke-dasharray: 6 6;
      animation: flowDash 1s linear infinite;
    }
    .flow-line-running {
      stroke-dasharray: 8 4;
      animation: flowDash 0.45s linear infinite;
      filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.85));
    }

    .agent-node-card {
      transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .agent-node-card:hover {
      transform: translateY(-2px);
    }
    .agent-node-card.selected {
      border-color: rgba(14, 165, 233, 0.75) !important;
      box-shadow: 0 0 20px -4px rgba(14, 165, 233, 0.35), inset 0 0 12px rgba(14, 165, 233, 0.12);
    }
    .agent-node-card.running {
      border-color: rgba(16, 185, 129, 0.85) !important;
      box-shadow: 0 0 24px -2px rgba(16, 185, 129, 0.45);
    }

    html:not(.dark) body {
      background-color: #F1F5F9 !important;
      color: #0F172A !important;
    }
    html:not(.dark) header,
    html:not(.dark) aside,
    html:not(.dark) main,
    html:not(.dark) #artifact-drawer,
    html:not(.dark) #drawer-content {
      background-color: #FFFFFF !important;
      color: #0F172A !important;
      border-color: rgba(15, 23, 42, 0.1) !important;
    }
    html:not(.dark) .glass-panel {
      background: rgba(255, 255, 255, 0.96) !important;
      border: 1px solid rgba(15, 23, 42, 0.1) !important;
      box-shadow: 0 6px 24px -4px rgba(15, 23, 42, 0.06);
    }
    html:not(.dark) .text-white {
      color: #0F172A !important;
    }
    html:not(.dark) .text-slate-200,
    html:not(.dark) .text-slate-300 {
      color: #334155 !important;
    }
    html:not(.dark) textarea,
    html:not(.dark) select {
      background-color: #F8FAFC !important;
      color: #0F172A !important;
      border-color: rgba(15, 23, 42, 0.15) !important;
    }
  </style>
</head>
<body class="bg-[#070B14] text-slate-200 font-sans antialiased min-h-screen flex flex-col">

  <!-- Top Navigation Bar -->
  <header class="sticky top-0 z-40 border-b border-white/10 bg-[#070B14]/90 backdrop-blur-md px-4 lg:px-8 py-3 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 via-cyan-500 to-teal-400 flex items-center justify-center shadow-lg shadow-sky-500/25 text-white font-black text-lg">
        K
      </div>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-lg text-white tracking-tight">K.H.A.V.I.S.</span>
          <span class="px-2 py-0.5 text-[11px] font-bold rounded-md bg-sky-500/20 text-sky-400 border border-sky-500/30">VISUAL WORKBENCH</span>
          <span class="px-2 py-0.5 text-[11px] font-bold rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
            TENCENT FLEET READY
          </span>
        </div>
        <p class="text-xs text-slate-400">圖形化多 Agent 調度拓撲 · Claude Code (MiniMax-M3.1-Flash) · Antigravity (AGY) · 7 角色 DAG 流水線</p>
      </div>
    </div>

    <!-- Top Right Quick Status Strip -->
    <div class="flex items-center gap-3">
      <div id="quota-capsule-strip" class="hidden xl:flex items-center gap-2 text-xs font-mono">
        <!-- Injected via JS -->
      </div>

      <button onclick="toggleTheme()" class="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition" title="切換深淺色主題">
        <i id="theme-icon" class="fas fa-sun text-amber-400"></i>
      </button>

      <a href="/dashboard" class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition border border-white/10">
        <i class="fas fa-chart-line text-sky-400"></i>
        <span>即時儀表板</span>
      </a>
    </div>
  </header>

  <!-- Main Shell Layout -->
  <div class="flex-1 flex flex-col md:flex-row overflow-hidden">

    <!-- Sidebar Navigation -->
    <aside class="w-full md:w-64 border-r border-white/10 bg-[#0F1626] p-4 flex md:flex-col gap-2 shrink-0 overflow-x-auto">
      <div class="text-[11px] font-bold text-slate-400 tracking-wider uppercase px-3 py-1 hidden md:block">
        圖形化指揮視圖
      </div>

      <button onclick="switchTab('command')" id="nav-command" class="tab-btn active flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-white bg-sky-600/20 text-sky-400 border border-sky-500/30">
        <i class="fas fa-project-diagram w-5 text-center"></i>
        <span>圖形化派工指揮中心</span>
      </button>

      <button onclick="switchTab('artifacts')" id="nav-artifacts" class="tab-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-slate-300 hover:bg-white/5 hover:text-white">
        <i class="fas fa-folder-open w-5 text-center text-teal-400"></i>
        <span>交付文件庫</span>
        <span id="artifacts-badge" class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300">--</span>
      </button>

      <button onclick="switchTab('quotas')" id="nav-quotas" class="tab-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-slate-300 hover:bg-white/5 hover:text-white">
        <i class="fas fa-chart-pie w-5 text-center text-amber-400"></i>
        <span>視覺化額度與熔斷</span>
      </button>

      <button onclick="switchTab('agents')" id="nav-agents" class="tab-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-slate-300 hover:bg-white/5 hover:text-white">
        <i class="fas fa-network-wired w-5 text-center text-indigo-400"></i>
        <span>雲端主機 Agent 拓撲</span>
      </button>

      <button onclick="switchTab('wizard')" id="nav-wizard" class="tab-btn flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-slate-300 hover:bg-white/5 hover:text-white">
        <i class="fas fa-magic w-5 text-center text-emerald-400"></i>
        <span>快速部署與 BYOK 精靈</span>
      </button>

      <!-- Mini Visual Architecture Summary in Sidebar -->
      <div class="mt-auto hidden md:block pt-4 border-t border-white/10 space-y-2">
        <div class="p-3 rounded-xl bg-white/5 border border-white/5 text-xs space-y-2">
          <div class="font-bold text-slate-200 flex items-center justify-between">
            <span class="flex items-center gap-1.5">
              <i class="fas fa-sliders-h text-sky-400"></i>
              <span>當前綁定模型配置</span>
            </span>
            <button type="button" onclick="toggleModelSettingsPanel()" class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 transition">
              調整
            </button>
          </div>
          <div id="sidebar-model-summary" class="text-[11px] text-slate-400 space-y-1 font-mono">
            <div class="flex justify-between gap-1"><span>Claude:</span><span id="side-model-claude" class="text-emerald-400 truncate">MiniMax-M3.1-Flash</span></div>
            <div class="flex justify-between gap-1"><span>Codex:</span><span id="side-model-codex" class="text-indigo-400 truncate">glm-5.3-flashx</span></div>
            <div class="flex justify-between gap-1"><span>Antigravity:</span><span id="side-model-antigravity" class="text-sky-400 truncate">antigravity-pro</span></div>
            <div class="flex justify-between gap-1"><span>MiniMax:</span><span id="side-model-minimax" class="text-teal-400 truncate">MiniMax-M3.1</span></div>
            <div class="flex justify-between gap-1"><span>zcode:</span><span id="side-model-zcode" class="text-amber-400 truncate">glm-5.3-flashx</span></div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Content Work Area -->
    <main class="flex-1 overflow-y-auto p-4 lg:p-6 bg-[#070B14] bg-grid-pattern">

      <!-- ================================================================= -->
      <!-- VIEW 1: 圖形化任務派工指揮中心 (Graphical Command Center) -->
      <!-- ================================================================= -->
      <section id="view-command" class="tab-content block space-y-5">

        <!-- Top 4 Visual Plan Status Cards with Mini Progress Bars -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="glass-panel p-3.5 rounded-2xl border border-white/10 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span id="card-title-claude">MiniMax-M3.1-Flash</span>
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-mono">Claude Code 綁定</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-lg font-bold text-white font-mono" id="stat-minimax">HEALTHY</span>
              <span class="text-[11px] text-slate-400 font-mono">可動態切換模型</span>
            </div>
            <div class="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-emerald-500 to-teal-400 w-[94%] rounded-full"></div>
            </div>
          </div>

          <div class="glass-panel p-3.5 rounded-2xl border border-white/10 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span id="card-title-codex">glm-5.3-flashx</span>
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 font-mono">Codex / zcode</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-lg font-bold text-white font-mono" id="stat-glm">HEALTHY</span>
              <span class="text-[11px] text-slate-400 font-mono">可動態切換模型</span>
            </div>
            <div class="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-400 w-[92%] rounded-full"></div>
            </div>
          </div>

          <div class="glass-panel p-3.5 rounded-2xl border border-white/10 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                GPT GO (OpenAI)
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-400 font-mono">Planner / 推理</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-lg font-bold text-white font-mono" id="stat-gpt">HEALTHY</span>
              <span class="text-[11px] text-slate-400 font-mono">系統架構設計</span>
            </div>
            <div class="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-sky-500 to-blue-400 w-[90%] rounded-full"></div>
            </div>
          </div>

          <div class="glass-panel p-3.5 rounded-2xl border border-white/10 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span id="card-title-antigravity">antigravity-pro</span>
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400 font-mono">Antigravity (AGY)</span>
            </div>
            <div class="flex items-baseline justify-between">
              <span class="text-lg font-bold text-white font-mono" id="stat-antigravity">READY</span>
              <span class="text-[11px] text-slate-400 font-mono">全域自主代理</span>
            </div>
            <div class="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-cyan-500 to-teal-400 w-[98%] rounded-full"></div>
            </div>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- SHARED PROJECT WORKSPACE & GIT WORKTREE / DIFF CONSOLE          -->
        <!-- =============================================================== -->
        <div id="workspace-control-bar" class="glass-panel p-4 rounded-2xl border border-teal-500/25 space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
                <i class="fas fa-folder-tree"></i>
              </div>
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-white text-xs sm:text-sm">多 CLI 共用專案資料夾與 Git Worktree 協同引擎</span>
                  <span id="ws-mode-badge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    🤝 共用同一個專案資料夾 (流暢接力讀寫)
                  </span>
                </div>
                <p class="text-[11px] text-slate-400 font-mono truncate max-w-2xl" id="ws-active-path">載入共用工作區路徑中...</p>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 text-xs">
              <div class="flex items-center gap-1 bg-[#050811] border border-white/10 rounded-lg px-2 py-1">
                <span class="text-slate-400 text-[11px]">專案目錄:</span>
                <select id="ws-project-select" onchange="switchSharedProject(this.value)" class="bg-transparent text-teal-300 font-mono text-xs focus:outline-none cursor-pointer">
                  <option value="shared-app">shared-app</option>
                </select>
                <button type="button" onclick="promptNewProjectFolder()" class="text-sky-400 hover:text-sky-300 px-1" title="新建共用專案資料夾">
                  <i class="fas fa-plus-circle"></i>
                </button>
              </div>

              <div class="inline-flex rounded-lg bg-[#050811] p-0.5 border border-white/10">
                <button type="button" id="btn-mode-shared" onclick="setIsolationMode('shared')" class="px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 transition" title="所有 CLI 直接共用同一個專案資料夾，前一個 CLI 產出的檔案下一個 CLI 可直接讀取修改">
                  🤝 共用資料夾 (預設)
                </button>
                <button type="button" id="btn-mode-worktree" onclick="setIsolationMode('worktree')" class="px-2.5 py-1 rounded-md text-xs font-medium text-slate-400 hover:text-white transition" title="並發派工時為每個 Agent 自動建立獨立 Git Worktree 分支，避免同時寫入衝突並支援 Diff 比較合併">
                  🌿 Git Worktree 分支隔離
                </button>
              </div>

              <button type="button" onclick="toggleWorkspaceDiffPanel()" class="px-2.5 py-1 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 font-medium transition">
                <i class="fas fa-code-branch mr-1"></i>🔍 專案檔案與 Diff 對比 (<span id="ws-file-count">0</span>)
              </button>
              <button type="button" onclick="commitSharedWorkspace()" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 font-medium transition" title="將目前共用資料夾的所有變更建立 Git Commit 基準快照">
                <i class="fas fa-camera mr-1"></i>Commit 快照
              </button>
            </div>
          </div>

          <!-- Expandable Shared Files & Visual Diff / Worktree Merge Drawer -->
          <div id="workspace-diff-panel" class="hidden pt-3 border-t border-white/10 grid grid-cols-1 lg:grid-cols-12 gap-4 text-xs">
            <!-- Left: Shared Project Files -->
            <div class="lg:col-span-4 bg-[#050811]/90 border border-white/10 rounded-xl p-3 space-y-2">
              <div class="flex items-center justify-between font-bold text-slate-200 border-b border-white/10 pb-1.5">
                <span><i class="fas fa-folder-open text-teal-400 mr-1.5"></i>共用資料夾檔案清單</span>
                <button type="button" onclick="loadWorkspaceStatus()" class="text-[11px] text-sky-400 hover:underline">重新整理</button>
              </div>
              <div id="ws-files-list" class="space-y-1.5 max-h-60 overflow-y-auto font-mono text-[11px]">
                <div class="text-slate-500 py-2 text-center">尚無檔案</div>
              </div>
            </div>

            <!-- Right: Visual Unified Diff & Worktree Branch Merge -->
            <div class="lg:col-span-8 bg-[#050811]/90 border border-white/10 rounded-xl p-3 space-y-2">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-1.5">
                <div class="flex items-center gap-1.5 flex-wrap" id="ws-diff-tabs">
                  <!-- Populated via JS -->
                </div>
                <div id="ws-merge-action" class="hidden">
                  <!-- Merge button injected when viewing a worktree diff -->
                </div>
              </div>
              <div id="ws-diff-viewer" class="font-mono text-[11px] leading-relaxed max-h-60 overflow-y-auto p-2 rounded bg-black/50 text-slate-300 whitespace-pre-wrap">
                目前共用專案資料夾工作區乾淨（無未提交之 Diff 差異）。
              </div>
            </div>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- INTERACTIVE GRAPHICAL TOPOLOGY CANVAS (互動式圖形化調度畫布) -->
        <!-- =============================================================== -->
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <i class="fas fa-sitemap"></i>
              </div>
              <div>
                <h2 class="font-bold text-white text-sm sm:text-base">互動式多 Agent 視覺化調度拓撲圖 (支援模型動態切換 & 用戶自訂 Agent)</h2>
                <p class="text-[11px] text-slate-400">點擊節點卡片啟用/停用 Agent；可隨時透過下拉選單切換模型，或點擊「➕ 新增自訂 Agent」掛載您慣用的外部 CLI / API Agent</p>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <button type="button" onclick="toggleCustomAgentPanel()" class="px-2.5 py-1 rounded-lg bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 border border-pink-500/30 font-medium transition">
                <i class="fas fa-plug mr-1"></i>➕ 新增自訂 Agent
              </button>
              <button type="button" onclick="toggleModelSettingsPanel()" class="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 font-medium transition">
                <i class="fas fa-sliders-h mr-1"></i>⚙️ 模型設定面板
              </button>
              <button type="button" onclick="saveAgentModels(false)" class="px-2.5 py-1 rounded-lg bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/30 font-medium transition">
                <i class="fas fa-save mr-1"></i>💾 儲存為預設
              </button>
              <button type="button" onclick="selectPresetAgents('all')" class="px-2.5 py-1 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 font-medium transition">
                <i class="fas fa-check-double mr-1"></i>全集群並發
              </button>
              <button type="button" onclick="selectPresetAgents('code_trio')" class="px-2.5 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 font-medium transition">
                <i class="fas fa-laptop-code mr-1"></i>代碼三劍客
              </button>
              <button type="button" onclick="selectPresetAgents('khavis_only')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 font-medium transition">
                僅 K.H.A.V.I.S. 團隊
              </button>
            </div>
          </div>

          <!-- Expandable User-Defined Custom Agent Registration Panel -->
          <div id="custom-agent-panel" class="hidden rounded-xl bg-[#120D24] border border-pink-500/30 p-4 space-y-3 text-xs">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div class="flex items-center gap-2">
                <i class="fas fa-plug text-pink-400"></i>
                <span class="font-bold text-white text-xs sm:text-sm">掛載您自行使用的 Agent (支援任意本地 CLI 工具或 OpenAI 相容 HTTP 端點)</span>
              </div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-slate-400 text-[11px]">一鍵載入常用範本:</span>
                <button type="button" onclick="fillCustomAgentPreset('aider')" class="px-2 py-0.5 rounded bg-white/5 hover:bg-pink-500/20 text-pink-300 border border-white/10">⚡ Aider CLI</button>
                <button type="button" onclick="fillCustomAgentPreset('opencode')" class="px-2 py-0.5 rounded bg-white/5 hover:bg-pink-500/20 text-pink-300 border border-white/10">🚀 OpenCode CLI</button>
                <button type="button" onclick="fillCustomAgentPreset('goose')" class="px-2 py-0.5 rounded bg-white/5 hover:bg-pink-500/20 text-pink-300 border border-white/10">🪿 Block Goose</button>
                <button type="button" onclick="fillCustomAgentPreset('deepseek')" class="px-2 py-0.5 rounded bg-white/5 hover:bg-pink-500/20 text-pink-300 border border-white/10">🧠 DeepSeek / Qwen HTTP</button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label class="text-slate-300 block mb-1">Agent 代號 (英文小寫 ID)</label>
                <input id="ca-id" type="text" placeholder="例如: aider 或 my-agent" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-white" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">顯示名稱</label>
                <input id="ca-name" type="text" placeholder="例如: Aider Pair Programmer" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 text-white" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">執行類型</label>
                <select id="ca-type" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 text-white font-mono">
                  <option value="cli">CLI 執行檔 (共用專案目錄 + API 兜底)</option>
                  <option value="http">HTTP API (OpenAI 相容端點)</option>
                </select>
              </div>
              <div>
                <label class="text-slate-300 block mb-1">預設綁定模型</label>
                <input id="ca-model" type="text" value="MiniMax-M3.1-Flash" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-emerald-300" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">CLI 執行檔名稱或路徑</label>
                <input id="ca-binary" type="text" placeholder="例如: aider / opencode / goose" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-white" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">CLI 參數模板 (含 {model} 與 {prompt})</label>
                <input id="ca-args" type="text" value="--model {model} --message {prompt}" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-slate-200" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">使用之 API Key 環境變數</label>
                <input id="ca-key-env" type="text" value="MINIMAX_API_KEY" placeholder="MINIMAX_API_KEY / ZHIPUAI_API_KEY" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-amber-300" />
              </div>
              <div>
                <label class="text-slate-300 block mb-1">自訂 Base URL (選填)</label>
                <input id="ca-base-url" type="text" placeholder="留空則依模型自動路由" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-slate-300" />
              </div>
            </div>

            <div class="flex items-center justify-between pt-1">
              <span class="text-[11px] text-slate-400">💡 註冊後將自動出現在下方拓撲畫布，並與其他 CLI 共用同一個專案資料夾（若主機尚未安裝該 CLI 執行檔，亦會自動以 API 轉接模式執行）。</span>
              <button type="button" onclick="submitCustomAgent()" class="px-4 py-1.5 rounded-lg bg-pink-500 hover:bg-pink-400 text-slate-950 font-bold transition">
                <i class="fas fa-plus mr-1"></i>註冊並加入拓撲畫布
              </button>
            </div>
          </div>

          <!-- Expandable Adjustable Model Settings Panel -->
          <div id="model-settings-panel" class="hidden rounded-xl bg-[#091020] border border-sky-500/30 p-4 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div class="flex items-center gap-2">
                <i class="fas fa-cogs text-amber-400"></i>
                <span class="font-bold text-white text-xs sm:text-sm">Agent 驅動模型自訂與預設持久化設定</span>
                <span id="model-save-toast" class="text-[11px] font-mono text-emerald-400 hidden"></span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <button type="button" onclick="saveAgentModels(true)" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-rose-500/20 text-slate-300 hover:text-rose-300 border border-white/10 transition">
                  <i class="fas fa-undo mr-1"></i>還原系統初始預設
                </button>
                <button type="button" onclick="saveAgentModels(false)" class="px-3 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition">
                  <i class="fas fa-save mr-1"></i>儲存並寫入伺服器預設 (.env)
                </button>
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
              <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 space-y-1.5">
                <label class="text-emerald-400 font-bold block">Claude Code 模型</label>
                <input id="custom-input-claude" type="text" value="MiniMax-M3.1-Flash" oninput="onCustomModelInput('claude', this.value)" class="w-full bg-[#050811] border border-white/15 rounded px-2 py-1 text-xs font-mono text-white focus:outline-none focus:border-emerald-400" placeholder="輸入或選擇模型..." />
                <div class="text-[10px] text-slate-400 font-mono">預設: MiniMax-M3.1-Flash</div>
              </div>
              <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 space-y-1.5">
                <label class="text-indigo-400 font-bold block">OpenAI Codex 模型</label>
                <input id="custom-input-codex" type="text" value="glm-5.3-flashx" oninput="onCustomModelInput('codex', this.value)" class="w-full bg-[#050811] border border-white/15 rounded px-2 py-1 text-xs font-mono text-white focus:outline-none focus:border-indigo-400" placeholder="輸入或選擇模型..." />
                <div class="text-[10px] text-slate-400 font-mono">預設: glm-5.3-flashx</div>
              </div>
              <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 space-y-1.5">
                <label class="text-sky-400 font-bold block">Antigravity (AGY) 模型</label>
                <input id="custom-input-antigravity" type="text" value="antigravity-pro" oninput="onCustomModelInput('antigravity', this.value)" class="w-full bg-[#050811] border border-white/15 rounded px-2 py-1 text-xs font-mono text-white focus:outline-none focus:border-sky-400" placeholder="輸入或選擇模型..." />
                <div class="text-[10px] text-slate-400 font-mono">預設: antigravity-pro</div>
              </div>
              <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 space-y-1.5">
                <label class="text-teal-400 font-bold block">MiniMax Code 模型</label>
                <input id="custom-input-minimax" type="text" value="MiniMax-M3.1" oninput="onCustomModelInput('minimax', this.value)" class="w-full bg-[#050811] border border-white/15 rounded px-2 py-1 text-xs font-mono text-white focus:outline-none focus:border-teal-400" placeholder="輸入或選擇模型..." />
                <div class="text-[10px] text-slate-400 font-mono">預設: MiniMax-M3.1</div>
              </div>
              <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 space-y-1.5">
                <label class="text-amber-400 font-bold block">Zhipu zcode 模型</label>
                <input id="custom-input-zcode" type="text" value="glm-5.3-flashx" oninput="onCustomModelInput('zcode', this.value)" class="w-full bg-[#050811] border border-white/15 rounded px-2 py-1 text-xs font-mono text-white focus:outline-none focus:border-amber-400" placeholder="輸入或選擇模型..." />
                <div class="text-[10px] text-slate-400 font-mono">預設: glm-5.3-flashx</div>
              </div>
            </div>
          </div>

          <!-- Graphical SVG Flow + Interactive Node Grid -->
          <div class="relative rounded-xl bg-[#050811]/90 border border-white/10 p-4 overflow-hidden">
            <!-- SVG Dynamic Connector Canvas (Desktop) -->
            <svg id="topology-svg" class="hidden lg:block w-full h-24 mb-2" viewBox="0 0 1000 95" preserveAspectRatio="none">
              <defs>
                <linearGradient id="beamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#0EA5E9" stop-opacity="0.9"/>
                  <stop offset="50%" stop-color="#10B981" stop-opacity="0.9"/>
                  <stop offset="100%" stop-color="#38BDF8" stop-opacity="0.9"/>
                </linearGradient>
              </defs>
              <!-- Dispatcher Hub at Top Center (500, 14) -->
              <circle cx="500" cy="14" r="8" fill="#0EA5E9" />
              <circle cx="500" cy="14" r="14" fill="none" stroke="#0EA5E9" stroke-opacity="0.4" stroke-width="2" />
              <text x="500" y="18" text-anchor="middle" fill="#E2E8F0" font-size="10" font-family="JetBrains Mono" dy="-12">COMMAND DISPATCHER</text>

              <!-- 6 Branching Paths to the 6 Agent Cards (x = 83, 250, 416, 583, 750, 916) -->
              <path id="beam-claude" d="M500,22 C500,55 83,40 83,90" fill="none" stroke="#1E293B" stroke-width="2.5" />
              <path id="beam-codex" d="M500,22 C500,55 250,40 250,90" fill="none" stroke="#1E293B" stroke-width="2.5" />
              <path id="beam-antigravity" d="M500,22 C500,55 416,40 416,90" fill="none" stroke="#1E293B" stroke-width="2.5" />
              <path id="beam-minimax" d="M500,22 C500,55 583,40 583,90" fill="none" stroke="#1E293B" stroke-width="2.5" />
              <path id="beam-zcode" d="M500,22 C500,55 750,40 750,90" fill="none" stroke="#1E293B" stroke-width="2.5" />
              <path id="beam-khavis" d="M500,22 C500,55 916,40 916,90" fill="none" stroke="url(#beamGrad)" stroke-width="3" class="flow-line-active" />
            </svg>

            <!-- 6 Clickable Graphical Agent Nodes -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <!-- Node 1: Claude Code -->
              <div id="node-card-claude" onclick="toggleAgentNode('claude')" class="agent-node-card cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="claude" class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <i class="fas fa-terminal"></i>
                  </div>
                  <span id="badge-node-claude" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">待命</span>
                </div>
                <div class="space-y-1">
                  <div class="font-bold text-white text-xs">Claude Code</div>
                  <div onclick="event.stopPropagation()">
                    <select id="model-select-claude" onchange="onAgentModelChange('claude', this.value)" class="w-full bg-[#070B14] border border-emerald-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-emerald-300 focus:outline-none focus:border-emerald-400 cursor-pointer" title="調整 Claude Code 綁定模型">
                      <option value="MiniMax-M3.1-Flash" selected>MiniMax-M3.1-Flash</option>
                      <option value="MiniMax-M3.1">MiniMax-M3.1</option>
                      <option value="glm-5.3-flashx">glm-5.3-flashx</option>
                      <option value="glm-5.3">glm-5.3</option>
                      <option value="claude-sonnet-5">claude-sonnet-5</option>
                      <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
                      <option value="__custom__">✏️ 自訂模型...</option>
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Tier-1 CLI</span>
                  <i class="fas fa-check-circle text-slate-600 check-indicator"></i>
                </div>
              </div>

              <!-- Node 2: OpenAI Codex -->
              <div id="node-card-codex" onclick="toggleAgentNode('codex')" class="agent-node-card cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="codex" class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                    <i class="fas fa-code"></i>
                  </div>
                  <span id="badge-node-codex" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">待命</span>
                </div>
                <div class="space-y-1">
                  <div class="font-bold text-white text-xs">OpenAI Codex</div>
                  <div onclick="event.stopPropagation()">
                    <select id="model-select-codex" onchange="onAgentModelChange('codex', this.value)" class="w-full bg-[#070B14] border border-indigo-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-indigo-300 focus:outline-none focus:border-indigo-400 cursor-pointer" title="調整 Codex 綁定模型">
                      <option value="glm-5.3-flashx" selected>glm-5.3-flashx</option>
                      <option value="glm-5.3">glm-5.3</option>
                      <option value="codegeex-4">codegeex-4</option>
                      <option value="MiniMax-M3.1-Flash">MiniMax-M3.1-Flash</option>
                      <option value="MiniMax-M3.1">MiniMax-M3.1</option>
                      <option value="gpt-5-mini">gpt-5-mini</option>
                      <option value="gpt-5-codex">gpt-5-codex</option>
                      <option value="__custom__">✏️ 自訂模型...</option>
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Tier-1 CLI</span>
                  <i class="fas fa-check-circle text-slate-600 check-indicator"></i>
                </div>
              </div>

              <!-- Node 3: Antigravity -->
              <div id="node-card-antigravity" onclick="toggleAgentNode('antigravity')" class="agent-node-card selected cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="antigravity" checked class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
                    <i class="fas fa-rocket"></i>
                  </div>
                  <span id="badge-node-antigravity" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300">已選取</span>
                </div>
                <div class="space-y-1">
                  <div class="font-bold text-white text-xs">Antigravity</div>
                  <div onclick="event.stopPropagation()">
                    <select id="model-select-antigravity" onchange="onAgentModelChange('antigravity', this.value)" class="w-full bg-[#070B14] border border-sky-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-sky-300 focus:outline-none focus:border-sky-400 cursor-pointer" title="調整 Antigravity 綁定模型">
                      <option value="antigravity-pro" selected>antigravity-pro</option>
                      <option value="antigravity-flash">antigravity-flash</option>
                      <option value="antigravity-ultra">antigravity-ultra</option>
                      <option value="MiniMax-M3.1-Flash">MiniMax-M3.1-Flash</option>
                      <option value="glm-5.3-flashx">glm-5.3-flashx</option>
                      <option value="__custom__">✏️ 自訂模型...</option>
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Tier-1 AGY</span>
                  <i class="fas fa-check-circle text-sky-400 check-indicator"></i>
                </div>
              </div>

              <!-- Node 4: MiniMax Code -->
              <div id="node-card-minimax" onclick="toggleAgentNode('minimax')" class="agent-node-card cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="minimax" class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
                    <i class="fas fa-microchip"></i>
                  </div>
                  <span id="badge-node-minimax" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">待命</span>
                </div>
                <div class="space-y-1">
                  <div class="font-bold text-white text-xs">MiniMax Code</div>
                  <div onclick="event.stopPropagation()">
                    <select id="model-select-minimax" onchange="onAgentModelChange('minimax', this.value)" class="w-full bg-[#070B14] border border-teal-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-teal-300 focus:outline-none focus:border-teal-400 cursor-pointer" title="調整 MiniMax Code 綁定模型">
                      <option value="MiniMax-M3.1" selected>MiniMax-M3.1</option>
                      <option value="MiniMax-M3.1-Flash">MiniMax-M3.1-Flash</option>
                      <option value="MiniMax-Text-01">MiniMax-Text-01</option>
                      <option value="__custom__">✏️ 自訂模型...</option>
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Tier-2 CLI</span>
                  <i class="fas fa-check-circle text-slate-600 check-indicator"></i>
                </div>
              </div>

              <!-- Node 5: Zhipu zcode -->
              <div id="node-card-zcode" onclick="toggleAgentNode('zcode')" class="agent-node-card cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="zcode" class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <i class="fas fa-bolt"></i>
                  </div>
                  <span id="badge-node-zcode" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">待命</span>
                </div>
                <div class="space-y-1">
                  <div class="font-bold text-white text-xs">Zhipu zcode</div>
                  <div onclick="event.stopPropagation()">
                    <select id="model-select-zcode" onchange="onAgentModelChange('zcode', this.value)" class="w-full bg-[#070B14] border border-amber-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-amber-300 focus:outline-none focus:border-amber-400 cursor-pointer" title="調整 zcode 綁定模型">
                      <option value="glm-5.3-flashx" selected>glm-5.3-flashx</option>
                      <option value="glm-5.3">glm-5.3</option>
                      <option value="codegeex-4">codegeex-4</option>
                      <option value="glm-4-plus">glm-4-plus</option>
                      <option value="__custom__">✏️ 自訂模型...</option>
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Tier-2 CLI</span>
                  <i class="fas fa-check-circle text-slate-600 check-indicator"></i>
                </div>
              </div>

              <!-- Node 6: K.H.A.V.I.S. 7-Role Team -->
              <div id="node-card-khavis" onclick="toggleAgentNode('khavis')" class="agent-node-card selected cursor-pointer rounded-xl p-3 bg-[#0E1525] border border-white/10 flex flex-col justify-between space-y-2.5 select-none">
                <input type="checkbox" name="agent_target" value="khavis" checked class="hidden" onchange="syncTopologyBeams()">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <i class="fas fa-network-wired"></i>
                  </div>
                  <span id="badge-node-khavis" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300">已選取</span>
                </div>
                <div>
                  <div class="font-bold text-white text-xs">K.H.A.V.I.S.</div>
                  <div class="text-[10px] text-cyan-400 font-mono truncate mt-0.5">LangGraph 7-Role</div>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                  <span>Master DAG</span>
                  <i class="fas fa-check-circle text-sky-400 check-indicator"></i>
                </div>
              </div>
            </div>

            <!-- Dynamic User-Defined Custom Agent Nodes Grid -->
            <div id="custom-agents-topology-grid" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-3 hidden">
              <!-- Populated dynamically via JS when custom agents are registered -->
            </div>
          </div>

          <!-- Task Prompt Input & Graphical Action Bar -->
          <div class="space-y-3 pt-1">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <i class="fas fa-magic text-sky-400"></i>
                <span>點擊載入圖形化任務範本：</span>
              </span>
              <div class="flex items-center gap-2 overflow-x-auto text-xs">
                <button onclick="setPromptTemplate('architecture')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-sky-500/20 hover:text-sky-300 border border-white/5 text-slate-300 transition">🏛️ 系統架構設計</button>
                <button onclick="setPromptTemplate('code_refactor')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-sky-500/20 hover:text-sky-300 border border-white/5 text-slate-300 transition">⚡ 代碼重構與優化</button>
                <button onclick="setPromptTemplate('unit_test')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-sky-500/20 hover:text-sky-300 border border-white/5 text-slate-300 transition">🧪 單元測試覆蓋</button>
                <button onclick="setPromptTemplate('debate_review')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-sky-500/20 hover:text-sky-300 border border-white/5 text-slate-300 transition">🔍 多 Agent 交叉審查</button>
              </div>
            </div>

            <div class="relative">
              <textarea id="prompt-input" rows="3" placeholder="在此輸入您的任務指示，上方選取的圖形節點將並發執行並匯流產出共識..." class="w-full bg-[#050811]/90 border border-white/10 rounded-xl p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 font-sans resize-y"></textarea>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-2 text-xs text-slate-400">
                <span>能力路由偏好:</span>
                <select id="capability-hint" class="bg-[#0B1120] border border-white/10 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500">
                  <option value="">🎯 能力自動識別 (Auto Capability)</option>
                  <option value="程式碼">💻 程式碼生成與重構 (Code)</option>
                  <option value="推理">🧠 深度架構推理 (Reasoning)</option>
                  <option value="中文">🇨🇳 中文語境優化 (Chinese)</option>
                  <option value="長文">📜 超長上下文分析 (LongContext)</option>
                </select>
              </div>

              <button id="btn-dispatch" onclick="submitDispatch()" class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 via-cyan-500 to-teal-500 hover:from-sky-400 hover:to-teal-400 text-white font-bold text-sm shadow-lg shadow-sky-500/25 flex items-center gap-2 transition transform active:scale-95">
                <i class="fas fa-play"></i>
                <span>啟動圖形化並發派工</span>
              </button>
            </div>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- GRAPHICAL 7-ROLE LANGGRAPH DAG & LIVE EXECUTION FEED            -->
        <!-- =============================================================== -->
        <div id="execution-panel" class="glass-panel p-5 rounded-2xl border border-white/10 space-y-5">
          <div class="flex items-center justify-between border-b border-white/10 pb-3">
            <div class="flex items-center gap-3">
              <div id="exec-spinner" class="hidden w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin"></div>
              <i class="fas fa-project-diagram text-sky-400"></i>
              <span id="exec-status-text" class="font-bold text-white text-sm">LangGraph 7 角色協同有向圖 (DAG Pipeline) · 待命就緒</span>
            </div>
            <span id="exec-timer" class="font-mono text-xs px-2.5 py-1 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">0.0s</span>
          </div>

          <!-- Graphical 7-Stage DAG Visualizer -->
          <div id="pipeline-stepper" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 text-center text-xs font-mono">
            <div class="step-planner p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-compass text-base text-sky-400"></i>
              <span class="font-bold">1. Planner</span>
              <span class="text-[10px] text-slate-400">任務拆解</span>
            </div>
            <div class="step-coder_a p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-code text-base text-emerald-400"></i>
              <span class="font-bold">2. Coder A</span>
              <span class="text-[10px] text-slate-400">Clean Code ∥</span>
            </div>
            <div class="step-coder_b p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-shield-alt text-base text-indigo-400"></i>
              <span class="font-bold">3. Coder B</span>
              <span class="text-[10px] text-slate-400">Defensive ∥</span>
            </div>
            <div class="step-debater p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-comments text-base text-amber-400"></i>
              <span class="font-bold">4. Debater</span>
              <span class="text-[10px] text-slate-400">A/B 交叉辯論</span>
            </div>
            <div class="step-critic p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-search-plus text-base text-rose-400"></i>
              <span class="font-bold">5. Critic</span>
              <span class="text-[10px] text-slate-400">邊界與安全審查</span>
            </div>
            <div class="step-verifier p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-vial text-base text-teal-400"></i>
              <span class="font-bold">6. Verifier</span>
              <span class="text-[10px] text-slate-400">驗證與重試迴圈</span>
            </div>
            <div class="step-learner p-3 rounded-xl bg-white/5 text-slate-300 border border-white/10 flex flex-col items-center gap-1.5">
              <i class="fas fa-brain text-base text-purple-400"></i>
              <span class="font-bold">7. Learner</span>
              <span class="text-[10px] text-slate-400">記憶庫沉澱</span>
            </div>
          </div>

          <!-- Visual Latency Comparison Chart (Populated on Dispatch Completion) -->
          <div id="latency-chart-box" class="hidden p-4 rounded-xl bg-[#050811]/70 border border-white/10 space-y-2.5">
            <div class="text-xs font-bold text-slate-300 flex items-center gap-2">
              <i class="fas fa-chart-bar text-sky-400"></i>
              <span>各 Agent 響應延遲與執行效能視覺化對比</span>
            </div>
            <div id="latency-bars-container" class="space-y-2 text-xs font-mono"></div>
          </div>

          <!-- Live Output Stream Container -->
          <div id="live-results-container" class="space-y-3">
            <!-- Results cards injected here -->
          </div>
        </div>

        <!-- Recent Dispatches List -->
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-slate-200 flex items-center gap-2">
              <i class="fas fa-history text-sky-400"></i>
              <span>最近任務派工與流水線執行紀錄</span>
            </h3>
            <button onclick="loadDashboardHistory()" class="text-xs text-sky-400 hover:underline">重新整理</button>
          </div>
          <div id="history-container" class="space-y-2 text-xs">
            <div class="text-slate-500 py-3 text-center">載入歷史紀錄中...</div>
          </div>
        </div>

      </section>

      <!-- ================================================================= -->
      <!-- VIEW 2: 交付文件庫 (Deliverables & Artifacts Explorer) -->
      <!-- ================================================================= -->
      <section id="view-artifacts" class="tab-content hidden space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold text-white">交付文件與產物資料庫</h2>
            <p class="text-xs text-slate-400">檢視、預覽並複製所有由 Agent 與系統生成的交付成果、技術簡報與代碼檔案（受白名單安全保護）</p>
          </div>
          <button onclick="loadArtifactsList()" class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-300 transition flex items-center gap-1.5">
            <i class="fas fa-sync-alt"></i> 重新整理
          </button>
        </div>

        <div id="artifacts-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Injected via JS -->
        </div>
      </section>

      <!-- ================================================================= -->
      <!-- VIEW 3: 視覺化額度與熔斷中心 (Graphical Quota & Circuit Breaker) -->
      <!-- ================================================================= -->
      <section id="view-quotas" class="tab-content hidden space-y-6">
        <div>
          <h2 class="text-xl font-bold text-white">4 大 LLM 付費方案環形水位錶與防線監控</h2>
          <p class="text-xs text-slate-400">主動攔截 HTTP 速率限制標頭、SVG 圓環配額水位錶、動態 Reset 倒數與自動切換本地 Ollama 防禦</p>
        </div>

        <div id="quota-cards-grid" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Injected via JS -->
        </div>

        <!-- Alert Log Panel -->
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <h3 class="font-bold text-sm text-slate-200 flex items-center gap-2">
            <i class="fas fa-bell text-amber-400"></i>
            <span>最新 Webhook 警報事件日誌</span>
          </h3>
          <div id="alerts-log-container" class="space-y-2 text-xs font-mono">
            <div class="text-slate-500 py-2 text-center">監控正常，尚無未處理之異常告警。</div>
          </div>
        </div>
      </section>

      <!-- ================================================================= -->
      <!-- VIEW 4: 雲端主機 Agent 集群狀態 (Tencent Cloud Fleet) -->
      <!-- ================================================================= -->
      <section id="view-agents" class="tab-content hidden space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold text-white">雲端主機主機 Agent 集群與用戶自訂 Agent 拓撲</h2>
            <p class="text-xs text-slate-400">包含 Claude Code (MiniMax-M3.1-Flash), Codex, Antigravity (AGY), MiniMax Code, zcode, K.H.A.V.I.S. 團隊以及您自訂掛載的 Agent</p>
          </div>
          <button type="button" onclick="switchTab('command'); document.getElementById('custom-agent-panel').classList.remove('hidden');" class="px-3.5 py-2 rounded-xl bg-pink-500/20 hover:bg-pink-500/30 text-pink-300 border border-pink-500/30 text-xs font-bold transition">
            <i class="fas fa-plug mr-1"></i>➕ 新增自訂 Agent
          </button>
        </div>

        <div id="agents-fleet-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Injected via JS -->
        </div>
      </section>

      <!-- ================================================================= -->
      <!-- VIEW 5: 開源 / 團隊快速部署與 BYOK 精靈 (Quick Setup Wizard)      -->
      <!-- ================================================================= -->
      <section id="view-wizard" class="tab-content hidden space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold text-white">🚀 開源 / 團隊快速部署與 BYOK 設定精靈</h2>
            <p class="text-xs text-slate-400">三步驟完成「頂級 CLI 外殼 + 高性價比 MiniMax / GLM 模型熱插拔 + 多 CLI 共用專案資料夾」一鍵部署</p>
          </div>
          <button type="button" onclick="loadSetupWizard()" class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-300 transition">
            <i class="fas fa-sync-alt mr-1"></i>重新檢測狀態
          </button>
        </div>

        <!-- Step 1: BYOK Credentials Health & Live Configuration -->
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold">STEP 1</span>
              <h3 class="font-bold text-white text-sm sm:text-base">BYOK 訂閱方案 API 金鑰健檢與線上熱更新</h3>
              <span id="wizard-save-toast" class="text-xs font-mono text-emerald-400 hidden"></span>
            </div>
            <button type="button" onclick="saveWizardKeys()" class="px-4 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition">
              <i class="fas fa-save mr-1"></i>儲存金鑰更新至 .env
            </button>
          </div>
          <div id="wizard-providers-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            <!-- Populated via JS -->
          </div>
        </div>

        <!-- Step 2 & Step 3: One-Click Commands & .env Template -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
            <div class="flex items-center gap-2 border-b border-white/10 pb-2.5">
              <span class="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono text-xs font-bold">STEP 2</span>
              <h3 class="font-bold text-white text-sm">新主機 / 團隊成員一鍵部署腳本</h3>
            </div>
            <p class="text-xs text-slate-400">在任何 Ubuntu / macOS 伺服器或開發機上執行以下指令，即可自動初始化共用專案資料夾、5 大 CLI 轉接器與預設模型綁定：</p>
            <div class="space-y-2.5 font-mono text-xs">
              <div class="p-3 rounded-xl bg-[#050811] border border-white/10 space-y-1">
                <div class="text-[10px] text-sky-400">1. 執行快速部署與共用目錄初始化精靈：</div>
                <div class="text-emerald-300 select-all">bash scripts/quick_setup_wizard.sh</div>
              </div>
              <div class="p-3 rounded-xl bg-[#050811] border border-white/10 space-y-1">
                <div class="text-[10px] text-sky-400">2. 安裝/更新 5 大 CLI 轉接執行檔 (Claude/Codex/AGY/MiniMax/zcode)：</div>
                <div class="text-emerald-300 select-all">sudo bash scripts/setup_tencent_agents.sh</div>
              </div>
              <div class="p-3 rounded-xl bg-[#050811] border border-white/10 space-y-1">
                <div class="text-[10px] text-sky-400">3. Docker Compose 全服務一鍵啟動：</div>
                <div class="text-emerald-300 select-all">docker compose -f deploy/docker-compose.all-in-one.yml up -d --build</div>
              </div>
            </div>
          </div>

          <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
            <div class="flex items-center justify-between border-b border-white/10 pb-2.5">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono text-xs font-bold">STEP 3</span>
                <h3 class="font-bold text-white text-sm">產生團隊專用 `.env` 設定範本</h3>
              </div>
              <button type="button" onclick="copyWizardEnvTemplate()" class="px-2.5 py-1 rounded bg-white/5 hover:bg-sky-500/20 text-sky-300 text-xs font-mono">
                <i class="fas fa-copy mr-1"></i>複製 .env 範本
              </button>
            </div>
            <pre id="wizard-env-template" class="p-3 rounded-xl bg-[#050811] border border-white/10 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-56">載入範本中...</pre>
          </div>
        </div>
      </section>

    </main>
  </div>

  <!-- Slide-out Drawer for Artifact Viewer -->
  <div id="artifact-drawer" class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-[#0F1626] border-l border-white/10 shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col">
    <div class="p-4 border-b border-white/10 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <i id="drawer-icon" class="fas fa-file text-sky-400"></i>
        <h3 id="drawer-title" class="font-bold text-white text-sm truncate max-w-md">檔案預覽</h3>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="copyDrawerContent()" class="p-2 text-slate-400 hover:text-white transition text-xs" title="複製內容">
          <i class="fas fa-copy"></i>
        </button>
        <button onclick="closeDrawer()" class="p-2 text-slate-400 hover:text-white transition text-sm">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>
    <div class="p-4 flex-1 overflow-y-auto font-mono text-xs text-slate-300 bg-[#070B14]" id="drawer-content">
      載入中...
    </div>
    <div class="p-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
      <span id="drawer-meta">--</span>
      <span class="text-emerald-400">唯讀安全白名單預覽模式</span>
    </div>
  </div>

  <!-- JavaScript Frontend Logic -->
  <script>
    let currentTab = 'command';
    let execTimerInterval = null;
    let execStartTime = 0;

    let AGENT_IDS = ['claude', 'codex', 'antigravity', 'minimax', 'zcode', 'khavis'];
    let ADJUSTABLE_AGENTS = ['claude', 'codex', 'antigravity', 'minimax', 'zcode'];
    let currentAgentModels = {
      claude: 'MiniMax-M3.1-Flash',
      codex: 'glm-5.3-flashx',
      antigravity: 'antigravity-pro',
      minimax: 'MiniMax-M3.1',
      zcode: 'glm-5.3-flashx'
    };
    let currentIsolationMode = 'shared';
    let currentProjectName = 'shared-app';
    let latestWorkspaceData = null;

    function toggleModelSettingsPanel() {
      const panel = document.getElementById('model-settings-panel');
      if (panel) panel.classList.toggle('hidden');
    }

    function toggleCustomAgentPanel() {
      const panel = document.getElementById('custom-agent-panel');
      if (panel) panel.classList.toggle('hidden');
    }

    function toggleWorkspaceDiffPanel() {
      const panel = document.getElementById('workspace-diff-panel');
      if (panel) {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) loadWorkspaceStatus();
      }
    }

    function formatColorizedDiff(rawDiff) {
      if (!rawDiff || !rawDiff.trim()) {
        return '<span class="text-slate-500">目前工作區乾淨，無未提交之 Diff 差異。</span>';
      }
      return rawDiff.split('\n').map(line => {
        const esc = escapeHtml(line);
        if (line.startsWith('+++') || line.startsWith('---')) {
          return `<div class="text-sky-300 font-bold">${esc}</div>`;
        } else if (line.startsWith('@@')) {
          return `<div class="text-cyan-400 bg-cyan-950/30 px-1">${esc}</div>`;
        } else if (line.startsWith('+')) {
          return `<div class="text-emerald-300 bg-emerald-950/30 px-1">${esc}</div>`;
        } else if (line.startsWith('-')) {
          return `<div class="text-rose-300 bg-rose-950/30 px-1">${esc}</div>`;
        }
        return `<div class="text-slate-300">${esc}</div>`;
      }).join('');
    }

    function syncIsolationModeUI(mode) {
      currentIsolationMode = mode === 'worktree' ? 'worktree' : 'shared';
      const btnShared = document.getElementById('btn-mode-shared');
      const btnWt = document.getElementById('btn-mode-worktree');
      const badge = document.getElementById('ws-mode-badge');
      if (currentIsolationMode === 'shared') {
        if (btnShared) btnShared.className = 'px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 transition';
        if (btnWt) btnWt.className = 'px-2.5 py-1 rounded-md text-xs font-medium text-slate-400 hover:text-white transition';
        if (badge) {
          badge.textContent = '🤝 共用同一個專案資料夾 (流暢接力讀寫)';
          badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
        }
      } else {
        if (btnWt) btnWt.className = 'px-2.5 py-1 rounded-md text-xs font-medium bg-amber-500/25 text-amber-300 border border-amber-500/40 transition';
        if (btnShared) btnShared.className = 'px-2.5 py-1 rounded-md text-xs font-medium text-slate-400 hover:text-white transition';
        if (badge) {
          badge.textContent = '🌿 Git Worktree 分支隔離 (並發防衝突 + Diff 對比)';
          badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30';
        }
      }
    }

    async function setIsolationMode(mode) {
      syncIsolationModeUI(mode);
      try {
        const res = await fetch('/api/workbench/workspace', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'configure', isolation_mode: currentIsolationMode, project: currentProjectName })
        });
        if (res.ok) {
          const data = await res.json();
          renderWorkspaceState(data);
        }
      } catch (_) {}
    }

    async function switchSharedProject(projName) {
      if (!projName) return;
      currentProjectName = projName;
      try {
        const res = await fetch('/api/workbench/workspace', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'configure', project: projName, isolation_mode: currentIsolationMode })
        });
        if (res.ok) {
          const data = await res.json();
          renderWorkspaceState(data);
        }
      } catch (_) {}
    }

    async function promptNewProjectFolder() {
      const name = prompt('請輸入新共用專案資料夾名稱 (英數字、連字號或底線，例如 my-webapp):', 'my-project');
      if (!name || !name.trim()) return;
      await switchSharedProject(name.trim());
    }

    async function commitSharedWorkspace() {
      const msg = prompt('請輸入共用專案資料夾 Git Commit 快照訊息 (留空使用預設時間戳):', 'snapshot: update shared project files');
      if (msg === null) return;
      try {
        const res = await fetch('/api/workbench/workspace', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'commit', message: msg, project: currentProjectName })
        });
        const data = await res.json();
        if (res.ok) {
          renderWorkspaceState(data);
          alert('✅ 已為共用專案資料夾建立 Git Commit 基準快照！');
        }
      } catch (err) {
        alert('Commit 失敗: ' + err.message);
      }
    }

    async function mergeAgentWorktree(agentId) {
      try {
        const res = await fetch('/api/workbench/workspace', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'merge', agent: agentId, project: currentProjectName })
        });
        const data = await res.json();
        if (res.ok) {
          renderWorkspaceState(data);
          alert(`✅ 已將 Agent [${agentId}] 分支的變更 (${(data.merged_files || []).length} 個檔案) 合併回共用專案資料夾！`);
        } else {
          alert(`合併失敗: ${data.detail || '未知錯誤'}`);
        }
      } catch (err) {
        alert(`合併連線錯誤: ${err.message}`);
      }
    }

    function selectDiffTab(tabKey) {
      if (!latestWorkspaceData) return;
      const viewer = document.getElementById('ws-diff-viewer');
      const mergeBox = document.getElementById('ws-merge-action');
      if (!viewer) return;

      if (tabKey === 'shared') {
        viewer.innerHTML = formatColorizedDiff(latestWorkspaceData.diff || '');
        if (mergeBox) mergeBox.classList.add('hidden');
      } else {
        const wt = (latestWorkspaceData.worktrees || []).find(w => w.agent === tabKey);
        viewer.innerHTML = formatColorizedDiff(wt ? wt.diff : '');
        if (mergeBox && wt && wt.has_changes) {
          mergeBox.classList.remove('hidden');
          mergeBox.innerHTML = `
            <button type="button" onclick="mergeAgentWorktree('${escapeHtml(wt.agent)}')" class="px-2.5 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] transition">
              <i class="fas fa-code-merge mr-1"></i>✅ 一鍵合併 ${escapeHtml(wt.agent)} 變更至共用資料夾
            </button>
          `;
        } else if (mergeBox) {
          mergeBox.classList.add('hidden');
        }
      }
    }

    function renderWorkspaceState(data) {
      if (!data) return;
      latestWorkspaceData = data;
      if (data.active_project) currentProjectName = data.active_project;
      if (data.isolation_mode) syncIsolationModeUI(data.isolation_mode);

      const pathEl = document.getElementById('ws-active-path');
      if (pathEl) pathEl.textContent = `共用目錄: ${data.active_path || '--'} (Git 分支: ${data.branch || 'main'})`;

      const sel = document.getElementById('ws-project-select');
      if (sel && Array.isArray(data.projects)) {
        sel.innerHTML = data.projects.map(p =>
          `<option value="${escapeHtml(p)}" ${p === data.active_project ? 'selected' : ''}>${escapeHtml(p)}</option>`
        ).join('');
      }

      const files = data.files || [];
      const countEl = document.getElementById('ws-file-count');
      if (countEl) countEl.textContent = files.length;

      const filesList = document.getElementById('ws-files-list');
      if (filesList) {
        if (files.length === 0) {
          filesList.innerHTML = '<div class="text-slate-500 py-2 text-center">尚無專案檔案</div>';
        } else {
          filesList.innerHTML = files.map(f => `
            <div class="flex items-center justify-between p-1.5 rounded bg-white/5 hover:bg-sky-500/15 transition">
              <button type="button" onclick="openArtifact('${escapeHtml(f.path)}', '${escapeHtml(f.rel_path)}')" class="text-left text-sky-300 hover:underline truncate max-w-[180px]" title="${escapeHtml(f.rel_path)}">
                <i class="fas fa-file-code mr-1 text-slate-400"></i>${escapeHtml(f.rel_path)}
              </button>
              <span class="text-[10px] text-slate-400">${escapeHtml(f.size)}</span>
            </div>
          `).join('');
        }
      }

      const tabsEl = document.getElementById('ws-diff-tabs');
      if (tabsEl) {
        const wts = data.worktrees || [];
        let tabsHtml = `
          <button type="button" onclick="selectDiffTab('shared')" class="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-mono text-[11px]">
            📂 共用資料夾 Diff (${(data.changed_files || []).length})
          </button>
        `;
        wts.forEach(w => {
          tabsHtml += `
            <button type="button" onclick="selectDiffTab('${escapeHtml(w.agent)}')" class="px-2 py-0.5 rounded bg-white/5 hover:bg-amber-500/20 text-amber-300 border border-white/10 font-mono text-[11px]">
              🌿 ${escapeHtml(w.agent)} 分支 (${(w.changed_files || []).length})
            </button>
          `;
        });
        tabsEl.innerHTML = tabsHtml;
      }

      selectDiffTab('shared');
    }

    async function loadWorkspaceStatus() {
      try {
        const res = await fetch('/api/workbench/workspace');
        if (!res.ok) return;
        const data = await res.json();
        renderWorkspaceState(data);
      } catch (_) {}
    }

    function fillCustomAgentPreset(preset) {
      const idEl = document.getElementById('ca-id');
      const nameEl = document.getElementById('ca-name');
      const typeEl = document.getElementById('ca-type');
      const modelEl = document.getElementById('ca-model');
      const binEl = document.getElementById('ca-binary');
      const argsEl = document.getElementById('ca-args');
      const keyEl = document.getElementById('ca-key-env');
      const urlEl = document.getElementById('ca-base-url');
      if (preset === 'aider') {
        idEl.value = 'aider';
        nameEl.value = 'Aider CLI';
        typeEl.value = 'cli';
        modelEl.value = 'MiniMax-M3.1-Flash';
        binEl.value = 'aider';
        argsEl.value = '--model {model} --yes-always --message {prompt}';
        keyEl.value = 'MINIMAX_API_KEY';
        urlEl.value = '';
      } else if (preset === 'opencode') {
        idEl.value = 'opencode';
        nameEl.value = 'OpenCode CLI';
        typeEl.value = 'cli';
        modelEl.value = 'glm-5.3-flashx';
        binEl.value = 'opencode';
        argsEl.value = 'run --model {model} -- {prompt}';
        keyEl.value = 'ZHIPUAI_API_KEY';
        urlEl.value = '';
      } else if (preset === 'goose') {
        idEl.value = 'goose';
        nameEl.value = 'Block Goose';
        typeEl.value = 'cli';
        modelEl.value = 'MiniMax-M3.1-Flash';
        binEl.value = 'goose';
        argsEl.value = 'session --text {prompt}';
        keyEl.value = 'MINIMAX_API_KEY';
        urlEl.value = '';
      } else if (preset === 'deepseek') {
        idEl.value = 'deepseek-coder';
        nameEl.value = 'DeepSeek / Qwen Agent';
        typeEl.value = 'http';
        modelEl.value = 'glm-5.3-flashx';
        binEl.value = 'openai-http';
        argsEl.value = '--model {model} -- {prompt}';
        keyEl.value = 'ZHIPUAI_API_KEY';
        urlEl.value = 'https://open.bigmodel.cn/api/coding/paas/v4';
      }
    }

    async function submitCustomAgent() {
      const payload = {
        id: document.getElementById('ca-id').value.trim(),
        name: document.getElementById('ca-name').value.trim(),
        type: document.getElementById('ca-type').value,
        model: document.getElementById('ca-model').value.trim(),
        binary: document.getElementById('ca-binary').value.trim(),
        args_template: document.getElementById('ca-args').value.trim(),
        api_key_env: document.getElementById('ca-key-env').value.trim(),
        base_url: document.getElementById('ca-base-url').value.trim()
      };
      if (!payload.id) {
        alert('請填寫 Agent 代號 (ID)！');
        return;
      }
      try {
        const res = await fetch('/api/workbench/agents/custom', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          await refreshCustomAgentsTopology();
          if (currentTab === 'agents') loadAgentsFleet();
          alert(`✅ 已成功掛載自訂 Agent: ${payload.name || payload.id}！`);
        } else {
          alert(`註冊失敗: ${data.detail || '未知錯誤'}`);
        }
      } catch (err) {
        alert(`註冊連線失敗: ${err.message}`);
      }
    }

    async function deleteCustomAgent(agentId, ev) {
      if (ev) ev.stopPropagation();
      try {
        const res = await fetch('/api/workbench/agents/custom', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'delete', id: agentId })
        });
        if (res.ok) {
          await refreshCustomAgentsTopology();
          if (currentTab === 'agents') loadAgentsFleet();
        }
      } catch (_) {}
    }

    async function refreshCustomAgentsTopology() {
      try {
        const res = await fetch('/api/workbench/agents');
        if (!res.ok) return;
        const data = await res.json();
        const allAgents = data.agents || [];
        const customAgents = allAgents.filter(a => a.custom);

        AGENT_IDS = ['claude', 'codex', 'antigravity', 'minimax', 'zcode', 'khavis', ...customAgents.map(a => a.id)];
        ADJUSTABLE_AGENTS = ['claude', 'codex', 'antigravity', 'minimax', 'zcode', ...customAgents.map(a => a.id)];
        customAgents.forEach(a => {
          if (!currentAgentModels[a.id]) currentAgentModels[a.id] = a.model;
        });

        const grid = document.getElementById('custom-agents-topology-grid');
        if (!grid) return;
        if (customAgents.length === 0) {
          grid.classList.add('hidden');
          grid.innerHTML = '';
          return;
        }
        grid.classList.remove('hidden');
        grid.innerHTML = customAgents.map(a => {
          const opts = (a.options || [a.model]).map(o =>
            `<option value="${escapeHtml(o)}" ${o === currentAgentModels[a.id] ? 'selected' : ''}>${escapeHtml(o)}</option>`
          ).join('');
          return `
            <div id="node-card-${escapeHtml(a.id)}" onclick="toggleAgentNode('${escapeHtml(a.id)}')" class="agent-node-card selected cursor-pointer rounded-xl p-3 bg-[#140E26] border border-pink-500/30 flex flex-col justify-between space-y-2.5 select-none">
              <input type="checkbox" name="agent_target" value="${escapeHtml(a.id)}" checked class="hidden" onchange="syncTopologyBeams()">
              <div class="flex items-center justify-between">
                <div class="w-8 h-8 rounded-lg bg-pink-500/20 border border-pink-500/30 flex items-center justify-center text-pink-400">
                  <i class="fas ${escapeHtml(a.icon || 'fa-plug')}"></i>
                </div>
                <div class="flex items-center gap-1">
                  <span id="badge-node-${escapeHtml(a.id)}" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300">已選取</span>
                  <button type="button" onclick="deleteCustomAgent('${escapeHtml(a.id)}', event)" class="text-slate-500 hover:text-rose-400 px-1 text-[10px]" title="移除此自訂 Agent">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </div>
              <div class="space-y-1">
                <div class="font-bold text-white text-xs truncate">${escapeHtml(a.name)}</div>
                <div onclick="event.stopPropagation()">
                  <select id="model-select-${escapeHtml(a.id)}" onchange="onAgentModelChange('${escapeHtml(a.id)}', this.value)" class="w-full bg-[#070B14] border border-pink-500/30 rounded px-1.5 py-1 text-[10px] font-mono text-pink-300 focus:outline-none">
                    ${opts}
                  </select>
                </div>
              </div>
              <div class="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/5">
                <span>Custom (${escapeHtml(a.type.toUpperCase())})</span>
                <i class="fas fa-check-circle text-sky-400 check-indicator"></i>
              </div>
            </div>
          `;
        }).join('');
        syncTopologyBeams(false);
      } catch (_) {}
    }

    async function loadSetupWizard() {
      const grid = document.getElementById('wizard-providers-grid');
      const tpl = document.getElementById('wizard-env-template');
      try {
        const res = await fetch('/api/workbench/setup');
        if (!res.ok) return;
        const data = await res.json();
        if (grid && Array.isArray(data.providers)) {
          grid.innerHTML = data.providers.map(p => `
            <div class="p-3.5 rounded-xl bg-black/40 border ${p.configured ? 'border-emerald-500/30' : 'border-amber-500/30'} space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-bold text-white">${escapeHtml(p.label)}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono ${p.configured ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}">
                  ${p.configured ? '✅ 已配置' : '⚠️ 未設定'}
                </span>
              </div>
              <div class="text-[11px] text-slate-400 font-mono">${escapeHtml(p.agents)}</div>
              <input type="password" data-wizard-env="${escapeHtml(p.env)}" placeholder="${escapeHtml(p.masked)}" class="w-full bg-[#050811] border border-white/15 rounded px-2.5 py-1.5 font-mono text-xs text-emerald-300 placeholder-slate-500 focus:outline-none focus:border-sky-400" />
            </div>
          `).join('');
        }
        if (tpl && data.env_template) {
          tpl.textContent = data.env_template;
        }
      } catch (_) {}
    }

    async function saveWizardKeys() {
      const inputs = document.querySelectorAll('input[data-wizard-env]');
      const keys = {};
      inputs.forEach(inp => {
        const k = inp.getAttribute('data-wizard-env');
        const v = inp.value.trim();
        if (k && v) keys[k] = v;
      });
      try {
        const res = await fetch('/api/workbench/setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keys })
        });
        if (res.ok) {
          const toast = document.getElementById('wizard-save-toast');
          if (toast) {
            toast.textContent = '✅ 已更新 BYOK 金鑰並寫入 .env！';
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 3500);
          }
          await loadSetupWizard();
        }
      } catch (err) {
        alert('儲存失敗: ' + err.message);
      }
    }

    function copyWizardEnvTemplate() {
      const tpl = document.getElementById('wizard-env-template');
      if (!tpl) return;
      navigator.clipboard.writeText(tpl.textContent);
      alert('已複製 .env 設定範本至剪貼簿！');
    }

    function syncModelUIElements() {
      ADJUSTABLE_AGENTS.forEach(id => {
        const val = currentAgentModels[id] || '';
        const sel = document.getElementById(`model-select-${id}`);
        if (sel && val) {
          let exists = Array.from(sel.options).some(o => o.value === val);
          if (!exists) {
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = val;
            sel.insertBefore(opt, sel.firstChild);
          }
          sel.value = val;
        }
        const inp = document.getElementById(`custom-input-${id}`);
        if (inp && document.activeElement !== inp) {
          inp.value = val;
        }
        const sideEl = document.getElementById(`side-model-${id}`);
        if (sideEl) sideEl.textContent = val;
      });

      const ctClaude = document.getElementById('card-title-claude');
      if (ctClaude) ctClaude.textContent = currentAgentModels.claude;
      const ctCodex = document.getElementById('card-title-codex');
      if (ctCodex) ctCodex.textContent = currentAgentModels.codex;
      const ctAg = document.getElementById('card-title-antigravity');
      if (ctAg) ctAg.textContent = currentAgentModels.antigravity;

      const strip = document.getElementById('quota-capsule-strip');
      if (strip) {
        strip.innerHTML = `
          <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Claude: ${escapeHtml(currentAgentModels.claude)}</span>
          <span class="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Codex: ${escapeHtml(currentAgentModels.codex)}</span>
          <span class="px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">AGY: ${escapeHtml(currentAgentModels.antigravity)}</span>
          <span class="px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">MiniMax: ${escapeHtml(currentAgentModels.minimax)}</span>
        `;
      }
    }

    function onAgentModelChange(agentId, value) {
      if (value === '__custom__') {
        const panel = document.getElementById('model-settings-panel');
        if (panel) panel.classList.remove('hidden');
        const inp = document.getElementById(`custom-input-${agentId}`);
        if (inp) {
          inp.focus();
          inp.select();
        }
        syncModelUIElements();
        return;
      }
      currentAgentModels[agentId] = value;
      syncModelUIElements();
    }

    function onCustomModelInput(agentId, value) {
      const trimmed = (value || '').trim();
      if (!trimmed) return;
      currentAgentModels[agentId] = trimmed;
      syncModelUIElements();
    }

    async function loadModelSettings() {
      try {
        const res = await fetch('/api/workbench/models');
        if (!res.ok) return;
        const data = await res.json();
        if (data.models) {
          ADJUSTABLE_AGENTS.forEach(id => {
            if (data.models[id]) currentAgentModels[id] = data.models[id];
          });
          syncModelUIElements();
        }
      } catch (_) {}
    }

    async function saveAgentModels(reset = false) {
      const toast = document.getElementById('model-save-toast');
      try {
        const res = await fetch('/api/workbench/models', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(reset ? { reset: true } : { models: currentAgentModels })
        });
        const data = await res.json();
        if (res.ok && data.models) {
          ADJUSTABLE_AGENTS.forEach(id => {
            if (data.models[id]) currentAgentModels[id] = data.models[id];
          });
          syncModelUIElements();
          if (currentTab === 'agents') loadAgentsFleet();
          if (toast) {
            toast.textContent = reset ? '✅ 已還原系統預設模型！' : '✅ 已儲存並寫入伺服器預設 (.env)！';
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 3500);
          } else {
            alert(reset ? '已還原系統預設模型！' : '已儲存為系統預設模型！');
          }
        } else {
          alert(`儲存模型設定失敗: ${data.detail || '未知錯誤'}`);
        }
      } catch (err) {
        alert(`儲存模型設定連線失敗: ${err.message}`);
      }
    }

    function switchTab(tab) {
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('bg-sky-600/20', 'text-sky-400', 'border', 'border-sky-500/30');
        b.classList.add('text-slate-300');
      });
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));

      const activeBtn = document.getElementById(`nav-${tab}`);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-300');
        activeBtn.classList.add('bg-sky-600/20', 'text-sky-400', 'border', 'border-sky-500/30');
      }

      const activeContent = document.getElementById(`view-${tab}`);
      if (activeContent) {
        activeContent.classList.remove('hidden');
      }

      if (tab === 'artifacts') loadArtifactsList();
      if (tab === 'quotas') loadQuotasData();
      if (tab === 'agents') loadAgentsFleet();
      if (tab === 'wizard') loadSetupWizard();
      if (tab === 'command') loadWorkspaceStatus();
    }

    function toggleTheme() {
      const html = document.documentElement;
      const isDark = html.classList.toggle('dark');
      const icon = document.getElementById('theme-icon');
      if (isDark) {
        icon.className = 'fas fa-sun text-amber-400';
      } else {
        icon.className = 'fas fa-moon text-slate-600';
      }
    }

    // Graphical Node Selection & SVG Beam Sync
    function toggleAgentNode(agentId) {
      const card = document.getElementById(`node-card-${agentId}`);
      if (!card) return;
      const cb = card.querySelector('input[name="agent_target"]');
      if (!cb) return;
      cb.checked = !cb.checked;
      syncTopologyBeams();
    }

    function selectPresetAgents(preset) {
      AGENT_IDS.forEach(id => {
        const card = document.getElementById(`node-card-${id}`);
        if (!card) return;
        const cb = card.querySelector('input[name="agent_target"]');
        if (!cb) return;
        if (preset === 'all') {
          cb.checked = true;
        } else if (preset === 'code_trio') {
          cb.checked = ['claude', 'codex', 'antigravity'].includes(id);
        } else if (preset === 'khavis_only') {
          cb.checked = (id === 'khavis');
        }
      });
      syncTopologyBeams();
    }

    function syncTopologyBeams(runningMode = false) {
      AGENT_IDS.forEach(id => {
        const card = document.getElementById(`node-card-${id}`);
        const beam = document.getElementById(`beam-${id}`);
        const badge = document.getElementById(`badge-node-${id}`);
        if (!card) return;
        const cb = card.querySelector('input[name="agent_target"]');
        const checkIcon = card.querySelector('.check-indicator');
        const isChecked = cb ? cb.checked : false;

        card.classList.toggle('selected', isChecked && !runningMode);
        card.classList.toggle('running', isChecked && runningMode);

        if (badge) {
          if (isChecked && runningMode) {
            badge.textContent = '執行中';
            badge.className = 'text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 animate-pulse';
          } else if (isChecked) {
            badge.textContent = '已選取';
            badge.className = 'text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300';
          } else {
            badge.textContent = '待命';
            badge.className = 'text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400';
          }
        }

        if (checkIcon) {
          checkIcon.className = isChecked
            ? 'fas fa-check-circle text-sky-400 check-indicator'
            : 'fas fa-check-circle text-slate-600 check-indicator';
        }

        if (beam) {
          if (isChecked && runningMode) {
            beam.setAttribute('stroke', 'url(#beamGrad)');
            beam.setAttribute('stroke-width', '3.5');
            beam.setAttribute('class', 'flow-line-running');
          } else if (isChecked) {
            beam.setAttribute('stroke', 'url(#beamGrad)');
            beam.setAttribute('stroke-width', '3');
            beam.setAttribute('class', 'flow-line-active');
          } else {
            beam.setAttribute('stroke', '#1E293B');
            beam.setAttribute('stroke-width', '2');
            beam.setAttribute('class', '');
          }
        }
      });
    }

    function setPromptTemplate(type) {
      const input = document.getElementById('prompt-input');
      if (type === 'architecture') {
        input.value = "請為雲端主機部署環境設計一套支援高可用、多付費方案配額感知與本地 Ollama 兜底的系統架構，標明模組劃分與數據流向。";
      } else if (type === 'code_refactor') {
        input.value = "請檢視並重構現有的請求排程模組，提高並發吞吐量並確保在遇到 HTTP 429 時能以指數退避演算法安全避讓。";
      } else if (type === 'unit_test') {
        input.value = "請為多 Agent 分發調度器撰寫完整的端到端單元測試，模擬 Claude Code (MiniMax-M3.1-Flash)、Codex 與 Antigravity 的返回狀態與超時場景。";
      } else if (type === 'debate_review') {
        input.value = "請針對當前的模型池配額追蹤演算法，由兩個不同設計哲學的 Coder 生成實現，並由 Debater 與 Verifier 進行交叉辯證。";
      }
      input.focus();
    }

    const PIPELINE_STEPS = [
      'step-planner',
      'step-coder_a',
      'step-coder_b',
      'step-debater',
      'step-critic',
      'step-verifier',
      'step-learner'
    ];
    let stepperInterval = null;

    function setPipelineStepState(activeIndex, completedAll = false) {
      PIPELINE_STEPS.forEach((cls, idx) => {
        const el = document.querySelector(`#pipeline-stepper .${cls}`);
        if (!el) return;
        const base = `${cls} p-3 rounded-xl border transition flex flex-col items-center gap-1.5 `;
        if (completedAll || idx < activeIndex) {
          el.className = base + 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-lg shadow-emerald-500/10';
        } else if (idx === activeIndex) {
          el.className = base + 'bg-sky-500/25 text-sky-200 border-sky-400 animate-pulse shadow-lg shadow-sky-500/20';
        } else {
          el.className = base + 'bg-white/5 text-slate-300 border-white/10';
        }
      });
    }

    async function submitDispatch() {
      const prompt = document.getElementById('prompt-input').value.trim();
      if (!prompt) {
        alert("請輸入任務指示！");
        return;
      }

      const selectedAgents = Array.from(document.querySelectorAll('input[name="agent_target"]:checked')).map(c => c.value);
      if (selectedAgents.length === 0) {
        alert("請至少在上方拓撲圖點選一個執行的 Agent！");
        return;
      }

      const capability = document.getElementById('capability-hint').value;
      const btn = document.getElementById('btn-dispatch');
      const spinner = document.getElementById('exec-spinner');
      const resultsContainer = document.getElementById('live-results-container');
      const statusText = document.getElementById('exec-status-text');
      const chartBox = document.getElementById('latency-chart-box');
      const barsContainer = document.getElementById('latency-bars-container');

      if (spinner) spinner.classList.remove('hidden');
      if (chartBox) chartBox.classList.add('hidden');
      resultsContainer.innerHTML = '';
      btn.disabled = true;
      btn.classList.add('opacity-50');
      syncTopologyBeams(true);

      let currentStepIdx = 0;
      setPipelineStepState(0, false);
      if (stepperInterval) clearInterval(stepperInterval);
      stepperInterval = setInterval(() => {
        if (currentStepIdx < PIPELINE_STEPS.length - 1) {
          currentStepIdx++;
          setPipelineStepState(currentStepIdx, false);
        }
      }, 1100);

      execStartTime = performance.now();
      document.getElementById('exec-timer').textContent = '0.0s';
      if (execTimerInterval) clearInterval(execTimerInterval);
      execTimerInterval = setInterval(() => {
        const elapsed = ((performance.now() - execStartTime) / 1000).toFixed(1);
        document.getElementById('exec-timer').textContent = `${elapsed}s`;
      }, 100);

      statusText.textContent = `執行中：正在並發調度 [${selectedAgents.join(', ')}]...`;

      try {
        const resp = await fetch('/api/workbench/dispatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: prompt,
            agents: selectedAgents,
            capability: capability || null,
            agent_models: currentAgentModels,
            isolation_mode: currentIsolationMode,
            project: currentProjectName
          })
        });

        const data = await resp.json();
        clearInterval(execTimerInterval);
        clearInterval(stepperInterval);
        if (spinner) spinner.classList.add('hidden');
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        syncTopologyBeams(false);

        if (!resp.ok) {
          statusText.textContent = `執行失敗: ${data.detail || '未知錯誤'}`;
          return;
        }

        setPipelineStepState(PIPELINE_STEPS.length, true);
        statusText.textContent = `✅ 並發派工完成！共 ${data.results ? data.results.length : 1} 個 Agent 節點回傳 (最優共識: ${data.consensus_source || '自動合成'}) · 模式: ${data.isolation_mode === 'worktree' ? 'Git Worktree 隔離' : '共用專案資料夾'}`;

        if (data.results && data.results.length > 0) {
          // Render Graphical Latency Bar Chart
          if (chartBox && barsContainer) {
            const maxLat = Math.max(100, ...data.results.map(r => r.latency_ms || 50));
            barsContainer.innerHTML = data.results.map(r => {
              const pct = Math.max(6, Math.min(100, Math.round(((r.latency_ms || 50) / maxLat) * 100)));
              const barColor = r.ok ? 'from-sky-500 to-emerald-400' : 'from-amber-500 to-rose-400';
              return `
                <div class="grid grid-cols-12 items-center gap-2">
                  <div class="col-span-3 sm:col-span-2 text-slate-300 font-bold uppercase truncate">${escapeHtml(r.backend)}</div>
                  <div class="col-span-7 sm:col-span-8 bg-white/5 h-3 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r ${barColor} rounded-full transition-all duration-500" style="width: ${pct}%"></div>
                  </div>
                  <div class="col-span-2 text-right text-sky-400">${r.latency_ms || 0} ms</div>
                </div>
              `;
            }).join('');
            chartBox.classList.remove('hidden');
          }

          data.results.forEach(res => {
            const card = document.createElement('div');
            card.className = "p-4 rounded-xl bg-white/5 border border-white/10 space-y-2";
            const changedFiles = Array.isArray(res.changed_files) ? res.changed_files : [];
            const diffSection = (res.diff || changedFiles.length > 0) ? `
              <div class="mt-2 pt-2 border-t border-white/10 space-y-1.5">
                <div class="flex items-center justify-between text-[11px] font-mono">
                  <span class="text-teal-300"><i class="fas fa-code-commit mr-1"></i>檔案變更 (${changedFiles.length}): ${escapeHtml(changedFiles.map(f => f.path).join(', ') || '已更新')}</span>
                  ${data.isolation_mode === 'worktree' ? `
                    <button onclick="mergeWorktree('${escapeHtml(res.backend)}')" class="px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-bold">
                      <i class="fas fa-code-merge mr-1"></i>合併回共用資料夾
                    </button>
                  ` : ''}
                </div>
                ${res.diff ? `<div class="p-2 rounded bg-[#050811] border border-white/10 text-[11px] font-mono max-h-40 overflow-y-auto">${formatColorizedDiff(res.diff)}</div>` : ''}
              </div>
            ` : '';
            card.innerHTML = `
              <div class="flex items-center justify-between border-b border-white/10 pb-2">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="px-2 py-0.5 rounded text-[11px] font-mono font-bold ${res.ok ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-300'}">
                    ${res.ok ? 'SUCCESS' : 'STANDBY / NOTICE'}
                  </span>
                  <strong class="text-white text-sm uppercase">${escapeHtml(res.backend)}</strong>
                  <span class="text-xs text-slate-400">(${escapeHtml(res.model || 'Default Model')})</span>
                  ${res.cwd ? `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-500/15 text-teal-300 border border-teal-500/30"><i class="fas fa-folder-open mr-1"></i>${escapeHtml(res.cwd)}</span>` : ''}
                </div>
                <div class="text-xs font-mono text-slate-400">
                  <i class="fas fa-clock mr-1"></i>${res.latency_ms || 0}ms
                </div>
              </div>
              <div class="text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto p-2 bg-[#050811]/70 rounded-lg">${escapeHtml(res.text || res.error || '無返回內容')}</div>
              ${diffSection}
            `;
            resultsContainer.appendChild(card);
          });
        }

        loadWorkspaceStatus();
        loadDashboardHistory();
        loadArtifactsList();
      } catch (err) {
        clearInterval(execTimerInterval);
        clearInterval(stepperInterval);
        if (spinner) spinner.classList.add('hidden');
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        syncTopologyBeams(false);
        statusText.textContent = `網路或伺服器通訊錯誤: ${err.message}`;
      }
    }

    async function loadArtifactsList() {
      const grid = document.getElementById('artifacts-grid');
      grid.innerHTML = '<div class="text-slate-400 py-6 text-center col-span-3">載入文件資料庫中...</div>';

      try {
        const res = await fetch('/api/workbench/artifacts');
        const data = await res.json();
        const items = data.artifacts || [];

        document.getElementById('artifacts-badge').textContent = items.length;

        if (items.length === 0) {
          grid.innerHTML = '<div class="text-slate-500 py-6 text-center col-span-3">尚未發現交付產物</div>';
          return;
        }

        grid.innerHTML = items.map(item => `
          <div class="glass-panel p-4 rounded-xl border border-white/10 hover:border-sky-500/40 transition flex flex-col justify-between group">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-semibold">
                  ${escapeHtml(item.badge || 'DOC')}
                </span>
                <span class="text-[11px] text-slate-400 font-mono">${escapeHtml(item.size)}</span>
              </div>
              <h4 class="font-bold text-white text-sm group-hover:text-sky-400 transition flex items-center gap-2">
                <i class="fas ${item.icon || 'fa-file'} text-sky-400"></i>
                <span class="truncate">${escapeHtml(item.name)}</span>
              </h4>
              <p class="text-[11px] text-slate-400 font-mono truncate" title="${escapeHtml(item.path)}">${escapeHtml(item.path)}</p>
            </div>
            <div class="pt-4 flex items-center justify-between border-t border-white/5 mt-3">
              <span class="text-[10px] text-slate-400 font-mono">${escapeHtml(item.mtime)}</span>
              <button onclick="openArtifact('${escapeHtml(item.path)}', '${escapeHtml(item.name)}')" class="px-2.5 py-1 rounded bg-white/5 hover:bg-sky-500 hover:text-white text-xs text-sky-400 transition font-medium">
                查看內容 &rarr;
              </button>
            </div>
          </div>
        `).join('');
      } catch (err) {
        grid.innerHTML = `<div class="text-rose-400 py-4 text-center col-span-3">載入產物庫失敗: ${err.message}</div>`;
      }
    }

    async function openArtifact(path, name) {
      const drawer = document.getElementById('artifact-drawer');
      const title = document.getElementById('drawer-title');
      const content = document.getElementById('drawer-content');
      const meta = document.getElementById('drawer-meta');

      title.textContent = name;
      content.textContent = "載入檔案內容中...";
      meta.textContent = path;
      drawer.classList.remove('translate-x-full');

      try {
        const res = await fetch(`/api/workbench/artifacts/read?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if (data.ok) {
          content.textContent = data.content;
          meta.textContent = `${data.filename} (${(data.size / 1024).toFixed(1)} KB)`;
        } else {
          content.textContent = `無法讀取檔案: ${data.error}`;
        }
      } catch (err) {
        content.textContent = `連線錯誤: ${err.message}`;
      }
    }

    function closeDrawer() {
      document.getElementById('artifact-drawer').classList.add('translate-x-full');
    }

    function copyDrawerContent() {
      const text = document.getElementById('drawer-content').textContent;
      navigator.clipboard.writeText(text);
      alert("已成功複製內容至剪貼簿！");
    }

    // Graphical Radial Gauge Helper
    function renderRadialGauge(percent, colorHex) {
      const radius = 24;
      const circumference = 2 * Math.PI * radius;
      const offset = circumference - (percent / 100) * circumference;
      return `
        <svg class="w-16 h-16 transform -rotate-90 shrink-0" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r="${radius}" stroke="rgba(255,255,255,0.08)" stroke-width="5" fill="transparent" />
          <circle cx="30" cy="30" r="${radius}" stroke="${colorHex}" stroke-width="5" stroke-dasharray="${circumference.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}" stroke-linecap="round" fill="transparent" />
          <text x="30" y="34" transform="rotate(90 30 30)" text-anchor="middle" fill="#F8FAFC" font-size="11" font-weight="bold" font-family="JetBrains Mono">${percent}%</text>
        </svg>
      `;
    }

    async function loadQuotasData() {
      const container = document.getElementById('quota-cards-grid');
      const alertsContainer = document.getElementById('alerts-log-container');
      container.innerHTML = '<div class="text-slate-400 py-6 text-center col-span-2">查詢各方案即時配額中...</div>';

      try {
        const [quotaRes, alertRes] = await Promise.all([
          fetch('/api/quota'),
          fetch('/api/alerts').catch(() => null)
        ]);
        const data = await quotaRes.json();
        const quotas = data.quotas || {};
        const poolRows = Array.isArray(data.pools) ? data.pools : [];

        const corePlans = [
          { key: 'MiniMax-M3', label: 'MiniMax Token Plan (MiniMax-M3.1-Flash)', role: 'Claude Code 預設 / 極速中文與測試', color: '#10B981', pct: 95 },
          { key: 'GLM-5.3', label: 'GLM Coding Plan (GLM 5.3 FlashX)', role: 'Codex & zcode 驅動 / 高速代碼生成', color: '#6366F1', pct: 92 },
          { key: 'OpenAI-API', label: 'GPT GO (OpenAI Platform)', role: '系統架構 / 深度推理', color: '#0EA5E9', pct: 90 },
          { key: 'Antigravity-Core', label: 'Antigravity AI Pro (AGY)', role: '全域自主 Agentic CLI 驅動', color: '#06B6D4', pct: 98 }
        ];

        const poolMap = {};
        poolRows.forEach(r => { if (r && r.name) poolMap[r.name] = r; });

        const cardsHtml = corePlans.map(plan => {
          const q = quotas[plan.key] || {};
          const p = poolMap[plan.key] || {};
          const isHealthy = p.ok !== false;
          const isExhausted = Boolean(q.is_exhausted);
          const reqRemaining = q.remaining_requests != null ? q.remaining_requests : (isHealthy ? '充足 (待命)' : '未就緒');
          const tokRemaining = q.remaining_tokens != null ? Number(q.remaining_tokens).toLocaleString() : (isHealthy ? '充足 (待命)' : '--');
          const resetSec = q.seconds_until_reset || q.reset_offset_s || 0;
          const resetOffset = resetSec > 0 ? `${Number(resetSec).toFixed(0)}s` : '即刻 (0s)';
          const isWarning = isExhausted || (q.remaining_requests != null && q.remaining_requests <= 2);
          const gaugePct = isExhausted ? 5 : (q.remaining_requests != null && q.limit_requests ? Math.round((q.remaining_requests / q.limit_requests) * 100) : plan.pct);

          return `
            <div class="glass-panel p-4 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3">
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  ${renderRadialGauge(gaugePct, isWarning ? '#F59E0B' : plan.color)}
                  <div class="space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="w-2.5 h-2.5 rounded-full ${isWarning ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}"></span>
                      <strong class="text-white text-sm sm:text-base">${escapeHtml(plan.label)}</strong>
                    </div>
                    <p class="text-[11px] text-slate-400 font-mono">${escapeHtml(plan.role)}</p>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[11px] font-mono shrink-0 ${isWarning ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'}">
                  ${isExhausted ? 'BREAKER OPEN' : 'HEALTHY'}
                </span>
              </div>

              <div class="grid grid-cols-3 gap-2 font-mono text-xs pt-1">
                <div class="bg-black/30 p-2 rounded-lg">
                  <span class="text-slate-400 block text-[10px]">剩餘請求 (RPM)</span>
                  <span class="font-bold text-white text-sm">${escapeHtml(String(reqRemaining))}</span>
                </div>
                <div class="bg-black/30 p-2 rounded-lg">
                  <span class="text-slate-400 block text-[10px]">剩餘 Token</span>
                  <span class="font-bold text-white text-sm">${escapeHtml(String(tokRemaining))}</span>
                </div>
                <div class="bg-black/30 p-2 rounded-lg">
                  <span class="text-slate-400 block text-[10px]">Reset 倒數</span>
                  <span class="font-bold text-sky-400 text-sm">${escapeHtml(String(resetOffset))}</span>
                </div>
              </div>
            </div>
          `;
        });

        container.innerHTML = cardsHtml.join('');

        if (alertRes && alertRes.ok && alertsContainer) {
          const alertData = await alertRes.json();
          const alerts = alertData.alerts || [];
          if (alerts.length > 0) {
            alertsContainer.innerHTML = alerts.slice(0, 8).map(a => `
              <div class="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
                <span class="text-amber-300">${escapeHtml(a.message || a.title || JSON.stringify(a))}</span>
                <span class="text-slate-400 text-[10px]">${escapeHtml(a.time || '')}</span>
              </div>
            `).join('');
          }
        }
      } catch (err) {
        container.innerHTML = `<div class="text-rose-400 col-span-2 py-4">配額資料取得失敗: ${err.message}</div>`;
      }
    }

    async function loadAgentsFleet() {
      const container = document.getElementById('agents-fleet-grid');
      container.innerHTML = '<div class="text-slate-400 py-6 text-center col-span-3">檢測雲端主機 Agent 狀態中...</div>';

      try {
        const res = await fetch('/api/workbench/agents');
        const data = await res.json();
        const agents = data.agents || [];

        container.innerHTML = agents.map(a => {
          const optsHtml = (a.options || [a.model]).map(opt =>
            `<option value="${escapeHtml(opt)}" ${opt === a.model ? 'selected' : ''}>${escapeHtml(opt)}</option>`
          ).join('');
          const modelControl = a.adjustable ? `
            <div class="flex items-center gap-1.5 mt-1">
              <select onchange="onAgentModelChange('${escapeHtml(a.id)}', this.value)" class="flex-1 bg-[#070B14] border border-sky-500/30 rounded px-2 py-1 text-xs font-mono text-emerald-300 focus:outline-none">
                ${optsHtml}
                <option value="__custom__">✏️ 自訂模型...</option>
              </select>
              <button onclick="saveAgentModels(false)" class="px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-[11px] font-mono">儲存</button>
            </div>
          ` : `<span class="text-emerald-400 font-bold">${escapeHtml(a.model || a.plan)}</span>`;

          const deleteBtn = a.custom ? `
            <button onclick="deleteCustomAgent('${escapeHtml(a.id)}')" class="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-[10px] font-mono">
              <i class="fas fa-trash-alt mr-1"></i>移除自訂
            </button>
          ` : '';

          return `
          <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3 hover:border-sky-500/40 transition">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-white/5 text-slate-300 font-bold">${escapeHtml(a.tier)}</span>
                ${deleteBtn}
              </div>
              <span class="flex items-center gap-1.5 text-xs font-mono ${a.status === 'ready' ? 'text-emerald-400' : 'text-sky-400'}">
                <span class="w-2 h-2 rounded-full ${a.status === 'ready' ? 'bg-emerald-400 animate-ping' : 'bg-sky-400'}"></span>
                ${escapeHtml(a.status.toUpperCase())}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 text-lg">
                <i class="fas ${escapeHtml(a.icon || 'fa-robot')}"></i>
              </div>
              <div>
                <h4 class="text-white font-bold text-base">${escapeHtml(a.name)}</h4>
                <p class="text-xs text-slate-400 mt-0.5">${escapeHtml(a.desc)}</p>
              </div>
            </div>
            <div class="bg-black/30 p-3 rounded-xl text-xs font-mono space-y-2">
              <div class="text-slate-400">
                <span class="block text-[11px] mb-0.5">當前綁定模型 (可動態調整):</span>
                ${modelControl}
              </div>
              <div class="text-slate-400 flex justify-between pt-1 border-t border-white/5">
                <span>綁定付費方案:</span>
                <span class="text-teal-400 font-semibold">${escapeHtml(a.plan)}</span>
              </div>
              <div class="text-slate-400 flex justify-between">
                <span>執行檔路徑:</span>
                <span class="text-slate-300 truncate max-w-[180px]">${escapeHtml(a.path || a.version)}</span>
              </div>
            </div>
          </div>
        `;
        }).join('');
      } catch (err) {
        container.innerHTML = `<div class="text-rose-400 col-span-3 py-4">取得集群狀態失敗: ${err.message}</div>`;
      }
    }

    async function loadDashboardHistory() {
      const container = document.getElementById('history-container');
      try {
        let history = [];
        const wbRes = await fetch('/api/workbench/history').catch(() => null);
        if (wbRes && wbRes.ok) {
          const wbData = await wbRes.json();
          history = wbData.history || [];
        } else {
          const res = await fetch('/api/dashboard');
          const data = await res.json();
          history = (data.history || []).map(h => ({
            prompt: h.prompt || `系統協同流水線執行 (${h.phase || h.kind || 'pipeline'})`,
            consensus_source: h.consensus_source || h.backend || h.phase || 'K.H.A.V.I.S. Pipeline',
            dispatched_at: h.dispatched_at || (h.ts ? new Date(h.ts * 1000).toLocaleString('zh-TW', { hour12: false }) : '剛剛'),
            ok: h.ok !== false,
            latency_ms: h.latency_ms
          }));
        }

        if (history.length === 0) {
          container.innerHTML = '<div class="text-slate-500 py-3 text-center">暫無派工紀錄</div>';
          return;
        }

        container.innerHTML = history.slice(0, 6).map(h => `
          <div class="p-2.5 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between gap-3">
            <div class="space-y-0.5 max-w-xl truncate">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full ${h.ok !== false ? 'bg-emerald-400' : 'bg-amber-400'} shrink-0"></span>
                <span class="text-white font-medium block truncate">${escapeHtml(h.prompt || '系統派工任務')}</span>
              </div>
              <span class="text-[10px] text-slate-400 pl-4 block">來源: ${escapeHtml(h.consensus_source || 'Fan-out')}${h.latency_ms != null ? ` · 耗時: ${h.latency_ms}ms` : ''}</span>
            </div>
            <div class="text-right font-mono text-[11px] text-slate-400 shrink-0">
              ${escapeHtml(h.dispatched_at || '剛剛')}
            </div>
          </div>
        `).join('');
      } catch (err) {
        container.innerHTML = '<div class="text-slate-500 py-2 text-center">歷史紀錄暫不可用</div>';
      }
    }

    async function loadOverviewStatus() {
      try {
        const res = await fetch('/api/dashboard');
        if (!res.ok) return;
        const data = await res.json();
        const pools = data.pools || [];
        const poolMap = {};
        pools.forEach(p => { if (p && p.name) poolMap[p.name] = p; });

        const mappings = [
          { id: 'stat-minimax', pool: 'MiniMax-M3' },
          { id: 'stat-glm', pool: 'GLM-5.3' },
          { id: 'stat-gpt', pool: 'OpenAI-API' }
        ];
        mappings.forEach(m => {
          const el = document.getElementById(m.id);
          const p = poolMap[m.pool];
          if (!el || !p) return;
          if (p.ok === true) {
            el.textContent = 'HEALTHY';
            el.className = 'text-lg font-bold text-white font-mono';
          } else if (p.ok === null) {
            el.textContent = 'WARMING';
            el.className = 'text-lg font-bold text-amber-300 font-mono';
          }
        });
      } catch (_) {}
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    document.addEventListener('DOMContentLoaded', () => {
      syncTopologyBeams(false);
      syncModelUIElements();
      loadModelSettings();
      loadWorkspaceStatus();
      refreshCustomAgentsTopology();
      loadArtifactsList();
      loadDashboardHistory();
      loadOverviewStatus();
    });
  </script>
</body>
</html>
"""
