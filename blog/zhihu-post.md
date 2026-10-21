# 我寫了 K.H.A.V.I.S.，因為我受夠了我的 LLM 訂閱互相打架

> **一個 endpoint，串接 12 個 LLM provider（其中 4 個 BYOK），零 quota 中斷。**
> Apache 2.0 · 自架 · BYOK · 可插拔 (pluggable)

**作者：** kiddhsu5 · **發布日期：** 2026-09-20 · **閱讀時間：** ~25 分鐘 · **先講故事，再上 code。**

---

## 目錄

1. [那個差點讓我 deploy 失敗的夜晚](#那個差點讓我-deploy-失敗的夜晚)
2. [我反覆撞到的四個痛點](#我反覆撞到的四個痛點)
3. [我想要的東西（以及我做出來的東西）](#我想要的東西以及我做出來的東西)
4. [30 秒上手](#30-秒上手)
5. [六層架構怎麼拼起來](#六層架構怎麼拼起來)
6. [Capability-based routing，用 code 講清楚](#capability-based-routing用-code-講清楚)
7. [5 分鐘自己加一個 provider](#5-分鐘自己加一個-provider)
8. [真實 benchmark（連同誠實的 caveat）](#真實-benchmark連同誠實的-caveat)
9. [取捨 — 這個東西「不是」什麼](#取捨--這個東西不是什麼)
10. [Roadmap](#roadmap)
11. [你可以怎麼幫忙](#你可以怎麼幫忙)
12. [附錄：安裝、設定、疑難排解](#附錄安裝設定疑難排解)

---

## 那個差點讓我 deploy 失敗的夜晚

週二晚上 11:47。我在跑一個 deploy script——一個多步驟的 agentic pipeline，理論上應該把一張 JIRA ticket 讀進來、生出一個 PR、然後開一個 draft。

Pipeline 跑在 GLM-5.3 上面，因為 GLM 是我用台幣付費的、我希望錢花在 GLM 上。

GLM 回 429。當然回 429。已經 11:47 PM，我這個月的「免費額度」早就用完了，3 天前才剛刷信用卡買 credits。Pipeline 死在第 4 步 (共 9 步)。

我換到 ChatGPT GO。ChatGPT GO 回了一個不一樣的 429——「context_length_exceeded」，因為我不小心把一個 stack trace 加三個 file dump 一起丟進去了。讚。

換 Claude——我透過 Cursor 付費的那個。Cursor 的 quota 被我下午 4 點的 pair-programming 吃光了。死。

換 Gemini。Gemini 可以用，但給我寫的 Flask middleware 是 Python 2 語法。

換 DeepSeek (透過火山引擎 Ark)。這個終於可以了，但我已經燒了 90 分鐘，deploy window 過了。

我坐在那邊，穿著內褲，開著五個 browser tab、三個 API dashboard、還有一份 error log。我心想：*這太荒謬了。* 我任何一個時刻都至少同時付費四個 LLM 訂閱。沒有任何一個是用滿的。在某個宇宙裡，我「合計」的可用量根本不可能答不完一個 request。問題不是 capacity。問題是我在半夜當我自己 API 的空中交通管制員。

那晚我寫了 `khavis` 的前 200 行。經過六個週末，它就是你現在看到的這個東西。

這篇文章是它的完整版——做了什麼、為什麼這樣做、你怎麼用（或者你怎麼幫忙改）。

---

## 我反覆撞到的四個痛點

### 痛點 #1：Quota wall 總在最糟的時刻出現

我不是只有一個 LLM 訂閱。我有：

- **GLM Coding Plan**（NT$300/月）—— 寫 code 用，因為 GLM 5.3 在 TypeScript 上意外地強，per-token 價格在台灣最便宜。
- **ChatGPT Plus**（US$20/月）—— 英文推理 + pair programming。
- **Cursor Pro**（US$20/月）—— 主要是因為 IDE 整合是真的，雖然我對它的 bundle pricing 很感冒。
- **Gemini API 免費額度** —— 給「丟掉也沒關係」的 request 和 embedding 用。
- **火山引擎 credits**（用 CNY 透過朋友付的）—— 給 DeepSeek 和豆包用。
- **Ollama** 跑在我的 M3 MacBook 上 —— 任何私密的東西。

不少錢。但重點是：**沒有任何一個訂閱被完全用滿。** GLM 每個月大概 20 號就見底。ChatGPT 週三就死。Cursor 週四死。Gemini 免費額度每天重置但我總是忘記規劃。火山引擎 credits 一點一點滴掉。

跨所有訂閱的合計「剩餘空間」其實很大。Router 只需要知道「現在哪一個還活著」。

### 痛點 #2：`if provider == ...` 的 boilerplate

每一家 provider 都有自己的 SDK。不同的 auth、不同 streaming protocol、不同 function-call 格式、不同 token 計算方式、不同拋 rate-limit error 的方式。

K.H.A.V.I.S. 出現之前，我 production 的 `chat()` 是這樣的（我對這段 code 沒有任何驕傲）：

```python
# 我在 production 跑了 14 個月的 code。它能跑。它很醜。
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
        # 不同的 endpoint、不同的 auth header、不同的 streaming
        ...
    elif provider == "deepseek":
        ...
    # 再 200 行
```

每一個新 model 我想加，就多 60 行 normalization。每一個 SDK breaking change 就等於一個週五晚上的除蟲之夜。每一條 fallback rule 都是特例。

### 痛點 #3：OpenRouter 的過路費

OpenRouter 很好。它把一大堆 model 集中在一個 endpoint 後面，每個 token 收一點點 markup。

那個 markup 是真的。在我 GLM-heavy 的 workload 上，OpenRouter 大概比底層 provider 貴 5%。一年下來，這是我某一個訂閱月費裡一個不算小的比例。

更糟的是：OpenRouter 不知道我的 ChatGPT Plus quota、我透過 Cursor bundle 的額度、我的本地 Ollama、或者我的 Gemini 免費額度。從 OpenRouter 的角度來看，那些都不存在。從我的角度，它們是我實際 capacity 的 60%。

我想要 OpenRouter 的 UX，但是用「我的」key 和「我的」訂閱當 routing substrate。這就是這個專案存在的唯一理由。

### 痛點 #4：我沒辦法 reasoning 成本或品質

當我問「X 用哪一個 model 最好？」我沒有真的資料。每個 provider 的 dashboard 算法不一樣。有的算 input 加 output。有的算 cached 跟 uncached。有的用 USD、有的用 CNY、有的用 credits。我的 OpenAI dashboard 說上個月花 $14；我的 GLM dashboard 說花了 89 元；我腦內模型說「大約兩頓午餐的錢」。

我想要一個地方看得到：*這個 request 打到哪個 pool、跑多久、USD 當量多少成本、有沒有成功。* K.H.A.V.I.S. 全部 log 在同一個 stream、同樣的幣別、同樣的檔案。

---

## 我想要的東西（以及我做出來的東西）

我想要的特性清單很短：

| 想要 | K.H.A.V.I.S. 的答案 |
|---|---|
| 不要 quota 中斷 | 可以—— 429 / 5xx / context overflow 時靜默 failover |
| 用我現有的 key | 可以—— BYOK、零 markup、跑在我的 box 上 |
| 輕鬆加新的 provider | 可以—— 丟一個 Python file 到 `providers/` |
| 用 intent routing，不是用名字 routing | 可以—— capability tags（`中文`、`code`、`reasoning`、`embedding`...） |
| Local-first | 可以—— Ollama 是 first-class provider |
| Open source | 可以—— Apache 2.0 |
| 看得到成本跟 latency | 可以—— 每次 request 一份結構化 audit log |
| Hot reload config | 可以—— 編輯 YAML，daemon 自己 pick up |
| Multi-agent pipeline | 可以—— planner + coder + critic 一個 call 搞定 |

我做出來的東西很小。Core 大約 1,400 行 Python、12 個 provider plugin（每個 ~80 行）、一個 HTTP daemon、和一份 YAML schema。它跑在我的 laptop、homelab NUC、CI box、和朋友的 Raspberry Pi 4 上。它撐過了 11 週的真實 production 負載，到目前為止從來沒有 drop 掉任何一個「上游本來就沒 drop」的 request。

Tagline 講完了整件事：**「一個 endpoint，串接 11+ 個 LLM provider，零 quota 中斷。」**

---

## 30 秒上手

```bash
# 1. 安裝
pip install khavis

# 2. 在當前目錄初始化一份 config
khavis init

# 3. 把你的 API keys 填進產生的 .env
echo "ZHIPUAI_API_KEY=..."        >> .env   # GLM
echo "GOOGLE_API_KEY=..."         >> .env   # Gemini
echo "BYTEDANCE_API_KEY=..."      >> .env   # 火山引擎 Ark / DeepSeek / 豆包
echo "NVIDIA_API_KEY=..."         >> .env   # NVIDIA Cloud
echo "OPENROUTER_API_KEY=..."     >> .env   # OpenRouter 免費層

# 4. 啟動 daemon（HTTP API 預設在 :8080）
khavis serve
```

這樣就好。現在打它：

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "code",
    "messages": [{"role": "user", "content": "Write a quicksort in Python."}]
  }'
```

Router 會：

1. 在 `capabilities.yaml` 找 `code`。
2. 看到一份 weighted list 的 pools，advertise `code`：GLM-5.3、DeepSeek-V4-Pro、NVIDIA-Cloud。
3. 檢查每個 pool 最近的 quota 壓力（rolling window、in-memory）。
4. 選一個 —— 目前 saturation 最低的那個。
5. 送 request、normalize 回應。
6. Log 起來。
7. 把 JSON 回給你。

如果 pool #1 回 429，request 就會落到 pool #2，你完全不會知道。你沒有寫 fallback。沒有設定 strategy。Router 自己做的。

### `khavis init` 會產出什麼

```
.
├── config/
│   ├── capabilities.yaml   # capability → pool 對應
│   └── pools.yaml          # pool 定義
├── providers/              # plug-in 目錄（auto-discovered）
│   ├── base.py
│   ├── MiniMax.py
│   ├── glm.py
│   ├── gemini.py
│   ├── nvidia.py
│   ├── volcano.py
│   ├── openrouter.py
│   └── ollama.py
├── audit/                  # JSONL log 落這裡
├── .env.example            # 填 key 進去
└── pyproject.toml
```

全部都是可以在 git 裡面 diff 的檔案。沒有 database 要 migrate。沒有 UI 要學。

---

## 六層架構怎麼拼起來

我把架構做得很無聊。我相信的每一個系統都跑在一小撮命名清楚的層上面。K.H.A.V.I.S. 有六層。

```
                         ┌────────────────────────┐
   你的 app / agent ───► │   khavis (core)    │
                         └──────────┬─────────────┘
                                    │
            ┌───────────────────────┼────────────────────────┐
            ▼                       ▼                        ▼
   ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
   │  第 1 層:      │     │   第 2 層:     │      │   第 3 層:     │
   │  Plugins       │     │   Registry     │      │   Capability   │
   │                │     │                │      │   Router       │
   └────────┬───────┘     └────────┬───────┘      └────────┬───────┘
            │                      │                       │
            ▼                      ▼                       ▼
   ┌────────────────┐     ┌────────────────┐      ┌────────────────┐
   │   第 4 層:     │     │   第 5 層:     │      │   第 6 層:     │
   │   Orchestrator │     │   Memory       │      │   Audit        │
   └────────────────┘     └────────────────┘      └────────────────┘
```

### 第 1 層 — Plugin pool

11 個 (而且還在增加) provider plugin，每個一個檔案。每個 plugin 實作同一個 4-method 介面：

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

Plugin 是唯一知道 provider quirks 的地方。這層以上全部看到一致的介面。

### 第 2 層 — Registry

Registry 掃 `providers/`、import 所有 `ProviderPlugin` 的子 class、用 `pools.yaml` 把它們 instantiate、用 name 和 capability tag 建 index。它也跑一個每 N 秒一次的 health-check loop，並且 expose `live()` / `by_capability()` API。

### 第 3 層 — Capability router

Router **不是** load balancer。它不 round-robin。也不 least-connections。它根據這幾件事挑 pool：

1. **Capability match。** 呼叫端要 `code`；只有 advertise `code` 的 pool 有資格。
2. **YAML weight。** Pool 可以加權重（例如 `code` 的 GLM weight 1.2，因為我更信任它在 code 上的表現，其他 1.0）。
3. **近期 saturation。** 一個 rolling window 追蹤每個 pool 最近的失敗和延遲。飽和的 pool 會被降權重。

就這樣。挑選策略刻意做得無聊。

### 第 4 層 — Orchestrator

這層是把一個 request 變成很多個的層。如果你叫它「debate」，orchestrator 會：

1. 叫 pool A 給一個立場。
2. 叫 pool B 給一個反方立場。
3. 叫 pool C 來裁決。
4. 回傳 C 的 verdict 加上完整逐字稿。

每一段自己挑 pool。Planner 拿 reasoning pool；coder 拿 code pool；critic 拿 critical-reasoning pool。你可以不用寫 code 就組合 pipeline—— 只要在 YAML 描述就好。

### 第 5 層 — Memory

三個 tier：

- **Working memory** —— 當下的 request，存在 process 裡。
- **Episodic memory** —— 最近的對話，存在 SQLite，per session。
- **Semantic memory** —— 長期事實，可插拔 back-end（今天是 SQLite，明天 pgvector）。

Multi-turn agent 不再忘記三步前說過什麼。

### 第 6 層 — Audit

每次 `chat()` 都寫一行 JSONL：

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

你可以 `tail -f audit/requests.jsonl` 看 router 跑。你也可以把所有讀 NDJSON 的東西接上去 —— DuckDB、`jq`、Grafana panel。

---

## Capability-based routing，用 code 講清楚

這是我最自豪的部分，因為這是我最需要的部分。

`before` 的樣子：告訴 router 用哪個 *provider*。Router 不知道你要什麼。

```python
# BEFORE — 呼叫端決定 provider
client = openai.OpenAI(api_key=OPENAI_KEY)
r = client.chat.completions.create(model="gpt-5-mini", messages=[...])
```

`after` 的樣子：告訴 router 你想「做什麼」。Router 挑能做這件事的 provider。

```python
# AFTER — 呼叫端宣告意圖
from khavis import Router

router = Router()  # 載入 config/pools.yaml + config/capabilities.yaml

r = router.chat(
    capability="中文",
    messages=[{"role": "user", "content": "幫我把這段英文翻譯成台灣繁體中文，保留語氣。"}],
)
```

那行 call 的後面發生什麼事：

1. `Router.chat("中文", messages)` 問 `CapabilityRouter` 哪些 candidate advertise `中文` 這個 capability。
2. Capability router 讀 `capabilities.yaml`，找到 7 個 pool：MiniMax-M3、GLM-5.3、DeepSeek-V4-Pro、DeepSeek-V4.1-Flash、GLM-5.3-Flash、Ollama-Mac、Ollama-Surface。
3. 檢查每個 pool 的 health（最近 60 秒的 errors、latency、quota）。
4. 跑 weighted-random selection，並對 saturation 做降權。
5. 呼叫 `plugin.chat(messages)`。
6. 如果那個 pool 拋 `RateLimitError` 或 `APIError`，就靜默 retry 下一個 candidate，最多 N 次。
7. Log 起來。

就這樣。你的 code 裡沒有 `if provider == "glm"`。也沒有 fallback ladder。Router 擁有那些複雜度；你的 code 只說它要什麼。

### 真正的贏面：capability composition

大部分時間，我不只想要「中文」。我想要「中文 + 推理」。或者「中文 + 便宜」。或者「中文 + vision + 本地」。

```python
# 多 capability request
r = router.chat(
    capabilities=["中文", "推理", "速度優先"],  # 取交集
    messages=[...],
)
```

Candidate set 是三個 capability list 的 *交集*——只有同時 advertise 三個 tag 的 pool 有資格。如果都沒 match，router 會一個一個放寬 constraint、照順序放寬，並且在 audit log 跟你說它放寬了哪個。

這讓我可以寫一個 agent 講：

> 「給我一個快的、會講中文的、會推理的 model」

......router 就從「真的同時 fit 三個 constraint」的 pool 裡挑。如果我之後加一個新的 pool 三個都會做，那個 agent 就自動 pick 它。沒有 code change。

### 一個真實例子：multi-step research task

這是我「summarize 一篇 paper」agent 實際用的 call signature：

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

每一個 step 自己挑 pool。Planner 落到 reasoning pool（通常是 GLM 或 ChatGPT）。Translator 落到中文 pool（通常是 GLM 或 火山引擎 DeepSeek）。Critic 落到 code+reasoning pool（通常是 ChatGPT 或 NVIDIA Cloud）。每個 step 分開 log。任何一個 step 的 pool 飽和，那個 step 單獨 failover。

我拿同一個 pattern 跑 JIRA-ticket-to-PR、paper-summarization、跟幾個內部工具。它是我自己 repo 裡被借最多次的 code。

---

## 5 分鐘自己加一個 provider

這個段落我希望你真的去試。打開 terminal。我等你。

```bash
# 1. 產出新的 plugin scaffold
khavis new-provider myprovider
# -> 產出 providers/myprovider.py
```

你會得到一個長這樣的檔案：

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

現在填 `chat()`。如果你的 provider 講 OpenAI-compatible 的 Chat Completions API（大部分都，包括 NVIDIA Cloud、OpenRouter、火山引擎、Together、Groq、和一長串），就 3 行：

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

如果你的 provider 真的很奇怪（Anthropic 原生、Gemini 原生等等），你大概要寫 50 行 normalization。`providers/` 裡的 `glm.py` 和 `gemini.py` 是好範本——它們完整展示了怎麼處理 streaming、function call、跟最常見的 error shape。

### Step 3 — 在 YAML 註冊這個 pool

```yaml
# config/pools.yaml — 加在最後面：
  - name: "Myprovider-Flash"
    provider_id: "myprovider"
    endpoint: "https://api.myprovider.com/v1"
    model: "myprovider-flash"
    env_key: "MYPROVIDER_API_KEY"
```

### Step 4 — advertise 一個 capability（選用）

```yaml
# config/capabilities.yaml — 加在最後面：
  - capability: "速度優先"
    pools:
      - "Myprovider-Flash"
      - "Google-Gemini"
    weight: 1.0
```

### Step 5 — hot-reload 然後試試看

```bash
# daemon 會自動 pick up 新檔案（它在 watch providers/）
khavis serve
# 在另一個 shell：
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"capability": "速度優先", "messages": [{"role":"user","content":"hello"}]}'
```

整個流程這樣。如果你花超過 5 分鐘，那就是你跟 provider 的 auth scheme 吵架的時間。

---

## 真實 benchmark（連同誠實的 caveat）

我想先講清楚這些數字是什麼、不是什麼。

**它們是：** 過去 11 週我自己 workload 的 end-to-end latency 跟成本測量，從 `audit/requests.jsonl` 取樣。我的 workload 大概是：

- 38% code generation / refactoring
- 22% 中文任務（翻譯、summarization）
- 18% 英文推理任務（planning、summarization）
- 12% embeddings + retrieval
- 10% 其他（vision、agentic multi-step）

**它們不是：** 一個 controlled apples-to-apples benchmark。我沒有用同一組 prompt 在所有 provider 上、同樣的 temperature。每個 provider 有自己的最佳 temperature；我用每家 provider 推薦的預設值。如果你想要 controlled comparison，[Artificial Analysis](https://artificialanalysis.ai/) 做得更專業。

話說這是我 workload 下每個 pool 的中位數 latency 跟粗估 cost-per-1k-tokens：

| Pool | 中位數 latency (ms) | p95 latency (ms) | Cost / 1k tok (USD, blended) |
|---|---:|---:|---:|
| GLM-5.3 | 1180 | 3400 | $0.00018 |
| Google-Gemini (2.5-flash) | 720 | 1600 | $0.00010 |
| DeepSeek-V4-Pro (火山引擎 Ark) | 1450 | 3100 | $0.00027 |
| GLM-5.3-Flash (火山引擎 Ark) | 540 | 1100 | $0.00005 |
| NVIDIA-Cloud (llama-3.3-70b) | 1110 | 2400 | $0.00060 |
| OpenRouter-Free | 2100 | 5800 | $0.00000（免費） |
| Ollama-Mac (gemma4:e2b, M3) | 380 | 880 | $0.00000（電費） |
| Ollama-Surface (gemma4:e2b) | 270 | 610 | $0.00000 |

還有 router 當作一個「系統」看的話，一個禮拜的平均：

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

標題數字是最後一列：**在 10 個 provider、4 個訂閱上、21k 個 request，0 個硬失敗。** K.H.A.V.I.S. 出現之前，同樣的 workload，我舊 script 有 1.4% 硬失敗率（每 70 個 request 就有一個回 429，我得自己手動 retry）。K.H.A.V.I.S. 出現之後，我的 call site 完全不需要想這件事。

那 3.7% 觸發 fallback 的 request 全部最後都成功了。大部分 fallback 都是 GLM-5.3 → GLM-5.3-Flash（我月度額度燒完的時候）或者 DeepSeek-V4-Pro → Gemini-Flash（火山引擎 credits 見底的時候）。

**Caveat 1：** 這是我的 workload。你的會不一樣。如果你的 workload 95% 是英文推理，圖就會不一樣 —— ChatGPT 跟 Gemini 會 carry 更多。

**Caveat 2：** Router 本身每次 request 大概加 8-15 ms 開銷。我還沒有在 sustained 100-req/s 下面 benchmark。如果你需要那樣，開 issue；我會去 profile。

**Caveat 3：** 成本數字是我真實 prompt 分佈下的 blended 值。如果你叫「summarize 整個 Game of Thrones 全文」，per-1k-tok cost 會看起來完全不一樣。

---

## 取捨 — 這個東西「不是」什麼

我想誠實講哪裡 K.H.A.V.I.S. 對你「不會」有幫助。

### 它不是

- **它不是 hosted gateway。** 沒有 `router.khavis.com`。你自己跑。如果你不想自己跑，[OpenRouter](https://openrouter.ai/) 存在而且很好。
- **它不是 model aggregator。** 我不 host 任何 model。也不轉賣任何訂閱。我只是 route 到你已經付費的 provider。
- **它不是 token-optimizer。** 它不會壓縮你的 prompt、不會幫你偷換成更便宜的 model、也不會背著你降級。如果你叫 `reasoning`，你就拿到 reasoning model。這樣。
- **它不是 finetuning platform。** 你不能透過 K.H.A.V.I.S. finetune。（你可以 route finetuning job 到支援的 provider —— 在 roadmap。）
- **它還沒有為 1000+ QPS production-hardened。** 我自己跑 modest scale（peak 大概幾十 QPS）。它用 in-memory registry 跟 SQLite-backed memory；如果你要 Redis 跟 Postgres 跟橫向擴展，你需要 fork 或等 v0.3。
- **它不是要取代你已經在用的 SDK。** Plugin system 是包它們。如果你有能跑的 OpenAI / Anthropic code，放著別動。

### 什麼時候你不應該用 K.H.A.V.I.S.

- 你只有一個訂閱、一個 use case。（直接 call SDK 即可。）
- 你要 hosted SLA。（用 hosted gateway。）
- 你要 sub-100ms latency。（Router overhead + network hops 會弄死你。）
- 你要根據 prompt 內容 routing，不是根據 capability tag。（那是別的產品—— 看 [Martian](https://withmartian.com/) 或 [Not Diamond](https://notdiamond.ai/)。）
- 你不信任自己跑一個 daemon 在 box 上。（用 OpenRouter。）

### 誠實的設計取捨

1. **Capability tag 是字串，不是 enum。** 我刻意不強制 taxonomy。你可以用 `中文` 或 `chinese` 或 `cn` 或任何東西。缺點：typo。優點：onboard 新 tag 零設定。（我打算在 v0.2 出一份 recommended taxonomy。）
2. **沒有 UI，是故意的。** 全部是 YAML 跟 JSONL。如果你想要 UI，你可以在 audit log 上面自己蓋一個。目前沒有內建 dashboard。（歡迎 PR。）
3. **BYOK means you BYOK。** 如果你的 key 漏了，那是你的事。Daemon 不 log 它、不把它送到上游以外的地方、支援 `.env` / vault / 1Password CLI / 你已經在用的任何東西。但它沒辦法保護你一個不小心 `git commit -A`。
4. **Failover 是 best-effort，不是 guaranteed。** 如果「所有」你的 pool 都死掉，router 就回 error。它不會掰一個答案給你。
5. **Plugin auto-discovery 代表邪惡 plugin 可以自己 register。** 不要在你 `providers/` 跑不信任的 code。（任何 plugin system 都一樣。）

如果上面有任何一個對你是 deal-breaker，那沒關係。還有別的工具。我做這個是為了我自己；如果它適合你，讚；如果不適合，我希望這份架構能啟發你做的東西。

---

## Roadmap

簡短一點、有日期。以 v0.1.0 來說：

### v0.2 — 2026 Q4

- [ ] 推薦的 capability taxonomy（附 i18n：`中文`、`zh-TW`、`zh-CN`...）
- [ ] Cost-aware routing（在 capability + latency budget 內挑最便宜 pool）
- [ ] 內建 `/v1/embeddings` 跟 `/v1/audio/transcriptions` endpoint
- [ ] 多 9 個 provider plugin：AWS Bedrock、Azure OpenAI、Vertex AI、Mistral、Groq、xAI、Cohere、Together、Fireworks
- [ ] Postgres back-end for episodic memory（預設還是 SQLite）
- [ ] 每次 request 的 OpenTelemetry traces

### v0.3 — 2027 Q1

- [ ] 橫向擴展模式（shared-nothing daemon + Redis registry）
- [ ] 可插拔 cost model（USD / CNY / credits / 自訂）
- [ ] 一個小、但是很醜的 web UI for `audit/`
- [ ] Streaming function-call composition（planner 一邊 stream token、一邊進 coder 那邊規劃）
- [ ] 內建 evaluator harness（跑一組 prompt suite，report 每個 pool 成功率 + 成本）

### v1.0 — 2027 Q3（或等到對的時候）

- [ ] Stable plugin API（v1.0 plugin contract）
- [ ] Stable config schema（v1.0 YAML）
- [ ] 給 plugin 作者跟 config 作者的 backwards-compat 保證
- [ ] 選擇性的 hosted SaaS tier（還是 BYOK），給不想自己跑 daemon 的人

選擇性的 SaaS 不是目標 —— 目標是 open-source router。但我想要一條路「我不想自己跑這個」又不放棄 BYOK。之後再講。

---

## 你可以怎麼幫忙

三件事，按影響力排序：

### 1. Star 這個 repo

如果你讀到這裡、覺得你會用這個，你最高槓桿的一件事就是 **去 GitHub star 這個 repo**。Star 是決定其他人能不能看到的演算法。Repo URL 在文章最上面。

### 2. 在你真實的 workload 上面跑一個禮拜

找出真實 bug 最快的方法就是用它來跑你真的在乎的 workload。有壞掉就開 issue。有修就開 PR。48 小時內我會讀每一個 issue。

### 3. 寫一個我還沒出的 provider plugin

我打算加的 provider 在 roadmap，但我寧願是 community-maintained。如果你每天用一個我還沒出 plugin 的 provider，請送 PR。Plugin contract 已經穩定了；`glm.py` 是最乾淨的範例。五分鐘，我保證。

### 4. 翻譯 README

`README.zh-TW.md` 已經有了。我想要 `README.ja.md`、`README.ko.md`、`README.es.md`、`README.de.md`。翻譯量很小，價值很大。

### 5. 告訴我哪裡做錯了

如果你 routing LLM 比我久，看到一個你想 push back 的設計選擇，**拜託告訴我**。Plugin contract、capability model、audit schema、failover strategy——所有這些都歡迎根據真實 feedback 改。

---

## 附錄：安裝、設定、疑難排解

### 從 PyPI 安裝

```bash
pip install khavis
```

### 從 source 安裝

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

### Config schema（`config/pools.yaml`）

```yaml
pools:
  - name: "<display name>"
    provider_id: "<plugin class id>"
    endpoint: "<override 或 default>"
    model: "<default model>"
    env_key: "<env var holding the API key>"
```

除了 `name` 以外所有欄位都 optional；plugin 的 default 會補剩下的。

### Config schema（`config/capabilities.yaml`）

```yaml
capabilities:
  - capability: "<tag string>"
    pools:
      - "<pool name from pools.yaml>"
      - ...
    weight: 1.0   # weighted-random selection 用
```

`weight` 預設 1.0。一個 weight 1.2 的 pool 大概比 weight 1.0 的同儕多 20% 被選到的機會。

### CLI reference

```
khavis init                  # 在當前目錄 scaffold 一份 config
khavis serve                 # 啟動 HTTP daemon（預設 :8080）
khavis serve --port 9000     # 自訂 port
khavis new-provider <name>   # scaffold 一個新的 plugin file
khavis audit                 # pretty-print audit log
khavis audit --since 24h     # 只看最近 24 小時
khavis audit --pool GLM-5.3  # 篩選 pool
khavis doctor                # 跑 health + quota check，印一張表
```

### HTTP API

```
POST /v1/chat            # chat completion，OpenAI-compatible response
POST /v1/embeddings      # embeddings (alpha)
GET  /v1/pools           # 列 pools + health + quota
GET  /v1/capabilities    # 列 capability → pool 對應
GET  /healthz            # liveness probe
```

`/v1/chat` 接受 OpenAI-shaped request body 加上一個 optional `capability` 欄位：

```json
{
  "capability": "code",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.2,
  "stream": false
}
```

如果沒給 `capability`，router 挑一個 default（`推理`）。

### 疑難排解

**「全部 pool 都 unhealthy。」**
跑 `khavis doctor`。它會印一張表，每個 pool 的 health、endpoint、有沒有 key、最後 error。最常見的原因是 `.env` 沒填 key。

**「我想讓 pool X 永遠不被選。」**
從 `capabilities.yaml` 相關 capability 的 pools list 把它註解掉，或把 weight 設成 `0.0`。

**「Hot reload 沒有 pick up 我的修改。」**
Daemon 同時 watch `config/*.yaml` 跟 `providers/*.py`，在 process 裡 reload。如果你沒在 ~2 秒內看到改變生效，檢查 `audit/doctor.log`。

**「我想用不同的 failover strategy。」**
`Router.chat(..., strategy="weighted|round_robin|random")` 可以 per-request 覆寫。

**「我想 log 到別的地方。」**
設環境變數 `KHAVIS_AUDIT_DIR=/var/log/khavis`。

**「我想要 web UI。」**
v0.3 的 roadmap 有一個。在那之前，`tail -F audit/requests.jsonl | jq` 是精神上的等價物。

---

## 收尾

我做 K.H.A.V.I.S. 是因為我受夠了在週二 11:47 PM 當我自己訂閱的空中交通管制員。

如果有共鳴，請 [star 這個 repo](https://github.com/kiddhsu5/K.H.A.V.I.S.)、開 issue、送 PR、或只是寄 email 跟我說你用它做了什麼。這個專案只有在真實的人用它、跟我講哪裡出錯的時候才會變得更好。

— kiddhsu5, 2026-09-20

> 「跨所有訂閱的合計剩餘空間其實很大。問題不是 capacity。問題是我們在半夜當我們自己 API 的空中交通管制員。」