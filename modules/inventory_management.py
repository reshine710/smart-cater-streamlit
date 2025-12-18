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
    """機台庫存管理主頁面 - 卡片式設計（僅顯示）"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing inventory management page")
    st.title("📦 庫存管理")
    
    # 添加重新整理按鈕（與機台狀態頁面一致）
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        pass  # 保留標題空間
    with col_refresh:
        if st.button("🔄 重新整理", key="refresh_inventory_all", type="secondary", width='stretch'):
            # 清除可能的快取，強制重新獲取資料
            if 'inventory_cache' in st.session_state:
                del st.session_state.inventory_cache
            if 'machines_cache' in st.session_state:
                del st.session_state.machines_cache
            ui_logger.info("User triggered refresh inventory data")
            st.success("✅ 正在重新整理庫存資料...")
            time.sleep(0.5)  # 短暫延遲讓用戶看到提示
            st.rerun()
    
    st.markdown("---")
    
    # 獲取所有機台
    machines = st.session_state.api.get_machines()
    if not machines:
        st.warning("⚠️ 目前沒有可用的機台")
        return
    
    # 使用 Tabs 分開不同層級的視圖
    tab1, tab2 = st.tabs(["📊 全域戰情看板", "🔍 單機台檢視"])
    
    with tab1:
        show_inventory_dashboard(machines)
    
    with tab2:
        show_machine_detail_view(machines)


def show_inventory_dashboard(machines: List[Dict]):
    """顯示全域戰情看板"""
    
    # 注入全局 CSS 樣式（與機台狀態頁面一致）
    st.markdown("""
    <style>
    .machine-card {
        width: 100%;
        height: 180px;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        box-sizing: border-box;
    }
    .machine-card-content {
        text-align: center;
        width: 100%;
    }
    .machine-card-title {
        margin: 0;
        font-size: 1.1em;
        font-weight: bold;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: 100%;
    }
    .machine-card-subtitle {
        margin: 5px 0 0 0;
        font-size: 0.9em;
        color: #666;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: 100%;
    }
    .machine-card-info {
        margin: 5px 0 0 0;
        font-size: 0.85em;
        color: #888;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 獲取所有機台的庫存數據
    machine_data = []
    critical_count = 0
    warning_count = 0
    good_count = 0
    
    with st.spinner("正在載入機台庫存數據..."):
        for machine in machines:
            machine_id = machine.get('id')
            if not machine_id:
                continue
            
            inventory_data = st.session_state.api.get_machine_inventory(machine_id)
            if not inventory_data:
                continue
            
            items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
            total_items = inventory_data.get('total_items', len(items))
            low_stock_count = inventory_data.get('low_stock_items', 0)
            out_of_stock_count = inventory_data.get('out_of_stock_items', 0)
            
            # 計算健康度（基於缺貨和低庫存比例）
            if total_items > 0:
                problem_ratio = (out_of_stock_count + low_stock_count) / total_items
                health_score = 1.0 - problem_ratio
            else:
                health_score = 0.0
            
            # 判斷狀態
            if out_of_stock_count > 0 or health_score < 0.2:
                status = "Critical"
                critical_count += 1
            elif low_stock_count > 0 or health_score < 0.5:
                status = "Warning"
                warning_count += 1
            else:
                status = "Good"
                good_count += 1
            
            machine_name = machine.get('name', 'Unknown')
            machine_code = machine.get('machine_code', 'N/A')
            
            # 處理位置資訊（與機台狀態頁面一致）
            location = machine.get('location', {})
            if isinstance(location, dict):
                location_name = location.get('name', '未知位置')
            else:
                location_name = str(location) if location else '未知位置'
            
            machine_data.append({
                "Machine ID": machine_code,
                "機台名稱": machine_name,
                "Location": location_name if location_name != '未知位置' else "未設定",
                "Status": status,
                "Stockout_Items": out_of_stock_count,
                "Low_Stock_Items": low_stock_count,
                "Total_Items": total_items,
                "Health_Score": health_score
            })
    
    # 頂部 KPI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🔴 急需補貨機台", 
            f"{critical_count} 台", 
            delta=f"{critical_count} 待處理" if critical_count > 0 else None,
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "🟡 警戒中機台", 
            f"{warning_count} 台",
            delta=f"{warning_count} 需關注" if warning_count > 0 else None
        )
    
    with col3:
        st.metric(
            "🟢 正常運作", 
            f"{good_count} 台"
        )
    
    st.divider()
    
    st.markdown("### 📋 機台庫存狀態 (優先處理紅燈機台)")
    
    if machine_data:
        # 按狀態分組
        status_groups = {
            "Critical": [],
            "Warning": [],
            "Good": []
        }
        
        for data in machine_data:
            status = data.get("Status", "Good")
            if status in status_groups:
                status_groups[status].append(data)
        
        # 狀態配置
        status_configs = {
            "Critical": {
                "icon": "🔴",
                "title": "急需補貨",
                "bg_color": "#f8d7da",
                "border_color": "#dc3545"
            },
            "Warning": {
                "icon": "🟡",
                "title": "警戒中",
                "bg_color": "#fff3cd",
                "border_color": "#ffc107"
            },
            "Good": {
                "icon": "🟢",
                "title": "正常運作",
                "bg_color": "#d4edda",
                "border_color": "#28a745"
            }
        }
        
        # 顯示卡片（按狀態分組）
        for status, machines_in_status in status_groups.items():
            if not machines_in_status:
                continue
            
            config = status_configs[status]
            st.markdown(f"### {config['icon']} {config['title']} ({len(machines_in_status)}台)")
            
            # 創建響應式網格布局（每行3個卡片）
            cols_per_row = 3
            for i in range(0, len(machines_in_status), cols_per_row):
                cols = st.columns(cols_per_row)
                
                for j, machine_info in enumerate(machines_in_status[i:i+cols_per_row]):
                    with cols[j]:
                        # 從 machines 列表中找到對應的 machine_id
                        machine_code = machine_info.get("Machine ID", "N/A")
                        machine_id = None
                        for m in machines:
                            if m.get('machine_code') == machine_code:
                                machine_id = m.get('id')
                                break
                        render_inventory_machine_card(machine_info, config, machine_id)
    else:
        st.info("📝 目前沒有機台庫存數據")


@st.dialog("🔍 機台庫存透視", width="large")
def show_machine_inventory_dialog(machine_id: int, machine_name: str, machine_code: str, location: str):
    """顯示機台庫存詳細透視 dialog"""
    st.markdown(f"### {machine_name} ({machine_code})")
    if location and location != "未設定":
        st.markdown(f"**地點**: {location}")
    
    st.divider()
    
    # 過濾器
    filter_mode = st.radio(
        "顯示模式:", 
        ["全部顯示", "只看缺貨/警告"], 
        horizontal=True,
        key=f"dialog_filter_{machine_id}"
    )
    
    # st.info("💡 提示：介面模擬真實機台排列，紅色代表庫存為 0，黃色代表低於安全庫存，綠色代表正常。")
    
    # 獲取庫存數據
    inventory_data = st.session_state.api.get_machine_inventory(machine_id)
    
    if not inventory_data:
        st.error("❌ 無法獲取庫存資料")
        return
    
    items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
    
    if not items:
        st.info("📝 此機台目前沒有庫存項目")
        return
    
    # 處理商品數據
    products = []
    for item in items:
        menu_item = item.get('menu_item', {})
        current_stock = item.get('current_stock', 0) or 0
        min_threshold = item.get('min_threshold', 0) or 0
        max_capacity = item.get('max_capacity', 1) or 1
        
        # 判斷狀態
        if current_stock == 0:
            color = "🔴"
            msg = "缺貨 (Stockout)"
        elif current_stock <= min_threshold:
            color = "🟡"
            msg = "低庫存 (Low)"
        else:
            color = "🟢"
            msg = "正常 (OK)"
        
        # 處理 product_code（如果為 None 或空字符串則使用默認值）
        product_code = menu_item.get('product_code') or 'N/A'
        product_name = menu_item.get('name', 'Unknown')
        
        products.append({
            "id": item.get('id'),
            "slot": product_code,  # 使用商品代碼作為貨道號
            "name": product_name,
            "current": current_stock,
            "min": min_threshold,
            "max": max_capacity,
            "color": color,
            "msg": msg,
            "item": item  # 保存完整項目數據用於操作
        })
    
    # 過濾商品
    if filter_mode == "只看缺貨/警告":
        products = [p for p in products if p['color'] in ["🔴", "🟡"]]
    
    if not products:
        st.success("✅ 所有商品庫存充足！")
        return
    
    # 網格佈局：每行 4 個商品
    cols_per_row = 4
    
    for i in range(0, len(products), cols_per_row):
        cols = st.columns(cols_per_row)
        batch = products[i:i+cols_per_row]
        
        for idx, product in enumerate(batch):
            with cols[idx]:
                # 卡片式設計
                with st.container(border=True):
                    # 標題區：燈號 + 貨道號
                    st.markdown(f"**{product['color']} {product['slot']}** {product['name']}")
                    
                    # 計算比例給進度條用
                    progress = product['current'] / product['max'] if product['max'] > 0 else 0
                    
                    # 進度條
                    st.progress(progress)
                    
                    # 關鍵數字
                    st.caption(f"庫存: {product['current']} / 最大: {product['max']}")
                    st.caption(f"警戒線: {product['min']}")
                    
                    # 狀態文字和補貨建議
                    if product['color'] == "🔴":
                        st.error(f"缺貨! 需補 {product['max']} 個")
                    elif product['color'] == "🟡":
                        restock_qty = product['max'] - product['current']
                        st.warning(f"請補貨 (建議補 {restock_qty} 個)")
                    else:
                        st.success("庫存充足")


def render_inventory_machine_card(machine_info: Dict, status_config: Dict, machine_id: int = None):
    """渲染單個機台庫存卡片（與機台狀態頁面一致的樣式）"""
    machine_code = machine_info.get("Machine ID", "N/A")
    machine_name = machine_info.get("機台名稱", "Unknown")
    location = machine_info.get("Location", "未設定")
    status = machine_info.get("Status", "Good")
    stockout_items = machine_info.get("Stockout_Items", 0)
    low_stock_items = machine_info.get("Low_Stock_Items", 0)
    total_items = machine_info.get("Total_Items", 0)
    health_score = machine_info.get("Health_Score", 0.0)
    health_percentage = int(health_score * 100)
    
    # 創建卡片容器（與機台狀態頁面一致的結構）
    with st.container():
        # 使用 CSS 類別 + 動態樣式（背景色和邊框色）
        card_style = f"""
        <div class="machine-card" style="
            background-color: {status_config['bg_color']};
            border: 2px solid {status_config['border_color']};
        ">
            <div class="machine-card-content">
                <h4 class="machine-card-title" style="color: {status_config['border_color']};">
                    {status_config['icon']} {machine_name}
                </h4>
                <p class="machine-card-subtitle">
                    {machine_code}
                </p>
                <p class="machine-card-info">
                    📍 {location}
                </p>
                <p class="machine-card-info" style="margin-top: 8px;">
                    📦 總項目: {total_items} | 缺貨: {stockout_items} | 低庫存: {low_stock_items}
                </p>
            </div>
        </div>
        """
        # <p class="machine-card-info" style="margin-top: 5px; font-weight: bold;">
        #        庫存警示燈號: {status_config['icon']}
        # </p>
        
        st.markdown(card_style, unsafe_allow_html=True)
        
        # 點擊按鈕來顯示詳細透視畫面
        if machine_id:
            if st.button("🔍 查看詳細", key=f"view_detail_{machine_id}", use_container_width=True):
                show_machine_inventory_dialog(machine_id, machine_name, machine_code, location)
            
            # 管理庫存按鈕（僅管理員）
            if can_create() or can_update():
                if st.button("🛠 管理庫存", key=f"manage_inventory_{machine_id}", use_container_width=True):
                    show_inventory_management_dialog(machine_id, machine_name, machine_code)


def show_machine_detail_view(machines: List[Dict]):
    """顯示單機台詳細檢視"""
    st.markdown("### 🔍 機台透視")
    
    # 機台選擇器
    machine_options = {}
    machine_id_to_info = {}
    for machine in machines:
        machine_id = machine.get('id')
        machine_name = machine.get('name', 'Unknown')
        machine_code = machine.get('machine_code', 'N/A')
        
        # 處理位置資訊（與機台狀態頁面一致）
        location = machine.get('location', {})
        if isinstance(location, dict):
            location_name = location.get('name', '未知位置')
        else:
            location_name = str(location) if location else '未知位置'
        
        if machine_id:
            display_name = f"{machine_name} ({machine_code})"
            if location_name and location_name != '未知位置':
                display_name += f" - {location_name}"
            machine_options[display_name] = machine_id
            machine_id_to_info[machine_id] = {
                'name': machine_name,
                'code': machine_code,
                'location': location_name if location_name != '未知位置' else "未設定"
            }
    
    if not machine_options:
        st.warning("⚠️ 無法取得機台資訊")
        return
    
    # 機台選擇
    col_select, col_refresh = st.columns([4, 1])
    with col_select:
        selected_machine_name = st.selectbox(
            "選擇機台",
            options=list(machine_options.keys()),
            key="detail_machine_selector"
        )
        selected_machine_id = machine_options[selected_machine_name]
        machine_info = machine_id_to_info[selected_machine_id]
    
    with col_refresh:
        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 重新整理", type="secondary", width='stretch', key="refresh_detail"):
            st.rerun()
    
    st.markdown(f"**機台**: {machine_info['name']} ({machine_info['code']})")
    if machine_info['location']:
        st.markdown(f"**地點**: {machine_info['location']}")
    
    # 管理按鈕（僅管理員）
    if can_create() or can_update():
        st.divider()
        col_add, col_edit, col_delete = st.columns(3)
        
        with col_add:
            if st.button("➕ 新增庫存項目", use_container_width=True, key="add_inventory_btn"):
                show_simple_inventory_form(selected_machine_id, mode="create")
        
        with col_edit:
            if st.button("✏️ 編輯庫存項目", use_container_width=True, key="edit_inventory_btn"):
                show_simple_inventory_form(selected_machine_id, mode="edit")
        
        with col_delete:
            if can_delete():
                if st.button("🗑️ 刪除庫存項目", use_container_width=True, key="delete_inventory_btn"):
                    show_simple_inventory_form(selected_machine_id, mode="delete")
            else:
                st.button("🗑️ 刪除庫存項目", use_container_width=True, key="delete_inventory_btn_disabled", disabled=True)
    
    st.divider()
    
    # 過濾器
    filter_mode = st.radio(
        "顯示模式:", 
        ["全部顯示", "只看缺貨/警告"], 
        horizontal=True,
        key="detail_filter_mode"
    )
    
    st.info("💡 提示：介面模擬真實機台排列，紅色代表庫存為 0，黃色代表低於安全庫存，綠色代表正常。")
    
    # 獲取庫存數據
    inventory_data = st.session_state.api.get_machine_inventory(selected_machine_id)
    
    if not inventory_data:
        st.error("❌ 無法獲取庫存資料")
        return
    
    items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
    
    if not items:
        st.info("📝 此機台目前沒有庫存項目")
        if can_create():
            st.info("💡 請在「管理功能」中新增庫存項目")
        return
    
    # 處理商品數據
    products = []
    for item in items:
        menu_item = item.get('menu_item', {})
        current_stock = item.get('current_stock', 0) or 0
        min_threshold = item.get('min_threshold', 0) or 0
        max_capacity = item.get('max_capacity', 1) or 1
        
        # 判斷狀態
        if current_stock == 0:
            color = "🔴"
            msg = "缺貨 (Stockout)"
        elif current_stock <= min_threshold:
            color = "🟡"
            msg = "低庫存 (Low)"
        else:
            color = "🟢"
            msg = "正常 (OK)"
        
        # 處理 product_code（如果為 None 或空字符串則使用默認值）
        product_code = menu_item.get('product_code') or 'N/A'
        product_name = menu_item.get('name', 'Unknown')
        
        products.append({
            "id": item.get('id'),
            "slot": product_code,  # 使用商品代碼作為貨道號
            "name": product_name,
            "current": current_stock,
            "min": min_threshold,
            "max": max_capacity,
            "color": color,
            "msg": msg,
            "item": item  # 保存完整項目數據用於操作
        })
    
    # 過濾商品
    if filter_mode == "只看缺貨/警告":
        products = [p for p in products if p['color'] in ["🔴", "🟡"]]
    
    if not products:
        st.success("✅ 所有商品庫存充足！")
        return
    
    # 網格佈局：每行 4 個商品
    cols_per_row = 4
    
    for i in range(0, len(products), cols_per_row):
        cols = st.columns(cols_per_row)
        batch = products[i:i+cols_per_row]
        
        for idx, product in enumerate(batch):
            with cols[idx]:
                # 卡片式設計
                with st.container(border=True):
                    # 標題區：燈號 + 貨道號
                    st.markdown(f"**{product['color']} {product['slot']}** {product['name']}")
                    
                    # 計算比例給進度條用
                    progress = product['current'] / product['max'] if product['max'] > 0 else 0
                    
                    # 進度條
                    st.progress(progress)
                    
                    # 關鍵數字
                    st.caption(f"庫存: {product['current']} / 最大: {product['max']}")
                    st.caption(f"警戒線: {product['min']}")
                    
                    # 狀態文字和補貨建議
                    if product['color'] == "🔴":
                        st.error(f"缺貨! 需補 {product['max']} 個")
                    elif product['color'] == "🟡":
                        restock_qty = product['max'] - product['current']
                        st.warning(f"請補貨 (建議補 {restock_qty} 個)")
                    else:
                        st.success("庫存充足")


@st.dialog("📦 庫存管理", width="large")
def show_inventory_management_dialog(machine_id: int, machine_name: str, machine_code: str):
    """顯示庫存管理 dialog（使用 tabs 切換功能）"""
    st.markdown(f"### {machine_name} ({machine_code})")
    st.divider()
    
    # 使用 tabs 來切換不同的管理功能
    tab1, tab2, tab3 = st.tabs(["➕ 新增庫存項目", "✏️ 編輯庫存項目", "🗑️ 刪除庫存項目"])
    
    with tab1:
        if can_create():
            show_simple_inventory_form_inline(machine_id, mode="create")
        else:
            st.warning("⚠️ 您沒有新增庫存項目的權限")
    
    with tab2:
        if can_update():
            show_simple_inventory_form_inline(machine_id, mode="edit")
        else:
            st.warning("⚠️ 您沒有編輯庫存項目的權限")
    
    with tab3:
        if can_delete():
            show_simple_inventory_form_inline(machine_id, mode="delete")
        else:
            st.warning("⚠️ 您沒有刪除庫存項目的權限")


def show_simple_inventory_form_inline(machine_id: int, mode: str = "create"):
    """簡單的庫存管理表單（內聯版本，可在 dialog 中使用）"""
    # 獲取機台的菜單項目
    machine_menu = st.session_state.api.get_machine_current_menu_items(machine_id)
    menu_items = []
    
    if machine_menu:
        if isinstance(machine_menu, dict):
            menu_items = machine_menu.get('items', [])
        elif isinstance(machine_menu, list):
            menu_items = machine_menu
    
    if not menu_items:
        # 如果沒有機台專屬菜單，獲取所有菜單項目
        menu_items = st.session_state.api.get_menu_items()
    
    if not menu_items:
        st.error("❌ 無法獲取菜單項目，請先建立菜單項目")
        return
    
    # 獲取當前庫存項目
    inventory_data = st.session_state.api.get_machine_inventory(machine_id)
    current_items = []
    if inventory_data:
        items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
        current_items = items
    
    if mode == "create":
        st.markdown("### ➕ 新增庫存項目")
        
        with st.form("create_inventory_form"):
            # 產品選擇
            menu_options = {}
            for item in menu_items:
                product_code = item.get('product_code') or 'N/A'
                name = item.get('name', 'Unknown')
                display_name = f"{name} ({product_code})"
                menu_options[display_name] = item.get('id')
            
            # 過濾已存在的項目
            existing_menu_ids = {item.get('menu_item', {}).get('id') for item in current_items if item.get('menu_item')}
            available_options = {k: v for k, v in menu_options.items() if v not in existing_menu_ids}
            
            if not available_options:
                st.warning("⚠️ 所有菜單項目都已添加到庫存中")
                return
            
            selected_menu_name = st.selectbox(
                "選擇產品",
                options=list(available_options.keys()),
                key="create_menu_select"
            )
            selected_menu_id = available_options[selected_menu_name]
            
            # 最低閾值
            min_threshold = st.number_input(
                "最低閾值",
                min_value=0,
                value=10,
                step=1,
                key="create_min_threshold"
            )
            
            # 最大容量
            max_capacity = st.number_input(
                "最大容量",
                min_value=1,
                value=100,
                step=1,
                key="create_max_capacity"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 確認新增", type="primary", use_container_width=True):
                    data = {
                        "menu_item_id": selected_menu_id,
                        "min_threshold": min_threshold,
                        "max_capacity": max_capacity
                    }
                    result = st.session_state.api.create_inventory_item(machine_id, data)
                    if result:
                        st.success("✅ 新增成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 新增失敗")
            
            with col2:
                if st.form_submit_button("❌ 取消", use_container_width=True):
                    st.rerun()
    
    elif mode == "edit":
        st.markdown("### ✏️ 編輯庫存項目")
        
        if not current_items:
            st.info("📝 此機台目前沒有庫存項目")
            return
        
        # 選擇要編輯的項目
        item_options = {}
        for item in current_items:
            menu_item = item.get('menu_item', {})
            product_code = menu_item.get('product_code') or 'N/A'
            name = menu_item.get('name', 'Unknown')
            display_name = f"{name} ({product_code})"
            item_options[display_name] = item
        
        selected_item_name = st.selectbox(
            "選擇要編輯的庫存項目",
            options=list(item_options.keys()),
            key="edit_item_select"
        )
        selected_item = item_options[selected_item_name]
        
        with st.form("edit_inventory_form"):
            # 顯示當前產品資訊（不可編輯）
            menu_item = selected_item.get('menu_item', {})
            product_code = menu_item.get('product_code') or 'N/A'
            product_name = menu_item.get('name', 'Unknown')
            st.info(f"**產品**: {product_name} ({product_code})")
            
            # 最低閾值
            min_threshold = st.number_input(
                "最低閾值",
                min_value=0,
                value=int(selected_item.get('min_threshold', 0)),
                step=1,
                key="edit_min_threshold"
            )
            
            # 最大容量
            max_capacity = st.number_input(
                "最大容量",
                min_value=1,
                value=int(selected_item.get('max_capacity', 1)),
                step=1,
                key="edit_max_capacity"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 確認更新", type="primary", use_container_width=True):
                    data = {
                        "min_threshold": min_threshold,
                        "max_capacity": max_capacity
                    }
                    item_id = selected_item.get('id')
                    success = st.session_state.api.update_inventory_item(machine_id, item_id, data)
                    if success:
                        st.success("✅ 更新成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 更新失敗")
            
            with col2:
                if st.form_submit_button("❌ 取消", use_container_width=True):
                    st.rerun()
    
    elif mode == "delete":
        st.markdown("### 🗑️ 刪除庫存項目")
        
        if not current_items:
            st.info("📝 此機台目前沒有庫存項目")
            return
        
        # 選擇要刪除的項目
        item_options = {}
        for item in current_items:
            menu_item = item.get('menu_item', {})
            product_code = menu_item.get('product_code') or 'N/A'
            name = menu_item.get('name', 'Unknown')
            display_name = f"{name} ({product_code})"
            item_options[display_name] = item
        
        selected_item_name = st.selectbox(
            "選擇要刪除的庫存項目",
            options=list(item_options.keys()),
            key="delete_item_select"
        )
        selected_item = item_options[selected_item_name]
        
        # 顯示確認資訊
        menu_item = selected_item.get('menu_item', {})
        product_code = menu_item.get('product_code') or 'N/A'
        product_name = menu_item.get('name', 'Unknown')
        current_stock = selected_item.get('current_stock', 0)
        
        st.warning(f"⚠️ 確定要刪除以下庫存項目嗎？")
        st.write(f"**產品**: {product_name} ({product_code})")
        st.write(f"**當前庫存**: {current_stock}")
        st.write(f"**最低閾值**: {selected_item.get('min_threshold', 0)}")
        st.write(f"**最大容量**: {selected_item.get('max_capacity', 0)}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 確認刪除", type="primary", use_container_width=True, key="confirm_delete"):
                item_id = selected_item.get('id')
                success = st.session_state.api.delete_inventory_item(machine_id, item_id)
                if success:
                    st.success("✅ 刪除成功！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 刪除失敗")
        
        with col2:
            if st.button("❌ 取消", use_container_width=True, key="cancel_delete"):
                st.rerun()


@st.dialog("📦 庫存管理", width="large")
def show_simple_inventory_form(machine_id: int, mode: str = "create"):
    """簡單的庫存管理表單（用於單機台檢視頁面，使用 dialog）"""
    # 直接調用內聯版本
    show_simple_inventory_form_inline(machine_id, mode)


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
