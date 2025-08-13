import streamlit as st
import pandas as pd
from utils import VendingMachineAPI, init_session_state, API_BASE_URL
from pages import (
    dashboard_page,
    machine_status_page, 
    menu_management_page,
    recipe_settings_page,
    sales_analytics_page
)

# 設定頁面配置
st.set_page_config(
    page_title="智慧販賣機後台管理系統",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

def login_page():
    """登入頁面"""
    st.title("🏪 智慧販賣機後台管理系統")
    st.markdown("---")
    
    # 頁籤選擇：登入或註冊
    tab1, tab2 = st.tabs(["🔐 登入", "📝 註冊"])
    
    with tab1:
        login_form()
    
    with tab2:
        register_form()


def login_form():
    """登入表單"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 系統登入")
        
        with st.form("login_form"):
            username = st.text_input("使用者名稱", placeholder="請輸入使用者名稱")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            submit_button = st.form_submit_button("登入", use_container_width=True)
            
            if submit_button:
                if username and password:
                    result = st.session_state.api.login(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.token = result["access_token"]
                        st.session_state.username = username
                        st.session_state.user_info = result.get("user_info", {})
                        
                        # 正確提取管理員狀態
                        user_info = result.get("user_info", {})
                        st.session_state.is_admin = user_info.get("is_admin", False)
                        
                        # 調試：檢查管理員狀態
                        print(f"API Debug - Token received, User Info: {user_info.get('id', 'N/A')}, is_admin: {user_info.get('is_admin', False)}")
                        print(f"Login Debug - Username: {username}, is_admin: {user_info.get('is_admin', False)}")
                        
                        st.session_state.api = VendingMachineAPI(API_BASE_URL, result["access_token"])
                        
                        # 根據角色顯示不同的成功訊息
                        if st.session_state.is_admin:
                            st.success(f"🎉 管理員登入成功！歡迎 {username}")
                        else:
                            st.success(f"✅ 使用者登入成功！歡迎 {username}")
                        
                        st.rerun()
                    else:
                        st.error("登入失敗，請檢查帳號密碼")
                else:
                    st.warning("請輸入使用者名稱和密碼")
        
        st.info("💡 預設測試帳號:")
        st.code("管理員: testadmin / testpassword")
        st.code("一般用戶: testuser / testpassword")


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
            
            submit_button = st.form_submit_button("註冊", use_container_width=True)
            
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
                    result = st.session_state.api.register(
                        username=username,
                        email=email,
                        password=password,
                        full_name=full_name,
                        is_admin=is_admin
                    )
                    
                    if result:
                        st.success("註冊成功！請使用新帳號登入")
                        st.balloons()
                        # 清空表單（透過重新運行）
                        st.rerun()
                    else:
                        st.error("註冊失敗，使用者名稱或電子郵件可能已存在")
        
        st.info("💡 註冊後請切換到登入頁籤使用新帳號登入")

def logout():
    """登出功能"""
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_info = {}
    st.session_state.is_admin = False
    st.session_state.api = VendingMachineAPI(API_BASE_URL)
    st.rerun()


def user_management_page():
    """使用者管理頁面（僅管理員可用）"""
    st.title("👥 使用者管理")
    st.markdown("---")
    
    # 使用者列表
    st.subheader("📋 使用者列表")
    
    users = st.session_state.api.get_users()
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
        st.dataframe(df, use_container_width=True)
        
        # 統計資訊
        col1, col2, col3 = st.columns(3)
        with col1:
            total_users = len(users)
            st.metric("總使用者數", total_users)
        with col2:
            admin_count = sum(1 for user in users if user.get("is_admin", False))
            st.metric("管理員數量", admin_count)
        with col3:
            active_count = sum(1 for user in users if user.get("is_active", False))
            st.metric("啟用使用者", active_count)
    else:
        st.info("目前沒有使用者資料")
    
    st.markdown("---")
    
    # 快速建立測試使用者
    st.subheader("🚀 快速建立測試使用者")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("建立測試管理員", use_container_width=True):
            result = st.session_state.api.register(
                username="testadmin",
                email="testadmin@example.com",
                password="testpassword",
                full_name="Test Admin",
                is_admin=True
            )
            if result:
                st.success("✅ 測試管理員建立成功")
                st.rerun()
            else:
                st.error("❌ 建立失敗，可能已存在")
    
    with col2:
        if st.button("建立測試使用者", use_container_width=True):
            result = st.session_state.api.register(
                username="testuser",
                email="testuser@example.com",
                password="testpassword",
                full_name="Test User",
                is_admin=False
            )
            if result:
                st.success("✅ 測試使用者建立成功")
                st.rerun()
            else:
                st.error("❌ 建立失敗，可能已存在")
    
    st.info("💡 測試帳號密碼都是: testpassword")



def main():
    """主程式"""
    init_session_state()
    
    # 檢查登入狀態
    if not st.session_state.logged_in:
        login_page()
        return
    
    # 側邊欄
    with st.sidebar:
        st.title("🏪 智慧販賣機")
        
        # 使用者資訊
        user_info = st.session_state.get('user_info', {})
        is_admin = st.session_state.get('is_admin', False)
        
        st.write(f"歡迎, {st.session_state.username}")
        
        # 顯示使用者角色
        if is_admin:
            st.success("👑 管理員")
        else:
            st.info("👤 一般使用者")
        
        # 顯示使用者詳細資訊
        if user_info:
            with st.expander("👤 使用者資訊"):
                st.write(f"**姓名**: {user_info.get('full_name', 'N/A')}")
                st.write(f"**電子郵件**: {user_info.get('email', 'N/A')}")
                st.write(f"**帳號狀態**: {'啟用' if user_info.get('is_active', False) else '停用'}")
                st.write(f"**權限等級**: {'管理員' if user_info.get('is_admin', False) else '一般使用者'}")
        
        if st.button("🚪 登出"):
            logout()
        
        st.markdown("---")
        
        # 導航選單 - 根據使用者權限顯示不同選項
        if is_admin:
            # 管理員可以看到所有頁面
            page_options = [
                "📊 營運儀表板",
                "🖥️ 機台狀態監控",
                "🍽️ 菜單管理",
                "⚙️ 配方設定",
                "📈 銷售分析",
                "👥 使用者管理"
            ]
        else:
            # 一般使用者只能看到部分頁面
            page_options = [
                "📊 營運儀表板",
                "🖥️ 機台狀態監控",
                "📈 銷售分析"
            ]
        
        page = st.selectbox("選擇頁面", page_options)
        
        st.markdown("---")
        st.markdown("### 🔧 系統資訊")
        
        # 檢查系統狀態
        try:
            import requests
            response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=5)
            if response.status_code == 200:
                st.success("🟢 API 服務正常")
            else:
                st.warning("🟡 API 服務異常")
        except:
            st.error("🔴 API 服務離線")
        
        st.info(f"API: {API_BASE_URL}")
        st.info(f"版本: v1.0.0")
        
        # 顯示離線模式提示
        if "offline" in st.session_state.get('token', ''):
            st.warning("⚠️ 離線模式運行")
            st.caption("部分功能可能受限")
    
    # 主要內容區域
    if page == "📊 營運儀表板":
        dashboard_page()
    elif page == "🖥️ 機台狀態監控":
        machine_status_page()
    elif page == "🍽️ 菜單管理":
        if is_admin:
            menu_management_page()
        else:
            st.error("❌ 權限不足：此功能僅限管理員使用")
    elif page == "⚙️ 配方設定":
        if is_admin:
            recipe_settings_page()
        else:
            st.error("❌ 權限不足：此功能僅限管理員使用")
    elif page == "📈 銷售分析":
        sales_analytics_page()
    elif page == "👥 使用者管理":
        if is_admin:
            user_management_page()
        else:
            st.error("❌ 權限不足：此功能僅限管理員使用")

if __name__ == "__main__":
    main()
