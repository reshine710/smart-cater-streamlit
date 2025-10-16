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
        if st.button("🔄 檢查AI狀態", key="ai_health_check_button"):
            health_status = check_ai_health()
            if health_status.get("status") == "ok":
                st.success("✅ AI系統運行正常")
                st.json(health_status)
            else:
                st.error("❌ AI系統異常")
                st.json(health_status)
    
    # 主要標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 推薦列表", "🎯 動態菜單", "📊 推播記錄", "➕ 創建推薦", "📈 交易數據"])
    
    with tab1:
        show_recommendations_list()
    
    with tab2:
        show_dynamic_menu_display()
    
    with tab3:
        show_push_notification_records()
    
    with tab4:
        show_create_recommendation_form()
    
    with tab5:
        show_transactional_data_analysis()

def check_ai_health() -> dict:
    """檢查AI系統健康狀態"""
    try:
        # 嘗試調用真實API
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.get_ai_health()
        else:
            return {"status": "error", "message": "API client not available"}
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
            ["全部", "PENDING", "IMPLEMENTED"],
            format_func=lambda x: {
                "全部": "全部狀態",
                "PENDING": "🟡 待審核",
                "IMPLEMENTED": "🚀 已實施",
            }.get(x, x),
            key="recommendations_status_filter_v2"
        )
    
    with col2:
        machine_filter = st.selectbox("機台篩選", ["全部", "1", "2", "3"], key="recommendations_machine_filter")
    
    with col3:
        if st.button("🔄 重新整理", key="recommendations_refresh_button"):
            # 清除所有可能的緩存狀態
            cache_keys_to_clear = [
                'ai_recommendations_cache',
                'ai_recommendations_data',
                'recommendations_data'
            ]
            for key in cache_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # 批量操作模式切換
    st.markdown("---")
    col_mode1, col_mode2 = st.columns([1, 4])
    with col_mode1:
        batch_mode = st.checkbox("🔧 批量操作模式", key="batch_mode_toggle", help="啟用批量選擇和更新機台菜單功能")
    with col_mode2:
        if batch_mode:
            st.info("💡 批量操作模式已啟用：您可以選擇多個AI推薦菜單項目，然後一次性更新到機台")
    
    # 獲取推薦數據
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            filter_status = None if status_filter == "全部" else status_filter
            filter_machine = None if machine_filter == "全部" else machine_filter
            
            # 強制重新獲取數據，不使用緩存
            ui_logger.debug(f"Fetching recommendations with status={filter_status}, machine={filter_machine}")
            recommendations = st.session_state.api.get_ai_recommendations(
                status_filter=filter_status, 
                machine_id=filter_machine
            )
            ui_logger.debug(f"Retrieved {len(recommendations)} recommendations")
            
            # 增強調試日誌 - 記錄API返回的原始數據結構
            api_logger.debug(f"Raw recommendations data structure: {[{k: v for k, v in rec.items() if k in ['id', 'backend_ref_id', 'recommendation_id']} for rec in recommendations]}")
            
        else:
            st.error("❌ API 客戶端不可用")
            recommendations = []
    except Exception as e:
        st.error(f"❌ 獲取推薦數據失敗: {str(e)}")
        api_logger.error(f"Failed to get recommendations: {str(e)}")
        recommendations = []
    
    st.write(f"顯示 {len(recommendations)} 個推薦")
    
    # 初始化批量選擇狀態
    if 'selected_recommendations' not in st.session_state:
        st.session_state.selected_recommendations = []
    
    # 批量操作控制面板
    if batch_mode:
        st.markdown("### 🔧 批量操作控制面板")
        col_control1, col_control2, col_control3 = st.columns(3)
        
        with col_control1:
            if st.button("✅ 全選", key="select_all_batch"):
                # 只選擇動態菜單類型的推薦
                dynamic_menu_recs = [rec for rec in recommendations if rec['recommendation_type'] == 'DYNAMIC_MENU']
                st.session_state.selected_recommendations = [rec['id'] for rec in dynamic_menu_recs]
                st.rerun()
        
        with col_control2:
            if st.button("❌ 清除選擇", key="clear_selection_batch"):
                st.session_state.selected_recommendations = []
                st.rerun()
        
        with col_control3:
            selected_count = len(st.session_state.selected_recommendations)
            st.metric("已選擇項目", selected_count)
        
        # 顯示已選擇的推薦摘要
        if selected_count > 0:
            st.markdown("**📋 已選擇的推薦摘要**")
            selected_recs = [rec for rec in recommendations if rec['id'] in st.session_state.selected_recommendations]
            
            # 收集所有菜單項目
            all_menu_items = []
            for rec in selected_recs:
                payload = rec.get('payload', {})
                suggested_menu = payload.get('suggested_menu', [])
                for item in suggested_menu:
                    all_menu_items.append({
                        'meal_id': item.get('meal_id'),
                        'suggested_price': item.get('suggested_price'),
                        'priority': item.get('priority'),
                        'recommendation_id': rec.get('recommendation_id')
                    })
            
            if all_menu_items:
                menu_df = pd.DataFrame(all_menu_items)
                st.dataframe(menu_df, width="stretch")
                
                # 機台選擇和更新按鈕
                st.markdown("**🎯 選擇目標機台並更新菜單**")
                col_machine, col_update = st.columns([2, 1])
                
                with col_machine:
                    target_machine = st.selectbox(
                        "選擇目標機台",
                        ["1", "2", "3"],
                        key="batch_target_machine",
                        help="選擇要更新菜單的機台"
                    )
                
                with col_update:
                    if st.button("🚀 批量更新機台菜單", key="batch_update_menu", type="primary"):
                        if batch_update_machine_menu(target_machine, all_menu_items):
                            st.success(f"✅ 成功更新機台 {target_machine} 的菜單！")
                            st.balloons()
                        else:
                            st.error("❌ 更新機台菜單失敗")
        
        st.markdown("---")
    
    # 顯示推薦列表
    for i, rec in enumerate(recommendations):
        # 調試日誌 - 記錄每個推薦的ID字段
        id_debug_info = {k: rec.get(k) for k in ['id', 'backend_ref_id', 'recommendation_id'] if k in rec}
        api_logger.debug(f"Recommendation {i} ID fields: {id_debug_info}")
        
        # 在批量模式下，為動態菜單推薦添加選擇框
        if batch_mode and rec['recommendation_type'] == 'DYNAMIC_MENU':
            _, col_expander = st.columns([1, 9]) # delete col_checkbox
            
            # with col_checkbox:
            #     is_selected = rec['id'] in st.session_state.selected_recommendations
            #     if st.checkbox(
            #         "選擇", 
            #         value=is_selected, 
            #         key=f"select_rec_{rec['id']}",
            #         help="選擇此推薦進行批量操作"
            #     ):
            #         if rec['id'] not in st.session_state.selected_recommendations:
            #             st.session_state.selected_recommendations.append(rec['id'])
            #     else:
            #         if rec['id'] in st.session_state.selected_recommendations:
            #             st.session_state.selected_recommendations.remove(rec['id'])
            
            with col_expander:
                with st.expander(f"{get_status_icon(rec['status'])} {rec['recommendation_id']} - {rec['recommendation_type']}", expanded=False):
                    show_recommendation_details(rec, i)
        else:
            with st.expander(f"{get_status_icon(rec['status'])} {rec['recommendation_id']} - {rec['recommendation_type']}", expanded=False):
                show_recommendation_details(rec, i)

def show_recommendation_details(rec: Dict, index: int):
    """顯示推薦詳細資訊"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.write(f"**AI模型版本**: {rec.get('ai_model_version', 'Unknown')}")
        st.write(f"**目標機台**: {', '.join(rec.get('target_machine_ids', []))}")
        confidence_score = rec.get('confidence_score')
        if confidence_score is not None:
            st.write(f"**信心分數**: {confidence_score:.2%}")
        else:
            st.write("**信心分數**: N/A")
        st.write(f"**有效期間**: {rec.get('valid_from', 'Unknown')} ~ {rec.get('valid_until', 'Unknown')}")
    
    with col2:
        st.write(f"**狀態**: {get_status_display(rec['status'])}")
        st.write(f"**創建時間**: {rec.get('created_at', 'Unknown')}")
        if rec.get('notes'):
            st.write(f"**備註**: {rec['notes']}")
        if rec.get('review_notes'):
            st.write(f"**審核備註**: {rec['review_notes']}")
    
    with col3:
        # 修正ID映射問題 - 使用正確的後端ID順序
        rec_id = None
        id_extraction_log = []
        
        # 修正：backend_ref_id 是正確的後端API ID，應該優先使用
        for id_field in ['backend_ref_id', 'id', 'recommendation_id']:
            if id_field in rec and rec[id_field] is not None:
                rec_id = rec[id_field]
                id_extraction_log.append(f"Found {id_field}: {rec_id}")
                break
            else:
                id_extraction_log.append(f"Missing/None {id_field}")
        
        # 如果仍然沒有找到有效的ID，記錄錯誤並跳過操作按鈕
        if rec_id is None:
            st.error("❌ 無效的推薦ID，無法執行操作")
            ui_logger.error(f"No valid ID found for recommendation: {rec}")
            return
        
        # 根據狀態顯示不同的操作按鈕
        current_status = rec['status']
        
        if current_status == 'PENDING':
            # 待審核狀態：顯示接受/拒絕按鈕
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ 通過", key=f"approve_{rec_id}_{index}", width="stretch"):
                    # 先更新狀態為APPROVED
                    if update_recommendation_status(rec_id, "APPROVED"):
                        if update_recommendation_status(rec_id, "IMPLEMENTED"):
                                st.success("✅ 推薦已通過並實施")
                        else:
                            st.success("✅ 推薦已通過")

                        # TODO: 實施選中的菜單項目，尚未完成
                        # 檢查是否是動態菜單推薦且有選中的菜單項目
                        if (rec['recommendation_type'] == 'DYNAMIC_MENU' and 
                            f'selected_menu_items_{rec_id}' in st.session_state and 
                            st.session_state[f'selected_menu_items_{rec_id}']):
                            
                            print(f"selected_menu_items_{rec_id}: {st.session_state[f'selected_menu_items_{rec_id}']}")
                            # 實施選中的菜單項目
                            if implement_selected_menu_items(rec, rec_id):
                                # 更新推薦狀態為已實施
                                if update_recommendation_status(rec_id, "IMPLEMENTED"):
                                    st.success("✅ 推薦已通過並實施選中的菜單項目")
                                else:
                                    st.success("✅ 推薦已通過，菜單項目已實施")
                            else:
                                st.success("✅ 推薦已通過")
                        else:
                            # 非動態菜單推薦或沒有選中項目，只更新狀態
                            if update_recommendation_status(rec_id, "IMPLEMENTED"):
                                st.success("✅ 推薦已通過並實施")
                            else:
                                st.success("✅ 推薦已通過")
                        
                        # 清除所有可能的緩存狀態
                        cache_keys_to_clear = [
                            'ai_recommendations_cache',
                            'ai_recommendations_data',
                            'recommendations_data'
                        ]
                        for key in cache_keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        # 添加短暫延遲確保後端數據更新
                        import time
                        time.sleep(0.5)
                        # 強制刷新頁面
                        st.rerun()
            with col_btn2:
                if st.button("❌ 拒絕", key=f"reject_{rec_id}_{index}", width="stretch"):
                    if update_recommendation_status(rec_id, "REJECTED"):
                        st.success("❌ 推薦已拒絕")
                        # 清除所有可能的緩存狀態
                        cache_keys_to_clear = [
                            'ai_recommendations_cache',
                            'ai_recommendations_data',
                            'recommendations_data'
                        ]
                        for key in cache_keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        # 強制刷新頁面
                        st.rerun()
        
        elif current_status == 'APPROVED':
            # 已通過狀態：可以實施或撤回
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚀 實施", key=f"implement_{rec_id}_{index}", width="stretch", type="primary"):
                    if update_recommendation_status(rec_id, "IMPLEMENTED"):
                        st.success("🚀 推薦已實施")
                        # 清除所有可能的緩存狀態
                        cache_keys_to_clear = [
                            'ai_recommendations_cache',
                            'ai_recommendations_data',
                            'recommendations_data'
                        ]
                        for key in cache_keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        # 強制刷新頁面
                        st.rerun()
            with col_btn2:
                if st.button("↩️ 撤回", key=f"revoke_{rec_id}_{index}", width="stretch"):
                    if update_recommendation_status(rec_id, "PENDING"):
                        st.success("↩️ 推薦已撤回至待審核")
                        # 清除所有可能的緩存狀態
                        cache_keys_to_clear = [
                            'ai_recommendations_cache',
                            'ai_recommendations_data',
                            'recommendations_data'
                        ]
                        for key in cache_keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        # 強制刷新頁面
                        st.rerun()
        
        elif current_status == 'IMPLEMENTED':
            # 已實施狀態：顯示狀態信息，不可修改
            st.info("🚀 此推薦已成功實施，無法修改")
        
        elif current_status in ['REJECTED', 'EXPIRED']:
            # 已拒絕或已過期：顯示狀態信息
            status_msg = "❌ 此推薦已被拒絕" if current_status == 'REJECTED' else "⏰ 此推薦已過期"
            st.warning(status_msg)
        
        # 刪除按鈕（除了已實施的推薦，其他都可以刪除）
        if current_status != 'IMPLEMENTED':
            st.markdown("---")
            confirm_key = f"confirm_delete_{rec_id}_{index}"
            
            # 檢查是否處於確認狀態
            if st.session_state.get(confirm_key, False):
                # 顯示確認對話框
                st.warning("⚠️ 確定要刪除此推薦嗎？此操作無法復原。")
                col_confirm1, col_confirm2 = st.columns(2)
                with col_confirm1:
                    if st.button("⚠️ 確認刪除", key=f"confirm_yes_{rec_id}_{index}", type="primary"):
                        if delete_recommendation(rec_id):
                            st.success("🗑️ 推薦已刪除")
                            # 清除確認狀態
                            if confirm_key in st.session_state:
                                del st.session_state[confirm_key]
                            st.rerun()
                        else:
                            # 刪除失敗，清除確認狀態
                            if confirm_key in st.session_state:
                                del st.session_state[confirm_key]
                with col_confirm2:
                    if st.button("❌ 取消", key=f"confirm_no_{rec_id}_{index}"):
                        st.session_state[confirm_key] = False
                        st.rerun()
            else:
                # 顯示刪除按鈕
                if st.button("🗑️ 刪除", key=f"delete_{rec_id}_{index}", type="secondary"):
                    st.session_state[confirm_key] = True
                    st.rerun()
    
    # 顯示推薦內容
    st.markdown("**📋 推薦內容**")
    payload = rec.get('payload', {})
    
    if rec['recommendation_type'] == 'DYNAMIC_MENU':
        suggested_menu = payload.get('suggested_menu', [])
        if suggested_menu:
            # 初始化選擇狀態
            if f'selected_menu_items_{rec_id}' not in st.session_state:
                st.session_state[f'selected_menu_items_{rec_id}'] = []
            
            # 獲取菜單項目名稱映射
            menu_name_mapping = get_menu_item_names()
            
            # 條列式顯示推薦菜單
            st.markdown("**🍽️ 推薦菜單項目**")
            for i, item in enumerate(suggested_menu):
                meal_id = item.get('meal_id', '')
                meal_name = menu_name_mapping.get(str(meal_id), f"餐點 {meal_id}")
                suggested_price = item.get('suggested_price', 0)
                priority = item.get('priority', 1)
                restock_quantity = item.get('restock_quantity', 0)
                restock_date = item.get('restock_date', '')
                
                # 創建選擇框和菜單項目顯示
                col_check, col_content = st.columns([1, 9]) # delete col_check
                
                with col_check:
                    is_selected = i in st.session_state[f'selected_menu_items_{rec_id}']
                    if st.checkbox(
                        "選擇", 
                        value=is_selected, 
                        key=f"select_menu_item_{rec_id}_{i}",
                        help=f"選擇 {meal_name}"
                    ):
                        if i not in st.session_state[f'selected_menu_items_{rec_id}']:
                            st.session_state[f'selected_menu_items_{rec_id}'].append(i)
                    else:
                        if i in st.session_state[f'selected_menu_items_{rec_id}']:
                            st.session_state[f'selected_menu_items_{rec_id}'].remove(i)
                
                with col_content:
                    # 顯示菜單項目資訊
                    st.markdown(f"**🍽️ {meal_name}**")
                    
                    # 顯示詳細資訊
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.caption(f"💰 建議價格: NT$ {suggested_price:.0f}")
                    
                    with col_info2:
                        priority_icon = {1: "🔴", 2: "🟡", 3: "🟢"}.get(priority, "⚪")
                        st.caption(f"{priority_icon} 優先級: {priority}")
                    
                    with col_info3:
                        if restock_quantity and restock_date:
                            st.caption(f"📦 補貨: {restock_quantity} 份 @ {restock_date}")
                        else:
                            st.caption("📦 補貨: 無")
                    
                    st.markdown("---")
            
            # 顯示選擇摘要
            selected_count = len(st.session_state[f'selected_menu_items_{rec_id}'])
            if selected_count > 0:
                st.info(f"✅ 已選擇 {selected_count} 個菜單項目")
                
                # 顯示已選擇的項目
                selected_items = []
                for i in st.session_state[f'selected_menu_items_{rec_id}']:
                    if i < len(suggested_menu):
                        item = suggested_menu[i]
                        meal_id = item.get('meal_id', '')
                        meal_name = menu_name_mapping.get(str(meal_id), f"餐點 {meal_id}")
                        selected_items.append(meal_name)
                
                if selected_items:
                    st.markdown("**已選擇的項目**: " + ", ".join(selected_items))
    
    elif rec['recommendation_type'] == 'RESTOCK':
        restock_suggestions = payload.get('restock_suggestions', [])
        if restock_suggestions:
            restock_df = pd.DataFrame(restock_suggestions)
            st.dataframe(restock_df, width="stretch")

def show_dynamic_menu_display():
    """顯示動態菜單接收/顯示功能"""
    st.subheader("🎯 AI動態菜單")
    
    # 獲取已通過和已實施的動態菜單推薦
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            # 獲取已通過的推薦
            ui_logger.debug("Fetching approved recommendations for dynamic menu")
            approved_recs = st.session_state.api.get_ai_recommendations(status_filter="APPROVED")
            ui_logger.debug(f"Retrieved {len(approved_recs)} approved recommendations")
            
            # 獲取已實施的推薦
            ui_logger.debug("Fetching implemented recommendations for dynamic menu")
            implemented_recs = st.session_state.api.get_ai_recommendations(status_filter="IMPLEMENTED")
            ui_logger.debug(f"Retrieved {len(implemented_recs)} implemented recommendations")
            
            # 合併並篩選出動態菜單類型的推薦
            all_recommendations = approved_recs + implemented_recs
            dynamic_menu_recommendations = [r for r in all_recommendations 
                                          if r['recommendation_type'] == 'DYNAMIC_MENU']
            ui_logger.debug(f"Total dynamic menu recommendations: {len(dynamic_menu_recommendations)} (Approved: {len([r for r in approved_recs if r['recommendation_type'] == 'DYNAMIC_MENU'])}, Implemented: {len([r for r in implemented_recs if r['recommendation_type'] == 'DYNAMIC_MENU'])})")
        else:
            st.error("❌ API 客戶端不可用")
            dynamic_menu_recommendations = []
    except Exception as e:
        st.error(f"❌ 獲取動態菜單失敗: {str(e)}")
        ui_logger.error(f"Failed to fetch dynamic menu recommendations: {str(e)}")
        dynamic_menu_recommendations = []
    
    if not dynamic_menu_recommendations:
        st.info("📝 目前沒有已通過或已實施的動態菜單推薦")
        return
    
    # 選擇機台
    machine_options = ["全部"]
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            machines_data = st.session_state.api.get_machines()
            if machines_data:
                for machine in machines_data:
                    machine_code = machine.get('machine_code', f"ID-{machine.get('id', 'Unknown')}")
                    machine_name = machine.get('name', 'Unknown')
                    option_text = f"{machine_code} - {machine_name}"
                    machine_options.append(option_text)
                ui_logger.debug(f"Machine options for filter: {machine_options}")
            else:
                machine_options.extend(["1", "2", "3"])
        else:
            machine_options.extend(["1", "2", "3"])
    except Exception as e:
        machine_options.extend(["1", "2", "3"])
        ui_logger.warning(f"Failed to get machines for filter: {str(e)}")
    
    selected_machine = st.selectbox("選擇機台", machine_options, key="dynamic_menu_machine_select")
    
    # 篩選適用的推薦
    applicable_recs = []
    for rec in dynamic_menu_recommendations:
        if selected_machine == "全部":
            applicable_recs.append(rec)
        else:
            # 提取選中的機台代碼
            selected_machine_code = selected_machine.split(" - ")[0] if " - " in selected_machine else selected_machine
            target_machine_ids = rec.get('target_machine_ids', [])
            
            # 檢查選中的機台代碼是否在目標機台列表中
            if selected_machine_code in target_machine_ids:
                applicable_recs.append(rec)
    
    if not applicable_recs:
        st.warning(f"機台 {selected_machine} 沒有適用的動態菜單推薦")
        return
    
    # 顯示動態菜單統計資訊
    approved_count = len([r for r in applicable_recs if r.get('status') == 'APPROVED'])
    implemented_count = len([r for r in applicable_recs if r.get('status') == 'IMPLEMENTED'])
    st.info(f"📊 找到 {len(applicable_recs)} 個動態菜單推薦 (已通過: {approved_count}, 已實施: {implemented_count})")
    
    # 顯示動態菜單
    for i, rec in enumerate(applicable_recs, 1):
        with st.container():
            st.markdown(f"### 🤖 {rec.get('recommendation_id', f'推薦 {i}')}")
            
            # 顯示推薦詳細資訊
            col_status, col_date, col_machines = st.columns([1, 2, 2])
            with col_status:
                status = rec.get('status', 'UNKNOWN')
                if status == 'APPROVED':
                    st.warning(f"🟡 {status}")
                elif status == 'IMPLEMENTED':
                    st.success(f"✅ {status}")
                else:
                    st.info(f"ℹ️ {status}")
            with col_date:
                st.write(f"**創建時間**: {rec.get('created_at', 'N/A')[:19] if rec.get('created_at') else 'N/A'}")
            with col_machines:
                target_machines = rec.get('target_machine_ids', [])
                st.write(f"**目標機台**: {', '.join(map(str, target_machines)) if target_machines else 'N/A'}")
            
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
                                # 顯示補貨資訊（如果有）
                                if 'restock_quantity' in item and 'restock_date' in item:
                                    st.caption(f"📦 補貨: {item['restock_quantity']} 份 @ {item['restock_date']}")
                            
                            with item_col2:
                                st.markdown(f"**💰 NT$ {item['suggested_price']:.0f}**")
                            
                            with item_col3:
                                priority_color = {1: "🔴", 2: "🟡", 3: "🟢"}.get(item['priority'], "⚪")
                                st.markdown(f"**{priority_color} 優先級 {item['priority']}**")
                            
                            st.markdown("---")
            
            with col2:
                confidence_score = rec.get('confidence_score')
                if confidence_score is not None:
                    st.metric("信心分數", f"{confidence_score:.1%}")
                else:
                    st.metric("信心分數", "N/A")
                st.metric("AI版本", rec.get('ai_model_version', 'Unknown')[:10])
                
                # 應用到機台按鈕
                if st.button(f"🚀 應用到機台", key=f"apply_{rec['id']}_{i}"):
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
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=7), key="push_records_start_date")
    with col2:
        end_date = st.date_input("結束日期", datetime.now(), key="push_records_end_date")
    
    # 獲取推播記錄
    push_records = get_push_records(start_date, end_date)
    
    # 如果沒有記錄，創建一些示例數據來演示功能
    if not push_records:
        # 創建示例推播記錄
        sample_records = [
            {
                "push_id": f"PUSH-{datetime.now().strftime('%Y%m%d%H%M%S')}-VM001",
                "recommendation_id": "AI-REC-20251004-001",
                "target_machines": ["VM001"],
                "push_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                "status": "SUCCESS",
                "response_time_ms": 250,
                "machine_code": "VM001",
                "menu_items_count": 3
            },
            {
                "push_id": f"PUSH-{(datetime.now() - timedelta(hours=1)).strftime('%Y%m%d%H%M%S')}-VM002",
                "recommendation_id": "AI-REC-20251004-002", 
                "target_machines": ["VM002"],
                "push_time": (datetime.now() - timedelta(hours=1)).isoformat(),
                "status": "SUCCESS",
                "response_time_ms": 180,
                "machine_code": "VM002",
                "menu_items_count": 2
            },
            {
                "push_id": f"PUSH-{(datetime.now() - timedelta(minutes=30)).strftime('%Y%m%d%H%M%S')}-VM003",
                "recommendation_id": "AI-REC-20251004-003",
                "target_machines": ["VM003"],
                "push_time": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "status": "FAILED",
                "response_time_ms": 0,
                "error_message": "MQTT 連接超時",
                "machine_code": "VM003",
                "menu_items_count": 4
            }
        ]
        
        # 初始化 session state 中的推播記錄
        if 'push_records' not in st.session_state:
            st.session_state.push_records = sample_records
            push_records = sample_records
        else:
            push_records = get_push_records(start_date, end_date)
    
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
        # 格式化推播時間
        try:
            push_time = datetime.fromisoformat(record['push_time'].replace('Z', '+00:00'))
            formatted_time = push_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = record['push_time']
        
        records_data.append({
            "推播ID": record['push_id'],
            "推薦ID": record['recommendation_id'],
            "目標機台": record.get('machine_code', ', '.join(record['target_machines'])),
            "推播時間": formatted_time,
            "狀態": get_push_status_display(record['status']),
            "回應時間": f"{record['response_time_ms']}ms",
            "菜單項目數": record.get('menu_items_count', '-'),
            "錯誤訊息": record.get('error_message', '-')
        })
    
    df = pd.DataFrame(records_data)
    
    # 添加刷新按鈕
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 刷新記錄", key="refresh_push_records"):
            st.rerun()
    
    with col2:
        st.caption(f"顯示 {len(push_records)} 條推播記錄")
    
    st.dataframe(df, width="stretch", hide_index=True)
    
    # 推播詳細資訊
    st.subheader("🔍 推播詳細資訊")
    selected_record = st.selectbox(
        "選擇推播記錄查看詳情",
        push_records,
        format_func=lambda x: f"{x['push_id']} - {x['recommendation_id']}",
        key="push_record_select"
    )
    
    if selected_record:
        with st.expander("📄 推播詳細內容", expanded=True):
            st.json(selected_record)

def show_create_recommendation_form():
    """顯示創建推薦表單"""
    st.subheader("➕ 創建AI推薦")
    
    # 初始化菜單項目數量（在表單外部）
    if 'menu_item_count' not in st.session_state:
        st.session_state.menu_item_count = 3
    
    # 菜單項目控制按鈕（在表單外部）
    st.markdown("**🍽️ 菜單項目配置**")
    col_add, col_remove, col_info = st.columns([1, 1, 2])
    
    with col_add:
        if st.button("➕ 增加項目", key="add_menu_item", help="增加一個菜單項目"):
            st.session_state.menu_item_count += 1
            st.rerun()
    
    with col_remove:
        if st.session_state.menu_item_count > 1:
            if st.button("➖ 減少項目", key="remove_menu_item", help="減少一個菜單項目"):
                st.session_state.menu_item_count -= 1
                st.rerun()
        else:
            st.button("➖ 減少項目", key="remove_menu_item_disabled", disabled=True, help="至少需要一個菜單項目")
    
    with col_info:
        st.info(f"目前有 {st.session_state.menu_item_count} 個菜單項目")
    
    st.markdown("---")
    
    with st.form("create_ai_recommendation"):
        col1, col2 = st.columns(2)
        
        with col1:
            rec_id = st.text_input("推薦ID", value=f"AI-REC-{datetime.now().strftime('%Y%m%d')}-001")
            ai_model_version = st.text_input("AI模型版本", value="v2.1.3-dynamic-menu")
            rec_type = st.selectbox("推薦類型", ["DYNAMIC_MENU", "RESTOCK"], key="recommendation_type_select")
            
            # 獲取實際機台列表
            available_machines = []
            try:
                if hasattr(st.session_state, 'api') and st.session_state.api:
                    machines_data = st.session_state.api.get_machines()
                    if machines_data:
                        # 創建機台選項，格式為 "代碼 - 名稱"
                        available_machines = []
                        for machine in machines_data:
                            machine_code = machine.get('machine_code', f"ID-{machine.get('id', 'Unknown')}")
                            machine_name = machine.get('name', 'Unknown')
                            option_text = f"{machine_code} - {machine_name}"
                            available_machines.append(option_text)
                        ui_logger.debug(f"Available machines: {available_machines}")
                    else:
                        # 如果無法獲取機台列表，使用預設選項
                        available_machines = ["1", "2", "3"]
                        st.warning("⚠️ 無法獲取機台列表，使用預設選項")
                else:
                    available_machines = ["1", "2", "3"]
                    st.warning("⚠️ API 不可用，使用預設選項")
            except Exception as e:
                available_machines = ["1", "2", "3"]
                st.warning(f"⚠️ 獲取機台列表失敗: {str(e)}，使用預設選項")
            
            target_machines = st.multiselect(
                "目標機台", 
                available_machines, 
                default=available_machines[:1] if available_machines else ["1"],
                help="選擇要應用推薦的機台"
            )
        
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
            
            # 獲取現有菜單項目
            available_menu_items = []
            try:
                if hasattr(st.session_state, 'api') and st.session_state.api:
                    menu_data = st.session_state.api.get_menu_items()
                    if menu_data and 'items' in menu_data:
                        available_menu_items = menu_data['items']
                    elif isinstance(menu_data, list):
                        available_menu_items = menu_data
            except Exception as e:
                st.warning(f"無法獲取菜單項目: {str(e)}")
            
            # 動態菜單項目輸入（包含補貨資訊）
            
            # 動態生成菜單項目輸入表單
            menu_items = []
            for i in range(st.session_state.menu_item_count):
                st.markdown(f"**餐點 {i+1}**")
                col_meal, col_price, col_priority = st.columns(3)
                
                with col_meal:
                    if available_menu_items:
                        # 創建選項列表，格式為 "ID - 名稱"
                        menu_options = []
                        menu_option_map = {}
                        
                        for item in available_menu_items:
                            item_id = str(item.get('id', ''))
                            item_name = item.get('name', 'Unknown')
                            option_text = f"{item_id} - {item_name}"
                            menu_options.append(option_text)
                            menu_option_map[option_text] = item_id
                        
                        # 預設選擇第一個選項
                        default_index = i if i < len(menu_options) else 0
                        
                        selected_option = st.selectbox(
                            f"選擇餐點", 
                            options=menu_options,
                            index=default_index,
                            key=f"meal_{i}",
                            help="從現有菜單項目中選擇"
                        )
                        
                        # 從選項中提取餐點ID
                        meal_id = menu_option_map.get(selected_option, chr(65+i))
                    else:
                        # 如果無法獲取菜單項目，使用文字輸入
                        meal_id = st.text_input(f"餐點ID", value=chr(65+i), key=f"meal_{i}")
                
                with col_price:
                    price = st.number_input(f"建議價格", value=80.0 + i*20, step=5.0, key=f"price_{i}")
                
                with col_priority:
                    priority = st.number_input(f"優先級", value=i+1, min_value=1, max_value=10, key=f"priority_{i}")
                
                # 補貨資訊
                col_quantity, col_date = st.columns(2)
                with col_quantity:
                    restock_quantity = st.number_input(f"補貨數量", value=3+i, min_value=0, key=f"restock_qty_{i}")
                with col_date:
                    restock_date = st.date_input(f"補貨日期", value=datetime.now().date() + timedelta(days=i*5), key=f"restock_date_{i}")
                
                if meal_id:
                    menu_items.append({
                        "meal_id": meal_id,
                        "suggested_price": price,
                        "priority": priority,
                        "restock_quantity": restock_quantity,
                        "restock_date": restock_date.strftime("%Y/%m/%d")
                    })
                
                st.markdown("---")
        
        submitted = st.form_submit_button("🚀 創建推薦", type="primary")
        
        if submitted:
            if not rec_id or not target_machines:
                st.error("❌ 請填寫必填欄位")
            else:
                # 提取機台代碼（從 "代碼 - 名稱" 格式中提取）
                machine_codes = []
                for machine_option in target_machines:
                    if " - " in machine_option:
                        # 提取代碼部分
                        machine_code = machine_option.split(" - ")[0]
                        machine_codes.append(machine_code)
                    else:
                        # 如果沒有 " - " 分隔符，直接使用原值
                        machine_codes.append(machine_option)
                
                # 構建推薦數據
                recommendation_data = {
                    "recommendation_id": rec_id,
                    "ai_model_version": ai_model_version,
                    "target_machine_ids": machine_codes,
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
        "IMPLEMENTED": "🚀",
        "REJECTED": "❌",
        "EXPIRED": "⏰"
    }
    return icons.get(status, "⚪")

def get_status_display(status: str) -> str:
    """獲取狀態顯示文字"""
    displays = {
        "PENDING": "🟡 待審核",
        "APPROVED": "✅ 已通過",
        "IMPLEMENTED": "🚀 已實施",
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


def update_recommendation_status(rec_id: int, status: str, review_notes: str = None) -> bool:
    """更新推薦狀態"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            # 獲取當前使用者名稱作為審核者
            reviewer = st.session_state.get('username', 'admin')
            return st.session_state.api.update_recommendation_status(
                rec_id, status, review_notes, reviewer
            )
        else:
            st.error("❌ API 客戶端不可用")
            return False
    except Exception as e:
        st.error(f"❌ 更新狀態失敗: {str(e)}")
        api_logger.error(f"Failed to update recommendation status: {str(e)}")
        return False

def create_ai_recommendation(recommendation_data: dict) -> bool:
    """創建AI推薦"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.create_ai_recommendation(recommendation_data)
        else:
            st.error("❌ API 客戶端不可用")
            return False
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
            "response_time_ms": 200,
            "machine_code": machine_id,
            "menu_items_count": len(recommendation.get('payload', {}).get('suggested_menu', []))
        }
        
        # 保存推播記錄到 session state
        if 'push_records' not in st.session_state:
            st.session_state.push_records = []
        st.session_state.push_records.append(push_record)
        
        ui_logger.info(f"Push record saved: {push_record['push_id']}")
        return True
    except Exception as e:
        # 記錄失敗的推播
        push_record = {
            "push_id": f"PUSH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{machine_id}",
            "recommendation_id": recommendation['recommendation_id'],
            "target_machines": [machine_id],
            "push_time": datetime.now().isoformat(),
            "status": "FAILED",
            "response_time_ms": 0,
            "error_message": str(e),
            "machine_code": machine_id,
            "menu_items_count": 0
        }
        
        if 'push_records' not in st.session_state:
            st.session_state.push_records = []
        st.session_state.push_records.append(push_record)
        
        ui_logger.error(f"Failed to apply dynamic menu to machine {machine_id}: {str(e)}")
        return False

def get_push_records(start_date, end_date):
    """獲取推播記錄"""
    try:
        # 從 session state 獲取推播記錄
        all_records = st.session_state.get('push_records', [])
        
        # 過濾日期範圍
        filtered_records = []
        for record in all_records:
            try:
                # 解析推播時間
                push_time = datetime.fromisoformat(record['push_time'].replace('Z', '+00:00'))
                push_date = push_time.date()
                
                # 檢查是否在日期範圍內
                if start_date <= push_date <= end_date:
                    filtered_records.append(record)
            except Exception as e:
                ui_logger.warning(f"Failed to parse push time for record {record.get('push_id', 'unknown')}: {e}")
                continue
        
        # 按時間排序（最新的在前）
        filtered_records.sort(key=lambda x: x['push_time'], reverse=True)
        
        ui_logger.debug(f"Retrieved {len(filtered_records)} push records for date range {start_date} to {end_date}")
        return filtered_records
        
    except Exception as e:
        ui_logger.error(f"Failed to get push records: {str(e)}")
        return []

def delete_recommendation(rec_id: int) -> bool:
    """刪除AI推薦"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            return st.session_state.api.delete_ai_recommendation(rec_id)
        else:
            st.error("❌ API 客戶端不可用")
            return False
    except Exception as e:
        st.error(f"❌ 刪除推薦失敗: {str(e)}")
        return False

def show_transactional_data_analysis():
    """顯示交易數據分析"""
    st.subheader("📈 交易數據分析")
    st.markdown("此功能用於AI模型訓練和分析，提供歷史交易數據查詢。")
    
    # 查詢參數
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "開始日期", 
            value=datetime.now().date() - timedelta(days=7),
            key="transactional_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "結束日期", 
            value=datetime.now().date(),
            key="transactional_end_date"
        )
    
    with col3:
        machine_filter = st.selectbox(
            "機台篩選", 
            ["全部", "1", "2", "3"],
            help="選擇特定機台或查看全部機台數據",
            key="transactional_machine_filter"
        )
    
    # 查詢限制
    col4, col5 = st.columns(2)
    with col4:
        limit = st.number_input("查詢筆數限制", min_value=1, max_value=1000, value=100, key="transactional_limit")
    
    with col5:
        skip = st.number_input("跳過筆數", min_value=0, value=0, key="transactional_skip")
    
    # 查詢按鈕
    if st.button("🔍 查詢交易數據", type="primary", key="transactional_query_button"):
        try:
            # 格式化日期
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            machine_id = None if machine_filter == "全部" else machine_filter
            
            # 獲取交易數據
            if hasattr(st.session_state, 'api') and st.session_state.api:
                transactional_data = st.session_state.api.get_transactional_data(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    machine_id=machine_id,
                    limit=limit,
                    skip=skip
                )
            else:
                st.error("❌ API 客戶端不可用")
                transactional_data = []
            
            if transactional_data:
                st.success(f"✅ 成功獲取 {len(transactional_data)} 筆交易數據")
                
                # 顯示數據統計
                st.markdown("### 📊 數據統計")
                col1, col2, col3, col4 = st.columns(4)
                
                # 計算統計數據
                total_transactions = len(transactional_data)
                if transactional_data:
                    total_revenue = sum(float(t.get('amount', 0)) for t in transactional_data)
                    unique_machines = len(set(str(t.get('machine_id', '')) for t in transactional_data))
                    unique_products = len(set(str(t.get('product_id', '')) for t in transactional_data))
                else:
                    total_revenue = 0
                    unique_machines = 0
                    unique_products = 0
                
                with col1:
                    st.metric("總交易筆數", total_transactions)
                
                with col2:
                    st.metric("總收入", f"${total_revenue:.2f}")
                
                with col3:
                    st.metric("涉及機台數", unique_machines)
                
                with col4:
                    st.metric("商品種類數", unique_products)
                
                # 顯示詳細數據表格
                st.markdown("### 📋 詳細交易記錄")
                if transactional_data:
                    df = pd.DataFrame(transactional_data)
                    st.dataframe(df, width="stretch")
                    
                    # 提供下載功能
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"transactional_data_{start_date_str}_to_{end_date_str}.csv",
                        mime="text/csv",
                        key="transactional_download_csv"
                    )
                else:
                    st.info("📝 查詢期間內沒有交易數據")
            else:
                st.warning("⚠️ 未找到符合條件的交易數據")
                
        except Exception as e:
            st.error(f"❌ 查詢交易數據失敗: {str(e)}")
            api_logger.error(f"Failed to query transactional data: {str(e)}")

def batch_update_machine_menu(machine_id: str, menu_items: List[Dict]) -> bool:
    """批量更新機台菜單"""
    try:
        if not hasattr(st.session_state, 'api') or not st.session_state.api:
            st.error("❌ API 客戶端不可用")
            return False
        
        # 提取菜單項目ID和顯示順序
        menu_item_ids = []
        display_orders = []
        
        for i, item in enumerate(menu_items, 1):
            # 從meal_id中提取數字ID，如果meal_id是字符串則嘗試轉換
            meal_id = item.get('meal_id', '')
            try:
                # 如果meal_id是純數字字符串，直接轉換
                if meal_id.isdigit():
                    menu_item_ids.append(int(meal_id))
                else:
                    # 如果是字母開頭（如A, B, C），轉換為數字
                    if meal_id and meal_id[0].isalpha():
                        menu_item_ids.append(ord(meal_id[0]) - ord('A') + 1)
                    else:
                        # 默認使用索引+1
                        menu_item_ids.append(i)
            except (ValueError, TypeError):
                # 如果轉換失敗，使用索引+1
                menu_item_ids.append(i)
            
            display_orders.append(i)
        
        ui_logger.info(f"Batch updating machine {machine_id} with menu items: {menu_item_ids}, display orders: {display_orders}")
        
        # 調用API更新機台菜單
        result = st.session_state.api.update_machine_menu_items(
            machine_id=int(machine_id),
            menu_item_ids=menu_item_ids,
            display_orders=display_orders
        )
        
        if result and result.get('success'):
            ui_logger.info(f"Successfully updated machine {machine_id} menu with {len(menu_items)} items")
            
            # 顯示更新結果
            updated_items = result.get('data', {}).get('updated_menu_items', [])
            if updated_items:
                st.markdown("**📋 更新結果**")
                result_df = pd.DataFrame(updated_items)
                st.dataframe(result_df, width="stretch")
            
            return True
        else:
            ui_logger.error(f"Failed to update machine {machine_id} menu")
            return False
            
    except Exception as e:
        ui_logger.error(f"Error in batch_update_machine_menu: {str(e)}")
        st.error(f"❌ 批量更新機台菜單時發生錯誤: {str(e)}")
        return False

def get_menu_item_names() -> Dict[str, str]:
    """獲取菜單項目ID到名稱的映射"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            menu_data = st.session_state.api.get_menu_items()
            if menu_data and 'items' in menu_data:
                menu_items = menu_data['items']
            elif isinstance(menu_data, list):
                menu_items = menu_data
            else:
                menu_items = []
            
            # 創建ID到名稱的映射
            name_mapping = {}
            for item in menu_items:
                item_id = str(item.get('id', ''))
                item_name = item.get('name', f"餐點 {item_id}")
                name_mapping[item_id] = item_name
            
            return name_mapping
        else:
            # 如果API不可用，返回空映射
            return {}
    except Exception as e:
        ui_logger.error(f"Error getting menu item names: {str(e)}")
        return {}

def implement_selected_menu_items(rec: Dict, rec_id: int) -> bool:
    """實施選中的菜單項目到目標機台"""
    try:
        # 獲取選中的菜單項目索引
        selected_indices = st.session_state.get(f'selected_menu_items_{rec_id}', [])
        if not selected_indices:
            ui_logger.warning(f"No selected menu items for recommendation {rec_id}")
            return False
        
        # 獲取推薦的菜單項目
        suggested_menu = rec.get('payload', {}).get('suggested_menu', [])
        if not suggested_menu:
            ui_logger.warning(f"No suggested menu items for recommendation {rec_id}")
            return False
        
        # 獲取目標機台ID
        target_machine_ids = rec.get('target_machine_ids', [])
        if not target_machine_ids:
            ui_logger.warning(f"No target machine IDs for recommendation {rec_id}")
            return False
        
        # 構建選中的菜單項目數據
        selected_menu_items = []
        for i in selected_indices:
            if i < len(suggested_menu):
                item = suggested_menu[i]
                meal_id = item.get('meal_id', '')
                if meal_id:
                    selected_menu_items.append({
                        'meal_id': meal_id,
                        'suggested_price': item.get('suggested_price', 0),
                        'priority': item.get('priority', 1),
                        'restock_quantity': item.get('restock_quantity', 0),
                        'restock_date': item.get('restock_date', '')
                    })
        
        if not selected_menu_items:
            ui_logger.warning(f"No valid selected menu items for recommendation {rec_id}")
            return False
        
        # 為每個目標機台實施選中的菜單項目
        success_count = 0
        for machine_id in target_machine_ids:
            try:
                # 提取菜單項目ID和顯示順序
                menu_item_ids = []
                display_orders = []
                
                for idx, item in enumerate(selected_menu_items):
                    meal_id = item['meal_id']
                    # 處理meal_id可能是字符串或數字的情況
                    if isinstance(meal_id, str) and meal_id.isdigit():
                        menu_item_ids.append(int(meal_id))
                    elif isinstance(meal_id, (int, float)):
                        menu_item_ids.append(int(meal_id))
                    else:
                        # 如果是字符串且包含非數字字符，跳過
                        ui_logger.warning(f"Skipping invalid meal_id: {meal_id}")
                        continue
                    
                    # 顯示順序從1開始
                    display_orders.append(idx + 1)
                
                if menu_item_ids:
                    # 調用API更新機台菜單項目
                    if hasattr(st.session_state, 'api') and st.session_state.api:
                        # 記錄API調用詳情
                        ui_logger.info(f"🚀 調用API更新機台 {machine_id} 菜單項目")
                        ui_logger.info(f"📡 POST {st.session_state.api.base_url}/machines/{machine_id}/update-menu-items")
                        ui_logger.info(f"📦 Request Body: {{'menu_item_ids': {menu_item_ids}, 'display_orders': {display_orders}}}")
                        
                        result = st.session_state.api.update_machine_menu_items(
                            int(machine_id), menu_item_ids, display_orders
                        )
                        
                        # 記錄API回應結果
                        if result:
                            success_count += 1
                            ui_logger.info(f"✅ 成功更新機台 {machine_id} 菜單項目")
                            ui_logger.info(f"📊 Response: {result}")
                        else:
                            ui_logger.error(f"❌ 更新機台 {machine_id} 菜單項目失敗")
                            ui_logger.error(f"📊 Response: {result}")
                    else:
                        ui_logger.error("❌ API 客戶端不可用")
                else:
                    ui_logger.warning(f"No valid menu item IDs for machine {machine_id}")
                    
            except Exception as e:
                ui_logger.error(f"Error updating machine {machine_id}: {str(e)}")
                continue
        
        # 返回是否至少有一個機台更新成功
        return success_count > 0
        
    except Exception as e:
        ui_logger.error(f"Error implementing selected menu items: {str(e)}")
        return False

