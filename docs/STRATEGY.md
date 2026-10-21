# K.H.A.V.I.S. 策略備忘錄

> 本文件把 K.H.A.V.I.S. 的定位、護城河、白地帶與行動建議寫在同一處。
> 對外 marketing copy 從 README 來；對內 roadmap 決策從這份文件來。
> 任何「付費 tier / 企業 sales / SaaS」相關提案，請先回頭讀 §7.2 的長期不建議事項。

## 一句話戰略

> **K.H.A.V.I.S. 不是 LiteLLM 的廉價版，是「個人 / homelab 開發者的 BYOK 純粹主義路由器」。把這件事講到極致，就是護城河。**

---

## 5. 差異化機會（找空隙）

### 5.1 個白地帶

| 機會 | 對手狀態 | K.H.A.V.I.S. 可做 |
| --- | --- | --- |
| ◎ 個人 / homelab / hobbyist 市場 | LiteLLM / Bifrost 都在打企業；Portkey 「Free tier 不適合 production」明確排除 | 已佔位。強化方向：web UI（LiteLLM LiteLLM UI、Bifrost 都沒有） |
| ◎ 「零成本 BYOK 路由器」純粹主義 | LiteLLM 改 license、Bifrost Enterprise 越來越厚、Portkey 是 Palo Alto 商業 | K.H.A.V.I.S. 的「永遠 Apache 2.0、零 markup」是**唯一**純粹主義聲量。強化方向：寫一篇「K.H.A.V.I.S. License 純度宣言」微章放 README |
| ◎ Telegram / IM 派工 bot | 4 家都沒有。Claude Code / Codex / 自家 router 三方聚合 = K.H.A.V.I.S. 獨家 | 加速方向：把 `bot/` 模組做完整（目前是 Phase 1+2+3），加 web dashboard |
| ◎ Capability tag 直覺 | LiteLLM 用 `model-group`；Bifrost 沿用 OpenAI `model name` | K.H.A.V.I.S. 的 `code` / `vision` / `long-context` / `cheap` / `local` 是任務導向，比對手更貼近使用者心智。強化方向：文件加「常見任務 → capability 速查表」、加 health badge |
| ◎ 跨境 / 多地域 quota 容錯 | 對手預設「單一 gateway、單一部署」 | K.H.A.V.I.S. 的 `Ollama-Mac` + `Ollama-Surface` LAN 模式是獨家 — 一台機器掛了另一台接。強化方向：加 Wireguard / Tailscale 案例、寫「edge failover」章節 |

### 5.2 個需守住的護城河（不要被追上）

1. **永遠免費、永遠 self-host** — 不能加付費 tier；一旦加，「個人開發者首選」這塊就崩。
2. **YAML-first + hot reload** — 對手要追也能做，但心智已成形。
3. **12 pool plugin 一行加一個** — 自動發現的 extensibility 對 indie hacker 是 killer feature。

### 5.3 個要補的功能缺口（影響長期）

- **無 semantic cache、無 prompt management、無 Guardrails** — 這是企業入場券。如果未來想接企業，至少要補 Guardrails（成本 cap、rate limit、PII 過濾）。**可以做成「plugin」**（保持 OSS 純粹的同時提供 enterprise 級 feature 入口）。

## 6. 可借鑑點（向對手學）

| 借鑑點 | 來源 | 怎麼用在 K.H.A.V.I.S. |
| --- | --- | --- |
| Landing page 明確打「Free forever、$0」 | LiteLLM / Bifrost | K.H.A.V.I.S. README 把「Apache 2.0 · Zero quota interruption」做成橫幅徽章 |
| OSS / Enterprise 分界清晰 | Bifrost 的 14 項 Enterprise-exclusive 表格 | 寫一份 `docs/FEATURE_MATRIX.md`，誠實標出哪些做了 / 哪些沒做 |
| Performance benchmark 自我披露 | Bifrost 的 20μs / 5k req/s | K.H.A.V.I.S. 補一份 benchmark：`khavis bench --compare` |
| Customer logo wall | LiteLLM 首頁 AT&T/NVIDIA/IBM/Netflix | K.H.A.V.I.S. 不適合打企業，但可以打「個人開發者 wall」（GitHub stargazers、依賴者 logo） |
| AI agent 為主的擴展方向 | AutoGen | K.H.A.V.I.S. 的 `agents/` 模組可更深入，但**不要重複造 AutoGen 的輪子**（用 AutoGen + K.H.A.V.I.S. 互通） |

## 7. 結論

### 7.1 定價 / 商業模式核心結論

| 維度 | K.H.A.V.I.S. 站位 |
| --- | --- |
| License 純度 | **5 家最純** — Apache 2.0、零 markup、零商業條款。LiteLLM 改 license 是「前車之鑑」。 |
| 收費透明度 | **唯一**一家完全沒有付費 tier（Portkey $49/月、Bifrost Custom、LiteLLM Talk-to-Sales、AutoGen 走 Azure 變現）。K.H.A.V.I.S. 是「免費也公開」。 |
| 商業模式 | 個人 / 社群 / 雇主買單 — 不是 SaaS。**這既是護城河也是天花板**：能贏得 homelab / 個人開發者，永遠贏不了企業銷售。 |
| BYOK 純度 | **完全 BYOK**；Portkey 是唯一提供「代收費」變體的對手，K.H.A.V.I.S. 應該堅持不要這條路。 |

### 7.2 策略建議（給 K.H.A.V.I.S.）

**短期（6 個月內）**

1. README 頂部加「Free forever, Apache 2.0, zero markup」三大徽章 — 把定價純度做成 brand identity。
2. 補 `docs/FEATURE_MATRIX.md` — 對手誠實公開做了什麼沒做什麼，反而增加信任。
3. 跑一份 `pytest benchmarks/` — 對手有數字（Bifrost 20μs）我們也要有。

**中期（6–12 個月）**

4. 寫一份 `blog/ZERO_QUOTA_INTERRUPTION.md` — 把「多 pool failover」這個差異化做成 thought leadership。
5. Telegram bot 模組繼續完善 — 這是其他 4 家都沒有的真正差異化。
6. 加 Wireguard / Tailscale 案例 — 把 `Ollama-Mac` + `Ollama-Surface` LAN failover 寫成 edge failover 故事。

**長期（不建議做）**

- **不要加付費 tier**
- **不要做企業 sales、不要做 SaaS**

---

## 附錄 A：本策略對應的程式碼錨點

> 寫這份策略時同步記錄「現況對應到哪個檔案」，避免策略與實作漂移。

| 策略項目 | 對應檔案 / 證據 |
| --- | --- |
| 12 個 pool plugin | `providers/` × 9 檔 + `config/pools.yaml` 12 條目 |
| Apache 2.0 / 零 markup | `pyproject.toml` `license = { text = "Apache-2.0" }` |
| YAML-first + hot reload | `core/hot_reload.py` + `watchdog>=3.0.0` |
| Ollama-Mac + Ollama-Surface | `config/pools.yaml` + `scripts/setup_ollama.sh` |
| Telegram bot | `bot/` 整包（含 `main.py` / `handlers.py` / `dispatch.py` / `aggregator.py`） |
| `/healthz` endpoint | `deploy/README.md`（已實作，但 README 尚未露出） |
| agents 模組 | `agents/`（`graph.py` / `agent_factory.py` / `memory.py` / `roles.py`） |
| 現有 FAQ | `docs/FAQ.md`（與 OpenRouter / LiteLLM 對照表已就位） |
| 現有 business plan | `BUSINESS_PLAN.md`（9 章 / 2016 行 — 偏 SaaS 框架，與本文件定位不同步；後續需收斂） |

## 附錄 B：尚未對應到實作的策略項目（gap）

| 策略建議 | 現況 | 行動 |
| --- | --- | --- |
| README 三大徽章（Free forever / Apache 2.0 / zero markup） | 只有 License badge，缺 Free / Quota 徽章 | 加 shields.io badge + shields.io `/healthz` 動態徽章 |
| `docs/FEATURE_MATRIX.md` | 缺 | 新建 |
| `pytest benchmarks/` | `pytest-benchmark` 已列為 dev dep，但沒有 `benchmarks/` 目錄 | 新建 `tests/benchmarks/`，至少跑 `selection_ms` 與 `chat_roundtrip_ms` |
| `blog/ZERO_QUOTA_INTERRUPTION.md` | 缺 | 新建 |
| Wireguard / Tailscale 案例 | 缺 | 用 `setup_ollama.sh` 當素材寫一篇 `docs/EDGE_FAILOVER.md` |
| web dashboard for bot | ✅ 2026-09-26 | `web/dashboard.py` + `/dashboard` `/api/dashboard` |
| 「個人開發者 wall」 | ✅ 2026-09-26 | README + `/wall` |

---

## 附錄 C：已關閉的策略項目（changelog）

> 對應附錄 B 的 gap 表 — 完成時打勾，並留下 commit / file 痕跡。

| 策略建議 | 完成日 | 對應檔案 |
| --- | --- | --- |
| `docs/FEATURE_MATRIX.md` | 2026-09-24 | `docs/FEATURE_MATRIX.md`（119 行） |
| `tests/benchmarks/` | 2026-09-24 | `tests/benchmarks/test_benchmarks.py`（14 tests）+ `scripts/run_benchmarks.py` |
| `docs/BENCHMARKS.md`（自我披露數字） | 2026-09-24 | `docs/BENCHMARKS.md`（selection p95 = 0.02 ms） |
| Wireguard / Tailscale 案例 | 2026-09-24 | `docs/EDGE_FAILOVER.md`（191 行） |
| web dashboard + 個人開發者 wall | 2026-09-26 | `web/dashboard.py`, README wall, `/dashboard` `/wall` |
| bot Phase 4 `/phase` | 2026-09-26 | `bot/phases.py`, `bot/history.py` |
| SECURITY.md PGP key | 2026-09-26 | `.github/SECURITY.md`, `deploy/pgp.txt` → khavis.example.com/pgp.txt |
