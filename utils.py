import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# API 配置
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# 系統狀態變數
class SystemStatus:
    ONLINE = "online"
    OFFLINE = "offline"
    DATABASE_ERROR = "database_error"

class VendingMachineAPI:
    """API 呼叫類別 - 目前使用假資料，後續可替換為真實 API"""
    
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    def login(self, username: str, password: str) -> Dict:
        """使用者登入"""
        try:
            # 準備登入資料
            login_data = {
                "username": username,
                "password": password
            }
            
            # 發送登入請求
            response = requests.post(
                f"{self.base_url}/users/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # 獲取使用者資訊，傳遞 username 以便離線模式使用
                user_info = self.get_current_user(token_data["access_token"], username)
                
                # 調試：檢查 API 返回的資料
                print(f"API Debug - Token received, User Info: {user_info.get('username', 'Unknown')}, is_admin: {user_info.get('is_admin', False)}")
                
                return {
                    "access_token": token_data["access_token"],
                    "token_type": token_data["token_type"],
                    "user_info": user_info
                }
            elif response.status_code == 500:
                # 伺服器內部錯誤，可能是資料庫問題
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，使用離線模式")
                # 回退到離線模式
                return self._offline_login(username, password)
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤，使用離線模式
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，使用離線模式: {str(e)}")
            return self._offline_login(username, password)
    
    def _offline_login(self, username: str, password: str) -> Dict:
        """離線模式登入"""
        # 預設測試帳號
        if username in ["testadmin", "admin"] and password in ["testpassword", "admin123"]:
            return {
                "access_token": "offline_admin_token",
                "token_type": "bearer",
                "user_info": {
                    "id": 1,
                    "username": username,
                    "email": f"{username}@example.com",
                    "full_name": "Test Admin (Offline)",
                    "is_active": True,
                    "is_admin": True,
                    "created_at": datetime.now().isoformat()
                }
            }
        elif username == "testuser" and password == "testpassword":
            return {
                "access_token": "offline_user_token",
                "token_type": "bearer",
                "user_info": {
                    "id": 2,
                    "username": username,
                    "email": f"{username}@example.com",
                    "full_name": "Test User (Offline)",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": datetime.now().isoformat()
                }
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
    
    def register(self, username: str, email: str, password: str, full_name: str, is_admin: bool = False) -> bool:
        """使用者註冊"""
        try:
            # 準備註冊資料
            user_data = {
                "username": username,
                "email": email,
                "password": password,
                "full_name": full_name,
                "is_active": True,
                "is_admin": is_admin
            }
            
            # 發送註冊請求
            response = requests.post(
                f"{self.base_url}/users/",
                json=user_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            elif response.status_code == 500:
                # 伺服器內部錯誤
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法註冊新使用者")
                return False
            else:
                return False
            
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，註冊功能暫時不可用: {str(e)}")
            return False
    
    def get_current_user(self, token: str, username: str = None) -> Dict:
        """獲取當前使用者資訊"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # 確保返回的資料不是空的
                if user_data and isinstance(user_data, dict):
                    return user_data
                else:
                    # API 返回空資料，使用離線模式
                    return self._get_offline_user_info(token)
            elif response.status_code == 500:
                # 伺服器內部錯誤，使用離線資料
                return self._get_offline_user_info(token, username)
            else:
                # 其他錯誤，使用離線資料
                return self._get_offline_user_info(token, username)
                
        except requests.exceptions.RequestException:
            # 網路連接錯誤，使用離線資料
            return self._get_offline_user_info(token, username)
    
    def _get_offline_user_info(self, token: str, username: str = None) -> Dict:
        """獲取離線模式使用者資訊"""
        # 優先使用傳入的 username，否則檢查 session state
        import streamlit as st
        if not username:
            username = st.session_state.get('username', '')
        
        print(f"Offline Debug - Passed username: {username}, Token: {token[:20]}...")
        
        # 根據用戶名判斷是否為管理員
        # 支援你資料庫中的管理員帳號：testadmin 和 admin
        if username in ["testadmin", "admin"] or "admin" in token:
            user_data = {
                "id": 1 if username == "testadmin" else 3,  # 根據實際資料庫 ID
                "username": username or "testadmin",
                "email": f"{username or 'testadmin'}@example.com",
                "full_name": "Test Admin (Offline)" if username == "testadmin" else "Jimmy Shen (Offline)",
                "is_active": True,
                "is_admin": True,
                "created_at": datetime.now().isoformat()
            }
            print(f"Offline Debug - Returning ADMIN data: {user_data}")
            return user_data
        else:
            user_data = {
                "id": 2,
                "username": username or "testuser",
                "email": f"{username or 'testuser'}@example.com",
                "full_name": f"Test User (Offline)",
                "is_active": True,
                "is_admin": False,
                "created_at": datetime.now().isoformat()
            }
            print(f"Offline Debug - Returning USER data: {user_data}")
            return user_data
    
    def get_users(self) -> List[Dict]:
        """獲取所有使用者列表（僅管理員可用）"""
        try:
            response = requests.get(
                f"{self.base_url}/users/",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 500:
                # 伺服器內部錯誤，返回離線資料
                import streamlit as st
                st.warning("⚠️ 伺服器資料庫未初始化，顯示模擬資料")
                return self._get_offline_users()
            else:
                return []
                
        except requests.exceptions.RequestException:
            # 網路連接錯誤，返回模擬資料
            return self._get_offline_users()
    
    def _get_offline_users(self) -> List[Dict]:
        """獲取離線模式使用者列表"""
        return [
            {
                "id": 1,
                "username": "testadmin",
                "email": "testadmin@example.com",
                "full_name": "Test Admin (Offline)",
                "is_active": True,
                "is_admin": True,
                "created_at": "2025-08-13T10:00:00Z"
            },
            {
                "id": 2,
                "username": "testuser",
                "email": "testuser@example.com",
                "full_name": "Test User (Offline)",
                "is_active": True,
                "is_admin": False,
                "created_at": "2025-08-13T11:00:00Z"
            },
            {
                "id": 3,
                "username": "demouser",
                "email": "demo@example.com",
                "full_name": "Demo User (Offline)",
                "is_active": True,
                "is_admin": False,
                "created_at": "2025-08-13T12:00:00Z"
            }
        ]

def init_session_state():
    """初始化 session state"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'api' not in st.session_state:
        st.session_state.api = VendingMachineAPI(API_BASE_URL)
