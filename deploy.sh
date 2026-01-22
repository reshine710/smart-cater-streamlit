#!/bin/bash

# Cloud Run 部署腳本
# 使用前請先設定以下環境變數：
# - PROJECT_ID: GCP 專案 ID
# - REGION: 部署區域
# - SERVICE_NAME: 服務名稱

set -e

# 預設值
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"asia-east1"}
SERVICE_NAME=${SERVICE_NAME:-"smartcater-streamlit"}
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 開始部署 SmartCater Streamlit 到 Cloud Run"
echo "專案 ID: ${PROJECT_ID}"
echo "區域: ${REGION}"
echo "服務名稱: ${SERVICE_NAME}"
echo "映像名稱: ${IMAGE_NAME}"

# 建置 Docker 映像
echo "📦 建置 Docker 映像..."
docker build -t ${IMAGE_NAME} .

# 推送映像到 Google Container Registry
echo "⬆️ 推送映像到 GCR..."
docker push ${IMAGE_NAME}

# 部署到 Cloud Run
echo "🚀 部署到 Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --set-env-vars "ENV_FOR_DYNACONF=production" \
    --set-env-vars "DYNACONF_API_URL=${DYNACONF_API_URL}" \


echo "✅ 部署完成！"
echo "服務 URL: https://${SERVICE_NAME}-${PROJECT_ID}.${REGION}.run.app"
