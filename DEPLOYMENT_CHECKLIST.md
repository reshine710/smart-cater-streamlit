# ✅ SmartCater 部署檢查清單

快速檢查清單，確保部署流程順利進行。

---

## 📋 部署前檢查

### ☐ 伺服器準備
- [ ] 伺服器已安裝 Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- [ ] 至少 2GB RAM（建議 4GB+）
- [ ] 至少 20GB 可用硬碟空間
- [ ] 已取得伺服器 SSH 訪問權限
- [ ] 伺服器有固定的公網 IP 位址

### ☐ 軟體安裝
- [ ] Docker 已安裝並運行
  ```bash
  docker --version
  docker ps
  ```
- [ ] Docker Compose 已安裝
  ```bash
  docker-compose --version
  ```
- [ ] Git 已安裝（如需從 Git 拉取代碼）
  ```bash
  git --version
  ```

### ☐ 網域設定
- [ ] 已擁有網域名稱
- [ ] DNS A 記錄已設定：`dashboard.yourdomain.com` → 伺服器 IP
- [ ] DNS A 記錄已設定：`api.yourdomain.com` → 伺服器 IP
- [ ] DNS 已傳播完成（可用 `nslookup` 或 `dig` 檢查）
  ```bash
  nslookup dashboard.yourdomain.com
  nslookup api.yourdomain.com
  ```

### ☐ 防火牆設定
- [ ] Port 80 (HTTP) 已開放
- [ ] Port 443 (HTTPS) 已開放
- [ ] Port 22 (SSH) 已開放（用於管理）
- [ ] 其他不必要的 Port 已關閉
  ```bash
  sudo ufw status
  ```

### ☐ 後端 API 準備
- [ ] 後端 API 的 Docker 映像檔已準備好
  - [ ] 選項 A：使用預先建置的映像檔
  - [ ] 選項 B：本地建置（需要 API 原始碼）
- [ ] 資料庫連接資訊已確認
- [ ] API 所需的環境變數已記錄

---

## 📝 部署步驟檢查

### ☐ 步驟 1：專案準備
- [ ] 專案已上傳到伺服器
  ```bash
  # 方法 1: SCP 上傳
  scp -r SmartCaterStreamlit user@server:/path/
  
  # 方法 2: Git clone
  git clone <repository-url>
  ```
- [ ] 已進入專案目錄
  ```bash
  cd SmartCaterStreamlit
  ```

### ☐ 步驟 2：環境變數配置
- [ ] 已複製環境變數範例檔案
  ```bash
  cp env.production.example .env.production
  ```
- [ ] 已編輯 `.env.production` 並填入以下資訊：
  - [ ] `DASHBOARD_DOMAIN` - 前端網域
  - [ ] `API_DOMAIN` - API 網域
  - [ ] `DATABASE_URL` - 資料庫連接字串
  - [ ] `SECRET_KEY` - JWT 密鑰（已生成強密碼）
  - [ ] `CERTBOT_EMAIL` - SSL 憑證通知信箱
  - [ ] 其他必要的環境變數

### ☐ 步驟 3：Nginx 配置
- [ ] 已更新 `nginx/conf.d/smartcater.conf` 中的網域名稱
  ```bash
  sed -i "s/dashboard\.yourdomain\.com/${DASHBOARD_DOMAIN}/g" nginx/conf.d/smartcater.conf
  sed -i "s/api\.yourdomain\.com/${API_DOMAIN}/g" nginx/conf.d/smartcater.conf
  ```
- [ ] Nginx 配置語法檢查通過
  ```bash
  docker run --rm -v $(pwd)/nginx:/etc/nginx nginx:1.25-alpine nginx -t
  ```

### ☐ 步驟 4：Docker Compose 配置
- [ ] 已檢查 `docker-compose.prod.yml` 配置
- [ ] API 服務的映像檔或建置路徑已正確設定
- [ ] 環境變數已正確對應
- [ ] 網路和 volumes 配置已確認

### ☐ 步驟 5：SSL 憑證申請
- [ ] 已創建 certbot 目錄
  ```bash
  mkdir -p certbot/conf certbot/www
  ```
- [ ] 已啟動 Nginx 用於 SSL 驗證
  ```bash
  docker-compose -f docker-compose.prod.yml up -d nginx
  ```
- [ ] Dashboard 網域的 SSL 憑證已成功申請
  ```bash
  docker run -it --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly --webroot \
    -w /var/www/certbot \
    -d dashboard.yourdomain.com \
    --email admin@yourdomain.com \
    --agree-tos
  ```
- [ ] API 網域的 SSL 憑證已成功申請
  ```bash
  docker run -it --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly --webroot \
    -w /var/www/certbot \
    -d api.yourdomain.com \
    --email admin@yourdomain.com \
    --agree-tos
  ```

### ☐ 步驟 6：服務部署
- [ ] Docker 映像檔已建置
  ```bash
  docker-compose -f docker-compose.prod.yml build
  ```
- [ ] 所有服務已啟動
  ```bash
  docker-compose -f docker-compose.prod.yml up -d
  ```
- [ ] 容器狀態正常（所有服務顯示 "Up"）
  ```bash
  docker-compose -f docker-compose.prod.yml ps
  ```

---

## 🔍 部署後驗證

### ☐ 健康檢查
- [ ] API 服務健康檢查通過
  ```bash
  curl https://api.yourdomain.com/health
  # 預期：200 OK
  ```
- [ ] Streamlit 服務健康檢查通過
  ```bash
  curl https://dashboard.yourdomain.com/_stcore/health
  # 預期：200 OK
  ```
- [ ] 所有容器健康狀態正常
  ```bash
  docker ps --format "table {{.Names}}\t{{.Status}}"
  ```

### ☐ 功能測試
- [ ] 可以透過瀏覽器訪問 `https://dashboard.yourdomain.com`
- [ ] Dashboard 頁面正常載入（無 SSL 警告）
- [ ] 可以成功登入系統
- [ ] Streamlit 互動功能正常（按鈕、滑桿等）
- [ ] API 端點可正常訪問 `https://api.yourdomain.com`
- [ ] 前端可以成功連接到後端 API
- [ ] WebSocket 連接正常（Streamlit 即時更新功能）

### ☐ SSL 驗證
- [ ] HTTPS 連接正常，無憑證警告
- [ ] 使用 SSL Labs 測試得分良好
  ```
  https://www.ssllabs.com/ssltest/analyze.html?d=dashboard.yourdomain.com
  ```
- [ ] HTTP 自動重定向到 HTTPS
  ```bash
  curl -I http://dashboard.yourdomain.com
  # 預期：301 或 302 重定向到 HTTPS
  ```

### ☐ 日誌檢查
- [ ] 沒有嚴重錯誤日誌
  ```bash
  docker-compose -f docker-compose.prod.yml logs --tail=50
  ```
- [ ] Nginx 訪問日誌正常記錄
  ```bash
  tail -f nginx/logs/access.log
  ```
- [ ] 應用日誌正常寫入
  ```bash
  tail -f logs/app_$(date +%Y-%m-%d).log
  ```

---

## 🔧 後續維護設定

### ☐ 自動化
- [ ] SSL 憑證自動更新已配置（certbot 容器運行中）
- [ ] 設定系統開機自動啟動 Docker 服務
  ```bash
  sudo systemctl enable docker
  ```
- [ ] 考慮設定自動重啟策略（已在 docker-compose.yml 中配置 `restart: always`）

### ☐ 監控
- [ ] 設定日誌輪替（logrotate）
- [ ] 設定磁碟空間監控
- [ ] 考慮使用監控工具（如 Prometheus + Grafana）

### ☐ 備份
- [ ] 設定定期備份計畫
  ```bash
  # 備份腳本範例
  tar -czf backup-$(date +%Y%m%d).tar.gz \
    logs/ nginx/ certbot/ .env.production settings.production.toml
  ```
- [ ] 測試備份還原流程

### ☐ 安全
- [ ] 修改預設的 SSH Port（選用）
- [ ] 設定 fail2ban 防止暴力破解（選用）
- [ ] 定期更新系統和 Docker 映像檔
- [ ] 確保敏感資訊（密碼、密鑰）已妥善保管

---

## 📊 效能優化（選用）

### ☐ 基礎優化
- [ ] 啟用 Nginx gzip 壓縮（已在配置中）
- [ ] 配置 Nginx 快取
- [ ] 設定合理的 Docker 資源限制

### ☐ 進階優化
- [ ] 使用 CDN 加速靜態資源
- [ ] 配置資料庫連接池
- [ ] 啟用 HTTP/2
- [ ] 考慮使用 Redis 快取

---

## 🆘 故障排除快速參考

### 問題：SSL 憑證申請失敗
```bash
# 檢查 DNS
nslookup dashboard.yourdomain.com

# 檢查 Port 80
curl http://dashboard.yourdomain.com/.well-known/acme-challenge/test

# 查看詳細日誌
docker-compose -f docker-compose.prod.yml logs certbot
```

### 問題：容器無法啟動
```bash
# 查看詳細日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 [service_name]

# 檢查配置
docker-compose -f docker-compose.prod.yml config

# 重新建置
docker-compose -f docker-compose.prod.yml up -d --build --force-recreate
```

### 問題：502 Bad Gateway
```bash
# 檢查後端服務狀態
docker-compose -f docker-compose.prod.yml ps

# 測試內部連接
docker-compose -f docker-compose.prod.yml exec nginx curl http://streamlit_app:8080

# 查看 Nginx 錯誤日誌
docker-compose -f docker-compose.prod.yml logs nginx
```

---

## ✅ 部署完成確認

當以上所有項目都完成並測試通過後，您的 SmartCater 系統已成功部署！

**最後檢查**：
- [ ] 所有服務運行正常
- [ ] HTTPS 訪問無誤
- [ ] 前後端通訊正常
- [ ] 日誌記錄正常
- [ ] 備份計畫已設定

**記錄重要資訊**：
- 伺服器 IP：`_________________`
- Dashboard URL：`_________________`
- API URL：`_________________`
- 部署日期：`_________________`
- 部署人員：`_________________`

---

## 📞 需要幫助？

參考完整文檔：`docs/SERVER_DEPLOYMENT.md`

**祝部署順利！** 🎉

