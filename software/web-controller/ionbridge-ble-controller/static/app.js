// IonBridge BLE Controller - Enhanced JavaScript
// Complete WebSocket client with all BLE command support

// WebSocket connection
let ws = null;
let reconnectInterval = null;
let selectedDevice = null;
let currentDialogAction = null;
let lastPortSelectValue = null; // 记录上一次的端口选择器值

// Auto-refresh timers
let portStatusRefreshTimer = null;
let cableInfoRefreshTimer = null;
let powerCurveRefreshTimer = null;
const REFRESH_INTERVAL = 2000; // 2 seconds

// Protocol names for port config (PowerFeatures bit positions)
const PROTOCOL_NAMES = [
    'TFCP', 'PE', 'QC2.0', 'QC3.0', 'QC3+', 'AFC', 'FCP', 'HV_SCP',
    'LV_SCP', 'SFCP', 'Apple 5V', 'Samsung 5V', 'BC1.2', 'UFCS', 'RPi 5V5A', 'VOOC',
    'PD', 'PPS', 'QC4.0', 'QC4+', 'Dash/Warp', 'SFC', 'MTK PE', 'MTK PE+'
];

// Fast charging protocol enum values (from data_types.h)
// These are the actual protocol values returned by the device
const FAST_CHARGING_PROTOCOLS = {
    0: "无",
    1: "QC2.0",
    2: "QC3.0",
    3: "QC3+",
    4: "SFCP",
    5: "AFC",
    6: "FCP",
    7: "SCP",
    8: "VOOC1.0",
    9: "VOOC4.0",
    10: "SuperVOOC2.0",
    11: "TFCP",
    12: "UFCS",
    13: "PE1.0",
    14: "PE2.0",
    15: "PD 5V",
    16: "PD 高压",
    17: "PD SPR AVS",
    18: "PD PPS",
    19: "PD EPR 高压",
    20: "PD AVS",
    0xFF: "未充电"
};

// Get protocol name from protocol value
function getProtocolName(protocolValue) {
    return FAST_CHARGING_PROTOCOLS[protocolValue] || `未知(${protocolValue})`;
}

// Charging strategy names
const CHARGING_STRATEGIES = {
    0: '自动分配',
    1: '固定分配',
    2: '优先级分配'
};

// Display mode names
const DISPLAY_MODES = {
    0: '默认模式',
    1: '简洁模式',
    2: '详细模式',
    3: '自定义模式'
};

// Initialize WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        addLog('WebSocket 已连接', 'info');
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onerror = (error) => {
        addLog('WebSocket 错误', 'error');
    };

    ws.onclose = () => {
        addLog('WebSocket 已断开', 'warning');
        if (!reconnectInterval) {
            reconnectInterval = setInterval(connectWebSocket, 5000);
        }
    };
}

// Handle incoming messages
function handleMessage(data) {
    switch (data.type) {
        case 'log':
            addLog(data.message, 'info');
            break;
        case 'status':
            updateStatus(data.data);
            break;
        case 'response':
            handleResponse(data.action, data);
            break;
        case 'error':
            addLog(`错误: ${data.message}`, 'error');
            showToast(data.message, 'error');
            break;
    }
}

// Update status bar
function updateStatus(status) {
    const deviceName = document.getElementById('device-name');
    const connectionStatus = document.getElementById('connection-status');
    const tokenValue = document.getElementById('token-value');
    const autoRefresh = document.getElementById('auto-refresh');
    const autoReconnect = document.getElementById('auto-reconnect');
    const uptime = document.getElementById('uptime');

    deviceName.textContent = status.device || '未连接';
    connectionStatus.textContent = status.connected ? '已连接' : '未连接';
    connectionStatus.className = `status-value ${status.connected ? 'connected' : 'disconnected'}`;
    tokenValue.textContent = status.token !== null ? `0x${status.token.toString(16).toUpperCase().padStart(2, '0')}` : '无';
    autoRefresh.textContent = status.auto_refresh ? '启用' : '禁用';
    autoReconnect.textContent = status.auto_reconnect ? '启用' : '禁用';

    if (status.uptime !== undefined) {
        const hours = Math.floor(status.uptime / 3600);
        const minutes = Math.floor((status.uptime % 3600) / 60);
        const seconds = status.uptime % 60;
        uptime.textContent = `${hours}h ${minutes}m ${seconds}s`;
    }
}

// Add log entry
function addLog(message, type = 'info') {
    const log = document.getElementById('log');
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="timestamp">[${timestamp}]</span>${message}`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

// Clear log
function clearLog() {
    document.getElementById('log').innerHTML = '';
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Send action to server
function sendAction(action, params = {}) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('WebSocket 未连接', 'error');
        return false;
    }

    ws.send(JSON.stringify({
        action: action,
        params: params
    }));
    return true;
}

// Handle response
function handleResponse(action, data) {
    if (!data.success) {
        addLog(`${action} 失败: ${data.message || '未知错误'}`, 'error');
        showToast(data.message || '操作失败', 'error');
        return;
    }

    addLog(`${action} 成功`, 'info');

    // Handle specific actions
    switch (action) {
        case 'scan_devices':
            handleScanDevices(data.data);
            break;
        case 'connect':
            showToast('设备已连接', 'success');
            break;
        case 'disconnect':
            showToast('设备已断开', 'info');
            break;
        case 'get_device_info':
            handleDeviceInfo(data.data);
            break;
        case 'get_port_status':
            handlePortStatus(data.data);
            break;
        case 'get_power_statistics':
            handlePowerStatistics(data.data);
            break;
        case 'get_charging_strategy':
            handleChargingStrategy(data.data);
            break;
        case 'get_wifi_status':
            handleWifiStatus(data.data);
            break;
        case 'scan_wifi':
            handleWifiScanResult(data.data);
            break;
        case 'get_display_settings':
            handleDisplaySettings(data.data);
            break;
        case 'get_port_config':
            handlePortConfig(data.data);
            break;
        case 'get_port_priority':
            handlePortPriority(data.data);
            break;
        case 'get_charging_status':
            handleChargingStatus(data.data);
            break;
        // Additional handlers
        case 'get_power_supply_status':
            handlePowerSupplyStatus(data.data);
            break;
        case 'get_device_model':
            handleDeviceModel(data.data);
            break;
        case 'get_device_serial':
            handleDeviceSerial(data.data);
            break;
        case 'get_device_uptime':
            handleDeviceUptime(data.data);
            break;
        case 'get_ap_version':
            handleApVersion(data.data);
            break;
        case 'get_ble_addr':
            handleBleAddr(data.data);
            break;
        case 'get_max_power':
            handleMaxPower(data.data);
            break;
        case 'get_port_max_power':
            handlePortMaxPower(data.data);
            break;
        case 'get_port_temperature':
            handlePortTemperature(data.data);
            break;
        case 'get_night_mode':
            handleNightMode(data.data);
            break;
        case 'get_language':
            handleLanguage(data.data);
            break;
        case 'get_led_mode':
            handleLedMode(data.data);
            break;
        case 'get_auto_off':
            handleAutoOff(data.data);
            break;
        case 'get_screen_saver':
            handleScreenSaver(data.data);
            break;
        case 'get_stored_tokens':
            handleStoredTokens(data.data);
            break;
        case 'load_token_from_storage':
            showToast('Token 已从存储加载', 'success');
            break;
        case 'clear_token_storage':
            showToast('Token 存储已清除', 'success');
            document.getElementById('stored-tokens-list').innerHTML = '';
            break;
        // Advanced Functions
        case 'get_port_pd_status':
            handlePortPDStatus(data.data);
            break;
        case 'get_power_historical_stats':
            handlePowerCurve(data.data);
            break;
        case 'get_start_charge_timestamp':
            handleChargingSession(data.data);
            break;
        case 'set_temperature_mode':
            handleTemperatureMode(data.data);
            break;
        case 'get_compatibility_modes':
            handleCompatibilityModes(data.data);
            break;
        case 'set_compatibility_mode':
            showToast('兼容模式已设置', 'success');
            break;
        case 'get_compatibility_settings':
            handleCompatibilitySettings(data.data);
            break;
        case 'set_custom_compatibility_settings':
            showToast('协议兼容设置已保存', 'success');
            break;
        // 新增: 版本信息
        case 'get_bp_version':
            handleVersionInfo('BP版本', data.data);
            break;
        case 'get_fpga_version':
            handleVersionInfo('FPGA版本', data.data);
            break;
        case 'get_zrlib_version':
            handleVersionInfo('ZRLIB版本', data.data);
            break;
        // 新增: 调试/测试
        case 'ble_echo_test':
            handleEchoTest(data.data);
            break;
        case 'get_debug_log':
            handleDebugLog(data.data);
            break;
        case 'ping_mqtt':
            handlePingResult('MQTT', data.data);
            break;
        case 'ping_http':
            handlePingResult('HTTP', data.data);
            break;
        // 新增: OTA
        case 'wifi_ota':
            showToast(data.message || 'OTA已启动', data.success ? 'success' : 'error');
            break;
        case 'get_ota_progress':
            handleOtaProgress(data.data);
            break;
        case 'confirm_ota':
            showToast('OTA确认成功', 'success');
            break;
        default:
            showToast('操作成功', 'success');
    }
}

// Device Management Functions
function scanDevices() {
    addLog('正在扫描设备...', 'info');
    sendAction('scan_devices', { timeout: 5.0 });
}

function handleScanDevices(data) {
    if (!data.devices || data.devices.length === 0) {
        showToast('未找到设备', 'warning');
        return;
    }

    let content = '<div class="device-list">';
    data.devices.forEach((device, index) => {
        const deviceName = (device.name || '未知设备').replace(/'/g, "\\'");
        content += `
            <div class="device-item" onclick="showConnectOptions('${device.address}', '${deviceName}')">
                <div>
                    <div class="device-name">${device.name || '未知设备'}</div>
                    <div class="device-address">${device.address}</div>
                </div>
                <div class="device-rssi">${device.rssi} dBm</div>
            </div>
        `;
    });
    content += '</div>';

    showDialog('选择设备', content, null);
}

function showConnectOptions(address, name) {
    closeDialog();

    const content = `
        <div class="info-display">
            <div class="info-item">
                <span class="info-label">设备名称</span>
                <span class="info-value">${name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">设备地址</span>
                <span class="info-value">${address}</span>
            </div>
        </div>
        <div class="form-group">
            <label>手动输入 Token (可选)</label>
            <input type="number" id="manual-token-input" min="0" max="255" placeholder="留空则暴力破解">
            <small>如果知道Token，可以手动输入（0-255）。留空则自动暴力破解。</small>
        </div>
    `;

    showDialog('连接设备', content, 'connectWithToken');

    // Store address and name for later use
    window.pendingConnectAddress = address;
    window.pendingConnectName = name;
}

function connectWithToken() {
    const tokenInput = document.getElementById('manual-token-input');
    const tokenValue = tokenInput.value.trim();

    const address = window.pendingConnectAddress;
    const name = window.pendingConnectName;

    closeDialog();

    if (tokenValue) {
        // Manual token
        const token = parseInt(tokenValue, 10);
        if (isNaN(token) || token < 0 || token > 255) {
            showToast('无效的 Token 值 (0-255)', 'error');
            return;
        }
        addLog(`正在连接设备: ${address} (${name})，使用手动Token: 0x${token.toString(16).toUpperCase().padStart(2, '0')}...`, 'info');
        sendAction('connect', { address, token });
    } else {
        // Bruteforce token
        addLog(`正在连接设备: ${address} (${name})，暴力破解Token中...`, 'info');
        sendAction('connect', { address, bruteforce: true });
    }

    // Clear stored values
    window.pendingConnectAddress = null;
    window.pendingConnectName = null;
}

function showConnectDialog() {
    const content = `
        <div class="form-group">
            <label>设备地址</label>
            <input type="text" id="device-address" placeholder="例如: 00:11:22:33:44:55" value="${selectedDevice ? selectedDevice.address : ''}">
        </div>
    `;
    showDialog('连接设备', content, 'connectDevice');
}

function connectDevice() {
    const address = document.getElementById('device-address').value.trim();
    if (!address) {
        showToast('请输入设备地址', 'error');
        return;
    }

    addLog(`正在连接设备: ${address}...`, 'info');
    sendAction('connect', { address });
    closeDialog();
}

function disconnect() {
    addLog('正在断开连接...', 'info');
    sendAction('disconnect');
}

function getDeviceInfo() {
    addLog('正在获取设备信息...', 'info');
    sendAction('get_device_info');
}

function handleDeviceInfo(data) {
    let content = '<div class="info-display">';
    for (const [key, value] of Object.entries(data)) {
        const label = {
            'model': '型号',
            'firmware': '固件版本',
            'serial': '序列号',
            'uptime': '运行时间',
            'uptime_formatted': '运行时间',
            'ble_addr': 'BLE 地址'
        }[key] || key;

        let displayValue = value;
        if (key === 'uptime') {
            // 如果后端没有返回uptime_formatted，则在前端格式化
            const hours = Math.floor(value / 3600);
            const minutes = Math.floor((value % 3600) / 60);
            const seconds = value % 60;
            displayValue = `${hours}h ${minutes}m ${seconds}s`;
        } else if (key === 'uptime_formatted') {
            // 使用后端格式化的运行时间
            displayValue = value;
        } else if (key === 'ble_addr') {
            displayValue = value.toUpperCase().match(/.{1,2}/g).join(':');
        }

        // 跳过原始uptime字段（因为已经有uptime_formatted）
        if (key === 'uptime' && data.uptime_formatted) {
            continue;
        }

        content += `
            <div class="info-item">
                <span class="info-label">${label}</span>
                <span class="info-value">${displayValue}</span>
            </div>
        `;
    }
    content += '</div>';

    showDialog('设备信息', content, null);
}

function getPowerSupplyStatus() {
    addLog('正在获取电源供应状态...', 'info');
    sendAction('get_power_supply_status');
}

function handlePowerSupplyStatus(data) {
    let content = '<div class="info-display">';

    if (data.port_mask !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">端口掩码</span>
                <span class="info-value">0x${data.port_mask.toString(16).toUpperCase().padStart(2, '0')}</span>
            </div>
        `;
    }

    if (data.open_ports !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">打开的端口</span>
                <span class="info-value">${data.open_ports.join(', ') || '无'}</span>
            </div>
        `;
    }

    if (data.raw_data) {
        content += `
            <div class="info-item">
                <span class="info-label">原始数据</span>
                <span class="info-value">${data.raw_data}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('电源供应状态', content, null);
}

function getDeviceModel() {
    addLog('正在获取设备型号...', 'info');
    sendAction('get_device_model');
}

function handleDeviceModel(data) {
    let content = '<div class="info-display">';

    if (data.model) {
        content += `
            <div class="info-item">
                <span class="info-label">设备型号</span>
                <span class="info-value">${data.model}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('设备型号', content, null);
}

function getDeviceSerial() {
    addLog('正在获取设备序列号...', 'info');
    sendAction('get_device_serial');
}

function handleDeviceSerial(data) {
    let content = '<div class="info-display">';

    if (data.serial) {
        content += `
            <div class="info-item">
                <span class="info-label">设备序列号</span>
                <span class="info-value">${data.serial}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('设备序列号', content, null);
}

function getDeviceUptime() {
    addLog('正在获取设备运行时间...', 'info');
    sendAction('get_device_uptime');
}

function handleDeviceUptime(data) {
    let content = '<div class="info-display">';

    if (data.uptime !== undefined) {
        const hours = Math.floor(data.uptime / 3600);
        const minutes = Math.floor((data.uptime % 3600) / 60);
        const seconds = data.uptime % 60;
        const uptimeStr = `${hours}h ${minutes}m ${seconds}s`;

        content += `
            <div class="info-item">
                <span class="info-label">运行时间</span>
                <span class="info-value">${uptimeStr}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('设备运行时间', content, null);
}

function getApVersion() {
    addLog('正在获取固件版本...', 'info');
    sendAction('get_ap_version');
}

function handleApVersion(data) {
    let content = '<div class="info-display">';

    if (data.version) {
        content += `
            <div class="info-item">
                <span class="info-label">固件版本</span>
                <span class="info-value">${data.version}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('固件版本', content, null);
}

function getBleAddr() {
    addLog('正在获取 BLE 地址...', 'info');
    sendAction('get_ble_addr');
}

function handleBleAddr(data) {
    let content = '<div class="info-display">';

    if (data.ble_addr) {
        const formattedAddr = data.ble_addr.toUpperCase().match(/.{1,2}/g).join(':');
        content += `
            <div class="info-item">
                <span class="info-label">BLE 地址</span>
                <span class="info-value">${formattedAddr}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('BLE 地址', content, null);
}

function rebootDevice() {
    if (!confirm('确定要重启设备吗？')) return;
    addLog('正在重启设备...', 'info');
    sendAction('reboot_device');
}

function resetDevice() {
    if (!confirm('警告：这将恢复出厂设置！确定要继续吗？')) return;
    if (!confirm('再次确认：此操作不可恢复！确定要重置设备吗？')) return;
    addLog('正在重置设备...', 'info');
    sendAction('reset_device');
}

// Port Control Functions
function getPortStatus() {
    addLog('正在获取端口状态...', 'info');
    sendAction('get_port_status');
}

function togglePortStatusAutoRefresh() {
    const btn = document.getElementById('port-status-refresh-btn');
    if (portStatusRefreshTimer) {
        clearInterval(portStatusRefreshTimer);
        portStatusRefreshTimer = null;
        btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
        addLog('端口状态自动刷新已关闭', 'info');
    } else {
        portStatusRefreshTimer = setInterval(() => {
            sendAction('get_port_status');
        }, REFRESH_INTERVAL);
        btn.innerHTML = '<i class="fas fa-stop"></i> 关闭自动刷新';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
        addLog('端口状态自动刷新已开启', 'info');
        sendAction('get_port_status'); // Immediate refresh
    }
}

function handlePortStatus(data) {
    const container = document.getElementById('ports-container');
    const portStatusDiv = document.getElementById('port-status');

    if (!data.ports || data.ports.length === 0) {
        showToast('无端口数据', 'warning');
        return;
    }

    // 保存端口状态数据到全局变量，供其他函数使用
    window.portStatusData = data;

    // Add refresh button if not exists
    let refreshBtn = document.getElementById('port-status-refresh-btn');
    if (!refreshBtn) {
        const btnContainer = document.createElement('div');
        btnContainer.style.marginBottom = '10px';
        btnContainer.innerHTML = `<button id="port-status-refresh-btn" class="btn btn-success btn-small" onclick="togglePortStatusAutoRefresh()"><i class="fas fa-play"></i> 开启自动刷新</button>`;
        portStatusDiv.insertBefore(btnContainer, container);
    }

    container.innerHTML = '';
    data.ports.forEach(port => {
        // Convert protocol number to name using FAST_CHARGING_PROTOCOLS
        let protocolName = getProtocolName(port.protocol);

        // 根据功率选择图标
        let powerIcon = 'fa-bolt';
        let powerColor = '#666';
        if (port.power > 0) {
            if (port.power < 10) {
                powerIcon = 'fa-bolt';
                powerColor = '#4CAF50'; // 绿色 - 低功率
            } else if (port.power < 30) {
                powerIcon = 'fa-bolt';
                powerColor = '#FF9800'; // 橙色 - 中功率
            } else if (port.power < 60) {
                powerIcon = 'fa-bolt';
                powerColor = '#FF5722'; // 红色 - 高功率
            } else {
                powerIcon = 'fa-bolt';
                powerColor = '#F44336'; // 深红色 - 超高功率
            }
        }

        const card = document.createElement('div');
        card.className = `port-card ${port.charging ? 'active' : 'inactive'}`;
        card.innerHTML = `
            <div class="port-header">
                <div class="port-title">
                    <i class="fas ${powerIcon}" style="color: ${powerColor}; margin-right: 8px;"></i>
                    端口 ${port.port_id + 1}
                </div>
                <span class="port-status ${port.charging ? 'on' : 'off'}">
                    <i class="fas ${port.charging ? 'fa-plug' : 'fa-power-off'}"></i>
                    ${port.charging ? '充电中' : '未充电'}
                </span>
            </div>
            <div class="port-info">
                <div class="port-info-item">
                    <span class="port-info-label"><i class="fas fa-bolt"></i> 电压</span>
                    <span class="port-info-value" style="color: ${port.voltage > 0 ? '#4CAF50' : '#666'};">${port.voltage.toFixed(2)} V</span>
                </div>
                <div class="port-info-item">
                    <span class="port-info-label"><i class="fas fa-tachometer-alt"></i> 电流</span>
                    <span class="port-info-value" style="color: ${port.current > 0 ? '#2196F3' : '#666'};">${port.current.toFixed(2)} A</span>
                </div>
                <div class="port-info-item">
                    <span class="port-info-label"><i class="fas fa-fire"></i> 功率</span>
                    <span class="port-info-value" style="color: ${powerColor}; font-weight: bold;">${port.power.toFixed(2)} W</span>
                </div>
                <div class="port-info-item">
                    <span class="port-info-label"><i class="fas fa-microchip"></i> 协议</span>
                    <span class="port-info-value">${protocolName}</span>
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    portStatusDiv.classList.remove('hidden');

    // 更新功率曲线（如果功率曲线对话框打开且选择"全部端口"）
    handlePowerStatisticsForCurve(data);
}

function showPortPowerDialog() {
    const content = `
        <div class="form-group">
            <label>端口掩码</label>
            <input type="text" id="port-mask" placeholder="例如: 1, 2, 3, 4, 5 或 31 (0x1F)" value="1">
            <small>可以使用逗号分隔的端口号 (1,2,3,4,5) 或十六进制掩码 (31)</small>
        </div>
        <div class="form-group">
            <label>操作</label>
            <select id="port-action">
                <option value="on">打开端口</option>
                <option value="off">关闭端口</option>
            </select>
        </div>
    `;
    showDialog('端口电源控制', content, 'setPortPower');
}

function setPortPower() {
    const maskInput = document.getElementById('port-mask').value.trim();
    const action = document.getElementById('port-action').value;

    let portMask;
    if (maskInput.includes(',')) {
        // Parse comma-separated ports
        const ports = maskInput.split(',').map(p => parseInt(p.trim()));
        portMask = ports.reduce((acc, p) => acc | (1 << (p - 1)), 0);
    } else {
        // Parse as hex or decimal
        portMask = parseInt(maskInput, 10);
        if (isNaN(portMask)) {
            portMask = parseInt(maskInput, 16);
        }
    }

    if (isNaN(portMask) || portMask < 0 || portMask > 255) {
        showToast('无效的端口掩码', 'error');
        return;
    }

    addLog(`正在${action === 'on' ? '打开' : '关闭'}端口 (掩码: 0x${portMask.toString(16)})...`, 'info');
    sendAction('set_port_power', {
        port_mask: portMask,
        enable: action === 'on'
    });
    closeDialog();
}

function showPortConfigDialog() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="port-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
    `;
    showDialog('端口配置', content, 'getPortConfig');
}

function getPortConfig() {
    const portId = parseInt(document.getElementById('port-id').value);
    addLog(`正在获取端口 ${portId + 1} 配置...`, 'info');
    sendAction('get_port_config', { port_id: portId });
    closeDialog();
}

function handlePortConfig(data) {
    let content = `
        <div class="info-display">
            <div class="info-item">
                <span class="info-label">端口 ID</span>
                <span class="info-value">${data.port_id + 1}</span>
            </div>
            <div class="info-item">
                <span class="info-label">协议特征</span>
                <span class="info-value">0x${data.power_features || 'N/A'}</span>
            </div>
        </div>
        <h4>支持的协议 (勾选启用):</h4>
        <div class="protocol-list">
    `;

    PROTOCOL_NAMES.forEach(protocol => {
        // Check if protocol is in the enabled protocols list
        const enabled = data.protocols && Array.isArray(data.protocols) && data.protocols.includes(protocol);
        content += `
            <div class="protocol-item">
                <input type="checkbox" id="protocol-${protocol.replace(/\s/g, '_')}" ${enabled ? 'checked' : ''}>
                <label for="protocol-${protocol.replace(/\s/g, '_')}">${protocol}</label>
            </div>
        `;
    });

    content += `
        </div>
        <input type="hidden" id="config-port-id" value="${data.port_id}">
        <p style="margin-top: 15px; font-size: 0.9em; color: #64748b;">
            <i class="fas fa-info-circle"></i> 勾选的协议将被启用到设备，取消勾选将被禁用。
        </p>
    `;

    showDialog('端口协议配置', content, 'savePortConfig');
}

function savePortConfig() {
    const portId = parseInt(document.getElementById('config-port-id').value);
    const protocols = {};

    PROTOCOL_NAMES.forEach(protocol => {
        const checkbox = document.getElementById(`protocol-${protocol}`);
        if (checkbox) {
            protocols[protocol] = checkbox.checked;
        }
    });

    addLog(`正在保存端口 ${portId + 1} 配置...`, 'info');
    sendAction('set_port_config', {
        port_mask: 1 << portId,
        protocols: protocols
    });
    closeDialog();
}

function showPortPriorityDialog() {
    // First get current priorities
    addLog('正在获取当前端口优先级...', 'info');
    sendAction('get_port_priority');
}

function handlePortPriority(data) {
    const priorities = data?.priorities || [0, 1, 2, 3, 4];
    const content = `
        <p style="margin-bottom:15px;color:#888;">拖动端口卡片来调整优先级顺序（上方优先级更高）</p>
        <div id="priority-list" style="display:flex;flex-direction:column;gap:8px;">
            ${priorities.map((p, i) => `
                <div class="priority-item" draggable="true" data-port="${i}" style="padding:12px;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;cursor:move;display:flex;align-items:center;gap:10px;">
                    <i class="fas fa-grip-vertical" style="color:#666;"></i>
                    <span style="flex:1;">端口 ${i + 1}</span>
                    <span style="color:#888;font-size:0.9em;">优先级: ${p}</span>
                </div>
            `).join('')}
        </div>
        <script>
            (function() {
                const list = document.getElementById('priority-list');
                let draggedItem = null;
                list.querySelectorAll('.priority-item').forEach(item => {
                    item.addEventListener('dragstart', e => { draggedItem = item; item.style.opacity = '0.5'; });
                    item.addEventListener('dragend', e => { item.style.opacity = '1'; });
                    item.addEventListener('dragover', e => { e.preventDefault(); });
                    item.addEventListener('drop', e => {
                        e.preventDefault();
                        if (draggedItem !== item) {
                            const items = [...list.children];
                            const draggedIdx = items.indexOf(draggedItem);
                            const targetIdx = items.indexOf(item);
                            if (draggedIdx < targetIdx) item.after(draggedItem);
                            else item.before(draggedItem);
                        }
                    });
                });
            })();
        </script>
    `;
    showDialog('端口优先级排序', content, 'savePortPriorities');
}

function savePortPriorities() {
    const list = document.getElementById('priority-list');
    const items = list.querySelectorAll('.priority-item');
    const priorities = [];
    items.forEach((item, idx) => {
        const portId = parseInt(item.dataset.port);
        priorities.push({ port_id: portId, priority: items.length - idx }); // Higher position = higher priority
    });

    addLog('正在保存端口优先级...', 'info');
    priorities.forEach(p => {
        sendAction('set_port_priority', { port_id: p.port_id, priority: p.priority });
    });
    closeDialog();
    showToast('端口优先级已更新', 'success');
}

function setPortPriority() {
    const portId = parseInt(document.getElementById('priority-port-id').value);
    const priority = parseInt(document.getElementById('port-priority').value);

    addLog(`正在设置端口 ${portId + 1} 优先级为 ${priority}...`, 'info');
    sendAction('set_port_priority', {
        port_id: portId,
        priority: priority
    });
    closeDialog();
}

function showProtocolDialog() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="protocol-port-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
        <div class="form-group">
            <label>协议</label>
            <select id="protocol-name">
                ${PROTOCOL_NAMES.map(p => `<option value="${p}">${p}</option>`).join('')}
            </select>
        </div>
        <div class="form-group">
            <label>操作</label>
            <select id="protocol-action">
                <option value="enable">启用</option>
                <option value="disable">禁用</option>
            </select>
        </div>
    `;
    showDialog('协议管理', content, 'manageProtocol');
}

function manageProtocol() {
    const portId = parseInt(document.getElementById('protocol-port-id').value);
    const protocol = document.getElementById('protocol-name').value;
    const action = document.getElementById('protocol-action').value;

    addLog(`正在${action === 'enable' ? '启用' : '禁用'}端口 ${portId + 1} 的 ${protocol} 协议...`, 'info');

    if (action === 'enable') {
        sendAction('enable_protocol', { port_id: portId, protocol: protocol });
    } else {
        sendAction('disable_protocol', { port_id: portId, protocol: protocol });
    }
    closeDialog();
}

// Power Management Functions
function getPowerStatistics() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="stats-port-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
    `;
    showDialog('电源统计', content, 'getPowerStats');
}

function getPowerStats() {
    const portId = parseInt(document.getElementById('stats-port-id').value);
    addLog(`正在获取端口 ${portId + 1} 电源统计...`, 'info');
    sendAction('get_power_statistics', { port_id: portId });
    closeDialog();
}

function handlePowerStatistics(data) {
    // 检查是否需要更新全端口功率曲线
    if (handlePowerStatisticsForCurve(data)) {
        return;
    }

    let content = '<div class="info-display">';

    if (data.voltage !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">端口 ID</span>
                <span class="info-value">${data.port_id + 1}</span>
            </div>
            <div class="info-item">
                <span class="info-label">电压</span>
                <span class="info-value">${data.voltage.toFixed(2)} V</span>
            </div>
            <div class="info-item">
                <span class="info-label">电流</span>
                <span class="info-value">${data.current.toFixed(3)} A</span>
            </div>
            <div class="info-item">
                <span class="info-label">功率</span>
                <span class="info-value">${data.power.toFixed(2)} W</span>
            </div>
        `;
    }

    if (data.temperature !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">温度</span>
                <span class="info-value">${data.temperature}°C</span>
            </div>
        `;
    }

    if (data.raw_data) {
        content += `
            <div class="info-item">
                <span class="info-label">原始数据</span>
                <span class="info-value">${data.raw_data}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('电源统计', content, null);
}

function getChargingStrategy() {
    addLog('正在获取充电策略...', 'info');
    sendAction('get_charging_strategy');
}

function handleChargingStrategy(data) {
    const strategy = data.strategy;
    const strategyName = CHARGING_STRATEGIES[strategy] || `未知 (${strategy})`;

    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">当前策略</span>
            <span class="info-value">${strategyName}</span>
        </div>
        <div class="info-item">
            <span class="info-label">策略值</span>
            <span class="info-value">${strategy}</span>
        </div>
    `;
    content += '</div>';

    showDialog('充电策略', content, null);
}

function showChargingStrategyDialog() {
    let content = '<div class="form-group">';
    content += '<label>充电策略</label>';
    content += '<select id="charging-strategy">';

    for (const [value, name] of Object.entries(CHARGING_STRATEGIES)) {
        content += `<option value="${value}">${name}</option>`;
    }

    content += '</select>';
    content += '</div>';

    showDialog('设置充电策略', content, 'setChargingStrategy');
}

function setChargingStrategy() {
    const strategy = parseInt(document.getElementById('charging-strategy').value);
    const strategyName = CHARGING_STRATEGIES[strategy];

    addLog(`正在设置充电策略为: ${strategyName}...`, 'info');
    sendAction('set_charging_strategy', { strategy: strategy });
    closeDialog();
}

function getChargingStatus() {
    addLog('正在获取充电状态...', 'info');
    sendAction('get_charging_status');
}

function handleChargingStatus(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">充电端口数</span>
            <span class="info-value">${data.num_ports || 0}</span>
        </div>
    `;

    if (data.ports && data.ports.length > 0) {
        content += `
            <div class="info-item">
                <span class="info-label">充电端口</span>
                <span class="info-value">${data.ports.join(', ')}</span>
            </div>
        `;
    }

    if (data.raw_data) {
        content += `
            <div class="info-item">
                <span class="info-label">原始数据</span>
                <span class="info-value">${data.raw_data}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('充电状态', content, null);
}

// WiFi Management Functions
function getWifiStatus() {
    addLog('正在获取 WiFi 状态...', 'info');
    sendAction('get_wifi_status');
}

function handleWifiStatus(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">WiFi 状态</span>
            <span class="info-value">${data.status_name || data.status}</span>
        </div>
    `;

    if (data.ip) {
        content += `
            <div class="info-item">
                <span class="info-label">IP 地址</span>
                <span class="info-value">${data.ip}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('WiFi 状态', content, null);
}

function scanWifi() {
    addLog('正在扫描 WiFi 网络...', 'info');
    sendAction('scan_wifi');
}

function handleWifiScanResult(data) {
    const networks = data.networks || [];
    let content = '<div class="info-display">';

    if (networks.length === 0) {
        content += '<p style="color:#888;">未发现 WiFi 网络</p>';
    } else {
        content += `<p style="margin-bottom:10px;">发现 ${networks.length} 个网络:</p>`;
        content += '<div style="max-height:300px;overflow-y:auto;">';
        networks.forEach(net => {
            const signalStrength = net.rssi > -50 ? '强' : (net.rssi > -70 ? '中' : '弱');
            const signalColor = net.rssi > -50 ? '#4CAF50' : (net.rssi > -70 ? '#FF9800' : '#f44336');
            const authType = net.auth === 0 ? '开放' : '加密';
            const storedIcon = net.stored ? ' <span style="color:#4CAF50;">★</span>' : '';
            content += `
                <div style="padding:8px;margin:4px 0;background:var(--card-bg);border:1px solid var(--border-color);border-radius:6px;cursor:pointer;" onclick="selectWifiNetwork('${net.ssid.replace(/'/g, "\\'")}')">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:500;">${net.ssid}${storedIcon}</span>
                        <span style="color:${signalColor};font-size:0.85em;">${signalStrength} (${net.rssi}dBm)</span>
                    </div>
                    <div style="font-size:0.8em;color:#888;margin-top:4px;">${authType}</div>
                </div>
            `;
        });
        content += '</div>';
    }
    content += '</div>';
    showDialog('WiFi 扫描结果', content, null);
}

function selectWifiNetwork(ssid) {
    closeDialog();
    const content = `
        <div class="form-group">
            <label>WiFi SSID</label>
            <input type="text" id="wifi-ssid" value="${ssid}" readonly>
        </div>
        <div class="form-group">
            <label>WiFi 密码</label>
            <input type="password" id="wifi-password" placeholder="输入 WiFi 密码">
        </div>
    `;
    showDialog('连接 WiFi', content, 'setWifi');
}

function showWifiDialog() {
    const content = `
        <div class="form-group">
            <label>WiFi SSID</label>
            <input type="text" id="wifi-ssid" placeholder="输入 WiFi 名称">
        </div>
        <div class="form-group">
            <label>WiFi 密码</label>
            <input type="password" id="wifi-password" placeholder="输入 WiFi 密码">
        </div>
    `;
    showDialog('设置 WiFi', content, 'setWifi');
}

function setWifi() {
    const ssid = document.getElementById('wifi-ssid').value.trim();
    const password = document.getElementById('wifi-password').value;

    if (!ssid) {
        showToast('请输入 WiFi SSID', 'error');
        return;
    }

    addLog(`正在设置 WiFi: ${ssid}...`, 'info');
    sendAction('set_wifi', { ssid, password });
    closeDialog();
}

// Display Management Functions
function getDisplaySettings() {
    addLog('正在获取显示设置...', 'info');
    sendAction('get_display_settings');
}

function handleDisplaySettings(data) {
    let content = '<div class="info-display">';

    if (data.brightness !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">亮度</span>
                <span class="info-value">${data.brightness}%</span>
            </div>
        `;
    }

    if (data.mode !== undefined) {
        const modeName = DISPLAY_MODES[data.mode] || `未知 (${data.mode})`;
        content += `
            <div class="info-item">
                <span class="info-label">模式</span>
                <span class="info-value">${modeName}</span>
            </div>
        `;
    }

    if (data.flip !== undefined) {
        content += `
            <div class="info-item">
                <span class="info-label">翻转</span>
                <span class="info-value">${data.flip ? '是' : '否'}</span>
            </div>
        `;
    }

    content += '</div>';
    showDialog('显示设置', content, null);
}

function showBrightnessDialog() {
    const content = `
        <div class="form-group">
            <label style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <i class="fas fa-sun" style="color: #FFD700; font-size: 1.2em;"></i>
                <span style="font-weight: 500;">屏幕亮度</span>
                <i class="fas fa-lightbulb" style="color: #FFA500; font-size: 1.2em;"></i>
            </label>
            <div style="position: relative; margin-bottom: 10px;">
                <input type="range" id="display-brightness" min="0" max="100" value="100"
                    style="width: 100%; height: 8px; border-radius: 4px; background: linear-gradient(to right, #333, #4CAF50); outline: none; -webkit-appearance: none;">
                <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.85em; color: #888;">
                    <span><i class="fas fa-moon"></i> 0%</span>
                    <span id="brightness-value" style="font-size: 1.5em; font-weight: bold; color: #4CAF50;">100%</span>
                    <span><i class="fas fa-sun"></i> 100%</span>
                </div>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 15px;">
                <button type="button" class="btn btn-small btn-secondary" onclick="setPresetBrightness(0)">
                    <i class="fas fa-moon"></i> 夜间
                </button>
                <button type="button" class="btn btn-small btn-secondary" onclick="setPresetBrightness(30)">
                    <i class="fas fa-cloud-moon"></i> 暗光
                </button>
                <button type="button" class="btn btn-small btn-secondary" onclick="setPresetBrightness(60)">
                    <i class="fas fa-cloud-sun"></i> 中等
                </button>
                <button type="button" class="btn btn-small btn-secondary" onclick="setPresetBrightness(100)">
                    <i class="fas fa-sun"></i> 明亮
                </button>
            </div>
        </div>
    `;

    showDialog('设置亮度', content, 'setBrightness');

    // Update brightness value display
    const slider = document.getElementById('display-brightness');
    const valueDisplay = document.getElementById('brightness-value');

    // Update brightness value and color
    slider.addEventListener('input', () => {
        const value = parseInt(slider.value);
        valueDisplay.textContent = `${value}%`;

        // Update color based on brightness
        let color = '#666';
        if (value <= 30) {
            color = '#2196F3'; // 蓝色 - 夜间
        } else if (value <= 60) {
            color = '#FF9800'; // 橙色 - 中等
        } else {
            color = '#4CAF50'; // 绿色 - 明亮
        }
        valueDisplay.style.color = color;

        // Update slider gradient
        const percentage = value;
        slider.style.background = `linear-gradient(to right, #4CAF50 ${percentage}%, #333 ${percentage}%)`;
    });
}

function setPresetBrightness(value) {
    const slider = document.getElementById('display-brightness');
    const valueDisplay = document.getElementById('brightness-value');
    if (slider) {
        slider.value = value;
        // Trigger input event to update display
        slider.dispatchEvent(new Event('input'));
    }
}

function setBrightness() {
    const brightness = parseInt(document.getElementById('display-brightness').value);
    addLog(`正在设置亮度为: ${brightness}%...`, 'info');
    sendAction('set_display_brightness', { brightness });
    closeDialog();
}

function showDisplayModeDialog() {
    let content = '<div class="form-group">';
    content += '<label>显示模式</label>';
    content += '<select id="display-mode">';

    for (const [value, name] of Object.entries(DISPLAY_MODES)) {
        content += `<option value="${value}">${name}</option>`;
    }

    content += '</select>';
    content += '</div>';

    showDialog('设置显示模式', content, 'setDisplayMode');
}

function setDisplayMode() {
    const mode = parseInt(document.getElementById('display-mode').value);
    const modeName = DISPLAY_MODES[mode];

    addLog(`正在设置显示模式为: ${modeName}...`, 'info');
    sendAction('set_display_mode', { mode });
    closeDialog();
}

function flipDisplay() {
    addLog('正在翻转显示...', 'info');
    sendAction('flip_display');
}

// System Control Functions
function refreshToken() {
    addLog('正在刷新 Token...', 'info');
    sendAction('refresh_token');
}

function toggleAutoRefresh() {
    const currentStatus = document.getElementById('auto-refresh').textContent;
    const enabled = currentStatus === '禁用';

    addLog(`正在${enabled ? '启用' : '禁用'}自动刷新...`, 'info');
    sendAction('set_auto_refresh', { enabled });
}

function toggleAutoReconnect() {
    const currentStatus = document.getElementById('auto-reconnect').textContent;
    const enabled = currentStatus === '禁用';

    addLog(`正在${enabled ? '启用' : '禁用'}自动重连...`, 'info');
    sendAction('set_auto_reconnect', { enabled });
}

function getSystemInfo() {
    const content = `
        <div class="info-display">
            <div class="info-item">
                <span class="info-label">设备</span>
                <span class="info-value">${document.getElementById('device-name').textContent}</span>
            </div>
            <div class="info-item">
                <span class="info-label">连接状态</span>
                <span class="info-value">${document.getElementById('connection-status').textContent}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Token</span>
                <span class="info-value">${document.getElementById('token-value').textContent}</span>
            </div>
            <div class="info-item">
                <span class="info-label">自动刷新</span>
                <span class="info-value">${document.getElementById('auto-refresh').textContent}</span>
            </div>
            <div class="info-item">
                <span class="info-label">自动重连</span>
                <span class="info-value">${document.getElementById('auto-reconnect').textContent}</span>
            </div>
        </div>
    `;

    showDialog('系统信息', content, null);
}

// Token Management Functions
function showTokenManagement() {
    const currentToken = document.getElementById('token-value').textContent;
    document.getElementById('current-token-display').textContent = currentToken;
    document.getElementById('token-management-dialog').classList.remove('hidden');
}

function closeTokenManagementDialog() {
    document.getElementById('token-management-dialog').classList.add('hidden');
}

function setManualToken() {
    const tokenInput = document.getElementById('manual-token-input');
    const token = parseInt(tokenInput.value);

    if (isNaN(token) || token < 0 || token > 255) {
        showToast('无效的 Token 值 (0-255)', 'error');
        return;
    }

    addLog(`正在设置手动 Token: 0x${token.toString(16).toUpperCase().padStart(2, '0')}...`, 'info');
    sendAction('set_manual_token', { token });
    tokenInput.value = '';
}

function bruteforceToken() {
    if (!confirm('暴力破解 Token 可能需要较长时间，确定要继续吗？')) {
        return;
    }
    addLog('正在暴力破解 Token...', 'info');
    sendAction('manual_bruteforce_token');
}

function loadStoredTokens() {
    addLog('正在获取已存储的 Token...', 'info');
    sendAction('get_stored_tokens');
}

function handleStoredTokens(data) {
    const list = document.getElementById('stored-tokens-list');

    if (!data.tokens || Object.keys(data.tokens).length === 0) {
        list.innerHTML = '<div style="padding: 15px; text-align: center; color: var(--text-muted);">暂无已存储的 Token</div>';
        return;
    }

    let html = '';
    for (const [address, tokenData] of Object.entries(data.tokens)) {
        const lastUsed = new Date(tokenData.last_used * 1000);
        const timeStr = lastUsed.toLocaleString('zh-CN');
        html += `
            <div class="stored-token-item">
                <div>
                    <div class="stored-token-address">${address}</div>
                    <div class="stored-token-time">最后使用: ${timeStr}</div>
                </div>
                <div class="stored-token-value">0x${tokenData.token.toString(16).toUpperCase().padStart(2, '0')}</div>
            </div>
        `;
    }
    list.innerHTML = html;
}

function loadTokenFromStorage() {
    const addressInput = document.getElementById('load-token-address');
    const address = addressInput.value.trim();

    if (!address) {
        showToast('请输入设备地址', 'error');
        return;
    }

    addLog(`正在从存储加载 Token: ${address}...`, 'info');
    sendAction('load_token_from_storage', { address });
    addressInput.value = '';
}

function clearTokenStorage() {
    if (!confirm('确定要清除所有已存储的 Token 吗？此操作不可恢复！')) {
        return;
    }
    addLog('正在清除 Token 存储...', 'info');
    sendAction('clear_token_storage');
}

// Compatibility Mode Functions
function showCompatibilityModesDialog() {
    addLog('正在获取兼容模式列表...', 'info');
    sendAction('get_compatibility_modes');
}

function handleCompatibilityModes(data) {
    const modes = data.modes || {};
    let content = '<div class="info-display">';
    content += '<h4>预定义兼容模式</h4>';

    for (const [modeKey, modeInfo] of Object.entries(modes)) {
        const modeName = modeInfo.name || modeKey;
        const modeDesc = modeInfo.description || '';
        const settings = modeInfo.settings || {};

        content += `
            <div class="compatibility-mode-item" style="margin-bottom: 15px; padding: 10px; background: var(--bg-secondary); border-radius: 8px;">
                <div style="font-weight: bold; color: var(--primary-color);">${modeName}</div>
                <div style="font-size: 0.9em; color: var(--text-muted); margin-bottom: 8px;">${modeDesc}</div>
                <div style="font-size: 0.85em;">
                    <div>TFCP: ${settings.isTfcpEnabled ? '启用' : '禁用'}</div>
                    <div>FCP: ${settings.isFcpEnabled ? '启用' : '禁用'}</div>
                    <div>UFCS: ${settings.isUfcsEnabled ? '启用' : '禁用'}</div>
                    <div>高压SCP: ${settings.isHvScpEnabled ? '启用' : '禁用'}</div>
                    <div>低压SCP: ${settings.isLvScpEnabled ? '启用' : '禁用'}</div>
                </div>
                <button class="btn btn-primary" style="margin-top: 10px; width: 100%;" onclick="setCompatibilityMode('${modeKey}')">应用此模式</button>
            </div>
        `;
    }

    content += '</div>';
    showDialog('协议兼容模式', content, null);
}

function setCompatibilityMode(modeKey) {
    addLog(`正在设置兼容模式: ${modeKey}...`, 'info');
    sendAction('set_compatibility_mode', { mode: modeKey });
}

function showCompatibilitySettingsDialog() {
    addLog('正在获取当前协议兼容设置...', 'info');
    sendAction('get_compatibility_settings');
}

function handleCompatibilitySettings(data) {
    const settings = data.settings || {};

    const content = `
        <div class="form-group">
            <label>启用 TFCP</label>
            <input type="checkbox" id="compat-tfcp" ${settings.isTfcpEnabled ? 'checked' : ''}>
            <small>启用 TFCP 协议（腾讯快充协议）</small>
        </div>
        <div class="form-group">
            <label>启用 FCP</label>
            <input type="checkbox" id="compat-fcp" ${settings.isFcpEnabled ? 'checked' : ''}>
            <small>启用 FCP 协议（华为快充协议）</small>
        </div>
        <div class="form-group">
            <label>启用 UFCS</label>
            <input type="checkbox" id="compat-ufcs" ${settings.isUfcsEnabled ? 'checked' : ''}>
            <small>启用 UFCS 协议（融合快充标准）</small>
        </div>
        <div class="form-group">
            <label>启用高压 SCP</label>
            <input type="checkbox" id="compat-hvscp" ${settings.isHvScpEnabled ? 'checked' : ''}>
            <small>启用高压 SCP 协议（华为超级快充）</small>
        </div>
        <div class="form-group">
            <label>启用低压 SCP</label>
            <input type="checkbox" id="compat-lvscp" ${settings.isLvScpEnabled ? 'checked' : ''}>
            <small>启用低压 SCP 协议（华为超级快充）</small>
        </div>
        <p style="margin-top: 15px; font-size: 0.9em; color: var(--text-muted);">
            <i class="fas fa-info-circle"></i> 勾选的协议将被启用，取消勾选将被禁用。
        </p>
    `;

    showDialog('协议兼容设置', content, 'saveCompatibilitySettings');
}

function saveCompatibilitySettings() {
    const settings = {
        isTfcpEnabled: document.getElementById('compat-tfcp').checked,
        isFcpEnabled: document.getElementById('compat-fcp').checked,
        isUfcsEnabled: document.getElementById('compat-ufcs').checked,
        isHvScpEnabled: document.getElementById('compat-hvscp').checked,
        isLvScpEnabled: document.getElementById('compat-lvscp').checked
    };

    addLog('正在保存协议兼容设置...', 'info');
    sendAction('set_custom_compatibility_settings', { settings });
    closeDialog();
}

// Additional Functions
function showMaxPowerDialog() {
    const content = `
        <div class="form-group">
            <label>最大功率 (0-255)</label>
            <input type="number" id="max-power" min="0" max="255" value="255">
            <small>设置设备的最大功率限制</small>
        </div>
    `;
    showDialog('设置最大功率', content, 'setMaxPower');
}

function setMaxPower() {
    const power = parseInt(document.getElementById('max-power').value);

    if (isNaN(power) || power < 0 || power > 255) {
        showToast('无效的最大功率值', 'error');
        return;
    }

    addLog(`正在设置最大功率为: ${power}...`, 'info');
    sendAction('set_max_power', { power });
    closeDialog();
}

function getMaxPower() {
    addLog('正在获取最大功率...', 'info');
    sendAction('get_max_power');
}

function handleMaxPower(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">最大功率</span>
            <span class="info-value">${data.max_power}</span>
        </div>
    `;
    content += '</div>';
    showDialog('最大功率', content, null);
}

function showPortMaxPowerDialog() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="port-max-power-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
        <div class="form-group">
            <label>最大功率 (0-255)</label>
            <input type="number" id="port-max-power" min="0" max="255" value="255">
            <small>设置端口的最大功率限制</small>
        </div>
    `;
    showDialog('设置端口最大功率', content, 'setPortMaxPower');
}

function setPortMaxPower() {
    const portId = parseInt(document.getElementById('port-max-power-id').value);
    const maxPower = parseInt(document.getElementById('port-max-power').value);

    if (isNaN(maxPower) || maxPower < 0 || maxPower > 255) {
        showToast('无效的最大功率值', 'error');
        return;
    }

    addLog(`正在设置端口 ${portId + 1} 最大功率为: ${maxPower}...`, 'info');
    sendAction('set_port_max_power', { port_id: portId, max_power: maxPower });
    closeDialog();
}

function showGetPortMaxPowerDialog() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="get-port-max-power-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
    `;
    showDialog('获取端口最大功率', content, 'getPortMaxPower');
}

function getPortMaxPower() {
    const portId = parseInt(document.getElementById('get-port-max-power-id').value);
    addLog(`正在获取端口 ${portId + 1} 最大功率...`, 'info');
    sendAction('get_port_max_power', { port_id: portId });
    closeDialog();
}

function handlePortMaxPower(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">端口 ID</span>
            <span class="info-value">${data.port_id + 1}</span>
        </div>
        <div class="info-item">
            <span class="info-label">最大功率</span>
            <span class="info-value">${data.max_power}</span>
        </div>
    `;
    content += '</div>';
    showDialog('端口最大功率', content, null);
}

function showGetPortTemperatureDialog() {
    const content = `
        <div class="form-group">
            <label>端口 ID</label>
            <select id="temp-port-id">
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
    `;
    showDialog('获取端口温度', content, 'getPortTemperature');
}

function getPortTemperature() {
    const portId = parseInt(document.getElementById('temp-port-id').value);
    addLog(`正在获取端口 ${portId + 1} 温度...`, 'info');
    sendAction('get_port_temperature', { port_id: portId });
    closeDialog();
}

function handlePortTemperature(data) {
    // 先尝试更新温度曲线
    if (handlePortTemperatureForCurve(data)) {
        return; // 温度曲线对话框打开时，不显示弹窗
    }

    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">端口 ID</span>
            <span class="info-value">${data.port_id + 1}</span>
        </div>
        <div class="info-item">
            <span class="info-label">温度</span>
            <span class="info-value">${data.temperature}°C</span>
        </div>
    `;
    content += '</div>';
    showDialog('端口温度', content, null);
}

function showNightModeDialog() {
    const content = `
        <div class="form-group">
            <label>启用夜间模式</label>
            <select id="night-mode-enabled">
                <option value="true">启用</option>
                <option value="false">禁用</option>
            </select>
        </div>
        <div class="form-group">
            <label>开始时间 (小时)</label>
            <input type="number" id="night-start-hour" min="0" max="23" value="22">
        </div>
        <div class="form-group">
            <label>开始时间 (分钟)</label>
            <input type="number" id="night-start-minute" min="0" max="59" value="0">
        </div>
        <div class="form-group">
            <label>结束时间 (小时)</label>
            <input type="number" id="night-end-hour" min="0" max="23" value="7">
        </div>
        <div class="form-group">
            <label>结束时间 (分钟)</label>
            <input type="number" id="night-end-minute" min="0" max="59" value="0">
        </div>
    `;
    showDialog('设置夜间模式', content, 'setNightMode');
}

function setNightMode() {
    const enabled = document.getElementById('night-mode-enabled').value === 'true';
    const startHour = parseInt(document.getElementById('night-start-hour').value);
    const startMinute = parseInt(document.getElementById('night-start-minute').value);
    const endHour = parseInt(document.getElementById('night-end-hour').value);
    const endMinute = parseInt(document.getElementById('night-end-minute').value);

    addLog(`正在设置夜间模式...`, 'info');
    sendAction('set_night_mode', {
        enabled: enabled,
        start_hour: startHour,
        start_minute: startMinute,
        end_hour: endHour,
        end_minute: endMinute
    });
    closeDialog();
}

function getNightMode() {
    addLog('正在获取夜间模式设置...', 'info');
    sendAction('get_night_mode');
}

function handleNightMode(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">夜间模式</span>
            <span class="info-value">${data.enabled ? '启用' : '禁用'}</span>
        </div>
        <div class="info-item">
            <span class="info-label">开始时间</span>
            <span class="info-value">${data.start_hour.toString().padStart(2, '0')}:${data.start_minute.toString().padStart(2, '0')}</span>
        </div>
        <div class="info-item">
            <span class="info-label">结束时间</span>
            <span class="info-value">${data.end_hour.toString().padStart(2, '0')}:${data.end_minute.toString().padStart(2, '0')}</span>
        </div>
    `;
    content += '</div>';
    showDialog('夜间模式', content, null);
}

function showLanguageDialog() {
    const content = `
        <div class="form-group">
            <label>语言</label>
            <select id="language">
                <option value="0">中文</option>
                <option value="1">English</option>
                <option value="2">日本語</option>
                <option value="3">한국어</option>
            </select>
        </div>
    `;
    showDialog('设置语言', content, 'setLanguage');
}

function setLanguage() {
    const language = parseInt(document.getElementById('language').value);
    addLog(`正在设置语言...`, 'info');
    sendAction('set_language', { language });
    closeDialog();
}

function getLanguage() {
    addLog('正在获取语言设置...', 'info');
    sendAction('get_language');
}

function handleLanguage(data) {
    const languageNames = ['中文', 'English', '日本語', '한국어'];
    const languageName = languageNames[data.language] || `未知 (${data.language})`;

    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">当前语言</span>
            <span class="info-value">${languageName}</span>
        </div>
    `;
    content += '</div>';
    showDialog('语言设置', content, null);
}

function showLedModeDialog() {
    const content = `
        <div class="form-group">
            <label>LED 模式</label>
            <select id="led-mode">
                <option value="0">默认</option>
                <option value="1">呼吸灯</option>
                <option value="2">常亮</option>
                <option value="3">关闭</option>
            </select>
        </div>
    `;
    showDialog('设置 LED 模式', content, 'setLedMode');
}

function setLedMode() {
    const mode = parseInt(document.getElementById('led-mode').value);
    addLog(`正在设置 LED 模式...`, 'info');
    sendAction('set_led_mode', { mode });
    closeDialog();
}

// Advanced Functions
let cableInfoData = {};

function showPortPDStatusDialog() {
    // Show expanded view for all 4 ports
    addLog('正在获取所有端口充电线信息...', 'info');
    cableInfoData = {};
    for (let i = 0; i < 5; i++) {
        sendAction('get_port_pd_status', { port_id: i });
    }

    // Show dialog with placeholder
    const content = `
        <div style="margin-bottom:10px;">
            <button id="cable-info-refresh-btn" class="btn btn-success btn-small" onclick="toggleCableInfoAutoRefresh()">
                <i class="fas fa-play"></i> 开启自动刷新
            </button>
        </div>
        <div id="cable-info-container">
            <p style="color:#888;">正在加载...</p>
        </div>
    `;
    showDialog('充电线信息 (全部端口)', content, null);
}

function toggleCableInfoAutoRefresh() {
    const btn = document.getElementById('cable-info-refresh-btn');
    if (cableInfoRefreshTimer) {
        clearInterval(cableInfoRefreshTimer);
        cableInfoRefreshTimer = null;
        btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
        addLog('充电线信息自动刷新已关闭', 'info');
    } else {
        cableInfoRefreshTimer = setInterval(() => {
            for (let i = 0; i < 5; i++) {
                sendAction('get_port_pd_status', { port_id: i });
            }
        }, REFRESH_INTERVAL);
        btn.innerHTML = '<i class="fas fa-stop"></i> 关闭自动刷新';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
        addLog('充电线信息自动刷新已开启', 'info');
    }
}

function getPortPDStatus() {
    const portId = parseInt(document.getElementById('pd-status-port-id')?.value || 0);
    addLog(`正在获取端口 ${portId} 的PD状态...`, 'info');
    sendAction('get_port_pd_status', { port_id: portId });
    closeDialog();
}

function handlePortPDStatus(data) {
    const pd = data || {};
    const container = document.getElementById('cable-info-container');

    // If container exists, update expanded view
    if (container) {
        // Use port_id from response data
        const portIdx = pd.port_id !== undefined ? pd.port_id : Object.keys(cableInfoData).length;
        cableInfoData[portIdx] = pd;

        // Render when we have data (don't wait for all 4)
        renderCableInfoExpanded();
        return;
    }

    // Fallback: show single port dialog
    let content = '<div class="info-display">';

    // Battery Info
    if (pd.battery) {
        content += `
            <h3>电池信息</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">电池VID</span>
                    <span class="info-value">${pd.battery.vid}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">电池PID</span>
                    <span class="info-value">${pd.battery.pid}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">设计容量</span>
                    <span class="info-value">${pd.battery.design_capacity} Wh</span>
                </div>
                <div class="info-item">
                    <span class="info-label">上次充满容量</span>
                    <span class="info-value">${pd.battery.last_full_capacity} Wh</span>
                </div>
                <div class="info-item">
                    <span class="info-label">当前容量</span>
                    <span class="info-value">${pd.battery.present_capacity} Wh</span>
                </div>
                <div class="info-item">
                    <span class="info-label">电池状态</span>
                    <span class="info-value">${pd.battery.status_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">电池存在</span>
                    <span class="info-value">${pd.battery.present ? '是' : '否'}</span>
                </div>
            </div>
        `;
    }

    // Cable Info
    if (pd.cable) {
        content += `
            <h3>线缆信息</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">线缆VID</span>
                    <span class="info-value">${pd.cable.vid}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">线缆PID</span>
                    <span class="info-value">${pd.cable.pid}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">物理类型</span>
                    <span class="info-value">${pd.cable.phy_type}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">线缆长度</span>
                    <span class="info-value">${pd.cable.length}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">最大电压</span>
                    <span class="info-value">${pd.cable.max_voltage}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">最大电流</span>
                    <span class="info-value">${pd.cable.max_current}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">USB速度</span>
                    <span class="info-value">${pd.cable.usb_speed}</span>
                </div>
            </div>
        `;
    }

    // Operating Info
    if (pd.operating) {
        content += `
            <h3>运行信息</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">当前电压</span>
                    <span class="info-value">${pd.operating.voltage} V</span>
                </div>
                <div class="info-item">
                    <span class="info-label">当前电流</span>
                    <span class="info-value">${pd.operating.current} A</span>
                </div>
                <div class="info-item">
                    <span class="info-label">当前功率</span>
                    <span class="info-value">${pd.operating.power} W</span>
                </div>
                <div class="info-item">
                    <span class="info-label">PD版本</span>
                    <span class="info-value">${pd.operating.pd_revision}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">PPS充电支持</span>
                    <span class="info-value">${pd.operating.pps_charging_supported ? '是' : '否'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">有电池</span>
                    <span class="info-value">${pd.operating.has_battery ? '是' : '否'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">有eMarker</span>
                    <span class="info-value">${pd.operating.has_emarker ? '是' : '否'}</span>
                </div>
            </div>
        `;
    }

    // Status Temperature
    if (pd.status && pd.status.temperature !== undefined) {
        content += `
            <h3>状态温度</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">温度</span>
                    <span class="info-value">${pd.status.temperature} °C</span>
                </div>
            </div>
        `;
    }

    content += '</div>';
    showDialog('充电线信息', content, null);
}

function renderCableInfoExpanded() {
    const container = document.getElementById('cable-info-container');
    if (!container) return;

    let html = '';
    for (let i = 0; i < 5; i++) {
        const pd = cableInfoData[i] || {};
        const hasData = pd.operating || pd.cable || pd.battery;

        // Calculate battery percentage and remaining time
        let batteryInfo = '';
        if (pd.battery && pd.battery.last_full_capacity > 0) {
            const percent = Math.min(100, Math.round((pd.battery.present_capacity / pd.battery.last_full_capacity) * 100));
            batteryInfo += `<div><span style="color:#888;">电量:</span> ${percent}%</div>`;

            // Estimate remaining time if charging
            if (pd.operating && pd.operating.power > 0 && percent < 100) {
                const remaining = pd.battery.last_full_capacity - pd.battery.present_capacity;
                const hours = remaining / pd.operating.power;
                if (hours < 1) {
                    batteryInfo += `<div><span style="color:#888;">预计充满:</span> ${Math.round(hours * 60)} 分钟</div>`;
                } else {
                    batteryInfo += `<div><span style="color:#888;">预计充满:</span> ${hours.toFixed(1)} 小时</div>`;
                }
            }
        }

        // Build cable info HTML
        let cableInfoHtml = '';
        if (pd.cable) {
            cableInfoHtml = `
                <div><span style="color:#888;">线缆VID:</span> ${pd.cable.vid || '-'}</div>
                <div><span style="color:#888;">线缆PID:</span> ${pd.cable.pid || '-'}</div>
                <div><span style="color:#888;">物理类型:</span> ${pd.cable.phy_type || '-'}</div>
                <div><span style="color:#888;">线缆长度:</span> ${pd.cable.length || '-'}</div>
                <div><span style="color:#888;">最大电压:</span> ${pd.cable.max_voltage || '-'}</div>
                <div><span style="color:#888;">最大电流:</span> ${pd.cable.max_current || '-'}</div>
                <div><span style="color:#888;">USB速度:</span> ${pd.cable.usb_speed || '-'}</div>
            `;
        }

        // 使用portStatusData来获取准确的电压/电流/功率数据
        // 因为get_port_pd_status的operating数据可能不准确
        let voltage = 0, current = 0, power = 0;
        if (window.portStatusData && window.portStatusData.ports) {
            const portData = window.portStatusData.ports.find(p => p.port_id === i);
            if (portData) {
                voltage = portData.voltage || 0;
                current = portData.current || 0;
                power = portData.power || 0;
            }
        }

        html += `
            <div style="margin-bottom:15px;padding:12px;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;">
                <h4 style="margin:0 0 10px 0;color:var(--primary-color);">端口 ${i + 1}</h4>
                ${hasData ? `
                    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;font-size:0.9em;">
                        <div><span style="color:#888;">电压:</span> ${voltage.toFixed(2)} V</div>
                        <div><span style="color:#888;">电流:</span> ${current.toFixed(2)} A</div>
                        <div><span style="color:#888;">功率:</span> ${power.toFixed(2)} W</div>
                        <div><span style="color:#888;">PD版本:</span> ${pd.operating?.pd_revision || '-'}</div>
                        ${batteryInfo}
                        ${cableInfoHtml}
                        ${pd.status ? `
                            <div><span style="color:#888;">温度:</span> ${pd.status.temperature || 0} °C</div>
                        ` : ''}
                    </div>
                ` : '<p style="color:#666;margin:0;">无数据</p>'}
            </div>
        `;
    }
    container.innerHTML = html;
}

function showPowerCurveDialog() {
    const content = `
        <div class="form-group">
            <label>选择端口</label>
            <select id="power-curve-port-id">
                <option value="all">全部端口</option>
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
        <div style="margin-top:10px;">
            <button id="power-curve-refresh-btn" class="btn btn-success btn-small" onclick="togglePowerCurveAutoRefresh()">
                <i class="fas fa-play"></i> 开启自动刷新
            </button>
        </div>
        <canvas id="power-chart" width="500" height="250" style="margin-top:15px;background:#1a1a2e;border-radius:8px;"></canvas>
        <div id="power-chart-legend" style="margin-top:10px;display:flex;gap:15px;font-size:0.85em;flex-wrap:wrap;"></div>
    `;
    showDialog('功率曲线', content, null);
    updatePowerChartLegend();
    // Initial fetch
    setTimeout(() => {
        fetchPowerCurveData();
    }, 100);
}

// 更新功率图例
function updatePowerChartLegend() {
    const legend = document.getElementById('power-chart-legend');
    if (!legend) return;
    const portSelect = document.getElementById('power-curve-port-id');
    const selectedPort = portSelect?.value;
    if (selectedPort === 'all') {
        legend.innerHTML = `
            <span><span style="color:#f44336;">●</span> 端口1</span>
            <span><span style="color:#FF9800;">●</span> 端口2</span>
            <span><span style="color:#4CAF50;">●</span> 端口3</span>
            <span><span style="color:#2196F3;">●</span> 端口4</span>
            <span><span style="color:#9C27B0;">●</span> 端口5</span>
        `;
    } else {
        legend.innerHTML = `
            <span><span style="color:#4CAF50;">●</span> 功率(W)</span>
            <span><span style="color:#2196F3;">●</span> 电压(V)</span>
            <span><span style="color:#FF9800;">●</span> 电流(A)</span>
        `;
    }
}

let powerCurveData = [];
let powerCurveHistory = []; // 历史数据用于滚动显示
let allPortsPowerHistory = [{}, {}, {}, {}, {}]; // 全端口功率历史
const MAX_POWER_CURVE_POINTS = 60; // 最多显示60个数据点

// 获取功率曲线数据
function fetchPowerCurveData() {
    const portSelect = document.getElementById('power-curve-port-id');
    if (!portSelect) return;
    const portVal = portSelect.value;

    // 当切换端口选择器时，清空所有历史数据
    if (portVal !== lastPortSelectValue) {
        console.log(`[POWER_CURVE] Port selection changed from ${lastPortSelectValue} to ${portVal}, clearing history`);
        lastPortSelectValue = portVal;
        // 清空所有历史数据
        allPortsPowerHistory = [{}, {}, {}, {}, {}];
        powerCurveHistory = [];

        // 清空画布
        const canvas = document.getElementById('power-chart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
    }

    if (portVal === 'all') {
        // 获取所有端口的当前功率数据（用于实时功率曲线）
        sendAction('get_port_status');
    } else {
        // 获取单个端口的历史数据（用于历史功率曲线曲线）
        sendAction('get_power_historical_stats', { port_id: parseInt(portVal), offset: 0 });
    }
}

function togglePowerCurveAutoRefresh() {
    const btn = document.getElementById('power-curve-refresh-btn');
    if (powerCurveRefreshTimer) {
        clearInterval(powerCurveRefreshTimer);
        powerCurveRefreshTimer = null;
        btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
        addLog('功率曲线自动刷新已关闭', 'info');
    } else {
        // 开启时重置历史数据
        powerCurveHistory = [];
        allPortsPowerHistory = [{}, {}, {}, {}, {}];
        updatePowerChartLegend();
        powerCurveRefreshTimer = setInterval(fetchPowerCurveData, REFRESH_INTERVAL);
        btn.innerHTML = '<i class="fas fa-stop"></i> 关闭自动刷新';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
        addLog('功率曲线自动刷新已开启', 'info');
    }
}

function getPowerCurve() {
    const portId = parseInt(document.getElementById('power-curve-port-id')?.value || 0);
    const offset = parseInt(document.getElementById('power-curve-offset')?.value || 0);
    addLog(`正在获取端口 ${portId} 的功率曲线...`, 'info');
    sendAction('get_power_historical_stats', { port_id: portId, offset: offset });
    closeDialog();
}

function handlePowerCurve(data) {
    const stats = data || {};
    const statList = stats.stats || [];
    const canvas = document.getElementById('power-chart');

    // If canvas exists, draw chart with scrolling
    if (canvas) {
        // 如果自动刷新开启，追加新数据实现滚动效果
        if (powerCurveRefreshTimer) {
            // 对于"全部端口"模式，使用handlePowerStatisticsForCurve处理
            const portSelect = document.getElementById('power-curve-port-id');
            if (portSelect && portSelect.value === 'all') {
                // 由handlePowerStatisticsForCurve处理，这里不处理
                return;
            }

            // 单端口模式：追加新数据实现滚动效果
            if (statList.length > 0) {
                const latestPoint = statList[0];
                latestPoint.timestamp = Date.now();
                powerCurveHistory.push(latestPoint);

                // 保持最大数据点数量
                while (powerCurveHistory.length > MAX_POWER_CURVE_POINTS) {
                    powerCurveHistory.shift();
                }

                drawPowerChart(canvas, powerCurveHistory);
            }
        } else {
            // 非自动刷新模式，直接显示返回的数据
            powerCurveData = statList;
            drawPowerChart(canvas, statList);
        }
        return;
    }

    // Fallback: show table
    let content = '<div class="info-display">';
    content += `<h3>端口 ${stats.port_id || 0} 功率曲线</h3>`;

    if (statList.length === 0) {
        content += '<p>暂无历史数据</p>';
    } else {
        content += '<table class="data-table">';
        content += '<thead><tr><th>索引</th><th>电压(V)</th><th>电流(A)</th><th>功率(W)</th><th>温度(°C)</th></tr></thead>';
        content += '<tbody>';
        statList.forEach(stat => {
            content += `<tr><td>${stat.index}</td><td>${stat.voltage}</td><td>${stat.current}</td><td>${stat.power}</td><td>${stat.temperature}</td></tr>`;
        });
        content += '</tbody></table>';
    }
    content += '</div>';
    showDialog('功率曲线', content, null);
}

function drawPowerChart(canvas, data) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };

    // Clear
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, w, h);

    if (!data || data.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('暂无数据', w / 2, h / 2);
        return;
    }

    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    // Find max values with smart scaling
    let maxPower = Math.max(...data.map(d => d.power || 0));
    // 智能Y轴刻度：向上取整到合适的刻度
    if (maxPower <= 0) maxPower = 10;
    else if (maxPower <= 10) maxPower = Math.ceil(maxPower / 2) * 2 || 2;
    else if (maxPower <= 50) maxPower = Math.ceil(maxPower / 10) * 10;
    else if (maxPower <= 100) maxPower = Math.ceil(maxPower / 20) * 20;
    else maxPower = Math.ceil(maxPower / 50) * 50;

    // 确保至少有10W的刻度范围
    if (maxPower < 10) maxPower = 10;

    const maxVoltage = Math.max(...data.map(d => d.voltage || 0), 1);
    const maxCurrent = Math.max(...data.map(d => d.current || 0), 1);

    // Draw grid
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(w - padding.right, y);
        ctx.stroke();
    }

    // Draw lines with animation
    const drawLine = (values, color, maxVal) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        values.forEach((v, i) => {
            const x = padding.left + (i / (values.length - 1 || 1)) * chartW;
            const y = padding.top + chartH - (v / maxVal) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    };

    drawLine(data.map(d => d.power || 0), '#4CAF50', maxPower);
    drawLine(data.map(d => d.voltage || 0), '#2196F3', maxVoltage);
    drawLine(data.map(d => d.current || 0), '#FF9800', maxCurrent);

    // Y-axis labels
    ctx.fillStyle = '#888';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        const val = Math.round(maxPower * (4 - i) / 4);
        ctx.fillText(val + 'W', padding.left - 5, y + 3);
    }

    // X-axis time labels (显示相对时间)
    ctx.textAlign = 'center';
    const totalSeconds = data.length * 2; // 每个点约2秒
    for (let i = 0; i <= 4; i++) {
        const x = padding.left + (i / 4) * chartW;
        const secondsAgo = Math.round(totalSeconds * (1 - i / 4));
        const label = secondsAgo === 0 ? '现在' : `-${secondsAgo}s`;
        ctx.fillText(label, x, h - 5);
    }
}

// 处理全端口功率曲线数据
function handlePowerStatisticsForCurve(data) {
    const canvas = document.getElementById('power-chart');
    const portSelect = document.getElementById('power-curve-port-id');
    if (!canvas || !portSelect || portSelect.value !== 'all') return false;

    // 检查是否是 get_port_status 的响应格式（包含 ports 数组）
    if (data.ports && Array.isArray(data.ports)) {
        // 处理 get_port_status 的响应格式
        console.log(`[POWER_CURVE] Received get_port_status response with ${data.ports.length} ports`);

        data.ports.forEach(port => {
            const portId = port.port_id;
            if (portId >= 0 && portId < 5) {
                const power = port.power || 0;
                const ts = Date.now();
                allPortsPowerHistory[portId][ts] = power;
                console.log(`[POWER_CURVE] Port ${portId} power: ${power}W, voltage: ${port.voltage}V, current: ${port.current}A`);
            }
        });

        // 清理旧数据
        const ts = Date.now();
        const cutoff = ts - MAX_POWER_CURVE_POINTS * REFRESH_INTERVAL;
        for (let i = 0; i < 5; i++) {
            for (const key of Object.keys(allPortsPowerHistory[i])) {
                if (parseInt(key) < cutoff) delete allPortsPowerHistory[i][key];
            }
        }

        drawAllPortsPowerChart(canvas);
        return true;
    } else if (data.port_id !== undefined) {
        // 处理 get_power_statistics 的响应格式
        const portId = data.port_id;
        if (portId === undefined || portId < 0 || portId >= 5) return false;

        // 调试日志：记录功率值
        console.log(`[POWER_CURVE] Port ${portId} power: ${data.power}, voltage: ${data.voltage}, current: ${data.current}`);

        const ts = Date.now();
        allPortsPowerHistory[portId][ts] = data.power || 0;

        // 清理旧数据
        const cutoff = ts - MAX_POWER_CURVE_POINTS * REFRESH_INTERVAL;
        for (let i = 0; i < 5; i++) {
            for (const key of Object.keys(allPortsPowerHistory[i])) {
                if (parseInt(key) < cutoff) delete allPortsPowerHistory[i][key];
            }
        }

        drawAllPortsPowerChart(canvas);
        return true;
    }

    // 不支持的格式
    console.log(`[POWER_CURVE] Unsupported data format:`, data);
    return false;
}

function drawAllPortsPowerChart(canvas) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };

    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, w, h);

    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;
    const colors = ['#f44336', '#FF9800', '#4CAF50', '#2196F3', '#9C27B0'];

    // 收集所有时间戳和功率值
    let allTimestamps = new Set();
    let maxPower = 0;
    for (let i = 0; i < 5; i++) {
        for (const [ts, power] of Object.entries(allPortsPowerHistory[i])) {
            allTimestamps.add(parseInt(ts));
            if (power > maxPower) maxPower = power;
        }
    }

    // 调试日志：显示最大功率值
    console.log(`[DRAW_ALL_PORTS] maxPower before scaling: ${maxPower}`);
    console.log(`[DRAW_ALL_PORTS] allPortsPowerHistory:`, allPortsPowerHistory);

    // 智能Y轴刻度（与drawPowerChart保持一致）
    if (maxPower <= 0) maxPower = 10;
    else if (maxPower <= 10) maxPower = Math.ceil(maxPower / 2) * 2 || 2;
    else if (maxPower <= 50) maxPower = Math.ceil(maxPower / 10) * 10;
    else if (maxPower <= 100) maxPower = Math.ceil(maxPower / 20) * 20;
    else maxPower = Math.ceil(maxPower / 50) * 50;

    console.log(`[DRAW_ALL_PORTS] maxPower after scaling: ${maxPower}`);

    // 确保至少有10W的刻度范围
    if (maxPower < 10) maxPower = 10;

    const timestamps = Array.from(allTimestamps).sort((a, b) => a - b);
    if (timestamps.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('暂无数据', w / 2, h / 2);
        return;
    }

    const minTs = timestamps[0], maxTs = timestamps[timestamps.length - 1];
    const tsRange = maxTs - minTs || 1;

    // 画网格
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(w - padding.right, y);
        ctx.stroke();
    }

    // 画每个端口的功率线
    for (let portIdx = 0; portIdx < 5; portIdx++) {
        const portData = allPortsPowerHistory[portIdx];
        const sortedTs = Object.keys(portData).map(Number).sort((a, b) => a - b);
        if (sortedTs.length < 2) continue;

        ctx.strokeStyle = colors[portIdx];
        ctx.lineWidth = 2;
        ctx.beginPath();
        sortedTs.forEach((ts, i) => {
            const x = padding.left + ((ts - minTs) / tsRange) * chartW;
            const y = padding.top + chartH - (portData[ts] / maxPower) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }

    // Y轴标签
    ctx.fillStyle = '#888';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        const val = Math.round(maxPower * (4 - i) / 4);
        ctx.fillText(val + 'W', padding.left - 5, y + 3);
    }
}

// ============ 温度曲线功能 ============
let temperatureCurveHistory = [];
let temperatureCurveRefreshTimer = null;
const MAX_TEMP_CURVE_POINTS = 60;

function showTemperatureCurveDialog() {
    const content = `
        <div class="form-group">
            <label>选择端口</label>
            <select id="temp-curve-port-id">
                <option value="all">全部端口</option>
                <option value="0">端口 1</option>
                <option value="1">端口 2</option>
                <option value="2">端口 3</option>
                <option value="3">端口 4</option>
                <option value="4">端口 5</option>
            </select>
        </div>
        <div style="margin-top:10px;">
            <button id="temp-curve-refresh-btn" class="btn btn-success btn-small" onclick="toggleTempCurveAutoRefresh()">
                <i class="fas fa-play"></i> 开启自动刷新
            </button>
        </div>
        <canvas id="temp-chart" width="500" height="250" style="margin-top:15px;background:#1a1a2e;border-radius:8px;"></canvas>
        <div id="temp-chart-legend" style="margin-top:10px;display:flex;gap:15px;font-size:0.85em;">
            <span><span style="color:#f44336;">●</span> 端口1</span>
            <span><span style="color:#FF9800;">●</span> 端口2</span>
            <span><span style="color:#4CAF50;">●</span> 端口3</span>
            <span><span style="color:#2196F3;">●</span> 端口4</span>
            <span><span style="color:#9C27B0;">●</span> 端口5</span>
        </div>
    `;
    showDialog('温度曲线', content, null);
    temperatureCurveHistory = [{}, {}, {}, {}, {}];
    fetchTemperatureData();
}

function toggleTempCurveAutoRefresh() {
    const btn = document.getElementById('temp-curve-refresh-btn');
    if (temperatureCurveRefreshTimer) {
        clearInterval(temperatureCurveRefreshTimer);
        temperatureCurveRefreshTimer = null;
        btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
        addLog('温度曲线自动刷新已关闭', 'info');
    } else {
        temperatureCurveHistory = [{}, {}, {}, {}, {}];
        temperatureCurveRefreshTimer = setInterval(fetchTemperatureData, REFRESH_INTERVAL);
        btn.innerHTML = '<i class="fas fa-stop"></i> 关闭自动刷新';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
        addLog('温度曲线自动刷新已开启', 'info');
    }
}

function fetchTemperatureData() {
    const portSelect = document.getElementById('temp-curve-port-id');
    if (!portSelect) return;
    const portVal = portSelect.value;
    if (portVal === 'all') {
        for (let i = 0; i < 5; i++) {
            sendAction('get_port_temperature', { port_id: i });
        }
    } else {
        sendAction('get_port_temperature', { port_id: parseInt(portVal) });
    }
}

function handlePortTemperatureForCurve(data) {
    const canvas = document.getElementById('temp-chart');
    if (!canvas) return false;

    const portId = data.port_id || 0;
    const temp = data.temperature || 0;
    const now = Date.now();

    if (!temperatureCurveHistory[portId]) temperatureCurveHistory[portId] = {};
    temperatureCurveHistory[portId][now] = temp;

    // 清理旧数据
    const cutoff = now - MAX_TEMP_CURVE_POINTS * REFRESH_INTERVAL;
    for (let i = 0; i < 5; i++) {
        if (temperatureCurveHistory[i]) {
            for (const ts of Object.keys(temperatureCurveHistory[i])) {
                if (parseInt(ts) < cutoff) delete temperatureCurveHistory[i][ts];
            }
        }
    }

    drawTemperatureChart(canvas);
    return true;
}

function drawTemperatureChart(canvas) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };

    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, w, h);

    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;
    const colors = ['#f44336', '#FF9800', '#4CAF50', '#2196F3', '#9C27B0'];

    // 收集所有时间戳和温度值
    let allTimestamps = new Set();
    let maxTemp = 50;
    for (let i = 0; i < 5; i++) {
        if (temperatureCurveHistory[i]) {
            for (const [ts, temp] of Object.entries(temperatureCurveHistory[i])) {
                allTimestamps.add(parseInt(ts));
                if (temp > maxTemp) maxTemp = temp;
            }
        }
    }

    const timestamps = Array.from(allTimestamps).sort((a, b) => a - b);
    if (timestamps.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('暂无数据', w / 2, h / 2);
        return;
    }

    const minTs = timestamps[0], maxTs = timestamps[timestamps.length - 1];
    const tsRange = maxTs - minTs || 1;

    // 画网格
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(w - padding.right, y);
        ctx.stroke();
    }

    // 画每个端口的温度线
    const portSelect = document.getElementById('temp-curve-port-id');
    const selectedPort = portSelect?.value;

    for (let portId = 0; portId < 5; portId++) {
        if (selectedPort !== 'all' && portId !== parseInt(selectedPort)) continue;
        if (!temperatureCurveHistory[portId]) continue;

        const entries = Object.entries(temperatureCurveHistory[portId]).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
        if (entries.length < 2) continue;

        ctx.strokeStyle = colors[portId];
        ctx.lineWidth = 2;
        ctx.beginPath();
        entries.forEach(([ts, temp], idx) => {
            const x = padding.left + ((parseInt(ts) - minTs) / tsRange) * chartW;
            const y = padding.top + chartH - (temp / maxTemp) * chartH;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }

    // Y轴标签
    ctx.fillStyle = '#888';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i;
        const val = Math.round(maxTemp * (4 - i) / 4);
        ctx.fillText(val + '°C', padding.left - 5, y + 3);
    }

    // X轴时间标签
    ctx.textAlign = 'center';
    const totalSeconds = Math.round(tsRange / 1000);
    for (let i = 0; i <= 4; i++) {
        const x = padding.left + (i / 4) * chartW;
        const secondsAgo = Math.round(totalSeconds * (1 - i / 4));
        const label = secondsAgo === 0 ? '现在' : `-${secondsAgo}s`;
        ctx.fillText(label, x, h - 5);
    }
}

let chargingSessionData = {};

function showChargingSessionDialog() {
    // Fetch all 4 ports
    addLog('正在获取所有端口充电会话...', 'info');
    chargingSessionData = {};
    for (let i = 0; i < 5; i++) {
        sendAction('get_start_charge_timestamp', { port_id: i });
    }

    const content = `
        <div id="charging-session-container">
            <p style="color:#888;">正在加载...</p>
        </div>
    `;
    showDialog('充电会话 (全部端口)', content, null);
}

function getChargingSession() {
    const portId = parseInt(document.getElementById('charging-session-port-id')?.value || 0);
    addLog(`正在获取端口 ${portId} 的充电会话...`, 'info');
    sendAction('get_start_charge_timestamp', { port_id: portId });
    closeDialog();
}

function handleChargingSession(data) {
    const container = document.getElementById('charging-session-container');

    // If container exists, update expanded view
    if (container) {
        const portIdx = Object.keys(chargingSessionData).length;
        if (portIdx < 5) {
            chargingSessionData[portIdx] = data;
        }

        // Render all ports when we have data
        if (Object.keys(chargingSessionData).length >= 5 || !container.innerHTML.includes('正在加载')) {
            renderChargingSessionExpanded();
        }
        return;
    }

    // Fallback: single port dialog
    const timestamp = data?.timestamp || 0;
    const date = new Date(timestamp * 1000);

    let content = '<div class="info-display">';
    content += `<h3>开始充电时间</h3>`;
    content += `
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">时间戳</span>
                <span class="info-value">${timestamp}</span>
            </div>
            <div class="info-item">
                <span class="info-label">日期时间</span>
                <span class="info-value">${date.toLocaleString('zh-CN')}</span>
            </div>
        </div>
    `;
    content += '</div>';
    showDialog('充电会话', content, null);
}

function renderChargingSessionExpanded() {
    const container = document.getElementById('charging-session-container');
    if (!container) return;

    let html = '';
    for (let i = 0; i < 5; i++) {
        const data = chargingSessionData[i] || {};
        // timestamp是设备启动后的毫秒数，不是Unix时间戳
        const chargingAtMs = data.timestamp || 0;
        const isCharging = chargingAtMs > 0;
        // 计算充电时长（毫秒转秒）
        const chargingDurationSec = isCharging ? Math.floor(chargingAtMs / 1000) : 0;

        html += `
            <div style="margin-bottom:12px;padding:12px;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <h4 style="margin:0;color:var(--primary-color);">端口 ${i + 1}</h4>
                    <span style="padding:4px 8px;border-radius:4px;font-size:0.85em;background:${isCharging ? '#4CAF50' : '#666'};color:white;">
                        ${isCharging ? '充电中' : '未充电'}
                    </span>
                </div>
                ${isCharging ? `
                    <div style="margin-top:10px;font-size:0.9em;">
                        <div><span style="color:#888;">充电开始于:</span> 设备运行 ${formatDuration(chargingDurationSec)} 时</div>
                    </div>
                ` : '<p style="color:#666;margin:8px 0 0 0;font-size:0.9em;">无充电会话</p>'}
            </div>
        `;
    }
    container.innerHTML = html;
}

function formatDuration(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}小时${m}分钟`;
    if (m > 0) return `${m}分钟${s}秒`;
    return `${s}秒`;
}

function showTemperatureModeDialog() {
    const content = `
        <div class="form-group">
            <label>温度模式</label>
            <select id="temperature-mode">
                <option value="0">功率优先</option>
                <option value="1">温度优先</option>
            </select>
        </div>
        <p style="margin-top: 15px; font-size: 0.9em; color: var(--text-muted);">
            <i class="fas fa-info-circle"></i> 功率优先：优先保证充电功率；温度优先：优先保证设备温度不过高。
        </p>
    `;
    showDialog('温度模式', content, 'setTemperatureMode');
}

function setTemperatureMode() {
    const mode = parseInt(document.getElementById('temperature-mode').value);
    addLog(`正在设置温度模式...`, 'info');
    sendAction('set_temperature_mode', { mode });
    closeDialog();
}

function handleTemperatureMode(data) {
    const mode = data?.mode || 0;
    const modeNames = { 0: '功率优先', 1: '温度优先' };
    const modeName = modeNames[mode] || `未知(${mode})`;

    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">温度模式</span>
            <span class="info-value">${modeName}</span>
        </div>
    `;
    content += '</div>';
    showDialog('温度模式', content, null);
}

function getLedMode() {
    addLog('正在获取 LED 模式...', 'info');
    sendAction('get_led_mode');
}

function handleLedMode(data) {
    const modeNames = ['默认', '呼吸灯', '常亮', '关闭'];
    const modeName = modeNames[data.mode] || `未知 (${data.mode})`;

    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">LED 模式</span>
            <span class="info-value">${modeName}</span>
        </div>
    `;
    content += '</div>';
    showDialog('LED 模式', content, null);
}

function showAutoOffDialog() {
    const content = `
        <div class="form-group">
            <label>启用自动关闭</label>
            <select id="auto-off-enabled">
                <option value="true">启用</option>
                <option value="false">禁用</option>
            </select>
        </div>
        <div class="form-group">
            <label>超时时间 (分钟)</label>
            <input type="number" id="auto-off-timeout" min="0" max="255" value="30">
        </div>
    `;
    showDialog('设置自动关闭', content, 'setAutoOff');
}

function setAutoOff() {
    const enabled = document.getElementById('auto-off-enabled').value === 'true';
    const timeout = parseInt(document.getElementById('auto-off-timeout').value);

    addLog(`正在设置自动关闭...`, 'info');
    sendAction('set_auto_off', { enabled, timeout });
    closeDialog();
}

function getAutoOff() {
    addLog('正在获取自动关闭设置...', 'info');
    sendAction('get_auto_off');
}

function handleAutoOff(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">自动关闭</span>
            <span class="info-value">${data.enabled ? '启用' : '禁用'}</span>
        </div>
        <div class="info-item">
            <span class="info-label">超时时间</span>
            <span class="info-value">${data.timeout} 分钟</span>
        </div>
    `;
    content += '</div>';
    showDialog('自动关闭', content, null);
}

function showScreenSaverDialog() {
    const content = `
        <div class="form-group">
            <label>启用屏保</label>
            <select id="screen-saver-enabled">
                <option value="true">启用</option>
                <option value="false">禁用</option>
            </select>
        </div>
        <div class="form-group">
            <label>超时时间 (秒)</label>
            <input type="number" id="screen-saver-timeout" min="0" max="255" value="60">
        </div>
    `;
    showDialog('设置屏保', content, 'setScreenSaver');
}

function setScreenSaver() {
    const enabled = document.getElementById('screen-saver-enabled').value === 'true';
    const timeout = parseInt(document.getElementById('screen-saver-timeout').value);

    addLog(`正在设置屏保...`, 'info');
    sendAction('set_screen_saver', { enabled, timeout });
    closeDialog();
}

function getScreenSaver() {
    addLog('正在获取屏保设置...', 'info');
    sendAction('get_screen_saver');
}

function handleScreenSaver(data) {
    let content = '<div class="info-display">';
    content += `
        <div class="info-item">
            <span class="info-label">屏保</span>
            <span class="info-value">${data.enabled ? '启用' : '禁用'}</span>
        </div>
        <div class="info-item">
            <span class="info-label">超时时间</span>
            <span class="info-value">${data.timeout} 秒</span>
        </div>
    `;
    content += '</div>';
    showDialog('屏保设置', content, null);
}

// Dialog Management
function showDialog(title, content, action) {
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-content').innerHTML = content;
    currentDialogAction = action;

    const confirmBtn = document.getElementById('dialog-confirm');
    if (action) {
        confirmBtn.classList.remove('hidden');
    } else {
        confirmBtn.classList.add('hidden');
    }

    document.getElementById('dialog-overlay').classList.remove('hidden');
}

function closeDialog() {
    // 停止所有自动刷新定时器
    if (portStatusRefreshTimer) {
        clearInterval(portStatusRefreshTimer);
        portStatusRefreshTimer = null;
        const btn = document.getElementById('port-status-refresh-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        }
    }
    if (cableInfoRefreshTimer) {
        clearInterval(cableInfoRefreshTimer);
        cableInfoRefreshTimer = null;
        const btn = document.getElementById('cable-info-refresh-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        }
    }
    if (powerCurveRefreshTimer) {
        clearInterval(powerCurveRefreshTimer);
        powerCurveRefreshTimer = null;
        const btn = document.getElementById('power-curve-refresh-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        }
    }
    if (temperatureCurveRefreshTimer) {
        clearInterval(temperatureCurveRefreshTimer);
        temperatureCurveRefreshTimer = null;
        const btn = document.getElementById('temp-curve-refresh-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        }
    }
    if (debugLogRefreshTimer) {
        clearInterval(debugLogRefreshTimer);
        debugLogRefreshTimer = null;
        const btn = document.getElementById('debug-log-refresh-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        }
    }

    document.getElementById('dialog-overlay').classList.add('hidden');
    currentDialogAction = null;
}

function confirmDialog() {
    if (currentDialogAction && typeof window[currentDialogAction] === 'function') {
        window[currentDialogAction]();
    }
}

// Initialize on page load
window.onload = function () {
    connectWebSocket();

    // Close dialog on overlay click
    document.getElementById('dialog-overlay').addEventListener('click', (e) => {
        if (e.target.id === 'dialog-overlay') {
            closeDialog();
        }
    });

    // Handle ESC key to close dialog
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeDialog();
        }
    });
};

// ============ 新增功能: 版本信息 ============

function getBpVersion() {
    addLog('正在获取BP版本...', 'info');
    sendAction('get_bp_version');
}

function getFpgaVersion() {
    addLog('正在获取FPGA版本...', 'info');
    sendAction('get_fpga_version');
}

function getZrlibVersion() {
    addLog('正在获取ZRLIB版本...', 'info');
    sendAction('get_zrlib_version');
}

function handleVersionInfo(name, data) {
    const version = data?.version || '未知';
    showDialog(name, `<div class="info-display"><div class="info-item"><span class="info-label">${name}</span><span class="info-value">${version}</span></div></div>`, null);
}

// ============ 新增功能: 调试/测试 ============

function showEchoTestDialog() {
    const content = `
        <div class="form-group">
            <label>测试数据</label>
            <input type="text" id="echo-test-data" value="Hello BLE" placeholder="输入测试数据">
        </div>
    `;
    showDialog('BLE回显测试', content, 'runEchoTest');
}

function runEchoTest() {
    const data = document.getElementById('echo-test-data').value;
    addLog('正在进行BLE回显测试...', 'info');
    sendAction('ble_echo_test', { data });
    closeDialog();
}

function handleEchoTest(data) {
    const echo = data?.echo || '';
    showDialog('回显结果', `<div class="info-display"><div class="info-item"><span class="info-label">返回数据</span><span class="info-value">${echo}</span></div></div>`, null);
}

function getDebugLog() {
    addLog('正在获取调试日志...', 'info');
    sendAction('get_debug_log');
}

// 调试日志自动刷新定时器
let debugLogRefreshTimer = null;

function handleDebugLog(data) {
    const log = data?.log || '无日志';
    const content = `
        <div class="info-display">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#888;">设备调试日志 (最大1024字节)</span>
                <div style="display:flex;gap:10px;">
                    <button id="debug-log-refresh-btn" class="btn btn-success btn-small" onclick="toggleDebugLogAutoRefresh()">
                        <i class="fas fa-play"></i> 开启自动刷新
                    </button>
                    <button class="btn btn-small btn-secondary" onclick="copyDebugLog()">
                        <i class="fas fa-copy"></i> 复制
                    </button>
                </div>
            </div>
            <pre id="debug-log-content" style="
                white-space:pre-wrap;
                word-break:break-all;
                max-height:500px;
                overflow:auto;
                background:#1a1a2e;
                padding:12px;
                border-radius:8px;
                font-family:monospace;
                font-size:13px;
                line-height:1.6;
                color:#e0e0e0;
            ">${escapeHtml(log)}</pre>
            <div style="margin-top:10px;font-size:0.85em;color:#666;">
                长度: ${log.length} 字节
            </div>
        </div>
    `;
    showDialog('调试日志', content, null);
}

function toggleDebugLogAutoRefresh() {
    const btn = document.getElementById('debug-log-refresh-btn');
    if (debugLogRefreshTimer) {
        clearInterval(debugLogRefreshTimer);
        debugLogRefreshTimer = null;
        btn.innerHTML = '<i class="fas fa-play"></i> 开启自动刷新';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
        addLog('调试日志自动刷新已关闭', 'info');
    } else {
        debugLogRefreshTimer = setInterval(() => {
            sendAction('get_debug_log');
        }, REFRESH_INTERVAL);
        btn.innerHTML = '<i class="fas fa-stop"></i> 关闭自动刷新';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
        addLog('调试日志自动刷新已开启', 'info');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyDebugLog() {
    const content = document.getElementById('debug-log-content');
    if (content) {
        navigator.clipboard.writeText(content.textContent).then(() => {
            showToast('日志已复制到剪贴板', 'success');
        }).catch(() => {
            showToast('复制失败', 'error');
        });
    }
}

function pingMqtt() {
    addLog('正在测试MQTT连接...', 'info');
    sendAction('ping_mqtt');
}

function showPingHttpDialog() {
    const content = `
        <div class="form-group">
            <label>测试URL</label>
            <input type="text" id="ping-http-url" value="http://www.baidu.com" placeholder="输入HTTP URL">
        </div>
    `;
    showDialog('HTTP连接测试', content, 'runPingHttp');
}

function runPingHttp() {
    const url = document.getElementById('ping-http-url').value;
    if (!url) {
        showToast('请输入URL', 'error');
        return;
    }
    addLog(`正在测试HTTP连接: ${url}...`, 'info');
    sendAction('ping_http', { url });
    closeDialog();
}

function handlePingResult(type, data) {
    const status = data?.status || 'unknown';
    const note = data?.note || '';
    const isOk = status === 'command_ok';
    let content = `<div class="info-display">
        <div class="info-item">
            <span class="info-label">命令状态</span>
            <span class="info-value" style="color:${isOk ? 'green' : 'red'}">${isOk ? '执行成功' : '执行失败'}</span>
        </div>`;
    if (note) {
        content += `<div class="info-item"><span class="info-label">说明</span><span class="info-value" style="font-size:0.9em;color:#888;">${note}</span></div>`;
    }
    if (data?.url) {
        content += `<div class="info-item"><span class="info-label">URL</span><span class="info-value">${data.url}</span></div>`;
    }
    content += '</div>';
    showDialog(`${type}测试结果`, content, null);
}

// ============ 新增功能: OTA固件更新 ============

function showOtaDialog() {
    const content = `
        <div class="form-group">
            <label>固件URL</label>
            <input type="text" id="ota-url" placeholder="输入固件下载URL">
        </div>
        <p style="margin-top:15px;font-size:0.9em;color:var(--text-muted);">
            <i class="fas fa-exclamation-triangle" style="color:orange"></i> 警告: OTA更新有风险，请确保URL正确且固件兼容。
        </p>
    `;
    showDialog('WiFi OTA更新', content, 'startWifiOta');
}

function startWifiOta() {
    const url = document.getElementById('ota-url').value;
    if (!url) {
        showToast('请输入固件URL', 'error');
        return;
    }
    addLog('正在启动WiFi OTA更新...', 'info');
    sendAction('wifi_ota', { url });
    closeDialog();
}

function getOtaProgress() {
    addLog('正在获取OTA进度...', 'info');
    sendAction('get_ota_progress');
}

function handleOtaProgress(data) {
    const progress = data?.progress || 0;
    showDialog('OTA进度', `<div class="info-display"><div class="info-item"><span class="info-label">进度</span><span class="info-value">${progress}%</span></div><div style="background:#333;border-radius:4px;height:20px;margin-top:10px;"><div style="background:#4CAF50;height:100%;width:${progress}%;border-radius:4px;"></div></div></div>`, null);
}

function confirmOta() {
    addLog('正在确认OTA更新...', 'info');
    sendAction('confirm_ota');
}

// Cleanup on page unload
window.onbeforeunload = function () {
    if (ws) {
        ws.close();
    }
};
