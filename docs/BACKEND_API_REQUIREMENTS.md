# 🚀 後端API需求文件

## 📋 概述

本文檔列出了前端應用程式需要但後端尚未完全實現或需要優化的API端點。基於前端代碼分析，以下是按優先級分類的API需求。

---

## 🟢 已實現且正常運作的API

### 使用者認證與管理
- ✅ `POST /api/v1/users/token` - 使用者登入
- ✅ `POST /api/v1/users/` - 使用者註冊
- ✅ `GET /api/v1/users/me` - 獲取當前使用者資訊
- ✅ `GET /api/v1/users/` - 獲取使用者列表（分頁）
- ✅ `GET /api/v1/users/count` - 獲取使用者總數

### 機台管理
- ✅ `GET /api/v1/machines` - 獲取機台列表
- ✅ `GET /api/v1/machines/{id}` - 獲取機台詳情
- ✅ `POST /api/v1/machines` - 創建機台
- ✅ `PUT /api/v1/machines/{id}` - 更新機台
- ✅ `DELETE /api/v1/machines/{id}` - 刪除機台
- ✅ `POST /api/v1/machines/{id}/status` - 更新機台狀態
- ✅ `POST /api/v1/machines/{id}/heartbeat` - 機台心跳

### 地點管理
- ✅ `GET /api/v1/locations/` - 獲取地點列表
- ✅ `POST /api/v1/locations/` - 創建地點
- ✅ `PUT /api/v1/locations/{id}` - 更新地點
- ✅ `DELETE /api/v1/locations/{id}` - 刪除地點

### 菜單管理
- ✅ `GET /api/v1/menu-items` - 獲取菜單項目列表
- ✅ `GET /api/v1/menu-items/{id}` - 獲取菜單項目詳情
- ✅ `POST /api/v1/menu-items` - 創建菜單項目
- ✅ `PUT /api/v1/menu-items/{id}` - 更新菜單項目
- ✅ `DELETE /api/v1/menu-items/{id}` - 刪除菜單項目
- ✅ `POST /api/v1/menu-items/{id}/activate` - 啟用菜單項目
- ✅ `POST /api/v1/menu-items/{id}/deactivate` - 停用菜單項目
- ✅ `POST /api/v1/menu-items/{id}/tags` - 更新菜單項目標籤

### AI推薦系統
- ✅ `GET /api/v1/ai/health` - AI服務健康檢查
- ✅ `GET /api/v1/ai/recommendations` - 獲取推薦列表
- ✅ `POST /api/v1/ai/recommendations` - 創建推薦
- ✅ `GET /api/v1/ai/transactional-data` - 獲取交易數據

### 系統健康檢查
- ✅ `GET /health` - 系統健康檢查

---

## 🟡 需要優化或修復的API

### 1. ✅ AI推薦狀態更新 - 已正確實現
**端點**: `PATCH /api/v1/ai/recommendations/{id}`

**狀態**: ✅ 無需修正 - 後端已正確實現

**已實現功能**:
- ✅ 支援 `new_status` 參數（RecommendationStatusEnum）
- ✅ 支援 `reviewer` 參數（可選，會從AI key信息自動獲取）
- ✅ 支援 `review_notes` 參數（可選）
- ✅ 支援資料庫ID和backend_ref_id兩種識別方式
- ✅ 返回標準的StatusUpdateResponse格式

### 2. ✅ AI推薦刪除 - 已正確實現
**端點**: `DELETE /api/v1/ai/recommendations/{id}`

**狀態**: ✅ 無需修正 - 後端已正確實現

**已實現功能**:
- ✅ DELETE方法已正確實現
- ✅ 支援軟刪除（設置deleted_at欄位）
- ✅ 支援資料庫ID和backend_ref_id兩種識別方式
- ✅ 返回HTTP 204 No Content狀態碼

### 3. ✅ 訂單查詢API - 已正確實現
**端點**: `GET /api/v1/orders`

**狀態**: ✅ 無需修正 - 已支援所有需要的參數

**已實現功能**:
- ✅ 支援 `skip` 和 `limit` 分頁參數
- ✅ 支援 `machine_id` 篩選
- ✅ 支援 `status` 篩選
- ✅ 返回標準的PaginatedResponse格式

---

## 🔴 完全缺失的API

### 1. 🚨 銷售數據API - 高優先級
**端點**: `GET /api/v1/sales`

**狀態**: ❌ 完全缺失 - 急需實現

**問題**: Dashboard和Sales Analytics頁面的核心功能需要此API

**需要的參數**:
```json
{
  "start_date": "2025-01-01",    // 必需：開始日期
  "end_date": "2025-01-31",      // 必需：結束日期
  "machine_id": 1                // 可選：特定機台篩選
}
```

**期望回應格式**:
```json
{
  "data": [
    {
      "date": "2025-01-01",
      "machine_id": 1,
      "machine_name": "機台001",
      "total_revenue": 1500.0,
      "order_count": 15,
      "items": [
        {
          "meal_id": "A",
          "meal_name": "A餐",
          "quantity": 5,
          "revenue": 500.0,
          "avg_price": 100.0
        }
      ]
    }
  ],
  "summary": {
    "total_revenue": 45000.0,
    "total_orders": 450,
    "avg_order_value": 100.0,
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-01-31"
    }
  }
}
```

**前端使用場景**:
- 📊 Dashboard頁面：每日營收趨勢圖
- 📈 Sales Analytics頁面：銷售分析圖表
- 📋 銷售報表生成

**實現建議**:
- 從orders表聚合銷售數據
- 支援按日期、機台分組
- 計算營收、訂單數、平均訂單價值
- 提供數據摘要資訊

**詳細實現指南**:

1. **數據來源**:
   ```sql
   -- 建議的SQL查詢邏輯
   SELECT 
     DATE(order_time) as date,
     machine_id,
     COUNT(*) as order_count,
     SUM(total_amount) as total_revenue,
     AVG(total_amount) as avg_order_value
   FROM orders 
   WHERE order_time BETWEEN ? AND ?
     AND (machine_id = ? OR ? IS NULL)
   GROUP BY DATE(order_time), machine_id
   ORDER BY date DESC
   ```

2. **錯誤處理**:
   - 無效日期格式：返回400錯誤
   - 日期範圍過大：建議限制查詢範圍
   - 無數據：返回空陣列而非錯誤

3. **性能優化**:
   - 建議添加數據庫索引：`(order_time, machine_id)`
   - 考慮數據快取機制
   - 限制查詢時間範圍（如最多90天）

4. **前端整合測試**:
   ```bash
   # 測試命令
   curl -X GET "http://localhost:8000/api/v1/sales?start_date=2025-01-01&end_date=2025-01-31" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### 2. 配方設定管理
**需要實現的端點**:
```
GET /api/v1/recipes - 獲取配方列表
GET /api/v1/recipes/{id} - 獲取配方詳情
POST /api/v1/recipes - 創建配方
PUT /api/v1/recipes/{id} - 更新配方
DELETE /api/v1/recipes/{id} - 刪除配方
POST /api/v1/recipes/{id}/activate - 啟用配方
POST /api/v1/recipes/{id}/deactivate - 停用配方
```

**配方數據結構**:
```json
{
  "id": 1,
  "name": "微波加熱配方A",
  "description": "適用於A餐的微波加熱設定",
  "heating_type": "MICROWAVE",
  "temperature": 80,
  "duration": 120,
  "power_level": 80,
  "applicable_items": ["A", "B"],
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### 2. 庫存管理
**需要實現的端點**:
```
GET /api/v1/inventory - 獲取庫存列表
GET /api/v1/inventory/{machine_id} - 獲取特定機台庫存
PUT /api/v1/inventory/{machine_id}/{item_id} - 更新庫存數量
POST /api/v1/inventory/{machine_id}/restock - 批量補貨
GET /api/v1/inventory/low-stock - 獲取低庫存警報
```

### 3. 環境監控數據
**需要實現的端點**:
```
GET /api/v1/machines/{id}/environment - 獲取機台環境數據
POST /api/v1/machines/{id}/environment - 上傳環境數據
GET /api/v1/environment/alerts - 獲取環境警報
```

**環境數據結構**:
```json
{
  "machine_id": 1,
  "timestamp": "2025-01-01T12:00:00Z",
  "temperature": 25.5,
  "humidity": 60.0,
  "air_quality": "good",
  "power_consumption": 150.0
}
```

### 4. 報表生成
**需要實現的端點**:
```
GET /api/v1/reports/daily - 日報表
GET /api/v1/reports/weekly - 週報表
GET /api/v1/reports/monthly - 月報表
GET /api/v1/reports/custom - 自定義報表
```

### 5. 系統設定
**需要實現的端點**:
```
GET /api/v1/settings - 獲取系統設定
PUT /api/v1/settings - 更新系統設定
GET /api/v1/settings/notifications - 獲取通知設定
PUT /api/v1/settings/notifications - 更新通知設定
```

---

## 📊 API優先級建議

### 🔥 高優先級（立即需要）
1. **🚨 銷售數據API** - Dashboard和Sales Analytics頁面的核心功能，完全缺失
   - 影響範圍：Dashboard、Sales Analytics頁面無法正常工作
   - 業務影響：無法查看銷售趨勢和營收分析
   - 緊急程度：⭐⭐⭐⭐⭐

### 🟡 中優先級（近期需要）
1. **配方設定管理** - Recipe Settings頁面需要
   - 影響範圍：Recipe Settings頁面功能不完整
   - 業務影響：無法管理加熱配方設定
   - 緊急程度：⭐⭐⭐

2. **庫存管理** - 庫存監控功能需要
   - 影響範圍：庫存監控和補貨提醒
   - 業務影響：無法有效管理庫存
   - 緊急程度：⭐⭐⭐

3. **環境監控數據** - 機台狀態監控需要
   - 影響範圍：機台環境參數監控
   - 業務影響：無法監控機台環境狀態
   - 緊急程度：⭐⭐

### 🟢 低優先級（長期規劃）
1. **報表生成** - 進階分析功能
   - 影響範圍：進階報表功能
   - 業務影響：缺少詳細報表分析
   - 緊急程度：⭐

2. **系統設定** - 管理員配置功能
   - 影響範圍：系統配置管理
   - 業務影響：缺少系統級設定
   - 緊急程度：⭐

### ✅ 已完成（無需處理）
1. **AI推薦狀態更新** - 已正確實現
2. **AI推薦刪除** - 已正確實現  
3. **訂單查詢API** - 已正確實現，支援所有需要的參數

---

## 🔧 技術建議

### 1. 錯誤處理標準化
所有API應該返回一致的錯誤格式：
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "start_date",
      "reason": "Date format must be YYYY-MM-DD"
    }
  }
}
```

### 2. 分頁標準化
所有列表API應該支援統一的分頁格式：
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "skip": 0,
    "limit": 20,
    "has_next": true,
    "has_prev": false
  }
}
```

### 3. 認證和授權
- 確保所有需要認證的端點正確驗證JWT token
- 實現基於角色的權限控制（管理員vs一般使用者）
- 提供清晰的401/403錯誤回應

### 4. API文檔
建議使用OpenAPI/Swagger規範生成API文檔，包含：
- 端點描述
- 請求/回應格式
- 錯誤碼說明
- 認證要求

---

## 🧪 測試建議

### 1. 單元測試
為每個API端點編寫單元測試，覆蓋：
- 正常情況
- 邊界條件
- 錯誤處理

### 2. 整合測試
使用前端測試腳本驗證API整合：
- 認證流程
- 數據一致性
- 錯誤處理

### 3. 性能測試
測試API在高負載下的表現：
- 響應時間
- 並發處理能力
- 數據庫查詢優化

---

## 📋 更新摘要

### ✅ 已確認完成的API（2025-10-05）
1. **AI推薦狀態更新** - 完全正常，支援所有參數
2. **AI推薦刪除** - 完全正常，支援軟刪除
3. **訂單查詢API** - 完全正常，支援分頁和篩選

### 🚨 仍需實現的API
1. **銷售數據API** - 完全缺失，**最高優先級**
   - 影響Dashboard和Sales Analytics頁面
   - 提供詳細實現指南和測試命令

### 📊 狀態統計
- ✅ 已實現且正常：15個API端點
- ✅ 已修復完成：3個API端點  
- ❌ 完全缺失：5個API端點
- 🚨 急需實現：1個API端點（銷售數據API）

---

## 📞 聯繫方式

如有任何API實現問題或需要澄清需求，請聯繫前端開發團隊。

**最後更新**: 2025-10-05（根據後端回饋更新）  
**版本**: 1.1
