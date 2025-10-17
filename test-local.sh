#!/bin/bash

# ===================================
# SmartCater 本地測試腳本
# ===================================
# 用於在本地開發環境測試部署架構

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
        print_error "Docker 未安裝！請先安裝 Docker Desktop。"
        exit 1
    fi
    print_success "Docker 已安裝: $(docker --version)"
    
    # 檢查 Docker 是否運行
    if ! docker info &> /dev/null; then
        print_error "Docker 未運行！請啟動 Docker Desktop。"
        exit 1
    fi
    print_success "Docker 正在運行"
    
    # 檢查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安裝！"
        exit 1
    fi
    print_success "Docker Compose 已安裝"
    
    # 檢查後端 API
    print_warning "檢查後端 API..."
    if curl -sf http://localhost:8000/health &> /dev/null; then
        print_success "後端 API 正在運行（http://localhost:8000）"
    else
        print_warning "後端 API 無法訪問"
        print_warning "請確保您的後端 API 在 http://localhost:8000 上運行"
        echo ""
        read -p "是否繼續？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# ===================================
# 停止現有服務
# ===================================
stop_existing_services() {
    print_header "清理現有服務"
    
    if docker-compose -f docker-compose.local.yml ps -q 2>/dev/null | grep -q .; then
        print_warning "停止現有的本地測試服務..."
        docker-compose -f docker-compose.local.yml down
        print_success "現有服務已停止"
    else
        print_success "沒有需要停止的服務"
    fi
}

# ===================================
# 啟動服務
# ===================================
start_services() {
    print_header "啟動本地測試服務"
    
    print_warning "建置 Docker 映像..."
    docker-compose -f docker-compose.local.yml build
    
    print_warning "啟動服務..."
    docker-compose -f docker-compose.local.yml up -d
    
    print_success "服務已啟動"
}

# ===================================
# 等待服務就緒
# ===================================
wait_for_services() {
    print_header "等待服務就緒"
    
    echo "等待容器啟動..."
    sleep 10
    
    # 檢查容器狀態
    print_warning "檢查容器狀態..."
    docker-compose -f docker-compose.local.yml ps
    
    # 等待 Streamlit 健康檢查
    echo ""
    print_warning "等待 Streamlit 服務就緒（最多等待 60 秒）..."
    
    for i in {1..12}; do
        if curl -sf http://localhost:8502/_stcore/health &> /dev/null; then
            print_success "Streamlit 服務已就緒"
            break
        fi
        
        if [ $i -eq 12 ]; then
            print_warning "Streamlit 服務尚未就緒，但我們可以繼續"
            print_warning "您可以手動檢查日誌：docker-compose -f docker-compose.local.yml logs"
        else
            echo -n "."
            sleep 5
        fi
    done
}

# ===================================
# 健康檢查
# ===================================
health_check() {
    print_header "服務健康檢查"
    
    echo ""
    echo "測試服務訪問..."
    echo ""
    
    # 測試直接訪問 Streamlit
    if curl -sf http://localhost:8502/_stcore/health &> /dev/null; then
        print_success "直接訪問 Streamlit: http://localhost:8502"
    else
        print_error "無法訪問 Streamlit (直接)"
    fi
    
    # 測試通過 Nginx 訪問
    if curl -sf http://localhost:8501 &> /dev/null; then
        print_success "通過 Nginx 訪問: http://localhost:8501"
    else
        print_warning "無法通過 Nginx 訪問（可能還在啟動中）"
    fi
    
    # 測試容器內 API 連接
    echo ""
    print_warning "測試容器內 API 連接..."
    if docker-compose -f docker-compose.local.yml exec -T streamlit_app curl -sf http://host.docker.internal:8000/health &> /dev/null; then
        print_success "容器可以訪問後端 API"
    else
        print_warning "容器無法訪問後端 API"
        print_warning "請確保後端 API 在運行並且可以從 Docker 訪問"
    fi
}

# ===================================
# 顯示訪問資訊
# ===================================
show_info() {
    print_header "本地測試環境已就緒"
    
    echo ""
    echo -e "${GREEN}🎉 本地測試環境啟動成功！${NC}"
    echo ""
    echo "訪問方式："
    echo -e "  🌐 通過 Nginx (推薦):  ${BLUE}http://localhost:8501${NC}"
    echo -e "  🔗 直接訪問 Streamlit: ${BLUE}http://localhost:8502${NC}"
    echo -e "  🔌 後端 API:          ${BLUE}http://localhost:8000${NC}"
    echo ""
    echo "常用命令："
    echo "  查看日誌:    docker-compose -f docker-compose.local.yml logs -f"
    echo "  查看狀態:    docker-compose -f docker-compose.local.yml ps"
    echo "  重啟服務:    docker-compose -f docker-compose.local.yml restart"
    echo "  停止服務:    docker-compose -f docker-compose.local.yml down"
    echo "  進入容器:    docker-compose -f docker-compose.local.yml exec streamlit_app sh"
    echo ""
    echo "調試提示："
    echo "  • 如果頁面無法載入，查看日誌找出錯誤"
    echo "  • 如果 API 連接失敗，確認後端服務正在運行"
    echo "  • 如果按鈕無反應，檢查瀏覽器控制台的 WebSocket 錯誤"
    echo ""
    
    # 詢問是否要查看日誌
    read -p "是否要查看即時日誌？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "按 Ctrl+C 停止查看日誌"
        sleep 2
        docker-compose -f docker-compose.local.yml logs -f
    fi
}

# ===================================
# 主流程
# ===================================
main() {
    clear
    print_header "SmartCater 本地測試環境"
    echo ""
    echo "此腳本將在本地啟動測試環境，包括："
    echo "  • Streamlit 前端容器"
    echo "  • Nginx 反向代理"
    echo ""
    echo "請確保："
    echo "  ✓ Docker Desktop 正在運行"
    echo "  ✓ 後端 API 在 http://localhost:8000 上運行"
    echo ""
    
    check_prerequisites
    stop_existing_services
    start_services
    wait_for_services
    health_check
    show_info
}

# 執行主流程
main

