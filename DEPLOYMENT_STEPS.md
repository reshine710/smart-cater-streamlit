# 🚀 部署步驟與測試指南

## 當前狀況分析

**後端網路**: `v023_smartcater_network`  
**問題**: Nginx 容器持續重啟 (Restarting)

---

## 📝 部署步驟

### 步驟 1: 修正網路配置 ✅

已更新 `docker-compose.prod.yml` 中的網路名稱為 `v023_smartcater_network`

### 步驟 2: 部署前端

```bash
# 建置
docker-compose -f docker-compose.prod.yml build

# 啟動
docker-compose -f docker-compose.prod.yml up -d

# 查看狀態
docker-compose -f docker-compose.prod.yml ps
```

### 步驟 3: 檢查網路連接

```bash
# 確認前端容器已加入網路
docker network inspect v023_smartcater_network | grep smartcater_streamlit

# 測試前端 → API 連接
docker exec smartcater_streamlit curl -f http://smartcater_api:8000/health
```

---

## ⚠️ 後端 Nginx 問題

**症狀**: `smartcater_nginx` 持續重啟

**可能原因**:
1. 配置文件 `nginx/sihai.conf` 不存在
2. 配置文件語法錯誤
3. 上游服務名稱錯誤

### 診斷命令

```bash
# 查看 Nginx 錯誤日誌
docker logs smartcater_nginx --tail=50

# 查看 Nginx 配置文件
docker exec smartcater_nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null || echo "配置文件不存在"

# 測試配置語法
docker exec smartcater_nginx nginx -t 2>&1
```

### 解決方案

**選項 A: 創建單一網域配置**

1. 在後端專案的 `nginx/` 目錄創建 `sihai.conf`：

```bash
# 從前端專案複製
cp /path/to/SmartCaterStreamlit/nginx-backend-config/sihai-single-domain.conf \
   /path/to/backend/nginx/sihai.conf
```

2. 確認後端 docker-compose.yml 的 volume 掛載：

```yaml
nginx:
  volumes:
    - ./nginx/sihai.conf:/etc/nginx/conf.d/default.conf:ro
```

3. 重啟 Nginx：

```bash
docker-compose restart nginx
```

**選項 B: 檢查現有配置**

如果已有配置文件，需要添加前端路由：

```nginx
# 在現有的 server 區塊中添加

# API 路由（優先）
location /api/ {
    proxy_pass http://smartcater_api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 前端路由
location / {
    proxy_pass http://smartcater_streamlit:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支援
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    proxy_buffering off;
}
```

---

## ✅ 完整測試流程

### 1. 確認所有容器運行

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"

# 預期結果：
# smartcater_nginx         Up (healthy)
# smartcater_api           Up (healthy)
# smartcater_emqx          Up (healthy)
# smartcater_postgres      Up (healthy)
# smartcater_streamlit     Up (healthy)  ← 前端
```

### 2. 測試網路連通性

```bash
# 從前端容器測試 API
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 從前端容器測試 MQTT
docker exec smartcater_streamlit ping -c 3 smartcater_emqx

# 預期：都應該成功
```

### 3. 測試 Nginx 代理

```bash
# 測試 API 路由
curl http://localhost/health
curl http://localhost/api/v1/

# 測試前端路由
curl -I http://localhost/

# 如果有 HTTPS：
curl -I https://sihai.baimeng.co/
curl https://sihai.baimeng.co/health
```

### 4. 測試前端功能

```bash
# 查看前端日誌
docker logs smartcater_streamlit --tail=50

# 檢查是否有 API 連接錯誤
docker logs smartcater_streamlit | grep -i "error\|failed\|connection"
```

### 5. 瀏覽器測試

訪問：`https://sihai.baimeng.co/` （或 `http://sihai.baimeng.co/`）

確認：
- [ ] 頁面正常載入
- [ ] 可以看到登入介面
- [ ] 可以成功登入
- [ ] 按鈕和互動功能正常

---

## 🐛 故障排除

### 問題 1: 前端容器無法啟動

```bash
# 查看詳細錯誤
docker-compose -f docker-compose.prod.yml logs

# 檢查映像是否建置成功
docker images | grep smartcater_streamlit
```

### 問題 2: 網路連接失敗

```bash
# 確認容器在同一網路
docker network inspect v023_smartcater_network

# 重新啟動前端
docker-compose -f docker-compose.prod.yml restart
```

### 問題 3: Nginx 502 錯誤

```bash
# 檢查前端容器狀態
docker ps | grep smartcater_streamlit

# 檢查 Nginx 到前端的連接
docker exec smartcater_nginx ping smartcater_streamlit
docker exec smartcater_nginx curl http://smartcater_streamlit:8080/_stcore/health
```

### 問題 4: API 連接失敗（前端報錯）

```bash
# 檢查環境變數
docker exec smartcater_streamlit env | grep API

# 測試內部連接
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 如果失敗，檢查網路
docker network inspect v023_smartcater_network | grep -A 10 smartcater
```

---

## 📋 部署檢查清單

### 後端（需要先修復）
- [ ] Nginx 容器正常運行（不再重啟）
- [ ] Nginx 配置包含前端路由
- [ ] 可以訪問 API：`curl http://localhost/health`

### 前端
- [ ] docker-compose.prod.yml 網路名稱正確
- [ ] 前端容器成功啟動
- [ ] 前端加入 v023_smartcater_network
- [ ] 可以從前端訪問 API
- [ ] 可以從前端訪問 MQTT

### 整合測試
- [ ] 可以通過 Nginx 訪問前端
- [ ] 可以通過 Nginx 訪問 API
- [ ] 前端可以成功登入
- [ ] 所有功能正常運作

---

## 🎯 下一步行動

### 優先順序 1: 修復後端 Nginx

```bash
# 查看錯誤
docker logs smartcater_nginx

# 根據錯誤訊息採取行動
```

### 優先順序 2: 部署前端

```bash
# 在前端專案目錄
docker-compose -f docker-compose.prod.yml up -d
```

### 優先順序 3: 驗證整合

```bash
# 執行上述所有測試
```

---

## 📞 需要幫助？

提供以下資訊：

```bash
# 1. Nginx 錯誤日誌
docker logs smartcater_nginx --tail=100

# 2. 網路詳情
docker network inspect v023_smartcater_network

# 3. 容器狀態
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

**當前狀態**: 
- ✅ 網路配置已修正
- ⚠️ 需要修復後端 Nginx
- ⏭️ 然後部署和測試前端

