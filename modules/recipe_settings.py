import streamlit as st
import time
from typing import Dict, Optional
from logger_config import ui_logger, system_logger
from modules.menu_management import render_five_stage_heating_params, format_heating_method

def recipe_settings_page():
    """配方設定頁面"""
    ui_logger.info(f"User {st.session_state.get('username', 'Unknown')} accessing recipe settings page")
    st.title("🧾 配方設定")
    st.markdown("---")
    
    # 檢查管理員權限（管理員或以上可訪問）
    from utils.permissions import is_admin_or_above, show_permission_error
    if not is_admin_or_above():
        show_permission_error('update')
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
        item_id = selected_item.get('id')
        item_name = selected_item.get('name', 'Unknown')
        heating_method = selected_item.get('heating_method', 'none')
        heating_params = selected_item.get('heating_params') or {}
        if not isinstance(heating_params, dict):
            heating_params = {}
        
        st.subheader(f"🍽️ {item_name} 加熱參數設定（五段式）")
        
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
            
            # 使用五段式加熱參數設定
            if heating_method == 'none':
                st.info("❄️ 無需加熱")
                st.write("此項目無需加熱，可直接供應。")
                recipe_config = None
            else:
                recipe_config = render_five_stage_heating_params(
                    heating_method,
                    heating_params if heating_params else None,
                    key_prefix=f"recipe_{item_id}"
                )
        
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
            from utils import format_datetime_display
            if selected_item.get('created_at'):
                st.write(f"**📅 建立時間**: {format_datetime_display(selected_item['created_at'])}")
            if selected_item.get('updated_at'):
                st.write(f"**🔄 更新時間**: {format_datetime_display(selected_item['updated_at'])}")
            
            st.markdown("---")
            
            # 加熱參數預覽
            if heating_method != 'none' and recipe_config:
                st.info(f"🔥 加熱方式：{format_heating_method(heating_method)}")
                
                # 計算總時間
                total_time = 0
                # 暫時隱藏混合模式處理
                # if heating_method == 'both':
                #     # 混合模式：取兩者總時間的最大值
                #     microwave_time = sum(p.get('time', 0) for p in recipe_config.get('microwave', {}).values())
                #     steam_time = sum(p.get('time', 0) for p in recipe_config.get('steam', {}).values())
                #     total_time = max(microwave_time, steam_time)
                # else:
                total_time = sum(p.get('time', 0) for p in recipe_config.values())
                
                st.info(f"⏱️ 預計總加熱時間：{total_time} 秒")
            else:
                st.info("🍽️ 此項目無需加熱，可直接享用")
        
        st.markdown("---")
        
        # 操作按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 儲存配方設定", width="stretch", type="primary"):
                if not item_id:
                    st.error("❌ 無法取得菜單項目 ID")
                else:
                    update_data = {
                        "heating_method": heating_method,
                        "heating_params": recipe_config
                    }
                    
                    ui_logger.info(f"Recipe settings saved for {item_name} (ID: {item_id}) by {st.session_state.get('username')}")
                    ui_logger.debug(f"Update data: {update_data}")
                    
                    # 調用 API 更新
                    result = st.session_state.api.update_menu_item(item_id, update_data)
                    if result:
                        st.success(f"✅ 已儲存 {item_name} 的配方設定")
                        st.toast(f"🎉 配方設定已更新：{item_name}", icon="✅", duration='long')
                        ui_logger.info(f"Recipe settings saved successfully for {item_name} (ID: {item_id})")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 儲存失敗，請稍後再試")
                        ui_logger.error(f"Failed to save recipe settings for {item_name} (ID: {item_id})")
                
        with col2:
            if st.button("🔄 重設為預設值", width="stretch"):
                if not item_id:
                    st.error("❌ 無法取得菜單項目 ID")
                else:
                    # 根據加熱方式設定預設值（五段式結構）
                    if heating_method == 'steam':
                        default_config = {
                            "first_process": {"time": 60, "power1": 0, "power2": 0, "power3": 0},
                            "second_process": {"time": 30, "power1": 0, "power2": 0, "power3": 0},
                            "third_process": {"time": 20, "power1": 0, "power2": 0, "power3": 0},
                            "fourth_process": {"time": 15, "power1": 0, "power2": 0, "power3": 0},
                            "fifth_process": {"time": 10, "power1": 0, "power2": 0, "power3": 0}
                        }
                    elif heating_method == 'microwave':
                        default_config = {
                            "first_process": {"time": 70, "power1": 70, "power2": 70, "power3": 70},
                            "second_process": {"time": 25, "power1": 85, "power2": 85, "power3": 85},
                            "third_process": {"time": 40, "power1": 0, "power2": 0, "power3": 0},
                            "fourth_process": {"time": 50, "power1": 100, "power2": 100, "power3": 100},
                            "fifth_process": {"time": 50, "power1": 100, "power2": 100, "power3": 100}
                        }
                    # 暫時隱藏混合模式，不開放給用戶使用
                    # elif heating_method == 'both':
                    #     default_config = {
                    #         "microwave": {
                    #             "first_process": {"time": 70, "power1": 70, "power2": 70, "power3": 70},
                    #             "second_process": {"time": 25, "power1": 85, "power2": 85, "power3": 85},
                    #             "third_process": {"time": 40, "power1": 0, "power2": 0, "power3": 0},
                    #             "fourth_process": {"time": 50, "power1": 100, "power2": 100, "power3": 100},
                    #             "fifth_process": {"time": 50, "power1": 100, "power2": 100, "power3": 100}
                    #         },
                    #         "steam": {
                    #             "first_process": {"time": 60, "power1": 0, "power2": 0, "power3": 0},
                    #             "second_process": {"time": 30, "power1": 0, "power2": 0, "power3": 0},
                    #             "third_process": {"time": 20, "power1": 0, "power2": 0, "power3": 0},
                    #             "fourth_process": {"time": 15, "power1": 0, "power2": 0, "power3": 0},
                    #             "fifth_process": {"time": 10, "power1": 0, "power2": 0, "power3": 0}
                    #         }
                    #     }
                    else:  # none
                        default_config = None
                    
                    update_data = {
                        "heating_method": heating_method,
                        "heating_params": default_config
                    }
                    
                    ui_logger.info(f"Recipe settings reset for {item_name} (ID: {item_id}) by {st.session_state.get('username')}")
                    
                    result = st.session_state.api.update_menu_item(item_id, update_data)
                    if result:
                        st.success(f"✅ {item_name} 的配方設定已重設為預設值")
                        st.toast(f"🔄 配方設定已重設：{item_name}", icon="✅", duration='long')
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 重設失敗，請稍後再試")
        
        with col3:
            if st.button("📋 查看詳細資訊", width="stretch"):
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
            st.dataframe(df, width="stretch", hide_index=True)


# format_heating_method 已從 menu_management 導入，無需重複定義
