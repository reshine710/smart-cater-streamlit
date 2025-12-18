import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import random
import warnings

DAY_THRESHOLD = 3

def dashboard_page():
    """儀表板頁面"""
    st.title("📊 營運儀表板")
    
    # 日期選擇器和模擬數據選項
    # 預設壓在今天，並提供「今日」快速按鈕
    today = datetime.now().date()
    if 'dashboard_start_date' not in st.session_state:
        st.session_state['dashboard_start_date'] = today
    if 'dashboard_end_date' not in st.session_state:
        st.session_state['dashboard_end_date'] = today
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div style='height: 0px;'></div>", unsafe_allow_html=True)
        st.session_state['dashboard_start_date'] = st.date_input(
            "開始日期", 
            value=st.session_state['dashboard_start_date'],
            key="dashboard_start_date_input"
        )
    with col2:
        st.markdown("<div style='height: 0px;'></div>", unsafe_allow_html=True)
        st.session_state['dashboard_end_date'] = st.date_input(
            "結束日期", 
            value=st.session_state['dashboard_end_date'],
            key="dashboard_end_date_input"
        )
    with col3:
        # 添加空標籤以對齊左側日期輸入框的標籤高度
        st.markdown("<div style='height: 42.5px;'></div>", unsafe_allow_html=True)
        # 添加 CSS 來調整按鈕高度，使其對齊日期輸入框
        # st.markdown("""
        # <style>
        # div[data-testid="column"]:nth-of-type(3) button {
        #     height: 38px !important;
        # }
        # </style>
        # """, unsafe_allow_html=True)
        if st.button("今日", key="today_button", width='stretch'):
            st.session_state['dashboard_start_date'] = today
            st.session_state['dashboard_end_date'] = today
    start_date = st.session_state['dashboard_start_date']
    end_date = st.session_state['dashboard_end_date']
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
                price = (
                    s.get('price')
                    or s.get('amount')
                    or s.get('total_amount')
                    or s.get('unit_price')
                    or s.get('unitPrice')
                    or 0
                )
                quantity = (
                    s.get('quantity')
                    or s.get('count')
                    or s.get('quantity_sold')
                    or s.get('qty')
                    or 1
                )

                subtotal = s.get('subtotal') or s.get('total') or s.get('total_amount')
                if subtotal is None:
                    subtotal = price * quantity
                total_sales += subtotal
            
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
            for field in ['timestamp', 'created_at', 'order_date', 'date', 'transaction_time', 'order_time', 'purchase_timestamp']:
                if field in df_sales.columns:
                    timestamp_field = field
                    break
            
            if timestamp_field:
                try:
                    # 嘗試解析時間戳
                    # 先移除小數秒與尾端 Z，避免混合格式解析失敗
                    df_sales[timestamp_field] = (
                        df_sales[timestamp_field]
                        .astype(str)
                        .str.replace(r'\.\d+', '', regex=True)
                        .str.replace('Z', '', regex=False)
                    )
                    df_sales['timestamp'] = pd.to_datetime(
                        df_sales[timestamp_field],
                        format='mixed',
                        errors='coerce'
                    )
                    df_sales['date'] = df_sales['timestamp'].dt.date
                    
                    # 確保數值欄位為數值型別
                    for col in ['price', 'unit_price', 'amount', 'total_amount', 'quantity', 'qty', 'count', 'quantity_sold', 'subtotal', 'total']:
                        if col in df_sales.columns:
                            df_sales[col] = pd.to_numeric(df_sales[col], errors='coerce')
                    
                    # 根據選擇的日期範圍過濾數據
                    df_sales = df_sales[
                        (df_sales['date'] >= start_date) & 
                        (df_sales['date'] <= end_date)
                    ]
                    
                    if len(df_sales) == 0:
                        st.info(f"📊 在選定期間 ({start_date_str} 至 {end_date_str}) 沒有銷售資料")
                    else:
                        # 計算每筆交易的總金額（保留原始 total_amount，避免被覆蓋成 0）
                        if 'total_amount' in df_sales.columns:
                            orig_total_amount = df_sales['total_amount'].copy()
                        else:
                            orig_total_amount = pd.Series([np.nan] * len(df_sales), index=df_sales.index)
                        
                        computed_totals = []
                        for idx, row in df_sales.iterrows():
                            # 先嘗試已存在的小計/總額欄位
                            candidates_primary = [
                                row.get('subtotal'),
                                row.get('total'),
                                orig_total_amount.iloc[idx],   # 使用原始 total_amount
                                row.get('amount')
                            ]
                            subtotal = next((v for v in candidates_primary if pd.notna(v) and float(v) != 0.0), None)
                            
                            if subtotal is None:
                                # 回退用單價 * 數量
                                price = next((v for v in [
                                    row.get('price'),
                                    row.get('unit_price'),
                                    row.get('unitPrice')
                                ] if pd.notna(v)), 0.0)
                                quantity = next((v for v in [
                                    row.get('quantity'),
                                    row.get('count'),
                                    row.get('quantity_sold'),
                                    row.get('qty')
                                ] if pd.notna(v)), 1.0)
                                subtotal = float(price or 0.0) * float(quantity or 0.0)
                            
                            computed_totals.append(float(subtotal or 0.0))
                        
                        df_sales['total_amount'] = pd.to_numeric(pd.Series(computed_totals, index=df_sales.index), errors='coerce').fillna(0.0)
                        
                        # 保險：轉為數值並填空
                        df_sales['total_amount'] = pd.to_numeric(df_sales['total_amount'], errors='coerce').fillna(0.0)
                        
                        # Debug 區塊（預設隱藏）
                        if False:
                            with st.expander("🔧 調試：查看原始列與加總", expanded=False):
                                cols = [c for c in ['timestamp', 'date', 'item_name', 'quantity', 'unit_price', 'subtotal', 'total', 'amount', 'total_amount'] if c in df_sales.columns]
                                st.write("關鍵欄位（前 10 筆）")
                                st.dataframe(df_sales[cols].head(10))
                                st.write("total_amount 加總：", float(df_sales['total_amount'].sum()))
                                st.caption("提示：若加總為 0，請檢查 quantity/unit_price 是否為非數值或皆為空。")
                        
                        # 依日期範圍動態決定顯示粒度：<DAY_THRESHOLD 天 -> 小時；>=DAY_THRESHOLD 天 -> 日
                        range_days = (end_date - start_date).days + 1
                        if range_days < DAY_THRESHOLD:
                            # 以小時聚合（使用 resample 更穩定）
                            hourly_sales = (
                                df_sales
                                .set_index('timestamp')
                                .resample('h')  # 注意：'H' 將棄用，改用小寫 'h'
                                ['total_amount']
                                .sum()
                                .reset_index()
                            )
                            hourly_sales['timestamp'] = pd.to_datetime(hourly_sales['timestamp'])
                            fig = px.line(
                                hourly_sales, x='timestamp', y='total_amount',
                                title=f'每小時營收趨勢 ({start_date_str})',
                                labels={'total_amount': '營收 (NT$)', 'timestamp': '時間'}
                            )
                        else:
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
                            xaxis_title='時間' if range_days < DAY_THRESHOLD else '日期',
                            yaxis_title='營收 (NT$)',
                            xaxis=dict(
                                tickformat='%Y-%m-%d %H:%M' if range_days < DAY_THRESHOLD else '%Y-%m-%d',
                                tickmode='auto',
                                range=[
                                    (hourly_sales['timestamp'].min() if range_days < DAY_THRESHOLD else daily_sales['date'].min()),
                                    (hourly_sales['timestamp'].max() if range_days < DAY_THRESHOLD else daily_sales['date'].max())
                                ]
                            )
                        )
                        
                        # Plotly 目前會對部份關鍵字參數發出棄用警告，這裡局部關閉該警告避免顯示在畫面上
                        with warnings.catch_warnings():
                            warnings.filterwarnings(
                                "ignore",
                                message=r"The keyword arguments have been deprecated and will be removed in a future release.*",
                                category=UserWarning,
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
            for field in ['item_name', 'product_name', 'name', 'menu_item_name', 'product', 'item', 'meal_id', 'product_code']:
                if field in df_sales.columns:
                    item_field = field
                    break
            
            if item_field:
                # 建立顯示標籤：餐點中文名稱(product_code)，參考 ai_recommendations 的作法
                code_field = 'product_code' if 'product_code' in df_sales.columns else ('meal_id' if 'meal_id' in df_sales.columns else None)
                
                # 從 API 取菜單，建立 product_code/id -> 中文名稱 的映射
                menu_name_mapping = {}
                try:
                    if hasattr(st.session_state, 'api') and st.session_state.api:
                        menu_items = st.session_state.api.get_menu_items()
                        for m in (menu_items or []):
                            if 'product_code' in m and m.get('product_code'):
                                menu_name_mapping[str(m['product_code'])] = m.get('name') or ''
                            if 'id' in m and m.get('id') is not None:
                                menu_name_mapping[str(m['id'])] = m.get('name') or ''
                except Exception:
                    pass
                
                if code_field:
                    # 以 row 為單位生成「中文名(product_code)」，若查不到中文名則用現有 item_field 或代碼
                    def _compose_label(row):
                        code = str(row.get(code_field) or '')
                        name = menu_name_mapping.get(code) or row.get(item_field) or code
                        return f"{name}({code})"
                    df_sales['display_label'] = df_sales.apply(_compose_label, axis=1)
                else:
                    df_sales['display_label'] = df_sales[item_field].astype(str)
                label_field = 'display_label'
                
                # 找到數量欄位
                quantity_field = None
                for field in ['quantity', 'count', 'amount', 'quantity_sold', 'qty']:
                    if field in df_sales.columns:
                        quantity_field = field
                        break
                
                if quantity_field:
                    item_sales = df_sales.groupby(label_field)[quantity_field].sum().reset_index()
                    fig = px.pie(item_sales, values=quantity_field, names=label_field, title='商品銷量分布')
                    # 局部關閉 Plotly 棄用警告，避免黃色提示干擾畫面
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message=r"The keyword arguments have been deprecated and will be removed in a future release.*",
                            category=UserWarning,
                        )
                        st.plotly_chart(fig)
                else:
                    # 如果沒有數量欄位，按交易次數統計
                    item_sales = df_sales.groupby(label_field).size().reset_index(name='count')
                    fig = px.pie(item_sales, values='count', names=label_field, title='商品交易次數分布')
                    # 局部關閉 Plotly 棄用警告，避免黃色提示干擾畫面
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message=r"The keyword arguments have been deprecated and will be removed in a future release.*",
                            category=UserWarning,
                        )
                        st.plotly_chart(fig)
            else:
                st.info("📊 無法找到商品名稱欄位，無法顯示銷量圖")
        else:
            st.info("📊 暫無銷售資料")

    # 排行區域：商品排行與機台排行
    st.markdown("---")
    st.subheader("🏆 銷售排行分析")

    col_rank1, col_rank2 = st.columns(2)

    # 共同：將 transactional data 轉成 DataFrame 並計算單筆交易金額
    def _prepare_sales_df_for_ranking(raw_sales):
        """將 sales_data 轉成 DataFrame，補上 total_amount 與 quantity 欄位，供排行使用"""
        if not raw_sales:
            return None
        df = pd.DataFrame(raw_sales)

        # 嘗試找出時間欄位（部分統計可能需要）
        timestamp_field = None
        for field in ['timestamp', 'created_at', 'order_date', 'date', 'transaction_time', 'order_time', 'purchase_timestamp']:
            if field in df.columns:
                timestamp_field = field
                break

        # 數值欄位轉型
        for col in ['price', 'unit_price', 'unitPrice', 'amount', 'total_amount',
                    'quantity', 'qty', 'count', 'quantity_sold', 'subtotal', 'total']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 計算每筆交易的 total_amount（與上方營收邏輯保持一致）
        if 'total_amount' in df.columns:
            orig_total_amount = df['total_amount'].copy()
        else:
            orig_total_amount = pd.Series([np.nan] * len(df), index=df.index)

        computed_totals = []
        for idx, row in df.iterrows():
            candidates_primary = [
                row.get('subtotal'),
                row.get('total'),
                orig_total_amount.iloc[idx],
                row.get('amount'),
            ]
            subtotal = next((v for v in candidates_primary if pd.notna(v) and float(v) != 0.0), None)
            if subtotal is None:
                price = next((v for v in [
                    row.get('price'),
                    row.get('unit_price'),
                    row.get('unitPrice'),
                ] if pd.notna(v)), 0.0)
                quantity = next((v for v in [
                    row.get('quantity'),
                    row.get('count'),
                    row.get('quantity_sold'),
                    row.get('qty'),
                ] if pd.notna(v)), 1.0)
                subtotal = float(price or 0.0) * float(quantity or 0.0)
            computed_totals.append(float(subtotal or 0.0))

        df['total_amount'] = pd.to_numeric(pd.Series(computed_totals, index=df.index), errors='coerce').fillna(0.0)

        # 統一一個「數量」欄位供後續使用
        quantity_field = None
        for field in ['quantity', 'count', 'quantity_sold', 'qty']:
            if field in df.columns:
                quantity_field = field
                break
        if quantity_field:
            df['__quantity_for_rank'] = pd.to_numeric(df[quantity_field], errors='coerce').fillna(0.0)
        else:
            # 若沒有明確數量欄位，就以每筆交易視為 1
            df['__quantity_for_rank'] = 1.0

        # 依選取日期區間過濾（若有時間欄位）
        if timestamp_field:
            df[timestamp_field] = (
                df[timestamp_field]
                .astype(str)
                .str.replace(r'\.\d+', '', regex=True)
                .str.replace('Z', '', regex=False)
            )
            df['__timestamp'] = pd.to_datetime(df[timestamp_field], format='mixed', errors='coerce')
            df['__date'] = df['__timestamp'].dt.date
            df = df[
                (df['__date'] >= start_date) &
                (df['__date'] <= end_date)
            ]

        if len(df) == 0:
            return None
        return df

    prepared_df = _prepare_sales_df_for_ranking(sales_data) if sales_data else None

    with col_rank1:
        st.markdown("#### 📦 商品銷售排行")
        if prepared_df is None:
            st.info("📊 選定期間內沒有銷售資料，無法產生商品排行")
        else:
            # 商品標籤：中文名稱(product_code)
            item_field = None
            for field in ['item_name', 'product_name', 'name', 'menu_item_name', 'product', 'item', 'meal_id', 'product_code']:
                if field in prepared_df.columns:
                    item_field = field
                    break

            if item_field is None:
                st.info("📊 無法找到商品名稱或代碼欄位，無法產生商品排行")
            else:
                code_field = None
                for field in ['product_code', 'meal_id']:
                    if field in prepared_df.columns:
                        code_field = field
                        break

                # 取菜單，建立 product_code/id -> 中文名稱 對照
                menu_name_mapping = {}
                try:
                    if hasattr(st.session_state, "api") and st.session_state.api:
                        menu_items = st.session_state.api.get_menu_items()
                        for m in (menu_items or []):
                            if m.get("product_code"):
                                menu_name_mapping[str(m["product_code"])] = m.get("name") or ""
                            if m.get("id") is not None:
                                menu_name_mapping[str(m["id"])] = m.get("name") or ""
                except Exception:
                    pass

                def _compose_product_label(row):
                    code = str(row.get(code_field) or "") if code_field else ""
                    name = None
                    if code:
                        name = menu_name_mapping.get(code)
                    if not name:
                        name = row.get(item_field)
                    if code and name:
                        return f"{name}({code})"
                    if name:
                        return str(name)
                    if code:
                        return f"({code})"
                    return "未命名商品"

                prepared_df["__product_label"] = prepared_df.apply(_compose_product_label, axis=1)

                # 控制元件：排序方向（radio 兩個選項）+ 顯示數量（number_input）+ 排序依據（selectbox）
                ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
                with ctrl_col1:
                    sort_order = st.radio(
                        "排序方向",
                        ["由第一名開始", "由倒數名開始"],
                        horizontal=True,
                        key="product_rank_order",
                    )
                with ctrl_col2:
                    top_n = st.number_input(
                        "顯示項目數量",
                        min_value=1,
                        max_value=50,
                        value=10,
                        step=1,
                        key="product_rank_top_n",
                    )
                with ctrl_col3:
                    metric_choice = st.selectbox(
                        "排序依據",
                        ["銷售金額", "銷售數量"],
                        index=0,
                        key="product_rank_metric",
                    )

                agg_df = prepared_df.groupby("__product_label").agg(
                    total_amount=("total_amount", "sum"),
                    total_quantity=("__quantity_for_rank", "sum"),
                ).reset_index()

                if agg_df.empty:
                    st.info("📊 無法計算商品彙總資料")
                else:
                    sort_col = "total_amount" if metric_choice == "銷售金額" else "total_quantity"
                    ascending_flag = True if sort_order == "由倒數名開始" else False
                    agg_df = agg_df.sort_values(sort_col, ascending=ascending_flag).head(int(top_n))

                    # 顯示表格
                    display_df = agg_df.rename(
                        columns={
                            "__product_label": "商品",
                            "total_amount": "銷售金額",
                            "total_quantity": "銷售數量",
                        }
                    )
                    # 不顯示索引欄位（避免最左側出現 0,1,2... 的ID欄）
                    st.dataframe(display_df, width='stretch', hide_index=True)

                    # 顯示長條圖
                    fig_rank = px.bar(
                        agg_df,
                        x="total_amount" if metric_choice == "銷售金額" else "total_quantity",
                        y="__product_label",
                        orientation="h",
                        labels={
                            "__product_label": "商品",
                            "total_amount": "銷售金額 (NT$)",
                            "total_quantity": "銷售數量",
                        },
                        title=f"商品{metric_choice}排行（Top {top_n}）",
                    )
                    # 固定讓長條不要貼滿整個寬度（特別是只有 1 筆資料時）
                    max_val = agg_df["total_amount" if metric_choice == "銷售金額" else "total_quantity"].max()
                    x_max = float(max_val) * 1.2 if max_val and max_val > 0 else 1.0
                    fig_rank.update_layout(
                        yaxis=dict(autorange="reversed"),
                        xaxis=dict(range=[0, x_max]),
                    )
                    # 局部關閉 Plotly 棄用警告，避免黃色提示干擾畫面
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message=r"The keyword arguments have been deprecated and will be removed in a future release.*",
                            category=UserWarning,
                        )
                        st.plotly_chart(fig_rank, width='stretch')

    with col_rank2:
        st.markdown("#### 🏪 機台銷售排行")
        if prepared_df is None:
            st.info("📊 選定期間內沒有銷售資料，無法產生機台排行")
        else:
            # 建立機台 ID / code -> 名稱 的對照
            # 注意：某些交易資料的 machine_id 可能是文字型別的 machine_code，
            # 因此這裡同時用「字串版 id」與「code」兩種 key 來建立映射，避免對不到。
            machine_by_id = {}
            machine_by_code = {}
            for m in machines or []:
                mid = m.get("id")
                mcode = m.get("machine_code") or m.get("code")
                mname = m.get("name") or ""
                loc_name = m.get("location_name") or ""
                if isinstance(loc_name, dict):
                    loc_name = loc_name.get("name", "")
                label_name = mname or mcode or "未命名機台"
                if loc_name:
                    label_name = f"{label_name} - {loc_name}"

                # 以「字串 id」作為 key，以容納 int / str 不同型別
                if mid is not None:
                    id_key = str(mid)
                    machine_by_id[id_key] = {"label": label_name, "code": mcode}

                if mcode:
                    code_key = str(mcode)
                    machine_by_code[code_key] = {"label": label_name, "code": mcode}

            machine_id_field = None
            for field in ["machine_id", "machineId"]:
                if field in prepared_df.columns:
                    machine_id_field = field
                    break

            machine_code_field = None
            for field in ["machine_code", "machineCode"]:
                if field in prepared_df.columns:
                    machine_code_field = field
                    break

            if not machine_id_field and not machine_code_field:
                st.info("📊 無法找到機台欄位（machine_id / machine_code），無法產生機台排行")
            else:
                def _compose_machine_label(row):
                    # 先取出原始欄位
                    raw_mid = row.get(machine_id_field) if machine_id_field else None
                    raw_mcode = row.get(machine_code_field) if machine_code_field else None

                    # 正規化成字串 key
                    mid_key = str(raw_mid) if raw_mid is not None else None
                    code_key = str(raw_mcode) if raw_mcode is not None else None

                    info = None

                    # 1) 先嘗試用 id 對映（機台列表中的 id 可能是 int，但這裡統一轉成字串）
                    if mid_key is not None and mid_key in machine_by_id:
                        info = machine_by_id[mid_key]
                    # 2) 再用 machine_code 對映
                    elif code_key is not None and code_key in machine_by_code:
                        info = machine_by_code[code_key]
                    # 3) 若 machine_id 看起來像是 code（例如 "SC-NCU-002"），也試著用 code 查一次
                    elif mid_key is not None and mid_key in machine_by_code:
                        info = machine_by_code[mid_key]

                    if info:
                        return info["label"]

                    # 找不到對應時，給出盡量有資訊的 fallback 標籤
                    if code_key:
                        return f"未知機台({code_key})"
                    if mid_key:
                        return f"未知機台(ID:{mid_key})"
                    return "未知機台"

                prepared_df["__machine_label"] = prepared_df.apply(_compose_machine_label, axis=1)

                # 控制元件：排序方向（radio 兩個選項）+ 顯示數量（number_input）+ 排序依據（selectbox）
                m_ctrl_col1, m_ctrl_col2, m_ctrl_col3 = st.columns(3)
                with m_ctrl_col1:
                    sort_order_m = st.radio(
                        "排序方向",
                        ["由第一名開始", "由倒數名開始"],
                        horizontal=True,
                        key="machine_rank_order",
                    )
                with m_ctrl_col2:
                    top_n_m = st.number_input(
                        "顯示項目數量",
                        min_value=1,
                        max_value=50,
                        value=10,
                        step=1,
                        key="machine_rank_top_n",
                    )
                with m_ctrl_col3:
                    metric_choice_m = st.selectbox(
                        "排序依據",
                        ["銷售金額", "銷售數量", "交易筆數"],
                        index=0,
                        key="machine_rank_metric",
                    )

                agg_m = prepared_df.groupby("__machine_label").agg(
                    total_amount=("total_amount", "sum"),
                    total_quantity=("__quantity_for_rank", "sum"),
                    transaction_count=("order_id", "nunique") if "order_id" in prepared_df.columns else ("__machine_label", "size"),
                ).reset_index()

                if agg_m.empty:
                    st.info("📊 無法計算機台彙總資料")
                else:
                    if metric_choice_m == "銷售金額":
                        sort_col_m = "total_amount"
                        x_field = "total_amount"
                    elif metric_choice_m == "銷售數量":
                        sort_col_m = "total_quantity"
                        x_field = "total_quantity"
                    else:
                        sort_col_m = "transaction_count"
                        x_field = "transaction_count"

                    ascending_flag_m = True if sort_order_m == "由倒數名開始" else False
                    agg_m = agg_m.sort_values(sort_col_m, ascending=ascending_flag_m).head(int(top_n_m))

                    display_m = agg_m.rename(
                        columns={
                            "__machine_label": "機台",
                            "total_amount": "銷售金額",
                            "total_quantity": "銷售數量",
                            "transaction_count": "交易筆數",
                        }
                    )
                    # 不顯示索引欄位（避免最左側出現 0,1,2... 的ID欄）
                    st.dataframe(display_m, width='stretch', hide_index=True)

                    fig_machine = px.bar(
                        agg_m,
                        x=x_field,
                        y="__machine_label",
                        orientation="h",
                        labels={
                            "__machine_label": "機台",
                            "total_amount": "銷售金額 (NT$)",
                            "total_quantity": "銷售數量",
                            "transaction_count": "交易筆數",
                        },
                        title=f"機台{metric_choice_m}排行（Top {top_n_m}）",
                    )
                    # 固定讓長條不要貼滿整個寬度（特別是只有 1 筆資料時）
                    max_val_m = agg_m[x_field].max()
                    x_max_m = float(max_val_m) * 1.2 if max_val_m and max_val_m > 0 else 1.0
                    fig_machine.update_layout(
                        yaxis=dict(autorange="reversed"),
                        xaxis=dict(range=[0, x_max_m]),
                    )
                    # 局部關閉 Plotly 棄用警告，避免黃色提示干擾畫面
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message=r"The keyword arguments have been deprecated and will be removed in a future release.*",
                            category=UserWarning,
                        )
                        st.plotly_chart(fig_machine, width='stretch')

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
