"""
Utils 模組
包含權限檢查工具等
"""

# 重新導出 utils.py 中的主要內容以保持向後兼容
# 由於 utils 現在是一個包，需要從上層目錄導入 utils.py 的內容
import sys
import os
import importlib.util

# 獲取當前文件所在目錄的父目錄（專案根目錄）
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

# 將父目錄添加到 sys.path（如果還沒有）
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 使用 importlib 動態導入 utils.py 模組
_utils_py_path = os.path.join(_parent_dir, 'utils.py')
if os.path.exists(_utils_py_path):
    _spec = importlib.util.spec_from_file_location("_utils_py_module", _utils_py_path)
    _utils_py_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_utils_py_module)
    
    # 重新導出主要內容
    API_BASE_URL = _utils_py_module.API_BASE_URL
    SystemStatus = _utils_py_module.SystemStatus
    VendingMachineAPI = _utils_py_module.VendingMachineAPI
    init_session_state = _utils_py_module.init_session_state
    format_datetime_display = _utils_py_module.format_datetime_display
else:
    # 如果找不到 utils.py，提供預設值以避免導入錯誤
    API_BASE_URL = "http://127.0.0.1:8000/api/v1"
    SystemStatus = None
    VendingMachineAPI = None
    init_session_state = None
    format_datetime_display = None

# 導出權限模組
from .permissions import (
    get_user_role,
    has_permission,
    can_create,
    can_update,
    can_delete,
    can_manage_users,
    is_super_admin,
    is_admin_or_above,
    is_user,
    get_role_label,
    show_permission_error,
    Role,
    Permission
)

__all__ = [
    'API_BASE_URL',
    'SystemStatus',
    'VendingMachineAPI',
    'init_session_state',
    'format_datetime_display',
    'get_user_role',
    'has_permission',
    'can_create',
    'can_update',
    'can_delete',
    'can_manage_users',
    'is_super_admin',
    'is_admin_or_above',
    'is_user',
    'get_role_label',
    'show_permission_error',
    'Role',
    'Permission',
]
