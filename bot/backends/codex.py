"""Subprocess wrapper for ``codex exec`` (OpenAI Codex CLI)."""

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


class CodexBackend(Backend):
    name = "codex"

    def __init__(
        self,
        binary: str = "codex",
        timeout_s: int = 180,
        model: str = "",
        cwd: str | None = None,
    ) -> None:
        self._binary = binary
        self._timeout = timeout_s
        self._model = model or os.environ.get("CODEX_DISPATCH_MODEL", "glm-5.3-flashx")
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
            version = (stdout.decode(errors="replace").strip().splitlines() or ["?"])[-1]
            return HealthResult(True, f"codex {version}")
        except FileNotFoundError as exc:
            return HealthResult(False, str(exc))
        except Exception as exc:  # noqa: BLE001 - health must never raise
            return HealthResult(False, repr(exc))

    async def run(self, envelope: DispatchEnvelope) -> BackendResult:
        args: list[str] = [self._binary, "exec", "--skip-git-repo-check"]
        if self._model:
            args += ["-m", self._model]
        # Try JSON output first; fall back to plain text if the flag is rejected.
        args += ["--json"]
        # ``--`` ends option parsing so a prompt that starts with "-" (or
        # names a subcommand like "resume") is always taken as the prompt.
        args += ["--", envelope.prompt]

        env = {
            **os.environ,
            "CI": "1",
            "NONINTERACTIVE": "1",
        }
        # Dynamic cross-provider credential mapping based on selected model
        model_lower = self._model.lower()
        glm_key = os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("GLM_API_KEY")
        minimax_key = os.environ.get("MINIMAX_API_KEY")
        if glm_key and ("glm" in model_lower or "flashx" in model_lower or "codegeex" in model_lower):
            env["OPENAI_API_KEY"] = glm_key
            if "OPENAI_BASE_URL" not in env:
                env["OPENAI_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"
        elif minimax_key and "minimax" in model_lower:
            env["OPENAI_API_KEY"] = minimax_key
            if "OPENAI_BASE_URL" not in env:
                env["OPENAI_BASE_URL"] = "https://api.minimax.cn/v1"

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
                    backend="codex",
                    ok=False,
                    error=f"timeout after {self._timeout}s",
                    model=self._model,
                )
            latency_ms = int((time.perf_counter() - t0) * 1000)
        except FileNotFoundError as exc:
            return BackendResult(backend="codex", ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - last-ditch
            return BackendResult(backend="codex", ok=False, error=repr(exc))

        stdout = stdout_b.decode(errors="replace").strip()
        stderr = stderr_b.decode(errors="replace").strip()

        if proc.returncode != 0:
            # Retry without --json in case the flag isn't accepted.
            if "--json" in args and "unknown flag" in stderr.lower():
                return await self._run_plain(envelope, latency_ms=latency_ms)
            return BackendResult(
                backend="codex",
                ok=False,
                error=stderr or f"exit={proc.returncode}",
                latency_ms=latency_ms,
                model=self._model,
            )

        text, model, tok_in, tok_out = _parse_codex_output(stdout)
        return BackendResult(
            backend="codex",
            ok=True,
            text=text,
            model=model or self._model,
            tokens_in=tok_in,
            tokens_out=tok_out,
            latency_ms=latency_ms,
        )

    async def _run_plain(self, envelope: DispatchEnvelope, *, latency_ms: int = 0) -> BackendResult:
        args = [self._binary, "exec"]
        if self._model:
            args += ["-m", self._model]
        args += ["--", envelope.prompt]
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "CI": "1"},
            )
            t0 = time.perf_counter()
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
            except TimeoutError:
                await _kill(proc)
                return BackendResult(
                    backend="codex",
                    ok=False,
                    error=f"timeout after {self._timeout}s",
                    model=self._model,
                )
        except FileNotFoundError as exc:
            return BackendResult(backend="codex", ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - last-ditch
            return BackendResult(backend="codex", ok=False, error=repr(exc))
        elapsed = int((time.perf_counter() - t0) * 1000) + latency_ms
        stdout = stdout_b.decode(errors="replace").strip()
        stderr = stderr_b.decode(errors="replace").strip()
        if proc.returncode != 0:
            return BackendResult(
                backend="codex",
                ok=False,
                error=stderr or f"exit={proc.returncode}",
                latency_ms=elapsed,
            )
        return BackendResult(
            backend="codex",
            ok=True,
            text=stdout,
            model=self._model,
            latency_ms=elapsed,
        )


async def _kill(proc: asyncio.subprocess.Process) -> None:
    """Kill a timed-out child and reap it so it does not linger as a zombie."""
    with contextlib.suppress(ProcessLookupError):
        proc.kill()
    with contextlib.suppress(Exception):
        await asyncio.wait_for(proc.wait(), timeout=5)


def _parse_codex_output(raw: str) -> tuple[str, str, int, int]:
    """Best-effort: many CLI shapes (JSON, JSONL, plain)."""
    raw = (raw or "").strip()
    if not raw:
        return "", "", 0, 0
    # Try the whole blob as JSON first.
    text, model, tin, tout = _try_json_one(raw)
    if text or model or tin or tout:
        return text, model, tin, tout
    # Otherwise scan for JSONL or {"role":"assistant",...} entries.
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        text, model, tin, tout = _try_json_one(line)
        if text:
            return text, model, tin, tout
    return raw, "", 0, 0


def _try_json_one(raw: str) -> tuple[str, str, int, int]:
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError:
        return "", "", 0, 0
    if isinstance(data, dict):
        for key in ("text", "content", "output", "message"):
            if key in data and isinstance(data[key], str):
                return data[key], str(data.get("model") or ""), 0, 0
        # Codex sometimes returns {"role":"assistant","content":[...]}
        if data.get("role") == "assistant":
            content = data.get("content")
            if isinstance(content, str):
                return content, "", 0, 0
            if isinstance(content, list):
                parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                joined = "\n".join(p for p in parts if p)
                return joined, "", 0, 0
        usage = data.get("usage") or {}
        return (
            "",
            str(data.get("model") or ""),
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
        )
    return "", "", 0, 0
