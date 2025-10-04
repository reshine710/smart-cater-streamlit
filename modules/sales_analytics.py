import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import random

def sales_analytics_page():
    """銷售分析頁面"""
    st.title("📈 銷售分析")
    
    # 日期選擇和模式選擇
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=13))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    with col3:
        use_demo_data = st.checkbox("使用模擬數據", value=False, help="顯示14天的模擬銷售數據用於展示")
    
    # 獲取訂單資料
    try:
        with st.spinner("正在載入銷售資料..."):
            if use_demo_data:
                st.info("🎯 正在顯示14天模擬數據")
                orders_data = generate_demo_sales_data(start_date, end_date)
            else:
                orders_data = get_orders_data(start_date, end_date)
            
        if not orders_data:
            st.warning("所選日期範圍內沒有銷售資料")
            if not use_demo_data:
                st.info("💡 提示：您可以勾選「使用模擬數據」查看功能展示")
            return
            
        # 處理訂單資料
        processed_data = process_orders_data(orders_data)
        
        if processed_data.empty:
            st.warning("無法處理銷售資料")
            return
            
        # 顯示統計摘要
        display_summary_metrics(processed_data)
        
        st.markdown("---")
        
        # 圖表分析
        display_analytics_tabs(processed_data)
        
    except Exception as e:
        st.error(f"載入銷售資料時發生錯誤: {str(e)}")
        st.info("請檢查API連線狀態或聯繫系統管理員")

def get_orders_data(start_date, end_date):
    """獲取訂單資料"""
    try:
        # 使用session state中的API客戶端
        if hasattr(st.session_state, 'api') and st.session_state.api:
            # 嘗試使用API客戶端獲取訂單
            orders = st.session_state.api.get_orders(skip=0, limit=1000)
        else:
            # 如果沒有API客戶端，返回空資料
            st.warning("API連線未建立，請先登入")
            return []
            
        # 過濾日期範圍
        filtered_orders = []
        for order in orders:
            order_date = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')).date()
            if start_date <= order_date <= end_date:
                filtered_orders.append(order)
                
        return filtered_orders
        
    except Exception as e:
        st.error(f"獲取訂單資料失敗: {str(e)}")
        return []

def process_orders_data(orders_data):
    """處理訂單資料轉換為分析用的DataFrame"""
    try:
        processed_rows = []
        
        for order in orders_data:
            # 基本訂單資訊
            order_info = {
                'order_id': order['id'],
                'order_number': order['order_number'],
                'machine_id': order['machine_id'],
                'total_amount': order['total_amount'],
                'status': order['status'],
                'payment_status': order['payment_status'],
                'payment_method': order['payment_method'],
                'weather': order.get('weather', '未知'),
                'temperature': order.get('temperature', 0),
                'created_at': pd.to_datetime(order['created_at']),
                'date': pd.to_datetime(order['created_at']).date(),
                'hour': pd.to_datetime(order['created_at']).hour
            }
            
            # 處理訂單項目
            if order.get('items'):
                for item in order['items']:
                    row = order_info.copy()
                    # 如果模擬數據中已有商品名稱則使用，否則從API獲取或使用預設
                    item_name = item.get('item_name') or get_item_name_from_api(item['menu_item_id'])
                    row.update({
                        'item_id': item['menu_item_id'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'subtotal': item['subtotal'],
                        'item_name': item_name
                    })
                    processed_rows.append(row)
            else:
                # 沒有項目的訂單也要記錄
                order_info.update({
                    'item_id': None,
                    'quantity': 0,
                    'unit_price': 0,
                    'subtotal': order['total_amount'],
                    'item_name': '未知商品'
                })
                processed_rows.append(order_info)
        
        df = pd.DataFrame(processed_rows)
        return df
        
    except Exception as e:
        st.error(f"處理訂單資料時發生錯誤: {str(e)}")
        return pd.DataFrame()

def display_summary_metrics(df):
    """顯示統計摘要"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_revenue = df['subtotal'].sum()
        st.metric("總營收", f"NT$ {total_revenue:,.0f}")
    
    with col2:
        total_quantity = df['quantity'].sum()
        st.metric("總銷量", f"{total_quantity} 件")
    
    with col3:
        unique_orders = df['order_id'].nunique()
        avg_order_value = total_revenue / unique_orders if unique_orders > 0 else 0
        st.metric("平均客單價", f"NT$ {avg_order_value:.0f}")
    
    with col4:
        st.metric("交易筆數", f"{unique_orders}")

def display_analytics_tabs(df):
    """顯示分析圖表標籤頁"""
    tab1, tab2, tab3, tab4 = st.tabs(["時間趨勢", "商品分析", "機台比較", "詳細資料"])
    
    with tab1:
        display_time_trends(df)
    
    with tab2:
        display_product_analysis(df)
    
    with tab3:
        display_machine_comparison(df)
        
    with tab4:
        display_detailed_data(df)

def display_time_trends(df):
    """顯示時間趨勢分析"""
    # 每日營收趨勢
    daily_stats = df.groupby('date').agg({
        'subtotal': 'sum',
        'quantity': 'sum',
        'order_id': 'nunique'
    }).reset_index()
    daily_stats.columns = ['date', 'revenue', 'quantity', 'orders']
    
    fig = px.line(daily_stats, x='date', y='revenue', 
                  title='每日營收趨勢',
                  labels={'revenue': '營收 (NT$)', 'date': '日期'})
    fig.update_layout(xaxis_title="日期", yaxis_title="營收 (NT$)")
    st.plotly_chart(fig)
    
    # 每小時銷售分布
    hourly_stats = df.groupby('hour').agg({
        'subtotal': 'sum',
        'quantity': 'sum'
    }).reset_index()
    
    fig = px.bar(hourly_stats, x='hour', y='subtotal', 
                 title='每小時營收分布',
                 labels={'subtotal': '營收 (NT$)', 'hour': '小時'})
    fig.update_layout(xaxis_title="小時", yaxis_title="營收 (NT$)")
    st.plotly_chart(fig)

def display_product_analysis(df):
    """顯示商品分析"""
    # 商品銷量和營收統計
    item_stats = df.groupby('item_name').agg({
        'quantity': 'sum',
        'subtotal': 'sum'
    }).reset_index().sort_values('subtotal', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(item_stats.head(10), x='item_name', y='quantity', 
                     title='商品銷量排行 (前10名)',
                     labels={'quantity': '銷量', 'item_name': '商品名稱'})
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig)
    
    with col2:
        fig = px.pie(item_stats.head(10), values='subtotal', names='item_name', 
                     title='營收占比 (前10名)')
        st.plotly_chart(fig)

def display_machine_comparison(df):
    """顯示機台比較分析"""
    # 機台統計
    machine_stats = df.groupby('machine_id').agg({
        'quantity': 'sum',
        'subtotal': 'sum',
        'order_id': 'nunique'
    }).reset_index()
    machine_stats.columns = ['machine_id', 'quantity', 'revenue', 'orders']
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(machine_stats, x='machine_id', y='revenue', 
                     title='各機台營收比較',
                     labels={'revenue': '營收 (NT$)', 'machine_id': '機台ID'})
        st.plotly_chart(fig)
    
    with col2:
        fig = px.bar(machine_stats, x='machine_id', y='orders', 
                     title='各機台訂單數比較',
                     labels={'orders': '訂單數', 'machine_id': '機台ID'})
        st.plotly_chart(fig)
    
    # 機台詳細統計表
    st.subheader("機台統計摘要")
    st.dataframe(machine_stats, )

def display_detailed_data(df):
    """顯示詳細資料"""
    st.subheader("詳細銷售資料")
    
    # 篩選選項
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_machines = st.multiselect(
            "選擇機台", 
            options=df['machine_id'].unique(),
            default=df['machine_id'].unique()
        )
    
    with col2:
        selected_status = st.multiselect(
            "訂單狀態",
            options=df['status'].unique(),
            default=df['status'].unique()
        )
    
    with col3:
        selected_payment = st.multiselect(
            "付款方式",
            options=df['payment_method'].unique(),
            default=df['payment_method'].unique()
        )
    
    # 篩選資料
    filtered_df = df[
        (df['machine_id'].isin(selected_machines)) &
        (df['status'].isin(selected_status)) &
        (df['payment_method'].isin(selected_payment))
    ]
    
    # 顯示篩選後的資料
    display_columns = [
        'order_number', 'machine_id', 'item_name', 'quantity', 
        'unit_price', 'subtotal', 'status', 'payment_method', 'created_at'
    ]
    
    st.dataframe(
        filtered_df[display_columns].sort_values('created_at', ascending=False),
    )

def generate_demo_sales_data(start_date, end_date):
    """生成14天的真實模擬銷售數據"""
    demo_orders = []
    
    # 定義商品類別（台灣傳統料理菜單）
    menu_items = [
        {'id': 59, 'name': '滷味三寶飯套餐', 'price': 125, 'category': '主餐'},
        {'id': 49, 'name': '肉粽套餐', 'price': 100, 'category': '主餐'},
        {'id': 50, 'name': '肉粽輕食套餐', 'price': 80, 'category': '輕食'},
        {'id': 52, 'name': '花枝丸套餐', 'price': 110, 'category': '主餐'},
        {'id': 53, 'name': '花枝米粉套餐', 'price': 90, 'category': '主餐'},
        {'id': 54, 'name': '虱目魚香腸套餐', 'price': 140, 'category': '主餐'},
        {'id': 60, 'name': '蝦捲麵套餐', 'price': 115, 'category': '主餐'},
        {'id': 61, 'name': '雙主食青菜套餐', 'price': 160, 'category': '主餐'},
        {'id': 55, 'name': '香腸肉燥飯套餐', 'price': 85, 'category': '輕食'},
    ]
    
    # 定義機台
    machines = ['VM-001', 'VM-002', 'VM-003', 'VM-004']
    
    # 定義天氣影響
    weather_conditions = [
        {'weather': '晴天', 'temp_range': (20, 28), 'sales_multiplier': 1.0},
        {'weather': '陰天', 'temp_range': (18, 24), 'sales_multiplier': 0.9},
        {'weather': '雨天', 'temp_range': (15, 22), 'sales_multiplier': 1.2},  # 雨天室內消費增加
    ]
    
    # 付款方式
    payment_methods = ['credit_card', 'cash', 'mobile_pay', 'mobile_pay', 'credit_card']  # 偏重電子支付
    
    order_counter = 1
    current_date = start_date
    
    # 生成14天的數據
    while current_date <= end_date:
        # 隨機天氣
        weather_condition = random.choice(weather_conditions)
        temperature = random.randint(*weather_condition['temp_range'])
        
        # 根據星期幾調整訂單量
        weekday = current_date.weekday()
        if weekday < 5:  # 週一到週五
            base_orders = random.randint(25, 40)  # 工作日訂單較多
        else:  # 週末
            base_orders = random.randint(10, 20)  # 週末訂單較少
        
        # 根據天氣調整訂單量
        daily_orders = int(base_orders * weather_condition['sales_multiplier'])
        
        for _ in range(daily_orders):
            # 生成訂單時間（營業時間 7:00-22:00，高峰期為午餐和下午）
            hour_weights = {
                7: 1, 8: 3, 9: 5, 10: 4, 11: 8, 12: 10, 13: 9, 14: 6,
                15: 5, 16: 7, 17: 8, 18: 9, 19: 7, 20: 4, 21: 3, 22: 2
            }
            hour = random.choices(list(hour_weights.keys()), weights=list(hour_weights.values()))[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            order_time = datetime.combine(
                current_date, 
                datetime.min.time().replace(hour=hour, minute=minute, second=second)
            )
            
            # 選擇機台
            machine_id = random.choice(machines)
            
            # 生成訂單項目（1-3個商品）
            num_items = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
            
            # 根據時間段選擇商品（早餐、午餐、下午茶、晚餐）
            if 7 <= hour <= 10:  # 早餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['輕食']]
            elif 11 <= hour <= 14:  # 午餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['主餐']]
            elif 15 <= hour <= 17:  # 下午茶時段
                preferred_items = [item for item in menu_items if item['category'] in ['輕食']]
            else:  # 晚餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['主餐']]
            
            # 從偏好商品中隨機選擇，如果沒有偏好則從全部選擇
            if not preferred_items:
                preferred_items = menu_items
            
            selected_items = random.sample(preferred_items, min(num_items, len(preferred_items)))
            
            order_items = []
            total_amount = 0
            
            for item in selected_items:
                quantity = random.choices([1, 2], weights=[85, 15])[0]  # 大多數是單份
                unit_price = item['price']
                subtotal = quantity * unit_price
                total_amount += subtotal
                
                order_items.append({
                    'menu_item_id': item['id'],
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': subtotal,
                    'item_name': item['name']
                })
            
            # 創建訂單
            order = {
                'id': order_counter,
                'order_number': f'ORD-{order_counter:06d}',
                'machine_id': machine_id,
                'total_amount': total_amount,
                'status': random.choices(['completed', 'cancelled'], weights=[95, 5])[0],  # 95%完成率
                'payment_status': 'paid',
                'payment_method': random.choice(payment_methods),
                'weather': weather_condition['weather'],
                'temperature': temperature,
                'created_at': order_time.isoformat() + 'Z',
                'items': order_items
            }
            
            demo_orders.append(order)
            order_counter += 1
        
        current_date += timedelta(days=1)
    
    return demo_orders

def get_item_name_from_api(item_id):
    """從API獲取商品名稱（如果可用）"""
    try:
        if hasattr(st.session_state, 'api') and st.session_state.api:
            menu_items = st.session_state.api.get_menu_items()
            for item in menu_items:
                if item.get('id') == item_id:
                    return item.get('name', f'商品 {item_id}')
        return f'商品 {item_id}'
    except:
        return f'商品 {item_id}'

