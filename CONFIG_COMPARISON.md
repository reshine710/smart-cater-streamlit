# 📊 配置對比：本地測試 vs 生產部署

快速參考指南，了解本地測試環境和生產環境的配置差異。

---

## 🔄 環境對比總覽

| 項目 | 本地測試 | 生產部署 |
|------|---------|---------|
| **目的** | 驗證部署架構 | 實際提供服務 |
| **配置文件** | `docker-compose.local.yml` | `docker-compose.prod.yml` |
| **啟動腳本** | `./test-local.sh` | `./deploy-server.sh` |
| **環境變數** | 不需要 | `.env.production` |
| **SSL 憑證** | ❌ 不使用 | ✅ Let's Encrypt |
| **協議** | HTTP | HTTPS |
| **網域** | localhost | 實際網域名稱 |

---

## 🌐 訪問方式對比

### 本地測試

```
通過 Nginx:     http://localhost:8501
直接訪問:       http://localhost:8502
後端 API:       http://localhost:8000
```

### 生產部署

```
Dashboard:     https://dashboard.yourdomain.com
API:           https://api.yourdomain.com
```

---

## 🔧 詳細配置差異

### 1. 後端 API 連接

#### 本地測試

```yaml
# docker-compose.local.yml
environment:
  - DYNACONF_API_URL=http://host.docker.internal:8000/api/v1

extra_hosts:
  - "host.docker.internal:host-gateway"
```

**說明**：
- 使用 `host.docker.internal` 訪問宿主機的 localhost
- 後端 API 在您的開發電腦上運行
- 端口通常是 8000

#### 生產部署

```yaml
# docker-compose.prod.yml
environment:
  - DYNACONF_API_URL=http://smartcater_api:8000/api/v1

depends_on:
  - smartcater_api
```

**說明**：
- 使用 Docker 服務名稱 `smartcater_api`
- 後端 API 在同一 Docker 網路中
- 內部直接通訊，更快更安全

---

### 2. Nginx 配置

#### 本地測試

```nginx
# nginx/conf.d/smartcater.local.conf
server {
    listen 80;
    server_name localhost;
    
    location / {
        proxy_pass http://streamlit_backend;
        # ... WebSocket 配置
    }
}
```

**特點**：
- ✅ 僅 HTTP
- ✅ 監聽 localhost
- ✅ 不需要 SSL 憑證
- ✅ 簡化的配置

#### 生產部署

```nginx
# nginx/conf.d/smartcater.conf
server {
    listen 443 ssl http2;
    server_name dashboard.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/.../fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/.../privkey.pem;
    
    # 安全標頭
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    location / {
        proxy_pass http://streamlit_backend;
        # ... WebSocket 配置
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name dashboard.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

**特點**：
- ✅ HTTPS + HTTP/2
- ✅ SSL 憑證驗證
- ✅ 安全標頭配置
- ✅ 自動 HTTPS 重定向

---

### 3. 端口映射

#### 本地測試

```yaml
ports:
  - "8501:80"   # Nginx (通過代理)
  - "8502:8080" # Streamlit (直接訪問)
```

**說明**：
- 兩種訪問方式供測試
- 端口不與常見服務衝突
- 可以同時運行其他開發服務

#### 生產部署

```yaml
ports:
  - "80:80"    # HTTP
  - "443:443"  # HTTPS
```

**說明**：
- 標準 Web 端口
- 僅對外開放必要端口
- Streamlit 端口不對外暴露

---

### 4. 日誌級別

#### 本地測試

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

**說明**：
- 詳細的調試資訊
- 方便排查問題
- 適合開發環境

#### 生產部署

```yaml
environment:
  - LOG_LEVEL=INFO
```

**說明**：
- 正常的運行日誌
- 減少日誌量
- 適合生產環境

---

### 5. Volume 掛載

#### 本地測試

```yaml
volumes:
  - ./logs:/app/logs
  - ./main.py:/app/main.py           # 掛載單個文件
  - ./utils.py:/app/utils.py
  - ./modules:/app/modules           # 掛載目錄
  - ./settings.toml:/app/settings.toml
```

**優點**：
- ✅ 修改代碼立即生效
- ✅ 無需重建容器
- ✅ 快速迭代開發

#### 生產部署

```yaml
volumes:
  - ./logs:/app/logs
  - ./settings.production.toml:/app/settings.production.toml:ro
```

**優點**：
- ✅ 僅掛載必要文件
- ✅ 只讀掛載（:ro）更安全
- ✅ 代碼在容器內，更穩定

---

### 6. 重啟策略

#### 本地測試

```yaml
restart: unless-stopped
```

**說明**：
- 手動停止後不會自動重啟
- 適合開發測試

#### 生產部署

```yaml
restart: always
```

**說明**：
- 崩潰自動重啟
- 伺服器重啟後自動啟動
- 確保服務可用性

---

## 🚀 快速切換指南

### 從本地測試切換到生產部署

1. **準備環境變數**
   ```bash
   cp env.production.example .env.production
   nano .env.production
   ```

2. **更新 Nginx 配置**
   ```bash
   # 將 yourdomain.com 替換為實際網域
   sed -i "s/yourdomain.com/your-actual-domain.com/g" nginx/conf.d/smartcater.conf
   ```

3. **上傳到伺服器**
   ```bash
   scp -r SmartCaterStreamlit user@server:/path/
   ```

4. **在伺服器上部署**
   ```bash
   ssh user@server
   cd /path/SmartCaterStreamlit
   ./deploy-server.sh
   ```

### 從生產回到本地測試

```bash
# 停止生產服務
docker-compose -f docker-compose.prod.yml down

# 啟動本地測試
./test-local.sh
```

---

## 📋 配置檢查清單

### 本地測試前檢查

- [ ] Docker Desktop 正在運行
- [ ] 後端 API 在 localhost:8000 運行
- [ ] Port 8501 和 8502 沒有被佔用
- [ ] 有足夠的磁碟空間（至少 2GB）

### 生產部署前檢查

- [ ] 已準備 `.env.production` 文件
- [ ] DNS 記錄已正確設定
- [ ] 伺服器防火牆已開放 80 和 443 端口
- [ ] 已更新 Nginx 配置中的網域名稱
- [ ] 已準備後端 API 的 Docker 映像檔

---

## 🎯 常見情境

### 情境 1：我想測試 Nginx 反向代理是否正確

```bash
# 使用本地測試配置
./test-local.sh

# 訪問通過 Nginx 的地址
curl http://localhost:8501

# 檢查 Nginx 日誌
docker-compose -f docker-compose.local.yml logs nginx
```

### 情境 2：我想測試前端連接後端是否正常

```bash
# 1. 確保後端 API 運行
curl http://localhost:8000/health

# 2. 啟動本地測試
./test-local.sh

# 3. 在容器內測試連接
docker-compose -f docker-compose.local.yml exec streamlit_app \
  curl http://host.docker.internal:8000/health
```

### 情境 3：我想測試 SSL 配置（生產環境模擬）

本地無法完整測試 SSL，但可以：

```bash
# 方法 1：使用 self-signed 憑證（進階）
# 需要額外配置，不推薦

# 方法 2：直接在測試伺服器上部署
# 使用實際的測試網域和 Let's Encrypt
```

### 情境 4：我想測試 WebSocket 功能

```bash
# 啟動本地測試
./test-local.sh

# 方法 1：通過 Nginx（測試完整路徑）
# 訪問 http://localhost:8501
# 測試按鈕、滑桿等互動功能

# 方法 2：直接訪問（排除 Nginx 問題）
# 訪問 http://localhost:8502
# 如果這裡正常，問題在 Nginx 配置
```

---

## 🔍 故障排除對比

### 問題：服務無法啟動

#### 本地測試

```bash
# 檢查 Docker Desktop
docker info

# 檢查端口佔用
lsof -i :8501 :8502

# 查看詳細日誌
docker-compose -f docker-compose.local.yml logs
```

#### 生產部署

```bash
# 檢查服務狀態
systemctl status docker

# 檢查端口佔用
sudo netstat -tulpn | grep -E ':(80|443)'

# 查看詳細日誌
docker-compose -f docker-compose.prod.yml logs
```

### 問題：無法連接後端 API

#### 本地測試

```bash
# 確認後端運行
curl http://localhost:8000/health

# 測試容器內訪問
docker-compose -f docker-compose.local.yml exec streamlit_app \
  curl http://host.docker.internal:8000/health

# 如果失敗，嘗試使用 IP
# 查找宿主機 IP：ipconfig getifaddr en0
# 修改配置使用實際 IP 而非 host.docker.internal
```

#### 生產部署

```bash
# 檢查 API 容器
docker-compose -f docker-compose.prod.yml ps smartcater_api

# 測試內部連接
docker-compose -f docker-compose.prod.yml exec streamlit_app \
  curl http://smartcater_api:8000/health

# 檢查網路連接
docker network inspect smartcaterstreamlit_app-network
```

---

## 📖 相關文檔

- **本地測試詳細指南**: [`docs/LOCAL_TESTING.md`](docs/LOCAL_TESTING.md)
- **生產部署指南**: [`docs/SERVER_DEPLOYMENT.md`](docs/SERVER_DEPLOYMENT.md)
- **部署檢查清單**: [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
- **快速開始**: [`README_DEPLOYMENT.md`](README_DEPLOYMENT.md)

---

## 💡 最佳實踐

1. **先本地測試，再生產部署**
   ```
   本地測試 → 驗證功能 → 提交代碼 → 生產部署
   ```

2. **使用版本控制**
   ```bash
   git add .
   git commit -m "Ready for production deployment"
   git tag v1.0.0
   ```

3. **保持配置同步**
   - 本地和生產使用相同的基礎配置
   - 只在必要處有差異
   - 使用環境變數控制差異

4. **定期更新**
   ```bash
   # 更新 Docker 映像檔
   docker-compose -f docker-compose.local.yml pull
   docker-compose -f docker-compose.local.yml up -d --build
   ```

---

**記住**：本地測試是為了驗證配置，不是為了取代生產環境！

