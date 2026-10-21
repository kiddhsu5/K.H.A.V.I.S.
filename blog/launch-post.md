# I built K.H.A.V.I.S. because I was tired of my LLM subscriptions fighting each other

> **One endpoint for 12 LLM providers with zero quota interruption.**
> Apache 2.0 · Self-hosted · BYOK · Pluggable

**Author:** kiddhsu5 · **Published:** 2026-09-20 · **Reading time:** ~25 minutes · **Code-forward, no marketing fluff.**

---

## Table of contents

1. [The night I almost shipped a 503](#the-night-i-almost-shipped-a-503)
2. [Four pain points I kept hitting](#four-pain-points-i-kept-hitting)
3. [What I wanted (and what I built)](#what-i-wanted-and-what-i-built)
4. [Quick start — 30 seconds to your first route](#quick-start--30-seconds-to-your-first-route)
5. [How the six layers fit together](#how-the-six-layers-fit-together)
6. [Capability-based routing, in code](#capability-based-routing-in-code)
7. [Adding your own provider in 5 minutes](#adding-your-own-provider-in-5-minutes)
8. [Real benchmarks (with the honest caveats)](#real-benchmarks-with-the-honest-caveats)
9. [Trade-offs and what this is *not*](#trade-offs-and-what-this-is-not)
10. [Roadmap](#roadmap)
11. [How you can help](#how-you-can-help)
12. [Appendix: install, config reference, troubleshooting](#appendix-install-config-reference-troubleshooting)

---

## The night I almost shipped a 503

It was 11:47 PM on a Tuesday. I had a deploy script running — a long, multi-step agentic pipeline that was supposed to take a JIRA ticket, generate a PR, and open a draft. The pipeline ran on top of GLM-5.3 because GLM is what I pay for in TWD and what I want my money to go to.

GLM returned a 429. Of course it did. It was 11:47 PM, my "free tier" of the month was gone, and the credit card I'd bought credits with had been charged three days ago. The pipeline died on step 4 of 9.

I switched to ChatGPT GO. ChatGPT GO returned a different 429 — "context_length_exceeded", because I'd accidentally given it a stack trace and three file dumps. Cool. Then I tried Claude, which I pay for through Cursor. Cursor's quota was eaten up by my pair-programming session at 4 PM. Dead.

Then Gemini. Gemini worked, but it returned Python 2 syntax for my Flask middleware. Then DeepSeek through Volcano Ark. That one actually worked, but I'd already burned 90 minutes, and the deploy window was gone.

I sat there, in my underwear, with five open browser tabs, three API dashboards, and an error log. And I thought: *this is ridiculous.* I am paying for at least four LLM subscriptions at any given moment. None of them are full. There is no universe in which my *combined* available capacity cannot answer a single request. The problem is not capacity. The problem is that I am playing air traffic controller for my own APIs at midnight.

That night I wrote the first 200 lines of `khavis`. Six weekends later, it is what you're reading about.

This post is the long version of what it does, why I built it that way, and how you can use it (or improve it) starting today.

---

## Four pain points I kept hitting

If any of these sound like you, the rest of this post will make sense.

### Pain #1: Quota walls at the worst possible time

I do not have one LLM subscription. I have:

- **GLM Coding Plan** (NT$300/month) — for code, because GLM 5.3 is shockingly good at TypeScript and the price-per-token is unbeatable in Taiwan.
- **ChatGPT Plus** (US$20/month) — for English reasoning and pair programming.
- **Cursor Pro** (US$20/month) — mostly because the IDE integration is real, even if I resent the bundled pricing.
- **Gemini API free tier** — for "throwaway" requests and embeddings.
- **Volcano Ark credits** (paid in CNY through a friend) — for DeepSeek and 豆包 access.
- **Ollama** on my M3 MacBook — for anything private.

That's a lot of money. But here's the thing: **no single subscription is ever fully utilized.** GLM runs out around the 20th of every month. ChatGPT dies by Wednesday. Cursor is dead by Thursday. The free Gemini tier resets daily but I forget to plan around it. Volcano Ark credits trickle away.

The combined *headroom* across all of them is enormous. The router just needs to know which one is currently alive.

### Pain #2: `if provider == ...` boilerplate

Every provider ships a different SDK. Different auth scheme, different streaming protocol, different function-call format, different token counter, different way of raising a rate-limit error.

Before K.H.A.V.I.S., my `chat()` function looked like this (and I'm not proud of it):

```python
# Old code I had in production for 14 months. It worked. It was ugly.
def chat(messages, provider="auto", **kwargs):
    if provider == "openai":
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        try:
            r = client.chat.completions.create(model="gpt-5-mini", messages=messages, **kwargs)
            return _norm_openai(r)
        except openai.RateLimitError:
            if _should_fallback(kwargs):
                return chat(messages, provider="anthropic", **kwargs)
            raise
    elif provider == "anthropic":
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        try:
            r = client.messages.create(
                model="claude-sonnet", messages=_to_anthropic(messages), **kwargs
            )
            return _norm_anthropic(r)
        except anthropic.RateLimitError:
            if _should_fallback(kwargs):
                return chat(messages, provider="openai", **kwargs)
            raise
    elif provider == "gemini":
        client = genai.GenerativeModel("gemini-flash-latest")
        try:
            r = client.generate_content(_to_gemini(messages))
            return _norm_gemini(r)
        except Exception:
            ...
    elif provider == "glm":
        # different endpoint, different auth header, different streaming
        ...
    elif provider == "deepseek":
        ...
    # 200 more lines
```

Every new model I wanted to add meant another 60 lines of normalization. Every new SDK breaking change meant a Friday night bug-hunt. Every fallback rule was a special case.

### Pain #3: The OpenRouter tax

OpenRouter is great. They aggregate a huge number of models behind one endpoint and they charge you a *small* per-token markup for routing.

That markup is real, though. On my GLM-heavy workload, OpenRouter charges roughly 5% on top of the underlying provider cost. Over a year, that's a meaningful chunk of one of my subscriptions.

Worse: OpenRouter does not know about my ChatGPT Plus quota, my Cursor bundle, my local Ollama, or my Gemini free tier. From OpenRouter's perspective, those don't exist. From mine, they are 60% of my actual capacity.

I wanted OpenRouter's UX, but with *my* keys and *my* subscriptions as the routing substrate. That's the entire reason this project exists.

### Pain #4: I cannot reason about cost or quality

When I asked "which model is best for X?" I had no real data. Each provider's dashboard counted differently. Some counted input and output. Some counted cached vs uncached. Some charged in USD, some in CNY, some in credits. My OpenAI dashboard said I spent $14 last month; my GLM dashboard said I spent 89 元; my mental model said "roughly the cost of two lunches".

I wanted one place to see: *what request hit what pool, how long it took, what it cost in USD-equivalent, and whether it succeeded.* K.H.A.V.I.S. logs all of this, in one stream, in one currency, in one file.

---

## What I wanted (and what I built)

The list of properties I wanted was short:

| Want | K.H.A.V.I.S. answer |
|---|---|
| No quota interruption | Yes — silent failover on 429 / 5xx / context overflow |
| Use my existing keys | Yes — BYOK, zero markup, runs on my box |
| Add new providers easily | Yes — drop a Python file in `providers/` |
| Route by intent, not by name | Yes — capability tags (`中文`, `code`, `reasoning`, `embedding`, ...) |
| Local-first | Yes — Ollama is a first-class provider |
| Open source | Yes — Apache 2.0 |
| Visible cost & latency | Yes — structured audit log per request |
| Hot reload config | Yes — edit YAML, watch the daemon pick it up |
| Multi-agent pipelines | Yes — planner + coder + critic in one call |

What I built is small. About 1,400 lines of Python core, 12 provider plugins (roughly 80 lines each), one HTTP daemon, and a YAML schema. It runs on my laptop, on a homelab NUC, on a CI box, and on a friend's Raspberry Pi 4. It has survived a real production load for 11 weeks and has not yet dropped a request that wasn't already dropped upstream.

The tagline says it all: **"One endpoint for 12 LLM providers with zero quota interruption."**

**About BYOK:** of the 12 pools, eight work with subscriptions you likely already have (MiniMax-M3, GLM-5.3, Volcano Ark, Google Gemini, OpenRouter Free, local Ollama). Four require a *separate* platform-API account billed directly by the provider — OpenAI Platform API, Anthropic Claude API, NVIDIA NIM. They are enabled in code by default and silently skipped if the env var is unset. You stay in control of every bill. BYOK is not a "missing feature" — it's the feature.

---

## Quick start — 30 seconds to your first route

```bash
# 1. Install
pip install khavis

# 2. Initialize a config in the current directory
khavis init

# 3. Drop your API keys into the generated .env
echo "ZHIPUAI_API_KEY=..."        >> .env   # GLM
echo "GOOGLE_API_KEY=..."         >> .env   # Gemini
echo "BYTEDANCE_API_KEY=..."      >> .env   # Volcano Ark / DeepSeek / 豆包
echo "NVIDIA_API_KEY=..."         >> .env   # NVIDIA Cloud
echo "OPENROUTER_API_KEY=..."     >> .env   # OpenRouter free tier

# 4. Run the daemon (HTTP API on :8080 by default)
khavis serve
```

That's it. Now hit it:

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "code",
    "messages": [{"role": "user", "content": "Write a quicksort in Python."}]
  }'
```

The router will:

1. Look up `code` in `capabilities.yaml`.
2. See a weighted list of pools that advertise `code`: GLM-5.3, DeepSeek-V4-Pro, NVIDIA-Cloud.
3. Check each pool's recent quota pressure (rolling window, in-memory).
4. Pick one — currently, the one with the lowest saturation.
5. Send the request, normalize the response.
6. Log it.
7. Return JSON to you.

If pool #1 returned a 429, the request would have gone to pool #2 without you knowing. You didn't write a fallback. You didn't configure a strategy. The router just did it.

### What `khavis init` produces

```
.
├── config/
│   ├── capabilities.yaml   # capability → pool mappings
│   └── pools.yaml          # pool definitions
├── providers/              # plug-in directory (auto-discovered)
│   ├── base.py
│   ├── MiniMax.py
│   ├── glm.py
│   ├── gemini.py
│   ├── nvidia.py
│   ├── volcano.py
│   ├── openrouter.py
│   └── ollama.py
├── audit/                  # JSONL logs land here
├── .env.example            # keys to fill in
└── pyproject.toml
```

Everything is a file you can diff in git. There is no database to migrate. There is no UI to learn.

---

## How the six layers fit together

I tried to keep the architecture boring. Every system I trust runs on a small number of well-named layers. K.H.A.V.I.S. has six.

```
                         ┌────────────────────────┐
   Your app / agent ───► │   khavis (core)    │
                         └──────────┬─────────────┘
                                    │
            ┌───────────────────────┼────────────────────────┐
            ▼                       ▼                        ▼
   ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
   │  Layer 1:      │     │   Layer 2:     │      │   Layer 3:     │
   │  Plugins       │     │   Registry     │      │   Capability   │
   │                │     │                │      │   Router       │
   └────────┬───────┘     └────────┬───────┘      └────────┬───────┘
            │                      │                       │
            ▼                      ▼                       ▼
   ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
   │   Layer 4:     │     │   Layer 5:     │      │   Layer 6:     │
   │   Orchestrator │     │   Memory       │      │   Audit        │
   └────────────────┘     └────────────────┘      └────────────────┘
```

### Layer 1 — Plugin pool

Twelve (and counting) provider plugins, one file each. Each plugin implements the same four-method interface:

```python
class ProviderPlugin(ABC):
    name: str
    provider_id: str
    capabilities: List[str]

    @abstractmethod
    def chat(self, messages, **kwargs) -> Dict[str, Any]: ...

    @abstractmethod
    def check_quota(self) -> Dict[str, Any]: ...

    @abstractmethod
    def list_models(self) -> List[str]: ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]: ...
```

The plugin is the only place that knows the provider's quirks. Everything above this layer sees a uniform interface.

### Layer 2 — Registry

The registry scans `providers/`, imports every class that subclasses `ProviderPlugin`, instantiates them from `pools.yaml`, and indexes them by name and by capability tag. It also runs a health-check loop every N seconds and exposes a `live()` / `by_capability()` API.

### Layer 3 — Capability router

The router is *not* a load balancer. It does not round-robin. It does not least-connections. It picks a pool based on:

1. **Capability match.** The caller asked for `code`; only pools that advertise `code` are eligible.
2. **YAML weight.** Pools can be weighted (e.g. `code` has GLM at 1.2 because I trust it more for code, the rest at 1.0).
3. **Recent saturation.** A rolling window tracks each pool's recent failures and slowdowns. Saturated pools are deprioritized.

That's it. The selection strategy is deliberately boring.

### Layer 4 — Orchestrator

This is the layer that turns one request into many. If you ask for "debate", the orchestrator will:

1. Ask pool A for a position.
2. Ask pool B for a counter-position.
3. Ask pool C to adjudicate.
4. Return C's verdict plus the full transcript.

Each leg picks its own pool based on capability. The planner gets a reasoning pool; the coder gets a code pool; the critic gets a critical-reasoning pool. You can compose pipelines without writing code — just describe them in YAML.

### Layer 5 — Memory

Three tiers:

- **Working memory** — current request, kept in-process.
- **Episodic memory** — recent turns, kept in SQLite, scoped per session.
- **Semantic memory** — long-term facts, pluggable back-end (SQLite today, pgvector tomorrow).

Multi-turn agents stop forgetting what they said three steps ago.

### Layer 6 — Audit

Every `chat()` call writes one JSONL line:

```json
{
  "ts": "2026-09-20T22:14:08.412Z",
  "request_id": "9b1f-...",
  "capability": "code",
  "pool": "GLM-5.3",
  "model": "glm-5.3",
  "input_tokens": 412,
  "output_tokens": 188,
  "latency_ms": 1247,
  "cost_usd": 0.00031,
  "outcome": "success",
  "fallback_chain": [],
  "session_id": "agent-2026-09-20-003"
}
```

You can `tail -f audit/requests.jsonl` and watch the router work. You can also point anything that reads NDJSON at it — DuckDB, `jq`, a quick Grafana panel.

---

## Capability-based routing, in code

This is the part I'm proudest of, because it's the part I needed most.

The `before` picture: tell the router which *provider* to use. The router has no idea what you want.

```python
# BEFORE — caller decides the provider
client = openai.OpenAI(api_key=OPENAI_KEY)
r = client.chat.completions.create(model="gpt-5-mini", messages=[...])
```

The `after` picture: tell the router what you want to *do*. The router picks a provider that can do it.

```python
# AFTER — caller declares intent
from khavis import Router

router = Router()  # loads config/pools.yaml + config/capabilities.yaml

r = router.chat(
    capability="中文",
    messages=[{"role": "user", "content": "幫我把這段英文翻譯成台灣繁體中文，保留語氣。"}],
)
```

What happens behind that call:

1. `Router.chat("中文", messages)` asks the `CapabilityRouter` for candidates that advertise the `中文` capability.
2. The capability router reads `capabilities.yaml` and finds seven pools: MiniMax-M3, GLM-5.3, DeepSeek-V4-Pro, DeepSeek-V4.1-Flash, GLM-5.3-Flash, Ollama-Mac, Ollama-Surface.
3. It checks each pool's health (last 60 seconds of errors, latency, quota).
4. It runs a weighted-random selection with deprioritization on saturation.
5. It calls `plugin.chat(messages)`.
6. If that pool raises a `RateLimitError` or `APIError`, it transparently retries with the next candidate, up to N times.
7. It logs the outcome.

That's it. There is no `if provider == "glm"` in your code. There is no fallback ladder. The router owns that complexity; your code just says what it wants.

### The real win: capability composition

Most days, I don't just want "Chinese". I want "Chinese + reasoning". Or "Chinese + cheap". Or "Chinese + vision + local".

```python
# multi-capability request
r = router.chat(
    capabilities=["中文", "推理", "速度優先"],  # intersection
    messages=[...],
)
```

The candidate set is the *intersection* of all three capability lists — only pools that advertise all three tags are eligible. If nothing matches, the router relaxes constraints one at a time, in order, and tells you about the relaxation in the audit log.

This lets me write an agent that says:

> "Give me a fast Chinese-speaking reasoning model"

...and the router picks among the pools that actually fit *all three* of those constraints. If I later add a new pool that does all three, the agent picks it up automatically. No code change.

### A real example: a multi-step research task

Here's the actual call signature I use for my "summarize a paper" agent:

```python
result = router.pipeline(
    [
        PipelineStep(
            capability="推理",
            role="planner",
            prompt="Read the following abstract and produce a 3-bullet outline. ...",
        ),
        PipelineStep(
            capability=["中文", "推理"],
            role="translator",
            prompt="Translate the outline to Taiwan Mandarin. ...",
        ),
        PipelineStep(
            capability=["程式碼", "推理"],
            role="critic",
            prompt="Identify any factual errors in the translated outline. ...",
        ),
    ],
    input=abstract,
)
```

Each step picks its own pool. The planner lands on a reasoning pool (usually GLM or ChatGPT). The translator lands on a Chinese pool (usually GLM or DeepSeek on Volcano Ark). The critic lands on a code+reasoning pool (usually ChatGPT or NVIDIA Cloud). Each step is logged separately. If any step's pool is saturated, that step alone fails over.

I use this exact pattern for JIRA-ticket-to-PR, paper-summarization, and a few internal tools. It is the most-borrowed code in my own repos.

---

## Adding your own provider in 5 minutes

This is the section I want you to actually try. Open a terminal. I'll wait.

```bash
# 1. Make a fresh plugin scaffold
khavis new-provider myprovider
# -> creates providers/myprovider.py
```

You'll get a file that looks like this:

```python
"""Myprovider provider plugin.

Auto-generated by `khavis new-provider myprovider`.
Fill in the four required methods and you are done.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import ProviderPlugin

DEFAULT_ENDPOINT = "https://api.myprovider.com/v1"
DEFAULT_MODEL = "myprovider-flash"
ENV_KEY = "MYPROVIDER_API_KEY"


class MyproviderPlugin(ProviderPlugin):
    provider_id = "myprovider"

    def __init__(self, endpoint=None, api_key=None, model=None, capabilities=None, metadata=None):
        super().__init__(
            name="Myprovider-Flash",
            endpoint=endpoint or DEFAULT_ENDPOINT,
            api_key=api_key or os.getenv(ENV_KEY),
            model=model or DEFAULT_MODEL,
            capabilities=capabilities or ["英文", "推理"],
            metadata=metadata or {"region": "us", "tier": "free"},
        )

    def chat(self, messages, **kwargs):
        # TODO: implement
        raise NotImplementedError

    def check_quota(self):
        return {"remaining": None, "total": None, "tier": None, "provider": self.provider_id}

    def list_models(self):
        return [self.model or DEFAULT_MODEL]

    def health_check(self):
        return {
            "ok": bool(self.api_key) and bool(self.default_endpoint),
            "detail": f"endpoint={self.default_endpoint} key_present={bool(self.api_key)}",
        }
```

Now fill in `chat()`. If your provider speaks the OpenAI-compatible Chat Completions API (and most do — including NVIDIA Cloud, OpenRouter, Volcano Ark, Together, Groq, and a long tail), it's three lines:

```python
from openai import OpenAI

def __init__(self, ...):
    super().__init__(...)
    self._client = OpenAI(api_key=self.api_key, base_url=self.default_endpoint)

def chat(self, messages, **kwargs):
    response = self._client.chat.completions.create(
        model=kwargs.pop("model", self.model),
        messages=messages,
        **kwargs,
    )
    return response.model_dump()
```

If your provider is genuinely weird (Anthropic native, Gemini native, etc.), you have about 50 lines of normalization to write. The `glm.py` and `gemini.py` files in `providers/` are good templates — they show exactly how to handle streaming, function calls, and the most common error shapes.

### Step 3 — register the pool in YAML

```yaml
# config/pools.yaml — append this:
  - name: "Myprovider-Flash"
    provider_id: "myprovider"
    endpoint: "https://api.myprovider.com/v1"
    model: "myprovider-flash"
    env_key: "MYPROVIDER_API_KEY"
```

### Step 4 — advertise a capability (optional)

```yaml
# config/capabilities.yaml — append this:
  - capability: "速度優先"
    pools:
      - "Myprovider-Flash"
      - "Google-Gemini"
    weight: 1.0
```

### Step 5 — hot-reload and try it

```bash
# the daemon picks up the new file automatically (it watches providers/)
khavis serve
# in another shell:
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"capability": "速度優先", "messages": [{"role":"user","content":"hello"}]}'
```

That's the whole flow. Five minutes, if you don't count the part where you argue with the provider's auth scheme.

---

## Real benchmarks (with the honest caveats)

I want to be upfront about what these numbers are and aren't.

**What they are:** end-to-end latency and cost measurements from my own workload over the last 11 weeks, sampled from `audit/requests.jsonl`. My workload is roughly:

- 38% code generation / refactoring tasks
- 22% Chinese-language tasks (translation, summarization)
- 18% English reasoning tasks (planning, summarization)
- 12% embeddings + retrieval
- 10% misc (vision, agentic multi-step)

**What they aren't:** a controlled apples-to-apples benchmark. I am not running the same prompts across all providers at the same temperature. Different providers have different optimal temperatures; I used each provider's recommended defaults. If you want a controlled comparison, [Artificial Analysis](https://artificialanalysis.ai/) does this professionally.

That said, here's the median latency and rough cost-per-1k-tokens for each pool on my workload:

| Pool | Median latency (ms) | p95 latency (ms) | Cost / 1k tok (USD, blended) |
|---|---:|---:|---:|
| GLM-5.3 | 1180 | 3400 | $0.00018 |
| Google-Gemini (2.5-flash) | 720 | 1600 | $0.00010 |
| DeepSeek-V4-Pro (Volcano Ark) | 1450 | 3100 | $0.00027 |
| GLM-5.3-Flash (Volcano Ark) | 540 | 1100 | $0.00005 |
| NVIDIA-Cloud (llama-3.3-70b) | 1110 | 2400 | $0.00060 |
| OpenRouter-Free | 2100 | 5800 | $0.00000 (free) |
| Ollama-Mac (gemma4:e2b, M3) | 380 | 880 | $0.00000 (electricity) |
| Ollama-Surface (gemma4:e2b) | 270 | 610 | $0.00000 |

And here is what the router looks like *as a system*, averaged over a week of traffic:

```
Router-level metrics (7-day window)
─────────────────────────────────────────────────
Total requests:           21,408
Successful first-attempt: 20,612  (96.3%)
Required 1 fallback:        687   (3.2%)
Required 2 fallbacks:        98   (0.46%)
Required 3+ fallbacks:       11   (0.05%)
Total failures (all pools exhausted):  0

Median latency (first attempt):  890 ms
Median latency (with fallback):  1640 ms

Cost-equivalent (USD, full week):  $ 9.42
Effective cost / 1k tokens:        $ 0.00031
```

The headline number is the last row: **0 hard failures over 21k requests across 10 providers and 4 subscriptions.** Before K.H.A.V.I.S., on the same workload, my old script had a 1.4% hard-failure rate (one in seventy requests returned a 429 that I had to manually retry). After K.H.A.V.I.S., my call site never has to think about it.

The 3.7% of requests that triggered a fallback all eventually succeeded. Most fallbacks were GLM-5.3 → GLM-5.3-Flash (when I burned through my monthly allotment) or DeepSeek-V4-Pro → Gemini-Flash (when Volcano Ark credits ran thin).

**Caveat 1:** this is my workload. Yours will be different. If your workload is 95% English reasoning, the picture changes — ChatGPT and Gemini carry more of it.

**Caveat 2:** the router itself adds about 8-15 ms of overhead per request. I haven't yet benchmarked it under sustained 100-req/s load. If you need that, file an issue; I'll profile.

**Caveat 3:** cost numbers are blended across my real prompt distribution. If you ask "summarize the entire Game of Thrones corpus", the per-1k-tok cost will look very different.

---

## Trade-offs and what this is *not*

I want to be honest about where K.H.A.V.I.S. will *not* help you.

### What it's not

- **It's not a hosted gateway.** There is no `router.khavis.com`. You run it yourself. If you don't want to run it yourself, [OpenRouter](https://openrouter.ai/) exists and is great.
- **It's not a model aggregator.** I don't host any models. I don't resell any subscriptions. I just route to providers you already pay for.
- **It's not a token-optimizer.** It will not compress your prompts, choose a cheaper model for you behind your back, or downgrade you silently. If you ask for `reasoning`, you get a reasoning model. Period.
- **It's not a finetuning platform.** You cannot fine-tune models through khavis. (You can route fine-tuning jobs to providers that support it — that's on the roadmap.)
- **It's not production-hardened for 1000+ QPS.** I run it at modest scale (a few dozen QPS at peak). It uses an in-memory registry and SQLite-backed memory; if you need Redis and Postgres and horizontal scaling, you will need to fork or wait for v0.3.
- **It's not trying to replace the SDKs you already use.** The plugin system wraps them. If you have working OpenAI / Anthropic code, leave it alone.

### When you should NOT use K.H.A.V.I.S.

- You have one subscription and one use case. (Just call the SDK directly.)
- You need a hosted SLA. (Use a hosted gateway.)
- You need sub-100ms latency. (Router overhead + network hops will kill you.)
- You need model routing based on prompt content, not capability tags. (Different product — look at [Martian](https://withmartian.com/) or [Not Diamond](https://notdiamond.ai/).)
- You don't trust yourself to run a daemon on a box. (Use OpenRouter.)

### Honest design trade-offs

1. **Capability tags are strings, not enums.** I deliberately did not enforce a taxonomy. You can use `中文` or `chinese` or `cn` or whatever. The downside: typos. The upside: zero config to onboard a new tag. (I do plan to ship a recommended taxonomy in v0.2.)
2. **No UI, by design.** Everything is YAML and JSONL. If you want a UI, you can build one on top of the audit log. There is no built-in dashboard yet. (PRs welcome.)
3. **BYOK means you BYOK.** If your keys leak, that is on you. The daemon does not log them, does not transmit them anywhere except to the upstream provider, and supports `.env` / vault / 1Password CLI / whatever you already use. But it cannot protect you from a `git commit -A` you didn't mean to make.
4. **Failover is best-effort, not guaranteed.** If *all* your pools are dead, the router returns an error. It will not invent an answer.
5. **Plugin auto-discovery means an evil plugin can register itself.** Don't run untrusted code in your `providers/` directory. (This is true of any plugin system.)

If any of those are deal-breakers for you, that's fine. There are other tools. I built this for me; if it fits you, great; if not, I hope the architecture inspires whatever you do build.

---

## Roadmap

I'll keep this short and dated. As of v0.1.0:

### v0.2 — Q4 2026

- [ ] Recommended capability taxonomy (with i18n: `中文`, `zh-TW`, `zh-CN`, ...)
- [ ] Cost-aware routing (prefer cheapest pool that meets the capability + latency budget)
- [ ] Built-in `/v1/embeddings` and `/v1/audio/transcriptions` endpoints
- [ ] 9 more provider plugins: AWS Bedrock, Azure OpenAI, Vertex AI, Mistral, Groq, xAI, Cohere, Together, Fireworks
- [ ] Postgres backend for episodic memory (still SQLite by default)
- [ ] OpenTelemetry traces per request

### v0.3 — Q1 2027

- [ ] Horizontal-scale mode (shared-nothing daemon + Redis registry)
- [ ] Pluggable cost model (USD / CNY / credits / custom)
- [ ] A small, ugly web UI for `audit/`
- [ ] Streaming function-call composition (planner streams tokens into coder while coder is still planning)
- [ ] Built-in evaluator harness (run a prompt suite, report per-pool success + cost)

### v1.0 — Q3 2027 (or whenever it's right)

- [ ] Stable plugin API (v1.0 plugin contract)
- [ ] Stable config schema (v1.0 YAML)
- [ ] Backwards-compat promise for plugin and config authors
- [ ] Hosted, optional SaaS tier (still BYOK) for people who don't want to run a daemon

The optional SaaS is not the goal — the goal is the open-source router. But I want a path to "I don't want to run this myself" without giving up BYOK. More on that later.

---

## How you can help

Three things, in order of impact:

### 1. Star the repo

If you made it this far and you think you'll use this, the single highest-leverage thing you can do is **star the repo on GitHub**. Stars are the algorithm that decides whether other people ever see this. The repo URL is at the top of the post.

### 2. Try it on your real workload for a week

The fastest way to find real bugs is to run this against a workload you actually care about. Open an issue if anything breaks. Open a PR if you fix it. I read every issue within 48 hours.

### 3. Write a plugin for a provider I haven't shipped yet

The provider list I plan to add is in the roadmap, but I'd rather have a community-maintained list. If you use a provider every day and I haven't shipped a plugin for it, please send a PR. The plugin contract is stable; the `glm.py` file is the cleanest example. Five minutes, I promise.

### 4. Translate the README

The `README.zh-TW.md` already exists. I'd love `README.ja.md`, `README.ko.md`, `README.es.md`, `README.de.md`. The translation memory is small, the value is large.

### 5. Tell me what I got wrong

If you've been routing LLMs for longer than I have and you see a design choice you'd push back on, **please tell me**. The plugin contract, the capability model, the audit schema, the failover strategy — all of this is in scope for revision based on real feedback.

---

## Appendix: install, config reference, troubleshooting

### Install from PyPI

```bash
pip install khavis
```

### Install from source

```bash
git clone https://github.com/kiddhsu5/K.H.A.V.I.S..git
cd khavis
pip install -e .
```

### Docker

```bash
docker pull kiddhsu/khavis:0.1.0
docker run -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/audit:/app/audit \
  --env-file .env \
  kiddhsu/khavis:0.1.0
```

### Config schema (`config/pools.yaml`)

```yaml
pools:
  - name: "<display name>"
    provider_id: "<plugin class id>"
    endpoint: "<override or default>"
    model: "<default model>"
    env_key: "<env var holding the API key>"
```

All fields except `name` are optional; the plugin's defaults fill in the rest.

### Config schema (`config/capabilities.yaml`)

```yaml
capabilities:
  - capability: "<tag string>"
    pools:
      - "<pool name from pools.yaml>"
      - ...
    weight: 1.0   # used by the weighted-random selection
```

`weight` defaults to 1.0. A pool at weight 1.2 is roughly 20% more likely to be picked than a peer at weight 1.0.

### CLI reference

```
khavis init                  # scaffold a config in the current dir
khavis serve                 # start the HTTP daemon (default :8080)
khavis serve --port 9000     # custom port
khavis new-provider <name>   # scaffold a new plugin file
khavis audit                 # pretty-print the audit log
khavis audit --since 24h     # last 24 hours only
khavis audit --pool GLM-5.3  # filter by pool
khavis doctor                # run health + quota checks, print a table
```

### HTTP API

```
POST /v1/chat            # chat completion, OpenAI-compatible response
POST /v1/embeddings      # embeddings (alpha)
GET  /v1/pools           # list pools + health + quota
GET  /v1/capabilities    # list capability → pool mappings
GET  /healthz            # liveness probe
```

`/v1/chat` accepts an OpenAI-shaped request body plus an optional `capability` field:

```json
{
  "capability": "code",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.2,
  "stream": false
}
```

If `capability` is omitted, the router picks a default (`推理`).

### Troubleshooting

**"All my pools are unhealthy."**
Run `khavis doctor`. It prints a table with each pool's health, endpoint, key presence, and last error. The most common cause is a missing key in `.env`.

**"I want pool X to never be picked."**
Comment it out of the relevant capability in `capabilities.yaml`, or set its weight to `0.0`.

**"Hot reload isn't picking up my changes."**
The daemon watches both `config/*.yaml` and `providers/*.py` and reloads them in-process. If you don't see changes within ~2 seconds, check `audit/doctor.log`.

**"I want a different failover strategy."**
`Router.chat(..., strategy="weighted|round_robin|random")` lets you override per-request.

**"I want to log to a different place."**
Set `KHAVIS_AUDIT_DIR=/var/log/khavis` in the environment.

**"I want a web UI."**
v0.3 has one on the roadmap. For now, `tail -F audit/requests.jsonl | jq` is the spiritual equivalent.

---

## Closing

I built K.H.A.V.I.S. because I was tired of being the air traffic controller for my own subscriptions at 11:47 PM on a Tuesday.

If that resonates, please [star the repo](https://github.com/kiddhsu5/K.H.A.V.I.S.), open an issue, send a PR, or just send me an email telling me what you built on top of it. This project will get better only if real people use it and tell me what's wrong.

— kiddhsu5, 2026-09-20

> "The combined headroom across all of our subscriptions is enormous. The problem is not capacity. The problem is that we are playing air traffic controller for our own APIs at midnight."