# K.H.A.V.I.S.

> **Unified Multi-Agent CLI Workbench & 24-Pool LLM Gateway — with Subscription Quota Awareness, Shared Workspace / Git Worktree Isolation, Custom Agent Extensibility, and Zero Quota Interruption.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-v0.4.0-emerald.svg)](#roadmap)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[繁體中文說明文件 (README.zh-TW.md)](README.zh-TW.md)

```
    ┌────────────────────────────────────────────────────────────────────┐
    │                          K.H.A.V.I.S.                              │
    │   5 Built-in CLIs + Custom Agents · 24 LLM Pools · Web Workbench   │
    └────────────────────────────────────────────────────────────────────┘
```

### 🌟 New in v0.4.0: Unified Graphical Workbench (`/workbench`)

- **🖥️ Graphical Multi-Agent Command Center (`/workbench`)**: Interactive SVG dispatch topology, LangGraph 7-Role progress stepper, radial quota gauges, latency comparison bar charts, and live artifact preview drawer.
- **🤖 5 Built-in CLI Agents + Dynamic Model Switching**:
  - **Claude Code (`claude`)** — Default model: `MiniMax-M3.1-Flash` (MiniMax Token Plan)
  - **OpenAI Codex (`codex`)** — Default model: `glm-5.3-flashx` (GLM Coding Plan)
  - **Google Antigravity (`antigravity` / `agy`)** — Default model: `antigravity-pro`
  - **MiniMax Code (`minimax` / `mcode`)** — Default model: `MiniMax-M3.1`
  - **Zhipu zcode (`zcode`)** — Default model: `glm-5.3-flashx`
- **🔌 User-Defined Custom Agents (`core/custom_agents.py`)**: Register your own CLI tools (**Aider**, **OpenCode**, **Block Goose**, **DeepSeek/Qwen**, or custom scripts/HTTP endpoints) with 1 click in `/workbench`.
- **📁 Shared Project Workspace + Git Worktree Isolation (`core/workspace_manager.py`)**:
  - **Shared Folder Mode (`shared`, default)**: All CLI agents execute inside the exact same project directory (`workspace/<project_name>`) for frictionless sequential collaboration.
  - **Git Worktree Mode (`worktree`)**: Automatically isolates parallel fan-out runs into per-agent worktrees (`workspace/<project_name>/.worktrees/<agent_id>`), with a colorized Unified Diff viewer and 1-click merge back into the shared folder.
- **🪄 Quick Setup & BYOK Wizard (`scripts/quick_setup_wizard.sh` & `/workbench`)**: Configure subscription API keys (`MINIMAX_API_KEY`, `ZHIPUAI_API_KEY`, `OPENAI_API_KEY`, `ANTIGRAVITY_API_KEY`, `TELEGRAM_BOT_TOKEN`) directly from the browser or via interactive CLI wizard.

---

### Router overhead (p95, real registry, mocked I/O)

| Path | Budget | Measured | Notes |
| --- | --- | --- | --- |
| Cold start (`discovery_ms`) | 200 ms | **0.4 ms** | importlib + class init (measured with 12 plugins; 24 pools today) |
| YAML reload (`capability_load_ms`) | 50 ms | **9.2 ms** | hot reload goes through this path |
| Per-request routing (`selection_ms`) | 2 ms | **0.02 ms** | same order as Bifrost's published 20 μs |
| End-to-end (`chat_roundtrip_ms`) | 10 ms | **0.2 ms** | router overhead only; upstream LLM I/O dominates |

Full numbers and methodology: [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md). CI gates on the budgets above.

---


### 個人開發者 wall

In production at personal / team setups — not enterprise logos. PRs welcome to join.

| Who | Setup |
| --- | --- |
| [@kiddhsu5](https://github.com/kiddhsu5) | Multi-Agent CLI Workbench · MiniMax / GLM / GPT GO / Antigravity / Ollama |

Unified Workbench: `/workbench` · Operator Dashboard: `/dashboard` · Live Wall: `/wall`

---

## Why K.H.A.V.I.S.?

If you have ever paid for multiple LLM subscriptions, you already know the pain:

- **You hit a quota wall mid-task.** Gemini Pro is rate-limited, GLM is down for maintenance, and the one prompt you actually need to run right now cannot complete.
- **You keep rewriting boilerplate.** Every provider ships a different SDK, a different auth scheme, a different streaming protocol, a different function-call format. Your `chat()` function is 600 lines of `if provider == ...`.
- **Your local GPU sits idle while you pay for cloud.** Ollama is right there, but switching contexts is friction.
- **You cannot benchmark fairly.** Each provider has its own temperature defaults, token counters, and pricing units. Apples-to-apples comparisons require glue code.
- **You want a fallback, not a failover.** OpenRouter gives you routing, but it does not know about *your* MiniMax-M3 keys, *your* Volcano Ark credits, or *your* local Ollama box.

**K.H.A.V.I.S. is built for people who already pay for LLMs and just want them to work together.** It treats your subscriptions, free tiers, and local models as one big, capability-tagged pool. When a request arrives, the router picks a well-weighted pool for the job, the budget guard watches per-session token and cost caps, and the audit log records exactly which pool served what.

It is not a hosted gateway. It is not a SaaS. It is a self-hosted, pluggable Python router that runs on your laptop, your homelab, or your CI box, and respects the API keys you already own.

### The promise

> **Zero quota interruption.** Weighted selection spreads requests across every pool that can serve them, and the budget guard (`config/budgets.yaml`, `filter_router`) drops over-budget pools from selection before you hit their 429s — no restart, no re-auth. Automatic in-call retry across pools on upstream errors is on the roadmap; today the caller re-selects (see Basic usage §6).

---

## Features

- ✓ **24 LLM pools out of the box** — MiniMax-M3, MiMo-Code, GLM-5.3, Google Gemini, NVIDIA Cloud, ByteDance Volcano Ark (DeepSeek ×2 + GLM), OpenRouter Free, OpenAI Platform API, Anthropic Claude API, Ollama (Mac + Surface), plus 11 OpenAI-compatible long-tail pools (Groq, Mistral, Cohere, xAI, Together, Fireworks, Perplexity, Moonshot, Qwen, DeepSeek, HuggingFace).
- ✓ **Capability-based routing** — request a capability tag (`程式碼`, `推理`, `長文`, `速度優先`, `工具調用`, `中文`, `英文`, …) and the router picks the best-weighted pool for it.
- ✓ **Pluggable provider system** — drop a Python file into `providers/` and it is auto-discovered.
- ✓ **YAML-first configuration** — no UI, no database, just files you can diff in git.
- ✓ **Hot reload** — edit `capabilities.yaml`, watch the router pick it up.
- ✓ **Multi-agent orchestration** — compose multiple LLMs in a single pipeline (planner + coder + critic).
- ✓ **Three-tier memory** — working, episodic, semantic — so multi-turn agents stay coherent.
- ✓ **Audit & observability** — every HTTP request is appended to `config/audit.jsonl` with pool, model, tokens, cost, latency, capability, and outcome.
- ✓ **Self-hosted, BYOK** — bring your own keys, your own machine, your own model.
- ✓ **Apache 2.0** — use it commercially, fork it, ship it.

---

## Architecture at a glance

```
                         ┌────────────────────────┐
   Your app / agent ───► │   K.H.A.V.I.S.     │
                         └──────────┬─────────────┘
                                    │
            ┌───────────────────────┼────────────────────────┐
            ▼                       ▼                        ▼
   ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
   │  Capability    │     │   Provider     │      │   Memory &     │
   │   Router       │     │   Registry     │      │   Audit        │
   └────────┬───────┘     └────────┬───────┘      └────────┬───────┘
            │                      │                       │
            ▼                      ▼                       ▼
   ┌──────────────────────────────────────────────────────────────┐
   │              Provider Plugin Pool (24 pools)                  │
   │  MiniMax-M3 · MiMo-Code · GLM-5.3 · Google Gemini ·           │
   │  NVIDIA Cloud · Volcano Ark (×3) · OpenRouter Free · Ollama   │
   │  OpenAI / Claude (BYOK) · 11 OpenAI-compatible long-tail      │
   └──────────────────────────────────────────────────────────────┘
```

A request flows through six layers — plugins, registry, capability router, orchestration, memory, and audit. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the deep dive.

---

## Telegram dispatch bot (optional)

A Telegram bot lives in `bot/` that fans a single user prompt out to
Claude Code + OpenAI Codex + this 24-pool gateway in parallel and
returns a synthesized result. See [`docs/TELEGRAM_BOT.md`](docs/TELEGRAM_BOT.md)
for the full operator guide. Quick start:

```bash
pip install -e ".[bot]"
cp deploy/.env.example .env       # fill in BOT_TOKEN, ALLOWED_CHAT_IDS
python -m bot.main --mode polling # local dev (no public endpoint needed)
# OR
docker compose -f deploy/docker-compose.yml up -d   # webhook + Caddy
```

Then from Telegram: `/start`, `/help`, `/status`, `/pools`, `/run <prompt>`.
A single bot user gets zero-quota-interruption: when one backend is
rate-limited or down, the other two still answer.

---

## Quick start

Two commands and you are routing — no server needed.

```bash
# 1. Install
pip install khavis

# 2. Send a prompt
khavis chat "Write a quicksort in Python."
```

If something looks wrong, ask it before you send anything else:

```bash
khavis doctor          # config + which pools are usable
khavis doctor --deep   # ...and actually call each one to prove it
```

`health_check()` only checks that a key, an endpoint and a model name are
configured — it never opens a socket. An expired key, a spent quota or a
retired model all pass it. `--deep` makes one real minimal request per pool and
reports what genuinely works.

Useful flags:

```bash
khavis chat --pool Google-Gemini "…"      # pin one pool
khavis chat --capability 程式碼 "…"       # route by capability tag
khavis chat --json "…"                    # full provider response
khavis chat --quiet "…"                   # no pool/model/token footer
```

`khavis chat` goes through the same circuit breaker and failover as the HTTP
API, so an exhausted or broken pool is recorded and skipped instead of
returning its error to you.

### Running as a server

```bash
khavis init     # write starter config/ files (never overwrites)
khavis serve    # OpenAI-compatible HTTP API on :8080
```

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write a quicksort in Python."}]}'
```

The router infers a capability tag from the prompt and picks a healthy pool for it (pass `"model": "<pool name>"` to pin one). The response is OpenAI-shaped — `choices`, `model`, `usage` — plus `pool`, `cost_usd` and `latency_ms`, and the call is appended to `config/audit.jsonl`.

### Retiring a pool

`discover()` instantiates every plugin under `providers/`, so deleting or
commenting out an entry in `pools.yaml` does **not** stop a pool from being
served — that file only overrides discovered plugins. Use:

```yaml
- name: "SomePool"
  disabled: true   # actually removes it from the registry
```

---

## Installation

### Option A — pip (recommended for development)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install khavis
```

Verify:

```bash
khavis --version
khavis doctor               # checks Python, config files, plugin discovery + per-pool health
```

### Option B — Docker (zero-install, fully isolated)

```bash
docker run -d \
  --name khavis \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  ghcr.io/kiddhsu5/khavis:0.1.0
```

The image ships with all provider plugins pre-installed. Mount your `config/` directory to persist keys and routing rules.

### Option C — from source (contributors)

```bash
git clone https://github.com/kiddhsu5/K.H.A.V.I.S..git
cd khavis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

For full step-by-step setup including Ollama, Docker, and platform-specific notes, see [`INSTALLATION.md`](INSTALLATION.md).

---

## Basic usage

### 1. Capability-based chat

```python
from pathlib import Path

from core.registry import PluginRegistry
from core.capability_router import CapabilityRouter

root = Path(".")  # project root holding config/
reg = PluginRegistry(root).discover()
reg.apply_pools_config(root / "config" / "pools.yaml")

router = CapabilityRouter(reg)
router.load_capabilities(root / "config" / "capabilities.yaml")

plugin = router.select("程式碼")  # any tag from config/capabilities.yaml
result = plugin.chat([{"role": "user", "content": "Refactor this function."}])

print(result["choices"][0]["message"]["content"])
print(result.get("usage"))
```

Every plugin returns an OpenAI-shaped dict (`choices` / `model` / `usage`). Over HTTP the response additionally carries `pool`, `cost_usd` and `latency_ms`, and each request is appended to `config/audit.jsonl`.

### 2. Pinning a specific pool

```python
plugin = reg.get("DeepSeek-V4-Pro")  # exact pool name from config/pools.yaml
result = plugin.chat([{"role": "user", "content": "Hello in Japanese."}])
```

### 3. Streaming

The OpenAI-compatible server accepts `"stream": true` and answers with SSE
`chat.completion.chunk` events — point any OpenAI SDK at
`base_url=http://localhost:8080/v1`. There is no in-process generator API yet;
native `stream()` is on the roadmap.

### 4. Token & cost budgets

```python
from core.budget import get_guard

guard = get_guard()  # policy from config/budgets.yaml
if guard.allow(session_id="demo", pool="MiniMax-M3", prompt_chars=120):
    result = plugin.chat(messages)
    rec = guard.record(session_id="demo", pool="MiniMax-M3", usage=result.get("usage") or {})
    print(f"tokens={rec['tokens']}  cost=${rec['cost_usd']:.6f}")
```

### 5. Multi-agent orchestration

```python
from agents.graph import run_team

state = run_team("Design a REST API for a todo app.", session_id="demo")
print(state["final"])
```

The team graph runs planner → parallel coders → debate → critic → verify → learn
(see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)), with working / episodic /
semantic memory and per-step attribution in `logs/attribution.jsonl`.

### 6. Local-first with cloud fallback

`config/capabilities.yaml` lists every pool that satisfies a tag (weighted). An
offline Ollama box simply errors at call time and the caller retries via
`router.select(...)` — the next weighted candidate is picked at the call site,
not buried in your application code:

```python
plugin = router.select("速度優先")  # Ollama-Mac sits in this group
result = plugin.chat(messages)
```

---

## Supported providers

Pool names are exactly what you write in `config/pools.yaml` and `config/capabilities.yaml`.

| Pool ID                    | Provider                        | Capability hints                     | Notes                                |
|----------------------------|---------------------------------|--------------------------------------|--------------------------------------|
| `MiniMax-M3`               | MiniMax                         | 中文, 英文, 推理, 工具調用            | High throughput, low latency         |
| `MiMo-Code`                | Xiaomi MiMo token plan          | 中文, 程式碼, 推理                    | Anthropic Messages API surface       |
| `GLM-5.3`                  | Zhipu GLM                       | 中文, 英文, 推理, 程式碼, 工具調用     | Strong Chinese-language support      |
| `Google-Gemini`            | Google Gemini (flash/pro)       | 英文, 推理, 長文                      | `-latest` model aliases              |
| `NVIDIA-Cloud`             | NVIDIA Cloud (NIM)              | 英文, 程式碼, 推理                    | GPU-accelerated inference            |
| `DeepSeek-V4-Pro`          | ByteDance Volcano Ark           | 中文, 英文, 推理, 程式碼, 工具調用     | Sub-pool sharing one BYTEDANCE key   |
| `DeepSeek-V4.1-Flash`      | ByteDance Volcano Ark           | 中文, 英文, 速度優先, 推理            | Sub-pool                             |
| `GLM-5.3-Flash`            | ByteDance Volcano Ark           | 中文, 英文, 速度優先                  | Sub-pool                             |
| `OpenRouter-Free`          | OpenRouter free tier            | 英文                                 | Aggregator fallback                  |
| `OpenAI-API`               | OpenAI Platform API *(BYOK)*    | 英文, 程式碼, 推理, 工具調用           | Separate billing from ChatGPT        |
| `Claude-API`               | Anthropic Claude API *(BYOK)*   | 英文, 程式碼, 推理, 工具調用, 長文     | Separate billing from Claude Code    |
| `Ollama-Mac`               | Ollama (LAN / Tailscale)        | 英文, 中文, Embedding, 速度優先       | Runs on your machine                 |
| `Ollama-Surface`           | Ollama (LAN / Tailscale)        | 英文, 中文, Embedding, 速度優先       | Second local box                     |

Plus 11 OpenAI-compatible long-tail pools (one `providers/openai_compat.py` factory):
`Groq-Llama`, `Mistral-Large`, `Cohere-Command`, `xAI-Grok`, `Together-Llama`,
`Fireworks-Llama`, `Perplexity-Sonar`, `Moonshot-Kimi`, `Qwen-DashScope`,
`DeepSeek-Official`, `HuggingFace-Inference` — **24 pools in total**.

Each pool is a self-contained plugin under `providers/`. To add your own, see [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md).

---

## BYOK — Bring Your Own Keys

Some plugins work out of the box with **subscriptions you already have**; others need a **separate API account** billed by usage. The list below clarifies which is which, so you know exactly what to sign up for if you want every pool.

### Works out of the box (uses your existing keys)

| Plugin              | Account you need                                  | Where to get the key                                  |
|---------------------|---------------------------------------------------|-------------------------------------------------------|
| `MiniMax-M3`        | MiniMax API key                                   | https://api.MiniMax.chat                              |
| `GLM-5.3`           | ZhipuAI / BigModel key                            | https://open.bigmodel.cn                               |
| `DeepSeek-V4-Pro`   | ByteDance Volcano Ark key                         | https://www.volcengine.com/product/ark                |
| `DeepSeek-V4.1-Flash` | (same ByteDance key)                            | (same as above)                                       |
| `GLM-5.3-Flash`     | (same ByteDance key)                              | (same as above)                                       |
| `Google-Gemini`     | Google AI Studio key                              | https://aistudio.google.com/app/apikey                |
| `OpenRouter-Free`   | OpenRouter free API key                           | https://openrouter.ai/keys                            |
| `Ollama-Mac`        | None — runs on your machine                       | n/a                                                   |
| `Ollama-Surface`    | None — runs on your LAN                           | n/a                                                   |

### Requires a separate API account (BYOK)

These plugins are **enabled in code by default** but the integration test will skip them if the corresponding env var is unset. Fill in `.env` only for the providers you actually pay for:

| Plugin              | Account you need                                  | Where to sign up                                       |
|---------------------|---------------------------------------------------|--------------------------------------------------------|
| `OpenAI-API`        | OpenAI Platform API key                           | https://platform.openai.com/api-keys                   |
| `Claude-API`        | Anthropic API key                                 | https://console.anthropic.com                          |
| `NVIDIA-Cloud`      | NVIDIA NIM API key                                | https://build.nvidia.com (paid GPU credits)            |

> **Important:** An OpenAI Platform API key is **different** from a ChatGPT Plus / ChatGPT GO subscription. The same goes for Claude API versus Claude Code or Cursor — those tools use their own billing, not the platform API. BYOK means *you* decide which bills you pay; K.H.A.V.I.S. does not add a markup.

---

## Configuration

K.H.A.V.I.S. is configured by two YAML files (and optional environment variables):

| File                              | Purpose                                              |
|-----------------------------------|------------------------------------------------------|
| `config/capabilities.yaml`        | Maps capability tags → ordered pool preferences      |
| `config/pools.yaml`               | Declares each pool, its auth, and per-pool overrides |
| `config/agents.yaml` *(optional)* | Multi-agent pipeline definitions                     |
| `.env`                            | Secrets — never commit this                          |

Example `capabilities.yaml` (the real schema — one entry per capability tag, weighted):

```yaml
capabilities:
  - capability: "程式碼"
    pools:
      - "GLM-5.3"
      - "DeepSeek-V4-Pro"
      - "NVIDIA-Cloud"
      - "OpenAI-API"
    weight: 1.2

  - capability: "速度優先"
    pools:
      - "Google-Gemini"
      - "DeepSeek-V4.1-Flash"
      - "OpenRouter-Free"
      - "Ollama-Mac"
    weight: 1.0
```

`config/pools.yaml` declares each pool (name, endpoint, model, `env_key`);
request-level guards (token/cost caps) live in `config/budgets.yaml`.

See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for the full reference.

---

## Plugin development

Adding a new provider is a single file. The registry auto-discovers anything that subclasses `ProviderPlugin`:

```python
# providers/my_provider.py
from providers.base import ProviderPlugin


class MyProvider(ProviderPlugin):
    provider_id = "acme"

    def __init__(self, **kwargs):
        super().__init__(
            name="Acme-1",
            capabilities=["英文", "程式碼"],
            **kwargs,
        )

    def chat(self, messages, **kwargs) -> dict:
        # return {"choices": [...], "model": ..., "usage": {...}}
        ...
```

Register it in `pools.yaml`, add capability tags, submit a PR. Full walkthrough in [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md).

---

## Roadmap

- [x] **v0.1.0** — Core router, registry, plugin pools (incl. OpenAI + Claude BYOK), capability routing.
- [x] **v0.2.0** — Token-aware cost budgets (per request / per session) via `core/budget.py` + `config/budgets.yaml`.
- [x] **v0.3.0** — Built-in RAG connector (`core/rag.py`, Chroma/Qdrant/pgvector).
- [x] **v0.4.0** — OpenAI-compatible drop-in server mode (`khavis-serve`, replaces `litellm` for many users).
- [ ] **v0.5.0** — First-class fine-tuned model registry with hot-swap.
- [x] **v0.6.0 (partial)** — Web dashboard for pool health + dispatch history (`/dashboard`). Quota charts still open.
- [x] **v0.7.0** — Per-request audit log (`config/audit.jsonl`) with cost, latency, pool, capability, outcome.
- [x] **v1.0.0** — Stable plugin API (`docs/PLUGIN_API.md`), SemVer guarantees.
- [ ] **Streaming** — `stream()` generator API on `ProviderPlugin` + true SSE passthrough (today's `stream: true` emits a single final chunk).

Have an idea? Open an issue or vote on the [discussion board](https://github.com/kiddhsu5/K.H.A.V.I.S./discussions).

---

## Contributing

We welcome PRs of every size — typo fixes, new providers, routing heuristics, docs. Before you start, please read [`CONTRIBUTING.md`](CONTRIBUTING.md).

Highlights:

- PEP 8 + type hints everywhere (`mypy --strict` clean).
- New providers ship with at least one integration test.
- Update `CHANGELOG.md` under "Unreleased".
- Be kind in code review. We optimize for the next contributor.

---

## Community & Enterprise Support (Open Core)

- **Open-Source Community (Apache 2.0 Free Forever)**:
  - GitHub Issues: bug reports and feature requests
  - GitHub Discussions: questions, show-and-tell, routing & multi-CLI recipes
  - Security: see [`SECURITY.md`](.github/SECURITY.md) for responsible disclosure
- **🏢 Team & Enterprise Support**:
  - For engineering teams and organizations adopting multi-agent coding workflows, we offer commercial support & custom deployment:
    - **Shared Team Coding-Plan Quota Pools & RBAC Access Control**
    - **On-Premise / VPC Private Deployment & Custom Internal CLI Integration**
    - **Team-Wide Git Worktree Audit Logs & Governance**
  - 📩 Contact for commercial inquiries, private deployment, or ecosystem partnerships: [`security@kiddhsu.taipei`](mailto:security@kiddhsu.taipei) or via [GitHub Discussions](https://github.com/kiddhsu5/K.H.A.V.I.S./discussions).

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE) for the full text.

```
Copyright 2026 khavis contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## Acknowledgements

K.H.A.V.I.S. stands on the shoulders of:

- The [LiteLLM](https://github.com/BerriAI/litellm) team for normalizing provider APIs.
- The [OpenRouter](https://openrouter.ai) team for proving the routing concept.
- Every provider whose API we adapt to.
- Every contributor who files an issue, writes a plugin, or improves a doc.
