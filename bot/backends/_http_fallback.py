"""Agentic Tool-Executing HTTP Failover Engine for CLI Backends & K.H.A.V.I.S. Team.

Upgrades Antigravity, zcode, MiniMax, Codex, and K.H.A.V.I.S. fallback from passive text
chat into a real autonomous Agentic Executor capable of:
1. Running live shell/system diagnostics & commands (`run_shell`) on the host
2. Reading files (`read_file`) and writing/modifying code (`write_file`) inside the
   shared project workspace (`cwd`)
3. Automatically failing over across all configured upstream pools in `.env`:
   - MiniMax Token Plan (`https://api.minimaxi.com/anthropic/v1/messages` & `api.minimax.chat`)
   - OpenAI GPT GO (`https://api.openai.com/v1/chat/completions`)
   - Zhipu GLM Coding Plan (`https://open.bigmodel.cn/api/paas/v4/chat/completions`)
   - OpenRouter (`https://openrouter.ai/api/v1/chat/completions`)

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

_TOOL_PROTOCOL_INSTRUCTION = """
【自主執行工具協定 (Autonomous Agentic Tool Execution Protocol)】
你不僅是問答助手，更是部署在雲端主機上具備**真實命令列與檔案系統執行權限**的自主 Agent！
當使用者的指令涉及：檢查系統狀態（如 Tailscale、SSH 通道、網路連線、程序、磁碟）、安裝/設定環境、讀寫專案檔案、或執行程式時，**請務必直接呼叫工具代為執行，不要只叫使用者自己去跑指令！**

若要執行工具，請在回覆中輸出 `<tool_call>` 標籤包裹的標準 JSON（請保持指令簡潔，避免在 JSON 內嵌多層轉義雙引號）：
1. 執行主機 Shell 指令：
<tool_call>{"tool": "run_shell", "command": "tailscale status && ss -tnlp"}</tool_call>
2. 寫入或建立檔案（相對路徑預設位於當前共用專案工作區）：
<tool_call>{"tool": "write_file", "path": "example.py", "content": "print('hello')\\n"}</tool_call>
3. 讀取檔案內容：
<tool_call>{"tool": "read_file", "path": "README.md"}</tool_call>

當你輸出 `<tool_call>` 後，系統會立即在主機上真實執行該工具，並將真實的 `stdout` / `stderr` 結果回傳給你；一旦拿到足夠的檢查結果，請立即輸出最終繁體中文詳細報告（不要再輸出 `<tool_call>`）。
"""

AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    "antigravity": (
        "你是 Google Antigravity (AGY)，部署於雲端主機、具備自主架構規劃、系統維運與全棧程式碼實作能力的 Agentic CLI 助手。"
        "請預設使用繁體中文回答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
    "codex": (
        "你是 OpenAI Codex CLI 助手，專精於高精度系統架構、程式碼生成、重構與自動化測試。"
        "請預設使用繁體中文回答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
    "minimax": (
        "你是 MiniMax Code (MiniMax-M3.1-Flash) 極速編碼 CLI 助手，擅長繁體中文技術分析與高性價比代碼生成。"
        "請預設使用繁體中文回答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
    "zcode": (
        "你是 Zhipu zcode (GLM-5.3-FlashX) 專屬編碼 CLI 助手，擅長快速演算法實現與代碼審查。"
        "請預設使用繁體中文回答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
    "claude": (
        "你是 Claude Code CLI 助手，擅長深度程式碼理解、架構重構與嚴謹除錯。"
        "請預設使用繁體中文回答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
    "khavis": (
        "你是 K.H.A.V.I.S. 7 角色多 Agent 協同團隊 (Planner / Coder A / Coder B / Debater / Critic / Verifier / Learner)。"
        "請整合規劃、工具實測與最終驗證，以繁體中文輸出最完整的綜合解答。" + _TOOL_PROTOCOL_INSTRUCTION
    ),
}

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)

# Block destructive host-wiping commands while allowing normal ops/diagnostics
_DANGEROUS_CMD_RE = re.compile(
    r"(?:\brm\s+-[rf]{1,2}\s+/(?:\s|$)|:\(\)\s*\{|\bmkfs\b|\bdd\s+if=.*of=/dev/|\bshutdown\b|\breboot\b)",
    re.IGNORECASE,
)


def has_any_upstream_key() -> bool:
    """Return True if at least one upstream API key is present in os.environ."""
    for k in ("MINIMAX_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "ZHIPUAI_API_KEY", "GLM_API_KEY"):
        val = os.environ.get(k, "").strip()
        if val and not val.startswith("your_"):
            return True
    return False


def _parse_tool_call(raw_json: str) -> dict[str, Any] | None:
    """Parse a `<tool_call>` JSON payload with fallback recovery for slightly malformed quotes/braces."""
    raw = raw_json.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:  # noqa: BLE001
        pass

    # Fallback: trim duplicate trailing "} or '} often emitted by LLMs on complex shell strings
    for suffix in ('"}"}', '"}}', "'}}"):
        if raw.endswith(suffix):
            candidate = raw[: -len(suffix)] + '"}'
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:  # noqa: BLE001
                pass

    # Regex extraction fallback for run_shell
    m_cmd = re.search(r'"tool"\s*:\s*"run_shell".*?"command"\s*:\s*"(.*)"\s*\}', raw, re.DOTALL)
    if m_cmd:
        cmd_raw = m_cmd.group(1)
        if cmd_raw.endswith('"}'):
            cmd_raw = cmd_raw[:-2]
        cmd_unescaped = cmd_raw.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        return {"tool": "run_shell", "command": cmd_unescaped}

    return None


def _execute_agent_tool(call_obj: dict[str, Any], cwd: str | None = None) -> str:
    """Execute `run_shell`, `write_file`, or `read_file` safely on the host."""
    tool = str(call_obj.get("tool") or "").strip().lower()
    work_dir = Path(cwd).resolve() if cwd and os.path.isdir(cwd) else Path.cwd()

    if tool == "run_shell":
        cmd = str(call_obj.get("command") or "").strip()
        if not cmd:
            return "[Error] Empty command"
        if _DANGEROUS_CMD_RE.search(cmd):
            return f"[Blocked] Destructive command rejected by safety guard: {cmd}"
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            combined = "\n".join(part for part in [out, err] if part).strip()
            if len(combined) > 3500:
                combined = combined[:3500] + "\n...[truncated]"
            return f"$ {cmd}\n[exit_code={proc.returncode}]\n{combined or '(no output)'}"
        except subprocess.TimeoutExpired:
            return f"$ {cmd}\n[Error] Command timed out after 25s"
        except Exception as exc:  # noqa: BLE001
            return f"$ {cmd}\n[Error] {exc}"

    if tool == "write_file":
        rel_path = str(call_obj.get("path") or "").strip()
        content = str(call_obj.get("content") or "")
        if not rel_path:
            return "[Error] Missing file path"
        target = (work_dir / rel_path).resolve() if not os.path.isabs(rel_path) else Path(rel_path).resolve()
        if not str(target).startswith(str(work_dir)) and not str(target).startswith("/tmp"):
            return f"[Blocked] Write path must be inside workspace ({work_dir}) or /tmp: {target}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"[OK] Wrote {len(content)} chars to {target}"
        except Exception as exc:  # noqa: BLE001
            return f"[Error] Failed to write {target}: {exc}"

    if tool == "read_file":
        rel_path = str(call_obj.get("path") or "").strip()
        if not rel_path:
            return "[Error] Missing file path"
        target = (work_dir / rel_path).resolve() if not os.path.isabs(rel_path) else Path(rel_path).resolve()
        if target.name.startswith(".env") or target.suffix in {".pem", ".key"}:
            return "[Blocked] Cannot read secret key/env files"
        try:
            if not target.is_file():
                return f"[Error] File not found: {target}"
            content = target.read_text(encoding="utf-8", errors="replace")[:3500]
            return f"[File: {target}]\n{content}"
        except Exception as exc:  # noqa: BLE001
            return f"[Error] Failed to read {target}: {exc}"

    return f"[Error] Unknown tool: {tool!r}"


def _format_with_logs(executed_logs: list[str], body_text: str) -> str:
    cleaned = _TOOL_CALL_RE.sub("", body_text or "").strip()
    if not executed_logs:
        return cleaned or body_text
    log_block = (
        "⚡ **【自主工具執行紀錄 (Autonomous Execution Log)】**\n```text\n"
        + "\n\n".join(executed_logs)
        + "\n```\n\n"
    )
    return log_block + (cleaned or "（已完成上述主機指令執行，請參閱上方實測輸出紀錄。）")


def call_upstream_llm_fallback(
    prompt: str,
    model: str = "",
    agent_name: str = "antigravity",
    timeout_s: int = 90,
    cwd: str | None = None,
    enable_tools: bool = True,
) -> dict[str, Any]:
    """Run an agentic multi-turn conversation (up to 3 tool rounds + synthesis) across active upstream pools."""
    sys_prompt = AGENT_SYSTEM_PROMPTS.get(agent_name, AGENT_SYSTEM_PROMPTS["antigravity"])
    messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
    executed_logs: list[str] = []
    total_in = 0
    total_out = 0
    used_model = model
    reply_text = ""

    max_tool_rounds = 2 if enable_tools else 0
    for round_idx in range(max_tool_rounds + 1):
        res = _single_turn_upstream(
            messages=messages,
            sys_prompt=sys_prompt,
            model=model,
            agent_name=agent_name,
            timeout_s=timeout_s,
        )
        if not res["ok"]:
            if executed_logs:
                return {
                    "ok": True,
                    "text": _format_with_logs(executed_logs, ""),
                    "model": used_model,
                    "tokens_in": total_in,
                    "tokens_out": total_out,
                    "error": "",
                }
            return res

        reply_text = str(res["text"] or "")
        used_model = str(res.get("model") or model)
        total_in += int(res.get("tokens_in") or 0)
        total_out += int(res.get("tokens_out") or 0)

        if not enable_tools:
            return {
                "ok": True,
                "text": reply_text,
                "model": used_model,
                "tokens_in": total_in,
                "tokens_out": total_out,
                "error": "",
            }

        matches = _TOOL_CALL_RE.findall(reply_text)
        if not matches:
            return {
                "ok": True,
                "text": _format_with_logs(executed_logs, reply_text),
                "model": used_model,
                "tokens_in": total_in,
                "tokens_out": total_out,
                "error": "",
            }

        # Execute each requested tool call
        round_outputs: list[str] = []
        for raw_json in matches[:3]:
            call_obj = _parse_tool_call(raw_json)
            if isinstance(call_obj, dict):
                tool_out = _execute_agent_tool(call_obj, cwd=cwd)
                executed_logs.append(tool_out)
                round_outputs.append(tool_out)

        if not round_outputs:
            return {
                "ok": True,
                "text": _format_with_logs(executed_logs, reply_text),
                "model": used_model,
                "tokens_in": total_in,
                "tokens_out": total_out,
                "error": "",
            }

        is_last_tool_round = round_idx >= max_tool_rounds - 1
        followup_instruction = (
            "請立即根據以上雲端主機真實執行結果，輸出完整、清楚的繁體中文總結報告（請勿再輸出任何 <tool_call> 標籤）。"
            if is_last_tool_round
            else "請根據以上真實執行結果決定是否還需要最後一次補充檢查；若資訊已充足，請直接輸出最終繁體中文總結報告（不要再包含 <tool_call> 標籤）。"
        )
        messages.append({"role": "assistant", "content": reply_text})
        messages.append(
            {
                "role": "user",
                "content": (
                    "以下為系統在雲端主機上為你真實執行上述工具後的輸出結果：\n\n"
                    + "\n---\n".join(round_outputs)
                    + "\n\n"
                    + followup_instruction
                ),
            }
        )

    return {
        "ok": True,
        "text": _format_with_logs(executed_logs, reply_text),
        "model": used_model,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "error": "",
    }


def _single_turn_upstream(
    messages: list[dict[str, str]],
    sys_prompt: str,
    model: str,
    agent_name: str,
    timeout_s: int,
) -> dict[str, Any]:
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
                messages=messages,
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
            messages=messages,
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
            messages=messages,
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
            messages=messages,
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
            messages=messages,
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
    messages: list[dict[str, str]],
    timeout_s: int,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 2048,
            "system": sys_prompt,
            "messages": messages,
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
    messages: list[dict[str, str]],
    timeout_s: int,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                *messages,
            ],
            "temperature": 0.25,
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
