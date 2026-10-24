# K.H.A.V.I.S.

> **跨廠牌 AI 編碼 CLI 與 12 個 LLM 模型池的統一智慧指揮中心 — 具備多訂閱配額感知、共用工作區 / Git Worktree 隔離、自訂 Agent 擴充與零額度中斷。**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-v0.4.0-emerald.svg)](#roadmap)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

```
    ┌────────────────────────────────────────────────────────────────────┐
    │                          K.H.A.V.I.S.                              │
    │   五大主流 CLI + 自訂 Agent · 十二個模型池 · 圖形化工作台 · 零額度中斷   │
    └────────────────────────────────────────────────────────────────────┘
```

### 🌟 v0.4.0 核心亮點 (Unified Graphical Workbench & Multi-CLI Orchestration)

1. **🖥️ 圖形化全功能智慧工作台 (`/workbench`)**
   - 內建互動式 **SVG 即時派工拓撲圖 (Interactive Dispatch Topology)**、**7 角色協同進度軸 (LangGraph 7-Role Stepper)**、**環形配額儀表 (Radial Quota Gauges)** 與 **各節點延遲橫條圖 (Latency Comparison Chart)**。
2. **🤖 5 大主流 CLI Agent 並發調度 + 動態模型切換**
   - **Claude Code (`claude`)**：預設驅動 **`MiniMax-M3.1-Flash`**（MiniMax Token Plan），支援於 Web 介面即時切換模型。
   - **OpenAI Codex (`codex`)**：預設驅動 **`glm-5.3-flashx`**（GLM Coding Plan）或 `gpt-5-codex`。
   - **Google Antigravity (`antigravity` / `agy`)**：預設驅動 **`antigravity-pro`**，負責全域自主 Agentic 開發。
   - **MiniMax Code (`minimax` / `mcode`)**：預設驅動 **`MiniMax-M3.1`**。
   - **Zhipu zcode (`zcode`)**：預設驅動 **`glm-5.3-flashx`**。
3. **🔌 用戶自訂 Agent 動態擴充機制 (`core/custom_agents.py`)**
   - 使用者可於 Web 介面一鍵加入自己常用的 CLI 工具（內建 **Aider**、**OpenCode**、**Block Goose**、**DeepSeek / Qwen** 範本）或自訂命令列與 OpenAI 相容 API 端點，註冊後立即整合至拓撲圖與並發派工佇列。
4. **📁 共用專案資料夾 + Git Worktree 隔離與 Diff 視覺化對比 (`core/workspace_manager.py`)**
   - **🤝 共用資料夾模式 (`shared`，預設)**：所有 CLI 在同一個專案資料夾（`workspace/<project>`）下無縫接力讀寫檔案，讓不同 CLI 個別或依序執行時極度流暢。
   - **🌿 Git Worktree 隔離模式 (`worktree`)**：並發派工時自動為各 Agent 建立獨立 Git Worktree 分支，在網頁上提供紅綠語法高亮的 **Unified Diff 視覺化對比** 與 **一鍵合併回共用資料夾**。
5. **🪄 開源 / 團隊快速部署與 BYOK 精靈 (`scripts/quick_setup_wizard.sh` & `/workbench`)**
   - 提供三步驟視覺化 BYOK 金鑰配置、環境檢測與一鍵啟動腳本。

---

### Router 開銷 (p95,真實 registry,mock I/O)

| 項目 | 預算 | 實測 | 註 |
| --- | --- | --- | --- |
| 冷啟動 (`discovery_ms`) | 200 ms | **0.4 ms** | 12 個 plugin 的 importlib + class init |
| YAML 重載 (`capability_load_ms`) | 50 ms | **9.2 ms** | hot reload 走同一條路徑 |
| 每次請求路由 (`selection_ms`) | 2 ms | **0.02 ms** | 與 Bifrost 公開的 20μs 同量級 |
| 端到端 (`chat_roundtrip_ms`) | 10 ms | **0.2 ms** | 只有 router 開銷;真正瓶頸在上游 LLM I/O |

完整數字與方法: [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)。CI 會對上述預算做 assertion。

---


### 個人開發者 wall

In production at — 個人 / 團隊實際部署，歡迎 PR 加入。

| 使用者 | 環境 |
| --- | --- |
| [@kiddhsu5](https://github.com/kiddhsu5) | Multi-Agent CLI Workbench · MiniMax / GLM / GPT GO / Antigravity / Ollama |

統一智慧工作台：`/workbench` · 維運儀表板：`/dashboard` · 狀態頁：`/wall`

---

## 為什麼選 K.H.A.V.I.S.?

如果你曾經訂閱過多個 LLM 服務,你一定經歷過這些痛點:

- **任務跑到一半就撞到額度牆。** Gemini Pro 被限流、GLM 在維護、你現在最需要完成的那個 prompt 就是跑不過去。
- **你一直在重寫樣板程式碼。** 每一家供應商都有自己的 SDK、認證機制、串流通訊協定、函式呼叫格式。你的 `chat()` 函式變成 600 行的 `if provider == ...`。
- **本地 GPU 閒置著,你卻繼續付費給雲端。** Ollama 明明就在那邊,但要切換情境就是麻煩。
- **你無法公平地做 benchmark。** 每家供應商的溫度預設、token 計價、計費單位都不同,要做蘋果對蘋果的比較就得自己寫膠水程式碼。
- **你想要 fallback,不是 failover。** OpenRouter 確實有路由,但它不知道 *你的* MiniMax-M3 key、*你的* Volcano Ark 點數、*你的* 本地 Ollama 主機。

**K.H.A.V.I.S. 是為那些「已經在付費給多家 LLM,只想讓它們一起好好工作」的人打造的。** 它把你訂閱的服務、免費額度、本地模型視為同一個具備能力標籤的大池子。當請求進來時,router 會挑出當下最好的模型、監控額度壓力,並在你看到 429 之前就靜默切換。

這不是託管式 gateway,也不是 SaaS。這是一個 self-hosted、可插拔的 Python router,可以跑在你的筆電、home lab、CI 主機上,並完全尊重你既有的 API key。

### 我們的承諾

> **零額度中斷。** 當某個 pool 滿載或回傳錯誤時,流量會在毫秒等級內被重新導向 —— 不需要重啟、不需要重新認證、呼叫端完全不需要改。

---

## 功能特色

- ✓ **內建 12 個 LLM 池** —— MiniMax-M3、GLM-5.3、Gemini Flash/Pro、NVIDIA Cloud、ByteDance Volcano Ark(3 個子模型)、OpenRouter Free、OpenAI Platform API、Anthropic Claude API、Ollama(本地 + Surface)。
- ✓ **基於能力 (capability) 的路由** —— 宣告一個能力(`code`、`vision`、`long-context`、`cheap`、`local`),router 會挑出最合適的模型。
- ✓ **可插拔的 provider 系統** —— 把一個 Python 檔丟進 `providers/`,就會被自動發現。
- ✓ **YAML-first 設定** —— 沒有 UI、沒有資料庫,全部都是可以用 git diff 的檔案。
- ✓ **熱重載 (Hot reload)** —— 編輯 `capabilities.yaml`,router 就會即時套用。
- ✓ **多代理 orchestration** —— 在同一條 pipeline 中組合多個 LLM(planner + coder + critic)。
- ✓ **三層記憶體** —— working、episodic、semantic,讓多輪代理保持連貫。
- ✓ **稽核與可觀察性** —— 每次呼叫都會記錄成本、延遲、capability、結果。
- ✓ **Self-hosted, BYOK** —— 用你自己的 key、自己的機器、自己的模型。
- ✓ **Apache 2.0** —— 商業使用、fork、發布都可以。

---

## 架構一覽

```
                         ┌────────────────────────┐
   你的 app / agent ───► │   K.H.A.V.I.S.     │
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
   │              Provider Plugin Pool (12 providers)              │
   │  MiniMax-M3 · GLM-5.3 · Gemini Flash/Pro ·                     │
   │  NVIDIA Cloud · Volcano Ark (×3) · OpenRouter Free · Ollama   │
   │  OpenAI Platform API (BYOK) · Anthropic Claude API (BYOK)     │
   └──────────────────────────────────────────────────────────────┘
```

一個請求會穿越六個層級 —— plugins、registry、capability router、orchestration、memory、audit。完整深入說明請見 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## 快速開始

兩個指令就能開始 routing —— 不需要先起 server。

```bash
# 1. 安裝
pip install khavis

# 2. 直接送 prompt
khavis chat "用 Python 寫一個 quicksort。"
```

覺得哪裡不對就先問它:

```bash
khavis doctor          # 設定檔 + 哪些 pool 可用
khavis doctor --deep   # ...並實際呼叫每個 pool 來證明
```

`health_check()` 只檢查「key、endpoint、模型名有沒有設定」,**完全不會開任何連線**。
所以過期的 key、用完的額度、已下架的模型全部都會通過它。`--deep` 會對每個 pool
實際發一個最小請求,告訴你哪些是真的能用。

常用參數:

```bash
khavis chat --pool Google-Gemini "…"      # 指定單一 pool
khavis chat --capability 程式碼 "…"       # 依 capability 標籤路由
khavis chat --json "…"                    # 完整的 provider 回應
khavis chat --quiet "…"                   # 不顯示 pool/模型/token 資訊
```

`khavis chat` 走的是和 HTTP API **同一套**熔斷器與 failover,所以額度用完或壞掉的
pool 會被記錄並跳過,而不是把上游的錯誤丟給你。

### 要跑成伺服器時

```bash
khavis init     # 產生範例設定檔(不會覆寫既有檔案)
khavis serve    # OpenAI 相容的 HTTP API,預設 :8080
```

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "用 Python 寫一個 quicksort。"}]}'
```

Router 會從 prompt 推斷 capability 標籤並挑一個健康的 pool(傳 `"model": "<pool 名稱>"`
可指定)。回應是 OpenAI 格式 —— `choices`、`model`、`usage` —— 另外附帶 `pool`、
`cost_usd`、`latency_ms`,整個呼叫會寫進 `config/audit.jsonl`。

遇到 429 會自動 failover 到下一個 pool,並完整記錄整個過程。

### 下架一個 pool

`discover()` 會自動實例化 `providers/` 底下的每個 plugin,所以在 `pools.yaml` 裡
**刪掉或註解**一個 entry **並不會**讓它停止被使用 —— 那個檔案只是「覆寫」已發現的
plugin。要真的停用:

```yaml
- name: "SomePool"
  disabled: true   # 才會真的從 registry 移除
```

---

## 安裝方式

### 選項 A —— pip(推薦給開發者)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install khavis
```

驗證:

```bash
khavis --version
khavis doctor               # 檢查 Python、網路、若有本地 Ollama 也會檢查
```

### 選項 B —— Docker(零安裝、完全隔離)

```bash
docker run -d \
  --name khavis \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  ghcr.io/kiddhsu5/khavis:0.1.0
```

映像檔已預載所有 provider plugin。把 `config/` 目錄掛載進去,即可持久保存 key 與 routing 規則。

### 選項 C —— 從原始碼安裝(給貢獻者)

```bash
git clone https://github.com/kiddhsu5/K.H.A.V.I.S..git
cd khavis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

包含 Ollama、Docker 與各平台注意事項的完整逐步說明,請見 [`INSTALLATION.md`](INSTALLATION.md)。

---

## 基本用法

### 1. 基於 capability 的 chat

```python
from pathlib import Path

from core.registry import PluginRegistry
from core.capability_router import CapabilityRouter

root = Path(".")  # 專案根目錄（裡面有 config/）
reg = PluginRegistry(root).discover()
reg.apply_pools_config(root / "config" / "pools.yaml")

router = CapabilityRouter(reg)
router.load_capabilities(root / "config" / "capabilities.yaml")

plugin = router.select("程式碼")  # 任何 config/capabilities.yaml 裡的 tag
result = plugin.chat([{"role": "user", "content": "請重構這個函式。"}])

print(result["choices"][0]["message"]["content"])
print(result.get("usage"))
```

每個 plugin 都回傳 OpenAI 格式的 dict（`choices` / `model` / `usage`）。走 HTTP 的話，response 會額外帶 `pool`、`cost_usd`、`latency_ms`，而且每次請求都會寫進 `config/audit.jsonl`。

### 2. 鎖定特定 pool

```python
plugin = reg.get("DeepSeek-V4-Pro")  # config/pools.yaml 裡的 pool 名稱
result = plugin.chat([{"role": "user", "content": "用日文打招呼。"}])
```

### 3. 額度用完自動換 pool

```bash
# 看每個 pool 的熔斷 / 配額狀態
khavis health --refresh

# 全部強制復原（手動解鎖熔斷的 pool）
khavis health --reset
```

```python
from core.health import get_tracker

tracker = get_tracker()
tracker.record_failure("MiniMax-M3", "HTTP 429")  # 配額錯誤 → EXHAUSTED
tracker.record_success("GLM-5.3")  # 恢復正常
print(tracker.explain("MiniMax-M3"))
```

`CapabilityRouter.select()` 會自動跳過熔斷中或配額用完的 pool；全部不可用時回傳 `None`，
由呼叫端丟出明確錯誤，而不是硬送進已知壞掉的 pool。用 `router.explain_unavailable(capability)`
可以拿到「為什麼全都不能用」的診斷訊息。

HTTP 層預設也會在 upstream 失敗時自動改送下一個 pool（`KHAVIS_FAILOVER=0` 可關閉）。

### 4. 串流回應

OpenAI 相容伺服器接受 `"stream": true` 並回 SSE `chat.completion.chunk`，
把任何 OpenAI SDK 的 `base_url` 指到 `http://localhost:8080/v1` 即可。
目前還沒有 in-process 的 generator API，原生 `stream()` 在 roadmap 上。

### 5. Token 與花費上限

```python
from core.budget import get_guard

guard = get_guard()  # 政策來自 config/budgets.yaml
if guard.allow(session_id="demo", pool="MiniMax-M3", prompt_chars=120):
    result = plugin.chat(messages)
    rec = guard.record(session_id="demo", pool="MiniMax-M3", usage=result.get("usage") or {})
    print(f"tokens={rec['tokens']}  cost=${rec['cost_usd']:.6f}")
```

### 6. 多代理 orchestration

```python
from agents.graph import run_team

state = run_team("設計一個 todo app 的 REST API。", session_id="demo")
print(state["final"])
```

### 7. 本地優先,雲端 fallback

```python
# capabilities.yaml 可以把某個 capability 綁到 Ollama,
# 本地主機離線時自動 fallback 到雲端 pool。
plugin = router.select("速度優先")
```

---

## 支援的供應商

| Pool ID                    | Provider                       | Capability 標籤                        | 備註                                |
|----------------------------|--------------------------------|----------------------------------------|--------------------------------------|
| `MiniMax-M3`               | MiniMax                        | general, code                          | 高吞吐、低延遲                      |
| `glm53`                    | Zhipu GLM-5.3                  | reasoning, code, long-context          | 強健的中文支援                      |
| `gemini-flash`             | Google Gemini Flash            | cheap, vision, long-context            | Google 最快的 tier                  |
| `gemini-pro`               | Google Gemini Pro              | reasoning, vision, long-context        | 更深的推理                          |
| `nvidia-cloud`             | NVIDIA Cloud (NIM)             | code, reasoning                        | GPU 加速推論                        |
| `volcano-ark-deepseek`     | ByteDance Volcano Ark (DeepSeek)| code, reasoning                       | 子模型                              |
| `volcano-ark-qwen`         | ByteDance Volcano Ark (Qwen)   | general, code                          | 子模型                              |
| `volcano-ark-doubao`       | ByteDance Volcano Ark (Doubao) | general, vision                        | 子模型                              |
| `openrouter-free`          | OpenRouter 免費層              | cheap, general                         | 聚合器 fallback                     |
| `openai-api`               | OpenAI Platform API *(BYOK)*   | code, reasoning, tools                 | gpt-5 系列,需另外申請 API 帳號      |
| `claude-api`               | Anthropic Claude API *(BYOK)*  | reasoning, tools, long-context         | Sonnet 5 / Opus 4.5 / Haiku 4.5      |
| `ollama-local`             | Ollama(本地)                  | local, private                         | 跑在你自己的機器上                  |

每個 pool 都是 `providers/` 下的獨立 plugin。想新增自己的,請見 [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md)。

---

## BYOK —— 自帶 API Key

部分 plugin 開箱即可搭配 **你已經有的訂閱/API key**;其他則需要 **另外申請一個計費帳號**。下表清楚標示差異,讓你一眼知道要為哪些 provider 註冊新帳號。

### 開箱可用(沿用你現有的 key)

| Plugin              | 你需要的帳號                                    | 申請位置                                              |
|---------------------|------------------------------------------------|-------------------------------------------------------|
| `MiniMax-M3`        | MiniMax API key                                 | https://api.MiniMax.chat                              |
| `GLM-5.3`           | ZhipuAI / BigModel key                          | https://open.bigmodel.cn                               |
| `DeepSeek-V4-Pro`   | ByteDance Volcano Ark key                       | https://www.volcengine.com/product/ark                |
| `DeepSeek-V4.1-Flash` | (同一個 ByteDance key)                        | (同上)                                                |
| `GLM-5.3-Flash`     | (同一個 ByteDance key)                          | (同上)                                                |
| `Google-Gemini`     | Google AI Studio key                            | https://aistudio.google.com/app/apikey                |
| `OpenRouter-Free`   | OpenRouter 免費 API key                         | https://openrouter.ai/keys                            |
| `Ollama-Mac`        | 無,跑在你的機器上                              | n/a                                                   |
| `Ollama-Surface`    | 無,跑在你的 LAN                                | n/a                                                   |

### 需要另外申請 API 帳號(BYOK)

這些 plugin **預設就會在程式碼中啟用**,但若對應的環境變數未設定,integration test 會自動跳過。請只在「你真的要付費」的 provider 上填寫 `.env`:

| Plugin              | 你需要的帳號                                    | 申請位置                                               |
|---------------------|------------------------------------------------|--------------------------------------------------------|
| `OpenAI-API`        | OpenAI Platform API key                         | https://platform.openai.com/api-keys                   |
| `Claude-API`        | Anthropic API key                               | https://console.anthropic.com                          |
| `NVIDIA-Cloud`      | NVIDIA NIM API key                              | https://build.nvidia.com(付費 GPU 點數)               |

> **重要:** OpenAI Platform API key **不等於** ChatGPT Plus / ChatGPT GO 訂閱。Claude API 也 **不等於** Claude Code 或 Cursor —— 後兩者用自己的計費,不走 platform API。BYOK 的意思是 *由你決定* 要付哪些帳單,K.H.A.V.I.S. 不會再加一層抽成。

---

## 設定

K.H.A.V.I.S. 透過兩個 YAML 檔(以及選用的環境變數)設定:

| 檔案                              | 用途                                              |
|-----------------------------------|------------------------------------------------------|
| `config/capabilities.yaml`        | 將 capability 標籤映射到有序的 pool 偏好      |
| `config/pools.yaml`               | 宣告每個 pool、認證方式、個別 pool 覆寫設定 |
| `config/agents.yaml` *(選用)*     | 多代理 pipeline 定義                            |
| `.env`                            | 機密 —— 永遠不要 commit                            |

`capabilities.yaml` 範例:

```yaml
capabilities:
  code:
    prefer: [MiniMax-M3, volcano-ark-deepseek, glm53]
    fallback: [nvidia-cloud, openrouter-free]
    max_cost_usd: 0.01

  vision:
    prefer: [gemini-pro, gemini-flash, volcano-ark-doubao]

  local:
    prefer: [ollama-local]
    fallback: [glm53]   # 僅在你同意 local→cloud 時啟用

routing:
  retry_on: [429, 503, timeout]
  max_retries: 3
  cooldown_seconds: 60
```

完整設定請見 [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。

---

## Plugin 開發

新增 provider 只需要一個檔案。Registry 會自動發現所有 `ProviderPlugin` 的子類別:

```python
# providers/my_provider.py
from khavis.plugins import ProviderPlugin, ChatResponse


class MyProvider(ProviderPlugin):
    name = "my-provider"

    def chat(self, messages, **kwargs) -> ChatResponse:
        # 你的實作
        ...
```

在 `pools.yaml` 註冊、加 capability 標籤、送出 PR。完整步驟請見 [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md)。

---

## Roadmap

- [x] **v0.1.0** —— 核心 router、registry、12 個 pool(含 OpenAI + Claude BYOK)、capability routing、稽核日誌。
- [ ] **v0.2.0** —— 每次請求 / 每個 session 的 token-aware 成本預算。
- [x] **v0.3.0** —— 內建 RAG 連接器(`core/rag.py`)。
- [x] **v0.4.0** —— 相容 OpenAI 的 drop-in server(`khavis-serve`)。
- [x] **v0.5.0** —— 正式支援 fine-tuned 模型註冊表與熱切換。
- [x] **v0.6.0** —— 即時監控 pool 健康與額度的 Web UI(`/dashboard`)。
- [x] **v1.0.0** —— 穩定的 plugin API(`docs/PLUGIN_API.md`)。

有想法嗎?開個 issue,或在 [discussion board](https://github.com/kiddhsu5/K.H.A.V.I.S./discussions) 投票。

---

## 貢獻

歡迎各種規模的 PR —— typo 修正、新 provider、routing 策略、文件。動手前請先讀 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

重點:

- 全面遵守 PEP 8 + 型別註記(`mypy --strict` 必須通過)。
- 新 provider 至少要附上一個整合測試。
- 在 `CHANGELOG.md` 的 "Unreleased" 段落更新。
- Code review 時保持善意。我們為下一位貢獻者而優化。

---

## 社群、團隊版與商業合作 (Open Core & Enterprise Support)

- **個人與開源社群（Apache 2.0 永久免費）**：
  - GitHub Issues：Bug 回報與功能請求
  - GitHub Discussions：問題討論、作品展示、Routing 與 Multi-CLI 協同食譜
  - 安全性：請見 [`SECURITY.md`](.github/SECURITY.md) 的負責任揭露流程
- **🏢 團隊版與企業私有化部署（Enterprise & Team Support）**：
  - 針對研發團隊與企業內部 AI 轉型，我們提供進階商業支持：
    - **多人共享 Coding Plan 配額池與 RBAC 權限管理**（統一納管團隊的 MiniMax / GLM / OpenAI / Anthropic 訂閱）
    - **企業內網私有化部署與自訂 CLI / 內部系統工具鏈整合**
    - **團隊級 Prompt 與 Git Worktree 變更審計日誌（Audit & Compliance）**
  - 📩 商業合作、技術顧問或私有化定制請聯繫：[`security@kiddhsu.taipei`](mailto:security@kiddhsu.taipei) 或透過 [GitHub Discussions](https://github.com/kiddhsu5/K.H.A.V.I.S./discussions) 留言。

---

## 授權

Apache License 2.0。完整內容請見 [`LICENSE`](LICENSE)。

```
Copyright 2026 khavis contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## 致謝

K.H.A.V.I.S. 站在巨人的肩膀上:

- [LiteLLM](https://github.com/BerriAI/litellm) 團隊,提供了 provider API 正規化的基礎。
- [OpenRouter](https://openrouter.ai) 團隊,證明了 routing 這個概念可行。
- 所有我們適配其 API 的供應商。
- 所有提出 issue、貢獻 plugin、改善文件的貢獻者。
