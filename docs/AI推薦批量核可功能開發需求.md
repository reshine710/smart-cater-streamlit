# 🤖 AI推薦批量核可功能開發需求

## 📋 需求概述

前端需要實現AI推薦列表的批量核可功能，讓管理員可以：
1. 查看完整的菜單名稱（而不只是meal_id）
2. 勾選需要核可的菜單項目
3. 批量核可選中的菜單項目
4. 將核可的菜單項目顯示在動態菜單中

## 🎯 功能需求

### 1. 推薦內容顯示優化
- **現狀**：推薦內容只顯示 `meal_id`、`suggested_price`、`priority` 等技術字段
- **需求**：顯示完整的菜單名稱和詳細資訊，提升用戶體驗

### 2. 批量核可機制
- **現狀**：只能單個推薦進行狀態更新
- **需求**：支援批量選擇和核可多個菜單項目

### 3. 動態菜單整合
- **現狀**：動態菜單功能已存在但需要優化
- **需求**：核可後的菜單項目能正確顯示在動態菜單中

## 🔧 後端API開發需求

### 1. 新增API端點

#### 1.1 獲取推薦菜單項目詳細資訊
```http
GET /api/v1/ai/recommendations/{recommendation_id}/menu-items
```

**功能**：獲取推薦中包含的菜單項目的完整詳細資訊

**請求參數**：
- `recommendation_id` (path): 推薦ID

**回應格式**：
```json
{
  "recommendation_id": "AI-REC-20251004-001",
  "menu_items": [
    {
      "meal_id": 1,
      "meal_name": "經典牛肉麵",
      "meal_description": "香濃牛肉湯底配手工拉麵",
      "category": "麵食",
      "suggested_price": 120,
      "priority": 1,
      "restock_quantity": 10,
      "restock_date": "2025-10-06",
      "current_stock": 5,
      "is_available": true
    },
    {
      "meal_id": 3,
      "meal_name": "招牌滷肉飯",
      "meal_description": "傳統台式滷肉配香Q白飯",
      "category": "米飯",
      "suggested_price": 80,
      "priority": 2,
      "restock_quantity": 15,
      "restock_date": "2025-10-06",
      "current_stock": 8,
      "is_available": true
    }
  ]
}
```

#### 1.2 批量核可推薦菜單項目
```http
POST /api/v1/ai/recommendations/{recommendation_id}/approve-menu-items
```

**功能**：批量核可推薦中的特定菜單項目

**請求體**：
```json
{
  "approved_meal_ids": [1, 3, 5],
  "approval_notes": "核可這些熱門商品，預期銷量良好",
  "approver_id": 1
}
```

**回應格式**：
```json
{
  "success": true,
  "message": "成功核可 3 個菜單項目",
  "approved_items": [
    {
      "meal_id": 1,
      "meal_name": "經典牛肉麵",
      "status": "approved",
      "approved_at": "2025-10-05T16:00:00Z"
    },
    {
      "meal_id": 3,
      "meal_name": "招牌滷肉飯", 
      "status": "approved",
      "approved_at": "2025-10-05T16:00:00Z"
    },
    {
      "meal_id": 5,
      "meal_name": "日式咖哩飯",
      "status": "approved", 
      "approved_at": "2025-10-05T16:00:00Z"
    }
  ],
  "updated_recommendation": {
    "id": "AI-REC-20251004-001",
    "status": "PARTIALLY_APPROVED",
    "updated_at": "2025-10-05T16:00:00Z"
  }
}
```

#### 1.3 獲取已核可的動態菜單項目
```http
GET /api/v1/ai/dynamic-menu/approved-items
```

**功能**：獲取所有已核可的動態菜單項目，用於顯示在動態菜單中

**請求參數**：
- `machine_id` (optional): 機台ID，用於篩選特定機台的菜單
- `status` (optional): 狀態篩選 (approved, implemented, active)

**回應格式**：
```json
{
  "approved_items": [
    {
      "recommendation_id": "AI-REC-20251004-001",
      "meal_id": 1,
      "meal_name": "經典牛肉麵",
      "meal_description": "香濃牛肉湯底配手工拉麵",
      "suggested_price": 120,
      "priority": 1,
      "approved_at": "2025-10-05T16:00:00Z",
      "approver": "test_admin",
      "target_machines": ["VM001", "VM002"],
      "status": "approved",
      "menu_item": {
        "id": 1,
        "name": "經典牛肉麵",
        "description": "香濃牛肉湯底配手工拉麵",
        "price": 120,
        "category": "麵食",
        "image_url": "/images/beef_noodle.jpg",
        "is_available": true
      }
    }
  ],
  "total_count": 5,
  "last_updated": "2025-10-05T16:00:00Z"
}
```

### 2. 修改現有API端點

#### 2.1 更新推薦狀態API
```http
PATCH /api/v1/ai/recommendations/{id}
```

**新增支援**：
- `approval_type`: 核可類型 ("full" | "partial" | "reject")
- `approved_meal_ids`: 部分核可時指定的菜單項目ID列表

**請求體範例**：
```json
{
  "new_status": "APPROVED",
  "approval_type": "partial",
  "approved_meal_ids": [1, 3, 5],
  "review_notes": "核可部分熱門商品",
  "reviewer": "test_admin"
}
```

## 📊 資料庫結構需求

### 1. 新增資料表

#### 1.1 AI推薦菜單項目表
```sql
CREATE TABLE ai_recommendation_menu_items (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(100) NOT NULL,
    meal_id INTEGER NOT NULL,
    meal_name VARCHAR(255) NOT NULL,
    meal_description TEXT,
    category VARCHAR(100),
    suggested_price DECIMAL(10,2) NOT NULL,
    priority INTEGER DEFAULT 1,
    restock_quantity INTEGER DEFAULT 0,
    restock_date DATE,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,
    approver_id INTEGER,
    approval_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recommendation_id) REFERENCES ai_recommendations(recommendation_id),
    FOREIGN KEY (meal_id) REFERENCES menu_items(id),
    FOREIGN KEY (approver_id) REFERENCES users(id)
);

CREATE INDEX idx_ai_rec_menu_items_rec_id ON ai_recommendation_menu_items(recommendation_id);
CREATE INDEX idx_ai_rec_menu_items_meal_id ON ai_recommendation_menu_items(meal_id);
CREATE INDEX idx_ai_rec_menu_items_approved ON ai_recommendation_menu_items(is_approved);
```

#### 1.2 動態菜單項目表
```sql
CREATE TABLE dynamic_menu_items (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(100) NOT NULL,
    menu_item_id INTEGER NOT NULL,
    machine_id INTEGER NOT NULL,
    suggested_price DECIMAL(10,2) NOT NULL,
    priority INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'approved', -- approved, implemented, active, expired
    approved_at TIMESTAMP NOT NULL,
    implemented_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recommendation_id) REFERENCES ai_recommendations(recommendation_id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    
    UNIQUE(recommendation_id, menu_item_id, machine_id)
);

CREATE INDEX idx_dynamic_menu_items_machine ON dynamic_menu_items(machine_id);
CREATE INDEX idx_dynamic_menu_items_status ON dynamic_menu_items(status);
CREATE INDEX idx_dynamic_menu_items_expires ON dynamic_menu_items(expires_at);
```

### 2. 修改現有資料表

#### 2.1 AI推薦表新增欄位
```sql
ALTER TABLE ai_recommendations 
ADD COLUMN approval_type VARCHAR(20) DEFAULT 'full', -- full, partial, reject
ADD COLUMN partial_approval_count INTEGER DEFAULT 0,
ADD COLUMN total_menu_items INTEGER DEFAULT 0;
```

## 🔄 業務邏輯需求

### 1. 推薦處理流程
1. **AI生成推薦** → 儲存到 `ai_recommendations` 和 `ai_recommendation_menu_items`
2. **管理員審核** → 可選擇全部核可或部分核可
3. **批量核可** → 更新 `ai_recommendation_menu_items.is_approved = TRUE`
4. **動態菜單更新** → 將核可項目插入 `dynamic_menu_items`
5. **狀態同步** → 更新 `ai_recommendations.status` 和相關計數

### 2. 狀態管理
- **PENDING**: 待審核
- **PARTIALLY_APPROVED**: 部分核可
- **APPROVED**: 全部核可
- **IMPLEMENTED**: 已實施到機台
- **REJECTED**: 已拒絕
- **EXPIRED**: 已過期

### 3. 權限控制
- 只有管理員可以進行批量核可操作
- 記錄核可人員和核可時間
- 支援核可備註

## 🧪 測試需求

### 1. API測試用例

#### 1.1 獲取推薦菜單項目詳細資訊
```bash
# 測試正常情況
curl -X GET "http://localhost:8000/api/v1/ai/recommendations/AI-REC-20251004-001/menu-items" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 測試不存在的推薦
curl -X GET "http://localhost:8000/api/v1/ai/recommendations/NONEXISTENT/menu-items" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 1.2 批量核可測試
```bash
# 測試正常批量核可
curl -X POST "http://localhost:8000/api/v1/ai/recommendations/AI-REC-20251004-001/approve-menu-items" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved_meal_ids": [1, 3, 5],
    "approval_notes": "核可熱門商品",
    "approver_id": 1
  }'

# 測試空列表
curl -X POST "http://localhost:8000/api/v1/ai/recommendations/AI-REC-20251004-001/approve-menu-items" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved_meal_ids": [],
    "approval_notes": "拒絕所有項目",
    "approver_id": 1
  }'
```

#### 1.3 獲取已核可項目測試
```bash
# 測試獲取所有已核可項目
curl -X GET "http://localhost:8000/api/v1/ai/dynamic-menu/approved-items" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 測試按機台篩選
curl -X GET "http://localhost:8000/api/v1/ai/dynamic-menu/approved-items?machine_id=1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 測試按狀態篩選
curl -X GET "http://localhost:8000/api/v1/ai/dynamic-menu/approved-items?status=approved" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. 資料庫測試
- 測試推薦菜單項目的CRUD操作
- 測試批量核可的資料一致性
- 測試動態菜單項目的狀態更新
- 測試索引效能

## 📈 效能考量

### 1. 資料庫優化
- 為 `recommendation_id`、`meal_id`、`machine_id` 建立索引
- 使用適當的資料類型減少儲存空間
- 考慮資料分區策略（按時間或機台）

### 2. API效能
- 實作適當的緩存策略
- 使用分頁處理大量資料
- 實作請求速率限制

### 3. 併發處理
- 使用資料庫事務確保資料一致性
- 實作樂觀鎖定避免併發衝突
- 考慮使用訊息佇列處理大量批量操作

## 🔒 安全性需求

### 1. 身份驗證
- 所有API都需要JWT token驗證
- 驗證用戶是否有管理員權限

### 2. 資料驗證
- 驗證 `approved_meal_ids` 是否屬於該推薦
- 驗證 `approver_id` 是否為有效的管理員
- 防止SQL注入和XSS攻擊

### 3. 審計日誌
- 記錄所有核可操作
- 記錄操作人員和時間
- 支援操作歷史查詢

## 📋 實作優先級

### 高優先級 (Phase 1)
1. ✅ 新增 `ai_recommendation_menu_items` 資料表
2. ✅ 實作獲取推薦菜單項目詳細資訊API
3. ✅ 實作批量核可API
4. ✅ 修改推薦狀態更新API支援部分核可

### 中優先級 (Phase 2)
1. ✅ 新增 `dynamic_menu_items` 資料表
2. ✅ 實作獲取已核可動態菜單項目API
3. ✅ 實作動態菜單狀態管理

### 低優先級 (Phase 3)
1. ✅ 效能優化和索引建立
2. ✅ 審計日誌功能
3. ✅ 進階篩選和搜尋功能

## 📞 聯絡資訊

如有任何問題或需要澄清的需求，請聯繫前端開發團隊。

---

**文件版本**: 1.0  
**建立日期**: 2025-10-05  
**最後更新**: 2025-10-05  
**狀態**: 📝 待實作
