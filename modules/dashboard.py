import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

def dashboard_page():
    """儀表板頁面"""
    st.title("📊 營運儀表板")
    
    # 日期選擇器
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    with col3:
        st.write("")  # 空白欄位用於對齊
    
    st.markdown("---")
    
    # 獲取資料
    machines = st.session_state.api.get_machines()
    
    # 獲取銷售資料，使用選擇的日期範圍
    sales_data = []
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    try:
        sales_data = st.session_state.api.get_sales_data(start_date_str, end_date_str)
        if not sales_data:
            # 嘗試使用交易數據作為備用
            try:
                sales_data = st.session_state.api.get_transactional_data(start_date_str, end_date_str, limit=1000)
                if sales_data:
                    st.info(f"📊 使用交易數據顯示銷售統計 ({start_date_str} 至 {end_date_str})")
                else:
                    st.info(f"📊 在選定期間 ({start_date_str} 至 {end_date_str}) 沒有銷售或交易資料")
            except Exception:
                st.info("📊 目前沒有銷售資料，或相關 API 端點尚未配置")
    except Exception as e:
        st.info("📊 目前沒有銷售資料，或相關 API 端點尚未配置")
    
    # 統計卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        online_machines = len([m for m in machines if m['status'] == 'online'])
        st.metric("線上機台", f"{online_machines}/{len(machines)}")
    
    with col2:
        if sales_data:
            # 嘗試不同的欄位組合來計算營收
            total_sales = 0
            for s in sales_data:
                # 嘗試不同的價格和數量欄位名稱
                price = s.get('price', s.get('amount', s.get('total_amount', 0)))
                quantity = s.get('quantity', s.get('count', 1))
                total_sales += price * quantity
            
            # 根據日期範圍調整標籤
            days_diff = (end_date - start_date).days + 1
            if days_diff == 1:
                revenue_label = "當日營收"
            elif days_diff <= 7:
                revenue_label = f"{days_diff}日營收"
            else:
                revenue_label = f"期間營收 ({days_diff}日)"
            
            st.metric(revenue_label, f"NT$ {total_sales:,.0f}")
        else:
            st.metric("期間營收", "NT$ 0")
    
    with col3:
        total_transactions = len(sales_data) if sales_data else 0
        days_diff = (end_date - start_date).days + 1
        if days_diff == 1:
            transaction_label = "當日交易"
        else:
            transaction_label = f"期間交易 ({days_diff}日)"
        st.metric(transaction_label, f"{total_transactions}")
    
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
            for field in ['timestamp', 'created_at', 'order_date', 'date', 'transaction_time', 'order_time']:
                if field in df_sales.columns:
                    timestamp_field = field
                    break
            
            if timestamp_field:
                try:
                    # 嘗試解析時間戳
                    df_sales['timestamp'] = pd.to_datetime(df_sales[timestamp_field])
                    df_sales['date'] = df_sales['timestamp'].dt.date
                    
                    # 根據選擇的日期範圍過濾數據
                    df_sales = df_sales[
                        (df_sales['date'] >= start_date) & 
                        (df_sales['date'] <= end_date)
                    ]
                    
                    if len(df_sales) == 0:
                        st.info(f"📊 在選定期間 ({start_date_str} 至 {end_date_str}) 沒有銷售資料")
                    else:
                        # 計算每筆交易的總金額
                        df_sales['total_amount'] = 0
                        for idx, row in df_sales.iterrows():
                            price = row.get('price', row.get('amount', row.get('total_amount', 0)))
                            quantity = row.get('quantity', row.get('count', 1))
                            df_sales.at[idx, 'total_amount'] = price * quantity
                        
                        daily_sales = df_sales.groupby('date').agg({
                            'total_amount': 'sum'
                        }).reset_index()
                        
                        # 確保日期格式正確
                        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
                        
                        fig = px.line(daily_sales, x='date', y='total_amount', 
                                     title=f'每日營收趨勢 ({start_date_str} 至 {end_date_str})',
                                     labels={'total_amount': '營收 (NT$)', 'date': '日期'})
                        fig.update_yaxis(title='營收 (NT$)')
                        fig.update_xaxis(title='日期')
                        
                        # 格式化 x 軸日期顯示
                        fig.update_layout(
                            xaxis=dict(
                                tickformat='%Y-%m-%d',
                                tickmode='auto',
                                range=[start_date, end_date]  # 設定 X 軸範圍
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"時間戳解析錯誤: {str(e)}")
                    # 顯示原始時間戳格式以便調試
                    st.write("原始時間戳範例:", df_sales[timestamp_field].head().tolist())
                    st.info("📊 無法解析時間戳格式，無法顯示趨勢圖")
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
            for field in ['item_name', 'product_name', 'name', 'menu_item_name', 'product', 'item']:
                if field in df_sales.columns:
                    item_field = field
                    break
            
            if item_field:
                # 找到數量欄位
                quantity_field = None
                for field in ['quantity', 'count', 'amount']:
                    if field in df_sales.columns:
                        quantity_field = field
                        break
                
                if quantity_field:
                    item_sales = df_sales.groupby(item_field)[quantity_field].sum().reset_index()
                    fig = px.pie(item_sales, values=quantity_field, names=item_field, title='商品銷量分布')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # 如果沒有數量欄位，按交易次數統計
                    item_sales = df_sales.groupby(item_field).size().reset_index(name='count')
                    fig = px.pie(item_sales, values='count', names=item_field, title='商品交易次數分布')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 無法找到商品名稱欄位，無法顯示銷量圖")
        else:
            st.info("📊 暫無銷售資料")
