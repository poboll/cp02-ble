# CP02-BLE

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Arduino](https://img.shields.io/badge/Arduino-1.8+-orange.svg)
![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.4-red.svg)

**IonBridge BLE 设备控制与安全研究项目**

[快速开始](#快速开始) • [项目架构](#项目架构) • [文档](#文档) • [贡献指南](#贡献指南)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [项目架构](#项目架构)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [文档](#文档)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [免责声明](#免责声明)

---

## 项目简介

CP02-BLE 是一个综合性的 IonBridge BLE 设备控制与安全研究项目，包含硬件固件、软件控制器以及相关的安全研究工具。本项目旨在为 IonBridge 充电器设备提供完整的控制解决方案，并支持安全研究。

### 核心组件

1. **BLE 蜜罐/诱捕器** - 基于 BW16 (RTL8720DN) 的 BLE 仿真设备
2. **Web 控制器** - 基于 FastAPI 的 Web 界面控制器
3. **Python 脚本工具** - 命令行工具和实用脚本
4. **ESP32 固件** - 厂家提供的原始固件代码（Git 子模块）

---

## 项目架构

```
cp02-ble/
├── docs/                      # 文档目录
│   ├── guides/               # 使用指南
│   └── archive/              # 归档文档（已忽略）
├── hardware/                  # 硬件相关代码
│   ├── arduino/              # Arduino 固件
│   └── esp32/                # ESP32 固件
└── software/                  # 软件控制器
    ├── python-scripts/       # Python 脚本工具
    └── web-controller/       # Web 控制器
```

---

## 功能特性

### BLE 蜜罐/诱捕器

- ✅ 高仿真 BLE 广播
- ✅ 完整的厂商数据伪装
- ✅ 双特征值模拟（Notify/Read + Write）
- ✅ 实时数据捕获
- ✅ 自动重连机制

### Web 控制器

- ✅ 自动 Token 管理（每 5 分钟刷新）
- ✅ 设备自动重连
- ✅ 完整功能支持（60+ 蓝牙命令）
- ✅ 命令行测试工具
- ✅ Web 界面控制
- ✅ WebSocket 实时通信

### Python 脚本工具

- ✅ BLE 设备管理
- ✅ WiFi 配置
- ✅ 设备重启
- ✅ 控制台交互

---

## 快速开始

### 前置要求

- Python 3.8+
- Arduino IDE 1.8+
- ESP-IDF v5.4
- BW16 (RTL8720DN) 开发板
- ESP32 开发板（可选）

### 安装 Web 控制器

```bash
# 克隆仓库
git clone https://github.com/yourusername/cp02-ble.git
cd cp02-ble

# 安装依赖
cd software/web-controller/ionbridge-ble-controller
pip install -r requirements.txt

# 启动 Web 服务器
python app.py
```

访问 `http://localhost:8000` 打开 Web 界面。

### 使用命令行工具

```bash
# 启动命令行控制器
python cli_controller.py

# 扫描设备
> scan

# 连接设备
> connect CP02-002548

# 查看端口状态
> status

# 打开端口 0
> on 0
```

### 编译 Arduino 固件

1. 安装 Arduino IDE
2. 添加 Realtek Ameba Boards 支持包：
   ```
   https://github.com/ambiot/ambd_arduino/raw/master/Arduino_package/package_realtek.com_ameba_index.json
   ```
3. 安装 AmebaBLE 库
4. 打开 [`hardware/arduino/cp02-ble.ino`](hardware/arduino/cp02-ble.ino)
5. 编译并上传到 BW16 开发板

---

## 文档

### 使用指南

- [IonBridge BLE 完整指南](docs/guides/IonBridge_BLE_Complete_Guide.md)
- [Web 控制器快速开始](docs/guides/QUICKSTART.md)
- [Web 界面使用指南](docs/guides/WEB_INTERFACE_GUIDE.md)

### 子项目文档

- [Arduino 固件说明](hardware/arduino/)
- [Web 控制器文档](software/web-controller/ionbridge-ble-controller/README.md)
- [ESP32 固件文档](hardware/esp32/IonBridge-main/README.md)

---

## 技术栈

### 硬件

- **BW16 (RTL8720DN)** - 双频 Wi-Fi + BLE 5.0
- **ESP32** - 微控制器

### 软件框架

- **Arduino** - 嵌入式开发框架
- **ESP-IDF** - Espressif IoT 开发框架

### 编程语言

- **Python** - 控制器和脚本
- **C++** - 固件开发
- **JavaScript** - Web 前端

### 主要库

- **Bleak** - Python BLE 库
- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **WebSockets** - 实时通信

---

## 项目结构

```
cp02-ble/
├── docs/                          # 文档目录
│   ├── guides/                   # 使用指南
│   │   ├── IonBridge_BLE_Complete_Guide.md
│   │   ├── QUICKSTART.md
│   │   └── WEB_INTERFACE_GUIDE.md
│   └── archive/                  # 归档文档（已忽略）
│       ├── plans/
│       └── *.md
├── hardware/                      # 硬件相关代码
│   ├── arduino/                  # Arduino 固件
│   │   ├── cp02-ble.ino          # BLE 蜜罐主程序
│   │   ├── debug.h               # 调试头文件
│   │   ├── wifi_cust_tx.cpp      # WiFi 自定义传输
│   │   └── wifi_cust_tx.h
│   └── esp32/                    # ESP32 固件
│       └── IonBridge-main/       # 厂家原始代码（Git 子模块）
│           ├── components/       # 组件目录
│           ├── main/             # 主程序
│           └── configs/          # 配置文件
└── software/                      # 软件控制器
    ├── python-scripts/           # Python 脚本工具
    │   ├── ble.py                # BLE 主脚本
    │   ├── ble_console.py        # BLE 控制台
    │   ├── ble_close.py          # BLE 关闭
    │   ├── ble_unbind.py         # BLE 解绑
    │   ├── check_wifi.py         # WiFi 检查
    │   ├── know.py               # 知识库
    │   ├── reboot_2548.py        # 重启脚本
    │   └── set_wifi.py           # WiFi 设置
    └── web-controller/           # Web 控制器
        └── ionbridge-ble-controller/
            ├── app.py            # Web 应用主程序
            ├── ble_manager.py    # BLE 管理器
            ├── cli_controller.py # 命令行控制器
            ├── protocol.py       # 协议定义
            ├── static/           # 静态资源
            │   ├── index.html
            │   ├── app.js
            │   └── style.css
            ├── tests/            # 测试文件
            ├── utils/            # 工具脚本
            ├── requirements.txt  # 依赖列表
            └── README.md         # 子项目文档
```

**注意**：`hardware/esp32/IonBridge-main/` 是一个 Git 子模块，链接到厂家的官方仓库：https://github.com/ifanrx/IonBridge

克隆仓库时需要初始化子模块：

```bash
git submodule update --init --recursive
```

---

## 贡献指南

我们欢迎任何形式的贡献！请遵循以下步骤：

### 报告问题

如果您发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/yourusername/cp02-ble/issues) 确保问题未被报告
2. 创建新的 Issue，详细描述问题或建议
3. 提供重现步骤和环境信息

### 提交代码

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 代码规范

- Python 代码遵循 PEP 8 规范
- C++ 代码遵循 Google C++ Style Guide
- 提交信息使用清晰的描述性语言
- 为新功能添加测试

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

```
MIT License

Copyright (c) 2024 poboll

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 免责声明

⚠️ **重要提示**

本项目仅供安全研究和教育目的使用。请勿用于任何非法活动。

- 请确保在使用前了解并遵守当地法律法规
- 本工具仅应在获得明确授权的环境中使用
- 不得用于未经授权的设备或网络
- 不得用于侵犯他人隐私或造成损害

使用本工具所造成的任何后果由使用者自行承担，作者不承担任何责任。

---

## 致谢

- [Realtek Ameba](https://www.realtek.com/) - Ameba 开发平台
- [Arduino](https://www.arduino.cc/) - 开源电子原型平台
- [Espressif](https://www.espressif.com/) - ESP-IDF 开发框架
- [IonBridge](https://github.com/ifanrx/IonBridge) - 原始开源项目

---

## 联系方式

- **作者**: poboll
- **项目主页**: [https://github.com/yourusername/cp02-ble](https://github.com/yourusername/cp02-ble)
- **问题反馈**: [https://github.com/yourusername/cp02-ble/issues](https://github.com/yourusername/cp02-ble/issues)

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

</div>
