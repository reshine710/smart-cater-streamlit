# 🚀 Cloud Run 部署指南

## 前置需求

### 1. GCP 環境設定
```bash
# 安裝 Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# 登入並設定專案
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-east1

# 啟用必要的 API
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. 環境變數設定
在部署前，請設定以下環境變數：

```bash
# GCP 專案設定
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-east1"
export SERVICE_NAME="smartcater-streamlit"

# API 配置
export DYNACONF_API_URL="https://your-api-url.com/api/v1"

# MQTT 配置（如果需要）
export MQTT_BROKER_HOST="your-mqtt-broker.com"
export MQTT_BROKER_PORT="8883"
export MQTT_USERNAME="your-mqtt-username"
export MQTT_PASSWORD="your-mqtt-password"
export MQTT_CLIENT_ID="smartcater_cloud_frontend"
```

## 部署步驟

### 方法一：使用部署腳本（推薦）
```bash
# 設定環境變數後執行
./deploy.sh
```

### 方法二：手動部署
```bash
# 1. 建置映像
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME} .

# 2. 推送映像
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}

# 3. 部署到 Cloud Run
gcloud run deploy ${SERVICE_NAME} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --set-env-vars "ENV_FOR_DYNACONF=production" \
    --set-env-vars "DYNACONF_API_URL=${DYNACONF_API_URL}"
```

## 配置說明

### Dockerfile 特點
- 使用 Python 3.12-slim 基礎映像
- 設定 Streamlit 在 8080 端口運行
- 包含健康檢查
- 優化的多階段建置

### 環境變數
- `ENV_FOR_DYNACONF=production`: 使用生產環境配置
- `DYNACONF_API_URL`: 後端 API 的 URL
- MQTT 相關變數（如果使用 MQTT 功能）

### 資源配置
- 記憶體：1GB
- CPU：1 核心
- 最大實例數：10
- 端口：8080

## 監控和日誌

### 查看日誌
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" --limit 50
```

### 監控指標
在 GCP Console 的 Cloud Run 頁面可以查看：
- 請求數
- 延遲時間
- 錯誤率
- 實例數

## 故障排除

### 常見問題

1. **映像建置失敗**
   - 檢查 Dockerfile 語法
   - 確認所有依賴都在 requirements.txt 中

2. **部署失敗**
   - 檢查 GCP 權限
   - 確認 API 已啟用
   - 檢查環境變數設定

3. **應用程式無法啟動**
   - 檢查日誌：`gcloud logging read`
   - 確認端口設定為 8080
   - 檢查環境變數是否正確

4. **API 連接失敗**
   - 確認 `DYNACONF_API_URL` 設定正確
   - 檢查網路連通性
   - 確認 API 服務正常運行

## 安全建議

1. **使用 Secret Manager**
   ```bash
   # 建立密鑰
   gcloud secrets create mqtt-password --data-file=- <<< "your-password"
   
   # 在部署時使用
   --set-secrets "MQTT_PASSWORD=mqtt-password:latest"
   ```

2. **設定 IAM 權限**
   - 限制 Cloud Run 服務的存取權限
   - 使用最小權限原則

3. **啟用 HTTPS**
   - Cloud Run 預設提供 HTTPS
   - 可以設定自訂網域

## 成本優化

1. **設定最小實例數**
   ```bash
   --min-instances 0  # 冷啟動，節省成本
   --max-instances 10 # 限制最大實例數
   ```

2. **使用預分配實例**
   ```bash
   --min-instances 1  # 保持一個實例運行，減少冷啟動
   ```

3. **監控使用量**
   - 定期檢查 Cloud Run 使用量
   - 根據實際需求調整資源配置
