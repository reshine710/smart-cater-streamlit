import streamlit as st
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
                        st.session_state.api = VendingMachineAPI(API_BASE_URL, result["access_token"])
                        st.success("登入成功！")
                        st.rerun()
                    else:
                        st.error("登入失敗，請檢查帳號密碼")
                else:
                    st.warning("請輸入使用者名稱和密碼")
        
        st.info("💡 測試帳號: admin / admin123")

def logout():
    """登出功能"""
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.api = VendingMachineAPI(API_BASE_URL)
    st.rerun()



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
        st.write(f"歡迎, {st.session_state.username}")
        
        if st.button("🚪 登出"):
            logout()
        
        st.markdown("---")
        
        # 導航選單
        page = st.selectbox(
            "選擇頁面",
            [
                "📊 營運儀表板",
                "🖥️ 機台狀態監控",
                "🍽️ 菜單管理",
                "⚙️ 配方設定",
                "📈 銷售分析"
            ]
        )
        
        st.markdown("---")
        st.markdown("### 🔧 系統資訊")
        st.info(f"API: {API_BASE_URL}")
        st.info(f"版本: v1.0.0")
    
    # 主要內容區域
    if page == "📊 營運儀表板":
        dashboard_page()
    elif page == "🖥️ 機台狀態監控":
        machine_status_page()
    elif page == "🍽️ 菜單管理":
        menu_management_page()
    elif page == "⚙️ 配方設定":
        recipe_settings_page()
    elif page == "📈 銷售分析":
        sales_analytics_page()

if __name__ == "__main__":
    main()
