# IonBridge BLE 控制器

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**基于 IonBridge 开源项目的完整蓝牙控制系统，支持所有 78 个蓝牙命令**

[快速开始](#快速开始) • [功能特性](#功能特性) • [API 文档](#api-文档)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [命令行工具使用](#命令行工具使用)
- [Web 控制器使用](#web-控制器使用)
- [API 文档](#api-文档)
- [支持的协议](#支持的协议)
- [技术细节](#技术细节)
- [故障排除](#故障排除)

---

## 项目简介

基于 IonBridge 开源项目的完整蓝牙控制系统，支持所有 78 个蓝牙命令。提供命令行界面和 Web 界面两种控制方式。

---

## 功能特性

✅ **自动 Token 管理**：每 5 分钟自动刷新 Token（暴力破解 0x00-0xFF）
✅ **设备自动重连**：Token 失效或连接断开时自动重新扫描和连接
✅ **完整功能支持**：支持所有 78 个蓝牙命令
✅ **命令行测试工具**：交互式命令行界面，支持所有功能
✅ **Web 控制器**：基于 FastAPI 的现代化 Web 界面
✅ **WebSocket 实时通信**：支持实时设备状态更新
✅ **完善的错误处理**：所有命令都有超时和重试机制

---

## 快速开始

### 前置要求

- Python 3.8+
- 蓝牙适配器
- IonBridge BLE 设备

### 安装依赖

```bash
# 安装依赖
pip install -r requirements.txt

# 或使用清华镜像（推荐国内用户）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bleak fastapi uvicorn websockets
```

### 文件结构

```
ionbridge-ble-controller/
├── app.py                    # Web 控制器主程序
├── ble_manager.py            # BLE 管理器（自动刷新、自动重连）
├── cli_controller.py         # 命令行控制器
├── protocol.py               # 协议定义（78 个命令）
├── requirements.txt          # 依赖项
├── static/                   # Web 界面静态资源
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/                    # 测试文件
│   ├── test_cli.py
│   ├── comprehensive_test.py
│   └── ...
└── utils/                    # 工具脚本
    ├── check_wifi_connection.py
    ├── configure_device.py
    └── ...
```

## 命令行工具使用

### 启动命令行控制器

```bash
python cli_controller.py
```

### 常用命令

#### 设备管理

```bash
# 扫描设备
> scan

# 连接设备（会自动选择或输入地址）
> connect

# 连接到指定设备
> connect CP02-002548

# 断开连接
> disconnect

# 获取设备信息
> info

# 重启设备
> reboot

# 重置设备（恢复出厂设置）
> reset
```

#### 端口控制

```bash
# 查看所有端口状态
> status

# 打开端口 0
> on 0

# 打开多个端口
> on 0,1,2

# 关闭端口 0
> off 0

# 查看端口 0 的协议配置
> config 0

# 设置端口 0 的协议配置
> set-config 0 PD,QC3.0,UFCS

# 设置端口优先级
> priority 0 10
```

#### 协议管理

```bash
# 列出所有支持的协议
> protocols

# 为端口 0 启用 USB PD 协议
> enable 0 PD

# 为端口 0 禁用 QC3.0 协议
> disable 0 QC3.0
```

#### 电源管理

```bash
# 获取端口 0 的电源统计
> power 0

# 获取充电策略
> strategy

# 设置充电策略
> set-strategy 1
```

#### WiFi 管理

```bash
# 获取 WiFi 状态
> wifi-status

# 扫描 WiFi 网络
> scan-wifi

# 设置 WiFi
> set-wifi MyNetwork MyPassword
```

#### 显示管理

```bash
# 获取显示设置
> display-info

# 设置亮度（0-100）
> brightness 80

# 设置显示模式
> mode 1

# 翻转显示
> flip
```

#### 系统控制

```bash
# 显示当前 Token
> token

# 手动刷新 Token
> refresh-token

# 启用/禁用自动刷新
> auto-refresh on
> auto-refresh off

# 启用/禁用自动重连
> auto-reconnect on
> auto-reconnect off

# 显示帮助
> help

# 退出
> quit
```

## 单元测试

运行单元测试验证基本功能：

```bash
# 运行所有测试
python tests/test_cli.py

# 运行综合测试
python tests/comprehensive_test.py

# 运行最终测试
python tests/final_test.py
```

测试内容包括：
- 协议编解码
- 消息构建和解析
- 命令分类
- 所有协议名称
- 设备连接和断开
- Token 刷新机制

## Web 控制器使用

### 启动 Web 服务器

```bash
python app.py
```

### 访问 Web 界面

打开浏览器访问：

```
http://localhost:8000
```

### WebSocket API

WebSocket 端点：`ws://localhost:8000/ws`

消息格式：

```json
{
  "action": "scan_devices",
  "params": {
    "timeout": 5.0
  }
}
```

支持的 action：
- `scan_devices` - 扫描设备
- `connect` - 连接设备
- `disconnect` - 断开连接
- `refresh_token` - 刷新 Token
- `get_device_info` - 获取设备信息
- `get_port_status` - 获取端口状态
- `set_port_power` - 设置端口电源
- `get_port_config` - 获取端口配置
- `set_port_config` - 设置端口配置
- `get_wifi_status` - 获取 WiFi 状态
- `set_wifi` - 设置 WiFi
- `reboot_device` - 重启设备
- `reset_device` - 重置设备
- `get_display_settings` - 获取显示设置
- `set_display_brightness` - 设置亮度
- `set_display_mode` - 设置模式
- `flip_display` - 翻转显示
- `get_status` - 获取状态

## 支持的协议

### 快充协议
- TFCP
- PE
- QC 2.0 / 3.0 / 3+
- AFC
- FCP
- UFCS

### 品牌协议
- Apple 5V
- Samsung 5V
- VOOC
- Dash/Warp

### USB PD
- PD
- PPS (Programmable Power Supply)
- QC 4.0 / 4+

### 其他
- HV SCP / LV SCP
- SFCP
- BC1.2
- RPi 5V5A
- SFC
- MTK PE / PE+

## 技术细节

### Token 机制

- Token 是 1 字节的随机数（0-255）
- Token 每 5 分钟自动刷新
- 所有命令（除 ASSOCIATE_DEVICE）都需要 Token
- Token 通过暴力破解获取（测试 0x00-0xFF）

### 自动重连机制

- 命令失败时自动尝试重连
- 最多重连 5 次
- 重连后自动获取新 Token
- 可通过 `auto-reconnect` 命令启用/禁用

### 蓝牙协议

- Service UUID: `048e3f2e-e1a6-4707-9e74-a930e898a1ea`
- TX Characteristic: `148e3f2e-e1a6-4707-9e74-a930e898a1ea` (Notify)
- RX Characteristic: `248e3f2e-e1a6-4707-9e74-a930e898a1ea` (Write)

## 命令分类

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

**总计：78 个命令**

## 注意事项

1. **Token 刷新**：每 5 分钟自动刷新，可能需要几秒钟时间
2. **设备重连**：Token 失效时会自动重连，请确保设备在范围内
3. **并发控制**：避免同时执行多个命令
4. **错误处理**：所有命令都有超时和重试机制
5. **日志记录**：所有操作都会记录日志，便于调试

## 故障排除

### 无法扫描到设备
- 确保设备已开机
- 确保设备在蓝牙范围内
- 检查系统蓝牙权限

### Token 获取失败
- 等待几秒后重试
- 检查设备是否响应
- 尝试手动刷新 Token

### 连接断开
- 检查设备是否在范围内
- 检查设备电池电量
- 尝试手动重连

## 开源项目

基于：https://github.com/ifanrx/IonBridge

## 相关文档

- [主项目 README](../../../README.md)
- [Arduino 固件](../../../hardware/arduino/README.md)
- [Python 脚本工具](../../../software/python-scripts/README.md)
- [Web 界面使用指南](../../../docs/guides/WEB_INTERFACE_GUIDE.md)
- [快速开始指南](../../../docs/guides/QUICKSTART.md)

## 许可证

本项目采用 MIT 许可证 - 详见项目根目录 [LICENSE](../../../LICENSE) 文件

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

</div>
