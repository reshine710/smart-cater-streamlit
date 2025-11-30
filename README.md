# 🏪 SmartCaterStreamlit - 智慧販賣機管理系統

基於 Streamlit 的智慧販賣機管理系統前端介面，提供完整的機台監控、菜單管理、銷售分析和 AI 推薦功能。

## ✨ 主要功能

### 🔐 使用者管理
- **雙重認證系統**：支援管理員和一般使用者角色
- **離線模式支援**：API 不可用時自動回退到離線模式
- **分頁查詢**：支援大量使用者的分頁顯示
- **使用者統計**：即時顯示使用者總數和分類統計

### 📍 地點管理 (新功能)
- **地點 CRUD 操作**：完整的地點創建、讀取、更新、刪除功能
- **室內外分類**：支援室內和室外環境分類
- **地點統計**：地點數量統計和分析
- **機台關聯**：機台創建時可選擇預設地點

### 🖥️ 機台監控
- **即時狀態監控**：機台線上/離線/維護狀態
- **MQTT 即時通訊**：支援即時命令發送和狀態更新
- **環境參數監控**：溫度、濕度等環境數據
- **遠端控制**：重啟、維護模式切換等操作

### 🍽️ 菜單管理 (增強功能)
- **營養資訊管理**：完整的營養成分記錄（熱量、蛋白質、碳水化合物、脂肪）
- **標籤系統**：支援靈活的標籤分類和管理
- **加熱參數配置**：微波、蒸氣等不同加熱方式設定
- **價格和狀態管理**：動態價格調整和商品上下架

### 📊 數據分析
- **銷售趨勢分析**：時間維度的銷售數據分析
- **商品銷量統計**：熱門商品排行和銷量分布
- **機台比較分析**：不同機台的營收和訂單比較
- **互動式圖表**：使用 Plotly 提供豐富的視覺化

### 🤖 AI 智能推薦
- **動態菜單推薦**：基於銷售數據的智能菜單配置
- **補貨建議**：庫存預測和補貨提醒
- **推薦審核流程**：管理員審核和批准機制
- **推播記錄追蹤**：推薦執行狀態和結果追蹤

## 🚀 快速開始

### 環境需求
- Python 3.12+
- Streamlit
- 相關依賴套件（見 requirements.txt）

### 安裝步驟

1. **克隆專案**
   ```bash
   git clone <repository-url>
   cd SmartCaterStreamlit
   ```

2. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置設定**
   ```bash
   # 複製並編輯配置文件
   cp settings.toml.example settings.toml
   # 編輯 API 端點和其他設定
   ```

4. **啟動應用**
   ```bash
   streamlit run main.py
   ```

### 預設帳號
- **管理員**：`testadmin` / `testpassword`
- **一般使用者**：`testuser` / `testpassword`

## 🏗️ 系統架構

### 核心模組
```
SmartCaterStreamlit/
├── main.py                 # 主程式和路由
├── utils.py                # API 客戶端和工具函數
├── logger_config.py        # 日誌配置
├── config.py               # 系統配置
├── modules/                # 頁面模組
│   ├── dashboard.py        # 儀表板
│   ├── machine_status.py   # 機台狀態
│   ├── menu_management.py  # 菜單管理
│   ├── location_management.py  # 地點管理 (新)
│   ├── sales_analytics.py  # 銷售分析
│   ├── recipe_settings.py  # 配方設定
│   └── ai_recommendations.py # AI 推薦
├── mqtt_client/            # MQTT 客戶端
└── tests/                  # 測試文件
```

### API 端點支援

#### 使用者管理
- `GET /api/v1/users/` - 獲取使用者列表（支援分頁）
- `GET /api/v1/users/count` - 獲取使用者總數
- `POST /api/v1/users/` - 創建使用者
- `POST /api/v1/users/token` - 使用者登入

#### 地點管理 (新)
- `GET /api/v1/locations/` - 獲取地點列表
- `POST /api/v1/locations/` - 創建地點
- `PUT /api/v1/locations/{id}` - 更新地點
- `DELETE /api/v1/locations/{id}` - 刪除地點

#### 機台管理
- `GET /api/v1/machines` - 獲取機台列表
- `POST /api/v1/machines` - 創建機台
- `PUT /api/v1/machines/{id}` - 更新機台
- `DELETE /api/v1/machines/{id}` - 刪除機台
- `POST /api/v1/machines/{id}/status` - 更新機台狀態
- `POST /api/v1/machines/{id}/heartbeat` - 記錄心跳

#### 菜單管理
- `GET /api/v1/menu-items/` - 獲取菜單項目
- `POST /api/v1/menu-items/` - 創建菜單項目（支援營養資訊）
- `PUT /api/v1/menu-items/{id}` - 更新菜單項目
- `DELETE /api/v1/menu-items/{id}` - 刪除菜單項目
- `POST /api/v1/menu-items/{id}/activate` - 啟用項目
- `POST /api/v1/menu-items/{id}/deactivate` - 停用項目

#### AI 推薦
- `GET /api/v1/ai/health` - AI 系統健康檢查
- `GET /api/v1/ai/recommendations` - 獲取推薦列表
- `POST /api/v1/ai/recommendations` - 創建推薦
- `PATCH /api/v1/ai/recommendations/{id}` - 更新推薦狀態

## 🔧 配置說明

### API 配置
```python
# utils.py
API_BASE_URL = "http://127.0.0.1:8000/api/v1"
```

### MQTT 配置
```python
# mqtt_client/client.py
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
```

### 日誌配置
- 應用日誌：`logs/app_YYYY-MM-DD.log`
- 錯誤日誌：`logs/error_YYYY-MM-DD.log`
- 支援多種日誌級別：API、認證、MQTT、UI、系統

## 🧪 測試

### 運行測試
```bash
# 單元測試
python -m pytest tests/

# MQTT 整合測試
python tests/test_mqtt_integration.py

# 新功能測試
python test_updated_features.py

# AI 推薦調試測試
python tests/test_ai_recommendations_debug.py
```

### API 測試
```bash
# 使用提供的測試腳本
chmod +x tmp/test_api.sh
./tmp/test_api.sh
```

## 📋 更新日誌

### v0.5.0 (最新)
- 📦 版本更新至 v0.5.0
- 持續優化系統穩定性和效能

### v0.3.2
- 📦 版本更新至 v0.3.2
- 持續優化系統穩定性和效能

### v0.2.0
- ✨ **新增地點管理功能**：完整的地點 CRUD 操作
- 🔧 **增強使用者管理**：支援分頁查詢和使用者統計
- 🍽️ **菜單營養資訊**：完整的營養成分管理
- 🏷️ **標籤系統優化**：支援靈活的標籤格式
- 📊 **離線模式增強**：更完整的離線數據支援
- 🐛 **錯誤處理改進**：更好的 API 錯誤處理和用戶提示

### v0.1.0
- 🎉 初始版本發布
- 基礎功能實現：使用者認證、機台監控、菜單管理
- MQTT 即時通訊支援
- AI 推薦系統整合

## 🤝 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

## 📞 聯絡資訊

- 專案維護者：[Your Name]
- Email: [your.email@example.com]
- 專案連結：[https://github.com/yourusername/SmartCaterStreamlit](https://github.com/yourusername/SmartCaterStreamlit)

## 🙏 致謝

感謝所有貢獻者和開源社群的支持！

---

**注意**：本系統需要配合後端 API 服務使用。請確保後端服務正常運行並且 API 端點配置正確。
