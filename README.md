<div align="center">

# CP02-BLE

**IonBridge CP02 充电站 BLE 控制与监控解决方案**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Bleak](https://img.shields.io/badge/Bleak-BLE-00B4D8.svg)](https://github.com/hbldh/bleak)
[![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C.svg?logo=espressif&logoColor=white)](https://platformio.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/poboll/cp02-ble/pulls)

[English](#english) · [简体中文](#简体中文)

</div>

---

## 简体中文

### 简介

CP02-BLE 是针对 IonBridge CP02 系列充电站的完整 BLE 控制与监控解决方案。无论是个人用户通过电脑蓝牙直连实现可视化监控，还是企业通过 ESP32-S3 网关集中管理多个站点，均有对应的开箱即用实现。

| 方案 | 适用场景 | 硬件要求 |
|:-----|:---------|:---------|
| [**单机版**（Charging Station）](#单机版charging-station) | 个人 / 单站点可视化监控 | 电脑蓝牙 |
| [**网关版**（BLE Gateway）](#网关版ble-gateway) | 企业多站点集中管理 | ESP32-S3 + 以太网 |
| [**开发者工具**（BLE Controller）](#开发者工具ble-controller) | 协议调试 / 脚本自动化 | 电脑蓝牙 |

---

### 界面预览

**主监控仪表盘** — 实时展示总功率、电压、电流、蓝牙信号及各端口充电状态与功率曲线

![主监控仪表盘](docs/pic/%E4%B8%BB%E7%9B%91%E6%8E%A7%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

**设备控制中心** — 扫描并连接 CP02 设备，管理 Token，一键控制各端口开关

![设备控制中心](docs/pic/%E8%AE%BE%E5%A4%87%E6%8E%A7%E5%88%B6%E4%B8%AD%E5%BF%83.png)

**设备管理面板** — WiFi 配置、显示亮度、功率分配策略、温控模式等全局设置

![设备管理面板](docs/pic/%E8%AE%BE%E5%A4%87%E7%AE%A1%E7%90%86%E9%9D%A2%E6%9D%BF.png)

**高级端口配置** — 单端口精细配置、原始 BLE 日志回显、CPO 状态 / 温度链 / BLE 包测试

![高级端口配置](docs/pic/%E9%AB%98%E7%BA%A7%E7%AB%AF%E5%8F%A3%E9%85%8D%E7%BD%AE.png)

---

### 单机版（Charging Station）

> 路径：`software/ble-charging-station/`

利用电脑自带蓝牙直连 CP02 充电站，无需额外硬件，开箱即用。

**核心功能**

- 3D 充电站模型 + 粒子呼吸光效
- 实时功率 / 电压 / 电流 / 温度曲线
- 智能线材类型识别（20+ 种）
- WiFi 配置、显示亮度、功率策略、温控模式一站式管理
- Token 自动获取与手动输入双模式

**快速启动**

```bash
cd software/ble-charging-station
pip install -r requirements.txt
python app.py
# 浏览器访问 http://localhost:5223
```

**操作流程**

1. 点击「扫描设备」，等待发现附近的 CP02 充电站
2. 点击目标设备连接，程序自动获取 Token
3. 进入主仪表盘，实时查看各端口状态与功率曲线
4. 点击端口卡片可开关充电、调整协议；顶部导航切换设备管理、高级配置等页面

> **macOS 用户**：首次运行需在「系统设置 → 隐私与安全性 → 蓝牙」中授权终端访问蓝牙。

---

### 网关版（BLE Gateway）

> 路径：`software/esp32-ble-gateway/`

通过 ESP32-S3 硬件网关桥接 BLE 与以太网，配合 MQTT 消息总线实现多站点集中管理。

**核心功能**

- 多网关集群并发管理
- MQTT 消息总线（Mosquitto）
- SQLite 历史数据持久化
- WebSocket 毫秒级实时推送

**系统架构**

```
Browser / Mobile
      │
 FastAPI Backend
      │
 MQTT (Mosquitto)
      │
  ┌───┴───┬───────┐
ESP32-S3  ESP32-S3  ESP32-S3   ← 每个网关通过 BLE 连接一台 CP02
  │         │         │
 CP02      CP02      CP02
```

**Docker 部署（推荐）**

```bash
cd software/esp32-ble-gateway/docker
docker-compose up -d
# 浏览器访问 http://localhost:5225
```

**本地开发**

```bash
cd software/esp32-ble-gateway/backend
pip install -r requirements.txt
python app.py
```

**ESP32-S3 固件烧录**

```bash
cd software/esp32-ble-gateway/firmware
pio run --target upload
```

---

### 开发者工具（BLE Controller）

> 路径：`software/web-controller/ionbridge-ble-controller/`

完整支持 IonBridge 协议定义的全部 78 个 BLE 命令，适合协议调试与脚本自动化。

```bash
cd software/web-controller/ionbridge-ble-controller
pip install -r requirements.txt

python cli_controller.py   # CLI 交互模式
python app.py              # Web API 模式（http://localhost:8000）
```

**常用 CLI 命令**

```
scan                    扫描周边设备
connect CP02-002548     连接指定设备
status                  查看各端口状态
on 0                    开启端口 0
set-config 0 PD,QC3.0  设置端口充电协议
```

---

### 项目结构

```
cp02-ble/
├── hardware/
│   ├── arduino/                           # Arduino 实现
│   └── esp32/                             # ESP32 子模块 (IonBridge)
├── software/
│   ├── ble-charging-station/              # 单机可视化监控
│   ├── esp32-ble-gateway/                 # 分布式网关
│   ├── web-controller/
│   │   └── ionbridge-ble-controller/      # BLE 控制器（开发者工具）
│   └── python-scripts/                    # 辅助脚本
└── docs/
    └── pic/                               # 界面截图
```

---

### 技术栈

| 层级 | 技术 |
|:-----|:-----|
| 后端框架 | FastAPI, Uvicorn |
| BLE 通信 | Bleak（跨平台：macOS / Windows / Linux） |
| 实时通信 | WebSocket |
| 数据可视化 | Chart.js, Three.js |
| 消息队列 | MQTT (Mosquitto) |
| 容器化 | Docker, Docker Compose |
| 嵌入式 | ESP32-S3, PlatformIO |

---

### 支持的充电协议

<details>
<summary>展开查看完整列表</summary>

| 类别 | 协议 |
|:-----|:-----|
| USB PD | PD, PPS, QC 4.0, QC 4+ |
| 快充 | QC 2.0, QC 3.0, QC 3+, AFC, FCP, UFCS |
| 私有协议 | VOOC, Dash/Warp, SCP (HV/LV), SFCP |
| 基础兼容 | Apple 5V, Samsung 5V, BC1.2 |

</details>

---

### 更新日志

#### v1.1.0 · 2026-02-24

**Charging Station（单机版）**

- 新增 3D 充电站可视化模型与粒子呼吸光效
- 新增实时功率曲线、温度曲线、充电会话统计
- 新增智能线材类型识别（20+ 种）
- 新增端口高级配置面板（协议 / 限流 / 温控策略）
- 新增 WiFi 扫描与一键配网
- 新增 Token 自动获取与手动输入支持
- 新增优雅关闭机制，避免 BLE 连接泄漏
- 修复温度数据解析异常
- 优化 WebSocket 断线重连逻辑

**BLE Controller（开发者工具）**

- 完整支持 IonBridge 协议 78 个 BLE 命令
- 新增 RESTful API 模式
- 新增自动 Token 刷新与持久化

#### v0.0.1 · 2024-01-01

- 初始化仓库结构，添加 IonBridge 子模块
- 完成 BLE Headers 适配（Realtek AmebaBLE）

---

## English

### Overview

CP02-BLE is a complete BLE control and monitoring solution for IonBridge CP02 charging stations — from personal single-device monitoring to enterprise multi-site fleet management.

| Solution | Use Case | Hardware |
|:---------|:---------|:---------|
| **Charging Station** (Standalone) | Personal / single-site visual monitoring | PC Bluetooth |
| **BLE Gateway** (Distributed) | Enterprise multi-site management | ESP32-S3 + Ethernet |
| **BLE Controller** (Dev Tool) | Protocol debugging / scripting | PC Bluetooth |

### Quick Start

```bash
# Standalone Monitor
cd software/ble-charging-station
pip install -r requirements.txt && python app.py
# → http://localhost:5223

# Gateway (Docker)
cd software/esp32-ble-gateway/docker
docker-compose up -d
# → http://localhost:5225

# Developer Tool
cd software/web-controller/ionbridge-ble-controller
pip install -r requirements.txt && python app.py
# → http://localhost:8000
```

---

## Contributing

PRs are welcome. Please open an issue first to discuss what you'd like to change.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [IonBridge](https://github.com/ifanrx/IonBridge) — Original open-source firmware
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Bleak](https://github.com/hbldh/bleak) — Cross-platform BLE library for Python

---

<div align="center">

**[Report Bug](https://github.com/poboll/cp02-ble/issues) · [Request Feature](https://github.com/poboll/cp02-ble/issues)**

Made with ♥ by [poboll](https://github.com/poboll)

</div>
