"""
閒置追蹤Streamlit組件
用於載入JavaScript並與前端通信
"""

import streamlit as st
import streamlit.components.v1 as components
import os
from pathlib import Path

def render_idle_tracker():
    """渲染閒置追蹤組件"""
    # 獲取靜態文件路徑
    static_dir = Path(__file__).parent / "static"
    js_file = static_dir / "idle_tracker.js"
    
    if not js_file.exists():
        st.warning("⚠️ 閒置追蹤JavaScript文件未找到")
        return
    
    # 讀取JavaScript內容
    with open(js_file, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # 創建HTML內容
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Idle Tracker</title>
    </head>
    <body>
        <script>
        {js_content}
        </script>
        <script>
        // 監聽來自Streamlit的消息
        window.addEventListener('message', function(event) {{
            if (event.data && event.data.type === 'streamlit') {{
                console.log('Received Streamlit message:', event.data);
            }}
        }});
        
        // 定期檢查localStorage中的動作
        setInterval(function() {{
            try {{
                const action = localStorage.getItem('idle_tracker_action');
                if (action) {{
                    const data = JSON.parse(action);
                    console.log('Idle tracker action:', data);
                    
                    // 清除已處理的動作
                    localStorage.removeItem('idle_tracker_action');
                }}
            }} catch (e) {{
                // 忽略localStorage錯誤
            }}
        }}, 1000);
        </script>
    </body>
    </html>
    """
    
    # 使用Streamlit組件渲染
    components.html(html_content, height=0, width=0)

def check_idle_actions():
    """檢查閒置追蹤動作（簡化版本）"""
    # 這個函數可以在需要時被調用來檢查JavaScript的動作
    # 由於Streamlit的限制，我們主要依賴服務端的閒置檢查
    pass
