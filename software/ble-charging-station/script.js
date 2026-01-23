class ChargingStationMonitor {
    constructor() {
        this.dataUrl = '/api/port-status';
        this.updateInterval = 3000; // 3秒更新一次
        this.chart = null;
        this.chartMode = 'realtime'; // 'realtime', 'tenminute', 'hourly'

        // 数据存储
        this.realtimeData = [];
        this.realtimeLabels = [];
        this.tenMinuteData = new Map();
        this.hourlyData = new Map();

        this.maxDataPoints = 30;
        this.maxTenMinutePoints = 144;
        this.maxHourlyPoints = 24;

        this.previousValues = {};
        this.portData = {};
        this.retryCount = 0;
        this.maxRetries = 5; // 增加最大重试次数，特别是移动设备

        // 屏幕唤醒锁相关
        this.wakeLock = null;
        this.isWakeLockEnabled = true;

        // 3D视图旋转状态
        this.isRotated = false;

        // 布局模式状态
        this.isCompactMode = false;

        // 布局切换动画标志
        this.isLayoutSwitching = false;

        // 设备连接状态
        this.isConnected = false;

        // 检测设备类型
        this.isMobile = this.detectMobileDevice();

        // 根据设备类型调整更新间隔
        if (this.isMobile) {
            this.updateInterval = 5000; // 移动设备5秒更新一次，减少网络压力
        }

        this.init();
    }

    // 检测移动设备
    detectMobileDevice() {
        const userAgent = navigator.userAgent;
        const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        const isSmallScreen = window.innerWidth <= 768;
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

        console.log('设备检测:', {
            userAgent: userAgent.substring(0, 50) + '...',
            isMobileUA,
            isSmallScreen,
            isTouchDevice,
            screenWidth: window.innerWidth
        });

        return isMobileUA || (isSmallScreen && isTouchDevice);
    }

    // 检查后端连接状态
    async checkConnectionStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            this.isConnected = data.connected;

            if (data.connected) {
                console.log('检测到已有连接:', data.device);
                
                // 恢复 UI 状态
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                if (statusDot) statusDot.className = 'status-dot';
                if (statusText) statusText.textContent = 'BLE在线';
                
                const disconnectBtn = document.getElementById('disconnectBtn');
                if (disconnectBtn) disconnectBtn.style.display = 'block';
                
                // 恢复 control panel 的状态
                this.updateControlPanelStatus();
            }
        } catch (e) {
            console.error('检查连接状态失败:', e);
        }
    }

    init() {
        this.setupChart();
        this.setupEventListeners();
        this.setupNetworkMonitoring();
        this.setupControlPanel(); // 初始化控制面板
        this.setupWebSocket();    // 初始化 WebSocket (新增)
        this.checkConnectionStatus(); // 检查初始连接状态
        this.startMonitoring();
        this.requestWakeLock();
        this.setupWakeLockHandlers();
    }

    // 设置网络状态监控
    setupNetworkMonitoring() {
        // 监听网络状态变化
        if ('navigator' in window && 'onLine' in navigator) {
            window.addEventListener('online', () => {
                console.log('网络已连接');
                const statusText = document.getElementById('statusText');
                if (statusText && statusText.textContent.includes('离线')) {
                    statusText.textContent = '网络已恢复，重新连接...';
                    this.retryCount = 0;
                    setTimeout(() => this.fetchData(), 1000);
                }
            });

            window.addEventListener('offline', () => {
                console.log('网络已断开');
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                if (statusDot) statusDot.className = 'status-dot disconnected';
                if (statusText) statusText.textContent = '网络离线';
            });

            // 初始网络状态检查
            if (!navigator.onLine) {
                console.log('初始检测：网络离线');
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                if (statusDot) statusDot.className = 'status-dot disconnected';
                if (statusText) statusText.textContent = '网络离线';
                return;
            }
        }

        // 监听Connection API（如果支持）
        if ('connection' in navigator) {
            const connection = navigator.connection;
            console.log('网络连接信息:', {
                effectiveType: connection.effectiveType,
                downlink: connection.downlink,
                rtt: connection.rtt
            });

            connection.addEventListener('change', () => {
                console.log('网络连接状态变化:', {
                    effectiveType: connection.effectiveType,
                    downlink: connection.downlink,
                    rtt: connection.rtt
                });
            });
        }
    }

    // 初始化 WebSocket 连接 (新增优化)
    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            console.log(`📡 连接 WebSocket: ${wsUrl}`);
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket 连接已建立');
                this.ws.send(JSON.stringify({ type: 'get_port_status' }));
                // 定时发送 Ping 和 获取数据 (3秒一次)
                this.pingInterval = setInterval(() => {
                    if (this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(JSON.stringify({ type: 'ping' }));
                        this.ws.send(JSON.stringify({ type: 'get_port_status' }));
                    }
                }, 3000);
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'port_status') {
                        const parsedData = this.parseBleData(message.data);
                        this.updateUI(parsedData);
                        this.updatePowerData(parsedData.totalPower);
                        
                        const statusDot = document.getElementById('statusDot');
                        const statusText = document.getElementById('statusText');
                        if (statusDot) statusDot.className = 'status-dot';
                        if (statusText) statusText.textContent = '实时同步中';
                        
                        this.retryCount = 0;
                    } else if (message.type === 'status') {
                        if (message.data.connected !== undefined) {
                            this.isConnected = message.data.connected;
                        }
                        if (message.data.connected) {
                            this.logAction && this.logAction(`设备已连接: ${message.data.device}`);
                        }
                    } else if (message.type === 'log') {
                        this.logAction && this.logAction(`[系统] ${message.message}`);
                    } else if (message.type === 'response' || message.type === 'action_response') {
                        this.handleActionResponse(message.action, message);
                    }
                } catch (e) {
                    console.error('WS 消息解析错误:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('⚠️ WebSocket 连接断开');
                if (this.pingInterval) clearInterval(this.pingInterval);
                setTimeout(() => this.setupWebSocket(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
            };
            
        } catch (error) {
            console.error('WebSocket 初始化失败，降级为轮询模式:', error);
            this.logAction && this.logAction('⚠️ 实时通信不可用，使用轮询模式');
            this.ws = null;
        }
    }

    setupChart() {
        const ctx = document.getElementById('powerChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '功率 (W)',
                    data: [],
                    borderColor: '#00f5ff',
                    backgroundColor: 'rgba(0, 245, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#00f5ff',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaa',
                            font: {
                                size: 12
                            }
                        }
                    },
                    y: {
                        display: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#aaa',
                            font: {
                                size: 12
                            },
                            callback: function (value) {
                                return value + 'W';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    setupEventListeners() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.isManualRefresh = true;
            this.fetchData();
        });

        // 三个图表模式切换按钮
        document.getElementById('realtimeToggle').addEventListener('click', () => {
            this.switchChartMode('realtime');
        });

        document.getElementById('tenMinuteToggle').addEventListener('click', () => {
            this.switchChartMode('tenminute');
        });

        document.getElementById('hourlyToggle').addEventListener('click', () => {
            this.switchChartMode('hourly');
        });

        // 屏幕常亮开关
        const wakeLockToggle = document.getElementById('wakeLockToggle');
        if (wakeLockToggle) {
            wakeLockToggle.addEventListener('click', () => {
                this.toggleWakeLock();
            });
        }

        // 3D视图旋转切换按钮
        const rotationToggle = document.getElementById('rotationToggle');
        if (rotationToggle) {
            rotationToggle.addEventListener('click', () => {
                this.toggle3DRotation();
            });
        }

        // 布局切换按钮
        // 新的头部布局切换按钮
        const headerLayoutToggle = document.getElementById('headerLayoutToggle');
        if (headerLayoutToggle) {
            headerLayoutToggle.addEventListener('click', () => {
                this.toggleLayout();
            });
        }

        // 保持原有的3D视图区域按钮（隐藏但保持功能）
        const layoutToggle = document.getElementById('layoutToggle');
        if (layoutToggle) {
            layoutToggle.addEventListener('click', () => {
                this.toggleLayout();
            });
        }
    }

    switchChartMode(mode) {
        this.chartMode = mode;

        // 更新按钮状态
        document.querySelectorAll('.chart-mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        const activeBtn = document.getElementById(mode === 'realtime' ? 'realtimeToggle' :
            mode === 'tenminute' ? 'tenMinuteToggle' : 'hourlyToggle');
        if (activeBtn) {
            activeBtn.classList.add('active');
        }

        this.updateChartDisplay();
    }

    startMonitoring() {
        clearInterval(this.monitoringInterval);
        clearTimeout(this.monitoringInterval);
        this.fetchData();
    }

    async fetchData() {
        // 如果有活跃的 WebSocket 连接，处理 WS 逻辑
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            if (this.isManualRefresh) {
                console.log('手动刷新: 通过WS请求数据');
                this.ws.send(JSON.stringify({ type: 'get_port_status' }));
                
                const refreshBtn = document.getElementById('refreshBtn');
                if (refreshBtn) {
                    refreshBtn.classList.add('loading');
                    setTimeout(() => refreshBtn.classList.remove('loading'), 800);
                }
                this.isManualRefresh = false;
            } else {
                // 非手动刷新，且WS活跃，跳过HTTP轮询 (WS有自己的定时器)
                console.log('WS活跃，跳过HTTP轮询');
            }
            return;
        }

        const refreshBtn = document.getElementById('refreshBtn');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        try {
            // UI反馈
            if (this.isManualRefresh) {
                refreshBtn.classList.add('loading');
                this.isManualRefresh = false;
            }
            if (this.retryCount > 0) statusText.textContent = '重连中...';

            const timeoutDuration = this.isMobile ? 15000 : 5000;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);

            const response = await fetch(this.dataUrl, {
                signal: controller.signal,
                headers: { 'Cache-Control': 'no-cache' }
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const bleData = await response.json();
            
            // 数据完整性校验
            if (!bleData || !bleData.connected) {
                throw new Error(bleData?.error || 'BLE未连接');
            }

            const parsedData = this.parseBleData(bleData);
            this.updateUI(parsedData);
            this.updatePowerData(parsedData.totalPower);

            // 重置状态
            statusDot.className = 'status-dot';
            statusText.textContent = 'BLE在线';
            this.retryCount = 0;
            
            // 动态调整下次轮询间隔
            const nextDelay = parsedData.activePorts === 0 ? 5000 : this.updateInterval;
            clearInterval(this.monitoringInterval);
            clearTimeout(this.monitoringInterval);
            this.monitoringInterval = setTimeout(() => this.fetchData(), nextDelay);

        } catch (error) {
            console.error('获取数据失败:', error);
            this.retryCount++;
            statusDot.className = 'status-dot disconnected';
            
            // 指数退避算法: 1s, 1.5s, 2.25s ... Max 30s
            const backoffDelay = Math.min(1000 * Math.pow(1.5, this.retryCount), 30000);
            
            statusText.textContent = `断开 (${this.retryCount})`;
            
            // 清除旧定时器，避免叠加
            clearInterval(this.monitoringInterval);
            clearTimeout(this.monitoringInterval);
            
            // 使用 setTimeout 递归调度，而非 setInterval
            this.monitoringInterval = setTimeout(() => this.fetchData(), backoffDelay);

        } finally {
            refreshBtn.classList.remove('loading');
        }
    }

    // 解析BLE数据
    parseBleData(bleData) {
        const portData = {};
        let totalPower = 0;
        let totalCurrent = 0;
        let maxVoltage = 0;
        let activePorts = 0;
        let wifiSignal = bleData.system?.wifiSignal || 0;
        let freeHeap = bleData.system?.freeHeap || 0;

        // 解析端口数据
        if (bleData.ports && Array.isArray(bleData.ports)) {
            bleData.ports.forEach((port, index) => {
                const cableName = this.getCableName(port.cablePid);
                const deviceName = this.getDeviceInfo(port.manufacturerVid, port.manufacturerPid);
                const batteryDeviceName = this.getBatteryDeviceInfo(port.batteryVid);
                const batteryPercentage = this.calculateBatteryPercentage(port.batteryLastFullCapacity, port.batteryPresentCapacity);
                const chargingTimeLeft = this.calculateChargingTime(port.batteryLastFullCapacity, port.batteryPresentCapacity, port.power);

                const portInfo = {
                    state: port.state || 0,
                    protocol: port.protocol || 0,
                    current: port.current || 0, // mA
                    voltage: port.voltage || 0, // mV
                    power: port.power || 0,     // W

                    // 新增字段
                    cablePid: port.cablePid || null,
                    cableName: cableName,
                    manufacturerVid: port.manufacturerVid || null,
                    manufacturerPid: port.manufacturerPid || null,
                    deviceName: deviceName,
                    batteryVid: port.batteryVid || null,
                    batteryDeviceName: batteryDeviceName,
                    batteryLastFullCapacity: port.batteryLastFullCapacity || 0,
                    batteryPresentCapacity: port.batteryPresentCapacity || 0,
                    batteryDesignCapacity: port.batteryDesignCapacity || 0,
                    batteryPercentage: batteryPercentage,
                    chargingTimeLeft: chargingTimeLeft
                };

                portData[index] = portInfo;

                totalPower += portInfo.power; // power已经是W单位，直接累加
                totalCurrent += portInfo.current;
                maxVoltage = Math.max(maxVoltage, portInfo.voltage);

                if (portInfo.current > 0) {
                    activePorts++;
                }
            });
        }

        return {
            ports: portData,
            totalPower: totalPower, // 已经是W单位，不需要再除以1000
            averageVoltage: maxVoltage / 1000, // 转换为V
            totalCurrent: totalCurrent / 1000, // 转换为A
            activePorts: activePorts,
            wifiSignal: wifiSignal,
            freeHeap: freeHeap,
            chargingStatus: activePorts > 0 ? `${activePorts}个端口充电中` : '待机',
            timestamp: Date.now()
        };
    }

    // 解析HTML页面数据
    parseHtmlData(htmlData) {
        const portData = {};
        let totalPower = 0;
        let totalCurrent = 0;
        let maxVoltage = 0;
        let activePorts = 0;
        let wifiSignal = htmlData.system?.wifiSignal || 0;
        let freeHeap = htmlData.system?.freeHeap || 0;

        // 解析端口数据
        if (htmlData.ports && Array.isArray(htmlData.ports)) {
            htmlData.ports.forEach((port, index) => {
                const cableName = this.getCableName(port.cablePid);
                const deviceName = this.getDeviceInfo(port.manufacturerVid, port.manufacturerPid);
                const batteryDeviceName = this.getBatteryDeviceInfo(port.batteryVid);
                const batteryPercentage = this.calculateBatteryPercentage(port.batteryLastFullCapacity, port.batteryPresentCapacity);
                const chargingTimeLeft = this.calculateChargingTime(port.batteryLastFullCapacity, port.batteryPresentCapacity, port.power);

                const portInfo = {
                    state: port.state || 0,
                    protocol: port.protocol || 0,
                    current: port.current || 0, // mA
                    voltage: port.voltage || 0, // mV
                    power: port.power || 0,     // W

                    // 新增字段
                    cablePid: port.cablePid || null,
                    cableName: cableName,
                    manufacturerVid: port.manufacturerVid || null,
                    manufacturerPid: port.manufacturerPid || null,
                    deviceName: deviceName,
                    batteryVid: port.batteryVid || null,
                    batteryDeviceName: batteryDeviceName,
                    batteryLastFullCapacity: port.batteryLastFullCapacity || 0,
                    batteryPresentCapacity: port.batteryPresentCapacity || 0,
                    batteryDesignCapacity: port.batteryDesignCapacity || 0,
                    batteryPercentage: batteryPercentage,
                    chargingTimeLeft: chargingTimeLeft
                };

                portData[index] = portInfo;

                totalPower += portInfo.power; // power已经是W单位，直接累加
                totalCurrent += portInfo.current;
                maxVoltage = Math.max(maxVoltage, portInfo.voltage);

                if (portInfo.current > 0) {
                    activePorts++;
                }
            });
        }

        return {
            ports: portData,
            totalPower: totalPower, // 已经是W单位，不需要再除以1000
            averageVoltage: maxVoltage / 1000, // 转换为V
            totalCurrent: totalCurrent / 1000, // 转换为A
            activePorts: activePorts,
            wifiSignal: wifiSignal,
            freeHeap: freeHeap,
            chargingStatus: activePorts > 0 ? `${activePorts}个端口充电中` : '待机',
            timestamp: Date.now()
        };
    }

    // 根据Cable PID获取线材名称（使用配置文件）
    // 根据Cable PID获取线材名称
    getCableName(cablePid) {
        // 检查CableConfig是否已加载
        if (typeof CableConfig !== 'undefined' && CableConfig.getCableName) {
            return CableConfig.getCableName(cablePid);
        }

        // 如果CableConfig未加载，使用备用映射
        const cableNames = {
            '0x3001': '云朵线',
            '0x0002': '魅族卷卷线',
            '0x3002': 'SlimBolt 细雳线 40Gbps',
            '0x3003': 'SlimBolt 细雳线 80Gbps',
            '0x3008': 'OK线',
            '0x7800': '苹果官方线',
            '0x4010': '苹果官方线',
            '0x4051': '酷态科',
            '0x3004': '花线',
        };
        return cableNames[cablePid] || (cablePid ? `线材 ${cablePid}` : '未知线材');
    }

    // 根据Manufacturer VID/PID获取设备名称
    getDeviceInfo(vid, pid) {
        const deviceMap = {
            '0x05AC': { // Apple Inc.
                // ---- iPhone 系列 ----
                '0x12A8': 'iPhone (通用 Lightning 模式)',
                '0x12A9': 'iPhone DFU 模式',
                '0x1290': 'iPhone 4/4S',
                '0x12A0': 'iPhone 5/5C/5S',
                '0x12A1': 'iPhone 6/6 Plus',
                '0x12A2': 'iPhone 6s/6s Plus',
                '0x12A3': 'iPhone 7/7 Plus',
                '0x12A4': 'iPhone 8/8 Plus',
                '0x12A5': 'iPhone X',
                '0x12A6': 'iPhone 11/11 Pro/11 Pro Max',
                '0x12A7': 'iPhone 12/12 Pro/12 mini',
                '0x7512': 'iPhone 15 Pro',
                '0x7519': 'iPhone 17 Pro',
                '0x7504': 'iPhone 12 (Lightning)',

                // ---- iPad / 平板 ----
                '0x12AB': 'iPad (通用 Lightning 模式)',
                '0x12B0': 'iPad Air 4/Air 5',
                '0x710D': 'iPad Air 5 (USB-C)',
                '0x12B1': 'iPad mini (5th/6th Gen)',
                '0x12B2': 'iPad Pro 11"/12.9" (USB-C)',
                '0x12B3': 'iPad Pro (M2/M4)',

                // ---- Apple Watch ----
                '0x12AF': 'Apple Watch (USB Composite)',
                '0x12B5': 'Apple Watch Series 7/8/9',

                // ---- iPod / 旧设备 ----
                '0x12AA': 'iPod touch (5th~7th Gen)',
                '0x1293': 'iPod nano (7th Gen)',

                // ---- 其他配件 ----
                '0x12AC': 'Apple TV (恢复模式)',
                '0x12AD': 'Lightning Digital AV Adapter',
                '0x12AE': 'Lightning VGA Adapter',

                // ---- Mac 系列 ----
                '0x7308': 'MacBook Pro 14" (M1,2021)',
                '0x730B': 'MacBook Air 13" (2022,M2)',
                '0x7312': 'MacBook Pro 16" (M2,2023)',
                '0x731A': 'Mac Studio/Mac mini (M2,2023)',

                // ---- 键盘鼠标配件 ----
                '0x0233': 'Grape Bridge',
                '0x0265': 'Magic Trackpad 2',
                '0x0267': 'Magic Keyboard',
                '0x0276': 'Apple Internal Keyboard/Trackpad',
                '0x0269': 'Magic Mouse 2',
                '0x026C': 'Magic Keyboard with Numeric Keypad',
                '0x029A': 'Magic Keyboard with Touch ID',
                '0x029C': 'Magic Keyboard (2nd generation)',
                '0x029F': 'Magic Keyboard with Touch ID + Numeric Keypad',
                '0x0315': 'Siri Remote (3rd generation)',
                '0x0340': 'Apple Internal Keyboard/Trackpad (T2)',

                // ---- 音响设备 ----
                '0x7700': 'HomePod Mini'
            },

            '0x315C': { // Huawei Wireless Charger
                // ---- 无线充电器 ----
                '0x8100': '华为立式无线充(80W)'
            },

            '0x1A86': { // Feizhi B8X Cooler
                // ---- 散热器 ----
                '0x0224': '飞智B8X散热器'
            }
        };

        if (deviceMap[vid] && deviceMap[vid][pid]) {
            return deviceMap[vid][pid];
        }

        return null; // 没有匹配的机型就不显示设备
    }

    // 根据Battery VID识别设备厂商
    getBatteryDeviceInfo(batteryVid) {
        if (batteryVid === '0x05C6') {
            return '高通';
        }
        return null;
    }

    // 根据设备VID/PID获取对应的设备图片
    getDeviceImage(vid, pid, deviceName) {
        // 处理Apple设备和华为设备
        if (!deviceName) {
            return '';
        }

        // 华为设备处理
        if (vid === '0x315C') {
            if (pid === '0x8100') {
                // 华为立式无线充(80W)
                return '<img src="hwwxc80.png" alt="华为无线充" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
            }
            return '';
        }

        // 飞智B8X散热器处理
        if (vid === '0x1A86' && pid === '0x0224') {
            // 飞智B8X散热器序列帧动画
            return '<img src="feizhiB8X/01.png" alt="飞智B8X" class="feizhi-animation" style="width: 16px; height: 16px; margin-left: 4px; vertical-align: middle;">';
        }

        // Apple设备处理
        if (vid !== '0x05AC') {
            return '';
        }

        // 特殊机型优先匹配（PID优先级最高）
        if (pid === '0x7519') {
            // iPhone 17 系列特殊图片
            return '<img src="iphshouji17.png" alt="iPhone 17" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        }

        if (pid === '0x7700') {
            // HomePod Mini 音响设备
            return '<img src="appleyinxiang.png" alt="HomePod" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        }

        // 根据设备名称分类匹配
        if (deviceName.includes('iPhone')) {
            // iPhone 系列通用图片
            return '<img src="iphshouji.png" alt="iPhone" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        } else if (deviceName.includes('iPad')) {
            // iPad / 平板系列
            return '<img src="ipad0.png" alt="iPad" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        } else if (deviceName.includes('MacBook') || deviceName.includes('Mac ') || deviceName.includes('iMac') || deviceName.includes('Mac Studio') || deviceName.includes('Mac mini')) {
            // Mac 系列电脑
            return '<img src="macbook.png" alt="Mac" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        } else if (deviceName.includes('HomePod') || deviceName.includes('音响')) {
            // 音响设备
            return '<img src="appleyinxiang.png" alt="音响" style="width: 14px; height: 14px; margin-left: 4px; vertical-align: middle;">';
        }

        return '';
    }

    // 根据制造商VID获取对应的logo
    getManufacturerLogo(vid) {
        if (vid === '0x05AC') {
            // Apple logo
            return '<img src="aaaple.svg" alt="Apple" style="width: 14px; height: 14px; margin-left: 8px; vertical-align: middle; filter: brightness(0) invert(1);">';
        } else if (vid === '0x315C') {
            // 华为无线充logo (如果有华为logo图片的话)
            // return '<img src="huawei.svg" alt="Huawei" style="width: 14px; height: 14px; margin-left: 8px; vertical-align: middle; filter: brightness(0) invert(1);">';
            return ''; // 暂时不显示华为logo，只显示设备图片
        }
        return '';
    }

    // 计算电池百分比
    calculateBatteryPercentage(lastFullCapacity, presentCapacity) {
        // 检查电量值是否有效（过滤异常值）
        if (!lastFullCapacity || lastFullCapacity === 0 || !presentCapacity) return -1;

        // 过滤异常的电量值（通常正常电池容量在1000mWh到200000mWh之间）
        if (lastFullCapacity < 1000 || lastFullCapacity > 200000) return -1;
        if (presentCapacity < 0 || presentCapacity > lastFullCapacity * 1.1) return -1;

        return Math.round((presentCapacity / lastFullCapacity) * 100);
    }

    // 计算充电剩余时间
    calculateChargingTime(lastFullCapacity, presentCapacity, power) {
        if (!power || power === 0 || !lastFullCapacity || !presentCapacity) return '未知';

        // 过滤异常的电量值
        if (lastFullCapacity < 1000 || lastFullCapacity > 200000) return '未知';
        if (presentCapacity < 0 || presentCapacity > lastFullCapacity * 1.1) return '未知';

        const remainingCapacity = lastFullCapacity - presentCapacity; // mWh
        if (remainingCapacity <= 0) return '已充满';

        // power单位是W，remainingCapacity单位是mWh
        // 转换power为mW: power * 1000
        const powerInMw = power * 1000; // mW

        // 估算剩余时间（小时）: mWh / mW = h
        const hoursLeft = remainingCapacity / powerInMw;

        if (hoursLeft < 1) {
            return `${Math.round(hoursLeft * 60)}分钟`;
        } else {
            const hours = Math.floor(hoursLeft);
            const minutes = Math.round((hoursLeft - hours) * 60);
            return `${hours}小时${minutes}分钟`;
        }
    }

    // 根据电池设计容量获取颜色分类
    getBatteryCapacityColorClass(designCapacity) {
        if (designCapacity <= 0) return 'capacity-unknown';
        if (designCapacity < 20000) return 'capacity-small';    // 小于20Wh - 小风扇、蓝牙耳机等
        if (designCapacity < 50000) return 'capacity-medium';   // 20-50Wh - 手机等
        if (designCapacity < 80000) return 'capacity-large';    // 50-80Wh - 平板等
        return 'capacity-xlarge';                               // 大于80Wh - 笔记本等
    }

    updateUI(data) {
        console.log('更新UI数据:', {
            totalPower: data.totalPower,
            averageVoltage: data.averageVoltage,
            totalCurrent: data.totalCurrent,
            wifiSignal: data.wifiSignal
        });

        // 更新顶部四个指标卡片
        this.updateMetricCard('power', data.totalPower, 'W', 1);

        // 更新功率负载条 (基于160W总功率)
        const maxPower = 160;
        const loadPercent = Math.min((data.totalPower / maxPower) * 100, 100).toFixed(1);
        const loadBar = document.getElementById('powerLoadBar');
        const loadText = document.getElementById('powerLoadText');
        
        if (loadBar) {
            loadBar.style.width = `${loadPercent}%`;
            if (parseFloat(loadPercent) > 80) loadBar.style.backgroundColor = '#ff4757';
            else if (parseFloat(loadPercent) > 50) loadBar.style.backgroundColor = '#ffa502';
            else loadBar.style.backgroundColor = '#2ed573';
        }
        
        if (loadText) {
            loadText.textContent = `负载 ${loadPercent}%`;
            loadText.style.color = parseFloat(loadPercent) > 80 ? '#ff4757' : (parseFloat(loadPercent) > 50 ? '#ffa502' : 'rgba(255,255,255,0.7)');
        }

        // 直接更新顶部指标元素
        const voltage2Element = document.getElementById('voltageValue2');
        const current2Element = document.getElementById('currentValue2');
        const wifiElement = document.getElementById('wifiValue');

        if (voltage2Element) voltage2Element.textContent = `${data.averageVoltage.toFixed(1)} V`;
        if (current2Element) current2Element.textContent = `${data.totalCurrent.toFixed(2)} A`;
        // 蓝牙信号：-100表示未连接，显示为--
        const wifiDisplay = data.wifiSignal <= -100 ? '--' : data.wifiSignal;
        if (wifiElement) wifiElement.textContent = `${wifiDisplay} dBm`;

        // 更新左侧状态区域的数据
        document.getElementById('voltageValue').textContent = `${data.averageVoltage.toFixed(1)} V`;
        document.getElementById('currentValue').textContent = `${data.totalCurrent.toFixed(2)} A`;
        document.getElementById('temperatureValue').textContent = `${wifiDisplay} dBm`;

        // 更新详细信息
        document.getElementById('chargingStatus').textContent = data.chargingStatus;
        document.getElementById('totalTime').textContent = `${data.activePorts} 个`;
        document.getElementById('totalEnergy').textContent = `${Math.round(data.freeHeap / 1024)} KB`;

        // 更新动态功率显示效果
        this.updatePowerLightEffect(data.totalPower);

        // 更新端口详细信息
        this.updatePortDetails(data.ports);

        // 充电完成弹窗功能已删除

        // 更新简洁模式下的实时数据显示
        this.updateCompactMetrics(data);
    }

    updateMetricCard(metric, value, unit, decimals) {
        const valueElement = document.getElementById(`${metric}Value`);
        const changeElement = document.getElementById(`${metric}Change`);

        if (!valueElement) {
            console.warn(`找不到元素: ${metric}Value`);
            return;
        }

        const formattedValue = value.toFixed(decimals);
        valueElement.textContent = `${formattedValue} ${unit}`;
        console.log(`更新${metric}: ${formattedValue} ${unit}`);

        // 计算变化
        if (changeElement) {
            const previousValue = this.previousValues[metric];
            if (previousValue !== undefined) {
                const change = value - previousValue;
                const changePercent = previousValue > 0 ? ((change / previousValue) * 100).toFixed(1) : '0.0';

                let changeClass = 'neutral';
                let changeText = '0%';

                if (Math.abs(change) > 0.01) {
                    if (change > 0) {
                        changeClass = 'positive';
                        changeText = `+${changePercent}%`;
                    } else {
                        changeClass = 'negative';
                        changeText = `${changePercent}%`;
                    }
                }

                changeElement.className = `metric-change ${changeClass}`;
                changeElement.textContent = changeText;
            }
        }

        this.previousValues[metric] = value;
    }

    // 更新功率数据并处理三种时间聚合
    updatePowerData(powerValue) {
        const now = new Date();
        const timestamp = now.getTime();

        // 更新实时数据
        const timeLabel = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        this.realtimeData.push(powerValue);
        this.realtimeLabels.push(timeLabel);

        if (this.realtimeData.length > this.maxDataPoints) {
            this.realtimeData.shift();
            this.realtimeLabels.shift();
        }

        // 更新10分钟聚合数据
        this.updateTenMinuteData(timestamp, powerValue);

        // 更新小时聚合数据
        this.updateHourlyData(timestamp, powerValue);

        // 更新图表显示
        this.updateChartDisplay();
    }

    // 更新10分钟聚合数据
    updateTenMinuteData(timestamp, power) {
        const tenMinuteKey = Math.floor(timestamp / (10 * 60 * 1000)) * (10 * 60 * 1000);

        if (!this.tenMinuteData.has(tenMinuteKey)) {
            this.tenMinuteData.set(tenMinuteKey, { total: 0, count: 0 });
        }

        const data = this.tenMinuteData.get(tenMinuteKey);
        data.total += power;
        data.count += 1;

        // 清理过老的数据
        const cutoffTime = timestamp - (this.maxTenMinutePoints * 10 * 60 * 1000);
        for (const [key] of this.tenMinuteData) {
            if (key < cutoffTime) {
                this.tenMinuteData.delete(key);
            }
        }
    }

    // 更新小时聚合数据
    updateHourlyData(timestamp, power) {
        const hourKey = Math.floor(timestamp / (60 * 60 * 1000)) * (60 * 60 * 1000);

        if (!this.hourlyData.has(hourKey)) {
            this.hourlyData.set(hourKey, { total: 0, count: 0 });
        }

        const data = this.hourlyData.get(hourKey);
        data.total += power;
        data.count += 1;

        // 清理过老的数据
        const cutoffTime = timestamp - (this.maxHourlyPoints * 60 * 60 * 1000);
        for (const [key] of this.hourlyData) {
            if (key < cutoffTime) {
                this.hourlyData.delete(key);
            }
        }
    }

    // 更新图表显示
    updateChartDisplay() {
        let labels = [];
        let data = [];

        if (this.chartMode === 'realtime') {
            labels = this.realtimeLabels;
            data = this.realtimeData;
        } else if (this.chartMode === 'tenminute') {
            // 生成10分钟平均数据
            const sortedKeys = Array.from(this.tenMinuteData.keys()).sort((a, b) => a - b);
            labels = sortedKeys.map(key => {
                const date = new Date(key);
                return date.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            });
            data = sortedKeys.map(key => {
                const item = this.tenMinuteData.get(key);
                return item.count > 0 ? item.total / item.count : 0;
            });
        } else if (this.chartMode === 'hourly') {
            // 生成小时平均数据
            const sortedKeys = Array.from(this.hourlyData.keys()).sort((a, b) => a - b);
            labels = sortedKeys.map(key => {
                const date = new Date(key);
                return date.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            });
            data = sortedKeys.map(key => {
                const item = this.hourlyData.get(key);
                return item.count > 0 ? item.total / item.count : 0;
            });
        }

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.update('none');
    }

    updatePortDetails(ports) {
        const portsContainer = document.getElementById('portsContainer');
        if (!portsContainer) return;

        // 更新3D可视化区域的线材显示
        this.update3DVisualization(ports);

        // 优化：增量DOM更新，避免重排
        let portsGrid = portsContainer.querySelector('.ports-grid');
        if (!portsGrid) {
            portsGrid = document.createElement('div');
            portsGrid.className = 'ports-grid';
            portsContainer.innerHTML = '';
            portsContainer.appendChild(portsGrid);
        }

        Object.entries(ports).forEach(([portId, port]) => {
            const isActive = port.current > 0;
            const power = port.power.toFixed(1); 
            const voltage = (port.voltage / 1000).toFixed(1); 
            const current = (port.current / 1000).toFixed(2); 

            const protocolName = this.getProtocolName(port.protocol);
            const capacityColorClass = this.getBatteryCapacityColorClass(port.batteryDesignCapacity);

            let statusClass, statusText;
            if (port.batteryPercentage > 0 && port.batteryPercentage >= 100) {
                statusClass = 'full';
                statusText = '已充满';
            } else if (isActive) {
                statusClass = 'active';
                statusText = port.batteryPercentage > 0 ? '充电中' : '供电中';
            } else {
                statusClass = 'idle';
                statusText = '空闲';
            }

            let cableStyleClass = '';
            if (typeof CableConfig !== 'undefined' && CableConfig.getChargingClass) {
                cableStyleClass = CableConfig.getChargingClass(port.cableName);
            } else {
                if (port.cableName && port.cableName.includes('SlimBolt')) cableStyleClass = 'slimbolt';
                else if (port.cableName === 'OK线') cableStyleClass = 'ok-cable';
                else if (port.cableName === '魅族卷卷线') cableStyleClass = 'meizu-cable';
                else if (port.cableName === '苹果官方线') cableStyleClass = 'apple-official';
                else if (port.cableName === '云朵线') cableStyleClass = 'cloud-cable';
                else if (port.cableName === '酷态科') cableStyleClass = 'kutaike-cable';
                else cableStyleClass = 'default';
            }

            const isChargingComplete = port.batteryPercentage >= 100 && port.deviceName && port.deviceName !== '未知设备';
            const chargingCompleteStars = isChargingComplete ? `
                <div class="charging-complete-star">
                    <div class="star-icon"></div>
                    <div class="star-small"></div>
                    <div class="star-small"></div>
                    <div class="star-small"></div>
                    <div class="star-particles">
                        ${'<div class="star-particle"></div>'.repeat(8)}
                    </div>
                </div>
            ` : '';

            const innerHTML = `
                ${chargingCompleteStars}
                <div class="port-header">
                    <div class="port-title">
                        <span class="port-id">端口 ${portId}${this.getManufacturerLogo(port.manufacturerVid)}${this.getDeviceImage(port.manufacturerVid, port.manufacturerPid, port.deviceName)}</span>
                        <div class="port-tags">
                            ${port.deviceName ? `<span class="port-tag device-tag ${port.deviceName === '飞智B8X散热器' ? 'feizhi-device' : ''}">${port.deviceName}</span>` : ''}
                            ${port.batteryDeviceName ? `<span class="port-tag device-tag qualcomm-device">${port.batteryDeviceName}</span>` : ''}
                            ${port.cableName !== '未知线材' ? `<span class="port-tag cable-tag ${cableStyleClass}">${port.cableName}</span>` : ''}
                            ${port.batteryPercentage > 0 && port.batteryPercentage <= 100 ? `<span class="port-tag battery-tag" data-progress="${port.batteryPercentage}">${port.batteryPercentage}%</span>` : ''}
                            ${port.batteryDesignCapacity > 0 && port.batteryDesignCapacity < 200000 ? `<span class="port-tag capacity-tag ${capacityColorClass}">${port.batteryDesignCapacity} mWh</span>` : ''}
                            ${port.chargingTimeLeft !== '未知' && port.batteryPercentage > 0 ? `<span class="port-tag time-tag">${port.chargingTimeLeft}</span>` : ''}
                        </div>
                    </div>
                    <span class="port-status ${statusClass}">${statusText}</span>
                </div>
                <div class="port-metrics">
                    <div class="port-metric"><span class="metric-label">功率</span><span class="metric-value">${power}W</span></div>
                    <div class="port-metric"><span class="metric-label">电压</span><span class="metric-value">${voltage}V</span></div>
                    <div class="port-metric"><span class="metric-label">电流</span><span class="metric-value">${current}A</span></div>
                    <div class="port-metric"><span class="metric-label">协议</span><span class="metric-value">${protocolName}</span></div>
                </div>
            `;

            const cardId = `port-card-${portId}`;
            let card = document.getElementById(cardId);
            const className = `port-item ${statusClass} ${isActive ? 'charging ' + cableStyleClass : ''} ${port.deviceName === '飞智B8X散热器' ? 'feizhi-device' : ''}`;

            if (!card) {
                card = document.createElement('div');
                card.id = cardId;
                card.className = className;
                card.style.position = 'relative';
                card.innerHTML = innerHTML;
                portsGrid.appendChild(card);
            } else {
                if (card.className !== className) card.className = className;
                if (card.innerHTML !== innerHTML) card.innerHTML = innerHTML;
            }
        });
    }

    // 更新3D可视化区域的线材显示 - 238x317区域，精确坐标
    update3DVisualization(ports) {
        console.log('=== 3D可视化更新开始 ===');
        console.log('当前布局模式:', this.isCompactMode ? '简洁布局' : '标准布局');
        console.log('是否布局切换中:', this.isLayoutSwitching);
        console.log('端口数据:', ports);

        // 只在布局切换时才清空所有线材显示并重新播放动画
        if (this.isLayoutSwitching) {
            console.log('🎬 布局切换中，清空所有线材准备重新播放动画');
            const cableClasses = ['cable-putong', 'cable-xili', 'cable-xili2', 'cable-yunduo', 'cable-okokok', 'cable-meizu',
                'cable-land-putong', 'cable-land-yunduo', 'cable-land-xili2', 'cable-land-okokok', 'cable-land-meizu', 'cable-usb'];
            cableClasses.forEach(className => {
                const elements = document.querySelectorAll(`.${className}`);
                elements.forEach((el, index) => {
                    el.style.display = 'none';
                    el.classList.remove('show'); // 移除动画类
                });
            });
        } else {
            console.log('📊 常规数据更新，不重复播放线材动画');
        }

        // 检查是否有端口在充电
        let hasChargingPort = false;
        const currentChargingPorts = new Set();

        // 遍历端口数据（ports是对象，键为端口索引）
        Object.entries(ports).forEach(([portIndex, port]) => {
            const originalPortNumber = parseInt(portIndex); // 原始端口号

            console.log(`\n检查端口${originalPortNumber}:`, port);

            // 端口0 - USB设备检测（只要有插线就显示）
            if (originalPortNumber === 0) {
                if (port && (port.current || port.voltage)) {
                    console.log(`✓ 端口0有USB设备连接`);
                    hasChargingPort = true;
                    currentChargingPorts.add(0);

                    // 显示端口0电力信息
                    this.showPowerInfo(0, port, port.cablePid || '0x0000');

                    // 显示充电指示图（带动画）
                    this.showChargingIndicator(0, 'left');

                    const usbElement = document.querySelector('.cable-usb.cable-port-usb');
                    if (usbElement) {
                        usbElement.style.display = 'block';

                        // 只在布局切换时或USB设备首次连接时播放动画
                        // 只在布局切换时播放动画，数据更新时保持现有状态
                        if (this.isLayoutSwitching) {
                            usbElement.classList.remove('show');
                            setTimeout(() => {
                                usbElement.classList.add('show');
                                console.log(`🎬 布局切换：端口0 USB设备动画已触发`);
                            }, 100);
                        } else {
                            // 数据更新时，只确保USB设备显示，不重复播放动画
                            if (!usbElement.classList.contains('show')) {
                                usbElement.classList.add('show');
                                console.log(`🎬 首次连接：端口0 USB设备动画已触发`);
                            } else {
                                console.log(`📊 数据更新：端口0 USB设备保持显示状态（无动画）`);
                            }
                        }

                        console.log(`✓ 显示端口0的USB设备图标，坐标:(12,90)`);
                    }
                } else {
                    // 端口0无设备连接，隐藏USB图标与指示
                    this.hidePowerInfo(0);
                    this.hideChargingIndicator(0, 'right');
                    const usbElement = document.querySelector('.cable-usb.cable-port-usb');
                    if (usbElement) {
                        usbElement.classList.remove('show');
                        usbElement.style.display = 'none';
                        console.log('📴 端口0无设备连接，USB图标已隐藏');
                    }
                }
                return; // 端口0处理完毕，跳过后续逻辑
            }

            // 端口4 - 特殊处理（在背景图下方）
            if (originalPortNumber === 4) {
                if (port && port.current && parseFloat(port.current) > 0) {
                    console.log(`✓ 端口4正在充电，电流:${port.current}mA，线材PID:${port.cablePid}`);
                    hasChargingPort = true;

                    // 显示端口4电力信息
                    this.showPowerInfo(4, port, port.cablePid || '0x0000');
                    currentChargingPorts.add(4);

                    // 显示充电指示图（带动画）
                    this.showChargingIndicator(4, 'up');

                    // 强制确保端口4充电指示图显示在背景图上方
                    const indicator4 = document.getElementById('charging-indicator-4');
                    if (indicator4) {
                        indicator4.style.display = 'block';
                        indicator4.style.visibility = 'visible';
                        indicator4.style.opacity = '1';
                        indicator4.style.zIndex = '3'; // 在背景图上方
                        console.log(`✓ 端口4充电指示图显示在背景图上方`);
                    }

                    // 根据线材PID显示对应的线材图片
                    const cablePid = port.cablePid || '0x0000';
                    let cableElement = null;

                    if (cablePid === '0x3001') {
                        cableElement = document.querySelector('.cable-land-yunduo.cable-port-3');
                        console.log(`✓ 端口4使用云朵线材`);
                    } else if (cablePid === '0x0002') {
                        cableElement = document.querySelector('.cable-land-meizu.cable-port-3');
                        console.log(`✓ 端口4使用魅族卷卷线材`);
                    } else if (cablePid === '0x3002') {
                        cableElement = document.querySelector('.cable-land-xili2.cable-port-3');
                        console.log(`✓ 端口4使用细雳线材2`);
                    } else if (cablePid === '0x3008') {
                        cableElement = document.querySelector('.cable-land-okokok.cable-port-3');
                        console.log(`✓ 端口4使用ok线材`);
                    } else if (cablePid === '0x7800' || cablePid === '0x4010') {
                        cableElement = document.querySelector('.cable-land-apple.cable-port-3');
                        console.log(`✓ 端口4使用苹果官方线材`);
                    } else if (cablePid === '0x4051') {
                        cableElement = document.querySelector('.cable-land-kutaike.cable-port-3');
                        console.log(`✓ 端口4使用酷态科线材`);
                    } else if (cablePid === '0x3004') {
                        cableElement = document.querySelector('.cable-land-huaxian.cable-port-3');
                        console.log(`✓ 端口4使用花线线材`);
                    } else {
                        cableElement = document.querySelector('.cable-land-putong.cable-port-3');
                        console.log(`✓ 端口4使用普通线材（默认）`);
                    }

                    // 先隐藏端口4的所有线材，防止重叠
                    const allCablesPort4 = document.querySelectorAll('.cable-land-putong.cable-port-3, .cable-land-yunduo.cable-port-3, .cable-land-xili2.cable-port-3, .cable-land-okokok.cable-port-3, .cable-land-meizu.cable-port-3, .cable-land-apple.cable-port-3, .cable-land-kutaike.cable-port-3, .cable-land-huaxian.cable-port-3');
                    allCablesPort4.forEach(el => {
                        if (el !== cableElement) {
                            el.style.display = 'none';
                            el.classList.remove('show');
                        }
                    });

                    if (cableElement) {
                        cableElement.style.display = 'block';
                        cableElement.style.visibility = 'visible';
                        cableElement.style.opacity = '1';
                        cableElement.style.zIndex = '-1';
                        cableElement.style.position = 'absolute';

                        // 在简洁布局下强制重置端口4线材样式
                        if (this.isCompactMode) {
                            cableElement.style.width = '42px';
                            cableElement.style.left = '184px';
                            console.log(`🔧 简洁布局：强制设置端口4线材样式 width:42px, left:184px`);
                        } else {
                            // 标准布局下清除内联样式，让CSS样式生效
                            cableElement.style.width = '';
                            cableElement.style.left = '';
                            console.log(`🔧 标准布局：清除端口4线材内联样式`);
                        }

                        // 强制设置重要属性，确保在横屏模式下不会跑到上层
                        cableElement.style.setProperty('z-index', '-1', 'important');

                        // 只在布局切换时或线材首次显示时播放动画
                        const isNewConnection = !cableElement.classList.contains('show');
                        if (this.isLayoutSwitching || isNewConnection) {
                            cableElement.classList.remove('show');
                            setTimeout(() => {
                                cableElement.classList.add('show');
                                console.log(`🎬 端口4线材动画已触发`);
                            }, this.isLayoutSwitching ? 450 : 100);
                        } else {
                            // 已经显示的线材，直接保持显示状态
                            cableElement.classList.add('show');
                            console.log(`📊 端口4线材保持显示状态（无动画）`);
                        }

                        console.log(`✓ 端口4线材显示在背景图下方，坐标:(92,235)，z-index: -1`);
                    }
                } else {
                    // 端口4不充电时，确保隐藏相关元素
                    const indicator4 = document.getElementById('charging-indicator-4');
                    // 隐藏端口4电力信息
                    this.hidePowerInfo(4);
                    if (indicator4) {
                        indicator4.style.display = 'none';
                    }

                    // 隐藏所有端口4线材
                    const cableElements = document.querySelectorAll('.cable-land-putong.cable-port-3, .cable-land-yunduo.cable-port-3, .cable-land-xili2.cable-port-3, .cable-land-okokok.cable-port-3, .cable-land-meizu.cable-port-3, .cable-land-apple.cable-port-3, .cable-land-kutaike.cable-port-3, .cable-land-huaxian.cable-port-3');
                    cableElements.forEach(el => {
                        el.classList.remove('show');
                        el.style.display = 'none';
                    });
                }
                return; // 端口4处理完毕
            }

            // 端口1,2,3 - 常规处理
            const displayPortIndex = originalPortNumber - 1; // 转换为显示索引（端口1→索引0，端口2→索引1）

            // 检查端口是否有设备连接且正在充电
            if (port && port.current && parseFloat(port.current) > 0) {
                console.log(`✓ 端口${originalPortNumber}正在充电，电流:${port.current}mA，线材PID:${port.cablePid}`);
                hasChargingPort = true;

                // 显示端口1-3电力信息
                this.showPowerInfo(originalPortNumber, port, port.cablePid || '0x0000');
                currentChargingPorts.add(originalPortNumber);

                // 显示充电指示图（带动画）
                this.showChargingIndicator(originalPortNumber, 'left');

                // 根据线材PID选择对应的线材类型
                let cableClass;
                if (port.cablePid === '0x3001') {
                    cableClass = 'cable-yunduo';  // 云朵线
                } else if (port.cablePid === '0x0002') {
                    cableClass = 'cable-meizu';  // 魅族卷卷线
                } else if (port.cablePid === '0x3002') {
                    cableClass = 'cable-xili';   // 细犀40Gbps线
                } else if (port.cablePid === '0x3003') {
                    cableClass = 'cable-xili2';  // 细雳线80Gps (保持原类名用于3D显示)
                } else if (port.cablePid === '0x3008') {
                    cableClass = 'cable-okokok';  // ok线
                } else if (port.cablePid === '0x7800' || port.cablePid === '0x4010') {
                    cableClass = 'cable-apple';  // 苹果官方线
                } else if (port.cablePid === '0x4051') {
                    cableClass = 'cable-kutaike';  // 酷态科线
                } else if (port.cablePid === '0x3004') {
                    cableClass = 'cable-huaxian';  // 花线
                } else {
                    cableClass = 'cable-putong'; // 普通线(默认)
                }

                console.log(`选择线材类型: ${cableClass}`);

                // 只显示前3个端口的线材（端口1,2,3对应显示索引0,1,2）
                if (displayPortIndex >= 0 && displayPortIndex < 3) {
                    // 先隐藏该端口所有线材，防止重叠
                    const allCablesForPort = document.querySelectorAll(`[class*="cable-port-${displayPortIndex}"]`);
                    allCablesForPort.forEach(el => {
                        el.style.display = 'none';
                        el.classList.remove('show');
                    });

                    // 使用组合选择器精确定位：线材类型 + 端口位置
                    const cableSelector = `.${cableClass}.cable-port-${displayPortIndex}`;
                    const cableElement = document.querySelector(cableSelector);
                    console.log(`查找选择器: ${cableSelector} (端口${originalPortNumber}→显示位置${displayPortIndex})`);

                    if (cableElement) {
                        cableElement.style.display = 'block';
                        cableElement.style.visibility = 'visible';
                        cableElement.style.opacity = '1';

                        // 在简洁布局下强制重置样式
                        if (this.isCompactMode) {
                            cableElement.style.width = '180px';
                            cableElement.style.position = 'absolute';
                            console.log(`🔧 简洁布局：强制设置线材样式 width:180px`);
                        } else {
                            // 标准布局下清除内联样式，让CSS样式生效
                            cableElement.style.width = '';
                            cableElement.style.position = '';
                            console.log(`🔧 标准布局：清除线材内联样式`);
                        }

                        // 只在布局切换时播放动画，数据更新时保持现有状态
                        if (this.isLayoutSwitching) {
                            cableElement.classList.remove('show');
                            const delay = displayPortIndex * 150;
                            setTimeout(() => {
                                cableElement.classList.add('show');
                                console.log(`🎬 布局切换：线材动画已触发: ${cableSelector}`);
                            }, delay);
                        } else {
                            // 数据更新时，只确保线材显示，不重复播放动画
                            if (!cableElement.classList.contains('show')) {
                                cableElement.classList.add('show');
                                console.log(`🎬 首次连接：线材动画已触发: ${cableSelector}`);
                            } else {
                                console.log(`📊 数据更新：线材保持显示状态（无动画）: ${cableSelector}`);
                            }
                        }

                        const expectedY = 135 + displayPortIndex * 33;
                        console.log(`✓ 显示端口${originalPortNumber}的${cableClass}线材，坐标:(12,${expectedY})`);
                    } else {
                        console.log(`❌ 未找到选择器${cableSelector}对应的元素`);
                    }
                } else {
                    console.log(`端口${originalPortNumber}超出显示范围(只显示端口1-3)`);
                }
            } else {
                console.log(`端口${originalPortNumber}未充电或无设备`);
                // 隐藏端口1-3电力信息
                this.hidePowerInfo(originalPortNumber);

                // 隐藏该端口所有线材元素（端口1-3对应显示索引0-2）
                const idx = displayPortIndex;
                ['cable-putong', 'cable-xili', 'cable-xili2', 'cable-yunduo', 'cable-okokok', 'cable-meizu', 'cable-apple', 'cable-kutaike', 'cable-huaxian'].forEach(cls => {
                    const el = document.querySelector(`.${cls}.cable-port-${idx}`);
                    if (el) {
                        el.classList.remove('show');
                        el.style.display = 'none';
                        console.log(`📴 隐藏线材: .${cls}.cable-port-${idx}`);
                    }
                });

                // 同步隐藏充电指示
                this.hideChargingIndicator(originalPortNumber, 'right');
            }
        });

        // 处理不再充电的端口（滑出动画）
        if (this.previousChargingPorts) {
            this.previousChargingPorts.forEach(portNum => {
                if (!currentChargingPorts.has(portNum)) {
                    // 端口不再充电，执行滑出动画
                    const direction = portNum === 4 ? 'down' : 'right';
                    this.hidePowerInfo(portNum);
                    this.hideChargingIndicator(portNum, direction);
                }
            });
        }

        // 保存当前充电端口状态
        this.previousChargingPorts = currentChargingPorts;

        // 根据充电状态调整背景图透明度
        const reallyvison = document.getElementById('reallyvison');
        if (reallyvison) {
            if (hasChargingPort) {
                reallyvison.classList.add('charging');
                console.log('✓ 设置背景图透明度为100%（有端口充电）');
            } else {
                reallyvison.classList.remove('charging');
                console.log('✓ 设置背景图透明度为60%（无端口充电）');
            }
        }

        console.log('=== 3D可视化更新结束 ===\n');
    }

    // 清除所有线材动画状态，准备重新播放
    clearAllCableAnimations() {
        const allCables = document.querySelectorAll('.cable-putong, .cable-xili, .cable-xili2, .cable-yunduo, .cable-okokok, .cable-meizu, .cable-apple, .cable-kutaike, .cable-huaxian, .cable-land-putong, .cable-land-yunduo, .cable-land-xili2, .cable-land-okokok, .cable-land-meizu, .cable-land-apple, .cable-land-kutaike, .cable-land-huaxian, .cable-usb');
        allCables.forEach(cable => {
            cable.classList.remove('show');
            // 重置transform和opacity，确保动画从初始状态开始
            if (cable.classList.contains('cable-land-putong') ||
                cable.classList.contains('cable-land-yunduo') ||
                cable.classList.contains('cable-land-xili2') ||
                cable.classList.contains('cable-land-okokok')) {
                // 端口4线材从下往上
                cable.style.transform = 'translateY(100%)';
            } else {
                // 其他线材从左往右
                cable.style.transform = 'translateX(-100%)';
            }
            cable.style.opacity = '0';
        });
        console.log('🎬 清除所有线材动画状态，准备重新播放');
    }

    // 显示充电指示图（带滑入动画）
    showChargingIndicator(portNum, direction) {
        const indicator = document.getElementById(`charging-indicator-${portNum}`);
        if (!indicator) return;

        // 移除所有动画类
        indicator.classList.remove('slide-in-left', 'slide-out-right', 'slide-in-up', 'slide-out-down');

        // 显示元素
        indicator.style.display = 'block';

        // 添加滑入动画
        const animationClass = direction === 'up' ? 'slide-in-up' : 'slide-in-left';
        indicator.classList.add(animationClass);

        // 特别处理端口4的z-index问题
        if (portNum === 4) {
            indicator.style.zIndex = '3'; // 端口4充电指示图在背景图上方
            indicator.style.visibility = 'visible';
            indicator.style.opacity = '1';
            indicator.style.position = 'absolute';
            console.log(`✓ 端口4充电指示图设置为z-index: 3（背景图上方）`);
        }

        console.log(`✓ 端口${portNum}充电指示图滑入动画（${direction}）`);
    }

    // 隐藏充电指示图（带滑出动画）
    hideChargingIndicator(portNum, direction) {
        const indicator = document.getElementById(`charging-indicator-${portNum}`);
        if (!indicator) return;

        // 移除滑入动画类
        indicator.classList.remove('slide-in-left', 'slide-in-up');

        // 添加滑出动画
        const animationClass = direction === 'down' ? 'slide-out-down' : 'slide-out-right';
        indicator.classList.add(animationClass);

        // 动画结束后隐藏元素
        setTimeout(() => {
            indicator.style.display = 'none';
            indicator.classList.remove(animationClass);
        }, 500); // 与CSS动画时间一致

        console.log(`✓ 端口${portNum}充电指示图滑出动画（${direction}）`);
    }

    getProtocolName(protocol) {
        const protocols = {
            0: 'NONE',
            1: 'QC2',
            2: 'QC3',
            3: 'QC3P',
            4: 'SFCP',
            5: 'AFC',
            6: 'FCP',
            7: 'SCP',
            8: 'VOOC1P0',
            9: 'VOOC4P0',
            10: 'SVOOC2P0',
            11: 'TFCP',
            12: 'UFCS',
            13: 'PE1',
            14: 'PE2',
            15: 'PD_FIX5V',
            16: 'PD_FIXHV',
            17: 'PD_SPR_AVS',
            18: 'PD_PPS',
            19: 'PD_EPR_HV',
            20: 'PD_AVS',
            255: 'NOT_CHARGING'
        };
        return protocols[protocol] || `未知协议(${protocol})`;
    }

    showConnectionError() {
        const portsContainer = document.getElementById('portsContainer');
        if (portsContainer) {
            portsContainer.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ff6b6b;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <h3>无法连接到充电桩</h3>
                    <p style="margin-top: 8px; color: #aaa;">请检查网络连接和充电桩状态</p>
                    <button onclick="location.reload()" style="margin-top: 16px; padding: 8px 16px; background: #ff6b6b; color: white; border: none; border-radius: 4px; cursor: pointer;">重新加载</button>
                </div>
            `;
        }
    }

    // 请求屏幕唤醒锁
    async requestWakeLock() {
        if (!('wakeLock' in navigator)) {
            console.log('此浏览器不支持 Screen Wake Lock API');
            this.updateWakeLockStatus('不支持');
            return;
        }

        try {
            this.wakeLock = await navigator.wakeLock.request('screen');
            console.log('屏幕唤醒锁已激活');
            this.updateWakeLockStatus('激活');

            this.wakeLock.addEventListener('release', () => {
                console.log('屏幕唤醒锁已释放');
                this.updateWakeLockStatus('已释放');
            });

        } catch (err) {
            console.error('无法获取屏幕唤醒锁:', err);
            this.updateWakeLockStatus('失败');
        }
    }

    // 释放屏幕唤醒锁
    async releaseWakeLock() {
        if (this.wakeLock) {
            await this.wakeLock.release();
            this.wakeLock = null;
            this.updateWakeLockStatus('已释放');
        }
    }

    // 切换屏幕唤醒锁
    async toggleWakeLock() {
        this.isWakeLockEnabled = !this.isWakeLockEnabled;

        if (this.isWakeLockEnabled) {
            await this.requestWakeLock();
        } else {
            await this.releaseWakeLock();
        }

        this.updateWakeLockToggleButton();
    }

    // 设置唤醒锁处理程序
    setupWakeLockHandlers() {
        // 页面可见性变化时重新获取唤醒锁
        document.addEventListener('visibilitychange', async () => {
            if (!document.hidden && this.isWakeLockEnabled && !this.wakeLock) {
                await this.requestWakeLock();
            }
        });

        // 页面获得焦点时重新获取唤醒锁
        window.addEventListener('focus', async () => {
            if (this.isWakeLockEnabled && !this.wakeLock) {
                await this.requestWakeLock();
            }
        });
    }

    // 更新唤醒锁状态显示
    updateWakeLockStatus(status) {
        const statusElement = document.getElementById('wakeLockStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `wake-lock-status ${status === '激活' ? 'active' : 'inactive'}`;
        }
    }

    // 更新唤醒锁切换按钮
    updateWakeLockToggleButton() {
        const toggleBtn = document.getElementById('wakeLockToggle');
        if (toggleBtn) {
            const iconSpan = toggleBtn.querySelector('.wake-icon');
            const textSpan = toggleBtn.querySelector('.wake-text');
            if (iconSpan) iconSpan.textContent = this.isWakeLockEnabled ? '☀️' : '🌙';
            if (textSpan) textSpan.textContent = this.isWakeLockEnabled ? '常亮中' : '常亮';
            toggleBtn.className = `wake-lock-btn ${this.isWakeLockEnabled ? 'active' : ''}`;
        }
    }

    // 切换3D视图旋转
    toggle3DRotation() {
        this.isRotated = !this.isRotated;
        const reallyvison = document.getElementById('reallyvison');

        if (reallyvison) {
            if (this.isRotated) {
                reallyvison.classList.add('rotated');
                console.log('🔄 3D充电站已旋转90度（横向）');
            } else {
                reallyvison.classList.remove('rotated');
                console.log('🔄 3D充电站已恢复默认方向（竖向）');
            }
        }

        // 更新按钮状态
        this.updateRotationToggleButton();
    }

    // 更新旋转切换按钮状态
    updateRotationToggleButton() {
        const toggleBtn = document.getElementById('rotationToggle');
        if (toggleBtn) {
            const textSpan = toggleBtn.querySelector('.toggle-text');

            if (this.isRotated) {
                toggleBtn.classList.add('active');
                toggleBtn.title = '切换为竖屏模式';
                if (textSpan) textSpan.textContent = '横屏';
            } else {
                toggleBtn.classList.remove('active');
                toggleBtn.title = '切换为横屏模式';
                if (textSpan) textSpan.textContent = '竖屏';
            }
        }
    }

    // 切换布局模式
    toggleLayout() {
        this.isCompactMode = !this.isCompactMode;

        // 设置布局切换标志
        this.isLayoutSwitching = true;

        // FLIP：记录切换前几何信息（First）
        // 外部方框为 3D充电站描边区域 #reallyvison，锚点为右上角
        const flipTarget = document.getElementById('reallyvison');
        const flipFirstRect = flipTarget ? flipTarget.getBoundingClientRect() : null;

        // 使用统一线材管理系统重置样式，防止位置错乱和拉升
        if (typeof window.cableManager !== 'undefined') {
            // 使用新的线材管理系统更新样式
            window.cableManager.updateCableStyles(this.isCompactMode);
        } else {
            // 兼容旧版本的重置方式
            const allCables = document.querySelectorAll('.cable, .cable-c1, .cable-c2, .cable-c3, .cable-c4, .cable-usb, .cable-putong, .cable-xili, .cable-xili2, .cable-yunduo, .cable-okokok, .cable-meizu, .cable-apple, .cable-kutaike, .cable-huaxian, .cable-land-putong, .cable-land-yunduo, .cable-land-xili2, .cable-land-okokok, .cable-land-meizu, .cable-land-apple, .cable-land-kutaike, .cable-land-huaxian');
            allCables.forEach(cable => {
                // 重置transform相关属性
                cable.style.transform = '';
                cable.style.transformOrigin = '';
                cable.style.scale = '';
                cable.style.translate = '';
                cable.style.rotate = '';

                // 重置简洁布局下可能设置的内联样式
                cable.style.width = '';
                cable.style.left = '';
                cable.style.top = '';
                cable.style.right = '';
                cable.style.bottom = '';
                cable.style.position = '';

                // 移除可能影响布局的类
                cable.classList.remove('compact-style');
            });
        }
        console.log('🔧 已重置所有线材样式，当前模式:', this.isCompactMode ? '简洁' : '标准');

        // 清除所有线材的show类，准备重新播放动画
        this.clearAllCableAnimations();

        const container = document.querySelector('.container');
        const compactMetrics = document.getElementById('compactMetrics');
        const rightPanel = document.querySelector('.right-panel');

        if (container && rightPanel) {
            // 清除之前的动画类
            rightPanel.classList.remove('switching-to-compact', 'switching-to-standard');

            if (this.isCompactMode) {
                // 添加切换到简洁模式的动画类
                rightPanel.classList.add('switching-to-compact');
                container.classList.add('compact-mode');
                console.log('🎨 切换到简洁模式');

                // 显示简洁模式下的实时数据
                if (compactMetrics) {
                    compactMetrics.style.display = 'flex';
                }

                // 动画完成后清除动画类
                setTimeout(() => {
                    rightPanel.classList.remove('switching-to-compact');
                }, 700);

            } else {
                // 添加切换到标准模式的动画类
                rightPanel.classList.add('switching-to-standard');
                container.classList.remove('compact-mode');
                console.log('🎨 切换到标准模式');

                // 隐藏简洁模式下的实时数据
                if (compactMetrics) {
                    compactMetrics.style.display = 'none';
                }

                // 动画完成后清除动画类
                setTimeout(() => {
                    rightPanel.classList.remove('switching-to-standard');
                }, 700);
            }
        }

        // 执行 FLIP 动画（Last → Invert → Play）
        if (flipTarget && flipFirstRect) {
            const flipLastRect = flipTarget.getBoundingClientRect();
            // 基于右上角计算位移，保证右上角对齐（以右上角为固定端点）
            const dx = (flipFirstRect.right - flipLastRect.right);
            const dy = (flipFirstRect.top - flipLastRect.top);
            const sx = (flipFirstRect.width / flipLastRect.width) || 1;
            const sy = (flipFirstRect.height / flipLastRect.height) || 1;

            // 设置变换原点为右上角，确保缩放和位移以右上角为基准
            flipTarget.style.transformOrigin = 'top right';
            flipTarget.style.willChange = 'transform';
            flipTarget.style.transition = 'none';
            flipTarget.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;

            // 下一帧开始过渡
            requestAnimationFrame(() => {
                // 使用更顺滑的缓动曲线，确保运动轨迹完整可见
                flipTarget.style.transition = 'transform 700ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                flipTarget.style.transform = 'translate(0px, 0px) scale(1, 1)';
            });

            const cleanup = () => {
                flipTarget.style.transition = '';
                flipTarget.style.transform = '';
                flipTarget.style.transformOrigin = '';
                flipTarget.style.willChange = '';
                flipTarget.removeEventListener('transitionend', cleanup);
            };
            flipTarget.addEventListener('transitionend', cleanup);
        }

        // 更新按钮状态
        this.updateLayoutToggleButton();

        // 延迟触发数据更新以显示线材动画，确保布局切换动画完成后再播放线材动画
        setTimeout(() => {
            this.fetchData();
        }, 800);

        // 2秒后重置布局切换标志，避免动画闪烁
        setTimeout(() => {
            this.isLayoutSwitching = false;
        }, 2000);
    }

    // 更新布局切换按钮状态
    updateLayoutToggleButton() {
        // 更新头部的新按钮
        const headerToggleBtn = document.getElementById('headerLayoutToggle');
        const standardLabel = document.getElementById('standardLabel');
        const compactLabel = document.getElementById('compactLabel');

        if (headerToggleBtn && standardLabel && compactLabel) {
            if (this.isCompactMode) {
                headerToggleBtn.classList.add('compact-active');
                headerToggleBtn.title = '切换为标准模式';
                standardLabel.classList.remove('active');
                compactLabel.classList.add('active');
            } else {
                headerToggleBtn.classList.remove('compact-active');
                headerToggleBtn.title = '切换为简洁模式';
                standardLabel.classList.add('active');
                compactLabel.classList.remove('active');
            }
        }

        // 保持原有按钮的更新（虽然已隐藏）
        const toggleBtn = document.getElementById('layoutToggle');
        if (toggleBtn) {
            const textSpan = toggleBtn.querySelector('.toggle-text');

            if (this.isCompactMode) {
                toggleBtn.classList.add('active');
                toggleBtn.title = '切换为标准模式';
                if (textSpan) textSpan.textContent = '标准';
            } else {
                toggleBtn.classList.remove('active');
                toggleBtn.title = '切换为简洁模式';
                if (textSpan) textSpan.textContent = '简洁';
            }
        }
    }

    // 更新简洁模式下的实时数据显示
    updateCompactMetrics(data) {
        if (!this.isCompactMode) return;

        const compactPower = document.getElementById('compactPower');
        const compactVoltage = document.getElementById('compactVoltage');
        const compactCurrent = document.getElementById('compactCurrent');
        const compactWifi = document.getElementById('compactWifi');

        if (compactPower) compactPower.textContent = `${data.totalPower.toFixed(1)} W`;
        if (compactVoltage) compactVoltage.textContent = `${data.averageVoltage.toFixed(1)} V`;
        if (compactCurrent) compactCurrent.textContent = `${data.totalCurrent.toFixed(2)} A`;
        // 蓝牙信号：-100表示未连接，显示为--
        const wifiDisplayCompact = data.wifiSignal <= -100 ? '--' : data.wifiSignal;
        if (compactWifi) compactWifi.textContent = `${wifiDisplayCompact} dBm`;

        console.log('📊 简洁模式实时数据已更新');
    }

    // 显示端口电力信息（仅在简约布局模式下显示）
    showPowerInfo(portNum, port, cablePid) {
        // 只在简约布局模式下显示电力信息
        if (!this.isCompactMode) {
            return;
        }

        const powerInfoElement = document.getElementById(`power-info-${portNum}`);
        if (!powerInfoElement || !port) return;

        // 格式化电力信息
        const current = parseFloat(port.current) / 1000; // 转换为A
        const voltage = parseFloat(port.voltage) / 1000; // 转换为V
        const power = parseFloat(port.power); // W

        // 新格式：功率·电压·电流，功率粗体，电压电流细体
        const powerHTML = `<span style="font-weight: bold;">${power.toFixed(2)}W</span>·<span style="font-weight: 300;">${voltage.toFixed(2)}V</span>·<span style="font-weight: 300;">${current.toFixed(2)}A</span>`;
        powerInfoElement.innerHTML = powerHTML;

        // 根据线材类型设置颜色
        powerInfoElement.className = 'power-info';
        if (cablePid === '0x3001') {
            powerInfoElement.classList.add('cable-yunduo');
        } else if (cablePid === '0x0002') {
            powerInfoElement.classList.add('cable-meizu');  // 魅族卷卷线
        } else if (cablePid === '0x3002') {
            powerInfoElement.classList.add('cable-xili');  // 细犀40Gbps线 - 红色
        } else if (cablePid === '0x3003') {
            powerInfoElement.classList.add('cable-80gps'); // 细霹线80Gps - 橙色 #FFA526
        } else if (cablePid === '0x3008') {
            powerInfoElement.classList.add('cable-okokok');
        } else if (cablePid === '0x7800' || cablePid === '0x4010') {
            powerInfoElement.classList.add('cable-apple');
        } else if (cablePid === '0x4051') {
            powerInfoElement.classList.add('cable-kutaike');
        } else if (cablePid === '0x3004') {
            powerInfoElement.classList.add('cable-huaxian');
        } else {
            powerInfoElement.classList.add('cable-putong');
        }

        // 显示电力信息
        powerInfoElement.style.display = 'block';
        powerInfoElement.classList.add('show');

        console.log(`✓ 端口${portNum}电力信息显示（简约模式）: ${power.toFixed(2)}W·${voltage.toFixed(2)}V·${current.toFixed(2)}A`);
    }

    // 隐藏端口电力信息
    hidePowerInfo(portNum) {
        const powerInfoElement = document.getElementById(`power-info-${portNum}`);
        if (powerInfoElement) {
            powerInfoElement.classList.remove('show');
            setTimeout(() => {
                powerInfoElement.style.display = 'none';
            }, 300);
            console.log(`✓ 端口${portNum}电力信息已隐藏`);
        }
    }
}

// 页面加载完成后初始化监控器
document.addEventListener('DOMContentLoaded', () => {
    new ChargingStationMonitor();
});

// 粒子系统控制类
class ParticleSystem {
    constructor(container, isLowPerformance = false) {
        this.container = container;
        this.isLowPerformance = isLowPerformance;
        this.particles = [];
        this.isActive = false;
        this.animationId = null;

        this.init();
    }

    init() {
        // 创建粒子元素
        // 低性能模式下显著减少粒子数量
        const count = this.isLowPerformance ? 6 : 20;
        this.createParticles(count);

        // 获取光环和波纹元素
        this.breathingGlow = this.container.querySelector('.breathing-glow');
        this.energyRipples = this.container.querySelectorAll('.energy-ripple');
    }

    createParticles(count) {
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';

            // 随机位置
            const x = Math.random() * 100;
            const y = Math.random() * 100;

            particle.style.left = `${x}%`;
            particle.style.top = `${y}%`;

            // 随机动画延迟
            particle.style.animationDelay = `${Math.random() * 3}s`;

            this.container.appendChild(particle);
            this.particles.push(particle);
        }
    }

    activate() {
        if (this.isActive) return;

        this.isActive = true;
        this.container.classList.add('active');

        // 激活呼吸光环
        if (this.breathingGlow) {
            this.breathingGlow.classList.add('active');
        }

        // 激活能量波纹
        this.energyRipples.forEach(ripple => {
            ripple.classList.add('active');
        });

        console.log('✨ 粒子呼吸光效已激活');
    }

    deactivate() {
        if (!this.isActive) return;

        this.isActive = false;
        this.container.classList.remove('active');

        // 停用呼吸光环
        if (this.breathingGlow) {
            this.breathingGlow.classList.remove('active');
        }

        // 停用能量波纹
        this.energyRipples.forEach(ripple => {
            ripple.classList.remove('active');
        });

        console.log('✨ 粒子呼吸光效已停用');
    }

    updateIntensity(chargingPortsCount) {
        if (!this.isActive) return;

        // 根据充电端口数量调整粒子密度和光效强度
        const intensity = Math.min(chargingPortsCount / 5, 1); // 最多5个端口

        // 调整粒子透明度
        this.particles.forEach(particle => {
            particle.style.opacity = 0.3 + (intensity * 0.5);
        });

        // 调整光环强度
        if (this.breathingGlow) {
            this.breathingGlow.style.opacity = intensity;
        }

        console.log(`✨ 粒子系统强度调整为: ${(intensity * 100).toFixed(0)}%`);
    }
}

// 扩展充电站监控器类，添加粒子系统支持
const originalInit = ChargingStationMonitor.prototype.init;
ChargingStationMonitor.prototype.init = function () {
    originalInit.call(this);

    // 初始化粒子系统
    const particleContainer = document.getElementById('particleSystem');
    if (particleContainer) {
        // 传入设备性能标志
        this.particleSystem = new ParticleSystem(particleContainer, this.isMobile);
        console.log('✨ 粒子系统已初始化');
    }
};

// 扩展充电站监控器类，添加动态功率显示方法
ChargingStationMonitor.prototype.updatePowerLightEffect = function (totalPower) {
    console.log(`🔆 更新功率灯光效果: ${totalPower}W`);

    // 移除所有现有的功率灯光效果
    const existingLights = document.querySelectorAll('.power-light-effect');
    existingLights.forEach(light => light.remove());

    // 根据总功率范围选择对应的灯光图片
    let lightImage = null;
    if (totalPower >= 0 && totalPower <= 40) {
        lightImage = 'light01.png';
    } else if (totalPower > 40 && totalPower <= 80) {
        lightImage = 'light02.png';
    } else if (totalPower > 80 && totalPower <= 120) {
        lightImage = 'light03.png';
    } else if (totalPower > 120 && totalPower <= 160) {
        lightImage = 'light04.png';
    }

    // 如果功率超过160W或为0，则不显示灯光效果
    if (!lightImage || totalPower === 0) {
        console.log(`🔆 功率${totalPower}W，不显示灯光效果`);
        return;
    }

    // 创建灯光效果元素
    const reallyvison = document.querySelector('.reallyvison');
    if (reallyvison) {
        const lightElement = document.createElement('div');
        lightElement.className = 'power-light-effect';
        lightElement.style.cssText = `
            position: absolute;
            width: 112px;
            height: 200px;
            background-image: url('${lightImage}');
            background-size: 112px 200px;
            background-repeat: no-repeat;
            background-position: 0 0;
            left: 63px;
            top: 47px;
            z-index: 1;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.5s ease;
        `;

        reallyvison.appendChild(lightElement);

        // 淡入效果
        setTimeout(() => {
            lightElement.style.opacity = '0.8';
        }, 50);

        console.log(`🔆 显示功率灯光效果: ${lightImage}，功率: ${totalPower}W`);
    }
};

// 扩展3D可视化更新方法，添加粒子系统控制
const originalUpdate3D = ChargingStationMonitor.prototype.update3DVisualization;
ChargingStationMonitor.prototype.update3DVisualization = function (ports) {
    // 调用原始方法
    originalUpdate3D.call(this, ports);

    // 控制粒子系统
    if (this.particleSystem) {
        // 计算充电端口数量
        let chargingPortsCount = 0;
        Object.entries(ports).forEach(([portIndex, port]) => {
            const portNum = parseInt(portIndex);

            // 端口0 - USB设备检测
            if (portNum === 0 && port && (port.current || port.voltage)) {
                chargingPortsCount++;
            }
            // 其他端口 - 充电检测
            else if (portNum > 0 && port && port.current && parseFloat(port.current) > 0) {
                chargingPortsCount++;
            }
        });

        // 根据充电状态控制粒子系统
        if (chargingPortsCount > 0) {
            this.particleSystem.activate();
            this.particleSystem.updateIntensity(chargingPortsCount);
        } else {
            this.particleSystem.deactivate();
        }
    }
};

// 飞智B8X散热器序列帧动画
class FeizhiAnimation {
    constructor() {
        this.frames = ['feizhiB8X/01.png', 'feizhiB8X/02.png', 'feizhiB8X/03.png', 'feizhiB8X/04.png'];
        this.currentFrame = 0;
        this.animationSpeed = 50; // 加快到0.5秒切换一帧
        this.animationInterval = null;
        this.init();
    }

    init() {
        this.startAnimation();
    }

    startAnimation() {
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
        }

        this.animationInterval = setInterval(() => {
            this.updateFrames();
        }, this.animationSpeed);
    }

    updateFrames() {
        const feizhiImages = document.querySelectorAll('.feizhi-animation');
        if (feizhiImages.length === 0) return;

        this.currentFrame = (this.currentFrame + 1) % this.frames.length;

        feizhiImages.forEach(img => {
            img.src = this.frames[this.currentFrame];
        });
    }

    stopAnimation() {
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
            this.animationInterval = null;
        }
    }
}

// 初始化飞智动画
const feizhiAnimation = new FeizhiAnimation();

// --- 新增：控制面板逻辑扩展 ---

ChargingStationMonitor.prototype.setupControlPanel = function() {
    console.log('🔧 初始化设备控制面板...');
    
    // 获取DOM元素
    const modal = document.getElementById('controlModal');
    const openBtn = document.getElementById('settingsBtn');
    const closeBtn = document.getElementById('closeModal');
    const tokenInput = document.getElementById('tokenInput');
    const portSwitchesContainer = document.getElementById('portSwitches');
    const logContainer = document.getElementById('actionLog');
    
    // 绑定开关模态框事件
    if (openBtn) openBtn.onclick = () => {
        modal.classList.add('active');
        this.updateControlPanelStatus(); // 打开时刷新状态
    };
    
    if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
    
    // 点击遮罩关闭
    window.onclick = (event) => {
        if (event.target === modal) {
            modal.classList.remove('active');
        }
    };
    
    // 生成5个端口开关 (端口0-4)
    if (portSwitchesContainer) {
        portSwitchesContainer.innerHTML = ''; // 清空
        for (let i = 0; i < 5; i++) {
            const switchHtml = `
                <div class="modern-port-card">
                    <div class="port-header">
                        <div class="port-icon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                            </svg>
                        </div>
                        <span class="port-id">PORT ${i}</span>
                    </div>
                    <label class="ios-switch">
                        <input type="checkbox" id="port-switch-${i}" onchange="window.monitor.controlPort(${i}, this.checked)">
                        <span class="ios-slider"></span>
                    </label>
                </div>
            `;
            portSwitchesContainer.insertAdjacentHTML('beforeend', switchHtml);
        }
    }
    
    // 绑定按钮事件
    const scanBtn = document.getElementById('scanBtn');
    if (scanBtn) scanBtn.onclick = () => this.scanDevices();
    
    const disconnectBtn = document.getElementById('disconnectBtn');
    if (disconnectBtn) disconnectBtn.onclick = () => this.disconnectDevice();

    document.getElementById('bruteforceBtn').onclick = () => this.bruteforceToken();
    document.getElementById('reconnectBtn').onclick = () => this.reconnectDevice();
    document.getElementById('rebootBtn').onclick = () => this.rebootDevice();
    document.getElementById('saveTokenBtn').onclick = () => this.manualSetToken();
    document.getElementById('refreshInfoBtn').onclick = () => this.updateControlPanelStatus();
    
    // 暴露实例给全局以便开关调用
    window.monitor = this;
    
    this.logAction('控制面板已就绪');
};

// 更新控制面板状态
ChargingStationMonitor.prototype.updateControlPanelStatus = async function() {
    this.logAction('正在刷新设备状态...');
    try {
        // 获取Token和连接状态
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        
        const tokenInput = document.getElementById('tokenInput');
        if (tokenInput && statusData.token !== null) {
            tokenInput.value = `0x${statusData.token.toString(16).toUpperCase().padStart(2, '0')}`;
        } else {
            tokenInput.value = '未获取';
        }
        
        // 获取端口状态以更新开关
        const portRes = await fetch(this.dataUrl); // /api/port-status
        const portData = await portRes.json();
        
        if (portData && portData.ports) {
            portData.ports.forEach((port, index) => {
                const switchEl = document.getElementById(`port-switch-${index}`);
                if (switchEl) {
                    // 如果有电流或电压，或者协议不为0，通常意味着端口是启用的
                    // 注意：这里我们假设 protocol > 0 或 voltage > 0 表示开启
                    // 更准确的方法是后端返回 enable 状态，但在 port-status 中主要是实时数据
                    // 这里我们根据 voltage > 0.5V 来判断
                    const isOn = (port.voltage > 500) || (port.state !== 0); 
                    switchEl.checked = isOn;
                }
            });
            this.logAction('状态刷新完成');
        }
    } catch (error) {
        console.error('刷新状态失败:', error);
        this.logAction('刷新状态失败: ' + error.message);
    }
};

// 端口控制 (优化版：添加防抖和状态锁)
ChargingStationMonitor.prototype.controlPort = async function(portId, enable) {
    // 状态锁：防止重复点击
    if (this._portLocks && this._portLocks[portId]) {
        this.logAction(`端口 ${portId} 操作过于频繁，请稍候`);
        // 恢复开关UI状态
        const switchEl = document.getElementById(`port-switch-${portId}`);
        if (switchEl) switchEl.checked = !enable;
        return;
    }

    // 初始化锁对象
    if (!this._portLocks) this._portLocks = {};
    this._portLocks[portId] = true;

    const action = enable ? '打开' : '关闭';
    this.logAction(`正在${action}端口 ${portId}...`);
    
    // UI反馈：禁用开关
    const switchEl = document.getElementById(`port-switch-${portId}`);
    if (switchEl) switchEl.disabled = true;

    try {
        const url = `/api/port/${portId}/${enable ? 'on' : 'off'}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时

        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        const result = await response.json();
        
        if (result.success) {
            this.logAction(`✅ 端口 ${portId} ${action}成功`);
            // 延迟刷新数据
            setTimeout(() => this.fetchData(), 1000);
        } else {
            throw new Error(result.error || '未知错误');
        }
    } catch (error) {
        this.logAction(`❌ 操作失败: ${error.message}`);
        // 回滚开关状态
        if (switchEl) switchEl.checked = !enable;
    } finally {
        // 解锁
        this._portLocks[portId] = false;
        if (switchEl) switchEl.disabled = false;
    }
};

// 暴力破解 Token - 添加连接检查
ChargingStationMonitor.prototype.bruteforceToken = async function() {
    // 检查设备连接状态
    if (!this.isConnected) {
        this.logAction('❌ 请先连接设备再暴力破解Token');
        alert('请先连接BLE设备');
        return;
    }

    // 双重检查：通过API确认
    try {
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        if (!statusData.connected) {
            this.isConnected = false;
            this.logAction('❌ 请先连接设备再暴力破解Token');
            alert('请先连接BLE设备');
            return;
        }
        this.isConnected = true;
    } catch (e) {
        this.logAction('❌ 无法检查连接状态');
        return;
    }

    this.logAction('🔍 开始暴力破解 Token (预计耗时 10-30秒)...');
    try {
        const response = await fetch('/api/token/bruteforce');
        const result = await response.json();

        if (result.success) {
            this.logAction(`✅ Token 获取成功: 0x${result.token.toString(16).toUpperCase().padStart(2, '0')} (${result.token})`);
            document.getElementById('tokenInput').value = `0x${result.token.toString(16).toUpperCase().padStart(2, '0')}`;
        } else {
            this.logAction(`Token 获取失败: ${result.error}`);
        }
    } catch (error) {
        this.logAction(`请求出错: ${error.message}`);
    }
};

// 重连设备
ChargingStationMonitor.prototype.reconnectDevice = async function() {
    this.logAction('正在断开并重连设备...');
    try {
        await fetch('/api/disconnect');
        this.logAction('已断开，正在重新扫描连接...');
        
        setTimeout(async () => {
            const response = await fetch('/api/connect');
            const result = await response.json();
            if (result.success) {
                this.logAction(`连接成功: ${result.device}`);
                this.retryCount = 0;
                this.fetchData();
            } else {
                this.logAction(`连接失败: ${result.error}`);
            }
        }, 2000);
    } catch (error) {
        this.logAction(`操作出错: ${error.message}`);
    }
};

// 重启设备 - 添加连接检查
ChargingStationMonitor.prototype.rebootDevice = async function() {
    // 检查设备连接状态
    try {
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        if (!statusData.connected) {
            this.logAction('❌ 请先连接设备');
            alert('请先连接BLE设备');
            return;
        }
    } catch (e) {
        this.logAction('❌ 无法检查连接状态');
        return;
    }

    if (!confirm('⚠️ 警告：确定要重启设备吗？\n重启期间将断开连接。')) return;

    this.logAction('🚀 发送重启指令...');
    try {
        const response = await fetch('/api/reboot');
        const result = await response.json();
        if (result.success) {
            this.logAction('✅ 指令已发送，设备正在重启...');
            
            // 倒计时反馈
            let count = 15;
            const logEntry = document.querySelector('.log-entry'); // 获取最新一条日志
            
            const interval = setInterval(() => {
                count--;
                if (logEntry) logEntry.textContent = `[${new Date().toLocaleTimeString()}] ⏳ 设备重启中 (${count}s)...`;
                
                if (count <= 0) {
                    clearInterval(interval);
                    this.logAction('🔄 正在尝试重新连接...');
                    this.reconnectDevice();
                }
            }, 1000);
            
        } else {
            this.logAction(`❌ 重启失败: ${result.error}`);
        }
    } catch (error) {
        this.logAction(`请求出错: ${error.message}`);
    }
};

// 手动设置 Token - 支持十进制和十六进制
ChargingStationMonitor.prototype.manualSetToken = async function() {
    const input = document.getElementById('tokenInput').value.trim();

    // 检查设备连接状态
    try {
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        if (!statusData.connected) {
            this.logAction('❌ 请先连接设备再设置Token');
            alert('请先连接BLE设备');
            return;
        }
    } catch (e) {
        this.logAction('❌ 无法检查连接状态');
        return;
    }

    let token;
    // 智能解析：支持十进制和十六进制
    if (input.toLowerCase().startsWith('0x')) {
        // 十六进制格式 (0x开头)
        token = parseInt(input, 16);
    } else if (/^[0-9a-fA-F]{1,2}$/.test(input)) {
        // 纯十六进制数字（不带0x）
        token = parseInt(input, 16);
    } else {
        // 十进制格式
        token = parseInt(input, 10);
    }

    // 验证范围
    if (isNaN(token) || token < 0 || token > 255) {
        this.logAction('❌ Token必须在0-255之间（十进制）或0x00-0xFF（十六进制）');
        alert('Token范围：0-255（十进制）或 0x00-0xFF（十六进制）');
        return;
    }

    this.logAction(`⚙️ 设置 Token 为 ${token} (0x${token.toString(16).toUpperCase().padStart(2, '0')})...`);
    try {
        const response = await fetch(`/api/token/set?token=${token}`, { method: 'POST' });
        const result = await response.json();
        if (result.success) {
            this.logAction(`✅ Token 设置成功: ${token} (0x${token.toString(16).toUpperCase().padStart(2, '0')})`);
            // 更新输入框显示为标准格式
            document.getElementById('tokenInput').value = `0x${token.toString(16).toUpperCase().padStart(2, '0')}`;
        } else {
            this.logAction('❌ 设置失败');
        }
    } catch (error) {
        this.logAction(`请求出错: ${error.message}`);
    }
};

// 日志输出助手
ChargingStationMonitor.prototype.logAction = function(message) {
    const logContainer = document.getElementById('actionLog');

    // 同时输出到信息反馈区域 (Info Feedback)
    const infoDisplay = document.getElementById('infoDisplay');
    if (infoDisplay) {
        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.style.marginBottom = '4px';
        entry.style.fontSize = '12px';
        entry.style.color = '#888';
        entry.style.borderBottom = '1px dashed rgba(255,255,255,0.05)';
        entry.textContent = `[${time}] ${message}`;
        infoDisplay.prepend(entry);

        // 保持最多20条
        if (infoDisplay.children.length > 20) {
            infoDisplay.lastElementChild.remove();
        }
    }

    if (!logContainer) return;

    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${time}] ${message}`;
    
    logContainer.prepend(entry);
    
    // 保持最多50条日志
    if (logContainer.children.length > 50) {
        logContainer.lastElementChild.remove();
    }
};

// --- 新增：扫描与连接逻辑 ---

ChargingStationMonitor.prototype.scanDevices = async function() {
    const listEl = document.getElementById('deviceList');
    const scanBtn = document.getElementById('scanBtn');
    if (!listEl || !scanBtn) return;
    
    listEl.innerHTML = '<li class="device-item scanning" style="padding:10px;color:#aaa;">正在扫描设备 (5s)...</li>';
    scanBtn.disabled = true;
    scanBtn.textContent = '扫描中...';
    
    try {
        const res = await fetch('/api/scan', { method: 'POST' });
        const data = await res.json();
        
        listEl.innerHTML = '';
        if (data.devices && data.devices.length > 0) {
            data.devices.forEach(dev => {
                const li = document.createElement('li');
                li.className = 'device-item';
                li.style.cursor = 'pointer';
                li.style.padding = '8px';
                li.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
                li.style.display = 'flex';
                li.style.justifyContent = 'space-between';
                li.style.alignItems = 'center';
                li.innerHTML = `
                    <div class="device-info">
                        <div class="device-name" style="font-weight:bold; color:#fff; font-size:14px;">${dev.name}</div>
                        <div class="device-addr" style="font-size:11px; color:#888;">${dev.address}</div>
                    </div>
                    <span class="device-rssi" style="color:#0f0; font-size:12px;">📶 ${dev.rssi}</span>
                `;
                
                // 添加悬停效果
                li.onmouseover = () => li.style.background = 'rgba(255,255,255,0.1)';
                li.onmouseout = () => li.style.background = 'transparent';
                
                li.onclick = () => this.connectToDevice(dev.address);
                listEl.appendChild(li);
            });
        } else {
            listEl.innerHTML = '<li class="device-item empty" style="padding:10px;text-align:center;color:#aaa;">未发现设备，请靠近重试</li>';
        }
    } catch (e) {
        listEl.innerHTML = `<li class="device-item error" style="color:red;padding:10px;">扫描失败: ${e.message}</li>`;
        this.logAction(`扫描失败: ${e.message}`);
    } finally {
        scanBtn.disabled = false;
        scanBtn.textContent = '扫描 (5s)';
    }
};

ChargingStationMonitor.prototype.connectToDevice = async function(address) {
    this.logAction(`正在连接到 ${address}...`);
    const statusText = document.getElementById('statusText');
    if (statusText) statusText.textContent = '连接中...';
    
    try {
        const res = await fetch('/api/connect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({address})
        });
        const data = await res.json();
        
        if (data.success) {
            this.logAction('连接成功！');
            // Ensure port switches are refreshed immediately upon connection
            this.updateControlPanelStatus();

            if (statusText) statusText.textContent = 'BLE在线';
            const statusDot = document.getElementById('statusDot');
            if (statusDot) statusDot.className = 'status-dot';
            
            // 显示断开按钮
            const disconnectBtn = document.getElementById('disconnectBtn');
            if (disconnectBtn) disconnectBtn.style.display = 'block';
            
            // 自动关闭模态框
            setTimeout(() => {
                document.getElementById('controlModal').classList.remove('active');
            }, 1000);
            
            // 立即刷新数据
            this.fetchData();
        } else {
            throw new Error(data.error || '连接失败');
        }
    } catch (e) {
        this.logAction(`连接失败: ${e.message}`);
        alert(`连接失败: ${e.message}`);
        if (statusText) statusText.textContent = '连接失败';
    }
};

ChargingStationMonitor.prototype.disconnectDevice = async function() {
    if (!confirm('确定要断开连接吗？')) return;
    
    try {
        await fetch('/api/disconnect', { method: 'POST' });
        this.logAction('设备已断开');
        document.getElementById('statusText').textContent = '已断开';
        document.getElementById('statusDot').className = 'status-dot disconnected';
        document.getElementById('disconnectBtn').style.display = 'none';
        
        // 清空列表
        const listEl = document.getElementById('deviceList');
        if (listEl) listEl.innerHTML = '<li class="device-item empty" style="padding:10px;text-align:center;">已断开，请重新扫描</li>';
        
    } catch (e) {
        this.logAction(`断开失败: ${e.message}`);
    }
};

// ============================================================================
// Advanced Control Panel Extensions (ionbridge-ble-controller integration)
// ============================================================================

/**
 * Send generic action via WebSocket
 * @param {string} action - Action name
 * @param {object} params - Action parameters
 */
ChargingStationMonitor.prototype.sendAction = function(action, params = {}) {
    // 允许离线执行的命令白名单
    const offlineActions = ['connect', 'scan', 'get_debug_log', 'disconnect'];

    if (!this.isConnected && !offlineActions.includes(action)) {
        this.logAction(`❌ 设备未连接，无法执行: ${action}`);
        // 尝试检查一次状态以更新
        this.checkConnectionStatus();
        return;
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        this.logAction('WebSocket未连接，尝试重连...');
        this.setupWebSocket();
        return;
    }

    const payload = { type: 'action', action: action, params: params };
    console.log(`📤 Sending action: ${action}`, params);
    this.ws.send(JSON.stringify(payload));
    this.logAction(`发送指令: ${action}`);
    
    const infoDisplay = document.getElementById('infoDisplay');
    if (infoDisplay) {
        const timestamp = new Date().toLocaleTimeString();
        const msg = `[${timestamp}] 🚀 执行: ${action}\n参数: ${JSON.stringify(params)}\n-------------------`;

        // Append instead of replace
        const entry = document.createElement('div');
        entry.textContent = msg;
        entry.style.marginBottom = '8px';
        entry.style.color = '#aaa';
        entry.style.borderBottom = '1px dashed rgba(255,255,255,0.1)';

        infoDisplay.prepend(entry);

        // Remove old entries if too many
        if (infoDisplay.children.length > 20) {
            infoDisplay.removeChild(infoDisplay.lastChild);
        }
    }
};

/**
 * Handle action responses from server
 * @param {string} action - Action name
 * @param {object} message - Response message
 */
ChargingStationMonitor.prototype.handleActionResponse = function(action, message) {
    const infoDisplay = document.getElementById('infoDisplay');
    if (!infoDisplay) return;

    const timestamp = new Date().toLocaleTimeString();

    const entry = document.createElement('div');
    entry.style.marginBottom = '8px';
    entry.style.borderBottom = '1px dashed rgba(255,255,255,0.1)';

    if (message.success) {
        entry.style.color = '#00f5ff';
        entry.textContent = `[${timestamp}] ✅ 成功: ${action}\n结果: ${JSON.stringify(message.data || message.result, null, 2)}`;
        this.logAction(`${action} 成功`);

        // Update UI state based on action
        if (action === 'get_charging_strategy' || action === 'set_charging_strategy') {
            const strategy = message.data?.strategy ?? (message.data?.result?.strategy);
            if (strategy !== undefined) {
                const select = document.getElementById('chargingStrategy');
                if (select) select.value = strategy;
            }
        } else if (action === 'get_temperature_mode' || action === 'set_temperature_mode') {
             // Supports both {mode: 1} and {data: {mode: 1}} formats
            const mode = message.data?.mode ?? message.data?.result?.mode;
            if (mode !== undefined) {
                const toggle = document.getElementById('tempModeToggle');
                const info = document.getElementById('tempModeInfo');
                if (toggle) toggle.checked = (mode === 1);
                if (info) info.textContent = (mode === 1) ? "当前: 温控优先 (Temperature Priority)" : "当前: 功率优先 (Power Priority)";
            }
        } else if (action === 'get_display_settings' || action === 'set_display_brightness') {
             const brightness = message.data?.brightness;
             if (brightness !== undefined) {
                 const slider = document.getElementById('brightnessSlider');
                 const val = document.getElementById('brightnessValue');
                 if (slider) slider.value = brightness;
                 if (val) val.textContent = brightness + '%';
             }
        }
    } else {
        entry.style.color = '#ff6b6b';
        entry.textContent = `[${timestamp}] ❌ 失败: ${action}\n原因: ${message.message || message.error || '未知错误'}`;
        this.logAction(`${action} 失败`);

        // Revert toggle if failed
        if (action === 'set_temperature_mode') {
            const toggle = document.getElementById('tempModeToggle');
            if (toggle) toggle.checked = !toggle.checked;
        }
    }

    // --- 新增：处理高级功能的弹窗展示 ---
    if (message.success) {
        if (['get_port_pd_status', 'get_power_historical_stats', 'get_port_temperature', 'ble_echo_test', 'get_debug_log'].includes(action)) {
            this.showFeatureModal(action, message.data || message.result);
        }
    }

    infoDisplay.prepend(entry);

    // Remove old entries
    if (infoDisplay.children.length > 20) {
        infoDisplay.removeChild(infoDisplay.lastChild);
    }
};

/**
 * 显示高级功能结果弹窗
 * @param {string} action - 动作名称
 * @param {object} data - 返回的数据
 */
ChargingStationMonitor.prototype.showFeatureModal = function(action, data) {
    const modal = document.getElementById('featureModal');
    const titleEl = document.getElementById('featureTitle');
    const iconEl = document.getElementById('featureIcon');
    const contentEl = document.getElementById('featureContent');
    const closeBtn = document.getElementById('closeFeatureModal');

    if (!modal || !contentEl) return;

    // 绑定关闭事件
    const closeModal = () => {
        modal.classList.remove('active');
        // 如果有图表实例，销毁它
        if (this.featureChart) {
            this.featureChart.destroy();
            this.featureChart = null;
        }
    };
    closeBtn.onclick = closeModal;
    modal.onclick = (e) => { if(e.target === modal) closeModal(); };

    // 根据动作类型渲染内容
    let title = '功能详情';
    let icon = '📊';
    let html = '';

    try {
        switch (action) {
            case 'get_port_pd_status':
                title = '端口 PD 协议状态';
                icon = '🔌';
                if (typeof data === 'object') {
                    html = '<table class="feature-table">';
                    for (const [key, value] of Object.entries(data)) {
                        // 格式化布尔值和复杂对象
                        let displayValue = value;
                        if (typeof value === 'boolean') displayValue = value ? '✅ 是' : '❌ 否';
                        else if (typeof value === 'object') displayValue = JSON.stringify(value);

                        html += `<tr><td>${key}</td><td>${displayValue}</td></tr>`;
                    }
                    html += '</table>';
                } else {
                    html = `<div class="json-view">${JSON.stringify(data, null, 2)}</div>`;
                }
                break;

            case 'get_port_temperature':
                title = '端口温度监控';
                icon = '🌡️';
                // 假设数据中有 temperature 字段，或者 data 本身就是数值
                let temp = data.temperature || data.temp || data;
                if (typeof temp === 'object') temp = JSON.stringify(temp);
                // 简单的颜色判断
                let color = '#2ed573'; // 绿色
                const tempVal = parseFloat(temp);
                if (!isNaN(tempVal)) {
                    if (tempVal > 60) color = '#ff4757'; // 红色
                    else if (tempVal > 40) color = '#ffa502'; // 橙色
                }

                html = `
                    <div class="temp-display">
                        <div class="temp-label">当前温度</div>
                        <div class="temp-value" style="color: ${color}">${temp}°C</div>
                        <div class="temp-label">状态良好</div>
                    </div>
                `;
                break;

            case 'get_power_historical_stats':
                title = '历史功率曲线';
                icon = '📈';
                html = '<div class="feature-chart-container"><canvas id="featureChartCanvas"></canvas></div>';
                // 需要在DOM更新后绘制图表，使用 setTimeout
                setTimeout(() => {
                    const ctx = document.getElementById('featureChartCanvas');
                    if (ctx) {
                        // 构造模拟数据或使用真实数据
                        const labels = Array.isArray(data.labels) ? data.labels : Array.from({length: 10}, (_, i) => `${i}m`);
                        const values = Array.isArray(data.values) ? data.values : (Array.isArray(data) ? data : [0,0,0,0,0]);

                        this.featureChart = new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: labels,
                                datasets: [{
                                    label: '历史功率 (W)',
                                    data: values,
                                    borderColor: '#00f5ff',
                                    backgroundColor: 'rgba(0, 245, 255, 0.2)',
                                    tension: 0.4,
                                    fill: true
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: { legend: { display: false } },
                                scales: {
                                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' } },
                                    x: { grid: { color: 'rgba(255,255,255,0.1)' } }
                                }
                            }
                        });
                    }
                }, 100);
                break;

            case 'get_debug_log':
                title = '系统调试日志';
                icon = '🐞';
                const logContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
                html = `<div class="debug-log-view">${logContent || '暂无日志数据'}</div>`;
                break;

            case 'ble_echo_test':
                title = 'BLE 回显测试';
                icon = '📡';
                html = `
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 48px; margin-bottom: 20px;">✅</div>
                        <div style="font-size: 18px; color: #fff;">测试成功</div>
                        <div style="margin-top: 10px; color: #888;">设备响应数据: ${JSON.stringify(data)}</div>
                    </div>
                `;
                break;

            default:
                html = `<div class="json-view">${JSON.stringify(data, null, 2)}</div>`;
        }
    } catch (e) {
        html = `<div style="color:red">渲染错误: ${e.message}</div><div class="json-view">${JSON.stringify(data)}</div>`;
    }

    // 更新DOM
    titleEl.textContent = title;
    iconEl.textContent = icon;
    contentEl.innerHTML = html;

    // 显示弹窗
    modal.classList.add('active');
};

/**
 * WiFi setup helper
 */
ChargingStationMonitor.prototype.setWifi = function() {
    const ssid = document.getElementById('wifiSSID')?.value;
    const password = document.getElementById('wifiPass')?.value;
    if (!ssid) { 
        alert('请输入 SSID'); 
        return; 
    }
    this.sendAction('set_wifi', { ssid, password });
};

/**
 * Port config helper - set protocol configuration
 */
ChargingStationMonitor.prototype.setPortConfig = function() {
    const portId = parseInt(document.getElementById('configPortId')?.value || '0');
    const protocols = {};
    document.querySelectorAll('#protocolCheckboxes input[type="checkbox"]').forEach(cb => {
        protocols[cb.dataset.protocol] = cb.checked;
    });
    this.sendAction('set_port_config', { port_mask: (1 << portId), protocols });
};

/**
 * Port priority helper
 */
ChargingStationMonitor.prototype.setPortPriority = function() {
    const portId = parseInt(document.getElementById('configPortId')?.value || '0');
    const priority = parseInt(document.getElementById('portPriority')?.value || '0');
    if (isNaN(priority)) return;
    this.sendAction('set_port_priority', { port_id: portId, priority });
};

/**
 * Render protocol checkboxes dynamically
 * @param {object} data - Protocol data from server
 */
ChargingStationMonitor.prototype.renderProtocolCheckboxes = function(data) {
    const container = document.getElementById('protocolCheckboxes');
    if (!container) return;
    
    const PROTOCOL_NAMES = [
        'TFCP', 'PE', 'QC2.0', 'QC3.0', 'QC3+', 'AFC', 'FCP', 'HV_SCP',
        'LV_SCP', 'SFCP', 'Apple 5V', 'Samsung 5V', 'BC1.2', 'UFCS', 'RPi 5V5A', 'VOOC',
        'PD', 'PPS', 'QC4.0', 'QC4+', 'Dash/Warp', 'SFC', 'MTK PE', 'MTK PE+'
    ];
    
    const enabledProtocols = data?.protocols || [];
    container.innerHTML = PROTOCOL_NAMES.map(p => `
        <label class="protocol-checkbox">
            <input type="checkbox" data-protocol="${p}" ${enabledProtocols.includes(p) ? 'checked' : ''}>
            ${p}
        </label>
    `).join('');
};

/**
 * Toggle collapsible section
 * @param {HTMLElement} header - The clicked header element
 */
ChargingStationMonitor.prototype.toggleSection = function(header) {
    const group = header.closest('.control-group');
    if (group) {
        group.classList.toggle('active');
    }
};

/**
 * Set display brightness
 * @param {number} value - Brightness value 0-100
 */
ChargingStationMonitor.prototype.setBrightness = function(value) {
    const displayEl = document.getElementById('brightnessValue');
    if (displayEl) displayEl.textContent = value + '%';
    this.sendAction('set_brightness', { brightness: parseInt(value) });
};

/**
 * Set charging strategy
 * @param {string} strategy - Strategy name
 */
ChargingStationMonitor.prototype.setStrategy = function(strategy) {
    this.sendAction('set_strategy', { strategy });
};