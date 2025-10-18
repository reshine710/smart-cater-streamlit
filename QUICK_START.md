# 🚀 快速開始指南

根據您的後端架構，前端已配置為**整合部署模式**。

---

## 📊 您的架構

```
後端 Nginx (Port 80/443)
    ├─→ API 服務
    ├─→ Dashboard (新增) ← Streamlit 前端
    └─→ EMQX MQTT
```

---

## ⚡ 3 步驟快速部署

### 步驟 1：配置後端 Nginx

```bash
# 1. 複製配置到後端
cp nginx-backend-config/dashboard.conf /path/to/backend/nginx/

# 2. 修改網域名稱
cd /path/to/backend
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/dashboard.conf

# 3. 更新後端 docker-compose.yml，添加 volume:
#    - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro

# 4. 重新載入 Nginx
docker-compose exec nginx nginx -s reload
```

### 步驟 2：申請 SSL 憑證（如需 HTTPS）

```bash
cd /path/to/backend

docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.your-actual-domain.com \
  --email admin@your-actual-domain.com \
  --agree-tos
```

### 步驟 3：部署前端

```bash
cd /path/to/SmartCaterStreamlit

# 方法 A：使用部署腳本（推薦）
./deploy-integrated.sh

# 方法 B：手動部署
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## ✅ 驗證部署

```bash
# 檢查容器
docker ps | grep smartcater_streamlit

# 測試 API 連接
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 瀏覽器訪問
# https://dashboard.your-domain.com
```

---

## 📚 完整文檔

| 文檔 | 說明 |
|------|------|
| [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) | 配置變更總結 |
| [docs/INTEGRATED_DEPLOYMENT.md](docs/INTEGRATED_DEPLOYMENT.md) | 完整部署指南 |
| [docs/LOCAL_TESTING.md](docs/LOCAL_TESTING.md) | 本地測試指南 |

---

## 🔧 常用命令

```bash
# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f

# 重啟服務
docker-compose -f docker-compose.prod.yml restart

# 更新部署
docker-compose -f docker-compose.prod.yml up -d --build

# 停止服務
docker-compose -f docker-compose.prod.yml down
```

---

## 🆘 遇到問題？

1. **檢查清單**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#檢查清單)
2. **故障排除**: [docs/INTEGRATED_DEPLOYMENT.md](docs/INTEGRATED_DEPLOYMENT.md#故障排除)
3. **診斷命令**: [docs/INTEGRATED_DEPLOYMENT.md](docs/INTEGRATED_DEPLOYMENT.md#診斷命令)

---

**訪問地址**: `https://dashboard.<your-domain>` 🎉

