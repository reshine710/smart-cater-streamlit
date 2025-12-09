"""
權限檢查工具模組
提供三層權限系統的權限檢查功能
"""
from typing import Literal
import streamlit as st

Role = Literal['super_admin', 'admin', 'user']
Permission = Literal['create', 'update', 'delete', 'manage_users', 'view']


def get_user_role() -> Role:
    """
    獲取當前使用者角色
    
    Returns:
        Role: 使用者角色，預設為 'user'
    """
    role = st.session_state.get('role')
    
    # 向後兼容：如果沒有 role，根據 is_admin 推斷
    if not role or role not in ['super_admin', 'admin', 'user']:
        is_admin = st.session_state.get('is_admin', False)
        if is_admin:
            # 預設為 super_admin（或根據實際需求調整）
            role = 'super_admin'
        else:
            role = 'user'
    
    return role


def has_permission(permission: Permission) -> bool:
    """
    檢查使用者是否有指定權限
    
    Args:
        permission: 需要的權限類型
    
    Returns:
        bool: 是否有權限
    """
    role = get_user_role()
    
    # 超級管理員擁有所有權限
    if role == 'super_admin':
        return True
    
    # 管理員可以創建和更新
    if role == 'admin':
        return permission in ['create', 'update', 'view']
    
    # 一般使用者只能查看
    if role == 'user':
        return permission == 'view'
    
    return False


def can_create() -> bool:
    """檢查是否可以創建資源"""
    return has_permission('create')


def can_update() -> bool:
    """檢查是否可以更新資源"""
    return has_permission('update')


def can_delete() -> bool:
    """檢查是否可以刪除資源"""
    return has_permission('delete')


def can_manage_users() -> bool:
    """檢查是否可以管理使用者"""
    return has_permission('manage_users')


def is_super_admin() -> bool:
    """檢查是否為超級管理員"""
    return get_user_role() == 'super_admin'


def is_admin_or_above() -> bool:
    """檢查是否為管理員或以上（包含超級管理員）"""
    role = get_user_role()
    return role in ['admin', 'super_admin']


def is_user() -> bool:
    """檢查是否為一般使用者"""
    return get_user_role() == 'user'


def get_role_label(role: Role = None) -> str:
    """
    獲取角色標籤
    
    Args:
        role: 角色，如果為 None 則使用當前使用者角色
    
    Returns:
        str: 角色標籤
    """
    if role is None:
        role = get_user_role()
    
    labels = {
        'super_admin': '👑 超級管理員',
        'admin': '🔧 管理員',
        'user': '👤 一般使用者'
    }
    return labels.get(role, '👤 一般使用者')


def show_permission_error(required_permission: Permission):
    """
    顯示權限不足錯誤訊息
    
    Args:
        required_permission: 需要的權限類型
    """
    messages = {
        'create': '此操作需要管理員權限',
        'update': '此操作需要管理員權限',
        'delete': '此操作需要超級管理員權限',
        'manage_users': '此操作需要超級管理員權限',
        'view': '此操作需要登入'
    }
    
    st.error(f"❌ 權限不足：{messages.get(required_permission, '您沒有權限執行此操作')}")
