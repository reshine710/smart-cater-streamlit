# 🤖 AI 推薦欄位更新說明

## 更新日期：2025-10-03

## 📋 更新概述

根據 API 規格，在 AI 推薦的動態菜單配置中補齊了缺漏的欄位，確保與後端 API 的完整對接。

---

## ✨ 新增欄位

### 動態菜單推薦 (DYNAMIC_MENU)

在 `suggested_menu` 中的每個餐點項目新增以下欄位：

| 欄位名稱 | 類型 | 說明 | 範例 |
|---------|------|------|------|
| `restock_quantity` | `int` | 補貨數量 | `2`, `5`, `3` |
| `restock_date` | `string` | 補貨日期 (YYYY/MM/DD) | `"2025/11/05"` |

---

## 🎯 完整資料結構

### API 請求格式

```json
{
  "recommendation_id": "AI-REC-20250802-001",
  "ai_model_version": "v2.1.3-dynamic-menu",
  "target_machine_ids": ["1", "2"],
  "recommendation_type": "DYNAMIC_MENU",
  "valid_from": "2025-08-03T00:00:00Z",
  "valid_until": "2025-08-03T23:59:59Z",
  "payload": {
    "suggested_menu": [
      {
        "meal_id": "B",
        "suggested_price": 105.0,
        "priority": 1,
        "restock_quantity": 2,        // ← 新增
        "restock_date": "2025/11/05"  // ← 新增
      },
      {
        "meal_id": "C",
        "suggested_price": 60.0,
        "priority": 2,
        "restock_quantity": 5,        // ← 新增
        "restock_date": "2025/11/10"  // ← 新增
      },
      {
        "meal_id": "A",
        "suggested_price": 80.0,
        "priority": 3,
        "restock_quantity": 3,        // ← 新增
        "restock_date": "2025/11/15"  // ← 新增
      }
    ]
  },
  "notes": "根據近期陰雨天氣及B餐銷量上升趨勢，提高B餐優先級並微調價格。",
  "confidence_score": 0.85
}
```

---

## 🔧 Streamlit UI 更新

### 1. 創建推薦表單 (Tab: "➕ 創建推薦")

**更新前**：
```python
for i in range(3):
    col_meal, col_price, col_priority = st.columns(3)
    # 只有 meal_id, suggested_price, priority
```

**更新後**：
```python
for i in range(3):
    st.markdown(f"**餐點 {i+1}**")
    
    # 基本資訊
    col_meal, col_price, col_priority = st.columns(3)
    with col_meal:
        meal_id = st.text_input(f"餐點ID", ...)
    with col_price:
        price = st.number_input(f"建議價格", ...)
    with col_priority:
        priority = st.number_input(f"優先級", ...)
    
    # 補貨資訊 ← 新增
    col_quantity, col_date = st.columns(2)
    with col_quantity:
        restock_quantity = st.number_input(f"補貨數量", ...)
    with col_date:
        restock_date = st.date_input(f"補貨日期", ...)
```

**生成的資料**：
```python
{
    "meal_id": meal_id,
    "suggested_price": price,
    "priority": priority,
    "restock_quantity": restock_quantity,    # ← 新增
    "restock_date": restock_date.strftime("%Y/%m/%d")  # ← 新增
}
```

### 2. 動態菜單顯示 (Tab: "🎯 動態菜單")

**更新**：在餐點名稱下方顯示補貨資訊

```python
with item_col1:
    st.markdown(f"**🍽️ 餐點 {item['meal_id']}**")
    # 顯示補貨資訊（如果有）← 新增
    if 'restock_quantity' in item and 'restock_date' in item:
        st.caption(f"📦 補貨: {item['restock_quantity']} 份 @ {item['restock_date']}")
```

**顯示效果**：
```
🍽️ 餐點 B
📦 補貨: 2 份 @ 2025/11/05
```

### 3. 推薦列表詳細資訊 (Tab: "📋 推薦列表")

**更新**：在推薦內容表格中顯示完整欄位

```python
menu_df = pd.DataFrame(suggested_menu)
# 重新排列欄位順序
desired_columns = ['meal_id', 'suggested_price', 'priority', 
                  'restock_quantity', 'restock_date']  # ← 包含新欄位
existing_columns = [col for col in desired_columns if col in menu_df.columns]
if existing_columns:
    menu_df = menu_df[existing_columns]
st.dataframe(menu_df, width="stretch")
```

**表格顯示**：
| meal_id | suggested_price | priority | restock_quantity | restock_date |
|---------|----------------|----------|------------------|--------------|
| B | 105.0 | 1 | 2 | 2025/11/05 |
| C | 60.0 | 2 | 5 | 2025/11/10 |
| A | 80.0 | 3 | 3 | 2025/11/15 |

---

## 📝 使用說明

### 創建帶補貨資訊的推薦

1. 進入「🤖 AI智能推薦管理」頁面
2. 選擇「➕ 創建推薦」標籤
3. 填寫基本資訊：
   - 推薦ID
   - AI模型版本
   - 推薦類型：選擇 "DYNAMIC_MENU"
   - 目標機台
   - 有效期間
4. 配置餐點資訊（每個餐點）：
   - **餐點ID**：例如 A, B, C
   - **建議價格**：例如 80.0, 105.0
   - **優先級**：1-10（1最高優先）
   - **補貨數量** ← 新增：例如 2, 5, 3
   - **補貨日期** ← 新增：例如 2025/11/05
5. 點擊「🚀 創建推薦」

### 查看補貨資訊

1. **在推薦列表中**：
   - 展開任一推薦
   - 查看「📋 推薦內容」表格
   - 可看到完整的 `restock_quantity` 和 `restock_date` 欄位

2. **在動態菜單中**：
   - 選擇「🎯 動態菜單」標籤
   - 在餐點名稱下方會顯示補貨資訊
   - 格式：`📦 補貨: X 份 @ YYYY/MM/DD`

---

## 🔍 欄位說明

### restock_quantity（補貨數量）

- **用途**：建議的補貨數量
- **類型**：整數（int）
- **範圍**：0 或正整數
- **預設值**：3, 4, 5（依餐點順序遞增）
- **說明**：AI 根據銷售預測和庫存狀況建議的補貨數量

### restock_date（補貨日期）

- **用途**：建議的補貨日期
- **類型**：字串（string）
- **格式**：`YYYY/MM/DD`（例如：`2025/11/05`）
- **預設值**：當前日期 + 0/5/10 天（依餐點順序）
- **說明**：AI 建議的最佳補貨時間點，考慮銷售速度和庫存週期

---

## 🎨 UI 改進

### 表單佈局優化

```
餐點 1
┌─────────────┬─────────────┬─────────────┐
│  餐點ID     │  建議價格   │  優先級     │
└─────────────┴─────────────┴─────────────┘
┌─────────────────────┬───────────────────┐
│  補貨數量           │  補貨日期         │
└─────────────────────┴───────────────────┘
─────────────────────────────────────────

餐點 2
...
```

### 顯示增強

- ✅ 表格中顯示所有欄位
- ✅ 動態菜單中以小字體顯示補貨資訊
- ✅ 使用圖示（📦 📅）提升可讀性

---

## 🧪 測試範例

### cURL 測試命令

```bash
curl -X POST "$API_URL/ai/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "recommendation_id": "AI-REC-20250802-001",
    "ai_model_version": "v2.1.3-dynamic-menu",
    "target_machine_ids": ["1", "2"],
    "recommendation_type": "DYNAMIC_MENU",
    "valid_from": "2025-08-03T00:00:00Z",
    "valid_until": "2025-08-03T23:59:59Z",
    "payload": {
      "suggested_menu": [
        {
          "meal_id": "B",
          "suggested_price": 105.0,
          "priority": 1,
          "restock_quantity": 2,
          "restock_date": "2025/11/05"
        }
      ]
    },
    "notes": "測試補貨資訊欄位",
    "confidence_score": 0.85
  }'
```

---

## ✅ 驗證清單

- [x] 創建推薦表單包含補貨欄位
- [x] 表單生成的資料包含 `restock_quantity` 和 `restock_date`
- [x] 推薦列表表格顯示補貨資訊
- [x] 動態菜單顯示補貨資訊
- [x] 日期格式符合 API 規格 (YYYY/MM/DD)
- [x] 欄位順序合理
- [x] UI 佈局清晰美觀
- [x] 模組導入無錯誤
- [x] 無 linter 錯誤

---

## 📚 相關文件

- `modules/ai_recommendations.py` - AI 推薦管理模組
- API 文件 - 動態菜單推薦規格

---

**更新人員**: AI Assistant  
**測試狀態**: ✅ 通過  
**版本**: 1.0

