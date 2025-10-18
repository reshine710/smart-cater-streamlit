# 後端 Nginx 配置變更 - 單一網域方案

## 📋 變更概述

**原方案**: 使用子網域 `dashboard.sihai.baimeng.co`  
**新方案**: 使用單一網域 `sihai.baimeng.co`，透過路徑區分前後端

- 前端: `https://sihai.baimeng.co/`
- API: `https://sihai.baimeng.co/api/v1/`

---

## 🔧 需要的變更

### 1. 替換 Nginx 配置文件

**位置**: `nginx/` 目錄

**操作**:
```bash
# 使用新的配置文件
cp /path/to/SmartCaterStreamlit/nginx-backend-config/sihai-single-domain.conf \
   ./nginx/sihai.conf
```

**或直接編輯現有的 `nginx/nginx.conf`**，添加以下路由規則：

```nginx
# API 路由 (優先匹配)
location /api/ {
    proxy_pass http://smartcater_api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 前端路由 (根路徑)
location / {
    proxy_pass http://smartcater_streamlit:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支援
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    proxy_buffering off;
}
```

### 2. 更新 docker-compose.yml (如需要)

如果使用新的配置文件，在 nginx 服務中添加：

```yaml
services:
  nginx:
    volumes:
      - ./nginx/sihai.conf:/etc/nginx/conf.d/sihai.conf:ro
```

### 3. 重新載入 Nginx

```bash
# 測試配置
docker-compose exec nginx nginx -t

# 重新載入
docker-compose exec nginx nginx -s reload
```

---

## ✅ 驗證

```bash
# 測試前端
curl -I https://sihai.baimeng.co/

# 測試 API
curl -I https://sihai.baimeng.co/api/v1/
curl https://sihai.baimeng.co/health
```

---

## 📌 重點說明

1. **路由優先順序**: `/api/` 必須在 `/` 之前配置
2. **SSL 憑證**: 使用主網域 `sihai.baimeng.co` 的憑證
3. **WebSocket**: 僅前端路由需要 WebSocket 配置
4. **無需新憑證**: 使用現有的主網域憑證即可

---

完整配置文件已提供於: `nginx-backend-config/sihai-single-domain.conf`

