import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, date
from typing import Dict, List, Optional
from logger_config import api_logger, ui_logger
from utils import format_datetime_display
from utils.permissions import can_create, can_update, can_delete, is_admin_or_above, show_permission_error


def inventory_management_page():
    """機台庫存管理主頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing inventory management page")
    st.title("📦 機台庫存管理")
    
    # 機台選擇器
    machines = st.session_state.api.get_machines()
    if not machines:
        st.warning("⚠️ 目前沒有可用的機台")
        return
    
    # 建立機台選項字典
    machine_options = {}
    machine_id_to_code = {}  # 用於調試顯示
    for machine in machines:
        machine_name = machine.get('name', 'Unknown')
        machine_code = machine.get('machine_code', 'N/A')
        machine_id = machine.get('id')
        if machine_id:
            machine_options[f"{machine_name} ({machine_code})"] = machine_id
            machine_id_to_code[machine_id] = machine_code
    
    if not machine_options:
        st.warning("⚠️ 無法取得機台資訊")
        return
    
    # 機台選擇
    col_select, col_refresh = st.columns([3, 1])
    with col_select:
        selected_machine_name = st.selectbox(
            "選擇機台",
            options=list(machine_options.keys()),
            key="inventory_machine_selector"
        )
        selected_machine_id = machine_options[selected_machine_name]
        selected_machine_code = machine_id_to_code.get(selected_machine_id, 'N/A')
    
    # 調試資訊（顯示當前選擇的機台）
    ui_logger.debug(f"Selected machine: ID={selected_machine_id}, Code={selected_machine_code}, Name={selected_machine_name}")
    
    with col_refresh:
        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 重新整理", type="secondary", width='stretch', key="refresh_inventory"):
            st.rerun()
    
    st.markdown("---")
    
    # Tab 結構
    tab_labels = ["📋 庫存總覽", "📊 庫存統計"]
    if can_create():  # 管理員
        tab_labels.insert(1, "➕ 新增庫存項目")
    if can_update():  # 管理員
        tab_labels.insert(-1, "✏️ 庫存操作")
    
    tabs = st.tabs(tab_labels)
    
    # Tab 1: 庫存總覽
    tab_index = 0
    with tabs[tab_index]:
        show_inventory_overview(selected_machine_id, selected_machine_code)
    
    # Tab 2: 新增庫存項目（僅管理員）
    if can_create():
        tab_index += 1
        with tabs[tab_index]:
            show_add_inventory_item_form(selected_machine_id)
        tab_index += 1
    
    # Tab 3: 庫存操作（僅管理員）
    if can_update():
        with tabs[tab_index]:
            show_inventory_operations(selected_machine_id)
        tab_index += 1
    
    # Tab 4: 庫存統計
    with tabs[tab_index]:
        show_inventory_statistics(selected_machine_id)


def show_inventory_overview(machine_id: int, machine_code: str = 'N/A'):
    """顯示庫存總覽"""
    st.subheader("📋 庫存總覽")
    
    # 篩選選項
    col_filter, col_alert = st.columns([2, 3])
    with col_filter:
        status_filter = st.selectbox(
            "庫存狀態篩選",
            ["全部", "充足", "低庫存", "缺貨"],
            key="inventory_status_filter"
        )
    
    # 獲取庫存資料（後端自動返回統計）
    inventory_data = st.session_state.api.get_machine_inventory(machine_id)
    
    # 調試：顯示 API 返回的原始數據（僅在開發模式下）
    if inventory_data is None:
        st.error("❌ 無法獲取庫存資料")
        st.info("💡 可能的原因：\n- API 連接失敗\n- 機台不存在\n- 權限不足")
        ui_logger.warning(f"Failed to get inventory for machine {machine_id}: API returned None")
        return
    
    # 記錄 API 返回的數據結構（用於調試）
    ui_logger.debug(f"Inventory data for machine {machine_id}: {inventory_data}")
    
    # 檢查數據格式
    if not isinstance(inventory_data, dict):
        st.error(f"❌ API 返回數據格式錯誤：期望字典，實際為 {type(inventory_data)}")
        with st.expander("🔍 調試資訊", expanded=False):
            st.json(inventory_data)
        ui_logger.error(f"Invalid inventory data format for machine {machine_id}: {type(inventory_data)}")
        return
    
    # 後端 API 返回的鍵名是 'inventory_items'，不是 'items'
    # 為了向後兼容，同時檢查兩種鍵名
    items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
    
    # 如果 items 是 None，轉為空列表
    if items is None:
        items = []
        ui_logger.warning(f"Inventory items is None for machine {machine_id}, converting to empty list")
    
    if not items:
        st.info("📝 此機台目前沒有庫存項目")
        if can_create():
            st.info("💡 請在「新增庫存項目」頁面新增庫存")
        
        # 顯示調試資訊（如果有統計數據但沒有項目列表）
        if inventory_data.get('total_items', 0) > 0:
            st.warning("⚠️ 檢測到統計數據顯示有庫存項目，但項目列表為空")
            with st.expander("🔍 調試資訊", expanded=False):
                st.json(inventory_data)
        return
    
    # 統計資訊（後端自動計算）
    total_items = inventory_data.get('total_items', len(items))
    low_stock_count = inventory_data.get('low_stock_items', 0)
    out_of_stock_count = inventory_data.get('out_of_stock_items', 0)
    sufficient_count = total_items - low_stock_count - out_of_stock_count
    
    # 統計卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總項目數", total_items)
    with col2:
        st.metric("充足庫存", sufficient_count)
    with col3:
        delta_color = "inverse" if low_stock_count > 0 else "normal"
        st.metric("低庫存", low_stock_count, delta=None, delta_color=delta_color)
    with col4:
        delta_color = "inverse" if out_of_stock_count > 0 else "normal"
        st.metric("缺貨", out_of_stock_count, delta=None, delta_color=delta_color)
    
    st.markdown("---")
    
    # 低庫存告警區塊
    if low_stock_count > 0 or out_of_stock_count > 0:
        with col_alert:
            st.warning(f"⚠️ 發現 {low_stock_count + out_of_stock_count} 個項目需要關注")
            if st.button("🔍 查看低庫存項目", key="view_low_stock"):
                low_stock_items = st.session_state.api.get_low_stock_items(machine_id)
                if low_stock_items:
                    show_low_stock_alert(low_stock_items)
    
    # 調試資訊（可展開查看原始數據）
    with st.expander("🔍 調試資訊（點擊查看 API 返回的原始數據）", expanded=False):
        st.write("**機台資訊：**")
        st.write(f"- 機台 ID: {machine_id}")
        st.write(f"- 機台代碼: {machine_code}")
        st.write("\n**API 返回數據：**")
        st.json(inventory_data)
        st.write("\n**數據結構分析：**")
        st.write(f"- 數據類型: {type(inventory_data)}")
        st.write(f"- 是否為字典: {isinstance(inventory_data, dict)}")
        if isinstance(inventory_data, dict):
            st.write(f"- 包含的鍵: {list(inventory_data.keys())}")
            # 檢查兩種可能的鍵名
            inventory_items_key = 'inventory_items' if 'inventory_items' in inventory_data else 'items'
            st.write(f"- 使用的鍵名: {inventory_items_key}")
            st.write(f"- items 類型: {type(items)}")
            st.write(f"- items 長度: {len(items)}")
            if items:
                st.write(f"- 第一個項目結構: {list(items[0].keys()) if isinstance(items[0], dict) else type(items[0])}")
    
    # 篩選庫存項目
    filtered_items = filter_inventory_items(items, status_filter)
    
    # 庫存列表表格
    show_inventory_table(filtered_items, machine_id)


def filter_inventory_items(items: List[Dict], status_filter: str) -> List[Dict]:
    """篩選庫存項目"""
    if status_filter == "全部":
        return items
    
    filtered = []
    for item in items:
        current_stock = item.get('current_stock', 0)
        min_threshold = item.get('min_threshold', 0)
        
        if status_filter == "缺貨" and current_stock == 0:
            filtered.append(item)
        elif status_filter == "低庫存" and 0 < current_stock <= min_threshold:
            filtered.append(item)
        elif status_filter == "充足" and current_stock > min_threshold:
            filtered.append(item)
    
    return filtered


def show_inventory_table(items: List[Dict], machine_id: int):
    """顯示庫存列表表格"""
    st.subheader(f"庫存列表 ({len(items)} 個項目)")
    
    if not items:
        st.info("📝 沒有庫存項目可顯示")
        return
    
    # 建立 DataFrame
    df_data = []
    for idx, item in enumerate(items):
        try:
            # 安全地獲取數據，處理可能的 None 值
            if not isinstance(item, dict):
                ui_logger.warning(f"Item {idx} is not a dict: {type(item)}")
                continue
            
            current_stock = item.get('current_stock', 0) or 0
            min_threshold = item.get('min_threshold', 0) or 0
            max_capacity = item.get('max_capacity', 0) or 0
            
            # 判斷庫存狀態
            if current_stock == 0:
                status = "🔴 缺貨"
            elif current_stock <= min_threshold:
                status = "🟡 低庫存"
            else:
                status = "🟢 充足"
            
            # 處理 menu_item（可能是字典、None 或其他格式）
            menu_item = item.get('menu_item')
            if menu_item is None:
                menu_item = {}
                ui_logger.warning(f"Item {idx} has no menu_item")
            elif not isinstance(menu_item, dict):
                ui_logger.warning(f"Item {idx} menu_item is not a dict: {type(menu_item)}")
                menu_item = {}
            
            df_data.append({
                'ID': item.get('id', 'N/A'),
                '商品名稱': menu_item.get('name', 'N/A'),
                '商品代碼': menu_item.get('product_code', 'N/A'),
                '當前庫存': current_stock,
                '最低閾值': min_threshold,
                '最大容量': max_capacity,
                '庫存狀態': status,
                '供應商': item.get('supplier', '未設定') or '未設定',
                '批次編號': item.get('batch_number', 'N/A') or 'N/A',
                '到期日': format_date(item.get('expiry_date')),
                '單位成本': f"NT$ {item.get('cost_per_unit', 0):.2f}" if item.get('cost_per_unit') else 'N/A'
            })
        except Exception as e:
            ui_logger.error(f"Error processing item {idx}: {str(e)}")
            ui_logger.debug(f"Item data: {item}")
            continue
    
    if not df_data:
        st.info("📝 沒有符合條件的庫存項目")
        return
    
    df = pd.DataFrame(df_data)
    
    # 顯示表格
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    # 顯示每個項目的詳情和操作按鈕
    st.markdown("---")
    st.subheader("📦 庫存項目詳情")
    
    for item in items:
        show_inventory_item_details(item, machine_id)


def format_date(date_str: Optional[str]) -> str:
    """格式化日期顯示"""
    if not date_str:
        return 'N/A'
    try:
        if isinstance(date_str, str):
            # 嘗試解析 ISO 格式日期
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        return str(date_str)
    except:
        return str(date_str) if date_str else 'N/A'


def show_inventory_item_details(item: Dict, machine_id: int):
    """顯示庫存項目詳情和操作按鈕"""
    menu_item = item.get('menu_item', {})
    item_name = menu_item.get('name', 'N/A')
    current_stock = item.get('current_stock', 0)
    min_threshold = item.get('min_threshold', 0)
    
    # 判斷庫存狀態
    if current_stock == 0:
        status_icon = "🔴"
        status_text = "缺貨"
    elif current_stock <= min_threshold:
        status_icon = "🟡"
        status_text = "低庫存"
    else:
        status_icon = "🟢"
        status_text = "充足"
    
    with st.expander(f"{status_icon} {item_name} - {status_text}", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**商品代碼**: {menu_item.get('product_code', 'N/A')}")
            st.write(f"**當前庫存**: {current_stock}")
            st.write(f"**最低閾值**: {min_threshold}")
            st.write(f"**最大容量**: {item.get('max_capacity', 0)}")
        
        with col2:
            if item.get('supplier'):
                st.write(f"**供應商**: {item['supplier']}")
            if item.get('batch_number'):
                st.write(f"**批次編號**: {item['batch_number']}")
            if item.get('expiry_date'):
                st.write(f"**到期日**: {format_date(item['expiry_date'])}")
            if item.get('cost_per_unit'):
                st.write(f"**單位成本**: NT$ {item['cost_per_unit']:.2f}")
        
        # 操作按鈕（僅管理員）
        if can_update():
            col_edit, col_delete = st.columns(2)
            
            with col_edit:
                if st.button("✏️ 編輯設定", key=f"edit_inv_{item['id']}"):
                    show_edit_inventory_item_dialog(item, machine_id)
            
            with col_delete:
                if can_delete():  # 僅超級管理員
                    if st.button("🗑️ 移除項目", key=f"delete_inv_{item['id']}"):
                        show_delete_inventory_item_dialog(item, machine_id)


def show_low_stock_alert(low_stock_items: List[Dict]):
    """顯示低庫存告警"""
    st.warning("⚠️ **低庫存告警**")
    
    for item in low_stock_items:
        current = item.get('current_stock', 0)
        threshold = item.get('min_threshold', 0)
        status = "🔴 缺貨" if current == 0 else "🟡 低庫存"
        menu_item = item.get('menu_item', {})
        
        st.write(f"{status} **{menu_item.get('name', 'N/A')}**")
        st.write(f"  當前庫存: {current} / 最低閾值: {threshold}")
        if current < threshold:
            st.write(f"  建議補貨: {threshold - current} 個單位")
        st.markdown("---")


def show_add_inventory_item_form(machine_id: int):
    """顯示新增庫存項目表單"""
    st.subheader("➕ 新增庫存項目")
    
    # 獲取機台菜單項目（用於選擇）
    # 先嘗試獲取機台當前菜單項目
    machine_menu = st.session_state.api.get_machine_current_menu_items(machine_id)
    menu_items = []
    
    if machine_menu:
        # 如果返回的是字典格式，提取 items
        if isinstance(machine_menu, dict):
            menu_items = machine_menu.get('items', [])
        elif isinstance(machine_menu, list):
            menu_items = machine_menu
    
    # 如果機台沒有菜單項目，嘗試獲取所有菜單項目
    if not menu_items:
        all_menu_items = st.session_state.api.get_menu_items()
        if all_menu_items:
            menu_items = all_menu_items
            st.info("💡 此機台尚未設定菜單，顯示所有可用商品。建議先在機台管理中設定菜單。")
    
    if not menu_items:
        st.warning("⚠️ 沒有可用的菜單項目，請先新增商品")
        return
    
    with st.form("add_inventory_item_form", clear_on_submit=True):
        # 商品選擇
        menu_item_options = {
            f"{item['name']} ({item.get('product_code', 'N/A')})": item['id']
            for item in menu_items
        }
        selected_menu_item = st.selectbox(
            "選擇商品 *",
            options=list(menu_item_options.keys()),
            key="add_inv_menu_item"
        )
        menu_item_id = menu_item_options[selected_menu_item]
        
        # 庫存數量設定
        col1, col2 = st.columns(2)
        
        with col1:
            current_stock = st.number_input(
                "當前庫存數量 *",
                min_value=0,
                value=0,
                step=1,
                key="add_inv_current_stock"
            )
        
        with col2:
            min_threshold = st.number_input(
                "最低庫存閾值 *",
                min_value=0,
                value=10,
                step=1,
                help="當庫存低於此值時會顯示低庫存告警",
                key="add_inv_min_threshold"
            )
        
        max_capacity = st.number_input(
            "最大容量 *",
            min_value=1,
            value=100,
            step=1,
            help="此商品在此機台的最大庫存容量",
            key="add_inv_max_capacity"
        )
        
        # 可選資訊（使用 expander 隱藏，預設不展開）
        with st.expander("⚙️ 進階設定（可選）", expanded=False):
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                supplier = st.text_input(
                    "供應商",
                    placeholder="例：供應商A",
                    key="add_inv_supplier"
                )
                
                batch_number = st.text_input(
                    "批次編號",
                    placeholder="例：BATCH20250101",
                    key="add_inv_batch_number"
                )
            
            with col_opt2:
                expiry_date = st.date_input(
                    "到期日期",
                    value=None,
                    key="add_inv_expiry_date"
                )
                
                cost_per_unit = st.number_input(
                    "單位成本 (NT$)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="add_inv_cost_per_unit"
                )
        
        submitted = st.form_submit_button("✨ 新增庫存項目", type="primary")
        
        if submitted:
            # 驗證
            if current_stock > max_capacity:
                st.error("❌ 當前庫存不能超過最大容量")
            elif min_threshold >= max_capacity:
                st.error("❌ 最低閾值應小於最大容量")
            else:
                # 構建請求資料
                data = {
                    "menu_item_id": menu_item_id,
                    "current_stock": current_stock,
                    "min_threshold": min_threshold,
                    "max_capacity": max_capacity
                }
                
                # 添加可選欄位
                if supplier:
                    data["supplier"] = supplier
                if batch_number:
                    data["batch_number"] = batch_number
                if expiry_date:
                    data["expiry_date"] = expiry_date.isoformat()
                if cost_per_unit > 0:
                    data["cost_per_unit"] = float(cost_per_unit)
                
                # 調用 API
                result = st.session_state.api.create_inventory_item(machine_id, data)
                if result:
                    st.success(f"✅ 庫存項目新增成功！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 新增庫存項目失敗，請檢查輸入資料")


def show_inventory_operations(machine_id: int):
    """顯示庫存操作頁面"""
    st.subheader("✏️ 庫存操作")
    
    # 獲取庫存列表
    inventory_data = st.session_state.api.get_machine_inventory(machine_id)
    # 後端 API 返回的鍵名是 'inventory_items'
    items = (inventory_data.get('inventory_items') or inventory_data.get('items') or []) if inventory_data else []
    
    if not items:
        st.info("📝 此機台目前沒有庫存項目")
        return
    
    # 操作類型選擇
    operation_type = st.radio(
        "選擇操作類型",
        ["📦 補貨", "🛒 銷售扣減", "✏️ 手動調整", "⚠️ 損壞/過期"],
        horizontal=True,
        key="inv_operation_type"
    )
    
    st.markdown("---")
    
    # 根據操作類型設定 operation_type 值
    operation_map = {
        "📦 補貨": "restock",
        "🛒 銷售扣減": "sale",
        "✏️ 手動調整": "adjustment",
        "⚠️ 損壞/過期": "expired"
    }
    
    selected_operation = operation_map[operation_type]
    
    # 商品選擇
    item_options = {}
    for item in items:
        menu_item = item.get('menu_item', {})
        item_name = menu_item.get('name', 'N/A')
        current_stock = item.get('current_stock', 0)
        item_id = item.get('id')
        if item_id:
            item_options[f"{item_name} (庫存: {current_stock})"] = item_id
    
    if not item_options:
        st.warning("⚠️ 沒有可用的庫存項目")
        return
    
    selected_item_name = st.selectbox(
        "選擇商品",
        options=list(item_options.keys()),
        key="inv_operation_item"
    )
    selected_item_id = item_options[selected_item_name]
    
    # 找到選中的項目詳情
    selected_item = next(
        (item for item in items if item.get('id') == selected_item_id),
        None
    )
    
    if not selected_item:
        st.error("❌ 找不到選中的庫存項目")
        return
    
    current_stock = selected_item.get('current_stock', 0)
    max_capacity = selected_item.get('max_capacity', 0)
    
    st.info(f"**當前庫存**: {current_stock} / {max_capacity}")
    
    # 數量輸入
    quantity_change = 0
    preview_stock = current_stock
    
    if operation_type == "📦 補貨":
        max_restock = max_capacity - current_stock if max_capacity > current_stock else 9999
        quantity_change = st.number_input(
            "補貨數量",
            min_value=1,
            max_value=max_restock,
            value=1,
            step=1,
            help=f"最多可補貨 {max_restock} 個單位" if max_restock < 9999 else "無限制",
            key="inv_restock_quantity"
        )
        preview_stock = current_stock + quantity_change
    elif operation_type == "🛒 銷售扣減":
        quantity_change = st.number_input(
            "銷售數量",
            min_value=1,
            max_value=current_stock,
            value=1,
            step=1,
            help=f"最多可扣減 {current_stock} 個單位",
            key="inv_sale_quantity"
        )
        quantity_change = -quantity_change  # 轉為負數
        preview_stock = current_stock + quantity_change
    elif operation_type == "✏️ 手動調整":
        new_stock = st.number_input(
            "調整後庫存",
            min_value=0,
            max_value=max_capacity,
            value=current_stock,
            step=1,
            key="inv_adjust_stock"
        )
        quantity_change = new_stock - current_stock
        preview_stock = new_stock
    else:  # 損壞/過期
        quantity_change = st.number_input(
            "損壞/過期數量",
            min_value=1,
            max_value=current_stock,
            value=1,
            step=1,
            key="inv_expired_quantity"
        )
        quantity_change = -quantity_change  # 轉為負數
        preview_stock = current_stock + quantity_change
    
    # 顯示預覽
    if quantity_change != 0:
        if preview_stock < 0:
            st.error(f"❌ 調整後庫存不能為負數（預期: {preview_stock}）")
        elif preview_stock > max_capacity:
            st.error(f"❌ 調整後庫存不能超過最大容量（預期: {preview_stock} > {max_capacity}）")
        else:
            st.success(f"✅ 調整後庫存: {current_stock} → {preview_stock}")
    
    # 備註
    notes = st.text_area(
        "備註說明",
        placeholder="輸入操作備註...",
        key="inv_operation_notes"
    )
    
    # 提交按鈕
    if st.button("💾 執行操作", type="primary", key="inv_operation_submit"):
        if quantity_change == 0:
            st.warning("⚠️ 數量變更為 0，無需更新")
        else:
            data = {
                "quantity_change": quantity_change,
                "operation_type": selected_operation,
            }
            if notes:
                data["notes"] = notes
            
            success = st.session_state.api.update_inventory_stock(
                machine_id, selected_item_id, data
            )
            
            if success:
                st.success(f"✅ 庫存更新成功！")
                st.rerun()
            else:
                st.error("❌ 庫存更新失敗")


def show_edit_inventory_item_dialog(item: Dict, machine_id: int):
    """顯示編輯庫存項目對話框"""
    @st.dialog(f"✏️ 編輯庫存項目 - {item.get('menu_item', {}).get('name', 'Unknown')}")
    def edit_dialog():
        col1, col2 = st.columns(2)
        
        with col1:
            min_threshold = st.number_input(
                "最低庫存閾值",
                min_value=0,
                value=item.get('min_threshold', 0),
                step=1,
                key=f"edit_threshold_{item['id']}"
            )
            
            max_capacity = st.number_input(
                "最大容量",
                min_value=1,
                value=item.get('max_capacity', 1),
                step=1,
                key=f"edit_capacity_{item['id']}"
            )
        
        with col2:
            supplier = st.text_input(
                "供應商",
                value=item.get('supplier', ''),
                key=f"edit_supplier_{item['id']}"
            )
            
            batch_number = st.text_input(
                "批次編號",
                value=item.get('batch_number', ''),
                key=f"edit_batch_{item['id']}"
            )
            
            expiry_date_str = item.get('expiry_date')
            expiry_date = None
            if expiry_date_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00')).date()
                except:
                    pass
            
            expiry_date = st.date_input(
                "到期日期",
                value=expiry_date,
                key=f"edit_expiry_{item['id']}"
            )
            
            # 安全地處理 cost_per_unit，可能是 None
            cost_per_unit_value = item.get('cost_per_unit')
            if cost_per_unit_value is None:
                cost_per_unit_value = 0.0
            else:
                try:
                    cost_per_unit_value = float(cost_per_unit_value)
                except (ValueError, TypeError):
                    cost_per_unit_value = 0.0
            
            cost_per_unit = st.number_input(
                "單位成本 (NT$)",
                min_value=0.0,
                value=cost_per_unit_value,
                step=0.01,
                format="%.2f",
                key=f"edit_cost_{item['id']}"
            )
        
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            if st.button("💾 儲存更改", width="stretch", type="primary"):
                # 驗證
                if min_threshold >= max_capacity:
                    st.error("❌ 最低閾值應小於最大容量")
                else:
                    data = {
                        "min_threshold": min_threshold,
                        "max_capacity": max_capacity,
                        "supplier": supplier if supplier else None,
                        "batch_number": batch_number if batch_number else None,
                        "cost_per_unit": float(cost_per_unit) if cost_per_unit and cost_per_unit > 0 else None
                    }
                    
                    if expiry_date:
                        data["expiry_date"] = expiry_date.isoformat()
                    
                    success = st.session_state.api.update_inventory_item(machine_id, item['id'], data)
                    if success:
                        st.success("✅ 庫存項目更新成功！")
                        st.rerun()
                    else:
                        st.error("❌ 更新失敗")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
    
    edit_dialog()


def show_delete_inventory_item_dialog(item: Dict, machine_id: int):
    """顯示刪除庫存項目對話框"""
    menu_item = item.get('menu_item', {})
    item_name = menu_item.get('name', 'Unknown')
    
    @st.dialog(f"🗑️ 刪除庫存項目 - {item_name}")
    def delete_dialog():
        st.error("⚠️ **危險操作警告**")
        st.write(f"您即將移除庫存項目：**{item_name}**")
        st.write(f"當前庫存：{item.get('current_stock', 0)}")
        
        st.markdown("---")
        st.warning("⚠️ **此操作將永久移除庫存項目，無法復原！**")
        
        # 確認輸入
        st.write("請輸入項目名稱以確認刪除：")
        confirmation_input = st.text_input("", placeholder=f"請輸入 '{item_name}'", key=f"delete_confirm_{item['id']}")
        
        col_delete, col_cancel = st.columns(2)
        
        with col_delete:
            delete_enabled = confirmation_input == item_name
            if st.button("🗑️ 確認刪除", width="stretch", type="primary", disabled=not delete_enabled):
                if delete_enabled:
                    success = st.session_state.api.delete_inventory_item(machine_id, item['id'])
                    if success:
                        ui_logger.info(f"Admin {st.session_state.get('username')} deleted inventory item {item['id']}")
                        st.success(f"✅ 庫存項目 '{item_name}' 已成功移除！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 移除庫存項目失敗")
        
        with col_cancel:
            if st.button("❌ 取消", width="stretch"):
                st.rerun()
        
        if not delete_enabled and confirmation_input:
            st.error("❌ 輸入的項目名稱不正確")
    
    delete_dialog()


def show_inventory_statistics(machine_id: int):
    """顯示庫存統計"""
    st.subheader("📊 庫存統計")
    
    inventory_data = st.session_state.api.get_machine_inventory(machine_id)
    
    # 後端 API 返回的鍵名是 'inventory_items'
    items = (inventory_data.get('inventory_items') or inventory_data.get('items') or []) if inventory_data else []
    
    if not inventory_data or not items:
        st.info("📝 此機台目前沒有庫存數據")
        return
    
    # 統計卡片
    total_items = inventory_data.get('total_items', len(items))
    low_stock_count = inventory_data.get('low_stock_items', 0)
    out_of_stock_count = inventory_data.get('out_of_stock_items', 0)
    sufficient_count = total_items - low_stock_count - out_of_stock_count
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總項目數", total_items)
    with col2:
        st.metric("充足庫存", sufficient_count)
    with col3:
        st.metric("低庫存項目", low_stock_count)
    with col4:
        st.metric("缺貨項目", out_of_stock_count)
    
    st.markdown("---")
    
    # 庫存分布圖
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 庫存狀態分布")
        status_counts = {
            "充足": 0,
            "低庫存": 0,
            "缺貨": 0
        }
        
        for item in items:
            stock = item.get('current_stock', 0)
            threshold = item.get('min_threshold', 0)
            
            if stock == 0:
                status_counts["缺貨"] += 1
            elif stock <= threshold:
                status_counts["低庫存"] += 1
            else:
                status_counts["充足"] += 1
        
        if sum(status_counts.values()) > 0:
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="庫存狀態分布"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("沒有數據可顯示")
    
    with col2:
        st.subheader("📈 庫存容量使用率")
        # 計算各商品的庫存使用率
        usage_data = []
        for item in items:
            current = item.get('current_stock', 0)
            max_cap = item.get('max_capacity', 1)
            usage_rate = (current / max_cap * 100) if max_cap > 0 else 0
            
            menu_item = item.get('menu_item', {})
            usage_data.append({
                '商品': menu_item.get('name', 'N/A'),
                '使用率 (%)': usage_rate
            })
        
        if usage_data:
            df_usage = pd.DataFrame(usage_data)
            # 只顯示前10個商品，避免圖表過於擁擠
            df_usage_top = df_usage.nlargest(10, '使用率 (%)')
            fig = px.bar(
                df_usage_top,
                x='商品',
                y='使用率 (%)',
                title="各商品庫存容量使用率（前10名）"
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("沒有數據可顯示")
    
    # 低庫存項目列表
    st.markdown("---")
    st.subheader("⚠️ 低庫存項目詳情")
    low_stock_items = [
        item for item in items
        if item.get('current_stock', 0) <= item.get('min_threshold', 0)
    ]
    
    if low_stock_items:
        low_stock_df = pd.DataFrame([
            {
                '商品名稱': item.get('menu_item', {}).get('name', 'N/A'),
                '當前庫存': item.get('current_stock', 0),
                '最低閾值': item.get('min_threshold', 0),
                '缺額': max(0, item.get('min_threshold', 0) - item.get('current_stock', 0)),
                '狀態': '缺貨' if item.get('current_stock', 0) == 0 else '低庫存'
            }
            for item in low_stock_items
        ])
        st.dataframe(low_stock_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ 目前沒有低庫存項目")
