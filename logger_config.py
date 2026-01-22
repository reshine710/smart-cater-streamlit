"""
Logging 配置模組
提供統一的 logging 設定和格式化
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# 創建 logs 目錄
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class WebSocketErrorFilter(logging.Filter):
    """
    過濾器：抑制 Streamlit/Tornado WebSocket 關閉時的無害錯誤
    
    這些錯誤通常在應用關閉時發生，是因為 WebSocket 連接已關閉
    但仍有異步任務試圖寫入消息。這些錯誤不會影響應用功能。
    """
    
    def filter(self, record):
        # 檢查是否為 WebSocket 相關的錯誤
        message = record.getMessage()
        
        # 過濾 WebSocket 關閉錯誤
        websocket_error_patterns = [
            "WebSocketClosedError",
            "Stream is closed",
            "Task exception was never retrieved",
            "WebSocketProtocol13.write_message",
        ]
        
        for pattern in websocket_error_patterns:
            if pattern in message:
                return False  # 過濾掉此日誌
        
        return True  # 保留其他日誌

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    設置 logger
    
    Args:
        name: logger 名稱
        level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # 創建格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # 創建 WebSocket 錯誤過濾器
    websocket_filter = WebSocketErrorFilter()
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(websocket_filter)  # 應用過濾器
    logger.addHandler(console_handler)
    
    # 文件 handler - 所有日誌
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        LOGS_DIR / f"app_{today}.log", 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(websocket_filter)  # 應用過濾器
    logger.addHandler(file_handler)
    
    # 錯誤文件 handler - 只記錄錯誤
    error_handler = logging.FileHandler(
        LOGS_DIR / f"error_{today}.log", 
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(websocket_filter)  # 應用過濾器
    logger.addHandler(error_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    獲取 logger 實例
    
    Args:
        name: logger 名稱
    
    Returns:
        logging.Logger: logger 實例
    """
    return setup_logger(name)

# 預設 logger 實例
api_logger = get_logger("api")
auth_logger = get_logger("auth") 

ui_logger = get_logger("ui")
system_logger = get_logger("system")

# 配置 Tornado 相關 logger，避免顯示 WebSocket 關閉錯誤
# 設置 Tornado logger 的級別為 WARNING，過濾掉 INFO 和 DEBUG 級別的無害錯誤
tornado_logger = logging.getLogger("tornado")
tornado_logger.setLevel(logging.WARNING)

tornado_access_logger = logging.getLogger("tornado.access")
tornado_access_logger.setLevel(logging.WARNING)

tornado_application_logger = logging.getLogger("tornado.application")
tornado_application_logger.setLevel(logging.WARNING)

tornado_general_logger = logging.getLogger("tornado.general")
tornado_general_logger.setLevel(logging.WARNING)

# 為根 logger 的 stderr handler 添加過濾器（捕獲未處理的異常）
root_logger = logging.getLogger()
websocket_filter = WebSocketErrorFilter()

# 為所有現有的 handler 添加過濾器
for handler in root_logger.handlers:
    handler.addFilter(websocket_filter)
