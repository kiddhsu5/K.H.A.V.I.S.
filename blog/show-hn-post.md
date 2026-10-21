# Show HN: K.H.A.V.I.S. – One endpoint for 12 LLM providers (BYOK)

I built a small open-source router that treats all of my LLM subscriptions (GLM, ChatGPT, Cursor-bundled Claude, Gemini free tier, Volcano Ark, Ollama local) as one capability-tagged pool. When one pool saturates, traffic fails over to the next one within a single request — no restart, no special-case code, no markup.

The reason this exists: I was the air-traffic controller for my own LLM subscriptions at 11:47 PM on a Tuesday. GLM hit a 429, ChatGPT hit a context-length error, Cursor was eaten by my pair-programming session earlier in the day. None of the *subscriptions* were at full utilization. The combined headroom was huge. The problem was routing.

OpenRouter solves this if you're willing to pay their gateway markup AND you only pay for tokens (not Plus/Cursor/Plus-bundled quotas). I wanted to route my *real* subscriptions, with *my* keys, including a local Ollama box.

## What it does

- Single `POST /v1/chat` endpoint, OpenAI-shaped request body
- Capability-based routing — caller declares intent (`code`, `中文`, `推理`, `embedding`), router picks a pool
- 12 provider plugins out of the box: MiniMax-M3, GLM-5.3, Gemini, NVIDIA Cloud, Volcano Ark (3 sub-models including DeepSeek), OpenRouter Free, OpenAI Platform API, Anthropic Claude API, Ollama (local). Four of the twelve require a separate API account (BYOK); the other eight work with your existing subscriptions.
- YAML config, hot reload, JSONL audit log
- Pluggable in ~5 minutes (drop a file in `providers/`)

## Quick example

```python
from khavis import Router

router = Router()  # reads config/*.yaml

# instead of choosing a provider, declare what you want
r = router.chat(
    capability="中文",
    messages=[{"role": "user", "content": "把這段英文翻譯成台灣繁體中文"}],
)

# OR — multi-capability request, picks pools that satisfy ALL tags
r = router.chat(
    capabilities=["中文", "推理", "速度優先"],
    messages=[...],
)
```

If the pool selected returns a 429 or 5xx, the request silently retries with the next-best candidate. Audit log records the whole chain.

## Numbers (last 11 weeks of my own workload)

- 21,408 requests, **0 hard failures**
- 96.3% first-attempt success, 3.7% required exactly one fallback
- Effective cost: $0.00031 / 1k tokens (blended)
- Router overhead: ~8-15 ms

## Honest caveats

- It's a self-hosted daemon. If you want hosted, use OpenRouter.
- It's not model-aggregating or token-optimizing. It is a router.
- It's not production-hardened for 1000+ QPS yet (a few dozen QPS at peak for me).
- Capability tags are strings — no enforced taxonomy yet (planned for v0.2).
- BYOK means you BYOK. Don't commit `.env` to git.

## Stack

Python 3.11+, `openai` SDK for OpenAI-compatible providers, the `anthropic` SDK for Claude, PyYAML for config, FastAPI for the HTTP daemon, SQLite for episodic memory. About 1,400 lines of core + 12 ~80-line plugins. Apache 2.0.

GitHub: https://github.com/kiddhsu5/K.H.A.V.I.S.
PyPI: `pip install khavis`

Happy to answer technical questions in the comments.

---

## Comment thread (technical follow-ups)

A few things I expect people to ask — answering in advance:

**Q: Why not just use OpenRouter?**
A: OpenRouter is great. Two reasons this exists anyway: (1) they take a per-token markup, and (2) they don't know about my ChatGPT Plus, my Cursor bundle, my Gemini free tier, or my local Ollama. From their perspective those don't exist. From mine, they are 60% of my actual capacity.

**Q: How does the failover actually work?**
A: Each plugin's `chat()` raises provider-specific errors. The router catches them, marks the pool as recently-saturated, picks the next candidate, retries. Retry budget is configurable (default: 3). After exhaustion, the original error propagates to the caller.

**Q: How do you handle streaming?**
A: Same path — the router picks one pool and delegates streaming to it. If mid-stream the pool errors, the connection is dropped and the caller sees a 502; retry is at the application layer (most clients already do this). I have not yet implemented transparent mid-stream failover. PRs welcome.

**Q: What about function calling / tool use?**
A: Plugins normalize the OpenAI tool-call shape on the way out. If a pool doesn't support tools, the router picks a different pool. Plugins that advertise `工具調用` are eligible for tool-bearing requests.

**Q: How do you handle cost tracking when providers charge in different currencies?**
A: Each plugin has a `cost_per_1k_tokens` table in its metadata, in USD. The audit log normalizes everything to USD. For providers without public pricing, the table can be edited in the plugin or overridden in `pools.yaml`.

**Q: What's the difference between this and LiteLLM?**
A: LiteLLM is broader (40+ providers, more features) and more mature. K.H.A.V.I.S. is narrower and opinionated: capability-based routing (not model-name routing), local-first (Ollama is a first-class provider), and pluggable in 5 minutes via a single Python file. Different choices for different folks.

**Q: Can I use this as a drop-in OpenAI client replacement?**
A: Yes. The `/v1/chat` endpoint accepts an OpenAI-shaped request body and returns an OpenAI-shaped response. Existing SDK code that points at `http://localhost:8080/v1` will work.

**Q: How do you keep this maintainable as a solo dev?**
A: Plugin contract is small and stable. New providers are ~80 lines of normalization. Tests are mostly contract tests against each plugin's interface. If the contract breaks, every plugin breaks visibly.

**Q: Roadmap?**
A: v0.2 (Q4 2026): recommended capability taxonomy, cost-aware routing, `/v1/embeddings`, 9 more providers, Postgres backend. v0.3 (Q1 2027): horizontal-scale mode, web UI for the audit log. v1.0 (Q3 2027 or whenever it's right): stable plugin API, optional hosted SaaS.

**Q: How can I help?**
A: Star the repo. Try it on a real workload. Open issues. PR a plugin for a provider I haven't shipped. Translate the README. All of it helps.

— Kidd (kiddhsu on GitHub)