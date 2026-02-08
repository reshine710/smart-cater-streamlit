# 移除 Streamlit 前端資料庫直連 - 實施計劃

## 問題分析

### 為何前端專案需要連接資料庫？

在 `order_management.py` 中發現 **4 處**直接使用資料庫連接：

#### 1️⃣ **訂單批量上傳功能** (L311-372 `upload_orders_from_dataframe`)
- **位置**: L341 使用 `get_database_connection()`
- **原因**: 需要執行複雜的批量訂單插入操作，包含：
  - 根據 `machine_code` 查詢 `machine_id`
  - 根據 `product_code` 查詢 `menu_item_id` 和價格
  - 建立或查詢 `env_context`（環境情境）
  - 插入 `orders` 和 `order_items` 資料
  - 支援事務（transaction）確保資料一致性
- **使用的輔助函數**:
  - `get_machine_id_by_code(db, machine_code)` (L66-74)
  - `get_menu_item_id_by_product_code(db, product_code)` (L77-85)
  - `get_or_create_env_context(db, ...)` (L88-154)
  - `create_order_from_row(db, row)` (L157-308)

#### 2️⃣ **按日期範圍刪除訂單** (L1395-1454 `delete_orders_by_date_range`)
- **位置**: L1402 使用 `get_database_connection()`
- **原因**: 需要執行批量刪除操作，包含：
  - 查詢日期範圍內的所有訂單
  - 先刪除 `order_items`，再刪除 `orders`（外鍵依賴）
  - 支援事務以確保刪除完整性

#### 3️⃣ **按訂單編號刪除訂單** (L1457-1502 `delete_order_by_number`)
- **位置**: L1464 使用 `get_database_connection()`
- **原因**: 需要執行單筆訂單刪除，包含：
  - 根據 `order_number` 查詢訂單
  - 先刪除 `order_items`，再刪除 `orders`
  - 支援事務

### 架構問題

目前的架構為：
```
Streamlit 前端 ──┬──→ 後端 API ──→ 資料庫
                 └──→ 資料庫（直連）
```

這違反了「關注點分離」原則，導致：
- ❌ 資料庫憑證需要暴露給前端專案
- ❌ 業務邏輯分散在前後端
- ❌ 難以維護和測試
- ❌ 資料驗證邏輯可能重複
- ❌ 無法統一管理資料存取權限

---

## 解決方案

### 目標架構

```
Streamlit 前端 ──→ 後端 API ──→ 資料庫
```

將所有資料庫操作移至後端 API，前端只透過 API 存取資料。

---

## 需要的後端 API 端點

### 1️⃣ **批量訂單上傳 API**

```
POST /api/v1/orders/batch-upload
```

**請求體**（JSON 陣列）:
```json
[
  {
    "order_number": "ORD-2025-001",
    "machine_code": "VM001",
    "product_code": "A001",
    "purchase_timestamp": "2025-10-24 13:12:38",
    "unit_price": 100.0,
    "quantity": 1,
    "weather": "SUNNY",
    "temperature": 25.5,
    "humidity": 60.0,
    "payment_method": "cash",
    "payment_number": "PAY-001",
    "recommended_item": "A002"
  },
  ...
]
```

**回應體**:
```json
{
  "total": 100,
  "success": 95,
  "failed": 5,
  "errors": [
    {
      "row": 10,
      "order_number": "ORD-2025-010",
      "error": "找不到機台: VM999"
    },
    ...
  ]
}
```

**功能需求**:
- 支援批量插入（建議使用批次操作提升效能）
- 自動查詢 `machine_id`、`menu_item_id`
- 自動建立或查詢 `env_context`
- 事務支援（全部成功或全部回滾，或部分成功記錄錯誤）
- 錯誤處理並回報詳細錯誤訊息

---

### 2️⃣ **按日期範圍刪除訂單 API**

```
DELETE /api/v1/orders/by-date-range
```

**請求參數**:
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31"
}
```

**回應體**:
```json
{
  "total_found": 100,
  "deleted": 100,
  "remaining": 0
}
```

**功能需求**:
- 支援日期範圍查詢（含起始和結束日期）
- 先刪除 `order_items`，再刪除 `orders`
- 事務支援
- 回報刪除統計資訊

---

### 3️⃣ **按訂單編號刪除訂單 API**

```
DELETE /api/v1/orders/{order_number}
```

**路徑參數**:
- `order_number`: 訂單編號（字串）

**回應體**:
```json
{
  "success": true,
  "order_id": 123,
  "order_number": "ORD-2025-001",
  "message": "訂單已成功刪除"
}
```

**錯誤回應**（404）:
```json
{
  "success": false,
  "error": "找不到訂單編號: ORD-2025-999"
}
```

**功能需求**:
- 根據 `order_number` 查詢並刪除訂單
- 先刪除 `order_items`，再刪除 `orders`
- 事務支援
- 若訂單不存在則回傳 404

---

## 前端修改計劃

### 修改檔案

#### [MODIFY] [order_management.py](file:///Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit/modules/order_management.py)

**移除內容**:
- L43-63: `get_database_connection()` 函數
- L66-74: `get_machine_id_by_code()` 函數
- L77-85: `get_menu_item_id_by_product_code()` 函數
- L88-154: `get_or_create_env_context()` 函數
- L157-308: `create_order_from_row()` 函數（使用直接 SQL 插入）
- L1395-1454: `delete_orders_by_date_range()` 函數
- L1457-1502: `delete_order_by_number()` 函數
- L13-14: 移除 `sqlalchemy` 相關 import

**修改內容**:

1. **`upload_orders_from_dataframe()` 函數**（L311-372）
   - 移除資料庫連接邏輯
   - 將 DataFrame 轉換為 JSON 格式
   - 呼叫新的 API `POST /api/v1/orders/batch-upload`
   - 處理 API 回應並顯示結果

2. **`render_delete_by_date()` 函數**（L1505-1588）
   - 移除直接資料庫刪除邏輯
   - 改為呼叫 API `DELETE /api/v1/orders/by-date-range`
   - 處理 API 回應

3. **`render_delete_by_number()` 函數**（L1590-1640）
   - 移除直接資料庫刪除邏輯
   - 改為呼叫 API `DELETE /api/v1/orders/{order_number}`
   - 處理 API 回應

---

#### [MODIFY] [utils.py](file:///Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit/utils.py)

在 `VendingMachineAPI` 類別中新增三個方法：

```python
def batch_upload_orders(self, orders_data: List[Dict]) -> Dict:
    """批量上傳訂單"""
    
def delete_orders_by_date_range(self, start_date: str, end_date: str) -> Dict:
    """按日期範圍刪除訂單"""
    
def delete_order_by_number(self, order_number: str) -> Dict:
    """按訂單編號刪除訂單"""
```

---

#### [MODIFY] [.secrets.toml](file:///Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit/.secrets.toml)

可以**移除**資料庫密碼配置：
```toml
# 可以移除或註解掉
# [development]
#   POSTGRES_PASSWORD = "db362512"
# [production]
#   POSTGRES_PASSWORD = "SihaiPSQLdb2025"
```

---

#### [MODIFY] [settings.toml](file:///Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit/settings.toml)

可以**移除**資料庫連接配置：
```toml
# 可以移除或註解掉
# [development]
#   POSTGRES_USER = "postgres"
#   POSTGRES_DB = "smartcater"
#   DB_HOST = "localhost"
#   DB_PORT = 5432
# [production]
#   DB_HOST = "host.docker.internal"
#   DB_PORT = 5432
#   POSTGRES_USER = "smartcater_prod"
#   POSTGRES_DB = "smartcater_prod_db"
```

---

#### [MODIFY] [requirements.txt](file:///Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit/requirements.txt)

可以**移除** SQLAlchemy 相關套件（如果沒有其他地方使用）:
```
# 檢查並移除（需確認其他模組是否使用）
# sqlalchemy
# psycopg2-binary
```

---

## 驗證計劃

### 階段一：後端 API 開發與測試

> [!IMPORTANT]
> 這部分需要您在後端專案中實作

1. **實作三個新的 API 端點**
   - `POST /api/v1/orders/batch-upload`
   - `DELETE /api/v1/orders/by-date-range`
   - `DELETE /api/v1/orders/{order_number}`

2. **後端單元測試**
   - 測試批量上傳功能（正常情況）
   - 測試批量上傳錯誤處理（找不到機台、找不到產品等）
   - 測試日期範圍刪除
   - 測試訂單編號刪除
   - 測試事務回滾

3. **API 測試工具驗證**
   - 使用 Postman 或 curl 測試 API 端點
   - 驗證回應格式符合規格
   - 驗證錯誤處理

### 階段二：前端重構與測試

1. **修改前端程式碼**
   - 在 `utils.py` 新增 API 方法
   - 重構 `order_management.py` 移除資料庫直連
   - 移除 SQLAlchemy 相關 import 和配置

2. **功能測試**
   - **訂單上傳測試**:
     1. 準備測試用 Excel 檔案（正常資料）
     2. 在 Streamlit 介面上傳檔案
     3. 驗證上傳成功並顯示正確統計
     4. 檢查資料庫確認訂單已正確建立
   
   - **訂單上傳錯誤處理測試**:
     1. 準備包含錯誤資料的 Excel（如不存在的機台編號）
     2. 上傳並驗證錯誤訊息正確顯示
     3. 確認部分成功的資料已寫入，失敗的資料未寫入
   
   - **按日期刪除測試**:
     1. 選擇日期範圍
     2. 確認刪除前輸入 "DELETE" 驗證
     3. 執行刪除並驗證統計資訊
     4. 檢查資料庫確認訂單已刪除
   
   - **按編號刪除測試**:
     1. 輸入已存在的訂單編號
     2. 確認需重複輸入訂單編號驗證
     3. 執行刪除並驗證成功訊息
     4. 檢查資料庫確認訂單已刪除

3. **效能測試**（可選）
   - 測試批量上傳 1000 筆訂單的效能
   - 確認 API 回應時間可接受

### 階段三：環境配置驗證

1. **移除資料庫配置**
   - 註解或移除 `.secrets.toml` 中的資料庫密碼
   - 註解或移除 `settings.toml` 中的資料庫連接設定
   - 確認 Streamlit 啟動正常

2. **部署測試**
   - 在開發環境測試
   - 在正式環境（Docker）測試
   - 確認所有功能正常運作

---

## 實施優先順序

### 高優先級（核心功能）
1. ✅ 批量訂單上傳 API
2. ✅ 前端批量上傳改用 API

### 中優先級（管理功能）
3. ✅ 按訂單編號刪除 API
4. ✅ 前端單筆刪除改用 API

### 低優先級（批量操作）
5. ✅ 按日期範圍刪除 API
6. ✅ 前端批量刪除改用 API
7. ✅ 移除資料庫配置和相關套件

---

## 額外建議

### 安全性考量
- 在後端 API 加入權限驗證（僅管理員可執行）
- 批量刪除操作需要額外的安全確認
- 記錄所有刪除操作的日誌（誰、何時、刪除了什麼）

### 效能優化
- 批量上傳使用批次插入而非逐筆插入
- 考慮加入背景任務處理大量資料上傳
- 設定合理的單次操作上限（如單次最多上傳 5000 筆）

### 錯誤處理
- 提供詳細的錯誤訊息幫助除錯
- 前端顯示友善的錯誤提示
- API 使用標準的 HTTP 狀態碼

### 向後相容
- 如果其他地方還有使用資料庫直連，需要一併檢查
- 建議在移除資料庫套件前先確認全專案沒有其他使用處
