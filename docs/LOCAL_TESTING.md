# 🧪 本地開發環境測試指南

在實際部署到伺服器前，您可以在本地開發電腦上測試整個部署架構。

---

## 📋 目錄

- [為什麼要本地測試](#為什麼要本地測試)
- [前置需求](#前置需求)
- [快速開始](#快速開始)
- [配置說明](#配置說明)
- [訪問方式](#訪問方式)
- [常見問題](#常見問題)
- [故障排除](#故障排除)

---

## 🎯 為什麼要本地測試

本地測試可以讓您：

✅ **驗證 Docker 配置** - 確保所有容器正確啟動  
✅ **測試 Nginx 反向代理** - 驗證路由和代理設定  
✅ **檢查服務通訊** - 確認前後端可以正常連接  
✅ **調試 WebSocket** - 測試 Streamlit 互動功能  
✅ **發現問題** - 在本地環境更容易 debug  

---

## 🔧 前置需求

### 軟體需求

1. **Docker Desktop**
   - Mac: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - Windows: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   
   ```bash
   # 驗證安裝
   docker --version
   docker-compose --version
   ```

2. **後端 API 服務**
   - 您的後端 API 需要在本地運行
   - 預設地址：`http://localhost:8000`
   - 確保 API 的 `/health` 端點可訪問

### 檢查後端 API

```bash
# 測試後端 API 是否正常運行
curl http://localhost:8000/health
# 預期：返回 200 OK

# 測試 API 端點
curl http://localhost:8000/api/v1/
```

---

## ⚡ 快速開始

### 方式一：使用本地測試配置（推薦）

```bash
# 1. 確保在專案目錄
cd SmartCaterStreamlit

# 2. 確保後端 API 已在本地運行
# 檢查：curl http://localhost:8000/health

# 3. 啟動本地測試環境
docker-compose -f docker-compose.local.yml up -d

# 4. 查看服務狀態
docker-compose -f docker-compose.local.yml ps

# 5. 查看日誌
docker-compose -f docker-compose.local.yml logs -f
```

### 方式二：僅運行 Streamlit（不使用 Nginx）

```bash
# 直接使用 Dockerfile 運行
docker build -t smartcater-streamlit:local .

docker run -d \
  --name smartcater-streamlit-test \
  -p 8501:8080 \
  -e DYNACONF_API_URL=http://host.docker.internal:8000/api/v1 \
  -v $(pwd)/logs:/app/logs \
  --add-host host.docker.internal:host-gateway \
  smartcater-streamlit:local
```

---

## ⚙️ 配置說明

### 本地配置與生產配置的差異

| 項目 | 本地測試 | 生產環境 |
|------|---------|---------|
| **配置文件** | `docker-compose.local.yml` | `docker-compose.prod.yml` |
| **SSL** | ❌ 不使用（HTTP） | ✅ 使用（HTTPS） |
| **網域** | localhost | 實際網域名稱 |
| **後端 API** | 宿主機 localhost | Docker 內部服務 |
| **端口** | 8501 (Nginx)<br>8502 (直接) | 80, 443 |
| **環境** | default（開發） | production |
| **日誌級別** | DEBUG | INFO |

### 關鍵配置：host.docker.internal

在本地測試中，Streamlit 容器需要訪問宿主機上的後端 API。Docker 提供了特殊的 DNS 名稱：

```yaml
# 在容器內，這個地址會解析到宿主機
DYNACONF_API_URL=http://host.docker.internal:8000/api/v1

# 需要配合這個設定
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### 後端 API 端口配置

如果您的後端 API 不在 port 8000，需要修改：

```yaml
# docker-compose.local.yml
environment:
  - DYNACONF_API_URL=http://host.docker.internal:您的端口/api/v1
```

---

## 🌐 訪問方式

### 通過 Nginx 訪問（測試完整架構）

```
http://localhost:8501
```

這種方式會：
- ✅ 經過 Nginx 反向代理
- ✅ 測試完整的請求路由
- ✅ 驗證 WebSocket 代理設定

### 直接訪問 Streamlit（快速測試）

```
http://localhost:8502
```

這種方式會：
- ✅ 直接訪問 Streamlit 容器
- ✅ 繞過 Nginx
- ✅ 適合快速調試 Streamlit 本身的問題

### 訪問後端 API

```
http://localhost:8000/api/v1
```

這是您的後端 API，在宿主機上運行。

---

## 🔄 常用命令

### 啟動服務

```bash
# 啟動所有服務
docker-compose -f docker-compose.local.yml up -d

# 啟動並查看日誌
docker-compose -f docker-compose.local.yml up

# 僅啟動 Streamlit（不啟動 Nginx）
docker-compose -f docker-compose.local.yml up -d streamlit_app
```

### 查看狀態

```bash
# 查看容器狀態
docker-compose -f docker-compose.local.yml ps

# 查看資源使用
docker stats

# 查看日誌
docker-compose -f docker-compose.local.yml logs -f

# 查看特定服務的日誌
docker-compose -f docker-compose.local.yml logs -f streamlit_app
```

### 重啟服務

```bash
# 重啟所有服務
docker-compose -f docker-compose.local.yml restart

# 重啟特定服務
docker-compose -f docker-compose.local.yml restart streamlit_app

# 重建並重啟
docker-compose -f docker-compose.local.yml up -d --build
```

### 停止和清理

```bash
# 停止所有服務
docker-compose -f docker-compose.local.yml down

# 停止並刪除 volumes
docker-compose -f docker-compose.local.yml down -v

# 停止並刪除映像檔
docker-compose -f docker-compose.local.yml down --rmi all
```

### 進入容器調試

```bash
# 進入 Streamlit 容器
docker-compose -f docker-compose.local.yml exec streamlit_app sh

# 在容器內測試 API 連接
docker-compose -f docker-compose.local.yml exec streamlit_app \
  curl http://host.docker.internal:8000/health
```

---

## ❓ 常見問題

### Q1: 無法訪問 http://localhost:8501

**可能原因**：
1. 容器沒有正常啟動
2. 端口被佔用

**解決方案**：

```bash
# 檢查容器狀態
docker-compose -f docker-compose.local.yml ps

# 檢查端口佔用
lsof -i :8501  # Mac/Linux
netstat -ano | findstr :8501  # Windows

# 查看詳細日誌
docker-compose -f docker-compose.local.yml logs
```

### Q2: Streamlit 無法連接到後端 API

**症狀**：頁面顯示 API 連接錯誤

**解決方案**：

```bash
# 1. 確認後端 API 正在運行
curl http://localhost:8000/health

# 2. 在容器內測試連接
docker-compose -f docker-compose.local.yml exec streamlit_app \
  curl http://host.docker.internal:8000/health

# 3. 檢查環境變數
docker-compose -f docker-compose.local.yml exec streamlit_app \
  env | grep API_URL

# 4. 如果還是不行，嘗試使用宿主機 IP
# 查找宿主機 IP
ifconfig | grep "inet "  # Mac/Linux
ipconfig  # Windows

# 修改 docker-compose.local.yml
# DYNACONF_API_URL=http://192.168.x.x:8000/api/v1
```

### Q3: WebSocket 連接失敗（按鈕無反應）

**症狀**：頁面載入但互動功能不工作

**解決方案**：

```bash
# 1. 確認 Nginx 配置正確
docker-compose -f docker-compose.local.yml exec nginx cat /etc/nginx/conf.d/default.conf | grep -A 3 "Upgrade"

# 應該看到：
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 2. 嘗試直接訪問（繞過 Nginx）
# http://localhost:8502

# 3. 查看瀏覽器控制台的錯誤訊息
```

### Q4: 修改代碼後沒有生效

**解決方案**：

```bash
# 方法 1：重建容器
docker-compose -f docker-compose.local.yml up -d --build

# 方法 2：使用 volume 掛載（已在配置中）
# 修改代碼後，只需重啟容器
docker-compose -f docker-compose.local.yml restart streamlit_app

# 方法 3：進入容器手動重啟 Streamlit
docker-compose -f docker-compose.local.yml exec streamlit_app pkill -f streamlit
```

### Q5: Docker Desktop 沒有運行

**症狀**：執行 docker 命令時出錯

**解決方案**：

```bash
# Mac: 啟動 Docker Desktop 應用程式
open -a Docker

# Windows: 從開始選單啟動 Docker Desktop

# 等待 Docker Desktop 完全啟動（圖示不再轉動）
```

---

## 🔍 故障排除

### 檢查清單

#### 1. Docker 環境檢查

```bash
# Docker 是否運行
docker info

# Docker Compose 版本
docker-compose --version

# 可用的 Docker 資源
docker system df
```

#### 2. 後端 API 檢查

```bash
# API 健康檢查
curl -v http://localhost:8000/health

# API 端點測試
curl http://localhost:8000/api/v1/

# 檢查 API 進程
ps aux | grep python  # 如果是 Python API
```

#### 3. 容器檢查

```bash
# 查看所有容器
docker ps -a

# 查看容器詳細資訊
docker inspect smartcater-streamlit-local

# 查看容器日誌
docker logs smartcater-streamlit-local --tail=100

# 檢查容器健康狀態
docker inspect --format='{{.State.Health.Status}}' smartcater-streamlit-local
```

#### 4. 網路檢查

```bash
# 查看 Docker 網路
docker network ls

# 檢查容器的網路連接
docker network inspect smartcaterstreamlit_local-network

# 測試容器間的網路連通性
docker-compose -f docker-compose.local.yml exec streamlit_app ping -c 3 nginx
```

#### 5. 端口檢查

```bash
# 檢查端口監聽
netstat -an | grep 8501  # Linux/Mac
netstat -ano | findstr 8501  # Windows

# 測試端口連接
telnet localhost 8501
# 或
nc -zv localhost 8501
```

### 完整的診斷腳本

創建一個診斷腳本 `diagnose-local.sh`：

```bash
#!/bin/bash

echo "=== Docker 環境 ==="
docker --version
docker-compose --version
docker info | grep "Server Version"

echo -e "\n=== 後端 API 狀態 ==="
curl -s http://localhost:8000/health || echo "後端 API 無法訪問"

echo -e "\n=== 容器狀態 ==="
docker-compose -f docker-compose.local.yml ps

echo -e "\n=== 端口監聽 ==="
lsof -i :8501 -i :8502 -i :8000 || netstat -ano | findstr "8501 8502 8000"

echo -e "\n=== 容器日誌（最後 20 行）==="
docker-compose -f docker-compose.local.yml logs --tail=20

echo -e "\n=== 容器內 API 連接測試 ==="
docker-compose -f docker-compose.local.yml exec -T streamlit_app \
  curl -s http://host.docker.internal:8000/health || echo "容器無法訪問後端 API"

echo -e "\n診斷完成"
```

---

## 🚀 從本地測試到生產部署

當本地測試都通過後，部署到生產環境只需要：

### 1. 確認配置差異

| 配置項 | 本地 | 生產 |
|--------|------|------|
| Compose 文件 | `docker-compose.local.yml` | `docker-compose.prod.yml` |
| API 地址 | `host.docker.internal` | `smartcater_api:8000` |
| 訪問方式 | HTTP | HTTPS |
| 端口 | 8501, 8502 | 80, 443 |

### 2. 準備生產環境

```bash
# 複製環境變數
cp env.production.example .env.production
nano .env.production

# 填入實際的：
# - DASHBOARD_DOMAIN
# - API_DOMAIN
# - DATABASE_URL
# - SECRET_KEY
# - CERTBOT_EMAIL
```

### 3. 部署到伺服器

```bash
# 上傳專案到伺服器
scp -r SmartCaterStreamlit user@server:/path/

# SSH 到伺服器
ssh user@server
cd /path/SmartCaterStreamlit

# 執行部署腳本
./deploy-server.sh
```

---

## 📊 效能測試（選用）

### 壓力測試

```bash
# 使用 ab (Apache Bench)
ab -n 1000 -c 10 http://localhost:8501/

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8501/
```

### 資源監控

```bash
# 持續監控容器資源使用
docker stats

# 記錄 5 分鐘的資源使用
docker stats --no-stream > stats.log
sleep 300
docker stats --no-stream >> stats.log
```

---

## 🎓 最佳實踐

### 開發工作流

1. **修改代碼** → 在本地編輯器修改
2. **本地測試** → 使用 `docker-compose.local.yml` 測試
3. **驗證功能** → 確保所有功能正常
4. **提交代碼** → Git commit
5. **部署生產** → 使用 `deploy-server.sh`

### 調試技巧

```bash
# 1. 即時查看日誌
docker-compose -f docker-compose.local.yml logs -f streamlit_app

# 2. 進入容器調試
docker-compose -f docker-compose.local.yml exec streamlit_app sh

# 3. 使用 DEBUG 模式
# 在 docker-compose.local.yml 中設定 LOG_LEVEL=DEBUG

# 4. 使用本地代碼（已配置 volume 掛載）
# 修改代碼後只需 restart，不需要 rebuild
```

### 清理環境

```bash
# 定期清理未使用的資源
docker system prune -a

# 清理 volume
docker volume prune

# 清理網路
docker network prune
```

---

## ✅ 測試檢查清單

部署前確認：

- [ ] ✅ Docker Desktop 正常運行
- [ ] ✅ 後端 API 在 localhost:8000 可訪問
- [ ] ✅ Streamlit 容器成功啟動
- [ ] ✅ 可以通過 http://localhost:8501 訪問
- [ ] ✅ 可以成功登入系統
- [ ] ✅ 前端可以連接到後端 API
- [ ] ✅ WebSocket 功能正常（按鈕、滑桿可用）
- [ ] ✅ 所有頁面都能正常載入
- [ ] ✅ 沒有嚴重的錯誤日誌
- [ ] ✅ 通過 Nginx 訪問和直接訪問都正常

---

## 📞 需要幫助？

- 📖 查看完整部署文檔：`docs/SERVER_DEPLOYMENT.md`
- 📋 使用部署檢查清單：`DEPLOYMENT_CHECKLIST.md`
- 🔍 查看故障排除：本文件的「故障排除」章節

---

**祝測試順利！** 🧪✨

