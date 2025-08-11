import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# API 配置
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

class VendingMachineAPI:
    """API 呼叫類別 - 目前使用假資料，後續可替換為真實 API"""
    
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    def login(self, username: str, password: str) -> Dict:
        """使用者登入 - 目前返回假 token"""
        # 模擬 API 呼叫
        if username == "admin" and password == "admin123":
            return {
                "access_token": "fake_token_12345",
                "token_type": "bearer"
            }
        return None
    
    def get_machines(self) -> List[Dict]:
        """獲取機台列表 - 假資料"""
        return [
            {
                "id": 1,
                "machine_code": "VM001",
                "name": "台北101店",
                "location": "台北市信義區",
                "status": "online",
                "temperature": 24.5,
                "last_heartbeat": "2025-08-03T22:50:00Z"
            },
            {
                "id": 2,
                "machine_code": "VM002",
                "name": "西門町店",
                "location": "台北市萬華區",
                "status": "maintenance",
                "temperature": 26.1,
                "last_heartbeat": "2025-08-03T22:48:00Z"
            },
            {
                "id": 3,
                "machine_code": "VM003",
                "name": "板橋車站店",
                "location": "新北市板橋區",
                "status": "offline",
                "temperature": None,
                "last_heartbeat": "2025-08-03T20:15:00Z"
            }
        ]
    
    def get_menu_items(self) -> List[Dict]:
        """獲取菜單項目 - 假資料"""
        return [
            {
                "id": 1,
                "name": "黑咖啡",
                "price": 50.0,
                "category": "飲品",
                "cooking_method": "蒸氣",
                "is_active": True,
                "image_url": "https://example.com/coffee.jpg"
            },
            {
                "id": 2,
                "name": "拿鐵咖啡",
                "price": 75.0,
                "category": "飲品",
                "cooking_method": "蒸氣",
                "is_active": True,
                "image_url": "https://example.com/latte.jpg"
            },
            {
                "id": 3,
                "name": "雞肉便當",
                "price": 120.0,
                "category": "主食",
                "cooking_method": "微波",
                "is_active": True,
                "image_url": "https://example.com/chicken.jpg"
            },
            {
                "id": 4,
                "name": "牛肉麵",
                "price": 150.0,
                "category": "主食",
                "cooking_method": "蒸氣",
                "is_active": False,
                "image_url": "https://example.com/beef.jpg"
            }
        ]
    
    def get_sales_data(self, start_date: str, end_date: str) -> List[Dict]:
        """獲取銷售資料 - 假資料"""
        # 生成假的銷售資料
        sales_data = []
        for i in range(50):
            sales_data.append({
                "transaction_id": f"T20250803{i:04d}",
                "machine_id": f"VM{(i % 3) + 1:03d}",
                "item_name": ["黑咖啡", "拿鐵咖啡", "雞肉便當"][i % 3],
                "quantity": np.random.randint(1, 4),
                "price": [50, 75, 120][i % 3],
                "timestamp": (datetime.now() - timedelta(hours=np.random.randint(0, 72))).isoformat(),
                "weather": np.random.choice(["晴", "陰", "雨"]),
                "temperature": np.random.uniform(20, 30)
            })
        return sales_data

def init_session_state():
    """初始化 session state"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'api' not in st.session_state:
        st.session_state.api = VendingMachineAPI(API_BASE_URL)
