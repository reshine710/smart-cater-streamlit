# 📚 SmartCater 前端部署文檔總覽

## 當前部署方案：單一網域

---

## 🎯 快速開始

### 網域配置
```
主網域: sihai.baimeng.co
前端:   https://sihai.baimeng.co/
API:    https://sihai.baimeng.co/api/v1/
```

### 部署步驟

1. **前端部署**（本專案）
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **後端配置**（需要後端工程師執行）
   - 參考：`BACKEND_CHANGES_REQUIRED.md`
   - 配置：`nginx-backend-config/sihai-single-domain.conf`

---

## 📖 文檔導航

### 主要文檔

| 文檔 | 說明 | 對象 |
|------|------|------|
| **BACKEND_CHANGES_REQUIRED.md** | 後端 Nginx 配置變更 | 後端工程師 |
| **DEPLOYMENT_SINGLE_DOMAIN.md** | 單一網域部署指南 | 所有人 |
| **docker-compose.prod.yml** | 前端部署配置 | DevOps |

### 配置文件

| 文件 | 說明 |
|------|------|
| `nginx-backend-config/sihai-single-domain.conf` | Nginx 完整配置（單一網域） |
| `docker-compose.prod.yml` | 前端 Docker Compose 配置 |

### 其他文檔

| 文檔 | 說明 |
|------|------|
| `DEPLOYMENT_GUIDE_sihai.md` | 原子網域方案（已棄用） |
| `docs/LOCAL_TESTING.md` | 本地測試指南 |
| `docs/API_CONNECTION_GUIDE.md` | API 連接配置說明 |

---

## 🚀 部署流程

### 前端（本專案）

```bash
# 1. 確認配置
cat docker-compose.prod.yml | grep DYNACONF_API_URL
# 應顯示: DYNACONF_API_URL=/api/v1

# 2. 部署
docker-compose -f docker-compose.prod.yml up -d

# 3. 驗證
docker ps | grep smartcater_streamlit
docker logs smartcater_streamlit
```

### 後端（需協調）

後端工程師需要：
1. 添加 Nginx 路由配置
2. 重新載入 Nginx

詳見：`BACKEND_CHANGES_REQUIRED.md`

---

## ✅ 驗證清單

### 前端驗證
- [ ] 容器運行中：`docker ps | grep smartcater_streamlit`
- [ ] 健康檢查通過：`docker exec smartcater_streamlit curl http://localhost:8080/_stcore/health`
- [ ] API 連接正常（容器內部）：`docker exec smartcater_streamlit curl http://smartcater_api:8000/health`

### 後端驗證
- [ ] Nginx 配置正確
- [ ] 可訪問前端：`https://sihai.baimeng.co/`
- [ ] 可訪問 API：`https://sihai.baimeng.co/api/v1/`
- [ ] 前端可成功登入

---

## 🔧 故障排除

### 問題：前端無法連接 API

**檢查**：
```bash
# 1. 確認 API URL 配置
docker exec smartcater_streamlit env | grep API_URL

# 2. 測試內部連接
docker exec smartcater_streamlit curl http://smartcater_api:8000/health

# 3. 檢查網路
docker network inspect smartcater_network | grep smartcater
```

### 問題：外部無法訪問

**檢查**：
```bash
# 後端 Nginx 配置
docker exec smartcater_nginx cat /etc/nginx/conf.d/sihai.conf

# Nginx 日誌
docker logs smartcater_nginx --tail=50
```

---

## 📞 支援

- **前端問題**：查看本專案文檔
- **後端配置**：聯絡後端工程師，參考 `BACKEND_CHANGES_REQUIRED.md`
- **本地測試**：參考 `docs/LOCAL_TESTING.md`

---

## 🗂️ 檔案結構

```
SmartCaterStreamlit/
├── docker-compose.prod.yml              ← 前端部署配置
├── BACKEND_CHANGES_REQUIRED.md          ← 後端變更說明
├── DEPLOYMENT_SINGLE_DOMAIN.md          ← 部署指南
├── README_DEPLOYMENT_FINAL.md           ← 本文件
├── nginx-backend-config/
│   └── sihai-single-domain.conf        ← 後端 Nginx 配置
└── docs/
    ├── LOCAL_TESTING.md                ← 本地測試
    └── API_CONNECTION_GUIDE.md         ← API 配置
```

---

**部署方案**: 單一網域 `sihai.baimeng.co` ✅  
**文檔版本**: v2.0 (2025-10-18)

