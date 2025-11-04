#!/usr/bin/env python3
"""
獨立測試 Transactional Data API
用於診斷 API 調用問題
"""

import requests
import json
from datetime import datetime, timedelta

# 配置
BASE_URL = "http://localhost:8000/api/v1"  # 本地測試
# BASE_URL = "https://sihai.baimeng.co/api/v1"  # 生產環境（如需測試）

API_KEY = "ai-team-key-001"

def test_transactional_data_api():
    """測試 transactional data API"""
    
    print("=" * 80)
    print("🔍 測試 Transactional Data API")
    print("=" * 80)
    print()
    
    # 準備日期參數
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3)
    
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    print(f"📅 測試日期範圍:")
    print(f"   開始日期: {start_date_str}")
    print(f"   結束日期: {end_date_str}")
    print()
    
    # 準備請求
    url = f"{BASE_URL}/ai/transactional-data"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 測試不同的參數組合
    test_cases = [
        {
            "name": "基本查詢（最近3天）",
            "params": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "limit": 10
            }
        },
        {
            "name": "只用 limit 參數",
            "params": {
                "limit": 10
            }
        },
        {
            "name": "加上 skip 參數",
            "params": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "limit": 10,
                "skip": 0
            }
        },
        {
            "name": "指定機台",
            "params": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "machine_id": "5",
                "limit": 10
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 測試案例 {i}: {test_case['name']}")
        print("-" * 80)
        
        # 顯示請求資訊
        print(f"🔗 URL: {url}")
        print(f"📦 Headers:")
        print(f"   Authorization: Bearer {API_KEY}")
        print(f"📦 Params:")
        for key, value in test_case['params'].items():
            print(f"   {key}: {value}")
        print()
        
        try:
            # 發送請求
            response = requests.get(
                url,
                headers=headers,
                params=test_case['params'],
                timeout=10
            )
            
            # 顯示響應狀態
            print(f"📊 響應狀態碼: {response.status_code}")
            print(f"📊 響應頭: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                # 成功
                data = response.json()
                print(f"✅ 成功獲取數據")
                print(f"📈 數據統計:")
                
                transactions = data.get('data', [])
                pagination = data.get('pagination', {})
                
                print(f"   - 返回記錄數: {len(transactions)}")
                print(f"   - 總記錄數: {pagination.get('total_records', 'N/A')}")
                print(f"   - 當前頁: {pagination.get('current_page', 'N/A')}")
                print()
                
                if transactions:
                    print(f"📝 第一筆交易樣本:")
                    print(json.dumps(transactions[0], indent=2, ensure_ascii=False))
                    print()
                    
                    print(f"✅ 此測試案例成功！")
                else:
                    print(f"⚠️  查詢範圍內沒有交易記錄")
                
            elif response.status_code == 422:
                # 參數驗證錯誤
                print(f"❌ 參數驗證錯誤 (422)")
                try:
                    error_detail = response.json()
                    print(f"📝 錯誤詳情:")
                    print(json.dumps(error_detail, indent=2, ensure_ascii=False))
                except:
                    print(f"📝 原始響應: {response.text}")
                print()
                print(f"💡 可能的問題:")
                print(f"   1. 日期格式不正確（應為 YYYY-MM-DD）")
                print(f"   2. 缺少必需參數")
                print(f"   3. 參數類型不匹配")
                
            elif response.status_code == 401:
                # 認證錯誤
                print(f"❌ 認證失敗 (401)")
                print(f"💡 請檢查 API Key 是否正確")
                
            else:
                # 其他錯誤
                print(f"❌ 請求失敗")
                try:
                    error_detail = response.json()
                    print(f"📝 錯誤詳情:")
                    print(json.dumps(error_detail, indent=2, ensure_ascii=False))
                except:
                    print(f"📝 原始響應: {response.text}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 網路錯誤: {e}")
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
        
        print()
        print("=" * 80)
        print()

def test_api_health():
    """測試 API 健康狀態"""
    print("🏥 測試 API 健康狀態")
    print("-" * 80)
    
    url = f"{BASE_URL}/ai/health"
    
    print(f"🔗 URL: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"📊 響應狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API 健康檢查通過")
            print(f"📝 健康狀態:")
            print(json.dumps(health_data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ API 健康檢查失敗")
            print(f"📝 響應: {response.text}")
    
    except Exception as e:
        print(f"❌ 無法連接到 API: {e}")
    
    print()
    print("=" * 80)
    print()

def test_with_streamlit_api_client():
    """使用 Streamlit API 客戶端測試"""
    print("🔧 使用 Streamlit API 客戶端測試")
    print("-" * 80)
    print()
    
    try:
        # 導入 utils
        import sys
        sys.path.insert(0, '/Users/user/Mirror/P_Projects/Dev/VendingMachineUI/SmartCaterStreamlit')
        from utils import VendingMachineAPI
        
        # 創建 API 客戶端
        api = VendingMachineAPI(BASE_URL, token=API_KEY)
        
        # 測試日期
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=3)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        print(f"📅 測試日期範圍: {start_date_str} 至 {end_date_str}")
        print()
        
        # 測試 get_transactional_data
        print("🔍 測試 get_transactional_data() 方法...")
        transactions = api.get_transactional_data(
            start_date_str,
            end_date_str,
            limit=10
        )
        
        if transactions:
            print(f"✅ 成功獲取 {len(transactions)} 筆交易")
            print(f"📝 第一筆交易:")
            print(json.dumps(transactions[0], indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  沒有獲取到交易數據")
        
        print()
        
        # 測試轉換方法
        print("🔍 測試 get_transactional_data_for_dashboard() 方法...")
        dashboard_data = api.get_transactional_data_for_dashboard(
            start_date_str,
            end_date_str,
            limit=10
        )
        
        if dashboard_data:
            print(f"✅ 成功轉換 {len(dashboard_data)} 筆記錄")
            print(f"📝 第一筆記錄:")
            print(json.dumps(dashboard_data[0], indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  轉換後沒有數據")
        
    except ImportError as e:
        print(f"❌ 無法導入 utils 模組: {e}")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print()

def main():
    """主函數"""
    print()
    print("🚀 開始測試 Transactional Data API")
    print()
    
    # 測試 1: API 健康檢查
    test_api_health()
    
    # 測試 2: 直接測試 API
    test_transactional_data_api()
    
    # 測試 3: 使用 Streamlit API 客戶端
    test_with_streamlit_api_client()
    
    print()
    print("✅ 所有測試完成")
    print()
    
    # 總結
    print("=" * 80)
    print("📋 問題診斷指南")
    print("=" * 80)
    print()
    print("如果看到 422 錯誤，可能的原因：")
    print()
    print("1️⃣  日期格式問題")
    print("   - 確保日期格式為 YYYY-MM-DD")
    print("   - 檢查日期是否有效")
    print()
    print("2️⃣  必需參數缺失")
    print("   - 檢查 API 文檔確認必需參數")
    print("   - 可能需要 start_date 和 end_date")
    print()
    print("3️⃣  參數類型錯誤")
    print("   - limit 應為整數")
    print("   - machine_id 應為字符串")
    print()
    print("4️⃣  API 版本問題")
    print("   - 確認使用的是正確的 API 端點")
    print("   - 檢查 API 是否需要不同的參數格式")
    print()
    print("解決方案：")
    print("   - 查看上面的測試結果找出成功的參數組合")
    print("   - 根據成功的案例調整 utils.py 中的參數")
    print()

if __name__ == "__main__":
    main()

