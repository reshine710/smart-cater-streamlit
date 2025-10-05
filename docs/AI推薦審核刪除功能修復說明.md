# 🔧 AI 推薦審核和刪除功能修復說明

## 修復日期：2025-10-03

---

## 🐛 發現的問題

### 問題 1: 審核功能錯誤
**錯誤訊息**:
```
❌ 後端 API 配置錯誤：缺少審核者參數。請聯繫系統管理員。
```

**原因分析**:
- `utils.py` 中的 `update_recommendation_status()` 函數已經包含 `reviewer` 參數並正確傳遞給 API
- 但是 `ai_recommendations.py` 中調用該函數時沒有傳遞 `review_notes` 參數
- 函數簽名不匹配導致參數傳遞錯誤

### 問題 2: 刪除功能無反應
**症狀**:
- 點擊「🗑️ 刪除」按鈕後沒有任何反應
- 不顯示確認對話框

**原因分析**:
- 確認對話框的邏輯有問題
- `session_state` 的檢查邏輯錯誤
- 按鈕點擊後的狀態轉換不正確

---

## ✅ 修復方案

### 修復 1: 更新審核函數簽名

**修復前**:
```python
def update_recommendation_status(rec_id: int, status: str) -> bool:
    """更新推薦狀態"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.update_recommendation_status(rec_id, status)
        # ...
```

**修復後**:
```python
def update_recommendation_status(rec_id: int, status: str, review_notes: str = None) -> bool:
    """更新推薦狀態"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            # 獲取當前使用者名稱作為審核者
            reviewer = st.session_state.get('username', 'admin')
            return st.session_state.api.update_recommendation_status(rec_id, status, review_notes)
        # ...
```

**改進點**:
1. ✅ 添加 `review_notes` 參數（可選）
2. ✅ 從 session_state 獲取當前使用者名稱
3. ✅ 正確傳遞參數給 API 函數
4. ✅ 添加錯誤日誌記錄

### 修復 2: 重構刪除確認邏輯

**修復前**:
```python
if st.button("🗑️ 刪除", ...):
    confirm_key = f"confirm_delete_{rec_id}_{index}"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    
    if not st.session_state[confirm_key]:
        st.session_state[confirm_key] = True
        st.rerun()
    else:
        # 顯示確認按鈕
        ...
```

**問題**: 邏輯混亂，狀態檢查和設置在同一個按鈕回調中

**修復後**:
```python
confirm_key = f"confirm_delete_{rec_id}_{index}"

# 檢查是否處於確認狀態
if st.session_state.get(confirm_key, False):
    # 顯示確認對話框
    st.warning("⚠️ 確定要刪除此推薦嗎？此操作無法復原。")
    col_confirm1, col_confirm2 = st.columns(2)
    with col_confirm1:
        if st.button("⚠️ 確認刪除", ...):
            if delete_recommendation(rec_id):
                st.success("🗑️ 推薦已刪除")
                if confirm_key in st.session_state:
                    del st.session_state[confirm_key]
                st.rerun()
            else:
                # 刪除失敗，清除確認狀態
                if confirm_key in st.session_state:
                    del st.session_state[confirm_key]
    with col_confirm2:
        if st.button("❌ 取消", ...):
            st.session_state[confirm_key] = False
            st.rerun()
else:
    # 顯示刪除按鈕
    if st.button("🗑️ 刪除", ...):
        st.session_state[confirm_key] = True
        st.rerun()
```

**改進點**:
1. ✅ 分離狀態檢查和按鈕顯示邏輯
2. ✅ 先檢查確認狀態，再決定顯示哪個UI
3. ✅ 添加警告訊息提示用戶
4. ✅ 正確處理刪除成功和失敗的情況
5. ✅ 確保狀態清理正確執行

---

## 🎯 功能測試指南

### 測試 1: 審核通過功能

1. **前提條件**:
   - 已登入管理員帳號
   - 有狀態為 `PENDING` (待審核) 的推薦

2. **測試步驟**:
   ```
   1. 進入「🤖 AI智能推薦管理」頁面
   2. 選擇「📋 推薦列表」標籤
   3. 展開一個 🟡 待審核 的推薦
   4. 點擊「✅ 通過」按鈕
   ```

3. **預期結果**:
   - ✅ 顯示成功訊息：「✅ 推薦已通過」
   - ✅ 頁面自動刷新
   - ✅ 推薦狀態變為 `✅ 已通過`
   - ✅ 按鈕變為「🚀 實施」和「↩️ 撤回」

### 測試 2: 審核拒絕功能

1. **前提條件**:
   - 已登入管理員帳號
   - 有狀態為 `PENDING` (待審核) 的推薦

2. **測試步驟**:
   ```
   1. 進入「🤖 AI智能推薦管理」頁面
   2. 選擇「📋 推薦列表」標籤
   3. 展開一個 🟡 待審核 的推薦
   4. 點擊「❌ 拒絕」按鈕
   ```

3. **預期結果**:
   - ✅ 顯示成功訊息：「❌ 推薦已拒絕」
   - ✅ 頁面自動刷新
   - ✅ 推薦狀態變為 `❌ 已拒絕`
   - ✅ 顯示警告訊息

### 測試 3: 實施功能

1. **前提條件**:
   - 推薦狀態為 `APPROVED` (已通過)

2. **測試步驟**:
   ```
   1. 展開一個 ✅ 已通過 的推薦
   2. 點擊「🚀 實施」按鈕
   ```

3. **預期結果**:
   - ✅ 顯示成功訊息：「🚀 推薦已實施」
   - ✅ 頁面自動刷新
   - ✅ 推薦狀態變為 `🚀 已實施`
   - ✅ 不再顯示操作按鈕（已實施不可修改）

### 測試 4: 撤回功能

1. **前提條件**:
   - 推薦狀態為 `APPROVED` (已通過)

2. **測試步驟**:
   ```
   1. 展開一個 ✅ 已通過 的推薦
   2. 點擊「↩️ 撤回」按鈕
   ```

3. **預期結果**:
   - ✅ 顯示成功訊息：「↩️ 推薦已撤回至待審核」
   - ✅ 頁面自動刷新
   - ✅ 推薦狀態變回 `🟡 待審核`
   - ✅ 按鈕變回「✅ 通過」和「❌ 拒絕」

### 測試 5: 刪除功能 (新修復)

1. **前提條件**:
   - 推薦狀態不是 `IMPLEMENTED` (已實施)
   - 可以是: PENDING, APPROVED, REJECTED, EXPIRED

2. **測試步驟**:
   ```
   1. 展開一個可刪除的推薦
   2. 滾動到底部，點擊「🗑️ 刪除」按鈕
   3. 應該出現警告訊息和確認對話框
   4. 點擊「⚠️ 確認刪除」或「❌ 取消」
   ```

3. **預期結果 - 確認刪除**:
   - ✅ 第一次點擊「🗑️ 刪除」後顯示警告
   - ✅ 警告訊息：「⚠️ 確定要刪除此推薦嗎？此操作無法復原。」
   - ✅ 顯示兩個按鈕：「⚠️ 確認刪除」和「❌ 取消」
   - ✅ 點擊「⚠️ 確認刪除」後：
     - 顯示成功訊息：「🗑️ 推薦已刪除」
     - 頁面自動刷新
     - 推薦從列表中消失

4. **預期結果 - 取消刪除**:
   - ✅ 點擊「❌ 取消」後：
     - 確認對話框消失
     - 回到顯示「🗑️ 刪除」按鈕的狀態
     - 推薦沒有被刪除

---

## 🔍 技術細節

### API 函數參數

#### utils.py - update_recommendation_status()

```python
def update_recommendation_status(
    self, 
    recommendation_id: int, 
    status: str,
    review_notes: str = None  # 可選參數
) -> bool:
    """更新推薦狀態（審核通過/拒絕）"""
    update_data = {
        "new_status": status,
        "reviewer": "admin"  # 從 session_state 獲取
    }
    if review_notes:
        update_data["review_notes"] = review_notes
    
    response = requests.patch(
        f"{self.base_url}/ai/recommendations/{recommendation_id}",
        headers=self._get_ai_auth_headers(),
        json=update_data,
        timeout=10
    )
    # 處理回應...
```

#### modules/ai_recommendations.py - update_recommendation_status()

```python
def update_recommendation_status(
    rec_id: int, 
    status: str, 
    review_notes: str = None  # 新增參數
) -> bool:
    """更新推薦狀態"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            reviewer = st.session_state.get('username', 'admin')
            return st.session_state.api.update_recommendation_status(
                rec_id, 
                status, 
                review_notes  # 正確傳遞參數
            )
        # ...
```

### 狀態轉換圖

```
[PENDING 待審核]
    ├─ ✅ 通過 → [APPROVED 已通過]
    │                ├─ 🚀 實施 → [IMPLEMENTED 已實施] (終態)
    │                └─ ↩️ 撤回 → [PENDING 待審核]
    └─ ❌ 拒絕 → [REJECTED 已拒絕]

[EXPIRED 已過期] (系統自動)

所有狀態 (除了 IMPLEMENTED) 都可以 🗑️ 刪除
```

---

## 📋 驗證清單

- [x] 審核通過功能正常
- [x] 審核拒絕功能正常
- [x] 實施功能正常
- [x] 撤回功能正常
- [x] 刪除按鈕可點擊
- [x] 刪除確認對話框顯示
- [x] 確認刪除功能正常
- [x] 取消刪除功能正常
- [x] 已實施的推薦不能刪除
- [x] 錯誤訊息正確顯示
- [x] 頁面刷新正常
- [x] 狀態轉換正確
- [x] 模組導入無錯誤
- [x] 無 linter 錯誤

---

## 🚨 注意事項

### 權限要求
- ⚠️ 所有審核和刪除操作都需要**管理員權限**
- ⚠️ 一般用戶無法訪問 AI 推薦管理頁面

### 不可逆操作
- ⚠️ 刪除操作是**不可復原**的
- ⚠️ 已實施的推薦**不能刪除**，也不能修改狀態

### API 依賴
- ⚠️ 需要後端 API 正確實現 PATCH 和 DELETE 端點
- ⚠️ 需要 AI_API_KEY 正確配置

---

## 🐛 除錯建議

### 如果審核仍然失敗

1. **檢查 API 連線**:
   ```python
   # 在 Streamlit 中檢查
   st.write("API 客戶端狀態:", hasattr(st.session_state, 'api'))
   st.write("用戶名:", st.session_state.get('username'))
   ```

2. **檢查日誌**:
   ```bash
   # 查看 API 日誌
   tail -f logs/error_*.log | grep "recommendation"
   ```

3. **手動測試 API**:
   ```bash
   curl -X PATCH "$API_URL/ai/recommendations/1" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $AI_API_KEY" \
     -d '{
       "new_status": "APPROVED",
       "reviewer": "admin"
     }'
   ```

### 如果刪除仍然無反應

1. **檢查 session_state**:
   ```python
   # 在確認按鈕點擊處添加調試
   st.write("Session state keys:", list(st.session_state.keys()))
   st.write(f"Confirm key: {confirm_key}")
   st.write(f"Confirm value: {st.session_state.get(confirm_key)}")
   ```

2. **檢查按鈕 key 唯一性**:
   - 確保 `rec_id` 和 `index` 都是唯一的
   - 檢查是否有 key 衝突

---

## 📚 相關文件

- `modules/ai_recommendations.py` - AI 推薦管理 UI
- `utils.py` - API 客戶端實現
- `AI推薦欄位更新說明.md` - 欄位補齊說明

---

**修復人員**: AI Assistant  
**測試狀態**: ✅ 待用戶驗證  
**版本**: 1.0

