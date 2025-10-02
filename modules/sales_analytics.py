import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

def sales_analytics_page():
    """銷售分析頁面"""
    st.title("📈 銷售分析")
    st.set_page_config(layout="wide",initial_sidebar_state="expanded")
    
    # 日期選擇
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    
    # 獲取訂單資料
    try:
        with st.spinner("正在載入銷售資料..."):
            orders_data = get_orders_data(start_date, end_date)
            
        if not orders_data:
            st.warning("所選日期範圍內沒有銷售資料")
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
                    row.update({
                        'item_id': item['menu_item_id'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'subtotal': item['subtotal'],
                        'item_name': f"商品 {item['menu_item_id']}"  # 預設名稱，實際應從menu_item獲取
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
    st.dataframe(machine_stats, use_container_width=True)

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
        use_container_width=True
    )

