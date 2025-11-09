import streamlit as st
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from logger_config import ui_logger


def init_notification_state():
    """初始化通知相關的 session state"""
    if 'ai_notification_read_items' not in st.session_state:
        st.session_state.ai_notification_read_items = set()
    
    if 'ai_notification_last_check' not in st.session_state:
        st.session_state.ai_notification_last_check = None
    
    if 'ai_notification_data' not in st.session_state:
        st.session_state.ai_notification_data = {
            'pending': [],
            'approved': []
        }


def get_pending_and_approved_recommendations() -> Tuple[List[Dict], List[Dict]]:
    """
    獲取待審核(PENDING)和已通過(APPROVED)的推薦
    返回: (pending_recommendations, approved_recommendations)
    """
    try:
        if not hasattr(st.session_state, 'api') or not st.session_state.api:
            return [], []
        
        # 獲取待審核的推薦
        pending_recs = st.session_state.api.get_ai_recommendations(status_filter="PENDING")
        ui_logger.debug(f"Notification: Retrieved {len(pending_recs)} pending recommendations from API")
        
        # 獲取已通過的推薦
        approved_recs = st.session_state.api.get_ai_recommendations(status_filter="APPROVED")
        ui_logger.debug(f"Notification: Retrieved {len(approved_recs)} approved recommendations from API")
        
        # 前端二次驗證：確保只返回正確狀態的推薦
        # 過濾出真正是 PENDING 狀態的推薦
        verified_pending = [rec for rec in pending_recs if rec.get('status') == 'PENDING']
        
        # 過濾出真正是 APPROVED 狀態的推薦
        verified_approved = [rec for rec in approved_recs if rec.get('status') == 'APPROVED']
        
        # 記錄過濾後的結果
        if len(verified_pending) != len(pending_recs):
            ui_logger.warning(f"Filtered pending recommendations: {len(pending_recs)} -> {len(verified_pending)}")
            # 記錄被過濾掉的推薦及其狀態
            filtered = [rec for rec in pending_recs if rec.get('status') != 'PENDING']
            for rec in filtered:
                ui_logger.warning(f"Filtered out recommendation {rec.get('recommendation_id')} with status {rec.get('status')} from PENDING list")
        
        if len(verified_approved) != len(approved_recs):
            ui_logger.warning(f"Filtered approved recommendations: {len(approved_recs)} -> {len(verified_approved)}")
            # 記錄被過濾掉的推薦及其狀態
            filtered = [rec for rec in approved_recs if rec.get('status') != 'APPROVED']
            for rec in filtered:
                ui_logger.warning(f"Filtered out recommendation {rec.get('recommendation_id')} with status {rec.get('status')} from APPROVED list")
        
        ui_logger.debug(f"Notification: After verification - {len(verified_pending)} pending, {len(verified_approved)} approved")
        
        return verified_pending, verified_approved
        
    except Exception as e:
        ui_logger.error(f"Failed to get recommendations for notification: {str(e)}")
        return [], []


def get_machine_code_mapping() -> Dict[str, str]:
    """
    獲取機台ID到機台代碼的映射
    返回: {machine_id: machine_code}
    """
    try:
        if not hasattr(st.session_state, 'api') or not st.session_state.api:
            return {}
        
        machines = st.session_state.api.get_machines()
        if not machines:
            return {}
        
        mapping = {}
        for machine in machines:
            machine_id = str(machine.get('id', ''))
            machine_code = machine.get('machine_code', machine_id)
            mapping[machine_id] = machine_code
            
        ui_logger.debug(f"Machine code mapping: {mapping}")
        return mapping
        
    except Exception as e:
        ui_logger.error(f"Failed to get machine code mapping: {str(e)}")
        return {}


def format_machine_codes(machine_ids: List[str], machine_mapping: Dict[str, str]) -> str:
    """
    格式化機台代碼列表
    參數:
        machine_ids: 機台ID列表
        machine_mapping: 機台ID到代碼的映射
    返回: 格式化的機台代碼字符串，如 "SC-NCU-001, SC-NCU-002"
    """
    if not machine_ids:
        return "未指定"
    
    codes = []
    for machine_id in machine_ids:
        code = machine_mapping.get(str(machine_id), f"機台-{machine_id}")
        codes.append(code)
    
    return ", ".join(codes)


def get_unread_recommendations(pending_recs: List[Dict], approved_recs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    過濾出未讀的推薦
    返回: (unread_pending, unread_approved)
    """
    read_items = st.session_state.get('ai_notification_read_items', set())
    
    unread_pending = [rec for rec in pending_recs if rec.get('id') not in read_items]
    unread_approved = [rec for rec in approved_recs if rec.get('id') not in read_items]
    
    return unread_pending, unread_approved


def mark_as_read(recommendation_id: int):
    """標記推薦為已讀"""
    if 'ai_notification_read_items' not in st.session_state:
        st.session_state.ai_notification_read_items = set()
    
    st.session_state.ai_notification_read_items.add(recommendation_id)
    ui_logger.debug(f"Marked recommendation {recommendation_id} as read")


def render_ai_notification_widget():
    """
    渲染 AI 推薦通知組件
    顯示在側邊欄頂部
    """
    # 初始化通知狀態
    init_notification_state()
    
    # 獲取推薦數據
    pending_recs, approved_recs = get_pending_and_approved_recommendations()
    
    # 首次載入時，將所有現有推薦標記為已讀（默認已讀）
    if 'ai_notification_initialized' not in st.session_state:
        ui_logger.debug("First time initialization: marking all existing recommendations as read")
        # 儲存每個推薦的初始狀態
        st.session_state.ai_notification_status_tracking = {}
        for rec in pending_recs + approved_recs:
            rec_id = rec.get('id')
            rec_status = rec.get('status')
            if rec_id:
                st.session_state.ai_notification_read_items.add(rec_id)
                st.session_state.ai_notification_status_tracking[rec_id] = rec_status
        st.session_state.ai_notification_initialized = True
        ui_logger.debug(f"Marked {len(st.session_state.ai_notification_read_items)} existing recommendations as read")
    else:
        # 檢測狀態變化：如果推薦的狀態改變了，將其從已讀列表中移除
        if 'ai_notification_status_tracking' not in st.session_state:
            st.session_state.ai_notification_status_tracking = {}
        
        for rec in pending_recs + approved_recs:
            rec_id = rec.get('id')
            rec_status = rec.get('status')
            if rec_id:
                # 檢查是否有狀態追踪記錄
                if rec_id in st.session_state.ai_notification_status_tracking:
                    old_status = st.session_state.ai_notification_status_tracking[rec_id]
                    # 如果狀態改變了，從已讀列表中移除，使其重新顯示為未讀
                    if old_status != rec_status:
                        if rec_id in st.session_state.ai_notification_read_items:
                            st.session_state.ai_notification_read_items.remove(rec_id)
                            ui_logger.info(f"Status changed for recommendation {rec.get('recommendation_id')}: {old_status} -> {rec_status}, marked as unread")
                        # 更新狀態追踪
                        st.session_state.ai_notification_status_tracking[rec_id] = rec_status
                else:
                    # 新推薦，記錄其狀態（不標記為已讀，讓它顯示為未讀）
                    st.session_state.ai_notification_status_tracking[rec_id] = rec_status
                    ui_logger.debug(f"New recommendation detected: {rec.get('recommendation_id')} with status {rec_status}")
    
    # 更新 session state 中的數據
    st.session_state.ai_notification_data = {
        'pending': pending_recs,
        'approved': approved_recs
    }
    st.session_state.ai_notification_last_check = datetime.now()
    
    # 獲取未讀推薦
    unread_pending, unread_approved = get_unread_recommendations(pending_recs, approved_recs)
    
    # 計算未讀總數
    total_unread = len(unread_pending) + len(unread_approved)
    
    # 獲取機台代碼映射
    machine_mapping = get_machine_code_mapping()
    
    # 顯示通知區域
    with st.container():
        # 通知標題和徽章
        if total_unread > 0:
            st.markdown(f"### 🔔 AI推薦通知")
            st.markdown(f"<div style='background-color: #ff4b4b; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-bottom: 10px;'>未讀訊息: {total_unread}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"### ✅ AI推薦通知")
            st.info("目前沒有新的AI推薦")
        
        # 使用 expander 顯示詳細內容
        if total_unread > 0:
            with st.expander(f"📋 查看詳細內容 ({total_unread} 則未讀)", expanded=True):
                # 顯示待審核推薦
                if unread_pending:
                    st.markdown(f"#### 🟡 待實施推薦 ({len(unread_pending)})")
                    st.caption("💡 提示：通過推薦後將立即實施並更新機台配置")
                    
                    for rec in unread_pending:
                        rec_id = rec.get('id')
                        rec_identifier = rec.get('recommendation_id', f"REC-{rec_id}")
                        rec_type = rec.get('recommendation_type', 'UNKNOWN')
                        target_machines = rec.get('target_machine_ids', [])
                        created_at = rec.get('created_at', 'Unknown')
                        confidence = rec.get('confidence_score')
                        
                        # 格式化機台代碼
                        machine_codes = format_machine_codes(target_machines, machine_mapping)
                        
                        # 獲取推薦項目數量
                        payload = rec.get('payload', {})
                        if rec_type == 'DYNAMIC_MENU':
                            item_count = len(payload.get('suggested_menu', []))
                            type_icon = "🍽️"
                            type_text = "菜單預測"
                        else:
                            item_count = len(payload.get('restock_suggestions', []))
                            type_icon = "📦"
                            type_text = "庫存預測"
                        
                        # 格式化時間
                        try:
                            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            time_str = created_time.strftime('%Y-%m-%d %H:%M')
                        except:
                            time_str = created_at
                        
                        # 顯示推薦卡片
                        with st.container():
                            st.markdown(f"""
                            <div style='background-color: #fff3cd; padding: 12px; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 10px;'>
                                <div style='font-weight: bold; font-size: 14px; margin-bottom: 5px;'>
                                    {type_icon} {type_text} - {rec_identifier}
                                </div>
                                <div style='font-size: 12px; color: #666;'>
                                    🏪 機台: {machine_codes}<br>
                                    📊 項目數: {item_count}<br>
                                    🕒 創建時間: {time_str}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 標記為已讀按鈕
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"👁️ 標記已讀", key=f"mark_read_pending_{rec_id}", use_container_width=True):
                                    mark_as_read(rec_id)
                                    st.rerun()
                            with col2:
                                if st.button(f"🔗 前往實施", key=f"goto_pending_{rec_id}", use_container_width=True):
                                    mark_as_read(rec_id)
                                    st.session_state.current_page = "🤖 AI智能推薦"
                                    st.rerun()
                    
                    st.markdown("---")
                
                # 顯示已通過推薦
                if unread_approved:
                    st.markdown(f"#### ✅ 已通過推薦 ({len(unread_approved)})")
                    
                    for rec in unread_approved:
                        rec_id = rec.get('id')
                        rec_identifier = rec.get('recommendation_id', f"REC-{rec_id}")
                        rec_type = rec.get('recommendation_type', 'UNKNOWN')
                        target_machines = rec.get('target_machine_ids', [])
                        created_at = rec.get('created_at', 'Unknown')
                        confidence = rec.get('confidence_score')
                        
                        # 格式化機台代碼
                        machine_codes = format_machine_codes(target_machines, machine_mapping)
                        
                        # 獲取推薦項目數量
                        payload = rec.get('payload', {})
                        if rec_type == 'DYNAMIC_MENU':
                            item_count = len(payload.get('suggested_menu', []))
                            type_icon = "🍽️"
                            type_text = "菜單預測"
                        else:
                            item_count = len(payload.get('restock_suggestions', []))
                            type_icon = "📦"
                            type_text = "庫存預測"
                        
                        # 格式化時間
                        try:
                            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            time_str = created_time.strftime('%Y-%m-%d %H:%M')
                        except:
                            time_str = created_at
                        
                        # 顯示推薦卡片
                        with st.container():
                            st.markdown(f"""
                            <div style='background-color: #d4edda; padding: 12px; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 10px;'>
                                <div style='font-weight: bold; font-size: 14px; margin-bottom: 5px;'>
                                    {type_icon} {type_text} - {rec_identifier}
                                </div>
                                <div style='font-size: 12px; color: #666;'>
                                    🏪 機台: {machine_codes}<br>
                                    📊 項目數: {item_count}<br>
                                    🕒 創建時間: {time_str}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 標記為已讀按鈕
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"👁️ 標記已讀", key=f"mark_read_approved_{rec_id}", use_container_width=True):
                                    mark_as_read(rec_id)
                                    st.rerun()
                            with col2:
                                if st.button(f"🔗 前往實施", key=f"goto_approved_{rec_id}", use_container_width=True):
                                    mark_as_read(rec_id)
                                    st.session_state.current_page = "🤖 AI智能推薦"
                                    st.rerun()
                    
                    st.markdown("---")
                
                # 全部標記為已讀按鈕
                if st.button("✅ 全部標記為已讀", key="mark_all_read", type="primary", use_container_width=True):
                    for rec in unread_pending + unread_approved:
                        mark_as_read(rec.get('id'))
                    st.rerun()
        
        # 顯示最後檢查時間
        last_check = st.session_state.get('ai_notification_last_check')
        if last_check:
            time_str = last_check.strftime('%H:%M:%S')
            st.caption(f"🕒 最後檢查: {time_str}")


def auto_refresh_notifications(refresh_interval: int = 60):
    """
    自動刷新通知
    參數:
        refresh_interval: 刷新間隔（秒）
    """
    last_check = st.session_state.get('ai_notification_last_check')
    
    if last_check is None:
        # 首次檢查
        return True
    
    # 檢查是否超過刷新間隔
    time_elapsed = (datetime.now() - last_check).total_seconds()
    
    if time_elapsed >= refresh_interval:
        ui_logger.debug(f"Auto-refresh triggered: {time_elapsed}s elapsed since last check")
        return True
    
    return False


def render_notification_auto_refresh(refresh_interval: int = 60):
    """
    渲染自動刷新機制
    在側邊欄顯示刷新按鈕和倒計時
    參數:
        refresh_interval: 刷新間隔（秒），預設60秒
    """
    last_check = st.session_state.get('ai_notification_last_check')
    
    if last_check is None:
        # 首次檢查
        time_remaining = 0
    else:
        # 計算剩餘時間
        time_elapsed = (datetime.now() - last_check).total_seconds()
        time_remaining = max(0, refresh_interval - int(time_elapsed))
    
    # 顯示刷新控制
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if time_remaining > 0:
                st.caption(f"🔄 下次自動檢查: {time_remaining}秒")
            else:
                st.caption(f"🔄 正在檢查新推薦...")
        
        with col2:
            if st.button("🔄", key="manual_refresh_notification", help="立即刷新"):
                st.rerun()
        
        # 如果時間到了，自動刷新
        if time_remaining == 0 and last_check is not None:
            ui_logger.debug("Auto-refresh triggered for AI notifications")
            time.sleep(0.5)  # 短暫延遲避免頻繁刷新
            st.rerun()

