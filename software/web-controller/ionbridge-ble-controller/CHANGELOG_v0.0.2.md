# IonBridge BLE Controller v0.0.2 更新日志

## 发布日期
2026-01-17

## 新增功能

### 1. 温度曲线功能
- 新增温度曲线功能，支持查看所有端口的温度变化趋势
- 支持单个端口和全部端口的温度曲线显示
- 实时更新温度数据，自动滚动显示
- 使用有符号字节转换，正确显示负温度值

### 2. 调试日志自动刷新
- 新增调试日志自动刷新功能
- 支持手动开启/关闭自动刷新
- 刷新间隔：2秒
- 支持复制日志内容到剪贴板

### 3. 充电线信息（全部端口）
- 新增充电线信息功能，支持查看所有端口的详细充电信息
- 显示电池信息（VID、PID、设计容量、当前容量、电量百分比、电池状态）
- 显示线缆信息（VID、PID、物理类型、线缆长度、最大电压、最大电流、USB速度）
- 显示运行信息（当前电压、电流、功率、PD版本、PPS支持、有电池、有eMarker）
- 显示状态温度（使用有符号字节转换）
- 支持自动刷新功能
- 电压/电流数据使用`get_port_status`命令获取，确保准确性

### 4. 功率曲线功能
- 新增功率曲线功能，支持查看所有端口的功率变化趋势
- 支持单个端口和全部端口的功率曲线显示
- 实时更新功率数据，自动滚动显示
- 智能Y轴刻度，确保至少有10W刻度范围
- 显示功率(W)、电压(V)、电流(A)三条曲线

### 5. 充电会话功能
- 新增充电会话功能，支持查看所有端口的充电状态
- 显示充电开始时间（设备运行时间）
- 显示充电时长
- 显示充电状态（充电中/未充电）

### 6. 温度模式功能
- 新增温度模式功能，支持功率优先和温度优先两种模式
- 功率优先：优先保证充电功率
- 温度优先：优先保证设备温度不过高

## 修复和改进

### 1. 修复温度解析问题
- **问题**：温度值显示不正确（如97°C）
- **原因**：温度字节使用补码表示负数，但没有进行有符号字节转换
- **修复**：在`parse_power_statistics_response`和`parse_port_pd_status_response`函数中添加有符号字节转换
- **修复代码**：
  ```python
  # 温度使用有符号字节转换（解决1600多度的问题）
  # 如果温度字节 >= 128，则表示负数（使用补码）
  temperature = temperature_raw if temperature_raw < 128 else temperature_raw - 256
  ```

### 2. 修复充电线信息温度显示问题
- **问题**：充电线信息中温度显示不正确（如97°C）
- **原因**：`parse_port_pd_status_response`函数中状态温度没有进行有符号字节转换
- **修复**：在`parse_port_pd_status_response`函数中为状态温度添加有符号字节转换
- **修复代码**：
  ```python
  # 状态温度 (byte 15) - 使用有符号字节转换
  status_temperature = get_byte(15)
  if status_temperature >= 128:
      status_temperature = status_temperature - 256
  result['status'] = {'temperature': status_temperature}
  ```

### 3. 修复温度曲线默认端口选择
- **问题**：温度曲线对话框中"全部端口"不是第一个选项
- **修复**：修改`showTemperatureCurveDialog()`函数，将"全部端口"放在第一位
- **修复代码**：
  ```javascript
  <select id="temp-curve-port-id">
      <option value="all">全部端口</option>
      <option value="0">端口 1</option>
      ...
  </select>
  ```

### 4. 优化调试日志UI
- **问题**：调试日志UI太小（单行），没有自动刷新功能
- **修复**：
  - 增加最大高度从400px到500px
  - 增加字体大小从12px到13px
  - 添加自动刷新按钮
  - 添加复制按钮
  - 修改`closeDialog()`函数，关闭对话框时停止调试日志刷新定时器
- **修复代码**：
  ```javascript
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
  ```

### 5. 优化监控动态图标UI
- **改进**：根据功率值动态显示不同颜色的闪电图标
- **颜色方案**：
  - 绿色 (#4CAF50)：低功率 (<10W)
  - 橙色 (#FF9800)：中功率 (10-30W)
  - 红色 (#FF5722)：高功率 (30-60W)
  - 深红色 (#F44336)：超高功率 (>60W)
  - 灰色 (#666)：无功率

### 6. 优化亮度调整UI
- **改进**：美化亮度调整界面
- **功能**：
  - 渐变背景色
  - 实时显示亮度值
  - 预设亮度按钮（夜间、暗光、中等、明亮）
  - 根据亮度值动态改变显示颜色

### 7. 修复对话框关闭后自动刷新继续运行问题
- **问题**：关闭对话框后，自动刷新定时器继续运行，导致干扰
- **修复**：修改`closeDialog()`函数，关闭对话框时停止所有自动刷新定时器
- **修复代码**：
  ```javascript
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
  ```

### 8. 修复充电会话第5个端口不显示问题
- **问题**：充电会话只显示4个端口，第5个端口不显示
- **原因**：`handleChargingSession`函数中循环只执行4次
- **修复**：修改循环为执行5次
- **修复代码**：
  ```javascript
  for (let i = 0; i < 5; i++) {
      sendAction('get_start_charge_timestamp', { port_id: i });
  }
  ```

### 9. 修复充电线信息电压/电流解析问题
- **问题**：充电线信息中电压/电流数据不准确
- **原因**：`get_port_pd_status`命令的operating数据可能不准确
- **修复**：使用`get_port_status`命令的数据来显示电压/电流
- **修复代码**：
  ```javascript
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
  ```

### 10. 修复功率曲线Y轴坐标显示错误问题
- **问题**：功率曲线Y轴坐标显示不正确
- **原因**：Y轴最大值计算逻辑有问题
- **修复**：统一使用`get_port_status`命令的数据
- **修复代码**：
  ```javascript
  // 智能Y轴刻度（与drawPowerChart保持一致）
  if (maxPower <= 0) maxPower = 10;
  else if (maxPower <= 10) maxPower = Math.ceil(maxPower / 2) * 2 || 2;
  else if (maxPower <= 50) maxPower = Math.ceil(maxPower / 10) * 10;
  else if (maxPower <= 100) maxPower = Math.ceil(maxPower / 20) * 20;
  else maxPower = Math.ceil(maxPower / 50) * 50;
  
  // 确保至少有10W的刻度范围
  if (maxPower < 10) maxPower = 10;
  ```

### 11. 在设备信息对话框中添加"运行时间"显示
- **新增**：在设备信息对话框中显示设备运行时间
- **功能**：显示格式化的运行时间（Xh Xm Xs）

### 12. 修复所有端口控制下拉框只显示1-4端口问题
- **问题**：端口电源、端口配置、端口优先级、协议管理的下拉框只显示1-4端口
- **修复**：修改所有相关函数，添加端口5选项
- **修复代码**：
  ```javascript
  <select id="port-id">
      <option value="0">端口 1</option>
      <option value="1">端口 2</option>
      <option value="2">端口 3</option>
      <option value="3">端口 4</option>
      <option value="4">端口 5</option>
  </select>
  ```

### 13. 修复协议兼容设置功能
- **新增**：协议兼容设置功能
- **支持**：6种预定义兼容模式
  - 原生模式：出厂默认的标准兼容状态，兼顾各种设备
  - 华为模式：优先握手华为的私有快充协议（SCP/FCP）
  - 安卓模式：默认开启并优化双档位PPS协议
  - 苹果全家桶模式：专为iPhone+iPad+MacBook组合优化
  - 睡眠模式/养生模式：慢充保护，降低输出功率上限
  - 小家电模式：屏蔽低电流自动关机功能
- **支持**：自定义协议兼容设置
  - TFCP（腾讯快充协议）
  - FCP（华为快充协议）
  - UFCS（融合快充标准）
  - 高压SCP（华为超级快充）
  - 低压SCP（华为超级快充）

### 14. 添加版本信息功能
- **新增**：版本信息功能
- **支持**：
  - BP版本（SW3566 MCU版本）
  - FPGA版本
  - ZRLIB版本

### 15. 添加调试/测试功能
- **新增**：调试/测试功能
- **支持**：
  - BLE回显测试
  - 调试日志（最大1024字节）
  - MQTT连接测试
  - HTTP连接测试

### 16. 添加OTA固件更新功能
- **新增**：OTA固件更新功能
- **支持**：
  - WiFi OTA更新
  - 获取OTA进度
  - 确认OTA更新

### 17. 修复PD状态电压/电流解析问题
- **问题**：PD状态中电压/电流解析不正确
- **原因**：单位转换和位域提取有问题
- **修复**：
  - 修正电压单位转换：10mV to V
  - 修正电流单位转换：10mA to A
  - 修正位域提取逻辑
- **修复代码**：
  ```python
  # 转换单位（10mA for current, 10mV for voltage）
  current_ma = op_current * 10  # 10mA units
  voltage_mv = op_voltage * 10  # 10mV units
  
  # 转换为标准单位
  current_a = current_ma / 1000.0  # mA to A
  voltage_v = voltage_mv / 1000.0  # mV to V
  power_w = current_a * voltage_v  # W
  ```

### 18. 添加线缆长度映射
- **新增**：线缆长度映射功能
- **支持**：8种线缆长度
  - <1m
  - ~2m
  - ~3m
  - ~4m
  - ~5m
  - ~6m
  - ~7m
  - >7m

### 19. 添加优雅关闭功能
- **新增**：优雅关闭功能
- **支持**：
  - SIGTERM信号处理
  - SIGINT信号处理
  - 应用关闭时断开BLE连接
  - 应用关闭时关闭所有WebSocket连接

### 20. 修改功率曲线为所有端口显示在一张表中
- **改进**：功率曲线支持所有端口显示在一张表中
- **功能**：
  - 支持单个端口和全部端口切换
  - 实时更新所有端口功率数据
  - 自动滚动显示
  - 智能Y轴刻度

## 技术改进

### 1. 协议解析优化
- **改进**：从IonBridge-main源码提取正确的协议定义
- **支持**：21种快充协议
  - QC2.0, QC3.0, QC3+, SFCP, AFC, FCP, SCP
  - VOOC1.0, VOOC4.0, SuperVOOC2.0
  - TFCP, UFCS, PE1.0, PE2.0
  - PD 5V, PD 高压, PD SPR AVS, PD PPS, PD EPR 高压, PD AVS

### 2. 温度数据解析优化
- **改进**：使用有符号字节转换
- **支持**：正确显示负温度值

### 3. WebSocket通信优化
- **改进**：添加错误处理和重连机制
- **支持**：
  - 自动重连
  - 错误处理
  - 状态广播

### 4. UI/UX优化
- **改进**：现代化UI设计
- **特性**：
  - 渐变背景色
  - 动态图标
  - 响应式布局
  - 动画效果
  - 深色主题

## 已知问题

### 1. WiFi扫描显示问题
- **描述**：WiFi扫描可能显示"没有获取到"
- **可能原因**：
  - 设备WiFi功能未启用
  - 设备周围没有WiFi网络
  - WiFi扫描命令执行失败
- **说明**：如果设备确实没有扫描到WiFi网络，显示"未发现 WiFi 网络"是正确的行为

## 升级说明

### 从v0.0.1升级到v0.0.2
1. 停止当前运行的服务
2. 替换以下文件：
   - `software/web-controller/ionbridge-ble-controller/app.py`
   - `software/web-controller/ionbridge-ble-controller/protocol.py`
   - `software/web-controller/ionbridge-ble-controller/static/app.js`
3. 重新启动服务

### 注意事项
1. 升级前请备份重要数据
2. 升级后请清除浏览器缓存
3. 如遇到问题，请查看调试日志

## 联系方式
- 项目地址：https://github.com/yourusername/ionbridge-ble-controller
- 问题反馈：请提交Issue

## 许可证
MIT License
