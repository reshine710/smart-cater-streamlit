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
except ImportError:
    st.warning("MQTT client not available. Some features may be limited.")
    MQTTClient = None
    initialize_mqtt_client = None

def machine_status_page():
    """機台狀態監控頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing machine status page")
    st.title("🖥️ 機台狀態監控")
    st.markdown("---")
    
    # Mode toggle switch
    col1, col2 = st.columns([3, 1])
    with col2:
        real_mode = st.toggle("🔴 真實機台模式", value=True, help="開啟後使用真實 API 和 MQTT 數據，關閉後使用模擬數據")
        
    ui_logger.debug(f"Machine status page mode: {'Real' if real_mode else 'Simulation'}")
    
    # Initialize MQTT client if available
    if 'mqtt_client' not in st.session_state and MQTTClient:
        try:
            st.session_state.mqtt_client = MQTTClient()
            # Note: In a real Streamlit app, you'd want to handle async connection differently
            # This is a simplified approach for demonstration
        except Exception as e:
            st.error(f"Failed to initialize MQTT client: {e}")
            st.session_state.mqtt_client = None
    
    # MQTT connection status
    if MQTTClient and 'mqtt_client' in st.session_state and st.session_state.mqtt_client:
        mqtt_status = "🟢 Connected" if getattr(st.session_state.mqtt_client, '_connected', False) else "🔴 Disconnected"
        st.sidebar.write(f"**MQTT Status**: {mqtt_status}")
        
        if st.sidebar.button("Connect MQTT" if not getattr(st.session_state.mqtt_client, '_connected', False) else "Disconnect MQTT"):
            try:
                if not getattr(st.session_state.mqtt_client, '_connected', False):
                    # In a real app, you'd handle this async properly
                    st.sidebar.info("Connecting to MQTT...")
                    # asyncio.run(st.session_state.mqtt_client.connect())
                else:
                    # asyncio.run(st.session_state.mqtt_client.disconnect())
                    st.sidebar.info("Disconnecting from MQTT...")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"MQTT operation failed: {e}")
    
    # Get machine data based on mode
    if real_mode:
        # 真實模式：從 API 獲取數據
        machines = st.session_state.api.get_machines()
        system_logger.debug(f"Retrieved {len(machines)} machines from API")
    else:
        # 模擬模式：生成模擬數據
        machines = generate_mock_machine_data()
        system_logger.debug(f"Generated {len(machines)} mock machines")
    
    # 狀態總覽
    col1, col2, col3 = st.columns(3)
    
    status_counts = {}
    for machine in machines:
        status = machine['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    with col1:
        st.metric("🟢 線上", status_counts.get('online', 0))
    with col2:
        st.metric("🟡 維護中", status_counts.get('maintenance', 0))
    with col3:
        st.metric("🔴 離線", status_counts.get('offline', 0))
    
    st.markdown("---")
    
    # 機台詳細狀態
    st.subheader("機台詳細狀態")
    
    for machine in machines:
        with st.expander(f"📍 {machine['name']} ({machine['machine_code']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = {
                    'online': '🟢',
                    'maintenance': '🟡',
                    'offline': '🔴'
                }
                st.write(f"**狀態**: {status_color.get(machine['status'], '⚪')} {machine['status']}")
                st.write(f"**位置**: {machine['location']}")
            
            with col2:
                if machine['temperature']:
                    st.write(f"**溫度**: {machine['temperature']}°C")
                else:
                    st.write("**溫度**: N/A")
                st.write(f"**最後心跳**: {machine['last_heartbeat']}")
            
            with col3:
                # MQTT-enabled commands
                if st.button(f"🔄 重啟機台 {machine['id']}", key=f"restart_{machine['id']}"):
                    if real_mode and MQTTClient and 'mqtt_client' in st.session_state and st.session_state.mqtt_client:
                        # 真實模式：發送 MQTT 命令
                        try:
                            st.session_state.mqtt_client.publish_command(machine['machine_code'], "restart")
                            mqtt_logger.info(f"Restart command sent to machine {machine['id']}")
                            st.success(f"✅ 重啟命令已發送到機台 {machine['id']}")
                        except Exception as e:
                            mqtt_logger.error(f"Failed to send restart command to machine {machine['id']}: {str(e)}")
                            st.error(f"❌ 發送命令失敗: {str(e)}")
                    else:
                        # 模擬模式或 MQTT 不可用
                        mqtt_logger.info(f"Simulated restart command for machine {machine['id']}")
                        st.success(f"✅ 模擬重啟機台 {machine['id']}")
                
                if st.button(f"🔧 維護模式 {machine['id']}", key=f"maintenance_{machine['id']}"):
                    if real_mode and MQTTClient and 'mqtt_client' in st.session_state and st.session_state.mqtt_client:
                        # 真實模式：發送 MQTT 命令
                        try:
                            st.session_state.mqtt_client.publish_command(machine['machine_code'], "maintenance_mode")
                            mqtt_logger.info(f"Maintenance mode command sent to machine {machine['id']}")
                            st.success(f"✅ 維護模式命令已發送到機台 {machine['id']}")
                        except Exception as e:
                            mqtt_logger.error(f"Failed to send maintenance command to machine {machine['id']}: {str(e)}")
                            st.error(f"❌ 發送命令失敗: {str(e)}")
                    else:
                        # 模擬模式或 MQTT 不可用
                        mqtt_logger.info(f"Simulated maintenance mode for machine {machine['id']}")
                        st.success(f"✅ 模擬設定機台 {machine['id']} 為維護模式")
                
                if st.button(f"📊 更新狀態 {machine['id']}", key=f"status_{machine['id']}"):
                    if send_mqtt_command(machine['machine_code'], "get_status"):
                        st.info(f"📊 已透過MQTT請求 {machine['name']} 狀態更新")
                    else:
                        st.info(f"已請求 {machine['name']} 狀態更新")
    
    # Real-time updates section
    st.markdown("---")
    st.subheader("📡 即時監控")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**MQTT 主題訂閱狀態**")
        if MQTTClient and 'mqtt_client' in st.session_state and st.session_state.mqtt_client:
            topics = [
                "machine/+/heartbeat",
                "machine/+/alert", 
                "machine/+/inventory/update",
                "machine/+/order/status"
            ]
            for topic in topics:
                st.write(f"• {topic}")
        else:
            st.write("MQTT 客戶端未連接")
    
    with col2:
        st.write("**最近 MQTT 訊息**")
        if 'mqtt_messages' not in st.session_state:
            st.session_state.mqtt_messages = []
        
        # Display recent messages (last 5)
        recent_messages = st.session_state.mqtt_messages[-5:] if st.session_state.mqtt_messages else []
        if recent_messages:
            for msg in reversed(recent_messages):
                st.text(f"{msg['timestamp']}: {msg['topic']} - {msg['summary']}")
        else:
            st.write("暫無訊息")
        
        if st.button("清除訊息記錄"):
            st.session_state.mqtt_messages = []
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


def generate_mock_machine_data():
    """生成模擬機台數據"""
    system_logger.debug("Generating mock machine data")
    mock_machines = []   
    # 固定的模擬機台資料，確保每次刷新都一致（除非特意更新）
    if 'mock_machines_data' not in st.session_state:
        mock_machines = [
            {
                'id': 1,
                'name': '智慧販賣機 A1',
                'machine_code': 'VM001',
                'location': '辦公大樓 1F 大廳',
                'status': random.choice(['online', 'maintenance', 'offline']),
                'temperature': random.randint(18, 28),
                'last_heartbeat': (datetime.now() - timedelta(minutes=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 2,
                'name': '智慧販賣機 B2',
                'machine_code': 'VM002',
                'location': '員工餐廳',
                'status': random.choice(['online', 'maintenance', 'offline']),
                'temperature': random.randint(18, 28),
                'last_heartbeat': (datetime.now() - timedelta(minutes=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 3,
                'name': '智慧販賣機 C3',
                'machine_code': 'VM003',
                'location': '研發部門 3F',
                'status': random.choice(['online', 'maintenance', 'offline']),
                'temperature': random.randint(18, 28),
                'last_heartbeat': (datetime.now() - timedelta(minutes=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 4,
                'name': '智慧販賣機 D4',
                'machine_code': 'VM004',
                'location': '會議室區域 2F',
                'status': random.choice(['online', 'maintenance', 'offline']),
                'temperature': random.randint(18, 28),
                'last_heartbeat': (datetime.now() - timedelta(minutes=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 5,
                'name': '智慧販賣機 E5',
                'machine_code': 'VM005',
                'location': '停車場入口',
                'status': random.choice(['online', 'maintenance', 'offline']),
                'temperature': random.randint(18, 28),
                'last_heartbeat': (datetime.now() - timedelta(minutes=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        st.session_state.mock_machines_data = mock_machines
    
    # 每次調用時稍微更新一些動態資料（如溫度、心跳時間）
    for machine in st.session_state.mock_machines_data:
        # 隨機更新溫度（小幅變化）
        if random.random() < 0.3:  # 30% 機率更新溫度
            machine['temperature'] = max(15, min(35, machine['temperature'] + random.randint(-2, 2)))
        
        # 隨機更新心跳時間
        if random.random() < 0.5:  # 50% 機率更新心跳
            machine['last_heartbeat'] = (datetime.now() - timedelta(minutes=random.randint(0, 15))).strftime('%Y-%m-%d %H:%M:%S')
        
        # 偶爾改變狀態
        if random.random() < 0.05:  # 5% 機率改變狀態
            machine['status'] = random.choice(['online', 'maintenance', 'offline'])
    
    return st.session_state.mock_machines_data


def generate_mock_mqtt_messages():
    """生成模擬 MQTT 消息"""
    mqtt_logger.debug("Generating mock MQTT messages")
    messages = []
    if not st.session_state.get('simulation_mode', False):
        return
    
    # 初始化訊息列表
    if 'mqtt_messages' not in st.session_state:
        st.session_state.mqtt_messages = []
    
    # 隨機生成一些模擬訊息
    if random.random() < 0.1:  # 10% 機率生成新訊息
        machine_codes = ['VM001', 'VM002', 'VM003', 'VM004', 'VM005']
        machine_code = random.choice(machine_codes)
        
        message_types = [
            {
                'topic': f'machine/{machine_code}/heartbeat',
                'summary': f'{machine_code} 心跳正常'
            },
            {
                'topic': f'machine/{machine_code}/alert',
                'summary': f'{machine_code} 告警: 溫度異常'
            },
            {
                'topic': f'machine/{machine_code}/inventory/update',
                'summary': f'{machine_code} 庫存更新'
            },
            {
                'topic': f'machine/{machine_code}/order/status',
                'summary': f'{machine_code} 訂單處理完成'
            }
        ]
        
        message = random.choice(message_types)
        message['timestamp'] = datetime.now().strftime('%H:%M:%S')
        
        st.session_state.mqtt_messages.append(message)
        
        # 保持最多 20 條訊息
        if len(st.session_state.mqtt_messages) > 20:
            st.session_state.mqtt_messages = st.session_state.mqtt_messages[-20:]
