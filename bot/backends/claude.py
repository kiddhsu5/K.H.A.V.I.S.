"""Subprocess wrapper for ``claude -p`` (Claude Code headless)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import time
from typing import Any

from ..models import BackendResult, DispatchEnvelope
from .base import Backend, HealthResult


class ClaudeBackend(Backend):
    name = "claude"

    def __init__(
        self,
        binary: str = "claude",
        timeout_s: int = 180,
        model: str = "",
        cwd: str | None = None,
    ) -> None:
        self._binary = binary
        self._timeout = timeout_s
        self._model = model or os.environ.get("CLAUDE_DISPATCH_MODEL", "MiniMax-M3.1-Flash")
        self._cwd = cwd

    async def health(self) -> HealthResult:
        binary = shutil.which(self._binary)
        if not binary:
            return HealthResult(False, f"{self._binary} not in PATH")
        try:
            proc = await asyncio.create_subprocess_exec(
                binary,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            except TimeoutError:
                await _kill(proc)
                return HealthResult(False, "version check timed out")
            if proc.returncode != 0:
                return HealthResult(False, f"exit={proc.returncode}")
            version = stdout.decode(errors="replace").strip().splitlines()[-1] if stdout else "?"
            return HealthResult(True, f"claude {version}")
        except FileNotFoundError as exc:
            return HealthResult(False, str(exc))

    async def run(self, envelope: DispatchEnvelope) -> BackendResult:
        args: list[str] = [self._binary, "-p"]
        if self._model:
            args += ["--model", self._model]
        # Ask Claude Code for a single JSON object — easy to parse.
        args += ["--output-format", "json"]
        # ``--`` ends option parsing so a prompt such as "--help" or
        # "--dangerously-skip-permissions" is never read as a CLI flag.
        args += ["--", envelope.prompt]

        env = {
            **os.environ,
            "CI": "1",  # disable interactive hooks
            "NONINTERACTIVE": "1",
        }
        # Dynamic cross-provider credential mapping based on selected model
        model_lower = self._model.lower()
        minimax_key = os.environ.get("MINIMAX_API_KEY")
        glm_key = os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("GLM_API_KEY")
        if "minimax" in model_lower and minimax_key:
            env["ANTHROPIC_API_KEY"] = minimax_key
            env["ANTHROPIC_AUTH_TOKEN"] = minimax_key
            env.setdefault("ANTHROPIC_BASE_URL", "https://api.minimax.cn/anthropic")
        elif ("glm" in model_lower or "codegeex" in model_lower) and glm_key:
            env["ANTHROPIC_API_KEY"] = glm_key
            env["ANTHROPIC_AUTH_TOKEN"] = glm_key
            env.setdefault("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
        elif "ANTHROPIC_API_KEY" not in env and minimax_key:
            env["ANTHROPIC_API_KEY"] = minimax_key

        run_cwd = self._cwd or envelope.workspace_dir or None
        exec_kwargs: dict[str, Any] = {"env": env}
        if run_cwd and os.path.isdir(run_cwd):
            exec_kwargs["cwd"] = run_cwd

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **exec_kwargs,
            )
            t0 = time.perf_counter()
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
            except TimeoutError:
                await _kill(proc)
                return BackendResult(
                    backend="claude",
                    ok=False,
                    error=f"timeout after {self._timeout}s",
                    model=self._model,
                )
            latency_ms = int((time.perf_counter() - t0) * 1000)
        except FileNotFoundError as exc:
            return BackendResult(backend="claude", ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - last-ditch
            return BackendResult(backend="claude", ok=False, error=repr(exc))

        stdout = stdout_b.decode(errors="replace").strip()
        stderr = stderr_b.decode(errors="replace").strip()

        if proc.returncode != 0:
            return BackendResult(
                backend="claude",
                ok=False,
                error=stderr or f"exit={proc.returncode}",
                latency_ms=latency_ms,
                model=self._model,
            )

        text, model, tok_in, tok_out = _parse_claude_json(stdout, envelope.prompt)
        return BackendResult(
            backend="claude",
            ok=True,
            text=text,
            model=model or self._model,
            tokens_in=tok_in,
            tokens_out=tok_out,
            latency_ms=latency_ms,
        )


async def _kill(proc: asyncio.subprocess.Process) -> None:
    """Kill a timed-out child and reap it so it does not linger as a zombie."""
    with contextlib.suppress(ProcessLookupError):
        proc.kill()
    with contextlib.suppress(Exception):
        await asyncio.wait_for(proc.wait(), timeout=5)


def _parse_claude_json(raw: str, prompt: str) -> tuple[str, str, int, int]:
    """Best-effort JSON extraction; falls back to the raw text.

    ``claude -p --output-format json`` emits a single object whose assistant
    text lives under ``result`` (not ``text``/``content``/``output`` — those
    are checked too for older/newer CLI shapes).  ``model`` is not at the
    top level either; it is a key of ``modelUsage``.  ``usage.input_tokens``
    / ``usage.output_tokens`` are top-level and parse directly.
    """
    raw = (raw or "").strip()
    if not raw:
        return "", "", 0, 0
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError:
        return raw, "", 0, 0
    if isinstance(data, list):
        # Newer CLIs (and ``--verbose``) emit the whole event stream as a
        # JSON array; the answer lives in the final ``{"type": "result"}``.
        results = [e for e in data if isinstance(e, dict) and e.get("type") == "result"]
        if not results:
            return raw, "", 0, 0
        data = results[-1]
    if isinstance(data, dict):
        text = str(
            data.get("result")
            or data.get("text")
            or data.get("content")
            or data.get("output")
            or ""
        )
        model = str(data.get("model") or "")
        if not model:
            model_usage = data.get("modelUsage") or {}
            if isinstance(model_usage, dict) and model_usage:
                model = str(next(iter(model_usage.keys())))
        usage = data.get("usage") or {}
        tok_in = int(usage.get("input_tokens") or usage.get("input") or 0)
        tok_out = int(usage.get("output_tokens") or usage.get("output") or 0)
        return text, model, tok_in, tok_out
    return raw, "", 0, 0
