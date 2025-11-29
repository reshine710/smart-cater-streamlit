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
                "status": "COMPLETED",
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
        recommended_item = row.get(
            "recommended_item", 
            row.get("recommend", 
            row.get("recommand"))   # codespell:ignore recommand
        ) 
        if pd.notna(recommended_item):
            # 正確序列化 JSON 資料
            recommended_items = str(recommended_item)
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
                from utils import format_datetime_display
                system_logger.info(
                    f"✅ [{index + 1}/{len(df)}] 訂單 {order_number} - "
                    f"{format_datetime_display(purchase_time)} - "
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
            if st.button("🚀 開始上傳", type="primary", width='stretch'):
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
                            st.dataframe(df.head(), width='stretch')
                            
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
        st.dataframe(example_df, width='stretch')


def render_order_query_tab():
    """訂單查詢功能標籤頁"""
    st.subheader("🔍 訂單查詢")
    
    # 獲取 API 客戶端
    api = st.session_state.api
    
    # 查詢方式選擇
    query_method = st.radio(
        "選擇查詢方式",
        ["📋 列表查詢", "📝 訂單編號查詢", "🏪 機台查詢", "📅 日期查詢"],
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
    elif query_method == "📅 日期查詢":
        render_date_query(api)


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
    
    if st.button("🔍 開始查詢", type="primary", width='stretch'):
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
    
#     if st.button("🔍 查詢", type="primary", width='stretch'):
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
    
    if st.button("🔍 查詢", type="primary", width='stretch'):
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
    st.markdown("### 🏪 根據機台查詢訂單")
    
    # 獲取所有機台列表
    with st.spinner("載入機台列表..."):
        machines = api.get_machines()
    
    if not machines:
        st.error("❌ 無法獲取機台列表，請檢查 API 連接")
        return
    
    # 準備下拉選單選項
    machine_options = {}
    for machine in machines:
        machine_id = machine.get('id')
        machine_code = machine.get('machine_code', 'Unknown')
        machine_name = machine.get('name', 'Unknown')
        location_name = machine.get('location_name', '')
        
        # 顯示格式：機台名稱 (機台編碼) - 地點
        if location_name:
            display_text = f"{machine_name} ({machine_code}) - {location_name}"
        else:
            display_text = f"{machine_name} ({machine_code})"
        
        machine_options[display_text] = {
            'id': machine_id,
            'code': machine_code,
            'name': machine_name
        }
    
    # 機台選擇和查詢筆數設定
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 下拉選單
        selected_display = st.selectbox(
            "選擇機台",
            options=list(machine_options.keys()),
            help="選擇要查詢訂單的機台"
        )
    
    with col2:
        # 查詢筆數設定
        limit = st.number_input(
            "查詢筆數",
            min_value=1,
            max_value=1000,
            value=100,
            step=10,
            help="設定要查詢的訂單數量上限"
        )
    
    # 顯示選中機台的資訊
    if selected_display:
        selected_machine = machine_options[selected_display]
        st.info(f"📋 機台編碼: {selected_machine['code']} | 機台名稱: {selected_machine['name']} | 查詢筆數: {limit}")
    
    if st.button("🔍 查詢訂單", type="primary", width='stretch'):
        if not selected_display:
            st.warning("請選擇機台")
            return
        
        selected_machine = machine_options[selected_display]
        machine_id = selected_machine['id']
        machine_code = selected_machine['code']
        
        with st.spinner(f"正在查詢機台 {machine_code} 的訂單（最多 {limit} 筆）..."):
            system_logger.info(f"查詢機台 {machine_id} ({machine_code}) 的訂單，page=1, limit={limit}")
            result = api.get_orders_by_machine_id(machine_id=machine_id, limit=limit)
            
            orders = result.get("items", []) if isinstance(result, dict) else []
            total_orders = result.get("total", len(orders)) if isinstance(result, dict) else len(orders)
            
            system_logger.info(f"API 返回 total={total_orders}, items={len(orders)}（設定 limit={limit}）")
            
            if orders:
                st.success(f"✅ 找到 {len(orders)} 筆訂單（總筆數：{total_orders}，查詢上限：{limit}）")
                
                # 如果總筆數大於查詢上限，提醒用戶
                if total_orders > limit:
                    st.warning(f"⚠️ 總共有 {total_orders} 筆訂單，目前僅顯示前 {limit} 筆。如需查看更多，請增加查詢筆數。")
                elif total_orders == limit and len(orders) == limit:
                    st.warning(f"⚠️ 已達到查詢筆數上限（{limit} 筆），可能還有更多訂單未顯示。如需查看更多，請增加查詢筆數。")
                
                st.markdown("---")
                
                # 顯示統計資訊
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("顯示筆數", len(orders))
                with col2:
                    total_amount = sum(order.get('total_amount', 0) for order in orders)
                    st.metric("總金額", f"${total_amount:.2f}")
                with col3:
                    avg_amount = total_amount / len(orders) if orders else 0
                    st.metric("平均金額", f"${avg_amount:.2f}")
                
                st.markdown("---")
                
                for idx, order in enumerate(orders, 1):
                    with st.expander(f"訂單 #{idx} - {order.get('order_number', 'N/A')}", expanded=False):
                        render_order_details(order)
            else:
                if total_orders == 0:
                    st.info(f"機台 {machine_code} 沒有找到訂單")
                else:
                    st.info(f"機台 {machine_code} 沒有找到符合查詢條件的訂單")


def render_date_query(api: VendingMachineAPI):
    """渲染日期查詢界面"""
    st.markdown("### 📅 依日期區間查詢訂單")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "開始日期",
            value=datetime.now().date() - timedelta(days=7),
            help="查詢範圍起始日期（含當日）"
        )
    with col2:
        end_date = st.date_input(
            "結束日期",
            value=datetime.now().date(),
            help="查詢範圍結束日期（含當日）"
        )

    if start_date > end_date:
        st.error("❌ 開始日期不得晚於結束日期")
        return

    with st.spinner("載入機台列表..."):
        machines = api.get_machines()

    machine_options = {"全部機台": None}
    for machine in machines:
        machine_id = machine.get('id')
        machine_code = machine.get('machine_code', 'Unknown')
        machine_name = machine.get('name', 'Unknown')
        location_name = machine.get('location_name', '')
        display_text = f"{machine_name} ({machine_code})" if not location_name else f"{machine_name} ({machine_code}) - {location_name}"
        machine_options[display_text] = machine_id

    col3, col4, col5 = st.columns([2, 1, 1])
    with col3:
        machine_display = st.selectbox(
            "機台篩選",
            options=list(machine_options.keys()),
            help="選擇特定機台或查詢全部機台"
        )
    with col4:
        status_filter = st.selectbox(
            "訂單狀態",
            options=["全部", "created", "completed", "cancelled", "failed", "pending"],
            help="依訂單狀態篩選"
        )
    with col5:
        limit = st.number_input(
            "每頁筆數",
            min_value=1,
            max_value=1000,
            value=100,
            step=10,
            help="單次查詢的筆數上限（最大1000）"
        )

    limit = int(limit)

    skip = st.number_input(
        "跳過筆數（分頁）",
        min_value=0,
        value=0,
        step=int(limit),
        help="用於分頁的跳過筆數，例如查詢第二頁可輸入上一頁的筆數"
    )

    skip = int(skip)

    if st.button("🔍 查詢訂單", type="primary", width='stretch'):
        with st.spinner("查詢中..."):
            try:
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")
                machine_id = machine_options[machine_display]
                order_status = status_filter if status_filter != "全部" else None

                result = api.get_orders_with_details(
                    skip=skip,
                    limit=limit,
                    machine_id=machine_id,
                    order_status=order_status,
                    start_date=start_date_str,
                    end_date=end_date_str
                )

                items = result.get("items", []) if isinstance(result, dict) else []
                total = result.get("total", len(items))

                if items:
                    st.success(f"✅ 找到 {len(items)} 筆訂單（總筆數：{total}，範圍：{start_date_str} 至 {end_date_str}）")

                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("顯示筆數", len(items))
                    with col_b:
                        st.metric("總筆數", total)
                    with col_c:
                        st.metric("跳過筆數", skip)
                    with col_d:
                        st.metric("每頁筆數", limit)

                    if total > skip + len(items):
                        st.warning("⚠️ 尚有更多訂單未顯示，可調整跳過筆數或增加查詢筆數。")

                    st.markdown("---")
                    st.markdown("### 📦 訂單詳情")

                    for idx, order in enumerate(items, 1):
                        header = f"訂單 #{skip + idx} - {order.get('order_number', order.get('id', 'N/A'))}"
                        with st.expander(header, expanded=False):
                            render_order_details(order)
                else:
                    st.info(f"在 {start_date_str} 至 {end_date_str} 範圍內沒有找到符合條件的訂單")
            except Exception as e:
                st.error(f"❌ 查詢失敗：{str(e)}")
                system_logger.error(f"Date range query failed: {e}")


def render_order_details(order: Dict):
    """渲染訂單詳情（從訂單API）- 美化版卡片呈現"""

    # 不顯示的欄位（包含巢狀結構）
    HIDDEN_FIELDS = {
        "unit_price",
        "humidity",
        "status",
        "payment_status",
        "payment_detail",
        "item",
        "machine",
    }

    def _filter_hidden_fields(data):
        """遞迴移除不需要顯示的欄位"""
        if isinstance(data, dict):
            return {
                k: _filter_hidden_fields(v)
                for k, v in data.items()
                if k not in HIDDEN_FIELDS
            }
        if isinstance(data, list):
            return [_filter_hidden_fields(v) for v in data]
        return data

    # ===== 基本欄位整理 =====
    order_id = order.get("id")
    order_number = order.get("order_number") or order.get("transaction_id") or "N/A"
    created_at = order.get("created_at") or order.get("purchase_timestamp")
    total_amount = order.get("total_amount")
    payment_method = order.get("payment_method")
    payment_number = order.get("payment_number") or order.get("bill_number")

    weather = order.get("weather")
    temperature = order.get("temperature") or order.get("temperature_celsius")

    # ===== 建立機台資訊映射（用於查詢機台名稱和代碼） =====
    def get_machine_info_mapping():
        """獲取機台資訊映射（ID -> 機台資訊，包含 name 和 machine_code）"""
        try:
            # 快取所有機台列表，避免重複呼叫 API
            if "order_machines_cache" not in st.session_state:
                api = st.session_state.get("api")
                machines = api.get_machines() if api else []
                # 建立映射：machine_id -> {name, machine_code, location_name}
                by_id = {}
                by_code = {}  # 也建立 machine_code -> 機台資訊的映射
                for m in machines or []:
                    mid = m.get("id")
                    if mid is not None:
                        # 處理 location_name：如果是字典格式，只提取 name 欄位
                        location_raw = m.get("location_name") or m.get("location")
                        if isinstance(location_raw, dict):
                            location_name_clean = location_raw.get("name")
                        else:
                            location_name_clean = location_raw
                        
                        by_id[mid] = {
                            "name": m.get("name"),
                            "machine_code": m.get("machine_code") or m.get("code"),
                            "location_name": location_name_clean
                        }
                        # 同時建立 code -> 機台資訊的映射
                        code = m.get("machine_code") or m.get("code")
                        if code:
                            by_code[code] = by_id[mid]
                st.session_state["order_machines_cache"] = {
                    "by_id": by_id,
                    "by_code": by_code
                }
            return st.session_state.get("order_machines_cache", {"by_id": {}, "by_code": {}})
        except Exception:
            return {"by_id": {}, "by_code": {}}

    # 嘗試取得機台資訊（需要透過查表轉換才能獲得正確的中文名稱）
    machine_code = None
    machine_name = None
    location_name = None

    # 可能存在 machine 物件，但使用者要求不顯示整個 machine，因此只取必要文字
    machine_obj = order.get("machine") or {}
    if isinstance(machine_obj, dict):
        machine_code = machine_obj.get("machine_code") or machine_obj.get("code")
        # 不直接使用 machine_obj 的 name，而是透過查表取得
        location_raw = machine_obj.get("location_name") or machine_obj.get("location")
        # 如果 location 是字典格式，只提取 name 欄位
        if isinstance(location_raw, dict):
            location_name = location_raw.get("name")
        else:
            location_name = location_raw

    # 後端有些版本只回傳 machine_id / machine_code 在訂單本身
    machine_id = order.get("machine_id")
    # 若訂單本身就有 machine_code，先記下來（例如 "SC-TRS-001"）
    if not machine_code:
        machine_code = order.get("machine_code") or order.get("machineCode")

    # 透過 API 查表轉換取得機台資訊（包含中文名稱）
    machine_mapping = get_machine_info_mapping()
    by_id = machine_mapping.get("by_id", {})
    by_code = machine_mapping.get("by_code", {})

    # 優先使用 machine_id 查詢
    if machine_id:
        machine_info = by_id.get(machine_id)
        if machine_info:
            machine_name = machine_info.get("name") or machine_name
            machine_code = machine_info.get("machine_code") or machine_code
            location_raw = machine_info.get("location_name") or location_name
            # 如果 location 是字典格式，只提取 name 欄位
            if isinstance(location_raw, dict):
                location_name = location_raw.get("name") or location_name
            else:
                location_name = location_raw or location_name

    # 如果沒有透過 ID 找到，嘗試使用 machine_code 查詢
    if not machine_name and machine_code:
        machine_info = by_code.get(machine_code)
        if machine_info:
            machine_name = machine_info.get("name") or machine_name
            location_raw = machine_info.get("location_name") or location_name
            # 如果 location 是字典格式，只提取 name 欄位
            if isinstance(location_raw, dict):
                location_name = location_raw.get("name") or location_name
            else:
                location_name = location_raw or location_name

    # ===== 訂單明細（items）處理 =====
    items = (
        order.get("items")
        or order.get("order_items")
        or order.get("order_details")
        or []
    )

    items_table = []
    total_quantity_from_items = 0

    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue

            # 商品名稱：優先 item_name，其次 name，再來 meal_id / product_code
            item_name = (
                item.get("item_name")
                or item.get("name")
                or item.get("meal_id")
                or item.get("product_code")
                or "-"
            )

            # 商品代碼
            item_code = (
                item.get("meal_id")
                or item.get("product_code")
                or item.get("menu_item_id")
            )

            # 商品數量（轉成整數，避免型別問題）
            raw_qty = item.get("quantity", item.get("qty", 0))
            try:
                quantity = int(raw_qty) if raw_qty not in (None, "") else 0
            except (ValueError, TypeError):
                quantity = 0

            # 小計（如果有的話）
            raw_subtotal = item.get("subtotal") or item.get("total") or item.get("amount")
            try:
                subtotal = float(raw_subtotal) if raw_subtotal not in (None, "") else None
            except (ValueError, TypeError):
                subtotal = None

            total_quantity_from_items += quantity

            row = {
                "商品/餐點": item_name,
                "代碼": item_code,
                "數量": quantity,
            }
            if subtotal is not None:
                row["小計"] = subtotal

            items_table.append(row)

    # ===== 總數量處理：優先使用訂單本身的 quantity，其次才用明細加總 =====
    raw_order_qty = order.get("quantity")
    try:
        order_quantity = int(raw_order_qty) if raw_order_qty not in (None, "") else None
    except (ValueError, TypeError):
        order_quantity = None

    total_quantity = order_quantity if order_quantity is not None else total_quantity_from_items

    # ===== 建立菜單項目映射（用於查詢中文名稱） =====
    def get_menu_item_name_by_code(product_code_or_meal_id):
        """根據 product_code 或 meal_id 查詢菜單項目中文名稱"""
        if not product_code_or_meal_id:
            return None
        
        try:
            # 快取菜單項目列表
            if "order_menu_items_cache" not in st.session_state:
                api = st.session_state.get("api")
                if api:
                    menu_items = api.get_menu_items() or []
                    # 建立映射：product_code -> name 和 meal_id -> name
                    mapping = {}
                    for item in menu_items:
                        product_code = item.get("product_code")
                        name = item.get("name")
                        if product_code and name:
                            mapping[product_code] = name
                        # 如果有 meal_id 欄位，也加入映射
                        meal_id = item.get("meal_id")
                        if meal_id and name:
                            mapping[meal_id] = name
                    st.session_state["order_menu_items_cache"] = mapping
                else:
                    st.session_state["order_menu_items_cache"] = {}
            
            menu_cache = st.session_state.get("order_menu_items_cache", {})
            return menu_cache.get(str(product_code_or_meal_id))
        except Exception:
            return None

    # ===== 提取購買的餐點列表（格式：中文（product_code）） =====
    purchased_items_display = []
    if isinstance(items, list) and items:
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # 取得中文名稱和代碼
            item_name_cn = (
                item.get("item_name")
                or item.get("name")
                or None
            )
            item_code = (
                item.get("product_code")
                or item.get("meal_id")
                or item.get("menu_item_id")
                or None
            )
            
            # 如果沒有中文名稱，嘗試從菜單查詢
            if not item_name_cn and item_code:
                item_name_cn = get_menu_item_name_by_code(item_code)
            
            # 格式化顯示：中文（product_code）
            if item_name_cn and item_code:
                purchased_items_display.append(f"{item_name_cn}（{item_code}）")
            elif item_name_cn:
                purchased_items_display.append(item_name_cn)
            elif item_code:
                purchased_items_display.append(f"（{item_code}）")
    
    # 如果沒有從 items 中取得，嘗試從訂單本身取得
    if not purchased_items_display:
        item_name_cn = (
            order.get("item_name")
            or order.get("name")
            or None
        )
        item_code = (
            order.get("product_code")
            or order.get("meal_id")
            or None
        )
        
        if not item_name_cn and item_code:
            item_name_cn = get_menu_item_name_by_code(item_code)
        
        if item_name_cn and item_code:
            purchased_items_display.append(f"{item_name_cn}（{item_code}）")
        elif item_name_cn:
            purchased_items_display.append(item_name_cn)
        elif item_code:
            purchased_items_display.append(f"（{item_code}）")

    # ===== 提取推薦的餐點內容（格式：中文（product_code）） =====
    recommended_item_display = None
    recommended_item_raw = order.get("recommended_item")
    if recommended_item_raw is not None:
        # 轉換為字串格式（處理各種類型：字串、數字等）
        if isinstance(recommended_item_raw, str):
            recommended_code = recommended_item_raw.strip()
        else:
            recommended_code = str(recommended_item_raw).strip()
        
        if recommended_code and recommended_code.lower() not in ("none", "null", ""):
            # 查詢中文名稱
            recommended_name_cn = get_menu_item_name_by_code(recommended_code)
            
            # 格式化顯示：中文（product_code）
            if recommended_name_cn:
                recommended_item_display = f"{recommended_name_cn}（{recommended_code}）"
            else:
                recommended_item_display = f"（{recommended_code}）"

    # ===== 版面呈現 =====
    # 上方概要：訂單編號與時間各自一列，避免被截斷
    st.markdown("#### 📌 訂單概要")
    st.write(f"**訂單編號：** {order_number}")
    if order_id is not None:
        st.caption(f"ID：{order_id}")

    if created_at:
        from utils import format_datetime_display
        st.write(f"**建立時間：** {format_datetime_display(created_at)}")
    else:
        st.write("**建立時間：** -")

    col_summary1, col_summary2 = st.columns(2)
    with col_summary1:
        if total_amount is not None:
            st.metric("總金額", f"${total_amount:,.0f}")
        else:
            st.metric("總金額", "-")
    with col_summary2:
        if total_quantity:
            st.metric("總數量", f"{total_quantity}")
        else:
            st.metric("總數量", "-")

    # 購買的餐點
    if purchased_items_display:
        st.markdown("**🛒 購買的餐點：**")
        for item_display in purchased_items_display:
            st.write(f"- {item_display}")
    else:
        st.markdown("**🛒 購買的餐點：** 無")

    # 推薦的餐點內容
    if recommended_item_display:
        st.markdown("**🤖 推薦的餐點內容：**")
        st.write(f"- {recommended_item_display}")
    else:
        st.markdown("**🤖 推薦的餐點內容：** 無")

    # 機台 / 付款資訊
    st.markdown("---")
    st.markdown("#### 🏪 機台與付款資訊")
    col4, col5 = st.columns(2)
    with col4:
        st.markdown("**機台資訊**")
        if machine_code or machine_name or location_name:
            # 格式：中文（machine_code）
            if machine_name and machine_code:
                st.write(f"- {machine_name}（{machine_code}）")
            elif machine_name:
                st.write(f"- {machine_name}")
            elif machine_code:
                st.write(f"- （{machine_code}）")
            
            if location_name:
                st.write(f"- 地點：{location_name}")
        elif machine_id:
            st.write(f"- 機台 ID：{machine_id}")
        else:
            st.write("（無機台資訊）")

    with col5:
        st.markdown("**付款資訊**")
        st.write(f"- 付款方式：{payment_method or '-'}")
        st.write(f"- 金流編號：{payment_number or '-'}")

    # 環境資訊（不顯示濕度）
    if weather or temperature is not None:
        st.markdown("---")
        st.markdown("#### 🌦️ 環境資訊")
        col6, col7 = st.columns(2)
        with col6:
            st.write(f"- 天氣：{weather or '-'}")
        with col7:
            if temperature is not None:
                st.write(f"- 溫度：{temperature}°C")
            else:
                st.write("- 溫度：-")

    # 訂單明細表格（不顯示單價）
    if items_table:
        st.markdown("---")
        st.markdown("#### 🧾 訂單明細")
        df_items = pd.DataFrame(items_table)
        st.dataframe(df_items, width='stretch')

    # 進階：顯示已過濾的原始 JSON（方便除錯）
    with st.expander("🧩 查看原始資料（已隱藏部份欄位）", expanded=False):
        filtered = _filter_hidden_fields(order)
        st.json(filtered)


def render_order_details_from_transactional_data(order: Dict):
    """渲染訂單詳情（從交易數據API）

    目前交易數據的結構與訂單列表相近，直接共用同一套美化呈現邏輯。
    """
    render_order_details(order)


def delete_orders_by_date_range(start_date: datetime, end_date: datetime) -> Tuple[int, int]:
    """
    按日期範圍刪除訂單
    
    返回: (刪除前數量, 刪除成功數量)
    """
    try:
        db = get_database_connection()
        
        # 設定時間範圍（開始日期的 00:00:00 到結束日期的 23:59:59）
        start_dt = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 查詢該日期區間的訂單
        query = text("""
            SELECT id, order_number, created_at
            FROM orders
            WHERE created_at >= :start_dt AND created_at <= :end_dt
            ORDER BY id ASC
        """)
        
        candidates = db.execute(
            query,
            {"start_dt": start_dt, "end_dt": end_dt}
        ).fetchall()
        
        total_before = len(candidates)
        system_logger.info(f"找到 {total_before} 筆訂單，日期區間: {start_dt} ~ {end_dt}")
        
        # 刪除訂單
        deleted = 0
        for order_row in candidates:
            order_id = order_row[0]
            try:
                # 先刪除訂單項目
                delete_items_query = text("""
                    DELETE FROM order_items WHERE order_id = :order_id
                """)
                db.execute(delete_items_query, {"order_id": order_id})
                
                # 再刪除訂單
                delete_order_query = text("""
                    DELETE FROM orders WHERE id = :order_id
                """)
                db.execute(delete_order_query, {"order_id": order_id})
                deleted += 1
            except Exception as e:
                system_logger.error(f"刪除訂單 {order_id} 失敗: {e}")
        
        db.commit()
        system_logger.info(f"刪除完成，共刪除 {deleted} 筆訂單")
        
        return total_before, deleted
        
    except Exception as e:
        db.rollback()
        system_logger.error(f"批量刪除訂單失敗: {e}")
        raise
    finally:
        db.close()


def delete_order_by_number(order_number: str) -> bool:
    """
    按訂單編號刪除訂單
    
    返回: 是否刪除成功
    """
    try:
        db = get_database_connection()
        
        # 查詢訂單
        query = text("""
            SELECT id, order_number
            FROM orders
            WHERE order_number = :order_number
        """)
        
        result = db.execute(query, {"order_number": order_number}).fetchone()
        
        if not result:
            system_logger.warning(f"找不到訂單編號: {order_number}")
            return False
        
        order_id = result[0]
        
        # 刪除訂單項目
        delete_items_query = text("""
            DELETE FROM order_items WHERE order_id = :order_id
        """)
        db.execute(delete_items_query, {"order_id": order_id})
        
        # 刪除訂單
        delete_order_query = text("""
            DELETE FROM orders WHERE id = :order_id
        """)
        db.execute(delete_order_query, {"order_id": order_id})
        
        db.commit()
        system_logger.info(f"成功刪除訂單: {order_number} (ID: {order_id})")
        return True
        
    except Exception as e:
        db.rollback()
        system_logger.error(f"刪除訂單 {order_number} 失敗: {e}")
        raise
    finally:
        db.close()


def render_delete_by_date():
    """渲染按日期刪除界面"""
    st.markdown("### 📅 按日期範圍刪除訂單")
    
    st.warning("⚠️ **警告**：此操作不可逆，請謹慎使用！刪除後無法恢復訂單數據。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "開始日期",
            value=datetime.now().date(),
            help="選擇要刪除訂單的起始日期"
        )
    
    with col2:
        end_date = st.date_input(
            "結束日期",
            value=datetime.now().date(),
            help="選擇要刪除訂單的結束日期"
        )
    
    # 日期驗證
    if start_date > end_date:
        st.error("❌ 開始日期不能晚於結束日期！")
        return
    
    # 顯示將要刪除的日期範圍
    st.info(f"📆 將刪除日期範圍：{start_date} 至 {end_date}")
    
    # 安全確認機制
    st.markdown("---")
    st.markdown("#### 🔒 安全確認")
    
    confirmation_text = st.text_input(
        "請輸入 'DELETE' 以確認刪除",
        placeholder="輸入 DELETE",
        help="為防止誤操作，請輸入 DELETE 確認"
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🗑️ 確認刪除", type="primary", width='stretch', disabled=(confirmation_text != "DELETE")):
            if confirmation_text == "DELETE":
                with st.spinner("正在刪除訂單..."):
                    try:
                        # 轉換為 datetime
                        start_dt = datetime.combine(start_date, datetime.min.time())
                        end_dt = datetime.combine(end_date, datetime.max.time())
                        
                        # 執行刪除
                        total_before, deleted = delete_orders_by_date_range(start_dt, end_dt)
                        
                        # 顯示結果
                        st.success(f"✅ 刪除完成！")
                        
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("刪除前數量", total_before)
                        with col_stat2:
                            st.metric("成功刪除", deleted)
                        with col_stat3:
                            remain = total_before - deleted
                            st.metric("剩餘", remain)
                        
                        if deleted == total_before and total_before > 0:
                            st.balloons()
                            st.success(f"🎉 已成功刪除該日期範圍內的所有 {deleted} 筆訂單！")
                        elif total_before == 0:
                            st.info("ℹ️ 該日期範圍內沒有找到訂單")
                        else:
                            st.warning(f"⚠️ 部分訂單刪除失敗，剩餘 {total_before - deleted} 筆")
                            
                    except Exception as e:
                        st.error(f"❌ 刪除失敗: {e}")
                        system_logger.error(f"按日期刪除訂單失敗: {e}")
            else:
                st.warning("⚠️ 請輸入 'DELETE' 以確認刪除")
    
    with col_btn2:
        if st.button("🔄 重置", width='stretch'):
            st.rerun()


def render_delete_by_number():
    """渲染按訂單編號刪除界面"""
    st.markdown("### 📝 按訂單編號刪除")
    
    st.warning("⚠️ **警告**：此操作不可逆，請謹慎使用！刪除後無法恢復訂單數據。")
    
    order_number = st.text_input(
        "訂單編號",
        placeholder="例如：600000031762416122",
        help="輸入要刪除的訂單編號"
    )
    
    if order_number:
        st.info(f"📋 將刪除訂單編號：{order_number}")
    
    # 安全確認機制
    st.markdown("---")
    st.markdown("#### 🔒 安全確認")
    
    confirmation_text = st.text_input(
        "請輸入訂單編號以確認刪除",
        placeholder="再次輸入訂單編號",
        help="為防止誤操作，請再次輸入訂單編號"
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🗑️ 確認刪除", type="primary", width='stretch', disabled=(not order_number or confirmation_text != order_number)):
            if not order_number:
                st.warning("⚠️ 請輸入訂單編號")
            elif confirmation_text != order_number:
                st.warning("⚠️ 確認訂單編號不匹配，請重新輸入")
            else:
                with st.spinner("正在刪除訂單..."):
                    try:
                        success = delete_order_by_number(order_number)
                        
                        if success:
                            st.success(f"✅ 訂單 {order_number} 已成功刪除！")
                            st.balloons()
                        else:
                            st.error(f"❌ 找不到訂單編號: {order_number}")
                            
                    except Exception as e:
                        st.error(f"❌ 刪除失敗: {e}")
                        system_logger.error(f"按訂單編號刪除失敗: {e}")
    
    with col_btn2:
        if st.button("🔄 重置", width='stretch'):
            st.rerun()


def render_order_delete_tab():
    """訂單刪除功能標籤頁"""
    st.subheader("🗑️ 訂單刪除")
    
    # 顯示重要警告
    st.error("⚠️ **重要提示**：訂單刪除操作無法撤銷！請務必確認後再執行。建議在刪除前先備份數據。")
    
    # 刪除方式選擇
    delete_method = st.radio(
        "選擇刪除方式",
        ["📅 按日期範圍刪除", "📝 按訂單編號刪除"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # 根據選擇的刪除方式顯示對應的界面
    if delete_method == "📅 按日期範圍刪除":
        render_delete_by_date()
    elif delete_method == "📝 按訂單編號刪除":
        render_delete_by_number()


def order_management_page():
    """訂單管理主頁面"""
    st.header("📦 訂單管理")
    st.markdown("---")
    
    # 創建標籤頁
    tab1, tab2, tab3 = st.tabs(["🔍 訂單查詢", "📤 訂單上傳", "🗑️ 訂單刪除"])
    
    with tab1:
        render_order_query_tab()
        
    with tab2:
        render_order_upload_tab()
    
    with tab3:
        render_order_delete_tab()

