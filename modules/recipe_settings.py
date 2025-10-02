import streamlit as st
import time
from logger_config import ui_logger, system_logger

def recipe_settings_page():
    """配方設定頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing recipe settings page")
    st.title("🧾 配方設定")
    st.set_page_config(layout="wide",initial_sidebar_state="expanded")
    st.markdown("---")
    
    # 檢查管理員權限
    if not st.session_state.get('is_admin', False):
        st.error("❌ 權限不足：此功能僅限管理員使用")
        ui_logger.warning(f"Non-admin user {st.session_state.get('username', 'Unknown')} attempted to access recipe settings")
        return
    
    menu_items = st.session_state.api.get_menu_items()
    ui_logger.debug(f"Retrieved {len(menu_items)} menu items for recipe settings")
    
    if not menu_items:
        st.info("📝 目前沒有菜單項目，請先在菜單管理中新增項目")
        return
    
    # 選擇商品
    selected_item = st.selectbox(
        "🍽️ 選擇商品",
        options=menu_items,
        format_func=lambda x: f"{x.get('name', 'Unknown')} ({format_heating_method(x.get('heating_method', 'none'))})",
        help="選擇要設定加熱參數的菜單項目"
    )
    
    if selected_item:
        item_name = selected_item.get('name', 'Unknown')
        heating_method = selected_item.get('heating_method', 'none')
        heating_params = selected_item.get('heating_params') or {}
        current_heating_time = heating_params.get('time_seconds', 0) if isinstance(heating_params, dict) else 0
        
        st.subheader(f"🍽️ {item_name} 加熱參數設定")
        
        # 顯示項目基本資訊
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("💰 價格", f"${selected_item.get('price', 0)}")
        with col_info2:
            st.metric("🔥 加熱方式", format_heating_method(heating_method))
        with col_info3:
            status = "✅ 啟用" if selected_item.get('is_active', False) else "❌ 停用"
            st.metric("📊 狀態", status)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚙️ 加熱參數設定")
            
            # 顯示現有參數
            if heating_params and isinstance(heating_params, dict):
                st.info("📋 目前設定參數:")
                st.json(heating_params)
            else:
                st.info("📝 尚未設定加熱參數")
            
            if heating_method == 'steam':
                st.success("💨 蒸氣加熱參數設定")
                current_temp = heating_params.get('temperature', 100)
                current_pressure = heating_params.get('pressure_bar', 1.5)
                
                steam_temp = st.slider("蒸氣溫度 (°C)", 80, 120, current_temp)
                steam_time = st.slider("加熱時間 (秒)", 30, 300, current_heating_time or 120)
                steam_pressure = st.slider("蒸氣壓力 (bar)", 1.0, 3.0, current_pressure, 0.1)
                
                recipe_config = {
                    "heating_method": "steam",
                    "temperature": steam_temp,
                    "time_seconds": steam_time,
                    "pressure_bar": steam_pressure
                }
                
                st.code(f"新參數配置:\n{recipe_config}", language="json")
            
            elif heating_method == 'microwave':
                st.success("🔥 微波加熱參數設定")
                current_power = heating_params.get('power_percent', 80)
                
                microwave_power = st.slider("微波功率 (%)", 30, 100, current_power)
                microwave_time = st.slider("加熱時間 (秒)", 30, 180, current_heating_time or 90)
                
                recipe_config = {
                    "heating_method": "microwave",
                    "power_percent": microwave_power,
                    "time_seconds": microwave_time
                }
                
                st.code(f"新參數配置:\n{recipe_config}", language="json")
            
            else:  # none
                st.info("❄️ 無需加熱")
                st.write("此項目無需加熱，可直接供應。")
                recipe_config = {
                    "heating_method": "none",
                    "time_seconds": 0
                }
        
        with col2:
            st.subheader("🔮 項目預覽")
            
            # 顯示項目資訊
            if selected_item.get('image_url'):
                try:
                    st.image(selected_item['image_url'], width=200, caption=item_name)
                except:
                    st.write("🖼️ 無法載入圖片")
            else:
                st.write("🖼️ 無圖片")
            
            # 顯示項目描述
            if selected_item.get('description'):
                st.write(f"**📝 描述**: {selected_item['description']}")
            
            # 顯示標籤
            tags = selected_item.get('tags', [])
            if tags:
                st.write("**🏷️ 標籤**:")
                tag_names = [tag.get('name', '') for tag in tags if isinstance(tag, dict)]
                if tag_names:
                    # 使用 columns 來顯示標籤
                    tag_cols = st.columns(len(tag_names))
                    for i, tag in enumerate(tag_names):
                        with tag_cols[i]:
                            st.markdown(f"`{tag}`")
                else:
                    st.write("無標籤")
            
            # 顯示時間資訊
            if selected_item.get('created_at'):
                st.write(f"**📅 建立時間**: {selected_item['created_at'][:19]}")
            if selected_item.get('updated_at'):
                st.write(f"**🔄 更新時間**: {selected_item['updated_at'][:19]}")
            
            st.markdown("---")
            
            # 加熱參數預覽
            if heating_method != 'none':
                st.info(f"🔥 加熱方式：{format_heating_method(heating_method)}")
                heating_time = recipe_config.get('time_seconds', current_heating_time or 60)
                st.info(f"⏱️ 預計加熱時間：{heating_time} 秒")
            else:
                st.info("🍽️ 此項目無需加熱，可直接享用")
        
        st.markdown("---")
        
        # 操作按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 儲存配方設定", use_container_width=True):
                # TODO: 實現將配方設定儲存到 API 的功能
                # 可以調用 API 更新 heating_params
                ui_logger.info(f"Recipe settings saved for {item_name} by {st.session_state.get('username')}")
                ui_logger.debug(f"New heating params: {recipe_config}")
                st.success(f"✅ 已儲存 {item_name} 的配方設定")
                st.info("💡 提示：配方設定已更新，將在下次重新載入時生效")
                
        with col2:
            if st.button("🔄 重設為預設值", use_container_width=True):
                ui_logger.info(f"Recipe settings reset for {item_name} by {st.session_state.get('username')}")
                st.info(f"🔄 {item_name} 的配方設定已重設")
                st.rerun()
        
        with col3:
            if st.button("📋 查看詳細資訊", use_container_width=True):
                ui_logger.info(f"Viewing detailed info for {item_name}")
                with st.expander(f"📊 {item_name} 詳細資訊", expanded=True):
                    st.json(selected_item)
    else:
        st.info("👆 請先選擇一個菜單項目來設定加熱參數")
        
        # 顯示可用的菜單項目概覽
        if menu_items:
            st.subheader("📋 可用菜單項目")
            
            # 創建簡化的項目列表
            items_data = []
            for item in menu_items:
                items_data.append({
                    "ID": item.get('id', 'N/A'),
                    "名稱": item.get('name', 'Unknown'),
                    "價格": f"${item.get('price', 0)}",
                    "加熱方式": format_heating_method(item.get('heating_method', 'none')),
                    "狀態": "✅ 啟用" if item.get('is_active', False) else "❌ 停用"
                })
            
            import pandas as pd
            df = pd.DataFrame(items_data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def format_heating_method(method: str) -> str:
    """格式化加熱方式顯示"""
    method_map = {
        "none": "無需加熱",
        "microwave": "微波加熱",
        "steam": "蒸氣加熱"
    }
    return method_map.get(method, method)
