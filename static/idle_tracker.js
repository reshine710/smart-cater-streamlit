/**
 * 閒置追蹤JavaScript
 * 監控使用者活動並與Streamlit通信
 */

class IdleTracker {
    constructor() {
        this.idleTimeout = 30 * 60 * 1000; // 30分鐘（毫秒）
        this.warningTime = 5 * 60 * 1000;  // 5分鐘警告（毫秒）
        this.lastActivity = Date.now();
        this.warningShown = false;
        this.timer = null;
        this.warningTimer = null;
        
        this.init();
    }
    
    init() {
        // 監聽各種使用者活動事件
        const events = [
            'mousedown', 'mousemove', 'keypress', 'scroll', 
            'touchstart', 'click', 'keydown'
        ];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.resetTimer();
            }, true);
        });
        
        // 開始計時器
        this.startTimer();
        
        console.log('Idle tracker initialized - 30 minute timeout');
    }
    
    resetTimer() {
        this.lastActivity = Date.now();
        this.warningShown = false;
        
        // 清除現有計時器
        if (this.timer) {
            clearTimeout(this.timer);
        }
        if (this.warningTimer) {
            clearTimeout(this.warningTimer);
        }
        
        // 重新開始計時器
        this.startTimer();
        
        // 通知Streamlit活動已更新
        this.notifyStreamlit('activity_updated');
    }
    
    startTimer() {
        // 設置警告計時器
        this.warningTimer = setTimeout(() => {
            this.showWarning();
        }, this.idleTimeout - this.warningTime);
        
        // 設置登出計時器
        this.timer = setTimeout(() => {
            this.performLogout();
        }, this.idleTimeout);
    }
    
    showWarning() {
        if (this.warningShown) return;
        
        this.warningShown = true;
        
        // 通知Streamlit顯示警告
        this.notifyStreamlit('show_warning');
        
        console.log('Idle warning triggered');
    }
    
    performLogout() {
        // 通知Streamlit執行登出
        this.notifyStreamlit('perform_logout');
        
        console.log('Idle logout triggered');
    }
    
    notifyStreamlit(action) {
        // 使用Streamlit的通信機制
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({
                type: 'idle_tracker',
                action: action,
                timestamp: Date.now()
            }, '*');
        }
        
        // 備用方案：使用localStorage
        try {
            localStorage.setItem('idle_tracker_action', JSON.stringify({
                action: action,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.warn('Could not use localStorage for idle tracking');
        }
    }
    
    getRemainingTime() {
        const elapsed = Date.now() - this.lastActivity;
        return Math.max(0, this.idleTimeout - elapsed);
    }
    
    getStatus() {
        const remaining = this.getRemainingTime();
        const remainingMinutes = Math.floor(remaining / (60 * 1000));
        const remainingSeconds = Math.floor((remaining % (60 * 1000)) / 1000);
        
        return {
            remainingTime: remaining,
            remainingMinutes: remainingMinutes,
            remainingSeconds: remainingSeconds,
            warningShown: this.warningShown,
            lastActivity: new Date(this.lastActivity).toLocaleTimeString()
        };
    }
}

// 初始化閒置追蹤器
let idleTracker = null;

// 等待頁面載入完成
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        idleTracker = new IdleTracker();
    });
} else {
    idleTracker = new IdleTracker();
}

// 導出到全局作用域
window.idleTracker = idleTracker;
