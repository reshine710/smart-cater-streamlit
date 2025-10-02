#!/usr/bin/env python3
"""
測試更新功能的腳本
驗證新增的 API 端點和功能是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import VendingMachineAPI
import json

def test_users_api():
    """測試使用者 API 更新"""
    print("===== 測試使用者 API 更新 =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    try:
        # 測試獲取使用者總數
        print("1. 測試獲取使用者總數...")
        count = api.get_users_count()
        print(f"   使用者總數: {count}")
        
        # 測試分頁查詢
        print("2. 測試分頁查詢使用者...")
        users_page1 = api.get_users(skip=0, limit=2)
        print(f"   第1頁使用者數量: {len(users_page1)}")
        
        users_page2 = api.get_users(skip=2, limit=2)
        print(f"   第2頁使用者數量: {len(users_page2)}")
        
        print("✅ 使用者 API 測試完成")
        
    except Exception as e:
        print(f"❌ 使用者 API 測試失敗: {str(e)}")
    
    print()

def test_locations_api():
    """測試地點 API"""
    print("===== 測試地點 API =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    try:
        # 測試獲取地點列表
        print("1. 測試獲取地點列表...")
        locations = api.get_locations()
        print(f"   地點數量: {len(locations)}")
        
        if locations:
            print("   地點列表:")
            for loc in locations:
                print(f"   - {loc.get('name', 'Unknown')}: {'室內' if loc.get('is_indoor', False) else '室外'}")
        
        # 測試創建地點
        print("2. 測試創建地點...")
        test_location = {
            "name": "測試地點API",
            "address": "測試地址123號",
            "description": "API測試用地點",
            "is_indoor": True
        }
        
        created_location = api.create_location(test_location)
        if created_location:
            print(f"   ✅ 地點創建成功: {created_location.get('name', 'Unknown')}")
        else:
            print("   ❌ 地點創建失敗")
        
        print("✅ 地點 API 測試完成")
        
    except Exception as e:
        print(f"❌ 地點 API 測試失敗: {str(e)}")
    
    print()

def test_menu_items_nutrition():
    """測試菜單項目營養資訊"""
    print("===== 測試菜單項目營養資訊 =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    try:
        # 測試獲取菜單項目
        print("1. 測試獲取菜單項目...")
        menu_items = api.get_menu_items()
        print(f"   菜單項目數量: {len(menu_items)}")
        
        if menu_items:
            print("   菜單項目營養資訊:")
            for item in menu_items:
                name = item.get('name', 'Unknown')
                nutrition = item.get('nutrition_info', {})
                tags = item.get('tags', [])
                
                print(f"   - {name}:")
                if nutrition:
                    print(f"     營養: 熱量{nutrition.get('calories', 0)}卡, 蛋白質{nutrition.get('protein', 0)}g")
                if tags:
                    print(f"     標籤: {', '.join(tags)}")
        
        # 測試創建帶營養資訊的菜單項目
        print("2. 測試創建帶營養資訊的菜單項目...")
        test_menu_item = {
            "name": "測試營養餐點",
            "description": "含完整營養資訊的測試餐點",
            "price": 150.0,
            "heating_method": "microwave",
            "heating_time": 90,
            "is_active": True,
            "nutrition_info": {
                "calories": 350,
                "protein": 20,
                "carbs": 40,
                "fat": 12
            },
            "tags": ["測試", "營養", "健康"]
        }
        
        created_item = api.create_menu_item(test_menu_item)
        if created_item:
            print(f"   ✅ 菜單項目創建成功: {created_item.get('name', 'Unknown')}")
        else:
            print("   ❌ 菜單項目創建失敗")
        
        print("✅ 菜單項目營養資訊測試完成")
        
    except Exception as e:
        print(f"❌ 菜單項目營養資訊測試失敗: {str(e)}")
    
    print()

def test_offline_data_format():
    """測試離線數據格式"""
    print("===== 測試離線數據格式 =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    try:
        # 測試離線菜單數據
        print("1. 測試離線菜單數據格式...")
        offline_menu = api._get_offline_menu_items()
        
        for item in offline_menu:
            name = item.get('name', 'Unknown')
            nutrition = item.get('nutrition_info', {})
            tags = item.get('tags', [])
            
            print(f"   - {name}:")
            print(f"     營養資訊: {bool(nutrition)}")
            print(f"     標籤格式: {type(tags)} - {tags}")
            
            # 驗證營養資訊結構
            if nutrition:
                required_fields = ['calories', 'protein', 'carbs', 'fat']
                missing_fields = [field for field in required_fields if field not in nutrition]
                if missing_fields:
                    print(f"     ❌ 缺少營養欄位: {missing_fields}")
                else:
                    print(f"     ✅ 營養資訊完整")
        
        # 測試離線地點數據
        print("2. 測試離線地點數據格式...")
        offline_locations = api._get_offline_locations()
        
        for location in offline_locations:
            name = location.get('name', 'Unknown')
            is_indoor = location.get('is_indoor', False)
            address = location.get('address', '')
            
            print(f"   - {name}: {'室內' if is_indoor else '室外'}")
            print(f"     地址: {address}")
        
        print("✅ 離線數據格式測試完成")
        
    except Exception as e:
        print(f"❌ 離線數據格式測試失敗: {str(e)}")
    
    print()

def run_all_tests():
    """運行所有測試"""
    print("🧪 開始測試更新功能...")
    print("=" * 50)
    
    test_users_api()
    test_locations_api()
    test_menu_items_nutrition()
    test_offline_data_format()
    
    print("=" * 50)
    print("🎉 所有測試完成！")

if __name__ == "__main__":
    run_all_tests()
