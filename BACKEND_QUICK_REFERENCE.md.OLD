# 🚀 後端工程師快速參考

## Nginx 配置 - 30 秒快速指南

---

## ✅ 快速完成（4 步驟）

### 1. 添加配置文件

```bash
cp /path/to/SmartCaterStreamlit/nginx-backend-config/dashboard.conf ./nginx/
```

### 2. 更新 docker-compose.yml

在 nginx 服務的 volumes 中添加：
```yaml
- ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro
```

### 3. 申請 SSL 憑證

```bash
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d dashboard.sihai.baimeng.co \
  --email admin@sihai.baimeng.co \
  --agree-tos
```

### 4. 重新載入 Nginx

```bash
docker-compose exec nginx nginx -t
docker-compose exec nginx nginx -s reload
```

---

## 🔍 驗證配置

```bash
# 測試訪問
curl -I https://dashboard.sihai.baimeng.co

# 應該返回：HTTP/2 200
```

---

## 📋 完整說明

詳見：**BACKEND_NGINX_SETUP.md**

---

## 🆘 遇到問題？

### 常見問題快速解決

**502 錯誤**：前端容器未啟動
```bash
docker ps | grep smartcater_streamlit
```

**配置錯誤**：檢查語法
```bash
docker-compose exec nginx nginx -t
```

**憑證問題**：檢查 DNS
```bash
nslookup dashboard.sihai.baimeng.co
```

---

## 📞 聯絡

完整文檔：**BACKEND_NGINX_SETUP.md**

