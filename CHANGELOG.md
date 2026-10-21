# Changelog

All notable changes to K.H.A.V.I.S. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`khavis chat "<prompt>"`** — send one prompt through the router without
  starting a daemon. Before this the only ways in were a Python script or
  starting the HTTP server and curling it, so the router could not be tried at
  all. Supports `--pool`, `--capability`, `--json`, `--quiet`, `--max-attempts`.
  Goes through the same circuit breaker and failover as the HTTP API, so a
  dead pool is recorded and skipped instead of returning its error.
- **`khavis doctor --deep`** — make one real minimal request per configured
  pool. `health_check()` never opens a socket; it only asserts that a key, an
  endpoint and a model name are configured, so an expired key, a spent quota
  and a retired model all pass it. `--deep` is what catches them. Opt-in
  because it costs one tiny request per pool. The probe deliberately sets no
  `max_tokens`: a small budget makes reasoning models spend the whole
  allowance internally and return empty content, which reports working pools as
  broken.
- **`disabled: true` in `pools.yaml`** — actually retires a pool.
  `PluginRegistry.discover()` instantiates every plugin under `providers/`, so
  deleting or commenting out an entry never stopped a pool from being served;
  that file only *overrides* discovered plugins. Until now there was no way to
  retire a pool whose upstream retired, short of moving the plugin out of the
  package.
- `core/failover.py` — the failover loop moved out of `server/openai_api.py` so
  the CLI and the HTTP path share one implementation.

### Fixed
Three defects that all had the same shape: the tool reported a state that was
not true.

- **`doctor` probed before loading `.env`, so every pool looked keyless.**
  `health_check()` reads `os.environ` to decide `key_present`, and the command
  located the `.env` file and then never loaded it. A fully configured install
  reported `0 pool(s) ready` while nine working credentials sat unused in the
  very file it had just found. `core.env` deliberately does not auto-load on
  import — that would pollute tests — so every CLI entry point has to ask for
  it, and none of `doctor`/`chat`/`health` did. Measured on this install: 0
  pools ready before, 10 after.
- **`khavis chat` bypassed the breaker entirely.** It called
  `plugin.chat()` directly while failover lived only in `server/openai_api.py`,
  so the CLI inherited none of mechanism 1 — an expired key on the chosen pool
  surfaced raw even with nine healthy pools available.
- **Upstream errors were dumped verbatim.** A 401 printed four lines of nested
  JSON plus a `request_id`; it now prints one actionable line and caps output
  length so a credential fragment cannot leak through.
- `doctor` no longer prints `all checks passed` when nothing can serve a
  request, and it separates "no API key" from "key present but rejected" —
  the two need different fixes and lumping them together misdirects the
  operator.
- `pools.yaml` disables five pools that pass `health_check` but fail every real
  request (NVIDIA `410 Gone`; DeepSeek-V4-Pro, DeepSeek-V4.1-Flash,
  GLM-5.3-Flash `404`; OpenRouter-Free `404`). Claude-API (`401`) and GLM-5.3
  (out of quota) stay enabled on purpose: both recover on their own and chat
  now fails over past them.
- **`khavis serve` never loaded `.env` either.** The same defect as `doctor`
  and `chat`, in the entry point that had been missed: only
  `scripts/start.sh` called `load_env()`, so starting the server the
  documented way — `khavis serve` — left every pool keyless and answered
  every request with a 401/502. Found by running the server in a subprocess
  with the keys stripped from the environment, not by reading the code. With
  the fix, the same command returns 200 from OpenAI-API.
- `README` quick start documents `khavis chat` and `doctor --deep`. The Chinese
  README's curl example still pointed at `/v1/chat` with a `capability` body —
  the real endpoint is `/v1/chat/completions` in OpenAI shape. Both verified
  against a live app: `/v1/chat` returns 404, `/v1/chat/completions` returns
  200 with `choices`/`model`/`usage` plus `pool`/`cost_usd`/`latency_ms`.


These were found by reviewing the `fix/review-2026-10-02` pass. Five defects,
each of which silently disabled or inverted a guarantee that pass claimed to
provide; regression tests are pinned for all five.

- **Failover was dead code for every request that named a model.** `_pick_plugin()` returns `capability=None` when the caller pins a model, and the retry loop opened with `if not capability: break`. Since `model` is what every OpenAI-compatible client sends by default (and what `/v1/models` hands out), a 429 on the requested model reached the caller untouched. Added `CapabilityRouter.select_any()` and routed the pinned case through it: the request now continues on another healthy pool, at the cost of possibly being served by a different model. `KHAVIS_FAILOVER=0` still pins strictly, and now means "return the 429 rather than substitute a model".
- **A non-429 error whose message merely mentioned a rate limit was classified `EXHAUSTED`, bypassing the circuit breaker.** `_looks_like_quota_error()` let the message regex overrule a structured status, so `400 "your rate limit config is malformed"` parked a healthy pool in `EXHAUSTED` — a state only left by a successful call or a quota refresh, neither of which a malformed request can ever produce. A structured status is now authoritative; the phrase match applies only when no status is available, where it still catches bare `"429"` strings and raw SDK exceptions.
- **`probe_timeout_s` returned `cooldown_s` verbatim, so `cooldown_s: 0` dissolved the single-probe guarantee.** The in-flight guard became `(now - probe_started_at) < 0.0` — permanently false — and 64 concurrent callers all entered `HALF_OPEN` at once. `probe_timeout_s` now has an independent 1.0 s floor.
- **`ChromaStore.doc_id()` was content-addressed, so editing an ingested document never replaced its chunk.** Every re-ingest minted a new id and left the superseded copy in the collection, where `search()` kept returning text the user had already deleted. Ids are now derived from document identity (`doc_id`/`id`, else `source` + `chunk`) and fall back to text+metadata only when the caller gave no identity. Added `delete_source()` for wholesale re-ingest after re-chunking.
- **The Ollama provider never called `raise_if_empty`.** Every other OpenAI-shaped provider did, so an HTTP 200 with a blank body (context wall, template emitting only thinking tags) returned an empty string instead of failing over. One commit earlier claimed to route empty responses to failover; this provider was missed.
- `scripts/launch_bot_daemon.py` — `_cmdline()` returned `""` both for "process is gone" and for "this platform cannot tell you" (macOS has no procfs, and a sandboxed shell may not have an executable `ps`). `bot stop` then reported a verified mismatch — `pid 123 is not the bot ('')` — and left a running daemon in place. The unverifiable case is now reported as such, and the stop path still fails safe.

### Added
- **`core/health.py` — quota-aware circuit breaker.** This is the module that makes the "zero quota interruption" promise real. Every plugin already exposed `health_check()` / `check_quota()`; before this, **nothing in `core/` ever called them**, so the router kept handing requests to pools that had been 429ing for minutes. Now:
  - Five pool states: `UNKNOWN` (cold-start optimistic) → `CLOSED` / `OPEN` (tripped) → `HALF_OPEN` (single probe after cooldown), plus `EXHAUSTED`.
  - **Quota errors are not circuit errors.** A pool that returns 429 / `insufficient_quota` / `RESOURCE_EXHAUSTED` is marked `EXHAUSTED` and recovers on the next quota refresh instead of waiting out a cooldown — the provider is healthy, it just has nothing left to give.
  - `select()` reads cached state only; it never does network I/O on the request path. State is refreshed out-of-band (server startup, a 60 s background task, or `khavis health --refresh`) and updated inline by `record_success()` / `record_failure()`.
  - Policy in `config/health.yaml` with env overrides (`KHAVIS_HEALTH_*`).
- `CapabilityRouter.select()` now filters out pools whose circuit is open or whose quota is spent, accepts an `exclude` set so retry loops can say "don't retry these", and returns `None` when every candidate is down instead of silently routing into a known-bad pool. `router.explain_unavailable(capability)` returns a per-pool diagnosis.
- New `strategy="priority"` — deterministic, walks the YAML `pools` order and takes the first available pool. This is what the failover path uses; `weighted` remains the default so existing callers are unaffected.
- Retry-next-pool in `server/openai_api.py` (`_call_with_failover`) for both the streaming and non-streaming paths, with per-attempt audit records and the pool that actually served echoed in `model` / `pool`. Opt out with `KHAVIS_FAILOVER=0`.
- `khavis health` CLI subcommand — `--refresh` to probe every pool first, `--reset` to force-close all circuits.
- Per-pool weights in `capabilities.yaml`: `pools: {Google-Gemini: 1.2, OpenAI-API: 0.85}`. The old list form (`pools: [...]` + one `weight`) still works unchanged. This is what finally makes the "down-weight BYOK pools" policy in `config/capabilities.yaml` expressible — the previous schema applied a single weight to every pool in the entry.
- `docs/HEALTH.md` — state machine, the three design trade-offs, end-to-end failover sequence, config reference.
- `OpenAI-API` plugin — OpenAI Platform API integration (gpt-5 series). Requires `OPENAI_API_KEY` from https://platform.openai.com. Independent of ChatGPT subscription.
- `Claude-API` plugin — Anthropic Claude API integration (Sonnet 5, Opus 4.5, Haiku 4.5). Requires `ANTHROPIC_API_KEY` from https://console.anthropic.com. Independent of Claude Code or Cursor subscriptions.
- New "長文" (long context) capability tag, primarily served by Claude.
- `anthropic>=0.40.0` to runtime dependencies (needed by the Claude-API plugin).
- BYOK documentation in README and INSTALLATION — clear guidance on which pools require a separate billing account.
- `scripts/setup_ollama.sh` — one-shot setup for Mac + Surface Ollama hosts; validates endpoint reachability, pulls required models if missing, smoke-tests each pool, and writes `SURFACE_IP` to `.env` for the Surface pool. Idempotent.
- `bot/` package — Telegram dispatch bot (FastAPI + long-polling) that fans out a single user prompt to Claude Code + Codex + K.H.A.V.I.S.'s own 12-pool gateway in parallel, aggregates results with attribution, and replies with a synthesized consensus. New `bot` optional-dependency group: `fastapi`, `uvicorn`, `httpx`, `python-telegram-bot`.
- `deploy/` directory — Docker + Caddyfile + Aliyun / Tencent Cloud deploy scripts; full operator guide in `deploy/README.md`. Health endpoint exposed at `/healthz`.
- `docs/TELEGRAM_BOT.md` — operator-facing reference for the dispatch bot (commands, env vars, allowlist, deploy).

### Fixed
- **A test asserted the missing failover as expected behaviour.** `tests/test_capability_router.py::TestFallback::test_select_when_only_plugin_fails_health` set a plugin's `health_check()` to `{"ok": False}` and then asserted it was still selected. That assertion is now inverted, and a second test covers the realistic case (one pool down, one healthy).
- `README.zh-TW.md` and `docs/ARCHITECTURE.md` documented a `khavis.Router` / `from_yaml()` / `router.chat(capability="code")` API that does not exist, using English capability tags while the real ones are Chinese (`程式碼` / `推理` / `長文` …). Both rewritten against the real `core.registry` / `core.capability_router` / `core.budget` / `agents.graph` API.
- `Ollama` plugin now strips the legacy `ollama/` model prefix before posting to the native `/api/chat` endpoint — pools that shipped with `ollama/gemma4:e2b`-style configs no longer fail with HTTP 404 "model not found". Backward compatible: existing configs are auto-normalised on the wire.
- `bot/main.py` now has an `if __name__ == "__main__":` guard so `python -m bot.main` actually invokes `main()` (previously the module imported and exited silently — only the console-script entrypoint worked).
- `bot/telegram_api.py` drops `None`-valued kwargs before posting to Telegram. `parse_mode=null` was being rejected with HTTP 400 "unsupported parse_mode"; the correct way to opt out of Markdown parsing is to omit the field. Default `parse_mode` for `send_message` / `edit_message` is now `None` (plain text); MarkdownV2 formatting is reserved for the aggregator's per-result blocks.
- `bot/handlers.py` switched the simple text replies (`/start`, `/help`, `/status`, `/pools`, `/run` empty-prompt hint, "🚫 Not authorized") to plain text — MarkdownV2 was being requested but the strings contained characters that MarkdownV2 would otherwise reject.

### Changed
- `Ollama-Surface` pool default model switched from `ollama/gemma4:e2b` to `qwen2.5:1.5b` (suitable for i5/8 GB CPU-only hosts; lives on the Surface by default). Mac pool stays on `gemma4:e2b`.
- `Ollama` plugin's `_plugin_instances` now includes the per-pool `model` field, so the registry instantiates each pool with the correct model from `config/pools.yaml` instead of the hard-coded default.

### Removed
- ChatGPT-GO plugin (`providers/chatgpt.py`) — ChatGPT GO subscription does not include API access. See `docs/PLUGIN_DEVELOPMENT.md` to re-add if you have OpenAI Platform credentials.
- Updated provider count from 11 to 12 (after ChatGPT-GO removal + OpenAI-API + Claude-API additions).

## [0.1.0] — 2026-09-20

The first public release of khavis.

### Added

**Core**
- Capability-based router with `prefer`/`fallback`/`forbid`/`require` filters.
- Plugin registry with auto-discovery of files in `providers/`.
- Hot reload of `capabilities.yaml`, `pools.yaml`, and individual plugin files.
- YAML-first configuration; no database required to run.
- Append-only JSONL audit log with daily rotation.

**Providers (10 pools shipped)**
- `MiniMax-M3` — MiniMax, tagged `general`, `code`.
- `glm53` — Zhipu GLM-5.3, tagged `general`, `code`, `long-context`.
- `gemini-flash` — Google Gemini Flash, tagged `cheap`, `vision`, `long-context`.
- `gemini-pro` — Google Gemini Pro, tagged `reasoning`, `vision`, `long-context`.
- `nvidia-cloud` — NVIDIA Cloud (NIM), tagged `code`, `reasoning`.
- `volcano-ark-deepseek` — ByteDance Volcano Ark / DeepSeek, tagged `code`, `reasoning`.
- `volcano-ark-qwen` — ByteDance Volcano Ark / Qwen, tagged `general`, `code`.
- `volcano-ark-doubao` — ByteDance Volcano Ark / Doubao, tagged `general`, `vision`.
- `openrouter-free` — OpenRouter free tier, tagged `cheap`, `general`.
- `ollama-local` — Ollama (local), tagged `local`, `private`, `general`.

**Multi-agent orchestration**
- `Pipeline` primitive — sequential LLM chains with per-step capability routing.
- `DAG` primitive — arbitrary directed graphs of LLM calls.
- `Debate` primitive — N agents respond in parallel, a judge picks the best.
- Step-level retry independent of the parent call.
- Per-pipeline cost budget enforcement.

**Memory**
- Working memory (in-process, one `Pipeline.run()` lifetime).
- Episodic memory (SQLite-backed, per `session_id`).
- Semantic memory (pluggable; Chroma / Qdrant / pgvector adapters).
- Per-request opt-in via the `memory={...}` kwarg.

**CLI**
- `khavis init` — generate starter config files.
- `khavis serve` — run the HTTP daemon.
- `khavis chat` — one-shot chat from the terminal.
- `khavis doctor` — validate config and connectivity.
- `khavis reload` — manually trigger hot reload.
- `khavis agent run <name>` — run a named agent pipeline.

**HTTP API**
- `POST /v1/chat` — OpenAI-compatible chat completions.
- `POST /v1/chat/stream` — server-sent-events streaming.
- `GET /v1/pools` — list pools and live health/quota status.
- `GET /healthz` — liveness probe.
- `GET /readyz` — readiness probe (returns 503 until at least one pool is healthy).

**Documentation**
- README (English) and README.zh-TW (Traditional Chinese).
- `docs/ARCHITECTURE.md` — six-layer deep dive with sequence diagram.
- `docs/PLUGIN_DEVELOPMENT.md` — Hello World plugin walkthrough.
- `docs/CONFIGURATION.md` — every YAML knob and env var.
- `INSTALLATION.md` — pip / Docker / source install paths.
- `CONTRIBUTING.md` — code style, PR process, provider PR template.
- `docs/FAQ.md` — 15+ common questions.

**Quality**
- `pytest` suite with `respx` for HTTP mocking.
- `mypy --strict` clean across `khavis/`.
- `ruff` lint and format enforced in CI.
- Pre-commit hooks for format, lint, types.
- GitHub Actions CI on Python 3.11 and 3.12.

### Notes

This is an alpha release. The plugin API (`ProviderPlugin`) is stable, but
routing semantics may still evolve before v0.2.0. Anything documented as
"experimental" in the docs may change without a SemVer major bump until v1.0.0.

### Known limitations

- Web UI is not yet shipped — use `GET /v1/pools` for now.
- Fine-tuned model registry is not yet shipped (planned for v0.5.0).
- OpenTelemetry exporter ships as an optional extra, not bundled.

## [0.0.x] — Internal pre-releases

Pre-public development. Not documented here.

---

[Unreleased]: https://github.com/kiddhsu5/K.H.A.V.I.S./compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kiddhsu5/K.H.A.V.I.S./releases/tag/v0.1.0
