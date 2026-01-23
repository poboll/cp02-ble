/**
 * 统一线材资源管理系统
 * 实现线材图片自动匹配和样式统一管理
 */

class CableManager {
    constructor() {
        // 线材配置映射
        this.cableConfigs = new Map();
        
        // 线材图片缓存
        this.imageCache = new Map();
        
        // 初始化配置
        this.initializeConfigs();
        
        // 预加载图片
        this.preloadImages();
    }

    /**
     * 初始化线材配置
     */
    initializeConfigs() {
        // 从现有的 cable-config.js 导入配置
        if (typeof CableConfig !== 'undefined') {
            // 转换配置格式，添加自动匹配功能
            Object.entries(CableConfig.cableNames).forEach(([pid, name]) => {
                const style = CableConfig.getCableStyle(name);
                this.cableConfigs.set(pid, {
                    name: name,
                    pid: pid,
                    ...style,
                    // 自动生成CSS类名
                    autoClass: this.generateAutoClass(name),
                    // 图片尺寸配置
                    dimensions: this.getImageDimensions(name),
                    // 布局适配配置
                    layoutConfig: this.getLayoutConfig(name)
                });
            });
        }
        
        console.log('📦 线材配置已初始化，共', this.cableConfigs.size, '种线材');
    }

    /**
     * 根据线材名称生成CSS类名
     */
    generateAutoClass(cableName) {
        return cableName
            .toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^\w\-]/g, '')
            .replace(/^-+|-+$/g, '');
    }

    /**
     * 获取线材图片尺寸配置
     */
    getImageDimensions(cableName) {
        // 特殊线材需要保持原始比例
        const specialCables = ['苹果官方线', '酷态科', '花线'];
        
        if (specialCables.includes(cableName)) {
            return {
                standard: { width: 90, height: 'auto', maxHeight: 60 },
                compact: { width: 180, height: 'auto', maxHeight: 120 },
                land: { width: 21, height: 'auto', maxHeight: 51 },
                compactLand: { width: 42, height: 'auto', maxHeight: 102 }
            };
        } else {
            return {
                standard: { width: 90, height: 40 },
                compact: { width: 180, height: 80 },
                land: { width: 21, height: 51 },
                compactLand: { width: 42, height: 102 }
            };
        }
    }

    /**
     * 获取布局适配配置
     */
    getLayoutConfig(cableName) {
        return {
            objectFit: 'contain',
            objectPosition: 'center',
            imageRendering: 'auto',
            preserveAspectRatio: true
        };
    }

    /**
     * 预加载线材图片
     */
    async preloadImages() {
        const loadPromises = [];
        
        this.cableConfigs.forEach((config, pid) => {
            // 预加载主图片
            if (config.imageFile) {
                loadPromises.push(this.loadImage(config.imageFile, `${pid}-main`));
            }
            
            // 预加载端口4图片
            if (config.landImageFile) {
                loadPromises.push(this.loadImage(config.landImageFile, `${pid}-land`));
            }
        });

        try {
            await Promise.all(loadPromises);
            console.log('🖼️ 线材图片预加载完成');
        } catch (error) {
            console.warn('⚠️ 部分线材图片加载失败:', error);
        }
    }

    /**
     * 加载单个图片
     */
    loadImage(src, key) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.imageCache.set(key, {
                    element: img,
                    src: src,
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    aspectRatio: img.naturalWidth / img.naturalHeight
                });
                resolve(img);
            };
            img.onerror = () => reject(new Error(`Failed to load ${src}`));
            img.src = src;
        });
    }

    /**
     * 根据PID获取线材配置
     */
    getCableConfig(pid) {
        return this.cableConfigs.get(pid) || this.getDefaultConfig(pid);
    }

    /**
     * 获取默认配置
     */
    getDefaultConfig(pid) {
        return {
            name: pid ? `线材 ${pid}` : '未知线材',
            pid: pid,
            cssClass: 'default-cable',
            imageFile: 'putong.png',
            landImageFile: 'landput.png',
            dimensions: this.getImageDimensions('默认'),
            layoutConfig: this.getLayoutConfig('默认'),
            tagBackground: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            tagTextColor: '#ffffff'
        };
    }

    /**
     * 动态生成线材元素
     */
    createCableElement(pid, portIndex, isLandscape = false) {
        const config = this.getCableConfig(pid);
        const img = document.createElement('img');
        
        // 设置基本属性
        img.src = isLandscape ? config.landImageFile : config.imageFile;
        img.alt = config.name;
        img.className = this.generateCableClasses(config, portIndex, isLandscape);
        img.style.display = 'none';
        
        // 应用尺寸配置
        this.applyCableDimensions(img, config, isLandscape);
        
        return img;
    }

    /**
     * 生成线材CSS类名
     */
    generateCableClasses(config, portIndex, isLandscape) {
        const baseClass = isLandscape ? 'cable-land' : 'cable';
        const typeClass = config.autoClass || config.cssClass;
        const portClass = `cable-port-${portIndex}`;
        
        return `${baseClass}-${typeClass} ${portClass}`;
    }

    /**
     * 应用线材尺寸配置
     */
    applyCableDimensions(element, config, isLandscape) {
        const isCompact = document.querySelector('.container')?.classList.contains('compact-mode');
        const dimensionKey = isLandscape ? 
            (isCompact ? 'compactLand' : 'land') : 
            (isCompact ? 'compact' : 'standard');
        
        const dimensions = config.dimensions[dimensionKey];
        
        // 应用尺寸
        element.style.width = dimensions.width + 'px';
        if (dimensions.height === 'auto') {
            element.style.height = 'auto';
            if (dimensions.maxHeight) {
                element.style.maxHeight = dimensions.maxHeight + 'px';
            }
        } else {
            element.style.height = dimensions.height + 'px';
        }
        
        // 应用布局配置
        if (config.layoutConfig) {
            element.style.objectFit = config.layoutConfig.objectFit;
            element.style.objectPosition = config.layoutConfig.objectPosition;
            element.style.imageRendering = config.layoutConfig.imageRendering;
        }
    }

    /**
     * 更新现有线材元素的样式
     */
    updateCableStyles(isCompactMode) {
        this.cableConfigs.forEach((config, pid) => {
            // 更新主线材元素
            for (let i = 0; i < 3; i++) {
                const selector = `.cable-${config.autoClass || config.cssClass}.cable-port-${i}`;
                const element = document.querySelector(selector);
                if (element) {
                    this.applyCableDimensions(element, config, false);
                }
            }
            
            // 更新端口4线材元素
            const landSelector = `.cable-land-${config.autoClass || config.cssClass}.cable-port-3`;
            const landElement = document.querySelector(landSelector);
            if (landElement) {
                this.applyCableDimensions(landElement, config, true);
            }
        });
        
        console.log('🎨 线材样式已更新为', isCompactMode ? '简洁模式' : '标准模式');
    }

    /**
     * 自动检测并添加新线材
     */
    async autoDetectNewCables() {
        // 扫描项目目录中的线材图片
        const imageFiles = await this.scanCableImages();
        const newCables = [];
        
        imageFiles.forEach(filename => {
            if (!this.isKnownCableImage(filename)) {
                const cableName = this.extractCableNameFromFilename(filename);
                const pid = this.generatePidForNewCable(cableName);
                
                newCables.push({
                    pid: pid,
                    name: cableName,
                    imageFile: filename,
                    landImageFile: this.findLandscapeImage(filename)
                });
            }
        });
        
        if (newCables.length > 0) {
            console.log('🔍 发现新线材:', newCables);
            return newCables;
        }
        
        return [];
    }

    /**
     * 扫描线材图片文件
     */
    async scanCableImages() {
        // 这里可以通过文件API或预定义列表来获取图片文件
        // 由于浏览器限制，这里使用预定义的图片列表
        const knownImages = [
            'putong.png', 'yunduo.png', 'xili.png', 'xili2.png', 
            'okokok.png', 'meizup.png', 'pingguox.png', 'kutaike.png', 
            'huaxian.png'
        ];
        
        return knownImages;
    }

    /**
     * 检查是否为已知线材图片
     */
    isKnownCableImage(filename) {
        for (let config of this.cableConfigs.values()) {
            if (config.imageFile === filename || config.landImageFile === filename) {
                return true;
            }
        }
        return false;
    }

    /**
     * 从文件名提取线材名称
     */
    extractCableNameFromFilename(filename) {
        const nameMap = {
            'putong': '普通线',
            'yunduo': '云朵线',
            'xili': '细雳线',
            'okokok': 'OK线',
            'meizu': '魅族线',
            'pingguo': '苹果线',
            'kutaike': '酷态科线',
            'huaxian': '花线'
        };
        
        const baseName = filename.replace(/\.(png|jpg|jpeg|gif)$/i, '');
        return nameMap[baseName] || baseName;
    }

    /**
     * 为新线材生成PID
     */
    generatePidForNewCable(cableName) {
        // 生成一个唯一的PID
        let counter = 0x9000;
        while (this.cableConfigs.has(`0x${counter.toString(16).toUpperCase()}`)) {
            counter++;
        }
        return `0x${counter.toString(16).toUpperCase()}`;
    }

    /**
     * 查找对应的横屏图片
     */
    findLandscapeImage(mainImage) {
        const baseName = mainImage.replace(/\.(png|jpg|jpeg|gif)$/i, '');
        return `land${baseName}.png`;
    }

    /**
     * 动态生成CSS样式
     */
    generateDynamicCSS() {
        let css = `
/* 动态生成的线材样式 */
`;
        
        this.cableConfigs.forEach((config, pid) => {
            const className = config.autoClass || config.cssClass;
            
            css += `
/* ${config.name} 样式 */
.cable-${className}, .cable-land-${className} {
    position: absolute;
    z-index: 2;
    transition: all 0.3s ease;
    object-fit: ${config.layoutConfig.objectFit};
    object-position: ${config.layoutConfig.objectPosition};
    image-rendering: ${config.layoutConfig.imageRendering};
}

.cable-tag.${className} {
    background: ${config.tagBackground};
    color: ${config.tagTextColor};
    font-weight: 600;
    box-shadow: 0 2px 8px ${config.tagShadowColor || 'rgba(0,0,0,0.3)'};
}
`;
        });
        
        return css;
    }

    /**
     * 注入动态样式到页面
     */
    injectDynamicStyles() {
        const styleId = 'cable-manager-styles';
        let styleElement = document.getElementById(styleId);
        
        if (!styleElement) {
            styleElement = document.createElement('style');
            styleElement.id = styleId;
            document.head.appendChild(styleElement);
        }
        
        styleElement.textContent = this.generateDynamicCSS();
        console.log('💉 动态线材样式已注入');
    }
}

// 创建全局实例
window.cableManager = new CableManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CableManager;
}