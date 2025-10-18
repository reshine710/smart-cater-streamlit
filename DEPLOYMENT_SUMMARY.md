# 📋 SmartCater 前端部署總結

## 🎯 配置變更總結

根據您的後端架構，前端配置已完全重構以實現正確整合。

---

## ✅ 主要變更

### 1. **移除了獨立的 Nginx 和 Certbot**

**原因**：後端已有 Nginx，前端不需要重複

**變更**：
- ❌ 移除 `nginx` 服務
- ❌ 移除 `certbot` 服務  
- ✅ 僅保留 `streamlit_app` 服務

### 2. **移除了 API 服務定義**

**原因**：後端已經有 `smartcater_api` 容器

**變更**：
- ❌ 移除 `smartcater_api` 服務定義
- ✅ Streamlit 直接連接後端的 API 容器

### 3. **使用外部網路**

**原因**：需要加入後端的 `smartcater_network`

**變更前**：
```yaml
networks:
  app-network:
    driver: bridge
```

**變更後**：
```yaml
networks:
  smartcater_network:
    external: true
    name: smartcater_network
```

### 4. **更新容器名稱**

**原因**：與後端命名規範保持一致

**變更**：
- `smartcater-streamlit` → `smartcater_streamlit` (下劃線)

### 5. **配置 MQTT 連接**

**原因**：前端需要連接後端的 EMQX

**新增配置**：
```yaml
- MQTT_BROKER_HOST=smartcater_emqx
- MQTT_BROKER_PORT=1883
- MQTT_USE_TLS=false
```

---

## 🏗️ 最終架構

```
外部流量
   ↓
後端 Nginx (Port 80/443)
   ├─→ API: smartcater_api:8000
   └─→ Dashboard: smartcater_streamlit:8080
           ↓
       [共享資源]
       - PostgreSQL (smartcater_postgres)
       - EMQX (smartcater_emqx)
```

---

## 📁 文件結構

### 已創建/更新的文件

```
SmartCaterStreamlit/
├── docker-compose.prod.yml              ← 🔄 已重構
├── nginx-backend-config/
│   └── dashboard.conf                   ← ✨ 新增（供後端使用）
├── docs/
│   ├── INTEGRATED_DEPLOYMENT.md         ← ✨ 新增
│   ├── SERVER_DEPLOYMENT.md             ← 原有（獨立部署，現已不適用）
│   ├── LOCAL_TESTING.md                 ← 原有
│   └── API_CONNECTION_GUIDE.md          ← 原有
├── DEPLOYMENT_SUMMARY.md                ← ✨ 新增（本文件）
└── deploy-server.sh                     ← ⚠️ 需要更新
```

---

## 🚀 部署流程

### 準備階段

1. **確認後端運行**
   ```bash
   docker ps | grep smartcater
   # 應看到：nginx, api, postgres, emqx
   ```

2. **檢查網路**
   ```bash
   docker network ls | grep smartcater_network
   ```

### 後端配置

3. **添加 Dashboard Nginx 配置**
   ```bash
   # 複製配置到後端專案
   cp nginx-backend-config/dashboard.conf /path/to/backend/nginx/
   
   # 修改網域
   sed -i 's/yourdomain.com/actual-domain.com/g' /path/to/backend/nginx/dashboard.conf
   ```

4. **更新後端 docker-compose.yml**
   ```yaml
   services:
     nginx:
       volumes:
         - ./nginx/dashboard.conf:/etc/nginx/conf.d/dashboard.conf:ro
   ```

5. **重新載入後端 Nginx**
   ```bash
   cd /path/to/backend
   docker-compose exec nginx nginx -s reload
   ```

6. **申請 SSL 憑證**
   ```bash
   docker run --rm \
     -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
     -v "$(pwd)/certbot/www:/var/www/certbot" \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot \
     -d dashboard.your-domain.com \
     --email admin@your-domain.com \
     --agree-tos
   ```

### 前端部署

7. **部署 Streamlit**
   ```bash
   cd /path/to/SmartCaterStreamlit
   
   # 建置
   docker-compose -f docker-compose.prod.yml build
   
   # 啟動
   docker-compose -f docker-compose.prod.yml up -d
   ```

8. **驗證部署**
   ```bash
   # 檢查容器
   docker ps | grep streamlit
   
   # 測試連接
   docker exec smartcater_streamlit curl http://smartcater_api:8000/health
   
   # 瀏覽器測試
   # https://dashboard.your-domain.com
   ```

---

## 🔗 網域配置

### DNS 設定

```
A Record:
dashboard.your-domain.com  →  伺服器 IP
```

### SSL 憑證

```bash
# 憑證位置（在後端專案）
/path/to/backend/certbot/conf/live/dashboard.your-domain.com/
├── fullchain.pem
└── privkey.pem
```

---

## ✅ 檢查清單

### 部署前

- [ ] 後端服務全部運行中
- [ ] `smartcater_network` 網路存在
- [ ] DNS 已設定並傳播完成
- [ ] 後端 Nginx 已添加 dashboard 配置
- [ ] SSL 憑證已申請

### 部署後

- [ ] Streamlit 容器運行中
- [ ] 健康檢查通過
- [ ] 可從容器訪問 API
- [ ] 可從容器訪問 MQTT
- [ ] HTTPS 訪問正常
- [ ] 登入功能正常
- [ ] WebSocket 功能正常

---

## 🔧 常用命令

```bash
# 查看所有 SmartCater 容器
docker ps --filter "name=smartcater"

# 查看前端日誌
docker-compose -f docker-compose.prod.yml logs -f

# 重啟前端
docker-compose -f docker-compose.prod.yml restart

# 更新前端
docker-compose -f docker-compose.prod.yml up -d --build

# 停止前端
docker-compose -f docker-compose.prod.yml down

# 測試 API 連接
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 測試 MQTT 連接
docker exec smartcater_streamlit ping smartcater_emqx
```

---

## 📊 配置對比

### 獨立部署 vs 整合部署

| 項目 | 獨立部署（舊） | 整合部署（新）✅ |
|------|--------------|-----------------|
| **Nginx** | 前端自己的 | 使用後端的 |
| **網路** | app-network | smartcater_network (外部) |
| **SSL** | 前端自己管理 | 後端統一管理 |
| **API** | 需要定義 | 使用後端的 |
| **MQTT** | 可選 | 使用後端的 |
| **端口** | 80, 443 對外 | 無需對外開放 |
| **複雜度** | 高 | 低 |

---

## 🆘 故障排除

### 網路問題

```bash
# 問題：network not found
# 解決：檢查網路名稱是否正確
docker network ls
docker network inspect smartcater_network
```

### API 連接問題

```bash
# 問題：無法連接 API
# 解決：檢查容器名稱
docker ps --filter "name=api"
docker exec smartcater_streamlit ping smartcater_api
```

### Nginx 502 錯誤

```bash
# 問題：502 Bad Gateway
# 解決：檢查 Streamlit 容器和 Nginx 配置
docker ps | grep streamlit
docker exec smartcater_nginx nginx -t
docker logs smartcater_nginx --tail=50
```

---

## 📚 詳細文檔

- **整合部署完整指南**: `docs/INTEGRATED_DEPLOYMENT.md`
- **本地測試**: `docs/LOCAL_TESTING.md`
- **API 連接配置**: `docs/API_CONNECTION_GUIDE.md`

---

## 🎯 下一步

1. **完成部署**
   - 按照本文檔的步驟執行
   - 使用檢查清單確保每一步都完成

2. **測試功能**
   - 登入系統
   - 測試所有功能模組
   - 驗證 MQTT 連接

3. **設定監控**（可選）
   - 日誌聚合
   - 健康檢查
   - 效能監控

---

**重要提醒**: 

- ⚠️ `deploy-server.sh` 腳本是為獨立部署設計的，不適用於整合部署
- ✅ 請參考 `docs/INTEGRATED_DEPLOYMENT.md` 進行整合部署
- 💡 如有疑問，請查看詳細文檔或運行診斷腳本

---

**部署完成後訪問**: `https://dashboard.your-domain.com` 🎉

