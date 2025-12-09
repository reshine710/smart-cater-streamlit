import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List
from logger_config import api_logger, ui_logger
from utils import format_datetime_display
from utils.permissions import can_create, can_update, can_delete, is_admin_or_above, show_permission_error

def location_management_page():
    """地點管理頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing location management page")
    st.title("📍 地點管理")

    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        pass  # 保留標題空間
    with col_refresh:
        if st.button("🔄 重新整理", type="secondary", width='stretch'):
            st.rerun()

    st.markdown("---")
    
    # 所有使用者都可以查看地點列表和統計
    # 管理員或以上可以新增地點
    tab_labels = ["📋 地點列表", "📊 地點統計"]
    if can_create():
        tab_labels.insert(1, "➕ 新增地點")
    
    tabs = st.tabs(tab_labels)
    
    tab_index = 0
    with tabs[tab_index]:
        show_locations_list()
    
    if can_create():
        tab_index += 1
        with tabs[tab_index]:
            show_create_location_form()
        tab_index += 1
    else:
        # 如果沒有創建權限，顯示提示
        if is_admin_or_above():
            pass  # 不應該到這裡
        else:
            st.info("💡 此功能需要管理員權限")
    
    with tabs[tab_index]:
        show_location_statistics()

def show_locations_list():
    """顯示地點列表"""
    st.subheader("📋 現有地點")
    
    # 獲取地點列表
    locations = st.session_state.api.get_locations()
    ui_logger.debug(f"Retrieved {len(locations)} locations for display")
    
    if not locations:
        st.info("📝 目前沒有地點資料，請先新增地點")
        return
    
    # 篩選和搜尋
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 搜尋地點", placeholder="輸入地點名稱...")
    with col2:
        indoor_filter = st.selectbox("環境篩選", ["全部", "室內", "室外"], key="location_indoor_filter")
    with col3:
        pass
    
    # 篩選地點
    filtered_locations = locations
    if search_term:
        filtered_locations = [loc for loc in filtered_locations if search_term.lower() in loc.get('name', '').lower()]
    if indoor_filter == "室內":
        filtered_locations = [loc for loc in filtered_locations if loc.get('is_indoor', False)]
    elif indoor_filter == "室外":
        filtered_locations = [loc for loc in filtered_locations if not loc.get('is_indoor', False)]
    
    st.write(f"顯示 {len(filtered_locations)} 個地點 (共 {len(locations)} 個)")
    
    # 顯示地點卡片
    for i, location in enumerate(filtered_locations):
        with st.expander(f"{'🏢' if location.get('is_indoor', False) else '🌳'} {location.get('name', 'Unknown')}", expanded=False):
            show_location_details(location, i)

def show_location_details(location: Dict, index: int):
    """顯示地點詳細資訊"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.write(f"**名稱**: {location.get('name', 'Unknown')}")
        st.write(f"**環境**: {'🏢 室內' if location.get('is_indoor', False) else '🌳 室外'}")
        st.write(f"**地址**: {location.get('address', '未提供')}")
    
    with col2:
        st.write(f"**描述**: {location.get('description', '無描述')}")
        from utils import format_datetime_display
        if location.get('created_at'):
            st.write(f"**建立時間**: {format_datetime_display(location['created_at'])}")
        if location.get('updated_at'):
            st.write(f"**更新時間**: {format_datetime_display(location['updated_at'])}")
    
    with col3:
        location_id = location.get('id')
        if location_id:
            # 編輯按鈕（管理員或以上可見）
            if can_update():
                if st.button("✏️ 編輯", key=f"edit_location_{location_id}_{index}"):
                    show_edit_location_form(location)
            
            # 刪除按鈕（僅超級管理員可見）
            if can_delete():
                st.markdown("---")
                st.write("**⚠️ 危險操作**")
                
                if st.button(f"🗑️ 刪除地點", 
                           key=f"delete_location_{location_id}_{index}",
                           type="secondary",
                           help="此操作無法復原，請謹慎使用"):
                    # 顯示確認對話框
                    if f"confirm_delete_location_{location_id}" not in st.session_state:
                        st.session_state[f"confirm_delete_location_{location_id}"] = False
                    
                    if not st.session_state.get(f"confirm_delete_location_{location_id}", False):
                        st.session_state[f"confirm_delete_location_{location_id}"] = True
                        st.rerun()
            
            # 確認刪除對話框
            if can_delete() and st.session_state.get(f"confirm_delete_location_{location_id}", False):
                st.error(f"⚠️ 確定要刪除地點 **{location.get('name', 'Unknown')}** 嗎？")
                st.write("此操作將永久刪除地點資料，無法復原！")
                
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button(f"✅ 確認刪除", 
                               key=f"confirm_delete_location_yes_{location_id}_{index}",
                               type="primary"):
                        try:
                            # 調用刪除地點的 API
                            success = st.session_state.api.delete_location(location_id)
                            if success:
                                st.success(f"✅ 地點 {location.get('name')} 已成功刪除")
                                ui_logger.info(f"Admin {st.session_state.get('username')} deleted location {location_id}")
                                # 清除確認狀態
                                st.session_state[f"confirm_delete_location_{location_id}"] = False
                                # 刷新頁面
                                st.rerun()
                            else:
                                ui_logger.error(f"Failed to delete location {location_id}")
                        except Exception as e:
                            st.error(f"❌ 刪除地點時發生錯誤: {str(e)}")
                            ui_logger.error(f"Error deleting location {location_id}: {str(e)}")
                
                with col_cancel:
                    if st.button(f"❌ 取消", 
                               key=f"confirm_delete_location_no_{location_id}_{index}"):
                        st.session_state[f"confirm_delete_location_{location_id}"] = False
                        st.rerun()

def show_create_location_form():
    """顯示創建地點表單"""
    st.subheader("➕ 新增地點")
    
    with st.form("create_location_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            location_name = st.text_input("地點名稱 *", placeholder="例：台北101店")
            location_address = st.text_input("地點地址", placeholder="例：台北市信義區信義路五段7號")
            is_indoor = st.checkbox("室內環境", value=True, help="勾選表示室內環境，不勾選表示室外環境")
        
        with col2:
            location_description = st.text_area("地點描述", placeholder="描述地點特色、環境等...")
            
            # 額外資訊
            st.write("**額外資訊 (可選)**")
            contact_person = st.text_input("聯絡人", placeholder="負責人姓名")
            contact_phone = st.text_input("聯絡電話", placeholder="聯絡電話號碼")
        
        submitted = st.form_submit_button("✨ 創建地點", width="stretch")
        
        if submitted:
            if not location_name:
                st.error("❌ 請填寫地點名稱")
            else:
                # 構建地點資料
                location_data = {
                    "name": location_name.strip(),
                    "address": location_address.strip() if location_address else "",
                    "description": location_description.strip() if location_description else "",
                    "is_indoor": is_indoor
                }
                
                # 添加可選欄位
                if contact_person:
                    location_data["contact_person"] = contact_person.strip()
                if contact_phone:
                    location_data["contact_phone"] = contact_phone.strip()
                
                ui_logger.info(f"Admin {st.session_state.get('username')} creating location: {location_name}")
                
                # 調用 API 創建地點
                try:
                    created_location = st.session_state.api.create_location(location_data)
                    if created_location:
                        st.success(f"✅ 地點 '{location_name}' 創建成功！")
                        st.balloons()
                        # 重新整理頁面以顯示新地點
                        st.rerun()
                    else:
                        st.error(f"❌ 創建地點 '{location_name}' 失敗，請稍後再試")
                except Exception as e:
                    st.error(f"❌ 創建地點時發生錯誤: {str(e)}")
                    ui_logger.error(f"Error creating location: {str(e)}")

def show_edit_location_form(location: Dict):
    """顯示編輯地點表單"""
    
    @st.dialog(f"✏️ 編輯地點 - {location.get('name', 'Unknown')}")
    def edit_dialog():
        col1, col2 = st.columns(2)
        
        with col1:
            updated_name = st.text_input("地點名稱", value=location.get('name', ''))
            updated_address = st.text_input("地點地址", value=location.get('address', ''))
            updated_is_indoor = st.checkbox("室內環境", value=location.get('is_indoor', False))
        
        with col2:
            updated_description = st.text_area("地點描述", value=location.get('description', ''))
            updated_contact_person = st.text_input("聯絡人", value=location.get('contact_person', ''))
            updated_contact_phone = st.text_input("聯絡電話", value=location.get('contact_phone', ''))
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("💾 儲存更改", width="stretch"):
                update_data = {
                    "name": updated_name,
                    "address": updated_address,
                    "description": updated_description,
                    "is_indoor": updated_is_indoor,
                    "contact_person": updated_contact_person,
                    "contact_phone": updated_contact_phone
                }
                
                ui_logger.info(f"Admin {st.session_state.get('username')} updating location: {location['id']}")
                
                # 調用更新地點的 API
                try:
                    success = st.session_state.api.update_location(location['id'], update_data)
                    if success:
                        st.success(f"✅ {updated_name} 更新成功！")
                        st.rerun()
                    else:
                        ui_logger.error(f"Failed to update location {location['id']}")
                except Exception as e:
                    st.error(f"❌ 更新地點時發生錯誤: {str(e)}")
                    ui_logger.error(f"Error updating location {location['id']}: {str(e)}")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
    
    # 觸發對話框
    edit_dialog()

def show_location_statistics():
    """顯示地點統計資訊"""
    st.subheader("📊 地點統計")
    
    # 獲取地點統計
    locations = st.session_state.api.get_locations()
    if locations:
        # 基本統計
        total_locations = len(locations)
        indoor_locations = len([loc for loc in locations if loc.get('is_indoor', False)])
        outdoor_locations = total_locations - indoor_locations
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總地點數", total_locations)
        with col2:
            st.metric("室內地點", indoor_locations)
        with col3:
            st.metric("室外地點", outdoor_locations)
        
        st.markdown("---")
        
        # 地點列表
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏢 室內地點")
            indoor_locs = [loc for loc in locations if loc.get('is_indoor', False)]
            if indoor_locs:
                for loc in indoor_locs:
                    st.write(f"• **{loc.get('name', 'Unknown')}**")
                    if loc.get('address'):
                        st.write(f"  📍 {loc['address']}")
            else:
                st.info("沒有室內地點")
        
        with col2:
            st.subheader("🌳 室外地點")
            outdoor_locs = [loc for loc in locations if not loc.get('is_indoor', False)]
            if outdoor_locs:
                for loc in outdoor_locs:
                    st.write(f"• **{loc.get('name', 'Unknown')}**")
                    if loc.get('address'):
                        st.write(f"  📍 {loc['address']}")
            else:
                st.info("沒有室外地點")
        
        # 詳細列表
        st.subheader("📋 地點詳細列表")
        if locations:
            df_data = []
            for location in locations:
                df_data.append({
                    'ID': location.get('id', 'N/A'),
                    '名稱': location.get('name', 'Unknown'),
                    '環境': '室內' if location.get('is_indoor', False) else '室外',
                    '地址': location.get('address', '未提供'),
                    '描述': location.get('description', '無描述')[:50] + ('...' if len(location.get('description', '')) > 50 else ''),
                    '建立時間': format_datetime_display(location.get('created_at', 'N/A'))
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("📝 沒有地點數據可供分析")
