"""
Test file to debug AI recommendations ID mapping issues
Based on the bash test script patterns for comprehensive testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from utils import VendingMachineAPI

def test_ai_health():
    """Test AI API health check"""
    print("===== AI API 健康檢查 =====")
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/ai/health", timeout=10)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Health check failed: {response.text}")
    except Exception as e:
        print(f"Health check error: {str(e)}")
    print()

def test_ai_recommendations_api_response():
    """Test what the actual API response looks like"""
    print("===== Testing AI Recommendations API Response =====")
    
    # Initialize API client
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    try:
        # Test direct API call
        print("1. Testing direct API call...")
        response = requests.get(
            "http://127.0.0.1:8000/api/v1/ai/recommendations",
            headers=api._get_ai_auth_headers(),
            params={"skip": 0, "limit": 100},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            raw_data = response.json()
            print(f"Raw API Response Structure:")
            print(json.dumps(raw_data, indent=2, ensure_ascii=False))
            
            # Check if it's nested
            if isinstance(raw_data, dict):
                print(f"\nResponse is dict with keys: {list(raw_data.keys())}")
                if 'data' in raw_data:
                    recommendations = raw_data['data']
                    print(f"Found {len(recommendations)} recommendations in 'data' field")
                elif 'items' in raw_data:
                    recommendations = raw_data['items']
                    print(f"Found {len(recommendations)} recommendations in 'items' field")
                else:
                    recommendations = raw_data
                    print("Using raw_data as recommendations")
            else:
                recommendations = raw_data
                print("Response is list, using directly")
            
            # Analyze each recommendation
            for i, rec in enumerate(recommendations):
                print(f"\n--- Recommendation {i} ---")
                print(f"Available fields: {list(rec.keys())}")
                
                # Check for ID fields
                id_fields = ['id', 'backend_ref_id', 'recommendation_id']
                found_ids = {}
                for field in id_fields:
                    if field in rec:
                        found_ids[field] = rec[field]
                
                print(f"ID fields found: {found_ids}")
                
                # Test which ID works for status updates
                print("Testing which ID works for status updates...")
                for id_field, id_value in found_ids.items():
                    print(f"  Testing {id_field}: {id_value}")
                    test_response = requests.patch(
                        f"http://127.0.0.1:8000/api/v1/ai/recommendations/{id_value}",
                        headers=api._get_ai_auth_headers(),
                        json={
                            "status": "PENDING",
                            "reviewed_by": "test_user"
                        },
                        timeout=10
                    )
                    print(f"    Status: {test_response.status_code}")
                    if test_response.status_code == 200:
                        print(f"    ✅ {id_field} works for status updates!")
                        break
                    else:
                        print(f"    ❌ {id_field} failed: {test_response.text}")
        
        print("\n2. Testing through VendingMachineAPI wrapper...")
        recommendations = api.get_ai_recommendations()
        print(f"API wrapper returned {len(recommendations)} recommendations")
        
        for i, rec in enumerate(recommendations):
            print(f"\n--- Wrapper Recommendation {i} ---")
            print(f"Available fields: {list(rec.keys())}")
            
            # Test our current ID extraction logic (backend_ref_id first)
            rec_id = None
            for id_field in ['backend_ref_id', 'id', 'recommendation_id']:
                if id_field in rec and rec[id_field] is not None:
                    rec_id = rec[id_field]
                    print(f"Found ID in field '{id_field}': {rec_id}")
                    break
            
            if rec_id is None:
                print("❌ No valid ID found!")
            else:
                print(f"✅ Using ID: {rec_id}")
                
                # Test if this ID works with the update API
                print(f"Testing update API with ID {rec_id}...")
                test_response = requests.patch(
                    f"http://127.0.0.1:8000/api/v1/ai/recommendations/{rec_id}",
                    headers=api._get_ai_auth_headers(),
                    json={
                        "status": "PENDING",
                        "reviewed_by": "test_user"
                    },
                    timeout=10
                )
                print(f"Update test status: {test_response.status_code}")
                if test_response.status_code == 200:
                    print("✅ Status update successful!")
                else:
                    print(f"❌ Update test failed: {test_response.text}")
    
    except Exception as e:
        print(f"Error during testing: {str(e)}")

def test_create_recommendation():
    """Test creating a recommendation and see what ID is returned"""
    print("\n===== Testing Create Recommendation =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    test_data = {
        "recommendation_id": "TEST-DEBUG-001",
        "ai_model_version": "debug-v1.0",
        "target_machine_ids": ["1"],
        "recommendation_type": "DYNAMIC_MENU",
        "valid_from": "2025-08-24T00:00:00",
        "valid_until": "2025-08-24T23:59:59",
        "notes": "Debug test recommendation",
        "confidence_score": 0.5,
        "payload": {
            "suggested_menu": [
                {"meal_id": "TEST", "suggested_price": 100.0, "priority": 1}
            ]
        }
    }
    
    try:
        # Test direct API call
        response = requests.post(
            "http://127.0.0.1:8000/api/v1/ai/recommendations",
            headers=api._get_ai_auth_headers(),
            json=test_data,
            timeout=10
        )
        
        print(f"Create status: {response.status_code}")
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"Create response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Test if we can find and update the created recommendation
            if 'backend_ref_id' in result:
                backend_ref_id = result['backend_ref_id']
                print(f"\nTesting status update with created backend_ref_id: {backend_ref_id}")
                
                update_response = requests.patch(
                    f"http://127.0.0.1:8000/api/v1/ai/recommendations/{backend_ref_id}",
                    headers=api._get_ai_auth_headers(),
                    json={
                        "status": "APPROVED",
                        "reviewed_by": "test_user"
                    },
                    timeout=10
                )
                print(f"Update status: {update_response.status_code}")
                if update_response.status_code == 200:
                    print("✅ Successfully updated created recommendation!")
                else:
                    print(f"❌ Failed to update: {update_response.text}")
        else:
            print(f"Create failed: {response.text}")
    
    except Exception as e:
        print(f"Error during create test: {str(e)}")

def test_status_filtering():
    """Test status filtering functionality"""
    print("\n===== Testing Status Filtering =====")
    
    api = VendingMachineAPI("http://127.0.0.1:8000/api/v1")
    
    statuses = ['PENDING', 'APPROVED', 'REJECTED']
    
    for status in statuses:
        try:
            print(f"Testing status filter: {status}")
            response = requests.get(
                "http://127.0.0.1:8000/api/v1/ai/recommendations",
                headers=api._get_ai_auth_headers(),
                params={"status_filter": status},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('data', [])
                print(f"  Found {len(recommendations)} recommendations with status {status}")
                
                # Verify all returned recommendations have the correct status
                for rec in recommendations:
                    if rec.get('status') != status:
                        print(f"  ❌ Status mismatch: expected {status}, got {rec.get('status')}")
                    else:
                        print(f"  ✅ Status filter working correctly")
                        break
            else:
                print(f"  ❌ Status filter failed: {response.status_code}")
        
        except Exception as e:
            print(f"  Error testing status {status}: {str(e)}")

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("===== AI 推薦系統綜合測試 =====\n")
    
    test_ai_health()
    test_ai_recommendations_api_response()
    test_create_recommendation()
    test_status_filtering()
    
    print("\n===== 測試完成 =====")

if __name__ == "__main__":
    run_comprehensive_test()
