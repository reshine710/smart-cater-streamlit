import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import json
from logger_config import mqtt_logger, ui_logger, system_logger
from typing import Optional, List, Dict

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
    
    # 按狀態分組機台
    status_groups = {
        'online': [],
        'maintenance': [],
        'offline': [],
        'unknown': []
    }
    
    for machine in valid_machines:
        status = machine.get('status', 'unknown').lower()
        if status in status_groups:
            status_groups[status].append(machine)
        else:
            status_groups['unknown'].append(machine)
    
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

def get_status_config(status: str) -> Dict:
    """獲取狀態配置"""
    configs = {
        'online': {
            'icon': '🟢',
            'title': '線上',
            'color': 'success',
            'bg_color': '#d4edda',
            'border_color': '#28a745'
        },
        'maintenance': {
            'icon': '🟡',
            'title': '維護中',
            'color': 'warning',
            'bg_color': '#fff3cd',
            'border_color': '#ffc107'
        },
        'offline': {
            'icon': '🔴',
            'title': '離線',
            'color': 'error',
            'bg_color': '#f8d7da',
            'border_color': '#dc3545'
        },
        'unknown': {
            'icon': '⚪',
            'title': '未知狀態',
            'color': 'info',
            'bg_color': '#e2e3e5',
            'border_color': '#6c757d'
        }
    }
    return configs.get(status, configs['unknown'])

def render_machine_card(machine: Dict, status_config: Dict):
    """渲染單個機台卡片"""
    machine_id = machine.get('id', 'N/A')
    machine_code = machine.get('machine_code', 'N/A')
    machine_name = machine.get('name', '未命名機台')
    status = machine.get('status', 'unknown')
    location = machine.get('location', {})
    
    # 處理位置資訊
    if isinstance(location, dict):
        location_name = location.get('name', '未知位置')
    else:
        location_name = str(location) if location else '未知位置'
    
    # 獲取其他資訊
    ip_address = machine.get('ip_address', 'N/A')
    firmware_version = machine.get('firmware_version', 'N/A')
    last_heartbeat = machine.get('last_heartbeat', 'N/A')
    
    # 計算最後心跳時間
    heartbeat_status = get_heartbeat_status(last_heartbeat)
    
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
                st.write(f"**狀態**: {status_config['icon']} {status_config['title']}")
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
                op_col1, op_col2, op_col3 = st.columns(3)
                
                with op_col1:
                    if st.button("🔄 重啟", key=f"overview_restart_{machine_id}"):
                        show_mqtt_command_dialog(machine_code, machine_name, "restart", "重啟")
                
                with op_col2:
                    if st.button("🔧 維護", key=f"overview_maintenance_{machine_id}"):
                        show_mqtt_command_dialog(machine_code, machine_name, "maintenance_mode", "維護模式", {"enabled": True})
                
                with op_col3:
                    if st.button("📊 狀態", key=f"overview_status_{machine_id}"):
                        show_mqtt_command_dialog(machine_code, machine_name, "status_request", "狀態請求")
            
            
            # 编辑机台按钮（仅管理员）
            if is_admin:
                st.markdown("**機台管理**")
                if st.button("✏️ 編輯機台資訊", key=f"edit_machine_{machine_id}"):
                    show_edit_machine_dialog(machine)
            
            # 菜單查看按鈕（所有用戶）
            st.markdown("**菜單資訊**")
            if st.button("📋 查看當前菜單", key=f"view_menu_{machine_id}"):
                show_machine_menu_dialog(machine_id, machine_name)

def get_heartbeat_status(last_heartbeat) -> str:
    """獲取心跳狀態"""
    if last_heartbeat == 'N/A' or not last_heartbeat:
        return "🔴 無心跳"
    
    try:
        # 嘗試解析時間戳
        if isinstance(last_heartbeat, str):
            heartbeat_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
        else:
            heartbeat_time = last_heartbeat
        
        # 計算時間差
        now = datetime.now(heartbeat_time.tzinfo) if heartbeat_time.tzinfo else datetime.now()
        time_diff = now - heartbeat_time
        
        if time_diff.total_seconds() < 60:  # 1分鐘內
            return "🟢 正常"
        elif time_diff.total_seconds() < 300:  # 5分鐘內
            return "🟡 延遲"
        else:
            return "🔴 超時"
    except Exception as e:
        ui_logger.warning(f"Error parsing heartbeat time: {e}")
        return "⚪ 未知"

def machine_status_page():
    """機台狀態監控頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing machine status page")
    st.title("🖥️ 機台狀態監控")
    st.markdown("---")
    
    ui_logger.debug("Machine status page accessed")
    
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
    
    # 狀態總覽
    col1, col2, col3 = st.columns(3)
    
    status_counts = {}
    for machine in machines:
        # 安全地獲取狀態
        if isinstance(machine, dict) and 'status' in machine:
            status = machine['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        else:
            system_logger.warning(f"Invalid machine data format: {type(machine)}, content: {machine}")
            # 跳過無效數據
            continue
    
    with col1:
        st.metric("🟢 線上", status_counts.get('online', 0))
    with col2:
        st.metric("🟡 維護中", status_counts.get('maintenance', 0))
    with col3:
        st.metric("🔴 離線", status_counts.get('offline', 0))
    
    st.markdown("---")
    
    # 機台總覽卡片
    st.subheader("📊 機台總覽")
    show_machine_overview(machines)
    
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
                        options=["online", "offline", "maintenance", "fault"],
                        format_func=lambda x: {"online": "🟢 線上", "offline": "🔴 離線", "maintenance": "🟡 維護中", "fault": "🔴 故障"}[x]
                    )
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
                        machine_data = {
                            "machine_code": machine_code.strip(),
                            "name": machine_name.strip(),
                            "location": selected_location.strip(),  # 直接使用地點名稱
                            "status": status,
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
    
    # 機台詳細狀態
    st.subheader("機台詳細狀態")
    
    for machine in machines:
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
                status_color = {
                    'online': '🟢',
                    'maintenance': '🟡',
                    'offline': '🔴'
                }
                machine_status = machine.get('status', 'unknown')
                st.write(f"**狀態**: {status_color.get(machine_status, '⚪')} {machine_status}")
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
                st.write(f"**最後心跳**: {machine.get('last_heartbeat', 'Unknown')}")
            
            with col3:
                # MQTT-enabled commands
                mqtt_client = st.session_state.get('mqtt_client')
                mqtt_available = (mqtt_client and 
                                mqtt_client.get_connection_status().get('connected', False))
                
                if st.button(f"🔄 重啟機台 {machine_id}", 
                           key=f"detail_restart_{machine_id}",
                           disabled=not mqtt_available):
                    if mqtt_available:
                        # 發送 MQTT 命令
                        try:
                            success = mqtt_client.publish_command(machine_code, "restart")
                            if success:
                                mqtt_logger.info(f"Restart command sent to machine {machine_code}")
                                st.success(f"✅ 重啟命令已發送到機台 {machine_name}")
                            else:
                                st.error(f"❌ 發送重啟命令失敗")
                        except Exception as e:
                            mqtt_logger.error(f"Failed to send restart command to machine {machine_code}: {str(e)}")
                            st.error(f"❌ 發送命令失敗: {str(e)}")
                    else:
                        st.error("❌ MQTT 連接不可用，無法發送命令")
                
                if st.button(f"🔧 維護模式 {machine_id}", 
                           key=f"detail_maintenance_{machine_id}",
                           disabled=not mqtt_available):
                    if mqtt_available:
                        # 發送 MQTT 命令
                        try:
                            success = mqtt_client.publish_command(machine_code, "maintenance_mode")
                            if success:
                                mqtt_logger.info(f"Maintenance mode command sent to machine {machine_code}")
                                st.success(f"✅ 維護模式命令已發送到機台 {machine_name}")
                            else:
                                st.error(f"❌ 發送維護模式命令失敗")
                        except Exception as e:
                            mqtt_logger.error(f"Failed to send maintenance command to machine {machine_code}: {str(e)}")
                            st.error(f"❌ 發送命令失敗: {str(e)}")
                    else:
                        st.error("❌ MQTT 連接不可用，無法發送命令")
                
                if st.button(f"📊 更新狀態 {machine_id}", 
                           key=f"detail_status_{machine_id}",
                           disabled=not mqtt_available):
                    if mqtt_available:
                        try:
                            success = mqtt_client.publish_command(machine_code, "get_status")
                            if success:
                                mqtt_logger.info(f"Status update command sent to machine {machine_code}")
                                st.info(f"📊 已透過MQTT請求 {machine_name} 狀態更新")
                            else:
                                st.error(f"❌ 發送狀態更新命令失敗")
                        except Exception as e:
                            mqtt_logger.error(f"Failed to send status command to machine {machine_code}: {str(e)}")
                            st.error(f"❌ 發送命令失敗: {str(e)}")
                    else:
                        st.error("❌ MQTT 連接不可用，無法發送命令")
                
                # 刪除機台功能 (僅管理員可用)
                is_admin = st.session_state.get('is_admin', False)
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
                
                # 顯示MQTT連接狀態提示
                if not mqtt_available:
                    st.caption("⚠️ 需要MQTT連接才能發送命令")
    
    # Real-time updates section
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
                    with st.expander(f"{icon} {msg['timestamp']} - {msg['summary']}", expanded=False):
                        st.write(f"**主題**: `{msg['topic']}`")
                        st.write(f"**時間**: {msg['timestamp']}")
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
    """發送 MQTT 命令到指定機台
    
    Args:
        machine_code: 機台代碼
        command: 命令名稱
        parameters: 命令參數（可選）
    
    Returns:
        bool: 是否成功發送
    """
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
    """設置 MQTT 回調函數以處理即時更新"""
    if not MQTTClient or 'mqtt_client' not in st.session_state or not st.session_state.mqtt_client:
        return
    
    mqtt_client = st.session_state.mqtt_client
    
    def on_heartbeat(topic: str, payload: dict):
        """處理機台心跳訊息"""
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
        """處理機台告警訊息"""
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

# 定義MQTT命令對話框函數
@st.dialog("🔧 MQTT命令執行")
def show_mqtt_command_dialog_content(machine_code: str, machine_name: str, command: str, command_name: str, parameters: dict = None):
    """MQTT命令對話框內容函數"""
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
                "發送時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
    """顯示MQTT命令執行對話框"""
    # 調用對話框函數
    show_mqtt_command_dialog_content(machine_code, machine_name, command, command_name, parameters)

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
        status_options = ["online", "offline", "maintenance", "error"]
        current_status = machine.get('status', 'offline')
        status_index = status_options.index(current_status) if current_status in status_options else 1
        
        status = st.selectbox(
            "機台狀態(測試環境)",
            options=status_options,
            index=status_index,
            format_func=lambda x: {
                "online": "🟢 在線",
                "offline": "🔴 離線",
                "maintenance": "🟡 維護中",
            }.get(x, x),
            key=f"edit_status_{machine_id}"
        )
        
        # 位置資訊
        st.markdown("**📍 位置資訊**")
        
        # 獲取所有位置選項
        try:
            if hasattr(st.session_state, 'api') and st.session_state.api:
                locations_data = st.session_state.api.get_locations()
                if locations_data:
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
                    location_index = location_options.index(current_location_name) if current_location_name in location_options else 0
                    
                    selected_location_name = st.selectbox(
                        "機台位置",
                        options=location_options,
                        index=location_index,
                        key=f"edit_location_{machine_id}"
                    )
                    
                    location_id = location_map.get(selected_location_name)
                else:
                    location_id = None
                    st.warning("無法獲取位置列表")
            else:
                location_id = None
                st.warning("API不可用")
        except Exception as e:
            ui_logger.error(f"Error fetching locations: {str(e)}")
            location_id = None
            st.error(f"獲取位置列表失敗: {str(e)}")
        
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
            submitted = st.form_submit_button("💾 儲存變更", type="primary", use_container_width=True)
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if cancelled:
            st.rerun()
        
        if submitted:
            # 驗證必填欄位
            if not machine_name:
                st.error("❌ 請填寫機台名稱")
                return
            
            # 準備更新數據
            update_data = {
                "name": machine_name,
                "ip_address": ip_address if ip_address else None,
                "firmware_version": firmware_version if firmware_version else None,
                "status": status,
                "description": description if description else None
            }
            
            # 如果有位置ID，添加到更新數據中
            if location_id:
                update_data["location_id"] = location_id
            
            # 記錄API調用
            ui_logger.info(f"🔄 開始更新機台 {machine_id} 資訊")
            ui_logger.info(f"📋 更新數據: {update_data}")
            
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


