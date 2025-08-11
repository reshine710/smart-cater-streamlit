import streamlit as st
import time

def recipe_settings_page():
    """配方設定頁面"""
    st.title("⚙️ 配方設定")
    
    menu_items = st.session_state.api.get_menu_items()
    
    # 選擇商品
    selected_item = st.selectbox(
        "選擇商品",
        options=menu_items,
        format_func=lambda x: f"{x['name']} ({x['cooking_method']})"
    )
    
    if selected_item:
        st.subheader(f"🍽️ {selected_item['name']} 加熱參數設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**加熱方式**: {selected_item['cooking_method']}")
            
            if selected_item['cooking_method'] == '蒸氣':
                steam_temp = st.slider("蒸氣溫度 (°C)", 80, 120, 100)
                steam_time = st.slider("加熱時間 (秒)", 30, 300, 120)
                steam_pressure = st.slider("蒸氣壓力 (bar)", 1.0, 3.0, 1.5, 0.1)
                
                st.json({
                    "cooking_method": "steam",
                    "temperature": steam_temp,
                    "time_seconds": steam_time,
                    "pressure_bar": steam_pressure
                })
            
            else:  # 微波
                microwave_power = st.slider("微波功率 (%)", 30, 100, 80)
                microwave_time = st.slider("加熱時間 (秒)", 30, 180, 90)
                
                st.json({
                    "cooking_method": "microwave",
                    "power_percent": microwave_power,
                    "time_seconds": microwave_time
                })
        
        with col2:
            st.subheader("預覽效果")
            
            # 模擬加熱過程
            if st.button("🔥 模擬加熱過程"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(101):
                    progress_bar.progress(i)
                    if i < 30:
                        status_text.text(f"預熱中... {i}%")
                    elif i < 80:
                        status_text.text(f"加熱中... {i}%")
                    else:
                        status_text.text(f"完成中... {i}%")
                    time.sleep(0.02)
                
                st.success("✅ 加熱完成！")
        
        # 儲存設定
        if st.button("💾 儲存配方設定", use_container_width=True):
            st.success(f"已儲存 {selected_item['name']} 的配方設定")
