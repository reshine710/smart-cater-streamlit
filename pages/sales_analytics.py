import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

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
