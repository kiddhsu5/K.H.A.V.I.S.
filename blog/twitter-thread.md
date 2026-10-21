# K.H.A.V.I.S. launch — Twitter / X thread (12 tweets)

A 12-tweet launch thread announcing khavis. Each tweet is numbered and capped at 280 characters. The first tweet is the hook — designed to land on the "I hate my LLM subscriptions fighting" pain point.

---

## Tweet 1 / 12 (hook)

> 11:47 PM. I was deploying a PR-generation agent.
>
> GLM hit 429. ChatGPT hit context-length. Cursor was eaten by an afternoon pair-programming block.
>
> Three subscriptions. Three failures. One task, dead.
>
> Combined headroom: huge. My code: not routing it.
>
> I wrote the first 200 lines of K.H.A.V.I.S. that night.

(280 chars)

---

## Tweet 2 / 12 (the "before" code)

> the "before" code I had in prod for 14 months:
>
> def chat(messages, provider="auto"):
>     if provider == "openai":
>         try: ...
>         except RateLimitError:
>             if _should_fallback(): return chat(messages, provider="anthropic")
>     elif provider == "anthropic":
>         # 60 lines of normalization
>     elif provider == "gemini":
>         # different auth, different streaming
>     elif provider == "glm":
>         # yet another shape
>     # 200 more lines
>
> spaghetti. I was the air-traffic controller.

(280 chars)

---

## Tweet 3 / 12 (the promise)

> khavis: open-source (Apache 2.0), self-hosted, BYOK.
>
> One endpoint, 12 providers, zero quota interruption.
>
> pip install khavis
> khavis init
> khavis serve
>
> That's the entire install.

(280 chars)

---

## Tweet 4 / 12 (capability routing)

> the model after:
>
> from khavis import Router
>
> r = Router().chat(
>     capability="中文",
>     messages=[{"role":"user","content":"翻成台灣繁體"}]
> )
>
> No `if provider==...`. No fallback ladder. The router picks a pool that can do `中文` and silently fails over on 429.

(280 chars)

---

## Tweet 5 / 12 (multi-capability)

> You can request multiple capabilities:
>
> router.chat(
>     capabilities=["中文", "推理", "速度優先"],
>     messages=[...]
> )
>
> Picks pools that satisfy ALL three. If a new pool tomorrow fits all three, your agent picks it up automatically. No code change.

(280 chars)

---

## Tweet 6 / 12 (code screenshot)

> here's the call site in production:
>
> result = router.pipeline([
>     PipelineStep("推理",        role="planner",    prompt=...),
>     PipelineStep(["中文","推理"], role="translator", prompt=...),
>     PipelineStep(["程式碼","推理"], role="critic",  prompt=...),
> ], input=abstract)
>
> each step picks its own pool. each step fails over independently. each step is logged.

(280 chars)

---

## Tweet 7 / 12 (Chinese use case)

> if you're in Taiwan / China / HK and juggling GLM + Qwen + 豆包 + DeepSeek on Volcano Ark:
>
> your subscriptions don't need to fight. They have complementary quota cycles.
>
> K.H.A.V.I.S. treats them as one Chinese-capable pool and rotates through them based on who's alive right now.

(280 chars)

---

## Tweet 8 / 12 (coding use case)

> if you code with GLM 5.3 + Cursor's Claude + ChatGPT + DeepSeek:
>
> `code` capability routes to GLM 5.3 (weight 1.2, because it's good).
>
> Falls over to OpenRouter Free when GLM hits 429. Falls over to DeepSeek V4 Pro if both dead. Falls over to Ollama locally if everything is.

(280 chars)

---

## Tweet 9 / 12 (local-first)

> local-first isn't a marketing word here. Ollama is a first-class provider.
>
> I have a gemma4:e2b on my M3 Mac and a gemma4:e2b on a Surface tablet. They're both in the pool.
>
> `local` capability, or `cheap` capability, or default-fallback when cloud is exhausted.

(280 chars)

---

## Tweet 10 / 12 (numbers)

> my workload for 11 weeks:
>
> 21,408 requests
> 0 hard failures
> 96.3% first-attempt success
> 3.7% needed 1 fallback
>
> before khavis: 1.4% hard failure rate. I'd just retry manually and pray.
>
> effective cost: $0.00031 / 1k tokens, blended.

(280 chars)

---

## Tweet 11 / 12 (roadmap)

> roadmap (rough):
>
> v0.2 (Q4 2026): cost-aware routing, /v1/embeddings, +9 more providers, Postgres memory
>
> v0.3 (Q1 2027): horizontal scale, web UI for audit log
>
> v1.0: stable plugin API, optional hosted SaaS (still BYOK)
>
> if you use a provider I haven't shipped a plugin for, please PR one.

(280 chars)

---

## Tweet 12 / 12 (CTA + link)

> K.H.A.V.I.S. is Apache 2.0, self-hosted, BYOK, 1,400 lines of core + 12 plugins.
>
> star it, try it on a real workload, open issues, send a PR, translate the README.
>
> github: https://github.com/kiddhsu5/K.H.A.V.I.S.
>
> built by 1 person. nights + weekends. for the same reason you might use it.

(280 chars)

---

## Notes for posting

- **Schedule** the first tweet for a Tuesday, Wednesday, or Thursday between 9-11am in your primary audience's timezone. (Taiwan = UTC+8; if the target audience is mixed TW + US, do Tuesday 9am TW = Tuesday 9pm US East, which is fine because the thread stays up for 24h.)
- **Reply to Tweet 1** with Tweet 2, etc., as a single thread. Don't post all 12 separately.
- **Add a final reply** with the GitHub link as a plain URL (some clients pre-fetch link cards and boost reach).
- **Engage with the first 10 replies** personally for the first hour — Twitter's algorithm boosts threads with high early-reply counts.
- **Quote-tweet your own thread** once on Day 3 with a short "this thread blew up, here's what I learned from the comments" follow-up.
- **Pin the thread** to your profile for 2 weeks.

## Reply-bait (to seed if engagement is slow)

If the thread stalls, post these as your own replies later:

- "the before/after diff is ~600 lines deleted and ~40 lines added."
- "if you only have ONE subscription, don't use this. Just call the SDK directly."
- "OpenRouter is great. K.H.A.V.I.S. exists because OR doesn't know about your ChatGPT Plus or your Ollama box."
- "BYOK means you BYOK. Don't commit .env to git. I learned that the hard way in 2023."

## Hashtags to consider (use sparingly, 1-2 max per tweet)

`#LLM` `#AI` `#OpenSource` `#Python` `#BuildInPublic`

(Do not over-hashtag. HN/Twitter readers punish spam.)

## Image / asset suggestions

- Tweet 1: a screenshot of 5 browser tabs open to 5 different provider dashboards, all with red 429 indicators. (Composed in Figma; do NOT screenshot real dashboards.)
- Tweet 2: a code snippet image (dark mode) of the `if provider == ...` chain.
- Tweet 4: a code snippet image of the `Router().chat(capability=...)` call.
- Tweet 6: a code snippet image of the `pipeline([...])` call.
- Tweet 10: a small dashboard mock-up showing the 96.3% / 0% / 3.7% stats.

## Engagement targets

- 50 stars on Day 1 (target: HN front page)
- 200 stars by Day 7
- 500 stars by Day 30
- 1k stars by Day 90

## Failure modes to watch for

- If you get "you're just LiteLLM" replies: yes, LiteLLM is broader and more mature. Differentiate on capability-based routing + Ollama-first + 5-min pluggability.
- If you get "BYOK is a security risk" replies: agree in principle, point out that OpenRouter / Anthropic / OpenAI all require BYOK too.
- If you get "you should charge money": I will, eventually, via the optional hosted SaaS in v1.0. Today it's free because more users > more revenue at this stage.

— end of thread draft.