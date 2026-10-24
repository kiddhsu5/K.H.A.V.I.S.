# K.H.A.V.I.S. Manus 指令台

K.H.A.V.I.S. 工作台的 `/workbench` 現在包含一個同源 Manus 指令台。它只把任務文字、profile、task ID 與狀態傳到伺服器；Manus API Key 留在騰訊雲 systemd 的 EnvironmentFile，不會進入瀏覽器、HTML、JavaScript 或 URL。

## 首次配置

在可信任的本機終端執行：

```bash
cd /Users/kiddhsu/data/khavis
SSH_KEY=/Users/kiddhsu/data/.work/kiddhsu.pem ./scripts/configure_manus_api_key.sh
```

腳本會以隱藏輸入讀取兩個不同的值：Manus API Key 與 K.H.A.V.I.S. Console Token。前者只供後端呼叫 `https://api.manus.ai/v2`；後者只用於瀏覽器到 K.H.A.V.I.S. 的管理路由。腳本透過 mode `0600` 的暫存檔傳送設定，接著安裝 `/home/ubuntu/.config/khavis/manus.env`、systemd drop-in 並重啟 `khavis-workbench.service`。不要把任一值貼入 URL、Git、聊天訊息或 shell 命令列。

服務完成後開啟 `http://43.156.115.110/workbench`，在「雲端指令台」輸入 Console Token。Token 只存於目前瀏覽器分頁的 `sessionStorage`，關閉分頁即移除；它不是 Manus API Key。

## API 路由

所有 `/api/manus/*` 路由都要求 `X-KHAVIS-Console-Token`，且伺服器未配置 `KHAVIS_CONSOLE_TOKEN` 時會 fail closed：

| 路由 | 用途 |
| --- | --- |
| `GET /api/manus/status` | 回報 Console Token 驗證後的 API Key 配置狀態，不回傳 Key |
| `POST /api/manus/tasks` | 建立 private Manus task，body 為 `message`、可選 `agent_profile` 與 `interactive_mode` |
| `GET /api/manus/tasks/{task_id}` | 讀取 task 狀態與 metadata |
| `GET /api/manus/tasks/{task_id}/messages?limit=50` | 讀取事件訊息 |
| `POST /api/manus/tasks/{task_id}/messages` | 追加後續訊息，可選 `agent_profile` |

client 對 task ID、profile、訊息長度及上游 401/429/5xx 做驗證和安全錯誤轉換。上游錯誤不會把 Authorization、API Key 或完整請求內容回傳給瀏覽器。

## 邊界與後續

這一版是任務控制與狀態查詢介面，不開放任意 shell 執行，也不自動確認 Manus 等待中的高影響操作。K.H.A.V.I.S. 原有的多 Agent `/api/workbench/dispatch` 流程保持不變；Manus 可作為規劃、追問與長任務協調層，具體代碼派工仍由既有 Agent router 執行。
