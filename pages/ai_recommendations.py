import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
from logger_config import api_logger, ui_logger

def ai_recommendations_page():
    """AI推薦管理頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing AI recommendations page")
    st.title("🤖 AI智能推薦管理")
    st.markdown("---")
    
    # 檢查管理員權限
    if not st.session_state.get('is_admin', False):
        st.error("❌ 權限不足：此功能僅限管理員使用")
        ui_logger.warning(f"Non-admin user {st.session_state.get('username', 'Unknown')} attempted to access AI recommendations")
        return
    
    # AI健康狀態檢查
    with st.sidebar:
        st.subheader("🔍 AI系統狀態")
        if st.button("🔄 檢查AI狀態"):
            health_status = check_ai_health()
            if health_status.get("status") == "ok":
                st.success("✅ AI系統運行正常")
                st.json(health_status)
            else:
                st.error("❌ AI系統異常")
                st.json(health_status)
    
    # 主要標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["📋 推薦列表", "🎯 動態菜單", "📊 推播記錄", "➕ 創建推薦"])
    
    with tab1:
        show_recommendations_list()
    
    with tab2:
        show_dynamic_menu_display()
    
    with tab3:
        show_push_notification_records()
    
    with tab4:
        show_create_recommendation_form()

def check_ai_health() -> dict:
    """檢查AI系統健康狀態"""
    try:
        # 嘗試調用真實API
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.get_ai_health()
        else:
            # 模擬AI健康檢查
            return {
                "status": "ok",
                "service": "AI Analysis API",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def show_recommendations_list():
    """顯示AI推薦列表"""
    st.subheader("📋 AI推薦列表")
    
    # 篩選選項
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "狀態篩選", 
            ["全部", "PENDING", "APPROVED", "REJECTED", "EXPIRED"],
            format_func=lambda x: {
                "全部": "全部狀態",
                "PENDING": "🟡 待審核",
                "APPROVED": "✅ 已通過",
                "REJECTED": "❌ 已拒絕",
                "EXPIRED": "⏰ 已過期"
            }.get(x, x)
        )
    
    with col2:
        machine_filter = st.selectbox("機台篩選", ["全部", "1", "2", "3"])
    
    with col3:
        if st.button("🔄 重新整理"):
            st.rerun()
    
    # 獲取推薦數據
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            filter_status = None if status_filter == "全部" else status_filter
            filter_machine = None if machine_filter == "全部" else machine_filter
            recommendations = st.session_state.api.get_ai_recommendations(
                status_filter=filter_status, 
                machine_id=filter_machine
            )
        else:
            recommendations = get_mock_recommendations()
    except Exception as e:
        st.error(f"❌ 獲取推薦數據失敗: {str(e)}")
        recommendations = get_mock_recommendations()
    
    st.write(f"顯示 {len(recommendations)} 個推薦")
    
    # 顯示推薦列表
    for i, rec in enumerate(recommendations):
        with st.expander(f"{get_status_icon(rec['status'])} {rec['recommendation_id']} - {rec['recommendation_type']}", expanded=False):
            show_recommendation_details(rec, i)

def show_recommendation_details(rec: Dict, index: int):
    """顯示推薦詳細資訊"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.write(f"**AI模型版本**: {rec.get('ai_model_version', 'Unknown')}")
        st.write(f"**目標機台**: {', '.join(rec.get('target_machine_ids', []))}")
        st.write(f"**信心分數**: {rec.get('confidence_score', 0):.2%}")
        st.write(f"**有效期間**: {rec.get('valid_from', 'Unknown')} ~ {rec.get('valid_until', 'Unknown')}")
    
    with col2:
        st.write(f"**狀態**: {get_status_display(rec['status'])}")
        st.write(f"**創建時間**: {rec.get('created_at', 'Unknown')}")
        if rec.get('notes'):
            st.write(f"**備註**: {rec['notes']}")
        if rec.get('review_notes'):
            st.write(f"**審核備註**: {rec['review_notes']}")
    
    with col3:
        rec_id = rec.get('id', index)
        
        # 審核按鈕（僅待審核狀態顯示）
        if rec['status'] == 'PENDING':
            if st.button("✅ 通過", key=f"approve_{rec_id}_{index}"):
                if update_recommendation_status(rec_id, "APPROVED"):
                    st.success("✅ 推薦已通過")
                    st.rerun()
            
            if st.button("❌ 拒絕", key=f"reject_{rec_id}_{index}"):
                if update_recommendation_status(rec_id, "REJECTED"):
                    st.success("❌ 推薦已拒絕")
                    st.rerun()
    
    # 顯示推薦內容
    st.markdown("**📋 推薦內容**")
    payload = rec.get('payload', {})
    
    if rec['recommendation_type'] == 'DYNAMIC_MENU':
        suggested_menu = payload.get('suggested_menu', [])
        if suggested_menu:
            menu_df = pd.DataFrame(suggested_menu)
            st.dataframe(menu_df, use_container_width=True)
    
    elif rec['recommendation_type'] == 'RESTOCK':
        restock_suggestions = payload.get('restock_suggestions', [])
        if restock_suggestions:
            restock_df = pd.DataFrame(restock_suggestions)
            st.dataframe(restock_df, use_container_width=True)

def show_dynamic_menu_display():
    """顯示動態菜單接收/顯示功能"""
    st.subheader("🎯 AI動態菜單")
    
    # 獲取已通過的動態菜單推薦
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            all_recommendations = st.session_state.api.get_ai_recommendations(status_filter="APPROVED")
        else:
            all_recommendations = get_mock_recommendations()
        
        approved_recommendations = [r for r in all_recommendations 
                                  if r['status'] == 'APPROVED' and r['recommendation_type'] == 'DYNAMIC_MENU']
    except Exception as e:
        st.error(f"❌ 獲取動態菜單失敗: {str(e)}")
        approved_recommendations = []
    
    if not approved_recommendations:
        st.info("📝 目前沒有已通過的動態菜單推薦")
        return
    
    # 選擇機台
    selected_machine = st.selectbox("選擇機台", ["1", "2", "3", "全部"])
    
    # 篩選適用的推薦
    applicable_recs = []
    for rec in approved_recommendations:
        if selected_machine == "全部" or selected_machine in rec['target_machine_ids']:
            applicable_recs.append(rec)
    
    if not applicable_recs:
        st.warning(f"機台 {selected_machine} 沒有適用的動態菜單推薦")
        return
    
    # 顯示動態菜單
    for rec in applicable_recs:
        with st.container():
            st.markdown(f"### 🤖 {rec['recommendation_id']}")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                payload = rec.get('payload', {})
                suggested_menu = payload.get('suggested_menu', [])
                
                if suggested_menu:
                    st.markdown("**推薦菜單配置**")
                    
                    # 創建美化的菜單顯示
                    for item in suggested_menu:
                        with st.container():
                            item_col1, item_col2, item_col3 = st.columns([2, 1, 1])
                            
                            with item_col1:
                                st.markdown(f"**🍽️ 餐點 {item['meal_id']}**")
                            
                            with item_col2:
                                st.markdown(f"**💰 NT$ {item['suggested_price']:.0f}**")
                            
                            with item_col3:
                                priority_color = {1: "🔴", 2: "🟡", 3: "🟢"}.get(item['priority'], "⚪")
                                st.markdown(f"**{priority_color} 優先級 {item['priority']}**")
                            
                            st.markdown("---")
            
            with col2:
                st.metric("信心分數", f"{rec.get('confidence_score', 0):.1%}")
                st.metric("AI版本", rec.get('ai_model_version', 'Unknown')[:10])
                
                # 應用到機台按鈕
                if st.button(f"🚀 應用到機台", key=f"apply_{rec['id']}"):
                    if apply_dynamic_menu_to_machine(selected_machine, rec):
                        st.success(f"✅ 動態菜單已應用到機台 {selected_machine}")
                    else:
                        st.error("❌ 應用失敗")

def show_push_notification_records():
    """顯示推播記錄"""
    st.subheader("📊 動態菜單推播記錄")
    
    # 日期範圍選擇
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    
    # 獲取推播記錄
    push_records = get_mock_push_records(start_date, end_date)
    
    if not push_records:
        st.info("📝 所選日期範圍內沒有推播記錄")
        return
    
    # 統計摘要
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總推播次數", len(push_records))
    with col2:
        success_count = len([r for r in push_records if r['status'] == 'SUCCESS'])
        st.metric("成功推播", success_count)
    with col3:
        failed_count = len([r for r in push_records if r['status'] == 'FAILED'])
        st.metric("失敗推播", failed_count)
    with col4:
        success_rate = (success_count / len(push_records)) * 100 if push_records else 0
        st.metric("成功率", f"{success_rate:.1f}%")
    
    st.markdown("---")
    
    # 詳細記錄表格
    st.subheader("📋 詳細推播記錄")
    
    # 轉換為DataFrame
    records_data = []
    for record in push_records:
        records_data.append({
            "推播ID": record['push_id'],
            "推薦ID": record['recommendation_id'],
            "目標機台": ", ".join(record['target_machines']),
            "推播時間": record['push_time'],
            "狀態": get_push_status_display(record['status']),
            "回應時間": f"{record['response_time_ms']}ms",
            "錯誤訊息": record.get('error_message', '-')
        })
    
    df = pd.DataFrame(records_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 推播詳細資訊
    st.subheader("🔍 推播詳細資訊")
    selected_record = st.selectbox(
        "選擇推播記錄查看詳情",
        push_records,
        format_func=lambda x: f"{x['push_id']} - {x['recommendation_id']}"
    )
    
    if selected_record:
        with st.expander("📄 推播詳細內容", expanded=True):
            st.json(selected_record)

def show_create_recommendation_form():
    """顯示創建推薦表單"""
    st.subheader("➕ 創建AI推薦")
    
    with st.form("create_ai_recommendation"):
        col1, col2 = st.columns(2)
        
        with col1:
            rec_id = st.text_input("推薦ID", value=f"AI-REC-{datetime.now().strftime('%Y%m%d')}-001")
            ai_model_version = st.text_input("AI模型版本", value="v2.1.3-dynamic-menu")
            rec_type = st.selectbox("推薦類型", ["DYNAMIC_MENU", "RESTOCK"])
            target_machines = st.multiselect("目標機台", ["1", "2", "3"], default=["1"])
        
        with col2:
            valid_from_date = st.date_input("有效開始日期", datetime.now().date())
            valid_from_time = st.time_input("有效開始時間", datetime.now().time())
            valid_until_date = st.date_input("有效結束日期", (datetime.now() + timedelta(hours=24)).date())
            valid_until_time = st.time_input("有效結束時間", (datetime.now() + timedelta(hours=24)).time())
            confidence_score = st.slider("信心分數", 0.0, 1.0, 0.85, 0.01)
            notes = st.text_area("備註", placeholder="推薦說明...")
        
        # 推薦內容配置
        st.markdown("**📋 推薦內容配置**")
        
        if rec_type == "DYNAMIC_MENU":
            st.markdown("**動態菜單配置**")
            
            # 簡化的菜單項目輸入
            menu_items = []
            for i in range(3):
                col_meal, col_price, col_priority = st.columns(3)
                with col_meal:
                    meal_id = st.text_input(f"餐點ID {i+1}", value=chr(65+i), key=f"meal_{i}")
                with col_price:
                    price = st.number_input(f"建議價格 {i+1}", value=80.0 + i*20, key=f"price_{i}")
                with col_priority:
                    priority = st.number_input(f"優先級 {i+1}", value=i+1, min_value=1, max_value=10, key=f"priority_{i}")
                
                if meal_id:
                    menu_items.append({
                        "meal_id": meal_id,
                        "suggested_price": price,
                        "priority": priority
                    })
        
        submitted = st.form_submit_button("🚀 創建推薦", type="primary")
        
        if submitted:
            if not rec_id or not target_machines:
                st.error("❌ 請填寫必填欄位")
            else:
                # 構建推薦數據
                recommendation_data = {
                    "recommendation_id": rec_id,
                    "ai_model_version": ai_model_version,
                    "target_machine_ids": [str(m) for m in target_machines],
                    "recommendation_type": rec_type,
                    "valid_from": f"{valid_from_date}T{valid_from_time}",
                    "valid_until": f"{valid_until_date}T{valid_until_time}",
                    "notes": notes,
                    "confidence_score": confidence_score
                }
                
                if rec_type == "DYNAMIC_MENU":
                    recommendation_data["payload"] = {
                        "suggested_menu": menu_items
                    }
                
                # 創建推薦
                if create_ai_recommendation(recommendation_data):
                    st.success("✅ AI推薦已成功創建！")
                    st.balloons()
                else:
                    st.error("❌ 創建推薦失敗")

# 輔助函數
def get_status_icon(status: str) -> str:
    """獲取狀態圖標"""
    icons = {
        "PENDING": "🟡",
        "APPROVED": "✅", 
        "REJECTED": "❌",
        "EXPIRED": "⏰"
    }
    return icons.get(status, "⚪")

def get_status_display(status: str) -> str:
    """獲取狀態顯示文字"""
    displays = {
        "PENDING": "🟡 待審核",
        "APPROVED": "✅ 已通過",
        "REJECTED": "❌ 已拒絕", 
        "EXPIRED": "⏰ 已過期"
    }
    return displays.get(status, status)

def get_push_status_display(status: str) -> str:
    """獲取推播狀態顯示"""
    displays = {
        "SUCCESS": "✅ 成功",
        "FAILED": "❌ 失敗",
        "PENDING": "🟡 處理中"
    }
    return displays.get(status, status)

def get_mock_recommendations() -> List[Dict]:
    """獲取模擬推薦數據"""
    return [
        {
            "id": 1,
            "recommendation_id": "AI-REC-20250823-001",
            "ai_model_version": "v2.1.3-dynamic-menu",
            "target_machine_ids": ["1", "2"],
            "recommendation_type": "DYNAMIC_MENU",
            "valid_from": "2025-08-23T00:00:00",
            "valid_until": "2025-08-23T23:59:59",
            "payload": {
                "suggested_menu": [
                    {"meal_id": "B", "suggested_price": 105.0, "priority": 1},
                    {"meal_id": "C", "suggested_price": 60.0, "priority": 2},
                    {"meal_id": "A", "suggested_price": 80.0, "priority": 3}
                ]
            },
            "notes": "根據近期陰雨天氣及B餐銷量上升趨勢，提高B餐優先級並微調價格。",
            "confidence_score": 0.85,
            "status": "PENDING",
            "created_at": "2025-08-23T15:27:29",
            "updated_at": "2025-08-23T15:27:29",
            "reviewed_by": None,
            "review_notes": None
        },
        {
            "id": 2,
            "recommendation_id": "AI-REC-20250823-002",
            "ai_model_version": "v1.5.2-restock-optimizer",
            "target_machine_ids": ["3"],
            "recommendation_type": "RESTOCK",
            "valid_from": "2025-08-23T08:00:00",
            "valid_until": "2025-08-23T18:00:00",
            "payload": {
                "restock_suggestions": [
                    {"meal_id": "A", "suggested_quantity": 15, "urgency_level": 3},
                    {"meal_id": "B", "suggested_quantity": 20, "urgency_level": 5}
                ]
            },
            "notes": "基於銷售預測，B餐需要緊急補貨",
            "confidence_score": 0.92,
            "status": "APPROVED",
            "created_at": "2025-08-23T14:30:00",
            "updated_at": "2025-08-23T15:00:00",
            "reviewed_by": "admin",
            "review_notes": "補貨建議合理，已通過"
        }
    ]

def get_mock_push_records(start_date, end_date) -> List[Dict]:
    """獲取模擬推播記錄"""
    return [
        {
            "push_id": "PUSH-20250823-001",
            "recommendation_id": "AI-REC-20250823-001",
            "target_machines": ["1", "2"],
            "push_time": "2025-08-23T15:30:00",
            "status": "SUCCESS",
            "response_time_ms": 245,
            "payload_size_bytes": 1024,
            "machine_responses": {
                "1": {"status": "ACK", "timestamp": "2025-08-23T15:30:01"},
                "2": {"status": "ACK", "timestamp": "2025-08-23T15:30:02"}
            }
        },
        {
            "push_id": "PUSH-20250823-002",
            "recommendation_id": "AI-REC-20250823-002",
            "target_machines": ["3"],
            "push_time": "2025-08-23T16:00:00",
            "status": "FAILED",
            "response_time_ms": 5000,
            "error_message": "Machine 3 connection timeout",
            "retry_count": 3
        }
    ]

def update_recommendation_status(rec_id: int, status: str) -> bool:
    """更新推薦狀態"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.update_recommendation_status(rec_id, status)
        else:
            # 模擬更新成功
            ui_logger.info(f"Mock update recommendation {rec_id} status to {status}")
            return True
    except Exception as e:
        st.error(f"❌ 更新狀態失敗: {str(e)}")
        return False

def create_ai_recommendation(recommendation_data: dict) -> bool:
    """創建AI推薦"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.create_ai_recommendation(recommendation_data)
        else:
            # 模擬創建成功
            ui_logger.info(f"Mock create AI recommendation: {recommendation_data['recommendation_id']}")
            return True
    except Exception as e:
        st.error(f"❌ 創建推薦失敗: {str(e)}")
        return False

def apply_dynamic_menu_to_machine(machine_id: str, recommendation: dict) -> bool:
    """應用動態菜單到機台"""
    try:
        # 這裡應該調用MQTT或API來推送菜單到機台
        ui_logger.info(f"Applying dynamic menu to machine {machine_id}: {recommendation['recommendation_id']}")
        
        # 記錄推播操作
        push_record = {
            "push_id": f"PUSH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{machine_id}",
            "recommendation_id": recommendation['recommendation_id'],
            "target_machines": [machine_id],
            "push_time": datetime.now().isoformat(),
            "status": "SUCCESS",
            "response_time_ms": 200
        }
        
        # 實際應用中應該保存到數據庫
        return True
    except Exception as e:
        ui_logger.error(f"Failed to apply dynamic menu to machine {machine_id}: {str(e)}")
        return False
