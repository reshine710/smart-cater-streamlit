import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

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
