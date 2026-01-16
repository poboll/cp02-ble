# ESP32 固件

<div align="center">

![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.4-red.svg)
![C++](https://img.shields.io/badge/C++-17-blue.svg)
![License](https://img.shields.io/badge/license-CERN%20OHL%20S%20v2-green.svg)

**IonBridge ESP32 固件 - 厂家原始代码**

[快速开始](#快速开始) • [开发环境](#开发环境) • [项目结构](#项目结构)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [开发环境](#开发环境)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [组件说明](#组件说明)
- [编译和烧录](#编译和烧录)
- [故障排除](#故障排除)

---

## 项目简介

本目录包含 IonBridge 设备的 ESP32 固件代码，这是由 ifanr / CANDYSIGN 开发的开源电源管理模块。

**注意**：`IonBridge-main` 是一个 Git 子模块，链接到厂家的官方仓库：https://github.com/ifanrx/IonBridge

### 克隆仓库时初始化子模块

如果您是首次克隆此仓库，需要初始化并更新子模块：

```bash
# 克隆仓库
git clone https://github.com/yourusername/cp02-ble.git
cd cp02-ble

# 初始化并更新子模块
git submodule update --init --recursive
```

### 更新子模块

如果厂家更新了固件代码，您可以更新子模块到最新版本：

```bash
# 更新子模块到最新版本
git submodule update --remote

# 或者进入子模块目录手动更新
cd hardware/esp32/IonBridge-main
git pull origin main
cd ../..
git add hardware/esp32/IonBridge-main
git commit -m "Update IonBridge submodule"
```

### 许可证

请参阅 [IonBridge-main/LICENSE](IonBridge-main/LICENSE) 文件以了解更多详细信息。

我们欢迎非商业用途和小批量（单一型号总生产量小于等于一百台）使用。然而，对于大批量或盈利生产，需要获得商业许可。

请注意，虽然这是一个开源软件项目，但这并不意味着我们放弃了对该项目的版权。

---

## 开发环境

### 前置要求

- macOS / Linux / Windows
- CMake 3.5+
- Ninja
- dfu-util
- Python 3.8+

### 安装依赖

#### macOS

```bash
brew install cmake ninja dfu-util python3
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install git cmake ninja-build dfu-util python3 python3-pip
```

---

## 快速开始

### 获取 ESP-IDF

克隆 ESP-IDF 仓库并设置：

```bash
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.4
```

### 更新子模块

更新 ESP-IDF 子模块：

```bash
cd ~/esp/esp-idf
git submodule update --init --recursive
```

### 安装 ESP-IDF 工具

运行安装脚本安装 ESP-IDF 工具：

```bash
./install.sh all
```

### 设置环境变量

设置所需的环境变量：

```bash
. $HOME/esp/esp-idf/export.sh
```

或者，您可以添加以下别名到您的 shell 配置文件以便于使用：

```bash
alias get_idf='. $HOME/esp/esp-idf/export.sh'
```

---

## 项目结构

```
IonBridge-main/
├── components/              # 组件目录
│   ├── acdc/              # ACDC 组件
│   ├── app/               # 应用程序组件
│   ├── ble/               # BLE 组件
│   ├── chip_data_types/    # 芯片数据类型
│   ├── controller/        # 控制器组件
│   ├── display/           # 显示组件
│   ├── firmware/          # 固件组件
│   ├── fpga/              # FPGA 组件
│   ├── handler/           # 处理器组件
│   ├── logging/           # 日志组件
│   ├── machine_info/      # 机器信息组件
│   ├── mqtt_app/          # MQTT 应用组件
│   ├── mqtt_message/      # MQTT 消息组件
│   ├── nvs_data/          # NVS 数据组件
│   ├── port/              # 端口组件
│   ├── rpc/               # RPC 组件
│   ├── service/           # 服务组件
│   ├── storage/           # 存储组件
│   ├── task/              # 任务组件
│   ├── uart/              # UART 组件
│   ├── utils/             # 工具组件
│   ├── version/           # 版本组件
│   ├── web_server/        # Web 服务器组件
│   └── wifi/              # WiFi 组件
├── main/                  # 主程序
│   ├── main.cpp
│   └── CMakeLists.txt
├── configs/               # 配置文件
│   ├── sdkconfig.develop
│   └── sdkconfig.fake
├── HummingBoard/          # HummingBoard 开发板
│   ├── CNC Plate.step
│   ├── PCB.step
│   └── Schematic Prints.PDF
├── mqtt_server/           # MQTT 服务器
│   ├── docker-compose.yml
│   └── emqx.conf
├── CMakeLists.txt
├── sdkconfig.defaults
└── README.md
```

---

## 组件说明

### 核心组件

| 组件 | 描述 |
|------|------|
| [`app/`](IonBridge-main/components/app/) | 主应用程序逻辑 |
| [`ble/`](IonBridge-main/components/ble/) | BLE 通信协议实现 |
| [`controller/`](IonBridge-main/components/controller/) | 设备控制器 |
| [`port/`](IonBridge-main/components/port/) | 端口管理 |

### 功能组件

| 组件 | 描述 |
|------|------|
| [`display/`](IonBridge-main/components/display/) | 显示管理 |
| [`wifi/`](IonBridge-main/components/wifi/) | WiFi 连接管理 |
| [`mqtt_app/`](IonBridge-main/components/mqtt_app/) | MQTT 通信 |
| [`firmware/`](IonBridge-main/components/firmware/) | 固件升级 |
| [`ota_handler/`](IonBridge-main/components/handler/ota_handler.cpp) | OTA 处理 |

### 硬件组件

| 组件 | 描述 |
|------|------|
| [`acdc/`](IonBridge-main/components/acdc/) | ACDC 转换 |
| [`fpga/`](IonBridge-main/components/fpga/) | FPGA 通信 |
| [`chip_data_types/`](IonBridge-main/components/chip_data_types/) | 芯片数据类型定义 |

### 工具组件

| 组件 | 描述 |
|------|------|
| [`logging/`](IonBridge-main/components/logging/) | 日志系统 |
| [`storage/`](IonBridge-main/components/storage/) | 存储管理 |
| [`utils/`](IonBridge-main/components/utils/) | 通用工具 |

---

## 编译和烧录

### 配置目标

导航到项目根目录并设置 ESP32 目标：

```bash
cd IonBridge-main
idf.py set-target esp32c3
```

### 复制配置文件

复制 sdkconfig.develop 或 sdkconfig.fake 到 sdkconfig：

```bash
cp configs/sdkconfig.develop sdkconfig
```

### 编译项目

使用以下命令编译项目：

```bash
idf.py build
```

### 烧录到设备

编译成功后，烧录到设备：

```bash
idf.py -p /dev/ttyUSB0 flash
```

### 监视串口输出

监视串口输出以查看设备日志：

```bash
idf.py -p /dev/ttyUSB0 monitor
```

### 一键编译、烧录和监视

```bash
idf.py -p /dev/ttyUSB0 flash monitor
```

---

## HummingBoard

HummingBoard 是为本项目中的电源适配器设计的全功能开发板，专为开发和测试而设计。

- **综合功能**：为电源转换提供完整的开发环境
- **原理图支持**：您可以在 [HummingBoard](IonBridge-main/HummingBoard/) 中找到详细的原理图和相关文档

---

## 故障排除

### 编译错误

- 确认 ESP-IDF 环境变量已正确设置
- 检查是否安装了所有依赖项
- 尝试清理构建目录：`idf.py fullclean`

### 烧录失败

- 检查 USB 连接
- 确认串口设备路径正确
- 尝试按住 BOOT 键后点击烧录
- 检查设备是否处于下载模式

### 设备不启动

- 检查串口监视器中的错误信息
- 确认固件已正确烧录
- 尝试恢复出厂设置

---

## 贡献

项目仍处于早期阶段。我们目前正在与法律团队一起整理版权问题，以确保我们能够合法地获得永久、非独占的贡献许可，同时保持符合相关法律框架。

因此，我们目前无法接受外部贡献。请关注更新！一旦问题解决，您将被要求签署贡献者许可协议（CLA）以授权我们非独占地使用您的版权作品。

---

## 缺失功能

电源分配的专有实现是专利功能，不包含在本仓库的开源范围内。

---

## 相关文档

- [主项目 README](../../../README.md)
- [Arduino 固件](../arduino/README.md)
- [Web 控制器](../../../software/web-controller/ionbridge-ble-controller/README.md)

---

## 许可证

本项目采用 CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-S-v2)

详见 [IonBridge-main/cern_ohl_s_v2.txt](IonBridge-main/cern_ohl_s_v2.txt) 文件

---

## 致谢

- [Espressif](https://www.espressif.com/) - ESP-IDF 开发框架
- [ifanr / CANDYSIGN](https://github.com/ifanrx/IonBridge) - 原始开源项目

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

</div>
