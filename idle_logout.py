"""
閒置登出管理模組
實現30分鐘閒置時間後自動登出功能
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from logger_config import auth_logger, system_logger

# 閒置時間設定（30分鐘）
IDLE_TIMEOUT_MINUTES = 30
IDLE_TIMEOUT_SECONDS = IDLE_TIMEOUT_MINUTES * 60

# 警告時間設定（5分鐘前警告）
WARNING_TIME_MINUTES = 5
WARNING_TIME_SECONDS = WARNING_TIME_MINUTES * 60

def init_idle_tracking():
    """初始化閒置追蹤"""
    if 'last_activity_time' not in st.session_state:
        st.session_state.last_activity_time = time.time()
        system_logger.debug("Idle tracking initialized")
    
    if 'idle_warning_shown' not in st.session_state:
        st.session_state.idle_warning_shown = False

def update_activity_time():
    """更新最後活動時間"""
    st.session_state.last_activity_time = time.time()
    if st.session_state.idle_warning_shown:
        st.session_state.idle_warning_shown = False
        system_logger.debug("Activity detected, warning cleared")

def check_idle_timeout():
    """檢查閒置超時"""
    if not st.session_state.get('logged_in', False):
        return False
    
    current_time = time.time()
    last_activity = st.session_state.get('last_activity_time', current_time)
    idle_time = current_time - last_activity
    
    # 檢查是否超過閒置時間
    if idle_time >= IDLE_TIMEOUT_SECONDS:
        auth_logger.info(f"User {st.session_state.get('username', 'Unknown')} logged out due to idle timeout ({IDLE_TIMEOUT_MINUTES} minutes)")
        perform_idle_logout()
        return True
    
    # 檢查是否需要顯示警告
    if idle_time >= (IDLE_TIMEOUT_SECONDS - WARNING_TIME_SECONDS) and not st.session_state.idle_warning_shown:
        remaining_time = IDLE_TIMEOUT_SECONDS - idle_time
        show_idle_warning(remaining_time)
        st.session_state.idle_warning_shown = True
        return False
    
    return False

def show_idle_warning(remaining_seconds):
    """顯示閒置警告"""
    remaining_minutes = int(remaining_seconds / 60)
    remaining_seconds = int(remaining_seconds % 60)
    
    warning_message = f"""
    ⚠️ **閒置警告**
    
    您已經閒置 {IDLE_TIMEOUT_MINUTES - WARNING_TIME_MINUTES} 分鐘，系統將在 **{remaining_minutes}分{remaining_seconds}秒** 後自動登出。
    
    請點擊任何按鈕或進行操作以保持登入狀態。
    """
    
    st.warning(warning_message)
    system_logger.info(f"Idle warning shown - {remaining_minutes} minutes remaining")

def perform_idle_logout():
    """執行閒置登出"""
    username = st.session_state.get('username', 'Unknown')
    
    # 記錄登出事件
    auth_logger.info(f"Performing idle logout for user: {username}")
    
    # 顯示登出訊息
    st.error(f"🔒 **自動登出**\n\n由於閒置時間超過 {IDLE_TIMEOUT_MINUTES} 分鐘，您已被自動登出。\n\n請重新登入以繼續使用系統。")
    
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
    other_keys = ['ai_recommendations_cache', 'push_records', 'last_activity_time', 'idle_warning_shown']
    for key in other_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    system_logger.info("Session state cleared due to idle timeout")
    
    # 重新初始化API客戶端
    from utils import VendingMachineAPI, API_BASE_URL
    st.session_state.api = VendingMachineAPI(API_BASE_URL)
    
    # 強制重新載入頁面
    st.rerun()

def get_idle_time_remaining():
    """獲取剩餘閒置時間"""
    if not st.session_state.get('logged_in', False):
        return 0
    
    current_time = time.time()
    last_activity = st.session_state.get('last_activity_time', current_time)
    idle_time = current_time - last_activity
    remaining_time = IDLE_TIMEOUT_SECONDS - idle_time
    
    return max(0, remaining_time)

def get_idle_status():
    """獲取閒置狀態資訊"""
    if not st.session_state.get('logged_in', False):
        return {
            'is_logged_in': False,
            'idle_time': 0,
            'remaining_time': 0,
            'warning_shown': False
        }
    
    current_time = time.time()
    last_activity = st.session_state.get('last_activity_time', current_time)
    idle_time = current_time - last_activity
    remaining_time = max(0, IDLE_TIMEOUT_SECONDS - idle_time)
    
    return {
        'is_logged_in': True,
        'idle_time': idle_time,
        'remaining_time': remaining_time,
        'warning_shown': st.session_state.get('idle_warning_shown', False),
        'last_activity': datetime.fromtimestamp(last_activity).strftime('%H:%M:%S')
    }

def render_idle_status_widget():
    """渲染閒置狀態小工具"""
    if not st.session_state.get('logged_in', False):
        return
    
    status = get_idle_status()
    remaining_minutes = int(status['remaining_time'] / 60)
    remaining_seconds = int(status['remaining_time'] % 60)
    
    # 根據剩餘時間選擇顏色
    if remaining_minutes <= 5:
        color = "🔴"  # 紅色 - 危險
    elif remaining_minutes <= 10:
        color = "🟡"  # 黃色 - 警告
    else:
        color = "🟢"  # 綠色 - 安全
    
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### {color} 登入狀態")
        
        if remaining_minutes > 0:
            st.info(f"**剩餘時間**: {remaining_minutes}分{remaining_seconds}秒")
            st.caption(f"最後活動: {status['last_activity']}")
        else:
            st.error("**即將登出**")
        
        # 手動延長會話按鈕
        if st.button("🔄 延長會話", help="點擊以重置閒置計時器"):
            update_activity_time()
            st.success("✅ 會話已延長")
            st.rerun()
