// 热重载功能 - 监听文件变化并自动刷新页面
let lastModified = {};

function checkForUpdates() {
    // 检查CSS文件是否有更新
    fetch('/api/file-status?file=styles.css')
        .then(response => response.json())
        .then(data => {
            if (lastModified.css && lastModified.css !== data.lastModified) {
                console.log('🔄 CSS文件已更新，重新加载样式...');
                reloadCSS();
            }
            lastModified.css = data.lastModified;
        })
        .catch(err => console.log('检查CSS更新失败:', err));

    // 检查JS文件是否有更新
    fetch('/api/file-status?file=script.js')
        .then(response => response.json())
        .then(data => {
            if (lastModified.js && lastModified.js !== data.lastModified) {
                console.log('🔄 JavaScript文件已更新，重新加载页面...');
                location.reload();
            }
            lastModified.js = data.lastModified;
        })
        .catch(err => console.log('检查JS更新失败:', err));
}

function reloadCSS() {
    // 重新加载CSS文件
    const links = document.querySelectorAll('link[rel="stylesheet"]');
    links.forEach(link => {
        const href = link.href;
        const newHref = href.includes('?') ? 
            href.split('?')[0] + '?v=' + Date.now() : 
            href + '?v=' + Date.now();
        link.href = newHref;
    });
    
    // 显示更新提示
    showUpdateNotification('样式已更新');
}

function showUpdateNotification(message) {
    // 创建更新提示
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        transition: opacity 0.3s;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // 3秒后自动消失
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// 每2秒检查一次文件更新
setInterval(checkForUpdates, 2000);

// 页面加载完成后开始监听
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 热重载功能已启动，正在监听文件变化...');
    checkForUpdates(); // 立即检查一次
});