# 📋 後端工程師 - Nginx 配置指南

## Streamlit 前端整合配置說明

**文檔版本**: v1.0  
**目標網域**: dashboard.sihai.baimeng.co  
**服務**: SmartCater Streamlit 前端管理介面  
**配置人**: 後端工程師  

---

## 📖 背景說明

### 整合需求

前端團隊已完成 Streamlit 管理介面開發，需要整合到現有後端系統中。整合方式為：

- **前端服務**: 獨立的 Docker 容器（`smartcater_streamlit`）
- **網路連接**: 加入後端的 `smartcater_network` Docker 網路
- **對外訪問**: 通過後端的 Nginx 反向代理
- **網域名稱**: `dashboard.sihai.baimeng.co`

### 架構概覽

```
外部請求 (Port 80/443)
        ↓
   後端 Nginx (您維護的)
        ↓
   ┌────┴─────────────┐
   ↓                  ↓
API 服務          Streamlit 前端
(現有)            (新增)
Port 8000         Port 8080
```

---

## 🎯 您需要做的事情

### 概述

1. 添加一個 Nginx 配置文件（`dashboard.conf`）
2. 更新 `docker-compose.yml` 掛載此配置
3. 為新子網域申請 SSL 憑證
4. 重新載入 Nginx

**預計時間**: 15-20 分鐘  
**影響範圍**: 僅新增配置，不影響現有服務  

---

## 📁 步驟 1：添加 Nginx 配置文件

### 1.1 獲取配置文件

前端團隊已準備好配置文件，位於：

```
SmartCaterStreamlit/nginx-backend-config/dashboard.conf
```

### 1.2 複製到後端專案

```bash
# 方法 A：從前端專案複製
cp /path/to/SmartCaterStreamlit/nginx-backend-config/dashboard.conf ./nginx/

# 方法 B：直接創建（內容見下方）
nano nginx/dashboard.conf
```

### 1.3 配置文件內容

**文件位置**: `nginx/dashboard.conf`

```nginx
# ===================================
# Streamlit Dashboard 配置
# ===================================

# 上游服務定義 - Streamlit 前端
upstream streamlit_backend {
    server smartcater_streamlit:8080;
}

# ===================================
# HTTP 配置 - 重定向到 HTTPS
# ===================================
server {
    listen 80;
    server_name dashboard.sihai.baimeng.co;
    
    # Let's Encrypt 驗證路徑
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # 其他請求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# ===================================
# HTTPS - Streamlit 儀表板
# ===================================
server {
    listen 443 ssl http2;
    server_name dashboard.sihai.baimeng.co;
    
    # SSL 憑證配置
    ssl_certificate /etc/letsencrypt/live/dashboard.sihai.baimeng.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.sihai.baimeng.co/privkey.pem;
    
    # SSL 安全設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全標頭
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 客戶端請求大小限制
    client_max_body_size 20M;
    
    # 日誌
    access_log /var/log/nginx/dashboard_access.log;
    error_log /var/log/nginx/dashboard_error.log;
    
    # ===================================
    # Streamlit 應用代理
    # ===================================
    location / {
        proxy_pass http://streamlit_backend;
        
        # 基本代理標頭
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支援（Streamlit 必需）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超時設定（Streamlit 需要較長時間）
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # 緩衝設定
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # ===================================
    # Streamlit 健康檢查端點
    # ===================================
    location /_stcore/health {
        proxy_pass http://streamlit_backend/_stcore/health;
        proxy_set_header Host $host;
        access_log off;
    }
}
```

### 1.4 配置重點說明

| 配置項 | 值 | 說明 |
|--------|-----|------|
| **upstream** | `smartcater_streamlit:8080` | 前端容器名稱和端口 |
| **server_name** | `dashboard.sihai.baimeng.co` | 前端訪問網域 |
| **SSL 憑證** | `/etc/letsencrypt/live/dashboard.sihai.baimeng.co/` | 憑證路徑 |
| **WebSocket** | `proxy_http_version 1.1` + `Upgrade` headers | Streamlit 互動功能必需 |
| **超時** | `600s` | Streamlit 需要較長超時時間 |

---

## 📝 步驟 2：更新 docker-compose.yml

### 2.1 編輯配置

```bash
nano docker-compose.yml
# 或
vim docker-compose.yml
```

### 2.2 添加 Volume 掛載

在 `nginx` 服務的 `volumes` 區塊中，添加新的配置文件：

**修改前**：
```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    container_name: smartcater_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      # ... 其他 volumes
```

**修改後**：
```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    container_name: smartcater_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro  # 新增這行
      # ... 其他 volumes
```

### 2.3 驗證配置

```bash
# 檢查 YAML 語法
docker-compose config

# 應該沒有錯誤輸出
```

---

## 🔐 步驟 3：申請 SSL 憑證

### 3.1 前置確認

確認 DNS 已設定：

```bash
# 測試 DNS 解析
nslookup dashboard.sihai.baimeng.co

# 應該返回您的伺服器 IP
```

### 3.2 申請憑證

```bash
# 使用 Certbot 申請憑證
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.sihai.baimeng.co \
  --email admin@sihai.baimeng.co \
  --agree-tos \
  --non-interactive
```

### 3.3 驗證憑證

```bash
# 檢查憑證是否存在
ls -la certbot/conf/live/dashboard.sihai.baimeng.co/

# 應該看到：
# fullchain.pem
# privkey.pem
```

### 3.4 憑證自動更新

如果您已經有 `certbot` 容器在運行，新的憑證會自動包含在更新流程中。

---

## 🔄 步驟 4：重新載入 Nginx

### 4.1 測試配置

```bash
# 測試 Nginx 配置語法
docker-compose exec nginx nginx -t

# 預期輸出：
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4.2 重新載入配置

```bash
# 方法 A：重新載入（推薦，不中斷服務）
docker-compose exec nginx nginx -s reload

# 方法 B：重啟容器（如果方法 A 失敗）
docker-compose restart nginx
```

### 4.3 確認配置生效

```bash
# 檢查 Nginx 容器日誌
docker-compose logs nginx --tail=20

# 應該沒有錯誤訊息
```

---

## ✅ 步驟 5：驗證配置

### 5.1 檢查 Nginx 配置文件

```bash
# 驗證配置文件已掛載
docker-compose exec nginx ls -la /etc/nginx/conf.d/

# 應該看到：
# default.conf
# dashboard.conf  ← 新增的
```

### 5.2 測試 upstream 連接

```bash
# 確認可以連接到 Streamlit 容器
docker-compose exec nginx ping -c 3 smartcater_streamlit

# 如果前端容器已啟動，應該能 ping 通
```

### 5.3 測試 HTTP 訪問

```bash
# 從外部測試（前端容器必須已啟動）
curl -I http://dashboard.sihai.baimeng.co

# 預期：301 重定向到 HTTPS
```

### 5.4 測試 HTTPS 訪問

```bash
# 測試 HTTPS
curl -I https://dashboard.sihai.baimeng.co

# 預期：200 OK
```

---

## 📊 完整配置檢查清單

### 配置前確認

- [ ] 前端團隊已提供 `dashboard.conf` 文件
- [ ] 前端容器名稱確認為 `smartcater_streamlit`
- [ ] DNS A 記錄已設定：`dashboard.sihai.baimeng.co`
- [ ] DNS 已傳播完成

### 配置步驟

- [ ] 已複製 `dashboard.conf` 到 `nginx/` 目錄
- [ ] 已更新 `docker-compose.yml` 添加 volume 掛載
- [ ] 已驗證 YAML 語法：`docker-compose config`
- [ ] 已申請 SSL 憑證
- [ ] 已測試 Nginx 配置：`nginx -t`
- [ ] 已重新載入 Nginx：`nginx -s reload`

### 配置後驗證

- [ ] Nginx 配置文件已正確掛載
- [ ] 可以 ping 通前端容器
- [ ] HTTP 請求正確重定向到 HTTPS
- [ ] HTTPS 訪問返回 200 OK
- [ ] 瀏覽器可以正常訪問
- [ ] SSL 憑證有效且無警告

---

## 🐛 故障排除

### 問題 1：Nginx 配置測試失敗

**錯誤訊息**：
```
nginx: [emerg] unknown directive "..." in /etc/nginx/conf.d/dashboard.conf
```

**解決方案**：
```bash
# 檢查配置文件語法
cat nginx/dashboard.conf

# 確認沒有多餘的空格或特殊字符
# 重新複製配置文件
```

---

### 問題 2：無法連接到 smartcater_streamlit

**錯誤訊息**：
```
nginx: [emerg] host not found in upstream "smartcater_streamlit"
```

**原因**：前端容器未啟動或不在同一網路

**解決方案**：
```bash
# 1. 檢查前端容器是否存在
docker ps -a | grep smartcater_streamlit

# 2. 檢查網路連接
docker network inspect smartcater_network | grep smartcater_streamlit

# 3. 通知前端團隊啟動容器
```

---

### 問題 3：SSL 憑證申請失敗

**錯誤訊息**：
```
Failed authorization procedure. dashboard.sihai.baimeng.co (http-01): ...
```

**解決方案**：
```bash
# 1. 確認 DNS 正確解析
nslookup dashboard.sihai.baimeng.co

# 2. 確認 80 端口可訪問
curl http://dashboard.sihai.baimeng.co/.well-known/acme-challenge/test

# 3. 檢查防火牆設定
sudo ufw status

# 4. 查看詳細錯誤
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.sihai.baimeng.co \
  --email admin@sihai.baimeng.co \
  --agree-tos \
  --dry-run  # 測試模式
```

---

### 問題 4：502 Bad Gateway

**症狀**：訪問 `https://dashboard.sihai.baimeng.co` 顯示 502

**解決方案**：
```bash
# 1. 檢查前端容器狀態
docker ps | grep smartcater_streamlit

# 2. 測試 Nginx → Streamlit 連接
docker-compose exec nginx curl http://smartcater_streamlit:8080/_stcore/health

# 3. 查看 Nginx 錯誤日誌
docker-compose exec nginx cat /var/log/nginx/dashboard_error.log

# 4. 查看前端容器日誌
docker logs smartcater_streamlit --tail=50

# 5. 通知前端團隊檢查容器
```

---

### 問題 5：WebSocket 連接失敗

**症狀**：頁面載入但互動功能無法使用

**解決方案**：
```bash
# 確認 WebSocket 配置存在
docker-compose exec nginx cat /etc/nginx/conf.d/dashboard.conf | grep -A 3 "Upgrade"

# 應該看到：
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 如果配置正確但還是不行，重新載入 Nginx
docker-compose exec nginx nginx -s reload
```

---

## 📋 與前端團隊的協調

### 前端團隊負責

- ✅ 提供 `dashboard.conf` 配置文件
- ✅ 建置和啟動 `smartcater_streamlit` 容器
- ✅ 確保容器加入 `smartcater_network` 網路
- ✅ 容器健康檢查和日誌監控
- ✅ 應用程式層面的問題排查

### 後端團隊（您）負責

- ✅ 配置 Nginx（添加 `dashboard.conf`）
- ✅ 申請和管理 SSL 憑證
- ✅ DNS 設定（如有權限）
- ✅ Nginx 層面的問題排查
- ✅ 服務器資源監控

### 溝通檢查點

| 階段 | 確認事項 |
|------|---------|
| **配置前** | DNS 已設定、容器名稱確認 |
| **配置中** | 配置文件正確、憑證申請成功 |
| **配置後** | 可訪問、功能正常 |
| **上線後** | 效能監控、錯誤追蹤 |

---

## 📊 效能和監控建議

### 日誌查看

```bash
# Nginx 訪問日誌
tail -f nginx/logs/dashboard_access.log

# Nginx 錯誤日誌
tail -f nginx/logs/dashboard_error.log

# Nginx 容器日誌
docker-compose logs -f nginx
```

### 效能監控

```bash
# 查看 Nginx 連接狀態
docker-compose exec nginx sh -c "echo 'status' | nc localhost 80"

# 查看資源使用
docker stats smartcater_nginx
```

### 建議的監控指標

- HTTP 狀態碼分布（特別關注 5xx）
- 回應時間
- WebSocket 連接數
- 錯誤日誌數量

---

## 🔄 後續維護

### SSL 憑證更新

憑證會自動更新（如果有 certbot 容器），無需手動操作。

### 配置變更

如需修改配置：

```bash
# 1. 編輯配置
nano nginx/dashboard.conf

# 2. 測試配置
docker-compose exec nginx nginx -t

# 3. 重新載入
docker-compose exec nginx nginx -s reload
```

### 回滾方案

如遇問題需要回滾：

```bash
# 1. 移除 volume 掛載（編輯 docker-compose.yml）
# 2. 重新載入 Nginx
docker-compose exec nginx nginx -s reload

# 或直接移除配置文件
docker-compose exec nginx rm /etc/nginx/conf.d/dashboard.conf
docker-compose exec nginx nginx -s reload
```

---

## ✅ 配置完成確認

當以下條件都滿足時，配置即為完成：

- [x] `dashboard.conf` 已添加到 nginx 目錄
- [x] `docker-compose.yml` 已更新
- [x] SSL 憑證已申請並安裝
- [x] Nginx 配置測試通過
- [x] Nginx 已成功重新載入
- [x] 可以通過 HTTPS 訪問 `https://dashboard.sihai.baimeng.co`
- [x] 前端頁面正常顯示
- [x] 互動功能正常（WebSocket 工作）

---

## 📞 聯絡資訊

### 需要支援

如遇到問題：

1. **查看本文檔的故障排除章節**
2. **聯絡前端團隊**（應用層面問題）
3. **查看詳細日誌**（`docker-compose logs nginx`）

### 文檔資訊

- **文檔版本**: v1.0
- **最後更新**: 2025-10-18
- **維護**: SmartCater DevOps Team
- **網域**: dashboard.sihai.baimeng.co

---

## 📚 附錄

### A. 完整的 docker-compose.yml 示例（nginx 部分）

```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    container_name: smartcater_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    networks:
      - smartcater_network
    depends_on:
      - api
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### B. 快速命令參考

```bash
# 測試配置
docker-compose exec nginx nginx -t

# 重新載入
docker-compose exec nginx nginx -s reload

# 查看日誌
docker-compose logs -f nginx

# 測試連接
docker-compose exec nginx curl http://smartcater_streamlit:8080/_stcore/health

# 檢查憑證
ls -la certbot/conf/live/dashboard.sihai.baimeng.co/
```

---

**配置完成後，請通知前端團隊可以開始部署容器。** 🚀

