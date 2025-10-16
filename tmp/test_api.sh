#!/bin/bash

# 智慧餐飲自動販賣機 API 測試腳本
# 使用 curl 測試 API 端點

# 設定 - 使用新的 /api/v1 前綴
# API_URL="https://scb-api-954587932054.asia-east1.run.app/api/v1"
API_URL="http://127.0.0.1:8000/api/v1"

echo "===== 智慧餐飲自動販賣機 API 測試腳本 ====="

# 1. 使用者認證
echo "===== 使用者認證測試 ====="

# 1.1 建立管理員使用者
echo "建立管理員使用者..."
curl -s -X POST "$API_URL/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testadmin",
    "email": "testadmin@example.com",
    "password": "testpassword",
    "full_name": "Test Admin",
    "is_active": true,
    "is_admin": true
  }' > /dev/null

# 1.2 建立一般使用者
echo "建立一般使用者..."
curl -s -X POST "$API_URL/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "testpassword",
    "full_name": "Test User",
    "is_active": true,
    "is_admin": false
  }' > /dev/null

# 1.3 管理員登入並獲取 Token
echo "管理員登入..."
ADMIN_TOKEN=$(curl -s -X POST "$API_URL/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testadmin&password=testpassword" \
  | jq -r .access_token)

if [ "$ADMIN_TOKEN" = "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "管理員登入失敗，無法獲取 Token。"
    exit 1
fi
echo "管理員 Token 獲取成功。"

# 1.4 一般使用者登入並獲取 Token
echo "一般使用者登入..."
USER_TOKEN=$(curl -s -X POST "$API_URL/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword" \
  | jq -r .access_token)

if [ "$USER_TOKEN" = "null" ] || [ -z "$USER_TOKEN" ]; then
    echo "一般使用者登入失敗，無法獲取 Token。"
    exit 1
fi
echo "一般使用者 Token 獲取成功。"
echo ""

# 1.4 測試管理員使用者查詢功能
echo "===== 管理員使用者查詢 API 測試 ====="

# 1.4.1 獲取所有使用者列表
echo "獲取所有使用者列表..."
curl -s -X GET "$API_URL/users/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
echo ""

# 1.4.2 獲取使用者總數
echo "獲取使用者總數..."
curl -s -X GET "$API_URL/users/count" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
echo ""

# 1.4.3 分頁查詢使用者
echo "分頁查詢使用者（前2筆）..."
curl -s -X GET "$API_URL/users/?skip=0&limit=2" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
echo ""

# 1.4.4 測試一般用戶權限（應該返回權限錯誤）
echo "測試一般用戶查詢權限（應返回權限錯誤）..."
curl -s -X GET "$API_URL/users/" \
  -H "Authorization: Bearer $USER_TOKEN" | jq
echo ""

# 2. 健康檢查端點測試
echo "測試健康檢查端點..."
# curl -s -X GET "https://scb-api-954587932054.asia-east1.run.app/health" | jq
curl -s -X GET "http://127.0.0.1:8000/health" | jq
echo ""

# 3. 機台管理 API 測試
echo "===== 機台管理 API 測試 ====="

# 3.0 先創建測試地點
echo "創建測試地點..."
curl -s -X POST "$API_URL/locations/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "測試地點",
    "is_indoor": true,
    "description": "測試用室內地點",
    "address": "測試地址123號"
  }' > /dev/null

curl -s -X POST "$API_URL/locations/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "測試刪除地點",
    "is_indoor": false,
    "description": "測試用室外地點",
    "address": "測試刪除地址456號"
  }' > /dev/null

echo "測試地點創建完成"
echo ""

# 3.1 獲取機台列表
echo "獲取機台列表..."
curl -s -X GET "$API_URL/machines" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
echo ""

# 3.2 建立新機台
echo "建立新機台..."
curl -s -X POST "$API_URL/machines" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "machine_code": "VM001",
    "name": "測試機台 001",
    "location": "測試地點",
    "ip_address": "192.168.1.100",
    "status": "online",
    "firmware_version": "1.0.0",
    "hardware_version": "A1",
    "max_capacity": 30,
    "temperature": 25.5,
    "humidity": 60.0
  }' | jq
echo ""

# 3.3 獲取機台詳情
echo "獲取機台詳情..."
curl -s -X GET "$API_URL/machines/1" \
  -H "Authorization: Bearer $USER_TOKEN" | jq
echo ""

# 3.4 更新機台資訊
echo "更新機台資訊..."
curl -s -X PUT "$API_URL/machines/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "更新後的測試機台 001",
    "firmware_version": "1.0.1"
  }' | jq
echo ""

# 3.5 更新機台狀態
echo "更新機台狀態..."
curl -s -X POST "$API_URL/machines/1/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{
    "status": "maintenance"
  }' | jq
echo ""

# 3.6 記錄機台心跳
echo "記錄機台心跳..."
curl -s -X POST "$API_URL/machines/1/heartbeat" | jq
echo ""

# 3.7 刪除機台測試（需要管理員權限）
echo "刪除機台測試..."
echo "注意：此操作需要管理員權限，將刪除指定的機台"

# 首先創建一個測試用機台來刪除
echo "創建測試用機台（用於刪除測試）..."
DELETE_TEST_MACHINE=$(curl -s -X POST "$API_URL/machines" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "machine_code": "DELETE_TEST",
    "name": "待刪除測試機台",
    "location": "測試刪除地點",
    "status": "offline"
  }')

echo "$DELETE_TEST_MACHINE" | jq
DELETE_MACHINE_ID=$(echo "$DELETE_TEST_MACHINE" | jq -r '.id // empty')

if [ -n "$DELETE_MACHINE_ID" ] && [ "$DELETE_MACHINE_ID" != "null" ]; then
    echo "成功創建測試機台，ID: $DELETE_MACHINE_ID"
    echo ""

    # 執行刪除操作
    echo "執行刪除機台操作..."
    DELETE_RESULT=$(curl -s -X DELETE "$API_URL/machines/$DELETE_MACHINE_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN")

    echo "$DELETE_RESULT" | jq
    echo ""

    # 驗證刪除結果
    echo "驗證機台是否已刪除..."
    curl -s -X GET "$API_URL/machines/$DELETE_MACHINE_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq
    echo ""

    # 測試刪除不存在的機台
    echo "測試刪除不存在的機台（應返回 404）..."
    curl -s -X DELETE "$API_URL/machines/99999" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq
    echo ""

    # 測試一般用戶刪除機台（應返回權限錯誤）
    echo "測試一般用戶刪除機台權限（應返回權限錯誤）..."
    curl -s -X DELETE "$API_URL/machines/1" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
    echo ""
else
    echo "⚠️  無法創建測試機台，跳過刪除測試"
    echo ""
fi

# 4. 菜單項目 API 測試
echo "===== 菜單項目 API 測試 ====="

# 首先創建一個測試菜單項目
echo "\n--- 4. 測試菜單項目 API ---"
echo "創建一個測試菜單項目..."
CREATE_MENU_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/menu-items/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Menu Item",
    "description": "A delicious item for testing purposes.",
    "price": 9.99,
    "is_active": true
  }')

if [ "$CREATE_MENU_RESPONSE" -eq 200 ] || [ "$CREATE_MENU_RESPONSE" -eq 201 ]; then
    echo "  測試菜單項目創建成功 (HTTP $CREATE_MENU_RESPONSE)"
else
    echo "  測試菜單項目創建失敗 (HTTP $CREATE_MENU_RESPONSE)"
fi

echo "獲取可用的菜單項目..."

# 調試日誌
echo "調試：測試菜單項目API端點..."
echo "1. 使用USER_TOKEN測試："
MENU_ITEMS_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" "$API_URL/menu-items/" \
  -H "Authorization: Bearer $USER_TOKEN")

HTTP_CODE=$(echo "$MENU_ITEMS_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
RESPONSE_BODY=$(echo "$MENU_ITEMS_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')

echo "HTTP狀態碼: $HTTP_CODE"
echo "響應內容:"
echo "$RESPONSE_BODY" | jq -C . 2>/dev/null || echo "$RESPONSE_BODY"

# 如果是307重定向，嘗試帶尾隨斜杠的URL
if [ "$HTTP_CODE" = "307" ]; then
    echo "檢測到307重定向，嘗試帶尾隨斜杠的URL..."
    MENU_ITEMS_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" "$API_URL/menu-items/" \
      -H "Authorization: Bearer $USER_TOKEN")

    HTTP_CODE=$(echo "$MENU_ITEMS_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$MENU_ITEMS_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')

    echo "修正後HTTP狀態碼: $HTTP_CODE"
    echo "修正後響應內容:"
    echo "$RESPONSE_BODY" | jq -C . 2>/dev/null || echo "$RESPONSE_BODY"
fi

# 如果USER_TOKEN失敗，嘗試ADMIN_TOKEN
if [ "$HTTP_CODE" != "200" ]; then
    echo "2. 使用ADMIN_TOKEN測試："
    MENU_ITEMS_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" "$API_URL/menu-items/" \
      -H "Authorization: Bearer $ADMIN_TOKEN")

    HTTP_CODE=$(echo "$MENU_ITEMS_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$MENU_ITEMS_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')

    echo "HTTP狀態碼: $HTTP_CODE"
    echo "響應內容:"
    echo "$RESPONSE_BODY" | jq -C . 2>/dev/null || echo "$RESPONSE_BODY"
fi

FIRST_MENU_ITEM_ID=$(echo "$RESPONSE_BODY" | jq -r '.items[0].id // empty' 2>/dev/null)

echo "調試：解析的菜單項目ID: '$FIRST_MENU_ITEM_ID'"

if [ -z "$FIRST_MENU_ITEM_ID" ] || [ "$FIRST_MENU_ITEM_ID" = "null" ] || [ "$FIRST_MENU_ITEM_ID" = "empty" ]; then
    echo "  無可用的菜單項目，跳過後續測試"
else
    echo "  使用菜單項目ID: $FIRST_MENU_ITEM_ID"

    # 4.1 獲取菜單項目列表
    echo "獲取菜單項目列表..."
    curl -s -X GET "$API_URL/menu-items/" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
    echo ""

    # 4.2 建立新菜單項目
    echo "建立新菜單項目..."
    curl -s -X POST "$API_URL/menu-items/" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -d '{
        "name": "測試餐點 001",
        "description": "這是一個測試餐點",
        "price": 100.0,
        "image_url": "https://example.com/images/test-food-001.jpg",
        "heating_method": "microwave",
        "heating_time": 60,
        "is_active": true,
        "nutrition_info": {
          "calories": 300,
          "protein": 10,
          "carbs": 30,
          "fat": 15
        },
        "tags": ["熱門", "健康"]
      }' | jq
    echo ""

    echo "===== API 測試完成 ====="
fi
