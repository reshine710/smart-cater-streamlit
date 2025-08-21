"""
MQTT客戶端適配器單元測試
測試所有MQTT客戶端功能的正確性
"""

import asyncio
import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing mqtt_client
sys.modules['streamlit'] = Mock()
mock_st = sys.modules['streamlit']
mock_st.session_state = {}

# Mock logger_config
sys.modules['logger_config'] = Mock()
mock_logger = Mock()
sys.modules['logger_config'].mqtt_logger = mock_logger

# 現在可以安全地導入mqtt_client
from mqtt_client.client import MQTTClient, initialize_mqtt_client
import paho.mqtt.client as mqtt


class TestMQTTClient(unittest.TestCase):
    """MQTT客戶端測試類別"""

    def setUp(self):
        """測試前置設定"""
        # 重置session_state
        mock_st.session_state.clear()
        mock_st.session_state['mqtt_messages'] = []
        
        # 重置logger mock
        mock_logger.reset_mock()
        
        # 建立測試用的MQTT客戶端
        with patch('mqtt_client.client.mqtt.Client') as mock_mqtt_client:
            self.mock_mqtt_client_instance = Mock()
            mock_mqtt_client.return_value = self.mock_mqtt_client_instance
            self.mqtt_client = MQTTClient()

    def tearDown(self):
        """測試後清理"""
        if hasattr(self.mqtt_client, '_client_thread') and self.mqtt_client._client_thread:
            self.mqtt_client._running = False
            if self.mqtt_client._client_thread.is_alive():
                self.mqtt_client._client_thread.join(timeout=1)

    def test_init_mqtt_client(self):
        """測試MQTT客戶端初始化"""
        # 驗證初始狀態
        self.assertFalse(self.mqtt_client._connected)
        self.assertEqual(self.mqtt_client._topic_callbacks, {})
        self.assertFalse(self.mqtt_client._running)
        
        # 驗證MQTT客戶端設定
        self.mock_mqtt_client_instance.username_pw_set.assert_not_called()  # 沒有設定用戶名密碼
        mock_logger.info.assert_called_with("MQTT client initialized")

    def test_init_with_credentials(self):
        """測試使用認證資訊初始化"""
        with patch.dict(os.environ, {
            'MQTT_USERNAME': 'test_user',
            'MQTT_PASSWORD': 'test_pass'
        }):
            with patch('mqtt_client.client.mqtt.Client') as mock_mqtt_client:
                mock_instance = Mock()
                mock_mqtt_client.return_value = mock_instance
                client = MQTTClient()
                
                mock_instance.username_pw_set.assert_called_once_with('test_user', 'test_pass')

    def test_init_with_tls(self):
        """測試使用TLS初始化"""
        with patch.dict(os.environ, {'MQTT_USE_TLS': 'true'}):
            with patch('mqtt_client.client.mqtt.Client') as mock_mqtt_client:
                mock_instance = Mock()
                mock_mqtt_client.return_value = mock_instance
                with patch('ssl.CERT_REQUIRED') as mock_cert:
                    client = MQTTClient()
                    mock_instance.tls_set.assert_called_once()

    def test_on_connect_success(self):
        """測試成功連接回調"""
        # 模擬成功連接 (rc=0)
        self.mqtt_client._on_connect(None, None, None, 0)
        
        self.assertTrue(self.mqtt_client._connected)
        mock_logger.info.assert_called_with(f"Connected to MQTT Broker: localhost:1883")

    def test_on_connect_failure(self):
        """測試連接失敗回調"""
        # 模擬連接失敗 (rc!=0)
        self.mqtt_client._on_connect(None, None, None, 1)
        
        self.assertFalse(self.mqtt_client._connected)
        mock_logger.error.assert_called_with("Failed to connect to MQTT Broker. Return code: 1")

    def test_on_connect_resubscribe(self):
        """測試連接時重新訂閱主題"""
        # 添加一些訂閱主題
        self.mqtt_client._topic_callbacks = {
            'test/topic1': [Mock()],
            'test/topic2': [Mock()]
        }
        
        # 模擬成功連接
        self.mqtt_client._on_connect(None, None, None, 0)
        
        # 驗證重新訂閱
        expected_calls = [
            call('test/topic1'),
            call('test/topic2')
        ]
        self.mock_mqtt_client_instance.subscribe.assert_has_calls(expected_calls, any_order=True)

    def test_on_disconnect(self):
        """測試斷線回調"""
        self.mqtt_client._connected = True
        self.mqtt_client._on_disconnect(None, None, 0)
        
        self.assertFalse(self.mqtt_client._connected)
        mock_logger.info.assert_called_with("Disconnected from MQTT Broker with code: 0")

    def test_on_disconnect_with_reconnect(self):
        """測試斷線後自動重連"""
        self.mqtt_client._connected = True
        self.mqtt_client._running = True
        
        with patch('time.sleep') as mock_sleep:
            self.mqtt_client._on_disconnect(None, None, 1)  # 非正常斷線
            
            mock_sleep.assert_called_once_with(5)
            self.mock_mqtt_client_instance.reconnect.assert_called_once()

    def test_on_message_json_payload(self):
        """測試接收JSON訊息"""
        # 建立模擬訊息
        mock_msg = Mock()
        mock_msg.topic = 'machine/VM001/heartbeat'
        mock_msg.payload = b'{"status": "online", "temperature": 25}'
        
        # 呼叫訊息處理
        self.mqtt_client._on_message(None, None, mock_msg)
        
        # 驗證訊息被添加到session_state
        self.assertEqual(len(mock_st.session_state['mqtt_messages']), 1)
        message = mock_st.session_state['mqtt_messages'][0]
        self.assertEqual(message['topic'], 'machine/VM001/heartbeat')
        self.assertEqual(message['summary'], 'VM001 心跳正常')
        self.assertIsInstance(message['payload'], dict)

    def test_on_message_non_json_payload(self):
        """測試接收非JSON訊息"""
        mock_msg = Mock()
        mock_msg.topic = 'test/topic'
        mock_msg.payload = b'plain text message'
        
        self.mqtt_client._on_message(None, None, mock_msg)
        
        # 驗證訊息被處理為字符串
        message = mock_st.session_state['mqtt_messages'][0]
        self.assertEqual(message['payload'], 'plain text message')

    def test_on_message_callback_execution(self):
        """測試訊息回調函數執行"""
        # 註冊回調函數
        callback = Mock()
        self.mqtt_client._topic_callbacks['machine/+/heartbeat'] = [callback]
        
        # 建立模擬訊息
        mock_msg = Mock()
        mock_msg.topic = 'machine/VM001/heartbeat'
        mock_msg.payload = b'{"status": "online"}'
        
        self.mqtt_client._on_message(None, None, mock_msg)
        
        # 驗證回調函數被呼叫
        callback.assert_called_once_with('machine/VM001/heartbeat', {"status": "online"})

    def test_message_cache_limit(self):
        """測試訊息緩存限制"""
        # 添加超過20條訊息
        for i in range(25):
            mock_msg = Mock()
            mock_msg.topic = f'test/topic/{i}'
            mock_msg.payload = b'{"test": "data"}'
            self.mqtt_client._on_message(None, None, mock_msg)
        
        # 驗證只保留最新20條
        self.assertEqual(len(mock_st.session_state['mqtt_messages']), 20)
        # 驗證是最新的20條
        self.assertEqual(mock_st.session_state['mqtt_messages'][0]['topic'], 'test/topic/5')
        self.assertEqual(mock_st.session_state['mqtt_messages'][-1]['topic'], 'test/topic/24')

    def test_generate_message_summary(self):
        """測試訊息摘要生成"""
        test_cases = [
            ('machine/VM001/heartbeat', {}, 'VM001 心跳正常'),
            ('machine/VM002/alert', {'type': '溫度異常'}, 'VM002 告警: 溫度異常'),
            ('machine/VM003/inventory', {}, 'VM003 庫存更新'),
            ('machine/VM004/order', {}, 'VM004 訂單狀態更新'),
            ('unknown/topic', {}, '收到訊息: unknown/topic')
        ]
        
        for topic, payload, expected in test_cases:
            with self.subTest(topic=topic):
                result = self.mqtt_client._generate_message_summary(topic, payload)
                self.assertEqual(result, expected)

    def test_topic_matches(self):
        """測試主題匹配功能"""
        test_cases = [
            ('machine/+/heartbeat', 'machine/VM001/heartbeat', True),
            ('machine/+/heartbeat', 'machine/VM002/heartbeat', True),
            ('machine/+/alert', 'machine/VM001/heartbeat', False),
            ('machine/VM001/+', 'machine/VM001/status', True),
            ('exact/topic', 'exact/topic', True),
            ('exact/topic', 'different/topic', False),
            ('machine/+/+', 'machine/VM001/heartbeat', True),
            ('machine/+', 'machine/VM001/heartbeat', False),  # 長度不匹配
        ]
        
        for pattern, topic, expected in test_cases:
            with self.subTest(pattern=pattern, topic=topic):
                result = self.mqtt_client._topic_matches(pattern, topic)
                self.assertEqual(result, expected)

    def test_subscribe(self):
        """測試訂閱功能"""
        callback = Mock()
        topic = 'test/topic'
        
        # 測試訂閱新主題
        self.mqtt_client.subscribe(topic, callback)
        
        self.assertIn(topic, self.mqtt_client._topic_callbacks)
        self.assertIn(callback, self.mqtt_client._topic_callbacks[topic])
        mock_logger.info.assert_called_with(f"Subscribed to topic: {topic}")

    def test_subscribe_when_connected(self):
        """測試連接狀態下的訂閱"""
        self.mqtt_client._connected = True
        callback = Mock()
        topic = 'test/topic'
        
        self.mqtt_client.subscribe(topic, callback)
        
        # 驗證直接訂閱broker
        self.mock_mqtt_client_instance.subscribe.assert_called_once_with(topic)

    def test_subscribe_multiple_callbacks(self):
        """測試同一主題多個回調"""
        callback1 = Mock()
        callback2 = Mock()
        topic = 'test/topic'
        
        self.mqtt_client.subscribe(topic, callback1)
        self.mqtt_client.subscribe(topic, callback2)
        
        self.assertEqual(len(self.mqtt_client._topic_callbacks[topic]), 2)
        self.assertIn(callback1, self.mqtt_client._topic_callbacks[topic])
        self.assertIn(callback2, self.mqtt_client._topic_callbacks[topic])

    def test_unsubscribe_specific_callback(self):
        """測試取消特定回調訂閱"""
        callback1 = Mock()
        callback2 = Mock()
        topic = 'test/topic'
        
        # 訂閱兩個回調
        self.mqtt_client.subscribe(topic, callback1)
        self.mqtt_client.subscribe(topic, callback2)
        
        # 取消其中一個
        self.mqtt_client.unsubscribe(topic, callback1)
        
        self.assertNotIn(callback1, self.mqtt_client._topic_callbacks[topic])
        self.assertIn(callback2, self.mqtt_client._topic_callbacks[topic])

    def test_unsubscribe_all_callbacks(self):
        """測試取消所有回調訂閱"""
        callback = Mock()
        topic = 'test/topic'
        
        self.mqtt_client.subscribe(topic, callback)
        self.mqtt_client.unsubscribe(topic)
        
        self.assertNotIn(topic, self.mqtt_client._topic_callbacks)

    def test_publish_success(self):
        """測試成功發布訊息"""
        self.mqtt_client._connected = True
        
        # 模擬成功發布
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        self.mock_mqtt_client_instance.publish.return_value = mock_result
        
        topic = 'test/topic'
        payload = {'test': 'data'}
        
        self.mqtt_client.publish(topic, payload)
        
        self.mock_mqtt_client_instance.publish.assert_called_once_with(
            topic, json.dumps(payload), qos=0, retain=False
        )
        mock_logger.info.assert_called_with(f"Published message to {topic}")

    def test_publish_string_payload(self):
        """測試發布字符串訊息"""
        self.mqtt_client._connected = True
        
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        self.mock_mqtt_client_instance.publish.return_value = mock_result
        
        topic = 'test/topic'
        payload = 'string message'
        
        self.mqtt_client.publish(topic, payload)
        
        self.mock_mqtt_client_instance.publish.assert_called_once_with(
            topic, payload, qos=0, retain=False
        )

    def test_publish_not_connected(self):
        """測試未連接時發布訊息"""
        self.mqtt_client._connected = False
        
        with self.assertRaises(ConnectionError) as context:
            self.mqtt_client.publish('test/topic', 'test')
        
        self.assertIn("Not connected to MQTT Broker", str(context.exception))

    def test_publish_error(self):
        """測試發布錯誤"""
        self.mqtt_client._connected = True
        
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        self.mock_mqtt_client_instance.publish.return_value = mock_result
        
        with self.assertRaises(ConnectionError) as context:
            self.mqtt_client.publish('test/topic', 'test')
        
        self.assertIn("MQTT publish error", str(context.exception))

    def test_publish_command_success(self):
        """測試成功發布命令"""
        self.mqtt_client._connected = True
        
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        self.mock_mqtt_client_instance.publish.return_value = mock_result
        
        machine_code = 'VM001'
        command = 'restart'
        parameters = {'force': True}
        
        result = self.mqtt_client.publish_command(machine_code, command, parameters)
        
        self.assertTrue(result)
        
        # 驗證發布的主題和內容
        expected_topic = f'machine/{machine_code}/command'
        call_args = self.mock_mqtt_client_instance.publish.call_args
        
        self.assertEqual(call_args[0][0], expected_topic)  # topic
        
        # 驗證payload內容
        payload = json.loads(call_args[0][1])
        self.assertEqual(payload['command'], command)
        self.assertEqual(payload['parameters'], parameters)
        self.assertIn('timestamp', payload)

    def test_publish_command_failure(self):
        """測試發布命令失敗"""
        self.mqtt_client._connected = False
        
        result = self.mqtt_client.publish_command('VM001', 'restart')
        
        self.assertFalse(result)
        mock_logger.error.assert_called()

    def test_get_connection_status(self):
        """測試獲取連接狀態"""
        self.mqtt_client._connected = True
        self.mqtt_client._topic_callbacks = {'test/topic': [Mock()]}
        
        status = self.mqtt_client.get_connection_status()
        
        expected_status = {
            "connected": True,
            "broker": "localhost",
            "port": 1883,
            "client_id": "smartcater_admin_frontend",
            "subscribed_topics": ['test/topic']
        }
        
        self.assertEqual(status, expected_status)

    def test_get_subscribed_topics(self):
        """測試獲取訂閱主題列表"""
        topics = ['topic1', 'topic2', 'topic3']
        for topic in topics:
            self.mqtt_client._topic_callbacks[topic] = [Mock()]
        
        result = self.mqtt_client.get_subscribed_topics()
        
        self.assertEqual(set(result), set(topics))

    def test_connect_success(self):
        """測試成功連接"""
        async def run_test():
            # 模擬連接成功
            def mock_connect_success(*args):
                self.mqtt_client._connected = True
            
            self.mock_mqtt_client_instance.connect.side_effect = mock_connect_success
            
            with patch('asyncio.sleep'):
                await self.mqtt_client.connect()
            
            self.assertTrue(self.mqtt_client._running)
            self.assertTrue(self.mqtt_client._connected)
        
        # 運行異步測試
        asyncio.run(run_test())

    def test_connect_timeout(self):
        """測試連接超時"""
        async def run_test():
            # 模擬連接超時（不設置_connected為True）
            with patch('asyncio.sleep'):
                with self.assertRaises(ConnectionError) as context:
                    await self.mqtt_client.connect()
                
                self.assertIn("MQTT connection timeout", str(context.exception))
        
        # 運行異步測試
        asyncio.run(run_test())

    def test_disconnect(self):
        """測試斷開連接"""
        async def run_test():
            self.mqtt_client._connected = True
            self.mqtt_client._running = True
            
            await self.mqtt_client.disconnect()
            
            self.assertFalse(self.mqtt_client._running)
            self.assertFalse(self.mqtt_client._connected)
            self.mock_mqtt_client_instance.disconnect.assert_called_once()
            self.mock_mqtt_client_instance.loop_stop.assert_called_once()
        
        # 運行異步測試
        asyncio.run(run_test())


class TestInitializeMQTTClient(unittest.TestCase):
    """測試初始化函數"""

    @patch('mqtt_client.client.MQTTClient')
    def test_initialize_mqtt_client(self, mock_mqtt_client_class):
        """測試初始化函數"""
        mock_instance = Mock()
        mock_mqtt_client_class.return_value = mock_instance
        
        result = initialize_mqtt_client()
        
        mock_mqtt_client_class.assert_called_once()
        self.assertEqual(result, mock_instance)


class TestIntegration(unittest.TestCase):
    """整合測試"""

    def setUp(self):
        """測試前置設定"""
        mock_st.session_state.clear()
        mock_st.session_state['mqtt_messages'] = []
        mock_logger.reset_mock()

    @patch('mqtt_client.client.mqtt.Client')
    def test_full_workflow(self, mock_mqtt_client):
        """測試完整工作流程"""
        # 建立mock客戶端
        mock_instance = Mock()
        mock_mqtt_client.return_value = mock_instance
        
        # 建立MQTT客戶端
        client = MQTTClient()
        
        # 測試訂閱
        callback = Mock()
        client.subscribe('test/topic', callback)
        
        # 模擬連接成功
        client._on_connect(None, None, None, 0)
        
        # 驗證重新訂閱
        mock_instance.subscribe.assert_called_with('test/topic')
        
        # 模擬接收訊息
        mock_msg = Mock()
        mock_msg.topic = 'test/topic'
        mock_msg.payload = b'{"test": "data"}'
        
        client._on_message(None, None, mock_msg)
        
        # 驗證回調被呼叫
        callback.assert_called_once_with('test/topic', {"test": "data"})
        
        # 驗證訊息被緩存
        self.assertEqual(len(mock_st.session_state['mqtt_messages']), 1)


if __name__ == '__main__':
    # 設定測試環境變數
    os.environ.setdefault('MQTT_BROKER_HOST', 'localhost')
    os.environ.setdefault('MQTT_BROKER_PORT', '1883')
    
    # 執行測試
    unittest.main(verbosity=2)
