/**
 * 线材配置文件
 * 在这里统一管理所有线材的配置信息
 * 添加新线材时只需要在这个文件中添加配置即可
 */

// 线材配置对象
const CableConfig = {
    // 线材PID到名称的映射
    cableNames: {
        '0x3001': '云朵线',
        '0x0002': '魅族卷卷线',
        '0x3002': 'SlimBolt 细雳线 40Gbps',
        '0x3003': 'SlimBolt 细雳线 80Gbps',
        '0x3008': 'OK线',
        '0x7800': '苹果官方线',
        '0x4010': '苹果官方线',
        '0x4051': '酷态科',
        '0x3004': '花线',
        
        // 添加新线材示例（取消注释并修改）：
        // '0x1234': '您的新线材名称',
        // '0x5678': '雷电线',
    },

    // 线材样式配置
    cableStyles: {
        '云朵线': {
            // CSS类名
            cssClass: 'cloud-cable',
            // 端口0-2使用的图片文件名
            imageFile: 'yunduo.png',
            // 端口4使用的图片文件名  
            landImageFile: 'landyunduo.png',
            // 标签背景渐变色
            tagBackground: 'linear-gradient(135deg, #ffffff 0%, #e0f2fe 100%)',
            // 标签文字颜色
            tagTextColor: '#1565c0',
            // 标签阴影颜色 (rgba格式)
            tagShadowColor: 'rgba(255, 255, 255, 0.4)',
            // 充电背光颜色 (rgba格式)
            chargingGlowColor: {
                outer: 'rgba(255, 255, 255, 0.8)',
                inner: 'rgba(173, 216, 230, 0.4)',
                border: 'rgba(255, 255, 255, 0.6)',
                background: 'rgba(255, 255, 255, 0.1)'
            }
        },

        '魅族卷卷线': {
            cssClass: 'meizu-cable',
            imageFile: 'meizup.png',
            landImageFile: 'meizup.png',
            tagBackground: '#FF6ED8',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(255, 110, 216, 0.3)',
            chargingGlowColor: {
                outer: 'rgba(255, 110, 216, 0.6)',
                inner: 'rgba(255, 110, 216, 0.3)',
                border: 'rgba(255, 110, 216, 0.5)',
                background: 'rgba(255, 110, 216, 0.1)'
            }
        },

        'SlimBolt 细雳线 40Gbps': {
            cssClass: 'slimbolt',
            imageFile: 'xili.png',
            landImageFile: 'landxili2.png',
            tagBackground: 'linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(255, 107, 53, 0.3)',
            chargingGlowColor: {
                outer: 'rgba(255, 154, 86, 0.6)',
                inner: 'rgba(255, 107, 53, 0.3)',
                border: 'rgba(255, 154, 86, 0.5)',
                background: 'rgba(255, 154, 86, 0.1)'
            }
        },

        'SlimBolt 细雳线 80Gbps': {
            cssClass: 'slimbolt',
            imageFile: 'xili2.png',
            landImageFile: 'landxili2.png',
            tagBackground: 'linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(255, 107, 53, 0.3)',
            chargingGlowColor: {
                outer: 'rgba(255, 154, 86, 0.6)',
                inner: 'rgba(255, 107, 53, 0.3)',
                border: 'rgba(255, 154, 86, 0.5)',
                background: 'rgba(255, 154, 86, 0.1)'
            }
        },

        'OK线': {
            cssClass: 'ok-cable',
            imageFile: 'okokok.png',
            landImageFile: 'landokokok.png',
            tagBackground: 'linear-gradient(135deg, #87c7ff 0%, #a19cff 100%)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(79, 172, 254, 0.3)',
            chargingGlowColor: {
                outer: 'rgba(135, 199, 255, 0.6)',
                inner: 'rgba(161, 156, 255, 0.3)',
                border: 'rgba(135, 199, 255, 0.5)',
                background: 'rgba(135, 199, 255, 0.1)'
            }
        },

        '苹果官方线': {
            cssClass: 'apple-official',
            imageFile: 'pingguox.png',
            landImageFile: 'landpingguo.png',
            tagBackground: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FFD23F 100%)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(255, 107, 53, 0.4)',
            chargingGlowColor: {
                outer: 'rgba(255, 107, 53, 0.6)',
                inner: 'rgba(247, 147, 30, 0.3)',
                border: 'rgba(255, 210, 63, 0.5)',
                background: 'rgba(255, 107, 53, 0.1)'
            }
        },

        '酷态科': {
            cssClass: 'kutaike-cable',
            imageFile: 'kutaike.png',
            landImageFile: 'landkutaik.png',
            tagBackground: 'linear-gradient(135deg, #8B5CF6, #06B6D4)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(139, 92, 246, 0.4)',
            chargingGlowColor: {
                outer: 'rgba(139, 92, 246, 0.6)',
                inner: 'rgba(6, 182, 212, 0.3)',
                border: 'rgba(139, 92, 246, 0.5)',
                background: 'rgba(139, 92, 246, 0.1)'
            }
        },

        '花线': {
            cssClass: 'flower-cable',
            imageFile: 'huaxian.png',
            landImageFile: 'landhuaxian.png',
            tagBackground: 'linear-gradient(45deg, #FF1493 0%, #FF1493 25%, #0080FF 25%, #0080FF 50%, #FF1493 50%, #FF1493 75%, #0080FF 75%, #0080FF 100%)',
            tagTextColor: '#ffffff',
            tagShadowColor: 'rgba(255, 20, 147, 0.4)',
            chargingGlowColor: {
                outer: 'rgba(255, 20, 147, 0.6)',
                inner: 'rgba(0, 128, 255, 0.3)',
                border: 'rgba(255, 20, 147, 0.5)',
                background: 'rgba(255, 20, 147, 0.1)'
            }
        },

        // 添加新线材样式示例（取消注释并修改）：
        /*
        '您的新线材名称': {
            cssClass: 'your-cable',
            imageFile: 'your-cable.png',
            landImageFile: 'your-cable-land.png',
            tagBackground: 'linear-gradient(135deg, #起始颜色 0%, #结束颜色 100%)',
            tagTextColor: '#文字颜色',
            tagShadowColor: 'rgba(R, G, B, 0.4)',
            chargingGlowColor: {
                outer: 'rgba(R, G, B, 0.6)',
                inner: 'rgba(R, G, B, 0.3)',
                border: 'rgba(R, G, B, 0.5)',
                background: 'rgba(R, G, B, 0.1)'
            }
        },
        */
    },

    // 默认线材样式（用于未配置的线材）
    defaultStyle: {
        cssClass: 'default',
        tagBackground: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        tagTextColor: '#ffffff',
        tagShadowColor: 'rgba(240, 147, 251, 0.3)',
        chargingGlowColor: {
            outer: 'rgba(0, 245, 255, 0.6)',
            inner: 'rgba(0, 245, 255, 0.3)',
            border: 'rgba(0, 245, 255, 0.5)',
            background: 'rgba(0, 245, 255, 0.1)'
        }
    },

    // 获取线材名称
    getCableName(cablePid) {
        return this.cableNames[cablePid] || (cablePid ? `线材 ${cablePid}` : '未知线材');
    },

    // 获取线材样式配置
    getCableStyle(cableName) {
        return this.cableStyles[cableName] || this.defaultStyle;
    },

    // 获取线材CSS类名
    getCableClass(cableName) {
        const style = this.getCableStyle(cableName);
        return style.cssClass;
    },

    // 获取充电背光样式类名
    getChargingClass(cableName) {
        if (cableName && cableName.includes('SlimBolt')) {
            return 'slimbolt';
        } else if (cableName === 'OK线') {
            return 'ok-cable';
        } else if (cableName === '魅族卷卷线') {
            return 'meizu-cable';
        } else if (cableName === '苹果官方线') {
            return 'apple-official';
        } else if (cableName === '云朵线') {
            return 'cloud-cable';
        } else if (cableName === '酷态科') {
            return 'kutaike-cable';
        } else if (cableName === '花线') {
            return 'flower-cable';
        } else {
            return 'default';
        }
    },

    // 生成CSS样式代码（用于动态生成样式）
    generateCSS() {
        let css = '';
        
        // 生成线材标签样式
        Object.entries(this.cableStyles).forEach(([cableName, style]) => {
            css += `
.cable-tag.${style.cssClass} {
    background: ${style.tagBackground};
    color: ${style.tagTextColor};
    font-weight: 600;
    box-shadow: 0 2px 8px ${style.tagShadowColor};
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.port-item.charging.${style.cssClass} {
    box-shadow: 0 0 20px ${style.chargingGlowColor.outer}, inset 0 0 20px ${style.chargingGlowColor.inner};
    border: 1px solid ${style.chargingGlowColor.border};
    background: ${style.chargingGlowColor.background};
}
`;
        });

        return css;
    }
};

// 导出配置对象
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CableConfig;
} else {
    window.CableConfig = CableConfig;
}