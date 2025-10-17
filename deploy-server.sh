#!/bin/bash

# ===================================
# SmartCater 自有伺服器部署腳本
# ===================================
# 此腳本用於在自有伺服器上部署完整的 SmartCater 系統
# 包含：Streamlit 前端、API 後端、Nginx 反向代理

set -e  # 遇到錯誤立即退出

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===================================
# 輔助函數
# ===================================
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ===================================
# 檢查前置條件
# ===================================
check_prerequisites() {
    print_header "檢查前置條件"
    
    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安裝！請先安裝 Docker。"
        exit 1
    fi
    print_success "Docker 已安裝: $(docker --version)"
    
    # 檢查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安裝！請先安裝 Docker Compose。"
        exit 1
    fi
    print_success "Docker Compose 已安裝"
    
    # 檢查環境變數檔案
    if [ ! -f .env.production ]; then
        print_warning ".env.production 檔案不存在"
        print_warning "請複製 .env.production.example 並填入實際值："
        print_warning "cp .env.production.example .env.production"
        read -p "是否現在創建？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.production.example .env.production
            print_success "已創建 .env.production，請編輯此檔案後再次執行此腳本"
            exit 0
        else
            exit 1
        fi
    fi
    print_success ".env.production 檔案存在"
}

# ===================================
# 載入環境變數
# ===================================
load_env() {
    print_header "載入環境變數"
    set -a
    source .env.production
    set +a
    print_success "環境變數已載入"
}

# ===================================
# 創建必要目錄
# ===================================
create_directories() {
    print_header "創建必要目錄"
    
    mkdir -p nginx/conf.d
    mkdir -p nginx/logs
    mkdir -p certbot/conf
    mkdir -p certbot/www
    mkdir -p logs
    mkdir -p api_logs
    
    print_success "目錄結構創建完成"
}

# ===================================
# 初次 SSL 憑證申請
# ===================================
request_ssl_certificates() {
    print_header "SSL 憑證配置"
    
    if [ -d "certbot/conf/live/${DASHBOARD_DOMAIN}" ] && [ -d "certbot/conf/live/${API_DOMAIN}" ]; then
        print_success "SSL 憑證已存在，跳過申請"
        return
    fi
    
    print_warning "需要申請 SSL 憑證"
    echo "請確認："
    echo "  1. 網域 ${DASHBOARD_DOMAIN} 和 ${API_DOMAIN} 已正確指向此伺服器"
    echo "  2. Port 80 和 443 已開放"
    echo ""
    read -p "是否繼續申請 SSL 憑證？(y/n) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "跳過 SSL 憑證申請，將使用 HTTP 模式部署"
        return
    fi
    
    # 先啟動 Nginx 用於驗證
    print_warning "啟動臨時 Nginx 服務用於 SSL 驗證..."
    docker-compose -f docker-compose.prod.yml up -d nginx
    sleep 5
    
    # 申請 dashboard 憑證
    print_warning "申請 ${DASHBOARD_DOMAIN} 的 SSL 憑證..."
    docker run -it --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly --webroot \
        -w /var/www/certbot \
        -d ${DASHBOARD_DOMAIN} \
        --email ${CERTBOT_EMAIL:-admin@${DASHBOARD_DOMAIN}} \
        --agree-tos \
        --no-eff-email
    
    # 申請 API 憑證
    print_warning "申請 ${API_DOMAIN} 的 SSL 憑證..."
    docker run -it --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly --webroot \
        -w /var/www/certbot \
        -d ${API_DOMAIN} \
        --email ${CERTBOT_EMAIL:-admin@${API_DOMAIN}} \
        --agree-tos \
        --no-eff-email
    
    print_success "SSL 憑證申請完成"
}

# ===================================
# 部署服務
# ===================================
deploy_services() {
    print_header "部署服務"
    
    # 更新 Nginx 配置中的網域名稱
    print_warning "更新 Nginx 配置..."
    sed -i.bak "s/dashboard\.yourdomain\.com/${DASHBOARD_DOMAIN}/g" nginx/conf.d/smartcater.conf
    sed -i.bak "s/api\.yourdomain\.com/${API_DOMAIN}/g" nginx/conf.d/smartcater.conf
    
    # 建置並啟動所有服務
    print_warning "建置 Docker 映像..."
    docker-compose -f docker-compose.prod.yml build
    
    print_warning "啟動所有服務..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "服務部署完成"
}

# ===================================
# 健康檢查
# ===================================
health_check() {
    print_header "服務健康檢查"
    
    echo "等待服務啟動..."
    sleep 10
    
    # 檢查容器狀態
    echo ""
    echo "容器狀態："
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "檢查服務健康狀態（可能需要等待 30-60 秒）..."
    
    # 檢查 API 健康
    if docker-compose -f docker-compose.prod.yml exec -T smartcater_api curl -f http://localhost:8000/health &> /dev/null; then
        print_success "API 服務健康"
    else
        print_warning "API 服務尚未就緒，請稍後手動檢查"
    fi
    
    # 檢查 Streamlit 健康
    if docker-compose -f docker-compose.prod.yml exec -T streamlit_app curl -f http://localhost:8080/_stcore/health &> /dev/null; then
        print_success "Streamlit 服務健康"
    else
        print_warning "Streamlit 服務尚未就緒，請稍後手動檢查"
    fi
}

# ===================================
# 顯示部署資訊
# ===================================
show_deployment_info() {
    print_header "部署完成"
    
    echo ""
    echo -e "${GREEN}🎉 SmartCater 系統部署成功！${NC}"
    echo ""
    echo "服務訪問地址："
    echo -e "  📊 儀表板: ${BLUE}https://${DASHBOARD_DOMAIN}${NC}"
    echo -e "  🔌 API:    ${BLUE}https://${API_DOMAIN}${NC}"
    echo ""
    echo "常用管理命令："
    echo "  查看日誌:    docker-compose -f docker-compose.prod.yml logs -f"
    echo "  查看狀態:    docker-compose -f docker-compose.prod.yml ps"
    echo "  重啟服務:    docker-compose -f docker-compose.prod.yml restart"
    echo "  停止服務:    docker-compose -f docker-compose.prod.yml down"
    echo "  更新服務:    ./deploy-server.sh"
    echo ""
    echo "SSL 憑證會自動每 12 小時檢查更新"
    echo ""
}

# ===================================
# 主流程
# ===================================
main() {
    clear
    print_header "SmartCater 自有伺服器部署"
    echo ""
    echo "此腳本將部署以下服務："
    echo "  • 後端 API (smartcater_api)"
    echo "  • Streamlit 前端 (streamlit_app)"
    echo "  • Nginx 反向代理"
    echo "  • SSL 憑證自動更新 (certbot)"
    echo ""
    
    check_prerequisites
    load_env
    create_directories
    request_ssl_certificates
    deploy_services
    health_check
    show_deployment_info
}

# 執行主流程
main

