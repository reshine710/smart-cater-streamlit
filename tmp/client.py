"""
MQTT 客戶端服務
負責處理與前台販賣機之間的即時通訊
"""

import asyncio
import json
import logging
import os
import ssl
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from paho.mqtt.client import MQTTv5

# 載入環境變數
load_dotenv()

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mqtt_client")

# 從環境變數獲取 MQTT 配置
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "smartcater_backend")


class MQTTClient:
    """
    MQTT 客戶端類別
    處理與 MQTT Broker 的連接和通訊
    """

    def __init__(self):
        """
        初始化 MQTT 客戶端
        """
        # 創建唯一的客戶端ID
        import uuid

        unique_client_id = f"{MQTT_CLIENT_ID}_{uuid.uuid4().hex[:8]}"

        # 創建 MQTT 客戶端
        self.client = mqtt.Client(
            client_id=unique_client_id,
            protocol=MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        # 設置 keep alive 和其他連接參數
        self.client.keepalive = 60  # 60秒心跳間隔
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)

        # 設置事件回調
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish

        # 設置用戶名密碼
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        # 啟用 TLS
        if MQTT_USE_TLS:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        # 存儲訂閱回調
        self._topic_callbacks: Dict[str, List[Callable]] = {}

        # 追蹤已訂閱的主題（避免重複訂閱）
        self._subscribed_topics: set = set()

        # 重連控制
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 1  # 秒
        self._last_disconnect_time = None

        # 異步事件迴圈
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果沒有運行中的事件迴圈，創建一個新的
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        # 連接狀態
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        連接成功回調
        """
        if rc == 0:
            logger.info(
                f"Connected to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}"
            )
            self._connected = True
            # 重置重連計數器
            self._reconnect_attempts = 0

            # 重新訂閱所有主題（僅在重新連接時需要）
            if self._topic_callbacks and not self._subscribed_topics:
                logger.info(
                    f"Resubscribing to {len(self._topic_callbacks)} "
                    + "topics after reconnection"
                )
                for topic in self._topic_callbacks:
                    logger.debug(f"Resubscribing to topic: {topic}")
                    self.client.subscribe(topic)
                    self._subscribed_topics.add(topic)
            elif self._topic_callbacks and self._subscribed_topics:
                logger.debug("Topics already subscribed, skipping resubscription")
        else:
            logger.error(f"Failed to connect to MQTT Broker. Return code: {rc}")
            self._connected = False

    def _on_disconnect(self, client, userdata, rc, reason_code=None, properties=None):
        """
        斷開連接回調
        """
        import time

        current_time = time.time()

        # 記錄斷開時間
        self._last_disconnect_time = current_time

        logger.info(f"Disconnected from MQTT Broker with code: {rc}")
        self._connected = False
        # 清除已訂閱主題記錄，因為連接已斷開
        self._subscribed_topics.clear()

        # 只在非正常斷開時才重連（rc != 0 表示非正常斷開）
        if rc != 0 and self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            # 使用指數退避算法增加重連延遲
            delay = min(
                self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)), 30
            )

            logger.info(
                "Attempting to reconnect... "
                + f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
                + f"in {delay} seconds"
            )
            try:
                time.sleep(delay)  # 延遲重連
                self.client.reconnect()
            except Exception as e:
                logger.error(
                    f"Reconnection attempt {self._reconnect_attempts} failed: {e}"
                )
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.error("Maximum reconnection attempts reached. Giving up.")
        elif rc != 0:
            logger.error("Maximum reconnection attempts reached. Connection abandoned.")
        else:
            logger.info("Normal disconnection, no reconnection needed.")

    def _on_message(self, client, userdata, msg):
        """
        接收訊息回調
        """
        logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")

        # 解析 JSON 訊息
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message on topic {msg.topic}")
            payload = msg.payload.decode()

        # 調用相應主題的回調函數
        for topic, callbacks in self._topic_callbacks.items():
            if mqtt.topic_matches_sub(topic, msg.topic):
                for callback in callbacks:
                    try:
                        # 如果回調是協程函數，則在事件迴圈中運行
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(msg.topic, payload))
                        else:
                            callback(msg.topic, payload)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")

    def _on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """
        訂閱成功回調
        """
        logger.debug(f"Subscribed with QoS: {granted_qos}")  # 改為 debug 級別

    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """
        發布訊息回調
        """
        logger.debug(f"Message published: {mid}")

    async def connect(self):
        """
        連接到 MQTT Broker
        """
        if self._connected:
            return

        # 在背景執行緒中連接到 Broker
        self.client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

        # 啟動背景執行緒
        self.client.loop_start()

        # 等待連接完成
        for _ in range(10):  # 最多等待 5 秒
            if self._connected:
                break
            await asyncio.sleep(0.5)

        if not self._connected:
            logger.error("Failed to connect to MQTT Broker in time")
            raise ConnectionError("MQTT connection timeout")

    async def disconnect(self):
        """
        斷開與 MQTT Broker 的連接
        """
        if self._connected:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False

    def is_connected(self) -> bool:
        """
        檢查是否已連接到 MQTT Broker

        Returns:
            bool: 連接狀態
        """
        return self._connected and self.client.is_connected()

    def subscribe(self, topic: str, callback: Callable[[str, Any], None]):
        """
        訂閱主題
        Args:
            topic: 要訂閱的主題
            callback: 接收訊息時的回調函數
        """
        # 初始化主題回調列表
        if topic not in self._topic_callbacks:
            self._topic_callbacks[topic] = []

        # 檢查回調是否已經存在，避免重複添加
        if callback not in self._topic_callbacks[topic]:
            self._topic_callbacks[topic].append(callback)
            logger.info(f"Added callback for topic: {topic}")
        else:
            logger.debug(f"Callback already exists for topic: {topic}, skipping")
            return  # 如果回調已存在，直接返回

        # 只有在尚未訂閱該主題時才進行 MQTT 訂閱
        if topic not in self._subscribed_topics and self._connected:
            self.client.subscribe(topic)
            self._subscribed_topics.add(topic)
            logger.info(f"Subscribed to MQTT topic: {topic}")
        elif topic not in self._subscribed_topics:
            logger.debug(f"Topic {topic} will be subscribed when connected")

    def unsubscribe(self, topic: str, callback: Optional[Callable] = None):
        """
        取消訂閱主題
        Args:
            topic: 要取消訂閱的主題
            callback: 要移除的回調函數，如果為 None，則移除所有回調
        """
        if topic in self._topic_callbacks:
            if callback:
                if callback in self._topic_callbacks[topic]:
                    self._topic_callbacks[topic].remove(callback)
                    logger.info(f"Removed callback from topic: {topic}")

                # 如果沒有更多回調，取消訂閱主題
                if not self._topic_callbacks[topic]:
                    if self._connected:
                        self.client.unsubscribe(topic)
                    self._subscribed_topics.discard(topic)
                    del self._topic_callbacks[topic]
                    logger.info(f"Unsubscribed from topic: {topic}")
            else:
                # 移除所有回調並取消訂閱
                if self._connected:
                    self.client.unsubscribe(topic)
                self._subscribed_topics.discard(topic)
                del self._topic_callbacks[topic]
                logger.info(f"Unsubscribed from topic: {topic}")

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False):
        """
        發布訊息到指定主題
        Args:
            topic: 要發布到的主題
            payload: 訊息內容，如果不是字符串，會被轉換為 JSON
            qos: 服務質量 (0, 1, 2)
            retain: 是否保留訊息
        """
        if not self._connected:
            logger.error("Not connected to MQTT Broker")
            raise ConnectionError("Not connected to MQTT Broker")

        # 轉換 payload 為 JSON 字符串
        if not isinstance(payload, str):
            try:
                payload = json.dumps(payload)
            except Exception as e:
                logger.error(f"Error serializing payload to JSON: {e}")
                raise

        # 發布訊息
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"Failed to publish message to {topic}. Error code: {result.rc}"
            )
            raise ConnectionError(f"MQTT publish error: {result.rc}")

        logger.debug(f"Published message to {topic}: {payload}")

    def publish_machine_status(self, machine_code: str, status: Dict[str, Any]):
        """
        發布機台狀態
        Args:
            machine_code: 機台編號
            status: 狀態資訊
        """
        topic = f"machine/{machine_code}/status"
        self.publish(topic, status)

    def publish_menu_update(self, machine_code: str, menu_data: Dict[str, Any]):
        """
        發布菜單更新
        Args:
            machine_code: 機台編號
            menu_data: 菜單資料
        """
        topic = f"machine/{machine_code}/menu/update"
        self.publish(topic, menu_data)

    def publish_command(
        self, machine_code: str, command: str, parameters: Dict[str, Any] = None
    ):
        """
        發布命令到機台
        Args:
            machine_code: 機台編號
            command: 命令名稱
            parameters: 命令參數
        """
        topic = f"machine/{machine_code}/command"
        payload = {
            "command": command,
            "timestamp": datetime.utcnow().isoformat(),
            "parameters": parameters or {},
        }
        self.publish(topic, payload, qos=1)  # 使用 QoS 1 確保命令送達


# 單例模式
mqtt_client = MQTTClient()


# 全局初始化標記
_mqtt_initialized = False


async def initialize_mqtt_client():
    """
    初始化並啟動 MQTT 客戶端
    Returns:
        MQTTClient 實例
    """
    global _mqtt_initialized

    # 避免重複初始化
    if _mqtt_initialized and mqtt_client.is_connected():
        logger.info("MQTT client already initialized and connected")
        return mqtt_client

    try:
        await mqtt_client.connect()

        # 等待連接完成
        import asyncio

        await asyncio.sleep(1)  # 等待 1 秒讓連接完成

        # 只在首次初始化時訂閱系統主題
        if not _mqtt_initialized:
            logger.info("Setting up system topic subscriptions...")
            mqtt_client.subscribe("machine/+/heartbeat", on_machine_heartbeat)
            mqtt_client.subscribe("machine/+/alert", on_machine_alert)
            mqtt_client.subscribe("machine/+/inventory/update", on_inventory_update)
            mqtt_client.subscribe("machine/+/order/status", on_order_status_update)
            mqtt_client.subscribe("machine/+/menu/update", on_menu_update)
            _mqtt_initialized = True

        logger.info("MQTT client initialized and connected")
        logger.info(f"MQTT client connected status: {mqtt_client._connected}")
        logger.info(f"Subscribed topics: {list(mqtt_client._subscribed_topics)}")
    except ConnectionError as e:
        logger.error(f"Failed to initialize MQTT client: {e}")
        raise

    return mqtt_client


def on_menu_update(topic: str, payload: Any):
    """
    處理菜單更新
    Args:
        topic: 主題
        payload: 菜單更新資料
    """
    logger.info(f"Received menu update: {topic} - {payload}")


# 預定義的主題處理函數
def on_machine_heartbeat(topic: str, payload: Any):
    """
    處理機台心跳
    Args:
        topic: 主題
        payload: 心跳資料
    """
    try:
        machine_code = topic.split("/")[1]
        logger.info(f"Received heartbeat from machine {machine_code}: {payload}")

        # 更新機台狀態，記錄最後在線時間
        try:
            from smartcaterbackend.core.services.machine_service import MachineService
            from smartcaterbackend.data.database import get_db

            # 獲取資料庫會話
            db = next(get_db())
            machine_service = MachineService()

            # 解析機台代碼
            machine_code = topic.split("/")[1]

            # 更新機台最後在線時間
            machine_service.update_machine_last_seen(db, machine_code)

            logger.info(f"Updated last seen time for machine {machine_code}")

        except Exception as e:
            logger.error(f"Failed to update machine status: {e}")

    except Exception as e:
        logger.error(f"Error processing machine heartbeat: {e}")


def on_machine_alert(topic: str, payload: Any):
    """
    處理機台告警
    Args:
        topic: 主題
        payload: 告警資料
    """
    try:
        machine_code = topic.split("/")[1]
        logger.info(f"Received alert from machine {machine_code}: {payload}")

        # 創建告警記錄，並觸發通知
        try:
            from smartcaterbackend.data.database import get_db
            from smartcaterbackend.data.schemas import Alert, AlertLevel, AlertType

            # 獲取資料庫會話
            db = next(get_db())

            # 解析機台代碼
            machine_code = topic.split("/")[1]

            # 查找機台
            from smartcaterbackend.core.services.machine_service import MachineService

            machine_service = MachineService()
            machine = machine_service.get_machine_by_code(db, machine_code)

            if not machine:
                logger.warning(f"Machine with code {machine_code} not found for alert")
                return

            # 解析告警資料
            import json

            alert_data = json.loads(payload) if isinstance(payload, str) else payload

            # 創建告警記錄
            alert = Alert(
                machine_id=machine.id,
                alert_type=AlertType.SYSTEM_ERROR,  # 預設類型，可根據 payload 調整
                level=AlertLevel.HIGH,  # 預設級別，可根據 payload 調整
                title=alert_data.get("title", "系統告警"),
                message=alert_data.get("message", str(payload)),
                is_resolved=False,
                resolved_at=None,
                resolved_by=None,
            )

            # 保存到數據庫
            db.add(alert)
            db.commit()

            logger.info(
                f"Created alert record for machine {machine_code}: {alert.title}"
            )

            # TODO: 這裡可以添加通知邏輯，如發送郵件、簡訊等

        except Exception as e:
            logger.error(f"Failed to create alert record: {e}")

    except Exception as e:
        logger.error(f"Error processing machine alert: {e}")


def on_inventory_update(topic: str, payload: Any):
    """
    處理庫存更新
    Args:
        topic: 主題
        payload: 庫存資料
    """
    try:
        machine_code = topic.split("/")[1]
        logger.info(f"Received inventory update from machine {machine_code}: {payload}")

        # 更新庫存資料
        try:
            from smartcaterbackend.core.models import InventoryStockUpdate
            from smartcaterbackend.core.services.inventory_service import (
                InventoryService,
            )
            from smartcaterbackend.data.database import get_db

            # 獲取資料庫會話
            db = next(get_db())
            inventory_service = InventoryService()

            # 解析機台代碼
            machine_code = topic.split("/")[1]

            # 解析庫存更新資料
            import json

            inventory_data = (
                json.loads(payload) if isinstance(payload, str) else payload
            )

            # 查找機台
            from smartcaterbackend.core.services.machine_service import MachineService

            machine_service = MachineService()
            machine = machine_service.get_machine_by_code(db, machine_code)

            if not machine:
                logger.warning(
                    f"Machine with code {machine_code} not found for inventory update"
                )
                return

            # 處理庫存更新
            for item_update in inventory_data.get("items", []):
                menu_item_id = item_update.get("menu_item_id")
                quantity_change = item_update.get("quantity_change", 0)
                operation_type = item_update.get("operation_type", "mqtt_update")
                notes = item_update.get("notes", "MQTT 庫存更新")

                if menu_item_id and quantity_change != 0:
                    # 創建庫存更新對象
                    stock_update = InventoryStockUpdate(
                        quantity_change=quantity_change,
                        operation_type=operation_type,
                        notes=notes,
                    )

                    # 更新庫存
                    inventory_service.update_inventory_stock(
                        db, machine.id, menu_item_id, stock_update
                    )

                    logger.info(
                        f"Updated inventory for machine {machine_code}, "
                        f"item {menu_item_id}, change: {quantity_change}"
                    )

        except Exception as e:
            logger.error(f"Failed to update inventory: {e}")

    except Exception as e:
        logger.error(f"Error processing inventory update: {e}")


def on_order_status_update(topic: str, payload: Any):
    """
    處理訂單狀態更新
    Args:
        topic: 主題
        payload: 訂單狀態資料
    """
    try:
        machine_code = topic.split("/")[1]
        logger.info(
            f"Received order status update from machine {machine_code}: {payload}"
        )

        # 更新訂單狀態
        try:
            from smartcaterbackend.core.models import OrderStatusEnum, PaymentStatusEnum
            from smartcaterbackend.core.services.order_service import OrderService
            from smartcaterbackend.data.database import get_db

            # 獲取資料庫會話
            db = next(get_db())
            order_service = OrderService()

            # 解析機台代碼
            machine_code = topic.split("/")[1]

            # 解析訂單狀態更新資料
            import json

            order_data = json.loads(payload) if isinstance(payload, str) else payload

            # 查找機台
            from smartcaterbackend.core.services.machine_service import MachineService

            machine_service = MachineService()
            machine = machine_service.get_machine_by_code(db, machine_code)

            if not machine:
                logger.warning(
                    f"Machine with code {machine_code} not found for order update"
                )
                return

            # 處理訂單狀態更新
            order_id = order_data.get("order_id")
            new_status = order_data.get("status")
            payment_status = order_data.get("payment_status")

            if order_id and new_status:
                # 轉換狀態枚舉
                try:
                    order_status = OrderStatusEnum(new_status)
                    payment_status_enum = (
                        PaymentStatusEnum(payment_status) if payment_status else None
                    )

                    # 更新訂單狀態
                    updated_order = order_service.update_order_status(
                        db, order_id, order_status, payment_status_enum
                    )

                    if updated_order:
                        logger.info(
                            f"Updated order {order_id} status to {new_status} "
                            f"for machine {machine_code}"
                        )
                    else:
                        logger.warning(f"Failed to update order {order_id}")

                except ValueError as e:
                    logger.error(f"Invalid order status: {e}")

        except Exception as e:
            logger.error(f"Failed to update order status: {e}")

    except Exception as e:
        logger.error(f"Error processing order status update: {e}")


# 啟動 MQTT 服務的入口函數
def start_mqtt_service():
    """
    啟動 MQTT 服務
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize_mqtt_client())
    logger.info("MQTT service started")

    # 這個函數可以從應用程式的主入口點調用

    return mqtt_client
