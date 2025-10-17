# 🔌 後端 API 連接配置指南

本指南說明如何配置 Streamlit 前端連接到不同場景的後端 API。

---

## 📋 目錄

- [配置位置](#配置位置)
- [常見場景](#常見場景)
- [故障排除](#故障排除)

---

## 📍 配置位置

### 本地測試環境

配置文件：`docker-compose.local.yml`

```yaml
services:
  streamlit_app:
    environment:
      - DYNACONF_API_URL=<您的API地址>
```

### 生產環境

配置文件：`docker-compose.prod.yml` 或 `.env.production`

```yaml
services:
  streamlit_app:
    environment:
      - DYNACONF_API_URL=<您的API地址>
```

---

## 🎯 常見場景

### 場景 1：後端 API 使用 Nginx（Port 80）✅ 當前配置

**情況**：您的後端通過 nginx 運行在 `http://localhost`

**配置**：
```yaml
- DYNACONF_API_URL=http://host.docker.internal/api/v1
```

**說明**：
- 使用 `host.docker.internal` 訪問宿主機
- 不指定端口，默認使用 80
- 這是您當前的配置 ✅

**測試**：
```bash
# 測試後端是否可訪問
curl http://localhost/health
curl http://localhost/api/v1/
```

---

### 場景 2：後端 API 直接運行（Port 8000）

**情況**：後端直接運行在 `http://localhost:8000`

**配置**：
```yaml
- DYNACONF_API_URL=http://host.docker.internal:8000/api/v1
```

**說明**：
- 需要明確指定端口 8000
- 適合開發環境直接運行 FastAPI/Flask

**測試**：
```bash
curl http://localhost:8000/health
```

---

### 場景 3：後端 API 在不同端口

**情況**：後端在自定義端口，例如 `http://localhost:3000`

**配置**：
```yaml
- DYNACONF_API_URL=http://host.docker.internal:3000/api/v1
```

**說明**：
- 替換 3000 為您實際的端口號
- 任何端口都可以，只要後端在監聽

**測試**：
```bash
curl http://localhost:3000/health
```

---

### 場景 4：後端 API 在同一 Docker 網路（生產環境）

**情況**：前後端都在 Docker 中，使用內部網路通訊

**配置**：
```yaml
- DYNACONF_API_URL=http://smartcater_api:8000/api/v1
```

**說明**：
- 使用 Docker 服務名稱 `smartcater_api`
- 不需要 `host.docker.internal`
- 內部網路通訊，速度更快

**測試**：
```bash
# 在 Streamlit 容器內測試
docker-compose -f docker-compose.prod.yml exec streamlit_app \
  curl http://smartcater_api:8000/health
```

---

### 場景 5：後端 API 在遠端伺服器

**情況**：後端在另一台伺服器或雲端

**配置**：
```yaml
- DYNACONF_API_URL=https://api.yourdomain.com/api/v1
```

**說明**：
- 使用完整的 URL（包含協議）
- 建議使用 HTTPS
- 適合測試或混合部署

**測試**：
```bash
curl https://api.yourdomain.com/health
```

---

## 🔍 如何確定我的後端配置

### 步驟 1：找到後端運行位置

```bash
# 檢查後端進程
ps aux | grep python    # Python 後端
ps aux | grep node      # Node.js 後端
ps aux | grep java      # Java 後端

# 檢查端口佔用
lsof -i :80          # 檢查 80 端口
lsof -i :8000        # 檢查 8000 端口
lsof -i :3000        # 檢查 3000 端口
```

### 步驟 2：測試後端連接

```bash
# 測試不同端口
curl http://localhost/health
curl http://localhost:80/health
curl http://localhost:8000/health
curl http://localhost:3000/health

# 測試 API 端點
curl http://localhost/api/v1/
curl http://localhost:8000/api/v1/
```

### 步驟 3：確認後端路徑

常見的 API 路徑結構：

```
✅ http://localhost/api/v1/users/token
✅ http://localhost:8000/api/v1/users/token
✅ http://localhost/users/token
❌ http://localhost/v1/api/users/token  (順序錯誤)
```

---

## 🔧 應用配置變更

### 方法 1：重新創建容器（推薦）

```bash
# 停止服務
docker-compose -f docker-compose.local.yml down

# 修改 docker-compose.local.yml 中的 API URL

# 重新啟動
docker-compose -f docker-compose.local.yml up -d
```

### 方法 2：使用環境變數覆蓋

```bash
# 臨時設定環境變數
export DYNACONF_API_URL=http://host.docker.internal/api/v1

# 啟動服務
docker-compose -f docker-compose.local.yml up -d
```

---

## 🐛 故障排除

### 問題 1：Connection Refused

**錯誤訊息**：
```
Failed to establish a new connection: [Errno 61] Connection refused
```

**可能原因**：
1. 後端服務未運行
2. 端口號錯誤
3. 防火牆阻擋

**解決方案**：

```bash
# 1. 確認後端運行
ps aux | grep python  # 或您的後端語言

# 2. 測試後端連接
curl http://localhost/health

# 3. 檢查端口
lsof -i :80
lsof -i :8000

# 4. 查看後端日誌
# 根據您的後端類型查看相應日誌
```

---

### 問題 2：404 Not Found

**錯誤訊息**：
```
404 Not Found
```

**可能原因**：
1. API 路徑錯誤
2. 後端路由配置不正確

**解決方案**：

```bash
# 測試不同路徑
curl http://localhost/health
curl http://localhost/api/health
curl http://localhost/api/v1/

# 查看後端路由配置
# FastAPI: 查看 main.py 的 @app.get() 定義
# Express: 查看 app.js 的 app.get() 定義
```

---

### 問題 3：host.docker.internal 無法解析

**錯誤訊息**：
```
Could not resolve host: host.docker.internal
```

**可能原因**：
- Linux 系統不支援 `host.docker.internal`

**解決方案**：

```yaml
# 方法 1：使用宿主機 IP（推薦）
environment:
  - DYNACONF_API_URL=http://192.168.x.x:8000/api/v1

# 查找宿主機 IP
# Mac:
ipconfig getifaddr en0

# Linux:
ip addr show docker0 | grep inet

# 方法 2：使用 Docker 的 host 網路模式
network_mode: "host"
```

---

### 問題 4：CORS 錯誤

**錯誤訊息**（瀏覽器控制台）：
```
Access to fetch at 'http://...' has been blocked by CORS policy
```

**解決方案**：

在後端 API 中啟用 CORS：

```python
# FastAPI 範例
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制具體網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 配置檢查清單

使用此清單確保配置正確：

- [ ] ✅ 後端 API 正在運行
- [ ] ✅ 知道後端的確切地址和端口
- [ ] ✅ 可以從宿主機訪問後端（`curl` 測試）
- [ ] ✅ API 路徑正確（包含 `/api/v1` 等）
- [ ] ✅ 已修改 `docker-compose.local.yml`
- [ ] ✅ 已重新創建容器（`down` 然後 `up`）
- [ ] ✅ 檢查容器內的環境變數
- [ ] ✅ 查看容器日誌確認無錯誤

---

## 🎓 最佳實踐

### 1. 使用健康檢查端點

確保後端有 `/health` 端點：

```python
# FastAPI 範例
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### 2. 統一 API 版本路徑

建議使用 `/api/v1` 作為前綴：

```
✅ http://localhost/api/v1/users
✅ http://localhost/api/v1/machines
```

### 3. 記錄配置

在 README 或文檔中記錄：
- 後端運行的地址和端口
- API 路徑結構
- 測試命令

### 4. 環境變數管理

```bash
# 創建 .env 文件
cat > .env.local << EOF
API_URL=http://host.docker.internal/api/v1
EOF

# 在 docker-compose 中引用
env_file:
  - .env.local
```

---

## 📞 需要幫助？

如果仍有問題：

1. **查看日誌**
   ```bash
   docker-compose -f docker-compose.local.yml logs -f
   ```

2. **進入容器調試**
   ```bash
   docker-compose -f docker-compose.local.yml exec streamlit_app sh
   # 在容器內執行：
   env | grep API
   ping host.docker.internal
   ```

3. **測試網路連通性**
   ```bash
   # 從容器測試後端
   docker-compose -f docker-compose.local.yml exec streamlit_app \
     wget -O- http://host.docker.internal/health
   ```

---

## 🔗 相關文檔

- [本地測試指南](LOCAL_TESTING.md)
- [生產部署指南](SERVER_DEPLOYMENT.md)
- [配置對比](../CONFIG_COMPARISON.md)

---

**記住**：修改配置後必須重新創建容器（`down` + `up`），重啟（`restart`）不會更新環境變數！

