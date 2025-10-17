# 🚀 SmartCater 自有伺服器部署指南

完整的自有伺服器部署說明，透過 Nginx 反向代理實現多服務整合。

---

## 📋 目錄

- [部署架構](#部署架構)
- [前置需求](#前置需求)
- [快速部署](#快速部署)
- [詳細步驟](#詳細步驟)
- [配置說明](#配置說明)
- [管理維護](#管理維護)
- [故障排除](#故障排除)

---

## 🏗️ 部署架構

### 服務架構圖

```
外部訪問 (Port 80/443)
        ↓
    [Nginx 反向代理]
        ↓
    ┌───────┴───────┐
    ↓               ↓
[Streamlit 前端] [後端 API]
 (內部 8080)     (內部 8000)
```

### 網域配置

- **儀表板**: `https://dashboard.yourdomain.com` → Streamlit (Port 8080)
- **API**: `https://api.yourdomain.com` → API Backend (Port 8000)

### 核心優勢

✅ **單一入口**: 所有流量經由 Nginx 統一管理  
✅ **SSL 加密**: 自動申請和更新 Let's Encrypt 憑證  
✅ **內部通訊**: 服務間透過 Docker 網路直接通訊，不對外暴露  
✅ **易於擴展**: 可輕鬆添加更多子網域服務  

---

## 🔧 前置需求

### 1. 伺服器要求

- **作業系統**: Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- **記憶體**: 最少 2GB RAM（建議 4GB+）
- **硬碟**: 最少 20GB 可用空間
- **網路**: 穩定的網路連接，固定 IP 位址

### 2. 軟體需求

#### 安裝 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 將當前使用者加入 docker 群組
sudo usermod -aG docker $USER
# 登出後重新登入以套用群組變更

# 驗證安裝
docker --version
```

#### 安裝 Docker Compose

```bash
# 方法一：使用 Docker Plugin (推薦)
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 方法二：獨立安裝
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 驗證安裝
docker-compose --version
```

### 3. 網域設定

在您的 DNS 提供商設定以下 A 記錄：

```
dashboard.yourdomain.com  →  您的伺服器 IP
api.yourdomain.com        →  您的伺服器 IP
```

**DNS 傳播時間**: 通常需要 5-30 分鐘，最長可能需要 48 小時。

### 4. 防火牆設定

確保以下 Port 已開放：

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

---

## ⚡ 快速部署

### 一鍵部署

```bash
# 1. 克隆專案
git clone <repository-url>
cd SmartCaterStreamlit

# 2. 複製環境變數檔案並編輯
cp env.production.example .env.production
nano .env.production  # 編輯必要的配置

# 3. 執行部署腳本
./deploy-server.sh
```

部署腳本會自動執行：
- ✅ 檢查前置條件
- ✅ 創建必要目錄
- ✅ 申請 SSL 憑證
- ✅ 建置並啟動所有服務
- ✅ 健康檢查

---

## 📝 詳細步驟

### 步驟 1：準備專案

```bash
# 上傳專案到伺服器
scp -r SmartCaterStreamlit user@your-server:/home/user/

# 或使用 Git
ssh user@your-server
git clone <repository-url>
cd SmartCaterStreamlit
```

### 步驟 2：配置環境變數

```bash
# 複製環境變數範例
cp env.production.example .env.production

# 編輯環境變數
nano .env.production
```

**必填項目**：

```bash
# 網域配置（必填）
DASHBOARD_DOMAIN=dashboard.yourdomain.com
API_DOMAIN=api.yourdomain.com

# 資料庫配置（必填）
DATABASE_URL=postgresql://user:password@db:5432/smartcater

# JWT 配置（必填）
SECRET_KEY=$(openssl rand -hex 32)  # 生成隨機密鑰

# Email（用於 SSL 憑證通知）
CERTBOT_EMAIL=admin@yourdomain.com
```

### 步驟 3：配置後端 API

如果您的後端 API 是獨立專案，需要先準備：

```bash
# 選項 A：使用預先建置的映像檔
# 在 docker-compose.prod.yml 中取消註解：
# image: smartcater-api:latest

# 選項 B：本地建置
# 確保 API 專案在正確的路徑，並在 docker-compose.prod.yml 中設定：
# build:
#   context: ../SmartCaterAPI
#   dockerfile: Dockerfile
```

### 步驟 4：申請 SSL 憑證（首次部署）

```bash
# 確保網域已正確指向伺服器
ping dashboard.yourdomain.com
ping api.yourdomain.com

# 創建必要目錄
mkdir -p certbot/conf certbot/www

# 先啟動 Nginx（用於 SSL 驗證）
docker-compose -f docker-compose.prod.yml up -d nginx

# 申請憑證 - Dashboard
docker run -it --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# 申請憑證 - API
docker run -it --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d api.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos
```

### 步驟 5：更新 Nginx 配置

```bash
# 替換配置檔中的網域名稱
sed -i "s/dashboard\.yourdomain\.com/${DASHBOARD_DOMAIN}/g" nginx/conf.d/smartcater.conf
sed -i "s/api\.yourdomain\.com/${API_DOMAIN}/g" nginx/conf.d/smartcater.conf

# 檢查配置語法
docker run --rm -v $(pwd)/nginx:/etc/nginx nginx:1.25-alpine nginx -t
```

### 步驟 6：部署所有服務

```bash
# 建置映像檔
docker-compose -f docker-compose.prod.yml build

# 啟動所有服務
docker-compose -f docker-compose.prod.yml up -d

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f
```

### 步驟 7：驗證部署

```bash
# 檢查容器健康狀態
docker ps

# 測試 API
curl -k https://api.yourdomain.com/health

# 測試 Streamlit
curl -k https://dashboard.yourdomain.com

# 在瀏覽器中訪問
# https://dashboard.yourdomain.com
```

---

## ⚙️ 配置說明

### Docker Compose 結構

```yaml
services:
  smartcater_api:      # 後端 API 服務
    - Port: 8000 (內部)
    - 健康檢查: /health
    
  streamlit_app:       # Streamlit 前端
    - Port: 8080 (內部)
    - 健康檢查: /_stcore/health
    - 依賴: smartcater_api
    
  nginx:               # 反向代理
    - Port: 80, 443 (對外)
    - SSL 憑證管理
    
  certbot:             # SSL 憑證自動更新
    - 每 12 小時檢查一次
```

### Nginx 配置重點

#### WebSocket 支援（Streamlit 必需）

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

#### CORS 設定（API）

```nginx
add_header Access-Control-Allow-Origin "*" always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
```

#### SSL 安全配置

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
add_header Strict-Transport-Security "max-age=31536000" always;
```

### 環境變數優先順序

1. `.env.production` 檔案中的變數
2. `docker-compose.prod.yml` 中定義的預設值
3. `settings.production.toml` 中的配置

---

## 🔄 管理維護

### 常用命令

```bash
# 查看所有容器狀態
docker-compose -f docker-compose.prod.yml ps

# 查看即時日誌
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服務日誌
docker-compose -f docker-compose.prod.yml logs -f streamlit_app

# 重啟單一服務
docker-compose -f docker-compose.prod.yml restart streamlit_app

# 重啟所有服務
docker-compose -f docker-compose.prod.yml restart

# 停止所有服務
docker-compose -f docker-compose.prod.yml down

# 停止並刪除 volumes
docker-compose -f docker-compose.prod.yml down -v
```

### 更新部署

```bash
# 拉取最新程式碼
git pull origin main

# 重新建置並啟動
docker-compose -f docker-compose.prod.yml up -d --build

# 清理未使用的映像檔
docker system prune -a
```

### SSL 憑證管理

```bash
# 手動更新憑證
docker-compose -f docker-compose.prod.yml exec certbot certbot renew

# 測試憑證更新（不實際更新）
docker-compose -f docker-compose.prod.yml exec certbot certbot renew --dry-run

# 查看憑證資訊
sudo certbot certificates --config-dir ./certbot/conf

# 憑證有效期
openssl x509 -in certbot/conf/live/dashboard.yourdomain.com/cert.pem -noout -dates
```

### 備份與還原

```bash
# 備份日誌和配置
tar -czf backup-$(date +%Y%m%d).tar.gz \
  logs/ \
  nginx/ \
  certbot/ \
  .env.production \
  settings.production.toml

# 還原
tar -xzf backup-20240101.tar.gz
```

### 監控

```bash
# 容器資源使用
docker stats

# 檢查 Nginx 錯誤日誌
tail -f nginx/logs/error.log

# 檢查應用日誌
tail -f logs/app_$(date +%Y-%m-%d).log
tail -f logs/error_$(date +%Y-%m-%d).log
```

---

## 🔍 故障排除

### 問題 1：SSL 憑證申請失敗

**症狀**: Let's Encrypt 驗證失敗

**解決方案**:

```bash
# 1. 確認網域 DNS 設定正確
nslookup dashboard.yourdomain.com

# 2. 確認 Port 80 可訪問
curl http://dashboard.yourdomain.com/.well-known/acme-challenge/test

# 3. 檢查防火牆
sudo ufw status

# 4. 查看 Certbot 詳細日誌
docker-compose -f docker-compose.prod.yml logs certbot
```

### 問題 2：Streamlit 無法連接 API

**症狀**: 前端顯示 API 連接錯誤

**解決方案**:

```bash
# 1. 確認 API 容器運行正常
docker-compose -f docker-compose.prod.yml ps smartcater_api

# 2. 檢查 API 健康狀態
docker-compose -f docker-compose.prod.yml exec streamlit_app curl http://smartcater_api:8000/health

# 3. 檢查環境變數
docker-compose -f docker-compose.prod.yml exec streamlit_app env | grep API_URL

# 4. 查看 Streamlit 日誌
docker-compose -f docker-compose.prod.yml logs streamlit_app
```

### 問題 3：Nginx 502 Bad Gateway

**症狀**: 訪問網站顯示 502 錯誤

**解決方案**:

```bash
# 1. 確認後端服務運行
docker-compose -f docker-compose.prod.yml ps

# 2. 檢查後端服務健康
docker-compose -f docker-compose.prod.yml exec nginx curl http://streamlit_app:8080/_stcore/health

# 3. 查看 Nginx 錯誤日誌
docker-compose -f docker-compose.prod.yml logs nginx

# 4. 測試 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# 5. 重啟 Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### 問題 4：WebSocket 連接失敗

**症狀**: Streamlit 互動功能無法使用

**解決方案**:

```bash
# 1. 確認 Nginx 配置包含 WebSocket 設定
grep -A 3 "Upgrade" nginx/conf.d/smartcater.conf

# 應該看到：
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 2. 重新載入 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### 問題 5：容器啟動失敗

**症狀**: 容器反覆重啟或無法啟動

**解決方案**:

```bash
# 1. 查看容器日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 streamlit_app

# 2. 檢查環境變數
docker-compose -f docker-compose.prod.yml config

# 3. 檢查端口衝突
sudo netstat -tulpn | grep -E ':(80|443|8000|8080)'

# 4. 清理並重新啟動
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### 問題 6：記憶體不足

**症狀**: 服務運行緩慢或崩潰

**解決方案**:

```bash
# 1. 檢查系統資源
free -h
df -h

# 2. 限制容器記憶體使用（在 docker-compose.prod.yml 中）
services:
  streamlit_app:
    mem_limit: 1g
    mem_reservation: 512m

# 3. 清理未使用的 Docker 資源
docker system prune -a
docker volume prune
```

---

## 📊 效能優化

### 1. Nginx 快取設定

```nginx
# 在 nginx/conf.d/smartcater.conf 中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;

location / {
    proxy_cache my_cache;
    proxy_cache_valid 200 60m;
}
```

### 2. Docker 映像檔優化

```bash
# 使用多階段建置減小映像檔大小
# 定期清理未使用的映像檔
docker image prune -a --filter "until=24h"
```

### 3. 日誌輪替

```bash
# 創建 logrotate 配置
sudo nano /etc/logrotate.d/smartcater

# 內容：
/path/to/SmartCaterStreamlit/nginx/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        docker-compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
    endscript
}
```

---

## 🔐 安全建議

### 1. 定期更新

```bash
# 更新系統套件
sudo apt update && sudo apt upgrade -y

# 更新 Docker 映像檔
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 使用強密碼

```bash
# 生成安全的 SECRET_KEY
openssl rand -hex 32

# 生成資料庫密碼
openssl rand -base64 24
```

### 3. 限制 SSH 訪問

```bash
# 禁用 root 登入
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no

# 使用 SSH 金鑰認證
# 禁用密碼登入
```

### 4. 設定防火牆規則

```bash
# 只允許必要的 Port
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 📞 支援與聯絡

如遇到本指南未涵蓋的問題，請：

1. 查看專案 Issues
2. 查閱相關文檔
3. 聯絡系統管理員

---

**祝部署順利！** 🚀

