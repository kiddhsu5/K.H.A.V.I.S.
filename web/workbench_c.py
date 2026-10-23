"""K.H.A.V.I.S. Workbench — 選項 C：任務卡片流 (Task-Stream) 介面。

設計目標
--------
1. 訊息減量：把原本「永遠展開」的工作區列、拓撲畫布、模型設定、自訂 Agent
   表單全部收進可摺疊面板，預設關閉。
2. 任務優先：主畫面是一條由新到舊的任務卡片流，每張卡片自帶狀態、
   參與 Agent、耗時、檔案變更與成果摘要。
3. 執行可見：執行中的卡片即時顯示階段進度與主控台串流，不必捲到頁底。
4. 莫蘭迪配色：低飽和霧感底色 + 單一強調色，避免原本高對比霓虹造成的視覺噪音。

實作方式
--------
本模組**重組** `web.workbench` 既有的 markup（以 marker 切片）並沿用其
client-side JS，因此所有 API 呼叫、狀態管理與後端契約完全不變；外層版面
（側欄 / 任務流 / composer）則是全新的。

已驗證 `_WORKBENCH_PAGE_HEAD` 重構後輸出與線上頁面 byte-identical。
"""

from __future__ import annotations

import re
from typing import Final

from .workbench import _WORKBENCH_CLIENT_JS, _WORKBENCH_PAGE_HEAD

__all__ = ["render_workbench_html_c"]

# ── markup 切片工具 ────────────────────────────────────────────────────────
_LINES: Final[list[str]] = _WORKBENCH_PAGE_HEAD.split("\n")

# 1-indexed inclusive slices into _WORKBENCH_PAGE_HEAD (verified by the
# contract check in tests/test_workbench.py).
_SLICES: Final[dict[str, tuple[int, int]]] = {
    # 工作區 + Git worktree/diff 主控台
    "workspace": (250, 327),
    # 拓撲畫布 + Agent 節點 + 協同模式 + 任務範本 (不含輸入框, 見 composer)
    "topology": (329, 709),
    # 快速範本 + textarea + 能力路由 + 派工按鈕
    "composer": (710, 743),
    # 執行面板：狀態列、pipeline stepper、延遲圖、成果容器
    "result": (747, 836),
    # VIEW 2-5：交付文件 / 額度熔斷 / Agent 集群 / 部署精靈
    "views": (839, 970),
    # 產物預覽抽屜
    "drawers": (975, 998),
}


def _slice(name: str) -> str:
    """Return a 1-indexed inclusive slice of the legacy markup."""
    start, end = _SLICES[name]
    return "\n".join(_LINES[start - 1 : end])


def _rebalance(html: str, extra_open: int = 0) -> str:
    """Close any <div>s left dangling by a partial slice.

    Slicing markup out of a deeply nested tree is inherently fragile; rather
    than hand-tuning boundaries we count the imbalance and append the closers
    needed so the resulting fragment is well-formed.
    """
    opened = len(re.findall(r"<div\b", html)) + extra_open
    closed = len(re.findall(r"</div>", html))
    return html + ("\n" + "</div>" * (opened - closed) if opened > closed else "")


def _legacy_style() -> str:
    """Reuse the original stylesheet (.agent-node-card, .check-indicator, ...).

    The topology panel markup still depends on those class hooks, so we keep
    them and layer the Morandi palette on top.
    """
    m = re.search(r"<style>(.*?)</style>", _WORKBENCH_PAGE_HEAD, re.S)
    return m.group(1) if m else ""


# ── 莫蘭迪設計語言 ─────────────────────────────────────────────────────────
_MORANDI_CSS: Final[str] = """
/* ══════════════════════════════════════════════════════════════════
   MORANDI DESIGN LANGUAGE — 低飽和霧感基底 + 單一強調色
   霧霾藍 #7C9BB5 為主色；灰綠 / 藕荷 / 豆沙 / 杏桃 為狀態跳色
   ══════════════════════════════════════════════════════════════════ */
:root{
  --m-mist:#7C9BB5;  --m-mist-soft:rgba(124,155,181,.16);
  --m-sage:#8FA894;  --m-sage-soft:rgba(143,168,148,.16);
  --m-lilac:#A99AB5; --m-lilac-soft:rgba(169,154,181,.16);
  --m-rose:#BC8B8B; --m-rose-soft:rgba(188,139,139,.16);
  --m-apricot:#C9A17E; --m-apricot-soft:rgba(201,161,126,.16);
  --m-bone:#E4E2DE;  --m-dim:#9A9A9E;  --m-faint:#6E6E74;
  --m-line:rgba(228,226,222,.07);
  --m-ink-900:#16181D; --m-ink-800:#1C1E25;
  --m-ink-700:#23262F; --m-ink-600:#2B2F3A;
  --m-on-accent:#16181D;
  --m-rose-text:#D2A5A5;
  /* 半透明面板底色（composer 外框 / 卡片內文 / 主控台 / 淡色底） */
  --m-panel:rgba(22,24,29,.82);
  --m-panel-2:rgba(22,24,29,.5);
  --m-panel-3:rgba(22,24,29,.65);
  --m-faint-bg:rgba(228,226,222,.05);
  --m-track:rgba(228,226,222,.06);
}

html{font-size:17px}
body{
  background:
    radial-gradient(1200px 620px at 12% -12%, rgba(124,155,181,.055), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(169,154,181,.045), transparent 55%),
    var(--m-ink-900);
  color:var(--m-bone);
}

/* 卡片採霧面而非純黑，帶一點暖色，避免死黑造成的廉價感 */
.frost{background:linear-gradient(180deg,rgba(43,47,58,.55),rgba(35,38,47,.78))}
.frost-2{background:linear-gradient(180deg,rgba(35,38,47,.7),rgba(28,30,37,.85))}

.m-line{border:1px solid var(--m-line)}
.m-scroll::-webkit-scrollbar{width:7px;height:7px}
.m-scroll::-webkit-scrollbar-track{background:transparent}
.m-scroll::-webkit-scrollbar-thumb{background:rgba(228,226,222,.10);border-radius:8px}
.m-scroll::-webkit-scrollbar-thumb:hover{background:rgba(228,226,222,.18)}

.m-raise{box-shadow:0 1px 2px rgba(0,0,0,.45),0 12px 32px -16px rgba(0,0,0,.75)}

@keyframes mPulse{0%,100%{opacity:1}50%{opacity:.28}}
.m-live{animation:mPulse 1.6s ease-in-out infinite}
@keyframes mBeam{to{stroke-dashoffset:-32}}
.m-beam{stroke-dasharray:5 5;animation:mBeam 1s linear infinite}
@keyframes mIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.m-in{animation:mIn .34s cubic-bezier(.16,1,.3,1) both}

.m-chip{border-radius:.5rem;font-size:11px;padding:.125rem .5rem;border:1px solid}

/* 主按鈕：霧霾藍實心，畫面中唯一的高對比元素，用來導引視線 */
.m-btn-primary{background:var(--m-mist);color:var(--m-on-accent)}
.m-btn-primary:hover:not(:disabled){background:#8FACBF}
.m-btn-primary:disabled{opacity:.45;cursor:not-allowed}

.m-btn-ghost{background:rgba(228,226,222,.05);color:var(--m-dim);border:1px solid var(--m-line)}
.m-btn-ghost:hover{background:rgba(228,226,222,.09);color:var(--m-bone)}

/* 側欄導覽（取代原本的 sky-500 選中態） */
.m-nav{color:var(--m-dim);transition:background .15s,color .15s}
.m-nav:hover{background:rgba(228,226,222,.04);color:var(--m-bone)}
.m-nav-active{background:var(--m-mist-soft);color:#8FACBF}

.m-section-label{font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--m-faint)}

/* 摺疊面板：預設收起，這是「訊息太多」的主要解方 */
.m-collapse > summary{list-style:none;cursor:pointer}
.m-collapse > summary::-webkit-details-marker{display:none}
.m-collapse[open] > summary .m-caret{transform:rotate(90deg)}
.m-caret{transition:transform .18s ease;color:var(--m-faint)}

/* composer 內的輸入框聚焦光暈 */
#prompt-input:focus{outline:none;box-shadow:none}
.composer:focus-within{border-color:rgba(124,155,181,.45)}

/* 讓舊拓撲面板在莫蘭迪底色下不突兀 */
.agent-node-card{background:linear-gradient(180deg,rgba(43,47,58,.5),rgba(28,30,37,.7))}
.agent-node-card.selected{border-color:rgba(124,155,181,.6)!important;box-shadow:0 0 22px -6px rgba(124,155,181,.35)}
.agent-node-card.running{border-color:rgba(143,168,148,.7)!important;box-shadow:0 0 24px -4px rgba(143,168,148,.4)}
.check-indicator{color:var(--m-faint)}

textarea,input,select{color-scheme:dark}
textarea::placeholder,input::placeholder{color:var(--m-faint)}

/* ══════════════════════════════════════════════════════════════════
   淺色主題 — 莫蘭迪的淺底變體
   原本只切 <html class>，但 legacy 的 !important 規則把 shell 塗成白色，
   文字色卻仍是深色版的 var(--m-dim)/var(--m-bone) → 側欄文字近乎不可見。
   這裡補上完整的淺色變數與元件覆寫。
   ══════════════════════════════════════════════════════════════════ */
html:not(.dark){
  --m-mist:#5C7F9C;   --m-mist-soft:rgba(92,127,156,.14);
  --m-sage:#61836A;   --m-sage-soft:rgba(97,131,106,.14);
  --m-lilac:#806F8E;  --m-lilac-soft:rgba(128,111,142,.14);
  --m-rose:#9E6D6D;   --m-rose-soft:rgba(158,109,109,.14);
  --m-apricot:#8A6A44; --m-apricot-soft:rgba(138,106,68,.14);
  --m-bone:#1B2330;   --m-dim:#57616F;  --m-faint:#8B95A4;
  --m-line:rgba(27,35,48,.12);
  --m-ink-900:#EDF0F4; --m-ink-800:#FFFFFF; --m-ink-700:#F2F5F9; --m-ink-600:#E6EBF2;
  --m-on-accent:#FFFFFF;
  --m-rose-text:#8C4A4A;
  --m-panel:rgba(255,255,255,.9);
  --m-panel-2:rgba(236,240,245,.9);
  --m-panel-3:rgba(240,244,248,.95);
  --m-faint-bg:rgba(27,35,48,.05);
  --m-track:rgba(27,35,48,.08);
}
html:not(.dark) body{
  background:
    radial-gradient(1200px 620px at 12% -12%, rgba(92,127,156,.10), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(128,111,142,.08), transparent 55%),
    var(--m-ink-900) !important;
  color:var(--m-bone) !important;
}
/* main 保持透明，讓 body 的漸層透出來；header / aside 則是實心面板 */
html:not(.dark) header{background-color:var(--m-ink-800) !important;color:var(--m-bone) !important;border-color:var(--m-line) !important}
html:not(.dark) aside{background-color:var(--m-ink-800) !important;color:var(--m-bone) !important;border-color:var(--m-line) !important}
html:not(.dark) main{background-color:transparent !important;color:var(--m-bone) !important}
html:not(.dark) #artifact-drawer,
html:not(.dark) #drawer-content{background-color:var(--m-ink-800) !important;color:var(--m-bone) !important;border-color:var(--m-line) !important}
html:not(.dark) .frost{background:linear-gradient(180deg,rgba(255,255,255,.97),rgba(240,243,248,.94)) !important}
html:not(.dark) .frost-2{background:linear-gradient(180deg,#fff,#f3f6fa) !important}
html:not(.dark) .m-btn-ghost{background:rgba(27,35,48,.05);color:var(--m-dim);border-color:var(--m-line)}
html:not(.dark) .m-btn-ghost:hover{background:rgba(27,35,48,.09);color:var(--m-bone)}
html:not(.dark) .m-nav-active{background:var(--m-mist-soft);color:#3F6280}
html:not(.dark) .m-section-label{color:#94A0B0}
html:not(.dark) textarea,
html:not(.dark) select,
html:not(.dark) input{background-color:#fff !important;color:var(--m-bone) !important;border-color:var(--m-line) !important;color-scheme:light}
html:not(.dark) textarea::placeholder,
html:not(.dark) input::placeholder{color:#9AA5B4}
html:not(.dark) .m-scroll::-webkit-scrollbar-thumb{background:rgba(27,35,48,.16)}
html:not(.dark) .m-scroll::-webkit-scrollbar-thumb:hover{background:rgba(27,35,48,.28)}
html:not(.dark) .c-toast{background:linear-gradient(180deg,rgba(255,255,255,.98),rgba(243,246,250,.98));color:var(--m-bone);box-shadow:0 12px 30px -14px rgba(27,35,48,.35)}

/* legacy 的執行面板用 bg-white/5 與深色漸層，淺色底下會變成白底白框 */
html:not(.dark) #execution-panel div[class*="bg-white/5"],
html:not(.dark) #live-results-container div[class*="bg-white/5"],
html:not(.dark) #execution-panel div[class*="bg-[#050811]"],
html:not(.dark) #live-results-container div[class*="bg-[#050811]"]{
  background:rgba(27,35,48,.045) !important;
}
html:not(.dark) #live-results-container > div{
  background:linear-gradient(180deg,rgba(236,253,245,.9),rgba(255,255,255,.96)) !important;
  border-color:rgba(16,120,70,.28) !important;
}

/* ══════════════════════════════════════════════════════════════════
   響應式 — 窄視窗改抽屜式側欄
   原本 aside 固定 w-60(240px)，在 471px 的視窗下主欄只剩 225px，
   任務卡的標題被壓到 0 寬度而完全看不見。
   ══════════════════════════════════════════════════════════════════ */
#c-sidebar{transition:transform .24s cubic-bezier(.16,1,.3,1)}
#c-menu-btn{display:none}
#c-sidebar-close{display:none}
#c-scrim{
  position:fixed;inset:0;z-index:45;background:rgba(8,10,14,.55);
  opacity:0;pointer-events:none;transition:opacity .2s ease;
}
#c-scrim.c-on{opacity:1;pointer-events:auto}
@media (min-width:901px){
  /* 寬螢幕沒有抽屜模式，遮罩必須完全隱形，否則會擋住整個頁面 */
  #c-scrim{display:none !important}
}
@media (max-width:900px){
  #c-menu-btn{display:inline-flex}
  #c-sidebar-close{display:grid}
  #c-sidebar{
    position:fixed;top:0;bottom:0;left:0;z-index:50;width:258px;
    transform:translateX(-100%);
    box-shadow:0 18px 50px -12px rgba(0,0,0,.6);
  }
  #c-sidebar.c-open{transform:none}
}
/* 主欄與卡片都不允許被內容撐破 */
#c-main{min-width:0}
.c-card{min-width:0}

/* ══════════════════════════════════════════════════════════════════
   任務卡版面
   ══════════════════════════════════════════════════════════════════ */
.c-card-title{
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;word-break:break-word;
}
.c-meta-line{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.c-caret{transition:transform .18s ease}
.c-caret-open{transform:rotate(180deg)}
.c-action{font-size:12.5px;padding:.275rem .675rem;border-radius:.5rem;transition:.15s}

/* 真實進度：後端 dispatch 是單次阻塞請求，沒有階段回報，
   所以用「不確定進度條 + 真實經過時間」取代假的百分比。 */
@keyframes mShimmer{0%{transform:translateX(-110%)}100%{transform:translateX(340%)}}
.m-indeterminate{position:relative;overflow:hidden}
.m-indeterminate::after{
  content:'';position:absolute;top:0;bottom:0;left:0;width:42%;
  background:linear-gradient(90deg,transparent,rgba(143,168,148,.6),transparent);
  animation:mShimmer 1.6s ease-in-out infinite;
}
@keyframes mDot{0%,80%,100%{opacity:.25;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}
.m-dot{display:inline-block;width:4px;height:4px;border-radius:50%;background:var(--m-mist);
  animation:mDot 1.1s ease-in-out infinite}
.m-dot:nth-child(2){animation-delay:.15s}
.m-dot:nth-child(3){animation-delay:.3s}

/* ══════════════════════════════════════════════════════════════════
   Toast（取代會阻塞流程的 browser alert）
   ══════════════════════════════════════════════════════════════════ */
#c-toast-host{
  /* 放右上角（header 下方）：放右下角會蓋住派工鈕這個最重要控制項 */
  position:fixed;z-index:60;right:16px;top:56px;
  display:flex;flex-direction:column;gap:8px;pointer-events:none;max-width:min(380px,calc(100vw - 32px));
}
.c-toast{
  pointer-events:auto;padding:10px 14px;border-radius:12px;font-size:12px;line-height:1.55;
  background:linear-gradient(180deg,rgba(43,47,58,.97),rgba(28,30,37,.97));
  border:1px solid var(--m-line);color:var(--m-bone);
  box-shadow:0 12px 30px -12px rgba(0,0,0,.7);
  animation:mIn .22s cubic-bezier(.16,1,.3,1) both;
}
.c-toast.c-err{border-color:rgba(188,139,139,.5);color:var(--m-rose-text)}
.c-toast.c-ok{border-color:rgba(143,168,148,.5);color:#C2D6C5}

/* 派工鈕沿用 legacy 的 markup（id 固定），這裡把它的霓虹漸層
   換成莫蘭迪主色，讓整頁只有一個高對比元素。 */
#btn-dispatch{
  background:var(--m-mist) !important;
  background-image:none !important;
  color:var(--m-on-accent) !important;
  box-shadow:0 10px 24px -12px rgba(124,155,181,.85) !important;
}
#btn-dispatch:hover:not(:disabled){background:#8FACBF !important}
#btn-dispatch:disabled{opacity:.45 !important;cursor:not-allowed}
#btn-dispatch i{color:currentColor !important}

/* ══════════════════════════════════════════════════════════════════
   中央對話串檢視（你的指令 → Agent 協同結果）
   ══════════════════════════════════════════════════════════════════ */
.c-conv-header{
  display:flex;align-items:center;gap:.625rem;flex-wrap:wrap;
  padding:.5rem .75rem;border-radius:12px;
  background:var(--m-panel-2);border:1px solid var(--m-line);
}
.c-conv-title{font-size:15px;font-weight:600;color:var(--m-bone)}
.c-turn{margin-top:.875rem}
.c-turn-label{
  font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--m-faint);margin-bottom:.375rem;display:flex;align-items:center;gap:.5rem;
  flex-wrap:wrap;
}
.c-turn-label .c-conn-badge{text-transform:none;white-space:nowrap}
.c-turn-user .c-turn-bubble{
  border-left:2px solid var(--m-mist);padding:.6rem .85rem;border-radius:0 10px 10px 0;
  background:var(--m-mist-soft);color:var(--m-bone);font-size:15px;line-height:1.7;
  white-space:pre-wrap;word-break:break-word;
}
.c-turn-agent .c-turn-bubble{
  border:1px solid var(--m-line);border-radius:12px;padding:.85rem 1rem;
  background:var(--m-panel-2);color:var(--m-bone);font-size:14.5px;line-height:1.75;
  white-space:pre-wrap;word-break:break-word;max-height:28rem;overflow-y:auto;
}
.c-turn-actions{display:flex;flex-wrap:wrap;gap:.375rem;margin-top:.5rem}
.c-live-slot:empty{display:none}
.c-live-slot{margin-top:.875rem}
.c-conn-badge{
  display:inline-flex;align-items:center;gap:.25rem;
  padding:.1rem .45rem;border-radius:6px;font-size:11.5px;font-family:ui-monospace,monospace;
}

/* 鍵盤可及性：主要可互動元件給出明確焦點環 */
:focus-visible{outline:2px solid var(--m-mist);outline-offset:2px;border-radius:6px}

/* ══════════════════════════════════════════════════════════════════
   MiniMax Code 風格的項目清單
   取自 MiniMax Code renderer 的真實 token：
     --mavis-radius-control: 8px
     --bg_interaction_tertiary_selected = white 8%（深）/ black 4%（淺）
     --border_default             = white 8%（深）/ black 8%（淺）
   ══════════════════════════════════════════════════════════════════ */
.c-item{
  display:block;width:100%;text-align:left;
  padding:.375rem .5rem;border-radius:8px;
  color:var(--m-dim);
  transition:background-color .16s ease,color .16s ease;
}
.c-item:hover{background:rgba(228,226,222,.05);color:var(--m-bone)}
.c-item.c-item-sel{background:var(--m-mist-soft);color:var(--m-bone)}
.c-item-title{color:inherit}
.c-item-time{color:var(--m-faint);opacity:.8;transition:opacity .16s ease}
.c-item:hover .c-item-time{opacity:1}
.c-item-meta{color:var(--m-faint);opacity:.7}
.c-item-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}

.c-group-head{
  display:flex;align-items:center;gap:.375rem;
  padding:.5rem .5rem .1875rem;
  font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--m-faint);
}
.c-group-count{margin-left:auto;font-size:10px;letter-spacing:0;font-family:ui-monospace,monospace}

.c-menu{
  position:absolute;z-index:30;left:0;right:0;min-width:190px;
  border-radius:10px;padding:4px;
  background:var(--m-panel);
  border:1px solid var(--m-line);
  box-shadow:0 12px 30px -12px rgba(0,0,0,.6);
  backdrop-filter:blur(12px);
}
.c-menu-item{
  display:flex;align-items:center;gap:.5rem;width:100%;
  padding:.375rem .5rem;border-radius:8px;
  font-size:12px;color:var(--m-dim);text-align:left;
  transition:background-color .16s ease,color .16s ease;
}
.c-menu-item:hover{background:rgba(228,226,222,.06);color:var(--m-bone)}
.c-menu-item.c-on{color:var(--m-mist)}
.c-foot-chip{
  padding:.125rem .375rem;border-radius:6px;
  color:var(--m-faint);transition:background-color .16s ease,color .16s ease;
}
.c-foot-chip:hover{background:rgba(228,226,222,.06);color:var(--m-bone)}

#c-list-search{outline:none}
#c-list-search:focus{border-color:rgba(124,155,181,.55)}

/* topbar 的次要資訊帶（配額晶片 / 模型名）——寬度門檻自訂，
   不用 Tailwind 的 breakpoint，避免 CDN 行為不確定導致 topbar 換行溢出。 */
.c-strip{display:none}
@media (min-width:1400px){ #quota-capsule-strip{display:flex} }
/* 配額帶的晶片由 legacy 產生（emerald/indigo/sky/teal），
   這裡換成莫蘭迪色階，讓整頁只有一套配色語言。 */
#quota-capsule-strip{flex-shrink:1;min-width:0}
#quota-capsule-strip span{border-radius:6px;white-space:nowrap;flex-shrink:0}
#quota-capsule-strip span:nth-child(1){background:var(--m-mist-soft)!important;color:var(--m-mist)!important;border-color:rgba(124,155,181,.3)!important}
#quota-capsule-strip span:nth-child(2){background:var(--m-lilac-soft)!important;color:var(--m-lilac)!important;border-color:rgba(169,154,181,.3)!important}
#quota-capsule-strip span:nth-child(3){background:var(--m-sage-soft)!important;color:var(--m-sage)!important;border-color:rgba(143,168,148,.3)!important}
#quota-capsule-strip span:nth-child(4){background:var(--m-apricot-soft)!important;color:var(--m-apricot)!important;border-color:rgba(201,161,126,.3)!important}

/* ══════════════════════════════════════════════════════════════════
   右側抽屜：執行明細
   寬螢幕是常駐的第三欄，窄螢幕改成覆蓋式抽屜。
   ══════════════════════════════════════════════════════════════════ */
.c-drawer{width:420px;flex-shrink:0;overflow:hidden}
@media (min-width:1280px){
  .c-drawer{
    width:0;border-left:1px solid transparent;
    transition:width .22s cubic-bezier(.16,1,.3,1),border-color .22s ease;
  }
  .c-drawer.c-open{width:420px;border-left-color:var(--m-line)}
}
@media (max-width:1279px){
  .c-drawer{
    position:fixed;top:0;right:0;bottom:0;z-index:45;
    width:420px;max-width:92vw;
    transform:translateX(100%);
    transition:transform .22s cubic-bezier(.16,1,.3,1);
    box-shadow:-18px 0 50px -12px rgba(0,0,0,.55);
  }
  .c-drawer.c-open{transform:none}
}
#c-drawer-scrim{display:none}
@media (max-width:1279px){
  #c-drawer-scrim{
    position:fixed;inset:0;z-index:44;background:rgba(8,10,14,.5);
    opacity:0;pointer-events:none;transition:opacity .2s ease;
  }
  #c-drawer-scrim.c-on{opacity:1;pointer-events:auto}
}
html:not(.dark) .c-item:hover{background:rgba(27,35,48,.045)}
html:not(.dark) .c-menu-item:hover{background:rgba(27,35,48,.05)}
html:not(.dark) .c-foot-chip:hover{background:rgba(27,35,48,.05)}
"""


# ── 新版外層版面 ───────────────────────────────────────────────────────────

_SIDEBAR: Final[str] = """
<aside id="c-sidebar" class="w-[268px] shrink-0 bg-ink-800/85 backdrop-blur border-r m-line flex flex-col">
  <div class="h-12 flex items-center gap-2.5 px-3 border-b m-line shrink-0">
    <div class="w-7 h-7 rounded-lg grid place-items-center text-[11px] font-black shrink-0"
         style="background:linear-gradient(135deg,#7C9BB5,#8FA894);color:#16181D">K</div>
    <span class="text-sm font-semibold truncate" style="color:var(--m-bone)">K.H.A.V.I.S.</span>
    <button type="button" onclick="cToggleSidebar(false)" id="c-sidebar-close" class="ml-auto w-7 h-7 rounded-lg m-btn-ghost grid place-items-center shrink-0"
            aria-label="關閉側欄">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke-linecap="round"/></svg>
    </button>
  </div>

  <div class="p-3 space-y-2 shrink-0">
    <button type="button" onclick="cNewTask()" id="c-new-task"
            class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg m-btn-primary text-xs font-bold transition">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke-linecap="round"/></svg>
      新任務
    </button>

    <!-- 目前工作區專案（派工實際執行的資料夾） -->
    <div class="relative">
      <button type="button" onclick="cToggleProjectMenu()" id="c-project-btn"
              class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg m-btn-ghost text-[11px] transition"
              aria-haspopup="menu" aria-expanded="false">
        <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke-linejoin="round"/></svg>
        <span class="truncate" id="c-active-project">shared-app</span>
        <span class="ml-auto text-[10px] font-mono shrink-0" style="color:var(--m-faint)" id="c-project-count">--</span>
        <svg class="shrink-0" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      <div id="c-project-menu" class="c-menu hidden" role="menu" aria-label="切換專案"></div>
    </div>

    <!-- 檢視切換：時間線 / 專案 / 執行電腦 / 協同模式 / 狀態 -->
    <div class="relative">
      <div class="flex items-center gap-1.5">
        <button type="button" onclick="cToggleViewMenu()" id="c-view-btn"
                class="flex-1 min-w-0 flex items-center gap-1.5 px-2 py-1.5 rounded-lg m-btn-ghost text-[11px] transition"
                aria-haspopup="menu" aria-expanded="false">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h6" stroke-linecap="round"/></svg>
          <span class="truncate" id="c-view-label">時間線</span>
          <svg class="ml-auto shrink-0" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button type="button" onclick="cToggleSearch()" id="c-search-btn"
                class="w-8 h-8 shrink-0 rounded-lg m-btn-ghost grid place-items-center transition" title="搜尋任務" aria-label="搜尋任務">
          <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="m20 20-3.5-3.5" stroke-linecap="round"/></svg>
        </button>
      </div>

      <div id="c-view-menu" class="c-menu hidden" role="menu" aria-label="檢視方式">
        <button type="button" class="c-menu-item c-on" data-view="timeline" onclick="cSetView('timeline')" role="menuitem">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:var(--m-mist)"></span>時間線<span class="ml-auto text-[10px] opacity-70">依日期</span>
        </button>
        <button type="button" class="c-menu-item" data-view="project" onclick="cSetView('project')" role="menuitem">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:var(--m-sage)"></span>依專案<span class="ml-auto text-[10px] opacity-70">分組</span>
        </button>
        <button type="button" class="c-menu-item" data-view="backend" onclick="cSetView('backend')" role="menuitem">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:var(--m-lilac)"></span>依執行電腦<span class="ml-auto text-[10px] opacity-70">分組</span>
        </button>
        <button type="button" class="c-menu-item" data-view="mode" onclick="cSetView('mode')" role="menuitem">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:var(--m-apricot)"></span>依協同模式<span class="ml-auto text-[10px] opacity-70">分組</span>
        </button>
        <button type="button" class="c-menu-item" data-view="status" onclick="cSetView('status')" role="menuitem">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:var(--m-rose)"></span>依狀態<span class="ml-auto text-[10px] opacity-70">分組</span>
        </button>
      </div>
    </div>

    <div id="c-search-row" class="hidden">
      <input id="c-list-search" type="search" placeholder="搜尋任務、專案或 Agent…"
             oninput="cFilterList(this.value)" autocomplete="off"
             class="w-full px-2 py-1.5 text-[11px] rounded-lg m-line" style="background:var(--m-panel-2);color:var(--m-bone)">
    </div>
  </div>

  <!-- 項目清單（參考 MiniMax Code 的 session list：標題 + 次要資訊 + 選中態） -->
  <div id="c-item-list" class="flex-1 overflow-y-auto m-scroll px-2 pb-2 text-xs"></div>

  <!-- 系統頁籤（保留 legacy 的 nav-* id 與 switchTab 契約） -->
  <div class="px-2 pb-2 grid grid-cols-2 gap-1 shrink-0">
    <button type="button" onclick="switchTab('agents')" id="nav-agents" class="c-menu-item tab-btn">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><circle cx="12" cy="5" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="M12 7v4m0 0-5 5m5-5 5 5" stroke-linecap="round"/></svg>
      Agent 拓撲
    </button>
    <button type="button" onclick="switchTab('artifacts')" id="nav-artifacts" class="c-menu-item tab-btn">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke-linejoin="round"/></svg>
      交付文件
      <span id="artifacts-badge" class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded" style="background:var(--m-sage-soft);color:var(--m-sage)">--</span>
    </button>
    <button type="button" onclick="switchTab('quotas')" id="nav-quotas" class="c-menu-item tab-btn">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path d="M12 3v18M7 8h7a3 3 0 1 1 0 6H7" stroke-linecap="round"/></svg>
      額度與熔斷
    </button>
    <button type="button" onclick="switchTab('wizard')" id="nav-wizard" class="c-menu-item tab-btn">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 3v2m0 14v2M3 12h2m14 0h2" stroke-linecap="round"/></svg>
      模型與部署
    </button>
  </div>

  <div class="p-3 border-t m-line shrink-0 space-y-2">
    <div class="flex items-center gap-2 text-[11px]">
      <span class="inline-flex items-center gap-1.5" style="color:var(--m-sage)">
        <span class="w-1.5 h-1.5 rounded-full m-live" style="background:var(--m-sage)"></span>
        <span id="c-fleet-count">6</span>/6 在線
      </span>
      <span class="ml-auto font-mono" style="color:var(--m-faint)" id="c-quota-pct">額度 --</span>
    </div>
    <div class="h-1 rounded-full overflow-hidden" style="background:var(--m-track)">
      <div id="c-quota-bar" class="h-full rounded-full transition-all" style="width:0%;background:linear-gradient(90deg,#8FA894,#7C9BB5)"></div>
    </div>
    <div class="flex items-center gap-1.5 text-[10px] font-mono">
      <button type="button" onclick="cFilter('running')" data-cfilter="running" class="c-foot-chip">執行 <span id="c-count-running">0</span></button>
      <button type="button" onclick="cFilter('done')" data-cfilter="done" class="c-foot-chip">完成 <span id="c-count-done">0</span></button>
      <button type="button" onclick="cFilter('failed')" data-cfilter="failed" class="c-foot-chip">失敗 <span id="c-count-failed">0</span></button>
    </div>
  </div>
</aside>
"""

_TOPBAR: Final[str] = """
<header class="h-12 shrink-0 bg-ink-800/60 backdrop-blur border-b m-line flex items-center justify-between px-3 sm:px-5 gap-3">
  <div class="flex items-center gap-2 text-xs min-w-0">
    <button type="button" onclick="cToggleSidebar(true)" id="c-menu-btn"
            class="w-8 h-8 shrink-0 rounded-lg m-btn-ghost grid place-items-center"
            aria-label="開啟側欄" aria-controls="c-sidebar" aria-expanded="false">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" stroke-linecap="round"/></svg>
    </button>
    <button type="button" onclick="switchTab('command')" id="nav-command" class="tab-btn m-nav rounded-lg px-2 py-1 truncate" title="回到任務工作台">shared-app</button>
    <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--m-faint)" aria-hidden="true"><path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <span class="font-medium truncate" id="c-view-title" style="color:var(--m-bone)">任務</span>
  </div>

  <div class="flex items-center gap-2 min-w-0 overflow-hidden">
    <div id="c-task-filter" class="inline-flex rounded-lg p-0.5 m-line text-[11px] shrink-0" style="background:var(--m-ink-700)" role="group" aria-label="任務篩選">
      <button type="button" onclick="cFilter('all')" class="c-filter-btn px-2.5 py-1 rounded-md font-medium" data-filter="all" aria-pressed="true">全部</button>
      <button type="button" onclick="cFilter('running')" class="c-filter-btn px-2.5 py-1 rounded-md" data-filter="running" aria-pressed="false">執行中</button>
      <button type="button" onclick="cFilter('done')" class="c-filter-btn px-2.5 py-1 rounded-md" data-filter="done" aria-pressed="false">已完成</button>
      <button type="button" onclick="cFilter('failed')" class="c-filter-btn px-2.5 py-1 rounded-md" data-filter="failed" aria-pressed="false">失敗</button>
    </div>

    <!-- 配額晶片會隨 pool 數量增生，必須可捲動收邊，否則會把整個 topbar 撐爆 -->
    <div id="quota-capsule-strip" class="c-strip items-center gap-2 text-[11px] font-mono min-w-0 overflow-x-auto"
         style="color:var(--m-faint);scrollbar-width:none"></div>

    <!-- 模型名由 legacy 的 syncModelUIElements 直接寫進上面的配額帶，
         這三個節點只是 legacy JS 的寫入目標（契約測試要求存在），不重複顯示。 -->
    <span id="c-model-claude" class="hidden"><strong id="card-title-claude">—</strong></span>
    <span id="c-model-codex" class="hidden"><strong id="card-title-codex">—</strong></span>
    <span id="c-model-antigravity" class="hidden"><strong id="card-title-antigravity">—</strong></span>

    <button type="button" onclick="cToggleDrawer()" id="c-drawer-btn"
            class="w-8 h-8 rounded-lg m-btn-ghost grid place-items-center transition shrink-0 relative"
            title="執行明細抽屜（各 Agent 輸出 / 延遲 / 流程圖）" aria-label="執行明細抽屜" aria-expanded="false">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h9" stroke-linecap="round"/><path d="M17 14v6M14 17h6" stroke-linecap="round"/></svg>
      <span id="c-drawer-dot" class="hidden absolute top-1 right-1 w-1.5 h-1.5 rounded-full m-live" style="background:var(--m-mist)"></span>
    </button>

    <button type="button" onclick="toggleTheme()" class="w-8 h-8 rounded-lg m-btn-ghost grid place-items-center transition shrink-0" title="切換深淺色主題">
      <i id="theme-icon" class="fas fa-sun" style="color:var(--m-apricot)"></i>
    </button>
  </div>
</header>
"""

# 摺疊面板外框
_COLLAPSE_TOP: Final[str] = """
<details class="m-collapse frost m-line rounded-2xl overflow-hidden">
  <summary class="px-4 py-3 flex items-center gap-2.5 hover:bg-white/[.02] transition">
    <svg class="m-caret" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
"""
_COLLAPSE_BOTTOM: Final[str] = """
  </details>
"""

_COMPOSER_CHROME_TOP: Final[str] = """
<div class="shrink-0 border-t m-line px-4 sm:px-6 py-2.5" style="background:var(--m-panel);backdrop-filter:blur(12px)">
  <div class="max-w-4xl mx-auto">
    <div class="composer frost-2 m-line rounded-2xl p-3 transition">

      <!-- 協同模式 + 參與 Agent（取代原本永遠展開的拓撲畫布） -->
      <div class="flex items-center gap-2 flex-wrap mb-2 pb-2" style="border-bottom:1px solid var(--m-line)">
        <div class="inline-flex rounded-lg p-0.5 m-line text-[11px]" style="background:var(--m-panel-2)" role="group" aria-label="協同模式">
          <button type="button" class="c-collab-btn m-btn-primary px-2.5 py-1 rounded-md font-semibold transition" data-mode="auto_loop"  onclick="setCollabMode('auto_loop')">自動閉環</button>
          <button type="button" class="c-collab-btn m-btn-ghost px-2.5 py-1 rounded-md transition" data-mode="relay"    onclick="setCollabMode('relay')">接力</button>
          <button type="button" class="c-collab-btn m-btn-ghost px-2.5 py-1 rounded-md transition" data-mode="critique" onclick="setCollabMode('critique')">互評</button>
          <button type="button" class="c-collab-btn m-btn-ghost px-2.5 py-1 rounded-md transition" data-mode="parallel" onclick="setCollabMode('parallel')">並發</button>
        </div>
        <span id="c-collab-desc" class="text-[11px] truncate hidden sm:inline" style="color:var(--m-faint)"></span>
        <div class="flex-1"></div>
        <div id="c-agent-chips" class="flex items-center gap-1.5 flex-wrap"></div>
      </div>
"""

_COMPOSER_CHROME_BOTTOM: Final[str] = """
    </div>
    <div class="flex items-center justify-between mt-1.5 px-1 text-[11px] font-mono" style="color:var(--m-faint)">
      <span id="c-composer-hint">shared-app · ⌘/Ctrl+⏎ 執行 · ⏎ 換行</span>
      <span id="c-context-badge" class="hidden"></span>
    </div>
  </div>
</div>
"""


# 必須在「既有 JS 之後、覆寫版之前」抓取原始函式參照。
# 原因：function 宣告會在各自 script 區塊求值前 hoist，因此若在同一個
# script 裡寫 `const x = switchTab; function switchTab(){}`，取到的會是
# 自己 → 無限遞迴。獨立成一個 script 區塊即可安全取得原始參照。
_LEGACY_CAPTURE_JS: Final[str] = """
<script>
  const __legacySwitchTab         = switchTab;
  const __legacySetCollabMode     = setCollabMode;
  const __legacySetPipelineStep   = setPipelineStepState;
  const __legacySubmitDispatch    = submitDispatch;
</script>
"""


# ── 新增的 client 邏輯（附加在既有 JS 之後，後者不會被覆蓋） ────────────────
_C_EXTRA_JS: Final[str] = """
<script>
// ══════════════════════════════════════════════════════════════════
// 選項 C：任務卡片流 — 專屬邏輯
// 附加於既有 workbench JS 之後；switchTab / setCollabMode 於此覆寫，
// 以套用莫蘭迪選中態並同步新的 composer。
// ══════════════════════════════════════════════════════════════════

const C_AGENT_COLORS = {
  claude:      ['--m-mist', '#7C9BB5'],
  codex:       ['--m-lilac', '#A99AB5'],
  antigravity: ['--m-sage', '#8FA894'],
  minimax:     ['--m-apricot','#C9A17E'],
  zcode:       ['--m-rose',  '#BC8B8B'],
  khavis:      ['--m-butter','#D9C89E']
};

let cTasks = [];            // 任務卡片資料
let cFilterKey = 'all';
let cRunningTask = null;    // 執行中的任務卡 id
let cAborted = false;       // 使用者主動中止
let _cAbortController = null;

// ── Toast：取代會阻塞整頁的 browser alert() ───────────────────────
function cToast(msg, kind) {
  const host = document.getElementById('c-toast-host');
  if (!host) return;
  const el = document.createElement('div');
  el.className = 'c-toast' + (kind === 'err' ? ' c-err' : (kind === 'ok' ? ' c-ok' : ''));
  el.textContent = String(msg == null ? '' : msg);
  host.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(6px)';
    setTimeout(() => { if (el.parentElement) el.parentElement.removeChild(el); }, 260);
  }, kind === 'err' ? 7000 : 4500);
}

// ── fetch 包裝：讓「中止」真的能打斷等待中的 dispatch ───────────────
// dispatch 是單次阻塞請求，沒有後端取消 API；這裡用 AbortController
// 中斷客戶端等待，讓 UI 不再被鎖死（後端仍可能自行完成任務）。
const _nativeFetch = (typeof fetch === 'function')
  ? fetch.bind(typeof window !== 'undefined' ? window : null)
  : null;
if (_nativeFetch) {
  window.fetch = function (input, init) {
    let url = '';
    try { url = typeof input === 'string' ? input : ((input && input.url) || ''); } catch (e) {}
    if (url.indexOf('/api/workbench/dispatch') !== -1) {
      const opts = Object.assign({}, init || {});
      if (typeof AbortController !== 'undefined') {
        try {
          _cAbortController = new AbortController();
          opts.signal = _cAbortController.signal;
        } catch (e) { /* 不支援就略過中止功能 */ }
      }
      return _nativeFetch(input, opts);
    }
    return _nativeFetch(input, init);
  };
}

// ── 覆寫 switchTab：改用莫蘭迪選中態 ───────────────────────────────
const _switchTabLegacy = __legacySwitchTab;
function switchTab(tab) {
  _switchTabLegacy(tab);
  document.querySelectorAll('.tab-btn').forEach(b => {
    // legacy 會塞 bg-sky-600/20 / text-sky-400 等高對比天藍選中態，
    // 在莫蘭迪配色下會像壞掉的一顆藥丸 → 一律清掉改用 m-nav-active。
    b.classList.remove('m-nav-active', 'bg-sky-600/20', 'text-sky-400', 'border-sky-500/30');
    b.classList.add('m-nav');
    b.setAttribute('aria-current', 'false');
  });
  const active = document.getElementById('nav-' + tab);
  if (active) {
    active.classList.remove('bg-sky-600/20', 'text-sky-400', 'border-sky-500/30');
    active.classList.add('m-nav-active');
    active.classList.remove('m-nav');
    active.setAttribute('aria-current', 'page');
  }
  const titles = { command:'任務', artifacts:'交付文件', quotas:'額度與熔斷', agents:'Agent 拓撲', wizard:'模型與部署' };
  const t = document.getElementById('c-view-title');
  if (t) t.textContent = titles[tab] || '任務';
  // 窄螢幕下側欄是抽屜，切換頁籤後自動收合
  cToggleSidebar(false);
}

// ── 覆寫 setCollabMode：同步 composer 內的模式列 ───────────────────
const _setCollabModeLegacy = __legacySetCollabMode;
function setCollabMode(mode) {
  _setCollabModeLegacy(mode);
  document.querySelectorAll('.c-collab-btn').forEach(b => {
    const on = b.dataset.mode === mode;
    b.classList.toggle('m-btn-primary', on);
    b.classList.toggle('font-semibold', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (!on) b.classList.add('m-btn-ghost');
  });
  const d = document.getElementById('c-collab-desc');
  if (d && COLLAB_MODE_DESCS[mode]) d.textContent = COLLAB_MODE_DESCS[mode];
}

// ── 側欄抽屜（窄視窗） ─────────────────────────────────────────────
function cToggleSidebar(open) {
  const sb = document.getElementById('c-sidebar');
  const scrim = document.getElementById('c-scrim');
  if (sb) sb.classList.toggle('c-open', !!open);
  if (scrim) scrim.classList.toggle('c-on', !!open);
  const btn = document.getElementById('c-menu-btn');
  if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

// ── 右側執行明細抽屜 ───────────────────────────────────────────────
function cToggleDrawer(force) {
  const d = document.getElementById('c-drawer');
  if (!d) return;
  const show = (typeof force === 'boolean') ? force : !d.classList.contains('c-open');
  d.classList.toggle('c-open', show);
  const scrim = document.getElementById('c-drawer-scrim');
  if (scrim) scrim.classList.toggle('c-on', show);
  const btn = document.getElementById('c-drawer-btn');
  if (btn) btn.setAttribute('aria-expanded', show ? 'true' : 'false');
  if (show) cSetDrawerDot(false);
}

function cSetDrawerDot(on) {
  const dot = document.getElementById('c-drawer-dot');
  if (dot) dot.classList.toggle('hidden', !on);
}

// ── 左側項目清單（參考 MiniMax Code 的 session list） ───────────────
let cViewKey = 'timeline';
let cSearchQuery = '';
let cSelectedId = null;
let cActiveProject = 'shared-app';

/* 對話串（thread）模型 —— 對應 MiniMax Code 的 session list */
let cThreads = new Map();     // threadId -> { id, tasks[], title, ... }
let cThreadId = null;         // 目前派工所屬的對話串
let cThreadStep = 0;          // 該對話串已完成的輪數
let cSelectedThread = null;   // 中央正在顯示的對話串
let cLiveThreadId = null;     // 本次頁面生命週期內最後派工的對話串
let cCenterMode = 'thread';   // 'thread' | 'overview'

const C_VIEWS = {
  timeline: { label:'時間線' },
  project:  { label:'依專案' },
  backend:  { label:'依執行電腦' },
  mode:     { label:'依協同模式' },
  status:   { label:'依狀態' }
};

const C_STATUS_LABEL = { running:'執行中', done:'已完成', failed:'失敗', aborted:'已中止' };

function cDayLabel(t) {
  const day = t.day || '';
  if (!day) return '最近';
  if (day === cToday()) return '今天';
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const p = n => String(n).padStart(2, '0');
  const yest = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  if (day === yest) return '昨天';
  return day;
}

// 每個任務可能同時屬於多個分組（例如一次派工跑了 3 個 Agent）
function cGroupKeys(t, viewKey) {
  // 舊的 dispatch 紀錄沒有記 project（記錄欄位是後來才補的），
  // 當時的 dispatch 其實就跑在當時的工作區專案 → 用目前專案回推。
  if (viewKey === 'project') return [t.project || cActiveProject || '未指定專案'];
  if (viewKey === 'backend') return (t.agents && t.agents.length) ? t.agents : ['未知'];
  if (viewKey === 'mode')    return [t.mode || '未標記'];
  if (viewKey === 'status')  return [C_STATUS_LABEL[t.status] || '未知'];
  return [cDayLabel(t)];
}

function cRelTime(t) {
  if (!t.time) return '';
  if (t.day === cToday()) {
    const parts = String(t.time).split(':').map(Number);
    const now = new Date();
    const itemS = (parts[0] || 0) * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0);
    const nowS = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
    const diff = Math.max(0, nowS - itemS);
    if (diff < 60) return '剛剛';
    if (diff < 3600) return Math.floor(diff / 60) + ' 分前';
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小時前';
  }
  return String(t.time).slice(0, 5);
}

// ── 對話串模型 ────────────────────────────────────────────────────────
// 每個 dispatch 帶 thread id；舊的紀錄沒有 thread → 一筆任務自成一串。
function cThreadKeyOf(t) {
  // 舊紀錄沒有 thread id → 一筆任務自成一串。
  // handle 只到秒，同秒的兩筆會撞號，所以要加上 ts 才唯一。
  if (t.thread) return t.thread;
  return 'legacy-' + (t.id || '') + '-' + (t.ts || '');
}

function cBuildThreads() {
  const map = new Map();
  cTasks.forEach(t => {
    const key = cThreadKeyOf(t);
    let th = map.get(key);
    if (!th) {
      th = { id:key, tasks:[], title:'', project:'', agents:[], mode:'',
             status:'done', day:t.day, time:t.time, duration:'' };
      map.set(key, th);
    }
    th.tasks.push(t);
    if (!th.title) th.title = t.prompt || '（無標題對話）';
    if (!th.project) th.project = t.project || '';
    if (!th.mode) th.mode = t.mode || '';
    (t.agents || []).forEach(a => { if (th.agents.indexOf(a) < 0) th.agents.push(a); });
  });
  map.forEach(th => {
    th.tasks.sort((a, b) => ((a.step || 0) - (b.step || 0)));
    const last = th.tasks[th.tasks.length - 1];
    if (last) {
      th.status = last.status;
      th.day = last.day || th.day;
      th.time = last.time || th.time;
      th.duration = last.duration || th.duration;
    }
    th.turns = th.tasks.length;
  });
  cThreads = map;
  // 預設顯示最近的一串（依最後一輪的 ts 判斷，不能靠 Map 插入順序）
  if (!cSelectedThread || !cThreads.has(cSelectedThread)) {
    let newest = null, newestTs = -1;
    cThreads.forEach(th => {
      const last = th.tasks[th.tasks.length - 1];
      const ts = last ? (last.ts || 0) : 0;
      if (ts >= newestTs) { newestTs = ts; newest = th; }
    });
    if (newest) cSelectedThread = newest.id;
  }
}

function cThreadGroupKeys(th, viewKey) {
  if (viewKey === 'project') return [th.project || cActiveProject || '未指定專案'];
  if (viewKey === 'backend') return th.agents.length ? th.agents : ['未知'];
  if (viewKey === 'mode')    return [th.mode || '未標記'];
  if (viewKey === 'status')  return [C_STATUS_LABEL[th.status] || '未知'];
  return [cDayLabel({ day: th.day })];
}

function cThreadRow(th) {
  const st = cStatusMeta(th.status);
  const sel = cSelectedThread === th.id;
  const bits = [];
  if (th.project) bits.push(th.project);
  if (th.mode) bits.push(th.mode);
  if (th.agents.length) bits.push(th.agents.join('+'));
  if (th.turns > 1) bits.push(th.turns + ' 輪');
  const time = cRelTime({ day: th.day, time: th.time });
  return `<button type="button" onclick="cSelectThread('${escapeHtml(th.id)}')" data-c-thread="${escapeHtml(th.id)}"
            class="c-item ${sel ? 'c-item-sel' : ''}">
    <div class="flex items-center gap-2">
      <span class="c-item-dot" style="background:${st.color}"></span>
      <span class="c-item-title text-[12px] truncate flex-1">${escapeHtml(th.title)}</span>
      <span class="c-item-time text-[10px] font-mono shrink-0">${escapeHtml(time)}</span>
    </div>
    ${bits.length ? `<div class="c-item-meta text-[10px] truncate mt-0.5 pl-3.5">${escapeHtml(bits.join(' · '))}</div>` : ''}
  </button>`;
}

function cRenderItemList() {
  const host = document.getElementById('c-item-list');
  if (!host) return;
  const q = String(cSearchQuery || '').trim().toLowerCase();
  const isFailed = st => st === 'failed' || st === 'aborted';

  cBuildThreads();
  const base = [];
  cThreads.forEach(th => {
    if (cFilterKey !== 'all') {
      const ok = cFilterKey === 'failed' ? isFailed(th.status) : th.status === cFilterKey;
      if (!ok) return;
    }
    if (q) {
      const hay = ((th.title || '') + ' ' + (th.project || '') + ' ' + (th.mode || '') + ' ' +
                   th.agents.join(' ') + ' ' +
                   th.tasks.map(t => t.prompt || '').join(' ')).toLowerCase();
      if (hay.indexOf(q) === -1) return;
    }
    base.push(th);
  });

  if (!base.length) {
    host.innerHTML = `<div class="px-2 py-8 text-center text-[11px]" style="color:var(--m-faint)">
      ${q ? '沒有符合的對話' : '尚無對話紀錄'}</div>`;
    return;
  }

  const order = [];
  const groups = new Map();
  base.forEach(th => {
    cThreadGroupKeys(th, cViewKey).forEach(k => {
      let g = groups.get(k);
      if (!g) { g = { key:k, items:[] }; groups.set(k, g); order.push(g); }
      g.items.push(th);
    });
  });

  let html = '';
  order.forEach(g => {
    html += `<div class="c-group-head"><span class="truncate">${escapeHtml(g.key)}</span>` +
            `<span class="c-group-count">${g.items.length}</span></div>`;
    g.items.forEach(th => { html += cThreadRow(th); });
  });
  host.innerHTML = html;
  cRenderConversation();
}

function cSelectThread(id) {
  cSelectedThread = id;
  cCenterMode = 'thread';
  const th = cThreads.get(id);
  if (th) {
    // 進入對話串時把該串設為後續派工的接續對象
    cThreadId = id;
    cThreadStep = th.tasks.length;
  }
  cUpdateComposerHint();
  cRenderConversation();
  cRenderItemList();
}

// 「新任務」= 開一串全新的對話（對應 MiniMax Code 的「新 session」）
function cNewTask() {
  cThreadId = null;
  cThreadStep = 0;
  cSelectedThread = null;
  cCenterMode = 'thread';
  cUpdateComposerHint();
  cRenderConversation();
  focusComposer();
}

// ── 中央對話串 ─────────────────────────────────────────────────────────
function cTurnHtml(t, idx) {
  const st = cStatusMeta(t.status);
  const id = escapeHtml(t.id || '');
  const agents = (t.agents || []).map(a => {
    const hex = (C_AGENT_COLORS[a] || [])[1] || '#7C9BB5';
    return `<span class="c-conn-badge" style="background:${hex}26;color:${hex}">${escapeHtml(C_AGENT_LABELS[a] || a)}</span>`;
  }).join('');
  const meta = [];
  if (t.mode) meta.push(escapeHtml(t.mode));
  if (t.duration) meta.push(escapeHtml(t.duration));
  if (t.project) meta.push(escapeHtml(t.project));

  let actions = '';
  if (t.status === 'running') {
    actions = `<button type="button" onclick="cOpenExec()" class="c-action m-btn-ghost">明細</button>
               <button type="button" onclick="cAbortTask()" class="c-action"
                 style="background:var(--m-rose-soft);color:var(--m-rose-text);border:1px solid rgba(188,139,139,.35)">中止</button>`;
  } else if (t.status === 'failed' || t.status === 'aborted') {
    actions = `<button type="button" onclick="cContinue('${id}')" class="c-action m-btn-primary font-semibold">重試</button>`;
  } else {
    actions = `<button type="button" onclick="cContinue('${id}')" class="c-action transition"
                style="background:transparent;color:#8FACBF;border:1px solid rgba(124,155,181,.38)">以此任務接續</button>
              <button type="button" onclick="cShowDiff()" class="c-action m-btn-ghost">專案檔案 Diff</button>`;
  }

  let result = '';
  if (t.consensus) {
    result = `<div class="c-turn-bubble">${escapeHtml(t.consensus)}</div>`;
  } else if (t.status === 'running') {
    result = `<div class="c-turn-bubble" style="color:var(--m-mist)"><span class="inline-flex items-center gap-1 mr-1.5" aria-hidden="true"><span class="m-dot"></span><span class="m-dot"></span><span class="m-dot"></span></span>⏳ Agent 團隊正在雲端主機與專案工作區執行任務中，完成後將自動顯示結果…</div>`;
  } else if (t.body) {
    result = `<div class="c-turn-bubble">${t.body}</div>`;
  } else {
    result = `<div class="c-turn-bubble" style="color:var(--m-faint)">（此輪沒有產出成果）</div>`;
  }

  return `<div class="c-turn">
    <div class="c-turn-user">
      <div class="c-turn-label">
        <span>你的指令</span>
        <span class="c-conn-badge" style="background:var(--m-mist-soft);color:var(--m-mist)">第 ${t.step || (idx + 1)} 輪</span>
        <span class="c-conn-badge" style="background:transparent;color:var(--m-faint)">${escapeHtml(t.time || '')}</span>
      </div>
      <div class="c-turn-bubble">${escapeHtml(t.prompt || '')}</div>
    </div>
    <div class="c-turn-agent">
      <div class="c-turn-label">
        <span>Agent 協同結果</span>
        ${agents}
        ${meta.map(m => `<span class="c-conn-badge" style="background:transparent;color:var(--m-faint)">${m}</span>`).join('')}
        <span class="c-conn-badge" style="background:${st.color}22;color:${st.color}">${st.label}</span>
      </div>
      ${result}
      <div class="c-turn-actions">${actions}</div>
    </div>
  </div>`;
}

function cRenderConversation() {
  const head = document.getElementById('c-conv-header');
  const turns = document.getElementById('c-conv-turns');
  const conv = document.getElementById('c-conversation');
  const stream = document.getElementById('c-task-stream');
  const slot = document.getElementById('c-live-slot');
  if (!head || !turns || !conv) return;

  const overview = cCenterMode === 'overview';
  if (conv) conv.classList.toggle('hidden', overview);
  if (stream) stream.classList.toggle('hidden', !overview);
  if (overview) {
    head.classList.remove('hidden');
    head.innerHTML = `<span class="c-conv-title">任務總覽</span>
      <span class="c-conn-badge" style="background:transparent;color:var(--m-faint)">${cTasks.length} 個任務 · ${cThreads.size} 個對話串</span>
      <span class="flex-1"></span>
      <button type="button" onclick="cSetCenterMode('thread')" class="c-action m-btn-ghost">回到對話串</button>`;
    return;
  }

  const th = cSelectedThread ? cThreads.get(cSelectedThread) : null;
  if (!th) {
    head.innerHTML = `<span class="c-conv-title">尚無對話</span>
      <span class="flex-1"></span>
      <button type="button" onclick="cSetCenterMode('overview')" class="c-action m-btn-ghost">任務總覽</button>`;
    turns.innerHTML = '';
    if (slot) slot.classList.remove('hidden');
    return;
  }

  const agents = th.agents.map(a => {
    const hex = (C_AGENT_COLORS[a] || [])[1] || '#7C9BB5';
    return `<span class="c-conn-badge" style="background:${hex}26;color:${hex}">${escapeHtml(C_AGENT_LABELS[a] || a)}</span>`;
  }).join('');

  head.innerHTML = `<span class="c-conv-title truncate">${escapeHtml(th.title)}</span>
    ${agents}
    <span class="c-conn-badge" style="background:transparent;color:var(--m-faint)">${th.turns} 輪</span>
    ${th.project ? `<span class="c-conn-badge" style="background:transparent;color:var(--m-faint)">${escapeHtml(th.project)}</span>` : ''}
    ${th.mode ? `<span class="c-conn-badge" style="background:var(--m-mist-soft);color:var(--m-mist)">${escapeHtml(th.mode)}</span>` : ''}
    <span class="flex-1"></span>
    <button type="button" onclick="cSetCenterMode('overview')" class="c-action m-btn-ghost">任務總覽</button>`;

  turns.innerHTML = th.tasks.map((t, i) => cTurnHtml(t, i)).join('');

  // live slot：只有「本頁面剛派工的那一串」才顯示 legacy 的 hero card，
  // 否則會顯示跟目前對話串無關的成果。
  if (slot) {
    const showSlot = !!cLiveThreadId && cLiveThreadId === th.id;
    slot.classList.toggle('hidden', !showSlot);
  }
}

function cSetCenterMode(mode) {
  cCenterMode = mode === 'overview' ? 'overview' : 'thread';
  cRenderConversation();
  cRenderStream();
}

function cSetView(key) {
  cViewKey = C_VIEWS[key] ? key : 'timeline';
  const v = C_VIEWS[cViewKey];
  const label = document.getElementById('c-view-label');
  if (label) label.textContent = v.label;
  document.querySelectorAll('.c-menu-item[data-view]').forEach(b => {
    b.classList.toggle('c-on', b.dataset.view === cViewKey);
  });
  cToggleViewMenu(false);
  cRenderItemList();
}

function cToggleViewMenu(force) {
  const menu = document.getElementById('c-view-menu');
  if (!menu) return;
  const show = (typeof force === 'boolean') ? force : menu.classList.contains('hidden');
  menu.classList.toggle('hidden', !show);
  const btn = document.getElementById('c-view-btn');
  if (btn) btn.setAttribute('aria-expanded', show ? 'true' : 'false');
  if (show) cToggleProjectMenu(false);
}

function cToggleProjectMenu(force) {
  const menu = document.getElementById('c-project-menu');
  if (!menu) return;
  const show = (typeof force === 'boolean') ? force : menu.classList.contains('hidden');
  menu.classList.toggle('hidden', !show);
  const btn = document.getElementById('c-project-btn');
  if (btn) btn.setAttribute('aria-expanded', show ? 'true' : 'false');
  if (show) cToggleViewMenu(false);
}

function cToggleSearch() {
  const row = document.getElementById('c-search-row');
  if (!row) return;
  const show = row.classList.contains('hidden');
  row.classList.toggle('hidden', !show);
  if (show) {
    const inp = document.getElementById('c-list-search');
    if (inp) inp.focus();
  } else {
    cFilterList('');
  }
}

function cFilterList(q) {
  cSearchQuery = q || '';
  cRenderItemList();
}

// ── Agent 選取：composer 的 chip 與拓撲面板的 checkbox 雙向同步 ──────
function cToggleAgent(id, on) {
  const cb = document.querySelector('input[name="agent_target"][value="' + id + '"]');
  if (!cb) return;
  cb.checked = !!on;
  syncTopologyBeams(!!cRunningTask);
  cSyncAgentChips();
}

function cSyncAgentChips() {
  // chip 的選中態是 inline style，因此直接重繪最簡單也最不易出錯
  cRenderAgentChips();
}

const C_AGENT_LABELS = {
  claude:'Claude', codex:'Codex', antigravity:'AGY',
  minimax:'minimax', zcode:'zcode', khavis:'K.H.A.V.I.S.'
};

function cRenderAgentChips() {
  const host = document.getElementById('c-agent-chips');
  if (!host) return;
  const seen = [];
  document.querySelectorAll('input[name="agent_target"]').forEach(b => {
    if (!seen.some(v => v.value === b.value)) seen.push(b);
  });
  host.innerHTML = seen.map(b => {
    const hex = (C_AGENT_COLORS[b.value] || [])[1] || '#7C9BB5';
    const label = C_AGENT_LABELS[b.value] || b.value;
    const on = b.checked;
    // 切換目標在渲染時就算好：原本用 classList.contains('m-btn-primary') 判斷，
    // 而 chip 從來沒有這個 class → 點擊永遠只能選取、無法取消。
    return `<button type="button" class="c-agent-chip px-2 py-0.5 rounded-md text-[11px] transition inline-flex items-center gap-1"
              data-agent="${b.value}" aria-pressed="${on ? 'true' : 'false'}"
              onclick="cToggleAgent('${b.value}', ${on ? 'false' : 'true'})"
              style="background:${on ? hex + '2E' : 'var(--m-faint-bg)'};color:${on ? hex : 'var(--m-dim)'};border:1px solid ${on ? hex + '66' : 'var(--m-line)'}"
              title="${label} — ${on ? '已選取，點擊取消' : '點擊選取'}">${on ? '<span aria-hidden="true">✓</span>' : ''}${label}</button>`;
  }).join('')
  + `<button type="button" onclick="cAddAgent()" class="px-2 py-0.5 rounded-md text-[11px] m-btn-ghost transition" title="掛載外部 CLI / API Agent">＋ 加入</button>`;
}

function cAddAgent() {
  const d = document.getElementById('c-topology-collapse');
  if (d) { d.open = true; d.scrollIntoView({ behavior:'smooth', block:'center' }); }
}

function cSelectProject(name) {
  const sel = document.getElementById('ws-project-select');
  if (sel && sel.value !== name) {
    sel.value = name;
    switchSharedProject(name);
  }
  if (typeof currentProjectName !== 'undefined') currentProjectName = name;
  const active = document.getElementById('c-active-project');
  if (active) active.textContent = name;
  document.querySelectorAll('#c-project-menu .c-menu-item').forEach(b => {
    b.classList.toggle('c-on', (b.getAttribute('data-project') || '') === name);
  });
  cUpdateComposerHint();
  cToggleSidebar(false);
}

function focusComposer() {
  switchTab('command');
  const el = document.getElementById('prompt-input');
  if (el) { el.focus(); el.scrollIntoView({ behavior:'smooth', block:'nearest' }); }
}

function cUpdateComposerHint() {
  const h = document.getElementById('c-composer-hint');
  if (!h) return;
  const proj = (typeof currentProjectName !== 'undefined' && currentProjectName) ? currentProjectName : 'shared-app';
  const ctx = cThreadId ? ' · 接續 ' + cThreadId.slice(0, 8) + ' 第 ' + ((cThreadStep || 0) + 1) + ' 輪' : '';
  h.textContent = proj + ctx + ' · ⌘/Ctrl+⏎ 執行 · ⏎ 換行';
}

// ── 任務卡片流 ──────────────────────────────────────────────────────
function cStatusMeta(status) {
  if (status === 'running') return { color:'var(--m-mist)', label:'執行中', live:true };
  if (status === 'failed')  return { color:'var(--m-rose)', label:'失敗', live:false };
  if (status === 'aborted') return { color:'var(--m-apricot)', label:'已中止', live:false };
  return { color:'var(--m-sage)', label:'已完成', live:false };
}

function cAgentDots(agents) {
  return (agents || []).map(a => {
    const [, hex] = C_AGENT_COLORS[a] || ['--m-mist', '#7C9BB5'];
    const initial = (a || '?').charAt(0).toUpperCase();
    return `<span class="w-4 h-4 rounded-full grid place-items-center text-[8px] font-bold"
              style="background:${hex}26;color:${hex};border:1px solid ${hex}55" title="${a}">${initial}</span>`;
  }).join('');
}

function cTaskActions(t, expanded) {
  const id = escapeHtml(t.id || '');
  if (t.status === 'running') {
    return `<button type="button" onclick="cOpenExec()" class="c-action m-btn-ghost">明細</button>
            <button type="button" onclick="cAbortTask()" class="c-action"
              style="background:var(--m-rose-soft);color:var(--m-rose-text);border:1px solid rgba(188,139,139,.35)">中止</button>`;
  }
  if (t.status === 'failed' || t.status === 'aborted') {
    return `<button type="button" onclick="cToggleExpand('${id}')" class="c-action m-btn-ghost">${expanded ? '收合' : '看原因'}</button>
            <button type="button" onclick="cRerun('${id}')" class="c-action m-btn-primary font-semibold">重試</button>`;
  }
  return `<button type="button" onclick="cContinue('${id}')" class="c-action transition"
            style="background:transparent;color:#8FACBF;border:1px solid rgba(124,155,181,.38)">以此任務接續</button>
          <button type="button" onclick="cRerun('${id}')" class="c-action m-btn-ghost">重新執行</button>`;
}

function cTaskCard(t, opts) {
  const expanded = !!(opts && opts.expanded);
  const agents = t.agents || [];
  const st = cStatusMeta(t.status);
  const id = escapeHtml(t.id || '');

  const meta = [];
  if (t.id) meta.push(`<span class="shrink-0">${id}</span>`);
  if (t.project) meta.push(`<span class="shrink-0" style="color:var(--m-line)">|</span><span class="truncate">${escapeHtml(t.project)}</span>`);
  if (t.duration) meta.push(`<span class="shrink-0" style="color:var(--m-line)">|</span><span class="shrink-0">${escapeHtml(t.duration)}</span>`);
  if (t.tokens) meta.push(`<span class="shrink-0" style="color:var(--m-line)">|</span><span class="shrink-0">${escapeHtml(t.tokens)} tok</span>`);
  if (t.summary) meta.push(`<span class="shrink-0" style="color:var(--m-line)">|</span><span class="truncate" style="color:${st.color}">${escapeHtml(t.summary)}</span>`);

  // 執行中：後端 dispatch 是單次阻塞請求，沒有可回報的階段進度。
  // 原本用 timer 假造「百分比」會在 4 秒內跳到 81%，這裡改成
  // 「不確定進度條 + 真實經過時間 + 真實狀態文字」。
  const liveBlock = t.status === 'running' ? `
    <div class="pt-2.5">
      <div class="h-1 rounded-full overflow-hidden m-indeterminate" style="background:var(--m-track)">
        <div id="c-progress-bar" class="h-full w-full" style="background:linear-gradient(90deg,#7C9BB5,#8FA894)"></div>
      </div>
      <div class="flex items-center gap-2 mt-2">
        <span class="text-[10px] shrink-0" style="color:var(--m-faint)">標準流程</span>
        <div id="c-stage-row" class="grid grid-cols-4 gap-1.5 text-[10.5px] flex-1 min-w-0"></div>
      </div>
      <div class="flex items-center gap-2 mt-2 text-[11px]" style="color:var(--m-dim)">
        <span class="inline-flex items-center gap-0.5 shrink-0" aria-hidden="true"><span class="m-dot"></span><span class="m-dot"></span><span class="m-dot"></span></span>
        <span id="c-live-status" class="truncate">執行中…</span>
        <span id="c-live-timer" class="ml-auto font-mono shrink-0" style="color:var(--m-faint)">0.0s</span>
      </div>
      <div id="c-console" class="mt-2 rounded-lg p-2.5 font-mono text-[10.5px] leading-[1.65] max-h-28 overflow-y-auto m-line"
           style="background:var(--m-panel-3)">
        <div style="color:var(--m-faint)">等待回應…</div>
      </div>
    </div>` : '';

  return `
  <article class="frost m-line rounded-2xl overflow-hidden m-raise c-card ${t.status==='running'?'m-in':''}"
           data-status="${t.status}" data-id="${id}">
    <div class="px-4 py-3">
      <!-- 第一行：狀態點 + 任務標題（標題永遠有自己的整行寬度，不會被動作鈕擠掉） -->
      <div class="flex items-start gap-2.5">
        <span class="w-2 h-2 rounded-full shrink-0 mt-1.5 ${st.live?'m-live':''}"
              style="background:${st.color}" title="${st.label}"></span>
        <div class="flex-1 min-w-0">
          <div class="flex items-start gap-2">
            <h3 class="c-card-title text-sm font-medium leading-snug flex-1 min-w-0"
                style="color:var(--m-bone)" title="${escapeHtml(t.prompt || '')}">${escapeHtml(t.prompt || '系統派工任務')}</h3>
            ${t.mode ? `<span class="m-chip shrink-0 mt-0.5" style="background:var(--m-mist-soft);color:var(--m-mist);border-color:rgba(124,155,181,.25)">${escapeHtml(t.mode)}</span>` : ''}
          </div>
          <div class="c-meta-line flex items-center gap-1.5 mt-1.5 text-[10px] font-mono" style="color:var(--m-faint)">
            ${meta.join(' ')}
            ${agents.length ? `<span class="inline-flex -space-x-1 shrink-0">${cAgentDots(agents)}</span>` : ''}
          </div>
        </div>
        <button type="button" onclick="cToggleExpand('${id}')"
                class="w-7 h-7 shrink-0 rounded-lg m-btn-ghost grid place-items-center transition"
                aria-expanded="${expanded ? 'true' : 'false'}" title="${expanded ? '收合' : '展開'}">
          <svg class="c-caret ${expanded?'c-caret-open':''}" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>

      ${liveBlock}

      <!-- 第二行：動作列 -->
      <div class="mt-2.5 flex items-center gap-1.5 flex-wrap justify-end">
        ${cTaskActions(t, expanded)}
      </div>
    </div>

    <div class="c-body ${expanded ? '' : 'hidden'} px-4 pb-3.5">
      ${t.body || '<div class="text-[11px]" style="color:var(--m-faint)">（此任務沒有額外輸出）</div>'}
      <div class="flex flex-wrap gap-1.5 mt-2.5">
        <button type="button" onclick="cShowDiff()" class="c-action m-btn-ghost">專案檔案 Diff</button>
        <button type="button" onclick="cOpenExec()" class="c-action m-btn-ghost">完整輸出</button>
      </div>
    </div>
  </article>`;
}

function cRenderStream() {
  const host = document.getElementById('c-task-stream');
  if (!host) return;
  const main = document.getElementById('c-main');
  const keepScroll = main ? main.scrollTop : 0;
  const isFailed = t => t.status === 'failed' || t.status === 'aborted';
  const list = cFilterKey === 'all'
    ? cTasks
    : cTasks.filter(t => cFilterKey === 'failed' ? isFailed(t) : t.status === cFilterKey);

  if (!list.length) {
    host.innerHTML = `<div class="text-center py-12" style="color:var(--m-faint)">
      <div class="text-sm mb-1">${cFilterKey==='all'?'尚無任務紀錄':'此篩選沒有任務'}</div>
      <div class="text-xs">在下方輸入你的目標，按 ⏎ 開始第一個任務</div>
    </div>`;
    cUpdateCounts();
    cRenderItemList();
    return;
  }

  let html = '';
  let lastDay = null;
  list.forEach(t => {
    if (t.day !== lastDay) {
      lastDay = t.day;
      html += `<div class="flex items-center gap-3 text-[11px] py-2" style="color:var(--m-faint)">
        <div class="h-px flex-1" style="background:var(--m-line)"></div><span>${escapeHtml(t.day||'')}</span>
        <div class="h-px flex-1" style="background:var(--m-line)"></div></div>`;
    }
    html += cTaskCard(t, { expanded: !!t.expanded });
  });
  host.innerHTML = html;
  if (main) main.scrollTop = keepScroll;   // 重新渲染不要把使用者捲回原位
  cUpdateCounts();
  cRenderItemList();
}

function cUpdateCounts() {
  const running = cTasks.filter(t => t.status === 'running').length;
  const done = cTasks.filter(t => t.status === 'done').length;
  const failed = cTasks.filter(t => t.status === 'failed' || t.status === 'aborted').length;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
  set('c-count-running', running);
  set('c-count-done', done);
  set('c-count-failed', failed);
}

function cFilter(key) {
  cFilterKey = key;
  document.querySelectorAll('.c-filter-btn').forEach(b => {
    const on = b.dataset.filter === key;
    b.style.background = on ? 'rgba(124,155,181,.18)' : 'transparent';
    b.style.color      = on ? '#8FACBF' : 'var(--m-dim)';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  document.querySelectorAll('[data-cfilter]').forEach(b => {
    const on = b.dataset.cfilter === key;
    b.classList.toggle('m-nav-active', on);
    b.classList.toggle('m-nav', !on);
  });
  cRenderStream();
  cRenderItemList();
}

// ── 卡片動作 ────────────────────────────────────────────────────────
function cToggleExpand(id) {
  const t = cTasks.find(x => x.id === id);
  if (!t) return;
  t.expanded = !t.expanded;      // 展開狀態必須存進資料，否則下次重繪就被收合
  cRenderStream();
}

function cContinue(id) {
  const t = cTasks.find(x => x.id === id);
  if (!t) return;
  // 續做哪一串對話，就切到哪一串
  cThreadId = cThreadKeyOf(t);
  cThreadStep = t.step || 1;
  cSelectedThread = cThreadId;
  // 真的帶入上一輪成果讓後端接續（原本只塞了一個 placeholder 字串）
  if (t.consensus) {
    try {
      const prev = (typeof previousTurnContext !== 'undefined' && previousTurnContext) ? previousTurnContext : null;
      previousTurnContext = {
        prompt: t.prompt,
        consensus: t.consensus,
        step: prev ? (prev.step || 1) + 1 : 1
      };
      if (typeof syncContinuationBanner === 'function') syncContinuationBanner();
    } catch (e) { /* 取不到就退回純文字接續 */ }
  }
  focusComposer();
  const el = document.getElementById('prompt-input');
  if (el) {
    el.value = t.prompt || '';
    el.focus();
    try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) {}
  }
  cToast(t.consensus ? '已帶入上一輪脈絡，可直接繼續下指令' : '已載入任務內容，可直接繼續下指令', 'ok');
}

function cRerun(id) {
  const t = cTasks.find(x => x.id === id);
  if (!t) return;
  if (cRunningTask) { cToast('目前已有任務在執行中，請等待完成或先中止', 'err'); return; }
  cThreadId = cThreadKeyOf(t);
  cThreadStep = t.step || 1;
  cSelectedThread = cThreadId;
  const el = document.getElementById('prompt-input');
  if (el) el.value = t.prompt || '';
  focusComposer();
  submitDispatch();
}

function cAbortTask() {
  if (!_cAbortController) { cToast('此任務已結束或無法中止', 'err'); return; }
  cAborted = true;
  try { _cAbortController.abort(); } catch (e) {}
  cToast('已中止等待（後端可能仍在完成任務）', 'err');
}

function cOpenExec() {
  cToggleDrawer(true);
}

function cShowDiff() {
  const ws = document.getElementById('c-workspace-collapse');
  if (ws) {
    ws.open = true;
    if (typeof ws.scrollIntoView === 'function') ws.scrollIntoView({ behavior:'smooth', block:'nearest' });
  }
  const v = document.getElementById('ws-diff-viewer');
  if (v && typeof v.scrollIntoView === 'function') v.scrollIntoView({ behavior:'smooth', block:'center' });
  cToast('已展開工作區的專案檔案 Diff', 'ok');
}

// ── 側欄工作區清單 ──────────────────────────────────────────────────
async function cLoadProjects() {
  const menu = document.getElementById('c-project-menu');
  if (!menu) return;
  try {
    const res = await fetch('/api/workbench/workspace');
    if (!res.ok) return;
    const data = await res.json();
    const active = data.active_project || 'shared-app';
    cActiveProject = active;
    const projects = data.projects || [];
    const activeEl = document.getElementById('c-active-project');
    if (activeEl) activeEl.textContent = active;
    const cnt = document.getElementById('c-project-count');
    if (cnt) cnt.textContent = String(projects.length);
    menu.innerHTML = projects.map(p => `
      <button type="button" data-project="${escapeHtml(p)}"
              onclick="cSelectProject('${escapeHtml(p)}');cToggleProjectMenu(false)"
              class="c-menu-item ${p === active ? 'c-on' : ''}">
        <span class="w-1.5 h-1.5 rounded-full shrink-0" style="background:${p === active ? 'var(--m-mist)' : 'var(--m-faint)'}"></span>
        <span class="truncate">${escapeHtml(p)}</span>
      </button>`).join('');
  } catch (_) { /* workspace 不可用時保留預設項目 */ }
}

// ── 從 /api/workbench/history 載入任務流 ─────────────────────────────
function cToday() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

function cClockNow() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
}

async function cLoadTasks() {
  try {
    const res = await fetch('/api/workbench/history');
    if (!res.ok) return;
    const data = await res.json();
    const items = data.history || [];
    if (!items.length) { cTasks = []; cRenderStream(); return; }

    cTasks = items.map((h, i) => {
      const ts = h.dispatched_at || '';
      const day = ts.indexOf('-') !== -1 ? ts.split(' ')[0] : '最近';
      // 用完整時間做 handle：同一分鐘內的多次派工必須有不同 id，
      // 否則「以此任務接續 / 重試」會永遠作用在第一張卡上。
      const hms = (ts.match(/\\d{2}:\\d{2}:\\d{2}/) || [''])[0];
      const lat = h.latency_ms != null ? `${(h.latency_ms/1000).toFixed(1)}s` : null;
      const ok = h.ok !== false;
      return {
        id: hms ? ('#' + hms.split(':').join('')) : ('#' + (0x8a3f - i * 0x11).toString(16)),
        prompt: h.prompt || '系統派工任務',
        source: h.consensus_source || 'K.H.A.V.I.S. Pipeline',
        project: h.project || '',
        thread: h.thread || '',
        step: h.step || 1,
        ts: h.ts || 0,
        day: day,
        time: hms,
        duration: lat,
        status: ok ? 'done' : 'failed',
        agents: Array.isArray(h.backends) ? h.backends : [],
        mode: h.collab_mode || '',
        summary: (h.consensus_source || (ok ? '成功' : '失敗')).slice(0, 28),
        consensus: h.consensus || '',
        expanded: false,
        body: `<div class="rounded-xl p-3 space-y-2 m-line" style="background:var(--m-panel-2)">
                 <div class="text-[11px] font-mono leading-[1.7]" style="color:var(--m-dim)">
                   來源: ${escapeHtml(h.consensus_source || 'Fan-out')}
                   ${lat ? ` · 耗時 ${lat}` : ''}
                   ${h.collab_mode ? ` · 模式 ${escapeHtml(h.collab_mode)}` : ''}
                   ${Array.isArray(h.backends) && h.backends.length ? ` · ${escapeHtml(h.backends.join(' + '))}` : ''}
                 </div>
                 ${h.consensus ? `<div class="text-[11px] font-mono leading-[1.7] whitespace-pre-wrap max-h-40 overflow-y-auto mt-1" style="color:var(--m-dim)">${escapeHtml(h.consensus)}</div>` : ''}
               </div>`
      };
    });

    cRenderStream();
  } catch (_) { /* history 不可用時靜默退回空狀態 */ }
}

// ── 派工生命週期：把既有 submitDispatch 的結果接進任務流 ────────────
// 把對話串識別帶進 legacy 的 previous_context。
// 後端會沿用 thread id 並以 step+1 當作這一輪的輪次；
// build_contextual_prompt 對空的 prompt/consensus 會直接略過，
// 所以第一輪帶一個只有 thread 的 context 不會改變模型收到的 prompt。
function cPrepareThreadContext() {
  if (!cThreadId) cThreadId = 't' + Date.now().toString(36);
  if (typeof previousTurnContext === 'undefined') return;
  if (!previousTurnContext) previousTurnContext = { prompt:'', consensus:'', step:0 };
  previousTurnContext.thread = cThreadId;
  previousTurnContext.step = cThreadStep;
}

function cBeginTask(prompt, agents, mode) {
  // 前綴 r 讓執行中任務的 handle 不會和歷史紀錄（純數字）撞號
  const id = '#r' + (Date.now() % 0xffff).toString(16);
  const task = {
    id, prompt, agents, mode,
    project: (typeof currentProjectName !== 'undefined' ? currentProjectName : 'shared-app'),
    thread: cThreadId || '',
    step: (cThreadStep || 0) + 1,
    ts: Date.now() / 1000,
    day: cToday(), status: 'running', duration: null, time: cClockNow(),
    summary: '執行中', consensus: '', body: '', expanded: false
  };
  cTasks.unshift(task);
  cRunningTask = id;
  cLiveThreadId = task.thread || cLiveThreadId;
  cSelectedThread = task.thread || cSelectedThread;
  cFilter('all');
  cRenderConversation();
  cRenderStream();
  const main = document.getElementById('c-main');
  if (main) main.scrollTop = 0;   // 新任務在最上方，直接看得到
  return id;
}

// 當瀏覽器/代理連線因長任務超時中斷時，背景輪詢 /api/workbench/history 自動取回後端寫入的成果
function cPollRecoverTask(taskId, promptText, threadId) {
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts += 1;
    if (attempts > 15) { clearInterval(timer); return; }
    try {
      const res = await fetch('/api/workbench/history');
      if (!res.ok) return;
      const data = await res.json();
      const items = data.history || [];
      const match = items.find(h =>
        (threadId && h.thread === threadId && h.consensus) ||
        (h.prompt === promptText && h.consensus && (Date.now()/1000 - (h.ts || 0) < 300))
      );
      if (match && match.consensus) {
        clearInterval(timer);
        const card = cTasks.find(t => t.id === taskId);
        if (card) {
          card.status = 'done';
          card.summary = '成功';
          card.consensus = match.consensus;
          card.duration = match.latency_ms != null ? `${(match.latency_ms/1000).toFixed(1)}s` : card.duration;
          card.body = `<div class="rounded-xl p-3 space-y-2 m-line" style="background:var(--m-panel-2)">
            <div class="text-[11px] font-mono whitespace-pre-wrap leading-[1.7] max-h-56 overflow-y-auto" style="color:var(--m-dim)">${escapeHtml(match.consensus)}</div>
          </div>`;
        }
        if (typeof latestFinalDeliverableText !== 'undefined') latestFinalDeliverableText = match.consensus;
        cRenderStream();
        cRenderConversation();
        cSetDrawerDot(true);
        cToast('已從伺服器同步取回剛才完成的任務成果！', 'ok');
      }
    } catch (_) {}
  }, 4000);
}

// 包裹既有的 submitDispatch：任務卡的建立 / 收尾都由這裡驅動，
// 原本的 fetch、collab_mode、previous_context 邏輯完全不動。
const _submitDispatchLegacy = __legacySubmitDispatch;
async function submitDispatch() {
  if (cRunningTask) { cToast('目前已有任務在執行中，請等待完成或先中止', 'err'); return; }
  const el = document.getElementById('prompt-input');
  const prompt = el ? el.value.trim() : '';
  if (!prompt) { cToast('請先輸入任務指示', 'err'); return; }

  // legacy 原本用 alert() 說「請至少在上方拓撲圖點選一個 Agent」，
  // 但 C 版把拓撲面板收進摺疊區，使用者根本看不到該處 → 改成可操作的提示。
  const picked = Array.from(document.querySelectorAll('input[name="agent_target"]:checked')).map(c => c.value);
  if (!picked.length) {
    cToast('請至少選取一個參與 Agent（展開「Agent 拓撲」面板即可勾選）', 'err');
    const topo = document.getElementById('c-topology-collapse');
    if (topo) {
      topo.open = true;
      if (typeof topo.scrollIntoView === 'function') topo.scrollIntoView({ behavior:'smooth', block:'nearest' });
    }
    return;
  }

  cAborted = false;
  cPrepareThreadContext();
  cBeginTask(prompt, picked, typeof currentCollabMode !== 'undefined' ? currentCollabMode : '');

  const startedAt = performance.now();
  const taskId = cRunningTask;
  let secs = '0.0s';
  let ok = false;
  let dispatchError = null;
  let statusText = '';
  try {
    await _submitDispatchLegacy();
    secs = ((performance.now() - startedAt) / 1000).toFixed(1);
    const statusEl = document.getElementById('exec-status-text');
    statusText = statusEl ? String(statusEl.textContent || '') : '';
    ok = statusText.indexOf('✅') !== -1;
  } catch (e) {
    dispatchError = e;
  }

  const card = cTasks.find(t => t.id === taskId);
  if (card) card.duration = secs + 's';

  const consensus = (typeof latestFinalDeliverableText !== 'undefined' && latestFinalDeliverableText)
    ? latestFinalDeliverableText : '';

  let body = '';
  if (consensus) {
    body = `<div class="rounded-xl p-3 space-y-2 m-line" style="background:var(--m-panel-2)">
              <div class="text-[11px] font-mono whitespace-pre-wrap leading-[1.7] max-h-56 overflow-y-auto" style="color:var(--m-dim)">${escapeHtml(consensus)}</div>
            </div>`;
  } else if (!ok) {
    // 原本失敗時 body 是空的，使用者只看到「失敗」兩個字，讀不到原因
    const reason = String(statusText || (dispatchError ? (dispatchError.message || dispatchError) : ''))
      .replace(/^執行失敗[:：]\\s*/, '')
      .replace(/^網路或伺服器通訊錯誤[:：]\\s*/, '')
      .trim();
    body = `<div class="rounded-xl p-3 m-line" style="background:var(--m-rose-soft);border-color:rgba(188,139,139,.35)">
              <div class="text-[11px] leading-[1.7]" style="color:var(--m-rose-text)">
                <b>${cAborted ? '已中止等待' : '連線逾時或執行未完成（正在背景自動同步伺服器成果…）'}</b><br>${escapeHtml(reason || '後端未回報詳細原因')}
              </div>
            </div>`;
  }

  cThreadStep = (cThreadStep || 0) + 1;
  if (typeof previousTurnContext !== 'undefined' && previousTurnContext) {
    previousTurnContext.step = cThreadStep;
    previousTurnContext.thread = cThreadId;
  }
  cFinishTask(ok && !dispatchError, body, consensus);
  cRenderConversation();

  if (!ok && !cAborted) {
    cPollRecoverTask(taskId, prompt, cThreadId);
  }

  if (dispatchError) { cToast('派工失敗：' + (dispatchError.message || '未知錯誤'), 'err'); }
  if (dispatchError) throw dispatchError;
  if (!ok) { cToast('等待回應逾時，系統將在後端完成後自動回填結果', 'err'); return; }

  cSetDrawerDot(true);  // 抽屜按鈕亮紅點，成果在右側等使用者展開
  cToast('任務完成，成果已產出（右上角可展開執行明細）', 'ok');
}

// 相容性：舊版 DOM 若仍存在 #c-stage-row 就更新它。
// C 版刻意「不」顯示階段百分比 —— 後端 dispatch 是單次阻塞請求，
// 沒有任何可回報的階段進度；原本每 1.1 秒自動前進一階的 timer 會在
// 4 秒內跳到 81%，嚴重誤導。這裡只呈現「標準流程的形狀」，
// 直到真的全部完成才轉為 ✓。
function cStageUpdate(idx) {
  const row = document.getElementById('c-stage-row');
  if (!row) return;
  const done = idx >= 4;                 // 只有「全部完成」是真實訊號
  const labels = ['規劃','實作','互評','驗收'];
  row.innerHTML = labels.map((l) => {
    const color = done ? 'var(--m-sage)' : 'var(--m-faint)';
    const mark  = done ? '✓' : '<span class="m-live" style="color:var(--m-mist)">·</span>';
    return `<div class="flex items-center gap-1 truncate" style="color:${color}">${mark}<span class="truncate">${l}</span></div>`;
  }).join('');
}

function cConsoleLine(html) {
  const box = document.getElementById('c-console');
  if (!box) return;
  box.insertAdjacentHTML('beforeend', `<div class="m-in">${html}</div>`);
  while (box.childElementCount > 8) box.removeChild(box.firstElementChild);
}

// 相容性保留：C 版改用不確定進度條（#c-progress-bar 是 shimmer 軌道），
// 不再設定百分比寬度。
function cProgress(pct) {
  const bar = document.getElementById('c-progress-bar');
  if (bar) bar.style.width = '100%';
}

function cFinishTask(ok, summaryHtml, consensus) {
  const card = cTasks.find(t => t.id === cRunningTask);
  if (card) {
    card.status = ok ? 'done' : (cAborted ? 'aborted' : 'failed');
    card.summary = ok ? '成功' : (cAborted ? '已中止' : '失敗');
    card.body = summaryHtml || '';
    card.consensus = consensus || '';
    card.expanded = true;
  }
  cRunningTask = null;
  _cAbortController = null;
  cRenderStream();
}

// ── 攔截既有 pipeline stepper ──────────────────────────────────────
const _setPipelineStepStateLegacy = __legacySetPipelineStep;
function setPipelineStepState(idx, finished) {
  _setPipelineStepStateLegacy(idx, finished);
  if (cRunningTask) {
    cStageUpdate(finished ? 4 : 0);
    if (finished) cConsoleLine('<span style="color:var(--m-sage)">✓ 協同流程完成</span>');
  }
}

// ── 把 legacy 面板內的真實狀態鏡像到摘要列與執行中的卡片 ────────────
function cMirrorStatus() {
  const map = [['exec-status-text','c-exec-status-text'],
               ['exec-timer','c-exec-timer'],
               ['ws-file-count','c-ws-file-count'],
               ['exec-status-text','c-live-status'],
               ['exec-timer','c-live-timer']];
  map.forEach(([src, dst]) => {
    const a = document.getElementById(src), b = document.getElementById(dst);
    if (a && b && b.textContent !== a.textContent) b.textContent = a.textContent;
  });
}

// ── composer 瘦身：把「快速任務範本」收進摺疊區，省下垂直空間 ──────
function cCompactComposer() {
  const composer = document.querySelector('.composer');
  if (!composer || !composer.querySelectorAll) return;
  let row = null;
  const btns = composer.querySelectorAll('button');
  for (let i = 0; i < btns.length; i++) {
    const oc = btns[i].getAttribute('onclick') || '';
    if (oc.indexOf('setPromptTemplate') !== -1) {
      row = btns[i].parentElement ? btns[i].parentElement.parentElement : null;
      break;
    }
  }
  if (!row || !row.parentElement) return;
  if (row.parentElement.tagName === 'DETAILS') return;   // 已經收過了

  const det = document.createElement('details');
  det.className = 'm-collapse';
  det.id = 'c-template-collapse';
  const sum = document.createElement('summary');
  sum.className = 'px-1 py-1 flex items-center gap-1.5 cursor-pointer text-[11px]';
  sum.style.color = 'var(--m-faint)';
  sum.innerHTML = '<svg class="m-caret" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg><span>快速任務範本</span>';
  det.appendChild(sum);
  row.parentElement.insertBefore(det, row);
  det.appendChild(row);
  const labelEl = row.firstElementChild;
  if (labelEl) labelEl.style.display = 'none';
}

// ── 啟動 ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  cRenderAgentChips();
  cSetView('timeline');
  cFilter('all');
  // 把 legacy 的成果容器搬到中央對話串（同一個元素，legacy JS 照常寫入）
  try {
    const live = document.getElementById('live-results-container');
    const slot = document.getElementById('c-live-slot');
    if (live && slot && live.parentElement !== slot) slot.appendChild(live);
  } catch (e) { /* 搬不動就維持原位 */ }
  setInterval(cMirrorStatus, 400);
  cLoadTasks();
  cLoadProjects();
  cCompactComposer();
  cUpdateComposerHint();
  cRenderConversation();
  switchTab('command');

  // Agent 勾選變動時回寫 composer chip
  document.addEventListener('change', e => {
    if (e.target && e.target.name === 'agent_target') cSyncAgentChips();
  });
  // ⌘/Ctrl+Enter 送出，一般 Enter 換行（避免打字或換行時誤觸直接送出執行）
  const pi = document.getElementById('prompt-input');
  if (pi) {
    pi.addEventListener('keydown', e => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submitDispatch(); }
    });
    pi.addEventListener('input', () => { pi.style.height='auto'; pi.style.height=Math.min(pi.scrollHeight,160)+'px'; });
  }
  // Esc 關閉側欄抽屜 / 選單
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    cToggleSidebar(false);
    cToggleViewMenu(false);
    cToggleProjectMenu(false);
  });
  // 點擊選單以外的地方就把選單收起來
  document.addEventListener('click', e => {
    const t = e.target;
    if (!t) return;
    const inside = id => {
      const el = document.getElementById(id);
      return !!(el && el.contains && el.contains(t));
    };
    if (!inside('c-view-menu') && !inside('c-view-btn')) cToggleViewMenu(false);
    if (!inside('c-project-menu') && !inside('c-project-btn')) cToggleProjectMenu(false);
  });
});
</script>
"""


def render_workbench_html_c() -> str:
    """Render the Option-C task-stream Workbench (Morandi palette)."""
    workspace = _rebalance(_slice("workspace"))
    topology = _rebalance(_slice("topology"))
    composer_block = _rebalance(_slice("composer"))
    result = _slice("result")
    views = _slice("views")
    drawers = _slice("drawers")

    body = f"""<body class="font-sans antialiased h-screen flex overflow-hidden m-scroll">
{_SIDEBAR}

<div class="flex-1 flex flex-col min-w-0">
{_TOPBAR}

<main id="c-main" class="flex-1 overflow-y-auto m-scroll">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 py-5">

    <section id="view-command" class="tab-content block space-y-3">
      <!-- 中央 = 對話串（你的指令 → Agent 協同結果 → 追問）。
           階段 / 延遲 / 各 Agent 原始輸出在右側抽屜，細節退到第二層。 -->
      <div id="c-conversation" class="space-y-3">
        <div id="c-conv-header" class="c-conv-header"></div>
        <div id="c-conv-turns" class="space-y-3"></div>
        <!-- legacy 的 live-results-container 會被搬進來：
             hero card、「接下來怎麼辦」按鈕與追問框都在這一格，且永不重建。 -->
        <div id="c-live-slot" class="c-live-slot"></div>
      </div>

      <!-- 總覽模式：所有任務的卡片流（次要視圖） -->
      <div id="c-task-stream" class="space-y-3 hidden"></div>

      <!-- 工作區 -->
      <details class="m-collapse frost m-line rounded-2xl overflow-hidden" id="c-workspace-collapse">
        <summary class="px-4 py-3 flex items-center gap-2.5 hover:bg-white/[.02] transition cursor-pointer">
          <svg class="m-caret" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span class="text-xs font-semibold shrink-0" style="color:var(--m-dim)">工作區</span>
          <span class="text-[11px] truncate hidden sm:inline" style="color:var(--m-faint)">Git Worktree 與檔案 Diff</span>
          <span class="flex-1"></span>
          <span class="text-[11px] font-mono shrink-0" style="color:var(--m-faint)" id="c-ws-file-count">0</span>
        </summary>
        <div class="px-4 pb-4">{workspace}</div>
      </details>

      <!-- Agent 拓撲與模型 -->
      <details class="m-collapse frost m-line rounded-2xl overflow-hidden" id="c-topology-collapse">
        <summary class="px-4 py-3 flex items-center gap-2.5 hover:bg-white/[.02] transition cursor-pointer">
          <svg class="m-caret" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span class="text-xs font-semibold shrink-0" style="color:var(--m-dim)">Agent 拓撲</span>
          <span class="text-[11px] truncate hidden sm:inline" style="color:var(--m-faint)">模型設定 · 自訂 Agent · 進階設定</span>
        </summary>
        <div class="px-4 pb-4">{topology}</div>
      </details>

    </section>

{views}
  </div>
</main>

{_COMPOSER_CHROME_TOP}
{composer_block}
{_COMPOSER_CHROME_BOTTOM}
</div>

<!-- 右側抽屜：執行明細（寬螢幕是常駐第三欄，窄螢幕是覆蓋式抽屜） -->
<aside id="c-drawer" class="c-drawer bg-ink-800 backdrop-blur flex flex-col">
  <div class="h-12 shrink-0 flex items-center gap-2 px-4 border-b m-line">
    <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8" style="color:var(--m-mist)" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h9" stroke-linecap="round"/></svg>
    <span class="text-xs font-semibold shrink-0" style="color:var(--m-bone)">執行明細</span>
    <span id="c-exec-status-text" class="text-[11px] truncate" style="color:var(--m-faint)">待命就緒</span>
    <span class="flex-1"></span>
    <span id="c-exec-timer" class="font-mono text-[11px] px-2 py-0.5 rounded shrink-0"
          style="background:var(--m-mist-soft);color:var(--m-mist)">0.0s</span>
    <button type="button" onclick="cToggleDrawer(false)" class="w-7 h-7 shrink-0 rounded-lg m-btn-ghost grid place-items-center" aria-label="關閉執行明細">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke-linecap="round"/></svg>
    </button>
  </div>
  <div id="c-drawer-body" class="flex-1 overflow-y-auto m-scroll p-4 space-y-4">
    {result}
  </div>
</aside>

<div id="c-drawer-scrim" onclick="cToggleDrawer(false)"></div>
<div id="c-scrim" onclick="cToggleSidebar(false)"></div>
{drawers}
<div id="c-toast-host" aria-live="polite" aria-atomic="false"></div>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant" class="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K.H.A.V.I.S. · 任務工作台 (Task Stream)</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{ extend: {{
        colors: {{
          ink: {{ 900:'#16181D', 800:'#1C1E25', 700:'#23262F', 600:'#2B2F3A' }}
        }},
        fontFamily: {{
          sans: ['Inter', 'Noto Sans TC', 'sans-serif'],
          mono: ['JetBrains Mono', 'monospace']
        }}
      }} }}
    }};
  </script>

  <style>
{_legacy_style()}
{_MORANDI_CSS}
  </style>
</head>
{body}

  <script>
{_WORKBENCH_CLIENT_JS}
  </script>
{_LEGACY_CAPTURE_JS}
{_C_EXTRA_JS}
</body>
</html>
"""