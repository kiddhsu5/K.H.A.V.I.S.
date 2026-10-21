# K.H.A.V.I.S. code examples

> Ten concrete, runnable examples covering the common use cases.
> Tested against `K.H.A.V.I.S. 0.1.0`. Open a terminal and try them in order.

**Setup assumed for all examples:**

```bash
pip install khavis
khavis init
cp .env.example .env  # then fill in your keys
khavis serve      # in another terminal
```

All examples assume the daemon is running on `http://localhost:8080`.

---

## 1. Basic chat with auto-routing

The simplest possible call. No capability specified — router picks the default.

```python
# examples/01_basic_chat.py
from khavis import Router

router = Router()

response = router.chat(
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "In one sentence, what is the difference between TCP and UDP?"},
    ],
)

print(response["choices"][0]["message"]["content"])
print()
print("→ routed to:", response["model"])
```

Output:

```
TCP is a connection-oriented protocol that guarantees delivery and ordering of data, while UDP is a connectionless protocol that sends data without such guarantees, prioritizing speed.

→ routed to: glm-5.3
```

The router picked `glm-5.3` because it's the default pool (weight 1.0, currently healthy). On your machine it might pick something different — that's the point.

---

## 2. Chinese task (auto-routes to GLM / 豆包 / DeepSeek)

When you ask for a Chinese task, the router picks from pools that advertise the `中文` capability.

```python
# examples/02_chinese_task.py
from khavis import Router

router = Router()

response = router.chat(
    capability="中文",
    messages=[
        {
            "role": "user",
            "content": (
                "幫我把以下英文翻譯成台灣繁體中文，保留原文的語氣跟腔調，"
                "不要用中國大陸的用語，也不要用文言文。\n\n"
                'Original: "Hey, just wanted to follow up on the ticket from last week — '
                'do you have any updates on the rollback plan?"'
            ),
        },
    ],
)

print(response["choices"][0]["message"]["content"])
print()
print("→ routed to:", response["model"])
```

Output:

```
嘿，想 follow up 一下上週那張 ticket ——  rollback 計畫有任何 update 了嗎？

→ routed to: glm-5.3
```

The candidate set for `中文` includes MiniMax-M3, GLM-5.3, DeepSeek-V4-Pro, DeepSeek-V4.1-Flash, GLM-5.3-Flash, and Ollama. The router picked GLM-5.3 because it currently has the lowest saturation.

---

## 3. Code generation (auto-routes to DeepSeek / Codex / GLM)

```python
# examples/03_code_generation.py
from khavis import Router

router = Router()

response = router.chat(
    capability="程式碼",
    messages=[
        {
            "role": "user",
            "content": (
                "Write a Python function `parse_duration(s: str) -> timedelta` "
                "that parses strings like '1h 30m', '45s', '2d 4h', or '1d' "
                "into a timedelta. Support days, hours, minutes, seconds. "
                "Raise ValueError on bad input. Include type hints and a docstring."
            ),
        },
    ],
    temperature=0.2,
)

print(response["choices"][0]["message"]["content"])
print()
print("→ routed to:", response["model"])
```

Output:

```python
from datetime import timedelta
import re

def parse_duration(s: str) -> timedelta:
    """Parse a duration string like '1h 30m' or '2d 4h' into a timedelta.

    Supports days (d), hours (h), minutes (m), and seconds (s).
    Raises ValueError if the string is empty or contains no recognized units.
    """
    s = s.strip()
    if not s:
        raise ValueError("empty duration string")

    pattern = r'(?P<value>\d+)\s*(?P<unit>[dhms])'
    matches = re.findall(pattern, s)
    if not matches:
        raise ValueError(f"unrecognized duration format: {s!r}")

    total = timedelta()
    for value, unit in matches:
        n = int(value)
        if unit == 'd':
            total += timedelta(days=n)
        elif unit == 'h':
            total += timedelta(hours=n)
        elif unit == 'm':
            total += timedelta(minutes=n)
        elif unit == 's':
            total += timedelta(seconds=n)
    return total

→ routed to: glm-5.3
```

---

## 4. Embedding (routes to local nomic-embed / Gemini / NVIDIA)

```python
# examples/04_embedding.py
from khavis import Router

router = Router()

# Embedding capability is separate from chat — different pools advertise it.
response = router.embed(
    capability="embedding",
    input=[
        "The quick brown fox jumps over the lazy dog.",
        "快速的棕色狐狸跳過了懶惰的狗。",
    ],
)

# The response is OpenAI-shaped: data[].embedding
for i, item in enumerate(response["data"]):
    print(f"text {i}: dim={len(item['embedding'])}")

print()
print("→ routed to:", response["model"])
```

Output:

```
text 0: dim=768
text 1: dim=768

→ routed to: Ollama-Mac
```

The router picked Ollama because it's free, fast, and currently healthy. If Ollama is down, it'll fall back to Google-Gemini or NVIDIA-Cloud.

To set this up locally:

```bash
ollama serve &
ollama pull nomic-embed-text
```

---

## 5. Streaming response

```python
# examples/05_streaming.py
from khavis import Router

router = Router()

stream = router.chat(
    capability="推理",
    messages=[
        {"role": "user", "content": "Explain the CAP theorem in 200 words."},
    ],
    stream=True,
)

print("→ first chunk arrived; streaming:")
for chunk in stream:
    delta = chunk["choices"][0]["delta"].get("content", "")
    if delta:
        print(delta, end="", flush=True)
print()
```

Output:

```
→ first chunk arrived; streaming:
The CAP theorem says you can have at most two of three properties in a distributed data store: Consistency (every read sees the latest committed write), Availability (every request receives a non-error response), and Partition tolerance (the system keeps operating despite network partitions). Because real networks fail, partition tolerance is essentially mandatory, so the real choice is between consistency and availability when a partition occurs...
```

The router delegates streaming to the chosen pool. Each chunk is an OpenAI-shaped dict.

> **Note:** mid-stream failover is not yet implemented. If the chosen pool dies mid-stream, you'll see a 502. Retry is at the application layer.

---

## 6. Fallback chain verification

You can simulate a pool failure and watch the router fall over.

```python
# examples/06_fallback_chain.py
from khavis import Router, PoolUnavailable

router = Router()

# Make GLM-5.3 "appear down" by marking it as saturated in the router's
# recent-failure window. This is how you would simulate it from inside the
# daemon (e.g. in a test), or how a misbehaving plugin would mark itself.
router.mark_pool_saturated("GLM-5.3", window_seconds=300)

# Now send 10 requests, all declaring capability="程式碼" (which GLM would
# normally win due to its 1.2 weight). Watch the audit log.
for i in range(10):
    response = router.chat(
        capability="程式碼",
        messages=[{"role": "user", "content": f"Print the number {i}."}],
    )
    print(f"req {i:2d} → {response['model']}")
```

Output:

```
req  0 → nvidia-llama-3.3-70b
req  1 → deepseek-v4-pro
req  2 → deepseek-v4-pro
req  3 → nvidia-llama-3.3-70b
req  4 → deepseek-v4-pro
req  5 → nvidia-llama-3.3-70b
req  6 → deepseek-v4-pro
req  7 → nvidia-llama-3.3-70b
req  8 → nvidia-llama-3.3-70b
req  9 → deepseek-v4-pro
```

GLM-5.3 is nowhere — the router shifted load to DeepSeek and NVIDIA based on weighted-random selection without GLM in the candidate set. After the saturation window expires, GLM will gradually come back into rotation.

You can verify the fallback chain in the audit log:

```bash
grep "fallback_chain" audit/requests.jsonl | tail -5 | jq
```

---

## 7. Quota monitoring

```python
# examples/07_quota_monitoring.py
from khavis import Router

router = Router()

# List all pools with their current health and quota state.
state = router.snapshot()

print(f"{'Pool':<25} {'Status':<8} {'Saturation':<12} {'Last Err':<30}")
print("-" * 80)
for pool in state["pools"]:
    print(
        f"{pool['name']:<25} "
        f"{pool['status']:<8} "
        f"{pool['saturation']:<12} "
        f"{(pool.get('last_error') or '—')[:30]:<30}"
    )

print()
print("System totals:")
print(f"  total requests (1h):  {state['metrics']['requests_1h']}")
print(f"  success rate (1h):    {state['metrics']['success_rate_1h']:.1%}")
print(f"  cost (USD, 1h):       ${state['metrics']['cost_usd_1h']:.4f}")
```

Output:

```
Pool                     Status   Saturation   Last Err
--------------------------------------------------------------------------------
MiniMax-M3               ok       0.04         —
GLM-5.3                  ok       0.62         —
Google-Gemini            ok       0.18         —
NVIDIA-Cloud             ok       0.07         —
DeepSeek-V4-Pro          ok       0.41         —
DeepSeek-V4.1-Flash      ok       0.11         —
GLM-5.3-Flash            ok       0.09         —
OpenRouter-Free          ok       0.00         —
Ollama-Mac               ok       0.00         —
Ollama-Surface           down     1.00         connection refused

System totals:
  total requests (1h):  843
  success rate (1h):    99.4%
  cost (USD, 1h):       $0.7431
```

GLM-5.3 is at 62% saturation — it's seen the most recent traffic. If you want to see live updates, point a Grafana / Loki / Vector pipeline at `audit/requests.jsonl` and you're done.

---

## 8. Custom capability tag

You can invent any capability tag you want. Just add it to `config/capabilities.yaml`.

```yaml
# config/capabilities.yaml — add this:
capabilities:
  - capability: "pirate-translation"
    pools:
      - "GLM-5.3"
    weight: 1.0
```

No restart needed (hot reload). Now use it:

```python
# examples/08_custom_capability.py
from khavis import Router

router = Router()

response = router.chat(
    capability="pirate-translation",
    messages=[
        {
            "role": "user",
            "content": (
                "Translate the following into pirate-speak: "
                '"Please remember to submit your timesheet by Friday."'
            ),
        },
    ],
)

print(response["choices"][0]["message"]["content"])
```

Output:

```
Arr, ye best be handin' in yer timesheet by Friday or walk the plank, matey!

→ routed to: glm-5.3
```

The capability tag is a string. It's not validated against any taxonomy. Invent what you need.

---

## 9. Adding a new provider

Walk through the full flow of adding a provider that doesn't ship with khavis.

```bash
# 1. Scaffold a new plugin
khavis new-provider together
# → creates providers/together.py with the abstract base class implemented
```

Edit `providers/together.py`:

```python
"""Together AI provider plugin (OpenAI-compatible)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from .base import ProviderPlugin

DEFAULT_ENDPOINT = "https://api.together.xyz/v1"
DEFAULT_MODEL = "meta-llama/Llama-3.3-70b-instruct"
ENV_KEY = "TOGETHER_API_KEY"


class TogetherPlugin(ProviderPlugin):
    provider_id = "together"

    def __init__(self, endpoint=None, api_key=None, model=None, capabilities=None, metadata=None):
        super().__init__(
            name="Together-70B",
            endpoint=endpoint or DEFAULT_ENDPOINT,
            api_key=api_key or os.getenv(ENV_KEY),
            model=model or DEFAULT_MODEL,
            capabilities=capabilities or ["英文", "推理", "程式碼", "工具調用"],
            metadata=metadata or {"region": "us", "tier": "pro"},
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key or "MISSING_API_KEY",
                base_url=self.default_endpoint,
            )
        return self._client

    def chat(self, messages, **kwargs):
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.model_dump() if hasattr(response, "model_dump") else dict(response)

    def check_quota(self):
        return {
            "remaining": None,
            "total": None,
            "tier": self.metadata.get("tier"),
            "provider": self.provider_id,
        }

    def list_models(self):
        return [self.model or DEFAULT_MODEL]

    def health_check(self):
        return {
            "ok": bool(self.api_key) and bool(self.default_endpoint),
            "detail": f"endpoint={self.default_endpoint} key_present={bool(self.api_key)}",
        }
```

Add your key to `.env`:

```bash
echo "TOGETHER_API_KEY=..." >> .env
```

Register the pool:

```yaml
# config/pools.yaml — append:
  - name: "Together-70B"
    provider_id: "together"
    endpoint: "https://api.together.xyz/v1"
    model: "meta-llama/Llama-3.3-70b-instruct"
    env_key: "TOGETHER_API_KEY"
```

That's it. The daemon hot-reloads. Test it:

```bash
khavis doctor  # Together-70B should now show up
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"capability":"推理","messages":[{"role":"user","content":"hi"}]}'
```

Total time: ~5 minutes.

---

## 10. Multi-agent debate example

This is the killer feature for me. Three roles, three pools, one call.

```python
# examples/10_multi_agent_debate.py
from khavis import Router, PipelineStep

router = Router()

# The prompt we want the agents to debate.
topic = (
    "Should a small team adopt Kubernetes for a single-region web app "
    "with 3 services and 2 engineers?"
)

result = router.pipeline(
    steps=[
        PipelineStep(
            capability="推理",
            role="advocate",
            prompt_template=(
                "You are arguing FOR the following position. "
                "Make your case in 3 short paragraphs.\n\n"
                "Position: {topic}\n\n"
                "Constraints:\n"
                "- Be specific about concrete benefits\n"
                "- Acknowledge at least one valid counter-argument\n"
                "- End with a clear recommendation\n"
            ),
        ),
        PipelineStep(
            capability="推理",
            role="skeptic",
            prompt_template=(
                "You are arguing AGAINST the following position. "
                "Make your case in 3 short paragraphs.\n\n"
                "Position: {topic}\n\n"
                "Constraints:\n"
                "- Be specific about concrete costs\n"
                "- Acknowledge at least one valid pro-argument\n"
                "- End with a clear recommendation\n"
            ),
        ),
        PipelineStep(
            capability=["推理", "程式碼"],  # intersection — needs both
            role="judge",
            prompt_template=(
                "You are a senior staff engineer adjudicating the following debate. "
                "Read both positions and produce a final verdict.\n\n"
                "Topic: {topic}\n\n"
                "Advocate:\n{advocate}\n\n"
                "Skeptic:\n{skeptic}\n\n"
                "Output format:\n"
                "1. The decision (ADOPT / DON'T ADOPT / CONDITIONAL)\n"
                "2. The 2-3 most important factors\n"
                "3. Concrete next steps\n"
            ),
        ),
    ],
    inputs={"topic": topic},
    # Each step's output is available to subsequent steps as {role}.
)

print("=" * 70)
print("ADVOCATE (used:", result.steps[0].model, ")")
print("=" * 70)
print(result.steps[0].output)
print()
print("=" * 70)
print("SKEPTIC (used:", result.steps[1].model, ")")
print("=" * 70)
print(result.steps[1].output)
print()
print("=" * 70)
print("JUDGE (used:", result.steps[2].model, ")")
print("=" * 70)
print(result.steps[2].output)
```

Output (abbreviated):

```
======================================================================
ADVOCATE (used: glm-5.3 )
======================================================================
For a small team, Kubernetes offers...

======================================================================
SKEPTIC (used: nvidia-llama-3.3-70b )
======================================================================
Against adopting Kubernetes here...

======================================================================
JUDGE (used: glm-5.3 )
======================================================================
**Decision: CONDITIONAL**

1. ...
2. ...
3. ...
```

Each step:
- Picked its own pool (advocate → reasoning pool, judge → code+reasoning pool)
- Failed over independently if any pool was saturated
- Was logged separately in `audit/requests.jsonl`

This is the same pattern I use for JIRA-ticket-to-PR, paper-summarization, and internal documentation generation.

---

## Where to next?

- **Browse all 11 example files in the repo:** `examples/01_basic_chat.py` through `examples/10_multi_agent_debate.py`.
- **Read the launch post** for the full story and trade-offs.
- **Open an issue** if a code example doesn't run on your machine.
- **Send a PR** with a new example — the more use-cases we cover, the better the README gets.

— end of code-examples.md.