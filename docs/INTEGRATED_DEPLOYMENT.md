# 🚀 前後端整合部署指南

本指南說明如何將 Streamlit 前端整合到已部署的後端系統中。

---

## 📋 目錄

- [架構概覽](#架構概覽)
- [前置條件](#前置條件)
- [部署步驟](#部署步驟)
- [驗證部署](#驗證部署)
- [故障排除](#故障排除)

---

## 🏗️ 架構概覽

### 整合架構圖

```
外部訪問 (Port 80/443)
        ↓
    [後端 Nginx]  ← 唯一的對外入口
        ↓
    ┌───────┴────────────┐
    ↓                    ↓
[後端 API]          [Streamlit 前端]
Port 8000           Port 8080
(smartcater_api)    (smartcater_streamlit)
    ↓                    ↓
[PostgreSQL]        [共享 EMQX]
```

### 網域配置

- **API**: `yourdomain.com` 或 `api.yourdomain.com`
- **Dashboard**: `dashboard.yourdomain.com` ← 新增

### 關鍵設計

✅ **單一 Nginx** - 後端的 Nginx 統一處理所有請求  
✅ **共享網路** - 前後端在同一 Docker 網路 `smartcater_network`  
✅ **共享 MQTT** - 前端直接連接後端的 EMQX  
✅ **內部通訊** - 服務間使用容器名稱直接通訊  

---

## 🔧 前置條件

### 1. 後端已部署並運行

確認後端服務正常：

```bash
# 檢查後端容器
docker ps | grep smartcater

# 應該看到以下容器：
# - smartcater_nginx
# - smartcater_api
# - smartcater_postgres
# - smartcater_emqx
```

### 2. 確認網路存在

```bash
# 檢查 Docker 網路
docker network ls | grep smartcater_network

# 應該看到：
# NETWORK ID     NAME                  DRIVER    SCOPE
# xxxxxxxxxx     smartcater_network    bridge    local
```

### 3. 準備前端專案

```bash
# 進入前端專案目錄
cd /path/to/SmartCaterStreamlit

# 確認文件存在
ls -la docker-compose.prod.yml
ls -la Dockerfile
```

---

## 📝 部署步驟

### 步驟 1：配置後端 Nginx

#### 1.1 複製 Dashboard 配置到後端

```bash
# 假設後端專案在 /path/to/backend
cp nginx-backend-config/dashboard.conf /path/to/backend/nginx/

# 或直接創建文件
cat > /path/to/backend/nginx/dashboard.conf << 'EOF'
# [貼上 dashboard.conf 的內容]
EOF
```

#### 1.2 修改網域名稱

```bash
# 進入後端專案目錄
cd /path/to/backend

# 替換網域名稱
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/dashboard.conf
```

#### 1.3 更新後端 docker-compose.yml

在後端的 `docker-compose.yml` 中，確保 Nginx 掛載了新配置：

```yaml
# 後端的 docker-compose.yml
services:
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro  # 新增這行
      # ... 其他 volumes
```

#### 1.4 重新載入 Nginx

```bash
cd /path/to/backend

# 方法 1：重新載入配置（推薦，不中斷服務）
docker-compose exec nginx nginx -s reload

# 方法 2：重啟容器（如果方法 1 失敗）
docker-compose restart nginx
```

---

### 步驟 2：申請 SSL 憑證

```bash
cd /path/to/backend

# 為 dashboard 子網域申請憑證
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.your-actual-domain.com \
  --email admin@your-actual-domain.com \
  --agree-tos

# 申請成功後，重新載入 Nginx
docker-compose exec nginx nginx -s reload
```

---

### 步驟 3：部署前端服務

#### 3.1 檢查配置

```bash
cd /path/to/SmartCaterStreamlit

# 確認 docker-compose.prod.yml 正確配置
cat docker-compose.prod.yml

# 檢查關鍵配置：
# 1. DYNACONF_API_URL=http://smartcater_api:8000/api/v1
# 2. networks: smartcater_network (external: true)
# 3. MQTT_BROKER_HOST=smartcater_emqx
```

#### 3.2 建置並啟動

```bash
# 建置 Docker 映像
docker-compose -f docker-compose.prod.yml build

# 啟動服務
docker-compose -f docker-compose.prod.yml up -d

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f
```

---

### 步驟 4：設定 DNS

在您的 DNS 提供商設定 A 記錄：

```
dashboard.your-actual-domain.com  →  伺服器 IP
```

等待 DNS 傳播（通常 5-30 分鐘）。

---

## ✅ 驗證部署

### 1. 檢查容器狀態

```bash
# 查看所有 SmartCater 容器
docker ps --filter "name=smartcater" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 應該看到：
# smartcater_nginx         Up (healthy)      0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# smartcater_api           Up (healthy)      
# smartcater_postgres      Up (healthy)      
# smartcater_emqx          Up (healthy)      0.0.0.0:8883->8883/tcp, 0.0.0.0:18083->18083/tcp
# smartcater_streamlit     Up (healthy)      
```

### 2. 測試健康檢查

```bash
# 測試 Streamlit 健康狀態
docker exec smartcater_streamlit curl -f http://localhost:8080/_stcore/health

# 測試通過 Nginx 訪問（從外部）
curl -k https://dashboard.your-actual-domain.com/_stcore/health
```

### 3. 測試網路連通性

```bash
# 從 Streamlit 容器測試 API 連接
docker exec smartcater_streamlit curl -f http://smartcater_api:8000/health

# 從 Streamlit 容器測試 MQTT 連接
docker exec smartcater_streamlit ping -c 3 smartcater_emqx
```

### 4. 瀏覽器測試

在瀏覽器中訪問：

```
https://dashboard.your-actual-domain.com
```

預期結果：
- ✅ 頁面正常載入（無 SSL 警告）
- ✅ 可以看到登入頁面
- ✅ 可以成功登入
- ✅ 所有互動功能正常

---

## 🐛 故障排除

### 問題 1：網路錯誤 - network not found

**錯誤訊息**：
```
Error response from daemon: network smartcater_network not found
```

**原因**：後端網路不存在或名稱不匹配

**解決方案**：

```bash
# 1. 檢查後端網路名稱
docker network ls | grep smartcater

# 2. 如果網路名稱不同，修改前端的 docker-compose.prod.yml
networks:
  smartcater_network:
    external: true
    name: <實際的網路名稱>  # 例如：backend_smartcater_network

# 3. 如果網路不存在，手動創建
docker network create smartcater_network --subnet 172.28.0.0/16
```

---

### 問題 2：Streamlit 無法連接 API

**症狀**：前端顯示 API 連接錯誤

**解決方案**：

```bash
# 1. 確認後端 API 容器名稱
docker ps --filter "name=api" --format "{{.Names}}"

# 2. 從 Streamlit 容器測試連接
docker exec smartcater_streamlit ping smartcater_api
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 3. 如果容器名稱不同，修改 docker-compose.prod.yml
environment:
  - DYNACONF_API_URL=http://<實際容器名稱>:8000/api/v1

# 4. 重新啟動
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

### 問題 3：502 Bad Gateway

**症狀**：訪問 dashboard 時出現 502 錯誤

**可能原因**：
1. Streamlit 容器未運行
2. Nginx 配置錯誤
3. 網路連接問題

**解決方案**：

```bash
# 1. 檢查 Streamlit 容器
docker ps | grep streamlit

# 2. 查看 Streamlit 日誌
docker logs smartcater_streamlit --tail=50

# 3. 測試 Nginx 到 Streamlit 的連接
docker exec smartcater_nginx ping smartcater_streamlit
docker exec smartcater_nginx curl http://smartcater_streamlit:8080/_stcore/health

# 4. 檢查 Nginx 配置
docker exec smartcater_nginx nginx -t

# 5. 查看 Nginx 錯誤日誌
docker exec smartcater_nginx cat /var/log/nginx/dashboard_error.log
```

---

### 問題 4：SSL 憑證錯誤

**症狀**：瀏覽器顯示憑證無效

**解決方案**：

```bash
# 1. 檢查憑證是否存在
ls -la /path/to/backend/certbot/conf/live/dashboard.your-domain.com/

# 2. 檢查憑證有效期
docker run --rm \
  -v "/path/to/backend/certbot/conf:/etc/letsencrypt" \
  certbot/certbot certificates

# 3. 手動更新憑證
docker run --rm \
  -v "/path/to/backend/certbot/conf:/etc/letsencrypt" \
  -v "/path/to/backend/certbot/www:/var/www/certbot" \
  certbot/certbot renew

# 4. 重新載入 Nginx
docker-compose -f docker-compose.yml exec nginx nginx -s reload
```

---

### 問題 5：WebSocket 連接失敗

**症狀**：頁面載入但按鈕無反應

**解決方案**：

```bash
# 1. 確認 Nginx 配置包含 WebSocket 支援
docker exec smartcater_nginx cat /etc/nginx/conf.d/dashboard.conf | grep -A 3 "Upgrade"

# 應該看到：
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 2. 如果配置不正確，修正並重新載入
docker-compose exec nginx nginx -s reload

# 3. 檢查瀏覽器控制台的 WebSocket 錯誤
```

---

## 📊 部署檢查清單

### 後端準備

- [ ] ✅ 後端服務正常運行
- [ ] ✅ `smartcater_network` 網路存在
- [ ] ✅ 已添加 `dashboard.conf` 到後端 Nginx
- [ ] ✅ Nginx 配置已重新載入
- [ ] ✅ DNS 記錄已設定
- [ ] ✅ SSL 憑證已申請

### 前端部署

- [ ] ✅ `docker-compose.prod.yml` 配置正確
- [ ] ✅ API URL 指向 `smartcater_api`
- [ ] ✅ MQTT 指向 `smartcater_emqx`
- [ ] ✅ 網路設定為 `external: true`
- [ ] ✅ Docker 映像已建置
- [ ] ✅ 容器已啟動並健康

### 驗證測試

- [ ] ✅ Streamlit 健康檢查通過
- [ ] ✅ 可以從容器內訪問 API
- [ ] ✅ 可以從容器內訪問 MQTT
- [ ] ✅ HTTPS 訪問正常（無憑證警告）
- [ ] ✅ 可以成功登入
- [ ] ✅ WebSocket 功能正常

---

## 🔄 日常維護

### 更新前端

```bash
cd /path/to/SmartCaterStreamlit

# 拉取最新代碼
git pull

# 重新建置並部署
docker-compose -f docker-compose.prod.yml up -d --build
```

### 查看日誌

```bash
# Streamlit 日誌
docker-compose -f docker-compose.prod.yml logs -f streamlit_app

# Nginx 日誌（在後端目錄）
docker-compose logs -f nginx

# 所有 SmartCater 容器的日誌
docker ps --filter "name=smartcater" --format "{{.Names}}" | xargs -I {} docker logs {} --tail=20
```

### 備份

```bash
# 備份前端配置和日誌
tar -czf streamlit-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.prod.yml \
  Dockerfile \
  settings.production.toml \
  logs/

# 備份到遠端（示例）
scp streamlit-backup-*.tar.gz user@backup-server:/backups/
```

---

## 📞 需要幫助？

### 相關文檔

- [本地測試指南](LOCAL_TESTING.md)
- [獨立部署指南](SERVER_DEPLOYMENT.md)
- [API 連接配置](API_CONNECTION_GUIDE.md)

### 診斷命令

```bash
# 完整診斷腳本
cat > diagnose.sh << 'EOF'
#!/bin/bash
echo "=== Docker 容器狀態 ==="
docker ps --filter "name=smartcater"

echo -e "\n=== 網路檢查 ==="
docker network inspect smartcater_network | grep -A 5 "Containers"

echo -e "\n=== Streamlit 健康檢查 ==="
docker exec smartcater_streamlit curl -sf http://localhost:8080/_stcore/health

echo -e "\n=== API 連接測試 ==="
docker exec smartcater_streamlit curl -sf http://smartcater_api:8000/health

echo -e "\n=== MQTT 連接測試 ==="
docker exec smartcater_streamlit ping -c 3 smartcater_emqx

echo -e "\n=== Nginx 配置測試 ==="
docker exec smartcater_nginx nginx -t

echo -e "\n診斷完成"
EOF

chmod +x diagnose.sh
./diagnose.sh
```

---

**部署成功後，您的系統將通過以下網址訪問：**

- 🌐 **API**: `https://your-domain.com`
- 📊 **Dashboard**: `https://dashboard.your-domain.com`
- 📡 **MQTT**: `mqtts://your-domain.com:8883`
- ⚙️ **EMQX 管理**: `https://your-domain.com:18083`

祝部署順利！ 🚀

