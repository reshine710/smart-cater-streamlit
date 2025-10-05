import streamlit as st
import pandas as pd
from utils import init_session_state, VendingMachineAPI, API_BASE_URL
from datetime import datetime
from logger_config import auth_logger, ui_logger, system_logger
from idle_logout import init_idle_tracking, check_idle_timeout, update_activity_time, render_idle_status_widget
from idle_tracker_component import render_idle_tracker
from modules import (
    dashboard_page,
    machine_status_page, 
    menu_management_page,
    recipe_settings_page,
    sales_analytics_page,
    ai_recommendations_page,
    location_management_page
)

def show_main_app():
    """顯示主應用程式"""
    ui_logger.debug(f"Showing main app for user: {st.session_state.get('username', 'Unknown')}")
    # st.set_page_config(layout="centered",initial_sidebar_state="expanded")
    st.title("🏪 智慧販賣機管理系統")
    st.markdown("---")
    
    # 頁籤選擇：登入或註冊
    tab1, tab2 = st.tabs(["🔐 登入", "📝 註冊"])
    
    with tab1:
        login_form()
    
    with tab2:
        register_form()


def login_function(username, password):

    if username and password:
        result = st.session_state.api.login(username, password)
        if result:
            st.session_state.logged_in = True
            st.session_state.token = result['access_token']
            st.session_state.username = result['user_info'].get('username', '')
            st.session_state.user_info = result['user_info']
            st.session_state.is_admin = result['user_info'].get('is_admin', False)
            print(result['user_info'])
            
            system_logger.info(f"Session state updated for user: {st.session_state.username}, admin: {st.session_state.is_admin}")
            user_info = result['user_info']
            auth_logger.info(f"UI Login successful - User ID: {user_info.get('id', 'N/A')}, Username: {user_info.get('username', 'Unknown')}, is_admin: {user_info.get('is_admin', False)}")
            ui_logger.debug(f"Login result: {result}")
            
            st.session_state.api = VendingMachineAPI(API_BASE_URL, result["access_token"])
            
            # 更新活動時間（登入成功）
            update_activity_time()
            
            # 根據角色顯示不同的成功訊息
            is_offline = result['user_info'].get('_offline_mode', False)
            
            if st.session_state.is_admin:
                if is_offline:
                    st.warning(f"🔌 管理員登入成功（離線模式）！歡迎 {username}")
                else:
                    st.success(f"🎉 管理員登入成功！歡迎 {username}")
            else:
                if is_offline:
                    st.warning(f"🔌 使用者登入成功（離線模式）！歡迎 {username}")
                else:
                    st.success(f"✅ 使用者登入成功！歡迎 {username}")
            
            st.rerun()
        else:
            auth_logger.warning(f"Login failed for username: {username}")
            st.error("❌ 登入失敗，請檢查帳號密碼")
    else:
        st.warning("請輸入使用者名稱和密碼")

def login_form():
    """登入表單"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 系統登入")
        
        with st.form("login_form"):
            username = st.text_input("使用者名稱", placeholder="請輸入使用者名稱")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            submit_button = st.form_submit_button("登入", width="stretch")
            
            if submit_button:
                login_function(username, password)
        
        st.info("💡 預設測試帳號: 管理員: testadmin / testpassword")
        st.button("使用測試帳號登入", on_click=login_function, args=("testadmin", "testpassword"))


def register_form():
    """註冊表單"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("📝 使用者註冊")
        
        with st.form("register_form"):
            username = st.text_input("使用者名稱", placeholder="請輸入使用者名稱")
            email = st.text_input("電子郵件", placeholder="請輸入電子郵件")
            full_name = st.text_input("姓名", placeholder="請輸入真實姓名")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            confirm_password = st.text_input("確認密碼", type="password", placeholder="請再次輸入密碼")
            
            # 使用者類型選擇
            user_type = st.selectbox(
                "使用者類型",
                ["一般使用者", "管理員"],
                help="管理員擁有更多系統權限"
            )
            
            submit_button = st.form_submit_button("註冊", width="stretch")
            
            if submit_button:
                # 表單驗證
                if not all([username, email, full_name, password, confirm_password]):
                    st.error("請填寫所有必填欄位")
                elif password != confirm_password:
                    st.error("密碼與確認密碼不一致")
                elif len(password) < 6:
                    st.error("密碼長度至少需要6個字元")
                elif "@" not in email:
                    st.error("請輸入有效的電子郵件格式")
                else:
                    # 呼叫註冊 API
                    is_admin = user_type == "管理員"
                    if st.session_state.api.register(username, email, password, full_name, is_admin):
                        auth_logger.info(f"Registration successful via UI - Username: {username}, is_admin: {is_admin}")
                        st.success(f"✅ 註冊成功！{'管理員' if is_admin else '使用者'} {username} 已建立")
                    else:
                        auth_logger.warning(f"Registration failed via UI - Username: {username}")
                        st.error("❌ 註冊失敗，請稍後再試")
    
    st.info("💡 註冊後請切換到登入頁籤使用新帳號登入")


def logout():
    """登出功能"""
    username = st.session_state.get('username', 'Unknown')
    auth_logger.info(f"User logout: {username}")
    
    # 清除所有認證相關狀態
    auth_keys = ['logged_in', 'token', 'username', 'user_info', 'is_admin']
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # 清除導航相關狀態
    nav_keys = ['current_page', 'main_navigation_selectbox_v2']
    for key in nav_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # 清除其他可能導致問題的狀態
    other_keys = ['ai_recommendations_cache', 'push_records']
    for key in other_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    system_logger.info("Session state cleared on logout")
    st.rerun()


def show_user_management():
    """使用者管理頁面（僅管理員可見）"""
    ui_logger.info(f"Admin {st.session_state.get('username', 'Unknown')} accessing user management")
    st.header("👥 使用者管理")
    st.markdown("---")
    
    # 使用者列表
    st.subheader("📋 使用者列表")
    
    # 分頁控制
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        page_size = st.selectbox("每頁顯示", [10, 20, 50], index=1)
    with col2:
        page_number = st.number_input("頁數", min_value=1, value=1)
    
    skip = (page_number - 1) * page_size
    
    # 獲取使用者列表和總數
    api = st.session_state.api
    users = api.get_users(skip=skip, limit=page_size)
    total_users = api.get_users_count()
    
    ui_logger.debug(f"Retrieved {len(users)} users for management display (page {page_number})")
    
    with col3:
        st.metric("總使用者數", total_users)
    
    if users:
        # 建立使用者資料表
        user_data = []
        for user in users:
            user_data.append({
                "ID": user.get("id", "N/A"),
                "使用者名稱": user.get("username", "N/A"),
                "姓名": user.get("full_name", "N/A"),
                "電子郵件": user.get("email", "N/A"),
                "角色": "管理員" if user.get("is_admin", False) else "一般使用者",
                "狀態": "啟用" if user.get("is_active", False) else "停用",
                "建立時間": user.get("created_at", "N/A")
            })
        
        df = pd.DataFrame(user_data)
        st.dataframe(df, width="stretch")
        
        # 統計資訊
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            current_page_users = len(users)
            st.metric("當前頁使用者", current_page_users)
        with col2:
            admin_count = sum(1 for user in users if user.get("is_admin", False))
            st.metric("管理員數量", admin_count)
        with col3:
            active_count = sum(1 for user in users if user.get("is_active", False))
            st.metric("啟用使用者", active_count)
        with col4:
            total_pages = (total_users + page_size - 1) // page_size
            st.metric("總頁數", total_pages)
    else:
        st.info("目前沒有使用者資料")
    
    st.markdown("---")
    
    # 快速建立測試使用者
    st.subheader("🚀 快速建立測試使用者")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("建立測試管理員", width="stretch"):
            ui_logger.info("Admin attempting to create test admin user")
            if st.session_state.api.register("testadmin", "testadmin@example.com", "testpassword", "Test Admin", True):
                auth_logger.info("Test admin user created successfully via UI")
                st.success("✅ 測試管理員建立成功！")
                st.rerun()
            else:
                auth_logger.warning("Failed to create test admin user via UI")
                st.error("❌ 建立失敗，可能已存在")
    
    with col2:
        if st.button("👤 建立測試使用者", key="create_user"):
            ui_logger.info("Admin attempting to create test regular user")
            if st.session_state.api.register("testuser2", "testuser2@example.com", "testpassword", "Test User 2", False):
                auth_logger.info("Test regular user created successfully via UI")
                st.success("✅ 測試使用者建立成功！")
                st.rerun()
            else:
                auth_logger.warning("Failed to create test regular user via UI")
                st.error("❌ 建立失敗")


def main():
    # 設置頁面配置 - 必須在其他 Streamlit 命令之前
    st.set_page_config(
        page_title="智慧販賣機管理系統",
        page_icon="🏪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化 session state
    init_session_state()
    ui_logger.debug("Session state initialized in main")
    
    # 初始化閒置追蹤
    init_idle_tracking()
    
    # 檢查閒置超時
    if check_idle_timeout():
        return  # 如果已登出，直接返回
    
    # 載入閒置追蹤組件（隱藏）
    render_idle_tracker()
    
    # 檢查登入狀態
    if not st.session_state.logged_in:
        show_main_app()
        return
    
    # 側邊欄 - 使用者資訊和導航
    with st.sidebar:
        st.markdown("---")
        
        # 使用者資訊
        user_info = st.session_state.get('user_info', {})
        username = user_info.get('username', st.session_state.get('username', 'Unknown'))
        is_admin = st.session_state.get('is_admin', False)
        
        ui_logger.debug(f"Sidebar - User: {username}, Admin: {is_admin}")
        
        # 顯示使用者角色
        if is_admin:
            st.success("👑 管理員")
        else:
            st.info("👤 一般使用者")
        
        # 顯示使用者詳細資訊
        if user_info:
            with st.expander("👤 使用者資訊"):
                # 檢查是否為離線模式
                is_offline = user_info.get('_offline_mode', False)
                
                if is_offline:
                    st.warning("🔌 **離線模式** - API 連接不可用，使用本地資料")
                
                st.write(f"**姓名**: {user_info.get('full_name', 'N/A')}")
                st.write(f"**電子郵件**: {user_info.get('email', 'N/A')}")
                st.write(f"**帳號狀態**: {'啟用' if user_info.get('is_active', False) else '停用'}")
                st.write(f"**權限等級**: {'管理員' if user_info.get('is_admin', False) else '一般使用者'}")
                
                # 顯示連接狀態
                if is_offline:
                    st.write(f"**連接狀態**: 🔌 離線模式")
                else:
                    st.write(f"**連接狀態**: 🌐 線上模式")
        
        if st.button("🚪 登出"):
            logout()
        
        # 頁面導航
        st.markdown("### 📋 功能選單")
        
        # 添加重置按鈕（僅在開發模式下顯示）
        if st.button("🔄 重置導航", help="如果功能選單卡住，點擊此按鈕重置"):
            # 清除導航相關的 session state
            keys_to_clear = ['current_page', 'main_navigation_selectbox_v2']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        # 基本功能（所有使用者）
        pages = {
            "🗄️ 機台狀態": "machine_status",
            "📊 首頁": "dashboard",
            "📈 銷售數據": "sales_data",
            "🛒 商品管理": "inventory",
            "🤖 AI智能推薦": "ai_recommendations",
            "🧾 配方設定": "settings"
        }
        
        ui_logger.debug(f"Available pages for user {username}: {list(pages.keys())}")
        
        # 管理員專用功能
        if is_admin:
            pages["📍 地點管理"] = "location_management"
            pages["👥 使用者管理"] = "user_management"
            ui_logger.debug(f"Admin pages added for user {username}")
        
        # 初始化頁面狀態
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "🏠 首頁"
        
        # 確保當前頁面在可用頁面列表中
        available_pages = list(pages.keys())
        if st.session_state.current_page not in available_pages:
            st.session_state.current_page = available_pages[0] if available_pages else "🏠 首頁"
        
        try:
            # 選擇頁面
            current_index = available_pages.index(st.session_state.current_page)
        except (ValueError, IndexError):
            current_index = 0
            st.session_state.current_page = available_pages[0] if available_pages else "🏠 首頁"
        
        # 使用更強健的 selectbox 實現
        try:
            selected_page = st.selectbox(
                "選擇功能", 
                available_pages,
                index=current_index,
                key="main_navigation_selectbox_v2",
                help="選擇要使用的功能模組"
            )
        except Exception as e:
            ui_logger.error(f"Selectbox error: {str(e)}")
            # 如果 selectbox 出錯，重置狀態
            st.session_state.current_page = available_pages[0] if available_pages else "🏠 首頁"
            selected_page = st.session_state.current_page
        
        # 更新當前頁面狀態
        if selected_page and selected_page in pages:
            st.session_state.current_page = selected_page
            page_key = pages[selected_page]
        else:
            # 如果選擇無效，使用預設頁面
            st.session_state.current_page = available_pages[0] if available_pages else "🏠 首頁"
            page_key = pages[st.session_state.current_page]
        
        ui_logger.info(f"User {username} selected page: {selected_page} ({page_key})")
        
        # API 連接狀態
        api_connected = check_api_connection()
        api_status = "🟢 正常" if api_connected else "🔴 離線"
        st.write(f"**API 連接狀態:** {api_status}")
        
        system_logger.info(f"API connection status: {'Connected' if api_connected else 'Offline'}")
        
        # 閒置狀態顯示
        render_idle_status_widget()
        
    # 顯示頁面內容
    if page_key == "machine_status":
        machine_status_page()
    elif page_key == "sales_data":
        sales_analytics_page()
    elif page_key == "inventory":
        menu_management_page()
    elif page_key == "settings":
        recipe_settings_page()
    elif page_key == "user_management":
        show_user_management()
    elif page_key == "ai_recommendations":
        ai_recommendations_page()
    elif page_key == "location_management":
        location_management_page()
    elif page_key == "dashboard":
        dashboard_page()


def check_api_connection() -> bool:
    """檢查 API 連接狀態"""
    try:
        import requests
        # 使用健康檢查端點，從配置文件獲取 base URL
        base_url = API_BASE_URL.replace("/api/v1", "")  # 移除 /api/v1 後綴
        response = requests.get(f"{base_url}/health", timeout=5)
        is_connected = response.status_code == 200
        if is_connected:
            health_data = response.json()
            system_logger.info(f"API connection successful - Status: {health_data.get('status', 'unknown')}, Version: {health_data.get('version', 'unknown')}")
        else:
            system_logger.warning(f"API connection check failed - Status: {response.status_code}")
        return is_connected
    except Exception as e:
        system_logger.warning(f"API connection check failed: {str(e)}")
        return False


if __name__ == "__main__":
    system_logger.info("Application starting...")
    main()
    system_logger.info("Application session ended")
