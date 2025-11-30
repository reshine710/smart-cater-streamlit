import streamlit as st
import pandas as pd
from utils import init_session_state, VendingMachineAPI, API_BASE_URL
from datetime import datetime
from logger_config import auth_logger, ui_logger, system_logger
from idle_logout import init_idle_tracking, check_idle_timeout, update_activity_time, render_idle_status_widget
from idle_tracker_component import render_idle_tracker
from ai_notification import render_ai_notification_widget, render_notification_auto_refresh
from modules import (
    dashboard_page,
    machine_status_page, 
    menu_management_page,
    recipe_settings_page,
    sales_analytics_page,
    ai_recommendations_page,
    location_management_page,
    order_management_page
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
            
            # st.rerun()
        else:
            auth_logger.warning(f"Login failed for username: {username}")
            st.error("❌ 登入失敗，請檢查帳號密碼")
            st.warning(
                "⚠️ 若後端服務目前無法連線，系統會改用離線模式。離線模式僅支援以下測試帳號：\n"
                "請確認使用的帳號密碼是否正確，或稍後再嘗試登入。"
            )
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
        
        st.info("💡 預設測試帳號: 管理員: admin_dev_team / admindev123")
        st.button("使用測試帳號登入", on_click=login_function, args=("admin_dev_team", "admindev123"))
        # st.button("使用測試帳號登入", on_click=login_function, args=("test_admin", "admin123"))
        # st.button("使用測試帳號登入", on_click=login_function, args=("testadmin", "testpassword"))


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
    # 分頁：使用者管理 / AI 通知收件者
    tab_users, tab_ai_recipients = st.tabs(["📋 使用者列表", "🔔 AI 通知收件者"])
    
    with tab_users:
        st.subheader("📋 使用者列表")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            page_size = st.selectbox("每頁顯示", [10, 20, 50], index=1, key="users_page_size")
        with col2:
            page_number = st.number_input("頁數", min_value=1, value=1, key="users_page_number")
        skip = (page_number - 1) * page_size
        api = st.session_state.api
        users = api.get_users(skip=skip, limit=page_size)
        total_users = api.get_users_count()
        ui_logger.debug(f"Retrieved {len(users)} users for management display (page {page_number})")
        with col3:
            st.metric("總使用者數", total_users)
        if users:
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
    
    with tab_ai_recipients:
        st.subheader("🔔 AI 通知收件者管理")
        # 權限保護（雙重保護）
        if not st.session_state.get('is_admin', False):
            st.error("❌ 權限不足：此功能僅限管理員使用")
            return
        
        # 上方操作列：狀態篩選、分頁、測試寄送
        colf1, colf2, colf3, colf4 = st.columns([1.2, 1, 1, 2])
        # 若上一輪操作要求強制切換為「全部」，需在 selectbox 建立前處理
        if st.session_state.get("ai_rec_force_all", False):
            st.session_state["ai_rec_status_filter"] = "全部"
            st.session_state["ai_rec_force_all"] = False
        with colf1:
            status_filter = st.selectbox("狀態篩選", ["全部", "啟用", "停用"], index=0, key="ai_rec_status_filter")
        with colf2:
            rec_limit = st.selectbox("每頁顯示", [20, 50, 100], index=1, key="ai_rec_limit")
        with colf3:
            rec_page = st.number_input("頁數", min_value=1, value=1, key="ai_rec_page")
        with colf4:
            with st.expander("✉️ 測試寄送", expanded=False):
                test_subject = st.text_input("主旨（選填）", value="AI 通知收件者測試郵件", disabled=True)
                test_body = st.text_area("內文（選填）", value="這是一封測試郵件，用以驗證 SMTP 與收件者設定。", disabled=True)
                if st.button("發送測試郵件", key="btn_send_test_email"):
                    st.session_state.api.send_ai_notification_test(subject=test_subject, body=test_body)
        
        # 取得列表
        is_active_param = None
        if status_filter == "啟用":
            is_active_param = True
        elif status_filter == "停用":
            is_active_param = False
        rec_result = st.session_state.api.get_ai_notification_recipients(
            is_active=is_active_param, page=rec_page, limit=rec_limit
        ) or {"items": [], "total": 0, "skip": 0, "limit": rec_limit}
        rec_items = rec_result.get("items", [])
        rec_total = rec_result.get("total", 0)
        # 前端樂觀過濾：剛刪除的項目先從當前列表隱藏
        removed_ids = st.session_state.get("ai_rec_removed_ids", set())
        if removed_ids:
            rec_items = [r for r in rec_items if r.get("id") not in removed_ids]
        
        # 上方工具列：新增
        st.markdown("---")
        with st.expander("➕ 新增收件者", expanded=(len(rec_items) == 0)):
            with st.form("form_create_ai_recipient"):
                new_email = st.text_input("Email（必填）", placeholder="ops@yourco.com").strip().lower()
                new_note = st.text_input("備註（選填，≤255）", placeholder="AI 團隊群組")
                submitted = st.form_submit_button("新增", type="primary")
                if submitted:
                    # 簡易前端驗證
                    if not new_email:
                        st.error("請輸入 Email")
                    elif "@" not in new_email or "." not in new_email.split("@")[-1]:
                        st.error("Email 格式不正確")
                    elif len(new_note) > 255:
                        st.error("備註長度不可超過 255 字元")
                    else:
                        created = st.session_state.api.create_ai_notification_recipient(email=new_email, note=new_note)
                        if created:
                            st.rerun()
        
        # 列表顯示
        st.markdown("#### 📋 收件者列表")
        if rec_items:
            # Dataframe 基本顯示
            table_data = []
            for r in rec_items:
                table_data.append({
                    "ID": r.get("id"),
                    "Email": r.get("email"),
                    "狀態": "啟用" if r.get("is_active", True) else "停用",
                    "備註": r.get("note", ""),
                    "建立時間": r.get("created_at", ""),
                    "更新時間": r.get("updated_at", "")
                })
            st.dataframe(pd.DataFrame(table_data), width='stretch')
            
            # 收件者管理操作（編輯 / 停用/啟用、刪除）
            st.markdown("##### 收件者管理操作")
            for r in rec_items:
                rid = r.get("id")
                r_email = r.get("email", "")
                r_note = r.get("note", "")
                r_active = r.get("is_active", True)
                row_cols = st.columns([7, 1, 1])
                with row_cols[0]:
                    with st.expander(f"✏️ 編輯 - {r_email}", expanded=False):
                        with st.form(f"form_edit_recipient_{rid}"):
                            upd_email = st.text_input("Email", value=r_email, key=f"edit_email_{rid}").strip().lower()
                            upd_note = st.text_input("備註（≤255）", value=r_note or "", key=f"edit_note_{rid}")
                            upd_active = st.checkbox("啟用", value=bool(r_active), key=f"edit_active_{rid}")
                            save_btn = st.form_submit_button("儲存", type="primary")
                            if save_btn:
                                if not upd_email:
                                    st.error("請輸入 Email")
                                elif "@" not in upd_email or "." not in upd_email.split("@")[-1]:
                                    st.error("Email 格式不正確")
                                elif len(upd_note) > 255:
                                    st.error("備註長度不可超過 255 字元")
                                else:
                                    updated = st.session_state.api.update_ai_notification_recipient(
                                        recipient_id=rid, email=upd_email, note=upd_note, is_active=upd_active
                                    )
                                    if updated:
                                        # 若狀態變更可能導致在「啟用/停用」篩選下消失，下一輪強制顯示「全部」
                                        if upd_active != r_active:
                                            st.session_state["ai_rec_force_all"] = True
                                        st.rerun()
                with row_cols[1]:
                    # 啟用/停用開關（軟刪）
                    toggle_key = f"row_active_{rid}"
                    current_val = st.session_state.get(toggle_key, r_active)
                    new_val = st.checkbox("啟用", value=current_val, key=toggle_key)
                    if new_val != r_active:
                        # 使用 PATCH /status 切換狀態
                        result = st.session_state.api.set_ai_notification_recipient_status(rid, new_val)
                        if result is not None:
                            # 下一輪切換篩選為「全部」，避免項目因篩選而消失
                            st.session_state["ai_rec_force_all"] = True
                            st.rerun()
                with row_cols[2]:
                    # 硬刪：不可回復
                    if st.button("刪除", key=f"btn_delete_{rid}", width='stretch'):
                        ok = st.session_state.api.delete_ai_notification_recipient(rid)
                        if ok:
                            # 二次驗證：立即向後端取一次資料確認是否仍存在
                            try:
                                verify_result = st.session_state.api.get_ai_notification_recipients(
                                    is_active=None, page=rec_page, limit=rec_limit
                                )
                                still_exists = False
                                for _r in (verify_result or {}).get("items", []):
                                    if _r.get("id") == rid:
                                        still_exists = True
                                        break
                                if still_exists:
                                    st.warning("⚠️ 後端仍回傳此收件者，可能由種子/環境變數重新建立，或刪除未生效。")
                            except Exception:
                                pass
                            # 樂觀更新：先在前端列表隱藏
                            removed_set = set(st.session_state.get("ai_rec_removed_ids", set()))
                            removed_set.add(rid)
                            st.session_state["ai_rec_removed_ids"] = removed_set
                            st.rerun()
            
            # 分頁資訊
            total_pages = (rec_total + rec_limit - 1) // rec_limit if rec_limit else 1
            st.caption(f"總數：{rec_total}，頁數：{rec_page}/{max(total_pages, 1)}")
        else:
            st.info("目前沒有收件者資料，請點擊上方「新增收件者」。")


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
        # AI 推薦通知 - 顯示在最頂部
        render_ai_notification_widget()
        
        st.markdown("---")

        placeholder = st.empty()

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
        
        
        # 基本功能（所有使用者）
        pages = {
            "🗄️ 機台狀態": "machine_status",
            "📊 營運儀表板": "dashboard",
            # "📈 銷售數據": "sales_data",
            "🛒 商品管理": "inventory",
            "🤖 AI智能推薦": "ai_recommendations",
            # "🧾 配方設定": "settings"
        }
        
        ui_logger.debug(f"Available pages for user {username}: {list(pages.keys())}")
        
        # 管理員專用功能
        if is_admin:
            pages["📍 地點管理"] = "location_management"
            pages["👥 使用者管理"] = "user_management"
            pages["📦 訂單管理"] = "order_management"
            ui_logger.debug(f"Admin pages added for user {username}")
        
        # 初始化頁面狀態
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "🗄️ 機台狀態"
        
        # 確保當前頁面在可用頁面列表中
        available_pages = list(pages.keys())
        if st.session_state.current_page not in available_pages:
            st.session_state.current_page = available_pages[0] if available_pages else "🗄️ 機台狀態"
        
        with placeholder.container():
            # 顯示功能選單
            st.markdown("### 📋 功能選單")
            
            # 當前頁面狀態
            page_key = pages.get(st.session_state.current_page, "machine_status")
            
            # 顯示所有可用頁面的按鈕
            for page_name in available_pages:
                page_value = pages[page_name]
                is_current_page = (page_key == page_value)
                
                # 使用不同的樣式來區分當前頁面和其他頁面
                if is_current_page:
                    # 當前頁面使用主要按鈕樣式
                    if st.button(page_name, key=f"nav_{page_value}", type="primary", width='stretch'):
                        st.session_state.current_page = page_name
                        st.rerun()
                else:
                    # 其他頁面使用次要按鈕樣式
                    if st.button(page_name, key=f"nav_{page_value}", width='stretch'):
                        st.session_state.current_page = page_name
                        st.rerun()
            
            ui_logger.info(f"User {username} current page: {st.session_state.current_page} ({page_key})")
            
            # API 連接狀態和版本信息
            api_connected, backend_version = check_api_connection()
            api_status = "🟢 正常" if api_connected else "🔴 離線"
            st.write(f"**API 連接狀態:** {api_status}")
            
            system_logger.info(f"API connection status: {'Connected' if api_connected else 'Offline'}")
        
        # 閒置狀態顯示
        render_idle_status_widget()
        
        # AI 通知自動刷新
        st.markdown("---")
        render_notification_auto_refresh(refresh_interval=300)  # 改為300秒（5分鐘）以減少API調用頻率
        
        # 版本號顯示
        st.markdown("---")
        st.caption("🖥️ 前端版本：v0.5.0")
        st.caption(f"⚙️ 後端版本：{backend_version if api_connected else '未連接'}")
        
    # 顯示頁面內容
    if page_key == "machine_status":
        machine_status_page()
    # elif page_key == "sales_data":
        # sales_analytics_page()
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
    elif page_key == "order_management":
        order_management_page()
    elif page_key == "dashboard":
        dashboard_page()


def check_api_connection() -> tuple:
    """檢查 API 連接狀態，返回 (是否連接, 後端版本)"""
    try:
        import requests
        # 使用健康檢查端點，從配置文件獲取 base URL
        base_url = API_BASE_URL.replace("/api/v1", "")  # 移除 /api/v1 後綴
        response = requests.get(f"{base_url}/health", timeout=5)
        is_connected = response.status_code == 200
        backend_version = "Unknown"
        
        if is_connected:
            health_data = response.json()
            backend_version = health_data.get('version', 'Unknown')
            system_logger.info(f"API connection successful - Status: {health_data.get('status', 'unknown')}, Version: {backend_version}")
        else:
            system_logger.warning(f"API connection check failed - Status: {response.status_code}")
        
        return is_connected, backend_version
    except Exception as e:
        system_logger.warning(f"API connection check failed: {str(e)}")
        return False, "Unknown"


if __name__ == "__main__":
    system_logger.info("Application starting...")
    main()
    system_logger.info("Application session ended")
