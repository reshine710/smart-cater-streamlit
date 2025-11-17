import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import random
import json
from logger_config import mqtt_logger, ui_logger, system_logger
from typing import Optional, List, Dict
from utils import format_datetime_display

# 台灣時區 (UTC+8)
TAIWAN_TZ = timezone(timedelta(hours=8))

def get_taiwan_now() -> datetime:
    """獲取台灣時區的當前時間"""
    return datetime.now(TAIWAN_TZ)

def convert_to_taiwan_time(dt: datetime) -> datetime:
    """將 datetime 轉換為台灣時區"""
    if dt.tzinfo is None:
        # 如果沒有時區信息，假設為 UTC
        dt = dt.replace(tzinfo=timezone.utc)
    # 轉換為台灣時區
    return dt.astimezone(TAIWAN_TZ)

# Import MQTT client (assuming it exists in the project)
try:
    from mqtt_client.client import MQTTClient, initialize_mqtt_client
    MQTT_AVAILABLE = True
    system_logger.info("MQTT client imported successfully")
except ImportError as e:
    system_logger.error(f"MQTT client import failed: {e}")
    st.warning("MQTT client not available. Some features may be limited.")
    MQTTClient = None
    initialize_mqtt_client = None
    MQTT_AVAILABLE = False
except Exception as e:
    system_logger.error(f"MQTT client initialization error: {e}")
    st.error(f"MQTT client error: {e}")
    MQTTClient = None
    initialize_mqtt_client = None
    MQTT_AVAILABLE = False

def show_machine_overview(machines: List[Dict]):
    """顯示機台總覽卡片"""
    if not machines:
        st.info("📭 目前沒有機台數據")
        return
    
    # 過濾有效的機台數據
    valid_machines = []
    for machine in machines:
        if isinstance(machine, dict) and machine.get('id'):
            valid_machines.append(machine)
    
    if not valid_machines:
        st.warning("⚠️ 沒有有效的機台數據")
        return
    
    ui_logger.info(f"Displaying overview for {len(valid_machines)} machines")
    
    # 按狀態分組機台（三種狀態：上線、離線、故障）
    # 注意：maintenance 狀態會被歸類為 offline（隱藏維護狀態）
    status_groups = {
        'online': [],
        'offline': [],
        'fault': []         # 故障
    }
    
    for machine in valid_machines:
        status = machine.get('status', 'offline').lower()
        # 處理未知狀態，預設為離線
        if status == 'unknown':
            status = 'offline'
        
        # 將 maintenance 狀態歸類為 offline（隱藏維護狀態）
        if status == 'maintenance':
            status = 'offline'
        
        # 直接使用後端返回的狀態值（online, offline, fault）
        if status in status_groups:
            status_groups[status].append(machine)
        else:
            # 未知狀態歸類為離線
            status_groups['offline'].append(machine)
    
    # 顯示機台卡片
    for status, machines_in_status in status_groups.items():
        if not machines_in_status:
            continue
            
        # 狀態標題
        status_config = get_status_config(status)
        st.markdown(f"### {status_config['icon']} {status_config['title']} ({len(machines_in_status)}台)")
        
        # 創建響應式網格布局
        cols_per_row = 3
        for i in range(0, len(machines_in_status), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, machine in enumerate(machines_in_status[i:i+cols_per_row]):
                with cols[j]:
                    render_machine_card(machine, status_config)

def get_fault_description(fault_code: int) -> str:
    """取得錯誤碼描述"""
    fault_descriptions = {
        10: "失去心跳",
        11: "溫度感應器異常",
        12: "加熱系統故障",
        13: "門鎖系統異常",
        14: "支付系統錯誤",
        15: "庫存感應器故障",
        20: "網路連線中斷",
        21: "資料庫連線失敗",
        30: "硬體顯示器故障",
        31: "硬體按鍵系統故障",
        32: "其他硬體故障",
        40: "記憶體不足",
        41: "儲存空間不足",
        50: "電源供應故障",
        51: "備用電源故障"
    }
    return fault_descriptions.get(fault_code, f"未知錯誤 ({fault_code})")

def get_status_config(status: str) -> Dict:
    """獲取狀態配置（根據後端實際狀態：online, offline, maintenance, fault）"""
    # 處理未知狀態，預設為離線
    if status == 'unknown':
        status = 'offline'
    
    configs = {
        'online': {
            'icon': '🟢',
            'title': '上線',
            'color': 'success',
            'bg_color': '#d4edda',
            'border_color': '#28a745'
        },
        'offline': {
            'icon': '⚪',
            'title': '離線',
            'color': 'info',
            'bg_color': '#e2e3e5',
            'border_color': '#6c757d'
        },
        'maintenance': {
            'icon': '🟡',
            'title': '維護中',
            'color': 'warning',
            'bg_color': '#fff3cd',
            'border_color': '#ffc107'
        },
        'fault': {
            'icon': '🔴',
            'title': '故障',
            'color': 'error',
            'bg_color': '#f8d7da',
            'border_color': '#dc3545'
        }
    }
    return configs.get(status, configs['offline'])

def render_machine_card(machine: Dict, status_config: Dict):
    """渲染單個機台卡片"""
    machine_id = machine.get('id', 'N/A')
    machine_code = machine.get('machine_code', 'N/A')
    machine_name = machine.get('name', '未命名機台')
    status = machine.get('status', 'offline')
    # 處理未知狀態，預設為離線
    if status == 'unknown':
        status = 'offline'
    # 直接使用後端返回的狀態值（online, offline, maintenance, fault）
    location = machine.get('location', {})
    
    # 處理位置資訊
    if isinstance(location, dict):
        location_name = location.get('name', '未知位置')
    else:
        location_name = str(location) if location else '未知位置'
    
    # 獲取其他資訊
    ip_address = machine.get('ip_address', 'N/A')
    firmware_version = machine.get('firmware_version', 'N/A')
    
    # 計算最後心跳時間（優先使用 last_online，否則使用 last_heartbeat）
    heartbeat_status = get_heartbeat_status(machine)
    
    # 創建卡片容器
    with st.container():
        # 使用自定義CSS樣式
        card_style = f"""
        <div style="
            background-color: {status_config['bg_color']};
            border: 2px solid {status_config['border_color']};
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="text-align: center;">
                <h4 style="margin: 0; color: {status_config['border_color']};">
                    {status_config['icon']} {machine_name}
                </h4>
                <p style="margin: 5px 0; font-size: 14px; color: #666;">
                    {machine_code} (ID: {machine_id})
                </p>
            </div>
        </div>
        """
        
        st.markdown(card_style, unsafe_allow_html=True)
        
        # 詳細資訊
        with st.expander(f"📋 {machine_name} 詳細資訊", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**機台代碼**: {machine_code}")
                st.write(f"**位置**: {location_name}")
                st.write(f"**IP地址**: {ip_address}")
            
            with col2:
                # 顯示狀態
                st.write(f"**狀態**: {status_config['icon']} {status_config['title']}")
                
                # 顯示錯誤碼（如果有）
                current_fault_code = machine.get('current_fault_code')
                if current_fault_code is not None:
                    fault_desc = get_fault_description(current_fault_code)
                    st.write(f"**錯誤碼**: {current_fault_code} - {fault_desc}")
                
                st.write(f"**韌體版本**: {firmware_version}")
                st.write(f"**心跳狀態**: {heartbeat_status}")
            
            # 環境資訊（如果有）
            if 'temperature' in machine or 'humidity' in machine:
                st.markdown("**環境資訊**")
                env_col1, env_col2 = st.columns(2)
                with env_col1:
                    if 'temperature' in machine:
                        temp = machine['temperature']
                        st.write(f"🌡️ 溫度: {temp}°C" if temp is not None else "🌡️ 溫度: N/A")
                with env_col2:
                    if 'humidity' in machine:
                        humidity = machine['humidity']
                        st.write(f"💧 濕度: {humidity}%" if humidity is not None else "💧 濕度: N/A")
            
            # 操作按鈕（僅管理員）
            is_admin = st.session_state.get('is_admin', False)
            if is_admin:
                st.markdown("**操作**")
                op_col1, op_col2 = st.columns(2)
                
                with op_col1:
                    # 狀態切換 (使用 REST API)
                    current_status = machine.get('status', 'offline').lower()
                    # 處理未知狀態，預設為離線
                    if current_status == 'unknown':
                        current_status = 'offline'
                    
                    if current_status == 'fault':
                        # 故障狀態：可以恢復上線
                        if st.button("✅ 恢復上線", key=f"overview_resume_{machine_id}"):
                            try:
                                # 使用狀態事件 API，fault_code=1 表示上線
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台恢復正常"
                                )
                                if result:
                                    ui_logger.info(f"Machine {machine_code} status updated to online via status event API")
                                    st.success(f"✅ {machine_name} 已恢復上線")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ 更新失敗")
                            except Exception as e:
                                ui_logger.error(f"Failed to update machine status: {str(e)}")
                                st.error(f"❌ 操作失敗: {str(e)}")
                    elif current_status == 'maintenance':
                        # 維護狀態：歸類為離線，顯示恢復上線按鈕
                        if st.button("✅ 恢復上線", key=f"overview_maintenance_online_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台恢復正常"
                                )
                                if result:
                                    st.success(f"✅ {machine_name} 已恢復上線")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ 操作失敗: {str(e)}")
                    elif current_status == 'offline':
                        # 離線狀態：可以設為上線
                        if st.button("✅ 設為上線", key=f"overview_online_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台上線"
                                )
                                if result:
                                    ui_logger.info(f"Machine {machine_code} status updated to online via status event API")
                                    st.success(f"✅ {machine_name} 已設為上線")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ 更新失敗")
                            except Exception as e:
                                ui_logger.error(f"Failed to update machine status: {str(e)}")
                                st.error(f"❌ 操作失敗: {str(e)}")
                    else:
                        # 上線狀態：可以設為故障（維護狀態已隱藏）
                        if st.button("🔧 設為故障", key=f"overview_online_fault_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "fault", "機台故障"
                                )
                                if result:
                                    st.success(f"✅ {machine_name} 已設為故障")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ 操作失敗: {str(e)}")
                
                with op_col2:
                    # 刷新狀態 (使用 REST API)
                    if st.button("📊 刷新", key=f"overview_refresh_{machine_id}"):
                        try:
                            machine_detail = st.session_state.api.get_machine_detail(machine_id)
                            if machine_detail:
                                ui_logger.info(f"Refreshed machine {machine_id} status from API")
                                st.success(f"✅ {machine_name} 狀態已更新")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ 無法獲取機台資訊")
                        except Exception as e:
                            ui_logger.error(f"Failed to refresh machine status: {str(e)}")
                            st.error(f"❌ 刷新失敗: {str(e)}")
                
                # with op_col3:
                #     # 預留第三個操作按鈕位置
                #     pass
            
            
            # 编辑机台按钮（仅管理员）
            if is_admin:
                st.markdown("**機台管理**")
                if st.button("✏️ 編輯機台資訊", key=f"edit_machine_{machine_id}"):
                    show_edit_machine_dialog(machine)
            
            # 菜單查看按鈕（所有用戶）
            st.markdown("**菜單資訊**")
            if st.button("📋 查看當前菜單", key=f"view_menu_{machine_id}"):
                show_machine_menu_dialog(machine_id, machine_name)

def get_heartbeat_status(machine_or_time) -> str:
    """
    獲取心跳狀態
    
    Args:
        machine_or_time: 可以是機台字典物件或時間戳字串/物件
                        如果是字典，會優先使用 'last_online'，否則使用 'last_heartbeat'
                        如果是時間戳，直接使用該時間戳
    
    Returns:
        str: 心跳狀態字串
    """
    # 如果是字典物件，檢查機台狀態
    if isinstance(machine_or_time, dict):
        machine_status = machine_or_time.get('status', 'offline').lower()
        # 離線或維護狀態的機台，直接顯示無心跳
        if machine_status == 'offline' or machine_status == 'maintenance':
            return "🔴 無心跳"
        
        # 故障狀態的機台，也顯示無心跳
        if machine_status == 'fault':
            return "🔴 無心跳"
        
        # 只有上線狀態的機台才計算心跳時間
        last_time = machine_or_time.get('last_online') or machine_or_time.get('last_heartbeat')
    else:
        last_time = machine_or_time
    
    # 如果沒有時間戳數據，顯示為無心跳
    if not last_time or last_time == 'N/A' or last_time == 'Unknown':
        return "🔴 無心跳"
    
    try:
        # 嘗試解析時間戳
        if isinstance(last_time, str):
            # 處理 ISO8601 格式的時間字串
            heartbeat_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
        elif isinstance(last_time, datetime):
            heartbeat_time = last_time
        else:
            # 如果是其他類型，嘗試轉換
            ui_logger.warning(f"Unexpected heartbeat time type: {type(last_time)}")
            return "🔴 無心跳"  # 統一顯示為無心跳
        
        # 將心跳時間轉換為台灣時區
        heartbeat_time = convert_to_taiwan_time(heartbeat_time)
        
        # 計算時間差（使用台灣時區的當前時間）
        now = get_taiwan_now()
        time_diff = now - heartbeat_time
        
        if time_diff.total_seconds() < 60:  # 1分鐘內
            return "🟢 正常"
        elif time_diff.total_seconds() < 300:  # 5分鐘內
            return "🟡 延遲"
        else:
            # 超過5分鐘統一顯示為無心跳（而非超時）
            return "🔴 無心跳"
    except Exception as e:
        ui_logger.warning(f"Error parsing heartbeat time: {e}")
        return "🔴 無心跳"  # 解析錯誤也統一顯示為無心跳

def machine_status_page():
    """機台狀態監控頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing machine status page")
    st.title("🖥️ 機台狀態監控")
    
    # 添加全部機台刷新按鈕
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        pass  # 保留標題空間
    with col_refresh:
        if st.button("🔄 刷新全部機台", key="refresh_all_machines", type="primary", width='stretch'):
            # 清除可能的快取，強制重新獲取資料
            if 'machines_cache' in st.session_state:
                del st.session_state.machines_cache
            ui_logger.info("User triggered refresh all machines")
            st.success("✅ 正在刷新機台資料...")
            time.sleep(0.5)  # 短暫延遲讓用戶看到提示
            st.rerun()
    
    st.markdown("---")
    
    ui_logger.debug("Machine status page accessed")
    
    # ============================================================================
    # MQTT 相關程式碼已移至檔案末尾的 _setup_mqtt_for_future_use() 函數
    # 目前使用 REST API 進行機台狀態管理
    # 如需啟用 MQTT，請取消註解下方程式碼並註解掉 REST API 相關部分
    # ============================================================================
    # _setup_mqtt_connection()  # 未來可用的 MQTT 設置函數
    
    # Get machine data from API
    machines = st.session_state.api.get_machines()
    system_logger.debug(f"Retrieved machines from API: {type(machines)}")
    system_logger.debug(f"Machines data: {machines}")
    
    # 檢查數據格式
    if machines is not None and isinstance(machines, list) and len(machines) > 0:
        # 檢查第一個元素的類型
        try:
            first_item = machines[0]
            system_logger.debug(f"First machine item type: {type(first_item)}, content: {first_item}")
            
            # 如果不是字典，記錄錯誤
            if not isinstance(first_item, dict):
                system_logger.warning(f"API returned unexpected data format: {type(first_item)}")
                st.error("⚠️ API 數據格式異常")
                machines = []
        except (IndexError, TypeError) as e:
            system_logger.error(f"Error accessing machines data: {e}")
            st.error("⚠️ API 數據存取錯誤")
            machines = []
    else:
        # 如果沒有數據或數據格式不正確
        system_logger.warning(f"Invalid machines data: {type(machines)}, content: {machines}")
        if not machines:
            st.info("ℹ️ 目前沒有機台數據")
        machines = machines or []
        
    system_logger.debug(f"Final machines count: {len(machines)}")
    
    # 過濾有效的機台數據（與 show_machine_overview 使用相同的過濾邏輯）
    valid_machines = []
    for machine in machines:
        if isinstance(machine, dict) and machine.get('id'):
            valid_machines.append(machine)
    
    system_logger.debug(f"Valid machines count: {len(valid_machines)}")
    
    # 狀態總覽（三種狀態：上線、離線、故障）
    col1, col2, col3 = st.columns(3)
    
    status_counts = {
        'online': 0,
        'offline': 0,
        'fault': 0
    }
    
    for machine in valid_machines:
        # 獲取狀態，如果沒有狀態欄位，預設為 'offline'
        status = machine.get('status', 'offline')
        if not status:
            status = 'offline'
        
        status = status.lower()
        
        # 處理未知狀態，預設為離線
        if status == 'unknown':
            status = 'offline'
        
        # 將 maintenance 狀態歸類為 offline（隱藏維護狀態）
        if status == 'maintenance':
            status = 'offline'
        
        # 直接使用後端返回的狀態值（online, offline, fault）
        if status not in status_counts:
            system_logger.warning(f"Unknown machine status: {status}, defaulting to offline. Machine ID: {machine.get('id')}")
            status = 'offline'
        
        status_counts[status] = status_counts.get(status, 0) + 1
    
    with col1:
        st.metric("🟢 上線", status_counts.get('online', 0))
    with col2:
        st.metric("⚪ 離線", status_counts.get('offline', 0))
    with col3:
        st.metric("🔴 故障", status_counts.get('fault', 0))
    
    st.markdown("---")
    
    # 機台總覽卡片（使用已過濾的有效機台）
    st.subheader("📊 機台總覽")
    show_machine_overview(valid_machines)
    
    st.markdown("---")
    
    # 管理員功能：新增機台
    is_admin = st.session_state.get('is_admin', False)
    if is_admin:
        st.subheader("➕ 新增機台")
        
        with st.expander("📝 創建新機台", expanded=False):
            with st.form("create_machine_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    machine_code = st.text_input(
                        "機台代碼 *", 
                        placeholder="例如: VM001",
                        help="機台的唯一識別代碼"
                    )
                    machine_name = st.text_input(
                        "機台名稱 *", 
                        placeholder="例如: 台北101店",
                        help="機台的顯示名稱"
                    )
                    
                    # 獲取可用地點
                    try:
                        locations = st.session_state.api.get_locations()
                        # 確保 locations 是列表且包含字典
                        if isinstance(locations, list) and locations:
                            location_options = []
                            location_mapping = {}  # 建立名稱到ID的映射
                            for loc in locations:
                                if isinstance(loc, dict):
                                    location_name = loc.get('name', 'Unknown')
                                    location_options.append(location_name)
                                    location_mapping[location_name] = loc.get('id')
                                else:
                                    system_logger.warning(f"Invalid location data format: {type(loc)}")
                        else:
                            location_options = []
                            location_mapping = {}
                            system_logger.warning(f"Invalid locations data: {type(locations)}")
                    except Exception as e:
                        system_logger.error(f"Error getting locations: {str(e)}")
                        location_options = []
                        location_mapping = {}
                    
                    if location_options:
                        selected_location = st.selectbox(
                            "機台位置 *",
                            options=location_options,
                            help="選擇機台的安裝地點"
                        )
                        location_id = location_mapping.get(selected_location)
                    else:
                        selected_location = st.text_input(
                            "機台位置 *", 
                            placeholder="例如: 台北市信義區信義路五段7號",
                            help="機台的實際安裝位置"
                        )
                        location_id = None
                        st.info("💡 提示：可以在地點管理中預先建立地點選項")
                    
                    ip_address = st.text_input(
                        "IP 地址", 
                        placeholder="例如: 192.168.1.100",
                        help="機台的網路IP地址（可選）"
                    )
                
                with col2:
                    status = st.selectbox(
                        "初始狀態", 
                        options=["online", "offline", "fault"],
                        format_func=lambda x: {
                            "online": "🟢 上線",
                            "offline": "⚪ 離線",
                            "fault": "🔴 故障"
                        }[x]
                    )
                    # 直接使用後端狀態值，無需映射
                    api_status = status
                    firmware_version = st.text_input(
                        "韌體版本", 
                        placeholder="例如: 1.0.0",
                        help="機台韌體版本（可選）"
                    )
                    hardware_version = st.text_input(
                        "硬體版本", 
                        placeholder="例如: A1",
                        help="機台硬體版本（可選）"
                    )
                    max_capacity = st.number_input(
                        "最大容量", 
                        min_value=1, 
                        max_value=100, 
                        value=30,
                        help="機台最大商品容量"
                    )
                
                submitted = st.form_submit_button("🚀 創建機台", type="primary")
                
                if submitted:
                    # 驗證必填欄位
                    if not machine_code or not machine_name or not selected_location:
                        st.error("❌ 請填寫所有必填欄位（標記 * 的欄位）")
                    else:
                        # 準備機台資料（按照 API 規格）
                        # 直接使用後端狀態值，無需映射
                        machine_data = {
                            "machine_code": machine_code.strip(),
                            "name": machine_name.strip(),
                            "location": selected_location.strip(),  # 直接使用地點名稱
                            "status": status,  # 直接使用選擇的狀態值（online, offline, maintenance, fault）
                            "max_capacity": max_capacity,
                            "temperature": None,  # 預設值，後續可由機台更新
                            "humidity": None      # 預設值，後續可由機台更新
                        }
                        
                        # 添加可選欄位
                        if ip_address.strip():
                            machine_data["ip_address"] = ip_address.strip()
                        if firmware_version.strip():
                            machine_data["firmware_version"] = firmware_version.strip()
                        if hardware_version.strip():
                            machine_data["hardware_version"] = hardware_version.strip()
                        
                        # 呼叫 API 創建機台
                        ui_logger.debug(f"Sending machine data: {machine_data}")
                        try:
                            created_machine = st.session_state.api.create_machine(machine_data)
                            if created_machine:
                                ui_logger.info(f"Admin {st.session_state.get('username')} created machine {machine_code}")
                                # 刷新頁面以顯示新機台
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ 創建機台時發生錯誤: {str(e)}")
                            ui_logger.error(f"Error creating machine: {str(e)}")
        
        st.markdown("---")
    
    # 機台詳細狀態（使用已過濾的有效機台）
    st.subheader("機台詳細狀態")
    
    for machine in valid_machines:
        # 安全地獲取機台資訊
        if not isinstance(machine, dict):
            system_logger.warning(f"Skipping invalid machine data: {type(machine)}")
            continue
            
        machine_name = machine.get('name', 'Unknown Machine')
        machine_code = machine.get('machine_code', 'Unknown')
        machine_id = machine.get('id', 'Unknown')
        
        with st.expander(f"📍 {machine_name} ({machine_code})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                machine_status = machine.get('status', 'offline').lower()
                # 處理未知狀態，預設為離線
                if machine_status == 'unknown':
                    machine_status = 'offline'
                
                status_config = get_status_config(machine_status)
                # 顯示狀態
                st.write(f"**狀態**: {status_config['icon']} {status_config['title']}")
                
                # 顯示錯誤碼（如果有）
                current_fault_code = machine.get('current_fault_code')
                if current_fault_code is not None:
                    fault_desc = get_fault_description(current_fault_code)
                    st.write(f"**錯誤碼**: {current_fault_code} - {fault_desc}")
                # 處理位置顯示格式
                location_info = machine.get('location', 'Unknown Location')
                if isinstance(location_info, dict):
                    location_name = location_info.get('name', 'Unknown')
                    location_env = '🏢 室內' if location_info.get('is_indoor', False) else '🌳 室外'
                    st.write(f"**位置**: {location_name}")
                    st.write(f"**環境**: {location_env}")
                else:
                    st.write(f"**位置**: {location_info}")
                    st.write(f"**環境**: 未知")
            
            with col2:
                temperature = machine.get('temperature')
                if temperature:
                    st.write(f"**溫度**: {temperature}°C")
                else:
                    st.write("**溫度**: N/A")
                # 顯示最後心跳時間（優先使用 last_online，否則使用 last_heartbeat）
                last_online = machine.get('last_online')
                last_heartbeat = machine.get('last_heartbeat')
                last_time_raw = last_online or last_heartbeat
                
                if last_time_raw and last_time_raw != 'Unknown':
                    try:
                        # 解析時間並轉換為台灣時區
                        if isinstance(last_time_raw, str):
                            last_time = datetime.fromisoformat(last_time_raw.replace('Z', '+00:00'))
                        elif isinstance(last_time_raw, datetime):
                            last_time = last_time_raw
                        else:
                            last_time = None
                        
                        if last_time:
                            # 轉換為台灣時區並格式化顯示
                            last_time_tw = convert_to_taiwan_time(last_time)
                            from utils import format_datetime_display
                            last_time_display = format_datetime_display(last_time_tw)
                        else:
                            last_time_display = str(last_time_raw)
                    except Exception as e:
                        ui_logger.warning(f"Error formatting heartbeat time: {e}")
                        last_time_display = str(last_time_raw)
                else:
                    last_time_display = 'Unknown'
                
                st.write(f"**最後心跳**: {last_time_display}")
            
            with col3:
                # 機台操作按鈕 (使用 REST API)
                is_admin = st.session_state.get('is_admin', False)
                if is_admin:
                    # 狀態切換
                    current_status = machine.get('status', 'offline').lower()
                    # 處理未知狀態，預設為離線
                    if current_status == 'unknown':
                        current_status = 'offline'
                    
                    if current_status == 'fault':
                        # 故障狀態：可以恢復上線
                        if st.button(f"✅ 恢復上線 {machine_id}", 
                                   key=f"detail_resume_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台恢復正常"
                                )
                                if result:
                                    ui_logger.info(f"Machine {machine_code} status updated to online via status event API")
                                    st.success(f"✅ 機台 {machine_name} 已恢復上線")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ 更新機台狀態失敗")
                            except Exception as e:
                                ui_logger.error(f"Failed to update machine status via API: {str(e)}")
                                st.error(f"❌ 更新狀態失敗: {str(e)}")
                    elif current_status == 'maintenance':
                        # 維護狀態：歸類為離線，顯示恢復上線按鈕
                        if st.button(f"✅ 恢復上線 {machine_id}", 
                                   key=f"detail_maintenance_online_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台恢復正常"
                                )
                                if result:
                                    st.success(f"✅ 機台 {machine_name} 已恢復上線")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ 更新狀態失敗: {str(e)}")
                    elif current_status == 'offline':
                        # 離線狀態：可以設為上線
                        if st.button(f"✅ 設為上線 {machine_id}", 
                                   key=f"detail_online_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "online", "機台上線"
                                )
                                if result:
                                    ui_logger.info(f"Machine {machine_code} status updated to online via status event API")
                                    st.success(f"✅ 機台 {machine_name} 已設為上線")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ 更新機台狀態失敗")
                            except Exception as e:
                                ui_logger.error(f"Failed to update machine status via API: {str(e)}")
                                st.error(f"❌ 更新狀態失敗: {str(e)}")
                    else:
                        # 上線狀態：可以設為故障（維護狀態已隱藏）
                        if st.button(f"🔧 設為故障 {machine_id}", 
                                   key=f"detail_online_fault_{machine_id}"):
                            try:
                                result = st.session_state.api.update_machine_status_by_code(
                                    machine_code, "fault", "機台故障"
                                )
                                if result:
                                    st.success(f"✅ 機台 {machine_name} 已設為故障")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ 更新狀態失敗: {str(e)}")
                    
                    # 更新狀態（從後端獲取最新狀態）
                    if st.button(f"📊 刷新狀態 {machine_id}", 
                               key=f"detail_refresh_{machine_id}"):
                        try:
                            # 重新獲取機台資料
                            machine_detail = st.session_state.api.get_machine_detail(machine_id)
                            if machine_detail:
                                ui_logger.info(f"Refreshed machine {machine_id} status from API")
                                st.success(f"✅ 已更新 {machine_name} 的狀態資訊")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ 無法獲取機台資訊")
                        except Exception as e:
                            ui_logger.error(f"Failed to refresh machine status: {str(e)}")
                            st.error(f"❌ 刷新狀態失敗: {str(e)}")
                else:
                    st.caption("🔒 機台操作功能僅限管理員使用")
                
                # 刪除機台功能 (僅管理員可用)
                if is_admin:
                    st.markdown("---")
                    st.write("**⚠️ 危險操作區域**")
                    
                    # 使用 st.dialog 確認對話框
                    if st.button(f"🗑️ 刪除機台", 
                               key=f"delete_{machine_id}",
                               type="secondary",
                               help="此操作無法復原，請謹慎使用"):
                        show_delete_machine_confirmation_dialog(machine)
                else:
                    # 非管理員用戶顯示提示
                    st.caption("🔒 刪除機台功能僅限管理員使用")
                
    # ============================================================================
    # MQTT 即時監控區塊已隱藏，相關程式碼已移至檔案末尾
    # 如需啟用 MQTT 即時監控，請取消註解下方程式碼
    # ============================================================================
    # _show_mqtt_realtime_monitoring()  # 未來可用的 MQTT 即時監控函數


# ============================================================================
# MQTT 相關函數已移至檔案末尾的 "MQTT 功能保留區塊"
# 目前使用 REST API 進行機台狀態管理，MQTT 相關函數已註解保留供未來使用
# ============================================================================


def show_delete_machine_confirmation_dialog(machine: dict):
    """顯示刪除機台確認對話框"""
    
    machine_id = machine.get('id', 'Unknown')
    machine_name = machine.get('name', 'Unknown')
    machine_code = machine.get('machine_code', 'Unknown')
    
    @st.dialog(f"🗑️ 刪除確認 - {machine_name} ({machine_code})")
    def delete_dialog():
        st.error("⚠️ **危險操作警告**")
        st.write(f"您即將刪除機台：**{machine_name}** ({machine_code})")
        
        # 顯示機台詳細資訊
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**機台ID**: {machine_id}")
            st.write(f"**狀態**: {machine.get('status', 'Unknown')}")
        with col2:
            location_info = machine.get('location', 'Unknown Location')
            if isinstance(location_info, dict):
                location_name = location_info.get('name', 'Unknown')
                st.write(f"**位置**: {location_name}")
            else:
                st.write(f"**位置**: {location_info}")
            st.write(f"**IP地址**: {machine.get('ip_address', 'N/A')}")
        
        st.markdown("---")
        st.warning("**此操作將永久刪除機台及其相關數據，無法復原！**")
        st.write("請確認您真的要執行此操作。")
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("✅ 確認刪除", 
                        type="primary", 
                        width="stretch"):
                try:
                    success = st.session_state.api.delete_machine(machine_id)
                    if success:
                        st.success(f"✅ 機台 {machine_name} 已成功刪除")
                        ui_logger.info(f"Admin {st.session_state.get('username')} deleted machine {machine_id} ({machine_code})")
                        # 刷新頁面以更新機台列表
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ 刪除機台 {machine_name} 失敗")
                except Exception as e:
                    st.error(f"❌ 刪除機台時發生錯誤: {str(e)}")
                    ui_logger.error(f"Error deleting machine {machine_id}: {str(e)}")
        
        with col_cancel:
            if st.button("❌ 取消", 
                        width="stretch"):
                st.rerun()
    
    delete_dialog()

# 定義對話框函數
@st.dialog("🍽️ 機台菜單")
def show_machine_menu_dialog_content(machine_id: int, machine_name: str):
    """對話框內容函數"""
    try:
        ui_logger.info(f"Showing current menu dialog for machine {machine_id} ({machine_name})")
        
        # 調用API獲取機台當前菜單
        if hasattr(st.session_state, 'api') and st.session_state.api:
            menu_data = st.session_state.api.get_machine_current_menu_items(machine_id)
            
            if menu_data and menu_data.get('success'):
                data = menu_data.get('data', {})
                current_menu_items = data.get('current_menu_items', [])
                total_items = data.get('total_items', 0)
                
                # 顯示菜單標題和基本資訊
                st.markdown(f"### 🍽️ {machine_name} 當前菜單")
                st.markdown(f"**總項目數**: {total_items}")
                
                if current_menu_items:
                    # 創建菜單項目表格
                    menu_df = pd.DataFrame(current_menu_items)
                    
                    # 重新排列欄位順序，讓重要資訊在前面
                    desired_columns = ['display_order', 'menu_item_name', 'price', 'heating_method', 'is_ai_recommended']
                    existing_columns = [col for col in desired_columns if col in menu_df.columns]
                    other_columns = [col for col in menu_df.columns if col not in desired_columns]
                    final_columns = existing_columns + other_columns
                    
                    if final_columns:
                        menu_df = menu_df[final_columns]
                    
                    # 美化顯示
                    menu_df_display = menu_df.copy()
                    
                    # 格式化價格
                    if 'price' in menu_df_display.columns:
                        menu_df_display['price'] = menu_df_display['price'].apply(lambda x: f"NT$ {x:.0f}" if pd.notna(x) else "N/A")
                    
                    # 格式化AI推薦狀態
                    if 'is_ai_recommended' in menu_df_display.columns:
                        menu_df_display['is_ai_recommended'] = menu_df_display['is_ai_recommended'].apply(
                            lambda x: "🤖 AI推薦" if x else "📋 手動設定"
                        )
                    
                    # 格式化加熱方式
                    if 'heating_method' in menu_df_display.columns:
                        heating_icons = {
                            'microwave': '🔥 微波',
                            'steam': '💨 蒸煮',
                            'fry': '🍳 油炸',
                            'bake': '🔥 烘烤'
                        }
                        menu_df_display['heating_method'] = menu_df_display['heating_method'].apply(
                            lambda x: heating_icons.get(x, f"🔥 {x}")
                        )
                    
                    # 重新命名欄位為中文
                    column_mapping = {
                        'display_order': '顯示順序',
                        'menu_item_name': '餐點名稱',
                        'price': '價格',
                        'heating_method': '加熱方式',
                        'is_ai_recommended': '推薦來源',
                        'description': '描述',
                        'image_url': '圖片',
                        'menu_item_id': '菜單ID'
                    }
                    
                    menu_df_display = menu_df_display.rename(columns=column_mapping)
                    
                    # 顯示表格
                    st.dataframe(menu_df_display, width="stretch", hide_index=True)
                    
                    # 顯示統計資訊
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        ai_recommended_count = len([item for item in current_menu_items if item.get('is_ai_recommended', False)])
                        st.metric("🤖 AI推薦項目", ai_recommended_count)
                    
                    with col2:
                        manual_count = total_items - ai_recommended_count
                        st.metric("📋 手動設定項目", manual_count)
                    
                    with col3:
                        if current_menu_items:
                            avg_price = sum(item.get('price', 0) for item in current_menu_items) / len(current_menu_items)
                            st.metric("💰 平均價格", f"NT$ {avg_price:.0f}")
                        else:
                            st.metric("💰 平均價格", "N/A")
                    
                    # 顯示詳細資訊
                    st.markdown("### 📋 菜單項目詳細資訊")
                    for i, item in enumerate(current_menu_items, 1):
                        with st.expander(f"{i}. {item.get('menu_item_name', 'Unknown')}", expanded=False):
                            col_detail1, col_detail2 = st.columns(2)
                            
                            with col_detail1:
                                st.write(f"**菜單ID**: {item.get('menu_item_id', 'N/A')}")
                                st.write(f"**顯示順序**: {item.get('display_order', 'N/A')}")
                                st.write(f"**價格**: NT$ {item.get('price', 0):.0f}")
                                st.write(f"**加熱方式**: {item.get('heating_method', 'N/A')}")
                            
                            with col_detail2:
                                st.write(f"**推薦來源**: {'🤖 AI推薦' if item.get('is_ai_recommended', False) else '📋 手動設定'}")
                                if item.get('description'):
                                    st.write(f"**描述**: {item['description']}")
                                if item.get('image_url'):
                                    st.write(f"**圖片**: {item['image_url']}")
                
                else:
                    st.info("📭 此機台目前沒有菜單項目")
                    
            else:
                st.error("❌ 獲取機台菜單失敗")
                if menu_data:
                    st.error(f"錯誤訊息: {menu_data.get('message', '未知錯誤')}")
        else:
            st.error("❌ API 客戶端不可用")
            
    except Exception as e:
        ui_logger.error(f"Error showing machine menu dialog: {str(e)}")
        st.error(f"❌ 顯示機台菜單時發生錯誤: {str(e)}")

def show_machine_menu_dialog(machine_id: int, machine_name: str):
    """顯示機台菜單對話框"""
    # 調用對話框函數
    show_machine_menu_dialog_content(machine_id, machine_name)

# ============================================================================
# MQTT 命令對話框函數已移至檔案末尾的 "MQTT 功能保留區塊"
# 如需使用 MQTT 功能，請取消註解相關函數
# ============================================================================

@st.dialog("✏️ 編輯機台資訊")
def show_edit_machine_dialog_content(machine: Dict):
    """編輯機台資訊的對話框內容"""
    machine_id = machine.get('id')
    
    st.markdown(f"### 編輯機台: {machine.get('name', '未命名')}")
    st.markdown(f"**機台ID**: {machine_id}")
    st.markdown(f"**機台代碼**: {machine.get('machine_code', 'N/A')}")
    st.markdown("---")
    
    with st.form(key=f"edit_machine_form_{machine_id}"):
        # 機台基本資訊
        st.markdown("**📋 基本資訊**")
        col1, col2 = st.columns(2)
        
        with col1:
            machine_name = st.text_input(
                "機台名稱 *",
                value=machine.get('name', ''),
                key=f"edit_name_{machine_id}",
                help="機台的顯示名稱"
            )
            
            machine_code = st.text_input(
                "機台代碼 *",
                value=machine.get('machine_code', ''),
                key=f"edit_code_{machine_id}",
                help="機台的唯一識別碼",
                disabled=True  # 機台代碼通常不允許修改
            )
        
        with col2:
            ip_address = st.text_input(
                "IP地址",
                value=machine.get('ip_address', ''),
                key=f"edit_ip_{machine_id}",
                help="機台的IP地址"
            )
            
            firmware_version = st.text_input(
                "韌體版本",
                value=machine.get('firmware_version', ''),
                key=f"edit_firmware_{machine_id}",
                help="機台的韌體版本號"
            )
        
        # 機台狀態
        st.markdown("**🔧 狀態設定**")
        # 處理當前狀態，直接使用後端狀態值
        current_status = machine.get('status', 'offline').lower()
        if current_status == 'unknown':
            current_status = 'offline'
        
        # 處理 maintenance 狀態：在編輯時歸類為 offline
        if current_status == 'maintenance':
            current_status = 'offline'
        
        status_options = ["online", "offline", "fault"]
        status_index = status_options.index(current_status) if current_status in status_options else 0
        
        status = st.selectbox(
            "機台狀態",
            options=status_options,
            index=status_index,
            format_func=lambda x: {
                "online": "🟢 上線",
                "offline": "⚪ 離線",
                "fault": "🔴 故障"
            }.get(x, x),
            key=f"edit_status_{machine_id}"
        )
        
        # 直接使用後端狀態值，無需映射
        api_status = status
        
        # 位置資訊
        st.markdown("**📍 位置資訊**")
        
        # 初始化位置ID變量
        location_id = None
        selected_location_name = None
        
        # 獲取所有位置選項
        try:
            if hasattr(st.session_state, 'api') and st.session_state.api:
                locations_data = st.session_state.api.get_locations()
                if locations_data and len(locations_data) > 0:
                    location_options = []
                    location_map = {}
                    
                    for loc in locations_data:
                        loc_id = loc.get('id')
                        loc_name = loc.get('name', f'Location {loc_id}')
                        location_options.append(loc_name)
                        location_map[loc_name] = loc_id
                    
                    # 當前位置
                    current_location = machine.get('location', {})
                    if isinstance(current_location, dict):
                        current_location_name = current_location.get('name', '')
                    else:
                        current_location_name = ''
                    
                    # 找到當前位置的索引
                    if current_location_name and current_location_name in location_options:
                        location_index = location_options.index(current_location_name)
                    else:
                        location_index = 0
                    
                    selected_location_name = st.selectbox(
                        "機台位置",
                        options=location_options,
                        index=location_index,
                        key=f"edit_location_{machine_id}",
                        help="選擇機台所在的位置"
                    )
                    
                    # 從選擇的位置名稱獲取位置ID
                    location_id = location_map.get(selected_location_name)
                    
                    # 記錄選擇的位置信息
                    ui_logger.debug(f"Selected location: {selected_location_name} (ID: {location_id})")
                else:
                    st.warning("⚠️ 無法獲取位置列表，請確認後端API正常運作")
                    ui_logger.warning("No locations data available")
            else:
                st.warning("⚠️ API不可用，無法載入位置列表")
                ui_logger.warning("API client not available")
        except Exception as e:
            ui_logger.error(f"Error fetching locations: {str(e)}")
            st.error(f"❌ 獲取位置列表失敗: {str(e)}")
        
        # 其他資訊
        st.markdown("**📝 其他資訊**")
        description = st.text_area(
            "描述",
            value=machine.get('description', ''),
            key=f"edit_description_{machine_id}",
            help="機台的詳細描述（選填）",
            height=100
        )
        
        st.markdown("---")
        st.markdown("*標示 `*` 為必填欄位")
        
        # 提交按鈕
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button("💾 儲存變更", type="primary", width='stretch')
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", width='stretch')
        
        if cancelled:
            st.rerun()
        
        if submitted:
            # 驗證必填欄位
            if not machine_name:
                st.error("❌ 請填寫機台名稱")
                return
            
            # 準備更新數據
            # 映射到 API 使用的狀態值（已在前面定義 api_status）
            update_data = {
                "name": machine_name,
                "ip_address": ip_address if ip_address else None,
                "firmware_version": firmware_version if firmware_version else None,
                "status": api_status,  # 使用映射後的 API 狀態值
                "description": description if description else None
            }
            
            # 如果有位置ID，添加到更新數據中
            if location_id is not None:
                update_data["location_id"] = location_id
                ui_logger.info(f"📍 將更新位置ID為: {location_id} (選擇的位置: {selected_location_name})")
            else:
                ui_logger.warning("⚠️ 未選擇位置或位置ID為None，不更新位置資訊")
            
            # 記錄API調用
            ui_logger.info(f"🔄 開始更新機台 {machine_id} 資訊")
            ui_logger.info(f"📋 更新數據: {update_data}")
            ui_logger.info(f"📋 位置資訊: location_id={location_id}, selected_location={selected_location_name}")
            
            # 調用API更新機台資訊
            try:
                if hasattr(st.session_state, 'api') and st.session_state.api:
                    success = st.session_state.api.update_machine(machine_id, update_data)
                    
                    if success:
                        st.success("✅ 機台資訊已成功更新！")
                        ui_logger.info(f"✅ 成功更新機台 {machine_id} 資訊")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 更新機台資訊失敗")
                        ui_logger.error(f"❌ 更新機台 {machine_id} 資訊失敗")
                else:
                    st.error("❌ API 客戶端不可用")
                    ui_logger.error("❌ API 客戶端不可用")
            except Exception as e:
                st.error(f"❌ 更新機台資訊時發生錯誤: {str(e)}")
                ui_logger.error(f"❌ 更新機台資訊時發生錯誤: {str(e)}")

def show_edit_machine_dialog(machine: Dict):
    """顯示編輯機台資訊對話框"""
    show_edit_machine_dialog_content(machine)


# ============================================================================
# MQTT 功能保留區塊 - 未來可能使用的 MQTT 相關程式碼
# ============================================================================
# 以下程式碼已註解保留，供未來需要時使用
# 目前機台狀態管理已改用 REST API 進行
# 如需啟用 MQTT 功能，請取消註解以下函數並在主函數中調用
# ============================================================================

"""
def _setup_mqtt_connection():
    \"\"\"設置 MQTT 連接（未來可用）\"\"\"
    # Initialize MQTT client if available
    if MQTT_AVAILABLE and 'mqtt_client' not in st.session_state:
        try:
            st.session_state.mqtt_client = MQTTClient()
            mqtt_logger.info("MQTT client initialized in Streamlit session")
        except Exception as e:
            st.error(f"Failed to initialize MQTT client: {e}")
            mqtt_logger.error(f"Failed to initialize MQTT client: {e}")
            st.session_state.mqtt_client = None
    elif not MQTT_AVAILABLE:
        st.session_state.mqtt_client = None
    
    # MQTT connection status and controls
    if MQTT_AVAILABLE and 'mqtt_client' in st.session_state and st.session_state.mqtt_client:
        mqtt_client = st.session_state.mqtt_client
        
        # Get detailed connection status
        status = mqtt_client.get_connection_status()
        mqtt_connected = status.get('connected', False)
        
        # Display connection status
        status_icon = "🟢" if mqtt_connected else "🔴"
        status_text = "Connected" if mqtt_connected else "Disconnected"
        st.sidebar.write(f"**MQTT Status**: {status_icon} {status_text}")
        st.sidebar.write(f"**Broker**: {status.get('broker', 'Unknown')}:{status.get('port', 'Unknown')}")
        
        # Connection control buttons
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🔌 Connect" if not mqtt_connected else "🔌 Connected", 
                        disabled=mqtt_connected, 
                        key="mqtt_connect"):
                try:
                    import asyncio
                    asyncio.run(mqtt_client.connect())
                    st.success("MQTT connected successfully!")
                    mqtt_logger.info("MQTT connection established from Streamlit")
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")
                    mqtt_logger.error(f"MQTT connection failed: {e}")
        
        with col2:
            if st.button("🔌 Disconnect" if mqtt_connected else "🔌 Disconnected", 
                        disabled=not mqtt_connected,
                        key="mqtt_disconnect"):
                try:
                    import asyncio
                    asyncio.run(mqtt_client.disconnect())
                    st.info("MQTT disconnected")
                    mqtt_logger.info("MQTT disconnected from Streamlit")
                    st.rerun()
                except Exception as e:
                    st.error(f"Disconnection failed: {e}")
                    mqtt_logger.error(f"MQTT disconnection failed: {e}")
        
        # Subscribe to machine topics if connected
        if mqtt_connected:
            # Subscribe to all machine topics for real-time updates
            machine_topics = [
                "machine/+/heartbeat",
                "machine/+/alert", 
                "machine/+/inventory/update",
                "machine/+/order/status"
            ]
            
            for topic in machine_topics:
                if topic not in mqtt_client.get_subscribed_topics():
                    try:
                        mqtt_client.subscribe(topic, lambda t, p: mqtt_logger.debug(f"Received: {t}"))
                        mqtt_logger.info(f"Subscribed to {topic}")
                    except Exception as e:
                        mqtt_logger.error(f"Failed to subscribe to {topic}: {e}")
    else:
        if MQTT_AVAILABLE:
            st.sidebar.write("**MQTT Status**: 🟡 Initializing...")
        else:
            st.sidebar.write("**MQTT Status**: ❌ Not Available")


def _show_mqtt_realtime_monitoring():
    \"\"\"顯示 MQTT 即時監控區塊（未來可用）\"\"\"
    st.markdown("---")
    st.subheader("📡 即時監控")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**MQTT 主題訂閱狀態**")
        mqtt_client = st.session_state.get('mqtt_client')
        if mqtt_client and mqtt_client.get_connection_status().get('connected', False):
            subscribed_topics = mqtt_client.get_subscribed_topics()
            if subscribed_topics:
                for topic in subscribed_topics:
                    st.write(f"✅ {topic}")
            else:
                st.write("📡 已連接，但未訂閱任何主題")
            
            # 顯示建議的機台主題
            st.write("**建議訂閱主題**")
            suggested_topics = [
                "machine/+/heartbeat",
                "machine/+/alert", 
                "machine/+/inventory/update",
                "machine/+/order/status"
            ]
            for topic in suggested_topics:
                if topic not in subscribed_topics:
                    st.write(f"⚪ {topic}")
        else:
            st.write("🔴 MQTT 客戶端未連接")
    
    with col2:
        st.write("**即時 MQTT 訊息**")
        if 'mqtt_messages' not in st.session_state:
            st.session_state.mqtt_messages = []
        
        # 顯示訊息統計
        total_messages = len(st.session_state.mqtt_messages)
        st.caption(f"總計收到 {total_messages} 條訊息")
        
        # 顯示最近訊息 (最多10條)
        recent_messages = st.session_state.mqtt_messages[-10:] if st.session_state.mqtt_messages else []
        
        if recent_messages:
            # 創建一個容器來顯示訊息，最新的在上面
            message_container = st.container()
            with message_container:
                for msg in reversed(recent_messages):
                    # 根據主題類型設置不同的圖標
                    topic_icons = {
                        'heartbeat': '💓',
                        'alert': '🚨',
                        'inventory': '📦',
                        'order': '🛒',
                        'status': '📊'
                    }
                    
                    # 找到合適的圖標
                    icon = '📡'
                    for key, emoji in topic_icons.items():
                        if key in msg['topic']:
                            icon = emoji
                            break
                    
                    # 顯示訊息
                    with st.expander(f"{icon} {format_datetime_display(msg['timestamp'])} - {msg['summary']}", expanded=False):
                        st.write(f"**主題**: `{msg['topic']}`")
                        st.write(f"**時間**: {format_datetime_display(msg['timestamp'])}")
                        if isinstance(msg['payload'], dict):
                            st.json(msg['payload'])
                        else:
                            st.code(str(msg['payload']))
        else:
            st.write("📭 暫無訊息")
            if mqtt_client and mqtt_client.get_connection_status().get('connected', False):
                st.caption("已連接MQTT，等待訊息...")
        
        # 控制按鈕
        col_clear, col_refresh = st.columns(2)
        with col_clear:
            if st.button("🗑️ 清除記錄", key="clear_mqtt_messages"):
                st.session_state.mqtt_messages = []
                st.rerun()
        
        with col_refresh:
            if st.button("🔄 刷新", key="refresh_mqtt_display"):
                st.rerun()


def send_mqtt_command(machine_code: str, command: str, parameters: Optional[dict] = None) -> bool:
    \"\"\"發送 MQTT 命令到指定機台（未來可用）
    
    Args:
        machine_code: 機台代碼
        command: 命令名稱
        parameters: 命令參數（可選）
    
    Returns:
        bool: 是否成功發送
    \"\"\"
    if not MQTTClient or 'mqtt_client' not in st.session_state or not st.session_state.mqtt_client:
        return False
    
    try:
        mqtt_client = st.session_state.mqtt_client
        if not getattr(mqtt_client, '_connected', False):
            st.warning("MQTT 客戶端未連接，無法發送命令")
            return False
        
        # Use the MQTT client's publish_command method
        mqtt_client.publish_command(machine_code, command, parameters or {})
        
        # Log the command
        if 'mqtt_messages' not in st.session_state:
            st.session_state.mqtt_messages = []
        
        st.session_state.mqtt_messages.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'topic': f'machine/{machine_code}/command',
            'summary': f'發送命令: {command}'
        })
        
        return True
        
    except Exception as e:
        st.error(f"發送 MQTT 命令失敗: {e}")
        return False


def setup_mqtt_callbacks():
    \"\"\"設置 MQTT 回調函數以處理即時更新（未來可用）\"\"\"
    if not MQTTClient or 'mqtt_client' not in st.session_state or not st.session_state.mqtt_client:
        return
    
    mqtt_client = st.session_state.mqtt_client
    
    def on_heartbeat(topic: str, payload: dict):
        \"\"\"處理機台心跳訊息\"\"\"
        try:
            machine_code = topic.split('/')[1]
            if 'mqtt_messages' not in st.session_state:
                st.session_state.mqtt_messages = []
            
            st.session_state.mqtt_messages.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'topic': topic,
                'summary': f'{machine_code} 心跳正常'
            })
        except Exception as e:
            st.error(f"處理心跳訊息錯誤: {e}")
    
    def on_alert(topic: str, payload: dict):
        \"\"\"處理機台告警訊息\"\"\"
        try:
            machine_code = topic.split('/')[1]
            alert_level = payload.get('level', 'info')
            message = payload.get('message', '未知告警')
            
            if 'mqtt_messages' not in st.session_state:
                st.session_state.mqtt_messages = []
            
            st.session_state.mqtt_messages.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'topic': topic,
                'summary': f'{machine_code} 告警: {message}'
            })
            
            # Show alert in Streamlit
            if alert_level == 'error':
                st.error(f"🚨 {machine_code}: {message}")
            elif alert_level == 'warning':
                st.warning(f"⚠️ {machine_code}: {message}")
            else:
                st.info(f"ℹ️ {machine_code}: {message}")
                
        except Exception as e:
            st.error(f"處理告警訊息錯誤: {e}")
    
    # Subscribe to topics with callbacks
    try:
        mqtt_client.subscribe("machine/+/heartbeat", on_heartbeat)
        mqtt_client.subscribe("machine/+/alert", on_alert)
    except Exception as e:
        st.error(f"設置 MQTT 回調失敗: {e}")


@st.dialog("🔧 MQTT命令執行")
def show_mqtt_command_dialog_content(machine_code: str, machine_name: str, command: str, command_name: str, parameters: dict = None):
    \"\"\"MQTT命令對話框內容函數（未來可用）\"\"\"
    try:
        ui_logger.info(f"Executing MQTT command '{command}' for machine {machine_code} ({machine_name})")
        
        # 顯示命令資訊
        st.markdown(f"### 🔧 執行MQTT命令")
        st.markdown(f"**機台**: {machine_name} ({machine_code})")
        st.markdown(f"**命令**: {command_name}")
        st.markdown(f"**命令類型**: {command}")
        
        if parameters:
            st.markdown(f"**參數**: {parameters}")
        
        # 執行MQTT命令
        with st.spinner("正在發送MQTT命令..."):
            result = send_mqtt_command(machine_code, command, parameters)
        
        # 顯示執行結果
        st.markdown("### 📊 執行結果")
        
        if result:
            st.success("✅ MQTT命令發送成功！")
            
            # 顯示詳細資訊
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("發送狀態", "成功")
                st.metric("機台代碼", machine_code)
            
            with col2:
                st.metric("命令類型", command_name)
                st.metric("執行時間", "即時")
            
            # 顯示命令詳情
            st.markdown("### 📋 命令詳情")
            command_details = {
                "機台名稱": machine_name,
                "機台代碼": machine_code,
                "命令": command,
                "命令描述": command_name,
                "參數": parameters if parameters else "無",
                "發送時間": format_datetime_display(datetime.now()),
                "狀態": "已發送"
            }
            
            for key, value in command_details.items():
                st.write(f"**{key}**: {value}")
            
            # 顯示注意事項
            st.markdown("### ⚠️ 注意事項")
            if command == "restart":
                st.warning("🔄 重啟命令已發送，機台將在幾秒內重新啟動。請等待機台重新上線。")
            elif command == "maintenance_mode":
                st.info("🔧 維護模式已啟用，機台將進入維護狀態，暫停正常服務。")
            elif command == "status_request":
                st.info("📊 狀態請求已發送，機台將回傳最新的狀態資訊。")
        
        else:
            st.error("❌ MQTT命令發送失敗！")
            
            # 顯示錯誤資訊
            st.markdown("### ❌ 錯誤詳情")
            st.write("**可能的原因**:")
            st.write("- MQTT連接未建立")
            st.write("- 機台離線或無回應")
            st.write("- 網路連接問題")
            st.write("- 命令格式錯誤")
            
            # 顯示建議操作
            st.markdown("### 💡 建議操作")
            st.write("1. 檢查MQTT連接狀態")
            st.write("2. 確認機台是否在線")
            st.write("3. 檢查網路連接")
            st.write("4. 稍後重試")
            
    except Exception as e:
        ui_logger.error(f"Error in MQTT command dialog: {str(e)}")
        st.error(f"❌ 執行MQTT命令時發生錯誤: {str(e)}")


def show_mqtt_command_dialog(machine_code: str, machine_name: str, command: str, command_name: str, parameters: dict = None):
    \"\"\"顯示MQTT命令執行對話框（未來可用）\"\"\"
    # 調用對話框函數
    show_mqtt_command_dialog_content(machine_code, machine_name, command, command_name, parameters)
"""


