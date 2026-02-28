#!/usr/bin/env python3
"""
測試腳本：驗證 API 返回的 product_code 是否為空
用於確認為什麼 UI 會顯示 "N/A"
"""

import requests
import json
from typing import Dict, List, Optional
from config import settings

# API 配置
API_BASE_URL = settings.get("API_URL", "http://127.0.0.1:8000/api/v1")

def create_test_user(username: str, password: str, email: str, is_admin: bool = True) -> bool:
    """創建測試用戶（如果不存在）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/users/",
            json={
                "username": username,
                "email": email,
                "password": password,
                "full_name": f"Test {'Admin' if is_admin else 'User'}",
                "is_active": True,
                "is_admin": is_admin
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        # 201 表示創建成功，409 表示已存在（也算成功）
        if response.status_code in [200, 201]:
            print(f"   ✅ 成功創建用戶 '{username}'")
            return True
        elif response.status_code == 409:
            print(f"   ℹ️  用戶 '{username}' 已存在")
            return True
        else:
            print(f"   ⚠️  創建用戶失敗: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"   ⚠️  創建用戶時發生錯誤: {str(e)}")
        return False

def login(username: str, password: str) -> Optional[str]:
    """登入並獲取 token"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/users/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"❌ 登入失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登入錯誤: {str(e)}")
        return None

def get_machines(token: str) -> List[Dict]:
    """獲取所有機台"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/machines",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('items', []) if isinstance(data, dict) else data
        else:
            print(f"❌ 獲取機台失敗: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 獲取機台錯誤: {str(e)}")
        return []

def get_machine_inventory(machine_id: int, token: str) -> Optional[Dict]:
    """獲取機台庫存"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/machines/{machine_id}/inventory",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 獲取機台 {machine_id} 庫存失敗: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 獲取機台 {machine_id} 庫存錯誤: {str(e)}")
        return None

def analyze_product_code(inventory_data: Dict) -> Dict:
    """分析庫存數據中的 product_code"""
    results = {
        'total_items': 0,
        'items_with_code': 0,
        'items_without_code': 0,
        'items_with_null': 0,
        'items_with_empty': 0,
        'details': []
    }
    
    items = inventory_data.get('inventory_items') or inventory_data.get('items') or []
    results['total_items'] = len(items)
    
    for item in items:
        menu_item = item.get('menu_item', {})
        product_code = menu_item.get('product_code')
        product_name = menu_item.get('name', 'Unknown')
        
        detail = {
            'product_name': product_name,
            'product_code_raw': product_code,
            'product_code_type': type(product_code).__name__,
            'is_none': product_code is None,
            'is_empty_string': product_code == '',
            'is_falsy': not product_code,  # None, '', 0, False 都會是 True
            'display_value': product_code if product_code else 'N/A'
        }
        
        results['details'].append(detail)
        
        if product_code is None:
            results['items_with_null'] += 1
            results['items_without_code'] += 1
        elif product_code == '':
            results['items_with_empty'] += 1
            results['items_without_code'] += 1
        elif not product_code:  # 其他 falsy 值（0, False 等）
            results['items_without_code'] += 1
        else:
            results['items_with_code'] += 1
    
    return results

def main():
    print("=" * 80)
    print("🔍 Product Code 測試腳本")
    print("=" * 80)
    print()
    
    # 1. 登入（先嘗試預設帳號，失敗則提示輸入）
    import os
    import sys
    
    # 優先檢查是否有直接提供的 token
    token = os.getenv('TEST_TOKEN')
    
    if token:
        print("🔑 使用環境變數中的 token")
    else:
        # 嘗試從環境變數或使用提供的帳號
        username = os.getenv('TEST_USERNAME', 'admin_ai_team')
        password = os.getenv('TEST_PASSWORD', 'adminai123')
        email = os.getenv('TEST_EMAIL', f'{username}@example.com')
        
        # 先嘗試創建測試帳號（如果不存在且不需要認證）
        print(f"📝 確保測試帳號 '{username}' 存在...")
        create_test_user(username, password, email, is_admin=True)
        
        print(f"🔐 正在使用帳號 '{username}' 登入...")
        token = login(username, password)
        
        if not token:
            # 檢查是否為非互動模式（沒有 TTY）
            if not sys.stdin.isatty():
                print("❌ 預設帳號登入失敗，且無法在非互動模式下輸入")
                print("💡 提示：請設置以下環境變數之一：")
                print("   1. TEST_TOKEN=your_token (直接提供 token)")
                print("   2. TEST_USERNAME=your_username 和 TEST_PASSWORD=your_password")
                print()
                print("   例如：")
                print("   export TEST_TOKEN=your_access_token")
                print("   或")
                print("   export TEST_USERNAME=your_username")
                print("   export TEST_PASSWORD=your_password")
                sys.exit(1)
            
            print("❌ 預設帳號登入失敗，請手動輸入：")
            try:
                username = input("用戶名: ").strip()
                password = input("密碼: ").strip()
                print(f"\n🔐 正在使用帳號 '{username}' 登入...")
                token = login(username, password)
                if not token:
                    print("❌ 無法登入，測試終止")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                print("\n❌ 輸入中斷，測試終止")
                sys.exit(1)
    
    print("✅ 登入成功")
    print()
    
    # 2. 獲取所有機台
    print("📦 正在獲取機台列表...")
    machines = get_machines(token)
    if not machines:
        print("❌ 沒有可用的機台")
        return
    
    print(f"✅ 找到 {len(machines)} 個機台")
    print()
    
    # 3. 對每個機台測試庫存數據
    all_results = {}
    
    for machine in machines:
        machine_id = machine.get('id')
        machine_name = machine.get('name', 'Unknown')
        machine_code = machine.get('machine_code', 'N/A')
        
        print(f"🔍 測試機台: {machine_name} ({machine_code}, ID: {machine_id})")
        
        inventory_data = get_machine_inventory(machine_id, token)
        if not inventory_data:
            print(f"   ⚠️  無法獲取庫存數據")
            print()
            continue
        
        # 分析 product_code
        analysis = analyze_product_code(inventory_data)
        all_results[machine_id] = {
            'machine_name': machine_name,
            'machine_code': machine_code,
            'analysis': analysis
        }
        
        print(f"   📊 總庫存項目: {analysis['total_items']}")
        print(f"   ✅ 有 product_code: {analysis['items_with_code']}")
        print(f"   ❌ 沒有 product_code: {analysis['items_without_code']}")
        print(f"      - None: {analysis['items_with_null']}")
        print(f"      - 空字符串: {analysis['items_with_empty']}")
        print()
        
        # 顯示詳細資訊（前 5 個項目）
        if analysis['details']:
            print("   📋 詳細資訊（前 5 個項目）：")
            for i, detail in enumerate(analysis['details'][:5], 1):
                print(f"      {i}. {detail['product_name']}")
                print(f"         product_code 原始值: {repr(detail['product_code_raw'])}")
                print(f"         product_code 類型: {detail['product_code_type']}")
                print(f"         是否為 None: {detail['is_none']}")
                print(f"         是否為空字符串: {detail['is_empty_string']}")
                print(f"         是否為 falsy: {detail['is_falsy']}")
                print(f"         顯示值: {detail['display_value']}")
                print()
    
    # 4. 總結報告
    print("=" * 80)
    print("📊 總結報告")
    print("=" * 80)
    
    total_items_all = 0
    total_with_code = 0
    total_without_code = 0
    
    for machine_id, result in all_results.items():
        analysis = result['analysis']
        total_items_all += analysis['total_items']
        total_with_code += analysis['items_with_code']
        total_without_code += analysis['items_without_code']
    
    print(f"總機台數: {len(all_results)}")
    print(f"總庫存項目數: {total_items_all}")
    print(f"有 product_code 的項目: {total_with_code} ({total_with_code/total_items_all*100:.1f}%)" if total_items_all > 0 else "有 product_code 的項目: 0")
    print(f"沒有 product_code 的項目: {total_without_code} ({total_without_code/total_items_all*100:.1f}%)" if total_items_all > 0 else "沒有 product_code 的項目: 0")
    print()
    
    # 5. 自動保存 JSON 格式的詳細結果
    output_file = 'product_code_test_results.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 詳細結果已自動保存到: {output_file}")
    except Exception as e:
        print(f"\n⚠️  保存 JSON 文件時發生錯誤: {str(e)}")
    
    print("\n✅ 測試完成！")
    
    # 6. 問題診斷和建議
    if total_without_code == total_items_all and total_items_all > 0:
        print("\n" + "=" * 80)
        print("🔍 問題診斷")
        print("=" * 80)
        print("❌ 發現問題：所有庫存項目的 product_code 都是 None")
        print("\n💡 解決方案：")
        print("   1. 檢查後端數據庫中的 menu_items 表")
        print("   2. 確認 product_code 欄位是否有值")
        print("   3. 如果沒有，需要在「菜單管理」中為每個商品設置 product_code")
        print("   4. 或者檢查後端 API 是否正確返回了 product_code 欄位")

if __name__ == "__main__":
    main()
