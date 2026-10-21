"""Telegram dispatch bot backends for khavis.

Sub-modules:
- ``base``        abstract ``Backend`` protocol
- ``claude``      subprocess wrapper around ``claude -p`` (Claude Code, default MiniMax-M3.1-Flash)
- ``codex``       subprocess wrapper around ``codex exec`` (Codex CLI)
- ``antigravity`` subprocess wrapper around ``antigravity`` / ``agy`` CLI (Antigravity)
- ``minimax``     subprocess wrapper around ``minimax`` CLI (MiniMax Token Plan)
- ``zcode``       subprocess wrapper around ``zcode`` CLI (GLM Coding Plan)
- ``khavis``      in-process call to ``agents.run_team`` / ``core.registry``
"""

from __future__ import annotations

from .antigravity import AntigravityBackend
from .base import Backend, HealthResult
from .claude import ClaudeBackend
from .codex import CodexBackend
from .custom import CustomAgentBackend
from .judge import JudgeBackend
from .khavis import KhavisBackend
from .minimax import MinimaxBackend
from .zcode import ZcodeBackend

__all__ = [
    "Backend",
    "HealthResult",
    "ClaudeBackend",
    "CodexBackend",
    "AntigravityBackend",
    "MinimaxBackend",
    "ZcodeBackend",
    "CustomAgentBackend",
    "JudgeBackend",
    "KhavisBackend",
]
