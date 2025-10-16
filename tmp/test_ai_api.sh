#!/bin/bash

# AI 分析團隊 API 測試腳本
# 測試新的 AI API 端點功能

# 設定 - 使用新的 /api/v1 前綴
# API_URL="https://scb-api-954587932054.asia-east1.run.app/api/v1"
API_URL="http://127.0.0.1:8000/api/v1"
AI_API_KEY="ai-team-key-001"

echo "===== AI 分析團隊 API 測試腳本 ====="

# 1. AI API 健康檢查
echo "===== AI API 健康檢查 ====="
echo "測試 AI API 健康檢查端點..."
curl -s -X GET "$API_URL/ai/health" | jq
echo ""

# 2. 測試交易數據查詢 API
echo "===== 交易數據查詢測試 ====="

# 2.1 測試無認證訪問（應該失敗）
echo "測試無認證訪問交易數據（應該失敗）..."
curl -s -X GET "$API_URL/ai/transactional-data?start_date=2025-05-15&end_date=2025-05-18" | jq
echo ""

# 2.2 測試有效 API Key 訪問
echo "測試有效 API Key 訪問交易數據..."
curl -s -X GET "$API_URL/ai/transactional-data?start_date=2025-05-15&end_date=2025-05-18&limit=3" \
  -H "Authorization: Bearer $AI_API_KEY" | jq
echo ""

# 2.3 測試帶機台篩選的查詢
echo "測試帶機台篩選的交易數據查詢..."
curl -s -X GET "$API_URL/ai/transactional-data?start_date=2025-05-15&end_date=2025-05-18&machine_id=1&limit=2" \
  -H "Authorization: Bearer $AI_API_KEY" | jq
echo ""

# 2.4 測試錯誤的日期格式
echo "測試錯誤的日期格式（應該失敗）..."
HTTP_STATUS=$(curl -s -w "%{http_code}" -o /tmp/ai_test_response.json -X GET "$API_URL/ai/transactional-data?start_date=2025-5-15&end_date=2025-5-18" \
  -H "Authorization: Bearer $AI_API_KEY")

if [ "$HTTP_STATUS" = "400" ]; then
  echo "✅ 正確拒絕了錯誤的日期格式"
  cat /tmp/ai_test_response.json | jq
else
  echo "❌ 測試失敗：應該返回400錯誤，但得到HTTP $HTTP_STATUS"
  cat /tmp/ai_test_response.json | jq
fi
echo ""

# 3. 測試推薦系統 API
echo "===== 推薦系統測試 ====="

# 3.1 測試創建動態菜單推薦
echo "測試創建動態菜單推薦..."
curl -s -X POST "$API_URL/ai/recommendations" \
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
        },
        {
          "meal_id": "C",
          "suggested_price": 60.0,
          "priority": 2,
          "restock_quantity": 5,
          "restock_date": "2025/11/10"
        },
        {
          "meal_id": "A",
          "suggested_price": 80.0,
          "priority": 3,
          "restock_quantity": 3,
          "restock_date": "2025/11/15"
        }
      ]
    },
    "notes": "根據近期陰雨天氣及B餐銷量上升趨勢，提高B餐優先級並微調價格。",
    "confidence_score": 0.85
  }' | jq
echo ""

# 3.2 測試創建補貨推薦
echo "測試創建補貨推薦..."
curl -s -X POST "$API_URL/ai/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "recommendation_id": "AI-REC-20250802-002",
    "ai_model_version": "v1.5.2-restock-optimizer",
    "target_machine_ids": ["all"],
    "recommendation_type": "RESTOCK",
    "valid_from": "2025-08-03T08:00:00Z",
    "valid_until": "2025-08-03T18:00:00Z",
    "payload": {
      "restock_suggestions": [
        {
          "meal_id": "A",
          "suggested_quantity": 15,
          "urgency_level": 3
        },
        {
          "meal_id": "B",
          "suggested_quantity": 20,
          "urgency_level": 5
        }
      ]
    },
    "notes": "基於銷售預測，B餐需要緊急補貨",
    "confidence_score": 0.92
  }' | jq
echo ""

# 3.3 測試無效的推薦數據（應該失敗）
echo "測試無效的推薦數據（空的 payload，應該失敗）..."
curl -s -X POST "$API_URL/ai/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "recommendation_id": "AI-REC-20250802-003",
    "ai_model_version": "v1.0.0",
    "target_machine_ids": ["1"],
    "recommendation_type": "DYNAMIC_MENU",
    "valid_from": "2025-08-03T00:00:00Z",
    "valid_until": "2025-08-03T23:59:59Z",
    "payload": {},
    "notes": "測試空推薦"
  }' | jq
echo ""

# 3.4 測試時間範圍錯誤（應該失敗）
echo "測試時間範圍錯誤（valid_from 晚於 valid_until，應該失敗）..."
curl -s -X POST "$API_URL/ai/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AI_API_KEY" \
  -d '{
    "recommendation_id": "AI-REC-20250802-004",
    "ai_model_version": "v1.0.0",
    "target_machine_ids": ["1"],
    "recommendation_type": "DYNAMIC_MENU",
    "valid_from": "2025-08-04T00:00:00Z",
    "valid_until": "2025-08-03T23:59:59Z",
    "payload": {
      "suggested_menu": [
        {
          "meal_id": "A",
          "suggested_price": 80.0,
          "priority": 1
        }
      ]
    }
  }' | jq
echo ""

# 4. 測試推薦列表查詢
echo "===== 推薦列表查詢測試 ====="

# 4.1 獲取所有推薦
echo "獲取所有推薦列表..."
curl -s -X GET "$API_URL/ai/recommendations" \
  -H "Authorization: Bearer $AI_API_KEY" | jq
echo ""

# 4.2 按狀態篩選推薦
echo "按狀態篩選推薦（PENDING）..."
curl -s -X GET "$API_URL/ai/recommendations?status_filter=PENDING" \
  -H "Authorization: Bearer $AI_API_KEY" | jq
echo ""

# 4.3 按機台篩選推薦
echo "按機台篩選推薦（machine_id=1）..."
curl -s -X GET "$API_URL/ai/recommendations?machine_id=1" \
  -H "Authorization: Bearer $AI_API_KEY" | jq
echo ""

# 4.4 測試軟刪除功能
echo "測試軟刪除推薦（ID: 1）..."
HTTP_STATUS=$(curl -s -w "%{http_code}" -o /tmp/ai_delete_response.json -X DELETE "$API_URL/ai/recommendations/1" \
  -H "Authorization: Bearer $AI_API_KEY")

if [ "$HTTP_STATUS" = "204" ]; then
  echo "✅ 成功刪除推薦記錄"
elif [ "$HTTP_STATUS" = "404" ]; then
  echo "⚠️  推薦記錄不存在或已被刪除"
  cat /tmp/ai_delete_response.json | jq
else
  echo "❌ 刪除失敗：HTTP $HTTP_STATUS"
  cat /tmp/ai_delete_response.json | jq
fi
echo ""

# 4.5 測試刪除後的查詢（應該不包含已刪除的記錄）
echo "驗證軟刪除：查詢所有推薦（已刪除的應該被過濾）..."
curl -s -X GET "$API_URL/ai/recommendations" \
  -H "Authorization: Bearer $AI_API_KEY" | jq '.data | length as $count | "找到 \($count) 個有效推薦記錄"'
echo ""

# 5. 測試無效 API Key
echo "===== 認證測試 ====="

# 5.1 測試無效 API Key
echo "測試無效 API Key（應該失敗）..."
curl -s -X GET "$API_URL/ai/transactional-data?start_date=2025-05-15&end_date=2025-05-18" \
  -H "Authorization: Bearer invalid-key" | jq
echo ""

# 5.2 測試權限不足的 API Key
echo "測試權限不足的 API Key（應該失敗）..."
curl -s -X POST "$API_URL/ai/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ai-team-key-002" \
  -d '{
    "recommendation_id": "AI-REC-20250802-005",
    "ai_model_version": "v1.0.0",
    "target_machine_ids": ["1"],
    "recommendation_type": "DYNAMIC_MENU",
    "valid_from": "2025-08-03T00:00:00Z",
    "valid_until": "2025-08-03T23:59:59Z",
    "payload": {
      "suggested_menu": [
        {
          "meal_id": "A",
          "suggested_price": 80.0,
          "priority": 1
        }
      ]
    }
  }' | jq
echo ""

echo "===== AI API 測試完成 ====="
