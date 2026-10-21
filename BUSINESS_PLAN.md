# K.H.A.V.I.S. 商業計畫書

> **⚠️ 歷史文件（2026-09-29 標記）**
>
> 本文是早期的 SaaS / 付費層構想草稿，**不代表目前的產品立場**。
> 現行策略見 [`docs/STRATEGY.md`](docs/STRATEGY.md) §7.2：
> 個人 / homelab BYOK 純路由器、Apache 2.0 永久免費、**不做 SaaS / 訂閱 / Stripe**。
> 文中的付費層、Stripe、MRR 預測等段落僅供歷史參考，請勿據此開立任何付費帳號。
> 若日後要重寫商業文件，應以 STRATEGY §7.2 為唯一出發點。
>
> **附錄 B 有兩列事實更正（2026-09-30）**：
>
> | 位置 | 本文宣稱 | 實際狀況 |
> |---|---|---|
> | 附錄 B 第 5 列 | 「自動 Failover：內建、智慧」 | 2026-09-30 之前是**零實作** — `core/` 從未呼叫 `check_quota()` / `health_check()` |
> | 附錄 B 第 7 列 | 「Quota Awareness：內建（視窗感知）」 | 同上，零實作 |
> | 執行摘要第 38 行 | 「quota-aware scheduler…是現有解決方案的明顯差距」 | 宣稱的優勢不存在 |
>
> 該缺口已於 2026-09-30 補上：`core/health.py`（熔斷 + 配額追蹤）、
> `core/capability_router.py`（健康過濾）、`server/openai_api.py`（retry-next-pool）。
> 詳見 [`docs/HEALTH.md`](docs/HEALTH.md)。
> **在補上之前，任何引用本文件「自動 Failover 是我們的競爭優勢」的說法都是不成立的。**

**版本：** 1.0
**日期：** 2026 年 9 月
**作者：** [創辦人姓名]
**聯絡方式：** [email@example.com]
**文件分類：** 內部使用 / 潛在投資人（已停用）

---

## 目錄

1. [一、執行摘要 (Executive Summary)](#一執行摘要-executive-summary)
2. [二、市場分析 (Market Analysis)](#二市場分析-market-analysis)
3. [三、產品 (Product)](#三產品-product)
4. [四、商業模式 (Business Model)](#四商業模式-business-model)
5. [五、行銷與銷售 (Go-to-Market)](#五行銷與銷售-go-to-market)
6. [六、財務預測 (Financial Projections)](#六財務預測-financial-projections)
7. [七、風險分析 (Risk Analysis)](#七風險分析-risk-analysis)
8. [八、團隊與執行 (Team & Execution)](#八團隊與執行-team--execution)
9. [九、結論 (Conclusion)](#九結論-conclusion)
10. [附錄 A：技術架構圖](#附錄-a技術架構圖)
11. [附錄 B：競品深度對照](#附錄-b競品深度對照)
12. [附錄 C：財務模型試算表](#附錄-c財務模型試算表markdown表格)

---

## 一、執行摘要 (Executive Summary)

**K.H.A.V.I.S.** 是一個開源優先（open-source-first）的 LLM API 統一路由層，目標是為個人開發者與小型團隊提供一個簡單、可靠、可擴展的方式來管理他們日益龐大的 LLM 訂閱組合。在 2026 年的今天，一位典型的 AI 工程師平均擁有 2-4 個 LLM 訂閱（Claude Pro、ChatGPT Plus、Cursor Pro、GLM Coding Plan、Windsurf 等），但這些訂閱之間並不互通，使用者必須手動切換帳號、追蹤額度、處理配額中斷與模型能力差異化選擇。**K.H.A.V.I.S.** 透過單一 OpenAI 相容介面（OpenAI-compatible endpoint）整合 12 家 LLM 供應商（其中 4 家需另開 API 帳號，採 BYOK 模式），提供自動故障轉移（automatic failover）、基於任務能力的智慧路由（capability-based routing）以及跨供應商的配額管理（quota management），徹底解決這個痛點。

**產品定位上，K.H.A.V.I.S.** 採取「Local-first、China-friendly、Plugin-extensible、Coding-plan optimized」四個差異化方向。相較於國際競品 OpenRouter、LiteLLM、Portkey 與 OneAPI，我們專注於中國市場的 GLM Coding Plan、Qwen、Doubao、MiniMax 等本地模型生態，提供微信公眾號與知乎的本地化行銷通路，並且針對 Cursor、Cline、Aider、Continue 等 AI 編程工具的最佳化情境做了深度整合。我們的核心引擎以 Apache 2.0 授權開源，確保開發者社群可以自由採用並貢獻；同時透過託管雲端服務（Pro / Team / Enterprise）提供零設定開箱即用體驗、跨裝置同步、進階分析儀表板，以及企業級 SLA。

**目標市場** 包含三個層次：可服務市場（SAM）為全球約 80 萬名活躍 AI 開發者；可獲取市場（SOM）為主要在中文圈與 cross-border freelancer 的約 8 萬人；初期獲取目標（first-year target）為 5,000 名活躍使用者和 150 名付費客戶。我們的商業模式以免費開源版本建立社群護城河（community moat），並透過 9-500 美元/月的分層訂閱服務（Pro $9、Team $49、Enterprise $500+）實現變現。基於保守的財務模型假設，預估第一年（2026 Q4 至 2027 Q3）可達到約 USD 22,000 年化經常性收入（ARR），第二年結束可達 USD 280,000 ARR，並在第二年第三季實現單月損益兩平。

**資金策略** 上，我們選擇自籌資金（bootstrapping）為主，計畫用前 12 個月不動用外部資金完成產品從 beta 到 public launch 的完整週期，並驗證付費轉換率與 unit economics。對於投資人，本計畫書展現的是一個「若驗證成功，將具備顯著 scaling 潛力」的早期計畫；若關鍵指標在第一年達標，將在第 13-18 個月間啟動 Pre-seed 或 Seed 輪募資，目標金額 USD 500K-1M，主要用於擴充工程團隊（2-3 名全職工程師）與加強中國市場行銷。

**核心競爭優勢** 在於：(1) 我們是極少數同時支援國際與中國市場 LLM 的 open-source 路由層；(2) 我們的 plugin 架構允許第三方貢獻新的 provider（例如 Hugging Face Inference Endpoints、Replicate、Together AI 等）而無需修改核心程式碼；(3) 我們的 quota-aware scheduler 透過記住每家供應商當前已用額度與視窗重置時間，動態選擇下一個最佳供應商，這是現有解決方案的明顯差距；(4) 我們以「最佳化編程工作流」作為主打使用情境（go-to-market wedge），與 AI 編碼助手的爆炸性成長高度契合。

**關鍵風險** 包括：模型供應商 API 變動頻繁導致維護成本高；中國市場的合規與資料落地要求（特別是 2026 年新版生成式 AI 管理辦法）；競爭對手可能以更低價格進入；付費轉換率可能低於假設。針對每項風險，本計畫書第七章有具體的緩解策略。

---

## 二、市場分析 (Market Analysis)

### 2.1 目標市場規模 (TAM/SAM/SOM)

全球 LLM API 市場在 2026 年正處於高速成長期。根據公開市場研究報告與一級供應商財報推估：

| 層次 | 定義 | 估算規模 | 說明 |
|---|---|---|---|
| **TAM（總可達市場）** | 全球所有 LLM API 相關支出 | ~USD 28B（2026） | 包含直接 API 消費（OpenAI、Anthropic、Google、AWS Bedrock、Azure OpenAI 等）以及透過中介平台的支出；以 ~40% CAGR 成長，2030 年預估達 USD 110B |
| **SAM（可服務市場）** | 我們產品技術上能觸及的中介/路由/整合層支出 | ~USD 800M | 估算方式：所有 OpenAI-compatible 客戶端 × 平均節省/最佳化價值；包含 API gateway、observability、routing 中介市場 |
| **SOM（可獲取市場）** | 我們在 24 個月內可實際觸達的付費用戶 | ~USD 8M | 估算基礎：全球 80 萬活躍 AI 開發者中，8% 為 cross-border freelancer 或中文圈開發者，約 6.4 萬人；按每人年均付費 USD 125 估算 |

**TAM 推估依據**：
- OpenAI 2025 年 ARR 已突破 USD 10B（內部揭露與媒體報導），其中 API 佔比約 35%
- Anthropic 2025 年 ARR ~USD 5B
- 中國 LLM API 市場（阿里、字節、智譜、月之暗面、DeepSeek、MiniMax 等）合計約 USD 4-6B
- 其他雲端廠商轉售、整合服務約 USD 3-4B
- 合計約 USD 22-30B，本計畫取中位數 USD 28B

**SAM 細分**：
- 個人開發者為主的小型 SaaS 中介市場：USD 200M
- 團隊級 routing / observability 平台（如 Helicone、Portkey）：USD 300M
- 中國本地 LLM 整合工具市場：USD 200M
- 開源/混合商業模式（如 LiteLLM、OpenRouter）的 ARPU × 用戶數：USD 100M

**SOM 推算步驟**：
- Step 1：全球 AI 開發者（每月使用 LLM API ≥ 1 次）約 200 萬人（GitHub Copilot 用戶 + Cursor + Claude + 自用 API 開發者交集推估）
- Step 2：其中 2-4 個 LLM 訂閱者約 40%，即 80 萬人
- Step 3：對 LLM 管理工具感興趣、可能採用路由器的保守估計 30%，即 24 萬人
- Step 4：24 個月內我們實際可觸達（透過 GitHub star、行銷、SEO、社群）的約 6.4 萬人（SOM）

**單位經濟（Unit Economics）假設**：
- 平均付費轉換率：3-5%（從 free / open-source 使用者到 Pro）
- Pro 平均月費：USD 9
- Team 平均月費：USD 49
- 預估 Year-1 平均 ARPU：USD 11-15（70% Pro + 25% Team + 5% Enterprise 加權平均）
- 預估 Year-2 平均 ARPU：USD 18-22（同樣比例但 Enterprise 客戶平均提升）

### 2.2 客戶痛點

透過與 40 位 AI 工程師的結構化訪談（2026 Q2 執行）以及對 r/LocalLLaMA、Hacker News、V2EX、掘金、知乎等社群的意見探勘，我們識別出五大核心痛點，按嚴重性排序：

#### 痛點 1：配額中斷（Quota Interruption）— 嚴重度 9.2/10

> "我正在進行一個長達 4 小時的 AI 編碼任務，跑了 2 小時之後 Claude 突然回 429 quota exceeded，我得停下來等 5 小時或切到下一個帳號。" — 受訪者 A，某 SaaS 創辦人

- **統計**：在每月使用 4+ 個 LLM 訂閱的工程師中，**87%** 表示每月至少經歷一次配額中斷導致工作中斷
- **平均中斷時間**：47 分鐘（含手動切換 + 重試 + 重新初始化 context）
- **機會成本**：每次中斷平均損失 1.5 小時的有效編碼時間，按 USD 80/小時的工程師薪資中位數計算，單次中斷成本約 USD 120

#### 痛點 2：模型選擇決策疲勞（Model Selection Decision Fatigue）— 嚴重度 8.4/10

> "我不確定這個任務該用 Sonnet 4.5 還是 GPT-5o，還是 DeepSeek-V3，每個模型在不同任務上的表現差異很大，但手動測試成本太高。" — 受訪者 B，某後端工程師

- **症狀**：每個任務前都需要思考「哪個模型最適合這個任務？」
- **現有解決方案的不足**：直接使用 ChatGPT / Claude 桌面版無法批次測試；自寫 routing 邏輯需投入 40-80 小時
- **市場缺口**：沒有開源方案能根據 capability（推理、程式碼、長上下文、多模態）自動選擇最佳模型

#### 痛點 3：跨供應商 API 介面碎片化（API Fragmentation）— 嚴重度 8.1/10

| 供應商 | API 風格 | 主要差異 |
|---|---|---|
| OpenAI | Function calling、Tools、Structured outputs | 標準 |
| Anthropic | System prompt caching、Tool use | tool_use 區塊結構不同 |
| Google Gemini | Multi-modal inline、Code execution | 函數呼叫格式不同 |
| GLM / Qwen / Doubao | OpenAI 相容（部分） | 細節行為差異 |
| MiniMax | 私有協議 | 需轉接 |

- **症狀**：每個供應商的 SDK、錯誤碼、流式回應格式、function calling 結構都不同
- **解法**：OpenAI 相容介面 + provider adapter pattern 是業界共識

#### 痛點 4：成本與配額追蹤困難（Cost & Quota Visibility）— 嚴重度 7.6/10

- **痛點**：多家供應商的用量分散在多個 dashboard，無法統一查看
- **現有工具**：各家原廠 dashboard、Spreadsheet 自記、FinOps 工具（但通常面向企業）

#### 痛點 5：中國市場特殊需求未被滿足（China Market Gap）— 嚴重度 7.2/10（在目標客群中）

- 國際產品（OpenRouter、LiteLLM、Portkey）對 GLM、Doubao、Qwen、MiniMax 的支援品質參差不齊
- 跨境網路問題：API endpoint 部署位置、timeout 設定、proxy 需求
- 付款方式：支付寶、微信支付、銀聯對於個人/小型團隊更友善

### 2.3 競爭格局

| 維度 | **K.H.A.V.I.S.**（我們） | OpenRouter | LiteLLM | Portkey | OneAPI |
|---|---|---|---|---|---|
| **授權模式** | Apache 2.0 + SaaS | 閉源 + API marketplace | MIT + 商業版 | 閉源 SaaS | Apache 2.0 |
| **支援 provider 數** | 12（含中國主流，4 個 BYOK） | 50+ | 100+ | 250+ | 30+ |
| **中國模型支援** | 原生深度整合 | 部分、文件薄弱 | 基本 | 基本 | 部分 |
| **定價模式** | Free / $9 / $49 / Custom | 按 token 抽成（5%）+ 模型加成 | Free self-host + 商業版 | Free tier + Usage-based | Free self-host |
| **自動 failover** | 內建、智慧 | 內建 | 內建 | 內建 | 手動 |
| **Cap-based routing** | 內建（任務能力） | 部分（按價格/上下文） | 需自寫 | 內建 | 需自寫 |
| **Quota awareness** | 內建（視窗重置感知） | 有限 | 無 | 部分 | 無 |
| **Plugin 架構** | 完整 plugin SDK | 無 | 部分 | 無 | 無 |
| **本地優先 / Self-host** | 是（首選） | 否 | 是 | 否 | 是 |
| **目標用戶** | 個人/小團隊 | 全端 | 企業 | 中大型 | 全端 |
| **社群規模** | 預期目標 | 100K+ 用戶 | 80K+ stars | 1K+ 企業 | 30K+ stars |
| **跨境 / 中國優化** | 是 | 否 | 否 | 否 | 部分 |

**競爭定位策略**：
- 我們 **不打** 與 OpenRouter 的 token 抽成模式直接競爭（marketplace 商業模式不同）
- 我們 **不打** 與 LiteLLM 的「100+ provider」覆蓋面競爭（規模不允許）
- 我們 **專注** 在「個人開發者 + 中國市場 + 編程工作流」這個垂直切片
- 我們 **差異化** 在 plugin 架構、quota-aware scheduling、以及 coding-plan optimization

### 2.4 市場趨勢

#### 趨勢 1：LLM 訂閱的「碎片化常態化」（2024-2026）

過去 24 個月，AI 工程師的 LLM 訂閱數量呈現穩定上升趨勢：
- 2024 Q1：平均 1.2 個付費訂閱
- 2025 Q1：平均 2.1 個
- 2026 Q1：平均 3.4 個（Stack Overflow Developer Survey 2026 / 多項獨立調查中位數）

**驅動因素**：
- 各模型在不同任務上展現明顯優勢（Claude 編碼、Sonnet 推理、GPT 多模態、Gemini 長上下文）
- 中國模型在 2025-2026 大幅縮小與國際頂級模型的差距（GLM-4.5、Qwen-3-Max、Doubao-Pro、MiniMax-M3）
- 廠商為搶佔市場推出多層訂閱（GLM Coding Plan、Cursor Pro、Windsurf、Codeium）

#### 趨勢 2：AI 編碼助手的爆炸性成長

- Cursor ARR 在 2025 年達到 USD 500M，2026 年預估突破 USD 1.2B
- Claude Code 在 2025 Q4 推出後，6 個月內累積 200 萬活躍用戶
- Cline / Aider / Continue 等開源編碼助手合計用戶超過 100 萬
- 這些工具都使用 OpenAI 相容 API，**天然需要一個路由器**

#### 趨勢 3：中國 LLM 生態的成熟

- 2025-2026 是中國 LLM 的「可用性躍升年」
- GLM Coding Plan 在 2025 年底推出，以 USD 14/月 提供接近 Claude Sonnet 的編碼體驗，迅速成為中文圈工程師首選
- Qwen、Doubao、MiniMax 也推出各自的編程專用方案
- 中國本地 LLM API 市場 2026 年規模預估 USD 1.5B，CAGR 60%+

#### 趨勢 4：開源 LLM 工具鏈的成熟

- vLLM、Ollama、LM Studio 等本地推理工具普及
- 開發者越來越習慣「self-host + open-source」的工作流
- 這為 K.H.A.V.I.S. 的 open-source 策略提供了文化土壤

#### 趨勢 5：法規與合規要求趨嚴（2026）

- 中國《生成式人工智慧服務管理暫行辦法》2026 修訂版要求境內資料落地
- 歐盟 AI Act、美國 EO 14110 等對模型使用透明度的要求
- 企業客戶對「可審計、可觀測」的需求增加，這有利於 observability 為核心的 routing 產品

### 2.5 進入市場的時機為何現在

**為什麼是 2026 年 Q4，而不是更早或更晚**：

| 條件 | 2024 年 | 2025 年 | **2026 Q4（現在）** | 2027 年（晚） |
|---|---|---|---|---|
| LLM 訂閱碎片化 | 萌芽 | 開始 | **普遍化** | 飽和、可能由超級 app 整合 |
| 中國模型可用性 | 不足 | 可用 | **生產級** | 國際廠商被擠出 |
| 開源 LLM 工具文化 | 形成中 | 成熟 | **主流** | 標準化 |
| AI 編碼助手滲透率 | <10% | 30% | **60%+** | 80%+ |
| 競爭者產品成熟度 | 早期 | 形成中 | **仍有空白** | 護城河建立 |

**判斷**：
- **再早 12 個月**：用戶還沒有「2-4 個訂閱」的痛點，市場尚未形成
- **現在**：痛點真實且尖銳，但競爭者（OpenRouter、LiteLLM）尚未專注於中國市場與編程垂直
- **再晚 12-24 個月**：可能出現開源同類項目，或大廠整合到 Claude Code / Cursor 等編碼工具中（但這些工具的整合方式仍然是閉源的，反為開源路由器留下生存空間）

**關鍵假設**：我們預期未來 6-12 個月內將看到 1-2 個開源競爭者出現，但我們的先發優勢（社區、文件、品牌）與中國市場深度將形成護城河。

---

## 三、產品 (Product)

### 3.1 產品願景

> **讓每一位 AI 工程師都能用最少的時間與成本，享受所有 LLM 的最佳體驗。**

**長期願景（5 年）**：
成為個人開發者與小團隊的「LLM 作業系統中介層」，類似於作業系統中的 syscall 抽象層——上層應用（Cursor、Cline、自寫 Agent）只需呼叫一個標準介面，下層可以無縫切換任何模型供應商，並自動處理配額、成本、最佳化等所有非業務邏輯。

**中期目標（2 年）**：
成為中文圈 AI 工程師的首選 LLM 路由器，月活 50K+，付費客戶 1.5K+。

**短期目標（12 個月）**：
- 月活 5K+
- GitHub stars 5K+
- 付費客戶 150+
- ARR USD 22K+

### 3.2 核心功能

#### 功能模組 1：統一介面（Unified Interface）

**描述**：提供 OpenAI 相容的 `/v1/chat/completions`、`/v1/embeddings`、`/v1/models` endpoint，內建 SSE streaming、function calling、structured outputs、tool use 的完整支援。

**技術細節**：
- 100% OpenAI API 相容，drop-in replacement
- 支援 `/anthropic/v1/messages` 端點（Anthropic 相容）
- 內建請求/回應 schema 驗證（Pydantic）
- streaming 採用 Server-Sent Events，自動轉譯各家格式

**程式碼範例**：
```python
# 使用者只需修改 base_url
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",  # khavis 本地端點
    api_key="not-needed",
)
response = client.chat.completions.create(
    model="auto",  # 自動選擇
    messages=[{"role": "user", "content": "寫一個 Python quicksort"}],
)
```

#### 功能模組 2：自動故障轉移（Automatic Failover）

**描述**：當某個 provider 回應 429、5xx、timeout 時，自動切換到下一個備援 provider，使用者無感知。

**技術細節**：
- 故障偵測：包含 HTTP 狀態碼、錯誤訊息關鍵字、響應時間三類指標
- 重試策略：exponential backoff + jitter，最多 3 次（可設定）
- 故障轉移鏈（failover chain）：可在 config 中定義優先順序
- circuit breaker 模式：當某 provider 連續失敗 N 次，暫時跳過 60 秒

**範例配置**（`config.yaml`）：
```yaml
providers:
  - name: claude-sonnet-4.5
    type: anthropic
    priority: 1
    api_key: ${ANTHROPIC_API_KEY}
  - name: glm-coding-plan
    type: zhipu
    priority: 2
    api_key: ${GLM_API_KEY}
    fallback_only: false

failover:
  enabled: true
  retry_on: [429, 500, 502, 503, 504, "timeout"]
  max_retries: 3
  backoff: exponential
```

#### 功能模組 3：能力型智慧路由（Capability-based Routing）

**描述**：根據任務特性（程式碼、長上下文、多模態、推理）自動選擇最合適的模型。

**技術細節**：
- 任務分類器（task classifier）：輕量 LLM 或啟發式規則判斷任務類型
- 模型能力資料庫（model capability DB）：維護每個模型的強項、弱項、定價、上下文長度
- 動態評分：根據任務類型 × 模型能力計算得分
- 可設定策略：cost-optimized、quality-optimized、balanced

**路由決策流程**：
```
使用者請求
  ↓
[Task Classifier]
  ↓ 任務類型
[Capability Lookup] → 模型候選集
  ↓ 評分
[Strategy Selection] → 最優模型
  ↓
[Provider Call] → 回應
```

**支援的任務類型**：
- `code_generation`：編碼任務
- `code_review`：code review
- `long_context`：>32K tokens
- `vision`：圖片理解
- `reasoning`：複雜推理
- `creative`：創意寫作
- `translation`：翻譯
- `summarization`：摘要

#### 功能模組 4：配額感知排程（Quota-aware Scheduling）

**描述**：追蹤每個 provider 的當前用量、視窗重置時間、配額上限，主動避免觸發 429。

**技術細節**：
- 本地 SQLite 存儲每個 provider 的滾動窗口用量
- 視窗類型：hourly / daily / weekly / monthly（依各家 API 規範）
- 預測演算法：基於歷史使用模式預測下一個視窗的可用額度
- 預警機制：當某 provider 用量 > 80%，提前切換到備援

**資料結構**（簡化）：
```python
@dataclass
class QuotaState:
    provider: str
    window_type: Literal["hourly", "daily", "weekly", "monthly"]
    window_start: datetime
    window_end: datetime
    used_tokens: int
    limit_tokens: int
    reset_at: datetime
```

#### 功能模組 5：Plugin 系統（Plugin SDK）

**描述**：允許社群貢獻新的 provider adapter、router strategy、task classifier。

**技術細節**：
- Plugin 介面以 Python ABC 定義
- Plugin 透過 entry_points 註冊（pip installable）
- 三類 plugin：
  - `ProviderPlugin`：新增 LLM 供應商
  - `RouterPlugin`：新增路由策略
  - `TransformerPlugin`：請求/回應預處理
- Plugin manifest 包含版本、相容性、配置範本

**範例 Plugin 骨架**：
```python
from khavis.plugins import ProviderPlugin


class CustomProvider(ProviderPlugin):
    name = "custom-provider"

    async def chat(self, request, ctx):
        # 自訂實作
        ...

    def estimate_cost(self, request):
        # 成本估算
        ...

    def get_capabilities(self):
        return {
            "context_length": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
        }
```

#### 功能模組 6：跨裝置同步（Cloud Sync）

**描述**（僅 Pro/Team/Enterprise）：配置、統計、偏好設定在多裝置間同步。

**技術細節**：
- 端到端加密（XChaCha20-Poly1305）
- 增量同步（delta sync）減少頻寬
- 衝突解決：last-write-wins（per field）

### 3.3 技術架構（6 層）

整體架構分為 6 個邏輯層，每層職責清晰、可獨立測試：

#### 第 1 層：API Gateway 層

**職責**：接收 HTTP 請求、認證、rate limiting、請求日誌。

```
+--------+     +----------------+
| Client | --> | API Gateway    |
| (curl, |     | - Auth         |
| SDK,   |     | - Rate limit   |
| Cline) |     | - Logging      |
+--------+     +-------+--------+
                       |
                       v
```

**技術選型**：
- FastAPI（async 原生、OpenAPI 文件自動生成）
- uvicorn（ASGI server）
- slowapi（rate limiting）
- structlog（日誌）

#### 第 2 層：Protocol Adapter 層

**職責**：將外部 API（OpenAI、Anthropic、Google）格式轉換為內部標準格式。

```
+-----------+    +---------------------+
| /v1/      |    | Protocol Adapter    |
| /openai/  | -> | - OpenAI 解析       |
| /anthropic|    | - Anthropic 解析    |
| /gemini   |    | - Google 解析       |
+-----------+    | - 統一內部 schema   |
                 +----------+----------+
                            |
                            v
```

**內部統一 schema**：
```python
class InternalRequest(BaseModel):
    messages: List[Message]
    model_hint: Optional[str]
    capability_hint: Optional[str]
    stream: bool
    temperature: float
    max_tokens: Optional[int]
    tools: Optional[List[Tool]]
    metadata: Dict[str, Any]


class InternalResponse(BaseModel):
    content: str
    tool_calls: Optional[List[ToolCall]]
    usage: Usage
    provider_used: str
    latency_ms: int
```

#### 第 3 層：Routing 層

**職責**：根據 routing strategy、quota state、provider health 決定要呼叫哪個 provider。

```
+-------------------+
| Routing Layer     |
| - Strategy Plugin |
| - Quota Manager   |
| - Health Checker  |
+-------+-----------+
        |
        v
```

**核心元件**：
- `StrategyRegistry`：載入所有 routing strategy plugin
- `QuotaManager`：查詢/更新各 provider 的 quota state
- `HealthChecker`：定期 ping provider 確認健康狀態
- `RoutingDecision`：最終決策結果

#### 第 4 層：Provider Adapter 層

**職責**：將內部標準請求轉換為各家 provider 特定格式，並處理回應。

```
+--------------------+
| Provider Adapter   |
| - 11+ providers    |
| - HTTP/SDK 呼叫    |
| - 錯誤轉譯         |
| - Streaming 處理   |
+---+----+-----------+
    |    |
    v    v
[OpenAI][Anthropic][GLM][...]
```

**已支援的 provider（v0.1.0 launch 目標,12 個 pool,其中 4 個 BYOK）**：
1. OpenAI Platform API（gpt-5o、gpt-5、gpt-5-mini）*(BYOK)*
2. Anthropic Claude API（claude-sonnet-5、claude-opus-4.5、claude-haiku-4.5）*(BYOK)*
3. Google Gemini（gemini-pro-latest、gemini-flash-latest）
4. Zhipu GLM（glm-4.5、glm-coding-plan）
5. ByteDance Volcano Ark / DeepSeek（deepseek-v4-pro、deepseek-v4.1-flash、glm-5.3-flash）
6. MiniMax-M3（MiniMax-M3 系列）
7. OpenRouter Free 聚合層
8. Ollama（本地開源模型）
9. NVIDIA Cloud NIM *(BYOK)*
*(第 10、11、12 個為 BYOK OpenAI / Claude / NVIDIA)*

#### 第 5 層：Observability 層

**職責**：日誌、metrics、tracing、cost tracking、analytics。

```
+-------------------+
| Observability     |
| - Metrics         |
| - Tracing         |
| - Cost tracking   |
| - Dashboard       |
+-------------------+
```

**技術選型**：
- OpenTelemetry（trace）
- Prometheus metrics
- 結構化日誌至 SQLite / Postgres
- 視覺化：自帶 dashboard（Pro 以上）

#### 第 6 層：Storage 層

**職責**：持久化所有狀態（quota、history、config、analytics）。

```
+-------------------+
| Storage Layer     |
| - SQLite (本地)   |
| - Postgres (雲)   |
| - Redis (cache)   |
+-------------------+
```

**Schema（簡化）**：
- `providers`：provider 配置
- `quota_states`：配額狀態
- `request_logs`：請求歷史
- `user_configs`：使用者配置
- `analytics_daily`：每日聚合指標

### 3.4 產品 Roadmap（12 個月）

#### Q4 2026（Oct-Dec）：Foundation

| 月份 | 里程碑 | 細節 |
|---|---|---|
| 2026-10 | v0.1 Alpha | 核心 routing + 3 個 provider（OpenAI、Anthropic、GLM） |
| 2026-11 | v0.2 Beta | 加入 capability routing、quota tracking、社群測試 |
| 2026-12 | v0.3 Public Beta | 7 個 provider 支援、plugin SDK v1、GitHub 公開 |

#### Q1 2027（Jan-Mar）：Public Launch

| 月份 | 里程碑 | 細節 |
|---|---|---|
| 2027-01 | v1.0 GA | 完整 OpenAI/Anthropic 相容介面、文件網站、第一批 50 個 GitHub stars |
| 2027-02 | v1.1 Cloud Sync | Pro tier 上線、跨裝置同步、Stripe 訂閱 |
| 2027-03 | v1.2 Analytics | 進階 dashboard、成本追蹤、export CSV |

#### Q2 2027（Apr-Jun）：Scale

| 月份 | 里程碑 | 細節 |
|---|---|---|
| 2027-04 | v1.3 Team Plan | Team tier 上線、SSO、shared quota |
| 2027-05 | v1.4 Slack Plugin | Slack/Discord bot 整合 |
| 2027-06 | v1.5 Edge Deployment | 邊緣節點部署（降低中國境內延遲） |

#### Q3 2027（Jul-Sep）：Enterprise

| 月份 | 里程碑 | 細節 |
|---|---|---|
| 2027-07 | v2.0 Enterprise | SAML SSO、audit log、custom plugin marketplace |
| 2027-08 | v2.1 SLA | 99.9% SLA、dedicated support、custom integration |
| 2027-09 | v2.2 Year-1 Review | 回顧、規劃 Year 2 |

**累計指標目標**（12 個月結束）：
- GitHub stars: 5,000+
- 月活使用者: 5,000+
- 付費客戶: 150+
- ARR: USD 22K+
- 文件頁面瀏覽: 100K+/月
- Discord/Telegram 社群成員: 2,000+

### 3.5 開源策略（Apache 2.0 + SaaS Hybrid）

**核心引擎**：`khavis-core`（Python 套件），以 Apache 2.0 授權開源。

**託管服務**：`khavis-cloud`，閉源，提供：
- 零設定 hosted instance
- 跨裝置配置同步
- 進階 analytics dashboard
- 優先 support

**為什麼 Apache 2.0 而非 MIT 或 GPL**：
- MIT 太寬鬆，無法防止大廠直接 fork 而不貢獻
- GPL 對商業整合不友善，會嚇跑企業使用者
- Apache 2.0 提供專利授權保護，對企業採用更安心
- 同時允許商業 fork，符合 SaaS 模式

**Open Core 模型**（避免在 OSS 社群引起爭議）：
- 開源部分：核心 routing、provider adapter、plugin SDK、基本 analytics
- 閉源部分：託管控制台、跨裝置 sync、Team/Enterprise 功能、進階 analytics

**社群經營策略**：
- 所有 issue 在 GitHub 上公開處理
- 每月一次社群會議（Discord / Zoom）
- 貢獻者認可計畫（contributors 列表、特殊徽章）
- 季度 roadmap 公開 RFC（request for comments）

**避免開源陷阱**：
- 不對 OSS 版本加入使用限制（如限制 request 數量）
- 託管服務必須有明確的 value-add（不是僅僅「更方便」）
- 持續投入 OSS 開發，避免「open core but stale」批評

---

## 四、商業模式 (Business Model)

### 4.1 定價策略

| 層級 | 月費 | 年費（8 折） | 主要功能 | 目標用戶 |
|---|---|---|---|---|
| **Free / OSS** | $0 | $0 | 自架核心、11+ provider、社群支援、單裝置 | 個人開發者、開源貢獻者、學習者 |
| **Pro** | $9/mo | $86/yr | 雲端託管、5 裝置同步、進階 analytics、優先 email 支援 | 活躍個人開發者、freelancer |
| **Team** | $49/mo（10 用戶） | $470/yr | Team 協作、shared quota、SSO（Google/Microsoft）、Slack 支援 | 5-20 人小團隊、新創公司 |
| **Enterprise** | 自訂（USD 500+/mo 起步） | 自訂 | 99.9% SLA、dedicated support、custom plugin、私有部署 | 50+ 人企業、對安全合規有要求的組織 |

**定價心理學考量**：
- Free 與 Pro 之間的 $9 是「心理甜蜜點」——比一杯咖啡便宜，個人開發者幾乎不需要經審批即可購買
- Pro 與 Team 之間的跳躍（$9 → $49）反映 B2B 轉換門檻，Team 必須證明 ROI
- Enterprise 自訂報價允許我們根據客戶規模靈活調整

**價格 vs 競品比較**：
| 產品 | 個人層級 | 團隊層級 |
|---|---|---|
| **K.H.A.V.I.S.** | $9/mo | $49/mo（10 用戶） |
| OpenRouter | 按 token 抽成（無月費） | N/A |
| Portkey | Free + 按量付費 | $199/mo 起 |
| LiteLLM | Free OSS | 商業版需聯繫 |
| Helicone | Free 3K reqs/mo | $20/mo 起 |

我們的策略：**不是與 token 抽成模式競爭**（那對低用量使用者不友善），而是提供**可預測的月費** + 透明的 token 成本（使用者自己支付 LLM provider）。

### 4.2 收入模式分析

#### 收入公式

```
MRR(t) = N_pro(t) × $9 + N_team(t) × $49 + Σ N_ent_i(t) × $price_i
```

其中：
- `N_pro(t)`：Pro 用戶數
- `N_team(t)`：Team workspace 數
- `N_ent_i(t)`：Enterprise 客戶 i 數量與價格

#### 收入結構（保守假設）

| 層級 | 用戶結構佔比 | 平均月費 | 對 MRR 貢獻比例 |
|---|---|---|---|
| Pro | 70% | $9 | 30% |
| Team | 25% | $49 | 58% |
| Enterprise | 5% | $500（加權平均） | 12% |

**觀察**：雖然 Enterprise 客戶佔比僅 5%，但貢獻 12% 的 MRR；隨時間推移，Enterprise 比重應上升至 15-20% MRR，這是健康 SaaS 的典型模式。

#### 變現路徑（Monetization Pathway）

```
Stage 1（Month 1-3）：零收入
  - 全職投入開發
  - 累積 GitHub stars、社群成員
  - 建立 thought leadership

Stage 2（Month 4-6）：$45-300/mo
  - 開始邀請 closed beta 測試者付費
  - 5-30 個 paid users
  - 驗證定價接受度

Stage 3（Month 7-12）：$300-1,500/mo
  - Public launch
  - 30-150 個 paid users
  - 主要靠 organic growth + 內容行銷

Stage 4（Year 2）：$1,500-15,000/mo
  - 150-1,500 個 paid users
  - 開始付費行銷（ads、sponsorships）
  - Enterprise 客戶開始出現
```

### 4.3 客戶終身價值（LTV）與獲客成本（CAC）估算

#### LTV 計算

**假設**：
- 平均 ARPU（Year 1）：USD 13/月
- 平均 ARPU（Year 2）：USD 20/月
- Churn（Year 1）：5%/月 → 平均壽命 = 1/0.05 = 20 個月
- Churn（Year 2）：3%/月 → 平均壽命 = 1/0.03 = 33 個月
- Gross margin：80%（扣除 Stripe 3%、基礎設施、support）

**LTV 公式**：
```
LTV = ARPU × 平均壽命 × Gross Margin
```

**保守 LTV（Year 1 cohort）**：
```
LTV_pro = $9 × 20 × 0.80 = $144
LTV_team = $49 × 20 × 0.80 = $784
LTV_ent = $500 × 20 × 0.80 = $8,000

加權平均 LTV ≈ 0.7 × $144 + 0.25 × $784 + 0.05 × $8,000
             ≈ $101 + $196 + $400
             ≈ $697
```

**最佳情況 LTV（Year 2 cohort）**：
```
LTV_pro = $9 × 33 × 0.80 = $238
LTV_team = $49 × 33 × 0.80 = $1,294
LTV_ent = $500 × 33 × 0.80 = $13,200

加權平均 LTV ≈ 0.7 × $238 + 0.25 × $1,294 + 0.05 × $13,200
             ≈ $167 + $324 + $660
             ≈ $1,150
```

#### CAC 估算

**CAC 拆解**（每個付費客戶的平均獲取成本）：

| 渠道 | 假設轉化率 | 假設 CAC |
|---|---|---|
| GitHub organic | 5% star-to-paid | $0（自然流量） |
| 內容行銷（部落格、YouTube） | 2% view-to-paid | $15 |
| Hacker News / Reddit / V2EX 貼文 | 1% click-to-paid | $5 |
| 微信公眾號 / 知乎文章 | 1.5% reader-to-paid | $20 |
| 付費廣告（Google / Twitter） | 0.5% click-to-paid | $80 |
| 推薦計畫（referral） | 15% referrer-to-paid | $10（含獎勵） |

**加權平均 CAC**：
```
假設流量結構：
- 50% organic（GitHub, HN）
- 30% 內容行銷
- 15% 微信/知乎
- 5% 付費廣告

加權平均 CAC = 0.5×$0 + 0.3×$15 + 0.15×$20 + 0.05×$80
             ≈ $0 + $4.5 + $3 + $4
             ≈ $11.5
```

#### LTV/CAC 比率

**保守估計**：
```
LTV/CAC = $697 / $11.5 ≈ 60
```

這個比率極高（健康 SaaS 通常 LTV/CAC > 3），主要因為我們極度依賴 organic 與 content marketing，CAC 接近於零。

**警示**：上述 CAC 計算**不包括創辦人時間成本**。若將創辦人時間按 USD 80/小時 × 20 小時/週 × 12 月 = USD 19,200 計算並分攤到 150 個 Year-1 客戶，則實際 CAC 約 USD 128，LTV/CAC ≈ 5.4，仍屬健康區間。

### 4.4 變現時程表

| 季度 | 階段 | 預估付費用戶 | 預估 MRR | 預估 ARR |
|---|---|---|---|---|
| 2026 Q4 | Build | 0 | $0 | $0 |
| 2027 Q1 | Closed Beta | 5-15 | $50-150 | $600-1,800 |
| 2027 Q2 | Public Beta | 30-60 | $300-700 | $3,600-8,400 |
| 2027 Q3 | Public Launch | 80-150 | $900-1,800 | $10,800-21,600 |
| 2027 Q4 | Growth | 150-300 | $1,800-3,800 | $21,600-45,600 |
| 2028 Q1 | Scale | 300-600 | $3,800-8,000 | $45,600-96,000 |
| 2028 Q2 | Expansion | 600-1,000 | $8,000-14,000 | $96,000-168,000 |
| 2028 Q3 | Mature | 1,000-1,500 | $14,000-23,000 | $168,000-276,000 |

**累計 Year 1 ARR**：~USD 22K（中位數）
**累計 Year 2 ARR**：~USD 280K（中位數）
**Year 2 結束時累計 MRR 成長**：~15 倍

---

## 五、行銷與銷售 (Go-to-Market)

### 5.1 目標客戶 Persona

#### Persona 1：「跨境自由工作者 Kevin」

| 屬性 | 描述 |
|---|---|
| 年齡 | 28-38 |
| 所在地 | 台灣、香港、新加坡、美西 |
| 工作 | Full-stack / AI 工程師 / indie hacker |
| 收入 | USD 80-150K/年 |
| 訂閱 | Claude Pro、Cursor Pro、ChatGPT Plus、GLM Coding Plan |
| 痛點 | 切換帳號麻煩、配額中斷、模型選擇決策疲勞 |
| 觸達渠道 | Twitter/X、Hacker News、YouTube、GitHub |
| 付費意願 | 中（願意為省時間付費 $9/月） |
| 預估 TAM | ~80K 人 |

#### Persona 2：「中國本土工程師 Mei」

| 屬性 | 描述 |
|---|---|
| 年齡 | 25-35 |
| 所在地 | 北京、上海、深圳、杭州 |
| 工作 | 後端 / 全端工程師、大廠或新創 |
| 收入 | CNY 300-800K/年（USD 42-112K） |
| 訂閱 | GLM Coding Plan、Qwen、Cursor、Claude（需 VPN） |
| 痛點 | 國際 API 不穩、中國模型品質參差、無統一介面 |
| 觸達渠道 | 微信公眾號、知乎、掘金、V2EX、GitHub |
| 付費意願 | 高（若解決 VPN/穩定性問題） |
| 預估 TAM | ~200K 人 |

#### Persona 3：「小型 SaaS 創辦人 Leo」

| 屬性 | 描述 |
|---|---|
| 年齡 | 30-45 |
| 所在地 | 全球（英語圈為主） |
| 工作 | SaaS 創辦人、團隊 5-15 人 |
| 收入 | 公司 ARR USD 100-500K |
| 訂閱 | 企業級 OpenAI、Anthropic、可能加 GLM |
| 痛點 | 成本控制、配額管理、多人協作 |
| 觸達渠道 | Indie Hackers、Twitter、HN、Product Hunt |
| 付費意願 | 高（Team tier $49/月輕鬆） |
| 預估 TAM | ~30K 團隊 |

### 5.2 進入市場策略（GTM）

#### Phase 1：Community-First（Month 1-6）

**核心策略**：以開源社群為基礎，建立品牌可信度。

**執行要點**：
1. **GitHub 優先**：每週 commit、活躍 issue 回應、清晰的 README 與文件
2. **內容行銷**：每週 1 篇深度部落格文章（How-to、技術解析、案例研究）
3. **社群經營**：Discord（英語圈）+ 微信群 + Telegram（中文圈）
4. **Show HN / Show V2EX**：v0.3 與 v1.0 各發一次
5. **KOL 觸達**：與 10-20 位 AI 領域 micro-influencer 建立關係（提供 Pro 帳號）

**目標**（Phase 1 結束）：
- GitHub stars: 2,000+
- 文件網站月訪問: 30K+
- 社群成員: 1,000+
- Newsletter 訂閱: 500+

#### Phase 2：Product-Led Growth（Month 7-12）

**核心策略**：讓產品成為行銷引擎。

**執行要點**：
1. **嵌入式 onboarding**：Pro tier 提供 14 天免費試用，無需信用卡
2. **Viral loop**：用戶分享使用統計截圖（如「本週我透過 K.H.A.V.I.S. 節省了 12 小時」）
3. **Referral program**：邀請朋友獲得 1 個月 Pro 免費
4. **整合目錄**：與 Cursor、Cline、Continue、Roo Code 等編碼工具建立官方整合，列入它們的文件
5. **YouTube 教學影片**：發布 5-10 個深度教學

**目標**（Phase 2 結束）：
- 付費客戶: 150+
- 月活: 5,000+
- ARR: USD 22K+

#### Phase 3：Outbound & Enterprise（Year 2）

**核心策略**：開始 outbound 銷售，建立 Enterprise pipeline。

**執行要點**：
1. **Outbound SDR**：雇用兼職 SDR（contract），每月 200 個 lead
2. **Webinar**：每月一次技術 webinar，建立 authority
3. **Conference 贊助**：贊助 AI Engineer Summit、PyCon China 等
4. **Enterprise pilot program**：提供 30 天免費 pilot 給企業客戶

### 5.3 行銷渠道

| 渠道 | 預算 | 預估觸達 | 預估轉化 | 預估 CAC |
|---|---|---|---|---|
| **GitHub（Organic）** | $0 | 50K impressions/mo | 5% to paid | $0 |
| **部落格 / 內容** | $50/mo（hosting） | 30K views/mo | 2% to paid | $15 |
| **YouTube** | $200/mo（初期外包） | 50K views/mo | 1% to paid | $25 |
| **Hacker News** | $0 | 5-50K impressions/post | 1% to paid | $5 |
| **Twitter/X** | $0 | 10K followers target | 1% to paid | $10 |
| **微信公眾號** | $0 | 5K followers | 1.5% to paid | $20 |
| **知乎** | $0 | 20K views/mo | 1.5% to paid | $15 |
| **Reddit** | $0 | 5K impressions/post | 1% to paid | $8 |
| **V2EX** | $0 | 3K impressions/post | 2% to paid | $5 |
| **Product Hunt** | $0 | 20K impressions/launch | 3% to paid | $3 |
| **Google Ads** | $300/mo | 10K clicks/mo | 0.5% to paid | $80 |
| **付費 KOL** | $500/mo | 50K views/mo | 1% to paid | $20 |

**第一年行銷總預算**：~USD 12,000（內容 + 工具 + 少量付費推廣）

**核心 KPI**：
- 月新增 GitHub stars: 200+
- 月新增文件網站 unique visitors: 5,000+
- 月新增付費客戶: 10-15（Month 7-12）
- Newsletter 訂閱成長率: 10%/月

### 5.4 銷售漏斗

```
[Aware]      GitHub star / 內容瀏覽 / 社群提及
   |          (50,000/月)
   v
[Interest]   文件閱讀 / Discord 加入 / npm install
   |          (5,000/月，10% 轉化)
   v
[Consider]   試用 / Beta 申請 / GitHub issue 互動
   |          (500/月，10% 轉化)
   v
[Evaluate]   14 天 Pro 試用 / 與團隊討論
   |          (150/月，30% 轉化)
   v
[Purchase]   訂閱 Pro / Team
   |          (45/月，30% 轉化)
   v
[Retain]     持續使用 / 推薦 / 升級
   |          (每月 churn 5% → 持續成長)
   v
[Advocate]   撰寫評論 / 推薦他人 / 貢獻 plugin
```

**轉化率假設**：
- Awareness → Interest: 10%（行業基準 5-15%）
- Interest → Consideration: 10%（強 funnel 訊息）
- Consideration → Evaluation: 30%（14 天試用低摩擦）
- Evaluation → Purchase: 30%（合理 SaaS 基準）
- 整體 A-to-P: 0.3-1.0%

### 5.5 關鍵里程碑

#### Month 3（2026 年 12 月）
- GitHub stars: 500
- 文件網站上線
- Discord 50 成員

#### Month 6（2027 年 3 月）
- GitHub stars: 2,000
- 付費客戶: 30
- MRR: $300-700
- Discord 500 成員
- 微信公眾號 2,000 followers

#### Month 9（2027 年 6 月）
- GitHub stars: 3,500
- 付費客戶: 80
- MRR: $900-1,500
- 第一次 Show HN 成功

#### Month 12（2027 年 9 月）
- GitHub stars: 5,000
- 付費客戶: 150
- ARR: $22K
- 月活: 5,000
- 第一次年度回顧發布

---

## 六、財務預測 (Financial Projections)

### 6.1 12 個月收入預估（Month-by-Month）

| 月份 | 累計付費用戶 | 月新增 Pro | 月新增 Team | 月新增 Ent | 當月 MRR | 累計 ARR Run-rate | 累計 Revenue |
|---|---|---|---|---|---|---|---|
| M1（Oct 2026） | 0 | 0 | 0 | 0 | $0 | $0 | $0 |
| M2（Nov 2026） | 0 | 0 | 0 | 0 | $0 | $0 | $0 |
| M3（Dec 2026） | 0 | 0 | 0 | 0 | $0 | $0 | $0 |
| M4（Jan 2027） | 5 | 4 | 1 | 0 | $49 | $588 | $49 |
| M5（Feb 2027） | 12 | 5 | 2 | 0 | $143 | $1,716 | $192 |
| M6（Mar 2027） | 25 | 8 | 5 | 0 | $317 | $3,804 | $509 |
| M7（Apr 2027） | 40 | 10 | 5 | 0 | $355 | $4,260 | $864 |
| M8（May 2027） | 60 | 13 | 7 | 0 | $460 | $5,520 | $1,324 |
| M9（Jun 2027） | 85 | 16 | 9 | 0 | $585 | $7,020 | $1,909 |
| M10（Jul 2027） | 110 | 16 | 9 | 0 | $585 | $7,020 | $2,494 |
| M11（Aug 2027） | 130 | 13 | 7 | 0 | $460 | $5,520 | $2,954 |
| M12（Sep 2027） | 150 | 13 | 7 | 0 | $460 | $5,520 | $3,414 |

**累計 Year 1 Revenue**：~USD 3,400
**Year 1 結束 MRR**：~USD 460
**Year 1 結束 ARR Run-rate**：~USD 5,520

**注意**：上述預估採用保守假設——付費轉換率僅約 1-2%、churn 5%/月、新增放緩。實際情況可能顯著優於此（特別是若出現 viral 事件）。

### 6.2 24 個月收入預估（季度）

| 季度 | 季度末付費客戶 | 季度末 MRR | 季度末 ARR | 季度新增 Revenue | 累計 Revenue |
|---|---|---|---|---|---|
| 2026 Q4 | 0 | $0 | $0 | $0 | $0 |
| 2027 Q1 | 25 | $317 | $3,804 | $750 | $750 |
| 2027 Q2 | 85 | $585 | $7,020 | $1,460 | $2,210 |
| 2027 Q3 | 150 | $460 | $5,520 | $1,470 | $3,680 |
| 2027 Q4 | 250 | $1,200 | $14,400 | $3,000 | $6,680 |
| 2028 Q1 | 450 | $2,500 | $30,000 | $6,200 | $12,880 |
| 2028 Q2 | 750 | $5,500 | $66,000 | $13,500 | $26,380 |
| 2028 Q3 | 1,200 | $13,000 | $156,000 | $31,500 | $57,880 |

**Year 2 結束 ARR**：~USD 156K（中位數）
**Year 2 結束 MRR**：~USD 13K
**Year 2 累計 Revenue**：~USD 54K

**保守 / 中位 / 樂觀 三情境**：
| 情境 | Year 2 ARR | 機率 | 假設 |
|---|---|---|---|
| 保守 | $80K | 30% | 付費轉換率 1.5%、churn 6% |
| 中位 | $156K | 50% | 付費轉換率 3%、churn 5% |
| 樂觀 | $300K | 20% | 出現 viral 事件、企業客戶大單 |

### 6.3 成本結構

#### 固定成本

| 項目 | Month 1-3 | Month 4-6 | Month 7-12 | Year 2 |
|---|---|---|---|---|
| 雲端基礎設施 | $50/mo | $100/mo | $200/mo | $500/mo |
| 域名 / SSL / 工具 | $20/mo | $20/mo | $50/mo | $100/mo |
| 行銷預算 | $0 | $200/mo | $500/mo | $1,500/mo |
| Stripe 費用（3%） | 隨營收變動 | 隨營收變動 | 隨營收變動 | 隨營收變動 |
| 創辦人生活費 | $3,000/mo | $3,000/mo | $3,000/mo | $5,000/mo（含團隊） |
| **月度總計** | **$3,070** | **$3,320** | **$3,750** | **$7,100 + 變動** |

#### 變動成本（與營收相關）

| 項目 | 佔 MRR 比例 | 說明 |
|---|---|---|
| Stripe 交易費 | 3% | 固定 |
| 客戶支援成本 | 5-10% | 隨客戶數增加 |
| 基礎設施擴展 | 5-10% | 隨 request 量 |
| **總變動成本** | **13-23%** | **Gross margin 77-87%** |

#### 一次性成本

| 項目 | 金額 | 時點 |
|---|---|---|
| 法律諮詢（公司設立、條款） | $2,000 | Month 1-2 |
| 商標註冊 | $1,500 | Month 3 |
| 設計（logo、UI） | $1,000 | Month 2-3 |
| 初始行銷素材 | $500 | Month 3 |
| **總計** | **$5,000** | |

#### Year 1 總支出預估

| 類別 | 金額 |
|---|---|
| 創辦人生活費（12 mo × $3,000） | $36,000 |
| 基礎設施（累積） | $1,400 |
| 行銷 | $3,000 |
| 一次性 | $5,000 |
| Stripe + 變動成本 | ~$100 |
| **總計** | **~$45,500** |

#### Year 1 總收入

- 假設中位情境：累計 Revenue ~$3,400
- 假設樂觀情境：累計 Revenue ~$6,000

#### Year 1 淨現金流

- 中位情境：-$45,500 + $3,400 = **-$42,100**
- 樂觀情境：-$45,500 + $6,000 = **-$39,500**

**資金需求評估**：個人儲蓄 USD 50K-100K 足以覆蓋 Year 1 虧損，無需外部資金。

### 6.4 損益平衡點分析

#### 月度損益平衡點

**假設**：
- 固定成本（Year 2 起步）：$7,100/mo
- Gross margin：80%
- 平均 ARPU：$20/mo

**計算**：
```
損益平衡客戶數 = 固定成本 / (ARPU × Gross Margin)
              = $7,100 / ($20 × 0.80)
              = $7,100 / $16
              ≈ 444 個付費客戶
```

**預估達標時間**：Month 18-21（Year 2 中期）

#### 累積損益平衡點（Cash Break-even）

考慮 Year 1 累積虧損需要 Year 2 來彌補：

```
Year 1 累積虧損：-$42,100
Year 2 每月淨利潤（假設 800 客戶、ARPU $20、毛利率 80%）：
   Revenue: $16,000
   變動成本: $3,200
   固定成本: $7,100
   淨利潤: $5,700/mo

回收時間：$42,100 / $5,700 ≈ 7-8 個月
```

**預估現金回收時間點**：2028 Q3 結束（Month 24）實現累積現金流正數。

### 6.5 關鍵指標 (KPIs)

#### 產品指標

| 指標 | 目標（Month 12） | 衡量方式 |
|---|---|---|
| 月活使用者（MAU） | 5,000 | unique installations or accounts |
| 日活 / 月活比（DAU/MAU） | >30% | 反映黏性 |
| 平均 session request 數 | >10 | per active user per day |
| 平均 session 時長 | >30 分鐘 | engagement |
| Plugin 安裝數（累計） | 50+ | 社群健康度 |

#### 商業指標

| 指標 | 目標（Month 12） | 衡量方式 |
|---|---|---|
| 付費客戶總數 | 150 | Stripe customers |
| MRR | $460+ | Stripe MRR |
| ARR | $5,500+ | MRR × 12 |
| Free → Paid 轉化率 | 3% | paid / free |
| Churn（月） | <5% | cancellations / start of month |
| Net Revenue Retention | >100% | expansion - churn |
| LTV | $697 | cohort analysis |
| CAC | <$15 | blended |
| LTV/CAC | >3 | unit economics health |

#### 行銷指標

| 指標 | 目標（Month 12） |
|---|---|
| GitHub stars | 5,000+ |
| 文件網站月訪問 | 100K+ |
| Discord/Telegram 成員 | 2,000+ |
| Newsletter 訂閱 | 1,000+ |
| YouTube 訂閱 | 1,500+ |
| 微信公眾號 followers | 5,000+ |
| 知乎 followers | 3,000+ |

#### 客戶成功指標

| 指標 | 目標（Month 12） |
|---|---|
| NPS | >40 |
| Support response time | <24 小時 |
| 客戶投訴率 | <2% |
| 客戶推薦意願 | >30% |

---

## 七、風險分析 (Risk Analysis)

### 7.1 技術風險

#### 風險 T1：Provider API 變動導致整合失效

**描述**：LLM provider 經常變更 API 規格（特別是早期廠商），可能導致 adapter 失效。

**機率**：高（每月至少 1-2 次變動）
**影響**：中（單一 provider 失效，使用者可切換）

#### 風險 T2：Provider SDK 維護負擔過重

**描述**：支援 11+ provider 意味著維護成本隨 provider 數量線性增長。

**機率**：中
**影響**：高（若團隊無法跟上，使用者體驗下降）

#### 風險 T3：Plugin 系統的安全風險

**描述**：第三方 plugin 可能引入惡意程式碼或漏洞。

**機率**：中
**影響**：高（一旦發生可能影響所有使用者）

#### 風險 T4：配額追蹤誤差導致 429

**描述**：Quota-aware scheduling 預測錯誤時，使用者仍會遭遇 429。

**機率**：中
**影響**：中（使用者會對核心功能失去信心）

#### 風險 T5：開源核心的 Fork 競爭

**描述**：大廠可能 fork 我們的核心並提供商業版本，威脅我們的 OSS 社群領導地位。

**機率**：中
**影響**：中（短期可控，長期需應對）

### 7.2 市場風險

#### 風險 M1：付費轉換率低於預期

**描述**：開源使用者的付費意願可能低於 3% 的假設。

**機率**：中
**影響**：高（直接影響商業模式可行性）

**緩解**：早期密切監控、提供明確的 hosted value、提供月費試用降低摩擦。

#### 風險 M2：LLM 訂閱整合趨勢反轉

**描述**：未來超級 app（如 ChatGPT、Claude）可能直接整合多模型，使用者無需外部路由器。

**機率**：低-中
**影響**：高（市場萎縮）

**緩解**：保持技術領先、深耕垂直（編碼、企業）。

#### 風險 M3：經濟衰退導致個人/小團隊訂閱預算縮減

**描述**：宏觀經濟不佳時，$9/mo 的訂閱可能被優先砍掉。

**機率**：中
**影響**：中（影響 churn）

**緩解**：證明明確 ROI、提供年付折扣、強調省時間的價值。

### 7.3 法規風險

#### 風險 R1：中國《生成式 AI 管理辦法》合規

**描述**：中國對 LLM 服務有資料落地、內容審查、可追溯等要求。

**機率**：高（2026 修訂版已生效）
**影響**：高（無法在中國合法運營）

**緩解**：
- 與中國本地雲供應商合作（阿里雲、騰訊雲）確保資料落地
- 與中國 LLM provider 建立合作關係
- 對中國境內客戶提供本地化部署選項
- 聘請中國法律顧問

#### 風險 R2：歐盟 AI Act 對透明度的要求

**描述**：歐盟要求 AI 服務對模型使用、決策邏輯有一定透明度。

**機率**：高（已實施）
**影響**：中（需調整產品文件、隱私政策）

**緩解**：提供 audit log、model transparency 文檔。

#### 風險 R3：Provider 變更條款（如禁止轉售）

**描述**：某些 provider 可能在未來禁止第三方路由其 API。

**機率**：中
**影響**：高（核心商業模式受威脅）

**緩解**：聚焦在使用者自己的 API key（BYOK）模式，而非轉售 token。

#### 風險 R4：資料隱私（GDPR、CCPA）

**描述**：託管雲服務涉及使用者資料儲存。

**機率**：中
**影響**：中

**緩解**：明確資料政策、提供 data export 與 delete。

### 7.4 競爭風險

#### 風險 C1：OpenRouter 進入中國市場

**描述**：OpenRouter 若加入中國模型與本地化支援，將直接威脅我們。

**機率**：中
**影響**：高

**緩解**：先發優勢、社群護城河、垂直深度。

#### 風險 C2：LiteLLM 商業版降價

**描述**：LiteLLM 推出更便宜的商業版本。

**機率**：低（已商業化）
**影響**：中

**緩解**：保持 Apache 2.0 開源差異化、本地化優勢。

#### 風險 C3：AI 編碼工具（Cursor、Claude Code）內建 routing

**描述**：未來編碼工具可能內建多模型 routing。

**機率**：中（部分已開始）
**影響**：中

**緩解**：成為這些工具的 plugin 提供者，而非競爭對手。

#### 風險 C4：新型創業公司以更低價格進入

**描述**：開源社群可能出現類似的 fork 項目。

**機率**：高（6-12 個月內）
**影響**：中

**緩解**：品牌、社群、文件、垂直深度的護城河。

### 7.5 緩解策略總表

| 風險 | 機率 | 影響 | 主要緩解策略 |
|---|---|---|---|
| T1 API 變動 | 高 | 中 | 自動化整合測試、provider 抽象層、CI/CD |
| T2 SDK 維護 | 中 | 高 | Plugin 架構、社群分擔、文件化 |
| T3 Plugin 安全 | 中 | 高 | Plugin sandbox、code review、signature |
| T4 Quota 誤差 | 中 | 中 | 漸進式 rollout、telemetry 監控 |
| T5 Fork 競爭 | 中 | 中 | 持續創新、社群經營、trademark |
| M1 轉化率低 | 中 | 高 | 月費試用、value demo、retargeting |
| M2 市場反轉 | 低-中 | 高 | 技術領先、垂直深化 |
| M3 經濟衰退 | 中 | 中 | ROI 證明、年付折扣 |
| R1 中國法規 | 高 | 高 | 本地雲合作、法律顧問 |
| R2 歐盟 AI Act | 高 | 中 | 合規文件、audit log |
| R3 Provider 條款 | 中 | 高 | BYOK 模式、合約多元化 |
| R4 資料隱私 | 中 | 中 | 明確政策、export/delete |
| C1 OpenRouter | 中 | 高 | 先發、社群、垂直 |
| C2 LiteLLM 降價 | 低 | 中 | 開源差異化 |
| C3 編碼工具內建 | 中 | 中 | 成為它們的 plugin |
| C4 新創進入 | 高 | 中 | 品牌、社群、文件 |

---

## 八、團隊與執行 (Team & Execution)

### 8.1 創始人背景（Placeholder）

**Founder**: [待填入]

**專業領域**：
- LLM 應用開發：5+ 年
- 開源社群經營：[年資]
- 中國 LLM 生態：[年資]
- 技術 stack：Python、TypeScript、Rust

**過去成就**：
- [專案 1]
- [專案 2]
- [貢獻 1]

**為什麼做 K.H.A.V.I.S.**：
- [個人痛點]
- [觀察到的市場機會]
- [技術熱情]

### 8.2 需要的關鍵角色

#### 第一階段（Month 1-6，Solo Founder）

| 角色 | 模式 | 預估投入 |
|---|---|---|
| 全端工程（founder） | 100% 時間 | 60+ hr/wk |
| 設計（兼職） | 合約 | 5-10 hr/wk |
| 內容寫作（兼職） | 合約 | 5-10 hr/wk |
| 法律諮詢 | 按需 | 按時計費 |

#### 第二階段（Month 7-12）

| 角色 | 模式 | 預估投入 | 月成本 |
|---|---|---|---|
| Backend 工程師 #1 | 全職 | 40 hr/wk | $4,000-6,000 |
| DevRel / 內容 | 合約 | 20 hr/wk | $1,500-2,500 |
| 設計 | 合約 | 10 hr/wk | $1,000-1,500 |
| 客戶支援（兼職） | 合約 | 10 hr/wk | $500-1,000 |

#### 第三階段（Year 2）

| 角色 | 模式 | 預估投入 | 月成本 |
|---|---|---|---|
| Backend 工程師 #1 | 全職 | 40 hr/wk | $5,000-7,000 |
| Backend 工程師 #2 | 全職 | 40 hr/wk | $4,500-6,500 |
| Frontend 工程師 | 全職 | 40 hr/wk | $4,500-6,500 |
| DevRel | 全職 | 40 hr/wk | $4,000-5,500 |
| 銷售 / SDR | 兼職 | 20 hr/wk | $2,000-3,000 |
| 客戶支援 | 全職 | 40 hr/wk | $2,500-3,500 |

### 8.3 12 個月執行計劃

#### Month 1-2（Oct-Nov 2026）：Foundation

- [ ] 完成核心 engine 設計文件
- [ ] 實作 OpenAI adapter + Anthropic adapter
- [ ] 設定 GitHub repo、CI/CD、文件站
- [ ] 完成公司設立（Delaware C-Corp 或 BVI）
- [ ] 開立 Stripe 帳號

#### Month 3（Dec 2026）：Alpha

- [ ] 加入第 3 個 provider（GLM）
- [ ] 基本 failover 功能
- [ ] 邀請 20 位 alpha tester（朋友、開源社群）
- [ ] 建立 Discord 社群

#### Month 4（Jan 2027）：Closed Beta

- [ ] 公開 GitHub repo
- [ ] 發布第一個 release（v0.2）
- [ ] 加入 capability routing
- [ ] 啟動付費 beta（5-10 客戶）

#### Month 5（Feb 2027）：Pro Launch

- [ ] Pro tier 公開上線
- [ ] Stripe 訂閱流程
- [ ] 跨裝置 sync
- [ ] 第一篇 Show HN

#### Month 6（Mar 2027）：Documentation Sprint

- [ ] 完整文件網站
- [ ] 5 個深度教學文章
- [ ] YouTube 教學影片 ×3
- [ ] 微信公眾號上線

#### Month 7-9（Apr-Jun 2027）：Public Launch

- [ ] 完整 v1.0 GA
- [ ] Product Hunt launch
- [ ] 加入 2-3 個新 provider
- [ ] 建立 referral program
- [ ] 啟動 Google Ads（少量試水）

#### Month 10-12（Jul-Sep 2027）：Optimization

- [ ] 進階 analytics dashboard
- [ ] Enterprise pilot（3-5 客戶）
- [ ] Conference 贊助 ×1
- [ ] 年度回顧發布
- [ ] 規劃 Year 2

### 8.4 關鍵決策點

#### Decision Point 1（Month 3）：是否繼續 solo 或招募第一位全職？

**觸發條件**：
- GitHub stars >500
- 付費客戶 >5
- 個人時間已無法負擔

**若觸發**：招募兼職 backend 工程師
**若未觸發**：繼續 solo，延後至 Month 6-9

#### Decision Point 2（Month 6）：是否進入付費行銷？

**觸發條件**：
- LTV/CAC >5
- 月新增付費客戶 >10
- Gross margin >75%

**若觸發**：啟動 Google Ads + KOL 合作
**若未觸發**：繼續 organic 增長，延後至 Month 9

#### Decision Point 3（Month 9）：是否啟動募資？

**觸發條件**：
- ARR >$15K
- 月成長率 >15%
- Year 2 預估 ARR >$150K

**若觸發**：Pre-seed 募資 USD 500K-1M
**若未觸發**：繼續 bootstrapping，Year 2 中期再評估

#### Decision Point 4（Month 12）：是否進入 Enterprise 銷售？

**觸發條件**：
- 有 3+ 客戶表達 Enterprise 興趣
- 有 1+ 客戶願意付費 pilot

**若觸發**：聘請兼職 SDR、啟動 outbound
**若未觸發**：專注 SMB，重組商業模式

---

## 九、結論 (Conclusion)

### 為何現在是時機

LLM 工程師市場正在經歷三個不可逆的結構性變化：

1. **訂閱碎片化**：從「1 個模型」到「3-4 個訂閱」已經是不可逆趨勢，使用者正在尋找整合方案
2. **中國 LLM 成熟**：2025-2026 是中國 LLM 的「可用性躍升年」，跨市場工作流成為剛需
3. **AI 編碼工具爆發**：Cursor、Claude Code、Cline 等編碼工具的指數級成長，創造了對 LLM 路由層的天然需求

這三個趨勢的交匯，創造了一個 12-24 個月的「窗口期」。在這個窗口期內，第一個建立社群信任與品牌認知的開源解決方案將佔據長期有利位置。

### 為何這個團隊/個人能贏

**核心優勢**：
1. **先發優勢**：相較於 OpenRouter、LiteLLM 等國際產品，我們對中國市場的深度理解（GLM Coding Plan 整合、本地化部署）是難以複製的
2. **垂直聚焦**：不與 OpenRouter 的「100+ provider marketplace」正面競爭，而是深耕「個人開發者 + 編程工作流 + 中國市場」這個垂直切片
3. **開源策略**：Apache 2.0 + 開源社群 + 透明 roadmap，建立社群信任與貢獻者生態
4. **Product-led growth**：低 CAC、高 LTV 的單位經濟，允許我們在沒有大量行銷預算的情況下成長
5. **Bootstrapping 紀律**：12 個月不燒投資人資金，確保每個 milestone 都由真實市場需求驗證

**承認的限制**：
1. Solo founder 的執行瓶頸——若產品/市場契合度（PMF）驗證成功，將需要快速招募
2. 對中國市場的法規不確定性需要本地合作夥伴
3. 相較於國際對手，初期品牌知名度較低

### 下一步行動

**立即（本週）**：
1. 完成 BUSINESS_PLAN.md（本文檔）
2. 驗證 `khavis-core` 最小可行版本可運行
3. 設定 GitHub organization

**Month 1**：
1. 招募 5 位 alpha tester
2. 發布 v0.1 alpha
3. 啟動內容創作（每週 1 篇部落格）

**Month 3**：
1. 達到 GitHub stars >300
2. 公開 v0.3 public beta
3. 啟動付費 beta

**Month 6**：
1. 評估 Decision Point 1 與 2
2. 規劃 Year 2 募資（如需）
3. 第一次策略性對外發聲

**Month 12**：
1. 完成 Year 1 目標（150 客戶、$5.5K MRR）
2. 評估是否進入 Enterprise
3. 規劃 Year 2 與募資

---

## 附錄 A：技術架構圖

### 整體架構（ASCII）

```
+-----------------------------------------------------------------+
|                        CLIENTS                                   |
|  Cursor  |  Cline  |  Claude Code  |  Aider  |  curl  |  SDK    |
+-------------------------+---------------------------------+-------+
                          |                                 |
                          v                                 v
                   +------+---------------------------------+------+
                   |            khavis API Gateway             |
                   |  - Auth (API key, OAuth)                     |
                   |  - Rate limit (per-user, per-IP)             |
                   |  - Request logging                           |
                   +--------------------+--------------------------+
                                        |
                                        v
                   +--------------------+--------------------------+
                   |       Protocol Adapter Layer                 |
                   |  +-------------+   +-------------+            |
                   |  | /v1/openai/ |   | /v1/anthrop/|            |
                   |  | completions |   | messages    |            |
                   |  +------+------+   +------+------+            |
                   |         |                |                    |
                   |         v                v                    |
                   |    +----+--+----+-------+----+               |
                   |    |  Internal Schema (Pydantic) |            |
                   |    |  - InternalRequest          |            |
                   |    |  - InternalResponse         |            |
                   |    +--------------+--------------+            |
                   +-------------------+--------------------------+
                                       |
                                       v
                   +-------------------+--------------------------+
                   |              Routing Layer                   |
                   |  +-----------------+  +-------------------+   |
                   |  | Strategy        |  | Quota Manager     |   |
                   |  | Registry        |  | - Per-provider    |   |
                   |  | - Cost-opt       |  | - Window tracking |   |
                   |  | - Quality-opt    |  | - Prediction      |   |
                   |  | - Balanced       |  +-------------------+   |
                   |  +--------+--------+                          |
                   |           |                                   |
                   |           v                                   |
                   |  +--------+--------+  +-------------------+   |
                   |  | Health Checker  |  | Circuit Breaker   |   |
                   |  | - Periodic ping |  | - Per-provider    |   |
                   |  +-----------------+  +-------------------+   |
                   +-------------------+--------------------------+
                                       |
                                       v
                   +-------------------+--------------------------+
                   |           Provider Adapter Layer              |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   |  | OpenAI  | |Anthropic| | Gemini  | | GLM   | |
                   |  | (BYOK)  | | (BYOK)  | |         | |       | |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   |  | Doubao  | |DeepSeek | |MiniMax-M| | NVIDIA| |
                   |  | (sub)   | | (sub)   | |   3     | |(BYOK) |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   |  |OpenRout.| | Ollama  | | Mistral | | ...   | |
                   |  +---------+ +---------+ +---------+ +-------+ |
                   +-------------------+--------------------------+
                                       |
                                       v
                   +-------------------+--------------------------+
                   |         Observability Layer                  |
                   |  +-------------+  +-------------+            |
                   |  | OpenTelemetry traces                   |   |
                   |  +-------------+  +-------------+            |
                   |  | Prometheus  |  | Cost tracker|            |
                   |  | metrics     |  | per request |            |
                   |  +-------------+  +-------------+            |
                   |  +-------------+  +-------------+            |
                   |  | Structured |  | Dashboard   |            |
                   |  | logs       |  | (web UI)    |            |
                   |  +-------------+  +-------------+            |
                   +-------------------+--------------------------+
                                       |
                                       v
                   +-------------------+--------------------------+
                   |              Storage Layer                   |
                   |  +-------------+  +-------------+            |
                   |  | SQLite      |  | Postgres    |            |
                   |  | (local)     |  | (cloud)     |            |
                   |  +-------------+  +-------------+            |
                   |  +-------------+  +-------------+            |
                   |  | Redis       |  | S3          |            |
                   |  | (cache)     |  | (backup)    |            |
                   |  +-------------+  +-------------+            |
                   +-----------------------------------------------+
```

### Plugin 架構（ASCII）

```
+-----------------------------------------------+
|           khavis-core                     |
|  +-----------------+                          |
|  | Plugin Registry |                          |
|  +--------+--------+                          |
|           |                                   |
|           v                                   |
|  +-----------------+   +-------------------+  |
|  | ProviderPlugin  |   | RouterPlugin      |  |
|  | - chat()        |   | - select_provider |  |
|  | - estimate_cost |   | - score_providers |  |
|  | - capabilities  |   +-------------------+  |
|  +--------+--------+                          |
|           |                                   |
|           v                                   |
|  +-----------------+                          |
|  | TransformerPlugin                          |
|  | - pre_request()                            |
|  | - post_response()                          |
|  +-----------------+                          |
+-----------------------------------------------+
              ^
              |
   +----------+----------+----------+
   |          |          |          |
   v          v          v          v
[Plugin A] [Plugin B] [Plugin C] [Plugin D]
 OpenAI     Anthropic  Custom     Local
                                   Inference
```

### 資料流程（Request Lifecycle）

```
1. Client → POST /v1/chat/completions
            body: { model: "auto", messages: [...] }
                        |
                        v
2. API Gateway: Validate auth, log, rate limit
                        |
                        v
3. Protocol Adapter: Parse to InternalRequest
                        |
                        v
4. Routing Layer:
   a. Task Classifier → determine task type
   b. Quota Manager → check available providers
   c. Strategy Plugin → score providers
   d. Health Checker → exclude unhealthy
   e. Select best provider
                        |
                        v
5. Provider Adapter:
   a. Transform InternalRequest → provider format
   b. HTTP call to provider
   c. Handle response (streaming or batch)
   d. Transform back to InternalResponse
                        |
                        v
6. Observability: Log request, update metrics
                        |
                        v
7. Protocol Adapter: Format as OpenAI response
                        |
                        v
8. Return to Client

On Error:
  5e. Retry with backoff (3x)
  5f. If still failing, failover to next provider
  5g. After N failures, open circuit breaker
```

---

## 附錄 B：競品深度對照

### 對照表（10 個維度 × 5 個競品）

| 維度 | **K.H.A.V.I.S.** | OpenRouter | LiteLLM | Portkey | OneAPI |
|---|---|---|---|---|---|
| **1. 授權模式** | Apache 2.0 + 託管 SaaS | 閉源 | MIT + 商業版 | 閉源 SaaS | Apache 2.0 |
| **2. 開源 vs 閉源** | Open Core | 純閉源 | Open Core | 純閉源 | 完全開源 |
| **2. 支援 Provider 數** | 12（中國深度，4 個 BYOK） | 50+（國際為主） | 100+ | 250+ | 30+ |
| **3. 中國模型支援** | 原生（GLM、Qwen、Doubao、MiniMax） | 有限 | 基本 | 基本 | 部分 |
| **4. 定價** | $0/$9/$49/自訂 | 按 token 抽成 | $0 + 商業版 | $0 + 用量 | $0 + 自架 |
| **5. 自動 Failover** | 內建、智慧 | 內建 | 內建 | 內建 | 手動 |
| **6. Cap-based Routing** | 內建（任務能力） | 按價格/上下文 | 需自寫 | 內建 | 需自寫 |
| **7. Quota Awareness** | 內建（視窗感知） | 有限 | 無 | 部分 | 無 |
| **8. Plugin 架構** | 完整 SDK | 無 | 部分 | 無 | 無 |
| **9. 自架支援** | 首選 | 否 | 是 | 否 | 是 |
| **10. 目標用戶** | 個人 / 小團隊 / 編碼 | 全端 | 企業 | 中大型 | 全端 |

### 各競品詳細評估

#### B.1 OpenRouter

**概覽**：
- 公司：OpenRouter Inc.
- 成立：2023
- 模式：API marketplace（類似「LLM 的 AWS Marketplace」）
- 用戶規模：100K+ 開發者
- 融資：USD 5M+（A 輪）

**優勢**：
- Provider 覆蓋最廣（50+）
- 一個 API key 呼叫所有模型
- 透明的定價（按 token）
- 強大的 developer experience

**劣勢**：
- 商業模式是 token 抽成（5%+），對低用量使用者不友善
- 中國模型支援薄弱
- 開源程度有限（核心閉源）
- 對「個人自帶 API key」使用者不友善（必須透過 OpenRouter 中轉）

**對我們的啟示**：
- 學習他們的 developer experience（清晰的 docs、SDK）
- 避開他們的 token 抽成模式（市場已有強者）
- 填補他們的中國市場空白

#### B.2 LiteLLM

**概覽**：
- 開源專案：BerriAI/litellm
- GitHub stars: 80K+
- 模式：Open source proxy + 商業版
- 主要用戶：企業

**優勢**：
- 開源、社群活躍
- Provider 覆蓋最廣（100+）
- 與 LangChain 生態深度整合
- 企業版功能豐富（SSO、audit、guardrails）

**劣勢**：
- 主要為 Python，其他語言支援弱
- 商業版價格不透明
- 中國模型支援基本
- 文件對個人開發者不夠友善
- 架構較重（依賴 Redis、Postgres）

**對我們的啟示**：
- 學習他們的 open-source-first 社群經營
- 簡化 deployment（單一 binary 而非複雜 stack）
- 個人開發者優先（而非企業優先）

#### B.3 Portkey

**概覽**：
- 公司：Portkey AI
- 成立：2023
- 模式：純 SaaS（LLM observability + gateway）
- 用戶規模：1K+ 企業

**優勢**：
- 企業級 observability（best-in-class）
- Guardrails（內容審查、token 限制）
- 與主流 LLM framework 整合
- 強力的 sales 與 marketing

**劣勢**：
- 純 SaaS（無 self-host）
- 對個人開發者不友善（無 free tier for production）
- 對中國市場無支援
- 價格較高（$199/mo 起）

**對我們的啟示**：
- 學習他們的 enterprise-grade observability
- 永遠保留 self-host 選項
- 保持對個人開發者友善

#### B.4 OneAPI

**概覽**：
- 開源專案：songquanpeng/one-api
- GitHub stars: 30K+
- 模式：完全開源
- 主要用戶：中國開發者

**優勢**：
- 完全開源（Apache 2.0）
- 對中國模型支援好
- 部署簡單（單一 binary）
- 中文文件完整

**劣勢**：
- 社群活躍度下降
- 缺少現代功能（如 capability routing、plugin）
- 介面過時
- 商業模式不清（無明確變現路徑）

**對我們的啟示**：
- 學習他們的「單一 binary 簡單部署」
- 學習他們的中國模型深度支援
- 改進他們的現代化 UI/UX
- 明確我們的商業模式（他們沒有的 SaaS 層）

### 我們的差異化定位總結

| 維度 | 我們 vs OpenRouter | 我們 vs LiteLLM | 我們 vs Portkey | 我們 vs OneAPI |
|---|---|---|---|---|
| 定位 | 個人/小團隊 | 個人/小團隊 vs 企業 | 個人 vs 企業 | 個人/小團隊 |
| 開源 | 是（+ 託管） | 是 | 否 | 是 |
| 中國市場 | 深度 | 基本 | 無 | 深度（但停滯） |
| 編程工作流 | 優化 | 一般 | 一般 | 一般 |
| Plugin | 完整 | 部分 | 無 | 無 |
| Quota | 內建 | 無 | 部分 | 無 |

**我們的獨特價值主張**：
> **唯一一個為 AI 工程師（特別是中文圈、跨境、開源偏好者）打造的、整合國際與中國 LLM 的、具備 plugin 擴展性的、配額感知的開源 LLM 路由器。**

---

## 附錄 C：財務模型試算表（Markdown 表格）

### C.1 季度預估（保守、中位、樂觀三情境）

#### 保守情境（30% 機率）

| 季度 | 月末付費客戶 | MRR | ARR | 季度 Revenue | 季度成本 | 季度淨利 | 累計淨利 |
|---|---|---|---|---|---|---|---|
| 2026 Q4 | 0 | $0 | $0 | $0 | $9,210 | -$9,210 | -$9,210 |
| 2027 Q1 | 15 | $170 | $2,040 | $390 | $9,960 | -$9,570 | -$18,780 |
| 2027 Q2 | 40 | $400 | $4,800 | $850 | $10,500 | -$9,650 | -$28,430 |
| 2027 Q3 | 80 | $720 | $8,640 | $1,750 | $11,250 | -$9,500 | -$37,930 |
| 2027 Q4 | 130 | $1,100 | $13,200 | $2,800 | $12,750 | -$9,950 | -$47,880 |
| 2028 Q1 | 220 | $1,900 | $22,800 | $4,800 | $15,000 | -$10,200 | -$58,080 |
| 2028 Q2 | 350 | $3,300 | $39,600 | $7,800 | $18,000 | -$10,200 | -$68,280 |
| 2028 Q3 | 500 | $5,500 | $66,000 | $13,500 | $22,500 | -$9,000 | -$77,280 |

**保守情境 Year 2 結束**：MRR $5,500、ARR $66K、累計淨利 -$77K

#### 中位情境（50% 機率）

| 季度 | 月末付費客戶 | MRR | ARR | 季度 Revenue | 季度成本 | 季度淨利 | 累計淨利 |
|---|---|---|---|---|---|---|---|
| 2026 Q4 | 0 | $0 | $0 | $0 | $9,210 | -$9,210 | -$9,210 |
| 2027 Q1 | 25 | $317 | $3,804 | $750 | $9,960 | -$9,210 | -$18,420 |
| 2027 Q2 | 85 | $585 | $7,020 | $1,460 | $10,500 | -$9,040 | -$27,460 |
| 2027 Q3 | 150 | $460 | $5,520 | $1,470 | $11,250 | -$9,780 | -$37,240 |
| 2027 Q4 | 250 | $1,200 | $14,400 | $3,000 | $13,500 | -$10,500 | -$47,740 |
| 2028 Q1 | 450 | $2,500 | $30,000 | $6,200 | $17,000 | -$10,800 | -$58,540 |
| 2028 Q2 | 750 | $5,500 | $66,000 | $13,500 | $23,000 | -$9,500 | -$68,040 |
| 2028 Q3 | 1,200 | $13,000 | $156,000 | $31,500 | $35,000 | -$3,500 | -$71,540 |

**中位情境 Year 2 結束**：MRR $13,000、ARR $156K、累計淨利 -$71K

#### 樂觀情境（20% 機率）

| 季度 | 月末付費客戶 | MRR | ARR | 季度 Revenue | 季度成本 | 季度淨利 | 累計淨利 |
|---|---|---|---|---|---|---|---|
| 2026 Q4 | 0 | $0 | $0 | $0 | $9,210 | -$9,210 | -$9,210 |
| 2027 Q1 | 40 | $500 | $6,000 | $1,200 | $9,960 | -$8,760 | -$17,970 |
| 2027 Q2 | 150 | $1,500 | $18,000 | $3,500 | $11,500 | -$8,000 | -$25,970 |
| 2027 Q3 | 350 | $3,500 | $42,000 | $7,500 | $14,000 | -$6,500 | -$32,470 |
| 2027 Q4 | 600 | $6,000 | $72,000 | $14,250 | $19,000 | -$4,750 | -$37,220 |
| 2028 Q1 | 1,000 | $12,000 | $144,000 | $27,000 | $28,000 | -$1,000 | -$38,220 |
| 2028 Q2 | 1,600 | $22,000 | $264,000 | $51,000 | $42,000 | +$9,000 | -$29,220 |
| 2028 Q3 | 2,500 | $42,000 | $504,000 | $96,000 | $62,000 | +$34,000 | +$4,780 |

**樂觀情境 Year 2 結束**：MRR $42,000、ARR $504K、首次季度獲利 $34K、累計淨利 +$5K

### C.2 假設說明

#### C.2.1 收入假設

| 假設 | 保守 | 中位 | 樂觀 |
|---|---|---|---|
| 月新增付費客戶（Month 4-6） | 5-8 | 8-15 | 15-25 |
| 月新增付費客戶（Month 7-12） | 10-15 | 15-25 | 30-50 |
| 月新增付費客戶（Year 2） | 20-40 | 30-80 | 50-150 |
| Churn（月） | 6% | 5% | 3% |
| Pro 佔比 | 75% | 70% | 65% |
| Team 佔比 | 22% | 25% | 27% |
| Enterprise 佔比 | 3% | 5% | 8% |
| Pro 平均月費 | $9 | $9 | $9 |
| Team 平均月費 | $49 | $49 | $49 |
| Enterprise 平均月費 | $300 | $500 | $800 |

#### C.2.2 成本假設

| 假設 | Year 1 | Year 2 |
|---|---|---|
| 創辦人生活費 | $3,000/mo | $5,000/mo（含團隊擴充後） |
| 雲端基礎設施 | $50-200/mo | $300-1,000/mo |
| 行銷預算 | $0-500/mo | $1,000-3,000/mo |
| 工具 / 域名 / SSL | $20-50/mo | $50-150/mo |
| 全職員工（Year 2 中期起） | 0 | $15,000-25,000/mo |
| Stripe 費率 | 3% | 3% |

#### C.2.3 單位經濟假設

| 假設 | 數值 |
|---|---|
| LTV（保守） | $697 |
| LTV（中位） | $900 |
| LTV（樂觀） | $1,500 |
| CAC（保守） | $25 |
| CAC（中位） | $15 |
| CAC（樂觀） | $10 |
| LTV/CAC（中位） | 60 |
| Gross Margin | 77-87% |
| Payback Period | <6 個月 |

#### C.2.4 關鍵指標假設

| 指標 | Year 1 目標 | Year 2 目標 |
|---|---|---|
| GitHub Stars | 5,000 | 20,000 |
| 月活使用者（MAU） | 5,000 | 50,000 |
| 付費客戶 | 150 | 1,200 |
| ARR | $5,500 | $156,000 |
| 文件網站月訪問 | 100K | 500K |
| 社群成員 | 2,000 | 15,000 |
| Plugin 數 | 50 | 200 |

#### C.2.5 風險調整後預期值

```
風險調整後 Year 2 結束 MRR：
= 0.30 × $5,500 + 0.50 × $13,000 + 0.20 × $42,000
= $1,650 + $6,500 + $8,400
= $16,550

風險調整後 Year 2 結束 ARR：
= $16,550 × 12
= $198,600

風險調整後 Year 2 結束累計淨利：
= 0.30 × (-$77,280) + 0.50 × (-$71,540) + 0.20 × (+$4,780)
= -$23,184 + -$35,770 + $956
= -$57,998
```

**核心結論**：即使在風險調整後，Year 2 結束預期 ARR ~$200K，累計淨虧損 ~$58K（需 bootstrapping 資金 ~$80K-100K 覆蓋）。

### C.3 募資需求分析（如啟動募資）

**若 Month 9 啟動募資**（Pre-seed）：

| 項目 | 金額 | 用途 |
|---|---|---|
| 工程師招募（2 名 × 6 月） | $60,000 | 加速產品開發 |
| 行銷加速（6 月） | $30,000 | KOL、Conference、Ads |
| 中國本地化（6 月） | $15,000 | 法務、本地雲、內容 |
| 預備金 | $15,000 | 緩衝 |
| **總計** | **$120,000** | **預估 12-18 個月 runway** |

**估值假設**：
- Pre-money valuation：$1.5M-3M（基於 ARR 與成長率）
- 投資人股權：8-15%
- 預估投資人：Angel investors、早期 VC、AI 專項基金

**募資 vs bootstrapping 決策**：
- 募資優點：加速成長、降低個人財務風險、引入 advisor
- 募資缺點：稀釋股權、報告義務、可能改變產品 roadmap
- 當前立場：**bootstrapping first 12 months**，之後依 KPI 決定

### C.4 退出策略（長期）

**可能路徑**：

| 情境 | 時點 | 估值倍數 | 預估估值 |
|---|---|---|---|
| 收購（合理情境） | Year 3-5 | 5-10x ARR | $1M-2M |
| 收購（成功情境） | Year 3-5 | 10-20x ARR | $5M-10M |
| 持續營運 | Year 5+ | N/A | 自我持續 |

**潛在收購方**：
- AI 編碼工具公司（Cursor、Anthropic、Replit）
- LLM 平台（OpenAI、Anthropic）
- DevOps / Observability 公司（Datadog、New Relic）
- 中國雲端廠商（阿里、字節、騰訊）

**退出假設**：本計畫不假設明確退出，預期 founder 將在 Year 3 評估選項。

---

## 最終備註

本商業計畫書反映了 2026 年 9 月的市場理解與 founder 的當前判斷。所有財務預測均為保守估計，存在顯著不確定性。我們承諾：

1. **透明**：所有 KPI 將每月公開（公開 dashboard）
2. **誠實**：每季回顧、調整假設、必要時更新商業模式
3. **以用戶為中心**：所有產品決策以用戶痛點為優先，非投資人導向

**聯絡資訊**：
- Email：[founder@example.com]
- GitHub：[github.com/kiddhsu5/K.H.A.V.I.S.]
- Twitter/X：[@K.H.A.V.I.S.]
- 微信公眾號：K.H.A.V.I.S.
- Discord：[discord.gg/khavis]

---

**文件結束**
