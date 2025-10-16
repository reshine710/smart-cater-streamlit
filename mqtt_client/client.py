"""
MQTT客戶端適配器
直接連接MQTT Broker，為Streamlit環境提供MQTT功能
"""

import asyncio
import json
import logging
import threading
import time
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
import streamlit as st
from logger_config import mqtt_logger

# MQTT配置 - 與後台使用相同的broker
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "smartcater_admin_frontend")


class MQTTClient:
    """
    MQTT客戶端適配器
    直接連接MQTT Broker，為Streamlit提供MQTT功能
    """

    def __init__(self):
        """初始化MQTT客戶端適配器"""
        self._connected = False
        self._client = None
        self._client_thread = None
        self._topic_callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        
        # 訊息緩存，用於在Streamlit中顯示
        try:
            if 'mqtt_messages' not in st.session_state:
                st.session_state.mqtt_messages = []
        except Exception:
            # 如果不在 Streamlit 環境中，使用本地緩存
            self._local_messages = []
        
        # 初始化MQTT客戶端
        self._init_mqtt_client()

    def _init_mqtt_client(self):
        """初始化MQTT客戶端"""
        try:
            self._client = mqtt.Client(client_id=MQTT_CLIENT_ID)
            
            # 設置回調函數
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._client.on_subscribe = self._on_subscribe
            self._client.on_publish = self._on_publish
            
            # 設置認證
            if MQTT_USERNAME and MQTT_PASSWORD:
                self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            
            # 設置TLS
            if MQTT_USE_TLS:
                import ssl
                self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                
            mqtt_logger.info("MQTT client initialized")
            
        except Exception as e:
            mqtt_logger.error(f"Failed to initialize MQTT client: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT連接回調"""
        if rc == 0:
            mqtt_logger.info(f"Connected to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
            self._connected = True
            
            # 重新訂閱所有主題
            for topic in self._topic_callbacks:
                mqtt_logger.info(f"Resubscribing to topic: {topic}")
                self._client.subscribe(topic)
        else:
            mqtt_logger.error(f"Failed to connect to MQTT Broker. Return code: {rc}")
            self._connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT斷線回調"""
        mqtt_logger.info(f"Disconnected from MQTT Broker with code: {rc}")
        self._connected = False
        
        # 自動重連
        if rc != 0 and self._running:
            mqtt_logger.info("Attempting to reconnect...")
            try:
                time.sleep(5)  # 等待5秒後重連
                self._client.reconnect()
            except Exception as e:
                mqtt_logger.error(f"Reconnection failed: {e}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT訊息接收回調"""
        try:
            mqtt_logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")
            
            # 解析JSON訊息
            try:
                payload = json.loads(msg.payload.decode())
            except json.JSONDecodeError:
                mqtt_logger.warning(f"Received non-JSON message on topic {msg.topic}")
                payload = msg.payload.decode()
            
            # 添加到訊息緩存
            message_entry = {
                'topic': msg.topic,
                'summary': self._generate_message_summary(msg.topic, payload),
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'payload': payload
            }
            
            try:
                st.session_state.mqtt_messages.append(message_entry)
                # 保持最多20條訊息
                if len(st.session_state.mqtt_messages) > 20:
                    st.session_state.mqtt_messages = st.session_state.mqtt_messages[-20:]
            except Exception:
                # 如果不在 Streamlit 環境中，使用本地緩存
                if not hasattr(self, '_local_messages'):
                    self._local_messages = []
                self._local_messages.append(message_entry)
                if len(self._local_messages) > 20:
                    self._local_messages = self._local_messages[-20:]
            
            # 調用註冊的回調函數
            self._call_topic_callbacks(msg.topic, payload)
            
        except Exception as e:
            mqtt_logger.error(f"Error processing MQTT message: {e}")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """MQTT訂閱回調"""
        mqtt_logger.info(f"Subscribed with QoS: {granted_qos}")
    
    def _on_publish(self, client, userdata, mid):
        """MQTT發布回調"""
        mqtt_logger.debug(f"Message published: {mid}")

    def _generate_message_summary(self, topic: str, payload: Any) -> str:
        """生成訊息摘要"""
        parts = topic.split('/')
        if len(parts) >= 3:
            machine_code = parts[1]
            message_type = parts[2]
            
            if message_type == 'heartbeat':
                return f'{machine_code} 心跳正常'
            elif message_type == 'alert':
                alert_type = payload.get('type', '未知告警')
                return f'{machine_code} 告警: {alert_type}'
            elif message_type == 'inventory':
                return f'{machine_code} 庫存更新'
            elif message_type == 'order':
                return f'{machine_code} 訂單狀態更新'
        
        return f'收到訊息: {topic}'

    def _call_topic_callbacks(self, topic: str, payload: Any):
        """調用主題回調函數"""
        for registered_topic, callbacks in self._topic_callbacks.items():
            # 簡單的主題匹配（支援+通配符）
            if self._topic_matches(registered_topic, topic):
                for callback in callbacks:
                    try:
                        callback(topic, payload)
                    except Exception as e:
                        mqtt_logger.error(f"Error in topic callback: {e}")

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """簡單的主題匹配，支援+通配符"""
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(pattern_parts) != len(topic_parts):
            return False
        
        for p, t in zip(pattern_parts, topic_parts):
            if p != '+' and p != t:
                return False
        
        return True

    async def connect(self):
        """連接到MQTT Broker"""
        if self._connected:
            return
        
        try:
            self._running = True
            
            # 在背景執行緒中啟動MQTT客戶端
            def mqtt_loop():
                try:
                    self._client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
                    self._client.loop_forever()
                except Exception as e:
                    mqtt_logger.error(f"MQTT loop error: {e}")
                    self._connected = False
            
            self._client_thread = threading.Thread(target=mqtt_loop, daemon=True)
            self._client_thread.start()
            
            # 等待連接建立
            for _ in range(20):  # 最多等待10秒
                if self._connected:
                    break
                await asyncio.sleep(0.5)
            
            if not self._connected:
                raise ConnectionError("MQTT connection timeout")
                
            mqtt_logger.info("Connected to MQTT Broker")
            
        except Exception as e:
            mqtt_logger.error(f"Failed to connect to MQTT Broker: {e}")
            self._running = False
            raise ConnectionError(f"MQTT connection failed: {e}")

    async def disconnect(self):
        """斷開MQTT連接"""
        self._running = False
        if self._client and self._connected:
            self._client.disconnect()
            self._client.loop_stop()
        self._connected = False
        mqtt_logger.info("Disconnected from MQTT Broker")

    def subscribe(self, topic: str, callback: Callable[[str, Any], None]):
        """訂閱MQTT主題"""
        if topic not in self._topic_callbacks:
            self._topic_callbacks[topic] = []
            # 如果已連接，直接訂閱
            if self._connected and self._client:
                self._client.subscribe(topic)
        
        self._topic_callbacks[topic].append(callback)
        mqtt_logger.info(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Optional[Callable] = None):
        """取消訂閱主題"""
        if topic in self._topic_callbacks:
            if callback and callback in self._topic_callbacks[topic]:
                self._topic_callbacks[topic].remove(callback)
            else:
                self._topic_callbacks[topic] = []
            
            if not self._topic_callbacks[topic]:
                del self._topic_callbacks[topic]
                mqtt_logger.info(f"Unsubscribed from topic: {topic}")

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False):
        """發布MQTT訊息"""
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to MQTT Broker")
        
        try:
            # 轉換payload為JSON字符串
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise ConnectionError(f"MQTT publish error: {result.rc}")
            
            mqtt_logger.info(f"Published message to {topic}")
            
        except Exception as e:
            mqtt_logger.error(f"Failed to publish message: {e}")
            raise

    def publish_command(self, machine_code: str, command: str, parameters: Dict[str, Any] = None):
        """發布命令到機台"""
        try:
            topic = f"machine/{machine_code}/command"
            payload = {
                "command": command,
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": parameters or {},
            }
            
            self.publish(topic, payload, qos=1)  # 使用QoS 1確保命令送達
            mqtt_logger.info(f"Command '{command}' sent to machine {machine_code}")
            return True
            
        except Exception as e:
            mqtt_logger.error(f"Failed to send command: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """獲取MQTT連接狀態"""
        return {
            "connected": self._connected,
            "broker": MQTT_BROKER_HOST,
            "port": MQTT_BROKER_PORT,
            "client_id": MQTT_CLIENT_ID,
            "subscribed_topics": list(self._topic_callbacks.keys())
        }

    def get_subscribed_topics(self) -> List[str]:
        """獲取已訂閱的主題列表"""
        return list(self._topic_callbacks.keys())


def initialize_mqtt_client():
    """初始化MQTT客戶端適配器"""
    return MQTTClient()
