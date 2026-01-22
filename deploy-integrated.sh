#!/bin/bash

# ===================================
# SmartCater 前端整合部署腳本
# ===================================
# 此腳本用於將 Streamlit 前端整合到已部署的後端系統中

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
        print_error "Docker 未安裝！"
        exit 1
    fi
    print_success "Docker 已安裝"
    
    # 檢查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安裝！"
        exit 1
    fi
    print_success "Docker Compose 已安裝"
    
    # 檢查後端容器
    print_warning "檢查後端服務..."
    
    required_containers=("smartcater_nginx" "smartcater_api" "smartcater_postgres")
    for container in "${required_containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            print_success "容器 ${container} 正在運行"
        else
            print_warning "容器 ${container} 未運行"
            print_warning "請確保後端服務已完全啟動"
        fi
    done
    
    # 檢查網路
    print_warning "檢查 Docker 網路..."
    if docker network ls | grep -q "smartcater_network"; then
        print_success "smartcater_network 網路存在"
    else
        print_error "smartcater_network 網路不存在！"
        print_warning "請先啟動後端服務，或手動創建網路："
        print_warning "docker network create smartcater_network --subnet 172.28.0.0/16"
        exit 1
    fi
}

# ===================================
# 檢查 Nginx 配置
# ===================================
check_nginx_config() {
    print_header "檢查 Nginx 配置"
    
    echo "請確認以下事項："
    echo "  1. 後端 Nginx 已添加 dashboard.conf 配置"
    echo "  2. Nginx 配置已重新載入"
    echo "  3. SSL 憑證已申請（如使用 HTTPS）"
    echo ""
    echo "需要的配置文件位於："
    echo "  nginx-backend-config/dashboard.conf"
    echo ""
    
    read -p "是否已完成上述配置？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "請先完成後端 Nginx 配置"
        print_warning "詳細步驟請查看："
        print_warning "  docs/INTEGRATED_DEPLOYMENT.md"
        print_warning "  DEPLOYMENT_SUMMARY.md"
        exit 1
    fi
}

# ===================================
# 建置映像檔
# ===================================
build_image() {
    print_header "建置 Docker 映像檔"
    
    print_warning "建置 Streamlit 映像檔..."
    docker-compose -f docker-compose.prod.yml build
    
    print_success "映像檔建置完成"
}

# ===================================
# 部署服務
# ===================================
deploy_service() {
    print_header "部署 Streamlit 服務"
    
    print_warning "啟動 Streamlit 容器..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "Streamlit 服務已啟動"
}

# ===================================
# 等待服務就緒
# ===================================
wait_for_service() {
    print_header "等待服務就緒"
    
    echo "等待容器啟動..."
    sleep 10
    
    # 檢查容器狀態
    print_warning "檢查容器狀態..."
    docker-compose -f docker-compose.prod.yml ps
    
    # 等待健康檢查
    echo ""
    print_warning "等待健康檢查通過（最多等待 60 秒）..."
    
    for i in {1..12}; do
        if docker exec smartcater_streamlit curl -sf http://localhost:8080/_stcore/health &> /dev/null; then
            print_success "Streamlit 服務健康檢查通過"
            break
        fi
        
        if [ $i -eq 12 ]; then
            print_warning "健康檢查未通過，但服務可能仍在啟動中"
            print_warning "請檢查日誌：docker-compose -f docker-compose.prod.yml logs"
        else
            echo -n "."
            sleep 5
        fi
    done
}

# ===================================
# 測試連接
# ===================================
test_connections() {
    print_header "測試服務連接"
    
    echo ""
    
    # 測試 API 連接
    print_warning "測試 API 連接..."
    if docker exec smartcater_streamlit curl -sf http://smartcater_api:8000/health &> /dev/null; then
        print_success "API 連接正常"
    else
        print_warning "API 連接失敗"
        print_warning "請檢查後端 API 服務是否運行"
    fi
    

    
    # 測試網路連接
    echo ""
    print_warning "網路連接測試完成"
}

# ===================================
# 顯示部署資訊
# ===================================
show_info() {
    print_header "部署完成"
    
    echo ""
    echo -e "${GREEN}🎉 Streamlit 前端部署成功！${NC}"
    echo ""
    echo "服務資訊："
    echo -e "  容器名稱: ${BLUE}smartcater_streamlit${NC}"
    echo -e "  內部端口: ${BLUE}8080${NC}"
    echo -e "  網路: ${BLUE}smartcater_network${NC}"
    echo ""
    echo "訪問地址："
    echo -e "  📊 Dashboard: ${BLUE}https://dashboard.<your-domain>${NC}"
    echo ""
    echo "常用命令："
    echo "  查看日誌:    docker-compose -f docker-compose.prod.yml logs -f"
    echo "  查看狀態:    docker-compose -f docker-compose.prod.yml ps"
    echo "  重啟服務:    docker-compose -f docker-compose.prod.yml restart"
    echo "  停止服務:    docker-compose -f docker-compose.prod.yml down"
    echo "  更新服務:    docker-compose -f docker-compose.prod.yml up -d --build"
    echo ""
    echo "測試命令："
    echo "  API 連接:    docker exec smartcater_streamlit curl http://smartcater_api:8000/health"

    echo "  健康檢查:    docker exec smartcater_streamlit curl http://localhost:8080/_stcore/health"
    echo ""
    echo "文檔："
    echo "  完整部署指南: docs/INTEGRATED_DEPLOYMENT.md"
    echo "  部署總結:     DEPLOYMENT_SUMMARY.md"
    echo ""
    
    # 詢問是否查看日誌
    read -p "是否要查看即時日誌？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "按 Ctrl+C 停止查看日誌"
        sleep 2
        docker-compose -f docker-compose.prod.yml logs -f
    fi
}

# ===================================
# 主流程
# ===================================
main() {
    clear
    print_header "SmartCater 前端整合部署"
    echo ""
    echo "此腳本將 Streamlit 前端整合到已部署的後端系統中"
    echo ""
    echo "前置要求："
    echo "  ✓ 後端服務已部署並運行"
    echo "  ✓ 後端 Nginx 已添加 dashboard 配置"
    echo "  ✓ DNS 已設定（如需對外訪問）"
    echo "  ✓ SSL 憑證已申請（如使用 HTTPS）"
    echo ""
    
    read -p "是否繼續？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "部署已取消"
        exit 0
    fi
    
    check_prerequisites
    check_nginx_config
    build_image
    deploy_service
    wait_for_service
    test_connections
    show_info
}

# 執行主流程
main

