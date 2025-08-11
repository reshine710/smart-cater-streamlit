import streamlit as st

def machine_status_page():
    """機台狀態頁面"""
    st.title("🖥️ 機台狀態監控")
    
    machines = st.session_state.api.get_machines()
    
    # 狀態總覽
    col1, col2, col3 = st.columns(3)
    
    status_counts = {}
    for machine in machines:
        status = machine['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    with col1:
        st.metric("🟢 線上", status_counts.get('online', 0))
    with col2:
        st.metric("🟡 維護中", status_counts.get('maintenance', 0))
    with col3:
        st.metric("🔴 離線", status_counts.get('offline', 0))
    
    st.markdown("---")
    
    # 機台詳細狀態
    st.subheader("機台詳細狀態")
    
    for machine in machines:
        with st.expander(f"📍 {machine['name']} ({machine['machine_code']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = {
                    'online': '🟢',
                    'maintenance': '🟡',
                    'offline': '🔴'
                }
                st.write(f"**狀態**: {status_color.get(machine['status'], '⚪')} {machine['status']}")
                st.write(f"**位置**: {machine['location']}")
            
            with col2:
                if machine['temperature']:
                    st.write(f"**溫度**: {machine['temperature']}°C")
                else:
                    st.write("**溫度**: N/A")
                st.write(f"**最後心跳**: {machine['last_heartbeat']}")
            
            with col3:
                if st.button(f"發送重啟命令", key=f"restart_{machine['id']}"):
                    st.success(f"已發送重啟命令至 {machine['name']}")
                if st.button(f"設為維護模式", key=f"maintenance_{machine['id']}"):
                    st.info(f"{machine['name']} 已設為維護模式")
