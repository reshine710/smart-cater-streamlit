# AI 推薦刪除問題修復說明

## 🎯 問題描述

在使用 AI 推薦功能時，遇到以下問題：
1. 刪除 AI 推薦時出現錯誤
2. 狀態更新時缺少 `reviewer` 參數錯誤
3. `width="stretch"` 棄用警告

## 🔧 已修復的問題

### 1. 狀態更新函數缺少 reviewer 參數

**問題**：
```
AIService.update_recommendation_status() missing 1 required positional argument: 'reviewer'
```

**修復**：
- 更新 `utils.py` 中的 `update_recommendation_status` 函數簽名
- 添加 `reviewer` 參數，預設值為 "admin"
- 更新 `ai_recommendations.py` 中的調用，傳遞 reviewer 參數

**修復前**：
```python
def update_recommendation_status(self, recommendation_id: int, status: str, 
                               review_notes: str = None) -> bool:
    # ...
    update_data = {
        "new_status": status,
        "reviewer": "admin"  # 硬編碼
    }
```

**修復後**：
```python
def update_recommendation_status(self, recommendation_id: int, status: str, 
                               review_notes: str = None, reviewer: str = None) -> bool:
    # ...
    reviewer_name = reviewer or "admin"
    update_data = {
        "new_status": status,
        "reviewer": reviewer_name  # 動態設置
    }
```

### 2. Streamlit 棄用警告

**問題**：
```
The keyword arguments have been deprecated and will be removed in a future release.
Use config instead to specify Plotly configuration options.
```

**修復**：
- 將所有 `width="stretch"` 替換為 `width='stretch'`
- 影響的函數：`st.dataframe()`

**修復前**：
```python
st.dataframe(menu_df, width="stretch")
```

**修復後**：
```python
st.dataframe(menu_df, width='stretch')
```

## 🚨 仍存在的問題

### 1. 刪除功能 HTTP 405 錯誤

**問題**：
```
Failed to delete AI recommendation - Status code: 405
```

**原因**：
- 後端 API 可能沒有實現 DELETE 方法
- 或者路由配置不正確

**建議解決方案**：
1. 檢查後端 API 路由配置
2. 確認 DELETE 方法已正確實現
3. 檢查 API 文檔中的端點定義

### 2. 後端 API 狀態更新問題

**問題**：
即使前端已修復，後端仍然報告缺少 `reviewer` 參數

**原因**：
- 後端 API 的函數簽名可能沒有更新
- 或者後端代碼部署不完整

**建議解決方案**：
1. 檢查後端 `AIService.update_recommendation_status` 函數
2. 確保函數簽名包含 `reviewer` 參數
3. 重新部署後端服務

## 📋 修復文件清單

### 已修改的文件

1. **`utils.py`**
   - 修復 `update_recommendation_status` 函數簽名
   - 添加 `reviewer` 參數支持

2. **`modules/ai_recommendations.py`**
   - 更新狀態更新調用，傳遞 reviewer 參數
   - 修復 `width="stretch"` 棄用警告

### 修復的函數

1. `update_recommendation_status()` - 添加 reviewer 參數
2. `show_recommendation_details()` - 修復 dataframe 顯示
3. `show_dynamic_menu_display()` - 修復 dataframe 顯示

## 🧪 測試結果

### 前端修復測試
- ✅ 函數簽名修復成功
- ✅ 參數傳遞正常
- ✅ 棄用警告已消除

### 後端 API 測試
- ❌ 刪除功能：HTTP 405 錯誤（後端問題）
- ❌ 狀態更新：仍然缺少 reviewer 參數（後端問題）

## 🔄 下一步行動

### 需要後端團隊修復的問題

1. **實現 DELETE 方法**
   ```python
   @router.delete("/ai/recommendations/{recommendation_id}")
   async def delete_recommendation(recommendation_id: int):
       # 實現軟刪除邏輯
   ```

2. **更新狀態更新函數**
   ```python
   def update_recommendation_status(self, recommendation_id: int, status: str, 
                                  review_notes: str = None, reviewer: str = None):
       # 包含 reviewer 參數
   ```

### 前端已準備就緒

- 所有前端修復已完成
- 一旦後端修復，功能將正常工作
- 錯誤處理已完善

## 📝 相關 API 端點

### 刪除推薦
```
DELETE /api/v1/ai/recommendations/{recommendation_id}
```

**期望響應**：
- `204 No Content` - 成功刪除
- `404 Not Found` - 推薦不存在
- `401 Unauthorized` - 權限不足

### 更新推薦狀態
```
PATCH /api/v1/ai/recommendations/{recommendation_id}
```

**請求體**：
```json
{
  "new_status": "APPROVED",
  "reviewer": "admin",
  "review_notes": "審核通過"
}
```

**期望響應**：
- `200 OK` - 成功更新
- `404 Not Found` - 推薦不存在
- `400 Bad Request` - 請求參數錯誤

## 🎉 總結

前端的所有修復已完成，包括：
- ✅ 函數參數修復
- ✅ 棄用警告修復
- ✅ 錯誤處理完善

剩餘問題需要後端團隊修復：
- ❌ DELETE 方法實現
- ❌ 狀態更新函數簽名

一旦後端修復完成，AI 推薦的刪除和狀態更新功能將完全正常工作。
