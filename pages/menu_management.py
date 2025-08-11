import streamlit as st

def menu_management_page():
    """菜單管理頁面"""
    st.title("🍽️ 菜單管理")
    
    tab1, tab2 = st.tabs(["固定菜單", "AI 動態菜單"])
    
    with tab1:
        st.subheader("固定菜單設定")
        
        menu_items = st.session_state.api.get_menu_items()
        
        # 新增菜單項目
        with st.expander("➕ 新增菜單項目"):
            with st.form("add_menu_item"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("商品名稱")
                    new_price = st.number_input("價格", min_value=0.0, step=1.0)
                    new_category = st.selectbox("分類", ["飲品", "主食", "點心"])
                
                with col2:
                    new_cooking_method = st.selectbox("加熱方式", ["蒸氣", "微波"])
                    new_image_url = st.text_input("圖片網址")
                    new_is_active = st.checkbox("啟用", value=True)
                
                if st.form_submit_button("新增商品"):
                    st.success(f"已新增商品: {new_name}")
        
        # 現有菜單項目
        st.subheader("現有菜單項目")
        
        for item in menu_items:
            with st.expander(f"{'✅' if item['is_active'] else '❌'} {item['name']} - NT$ {item['price']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**分類**: {item['category']}")
                    st.write(f"**加熱方式**: {item['cooking_method']}")
                
                with col2:
                    st.write(f"**價格**: NT$ {item['price']}")
                    st.write(f"**狀態**: {'啟用' if item['is_active'] else '停用'}")
                
                with col3:
                    if st.button(f"編輯", key=f"edit_{item['id']}"):
                        st.info("編輯功能")
                    if item['is_active']:
                        if st.button(f"停用", key=f"deactivate_{item['id']}"):
                            st.warning(f"{item['name']} 已停用")
                    else:
                        if st.button(f"啟用", key=f"activate_{item['id']}"):
                            st.success(f"{item['name']} 已啟用")
    
    with tab2:
        st.subheader("AI 動態菜單")
        
        # 模擬 AI 推薦
        st.info("🤖 AI 分析結果")
        
        ai_recommendations = [
            {
                "item_name": "拿鐵咖啡",
                "suggested_price": 80,
                "confidence": 0.85,
                "reason": "根據天氣預報，明日氣溫較低，熱飲需求預期上升"
            },
            {
                "item_name": "雞肉便當",
                "suggested_price": 125,
                "confidence": 0.72,
                "reason": "午餐時段銷量穩定，建議微調價格"
            }
        ]
        
        for rec in ai_recommendations:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{rec['item_name']}**")
                    st.write(f"推薦理由: {rec['reason']}")
                
                with col2:
                    st.write(f"建議價格: NT$ {rec['suggested_price']}")
                    st.write(f"信心度: {rec['confidence']:.0%}")
                
                with col3:
                    if st.button(f"採用建議", key=f"adopt_{rec['item_name']}"):
                        st.success(f"已採用 {rec['item_name']} 的 AI 建議")
                    if st.button(f"拒絕", key=f"reject_{rec['item_name']}"):
                        st.info(f"已拒絕 {rec['item_name']} 的建議")
                
                st.markdown("---")
