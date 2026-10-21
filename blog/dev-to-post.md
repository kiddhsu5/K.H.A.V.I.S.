# How to Stop Fighting Your LLM Subscriptions

> A hands-on tutorial for setting up K.H.A.V.I.S. on your laptop in 10 minutes.

![cover-image-placeholder — three browser tabs, each showing a different LLM dashboard with a red 429 indicator. Replace with a real screenshot when publishing.]

**By kiddhsu5 · 8 min read · Tutorial · Python · LLMs · Open Source**

---

## Who this is for

You pay for at least two LLM subscriptions. Maybe ChatGPT Plus + Cursor Pro + GLM Coding. Maybe Gemini free + Ollama local + DeepSeek. Maybe you're a solo developer in Taiwan juggling GLM and Qwen and 豆包.

And you're tired of:

- Hitting quota walls at 11 PM.
- Writing the same `if provider == "openai"` chain in every project.
- Paying 5% markup to a routing gateway that doesn't even know about your ChatGPT Plus.
- Not knowing which model you actually spent the most money on.

This tutorial walks you through installing **K.H.A.V.I.S.** — an open-source, Apache 2.0 router that treats your subscriptions as one capability-tagged pool — and using it from your Python code.

By the end, you'll have:

- K.H.A.V.I.S. running locally on `:8080`
- 10 providers registered (12 in the latest release, including OpenAI + Claude BYOK)
- Your code saying *what it wants* (e.g. `capability="中文"`) instead of *which provider* to use
- A JSONL audit log of every request

No prior routing experience needed. Some Python and command-line comfort assumed.

---

## Prerequisites

- Python 3.11 or newer
- At least one LLM API key (OpenAI, Gemini, GLM, etc.) — more is better, but one is enough to start
- 10 minutes
- A terminal

Optional but nice:

- Docker (for the containerized install)
- Ollama installed locally with at least one model pulled (`ollama pull gemma4:e2b` is a good default)

---

## Step 1 — Install

```bash
pip install khavis
```

Verify:

```bash
khavis --version
# khavis 0.1.0
```

If you prefer Docker:

```bash
docker pull kiddhsu/khavis:0.1.0
```

(We'll come back to Docker in Step 6.)

---

## Step 2 — Scaffold a config

```bash
mkdir khavis-demo
cd khavis-demo
khavis init
```

You should see:

```
Created config/capabilities.yaml
Created config/pools.yaml
Created providers/   (auto-discovered from package)
Created audit/       (request logs will land here)
Created .env.example (copy to .env and fill in)
```

Your directory now looks like:

```
.
├── config/
│   ├── capabilities.yaml
│   └── pools.yaml
├── providers/          (auto-discovered; you don't need to touch this)
├── audit/
└── .env.example
```

---

## Step 3 — Add your API keys

```bash
cp .env.example .env
```

Open `.env` in your editor. It should look like:

```bash
# .env — DO NOT COMMIT THIS FILE
ZHIPUAI_API_KEY=
GOOGLE_API_KEY=
BYTEDANCE_API_KEY=
NVIDIA_API_KEY=
OPENROUTER_API_KEY=
```

Fill in any keys you have. Leave the rest blank — the router will mark those pools as `unhealthy` until you add a key, but they won't break anything.

> **Important:** add `.env` to your `.gitignore`. The CLI does this automatically when you run `khavis init`, but double-check.

```bash
echo ".env" >> .gitignore
```

---

## Step 4 — Start the daemon

```bash
khavis serve
```

You should see:

```
2026-09-20 22:14:08 [info] khavis 0.1.0 starting
2026-09-20 16:14:08 [info] Loaded 12 pools from config/pools.yaml
2026-09-20 22:14:08 [info] Loaded 7 capabilities from config/capabilities.yaml
2026-09-20 22:14:08 [info] Health-check loop started (every 30s)
2026-09-20 22:14:08 [info] HTTP daemon listening on http://0.0.0.0:8080
```

In another terminal, run the diagnostic:

```bash
khavis doctor
```

Output:

```
Pool                Status    Key   Endpoint                                  Last Error
─────────────────────────────────────────────────────────────────────────────────────────
MiniMax-M3          ok        yes   https://api.MiniMax.chat/v1                —
GLM-5.3             ok        yes   https://open.bigmodel.cn/api/paas/v4        —
Google-Gemini       ok        yes   https://generativelanguage.googleapis.com  —
NVIDIA-Cloud        ok        yes   https://integrate.api.nvidia.com/v1        —
DeepSeek-V4-Pro     ok        yes   https://ark.cn-beijing.volces.com/api/v3   —
DeepSeek-V4.1-Flash ok        yes   https://ark.cn-beijing.volces.com/api/v3   —
GLM-5.3-Flash       ok        yes   https://ark.cn-beijing.volces.com/api/v3   —
OpenRouter-Free     ok        yes   https://openrouter.ai/api/v1               —
Ollama-Mac          down      n/a   http://localhost:11434                    connection refused
Ollama-Surface      down      n/a   http://${SURFACE_IP}:11434                unreachable
```

The two `Ollama-*` rows are `down` because Ollama isn't running on this box. That's fine — they'll come online when you `ollama serve`.

---

## Step 5 — Your first request

Open a third terminal. Try the simplest possible thing:

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Say hello in five languages."}]
  }'
```

You'll get back an OpenAI-shaped JSON response. Look at the `model` field — that's which pool the router picked. Then look at `audit/requests.jsonl`:

```bash
tail -1 audit/requests.jsonl | jq
```

```json
{
  "ts": "2026-09-20T22:14:08.412Z",
  "request_id": "9b1f-...",
  "capability": "default",
  "pool": "GLM-5.3",
  "model": "glm-5.3",
  "input_tokens": 16,
  "output_tokens": 42,
  "latency_ms": 980,
  "cost_usd": 0.00004,
  "outcome": "success",
  "fallback_chain": []
}
```

Without telling it which provider, the router picked one. Welcome to capability-based routing.

---

## Step 6 — Declare intent, not provider

The interesting bit. Replace that curl with this Python:

```python
# hello_routing.py
from khavis import Router

router = Router()  # reads config/*.yaml

# Capability: code. Router picks a pool that can do code.
r = router.chat(
    capability="程式碼",
    messages=[{"role": "user", "content": "Write a quicksort in Python."}],
)
print("Code pool picked:", r["model"])
print(r["choices"][0]["message"]["content"])
```

```bash
pip install openai   # the Router uses openai SDK under the hood for transport
python hello_routing.py
```

Output:

```
Code pool picked: glm-5.3
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    ...
```

The router saw `程式碼` in `capabilities.yaml`, found three candidate pools (GLM-5.3, DeepSeek-V4-Pro, NVIDIA-Cloud), checked their health, and picked one. With weighted randomness, GLM-5.3 has weight 1.2 (it gets picked slightly more often).

Try a Chinese task:

```python
r = router.chat(
    capability="中文",
    messages=[{"role": "user", "content": "幫我把這段翻譯成台灣繁體中文。Hello, world."}],
)
print("Chinese pool picked:", r["model"])
print(r["choices"][0]["message"]["content"])
```

You should see one of: MiniMax-M3, GLM-5.3, DeepSeek-V4-Pro, GLM-5.3-Flash, or Ollama.

---

## Step 7 — Multi-capability requests

Sometimes you want "fast Chinese + good reasoning". The router supports that:

```python
r = router.chat(
    capabilities=["中文", "推理", "速度優先"],
    messages=[{"role": "user", "content": "用一句話解釋量子纠缠。"}],
)
print(r["model"])
```

The candidate set is the *intersection* of all three capability lists. If you only have one pool that does all three, that's the one you'll get.

---

## Step 8 — Streaming

Add `stream=True`:

```python
stream = router.chat(
    capability="程式碼",
    messages=[{"role": "user", "content": "Write a linked list in Rust."}],
    stream=True,
)

for chunk in stream:
    delta = chunk["choices"][0]["delta"].get("content", "")
    print(delta, end="", flush=True)
print()
```

The router delegates streaming to the underlying pool. Each chunk is one dict; `delta.content` is the new text.

> **Note:** mid-stream failover is not yet implemented. If the chosen pool dies mid-stream, you'll see a 502; retry is at the application layer. PRs welcome.

---

## Step 9 — Multi-agent pipeline

The killer feature for me. A planner → translator → critic pipeline:

```python
from khavis import Router, PipelineStep

router = Router()

result = router.pipeline(
    steps=[
        PipelineStep(
            capability="推理",
            role="planner",
            prompt_template=("Read this abstract and produce a 3-bullet outline.\n\n{{input}}"),
        ),
        PipelineStep(
            capabilities=["中文", "推理"],
            role="translator",
            prompt_template=("Translate the following outline to Taiwan Mandarin.\n\n{{input}}"),
        ),
        PipelineStep(
            capabilities=["程式碼", "推理"],
            role="critic",
            prompt_template=("Identify any factual errors in this outline.\n\n{{input}}"),
        ),
    ],
    input="""Recent advances in transformer architectures have demonstrated
    emergent in-context learning capabilities when model scale exceeds
    certain threshold parameters...""",
)

print("Planner used:", result.steps[0].model)
print("Translator used:", result.steps[1].model)
print("Critic used:", result.steps[2].model)
print("\nFinal output:")
print(result.output)
```

Each step picks its own pool. Each step is logged independently. Each step can fail over independently. The whole thing is one Python call.

---

## Step 10 — Docker

If you prefer containers:

```bash
docker run -d \
  --name khavis \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/audit:/app/audit \
  --env-file .env \
  kiddhsu/khavis:0.1.0
```

Check logs:

```bash
docker logs -f khavis
```

Stop:

```bash
docker stop khavis
```

---

## What's next?

You now have K.H.A.V.I.S. running. A few things to try:

1. **Stress test it.** Send 1,000 requests with `capability` randomly chosen and watch the audit log. You'll see failover in action.

2. **Add a custom capability.** Edit `config/capabilities.yaml`:
   ```yaml
   - capability: "vision"
     pools:
       - "Google-Gemini"
     weight: 1.0
   ```
   Save. The daemon hot-reloads. No restart.

3. **Plug in Ollama locally.**
   ```bash
   ollama serve &
   ollama pull gemma4:e2b
   ```
   `Ollama-Mac` flips from `down` to `ok` in your next `doctor` run. Now your `local` requests don't even leave the machine.

4. **Read the audit log.**
   ```bash
   tail -f audit/requests.jsonl | jq
   ```
   This is your new "single pane of glass" for LLM spend.

5. **Add a plugin.** Want a provider I haven't shipped? `khavis new-provider yourprovider` scaffolds it. About 80 lines.

6. **Star the repo.** It genuinely helps: https://github.com/kiddhsu5/K.H.A.V.I.S.

---

## Troubleshooting

**The daemon won't start.**
- Run `khavis doctor` to see which pools are misconfigured.
- Check that `config/pools.yaml` is valid YAML.
- Make sure you ran `khavis init` in the directory you're serving from.

**All my pools show `unhealthy`.**
- Most likely: missing keys in `.env`. The daemon does not crash, it just marks the pool `unhealthy` until you add a key.
- Run `khavis doctor --verbose` for the actual error.

**Hot reload isn't picking up my changes.**
- The daemon watches both `config/*.yaml` and `providers/*.py`.
- If you change a `.py` file, the plugin is re-imported in-process. Some edge cases (e.g. renamed classes) require a full restart.
- If you change `.env`, you must restart the daemon.

**I want to disable a pool.**
- Comment it out of the `pools` list in `capabilities.yaml` for the relevant capability, **or** set its `weight: 0.0`, **or** comment out the entire entry in `pools.yaml`.

**I want a web UI.**
- v0.3 has one on the roadmap. For now, `tail -F audit/requests.jsonl | jq` is the spiritual equivalent. A community PR would be very welcome.

---

## Where to learn more

- **README** — https://github.com/kiddhsu5/K.H.A.V.I.S.
- **Architecture doc** — https://github.com/kiddhsu5/K.H.A.V.I.S./blob/main/docs/ARCHITECTURE.md
- **Plugin contract** — https://github.com/kiddhsu5/K.H.A.V.I.S./blob/main/providers/base.py
- **Roadmap** — in the launch blog post
- **Issues & discussions** — https://github.com/kiddhsu5/K.H.A.V.I.S./issues

---

## Closing

K.H.A.V.I.S. is small (1,400 lines of core, 12 ~80-line plugins), boring (YAML config, JSONL logs, in-process state), and opinionated (capability tags, BYOK, local-first).

If you've been writing `if provider == "openai"` chains in every project, give it 10 minutes. You might save yourself 11 PM on a Tuesday.

— kiddhsu5, 2026-09-20