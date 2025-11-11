"""
訂單管理模組
包含訂單上傳和訂單查詢功能
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from logger_config import system_logger, api_logger
from utils import VendingMachineAPI

# 載入環境變數
load_dotenv()


def parse_timestamp(timestamp_str):
    """解析時間戳字串，支援多種格式"""
    # 支援的時間格式列表
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2025-10-24 1:12:38
        "%Y/%m/%d %H:%M:%S",  # 2025/10/24 1:12:38
        "%Y-%m-%d %H:%M",     # 2025-10-24 1:12
        "%Y/%m/%d %H:%M",     # 2025/10/24 1:12
        "%Y-%m-%dT%H:%M:%S",  # ISO format
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(timestamp_str).strip(), fmt)
        except ValueError:
            continue

    # 如果所有格式都失敗，拋出錯誤
    raise ValueError(f"無法解析時間格式: {timestamp_str}")


def get_database_connection():
    """建立資料庫連接"""
    try:
        # 從環境變數獲取資料庫配置
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "smartcater")

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        system_logger.info(f"🔗 連接到資料庫: {db_host}:{db_port}/{db_name}")

        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        return SessionLocal()
    except Exception as e:
        system_logger.error(f"資料庫連接失敗: {e}")
        raise


def get_machine_id_by_code(db, machine_code):
    """根據 machine_code 獲取 machine_id"""
    query = text("SELECT id FROM machines WHERE machine_code = :machine_code")
    result = db.execute(query, {"machine_code": machine_code}).fetchone()

    if result:
        return result[0]
    else:
        raise ValueError(f"找不到機台: {machine_code}")


def get_menu_item_id_by_product_code(db, product_code):
    """根據 product_code 獲取 menu_item_id"""
    query = text("SELECT id, price FROM menu_items WHERE product_code = :product_code")
    result = db.execute(query, {"product_code": product_code}).fetchone()

    if result:
        return result[0], result[1]  # 返回 id 和 price
    else:
        raise ValueError(f"找不到產品: {product_code}")


def get_or_create_env_context(db, machine_code, weather, temperature, humidity, timestamp):
    """獲取或創建環境情境"""
    try:
        # 先獲取機台的 location_id
        location_query = text("""
            SELECT l.id
            FROM locations l
            JOIN machines m ON m.location_id = l.id
            WHERE m.machine_code = :machine_code
        """)
        location_result = db.execute(
            location_query, {"machine_code": machine_code}
        ).fetchone()

        if not location_result:
            raise ValueError(f"找不到機台 {machine_code} 的地點資訊")

        location_id = location_result[0]

        # 檢查是否已存在相似的環境情境（時間差在1小時內）
        check_query = text("""
            SELECT id FROM env_context
            WHERE location_id = :location_id
            AND ABS(EXTRACT(EPOCH FROM (timestamp - :timestamp))) < 3600
            AND weather = :weather
            ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - :timestamp)))
            LIMIT 1
        """)

        existing = db.execute(
            check_query,
            {"location_id": location_id, "timestamp": timestamp, "weather": weather},
        ).fetchone()

        if existing:
            return existing[0]

        # 創建新的環境情境
        insert_query = text("""
            INSERT INTO env_context (
                location_id, weather, temperature, humidity,
                timestamp, created_at, updated_at
            )
            VALUES (
                :location_id, :weather, :temperature, :humidity,
                :timestamp, :timestamp, :timestamp
            )
            RETURNING id
        """)

        result = db.execute(
            insert_query,
            {
                "location_id": location_id,
                "weather": weather,
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": timestamp,
            },
        )

        db.commit()
        return result.fetchone()[0]

    except Exception as e:
        db.rollback()
        raise Exception(f"創建環境情境失敗: {e}") from e


def create_order_from_row(db, row) -> Tuple[int, str]:
    """從 DataFrame 行創建訂單"""
    try:
        # 解析時間
        purchase_time = parse_timestamp(row["purchase_timestamp"])

        # 獲取機台編號（支援新舊格式）
        machine_code = row.get("machine_code", row.get("machine_id"))
        if not machine_code:
            raise ValueError("缺少機台編號 (machine_code 或 machine_id)")

        # 獲取機台 ID
        machine_id = get_machine_id_by_code(db, machine_code)

        # 獲取產品編號（支援新舊格式）
        product_code = row.get("product_code", row.get("meal_id"))
        if not product_code:
            raise ValueError("缺少產品編號 (product_code 或 meal_id)")

        # 獲取菜單項目 ID 和價格
        menu_item_id, default_price = get_menu_item_id_by_product_code(db, product_code)

        # 使用 Excel 中的價格，如果沒有則使用預設價格
        unit_price = float(row.get("unit_price", default_price))
        quantity = int(row.get("quantity", row.get("quantity_sold", 1)))
        total_amount = unit_price * quantity

        # 取得溫度值（支援多種欄位名稱）
        temperature = float(
            row.get(
                "temperature",
                row.get("temperature_celsius", row.get("temperature_cels", 25.0)),
            )
        )

        # 取得濕度值（可選）
        humidity = None
        if pd.notna(row.get("humidity")):
            humidity = float(row.get("humidity"))

        # 獲取或創建環境情境
        env_context_id = get_or_create_env_context(
            db,
            machine_code,
            row.get("weather", "UNKNOWN"),
            temperature,
            humidity,
            purchase_time,
        )

        # 獲取訂單編號（支援新舊格式）
        order_number = row.get("order_number", row.get("transaction_id"))
        if not order_number:
            raise ValueError("缺少訂單編號 (order_number 或 transaction_id)")

        # 獲取金流編號（可選）
        payment_number = row.get("bill_number", row.get("payment_number"))

        # 獲取付款方式（可選，預設為 cash）
        payment_method = row.get("payment_method", "cash")
        if pd.isna(payment_method):
            payment_method = "cash"

        # 創建訂單（預設訂單狀態為 "CREATED"，付款狀態為 "COMPLETED"）
        order_query = text("""
            INSERT INTO orders (
                order_number, machine_id, env_context_id, total_amount,
                status, payment_status, payment_method, payment_number,
                weather, temperature, humidity,
                created_at, updated_at
            ) VALUES (
                :order_number, :machine_id, :env_context_id, :total_amount,
                :status, :payment_status, :payment_method, :payment_number,
                :weather, :temperature, :humidity,
                :created_at, :updated_at
            )
            RETURNING id
        """)

        order_result = db.execute(
            order_query,
            {
                "order_number": order_number,
                "machine_id": machine_id,
                "env_context_id": env_context_id,
                "total_amount": total_amount,
                "status": "CREATED",
                "payment_status": "COMPLETED",
                "payment_method": payment_method,
                "payment_number": payment_number,
                "weather": row.get("weather", "UNKNOWN"),
                "temperature": temperature,
                "humidity": humidity,
                "created_at": purchase_time,
                "updated_at": purchase_time,
            },
        )

        order_id = order_result.fetchone()[0]

        # 創建訂單項目
        order_item_query = text("""
            INSERT INTO order_items (
                order_id, menu_item_id, quantity, unit_price, subtotal,
                created_at, updated_at
            ) VALUES (
                :order_id, :menu_item_id, :quantity, :unit_price, :subtotal,
                :created_at, :updated_at
            )
        """)

        db.execute(
            order_item_query,
            {
                "order_id": order_id,
                "menu_item_id": menu_item_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": total_amount,
                "created_at": purchase_time,
                "updated_at": purchase_time,
            },
        )

        # 如果有推薦項目，更新訂單的 recommended_items（支援新舊格式及拼寫錯誤）
        recommended_item = row.get("recommended_item", row.get("recommend", row.get("recommand"))) # codespell:ignore recommand
        if pd.notna(recommended_item):
            # 正確序列化 JSON 資料
            recommended_items = {"items": [str(recommended_item)]}
            update_recommended = text("""
                UPDATE orders
                SET recommended_items = CAST(:recommended_items AS jsonb)
                WHERE id = :order_id
            """)
            db.execute(
                update_recommended,
                {
                    "order_id": order_id,
                    "recommended_items": json.dumps(recommended_items),
                },
            )

        db.commit()
        return order_id, order_number

    except Exception as e:
        db.rollback()
        raise Exception(f"創建訂單失敗: {e}") from e


def upload_orders_from_dataframe(df: pd.DataFrame) -> Tuple[int, int, int, List[str]]:
    """
    從 DataFrame 上傳訂單
    
    返回值: (success_count, fail_count, total_rows, error_messages)
    """
    success_count = 0
    fail_count = 0
    error_messages = []
    
    # 檢查必要欄位（支援新舊格式）
    required_fields = {
        "order_number": ["order_number", "transaction_id"],
        "machine_code": ["machine_code", "machine_id"],
        "purchase_timestamp": ["purchase_timestamp"],
        "product_code": ["product_code", "meal_id"],
    }

    missing_fields = []
    for field_name, possible_columns in required_fields.items():
        if not any(col in df.columns for col in possible_columns):
            missing_fields.append(f"{field_name} ({' 或 '.join(possible_columns)})")

    if missing_fields:
        error_msg = f"❌ 缺少必要欄位: {', '.join(missing_fields)}"
        system_logger.error(error_msg)
        return 0, 0, len(df), [error_msg]

    # 連接資料庫
    try:
        db = get_database_connection()
    except Exception as e:
        error_msg = f"❌ 資料庫連接失敗: {e}"
        system_logger.error(error_msg)
        return 0, 0, len(df), [error_msg]

    try:
        # 處理每一筆資料
        for index, row in df.iterrows():
            try:
                order_id, order_number = create_order_from_row(db, row)
                success_count += 1
                
                purchase_time = parse_timestamp(row["purchase_timestamp"])
                product_code = row.get("product_code", row.get("meal_id"))
                system_logger.info(
                    f"✅ [{index + 1}/{len(df)}] 訂單 {order_number} - "
                    f"{purchase_time.strftime('%Y-%m-%d %H:%M:%S')} - "
                    f"產品: {product_code}"
                )

            except Exception as e:
                fail_count += 1
                error_msg = f"❌ [{index + 1}/{len(df)}] 失敗: {e}"
                system_logger.error(error_msg)
                error_messages.append(error_msg)

        return success_count, fail_count, len(df), error_messages

    finally:
        db.close()


def render_order_upload_tab():
    """訂單上傳功能標籤頁"""
    st.subheader("📤 訂單數據上傳")
    
    # 說明區域
    with st.expander("ℹ️ 使用說明", expanded=False):
        st.markdown("""
        ### 功能說明
        此功能可以批量上傳 Excel 訂單數據到資料庫。
        
        ### 必要欄位
        Excel 文件必須包含以下欄位（支援舊格式）：
        - `order_number` 或 `transaction_id` - 訂單編號
        - `machine_code` 或 `machine_id` - 機台編號
        - `purchase_timestamp` - 購買時間戳（格式：YYYY-MM-DD HH:MM:SS）
        - `product_code` 或 `meal_id` - 產品編號
        
        ### 可選欄位
        - `unit_price` - 單價（若無則使用產品預設價格）
        - `quantity` 或 `quantity_sold` - 數量（預設為 1）
        - `weather` - 天氣狀況
        - `temperature` 或 `temperature_celsius` - 溫度
        - `humidity` - 濕度
        - `payment_method` - 付款方式（預設為 cash）
        - `payment_number` 或 `bill_number` - 金流編號
        - `recommended_item` 或 `recommend` 或 `recommand` - 推薦項目
        
        ### 時間格式支援
        - `YYYY-MM-DD HH:MM:SS` (例: 2025-10-24 13:12:38)
        - `YYYY/MM/DD HH:MM:SS` (例: 2025/10/24 13:12:38)
        - `YYYY-MM-DD HH:MM` (例: 2025-10-24 13:12)
        - `YYYY/MM/DD HH:MM` (例: 2025/10/24 13:12)
        """)
    
    st.markdown("---")
    
    # 文件上傳區
    st.subheader("📁 上傳 Excel 文件")
    
    # 支援多文件上傳
    uploaded_files = st.file_uploader(
        "選擇 Excel 文件（可多選）",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="支援 .xlsx 和 .xls 格式"
    )
    
    if uploaded_files:
        st.success(f"✅ 已選擇 {len(uploaded_files)} 個文件")
        
        # 顯示選中的文件列表
        st.markdown("#### 📋 文件列表")
        for i, file in enumerate(uploaded_files, 1):
            st.write(f"{i}. {file.name} ({file.size / 1024:.2f} KB)")
        
        st.markdown("---")
        
        # 預覽和上傳按鈕
        col1, col2 = st.columns(2)
        
        with col1:
            preview_mode = st.checkbox("🔍 預覽模式（不實際上傳）", value=False)
        
        with col2:
            if st.button("🚀 開始上傳", type="primary", use_container_width=True):
                # 處理所有文件
                total_success = 0
                total_fail = 0
                total_rows = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for file_idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"正在處理文件 {file_idx + 1}/{len(uploaded_files)}: {uploaded_file.name}")
                    
                    # 顯示當前文件的處理狀態
                    with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                        try:
                            # 讀取 Excel 文件
                            df = pd.read_excel(uploaded_file)
                            
                            st.info(f"✅ 成功讀取 {len(df)} 筆資料")
                            st.write(f"📋 欄位: {', '.join(df.columns.tolist())}")
                            
                            # 顯示前幾筆資料預覽
                            st.markdown("##### 數據預覽（前 5 筆）")
                            st.dataframe(df.head(), use_container_width=True)
                            
                            if not preview_mode:
                                st.markdown("---")
                                st.markdown("##### 上傳進度")
                                
                                # 上傳訂單
                                with st.spinner("正在上傳訂單..."):
                                    success, fail, rows, errors = upload_orders_from_dataframe(df)
                                    
                                    total_success += success
                                    total_fail += fail
                                    total_rows += rows
                                    
                                    # 顯示結果
                                    col_a, col_b, col_c = st.columns(3)
                                    with col_a:
                                        st.metric("總筆數", rows)
                                    with col_b:
                                        st.metric("✅ 成功", success)
                                    with col_c:
                                        st.metric("❌ 失敗", fail)
                                    
                                    # 如果有錯誤，顯示錯誤訊息
                                    if errors:
                                        st.warning(f"⚠️ 發現 {len(errors)} 個錯誤")
                                        with st.expander("查看錯誤詳情"):
                                            for error in errors[:10]:  # 只顯示前10個錯誤
                                                st.error(error)
                                            if len(errors) > 10:
                                                st.info(f"... 還有 {len(errors) - 10} 個錯誤未顯示")
                                    else:
                                        st.success("🎉 所有訂單上傳成功！")
                            
                        except Exception as e:
                            st.error(f"❌ 處理文件時發生錯誤: {e}")
                            system_logger.error(f"處理文件 {uploaded_file.name} 時發生錯誤: {e}")
                    
                    # 更新進度條
                    progress_bar.progress((file_idx + 1) / len(uploaded_files))
                
                # 顯示總體統計
                if not preview_mode:
                    st.markdown("---")
                    st.markdown("### 📊 總體上傳統計")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("處理文件數", len(uploaded_files))
                    with col2:
                        st.metric("總資料筆數", total_rows)
                    with col3:
                        st.metric("✅ 成功上傳", total_success)
                    with col4:
                        st.metric("❌ 失敗", total_fail)
                    
                    if total_fail == 0 and total_success > 0:
                        st.balloons()
                        st.success(f"🎉 完成！所有 {total_success} 筆訂單已成功上傳到資料庫")
                    elif total_success > 0:
                        st.warning(f"⚠️ 部分上傳成功：{total_success} 筆成功，{total_fail} 筆失敗")
                    else:
                        st.error("❌ 上傳失敗，請檢查文件格式和資料內容")
                else:
                    st.info("🔍 預覽模式：已完成資料檢查，未實際上傳到資料庫")
                
                status_text.text("處理完成！")
    
    else:
        st.info("👆 請選擇要上傳的 Excel 文件")
        
        # 顯示示例資料格式
        st.markdown("---")
        st.markdown("### 📋 Excel 文件範例格式")
        
        example_data = {
            "order_number": ["ORD-2025-001", "ORD-2025-002"],
            "machine_code": ["VM001", "VM002"],
            "product_code": ["A001", "A002"],
            "purchase_timestamp": ["2025-10-24 13:12:38", "2025-10-24 14:30:00"],
            "unit_price": [100.0, 150.0],
            "quantity": [1, 2],
            "weather": ["SUNNY", "CLOUDY"],
            "temperature": [25.5, 22.0],
            "humidity": [60.0, 70.0],
            "payment_method": ["cash", "card"]
        }
        
        example_df = pd.DataFrame(example_data)
        st.dataframe(example_df, use_container_width=True)


def render_order_query_tab():
    """訂單查詢功能標籤頁"""
    st.subheader("🔍 訂單查詢")
    
    # 獲取 API 客戶端
    api = st.session_state.api
    
    # 查詢方式選擇
    query_method = st.radio(
        "選擇查詢方式",
        ["📋 列表查詢", "📝 訂單編號查詢", "🏪 機台查詢"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # 根據選擇的查詢方式顯示對應的界面
    if query_method == "📋 列表查詢":
        render_list_query(api)
    elif query_method == "📝 訂單編號查詢":
        render_number_query(api)
    elif query_method == "🏪 機台查詢":
        render_machine_query(api)
    # elif query_method == "📅 日期查詢":
    #     render_date_query(api)


def render_list_query(api: VendingMachineAPI):
    """渲染列表查詢界面"""
    st.markdown("### 📋 訂單列表查詢")
    
    col1, col2 = st.columns(2)
    
    with col1:
        skip = st.number_input("跳過筆數", min_value=0, value=0, step=10)
        machine_id_filter = st.text_input("機台ID篩選（可選）", placeholder="留空表示所有機台")
    
    with col2:
        limit = st.number_input("查詢筆數", min_value=1, max_value=500, value=100, step=10)
        status_filter = st.selectbox(
            "狀態篩選（可選）",
            ["全部", "CREATED", "PENDING", "COMPLETED", "CANCELLED", "FAILED"]
        )
    
    if st.button("🔍 開始查詢", type="primary", use_container_width=True):
        with st.spinner("查詢中..."):
            # 準備查詢參數
            machine_id = int(machine_id_filter) if machine_id_filter else None
            order_status = status_filter if status_filter != "全部" else None
            
            # 調用 API
            result = api.get_orders_with_details(
                skip=skip,
                limit=limit,
                machine_id=machine_id,
                order_status=order_status
            )
            
            if result:
                # 顯示統計資訊
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("總記錄數", result.get("total", 0))
                with col2:
                    st.metric("本頁筆數", len(result.get("items", [])))
                with col3:
                    current_page = (skip // limit) + 1
                    total_pages = (result.get("total", 0) + limit - 1) // limit
                    st.metric("頁數", f"{current_page}/{total_pages}")
                
                # 顯示訂單列表
                items = result.get("items", [])
                if items:
                    st.markdown("---")
                    st.markdown("### 📦 訂單詳情")
                    
                    for idx, order in enumerate(items, 1):
                        with st.expander(f"訂單 #{idx} - {order.get('order_number', 'N/A')}", expanded=False):
                            render_order_details(order)
                else:
                    st.info("查詢範圍內沒有找到訂單")


# def render_id_query(api: VendingMachineAPI):
#     """渲染ID查詢界面"""
#     st.markdown("### 🆔 根據訂單ID查詢")
    
#     order_id = st.number_input("訂單ID", min_value=1, value=1, step=1)
    
#     if st.button("🔍 查詢", type="primary", use_container_width=True):
#         with st.spinner("查詢中..."):
#             order = api.get_order_by_id(order_id)
            
#             if order:
#                 st.success("✅ 查詢成功！")
#                 st.markdown("---")
#                 render_order_details(order)
#             else:
#                 st.error(f"❌ 找不到訂單ID: {order_id}")


def render_number_query(api: VendingMachineAPI):
    """渲染訂單編號查詢界面"""
    st.markdown("### 📝 根據訂單編號查詢")
    
    order_number = st.text_input(
        "訂單編號",
        placeholder="例如：600000031762416122"
    )
    
    if st.button("🔍 查詢", type="primary", use_container_width=True):
        if not order_number:
            st.warning("請輸入訂單編號")
            return
        
        with st.spinner("查詢中..."):
            order = api.get_order_by_number(order_number)
            
            if order:
                st.success("✅ 查詢成功！")
                st.markdown("---")
                render_order_details(order)
            else:
                st.error(f"❌ 找不到訂單編號: {order_number}")


def render_machine_query(api: VendingMachineAPI):
    """渲染機台查詢界面"""
    st.markdown("### 🏪 根據機台ID查詢")
    
    machine_id = st.number_input("機台ID", min_value=1, value=1, step=1)
    
    if st.button("🔍 查詢", type="primary", use_container_width=True):
        with st.spinner("查詢中..."):
            orders = api.get_orders_by_machine_id(machine_id)
            
            if orders:
                st.success(f"✅ 找到 {len(orders)} 筆訂單")
                st.markdown("---")
                
                for idx, order in enumerate(orders, 1):
                    with st.expander(f"訂單 #{idx} - {order.get('order_number', 'N/A')}", expanded=False):
                        render_order_details(order)
            else:
                st.info(f"該機台沒有找到訂單")


# def render_date_query(api: VendingMachineAPI):
#     """渲染日期查詢界面"""
#     st.markdown("### 📅 根據日期範圍查詢")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         start_date = st.date_input(
#             "開始日期",
#             value=datetime.now().date()
#         )
    
#     with col2:
#         end_date = st.date_input(
#             "結束日期",
#             value=datetime.now().date()
#         )
    
#     machine_id_filter = st.text_input(
#         "機台ID篩選（可選）",
#         placeholder="留空表示所有機台"
#     )
    
#     limit = st.number_input(
#         "查詢筆數上限",
#         min_value=1,
#         max_value=1000,
#         value=100,
#         step=50
#     )
    
#     if st.button("🔍 查詢", type="primary", use_container_width=True):
#         with st.spinner("查詢中..."):
#             # 格式化日期
#             start_date_str = start_date.strftime("%Y-%m-%d")
#             end_date_str = end_date.strftime("%Y-%m-%d")
#             machine_id = machine_id_filter if machine_id_filter else None
            
#             # 調用 API（使用 AI API）
#             result = api.get_orders_by_date_range(
#                 start_date=start_date_str,
#                 end_date=end_date_str,
#                 machine_id=machine_id,
#                 limit=limit
#             )
            
#             if result and "data" in result:
#                 data = result.get("data", [])
#                 pagination = result.get("pagination", {})
                
#                 # 顯示統計資訊
#                 col1, col2, col3, col4 = st.columns(4)
#                 with col1:
#                     st.metric("總記錄數", pagination.get("total_records", len(data)))
#                 with col2:
#                     st.metric("本頁筆數", len(data))
#                 with col3:
#                     st.metric("日期範圍", f"{start_date_str} 至 {end_date_str}")
#                 with col4:
#                     current_page = pagination.get("current_page", 1)
#                     total_pages = pagination.get("total_pages", 1)
#                     st.metric("頁數", f"{current_page}/{total_pages}")
                
#                 # 顯示訂單列表
#                 if data:
#                     st.markdown("---")
#                     st.markdown("### 📦 訂單詳情")
                    
#                     for idx, order in enumerate(data, 1):
#                         with st.expander(f"訂單 #{idx} - {order.get('order_number', 'N/A')}", expanded=False):
#                             render_order_details_from_transactional_data(order)
#                 else:
#                     st.info("查詢範圍內沒有找到訂單")


def render_order_details(order: Dict):
    """渲染訂單詳情（從訂單API）- 顯示 JSON 格式"""
    import json
    st.json(order)


def render_order_details_from_transactional_data(order: Dict):
    """渲染訂單詳情（從交易數據API）- 顯示 JSON 格式"""
    import json
    st.json(order)


def order_management_page():
    """訂單管理主頁面"""
    st.header("📦 訂單管理")
    st.markdown("---")
    
    # 創建標籤頁
    tab1, tab2 = st.tabs(["📤 訂單上傳", "🔍 訂單查詢"])
    
    with tab1:
        render_order_upload_tab()
    
    with tab2:
        render_order_query_tab()

