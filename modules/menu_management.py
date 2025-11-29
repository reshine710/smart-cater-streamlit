import time
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from logger_config import api_logger, ui_logger


def get_machine_type_from_product_code(product_code: Optional[str]) -> str:
    """
    從 product_code 提取機型代號
    
    Args:
        product_code: 商品代碼
    
    Returns:
        str: 機型代號（A-Z）或 '其他'
    """
    if not product_code or not isinstance(product_code, str):
        return '其他'
    
    product_code = product_code.strip()
    if not product_code:
        return '其他'
    
    first_char = product_code[0].upper()
    if first_char.isalpha() and 'A' <= first_char <= 'Z':
        return first_char
    
    return '其他'


def categorize_menu_items_by_machine_type(menu_items: List[Dict]) -> Dict[str, List[Dict]]:
    """
    將菜單項目按機型分類
    
    Args:
        menu_items: 所有菜單項目列表
    
    Returns:
        Dict[str, List[Dict]]: {
            'A': [A機型的項目列表],
            'B': [B機型的項目列表],
            '其他': [無法分類的項目列表]
        }
    """
    categorized = {}
    
    for item in menu_items:
        product_code = item.get('product_code')
        machine_type = get_machine_type_from_product_code(product_code)
        
        if machine_type not in categorized:
            categorized[machine_type] = []
        
        categorized[machine_type].append(item)
    
    return categorized


def get_available_machine_types(categorized: Dict[str, List[Dict]]) -> List[str]:
    """
    獲取目前資料中實際存在的機型列表並排序
    
    Args:
        categorized: 已分類的菜單項目字典
    
    Returns:
        List[str]: 排序後的機型列表，如 ['A', 'B', 'C', '其他']
    """
    available_types = []
    
    # 先收集 A-Z 的機型
    letter_types = sorted([k for k in categorized.keys() if k != '其他' and len(k) == 1 and k.isalpha()])
    available_types.extend(letter_types)
    
    # 最後加入「其他」
    if '其他' in categorized:
        available_types.append('其他')
    
    return available_types


def menu_management_page():
    """菜單管理頁面（按機型分類）"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing menu management page")
    st.title("🍽️ 菜單管理")
    st.markdown("---")
    
    # 檢查管理員權限
    if not st.session_state.get('is_admin', False):
        st.error("❌ 權限不足：此功能僅限管理員使用")
        ui_logger.warning(f"Non-admin user {st.session_state.get('username', 'Unknown')} attempted to access menu management")
        return
    
    # 獲取所有菜單項目
    menu_items = st.session_state.api.get_menu_items()
    ui_logger.debug(f"Retrieved {len(menu_items)} menu items for display")
    
    if not menu_items:
        st.info("📝 目前沒有菜單項目，請先新增項目")
        # 仍然顯示新增項目表單
        st.markdown("---")
        st.subheader("➕ 新增菜單項目")
        show_add_menu_item_form()
        return
    
    # 按機型分類
    categorized = categorize_menu_items_by_machine_type(menu_items)
    available_types = get_available_machine_types(categorized)
    
    if not available_types:
        st.info("📝 目前沒有有效的菜單項目")
        return
    
    # 方案C：主要機型（A-Z）使用 tabs，「其他」作為單獨 tab
    # 建立 tab 標籤列表
    tab_labels = []
    for machine_type in available_types:
        if machine_type == '其他':
            tab_labels.append(f"📦 {machine_type}")
        else:
            tab_labels.append(f"{machine_type}機型")
    
    # 創建機型 tabs
    machine_tabs = st.tabs(tab_labels)
    
    # 為每個機型 tab 顯示內容
    for idx, machine_type in enumerate(available_types):
        with machine_tabs[idx]:
            # 顯示機型標題
            if machine_type == '其他':
                st.subheader(f"📦 {machine_type}機型商品")
            else:
                st.subheader(f"{machine_type}機型商品管理")
            
            # 獲取該機型的商品列表
            machine_items = categorized.get(machine_type, [])
            
            # 顯示統計資訊
            if machine_items:
                total_count = len(machine_items)
                active_count = len([item for item in machine_items if item.get('is_active', False)])
                inactive_count = total_count - active_count
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("商品總數", total_count)
                with col2:
                    st.metric("啟用", active_count)
                with col3:
                    st.metric("停用", inactive_count)
                with col4:
                    avg_price = sum(item.get('price', 0) for item in machine_items) / total_count if total_count > 0 else 0
                    st.metric("平均價格", f"NT$ {avg_price:.1f}")
                
                st.markdown("---")
            
            # 在每個機型 tab 內，顯示三個子功能：商品列表、新增項目、分析
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📋 商品列表", "➕ 新增項目", "📊 機型分析"])
            
            with sub_tab1:
                show_machine_type_items_list(machine_items, machine_type)
            
            with sub_tab2:
                show_add_menu_item_form(machine_type)
            
            with sub_tab3:
                if machine_items:
                    show_menu_analytics(machine_items)
                else:
                    st.info(f"📝 {machine_type}機型目前沒有商品數據可供分析")


def show_machine_type_items_list(machine_items: List[Dict], machine_type: str):
    """顯示指定機型的商品列表"""
    if not machine_items:
        st.info(f"📝 {machine_type}機型目前沒有商品，請先新增項目")
        return
    
    # 篩選和搜尋
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 搜尋商品", placeholder="輸入商品名稱...", key=f"search_{machine_type}")
    with col2:
        status_filter = st.selectbox("狀態篩選", ["全部", "啟用", "停用"], key=f"status_filter_{machine_type}")
    with col3:
        if st.button("🔄 重新整理", key=f"refresh_{machine_type}"):
            st.rerun()
    
    # 篩選商品
    filtered_items = machine_items
    if search_term:
        filtered_items = [item for item in filtered_items if search_term.lower() in item.get('name', '').lower()]
    if status_filter == "啟用":
        filtered_items = [item for item in filtered_items if item.get('is_active', False)]
    elif status_filter == "停用":
        filtered_items = [item for item in filtered_items if not item.get('is_active', False)]
    
    st.write(f"顯示 {len(filtered_items)} 個項目 (共 {len(machine_items)} 個)")
    
    # 顯示商品列表
    for i, item in enumerate(filtered_items):
        with st.expander(f"{'✅' if item.get('is_active', False) else '❌'} {item.get('name', 'Unknown')} - NT$ {item.get('price', 0)}", expanded=False):
            show_menu_item_details(item, i)


def show_add_menu_item_form(suggested_machine_type: Optional[str] = None):
    """顯示新增菜單項目表單"""
    st.subheader("➕ 新增菜單項目")
    
    # 如果有建議的機型，顯示提示
    if suggested_machine_type and suggested_machine_type != '其他':
        st.info(f"💡 提示：建議的商品代碼格式為 {suggested_machine_type}001, {suggested_machine_type}002...")
    
    # 為每個機型使用唯一的 form key 和所有輸入欄位的 key
    prefix = f"_{suggested_machine_type}" if suggested_machine_type else ""
    form_key = f"add_menu_item{prefix}"
    
    with st.form(form_key, clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("商品名稱 *", placeholder="例：拿鐵咖啡", key=f"name{prefix}")
            # 如果有建議機型，預設商品代碼格式
            default_code = f"{suggested_machine_type}001" if suggested_machine_type and suggested_machine_type != '其他' else ""
            new_product_code = st.text_input("商品代碼", value=default_code, placeholder="例：A001", 
                                           help="產品編號，用於訂單管理", key=f"code{prefix}")
            new_description = st.text_area("商品描述", placeholder="詳細描述商品特色...", key=f"desc{prefix}")
            new_price = st.number_input("價格 (NT$) *", min_value=0.0, step=1.0, format="%.1f", key=f"price{prefix}")
            new_image_url = st.text_input("圖片網址", placeholder="https://example.com/image.jpg", key=f"img{prefix}")
        
        with col2:
            new_heating_method = st.selectbox("加熱方式 *", ["none", "microwave", "steam"], 
                                            format_func=lambda x: {"none": "無需加熱", "microwave": "微波加熱", "steam": "蒸氣加熱"}[x],
                                            key=f"heating{prefix}")
            new_heating_time = st.number_input("加熱時間 (秒)", min_value=0, max_value=300, step=5, key=f"time{prefix}")
            new_is_active = st.checkbox("立即啟用", value=True, key=f"active{prefix}")
            
            # 營養資訊
            st.write("**營養資訊 (可選)**")
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                calories = st.number_input("熱量 (卡)", min_value=0, step=10, key=f"cal{prefix}")
                protein = st.number_input("蛋白質 (g)", min_value=0.0, step=0.1, format="%.1f", key=f"pro{prefix}")
            with col2_2:
                carbs = st.number_input("碳水化合物 (g)", min_value=0.0, step=0.1, format="%.1f", key=f"carb{prefix}")
                fat = st.number_input("脂肪 (g)", min_value=0.0, step=0.1, format="%.1f", key=f"fat{prefix}")
        
        # 標籤
        tags_input = st.text_input("標籤 (用逗號分隔)", placeholder="熱門, 健康, 咖啡", key=f"tags{prefix}")
        
        submitted = st.form_submit_button("✨ 創建菜單項目", width="stretch")
        
        if submitted:
            if not new_name or new_price <= 0:
                st.error("❌ 請填寫必填欄位：商品名稱和價格")
            else:
                # 處理標籤
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
                
                # 構建菜單項目數據
                menu_item_data = {
                    "name": new_name,
                    "product_code": new_product_code.strip() if new_product_code else None,
                    "description": new_description or f"{new_name} - 美味可口",
                    "price": float(new_price),
                    "image_url": new_image_url or "https://via.placeholder.com/300x200?text=No+Image",
                    "heating_method": new_heating_method,
                    "heating_time": new_heating_time,
                    "is_active": new_is_active,
                    "nutrition_info": {
                        "calories": int(calories),
                        "protein": float(protein),
                        "carbs": float(carbs),
                        "fat": float(fat)
                    },
                    "tags": tags
                }
                
                ui_logger.info(f"Admin {st.session_state.get('username')} creating menu item: {new_name}")
                
                # 調用 API 創建菜單項目
                if st.session_state.api.create_menu_item(menu_item_data):
                    st.success(f"✅ 菜單項目 '{new_name}' 創建成功！")
                    st.toast(f"🎉 已成功建立新菜單項目：{new_name}", icon="✅", duration='long')
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ 創建菜單項目 '{new_name}' 失敗，請稍後再試")
                    st.toast(f"❌ 建立菜單項目失敗：{new_name}", icon="❌", duration='long')


def show_menu_item_details(item: Dict, index: int):
    """顯示菜單項目詳細資訊和操作按鈕"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.write(f"**商品代碼**: {item.get('product_code', '未設定')}")
        st.write(f"**描述**: {item.get('description', '無描述')}")
        st.write(f"**加熱方式**: {format_heating_method(item.get('heating_method', 'none'))}")
        if item.get('heating_time', 0) > 0:
            st.write(f"**加熱時間**: {item.get('heating_time')} 秒")
        
        # 顯示標籤
        tags = item.get('tags', [])
        if tags:
            # 處理標籤格式 - 支援字串和字典格式
            formatted_tags = []
            for tag in tags:
                if isinstance(tag, dict):
                    # 如果是字典格式，取 name 欄位
                    tag_name = tag.get('name', str(tag))
                else:
                    # 如果是字串格式，直接使用
                    tag_name = str(tag)
                formatted_tags.append(tag_name)
            
            # 使用 Streamlit 的標籤樣式顯示
            st.write("**標籤**:")
            tag_cols = st.columns(min(len(formatted_tags), 4))  # 最多4列
            for i, tag_name in enumerate(formatted_tags):
                with tag_cols[i % 4]:
                    st.markdown(f"`{tag_name}`")
    
    with col2:
        st.write(f"**價格**: NT$ {item.get('price', 0):.1f}")
        st.write(f"**狀態**: {'🟢 啟用' if item.get('is_active', False) else '🔴 停用'}")
        
        # 營養資訊
        nutrition = item.get('nutrition_info', {})
        if nutrition and any(nutrition.values()):
            st.write("**營養資訊**:")
            if nutrition.get('calories', 0) > 0:
                st.write(f"  • 熱量: {nutrition['calories']} 卡")
            if nutrition.get('protein', 0) > 0:
                st.write(f"  • 蛋白質: {nutrition['protein']}g")
    
    with col3:
        item_id = item.get('id')
        if item_id:
            # 編輯按鈕
            if st.button("✏️ 編輯", key=f"edit_{item_id}_{index}"):
                show_edit_menu_item_form(item)
            
            # 啟用/停用按鈕
            if item.get('is_active', False):
                if st.button("🔴 停用", key=f"deactivate_{item_id}_{index}"):
                    if st.session_state.api.deactivate_menu_item(item_id):
                        st.success(f"✅ {item.get('name')} 已停用")
                        ui_logger.info(f"Menu item deactivated: {item.get('name')} (ID: {item_id})")
                        st.rerun()
                    else:
                        st.error("❌ 停用失敗")
            else:
                if st.button("🟢 啟用", key=f"activate_{item_id}_{index}"):
                    if st.session_state.api.activate_menu_item(item_id):
                        st.success(f"✅ {item.get('name')} 已啟用")
                        ui_logger.info(f"Menu item activated: {item.get('name')} (ID: {item_id})")
                        st.rerun()
                    else:
                        st.error("❌ 啟用失敗")
            
            # 標籤管理
            if st.button("🏷️ 管理標籤", key=f"tags_{item_id}_{index}"):
                show_tags_management(item)
            
            # 配方管理
            if st.button("🧾 配方管理", key=f"recipe_{item_id}_{index}"):
                show_recipe_management_dialog(item)
            
            # 刪除菜單項目功能 (危險操作)
            st.markdown("---")
            st.write("**⚠️ 危險操作**")
            
            # 使用 st.dialog 確認對話框
            if st.button(f"🗑️ 刪除項目", 
                       key=f"delete_{item_id}_{index}",
                       type="secondary",
                       help="此操作無法復原，請謹慎使用"):
                show_delete_confirmation_dialog(item)


def show_delete_confirmation_dialog(item: Dict):
    """顯示刪除確認對話框"""
    
    @st.dialog(f"🗑️ 刪除確認 - {item.get('name', 'Unknown')}")
    def delete_dialog():
        st.error("⚠️ **危險操作警告**")
        st.write(f"您即將刪除菜單項目：**{item.get('name', 'Unknown')}**")
        st.write(f"價格：NT$ {item.get('price', 0):.1f}")
        
        # 顯示項目詳細資訊
        if item.get('description'):
            st.write(f"描述：{item.get('description')}")
        
        st.markdown("---")
        st.warning("⚠️ **此操作將永久刪除菜單項目及其相關數據，無法復原！**")
        
        # 確認輸入
        st.write("請輸入項目名稱以確認刪除：")
        confirmation_input = st.text_input("", placeholder=f"請輸入 '{item.get('name', '')}'")
        
        col_delete, col_cancel = st.columns(2)
        
        with col_delete:
            # 只有當輸入正確時才啟用刪除按鈕
            delete_enabled = confirmation_input == item.get('name', '')
            if st.button("🗑️ 確認刪除", 
                        width="stretch", 
                        type="primary",
                        disabled=not delete_enabled):
                if delete_enabled:
                    try:
                        success = st.session_state.api.delete_menu_item(item['id'])
                        if success:
                            ui_logger.info(f"Admin {st.session_state.get('username')} deleted menu item {item['id']} ({item.get('name')})")
                            st.success(f"✅ 菜單項目 '{item.get('name')}' 已成功刪除！")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 刪除菜單項目失敗")
                    except Exception as e:
                        st.error(f"❌ 刪除菜單項目時發生錯誤: {str(e)}")
                        ui_logger.error(f"Error deleting menu item {item['id']}: {str(e)}")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
        
        if not delete_enabled and confirmation_input:
            st.error("❌ 輸入的項目名稱不正確")
    
    # 觸發對話框
    delete_dialog()


def show_edit_menu_item_form(item: Dict):
    """顯示編輯菜單項目表單"""
    
    @st.dialog(f"✏️ 編輯 {item.get('name', 'Unknown')}")
    def edit_dialog():
        col1, col2 = st.columns(2)
        with col1:
            updated_name = st.text_input("商品名稱", value=item.get('name', ''))
            updated_product_code = st.text_input("商品代碼", value=item.get('product_code', ''), 
                                                placeholder="例：A001", help="產品編號，用於訂單管理")
            updated_description = st.text_area("商品描述", value=item.get('description', ''))
            updated_price = st.number_input("價格 (NT$)", value=float(item.get('price', 0)), min_value=0.0, step=1.0)
        
        with col2:
            current_heating = item.get('heating_method', 'none')
            heating_options = ["none", "microwave", "steam"]
            heating_index = heating_options.index(current_heating) if current_heating in heating_options else 0
            updated_heating_method = st.selectbox("加熱方式", heating_options, index=heating_index,
                                                format_func=lambda x: {"none": "無需加熱", "microwave": "微波加熱", "steam": "蒸氣加熱"}[x])
            updated_heating_time = st.number_input("加熱時間 (秒)", value=item.get('heating_time', 0), min_value=0, max_value=300)
            updated_image_url = st.text_input("圖片網址", value=item.get('image_url', ''))
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("💾 儲存更改", width="stretch"):
                update_data = {
                    "name": updated_name,
                    "product_code": updated_product_code.strip() if updated_product_code else None,
                    "description": updated_description,
                    "price": float(updated_price),
                    "heating_method": updated_heating_method,
                    "heating_time": updated_heating_time,
                    "image_url": updated_image_url
                }
                
                ui_logger.info(f"Admin {st.session_state.get('username')} updating menu item: {item['id']}")
                
                if st.session_state.api.update_menu_item(item['id'], update_data):
                    st.success(f"✅ {updated_name} 更新成功！")
                    st.rerun()
                else:
                    st.error("❌ 更新失敗，請稍後再試")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
    
    # 觸發對話框
    edit_dialog()


def show_tags_management(item: Dict):
    """顯示標籤管理介面"""
    
    @st.dialog(f"🏷️ 管理標籤 - {item.get('name', 'Unknown')}")
    def tags_dialog():
        current_tags = item.get('tags', [])
        
        # 處理標籤格式 - 支援字串和字典格式
        formatted_current_tags = []
        for tag in current_tags:
            if isinstance(tag, dict):
                # 如果是字典格式，取 name 欄位
                tag_name = tag.get('name', str(tag))
            else:
                # 如果是字串格式，直接使用
                tag_name = str(tag)
            formatted_current_tags.append(tag_name)
        
        current_tags_str = ', '.join(formatted_current_tags) if formatted_current_tags else ''
        
        updated_tags_str = st.text_input("標籤 (用逗號分隔)", value=current_tags_str, 
                                       placeholder="熱門, 健康, 咖啡")
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("🏷️ 更新標籤", width="stretch"):
                new_tags = [tag.strip() for tag in updated_tags_str.split(',') if tag.strip()]
                
                ui_logger.info(f"Admin {st.session_state.get('username')} updating tags for menu item: {item['id']}")
                
                if st.session_state.api.update_menu_item_tags(item['id'], new_tags):
                    st.success(f"✅ {item.get('name')} 的標籤更新成功！")
                    st.rerun()
                else:
                    st.error("❌ 標籤更新失敗，請稍後再試")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
    
    # 觸發對話框
    tags_dialog()


def show_recipe_management_dialog(item: Dict):
    """顯示配方管理對話框"""
    
    @st.dialog(f"🧾 配方管理 - {item.get('name', 'Unknown')}")
    def recipe_dialog():
        # 權限檢查
        if not st.session_state.get('is_admin', False):
            st.error("❌ 權限不足：此功能僅限管理員使用")
            ui_logger.warning(f"Non-admin user {st.session_state.get('username', 'Unknown')} attempted to access recipe management")
            if st.button("❌ 關閉", width="stretch"):
                st.rerun()
            return
        
        item_name = item.get('name', 'Unknown')
        item_id = item.get('id')
        
        if not item_id:
            st.error("❌ 無法取得商品ID")
            if st.button("❌ 關閉", width="stretch"):
                st.rerun()
            return
        
        # 商品基本資訊顯示
        st.subheader(f"🍽️ {item_name}")
        
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.write(f"**💰 價格**: NT$ {item.get('price', 0):.1f}")
        with col_info2:
            status = "✅ 啟用" if item.get('is_active', False) else "❌ 停用"
            st.write(f"**📊 狀態**: {status}")
        with col_info3:
            st.write(f"**🆔 商品代碼**: {item.get('product_code', '未設定')}")
        
        st.markdown("---")
        
        # 獲取現有參數
        current_heating_method = item.get('heating_method', 'none')
        heating_params = item.get('heating_params') or {}
        if not isinstance(heating_params, dict):
            heating_params = {}
        
        # 加熱方式選擇器
        st.subheader("⚙️ 加熱方式設定")
        heating_options = ["none", "microwave", "steam"]
        heating_index = heating_options.index(current_heating_method) if current_heating_method in heating_options else 0
        selected_heating_method = st.selectbox(
            "🔥 選擇加熱方式",
            heating_options,
            index=heating_index,
            format_func=lambda x: {"none": "❄️ 無需加熱", "microwave": "🔥 微波加熱", "steam": "💨 蒸氣加熱"}[x],
            help="選擇此商品的加熱方式，切換後可設定對應的加熱參數"
        )
        
        st.markdown("---")
        
        # 動態參數設定區
        st.subheader("📋 加熱參數設定")
        
        recipe_config = {}
        current_heating_time = heating_params.get('time_seconds', 0) if isinstance(heating_params, dict) else 0
        
        if selected_heating_method == 'steam':
            st.success("💨 蒸氣加熱參數設定")
            
            # 從現有參數讀取，如果加熱方式改變則使用預設值
            if current_heating_method == 'steam' and heating_params:
                current_temp = heating_params.get('temperature', 100)
                current_pressure = heating_params.get('pressure_bar', 1.5)
                current_time = heating_params.get('time_seconds', 120)
            else:
                current_temp = 100
                current_pressure = 1.5
                current_time = 120
            
            steam_temp = st.slider("蒸氣溫度 (°C)", 80, 120, current_temp, help="建議範圍：80-120°C")
            steam_time = st.slider("加熱時間 (秒)", 30, 300, current_time, step=5, help="建議範圍：30-300秒")
            steam_pressure = st.slider("蒸氣壓力 (bar)", 1.0, 3.0, current_pressure, 0.1, help="建議範圍：1.0-3.0 bar")
            
            recipe_config = {
                "heating_method": "steam",
                "temperature": steam_temp,
                "time_seconds": steam_time,
                "pressure_bar": steam_pressure
            }
            
        elif selected_heating_method == 'microwave':
            st.success("🔥 微波加熱參數設定")
            
            # 從現有參數讀取，如果加熱方式改變則使用預設值
            if current_heating_method == 'microwave' and heating_params:
                current_power = heating_params.get('power_percent', 80)
                current_time = heating_params.get('time_seconds', 90)
            else:
                current_power = 80
                current_time = 90
            
            microwave_power = st.slider("微波功率 (%)", 30, 100, current_power, step=5, help="建議範圍：30-100%")
            microwave_time = st.slider("加熱時間 (秒)", 30, 180, current_time, step=5, help="建議範圍：30-180秒")
            
            recipe_config = {
                "heating_method": "microwave",
                "power_percent": microwave_power,
                "time_seconds": microwave_time
            }
            
        else:  # none
            st.info("❄️ 無需加熱")
            st.write("此項目無需加熱，可直接供應。")
            recipe_config = {
                "heating_method": "none",
                "time_seconds": 0
            }
        
        # 參數預覽
        st.markdown("---")
        st.subheader("🔮 參數預覽")
        st.code(f"{recipe_config}", language="json")
        
        # 顯示現有參數（如果存在且與新設定不同）
        if heating_params and isinstance(heating_params, dict) and current_heating_method == selected_heating_method:
            st.info("📋 目前設定參數:")
            st.json(heating_params)
        
        st.markdown("---")
        
        # 操作按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 儲存配方設定", width="stretch", type="primary"):
                # 構建更新資料
                update_data = {
                    "heating_method": selected_heating_method,
                    "heating_params": recipe_config
                }
                
                ui_logger.info(f"Admin {st.session_state.get('username')} saving recipe settings for {item_name} (ID: {item_id})")
                ui_logger.debug(f"Update data: {update_data}")
                
                # 調用 API 更新
                result = st.session_state.api.update_menu_item(item_id, update_data)
                if result:
                    st.success(f"✅ {item_name} 的配方設定已儲存！")
                    st.toast(f"🎉 配方設定已更新：{item_name}", icon="✅", duration='long')
                    ui_logger.info(f"Recipe settings saved successfully for {item_name} (ID: {item_id})")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗，請稍後再試")
                    ui_logger.error(f"Failed to save recipe settings for {item_name} (ID: {item_id})")
        
        with col2:
            if st.button("🔄 重設為預設值", width="stretch"):
                # 根據加熱方式設定預設值
                if selected_heating_method == 'steam':
                    default_config = {
                        "heating_method": "steam",
                        "temperature": 100,
                        "time_seconds": 120,
                        "pressure_bar": 1.5
                    }
                elif selected_heating_method == 'microwave':
                    default_config = {
                        "heating_method": "microwave",
                        "power_percent": 80,
                        "time_seconds": 90
                    }
                else:
                    default_config = {
                        "heating_method": "none",
                        "time_seconds": 0
                    }
                
                update_data = {
                    "heating_method": selected_heating_method,
                    "heating_params": default_config
                }
                
                ui_logger.info(f"Admin {st.session_state.get('username')} resetting recipe settings for {item_name} (ID: {item_id})")
                
                result = st.session_state.api.update_menu_item(item_id, update_data)
                if result:
                    st.success(f"✅ {item_name} 的配方設定已重設為預設值")
                    st.toast(f"🔄 配方設定已重設：{item_name}", icon="✅", duration='long')
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 重設失敗，請稍後再試")
        
        with col3:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
    
    # 觸發對話框
    recipe_dialog()


def show_menu_analytics(menu_items: List[Dict]):
    """顯示菜單分析資訊"""
    # 基本統計
    total_items = len(menu_items)
    active_items = len([item for item in menu_items if item.get('is_active', False)])
    inactive_items = total_items - active_items
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總項目數", total_items)
    with col2:
        st.metric("啟用項目", active_items)
    with col3:
        st.metric("停用項目", inactive_items)
    with col4:
        avg_price = sum(item.get('price', 0) for item in menu_items) / total_items if total_items > 0 else 0
        st.metric("平均價格", f"NT$ {avg_price:.1f}")
    
    st.markdown("---")
    
    # 價格分佈
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 價格分佈")
        if menu_items:
            prices = [item.get('price', 0) for item in menu_items]
            price_df = pd.DataFrame({
                '項目名稱': [item.get('name', 'Unknown') for item in menu_items],
                '價格': prices,
                '狀態': ['啟用' if item.get('is_active', False) else '停用' for item in menu_items]
            })
            st.bar_chart(price_df.set_index('項目名稱')['價格'])
    
    with col2:
        st.subheader("🏷️ 熱門標籤")
        if menu_items:
            all_tags = []
            for item in menu_items:
                tags = item.get('tags', [])
                if tags:  # 確保 tags 是列表且不為空
                    all_tags.extend(tags)
            
            if all_tags:
                # 過濾並確保標籤都是字串類型
                valid_tags = []
                for tag in all_tags:
                    if isinstance(tag, str) and tag.strip():  # 確保是字串且不為空
                        valid_tags.append(tag.strip())
                    elif isinstance(tag, dict):  # 如果是字典，嘗試提取名稱
                        if 'name' in tag:
                            valid_tags.append(str(tag['name']).strip())
                        elif 'tag' in tag:
                            valid_tags.append(str(tag['tag']).strip())
                        else:
                            # 如果是字典但沒有預期的鍵，轉為字串
                            valid_tags.append(str(tag).strip())
                    else:
                        # 其他類型轉為字串
                        valid_tags.append(str(tag).strip())
                
                # 計算標籤出現次數
                from collections import Counter
                tag_counts = Counter(valid_tags)
                
                # 顯示前10個熱門標籤
                st.write("**最受歡迎的標籤：**")
                for i, (tag, count) in enumerate(tag_counts.most_common(10), 1):
                    percentage = (count / len(valid_tags)) * 100
                    st.write(f"{i}. **{tag}** - {count} 次使用 ({percentage:.1f}%)")
                
                # 顯示使用這些標籤的菜單項目
                st.write("**相關菜單項目：**")
                popular_tags = [tag for tag, _ in tag_counts.most_common(5)]
                
                for tag in popular_tags:
                    items_with_tag = []
                    for item in menu_items:
                        item_tags = item.get('tags', [])
                        # 檢查標籤是否匹配
                        for item_tag in item_tags:
                            if isinstance(item_tag, str) and item_tag.strip() == tag:
                                items_with_tag.append(item)
                                break
                            elif isinstance(item_tag, dict):
                                tag_name = None
                                if 'name' in item_tag:
                                    tag_name = str(item_tag['name']).strip()
                                elif 'tag' in item_tag:
                                    tag_name = str(item_tag['tag']).strip()
                                else:
                                    tag_name = str(item_tag).strip()
                                
                                if tag_name == tag:
                                    items_with_tag.append(item)
                                    break
                    
                    if items_with_tag:
                        with st.expander(f"🏷️ {tag} ({len(items_with_tag)} 個項目)", expanded=False):
                            for item in items_with_tag:
                                status_icon = "🟢" if item.get('is_active', False) else "🔴"
                                st.write(f"{status_icon} **{item.get('name', 'Unknown')}** - NT$ {item.get('price', 0):.1f}")
            else:
                st.info("沒有標籤數據")
    
    # 詳細列表
    st.subheader("📋 項目詳細列表")
    if menu_items:
        df_data = []
        for item in menu_items:
            df_data.append({
                'ID': item.get('id', 'N/A'),
                '商品代碼': item.get('product_code', '未設定'),
                '名稱': item.get('name', 'Unknown'),
                '價格': f"NT$ {item.get('price', 0):.1f}",
                '加熱方式': format_heating_method(item.get('heating_method', 'none')),
                '狀態': '🟢 啟用' if item.get('is_active', False) else '🔴 停用',
                '標籤數量': len(item.get('tags', []))
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, width="stretch", hide_index=True)


def format_heating_method(method: str) -> str:
    """格式化加熱方式顯示"""
    method_map = {
        "none": "無需加熱",
        "microwave": "微波加熱",
        "steam": "蒸氣加熱"
    }
    return method_map.get(method, method)
