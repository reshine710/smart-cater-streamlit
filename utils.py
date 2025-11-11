import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from logger_config import api_logger, auth_logger, system_logger
from config import settings

# API 配置 - 從配置文件讀取
API_BASE_URL = settings.get("API_URL", "http://127.0.0.1:8000/api/v1")
# 備用 URL: "https://scb-api-954587932054.asia-east1.run.app/api/v1"

# 系統狀態變數
class SystemStatus:
    ONLINE = "online"
    OFFLINE = "offline"
    DATABASE_ERROR = "database_error"

class VendingMachineAPI:
    """API 呼叫類別"""
    
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        
        api_logger.info(f"VendingMachineAPI initialized with base_url: {base_url}, has_token: {bool(token)}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """獲取認證標頭"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def login(self, username: str, password: str) -> Dict:
        """使用者登入"""
        auth_logger.info(f"Login attempt for username: {username}")
        try:
            # 準備登入資料
            login_data = {
                "username": username,
                "password": password
            }
            
            # 發送登入請求
            auth_logger.debug(f"Sending login request to {self.base_url}/users/token")
            response = requests.post(
                f"{self.base_url}/users/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            auth_logger.debug(f"Login API response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                
                # 更新 API 客戶端的 token
                self.token = token_data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"
                
                # 獲取使用者資訊，傳遞 username 以便離線模式使用
                user_info = self.get_current_user(token_data["access_token"], username)
                
                # 記錄登入成功資訊
                auth_logger.info(f"Login successful - User: {user_info.get('username', 'Unknown')}, is_admin: {user_info.get('is_admin', False)}, user_id: {user_info.get('id', 'N/A')}")
                auth_logger.debug(f"Token received, full user info: {user_info}")
                
                return {
                    "access_token": token_data["access_token"],
                    "token_type": token_data["token_type"],
                    "user_info": user_info
                }
            elif response.status_code == 500:
                # 伺服器內部錯誤，可能是資料庫問題
                auth_logger.warning(f"Server error (500) during login for {username}, falling back to offline mode")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，使用離線模式")
                # 回退到離線模式
                return self._offline_login(username, password)
            else:
                auth_logger.warning(f"Login failed for {username} - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤，使用離線模式
            auth_logger.error(f"Network error during login for {username}: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，使用離線模式: {str(e)}")
            return self._offline_login(username, password)
    
    def _offline_login(self, username: str, password: str) -> Dict:
        """離線模式登入"""
        auth_logger.info(f"Attempting offline login for username: {username}")
        # 預設測試帳號
        if username in ["testadmin", "admin"] and password in ["testpassword", "admin123"]:
            auth_logger.info(f"Offline admin login successful for {username}")
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
            auth_logger.info(f"Offline user login successful for {username}")
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
        auth_logger.warning(f"Offline login failed for {username} - invalid credentials")
        return None
    
    def get_machines(self) -> List[Dict]:
        """獲取機台列表"""
        api_logger.debug("Fetching machine list from API")
        try:
            response = requests.get(
                f"{self.base_url}/machines",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                api_logger.debug(f"Raw API response: {response_data}")
                
                # 檢查是否為分頁格式 {'items': [...], 'total': N}
                if isinstance(response_data, dict) and 'items' in response_data:
                    machines_data = response_data['items']
                    api_logger.info(f"Successfully retrieved {len(machines_data)} machines from paginated API response")
                else:
                    # 直接返回機台列表
                    machines_data = response_data
                    api_logger.info(f"Successfully retrieved {len(machines_data)} machines from API")
                
                api_logger.debug(f"Machines data: {machines_data}")
                return machines_data
            elif response.status_code == 401:
                api_logger.warning("Unauthorized access to machines API")
                import streamlit as st
                st.error("❌ 未授權存取，請重新登入")
                return []
            elif response.status_code == 500:
                # 伺服器內部錯誤
                api_logger.warning("Server error (500) getting machines list")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return []
            else:
                api_logger.warning(f"Failed to get machines list - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            api_logger.error(f"Network error getting machines list: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return []
    
    
    def get_machine_detail(self, machine_id: int) -> Dict:
        """獲取機台詳細資訊"""
        api_logger.debug(f"Fetching machine detail for ID: {machine_id}")
        try:
            response = requests.get(
                f"{self.base_url}/machines/{machine_id}",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                machine_data = response.json()
                api_logger.info(f"Successfully retrieved machine detail for ID: {machine_id}")
                return machine_data
            elif response.status_code == 404:
                api_logger.warning(f"Machine not found for ID: {machine_id}")
                return {}
            elif response.status_code == 401:
                api_logger.warning("Unauthorized access to machine detail API")
                import streamlit as st
                st.error("❌ 未授權存取，請重新登入")
                return {}
            else:
                api_logger.warning(f"Failed to get machine detail - Status code: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting machine detail: {str(e)}")
            return {}
    
    def update_machine_status(self, machine_id: int, status: str) -> bool:
        """更新機台狀態"""
        api_logger.debug(f"Updating machine {machine_id} status to: {status}")
        try:
            response = requests.post(
                f"{self.base_url}/machines/{machine_id}/status",
                headers=self._get_auth_headers(),
                json={"status": status},
                timeout=10
            )
            
            if response.status_code == 200:
                api_logger.info(f"Successfully updated machine {machine_id} status to {status}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Machine not found for ID: {machine_id}")
                return False
            elif response.status_code == 401:
                api_logger.warning("Unauthorized access to machine status update API")
                import streamlit as st
                st.error("❌ 未授權存取，請重新登入")
                return False
            else:
                api_logger.warning(f"Failed to update machine status - Status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error updating machine status: {str(e)}")
            return False
    
    def record_machine_heartbeat(self, machine_id: int) -> bool:
        """記錄機台心跳"""
        api_logger.debug(f"Recording heartbeat for machine ID: {machine_id}")
        try:
            response = requests.post(
                f"{self.base_url}/machines/{machine_id}/heartbeat",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                api_logger.info(f"Successfully recorded heartbeat for machine {machine_id}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Machine not found for ID: {machine_id}")
                return False
            else:
                api_logger.warning(f"Failed to record heartbeat - Status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error recording heartbeat: {str(e)}")
            return False
    
    def create_machine(self, machine_data: Dict) -> Dict:
        """建立新機台"""
        api_logger.debug(f"Creating new machine: {machine_data.get('machine_code', 'Unknown')}")
        try:
            response = requests.post(
                f"{self.base_url}/machines",
                headers=self._get_auth_headers(),
                json=machine_data,
                timeout=10
            )
            
            if response.status_code == 201:
                created_machine = response.json()
                api_logger.info(f"Successfully created machine: {created_machine.get('machine_code', 'Unknown')}")
                import streamlit as st
                st.success(f"✅ 機台 {created_machine.get('name', '未知')} 創建成功！")
                return created_machine
            elif response.status_code == 400:
                api_logger.warning(f"Bad request creating machine - validation error")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', '資料驗證失敗')
                    st.error(f"❌ 創建機台失敗：{error_detail}")
                except:
                    st.error("❌ 創建機台失敗：資料格式不正確")
                return {}
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to machine creation API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可創建機台")
                return {}
            elif response.status_code == 409:
                api_logger.warning("Machine code conflict - already exists")
                import streamlit as st
                st.error("❌ 機台代碼已存在，請使用不同的代碼")
                return {}
            elif response.status_code == 422:
                api_logger.warning("Validation error creating machine")
                import streamlit as st
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, dict) and 'detail' in error_detail:
                        # FastAPI 驗證錯誤格式
                        if isinstance(error_detail['detail'], list):
                            error_messages = []
                            for error in error_detail['detail']:
                                field = ' -> '.join(str(x) for x in error.get('loc', []))
                                msg = error.get('msg', '驗證失敗')
                                error_messages.append(f"{field}: {msg}")
                            st.error(f"❌ 資料驗證失敗：\n" + "\n".join(error_messages))
                        else:
                            st.error(f"❌ 資料驗證失敗：{error_detail['detail']}")
                    else:
                        st.error(f"❌ 資料驗證失敗：{error_detail}")
                    api_logger.debug(f"Validation error details: {error_detail}")
                except:
                    st.error("❌ 資料驗證失敗，請檢查輸入格式")
                return {}
            elif response.status_code == 500:
                api_logger.warning("Server error creating machine")
                import streamlit as st
                st.error("❌ 伺服器內部錯誤，無法創建機台")
                return {}
            else:
                api_logger.warning(f"Failed to create machine - Status code: {response.status_code}")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', f'狀態碼: {response.status_code}')
                    st.error(f"❌ 創建機台失敗：{error_detail}")
                except:
                    st.error(f"❌ 創建機台失敗 - 狀態碼: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error creating machine: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法創建機台: {str(e)}")
            return {}
    
    def update_machine(self, machine_id: int, machine_data: Dict) -> bool:
        """更新機台資訊"""
        api_logger.info(f"🔄 開始更新機台 {machine_id} 資訊")
        api_logger.info(f"📋 更新數據: {machine_data}")
        
        try:
            # 記錄完整的API調用資訊
            api_logger.info(f"📡 API調用: PUT {self.base_url}/machines/{machine_id}")
            api_logger.info(f"📦 Request Headers: {self._get_auth_headers()}")
            api_logger.info(f"📦 Request Body: {machine_data}")
            
            response = requests.put(
                f"{self.base_url}/machines/{machine_id}",
                headers=self._get_auth_headers(),
                json=machine_data,
                timeout=10
            )
            
            # 記錄回應詳情
            api_logger.info(f"📊 Response Status Code: {response.status_code}")
            api_logger.info(f"📊 Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                api_logger.info(f"📊 Response Body: {response_json}")
            except:
                api_logger.info(f"📊 Response Text: {response.text}")
            
            if response.status_code == 200:
                api_logger.info(f"✅ 成功更新機台 {machine_id} 資訊")
                import streamlit as st
                st.success(f"✅ 機台 {machine_id} 資訊已更新")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"❌ 機台 {machine_id} 不存在")
                import streamlit as st
                st.error(f"❌ 機台 {machine_id} 不存在")
                return False
            elif response.status_code == 401:
                api_logger.warning("❌ 權限不足：無法更新機台資訊")
                import streamlit as st
                st.error("❌ 未授權存取，請重新登入")
                return False
            else:
                api_logger.warning(f"❌ 更新機台資訊失敗 - 狀態碼: {response.status_code}")
                api_logger.warning(f"📊 Error Response: {response.text}")
                import streamlit as st
                st.error(f"❌ 更新機台資訊失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error updating machine: {str(e)}")
            return False

    def delete_machine(self, machine_id: int) -> bool:
        """刪除機台"""
        api_logger.debug(f"Deleting machine ID: {machine_id}")
        try:
            response = requests.delete(
                f"{self.base_url}/machines/{machine_id}",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                api_logger.info(f"Successfully deleted machine {machine_id}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Machine not found for ID: {machine_id}")
                import streamlit as st
                st.error("❌ 機台不存在")
                return False
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to machine deletion API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可刪除機台")
                return False
            elif response.status_code == 500:
                # 處理伺服器內部錯誤，通常是資料庫約束問題
                api_logger.warning(f"Server error deleting machine {machine_id} - likely foreign key constraint")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', '')
                    if 'foreign key' in error_detail.lower() or 'constraint' in error_detail.lower() or 'orders' in error_detail.lower():
                        st.error("❌ 無法刪除機台：此機台仍有相關訂單記錄。請先處理或刪除相關訂單後再試。")
                    else:
                        st.error(f"❌ 伺服器內部錯誤，無法刪除機台")
                except:
                    st.error("❌ 無法刪除機台：此機台可能仍有相關的訂單或庫存記錄。請先清理相關數據後再試。")
                return False
            else:
                api_logger.warning(f"Failed to delete machine - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 刪除機台失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error deleting machine: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法刪除機台: {str(e)}")
            return False
    
    def get_menu_items(self) -> List[Dict]:
        """獲取菜單項目列表"""
        api_logger.info("Fetching menu items from API")
        try:
            response = requests.get(
                f"{self.base_url}/menu-items",
                headers=self._get_auth_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                api_logger.info(f"Successfully fetched {len(items)} menu items")
                # 確保每個項目都有必要的字段
                for item in items:
                    if 'heating_params' not in item:
                        item['heating_params'] = None
                    if 'heating_time' not in item:
                        # 從 heating_params 中提取或設置默認值
                        item['heating_time'] = self._extract_heating_time(item.get('heating_params'))
                return items
            else:
                api_logger.error(f"Failed to fetch menu items: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            api_logger.error(f"Error fetching menu items: {str(e)}")
            return []
    
    def _extract_heating_time(self, heating_params) -> int:
        """從 heating_params 中提取加熱時間"""
        if not heating_params:
            return 0
        if isinstance(heating_params, dict):
            return heating_params.get('time_seconds', 0)
        return 0
    
    
    def create_menu_item(self, item_data: Dict) -> Dict:
        """建立新菜單項目"""
        api_logger.info(f"Creating menu item: {item_data.get('name', 'Unknown')}")
        try:
            response = requests.post(
                f"{self.base_url}/menu-items",
                json=item_data,
                headers=self._get_auth_headers(),
                timeout=10
            )
            api_logger.debug(f"Create menu item API response status: {response.status_code}")
            
            if response.status_code in [200, 201]: 
                api_logger.info(f"Menu item created successfully: {item_data.get('name')}")
                return response.json()
            elif response.status_code == 500:
                api_logger.error(f"Server error (500) creating menu item: {item_data.get('name')}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法創建菜單項目")
                return None
            else:
                api_logger.warning(f"Failed to create menu item - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error creating menu item: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，創建功能暫時不可用: {str(e)}")
            return None
    
    def update_menu_item(self, item_id: int, item_data: Dict) -> Dict:
        """更新菜單項目"""
        api_logger.info(f"Updating menu item {item_id}")
        try:
            response = requests.put(
                f"{self.base_url}/menu-items/{item_id}",
                json=item_data,
                headers=self._get_auth_headers(),
                timeout=10
            )
            api_logger.debug(f"Update menu item API response status: {response.status_code}")
            
            if response.status_code == 200:
                api_logger.info(f"Menu item updated successfully: ID {item_id}")
                return response.json()
            elif response.status_code == 500:
                api_logger.error(f"Server error (500) updating menu item ID: {item_id}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法更新菜單項目")
                return None
            else:
                api_logger.warning(f"Failed to update menu item - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error updating menu item: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，更新功能暫時不可用: {str(e)}")
            return None
    
    def activate_menu_item(self, item_id: int) -> Dict:
        """啟用菜單項目"""
        api_logger.info(f"Activating menu item {item_id}")
        try:
            response = requests.post(
                f"{self.base_url}/menu-items/{item_id}/activate",
                headers=self._get_auth_headers(),
                timeout=10
            )
            api_logger.debug(f"Activate menu item API response status: {response.status_code}")
            
            if response.status_code == 200:
                api_logger.info(f"Menu item activated successfully: ID {item_id}")
                return response.json()
            elif response.status_code == 500:
                api_logger.error(f"Server error (500) activating menu item ID: {item_id}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法啟用菜單項目")
                return None
            else:
                api_logger.warning(f"Failed to activate menu item - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error activating menu item: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，啟用功能暫時不可用: {str(e)}")
            return None
    
    def deactivate_menu_item(self, item_id: int) -> Dict:
        """停用菜單項目"""
        api_logger.info(f"Deactivating menu item {item_id}")
        try:
            response = requests.post(
                f"{self.base_url}/menu-items/{item_id}/deactivate",
                headers=self._get_auth_headers(),
                timeout=10
            )
            api_logger.debug(f"Deactivate menu item API response status: {response.status_code}")
            
            if response.status_code == 200:
                api_logger.info(f"Menu item deactivated successfully: ID {item_id}")
                return response.json()
            elif response.status_code == 500:
                api_logger.error(f"Server error (500) deactivating menu item ID: {item_id}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法停用菜單項目")
                return None
            else:
                api_logger.warning(f"Failed to deactivate menu item - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error deactivating menu item: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，停用功能暫時不可用: {str(e)}")
            return None
    
    def update_menu_item_tags(self, item_id: int, tags: List[str]) -> Dict:
        """更新菜單項目標籤"""
        api_logger.info(f"Updating tags for menu item {item_id}: {tags}")
        try:
            response = requests.post(
                f"{self.base_url}/menu-items/{item_id}/tags",
                json={"tags": tags},
                headers=self._get_auth_headers(),
                timeout=10
            )
            api_logger.debug(f"Update menu item tags API response status: {response.status_code}")
            
            if response.status_code == 200:
                api_logger.info(f"Menu item tags updated successfully: ID {item_id}")
                return response.json()
            elif response.status_code == 500:
                api_logger.error(f"Server error (500) updating menu item tags ID: {item_id}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法更新標籤")
                return None
            else:
                api_logger.warning(f"Failed to update menu item tags - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error updating menu item tags: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，標籤更新功能暫時不可用: {str(e)}")
            return None
    
    def get_menu_item_detail(self, item_id: int) -> Dict:
        """獲取菜單項目詳細資訊"""
        api_logger.info(f"Fetching menu item detail for ID: {item_id}")
        try:
            response = requests.get(
                f"{self.base_url}/menu-items/{item_id}",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                item_data = response.json()
                api_logger.info(f"Menu item detail fetched successfully: ID {item_id}")
                return item_data
            elif response.status_code == 404:
                api_logger.warning(f"Menu item not found: ID {item_id}")
                return None
            elif response.status_code == 500:
                api_logger.warning(f"Server error (500) getting menu item detail")
                return None
            else:
                api_logger.warning(f"Failed to get menu item detail - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting menu item detail: {str(e)}")
            return None
    
    def get_sales_data(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """獲取銷售資料"""
        api_logger.debug(f"Fetching sales data from API (start_date={start_date}, end_date={end_date})")
        try:
            # 構建查詢參數
            params = {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = requests.get(
                f"{self.base_url}/sales",
                headers=self._get_auth_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                api_logger.debug(f"Raw sales API response: {response_data}")
                
                # 檢查是否為分頁格式 {'items': [...], 'total': N}
                if isinstance(response_data, dict) and 'items' in response_data:
                    sales_data = response_data['items']
                elif isinstance(response_data, list):
                    sales_data = response_data
                else:
                    sales_data = []
                
                api_logger.info(f"Successfully retrieved {len(sales_data)} sales records from API")
                return sales_data
            elif response.status_code == 500:
                # 伺服器內部錯誤
                api_logger.warning("Server error (500) getting sales data")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return []
            else:
                api_logger.warning(f"Failed to get sales data - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            api_logger.error(f"Network error getting sales data: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return []
        except Exception as e:
            api_logger.error(f"Unexpected error getting sales data: {str(e)}")
            return []

    
    def get_orders(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """獲取訂單列表"""
        api_logger.debug(f"Fetching orders list from API (skip={skip}, limit={limit})")
        try:
            response = requests.get(
                f"{self.base_url}/orders",
                params={"skip": skip, "limit": limit},
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                api_logger.debug(f"Raw orders API response: {response_data}")
                
                # 檢查是否為分頁格式 {'items': [...], 'total': N}
                if isinstance(response_data, dict) and 'items' in response_data:
                    orders = response_data['items']
                    api_logger.info(f"Successfully retrieved {len(orders)} orders from paginated API response")
                    return orders
                elif isinstance(response_data, list):
                    # 直接返回訂單列表
                    api_logger.info(f"Successfully retrieved {len(response_data)} orders from API")
                    return response_data
                else:
                    api_logger.warning(f"Unexpected API response format: {type(response_data)}")
                    return []
            elif response.status_code == 500:
                # 伺服器內部錯誤
                api_logger.warning("Server error (500) getting orders list")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return []
            else:
                api_logger.warning(f"Failed to get orders list - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            api_logger.error(f"Network error getting orders list: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return []

    def get_orders_with_details(self, skip: int = 0, limit: int = 100, 
                                machine_id: int = None, order_status: str = None) -> Dict:
        """獲取訂單列表（帶詳細資訊和分頁）"""
        api_logger.debug(f"Fetching orders with details (skip={skip}, limit={limit}, machine_id={machine_id}, status={order_status})")
        try:
            params = {"skip": skip, "limit": limit}
            if machine_id:
                params["machine_id"] = machine_id
            if order_status:
                params["order_status"] = order_status
            
            response = requests.get(
                f"{self.base_url}/orders",
                params=params,
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                api_logger.info(f"Successfully retrieved orders with details")
                return response_data
            elif response.status_code == 500:
                api_logger.warning("Server error (500) getting orders with details")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return {"total": 0, "items": []}
            else:
                api_logger.warning(f"Failed to get orders - Status code: {response.status_code}")
                return {"total": 0, "items": []}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting orders with details: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return {"total": 0, "items": []}

    def get_order_by_id(self, order_id: int) -> Dict:
        """根據訂單ID查詢單筆訂單"""
        api_logger.debug(f"Fetching order by ID: {order_id}")
        try:
            response = requests.get(
                f"{self.base_url}/orders/{order_id}",
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                order = response.json()
                api_logger.info(f"Successfully retrieved order ID: {order_id}")
                return order
            elif response.status_code == 404:
                api_logger.warning(f"Order not found: {order_id}")
                return None
            else:
                api_logger.warning(f"Failed to get order - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting order by ID: {str(e)}")
            return None

    def get_order_by_number(self, order_number: str) -> Dict:
        """根據訂單編號查詢訂單"""
        api_logger.debug(f"Fetching order by number: {order_number}")
        try:
            response = requests.get(
                f"{self.base_url}/orders/number/{order_number}",
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                order = response.json()
                api_logger.info(f"Successfully retrieved order number: {order_number}")
                return order
            elif response.status_code == 404:
                api_logger.warning(f"Order not found: {order_number}")
                return None
            else:
                api_logger.warning(f"Failed to get order - Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting order by number: {str(e)}")
            return None

    def get_orders_by_machine_id(self, machine_id: int) -> List[Dict]:
        """查詢特定機台的所有訂單"""
        api_logger.debug(f"Fetching orders for machine ID: {machine_id}")
        try:
            response = requests.get(
                f"{self.base_url}/orders/machine/{machine_id}",
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                orders = response.json()
                api_logger.info(f"Successfully retrieved {len(orders)} orders for machine {machine_id}")
                return orders
            elif response.status_code == 404:
                api_logger.warning(f"Machine not found or no orders: {machine_id}")
                return []
            else:
                api_logger.warning(f"Failed to get orders - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting orders by machine ID: {str(e)}")
            return []

    def get_orders_by_date_range(self, start_date: str, end_date: str, 
                                 machine_id: str = None, limit: int = 100) -> Dict:
        """按日期範圍查詢訂單（使用 AI API）"""
        api_logger.debug(f"Fetching orders by date range: {start_date} to {end_date}")
        try:
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "page": 1,
                "limit": limit
            }
            if machine_id:
                params["machine_id"] = str(machine_id)
            
            response = requests.get(
                f"{self.base_url}/ai/transactional-data",
                headers=self._get_ai_auth_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                api_logger.info(f"Successfully retrieved orders by date range")
                return result
            elif response.status_code == 400:
                error_detail = response.json().get('detail', 'Invalid request')
                api_logger.warning(f"Invalid date range request: {error_detail}")
                import streamlit as st
                st.error(f"❌ 查詢參數無效：{error_detail}")
                return {"data": [], "pagination": {}}
            else:
                api_logger.warning(f"Failed to get orders by date - Status code: {response.status_code}")
                return {"data": [], "pagination": {}}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting orders by date range: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return {"data": [], "pagination": {}}

    def register(self, username: str, email: str, password: str, full_name: str, is_admin: bool = False) -> bool:
        """使用者註冊"""
        auth_logger.info(f"Registration attempt for username: {username}, email: {email}, is_admin: {is_admin}")
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
            auth_logger.debug(f"Sending registration request to {self.base_url}/users/")
            response = requests.post(
                f"{self.base_url}/users/",
                json=user_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            auth_logger.debug(f"Registration API response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                auth_logger.info(f"Registration successful for username: {username}")
                return True
            elif response.status_code == 500:
                # 伺服器內部錯誤
                auth_logger.error(f"Server error (500) during registration for {username}")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化，無法註冊新使用者")
                return False
            else:
                auth_logger.warning(f"Registration failed for {username} - Status code: {response.status_code}")
                return False
            
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            auth_logger.error(f"Network error during registration for {username}: {str(e)}")
            import streamlit as st
            st.warning(f"🌐 無法連接到 API 伺服器，註冊功能暫時不可用: {str(e)}")
            return False
    
    def get_current_user(self, token: str, username: str = None) -> Dict:
        """獲取當前使用者資訊 - 優先使用 API，失敗時使用離線模式"""
        api_logger.info(f"Getting current user info for username: {username}")
        
        # 嘗試使用 API 獲取使用者資訊
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                api_logger.info(f"Successfully retrieved user info from API for user: {user_data.get('username', 'Unknown')}")
                auth_logger.debug(f"API user data: {user_data}")
                return user_data
            elif response.status_code == 401:
                # 未授權，token 可能已過期
                api_logger.warning("Unauthorized access to /users/me - token may be expired")
                auth_logger.warning("Token expired, falling back to offline mode")
                return self._get_offline_user_info(token, username)
            elif response.status_code == 500:
                # 伺服器內部錯誤
                api_logger.warning("Server error (500) getting current user info")
                auth_logger.warning("Server error, falling back to offline mode")
                return self._get_offline_user_info(token, username)
            else:
                # 其他 HTTP 錯誤
                api_logger.warning(f"Failed to get current user info - Status code: {response.status_code}")
                auth_logger.warning(f"API error {response.status_code}, falling back to offline mode")
                return self._get_offline_user_info(token, username)
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            api_logger.error(f"Network error getting current user info: {str(e)}")
            auth_logger.warning(f"Network error, falling back to offline mode: {str(e)}")
            return self._get_offline_user_info(token, username)
        except Exception as e:
            # 其他未預期的錯誤
            api_logger.error(f"Unexpected error getting current user info: {str(e)}")
            auth_logger.warning(f"Unexpected error, falling back to offline mode: {str(e)}")
            return self._get_offline_user_info(token, username)
    
    def _get_offline_user_info(self, token: str, username: str = None) -> Dict:
        """獲取離線模式使用者資訊 - 當 API 不可用時使用"""
        # 優先使用傳入的 username，否則檢查 session state
        import streamlit as st
        if not username:
            username = st.session_state.get('username', '')
        
        auth_logger.info(f"🔌 離線模式 - 使用本地使用者資訊，username: {username}")
        auth_logger.debug(f"Offline mode - username: {username}, token: {token[:20] if token else 'None'}...")
        
        # 根據用戶名判斷是否為管理員
        # 支援你資料庫中的管理員帳號：testadmin 和 admin
        if username in ["testadmin", "admin"]:
            user_data = {
                "id": 1 if username == "testadmin" else 3,  # 根據實際資料庫 ID
                "username": username or "testadmin",
                "email": f"{username or 'testadmin'}@example.com",
                "full_name": "Test Admin (離線模式)" if username == "testadmin" else "Jimmy Shen (離線模式)",
                "is_active": True,
                "is_admin": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "_offline_mode": True  # 標記這是離線模式
            }
            auth_logger.info(f"🔌 離線模式 - 返回管理員資料: {user_data['username']}")
            auth_logger.debug(f"Offline admin user data: {user_data}")
            return user_data
        else:
            user_data = {
                "id": 2,
                "username": username or "testuser",
                "email": f"{username or 'testuser'}@example.com",
                "full_name": f"Test User (離線模式)",
                "is_active": True,
                "is_admin": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "_offline_mode": True  # 標記這是離線模式
            }
            auth_logger.info(f"🔌 離線模式 - 返回一般使用者資料: {user_data['username']}")
            auth_logger.debug(f"Offline user data: {user_data}")
            return user_data
    
    def get_users(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """獲取所有使用者列表（僅管理員可用）"""
        api_logger.debug(f"Fetching users list (skip={skip}, limit={limit})")
        try:
            params = {"skip": skip, "limit": limit}
            response = requests.get(
                f"{self.base_url}/users/",
                headers=self._get_auth_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                users_data = response.json()
                api_logger.info(f"Successfully retrieved {len(users_data)} users from API")
                return users_data
            elif response.status_code == 500:
                # 伺服器內部錯誤
                api_logger.warning("Server error (500) getting users list")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return []
            else:
                api_logger.warning(f"Failed to get users list - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            # 網路連接錯誤
            api_logger.error(f"Network error getting users list: {str(e)}")
            return []
    
    def get_users_count(self) -> int:
        """獲取使用者總數（僅管理員可用）"""
        api_logger.debug("Fetching users count")
        try:
            response = requests.get(
                f"{self.base_url}/users/count",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                count_data = response.json()
                count = count_data.get('count', 0)
                api_logger.info(f"Successfully retrieved users count: {count}")
                return count
            elif response.status_code == 500:
                api_logger.warning("Server error (500) getting users count")
                return 0
            else:
                api_logger.warning(f"Failed to get users count - Status code: {response.status_code}")
                return 0
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting users count: {str(e)}")
            return 0
    

    def delete_menu_item(self, item_id: int) -> bool:
        """刪除菜單項目"""
        api_logger.debug(f"Deleting menu item ID: {item_id}")
        try:
            response = requests.delete(
                f"{self.base_url}/menu-items/{item_id}",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                api_logger.info(f"Successfully deleted menu item {item_id}")
                import streamlit as st
                st.success("✅ 菜單項目已成功刪除")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Menu item not found for ID: {item_id}")
                import streamlit as st
                st.error("❌ 菜單項目不存在")
                return False
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to menu item deletion API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可刪除菜單項目")
                return False
            elif response.status_code == 409:
                api_logger.warning("Cannot delete menu item - has related orders")
                import streamlit as st
                st.error("❌ 無法刪除菜單項目：此項目仍有相關訂單記錄。請先處理相關訂單後再試。")
                return False
            elif response.status_code == 500:
                api_logger.warning("Server error deleting menu item")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', '')
                    if 'foreign key' in error_detail.lower() or 'constraint' in error_detail.lower() or 'orders' in error_detail.lower():
                        st.error("❌ 無法刪除菜單項目：此項目仍有相關訂單記錄。請先處理相關訂單後再試。")
                    else:
                        st.error("❌ 伺服器內部錯誤，無法刪除菜單項目")
                except:
                    st.error("❌ 無法刪除菜單項目：此項目可能仍有相關的訂單記錄。請先清理相關數據後再試。")
                return False
            else:
                api_logger.warning(f"Failed to delete menu item - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 刪除菜單項目失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error deleting menu item: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法刪除菜單項目: {str(e)}")
            return False

    # AI 推薦系統相關方法
    def get_ai_health(self) -> dict:
        """檢查AI API健康狀態"""
        api_logger.debug("Checking AI API health")
        try:
            response = requests.get(
                f"{self.base_url}/ai/health",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                api_logger.warning(f"AI health check failed - Status code: {response.status_code}")
                return {"status": "error", "message": f"Health check failed: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error during AI health check: {str(e)}")
            return {"status": "error", "message": f"Network error: {str(e)}"}
        except Exception as e:
            api_logger.error(f"Unexpected error during AI health check: {str(e)}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

    def get_ai_recommendations(self, status_filter: str = None, machine_id: str = None, 
                             skip: int = 0, limit: int = 100) -> list:
        """獲取AI推薦列表"""
        api_logger.debug(f"Fetching AI recommendations with filters: status={status_filter}, machine_id={machine_id}")
        try:
            # 構建查詢參數
            params = {"skip": skip, "limit": limit}
            if status_filter:
                params["status_filter"] = status_filter
            if machine_id:
                params["machine_id"] = machine_id
            
            # 禁用緩存，確保獲取最新數據
            headers = {**self._get_ai_auth_headers(), 'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
            
            response = requests.get(
                f"{self.base_url}/ai/recommendations",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                api_logger.info(f"Successfully fetched {len(data.get('data', []))} AI recommendations")
                return data.get('data', [])
            elif response.status_code == 401:
                api_logger.warning("Unauthorized access to AI recommendations")
                import streamlit as st
                st.error("❌ 權限不足：無法存取AI推薦資料")
                return []
            else:
                api_logger.warning(f"Failed to fetch AI recommendations - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 獲取AI推薦失敗 - 狀態碼: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when fetching AI recommendations: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return []
        except Exception as e:
            api_logger.error(f"Unexpected error when fetching AI recommendations: {str(e)}")
            import streamlit as st
            st.error(f"❌ 獲取AI推薦時發生未預期的錯誤：{str(e)}")
            return []

    def create_ai_recommendation(self, recommendation_data: dict) -> bool:
        """創建AI推薦"""
        rec_id = recommendation_data.get('recommendation_id', 'Unknown')
        api_logger.info(f"🚀 開始創建AI推薦: {rec_id}")
        api_logger.info(f"📋 推薦類型: {recommendation_data.get('recommendation_type', 'Unknown')}")
        api_logger.info(f"🎯 目標機台: {recommendation_data.get('target_machine_ids', [])}")
        
        try:
            # 記錄完整的API調用資訊
            api_logger.info(f"📡 API調用: POST {self.base_url}/ai/recommendations")
            api_logger.info(f"📦 Request Headers: {self._get_ai_auth_headers()}")
            api_logger.info(f"📦 Request Body: {recommendation_data}")
            
            response = requests.post(
                f"{self.base_url}/ai/recommendations",
                headers=self._get_ai_auth_headers(),
                json=recommendation_data,
                timeout=10
            )
            
            # 記錄回應詳情
            api_logger.info(f"📊 Response Status Code: {response.status_code}")
            api_logger.info(f"📊 Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                api_logger.info(f"📊 Response Body: {response_json}")
            except:
                api_logger.info(f"📊 Response Text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                backend_ref_id = result.get('backend_ref_id', 'N/A')
                api_logger.info(f"✅ 成功創建AI推薦: {rec_id} (後端參考ID: {backend_ref_id})")
                import streamlit as st
                st.success(f"✅ AI推薦已成功創建 - 參考ID: {backend_ref_id}")
                return True
            elif response.status_code == 400:
                error_detail = response.json().get('detail', 'Unknown error')
                api_logger.warning(f"❌ 推薦資料無效: {error_detail}")
                api_logger.warning(f"📊 Error Response: {response.json()}")
                import streamlit as st
                st.error(f"❌ 推薦資料無效：{error_detail}")
                return False
            elif response.status_code == 401:
                api_logger.warning("❌ 權限不足：無法創建AI推薦")
                import streamlit as st
                st.error("❌ 權限不足：無法創建AI推薦")
                return False
            else:
                api_logger.warning(f"❌ 創建AI推薦失敗 - 狀態碼: {response.status_code}")
                api_logger.warning(f"📊 Error Response: {response.text}")
                import streamlit as st
                st.error(f"❌ 創建AI推薦失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"❌ 網路錯誤: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return False
        except Exception as e:
            api_logger.error(f"❌ 創建AI推薦時發生未預期的錯誤: {str(e)}")
            import streamlit as st
            st.error(f"❌ 創建AI推薦時發生未預期的錯誤：{str(e)}")
            return False

    def update_recommendation_status(self, recommendation_id: int, status: str, 
                                   review_notes: str = None, reviewer: str = None) -> bool:
        """更新推薦狀態（審核通過/拒絕）"""
        api_logger.debug(f"Updating recommendation {recommendation_id} status to {status}")
        try:
            # 使用傳入的 reviewer 或預設為 "admin"
            reviewer_name = reviewer or "admin"
            update_data = {
                "new_status": status,  # API 期望的欄位名稱是 new_status
                "reviewer": reviewer_name  # API 期望的欄位名稱是 reviewer
            }
            if review_notes:
                update_data["review_notes"] = review_notes
            
            response = requests.patch(
                f"{self.base_url}/ai/recommendations/{recommendation_id}",  
                headers=self._get_ai_auth_headers(),
                json=update_data,
                timeout=10
            )
            
            if response.status_code == 200:
                api_logger.info(f"Successfully updated recommendation {recommendation_id} status to {status}")
                import streamlit as st
                st.success(f"✅ 推薦狀態已更新為：{status}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Recommendation {recommendation_id} not found")
                import streamlit as st
                st.error("❌ 找不到指定的推薦")
                return False
            elif response.status_code == 401:
                api_logger.warning(f"Unauthorized to update recommendation {recommendation_id}")
                import streamlit as st
                st.error("❌ 權限不足：無法更新推薦狀態")
                return False
            elif response.status_code == 422:
                # 處理驗證錯誤
                try:
                    error_detail = response.json()
                    api_logger.warning(f"Validation error updating recommendation {recommendation_id}: {error_detail}")
                    import streamlit as st
                    st.error(f"❌ 資料驗證錯誤：{error_detail.get('detail', '未知錯誤')}")
                except:
                    api_logger.warning(f"422 error updating recommendation {recommendation_id}: {response.text}")
                    import streamlit as st
                    st.error("❌ 資料驗證錯誤，請檢查輸入資料")
                return False
            elif response.status_code == 500:
                # 處理伺服器內部錯誤
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get('detail', '伺服器內部錯誤')
                    api_logger.warning(f"Server error updating recommendation {recommendation_id}: {error_msg}")
                    import streamlit as st
                    if "missing 1 required positional argument: 'reviewer'" in error_msg:
                        st.error("❌ 後端 API 配置錯誤：缺少審核者參數。請聯繫系統管理員。")
                    else:
                        st.error(f"❌ 伺服器錯誤：{error_msg}")
                except:
                    api_logger.warning(f"500 error updating recommendation {recommendation_id}: {response.text}")
                    import streamlit as st
                    st.error("❌ 伺服器內部錯誤，請稍後再試或聯繫系統管理員")
                return False
            else:
                api_logger.warning(f"Failed to update recommendation status - Status code: {response.status_code}")
                try:
                    error_detail = response.json()
                    import streamlit as st
                    st.error(f"❌ 更新推薦狀態失敗 - 狀態碼: {response.status_code}, 錯誤: {error_detail}")
                except:
                    import streamlit as st
                    st.error(f"❌ 更新推薦狀態失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when updating recommendation status: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return False
        except Exception as e:
            api_logger.error(f"Unexpected error when updating recommendation status: {str(e)}")
            import streamlit as st
            st.error(f"❌ 更新推薦狀態時發生未預期的錯誤：{str(e)}")
            return False

    # 地點管理 API 方法
    def get_locations(self) -> List[Dict]:
        """獲取地點列表"""
        api_logger.debug("Fetching locations list")
        try:
            response = requests.get(
                f"{self.base_url}/locations",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                api_logger.debug(f"Raw locations API response: {response_data}")
                
                # 檢查是否為分頁格式 {'items': [...], 'total': N}
                if isinstance(response_data, dict) and 'items' in response_data:
                    locations_data = response_data['items']
                    api_logger.info(f"Successfully retrieved {len(locations_data)} locations from paginated API response")
                elif isinstance(response_data, list):
                    # 直接返回地點列表
                    locations_data = response_data
                    api_logger.info(f"Successfully retrieved {len(locations_data)} locations from API")
                else:
                    # 如果不是預期的格式，返回空列表
                    api_logger.warning(f"Unexpected API response format: {type(response_data)}")
                    locations_data = []
                
                api_logger.debug(f"Locations data: {locations_data}")
                return locations_data
            elif response.status_code == 500:
                api_logger.warning("Server error (500) getting locations list")
                import streamlit as st
                st.error("⚠️ 伺服器資料庫未初始化")
                return []
            else:
                api_logger.warning(f"Failed to get locations list - Status code: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error getting locations list: {str(e)}")
            import streamlit as st
            st.error(f"🌐 無法連接到 API 伺服器: {str(e)}")
            return []
    
    def create_location(self, location_data: Dict) -> Dict:
        """建立新地點"""
        api_logger.debug(f"Creating new location: {location_data.get('name', 'Unknown')}")
        try:
            response = requests.post(
                f"{self.base_url}/locations/",
                headers=self._get_auth_headers(),
                json=location_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                created_location = response.json()
                api_logger.info(f"Successfully created location: {created_location.get('name', 'Unknown')}")
                import streamlit as st
                st.success(f"✅ 地點 {created_location.get('name', '未知')} 創建成功！")
                return created_location
            elif response.status_code == 400:
                api_logger.warning(f"Bad request creating location - validation error")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', '資料驗證失敗')
                    st.error(f"❌ 創建地點失敗：{error_detail}")
                except:
                    st.error("❌ 創建地點失敗：資料格式不正確")
                return {}
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to location creation API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可創建地點")
                return {}
            else:
                api_logger.warning(f"Failed to create location - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 創建地點失敗 - 狀態碼: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error creating location: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法創建地點: {str(e)}")
            return {}

    def delete_location(self, location_id: int) -> bool:
        """刪除地點"""
        api_logger.debug(f"Deleting location ID: {location_id}")
        try:
            response = requests.delete(
                f"{self.base_url}/locations/{location_id}",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                api_logger.info(f"Successfully deleted location {location_id}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Location not found for ID: {location_id}")
                import streamlit as st
                st.error("❌ 地點不存在")
                return False
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to location deletion API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可刪除地點")
                return False
            elif response.status_code == 409:
                api_logger.warning("Cannot delete location - has related machines")
                import streamlit as st
                st.error("❌ 無法刪除地點：此地點仍有相關機台。請先處理相關機台後再試。")
                return False
            elif response.status_code == 500:
                api_logger.warning("Server error deleting location")
                import streamlit as st
                st.error("⚠️ 伺服器錯誤，請稍後再試")
                return False
            else:
                api_logger.warning(f"Failed to delete location - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 刪除地點失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error deleting location: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法刪除地點: {str(e)}")
            return False

    def update_location(self, location_id: int, update_data: Dict) -> bool:
        """更新地點資訊"""
        api_logger.debug(f"Updating location ID: {location_id}")
        try:
            response = requests.put(
                f"{self.base_url}/locations/{location_id}",
                headers=self._get_auth_headers(),
                json=update_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                api_logger.info(f"Successfully updated location {location_id}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"Location not found for ID: {location_id}")
                import streamlit as st
                st.error("❌ 地點不存在")
                return False
            elif response.status_code == 400:
                api_logger.warning(f"Bad request updating location - validation error")
                import streamlit as st
                try:
                    error_detail = response.json().get('detail', '資料驗證失敗')
                    st.error(f"❌ 更新地點失敗：{error_detail}")
                except:
                    st.error("❌ 更新地點失敗：資料格式不正確")
                return False
            elif response.status_code in [401, 403]:
                api_logger.warning("Unauthorized access to location update API")
                import streamlit as st
                st.error("❌ 權限不足，僅管理員可更新地點")
                return False
            elif response.status_code == 500:
                api_logger.warning("Server error updating location")
                import streamlit as st
                st.error("⚠️ 伺服器錯誤，請稍後再試")
                return False
            else:
                api_logger.warning(f"Failed to update location - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 更新地點失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error updating location: {str(e)}")
            import streamlit as st
            st.error(f"🌐 網路錯誤，無法更新地點: {str(e)}")
            return False

    def get_transactional_data(self, start_date: str, end_date: str, machine_id: str = None, 
                             limit: int = 100, skip: int = 0) -> List[Dict]:
        """獲取交易數據（AI分析用）"""
        api_logger.debug(f"Fetching transactional data from {start_date} to {end_date}")
        try:
            # 構建查詢參數
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "skip": skip
            }
            if machine_id:
                params["machine_id"] = machine_id
            
            response = requests.get(
                f"{self.base_url}/ai/transactional-data",
                headers=self._get_ai_auth_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                api_logger.info(f"Successfully fetched {len(data.get('data', []))} transactional records")
                return data.get('data', [])
            elif response.status_code == 400:
                error_detail = response.json().get('detail', 'Invalid request')
                api_logger.warning(f"Invalid transactional data request: {error_detail}")
                import streamlit as st
                st.error(f"❌ 查詢參數無效：{error_detail}")
                return []
            elif response.status_code == 401:
                api_logger.warning("Unauthorized access to transactional data")
                import streamlit as st
                st.error("❌ 權限不足：無法存取交易數據")
                return []
            elif response.status_code == 422:
                # 參數驗證錯誤 - 記錄詳細信息
                try:
                    error_detail = response.json()
                    api_logger.error(f"Validation error (422) for transactional data request:")
                    api_logger.error(f"  Request params: {params}")
                    api_logger.error(f"  Error detail: {error_detail}")
                    import streamlit as st
                    st.error(f"❌ 參數驗證錯誤：{error_detail}")
                except:
                    api_logger.error(f"422 error, raw response: {response.text}")
                    import streamlit as st
                    st.error(f"❌ 參數驗證錯誤 (422)")
                return []
            else:
                api_logger.warning(f"Failed to fetch transactional data - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 獲取交易數據失敗 - 狀態碼: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when fetching transactional data: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return []
        except Exception as e:
            api_logger.error(f"Unexpected error when fetching transactional data: {str(e)}")
            import streamlit as st
            st.error(f"❌ 獲取交易數據時發生未預期的錯誤：{str(e)}")
            return []

    def get_transactional_data_for_dashboard(self, start_date: str, end_date: str, 
                                             machine_id: str = None, limit: int = 1000) -> List[Dict]:
        """
        獲取適用於 Dashboard 的交易數據
        將 transactional-data API 的格式轉換為 Dashboard 需要的格式
        """
        api_logger.info(f"Fetching transactional data for dashboard: {start_date} to {end_date}")
        
        # 硬編碼映射表（備用方案）
        FALLBACK_MEAL_ID_MAP = {
            'A001': '早餐套餐',
            'A002': '午餐套餐A',
            'A003': '午餐套餐B',
            'A004': '午餐套餐C',
            'A005': '下午茶套餐',
            'A006': '晚餐套餐A',
            'A007': '晚餐套餐B',
            'A008': '雞塊套餐',
            'A009': '沙拉套餐',
            'A010': '飲料套餐',
            'A011': '魷魚套餐',
            'A012': '薯條套餐',
            'A013': '滷味三寶飯套餐',
            'A014': '便當套餐',
            'B001': '咖啡套餐',
            'B002': '茶飲套餐',
            'B003': '果汁套餐',
            'C001': '甜點套餐',
        }
        
        try:
            # 調用現有的 get_transactional_data 方法
            transactions = self.get_transactional_data(start_date, end_date, machine_id, limit)
            
            if not transactions:
                api_logger.warning("No transactional data returned from API")
                return []
            
            # 獲取菜單項目以便映射 meal_id 到 item_name
            menu_items = []
            try:
                menu_items = self.get_menu_items()
            except Exception as e:
                api_logger.warning(f"Failed to fetch menu items: {str(e)}")
            
            # 建立映射表（支援多種映射方式）
            menu_map = {}
            product_code_map = {}
            
            for item in menu_items:
                # ID 映射
                item_id = str(item.get('id', ''))
                if item_id:
                    menu_map[item_id] = item.get('name', 'Unknown')
                
                # product_code 映射
                product_code = str(item.get('product_code', ''))
                if product_code:
                    product_code_map[product_code] = item.get('name', 'Unknown')
            
            # 如果菜單為空，記錄警告
            if not menu_map and not product_code_map:
                api_logger.warning("Menu items not available, using meal_id as item name")
            
            # 轉換數據格式
            dashboard_data = []
            for tx in transactions:
                # 基本交易資訊
                tx_id = tx.get('transaction_id', 'Unknown')
                machine_id = tx.get('machine_id', 'Unknown')
                timestamp = tx.get('purchase_timestamp', '')
                context = tx.get('context', {})
                
                # 處理每個交易項目
                for detail in tx.get('transaction_details', []):
                    meal_id = str(detail.get('meal_id', 'Unknown'))
                    
                    # 多層映射策略
                    item_name = meal_id  # 預設使用 meal_id
                    
                    # 策略 1: 從 product_code 映射（優先，因為 meal_id 看起來是產品代碼）
                    if meal_id in product_code_map:
                        item_name = product_code_map[meal_id]
                    # 策略 2: 從 ID 映射
                    elif meal_id in menu_map:
                        item_name = menu_map[meal_id]
                    # 策略 3: 使用硬編碼映射表（備用）
                    elif meal_id in FALLBACK_MEAL_ID_MAP:
                        item_name = FALLBACK_MEAL_ID_MAP[meal_id]
                    
                    record = {
                        'timestamp': timestamp,
                        'created_at': timestamp,
                        'order_id': tx_id,
                        'transaction_id': tx_id,
                        'machine_id': str(machine_id),
                        'item_name': item_name,
                        'product_name': item_name,
                        'meal_id': meal_id,  # 保留原始 meal_id
                        'quantity': detail.get('quantity_sold', 1),
                        'price': detail.get('unit_price', 0),
                        'unit_price': detail.get('unit_price', 0),
                        'amount': detail.get('quantity_sold', 1) * detail.get('unit_price', 0),
                        'total_amount': detail.get('quantity_sold', 1) * detail.get('unit_price', 0),
                        'status': 'completed',  # 假設所有交易都已完成
                        'payment_method': 'unknown',  # API未提供，使用預設值
                        'weather': context.get('weather', 'Unknown'),
                        'temperature': context.get('temperature_celsius', 0),
                        'humidity': context.get('humidity', 0),
                        'is_holiday': context.get('is_holiday', False),
                        'hour_of_day': context.get('hour_of_day', 0),
                        'recommended_items': tx.get('recommended_items', [])
                    }
                    
                    dashboard_data.append(record)
            
            api_logger.info(f"Converted {len(dashboard_data)} transaction records for dashboard")
            return dashboard_data
            
        except Exception as e:
            api_logger.error(f"Error converting transactional data for dashboard: {str(e)}")
            import streamlit as st
            st.error(f"❌ 數據轉換錯誤：{str(e)}")
            return []

    def get_transactional_data_for_sales_analytics(self, start_date: str, end_date: str,
                                                    machine_id: str = None, limit: int = 1000) -> List[Dict]:
        """
        獲取適用於 Sales Analytics 的訂單數據
        將 transactional-data API 的格式轉換為 Sales Analytics 需要的訂單格式
        """
        api_logger.info(f"Fetching transactional data for sales analytics: {start_date} to {end_date}")
        
        # 硬編碼映射表（備用方案）
        FALLBACK_MEAL_ID_MAP = {
            'A001': '早餐套餐',
            'A002': '午餐套餐A',
            'A003': '午餐套餐B',
            'A004': '午餐套餐C',
            'A005': '下午茶套餐',
            'A006': '晚餐套餐A',
            'A007': '晚餐套餐B',
            'A008': '雞塊套餐',
            'A009': '沙拉套餐',
            'A010': '飲料套餐',
            'A011': '魷魚套餐',
            'A012': '薯條套餐',
            'A013': '滷味三寶飯套餐',
            'A014': '便當套餐',
            'B001': '咖啡套餐',
            'B002': '茶飲套餐',
            'B003': '果汁套餐',
            'C001': '甜點套餐',
        }
        
        try:
            # 調用現有的 get_transactional_data 方法
            transactions = self.get_transactional_data(start_date, end_date, machine_id, limit)
            
            if not transactions:
                api_logger.warning("No transactional data returned from API")
                return []
            
            # 獲取菜單項目以便映射 meal_id 到 item_name
            menu_items = []
            try:
                menu_items = self.get_menu_items()
            except Exception as e:
                api_logger.warning(f"Failed to fetch menu items: {str(e)}")
            
            # 建立映射表（支援多種映射方式）
            menu_map = {}
            product_code_map = {}
            
            for item in menu_items:
                # ID 映射
                item_id = str(item.get('id', ''))
                if item_id:
                    menu_map[item_id] = item.get('name', 'Unknown')
                
                # product_code 映射
                product_code = str(item.get('product_code', ''))
                if product_code:
                    product_code_map[product_code] = item.get('name', 'Unknown')
            
            # 轉換為訂單格式
            orders = []
            for idx, tx in enumerate(transactions, 1):
                tx_id = tx.get('transaction_id', f'TX-{idx}')
                machine_id = tx.get('machine_id', 'Unknown')
                timestamp = tx.get('purchase_timestamp', '')
                context = tx.get('context', {})
                
                # 計算訂單總金額
                total_amount = sum(
                    detail.get('quantity_sold', 0) * detail.get('unit_price', 0)
                    for detail in tx.get('transaction_details', [])
                )
                
                # 轉換訂單項目
                items = []
                for detail in tx.get('transaction_details', []):
                    meal_id = str(detail.get('meal_id', 'Unknown'))
                    
                    # 多層映射策略
                    item_name = meal_id  # 預設使用 meal_id
                    
                    # 策略 1: 從 product_code 映射（優先）
                    if meal_id in product_code_map:
                        item_name = product_code_map[meal_id]
                    # 策略 2: 從 ID 映射
                    elif meal_id in menu_map:
                        item_name = menu_map[meal_id]
                    # 策略 3: 使用硬編碼映射表（備用）
                    elif meal_id in FALLBACK_MEAL_ID_MAP:
                        item_name = FALLBACK_MEAL_ID_MAP[meal_id]
                    
                    quantity = detail.get('quantity_sold', 1)
                    unit_price = detail.get('unit_price', 0)
                    
                    items.append({
                        'menu_item_id': meal_id,
                        'meal_id': meal_id,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'subtotal': quantity * unit_price,
                        'item_name': item_name
                    })
                
                # 構建訂單對象
                order = {
                    'id': idx,  # 使用序號作為 ID
                    'order_number': tx_id,
                    'transaction_id': tx_id,
                    'machine_id': str(machine_id),
                    'total_amount': total_amount,
                    'status': 'completed',
                    'payment_status': 'paid',
                    'payment_method': 'unknown',
                    'created_at': timestamp,
                    'updated_at': timestamp,
                    'items': items,
                    'weather': context.get('weather', 'Unknown'),
                    'temperature': context.get('temperature_celsius', 0),
                    'humidity': context.get('humidity', 0),
                    'is_holiday': context.get('is_holiday', False),
                    'hour_of_day': context.get('hour_of_day', 0),
                    'recommended_items': tx.get('recommended_items', [])
                }
                
                orders.append(order)
            
            api_logger.info(f"Converted {len(orders)} orders for sales analytics")
            return orders
            
        except Exception as e:
            api_logger.error(f"Error converting transactional data for sales analytics: {str(e)}")
            import streamlit as st
            st.error(f"❌ 數據轉換錯誤：{str(e)}")
            return []

    def delete_ai_recommendation(self, recommendation_id: int) -> bool:
        """刪除AI推薦（軟刪除）"""
        api_logger.debug(f"Deleting AI recommendation: {recommendation_id}")
        try:
            response = requests.delete(
                f"{self.base_url}/ai/recommendations/{recommendation_id}",
                headers=self._get_ai_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 204:
                api_logger.info(f"Successfully deleted AI recommendation: {recommendation_id}")
                import streamlit as st
                st.success(f"✅ AI推薦已成功刪除 - ID: {recommendation_id}")
                return True
            elif response.status_code == 404:
                api_logger.warning(f"AI recommendation not found: {recommendation_id}")
                import streamlit as st
                st.warning(f"⚠️ 推薦記錄不存在或已被刪除 - ID: {recommendation_id}")
                return False
            elif response.status_code == 401:
                api_logger.warning("Unauthorized to delete AI recommendation")
                import streamlit as st
                st.error("❌ 權限不足：無法刪除AI推薦")
                return False
            else:
                api_logger.warning(f"Failed to delete AI recommendation - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 刪除AI推薦失敗 - 狀態碼: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when deleting AI recommendation: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return False
        except Exception as e:
            api_logger.error(f"Unexpected error when deleting AI recommendation: {str(e)}")
            import streamlit as st
            st.error(f"❌ 刪除AI推薦時發生未預期的錯誤：{str(e)}")
            return False
    
    def update_machine_menu_items(self, machine_id: int, menu_item_ids: List[int], display_orders: List[int]) -> Dict:
        """更新機台菜單項目"""
        api_logger.info(f"🔄 開始更新機台 {machine_id} 菜單項目")
        api_logger.info(f"📋 菜單項目ID: {menu_item_ids}")
        api_logger.info(f"📋 顯示順序: {display_orders}")
        
        try:
            payload = {
                "menu_item_ids": menu_item_ids,
                "display_orders": display_orders
            }
            
            # 記錄完整的API調用資訊
            api_logger.info(f"📡 API調用: POST {self.base_url}/machines/{machine_id}/update-menu-items")
            api_logger.info(f"📦 Request Headers: {self._get_auth_headers()}")
            api_logger.info(f"📦 Request Body: {payload}")
            
            response = requests.post(
                f"{self.base_url}/machines/{machine_id}/update-menu-items",
                headers=self._get_auth_headers(),
                json=payload,
                timeout=10
            )
            
            # 記錄回應詳情
            api_logger.info(f"📊 Response Status Code: {response.status_code}")
            api_logger.info(f"📊 Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                api_logger.info(f"📊 Response Body: {response_json}")
            except:
                api_logger.info(f"📊 Response Text: {response.text}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                api_logger.info(f"✅ 成功更新機台 {machine_id} 菜單項目")
                return result
            elif response.status_code == 404:
                api_logger.warning(f"❌ 機台 {machine_id} 不存在")
                import streamlit as st
                st.error(f"❌ 機台 {machine_id} 不存在")
                return None
            elif response.status_code == 401:
                api_logger.warning("❌ 權限不足：無法更新機台菜單")
                import streamlit as st
                st.error("❌ 權限不足：無法更新機台菜單")
                return None
            else:
                api_logger.warning(f"❌ 更新機台菜單失敗 - 狀態碼: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 更新機台菜單失敗 - 狀態碼: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when updating machine menu items: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return None
        except Exception as e:
            api_logger.error(f"Unexpected error when updating machine menu items: {str(e)}")
            import streamlit as st
            st.error(f"❌ 更新機台菜單時發生未預期的錯誤：{str(e)}")
            return None

    def get_machine_current_menu_items(self, machine_id: int) -> Dict:
        """獲取機台當前菜單項目"""
        api_logger.info(f"Getting current menu items for machine {machine_id}")
        try:
            response = requests.get(
                f"{self.base_url}/machines/{machine_id}/current-menu-items",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            api_logger.debug(f"Get machine current menu items API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                api_logger.info(f"Successfully retrieved current menu items for machine {machine_id}")
                return result
            elif response.status_code == 404:
                api_logger.warning(f"Machine {machine_id} not found")
                import streamlit as st
                st.error(f"❌ 機台 {machine_id} 不存在")
                return None
            elif response.status_code == 401:
                api_logger.warning("Unauthorized to get machine menu items")
                import streamlit as st
                st.error("❌ 權限不足：無法獲取機台菜單")
                return None
            else:
                api_logger.warning(f"Failed to get machine menu items - Status code: {response.status_code}")
                import streamlit as st
                st.error(f"❌ 獲取機台菜單失敗 - 狀態碼: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            api_logger.error(f"Network error when getting machine menu items: {str(e)}")
            import streamlit as st
            st.error(f"❌ 網路錯誤：{str(e)}")
            return None
        except Exception as e:
            api_logger.error(f"Unexpected error when getting machine menu items: {str(e)}")
            import streamlit as st
            st.error(f"❌ 獲取機台菜單時發生未預期的錯誤：{str(e)}")
            return None

    def _get_ai_auth_headers(self) -> dict:
        """獲取AI API認證標頭"""
        # 使用固定的AI API Key，實際應用中應該從環境變數或配置檔案讀取
        ai_api_key = "ai-team-key-001"
        return {
            "Authorization": f"Bearer {ai_api_key}",
            "Content-Type": "application/json"
        }

def init_session_state():
    """初始化 session state"""
    system_logger.debug("Initializing session state")
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
    
    # 初始化閒置追蹤相關狀態
    if 'last_activity_time' not in st.session_state:
        st.session_state.last_activity_time = time.time()
    if 'idle_warning_shown' not in st.session_state:
        st.session_state.idle_warning_shown = False
    
    system_logger.info("Session state initialized successfully")
