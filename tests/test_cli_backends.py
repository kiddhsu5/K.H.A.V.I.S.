"""Unit tests for Tencent Cloud CLI backends (Antigravity, Claude, MiniMax, zcode).

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from bot.backends import AntigravityBackend, ClaudeBackend, MinimaxBackend, ZcodeBackend
from bot.dispatch import DispatchRouter
from bot.models import DispatchEnvelope


def test_claude_default_model_is_minimax_flash() -> None:
    backend = ClaudeBackend()
    assert backend._model == "MiniMax-M3.1-Flash"


def test_antigravity_backend_health_not_found() -> None:
    backend = AntigravityBackend(binary="__non_existent_antigravity_cli__")
    health = asyncio.run(backend.health())
    assert health.ok is False
    assert "not in PATH" in health.detail


def test_minimax_backend_health_not_found() -> None:
    backend = MinimaxBackend(binary="__non_existent_minimax_cli__")
    health = asyncio.run(backend.health())
    assert health.ok is False
    assert "not in PATH" in health.detail


def test_zcode_backend_health_not_found() -> None:
    backend = ZcodeBackend(binary="__non_existent_zcode_cli__")
    health = asyncio.run(backend.health())
    assert health.ok is False
    assert "not in PATH" in health.detail


def test_cli_backends_mock_run() -> None:
    envelope = DispatchEnvelope(chat_id=1, prompt="Implement quicksort in Python")

    # 1. Test Antigravity mock run
    agy = AntigravityBackend(binary="antigravity")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (b'{"text": "def quicksort(): pass"}', b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        res = asyncio.run(agy.run(envelope))
        assert res.ok is True
        assert res.backend == "antigravity"
        assert "quicksort" in res.text

    # 2. Test MiniMax mock run
    minimax = MinimaxBackend(binary="minimax")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (b'{"text": "MiniMax generated python code"}', b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        res = asyncio.run(minimax.run(envelope))
        assert res.ok is True
        assert res.backend == "minimax"
        assert "MiniMax" in res.text

    # 3. Test zcode mock run
    zcode = ZcodeBackend(binary="zcode")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (b'{"text": "GLM codegeex implementation"}', b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        res = asyncio.run(zcode.run(envelope))
        assert res.ok is True
        assert res.backend == "zcode"
        assert "GLM" in res.text


def test_dispatch_router_with_all_backends() -> None:
    backends = {
        "antigravity": AntigravityBackend(binary="__non_existent__"),
        "minimax": MinimaxBackend(binary="__non_existent__"),
        "zcode": ZcodeBackend(binary="__non_existent__"),
    }
    router = DispatchRouter(backends)  # type: ignore[arg-type]

    envelope = DispatchEnvelope(chat_id=1, prompt="hello world", only=["antigravity", "minimax"])
    report = asyncio.run(router.dispatch(envelope))

    assert len(report.results) == 2
    b_names = [r.backend for r in report.results]
    assert "antigravity" in b_names
    assert "minimax" in b_names
