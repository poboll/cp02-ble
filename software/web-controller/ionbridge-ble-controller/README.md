<div align="center">

# IonBridge BLE Controller

**完整支持 78 个 BLE 命令的开发者工具**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](../../../LICENSE)

[English](#english) | [简体中文](#简体中文)

</div>

---

## 简体中文

### 概述

IonBridge BLE Controller 是面向开发者的底层控制工具，基于 [IonBridge](https://github.com/ifanrx/IonBridge) 开源项目，完整支持协议定义的全部 78 个 BLE 命令。提供命令行界面 (CLI) 和 Web API 两种控制方式。

### 特性

| 特性 | 描述 |
|:-----|:-----|
| **完整命令支持** | 78 个 BLE 命令全覆盖 |
| **自动 Token 管理** | 每 5 分钟自动刷新 (暴力破解 0x00-0xFF) |
| **设备自动重连** | Token 失效或连接断开时自动恢复 |
| **双模式控制** | CLI 交互式 + Web API |
| **WebSocket 实时通信** | 毫秒级状态更新 |

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# CLI 模式
python cli_controller.py

# Web API 模式
python app.py
# 访问 http://localhost:8000
```

### 命令参考

#### 设备管理

```bash
> scan                    # 扫描设备
> connect CP02-002548     # 连接指定设备
> disconnect              # 断开连接
> info                    # 获取设备信息
> reboot                  # 重启设备
```

#### 端口控制

```bash
> status                  # 查看所有端口状态
> on 0                    # 开启端口 0
> on 0,1,2                # 开启多个端口
> off 0                   # 关闭端口 0
> config 0                # 查看端口配置
> set-config 0 PD,QC3.0   # 设置协议
```

#### 协议管理

```bash
> protocols               # 列出支持的协议
> enable 0 PD             # 启用 USB PD
> disable 0 QC3.0         # 禁用 QC3.0
```

#### 系统控制

```bash
> token                   # 显示当前 Token
> refresh-token           # 手动刷新 Token
> auto-refresh on         # 启用自动刷新
> help                    # 显示帮助
```

### 命令分类统计

| 类别 | 数量 | 示例 |
|:-----|:-----|:-----|
| 测试命令 | 7 | BLE_ECHO_TEST, PING_HTTP |
| 设备管理 | 13 | REBOOT_DEVICE, GET_DEVICE_INFO |
| OTA 更新 | 5 | PERFORM_WIFI_OTA, CONFIRM_OTA |
| WiFi 管理 | 11 | SCAN_WIFI, SET_WIFI_SSID |
| 电源管理 | 24 | TOGGLE_PORT_POWER, GET_CHARGING_STATUS |
| 显示管理 | 9 | SET_DISPLAY_INTENSITY, FLIP_DISPLAY |
| 系统命令 | 6 | START_TELEMETRY_STREAM |
| 功能管理 | 3 | MANAGE_FEATURE_TOGGLE |
| **总计** | **78** | |

### 技术细节

**BLE 协议**

| 项目 | 值 |
|:-----|:---|
| Service UUID | `048e3f2e-e1a6-4707-9e74-a930e898a1ea` |
| TX Characteristic | `148e3f2e-e1a6-4707-9e74-a930e898a1ea` (Notify) |
| RX Characteristic | `248e3f2e-e1a6-4707-9e74-a930e898a1ea` (Write) |

**Token 机制**

- Token: 1 字节随机数 (0-255)
- 刷新周期: 5 分钟
- 获取方式: 暴力破解 0x00-0xFF

### 项目结构

```
ionbridge-ble-controller/
├── app.py                # Web 服务入口
├── ble_manager.py        # BLE 管理器
├── cli_controller.py     # 命令行控制器
├── protocol.py           # 协议定义 (78 命令)
├── requirements.txt      # 依赖列表
├── static/               # Web 静态资源
└── utils/                # 工具脚本
```

---

## English

### Overview

IonBridge BLE Controller is a developer tool that fully supports all 78 BLE commands defined in the IonBridge protocol. It provides both CLI and Web API control modes.

### Quick Start

```bash
pip install -r requirements.txt

# CLI mode
python cli_controller.py

# Web API mode
python app.py  # http://localhost:8000
```

### Features

- Full 78 BLE command support
- Automatic Token management (5-min refresh)
- Auto device reconnection
- CLI + Web API dual mode
- WebSocket real-time communication

---

## Related

- [Main Project](../../../README.md)
- [Charging Station Monitor](../../ble-charging-station/README.md)
- [BLE Gateway](../../esp32-ble-gateway/README.md)

## License

MIT License © 2023 [在虎 (poboll)](https://github.com/poboll)
