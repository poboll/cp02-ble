<div align="center">

# CP02-BLE

**IonBridge BLE 充电站控制与监控解决方案**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C.svg?logo=espressif&logoColor=white)](https://platformio.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/poboll/cp02-ble/pulls)

[English](#english) | [简体中文](#简体中文)

</div>

---

## 简体中文

### 概述

CP02-BLE 是一套完整的 IonBridge CP02 系列充电站 BLE 控制与监控解决方案。项目提供三种不同定位的实现方案，覆盖从开发调试到企业级部署的全场景需求。

### 方案对比

| 方案 | 定位 | 核心能力 | 适用场景 |
|:-----|:-----|:---------|:---------|
| **[BLE Controller](#ble-controller)** | 开发者工具 | 78个BLE命令完整支持 | 开发调试、协议研究、自动化脚本 |
| **[Charging Station](#charging-station)** | 可视化监控 | 3D界面、实时图表、智能识别 | 个人用户、单站点监控 |
| **[BLE Gateway](#ble-gateway)** | 分布式网关 | MQTT、多网关、历史数据 | 企业部署、多站点管理 |

---

### BLE Controller

> 路径: `software/web-controller/ionbridge-ble-controller/`

面向开发者的底层控制工具，完整支持 IonBridge 协议定义的全部 78 个 BLE 命令。

**核心特性**

- 交互式命令行界面 (CLI)
- RESTful API + WebSocket 实时通信
- 自动 Token 管理与设备重连
- 端口控制、协议管理、WiFi 配置

**快速开始**

```bash
cd software/web-controller/ionbridge-ble-controller
pip install -r requirements.txt

# CLI 模式
python cli_controller.py

# Web API 模式
python app.py  # 访问 http://localhost:8000
```

**命令示例**

```bash
> scan                    # 扫描设备
> connect CP02-002548     # 连接设备
> status                  # 查看端口状态
> on 0                    # 开启端口 0
> set-config 0 PD,QC3.0   # 配置协议
```

---

### Charging Station

> 路径: `software/ble-charging-station/`

面向普通用户的可视化监控系统，提供现代化 3D 界面与实时数据展示。

**核心特性**

- 3D 充电站模型 + 粒子呼吸光效
- 实时功率、电压、电流监控
- 智能线材识别 (20+ 种类型)
- 响应式设计，适配桌面与移动端

**快速开始**

```bash
cd software/ble-charging-station
pip install -r requirements.txt
python app.py  # 访问 http://localhost:5223
```

---

### BLE Gateway

> 路径: `software/esp32-ble-gateway/`

面向企业的分布式监控方案，通过 ESP32-S3 网关实现多站点集中管理。

**核心特性**

- 多网关集群管理
- MQTT 消息总线
- SQLite 历史数据持久化
- Docker 一键部署
- WebSocket 毫秒级推送

**系统架构**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │     │   Backend    │     │    MQTT      │
│   Mobile     │◄───►│   FastAPI    │◄───►│  Mosquitto   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┼────────────────────────────┐
                     │                            │                            │
              ┌──────▼──────┐              ┌──────▼──────┐              ┌──────▼──────┐
              │  ESP32-S3   │              │  ESP32-S3   │              │  ESP32-S3   │
              │   Gateway   │              │   Gateway   │              │   Gateway   │
              └──────┬──────┘              └──────┬──────┘              └──────┬──────┘
                     │ BLE                        │ BLE                        │ BLE
              ┌──────▼──────┐              ┌──────▼──────┐              ┌──────▼──────┐
              │    CP02     │              │    CP02     │              │    CP02     │
              │   Station   │              │   Station   │              │   Station   │
              └─────────────┘              └─────────────┘              └─────────────┘
```

**快速开始**

```bash
# Docker 部署
cd software/esp32-ble-gateway/docker
docker-compose up -d  # 访问 http://localhost:5225

# 本地开发
cd software/esp32-ble-gateway/backend
pip install -r requirements.txt
python app.py
```

---

### 项目结构

```
cp02-ble/
├── hardware/                              # 硬件固件
│   ├── arduino/                           # Arduino 实现
│   └── esp32/                             # ESP32 子模块 (IonBridge)
│
├── software/                              # 软件方案
│   ├── web-controller/
│   │   └── ionbridge-ble-controller/      # BLE 控制器
│   ├── ble-charging-station/              # 可视化监控
│   ├── esp32-ble-gateway/                 # 分布式网关
│   └── python-scripts/                    # 辅助脚本
│
└── docs/                                  # 文档
    └── guides/                            # 使用指南
```

### 技术栈

| 层级 | 技术选型 |
|:-----|:---------|
| **后端框架** | FastAPI, Uvicorn |
| **BLE 通信** | Bleak (跨平台) |
| **实时通信** | WebSocket |
| **数据可视化** | Chart.js, Three.js |
| **消息队列** | MQTT (Mosquitto) |
| **容器化** | Docker, Docker Compose |
| **嵌入式** | ESP32-S3, PlatformIO |

### 支持的协议

<details>
<summary>点击展开完整协议列表</summary>

| 类别 | 协议 |
|:-----|:-----|
| **USB PD** | PD, PPS, QC 4.0, QC 4+ |
| **快充** | QC 2.0, QC 3.0, QC 3+, AFC, FCP, UFCS |
| **私有** | VOOC, Dash/Warp, SCP (HV/LV), SFCP |
| **兼容** | Apple 5V, Samsung 5V, BC1.2 |

</details>

---

## English

### Overview

CP02-BLE is a comprehensive BLE control and monitoring solution for IonBridge CP02 series charging stations. The project offers three implementation approaches covering scenarios from development debugging to enterprise deployment.

### Solutions

| Solution | Target | Core Capabilities | Use Cases |
|:---------|:-------|:------------------|:----------|
| **BLE Controller** | Developers | Full 78 BLE commands | Development, Protocol research |
| **Charging Station** | End Users | 3D UI, Real-time charts | Personal monitoring |
| **BLE Gateway** | Enterprise | MQTT, Multi-gateway, History | Multi-site management |

### Quick Start

```bash
# BLE Controller (Developer Tool)
cd software/web-controller/ionbridge-ble-controller
pip install -r requirements.txt && python app.py

# Charging Station (Visual Monitor)
cd software/ble-charging-station
pip install -r requirements.txt && python app.py

# BLE Gateway (Distributed)
cd software/esp32-ble-gateway/docker
docker-compose up -d
```

---

## Contributing

We welcome contributions! Please see our contributing guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2023 在虎 (�poboll)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## Acknowledgments

- [IonBridge](https://github.com/ifanrx/IonBridge) - Original open-source project
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Bleak](https://github.com/hbldh/bleak) - Cross-platform BLE library

---

<div align="center">

**[Report Bug](https://github.com/poboll/cp02-ble/issues) · [Request Feature](https://github.com/poboll/cp02-ble/issues)**

Made with :heart: by [poboll](https://github.com/poboll)

</div>
