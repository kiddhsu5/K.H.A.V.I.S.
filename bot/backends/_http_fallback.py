"""Zero-dependency HTTP failover helper for CLI backends and K.H.A.V.I.S. team.

When a CLI wrapper or sub-agent encounters an expired/invalid provider key (HTTP 401),
missing OAuth session (`mcode login`), or missing SDK in the host virtualenv, this module
transparently fails over across all configured upstream pools in `.env`:
1. MiniMax Token Plan (`https://api.minimaxi.com/anthropic/v1/messages` & `api.minimax.chat`)
2. OpenAI GPT GO (`https://api.openai.com/v1/chat/completions`)
3. Zhipu GLM Coding Plan (`https://open.bigmodel.cn/api/paas/v4/chat/completions`)
4. OpenRouter (`https://openrouter.ai/api/v1/chat/completions`)

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    "antigravity": (
        "你是 Google Antigravity (AGY)，具備自主架構規劃與全棧程式碼實作能力的 Agentic CLI 助手。"
        "請預設使用繁體中文回答，提供結構清晰、可直接投入生產環境的解答與程式碼。"
    ),
    "codex": (
        "你是 OpenAI Codex CLI 助手，專精於高精度系統架構、程式碼生成、重構與自動化測試。"
        "請預設使用繁體中文回答。"
    ),
    "minimax": (
        "你是 MiniMax Code (MiniMax-M3.1-Flash) 極速編碼 CLI 助手，擅長繁體中文技術分析與高性價比代碼生成。"
        "請預設使用繁體中文回答。"
    ),
    "zcode": (
        "你是 Zhipu zcode (GLM-5.3-FlashX) 專屬編碼 CLI 助手，擅長快速演算法實現與代碼審查。"
        "請預設使用繁體中文回答。"
    ),
    "claude": (
        "你是 Claude Code CLI 助手，擅長深度程式碼理解、架構重構與嚴謹除錯。"
        "請預設使用繁體中文回答。"
    ),
    "khavis": (
        "你是 K.H.A.V.I.S. 7 角色多 Agent 協同團隊 (Planner / Coder A / Coder B / Debater / Critic / Verifier / Learner)。"
        "請整合規劃、雙向辯證與最終驗證，以繁體中文輸出最完整的綜合解答。"
    ),
}


def has_any_upstream_key() -> bool:
    """Return True if at least one upstream API key is present in os.environ."""
    for k in ("MINIMAX_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "ZHIPUAI_API_KEY", "GLM_API_KEY"):
        val = os.environ.get(k, "").strip()
        if val and not val.startswith("your_"):
            return True
    return False


def call_upstream_llm_fallback(
    prompt: str,
    model: str = "",
    agent_name: str = "antigravity",
    timeout_s: int = 90,
) -> dict[str, Any]:
    """Try configured upstream pools in order until one succeeds."""
    sys_prompt = AGENT_SYSTEM_PROMPTS.get(agent_name, AGENT_SYSTEM_PROMPTS["antigravity"])
    minimax_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    glm_key = (os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("GLM_API_KEY") or "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    errors: list[str] = []

    # 1. If GLM key is configured and model explicitly asks for glm, try GLM first
    if glm_key and not glm_key.startswith("your_") and ("glm" in model.lower() or agent_name == "zcode"):
        for glm_url in (
            "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        ):
            res = _try_openai_compat(
                url=glm_url,
                api_key=glm_key,
                model="glm-4-flash" if "glm" not in model.lower() else model,
                sys_prompt=sys_prompt,
                prompt=prompt,
                timeout_s=min(timeout_s, 20),
            )
            if res["ok"]:
                res["model"] = model or res["model"]
                return res
            errors.append(f"GLM: {res['error']}")

    # 2. MiniMax Token Plan (Anthropic-compatible endpoint on minimaxi.com)
    if minimax_key and not minimax_key.startswith("your_"):
        mm_model = model if "minimax" in model.lower() else "MiniMax-M2.7"
        res = _try_minimax_anthropic(
            api_key=minimax_key,
            model=mm_model,
            sys_prompt=sys_prompt,
            prompt=prompt,
            timeout_s=timeout_s,
        )
        if res["ok"]:
            res["model"] = model or mm_model
            return res
        errors.append(f"MiniMax-Anthropic: {res['error']}")

        # Also try MiniMax V2 chatcompletion endpoint
        res_v2 = _try_openai_compat(
            url="https://api.minimax.chat/v1/text/chatcompletion_v2",
            api_key=minimax_key,
            model="MiniMax-Text-01",
            sys_prompt=sys_prompt,
            prompt=prompt,
            timeout_s=timeout_s,
        )
        if res_v2["ok"]:
            res_v2["model"] = model or "MiniMax-M3.1-Flash"
            return res_v2
        errors.append(f"MiniMax-V2: {res_v2['error']}")

    # 3. OpenAI GPT GO Platform API
    if openai_key and not openai_key.startswith("your_"):
        oa_model = model if model.startswith("gpt-") else "gpt-4o-mini"
        res_oa = _try_openai_compat(
            url="https://api.openai.com/v1/chat/completions",
            api_key=openai_key,
            model=oa_model,
            sys_prompt=sys_prompt,
            prompt=prompt,
            timeout_s=timeout_s,
        )
        if res_oa["ok"]:
            res_oa["model"] = model or oa_model
            return res_oa
        errors.append(f"OpenAI: {res_oa['error']}")

    # 4. OpenRouter API
    if openrouter_key and not openrouter_key.startswith("your_"):
        res_or = _try_openai_compat(
            url="https://openrouter.ai/api/v1/chat/completions",
            api_key=openrouter_key,
            model="openrouter/auto",
            sys_prompt=sys_prompt,
            prompt=prompt,
            timeout_s=timeout_s,
        )
        if res_or["ok"]:
            res_or["model"] = model or "openrouter/auto"
            return res_or
        errors.append(f"OpenRouter: {res_or['error']}")

    return {
        "ok": False,
        "text": "",
        "model": model,
        "tokens_in": 0,
        "tokens_out": 0,
        "error": "; ".join(errors) if errors else "No valid upstream API keys configured in .env",
    }


def _try_minimax_anthropic(
    api_key: str,
    model: str,
    sys_prompt: str,
    prompt: str,
    timeout_s: int,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 2048,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.minimaxi.com/anthropic/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
            blocks = raw.get("content") or []
            texts = [
                str(b.get("text") or "")
                for b in blocks
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            if not texts and blocks:
                texts = [str(b.get("text") or b.get("thinking") or "") for b in blocks if isinstance(b, dict)]
            text = "\n".join(t for t in texts if t).strip()
            usage = raw.get("usage") or {}
            if text:
                return {
                    "ok": True,
                    "text": text,
                    "model": raw.get("model") or model,
                    "tokens_in": int(usage.get("input_tokens") or 0),
                    "tokens_out": int(usage.get("output_tokens") or 0),
                    "error": "",
                }
            return {"ok": False, "error": "empty content from MiniMax Anthropic API"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _try_openai_compat(
    url: str,
    api_key: str,
    model: str,
    sys_prompt: str,
    prompt: str,
    timeout_s: int,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
            choices = raw.get("choices") or []
            msg = (choices[0].get("message") or {}) if choices else {}
            content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            usage = raw.get("usage") or {}
            if content:
                return {
                    "ok": True,
                    "text": content,
                    "model": raw.get("model") or model,
                    "tokens_in": int(usage.get("prompt_tokens") or 0),
                    "tokens_out": int(usage.get("completion_tokens") or 0),
                    "error": "",
                }
            return {"ok": False, "error": f"empty response from {url}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
