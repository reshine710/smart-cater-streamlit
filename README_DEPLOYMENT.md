# 🚀 SmartCater 部署快速開始

這是 SmartCater 智慧販賣機管理系統的部署快速指南。

---

## 📚 文檔導航

根據您的部署目標選擇對應的文檔：

### 🏢 自有伺服器部署（推薦用於生產環境）
- **完整指南**: [`docs/SERVER_DEPLOYMENT.md`](docs/SERVER_DEPLOYMENT.md)
- **檢查清單**: [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
- **部署腳本**: [`deploy-server.sh`](deploy-server.sh)

**適用場景**：
- ✅ 有自己的伺服器（VPS、實體機）
- ✅ 有固定 IP 和網域名稱
- ✅ 需要完全控制和自定義配置
- ✅ 預算有限，希望長期使用降低成本

### ☁️ Cloud Run 部署（適合快速原型）
- **完整指南**: [`docs/CLOUD_DEPLOYMENT.md`](docs/CLOUD_DEPLOYMENT.md)
- **部署腳本**: [`deploy.sh`](deploy.sh)

**適用場景**：
- ✅ 快速驗證概念（POC）
- ✅ 不想管理伺服器
- ✅ 流量不穩定，需要自動擴展
- ✅ 已使用 Google Cloud Platform

---

## ⚡ 5 分鐘快速部署（自有伺服器）

### 前置條件
- Ubuntu/Debian 伺服器
- Docker 和 Docker Compose
- 網域名稱（已設定 DNS A 記錄）

### 部署步驟

```bash
# 1. 克隆專案
git clone <repository-url>
cd SmartCaterStreamlit

# 2. 配置環境變數
cp env.production.example .env.production
nano .env.production  # 修改必要的配置

# 3. 執行部署腳本
chmod +x deploy-server.sh
./deploy-server.sh
```

部署完成後訪問：
- **儀表板**: `https://dashboard.yourdomain.com`
- **API**: `https://api.yourdomain.com`

---

## 🏗️ 架構概覽

### 自有伺服器架構

```
外部流量 (Port 80/443)
        ↓
    [Nginx 反向代理]
    - SSL 終止
    - 路由分發
        ↓
    ┌───────┴───────┐
    ↓               ↓
[Streamlit]     [API Backend]
 Port 8080       Port 8000
```

**核心優勢**：
- 🔒 自動 SSL 憑證管理
- 🚀 內部高速通訊
- 📊 統一日誌管理
- 🔧 易於擴展

### 服務組成

| 服務 | 說明 | 端口 |
|------|------|------|
| **Nginx** | 反向代理和 SSL 終止 | 80, 443 |
| **Streamlit** | 前端管理介面 | 8080 (內部) |
| **API Backend** | 後端 API 服務 | 8000 (內部) |
| **Certbot** | SSL 憑證自動管理 | - |

---

## 📝 配置檔案說明

### 必須配置的檔案

1. **`.env.production`** - 環境變數
   ```bash
   DASHBOARD_DOMAIN=dashboard.yourdomain.com
   API_DOMAIN=api.yourdomain.com
   DATABASE_URL=postgresql://user:pass@db:5432/smartcater
   SECRET_KEY=<生成的密鑰>
   ```

2. **`nginx/conf.d/smartcater.conf`** - Nginx 配置
   - 修改網域名稱
   - 調整 SSL 設定（如需要）

3. **`docker-compose.prod.yml`** - Docker Compose 配置
   - 配置 API 映像檔來源
   - 調整資源限制（如需要）

### 選用配置

- **`settings.production.toml`** - Streamlit 應用配置
- **`nginx/nginx.conf`** - Nginx 主配置（通常不需要修改）

---

## 🔧 常用管理命令

```bash
# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看即時日誌
docker-compose -f docker-compose.prod.yml logs -f

# 重啟服務
docker-compose -f docker-compose.prod.yml restart

# 更新部署
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# 停止服務
docker-compose -f docker-compose.prod.yml down
```

---

## 🔍 故障排除

### SSL 憑證問題
```bash
# 檢查 DNS 設定
nslookup dashboard.yourdomain.com

# 手動更新憑證
docker-compose -f docker-compose.prod.yml exec certbot certbot renew
```

### 容器無法啟動
```bash
# 查看詳細日誌
docker-compose -f docker-compose.prod.yml logs [service_name]

# 檢查配置
docker-compose -f docker-compose.prod.yml config
```

### 502 錯誤
```bash
# 檢查後端服務
docker-compose -f docker-compose.prod.yml ps

# 測試內部連接
docker-compose -f docker-compose.prod.yml exec nginx \
  curl http://streamlit_app:8080/_stcore/health
```

---

## 📊 環境對比

| 特性 | 自有伺服器 | Cloud Run |
|------|-----------|-----------|
| **成本** | 固定月費 | 按使用量計費 |
| **管理** | 需要維護 | 無需維護 |
| **擴展性** | 手動擴展 | 自動擴展 |
| **控制權** | 完全控制 | 有限控制 |
| **適用場景** | 生產環境 | 原型/測試 |

---

## 🔐 安全建議

1. **使用強密碼**
   ```bash
   # 生成 SECRET_KEY
   openssl rand -hex 32
   ```

2. **設定防火牆**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **定期更新**
   ```bash
   # 更新系統
   sudo apt update && sudo apt upgrade -y
   
   # 更新 Docker 映像檔
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **啟用日誌輪替**
   - 參考 `docs/SERVER_DEPLOYMENT.md` 中的日誌輪替設定

---

## 📈 效能優化建議

### 基礎優化（已內建）
- ✅ Gzip 壓縮
- ✅ HTTP/2
- ✅ 健康檢查
- ✅ 自動重啟

### 進階優化
- 配置 Nginx 快取
- 使用 CDN
- 資料庫連接池
- Redis 快取層

參考完整文檔：`docs/SERVER_DEPLOYMENT.md`

---

## 📞 技術支援

### 文檔資源
- [完整部署指南](docs/SERVER_DEPLOYMENT.md)
- [部署檢查清單](DEPLOYMENT_CHECKLIST.md)
- [Cloud Run 部署](docs/CLOUD_DEPLOYMENT.md)
- [環境切換說明](docs/環境切換配置說明.md)

### 常見問題
查看 `docs/SERVER_DEPLOYMENT.md` 的「故障排除」章節

### 獲取幫助
- 查看專案 Issues
- 聯絡系統管理員

---

## 🎯 下一步

部署完成後，您可能需要：

1. **配置備份計畫** - 定期備份日誌和配置
2. **設定監控** - 使用 Prometheus/Grafana 等工具
3. **優化效能** - 根據實際使用情況調整資源
4. **安全加固** - 限制 SSH 訪問、設定 fail2ban 等

---

**祝您部署順利！** 🚀

如有任何問題，請參考完整文檔或聯絡支援團隊。

