# IonBridge BLE 控制器 - 快速开始指南

## 📋 项目概述

这是一个完整的 IonBridge（小电拼）蓝牙控制系统，支持所有 78 个蓝牙命令，具有以下特性：

✅ **自动 Token 管理**：每 5 分钟自动刷新 Token（暴力破解 0x00-0xFF）
✅ **设备自动重连**：Token 失效或连接断开时自动重新扫描和连接
✅ **完整功能支持**：支持所有 78 个蓝牙命令
✅ **命令行测试工具**：交互式命令行界面，支持所有功能
✅ **Web 控制器**：现代化的 Web 界面，实时状态更新

## 🚀 快速开始

### 1. 安装依赖

依赖项已经在 conda 的 `uu` 环境中安装好了（使用清华镜像）。

如果需要重新安装：

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bleak fastapi uvicorn websockets
```

### 2. 运行单元测试

验证基本功能：

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python ionbridge-ble-controller/test_cli.py
```

预期输出：
```
======================================================================
  IonBridge BLE 控制器 - 单元测试
======================================================================

测试协议编解码...
  ✓ 协议编解码测试通过

测试消息构建...
  ✓ 消息构建测试通过

测试命令分类...
  ✓ 命令分类测试通过

测试所有协议名称...
  ✓ 协议名称测试通过

======================================================================
  所有测试通过! ✓
======================================================================
```

### 3. 使用命令行工具

启动命令行控制器：

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python ionbridge-ble-controller/cli_controller.py
```

基本操作流程：

```bash
# 1. 扫描设备
> scan

# 2. 连接设备（会自动获取 Token）
> connect

# 3. 查看设备信息
> info

# 4. 查看端口状态
> status

# 5. 打开端口 0
> on 0

# 6. 查看端口 0 的协议配置
> config 0

# 7. 为端口 0 启用 USB PD 协议
> enable 0 PD

# 8. 退出
> quit
```

### 4. 使用 Web 控制器

启动 Web 服务器：

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python ionbridge-ble-controller/app.py
```

打开浏览器访问：

```
http://localhost:8000
```

Web 界面功能：
- 📱 设备管理：扫描、连接、断开、信息、重启、重置
- 🔌 端口控制：状态、电源、配置、优先级
- 📋 协议管理：列表、启用/禁用
- ⚡ 电源管理：统计、策略
- 📶 WiFi 管理：状态、扫描、设置
- 🖥️ 显示管理：设置、亮度、模式、翻转
- ⚙️ 系统控制：Token 刷新、自动刷新、自动重连

## 📝 命令行工具完整命令列表

### 设备管理
```
scan                    - 扫描设备
connect <address>       - 连接设备
disconnect              - 断开连接
info                    - 获取设备信息
reboot                  - 重启设备
reset                   - 重置设备
```

### 端口控制
```
status                  - 查看所有端口状态
on <port>              - 打开端口（支持逗号分隔：on 0,1,2）
off <port>             - 关闭端口（支持逗号分隔：off 0,1,2）
config <port>           - 查看端口配置
set-config <port> <protos> - 设置端口配置
priority <port> <val>   - 设置端口优先级
```

### 协议管理
```
protocols               - 列出所有支持的协议
enable <port> <proto>  - 启用协议
disable <port> <proto> - 禁用协议
```

### 电源管理
```
power [port]            - 获取电源统计
strategy                - 获取充电策略
set-strategy <val>      - 设置充电策略
```

### WiFi 管理
```
wifi-status             - 获取 WiFi 状态
scan-wifi               - 扫描 WiFi 网络
set-wifi <ssid> <pwd> - 设置 WiFi
```

### 显示管理
```
display-info            - 获取显示设置
brightness <val>        - 设置亮度 (0-100)
mode <val>              - 设置显示模式
flip                    - 翻转显示
```

### 系统控制
```
token                   - 显示当前 Token
refresh-token           - 手动刷新 Token
auto-refresh [on|off]  - 切换自动刷新
auto-reconnect [on|off] - 切换自动重连
help                    - 显示帮助
quit                    - 退出
```

## 🔧 支持的协议列表

### 快充协议
- TFCP, PE, QC 2.0, QC 3.0, QC 3+, AFC, FCP, UFCS

### 品牌协议
- Apple 5V, Samsung 5V, VOOC, Dash/Warp

### USB PD
- PD, PPS, QC 4.0, QC 4+

### 其他
- HV SCP, LV SCP, SFCP, BC1.2, RPi 5V5A, SFC, MTK PE, MTK PE+

**总计：24 种协议**

## 📊 支持的蓝牙命令（78 个）

### 测试命令（7 个）
- BLE_ECHO_TEST, GET_DEBUG_LOG, GET_SECURE_BOOT_DIGEST
- PING_MQTT_TELEMETRY, PING_HTTP, GET_DEVICE_PASSWORD
- MANAGE_POWER_ALLOCATOR_ENABLED

### 设备管理（13 个）
- ASSOCIATE_DEVICE, REBOOT_DEVICE, RESET_DEVICE
- GET_DEVICE_SERIAL_NO, GET_DEVICE_UPTIME, GET_AP_VERSION
- GET_DEVICE_BLE_ADDR, SWITCH_DEVICE, GET_DEVICE_SWITCH
- GET_DEVICE_MODEL, PUSH_LICENSE, GET_BLE_RSSI, GET_BLE_MTU

### OTA 命令（5 个）
- PERFORM_BLE_OTA, PERFORM_WIFI_OTA, GET_WIFI_OTA_PROGRESS
- CONFIRM_OTA, START_OTA

### WiFi 管理（11 个）
- SCAN_WIFI, GET_WIFI_SCAN_RESULT, SET_WIFI_SSID
- RESET_WIFI, GET_WIFI_STATUS, GET_DEVICE_WIFI_ADDR
- SET_WIFI_SSID_AND_PASSWORD, GET_WIFI_RECORDS
- OPERATE_WIFI_RECORD, GET_WIFI_STATE_MACHINE, SET_WIFI_STATE_MACHINE

### 电源管理（24 个）
- TOGGLE_PORT_POWER, GET_POWER_STATISTICS, GET_POWER_SUPPLY_STATUS
- SET_CHARGING_STRATEGY, GET_CHARGING_STATUS, GET_POWER_HISTORICAL_STATS
- SET_PORT_PRIORITY, GET_PORT_PRIORITY, GET_CHARGING_STRATEGY
- GET_PORT_PD_STATUS, GET_ALL_POWER_STATISTICS, GET_START_CHARGE_TIMESTAMP
- TURN_ON_PORT, TURN_OFF_PORT, SET_STATIC_ALLOCATOR
- GET_STATIC_ALLOCATOR, SET_PORT_CONFIG, GET_PORT_CONFIG
- SET_PORT_COMPATIBILITY_SETTINGS, GET_PORT_COMPATIBILITY_SETTINGS
- SET_TEMPERATURE_MODE, SET_TEMPORARY_ALLOCATOR
- SET_PORT_CONFIG1, GET_PORT_CONFIG1

### 显示管理（9 个）
- SET_DISPLAY_INTENSITY, SET_DISPLAY_MODE, GET_DISPLAY_INTENSITY
- GET_DISPLAY_MODE, SET_DISPLAY_FLIP, GET_DISPLAY_FLIP
- SET_DISPLAY_CONFIG, SET_DISPLAY_STATE, GET_DISPLAY_STATE

### 系统命令（6 个）
- START_TELEMETRY_STREAM, STOP_TELEMETRY_STREAM
- GET_DEVICE_INFO, SET_BLE_STATE, SET_SYSLOG_STATE, SET_SYSTEM_TIME

### 功能管理（3 个）
- MANAGE_POWER_CONFIG, MANAGE_FEATURE_TOGGLE, ENABLE_RELEASE_MODE

## ⚙️ 核心功能说明

### 自动 Token 刷新

- **刷新间隔**：5 分钟（可配置）
- **刷新方式**：暴力破解 0x00-0xFF
- **自动触发**：后台任务自动执行
- **手动触发**：`refresh-token` 命令

### 设备自动重连

- **触发条件**：命令失败或连接断开
- **重连次数**：最多 5 次
- **重连流程**：断开 → 扫描 → 连接 → 获取 Token
- **可配置**：`auto-reconnect` 命令启用/禁用

### 蓝牙通信

- **Service UUID**: `048e3f2e-e1a6-4707-9e74-a930e898a1ea`
- **TX Characteristic**: `148e3f2e-e1a6-4707-9e74-a930e898a1ea` (Notify)
- **RX Characteristic**: `248e3f2e-e1a6-4707-9e74-a930e898a1ea` (Write)

## 📁 文件结构

```
ionbridge-ble-controller/
├── protocol.py              # 协议定义（78 个命令）
├── ble_manager.py           # BLE 管理器（自动刷新、自动重连）
├── cli_controller.py        # 命令行控制器
├── app.py                  # Web 控制器（FastAPI）
├── test_cli.py             # 单元测试
├── requirements.txt         # 依赖项
├── README.md               # 完整文档
├── QUICKSTART.md           # 本文档
└── static/                # Web 界面
    ├── index.html          # 主页面
    ├── app.js             # 前端逻辑
    └── style.css          # 样式
```

## 🐛 故障排除

### 问题：无法扫描到设备

**解决方案**：
1. 确保设备已开机
2. 确保设备在蓝牙范围内（建议 5 米以内）
3. 检查系统蓝牙权限
4. 重启蓝牙服务

### 问题：Token 获取失败

**解决方案**：
1. 等待几秒后重试
2. 检查设备是否响应
3. 尝试手动刷新 Token：`refresh-token`
4. 检查设备是否被其他设备连接

### 问题：连接频繁断开

**解决方案**：
1. 检查设备电池电量
2. 确保设备在范围内
3. 启用自动重连：`auto-reconnect on`
4. 检查蓝牙信号强度

### 问题：Web 界面无法连接

**解决方案**：
1. 检查 WebSocket 是否连接（查看浏览器控制台）
2. 确认后端服务正在运行
3. 检查防火墙设置
4. 尝试刷新页面

## 💡 使用技巧

### 命令行工具

1. **批量操作**：使用逗号分隔多个端口
   ```bash
   > on 0,1,2  # 同时打开端口 0, 1, 2
   ```

2. **协议配置**：一次性配置多个协议
   ```bash
   > set-config 0 PD,QC3.0,UFCS  # 为端口 0 启用多个协议
   ```

3. **自动刷新**：让系统自动管理 Token
   ```bash
   > auto-refresh on  # 启用自动刷新（默认已启用）
   ```

### Web 界面

1. **实时日志**：所有操作都会显示在日志区域
2. **状态监控**：顶部状态栏实时显示连接状态
3. **快捷操作**：常用功能一键操作
4. **响应式设计**：支持手机和平板设备

## 📚 更多信息

- **完整文档**：[`README.md`](README.md)
- **设计方案**：[`../plans/ionbridge-ble-controller-plan.md`](../plans/ionbridge-ble-controller-plan.md)
- **开源项目**：https://github.com/ifanrx/IonBridge
- **蓝牙指南**：[`../IonBridge_BLE_Complete_Guide.md`](../IonBridge_BLE_Complete_Guide.md)

## ✅ 测试状态

- ✅ 协议编解码测试通过
- ✅ 消息构建测试通过
- ✅ 命令分类测试通过
- ✅ 所有协议名称测试通过
- ✅ 命令行工具测试通过
- ✅ Web 控制器测试通过

## 🎉 开始使用

现在你已经准备好使用 IonBridge BLE 控制器了！

选择你喜欢的使用方式：
- 🖥️ **命令行工具**：适合高级用户和自动化脚本
- 🌐 **Web 界面**：适合图形化操作和实时监控

祝使用愉快！🎊
