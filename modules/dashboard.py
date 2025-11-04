import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import random

def dashboard_page():
    """儀表板頁面"""
    st.title("📊 營運儀表板")
    
    # 日期選擇器和模擬數據選項
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=13))
    with col2:
        end_date = st.date_input("結束日期", datetime.now())
    # with col3:
    #     use_demo_data = st.checkbox("使用模擬數據", value=False, help="顯示14天的模擬銷售數據用於展示")
    use_demo_data = False  # 使用真實 API 數據
    
    st.markdown("---")
    
    # 獲取資料
    machines = st.session_state.api.get_machines()
    
    # 獲取銷售資料，使用選擇的日期範圍
    sales_data = []
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    if use_demo_data:
        # 使用模擬數據
        # st.info("🎯 正在顯示14天模擬數據")
        demo_orders = generate_demo_sales_data(start_date, end_date)
        sales_data = convert_orders_to_sales_data(demo_orders)
    else:
        # 使用真實 API 數據（新的轉換方法）
        try:
            with st.spinner("正在載入交易數據..."):
                sales_data = st.session_state.api.get_transactional_data_for_dashboard(
                    start_date_str, 
                    end_date_str,
                    limit=1000  # API 最大限制為 1000
                )
            
            if not sales_data:
                st.info(f"📊 在選定期間 ({start_date_str} 至 {end_date_str}) 沒有交易資料")
            else:
                st.success(f"✅ 成功載入 {len(sales_data)} 筆交易記錄 ({start_date_str} 至 {end_date_str})")
        except AttributeError:
            # 如果方法不存在，提示需要更新 utils.py
            st.error("❌ API 客戶端需要更新。請確認 utils.py 中已添加 get_transactional_data_for_dashboard 方法。")
            st.info("💡 提示：請參考 API整合方案.md 文件")
            sales_data = []
        except Exception as e:
            st.error(f"❌ 載入交易數據失敗：{str(e)}")
            from logger_config import api_logger
            api_logger.error(f"Error loading transactional data for dashboard: {str(e)}")
            sales_data = []
    
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
                        
                        # 格式化圖表
                        fig.update_layout(
                            xaxis_title='日期',
                            yaxis_title='營收 (NT$)',
                            xaxis=dict(
                                tickformat='%Y-%m-%d',
                                tickmode='auto',
                                range=[start_date, end_date]
                            )
                        )
                        
                        st.plotly_chart(fig)
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
                    st.plotly_chart(fig)
                else:
                    # 如果沒有數量欄位，按交易次數統計
                    item_sales = df_sales.groupby(item_field).size().reset_index(name='count')
                    fig = px.pie(item_sales, values='count', names=item_field, title='商品交易次數分布')
                    st.plotly_chart(fig)
            else:
                st.info("📊 無法找到商品名稱欄位，無法顯示銷量圖")
        else:
            st.info("📊 暫無銷售資料")

def generate_demo_sales_data(start_date, end_date):
    """生成14天的真實模擬銷售數據（與 sales_analytics 相同）"""
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
        {'weather': '雨天', 'temp_range': (15, 22), 'sales_multiplier': 1.2},
    ]
    
    # 付款方式
    payment_methods = ['credit_card', 'cash', 'mobile_pay', 'mobile_pay', 'credit_card']
    
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
            base_orders = random.randint(25, 40)
        else:  # 週末
            base_orders = random.randint(10, 20)
        
        # 根據天氣調整訂單量
        daily_orders = int(base_orders * weather_condition['sales_multiplier'])
        
        for _ in range(daily_orders):
            # 生成訂單時間
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
            
            # 根據時間段選擇商品
            if 7 <= hour <= 10:  # 早餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['輕食']]
            elif 11 <= hour <= 14:  # 午餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['主餐']]
            elif 15 <= hour <= 17:  # 下午茶時段
                preferred_items = [item for item in menu_items if item['category'] in ['輕食']]
            else:  # 晚餐時段
                preferred_items = [item for item in menu_items if item['category'] in ['主餐']]
            
            if not preferred_items:
                preferred_items = menu_items
            
            selected_items = random.sample(preferred_items, min(num_items, len(preferred_items)))
            
            order_items = []
            total_amount = 0
            
            for item in selected_items:
                quantity = random.choices([1, 2], weights=[85, 15])[0]
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
                'status': random.choices(['completed', 'cancelled'], weights=[95, 5])[0],
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

def convert_orders_to_sales_data(orders):
    """將訂單數據轉換為 dashboard 所需的銷售數據格式"""
    sales_data = []
    
    for order in orders:
        for item in order['items']:
            sales_record = {
                'timestamp': order['created_at'],
                'created_at': order['created_at'],
                'order_id': order['order_number'],
                'machine_id': order['machine_id'],
                'item_name': item['item_name'],
                'product_name': item['item_name'],
                'quantity': item['quantity'],
                'price': item['unit_price'],
                'amount': item['subtotal'],
                'total_amount': item['subtotal'],
                'status': order['status'],
                'payment_method': order['payment_method'],
                'weather': order['weather'],
                'temperature': order['temperature']
            }
            sales_data.append(sales_record)
    
    return sales_data
