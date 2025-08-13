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
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件 handler - 所有日誌
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        LOGS_DIR / f"app_{today}.log", 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 錯誤文件 handler - 只記錄錯誤
    error_handler = logging.FileHandler(
        LOGS_DIR / f"error_{today}.log", 
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
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
mqtt_logger = get_logger("mqtt")
ui_logger = get_logger("ui")
system_logger = get_logger("system")
