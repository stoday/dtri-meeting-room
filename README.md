# P2026 Meeting Room

以命令列查詢及預約 III 內部會議室的工具。使用 Playwright 的專案獨立瀏覽器設定檔完成一次人工登入後，後續操作可沿用該登入狀態，不須匯出或顯示 cookie、session、token 等憑證。

## 目前功能

| 指令 | 功能 | 狀態 |
| --- | --- | --- |
| `dtri-meeting-room login` | 開啟獨立瀏覽器，供人工登入並儲存當週會議室資料 | 可用 |
| `dtri-meeting-room view` | 讀取本機快照，顯示會議室的**可借時段** | 可用 |
| `dtri-meeting-room view --refresh` | 使用已登入的設定檔重新抓取當週資料 | 可用 |
| `dtri-meeting-room reserve <room> <日期> <時段>` | 查核可借時段、詢問會議事由並預約 | 可用 |
| `dtri-meeting-room cancel` | 列出並取消自己的預約 | 尚未實作 |

`view` 的時間區間是「可以借用」的時間，而不是已被預約的時間。例如 `10:00-20:00` 表示該會議室在這段時間可供預約。

## 安裝

在 PowerShell 中進入專案根目錄後：

```powershell
. .\.venv\Scripts\Activate.ps1
uv pip install --python .\.venv\Scripts\python.exe -e .
python -m playwright install chromium
```

## 第一次登入

```powershell
dtri-meeting-room login
```

程式會開啟 Playwright 管理的獨立 Chromium 視窗並前往內部網站。請在該視窗自行完成登入；當週表出現後，CLI 會自動儲存快照。之後可關閉瀏覽器。

登入狀態只保留在專案內的 `.dtri-meeting-room/profile/`，且已被 Git 忽略。它不是一般 Chrome 設定檔，也不會把 cookie、token 或密碼輸出到終端機、JSON 快照或文件。若要清除本機登入狀態，可手動刪除該確切資料夾。

## 查看會議室

```powershell
# 顯示目前本機快照的全部日期與會議室
dtri-meeting-room view

# 先向網站更新，再只顯示指定日期
dtri-meeting-room view --refresh --date 2026-09-11
```

快照儲存在 `data/current_week.json`，是抓取當下的資料；實際預約前，`reserve` 會再次向網站確認會議室與時段仍可借用。

## 預約會議室

日期與時段皆為必要參數：

```powershell
dtri-meeting-room reserve 1002 2026-09-11 10:00-10:30
```

流程如下：

1. 確認會議室編號存在，且日期位於目前週表範圍。
2. 確認指定區間完整落在該會議室的可借時段中。
3. 詢問會議事由；直接按 Enter 會使用預設值 `工作進度討論`。
4. 顯示預約摘要；只有輸入精確的大寫 `YES` 才會繼續。
5. 在同一個已登入瀏覽器環境中，依網站觀察到的順序執行規則檢核，再送出預約請求。

預約請求使用網站實際觀察到的 Ajax 流程：先載入 `default.aspx`，執行兩輪 Rule 1／Rule 2 檢核（含預約分鐘數），最後才送出 `SaveBorrow`。網站回傳含有 `Borrowed` 表格（包含 Ajax 跳脫引號格式）時，CLI 會顯示預約成功。

預約是實際寫入動作。沒有輸入 `YES` 不會送出任何預約；若規則檢核或最終回應不符合已知成功契約，CLI 不會自動重試，請先到網站確認結果。

## 重新觀察網站預約流程

若內部網站改版、預約失敗或需要重新擷取流程，可執行：

```powershell
dtri-meeting-room login --capture-reservation
```

登入後，在開啟的瀏覽器中手動完成一筆你確定要建立的預約，看到「預借成功」後按確認並關閉瀏覽器。程式會將去識別化的請求摘要寫入 `data/reservation-flow.private.json`，供程式使用目前的動態 `SaveBorrow` handler。

這份私有檔案與瀏覽器設定檔都由 `.gitignore` 排除；其中不會記錄 cookie、token、密碼、`__VIEWSTATE` 或 event validation。更完整的觀察內容請見 [docs/reservation-api-observation.md](docs/reservation-api-observation.md)。

## 限制與安全原則

- 週表是即時資料的快照，其他人可能在查詢與送出之間預約同一時段。
- `reserve` 不會猜測日期；必須使用 `YYYY-MM-DD`。
- 不會自動重試失敗的寫入請求，以免建立重複預約。
- `cancel` 的網站流程尚未完成觀察與實作，目前不可用。
