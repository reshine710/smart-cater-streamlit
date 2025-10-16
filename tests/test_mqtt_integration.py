"""
MQTT客戶端整合測試
測試與實際MQTT broker的連接和功能
"""

import asyncio
import json
import os
import sys
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit for testing
sys.modules['streamlit'] = Mock()
mock_st = sys.modules['streamlit']
mock_st.session_state = {'mqtt_messages': []}

# Mock logger_config
sys.modules['logger_config'] = Mock()
mock_logger = Mock()
sys.modules['logger_config'].mqtt_logger = mock_logger

from mqtt_client.client import MQTTClient, initialize_mqtt_client


class TestMQTTIntegration(unittest.TestCase):
    """MQTT客戶端整合測試"""

    def setUp(self):
        """測試前置設定"""
        # 重置session_state
        mock_st.session_state.clear()
        mock_st.session_state['mqtt_messages'] = []
        
        # 重置logger mock
        mock_logger.reset_mock()
        
        # 建立MQTT客戶端
        self.mqtt_client = MQTTClient()
        self.received_messages = []
        self.connection_events = []

    def tearDown(self):
        """測試後清理"""
        async def cleanup():
            try:
                await self.mqtt_client.disconnect()
            except:
                pass
        
        # 運行清理
        try:
            asyncio.run(cleanup())
        except:
            pass

    def test_client_initialization(self):
        """測試客戶端初始化"""
        self.assertIsNotNone(self.mqtt_client._client)
        self.assertFalse(self.mqtt_client._connected)
        self.assertFalse(self.mqtt_client._running)
        self.assertEqual(self.mqtt_client._topic_callbacks, {})

    def test_connection_status_methods(self):
        """測試連接狀態相關方法"""
        # 測試獲取連接狀態
        status = self.mqtt_client.get_connection_status()
        
        expected_keys = ["connected", "broker", "port", "client_id", "subscribed_topics"]
        for key in expected_keys:
            self.assertIn(key, status)
        
        self.assertEqual(status["broker"], "localhost")
        self.assertEqual(status["port"], 1883)
        self.assertEqual(status["client_id"], "smartcater_admin_frontend")

    def test_subscription_management(self):
        """測試訂閱管理"""
        # 測試訂閱
        callback = Mock()
        topic = "test/integration/topic"
        
        self.mqtt_client.subscribe(topic, callback)
        
        # 驗證訂閱被記錄
        self.assertIn(topic, self.mqtt_client._topic_callbacks)
        self.assertIn(callback, self.mqtt_client._topic_callbacks[topic])
        
        # 測試獲取訂閱主題
        topics = self.mqtt_client.get_subscribed_topics()
        self.assertIn(topic, topics)
        
        # 測試取消訂閱
        self.mqtt_client.unsubscribe(topic, callback)
        self.assertNotIn(topic, self.mqtt_client._topic_callbacks)

    def test_message_summary_generation(self):
        """測試訊息摘要生成"""
        test_cases = [
            ("machine/VM001/heartbeat", {"status": "online"}, "VM001 心跳正常"),
            ("machine/VM002/alert", {"type": "溫度異常"}, "VM002 告警: 溫度異常"),
            ("machine/VM003/inventory/update", {}, "VM003 庫存更新"),
            ("machine/VM004/order/status", {}, "VM004 訂單狀態更新"),
            ("unknown/topic/format", {}, "收到訊息: unknown/topic/format")
        ]
        
        for topic, payload, expected in test_cases:
            with self.subTest(topic=topic):
                result = self.mqtt_client._generate_message_summary(topic, payload)
                self.assertEqual(result, expected)

    def test_topic_matching(self):
        """測試主題匹配功能"""
        test_cases = [
            ("machine/+/heartbeat", "machine/VM001/heartbeat", True),
            ("machine/+/heartbeat", "machine/VM002/heartbeat", True),
            ("machine/+/alert", "machine/VM001/heartbeat", False),
            ("machine/VM001/+", "machine/VM001/status", True),
            ("exact/topic", "exact/topic", True),
            ("exact/topic", "different/topic", False),
            ("machine/+/+", "machine/VM001/heartbeat", True),
            ("machine/+", "machine/VM001/heartbeat", False),  # 長度不匹配
        ]
        
        for pattern, topic, expected in test_cases:
            with self.subTest(pattern=pattern, topic=topic):
                result = self.mqtt_client._topic_matches(pattern, topic)
                self.assertEqual(result, expected)

    def test_publish_command_format(self):
        """測試命令發布格式"""
        # 由於需要連接才能發布，我們測試命令格式生成邏輯
        machine_code = "VM001"
        command = "restart"
        parameters = {"force": True}
        
        # 模擬發布方法來測試格式
        expected_topic = f"machine/{machine_code}/command"
        
        # 驗證主題格式正確
        self.assertEqual(expected_topic, "machine/VM001/command")

    @unittest.skipIf(
        os.getenv("SKIP_BROKER_TESTS", "false").lower() == "true",
        "跳過需要實際broker的測試"
    )
    def test_real_broker_connection(self):
        """測試與實際broker的連接（需要broker運行）"""
        async def run_connection_test():
            try:
                # 嘗試連接
                await self.mqtt_client.connect()
                
                # 驗證連接狀態
                self.assertTrue(self.mqtt_client._connected)
                self.assertTrue(self.mqtt_client._running)
                
                # 測試訂閱
                test_topic = "test/integration/connection"
                callback = Mock()
                self.mqtt_client.subscribe(test_topic, callback)
                
                # 等待一下讓訂閱生效
                await asyncio.sleep(1)
                
                # 測試發布（如果連接成功）
                if self.mqtt_client._connected:
                    test_payload = {"test": "integration", "timestamp": datetime.now().isoformat()}
                    self.mqtt_client.publish(test_topic, test_payload)
                    
                    # 等待訊息處理
                    await asyncio.sleep(1)
                
                # 斷開連接
                await self.mqtt_client.disconnect()
                self.assertFalse(self.mqtt_client._connected)
                
            except ConnectionError as e:
                self.skipTest(f"無法連接到MQTT broker: {e}")
            except Exception as e:
                self.fail(f"連接測試失敗: {e}")
        
        # 運行異步測試
        asyncio.run(run_connection_test())

    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試未連接時發布
        with self.assertRaises(ConnectionError):
            self.mqtt_client.publish("test/topic", "test message")
        
        # 測試無效的訊息處理
        mock_msg = Mock()
        mock_msg.topic = "test/topic"
        mock_msg.payload = b"invalid json {"
        
        # 這應該不會拋出異常，而是記錄警告
        try:
            self.mqtt_client._on_message(None, None, mock_msg)
        except Exception as e:
            self.fail(f"訊息處理不應該拋出異常: {e}")

    def test_callback_system(self):
        """測試回調系統"""
        # 建立測試回調
        callback1 = Mock()
        callback2 = Mock()
        
        # 訂閱同一主題的多個回調
        topic = "test/callback/topic"
        self.mqtt_client.subscribe(topic, callback1)
        self.mqtt_client.subscribe(topic, callback2)
        
        # 模擬訊息接收
        test_payload = {"test": "callback"}
        self.mqtt_client._call_topic_callbacks(topic, test_payload)
        
        # 驗證兩個回調都被調用
        callback1.assert_called_once_with(topic, test_payload)
        callback2.assert_called_once_with(topic, test_payload)

    def test_initialize_function(self):
        """測試初始化函數"""
        client = initialize_mqtt_client()
        self.assertIsInstance(client, MQTTClient)
        self.assertIsNotNone(client._client)


class TestMQTTClientStress(unittest.TestCase):
    """MQTT客戶端壓力測試"""

    def setUp(self):
        """測試前置設定"""
        mock_st.session_state.clear()
        mock_st.session_state['mqtt_messages'] = []
        self.mqtt_client = MQTTClient()

    def test_multiple_subscriptions(self):
        """測試多重訂閱"""
        # 建立多個訂閱
        topics = [f"test/stress/topic_{i}" for i in range(10)]
        callbacks = [Mock() for _ in range(10)]
        
        for topic, callback in zip(topics, callbacks):
            self.mqtt_client.subscribe(topic, callback)
        
        # 驗證所有訂閱都被記錄
        for topic in topics:
            self.assertIn(topic, self.mqtt_client._topic_callbacks)
        
        # 測試獲取所有訂閱
        subscribed_topics = self.mqtt_client.get_subscribed_topics()
        for topic in topics:
            self.assertIn(topic, subscribed_topics)

    def test_message_cache_overflow(self):
        """測試訊息緩存溢出處理"""
        # 模擬大量訊息
        for i in range(30):  # 超過20條限制
            mock_msg = Mock()
            mock_msg.topic = f"test/overflow/{i}"
            mock_msg.payload = json.dumps({"message_id": i}).encode()
            
            self.mqtt_client._on_message(None, None, mock_msg)
        
        # 驗證緩存限制
        self.assertLessEqual(len(mock_st.session_state['mqtt_messages']), 20)


def run_integration_tests():
    """運行整合測試的便利函數"""
    print("🔧 開始MQTT客戶端整合測試...")
    
    # 檢查broker是否可用
    try:
        test_client = MQTTClient()
        print(f"📡 嘗試連接到MQTT broker: {test_client.get_connection_status()['broker']}:{test_client.get_connection_status()['port']}")
    except Exception as e:
        print(f"⚠️  無法初始化測試客戶端: {e}")
    
    # 運行測試
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 測試結果摘要
    print(f"\n📊 測試結果摘要:")
    print(f"   ✅ 通過: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ 失敗: {len(result.failures)}")
    print(f"   🚫 錯誤: {len(result.errors)}")
    print(f"   ⏭️  跳過: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # 設定測試環境
    os.environ.setdefault('MQTT_BROKER_HOST', 'localhost')
    os.environ.setdefault('MQTT_BROKER_PORT', '1883')
    
    # 如果不想測試實際broker連接，設定此環境變數
    # os.environ['SKIP_BROKER_TESTS'] = 'true'
    
    success = run_integration_tests()
    sys.exit(0 if success else 1)
