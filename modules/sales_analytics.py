import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import random
import uuid

def sales_analytics_page():
    """銷售分析頁面"""
    st.title("📈 銷售分析")
    
    # 日期選擇和選項
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    with col3:
        use_demo_data = st.checkbox("使用示例資料", help="當API沒有資料時，顯示示例資料以展示功能")
    
    # 獲取訂單資料
    try:
        with st.spinner("正在載入銷售資料..."):
            if use_demo_data:
                orders_data = generate_demo_data(start_date, end_date)
                st.info("🎯 正在使用示例資料展示功能")
            else:
                orders_data = get_orders_data(start_date, end_date)
            
        if not orders_data:
            if not use_demo_data:
                st.warning("所選日期範圍內沒有銷售資料")
                st.info("💡 提示：您可以勾選「使用示例資料」來查看功能展示")
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
        display_analytics_tabs(processed_data, start_date, end_date)
        
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
                    row.update({
                        'item_id': item['menu_item_id'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'subtotal': item['subtotal'],
                        'item_name': get_item_name(item['menu_item_id'])  # 獲取商品名稱
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

def display_analytics_tabs(df, start_date, end_date):
    """顯示分析圖表標籤頁"""
    tab1, tab2, tab3, tab4 = st.tabs(["時間趨勢", "商品分析", "機台比較", "詳細資料"])
    
    with tab1:
        display_time_trends(df, start_date, end_date)
    
    with tab2:
        display_product_analysis(df)
    
    with tab3:
        display_machine_comparison(df)
        
    with tab4:
        display_detailed_data(df)

def display_time_trends(df, start_date, end_date):
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
    
    # 設定X軸範圍與使用者選擇的日期範圍連動
    fig.update_layout(
        xaxis_title="日期", 
        yaxis_title="營收 (NT$)",
        xaxis=dict(
            range=[start_date, end_date],
            type='date'
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 每小時銷售分布
    hourly_stats = df.groupby('hour').agg({
        'subtotal': 'sum',
        'quantity': 'sum'
    }).reset_index()
    
    fig = px.bar(hourly_stats, x='hour', y='subtotal', 
                 title='每小時營收分布',
                 labels={'subtotal': '營收 (NT$)', 'hour': '小時'})
    fig.update_layout(xaxis_title="小時", yaxis_title="營收 (NT$)")
    st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.pie(item_stats.head(10), values='subtotal', names='item_name', 
                     title='營收占比 (前10名)')
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(machine_stats, x='machine_id', y='orders', 
                     title='各機台訂單數比較',
                     labels={'orders': '訂單數', 'machine_id': '機台ID'})
        st.plotly_chart(fig, use_container_width=True)
    
    # 機台詳細統計表
    st.subheader("機台統計摘要")
    st.dataframe(machine_stats, width='stretch')

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
        width='stretch'
    )

def generate_demo_data(start_date, end_date):
    """生成示例銷售資料"""
    demo_orders = []
    
    # 計算日期範圍
    current_date = start_date
    order_counter = 1
    
    while current_date <= end_date:
        # 每天生成1-5筆訂單
        daily_orders = random.randint(1, 5)
        
        for _ in range(daily_orders):
            # 隨機時間
            hour = random.randint(8, 22)
            minute = random.randint(0, 59)
            
            # 創建訂單時間
            order_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
            
            # 生成訂單
            order = {
                'id': order_counter,
                'order_number': f'DEMO-{order_counter:06d}',
                'machine_id': random.choice(['DEMO-001', 'DEMO-002', 'DEMO-003']),
                'total_amount': 0,  # 會在後面計算
                'status': random.choice(['completed', 'completed', 'completed', 'cancelled']),
                'payment_status': 'paid',
                'payment_method': random.choice(['credit_card', 'cash', 'mobile_pay']),
                'weather': random.choice(['晴天', '陰天', '雨天']),
                'temperature': random.randint(15, 35),
                'created_at': order_time.isoformat() + 'Z',
                'items': []
            }
            
            # 生成訂單項目
            num_items = random.randint(1, 3)
            total_amount = 0
            
            for item_idx in range(num_items):
                menu_item_id = random.choice(['A', 'B', 'C', 'D', 'E'])
                quantity = random.randint(1, 2)
                unit_price = random.choice([50, 60, 80, 100, 120])
                subtotal = quantity * unit_price
                total_amount += subtotal
                
                item = {
                    'menu_item_id': menu_item_id,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': subtotal
                }
                order['items'].append(item)
            
            order['total_amount'] = total_amount
            demo_orders.append(order)
            order_counter += 1
        
        current_date += timedelta(days=1)
    
    return demo_orders

def get_item_name(menu_item_id):
    """根據商品ID獲取商品名稱"""
    item_names = {
        'A': '經典便當',
        'B': '健康沙拉',
        'C': '熱湯麵條',
        'D': '三明治',
        'E': '飲料'
    }
    return item_names.get(menu_item_id, f"商品 {menu_item_id}")

