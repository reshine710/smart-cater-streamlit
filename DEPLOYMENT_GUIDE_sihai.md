# 🚀 SmartCater 前端部署指南
## 專用於 sihai.baimeng.co

本指南包含針對您伺服器的實際配置。

---

## 📋 您的配置資訊

- **主機名稱**: `sihai.baimeng.co`
- **Dashboard 網域**: `dashboard.sihai.baimeng.co`
- **API 網域**: `api.sihai.baimeng.co` (如果後端使用子網域)
- **Email**: `admin@sihai.baimeng.co`

---

## 🚀 快速部署（3 步驟）

### 步驟 1：配置後端 Nginx

```bash
# 1. 進入後端專案目錄
cd /path/to/backend

# 2. 複製 dashboard 配置
cp /path/to/SmartCaterStreamlit/nginx-backend-config/dashboard.conf ./nginx/

# 3. 驗證配置（網域名稱已經正確設定為 sihai.baimeng.co）
cat nginx/dashboard.conf | grep sihai.baimeng.co

# 4. 更新後端的 docker-compose.yml
# 在 nginx 服務的 volumes 中添加：
nano docker-compose.yml
```

添加這一行到 nginx volumes：
```yaml
services:
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro  # 新增這行
      # ... 其他 volumes
```

```bash
# 5. 重新載入 Nginx
docker-compose exec nginx nginx -s reload
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
  -d dashboard.sihai.baimeng.co \
  --email admin@sihai.baimeng.co \
  --agree-tos \
  --non-interactive

# 憑證申請成功後，重新載入 Nginx
docker-compose exec nginx nginx -s reload
```

---

### 步驟 3：設定 DNS

在您的 DNS 提供商設定 A 記錄：

```
類型: A
名稱: dashboard
主機: dashboard.sihai.baimeng.co
指向: <您的伺服器 IP>
TTL: 300 (或自動)
```

等待 DNS 傳播（通常 5-30 分鐘）：

```bash
# 測試 DNS 傳播
nslookup dashboard.sihai.baimeng.co

# 或使用
dig dashboard.sihai.baimeng.co
```

---

### 步驟 4：部署前端

```bash
# 進入前端專案目錄
cd /path/to/SmartCaterStreamlit

# 使用自動化部署腳本
./deploy-integrated.sh

# 或手動部署
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## ✅ 驗證部署

### 1. 檢查所有容器

```bash
docker ps --filter "name=smartcater" --format "table {{.Names}}\t{{.Status}}"

# 應該看到：
# smartcater_nginx         Up (healthy)
# smartcater_api           Up (healthy)
# smartcater_postgres      Up (healthy)
# smartcater_emqx          Up (healthy)
# smartcater_streamlit     Up (healthy)  ← 新增的
```

### 2. 測試內部連接

```bash
# 測試 Streamlit → API
docker exec smartcater_streamlit curl -f http://smartcater_api:8000/health

# 測試 Streamlit → MQTT
docker exec smartcater_streamlit ping -c 3 smartcater_emqx

# 測試 Streamlit 健康檢查
docker exec smartcater_streamlit curl -f http://localhost:8080/_stcore/health
```

### 3. 測試外部訪問

```bash
# 測試 HTTPS 訪問（從外部）
curl -I https://dashboard.sihai.baimeng.co

# 應該返回：
# HTTP/2 200
# server: nginx/1.25.5
# ...
```

### 4. 瀏覽器測試

在瀏覽器中訪問：

```
https://dashboard.sihai.baimeng.co
```

預期結果：
- ✅ 頁面正常載入，無 SSL 警告
- ✅ 看到登入頁面
- ✅ 可以成功登入
- ✅ 所有互動功能正常（按鈕、滑桿等）

---

## 🔧 故障排除

### 問題 1：DNS 未傳播

```bash
# 檢查 DNS
nslookup dashboard.sihai.baimeng.co

# 如果無法解析，等待 DNS 傳播
# 或聯絡您的 DNS 提供商
```

### 問題 2：SSL 憑證錯誤

```bash
# 檢查憑證
docker run --rm \
  -v "/path/to/backend/certbot/conf:/etc/letsencrypt" \
  certbot/certbot certificates

# 如果沒有憑證，重新申請
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.sihai.baimeng.co \
  --email admin@sihai.baimeng.co \
  --agree-tos
```

### 問題 3：502 Bad Gateway

```bash
# 檢查 Streamlit 容器
docker ps | grep streamlit

# 如果沒有運行，啟動它
cd /path/to/SmartCaterStreamlit
docker-compose -f docker-compose.prod.yml up -d

# 查看日誌
docker logs smartcater_streamlit --tail=50

# 測試 Nginx → Streamlit 連接
docker exec smartcater_nginx curl http://smartcater_streamlit:8080/_stcore/health
```

### 問題 4：無法連接 API

```bash
# 從 Streamlit 容器測試
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 檢查網路
docker network inspect smartcater_network | grep -A 10 smartcater_streamlit

# 確認容器在同一網路
docker network inspect smartcater_network | grep -E "smartcater_api|smartcater_streamlit"
```

---

## 📊 完整診斷腳本

創建診斷腳本：

```bash
cat > /tmp/diagnose_sihai.sh << 'EOF'
#!/bin/bash

echo "=== SmartCater 診斷報告 ==="
echo "伺服器: sihai.baimeng.co"
echo "時間: $(date)"
echo ""

echo "=== 1. Docker 容器狀態 ==="
docker ps --filter "name=smartcater" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== 2. 網路檢查 ==="
docker network inspect smartcater_network | grep -A 5 "Containers"
echo ""

echo "=== 3. Streamlit 健康檢查 ==="
docker exec smartcater_streamlit curl -sf http://localhost:8080/_stcore/health && echo "✅ Streamlit 健康" || echo "❌ Streamlit 異常"
echo ""

echo "=== 4. API 連接測試 ==="
docker exec smartcater_streamlit curl -sf http://smartcater_api:8000/health && echo "✅ API 連接正常" || echo "❌ API 連接失敗"
echo ""

echo "=== 5. MQTT 連接測試 ==="
docker exec smartcater_streamlit ping -c 2 smartcater_emqx > /dev/null 2>&1 && echo "✅ MQTT 連接正常" || echo "❌ MQTT 連接失敗"
echo ""

echo "=== 6. DNS 檢查 ==="
nslookup dashboard.sihai.baimeng.co | grep "Address" | tail -1
echo ""

echo "=== 7. SSL 憑證檢查 ==="
curl -I https://dashboard.sihai.baimeng.co 2>&1 | grep -E "HTTP|SSL"
echo ""

echo "=== 8. Nginx 配置測試 ==="
docker exec smartcater_nginx nginx -t 2>&1
echo ""

echo "=== 診斷完成 ==="
EOF

chmod +x /tmp/diagnose_sihai.sh
/tmp/diagnose_sihai.sh
```

---

## 🔄 日常維護

### 更新前端

```bash
cd /path/to/SmartCaterStreamlit

# 拉取最新代碼
git pull

# 重新建置並部署
docker-compose -f docker-compose.prod.yml up -d --build

# 查看日誌確認更新成功
docker-compose -f docker-compose.prod.yml logs -f --tail=50
```

### 查看日誌

```bash
# Streamlit 日誌
docker-compose -f docker-compose.prod.yml logs -f streamlit_app

# 或直接查看容器日誌
docker logs smartcater_streamlit -f --tail=100
```

### 重啟服務

```bash
cd /path/to/SmartCaterStreamlit

# 重啟 Streamlit
docker-compose -f docker-compose.prod.yml restart

# 或
docker restart smartcater_streamlit
```

### SSL 憑證更新

憑證會自動更新（後端的 certbot 容器），但您可以手動觸發：

```bash
cd /path/to/backend

# 手動更新憑證
docker-compose exec certbot certbot renew

# 重新載入 Nginx
docker-compose exec nginx nginx -s reload
```

---

## 📞 需要幫助？

### 完整文檔

- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - 配置變更總結
- [docs/INTEGRATED_DEPLOYMENT.md](docs/INTEGRATED_DEPLOYMENT.md) - 完整部署指南
- [QUICK_START.md](QUICK_START.md) - 快速開始

### 關鍵配置文件

- `nginx-backend-config/dashboard.conf` - Nginx 配置（已配置 sihai.baimeng.co）
- `docker-compose.prod.yml` - 前端部署配置
- `env.production.example` - 環境變數範例（已配置 sihai.baimeng.co）

---

## ✅ 部署檢查清單

- [ ] ✅ 後端服務全部運行
- [ ] ✅ `smartcater_network` 網路存在
- [ ] ✅ 已複製 `dashboard.conf` 到後端
- [ ] ✅ 已更新後端 `docker-compose.yml`
- [ ] ✅ 已重新載入後端 Nginx
- [ ] ✅ DNS A 記錄已設定：`dashboard.sihai.baimeng.co`
- [ ] ✅ SSL 憑證已申請並安裝
- [ ] ✅ 前端容器已建置並啟動
- [ ] ✅ 所有健康檢查通過
- [ ] ✅ 可通過 HTTPS 訪問：`https://dashboard.sihai.baimeng.co`
- [ ] ✅ 登入功能正常
- [ ] ✅ WebSocket 功能正常

---

## 🎉 部署成功後

您的服務將通過以下網址訪問：

- 📊 **Dashboard**: `https://dashboard.sihai.baimeng.co`
- 🔌 **API**: `https://sihai.baimeng.co` (或 `https://api.sihai.baimeng.co`)
- 📡 **MQTT**: `mqtts://sihai.baimeng.co:8883`
- ⚙️ **EMQX 管理**: `https://sihai.baimeng.co:18083`

**祝部署順利！** 🚀

