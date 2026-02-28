# 🏪 SmartCater Streamlit 前端專案 - 交接說明文件

## 1. 專案概觀

**SmartCater Streamlit** 是一個為「智慧販賣機系統」打造的後台管理介面，完全基於 Python 的 [Streamlit](https://streamlit.io/) 框架開發。它提供給系統管理員、營運人員和一般使用者一個直覺的 UI，用來控管機台狀態、商品庫存、菜單、銷售數據及 AI 推薦功能。

本專案與後端 API 服務 (`SmartCaterBackend`) 高度整合，主要負責資料的視覺化呈現和使用者操作面板。

---

## 2. 專案架構與核心模組

專案採用模組化的單頁應用 (Single Page Application) 結構，主要目錄與檔案說明如下：

### 📁 根目錄重要檔案
- **[main.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py)**: 應用的進入點。負責初始化設定、檢查連線狀態、處理使用者登入/登出，以及管理側邊欄 (Sidebar) 導覽選單的路由派發。
- **[config.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/config.py) & [settings.toml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/settings.toml) / [.secrets.toml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/.secrets.toml)**: 專案設定檔中心。使用 `Dynaconf` 進行管理，支援多環境（`default`, `development`, `production`）切換。
- **[Dockerfile](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/Dockerfile) & `docker-compose.*.yml`**: Docker 容器化配置，包含本地開發測試與生產環境的部署設定。
- **`nginx/`**: Nginx 反向代理設定，主要用於本地測試與部署時的請求轉發與靜態資源處理。
- **`docs/`**: 存放了各項功能的詳細規格與討論紀錄（如 API 整合、機台狀態邏輯、AI 推薦功能開發等），**強烈建議後續接手者詳閱此目錄**。

### 📁 核心目錄
#### `modules/` (頁面功能模組)
每個 [.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py) 檔案對應側邊欄的一個功能頁面：
1. **[dashboard.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/dashboard.py)**: 營運儀表板，提供核心數據概覽。
2. **[machine_status.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/machine_status.py)**: 機台狀態監控（線上/離線/故障、冰箱溫度警告等），支援即時遠端操作。
3. **[inventory_management.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/inventory_management.py)**: 機台庫存管理與補貨追蹤。
4. **[menu_management.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/menu_management.py)**: 菜單管理（支援商品上下架、營養標籤等）。
5. **[sales_analytics.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/sales_analytics.py)**: 銷售數據圖表分析（整合 Plotly 呈現）。
6. **[ai_recommendations.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/ai_recommendations.py)**: AI 智能推薦系統的後台操作面板與審核流程。
7. **[location_management.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/location_management.py)**: 販賣機配置地點的 CRUD 操作管理。
8. **[order_management.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/order_management.py)**: 訂單查詢與上傳管理。
9. **[recipe_settings.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/recipe_settings.py)**: 產品配方或加熱參數的設定介面。

#### [utils.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils.py) & `utils/` (共用工具)
- **`utils.py: VendingMachineAPI 類別`**: 這是最核心的 API 溝通層。所有頁面向後端拉取或更新資料時，皆透過這個 Wrapper 類別發送 HTTP/HTTPS 請求。
- **[logger_config.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/logger_config.py)**: 系統日誌記錄器設定（包含 [api](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py#604-625), [auth](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils.py#307-313), `ui`, `system` 等不同維度），並處理了 WebSockets 的無害錯誤過濾。
- **[permissions.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py)**: 定義了三層權限系統 ([super_admin](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#80-83), [admin](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#80-83), [user](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#91-94))，控制不同角色在 UI 上能看到與操作的功能。
- **[idle_logout.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/idle_logout.py) & [ai_notification.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/ai_notification.py)**: 分別負責「30分鐘閒置自動登出」機制與「右上方/側邊欄 AI 推播通知」組件。

---

## 3. 專案如何運作

### 3.1 啟動流程
1. 執行 `streamlit run main.py`。
2. [config.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/config.py) 會根據系統環境變數 (`ENV_FOR_DYNACONF`) 讀取 [settings.toml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/settings.toml) 載入對應環境的 API 網址與資料庫預設參數。
3. 進入 [main.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py) 的 [main()](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py#407-602) 函式，讀取 session_state 判斷登入狀態。
4. 若未登入，顯示登入/註冊畫面。透過 `VendingMachineAPI.login` 向後端取得 JWT Token。
5. 登入成功後，依據 [utils.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils.py) 解析出的 `user_info.role` 角色層級，動態載入側邊欄允許的選單按鈕。
6. 使用者點擊側邊欄按鈕改變 `st.session_state.current_page`，藉由 `if-elif` 載入 `modules/` 底下對應的頁面函式 (如 `dashboard_page()`)。

### 3.2 資料流限制與快取 (State Management)
- **Session State**: Streamlit 是基於 Python 腳本由上到下反覆執行的機制。專案重度依賴 `st.session_state` 來保留 JWT token (`st.session_state.token`)、使用者資訊、目前頁面，以及各種快取資料（避免頻繁呼叫 API）。
- **API 通訊**: 所有需要資料的地方皆會呼叫 `st.session_state.api.[method_name]`（實例化於登入時）。如遇到網路無法連線，系統會嘗試進入**離線模式**（部分展示讀取預設/假測試資料）。

---

## 4. 如何執行與部署專案

### 4.1 本地開發環境 (Local Development)

#### 環境需求：
- Python >= 3.12 (建議使用虛擬環境 `venv` 或 `uv`)
- Docker & Docker Compose (若要與 Nginx 一同測試)

#### 啟動步驟：
1. **安裝套件**：
   ```bash
   pip install -r requirements.txt
   ```
2. **設定環境變數**：
   複製設定檔並根據實際 API 位置填寫：
   ```bash
   cp settings.toml.example settings.toml  # 若有
   cp env.production.example .env.production
   ```
3. **單純執行 Streamlit**：
   ```bash
   export ENV_FOR_DYNACONF=development
   streamlit run main.py
   ```
   網頁預設會在 `http://localhost:8501` 開啟。

4. **使用 Docker 本地測試**：
   專案提供了 [docker-compose.local.yml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/docker-compose.local.yml)，會將 Streamlit 與 Nginx 反向代理一同啟動。
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```
   網頁將可透過 `http://localhost:8501` (Nginx代理) 存取。

### 4.2 生產環境部署 (Production Deployment)

專案預設佈署於 **GCP Cloud Run** 或其他支援 Docker 的容器服務中。
- **GCP Cloud Build**: 參考 [cloudbuild.prod.yaml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/cloudbuild.prod.yaml)，使用 CI/CD 將映像檔推送到 Artifact Registry。
- **Cloud Run 直接佈署腳本**: 參見 [deploy.sh](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/deploy.sh)，該腳本包裝了 `docker build`、`docker push` 與 `gcloud run deploy` 流程。
   ```bash
   # 請先設定環境變數，或編輯腳本
   export PROJECT_ID="your-project-id"
   ./deploy.sh
   ```

> **資安提醒**: [.secrets.toml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/.secrets.toml) 與環境變數檔案 (例如 API金鑰、DB密碼) **絕不能** 提交進 Git 版本庫。請確認生產環境的 Secret Manager 是否設定正確。

---

## 5. 功能亮點與特色介紹

1. **AI 智能推薦系統整合 ([ai_recommendations.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/ai_recommendations.py), [ai_notification.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/ai_notification.py))**：
   與後端 AI 模型對接，可預測熱銷產品並提出「菜單配置建議」或「補貨建議」。提供通知小工具推播給管理員，並有完整的「待審核 ➔ 審核通過 ➔ 自動推播生效」的流程卡片與列表。
2. **多維度機台監控 ([machine_status.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/modules/machine_status.py))**：
   - 即時連線狀態判定（最後心跳時間）。
   - **冰箱溫度數據歷史圖表**：使用 Plotly 呈現溫度曲線。可以動態修改機台冷藏/冷凍溫度區間警告值。
3. **完善的權限系統 ([permissions.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py))**：
   利用 [super_admin](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#80-83), [admin](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#80-83), [user](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/utils/permissions.py#91-94) 級別區分。一般 User 只能瀏覽報表或操作有限功能；Admin 可執行商品與訂單異動；僅 Super Admin 可看見 `使用者管理` 並管理帳號。
4. **離線模式退路設計**：
   在開發或後端斷線時，介面會主動提示並試著切換到離線測試資料，不會讓整個系統卡死。
5. **增強的安全性 ([idle_logout.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/idle_logout.py))**：
   背景執行 JavaScript 及 Python 端時間戳比對的閒置檢測。若滑鼠/鍵盤 30 分鐘無動作，系統將會彈出警告並強制清除 session token 退回登入畫面。

---

## 6. 後續維護建議與待辦事項 (TODO)

1. **依賴管理**：目前使用 `pip` 與 [requirements.txt](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/requirements.txt)。專案內也有 [pyproject.toml](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/pyproject.toml) 與 [uv.lock](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/uv.lock)，建議後續團隊可徹底移行到 `uv` 管理工具以加快建置與依賴解析解析速度。
2. **Plotly 警告處理**：在 [main.py](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/main.py) 最下方目前有強制過濾 Plotly 的棄用警告（DeprecationWarning），未來若升級 Plotly 版本，可能需要根據官方新版 `config` 語法改寫圖表參數。
3. **效能優化**：Streamlit 的 UI 渲染特性在大量資料（如超大張銷售報表）時容易延遲。建議後續複雜報表可善用 `@st.cache_data` 等快取裝飾器優化使用者體驗。
4. **研讀舊文件**：在開發新功能或修改現有連線邏輯前，建議先查閱 `docs/` 內的設計討論（如 [TODO_refactor_remove_db_connection.md](file:///Users/reshinemac/JimmyWorks/P.Projects/smart_cater_frontend/smart-cater-streamlit/docs/TODO_refactor_remove_db_connection.md), `前端API說明-冰箱溫度數據.md` 等），可大幅減少踩坑機率。
