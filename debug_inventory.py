#!/usr/bin/env python3
"""
調試腳本：查詢機台 SC-NUC-001 的庫存資料
"""
import sys
import json
from utils import VendingMachineAPI, API_BASE_URL
from config import settings

def debug_machine_inventory(machine_code: str = "SC-NUC-001"):
    """查詢指定機台的庫存資料"""
    
    print(f"🔍 查詢機台 {machine_code} 的庫存資料...")
    print(f"API Base URL: {API_BASE_URL}")
    print("-" * 80)
    
    # 初始化 API（需要登入 token，這裡先嘗試獲取機台列表）
    api = VendingMachineAPI(API_BASE_URL)
    
    # 1. 先獲取所有機台，找到目標機台
    print("\n1️⃣ 獲取機台列表...")
    machines = api.get_machines()
    
    if not machines:
        print("❌ 無法獲取機台列表")
        return
    
    print(f"✅ 找到 {len(machines)} 個機台")
    
    # 查找目標機台
    target_machine = None
    for machine in machines:
        if machine.get('machine_code') == machine_code:
            target_machine = machine
            break
    
    if not target_machine:
        print(f"❌ 找不到機台 {machine_code}")
        print("\n可用的機台列表：")
        for machine in machines:
            print(f"  - {machine.get('name', 'Unknown')} ({machine.get('machine_code', 'N/A')}) - ID: {machine.get('id')}")
        return
    
    machine_id = target_machine.get('id')
    machine_name = target_machine.get('name', 'Unknown')
    
    print(f"✅ 找到機台：{machine_name} (ID: {machine_id})")
    print(f"   機台代碼: {target_machine.get('machine_code')}")
    print(f"   機台狀態: {target_machine.get('status', 'N/A')}")
    print("-" * 80)
    
    # 2. 查詢庫存資料
    print(f"\n2️⃣ 查詢機台 {machine_id} 的庫存資料...")
    inventory_data = api.get_machine_inventory(machine_id)
    
    if inventory_data is None:
        print("❌ API 返回 None（可能是權限問題或機台不存在）")
        print("💡 提示：需要登入 token 才能查詢庫存")
        return
    
    print(f"✅ API 返回數據類型: {type(inventory_data)}")
    print(f"✅ 返回數據內容:")
    print(json.dumps(inventory_data, indent=2, ensure_ascii=False, default=str))
    print("-" * 80)
    
    # 3. 分析數據結構
    print(f"\n3️⃣ 分析數據結構...")
    
    if isinstance(inventory_data, dict):
        items = inventory_data.get('items', [])
        total_items = inventory_data.get('total_items', 0)
        low_stock_items = inventory_data.get('low_stock_items', 0)
        out_of_stock_items = inventory_data.get('out_of_stock_items', 0)
        
        print(f"   總項目數: {total_items}")
        print(f"   低庫存項目: {low_stock_items}")
        print(f"   缺貨項目: {out_of_stock_items}")
        print(f"   庫存項目列表長度: {len(items)}")
        
        if items:
            print(f"\n   前 3 個庫存項目:")
            for i, item in enumerate(items[:3], 1):
                print(f"   {i}. ID: {item.get('id')}")
                print(f"      商品: {item.get('menu_item', {}).get('name', 'N/A')}")
                print(f"      當前庫存: {item.get('current_stock', 0)}")
                print(f"      最低閾值: {item.get('min_threshold', 0)}")
        else:
            print("   ⚠️ 庫存項目列表為空")
    else:
        print(f"   ⚠️ 返回數據不是字典格式: {type(inventory_data)}")
    
    print("-" * 80)
    print("\n✅ 調試完成")


if __name__ == "__main__":
    machine_code = sys.argv[1] if len(sys.argv) > 1 else "SC-NUC-001"
    debug_machine_inventory(machine_code)
