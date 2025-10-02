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
    sales_data = st.session_state.api.get_sales_data()
    
    # 統計卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        online_machines = len([m for m in machines if m['status'] == 'online'])
        st.metric("線上機台", f"{online_machines}/{len(machines)}")
    
    with col2:
        if sales_data:
            total_sales = sum([s.get('quantity', 0) * s.get('price', 0) for s in sales_data])
            st.metric("今日營收", f"NT$ {total_sales:,.0f}")
        else:
            st.metric("今日營收", "NT$ 0")
    
    with col3:
        total_transactions = len(sales_data) if sales_data else 0
        st.metric("交易筆數", f"{total_transactions}")
    
    with col4:
        temps = [m['temperature'] for m in machines if m.get('temperature')]
        if temps:
            avg_temp = np.mean(temps)
            st.metric("平均溫度", f"{avg_temp:.1f}°C")
        else:
            st.metric("平均溫度", "N/A")
    
    st.markdown("---")
    
    # 圖表區域
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 銷售趨勢")
        if sales_data:
            df_sales = pd.DataFrame(sales_data)
            
            # 處理不同的時間戳欄位名稱
            timestamp_field = None
            for field in ['timestamp', 'created_at', 'order_date', 'date']:
                if field in df_sales.columns:
                    timestamp_field = field
                    break
            
            if timestamp_field:
                df_sales['timestamp'] = pd.to_datetime(df_sales[timestamp_field])
                df_sales['date'] = df_sales['timestamp'].dt.date
                daily_sales = df_sales.groupby('date').agg({
                    'quantity': 'sum',
                    'price': lambda x: (x * df_sales.loc[x.index, 'quantity']).sum()
                }).reset_index()
                
                fig = px.line(daily_sales, x='date', y='price', title='每日營收趨勢')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 無法找到時間戳欄位，無法顯示趨勢圖")
        else:
            st.info("📊 暫無銷售資料")
    
    with col2:
        st.subheader("🥤 商品銷量")
        if sales_data:
            df_sales = pd.DataFrame(sales_data)
            
            # 處理不同的商品名稱欄位
            item_field = None
            for field in ['item_name', 'product_name', 'name']:
                if field in df_sales.columns:
                    item_field = field
                    break
            
            if item_field:
                item_sales = df_sales.groupby(item_field)['quantity'].sum().reset_index()
                fig = px.pie(item_sales, values='quantity', names=item_field, title='商品銷量分布')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 無法找到商品名稱欄位，無法顯示銷量圖")
        else:
            st.info("📊 暫無銷售資料")
