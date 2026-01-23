class ChargingStationMonitor {
    constructor() {
        this.dataUrl = '/api/port-status';
        this.gatewaysUrl = '/api/gateways';
        this.cmdUrl = '/api/gateway';
        
        this.updateInterval = 3000;
        this.chart = null;
        this.chartMode = 'realtime';

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
        this.maxRetries = 5;

        this.wakeLock = null;
        this.isWakeLockEnabled = true;

        this.isRotated = false;

        this.isCompactMode = false;
        this.isLayoutSwitching = false;

        this.gateways = {};
        this.currentGatewayId = null;
        this.isConnected = false;
        
        this.apiKey = localStorage.getItem('cp02_api_key') || '';

        this.isMobile = this.detectMobileDevice();
        if (this.isMobile) {
            this.updateInterval = 5000;
        }

        this.init();
    }

    detectMobileDevice() {
        const userAgent = navigator.userAgent;
        const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        const isSmallScreen = window.innerWidth <= 768;
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        return isMobileUA || (isSmallScreen && isTouchDevice);
    }

    getHeaders(contentType = 'application/json') {
        const headers = {};
        if (contentType) headers['Content-Type'] = contentType;
        if (this.apiKey) headers['X-API-Key'] = this.apiKey;
        return headers;
    }

    async init() {
        this.setupChart();
        this.setupEventListeners();
        this.setupControlPanel();
        
        this.showEmptyPortsState('正在连接服务器...');
        
        await this.fetchGateways();
        
        this.setupWebSocket();
        this.startMonitoring();
        this.requestWakeLock();
        this.setupWakeLockHandlers();
        
        const apiKeyInput = document.getElementById('apiKeyInput');
        if (apiKeyInput) apiKeyInput.value = this.apiKey;
    }

    showEmptyPortsState(message = '等待设备连接') {
        const container = document.getElementById('portsContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 40px; color: #666;">
                <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">📡</div>
                <h3 style="color: #fff; margin-bottom: 8px;">${message}</h3>
                <p style="font-size: 12px;">请确保 ESP32 网关已连接到 MQTT</p>
            </div>
        `;
    }

    async fetchGateways() {
        try {
            const response = await fetch(this.gatewaysUrl, {
                headers: this.getHeaders()
            });
            const data = await response.json();
            
            this.gateways = {};
            data.gateways.forEach(gw => {
                this.gateways[gw.gateway_id] = gw;
            });
            
            this.updateGatewaySelector();
            
            if (!this.currentGatewayId && data.gateways.length > 0) {
                this.selectGateway(data.gateways[0].gateway_id);
            }
        } catch (error) {
            console.error('Failed to fetch gateways:', error);
            this.logAction('获取网关列表失败');
            this.showEmptyPortsState('无法连接服务器');
        }
    }

    updateGatewaySelector() {
        const select = document.getElementById('gatewaySelect');
        const gatewayList = Object.values(this.gateways);
        
        // 更新集群大盘数据
        this.updateClusterStats(gatewayList);

        if (gatewayList.length === 0) {
            select.innerHTML = '<option value="">未发现网关</option>';
            return;
        }
        
        select.innerHTML = gatewayList.map(gw => 
            `<option value="${gw.gateway_id}" ${gw.gateway_id === this.currentGatewayId ? 'selected' : ''}>
                ${gw.device_name || gw.gateway_id} ${gw.online ? '🟢' : '🔴'}
            </option>`
        ).join('');
        
        this.updateControlPanelGateways();
    }

    updateClusterStats(gatewayList) {
        let totalPower = 0;
        let activeDevices = 0;
        let onlineCount = 0;
        const matrixContainer = document.getElementById('gatewayMatrix');
        let matrixHtml = '';

        gatewayList.forEach(gw => {
            // 统计在线数
            if (gw.online) onlineCount++;

            // 统计功率 (后端数据结构可能不同，做容错处理)
            const power = parseFloat(gw.total_power || 0);
            totalPower += power;

            // 统计设备数
            const devices = parseInt(gw.active_ports || 0);
            activeDevices += devices;

            // 生成矩阵项
            const isSelected = gw.gateway_id === this.currentGatewayId;
            matrixHtml += `
                <div class="matrix-item ${gw.online ? 'online' : 'offline'} ${isSelected ? 'selected' : ''}" 
                     onclick="monitor.selectGateway('${gw.gateway_id}')">
                    <span class="matrix-name">${gw.device_name || gw.gateway_id}</span>
                    <span class="matrix-val">${power.toFixed(1)}W</span>
                </div>
            `;
        });

        // 更新UI
        const onlineBadge = document.getElementById('onlineGatewayCount');
        if (onlineBadge) onlineBadge.textContent = `${onlineCount}/${gatewayList.length} 在线`;

        const globalPower = document.getElementById('globalTotalPower');
        if (globalPower) globalPower.textContent = totalPower.toFixed(1);

        const globalDevices = document.getElementById('globalActiveDevices');
        if (globalDevices) globalDevices.textContent = activeDevices;

        if (matrixContainer) matrixContainer.innerHTML = matrixHtml;
    }
    
    updateControlPanelGateways() {
        const list = document.getElementById('gatewayList');
        if (!list) return;
        
        const gatewayList = Object.values(this.gateways);
        list.innerHTML = gatewayList.length === 0 
            ? '<div class="no-gateways">未连接网关</div>'
            : gatewayList.map(gw => `
                <div class="gateway-item ${gw.gateway_id === this.currentGatewayId ? 'selected' : ''}"
                     onclick="monitor.selectGateway('${gw.gateway_id}')">
                    <span class="gw-status ${gw.online ? 'online' : 'offline'}"></span>
                    <span class="gw-name">${gw.device_name || gw.gateway_id}</span>
                    <span class="gw-power">${gw.total_power?.toFixed(1) || 0} W</span>
                </div>
            `).join('');
    }

    selectGateway(gatewayId) {
        this.currentGatewayId = gatewayId;
        const select = document.getElementById('gatewaySelect');
        if (select) select.value = gatewayId;
        
        this.logAction(`切换至网关: ${gatewayId}`);
        this.updateControlPanelGateways();
        this.fetchData();
    }

    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            console.log(`📡 连接 WebSocket: ${wsUrl}`);
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket 连接已建立');
                this.updateStatus('connected');
                if (this.currentGatewayId) {
                    this.ws.send(JSON.stringify({ 
                        type: 'subscribe', 
                        gateway_id: this.currentGatewayId 
                    }));
                }
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'init') {
                        this.gateways = {};
                        message.data.gateways.forEach(gw => {
                            this.gateways[gw.gateway_id] = gw;
                        });
                        this.updateGatewaySelector();
                        if (!this.currentGatewayId && message.data.gateways.length > 0) {
                            this.selectGateway(message.data.gateways[0].gateway_id);
                        } else if (message.data.gateways.length === 0) {
                            this.showEmptyPortsState('暂无网关连接');
                        }
                    } else if (message.type === 'gateway_data') {
                        if (message.gateway_id === this.currentGatewayId) {
                            const bleData = message.data;
                            this.gateways[message.gateway_id] = bleData;
                            
                            const parsedData = this.parseBleData(bleData);
                            this.updateUI(parsedData);
                            this.updatePowerData(parsedData.totalPower);
                            
                            this.updateStatus(bleData.online ? 'connected' : 'disconnected');
                            this.retryCount = 0;
                        } else {
                            this.gateways[message.gateway_id] = message.data;
                            this.updateGatewaySelector();
                        }
                    } else if (message.type === 'timeout') {
                        if (message.gateway_id === this.currentGatewayId) {
                            this.updateStatus('disconnected');
                            this.logAction('网关连接超时');
                        }
                        if (this.gateways[message.gateway_id]) {
                            this.gateways[message.gateway_id].online = false;
                            this.updateGatewaySelector();
                        }
                    }
                } catch (e) {
                    console.error('WS 消息解析错误:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('⚠️ WebSocket 连接断开');
                this.updateStatus('disconnected');
                setTimeout(() => this.setupWebSocket(), 5000);
            };
            
        } catch (error) {
            console.error('WebSocket 初始化失败:', error);
        }
    }

    updateStatus(status) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (status === 'connected') {
            statusDot.className = 'status-dot';
            statusText.textContent = '在线';
        } else {
            statusDot.className = 'status-dot disconnected';
            statusText.textContent = '离线';
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
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        display: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#aaa', font: { size: 12 } }
                    },
                    y: {
                        display: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                            color: '#aaa', 
                            font: { size: 12 },
                            callback: function(value) { return value + 'W'; }
                        }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    setupEventListeners() {
        document.getElementById('gatewaySelect').addEventListener('change', (e) => {
            this.selectGateway(e.target.value);
        });

        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.isManualRefresh = true;
            this.fetchData();
        });

        document.getElementById('realtimeToggle').addEventListener('click', () => this.switchChartMode('realtime'));
        document.getElementById('tenMinuteToggle').addEventListener('click', () => this.switchChartMode('tenminute'));
        document.getElementById('hourlyToggle').addEventListener('click', () => this.switchChartMode('hourly'));

        const wakeLockToggle = document.getElementById('wakeLockToggle');
        if (wakeLockToggle) {
            wakeLockToggle.addEventListener('click', () => this.toggleWakeLock());
        }

        const rotationToggle = document.getElementById('rotationToggle');
        if (rotationToggle) {
            rotationToggle.addEventListener('click', () => this.toggle3DRotation());
        }

        const headerLayoutToggle = document.getElementById('headerLayoutToggle');
        if (headerLayoutToggle) {
            headerLayoutToggle.addEventListener('click', () => this.toggleLayout());
        }
        
        const layoutToggle = document.getElementById('layoutToggle');
        if (layoutToggle) {
            layoutToggle.addEventListener('click', () => this.toggleLayout());
        }

        document.getElementById('settingsBtn').addEventListener('click', () => {
            document.getElementById('controlModal').classList.add('active');
            this.updateControlPanelGateways();
        });
        document.getElementById('closeModal').addEventListener('click', () => {
            document.getElementById('controlModal').classList.remove('active');
        });
        
        document.getElementById('apiKeyInput').addEventListener('input', (e) => {
            this.apiKey = e.target.value;
            localStorage.setItem('cp02_api_key', this.apiKey);
        });
        
        document.getElementById('uploadFirmwareBtn').addEventListener('click', () => this.uploadFirmware());
        
        const scanBtn = document.getElementById('scanBtn');
        if (scanBtn) scanBtn.addEventListener('click', () => this.startRemoteScan());
        
        const disconnectBtn = document.getElementById('disconnectBtn');
        if (disconnectBtn) disconnectBtn.addEventListener('click', () => this.disconnectBle());
        
        const bruteforceBtn = document.getElementById('bruteforceBtn');
        if (bruteforceBtn) bruteforceBtn.addEventListener('click', () => this.bruteforceToken());
        
        const reconnectBtn = document.getElementById('reconnectBtn');
        if (reconnectBtn) reconnectBtn.addEventListener('click', () => this.fetchData());
        
        const saveTokenBtn = document.getElementById('saveTokenBtn');
        if (saveTokenBtn) saveTokenBtn.addEventListener('click', () => this.saveToken());
        
        const rebootBtn = document.getElementById('rebootBtn');
        if (rebootBtn) rebootBtn.addEventListener('click', () => this.rebootDevice());
        
        const refreshInfoBtn = document.getElementById('refreshInfoBtn');
        if (refreshInfoBtn) refreshInfoBtn.addEventListener('click', () => this.getDeviceInfo());
    }

    async sendAction(command, params = {}) {
        if (!this.currentGatewayId) {
            this.logAction('请先选择网关');
            return null;
        }

        this.logAction(`发送指令: ${command}...`);
        
        try {
            let apiParams = params;
            
            // Command mapping - 前端命令 => 后端/固件命令
            const commandMap = {
                // 设备管理
                'get_device_info': 'get_device_info',
                'reboot_device': 'reboot',
                'reboot': 'reboot',
                'reset_wifi': 'reset_wifi',
                'factory_reset': 'factory_reset',
                'restart': 'restart',
                
                // 显示控制
                'set_display_brightness': 'set_brightness',
                'set_brightness': 'set_brightness',
                'set_display_mode': 'set_display_mode',
                'flip_display': 'flip_display',
                'get_display_settings': 'get_display_settings',
                
                // BLE 管理
                'scan_ble': 'scan_ble',
                'disconnect_ble': 'disconnect_ble',
                'connect_to': 'connect_to',
                'ble_echo_test': 'ble_echo_test',
                
                // Token 管理
                'bruteforce_token': 'bruteforce_token',
                'set_token': 'set_token',
                
                // WiFi 管理
                'get_wifi_status': 'get_wifi_status',
                'scan_wifi': 'scan_wifi',
                'set_wifi': 'set_wifi',
                
                // 端口控制
                'turn_on_port': 'turn_on_port',
                'turn_off_port': 'turn_off_port',
                'set_port_priority': 'set_port_priority',
                'get_port_config': 'get_port_config',
                'set_port_config': 'set_port_config',
                'get_port_pd_status': 'get_port_pd_status',
                
                // 充电策略
                'set_power_mode': 'set_power_mode',
                'set_temp_mode': 'set_temp_mode',
                'get_charging_strategy': 'get_charging_strategy',
                
                // 调试
                'get_power_curve': 'get_power_curve',
                'get_temp_info': 'get_temp_info',
                'get_debug_log': 'get_debug_log'
            };
            
            let apiCommand = commandMap[command] || command;
            
            const response = await fetch(`${this.cmdUrl}/${this.currentGatewayId}/cmd`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    command: apiCommand,
                    params: apiParams
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.logAction(`指令成功: ${command}`);
                
                // Handle specific responses
                if (command === 'get_device_info' && data.response) {
                    this.updateDeviceInfoPanel(data.response);
                } else if (command === 'get_strategy_config' && data.response) {
                    this.updateStrategyUI(data.response);
                }
            } else {
                this.logAction(`指令失败: ${data.error || 'Unknown error'}`);
            }
            return data;
            
        } catch (error) {
            console.error('Command failed:', error);
            this.logAction(`发送失败: ${error.message}`);
            return null;
        }
    }
    
    getDeviceInfo() { this.sendAction('get_device_info'); }
    rebootDevice() { 
        if(confirm('确定要重启设备吗?')) this.sendAction('reboot_device'); 
    }
    resetWifi() {
        if(confirm('确定要重置WiFi设置吗? 设备将重启并进入配网模式。')) this.sendAction('reset_wifi');
    }
    
    async uploadFirmware() {
        const fileInput = document.getElementById('firmwareFile');
        const file = fileInput.files[0];
        if (!file) {
            alert('请先选择固件文件 (.bin)');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        const progressBar = document.getElementById('uploadProgressBar');
        const progressContainer = document.getElementById('uploadProgressContainer');
        const statusMsg = document.getElementById('otaStatusMessage');
        
        progressContainer.style.display = 'block';
        statusMsg.textContent = '正在上传...';
        
        try {
            const response = await fetch('/api/ota/upload', {
                method: 'POST',
                headers: { 'X-API-Key': this.apiKey },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                progressBar.style.width = '100%';
                statusMsg.textContent = '上传成功，正在触发更新...';
                
                await this.triggerOtaUpdate(data.download_url);
            } else {
                statusMsg.textContent = `上传失败: ${data.detail || '未知错误'}`;
                progressBar.style.width = '0%';
            }
        } catch (error) {
            statusMsg.textContent = `错误: ${error.message}`;
        }
    }
    
    async triggerOtaUpdate(firmwarePath) {
        if (!this.currentGatewayId) return;
        
        try {
            const fullUrl = `${window.location.origin}${firmwarePath}`;
            
            const response = await fetch(`/api/gateway/${this.currentGatewayId}/ota`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    gateway_id: this.currentGatewayId,
                    firmware_url: fullUrl
                })
            });
            
            const data = await response.json();
            if (data.success) {
                document.getElementById('otaStatusMessage').textContent = '更新指令已发送，设备将重启...';
            } else {
                document.getElementById('otaStatusMessage').textContent = '更新指令发送失败';
            }
        } catch (error) {
            console.error(error);
        }
    }

    switchChartMode(mode) {
        this.chartMode = mode;
        document.querySelectorAll('.chart-mode-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById(mode === 'realtime' ? 'realtimeToggle' :
            mode === 'tenminute' ? 'tenMinuteToggle' : 'hourlyToggle');
        if (activeBtn) activeBtn.classList.add('active');
        this.updateChartDisplay();
    }

    startMonitoring() {
        this.fetchData();
    }

    async fetchData() {
        if (!this.currentGatewayId) return;
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.isManualRefresh) {
            return;
        }

        try {
            if (this.isManualRefresh) {
                document.getElementById('refreshBtn').classList.add('loading');
            }
            
            const response = await fetch(`${this.dataUrl}?gateway_id=${this.currentGatewayId}`, {
                headers: this.getHeaders()
            });
            const bleData = await response.json();
            
            bleData.connected = bleData.online; 
            
            const parsedData = this.parseBleData(bleData);
            this.updateUI(parsedData);
            this.updatePowerData(parsedData.totalPower);
            
            this.updateStatus(bleData.online ? 'connected' : 'disconnected');
            
            this.retryCount = 0;
            this.isManualRefresh = false;
            document.getElementById('refreshBtn').classList.remove('loading');
            
            clearTimeout(this.monitoringInterval);
            this.monitoringInterval = setTimeout(() => this.fetchData(), this.updateInterval);
            
        } catch (error) {
            console.error('Fetch data failed:', error);
            this.retryCount++;
            this.updateStatus('disconnected');
            document.getElementById('refreshBtn').classList.remove('loading');
            
            const backoff = Math.min(1000 * Math.pow(1.5, this.retryCount), 30000);
            this.monitoringInterval = setTimeout(() => this.fetchData(), backoff);
        }
    }

    parseBleData(bleData) {
        const portData = {};
        let totalPower = 0;
        let totalCurrent = 0;
        let maxVoltage = 0;
        let activePorts = 0;
        let wifiSignal = bleData.system?.wifiSignal || bleData.rssi || 0;
        let freeHeap = bleData.system?.freeHeap || 0;

        if (bleData.ports && Array.isArray(bleData.ports)) {
            bleData.ports.forEach((port, index) => {
                const pId = port.port_id !== undefined ? port.port_id : index;
                
                const cableName = this.getCableName(port.cablePid);
                const deviceName = this.getDeviceInfo(port.manufacturerVid, port.manufacturerPid);
                
                const portInfo = {
                    state: port.state || 0,
                    protocol: port.protocol || 0,
                    current: port.current || 0, 
                    voltage: port.voltage || 0, 
                    power: port.power || 0,     
                    
                    cableName: cableName,
                    deviceName: deviceName,
                    
                    ...port
                };

                portData[pId] = portInfo;

                totalPower += portInfo.power;
                totalCurrent += portInfo.current;
                maxVoltage = Math.max(maxVoltage, portInfo.voltage);

                if (portInfo.current > 0) activePorts++;
            });
        }
        
        if (bleData.totalPower !== undefined) totalPower = bleData.totalPower;

        return {
            ports: portData,
            totalPower: totalPower,
            averageVoltage: maxVoltage / 1000,
            totalCurrent: totalCurrent / 1000,
            activePorts: activePorts,
            wifiSignal: wifiSignal,
            freeHeap: freeHeap,
            chargingStatus: activePorts > 0 ? `${activePorts}个端口充电中` : '待机',
            timestamp: Date.now()
        };
    }

    getCableName(cablePid) {
        if (typeof CableConfig !== 'undefined' && CableConfig.getCableName) {
            return CableConfig.getCableName(cablePid);
        }
        return cablePid ? `线材 ${cablePid}` : '未知线材';
    }

    getDeviceInfo(vid, pid) {
        if (typeof CableManager !== 'undefined' && CableManager.getDeviceInfo) {
            return CableManager.getDeviceInfo(vid, pid);
        }
        return null;
    }
    
    getDeviceImage(vid, pid, deviceName) {
        if (typeof CableManager !== 'undefined' && CableManager.getDeviceImage) {
            return CableManager.getDeviceImage(vid, pid, deviceName);
        }
        return '';
    }

    getManufacturerLogo(vid) {
        if (typeof CableManager !== 'undefined' && CableManager.getManufacturerLogo) {
            return CableManager.getManufacturerLogo(vid);
        }
        return '';
    }

    getProtocolName(protocol) {
        const protocols = {
            0: 'None', 1: 'QC2.0', 2: 'QC3.0', 3: 'FCP', 4: 'SCP',
            5: 'PD2.0', 6: 'PD3.0', 7: 'PD3.1', 8: 'APPLE', 9: 'PPS',
            10: 'UFCS', 11: 'PE', 12: 'SFCP', 13: 'AFC'
        };
        return protocols[protocol] || `Unknown (${protocol})`;
    }

    getBatteryCapacityColorClass(designCapacity) {
        if (designCapacity <= 0) return 'capacity-unknown';
        if (designCapacity < 20000) return 'capacity-small';
        if (designCapacity < 50000) return 'capacity-medium';
        if (designCapacity < 80000) return 'capacity-large';
        return 'capacity-xlarge';
    }

    updateUI(data) {
        // 更新连接状态面板
        const connStatus = document.getElementById('bleConnectionStatus');
        const gwName = document.getElementById('currentGatewayName');
        const targetName = document.getElementById('targetDeviceName');
        
        if (gwName) gwName.textContent = this.gateways[this.currentGatewayId]?.device_name || this.currentGatewayId || 'Unknown';
        
        // 使用后端返回的 ble_connected 状态
        const isBleConnected = data.activePorts > 0 || (this.gateways[this.currentGatewayId]?.ble_connected); 
        
        if (connStatus) {
            connStatus.textContent = isBleConnected ? '已连接' : '未连接';
            connStatus.className = `status-badge ${isBleConnected ? 'connected' : 'disconnected'}`;
        }
        
        if (targetName) {
            targetName.textContent = isBleConnected ? (this.gateways[this.currentGatewayId]?.charger_name || 'CP02-Device') : '未连接';
            targetName.style.color = isBleConnected ? '#00f5ff' : '#666';
        }

        this.updateMetricCard('power', data.totalPower, 'W', 1);
        
        const voltageEl = document.getElementById('voltageValue2');
        if (voltageEl) voltageEl.textContent = `${data.averageVoltage.toFixed(1)} V`;
        
        const currentEl = document.getElementById('currentValue2');
        if (currentEl) currentEl.textContent = `${data.totalCurrent.toFixed(2)} A`;
        
        const wifiEl = document.getElementById('wifiValue');
        if (wifiEl) wifiEl.textContent = `${data.wifiSignal} dBm`;
        
        document.getElementById('voltageValue').textContent = `${data.averageVoltage.toFixed(1)} V`;
        document.getElementById('currentValue').textContent = `${data.totalCurrent.toFixed(2)} A`;
        document.getElementById('chargingStatus').textContent = data.chargingStatus;
        document.getElementById('totalTime').textContent = `${data.activePorts} 个`;
        
        this.updatePortDetails(data.ports);
        
        const cPower = document.getElementById('compactPower');
        if (cPower) cPower.textContent = `${data.totalPower.toFixed(1)} W`;
        
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
    }

    updateMetricCard(metric, value, unit, decimals) {
        const el = document.getElementById(`${metric}Value`);
        if (el) el.textContent = `${value.toFixed(decimals)} ${unit}`;
        
        const changeEl = document.getElementById(`${metric}Change`);
        if (changeEl) {
            const previousValue = this.previousValues[metric];
            if (previousValue !== undefined) {
                const change = value - previousValue;
                const changePercent = previousValue > 0 ? ((change / previousValue) * 100).toFixed(1) : '0.0';
                
                let changeClass = 'neutral';
                let changeText = '0%';
                if (Math.abs(change) > 0.01) {
                    if (change > 0) { changeClass = 'positive'; changeText = `+${changePercent}%`; }
                    else { changeClass = 'negative'; changeText = `${changePercent}%`; }
                }
                changeEl.className = `metric-change ${changeClass}`;
                changeEl.textContent = changeText;
            }
        }
        
        this.previousValues[metric] = value;
    }

    updatePowerData(power) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        this.realtimeData.push(power);
        this.realtimeLabels.push(timeLabel);
        if (this.realtimeData.length > this.maxDataPoints) {
            this.realtimeData.shift();
            this.realtimeLabels.shift();
        }
        this.updateChartDisplay();
    }

    updateChartDisplay() {
        if (!this.chart) return;
        this.chart.data.labels = this.realtimeLabels;
        this.chart.data.datasets[0].data = this.realtimeData;
        this.chart.update('none');
    }

    updatePortDetails(ports) {
        const container = document.getElementById('portsContainer');
        if (!container) return;
        
        if (!ports || Object.keys(ports).length === 0) {
            this.showEmptyPortsState('等待设备连接');
            this.update3DVisualization({});
            return;
        }

        this.update3DVisualization(ports);
        
        let grid = container.querySelector('.ports-grid');
        if (!grid) {
            grid = document.createElement('div');
            grid.className = 'ports-grid';
            container.innerHTML = '';
            container.appendChild(grid);
        }
        
        Object.entries(ports).forEach(([key, port]) => {
            const portId = parseInt(key);
            const cardId = `port-card-${portId}`;
            let card = document.getElementById(cardId);
            
            const power = port.power.toFixed(1);
            const voltage = (port.voltage / 1000).toFixed(1);
            const current = (port.current / 1000).toFixed(2);
            const active = port.current > 0;
            const statusClass = active ? 'active' : 'idle';
            const protocolName = this.getProtocolName(port.protocol);
            
            const html = `
                <div class="port-header">
                    <div class="port-title">
                        <span class="port-id">端口 ${portId + 1} ${this.getManufacturerLogo(port.manufacturerVid)}</span>
                        <div class="port-tags">
                            ${port.cableName && port.cableName !== '未知线材' ? `<span class="port-tag cable-tag">${port.cableName}</span>` : ''}
                            ${port.deviceName ? `<span class="port-tag device-tag">${port.deviceName}</span>` : ''}
                        </div>
                    </div>
                    <span class="port-status ${statusClass}">${active ? '充电中' : '空闲'}</span>
                </div>
                <div class="port-metrics">
                    <div class="port-metric"><span class="metric-label">功率</span><span class="metric-value">${power}W</span></div>
                    <div class="port-metric"><span class="metric-label">电压</span><span class="metric-value">${voltage}V</span></div>
                    <div class="port-metric"><span class="metric-label">电流</span><span class="metric-value">${current}A</span></div>
                    <div class="port-metric"><span class="metric-label">协议</span><span class="metric-value">${protocolName}</span></div>
                </div>
            `;
            
            if (!card) {
                card = document.createElement('div');
                card.id = cardId;
                card.className = `port-item ${statusClass}`;
                card.innerHTML = html;
                grid.appendChild(card);
            } else {
                card.className = `port-item ${statusClass}`;
                if (card.innerHTML !== html) card.innerHTML = html;
            }
        });
        
        this.updateControlPanelSwitches(ports);
    }
    
    updateControlPanelSwitches(ports) {
        const container = document.getElementById('portSwitches');
        if (!container) return;
        
        const html = Object.entries(ports).map(([key, port]) => {
            const pId = parseInt(key);
            const isActive = port.current > 0 || port.state === 1; // Assuming state 1 is ON
            
            return `
            <div class="modern-port-card">
                <div class="port-header">
                    <div class="port-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                        </svg>
                    </div>
                    <span class="port-id">端口 ${pId + 1}</span>
                </div>
                <label class="ios-switch">
                    <input type="checkbox" ${isActive ? 'checked' : ''} onchange="monitor.togglePort(${pId}, this.checked)">
                    <span class="ios-slider"></span>
                </label>
            </div>`;
        }).join('');
        
        if (container.innerHTML !== html) container.innerHTML = html;
    }
    
    togglePort(portId, state) {
        if (state) {
            this.turnOnPort(portId);
        } else {
            this.turnOffPort(portId);
        }
    }

    // ============ 端口控制方法 ============
    async turnOnPort(portId) {
        if (!this.currentGatewayId) {
            this.logAction('请先选择网关');
            return;
        }
        
        this.logAction(`正在打开端口 ${portId + 1}...`);
        
        try {
            const response = await fetch(`/api/gateway/${this.currentGatewayId}/port/${portId}/on`, {
                headers: this.getHeaders()
            });
            const data = await response.json();
            
            if (data.success) {
                this.logAction(`端口 ${portId + 1} 已打开`);
            } else {
                this.logAction(`端口 ${portId + 1} 打开失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            this.logAction(`端口 ${portId + 1} 打开失败: ${error.message}`);
        }
    }
    
    async turnOffPort(portId) {
        if (!this.currentGatewayId) {
            this.logAction('请先选择网关');
            return;
        }
        
        this.logAction(`正在关闭端口 ${portId + 1}...`);
        
        try {
            const response = await fetch(`/api/gateway/${this.currentGatewayId}/port/${portId}/off`, {
                headers: this.getHeaders()
            });
            const data = await response.json();
            
            if (data.success) {
                this.logAction(`端口 ${portId + 1} 已关闭`);
            } else {
                this.logAction(`端口 ${portId + 1} 关闭失败: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            this.logAction(`端口 ${portId + 1} 关闭失败: ${error.message}`);
        }
    }
    
    // ============ BLE扫描与连接 ============
    async startRemoteScan() {
        const overlay = document.getElementById('radarOverlay');
        const list = document.getElementById('deviceList');
        
        // 显示雷达动画
        if (overlay) overlay.style.display = 'flex';
        
        this.logAction('正在请求网关扫描周边BLE设备...');
        
        try {
            const result = await this.sendAction('scan_ble');
            
            if (overlay) overlay.style.display = 'none';
            
            if (result && result.success) {
                // 如果固件返回扫描结果
                if (result.response && result.response.devices) {
                    const devices = result.response.devices;
                    list.innerHTML = devices.map(dev => `
                        <li class="device-item" onclick="monitor.connectToDevice('${dev.name}')">
                            <div class="device-info">
                                <span class="device-name">${dev.name}</span>
                                <span class="device-rssi">📶 ${dev.rssi} dBm</span>
                            </div>
                            <button class="connect-btn">连接</button>
                        </li>
                    `).join('');
                    this.logAction(`扫描完成，发现 ${devices.length} 个设备`);
                } else {
                    this.logAction('扫描命令已发送，等待网关返回结果...');
                    // 模拟等待
                    setTimeout(() => this.fetchData(), 3000);
                }
            } else {
                this.logAction('扫描请求失败');
            }
        } catch (error) {
            if (overlay) overlay.style.display = 'none';
            this.logAction(`扫描失败: ${error.message}`);
        }
    }

    async connectToDevice(deviceName) {
        this.logAction(`正在请求连接设备: ${deviceName}...`);
        const result = await this.sendAction('connect_to', { device_name: deviceName });
        if (result && result.success) {
            this.logAction(`已请求连接 ${deviceName}`);
            setTimeout(() => this.fetchData(), 2000);
        }
    }
    
    async disconnectBle() {
        if (!this.currentGatewayId) {
            this.logAction('请先选择网关');
            return;
        }
        
        this.logAction('正在断开BLE连接...');
        const result = await this.sendAction('disconnect_ble');
        if (result && result.success) {
            this.logAction('BLE已断开');
        }
    }
    
    // ============ Token管理 ============
    async bruteforceToken() {
        if (!this.currentGatewayId) {
            this.logAction('请先选择网关');
            return;
        }
        
        this.logAction('正在暴力破解Token (0x00-0xFF)...');
        const result = await this.sendAction('bruteforce_token');
        if (result && result.success) {
            this.logAction(`Token破解成功: 0x${result.token?.toString(16).toUpperCase().padStart(2, '0') || '??'}`);
            const tokenInput = document.getElementById('tokenInput');
            if (tokenInput && result.token !== undefined) {
                tokenInput.value = `0x${result.token.toString(16).toUpperCase().padStart(2, '0')}`;
            }
        } else {
            this.logAction('Token破解失败');
        }
    }
    
    async saveToken() {
        const tokenInput = document.getElementById('tokenInput');
        if (!tokenInput || !tokenInput.value) {
            this.logAction('请输入Token');
            return;
        }
        
        let tokenValue = tokenInput.value.trim();
        let token;
        
        // 支持十进制和十六进制
        if (tokenValue.startsWith('0x') || tokenValue.startsWith('0X')) {
            token = parseInt(tokenValue, 16);
        } else {
            token = parseInt(tokenValue, 10);
        }
        
        if (isNaN(token) || token < 0 || token > 255) {
            this.logAction('Token无效，请输入0-255之间的值');
            return;
        }
        
        this.logAction(`正在保存Token: 0x${token.toString(16).toUpperCase().padStart(2, '0')}...`);
        const result = await this.sendAction('set_token', { token: token });
        if (result && result.success) {
            this.logAction(`Token已保存: 0x${token.toString(16).toUpperCase().padStart(2, '0')}`);
        }
    }
    
    // ============ 设备信息更新 ============
    updateDeviceInfoPanel(info) {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if(el) el.textContent = val || '--';
        };
        
        setVal('infoModel', info.model);
        setVal('infoSerial', info.serial);
        setVal('infoFirmware', info.firmware || info.version);
        setVal('infoBleAddr', info.ble_addr || info.mac || info.bleAddr);
        setVal('infoUptime', this.formatUptime(info.uptime));
    }
    
    formatUptime(seconds) {
        if (!seconds) return '--';
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) return `${days}天 ${hours}小时`;
        if (hours > 0) return `${hours}小时 ${mins}分钟`;
        return `${mins}分钟`;
    }
    
    // ============ 策略配置 ============
    updateStrategyUI(config) {
        if (config.power_mode !== undefined) {
            const toggle = document.getElementById('powerModeToggle');
            const text = document.getElementById('powerModeText');
            if (toggle) toggle.checked = config.power_mode === 1;
            if (text) text.textContent = config.power_mode === 1 ? '自动 (Auto)' : '手动 (Manual)';
        }
        if (config.temp_mode !== undefined) {
            const toggle = document.getElementById('tempModeToggle');
            if (toggle) toggle.checked = config.temp_mode;
        }
    }
    
    // ============ 端口优先级设置（支持单端口） ============
    setPortPriority(portId) {
        // 如果传入portId，使用对应输入框
        let priority, pId;
        
        if (portId !== undefined) {
            pId = portId;
            const inputId = `p${portId + 1}_priority`;
            const input = document.getElementById(inputId);
            priority = input ? parseInt(input.value) : NaN;
        } else {
            // 兼容旧的全局方式
            pId = parseInt(document.getElementById('configPortId')?.value || 0);
            priority = parseInt(document.getElementById('portPriority')?.value);
        }
        
        if (isNaN(priority) || priority < 0 || priority > 255) {
            alert('请输入有效的优先级 (0-255)');
            return;
        }
        
        this.logAction(`设置端口 ${pId + 1} 优先级为 ${priority}...`);
        this.sendAction('set_port_priority', {
            port_id: pId,
            priority: priority
        });
    }

    setPortConfig() {
        const portId = parseInt(document.getElementById('configPortId')?.value || 0);
        // 收集协议配置
        const protocols = [];
        // 这里需要根据实际的checkbox来收集
        this.sendAction('set_port_config', {
            port_id: portId,
            protocols: protocols
        });
    }

    // ============ WiFi管理 ============
    async setWifi() {
        const ssid = document.getElementById('wifiSSID')?.value;
        const pass = document.getElementById('wifiPass')?.value;
        
        if (!ssid) {
            alert('请输入SSID');
            return;
        }
        
        if(confirm(`确定要将设备连接到WiFi: ${ssid}?`)) {
            this.logAction(`正在配置WiFi: ${ssid}...`);
            const result = await this.sendAction('set_wifi', { ssid: ssid, password: pass || '' });
            if (result && result.success) {
                this.logAction('WiFi配置已发送');
            }
        }
    }

    async getWifiStatus() {
        this.logAction('正在查询WiFi状态...');
        const result = await this.sendAction('get_wifi_status');
        if (result && result.success && result.response) {
            const status = result.response;
            const statusEl = document.getElementById('wifiStatusValue');
            if (statusEl) {
                statusEl.textContent = status.connected ? `已连接: ${status.ssid || 'Unknown'}` : '未连接';
                statusEl.style.color = status.connected ? '#2ed573' : '#ff4757';
            }
            this.logAction(`WiFi状态: ${status.connected ? '已连接' : '未连接'}`);
        }
    }

    async scanWifi() {
        this.logAction('正在扫描WiFi热点...');
        const result = await this.sendAction('scan_wifi');
        const container = document.getElementById('wifiScanResults');
        
        if (result && result.success && result.response && result.response.networks) {
            const networks = result.response.networks;
            container.innerHTML = networks.map(net => `
                <div class="wifi-item" style="display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); cursor: pointer;" 
                     onclick="document.getElementById('wifiSSID').value='${net.ssid}'">
                    <span>${net.ssid}</span>
                    <span style="color: #888;">${net.rssi} dBm</span>
                </div>
            `).join('');
            this.logAction(`发现 ${networks.length} 个WiFi热点`);
        } else {
            container.innerHTML = '<div style="padding: 8px; color: #888;">未发现热点或扫描失败</div>';
            this.logAction('WiFi扫描失败或无结果');
        }
    }

    // ============ 显示设置 ============
    async setDisplayMode(mode) {
        this.logAction(`设置显示模式: ${mode}...`);
        await this.sendAction('set_display_mode', { mode: mode });
    }

    async getDisplaySettings() {
        this.logAction('正在查询显示设置...');
        const result = await this.sendAction('get_display_settings');
        if (result && result.success && result.response) {
            const settings = result.response;
            const brightnessSlider = document.getElementById('brightnessSlider');
            const modeSelect = document.getElementById('displayModeSelect');
            
            if (brightnessSlider && settings.brightness !== undefined) {
                brightnessSlider.value = settings.brightness;
            }
            if (modeSelect && settings.mode !== undefined) {
                modeSelect.value = settings.mode;
            }
            this.logAction(`显示设置: 亮度=${settings.brightness || '--'}, 模式=${settings.mode || '--'}`);
        }
    }

    // ============ 端口高级配置 ============
    async getPortConfig() {
        const portId = parseInt(document.getElementById('configPortId')?.value || 0);
        this.logAction(`正在读取端口 ${portId + 1} 配置...`);
        
        const result = await this.sendAction('get_port_config', { port_id: portId });
        if (result && result.success && result.response) {
            const config = result.response;
            document.getElementById('portConfigProtocol').textContent = this.getProtocolName(config.protocol || 0);
            document.getElementById('portConfigPriority').textContent = config.priority !== undefined ? config.priority : '--';
            this.logAction(`端口 ${portId + 1} 配置读取成功`);
        }
    }

    setPortConfig() {
        const portId = parseInt(document.getElementById('configPortId')?.value || 0);
        // 收集协议配置
        const protocols = [];
        // 这里需要根据实际的checkbox来收集
        this.logAction(`正在保存端口 ${portId + 1} 配置...`);
        this.sendAction('set_port_config', {
            port_id: portId,
            protocols: protocols
        });
    }

    // ============ 高级调试功能 ============
    async getPortPdStatus() {
        const portId = parseInt(document.getElementById('debugPortId')?.value || 0);
        this.logAction(`正在查询端口 ${portId + 1} PD状态...`);
        
        const result = await this.sendAction('get_port_pd_status', { port_id: portId });
        this.showDebugInfo(result);
    }

    async getPortTemperature() {
        const portId = parseInt(document.getElementById('debugPortId')?.value || 0);
        this.logAction(`正在查询端口 ${portId + 1} 温度...`);
        
        const result = await this.sendAction('get_temp_info', { port_id: portId });
        if (result && result.success && result.response) {
            this.showDebugInfo({ temperature: result.response.temperature + '°C' });
        } else {
            this.showDebugInfo(result);
        }
    }

    async getPowerCurve() {
        this.logAction('正在获取功率曲线数据...');
        const result = await this.sendAction('get_power_curve');
        this.showDebugInfo(result);
    }

    async bleEchoTest() {
        const testData = 'ECHO_TEST_' + Date.now();
        this.logAction(`BLE回显测试: ${testData}`);
        
        const result = await this.sendAction('ble_echo_test', { data: testData });
        if (result && result.success) {
            this.logAction('BLE回显测试成功');
            this.showDebugInfo({ status: 'OK', sent: testData, received: result.response?.data || 'N/A' });
        } else {
            this.logAction('BLE回显测试失败');
            this.showDebugInfo({ status: 'FAILED', error: result?.error || 'Unknown' });
        }
    }

    async getDebugLog() {
        this.logAction('正在获取调试日志...');
        const result = await this.sendAction('get_debug_log');
        this.showDebugInfo(result);
    }

    showDebugInfo(data) {
        const card = document.getElementById('debugInfoCard');
        const content = document.getElementById('debugInfoContent');
        
        if (card && content) {
            card.style.display = 'block';
            if (typeof data === 'object') {
                content.textContent = JSON.stringify(data, null, 2);
            } else {
                content.textContent = String(data);
            }
        }
    }
    
    // ============ 控制面板状态刷新 ============
    updateControlPanelStatus() {
        this.fetchData();
        this.logAction('已刷新端口状态');
    }
    
    // ============ 显示信息反馈 ============
    displayInfo(message) {
        const infoDisplay = document.getElementById('infoDisplay');
        if (infoDisplay) {
            const timestamp = new Date().toLocaleTimeString();
            if (typeof message === 'object') {
                infoDisplay.textContent = `[${timestamp}]\n${JSON.stringify(message, null, 2)}`;
            } else {
                infoDisplay.textContent = `[${timestamp}] ${message}`;
            }
        }
    }

    update3DVisualization(ports) {
        Object.entries(ports).forEach(([key, port]) => {
            const pId = parseInt(key);
            
            const cableEl = document.querySelector(`.cable-port-${pId}.cable-putong`);
            if (cableEl) {
                if (port.current > 0) {
                    cableEl.style.display = 'block';
                    setTimeout(() => cableEl.classList.add('show'), 10);
                } else {
                    cableEl.style.display = 'none';
                    cableEl.classList.remove('show');
                }
            }
            
            const ind = document.getElementById(`charging-indicator-${pId}`);
            if (ind) {
                ind.style.display = port.current > 0 ? 'block' : 'none';
            }
            
            const info = document.getElementById(`power-info-${pId}`);
            if (info) {
                if (port.current > 0) {
                    info.style.display = 'block';
                    info.textContent = `${port.power.toFixed(1)}W`;
                } else {
                    info.style.display = 'none';
                }
            }
        });
    }

    setupControlPanel() {
    }

    toggleWakeLock() {
        if (!navigator.wakeLock) return;
        if (!this.wakeLock) {
            this.requestWakeLock();
        } else {
            this.wakeLock.release();
            this.wakeLock = null;
            document.getElementById('wakeLockToggle')?.classList.remove('active');
        }
    }

    async requestWakeLock() {
        try {
            this.wakeLock = await navigator.wakeLock.request('screen');
            document.getElementById('wakeLockToggle')?.classList.add('active');
        } catch (err) {
            console.log(err);
        }
    }
    
    setupWakeLockHandlers() {
        document.addEventListener('visibilitychange', async () => {
            if (this.wakeLock !== null && document.visibilityState === 'visible') {
                this.requestWakeLock();
            }
        });
    }

    toggle3DRotation() {
        this.isRotated = !this.isRotated;
        const viz = document.getElementById('reallyvison');
        const btn = document.getElementById('rotationToggle');
        
        if (this.isRotated) {
            viz.classList.add('rotated');
            btn.classList.add('active');
            btn.querySelector('.toggle-text').textContent = '横屏';
        } else {
            viz.classList.remove('rotated');
            btn.classList.remove('active');
            btn.querySelector('.toggle-text').textContent = '竖屏';
        }
    }

    toggleLayout() {
        this.isCompactMode = !this.isCompactMode;
        const container = document.querySelector('.container');
        const headerToggle = document.getElementById('headerLayoutToggle');
        const layoutToggle = document.getElementById('layoutToggle');
        
        if (this.isCompactMode) {
            container.classList.add('compact-mode');
            if (headerToggle) headerToggle.classList.add('compact-active');
            if (layoutToggle) layoutToggle.classList.add('active');
            document.getElementById('standardLabel').classList.remove('active');
            document.getElementById('compactLabel').classList.add('active');
        } else {
            container.classList.remove('compact-mode');
            if (headerToggle) headerToggle.classList.remove('compact-active');
            if (layoutToggle) layoutToggle.classList.remove('active');
            document.getElementById('standardLabel').classList.add('active');
            document.getElementById('compactLabel').classList.remove('active');
        }
        
        this.isLayoutSwitching = true;
        setTimeout(() => this.isLayoutSwitching = false, 1000);
    }
    
    logAction(msg) {
        const log = document.getElementById('actionLog');
        if (!log) return;
        const time = new Date().toLocaleTimeString();
        const div = document.createElement('div');
        div.className = 'log-entry';
        div.innerHTML = `<span class="log-time">[${time}]</span><span class="log-msg">${msg}</span>`;
        log.insertBefore(div, log.firstChild);
        if (log.children.length > 50) log.removeChild(log.lastChild);
    }
}

const monitor = new ChargingStationMonitor();
