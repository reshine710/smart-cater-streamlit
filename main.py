import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import requests
from typing import Dict, List, Optional

# 設定頁面配置
st.set_page_config(
    page_title="智慧販賣機後台管理系統",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def login_page():
    """登入頁面"""
    st.title("🏪 智慧販賣機後台管理系統")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 系統登入")
        
        with st.form("login_form"):
            username = st.text_input("使用者名稱", placeholder="請輸入使用者名稱")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            submit_button = st.form_submit_button("登入", use_container_width=True)
            
            if submit_button:
                if username and password:
                    result = st.session_state.api.login(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.token = result["access_token"]
                        st.session_state.username = username
                        st.session_state.api = VendingMachineAPI(API_BASE_URL, result["access_token"])
                        st.success("登入成功！")
                        st.rerun()
                    else:
                        st.error("登入失敗，請檢查帳號密碼")
                else:
                    st.warning("請輸入使用者名稱和密碼")
        
        st.info("💡 測試帳號: admin / admin123")

def logout():
    """登出功能"""
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.api = VendingMachineAPI(API_BASE_URL)
    st.rerun()

def dashboard_page():
    """儀表板頁面"""
    st.title("📊 營運儀表板")
    
    # 獲取資料
    machines = st.session_state.api.get_machines()
    sales_data = st.session_state.api.get_sales_data(
        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        datetime.now().strftime("%Y-%m-%d")
    )
    
    # 統計卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        online_machines = len([m for m in machines if m['status'] == 'online'])
        st.metric("線上機台", f"{online_machines}/{len(machines)}")
    
    with col2:
        total_sales = sum([s['quantity'] * s['price'] for s in sales_data])
        st.metric("今日營收", f"NT$ {total_sales:,.0f}")
    
    with col3:
        total_transactions = len(sales_data)
        st.metric("交易筆數", f"{total_transactions}")
    
    with col4:
        avg_temp = np.mean([m['temperature'] for m in machines if m['temperature']])
        st.metric("平均溫度", f"{avg_temp:.1f}°C")
    
    st.markdown("---")
    
    # 圖表區域
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 銷售趨勢")
        df_sales = pd.DataFrame(sales_data)
        df_sales['timestamp'] = pd.to_datetime(df_sales['timestamp'])
        df_sales['date'] = df_sales['timestamp'].dt.date
        daily_sales = df_sales.groupby('date').agg({
            'quantity': 'sum',
            'price': lambda x: (x * df_sales.loc[x.index, 'quantity']).sum()
        }).reset_index()
        
        fig = px.line(daily_sales, x='date', y='price', title='每日營收趨勢')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🥤 商品銷量")
        item_sales = df_sales.groupby('item_name')['quantity'].sum().reset_index()
        fig = px.pie(item_sales, values='quantity', names='item_name', title='商品銷量分布')
        st.plotly_chart(fig, use_container_width=True)

def machine_status_page():
    """機台狀態頁面"""
    st.title("🖥️ 機台狀態監控")
    
    machines = st.session_state.api.get_machines()
    
    # 狀態總覽
    col1, col2, col3 = st.columns(3)
    
    status_counts = {}
    for machine in machines:
        status = machine['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    with col1:
        st.metric("🟢 線上", status_counts.get('online', 0))
    with col2:
        st.metric("🟡 維護中", status_counts.get('maintenance', 0))
    with col3:
        st.metric("🔴 離線", status_counts.get('offline', 0))
    
    st.markdown("---")
    
    # 機台詳細狀態
    st.subheader("機台詳細狀態")
    
    for machine in machines:
        with st.expander(f"📍 {machine['name']} ({machine['machine_code']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = {
                    'online': '🟢',
                    'maintenance': '🟡',
                    'offline': '🔴'
                }
                st.write(f"**狀態**: {status_color.get(machine['status'], '⚪')} {machine['status']}")
                st.write(f"**位置**: {machine['location']}")
            
            with col2:
                if machine['temperature']:
                    st.write(f"**溫度**: {machine['temperature']}°C")
                else:
                    st.write("**溫度**: N/A")
                st.write(f"**最後心跳**: {machine['last_heartbeat']}")
            
            with col3:
                if st.button(f"發送重啟命令", key=f"restart_{machine['id']}"):
                    st.success(f"已發送重啟命令至 {machine['name']}")
                if st.button(f"設為維護模式", key=f"maintenance_{machine['id']}"):
                    st.info(f"{machine['name']} 已設為維護模式")

def menu_management_page():
    """菜單管理頁面"""
    st.title("🍽️ 菜單管理")
    
    tab1, tab2 = st.tabs(["固定菜單", "AI 動態菜單"])
    
    with tab1:
        st.subheader("固定菜單設定")
        
        menu_items = st.session_state.api.get_menu_items()
        
        # 新增菜單項目
        with st.expander("➕ 新增菜單項目"):
            with st.form("add_menu_item"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("商品名稱")
                    new_price = st.number_input("價格", min_value=0.0, step=1.0)
                    new_category = st.selectbox("分類", ["飲品", "主食", "點心"])
                
                with col2:
                    new_cooking_method = st.selectbox("加熱方式", ["蒸氣", "微波"])
                    new_image_url = st.text_input("圖片網址")
                    new_is_active = st.checkbox("啟用", value=True)
                
                if st.form_submit_button("新增商品"):
                    st.success(f"已新增商品: {new_name}")
        
        # 現有菜單項目
        st.subheader("現有菜單項目")
        
        for item in menu_items:
            with st.expander(f"{'✅' if item['is_active'] else '❌'} {item['name']} - NT$ {item['price']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**分類**: {item['category']}")
                    st.write(f"**加熱方式**: {item['cooking_method']}")
                
                with col2:
                    st.write(f"**價格**: NT$ {item['price']}")
                    st.write(f"**狀態**: {'啟用' if item['is_active'] else '停用'}")
                
                with col3:
                    if st.button(f"編輯", key=f"edit_{item['id']}"):
                        st.info("編輯功能")
                    if item['is_active']:
                        if st.button(f"停用", key=f"deactivate_{item['id']}"):
                            st.warning(f"{item['name']} 已停用")
                    else:
                        if st.button(f"啟用", key=f"activate_{item['id']}"):
                            st.success(f"{item['name']} 已啟用")
    
    with tab2:
        st.subheader("AI 動態菜單")
        
        # 模擬 AI 推薦
        st.info("🤖 AI 分析結果")
        
        ai_recommendations = [
            {
                "item_name": "拿鐵咖啡",
                "suggested_price": 80,
                "confidence": 0.85,
                "reason": "根據天氣預報，明日氣溫較低，熱飲需求預期上升"
            },
            {
                "item_name": "雞肉便當",
                "suggested_price": 125,
                "confidence": 0.72,
                "reason": "午餐時段銷量穩定，建議微調價格"
            }
        ]
        
        for rec in ai_recommendations:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{rec['item_name']}**")
                    st.write(f"推薦理由: {rec['reason']}")
                
                with col2:
                    st.write(f"建議價格: NT$ {rec['suggested_price']}")
                    st.write(f"信心度: {rec['confidence']:.0%}")
                
                with col3:
                    if st.button(f"採用建議", key=f"adopt_{rec['item_name']}"):
                        st.success(f"已採用 {rec['item_name']} 的 AI 建議")
                    if st.button(f"拒絕", key=f"reject_{rec['item_name']}"):
                        st.info(f"已拒絕 {rec['item_name']} 的建議")
                
                st.markdown("---")

def recipe_settings_page():
    """配方設定頁面"""
    st.title("⚙️ 配方設定")
    
    menu_items = st.session_state.api.get_menu_items()
    
    # 選擇商品
    selected_item = st.selectbox(
        "選擇商品",
        options=menu_items,
        format_func=lambda x: f"{x['name']} ({x['cooking_method']})"
    )
    
    if selected_item:
        st.subheader(f"🍽️ {selected_item['name']} 加熱參數設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**加熱方式**: {selected_item['cooking_method']}")
            
            if selected_item['cooking_method'] == '蒸氣':
                steam_temp = st.slider("蒸氣溫度 (°C)", 80, 120, 100)
                steam_time = st.slider("加熱時間 (秒)", 30, 300, 120)
                steam_pressure = st.slider("蒸氣壓力 (bar)", 1.0, 3.0, 1.5, 0.1)
                
                st.json({
                    "cooking_method": "steam",
                    "temperature": steam_temp,
                    "time_seconds": steam_time,
                    "pressure_bar": steam_pressure
                })
            
            else:  # 微波
                microwave_power = st.slider("微波功率 (%)", 30, 100, 80)
                microwave_time = st.slider("加熱時間 (秒)", 30, 180, 90)
                
                st.json({
                    "cooking_method": "microwave",
                    "power_percent": microwave_power,
                    "time_seconds": microwave_time
                })
        
        with col2:
            st.subheader("預覽效果")
            
            # 模擬加熱過程
            if st.button("🔥 模擬加熱過程"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                import time
                for i in range(101):
                    progress_bar.progress(i)
                    if i < 30:
                        status_text.text(f"預熱中... {i}%")
                    elif i < 80:
                        status_text.text(f"加熱中... {i}%")
                    else:
                        status_text.text(f"完成中... {i}%")
                    time.sleep(0.02)
                
                st.success("✅ 加熱完成！")
        
        # 儲存設定
        if st.button("💾 儲存配方設定", use_container_width=True):
            st.success(f"已儲存 {selected_item['name']} 的配方設定")

def sales_analytics_page():
    """銷售分析頁面"""
    st.title("📈 銷售分析")
    
    # 日期選擇
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    
    # 獲取銷售資料
    sales_data = st.session_state.api.get_sales_data(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )
    
    df = pd.DataFrame(sales_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['revenue'] = df['quantity'] * df['price']
    
    # 統計摘要
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_revenue = df['revenue'].sum()
        st.metric("總營收", f"NT$ {total_revenue:,.0f}")
    
    with col2:
        total_quantity = df['quantity'].sum()
        st.metric("總銷量", f"{total_quantity} 件")
    
    with col3:
        avg_order_value = df['revenue'].mean()
        st.metric("平均客單價", f"NT$ {avg_order_value:.0f}")
    
    with col4:
        unique_customers = len(df)
        st.metric("交易筆數", f"{unique_customers}")
    
    st.markdown("---")
    
    # 圖表分析
    tab1, tab2, tab3 = st.tabs(["時間趨勢", "商品分析", "機台比較"])
    
    with tab1:
        # 每日營收趨勢
        df['date'] = df['timestamp'].dt.date
        daily_stats = df.groupby('date').agg({
            'revenue': 'sum',
            'quantity': 'sum'
        }).reset_index()
        
        fig = px.line(daily_stats, x='date', y='revenue', title='每日營收趨勢')
        st.plotly_chart(fig, use_container_width=True)
        
        # 每小時銷售分布
        df['hour'] = df['timestamp'].dt.hour
        hourly_stats = df.groupby('hour')['revenue'].sum().reset_index()
        
        fig = px.bar(hourly_stats, x='hour', y='revenue', title='每小時營收分布')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # 商品銷量排行
        item_stats = df.groupby('item_name').agg({
            'quantity': 'sum',
            'revenue': 'sum'
        }).reset_index().sort_values('revenue', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(item_stats, x='item_name', y='quantity', title='商品銷量排行')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(item_stats, values='revenue', names='item_name', title='營收占比')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # 機台比較
        machine_stats = df.groupby('machine_id').agg({
            'quantity': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        fig = px.bar(machine_stats, x='machine_id', y='revenue', title='各機台營收比較')
        st.plotly_chart(fig, use_container_width=True)
        
        # 詳細資料表
        st.subheader("詳細銷售資料")
        st.dataframe(df.sort_values('timestamp', ascending=False), use_container_width=True)

def main():
    """主程式"""
    init_session_state()
    
    # 檢查登入狀態
    if not st.session_state.logged_in:
        login_page()
        return
    
    # 側邊欄
    with st.sidebar:
        st.title("🏪 智慧販賣機")
        st.write(f"歡迎, {st.session_state.username}")
        
        if st.button("🚪 登出"):
            logout()
        
        st.markdown("---")
        
        # 導航選單
        page = st.selectbox(
            "選擇頁面",
            [
                "📊 營運儀表板",
                "🖥️ 機台狀態監控",
                "🍽️ 菜單管理",
                "⚙️ 配方設定",
                "📈 銷售分析"
            ]
        )
        
        st.markdown("---")
        st.markdown("### 🔧 系統資訊")
        st.info(f"API: {API_BASE_URL}")
        st.info(f"版本: v1.0.0")
    
    # 主要內容區域
    if page == "📊 營運儀表板":
        dashboard_page()
    elif page == "🖥️ 機台狀態監控":
        machine_status_page()
    elif page == "🍽️ 菜單管理":
        menu_management_page()
    elif page == "⚙️ 配方設定":
        recipe_settings_page()
    elif page == "📈 銷售分析":
        sales_analytics_page()

if __name__ == "__main__":
    main()
