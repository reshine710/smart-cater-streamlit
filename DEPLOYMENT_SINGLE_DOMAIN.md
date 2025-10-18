# 🚀 單一網域部署指南

## sihai.baimeng.co 部署方案

---

## 📋 部署架構

```
https://sihai.baimeng.co/          → Streamlit 前端
https://sihai.baimeng.co/api/v1/   → 後端 API
```

**特點**:
- ✅ 單一 SSL 憑證
- ✅ 單一網域名稱
- ✅ 透過路徑區分前後端

---

## 🎯 前端配置（已完成）

### 1. docker-compose.prod.yml
```yaml
environment:
  - DYNACONF_API_URL=/api/v1  # 使用相對路徑
```

### 2. 部署前端
```bash
cd /path/to/SmartCaterStreamlit
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔧 後端配置（需要後端工程師執行）

### 關鍵變更
在後端 Nginx 配置中添加路由規則，完整配置見：
`BACKEND_CHANGES_REQUIRED.md`

### 快速步驟
```bash
# 1. 複製配置
cp /path/to/SmartCaterStreamlit/nginx-backend-config/sihai-single-domain.conf \
   ./nginx/

# 2. 更新 docker-compose.yml
# 添加 volume: ./nginx/sihai-single-domain.conf:/etc/nginx/conf.d/sihai.conf:ro

# 3. 重新載入
docker-compose exec nginx nginx -t
docker-compose exec nginx nginx -s reload
```

---

## ✅ 驗證

```bash
# 前端
curl -I https://sihai.baimeng.co/

# API
curl https://sihai.baimeng.co/health
curl https://sihai.baimeng.co/api/v1/
```

---

## 📚 相關文檔

- **BACKEND_CHANGES_REQUIRED.md** - 後端變更詳情
- **nginx-backend-config/sihai-single-domain.conf** - 完整 Nginx 配置

