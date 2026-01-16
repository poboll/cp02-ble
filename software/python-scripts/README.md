# Python 脚本工具

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**IonBridge BLE 设备 Python 脚本工具集**

[快速开始](#快速开始) • [工具列表](#工具列表) • [使用示例](#使用示例)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [工具列表](#工具列表)
- [快速开始](#快速开始)
- [使用示例](#使用示例)
- [依赖要求](#依赖要求)

---

## 项目简介

本目录包含用于控制 IonBridge BLE 设备的 Python 脚本工具集。这些工具提供了设备管理、WiFi 配置、设备重启等基础功能。

---

## 工具列表

| 脚本文件 | 功能描述 | 使用场景 |
|---------|---------|---------|
| [`ble.py`](ble.py) | BLE 主脚本 | 设备连接和数据交互 |
| [`ble_console.py`](ble_console.py) | BLE 控制台 | 交互式命令行界面 |
| [`ble_close.py`](ble_close.py) | BLE 关闭 | 关闭 BLE 连接 |
| [`ble_unbind.py`](ble_unbind.py) | BLE 解绑 | 解绑设备 |
| [`check_wifi.py`](check_wifi.py) | WiFi 检查 | 检查 WiFi 连接状态 |
| [`set_wifi.py`](set_wifi.py) | WiFi 设置 | 配置 WiFi 网络 |
| [`reboot_2548.py`](reboot_2548.py) | 设备重启 | 重启指定设备 |
| [`know.py`](know.py) | 知识库 | 设备信息查询 |

---

## 快速开始

### 前置要求

- Python 3.8+
- 蓝牙适配器
- IonBridge BLE 设备

### 安装依赖

```bash
pip install bleak
```

### 基本使用

```bash
# 运行 BLE 主脚本
python ble.py

# 启动 BLE 控制台
python ble_console.py

# 检查 WiFi 状态
python check_wifi.py

# 设置 WiFi
python set_wifi.py <SSID> <PASSWORD>
```

---

## 使用示例

### BLE 主脚本

```bash
# 连接到设备
python ble.py CP02-002548

# 扫描设备
python ble.py --scan

# 查看帮助
python ble.py --help
```

### BLE 控制台

```bash
# 启动交互式控制台
python ble_console.py

# 在控制台中可用命令：
> scan                    # 扫描设备
> connect <address>       # 连接设备
> disconnect              # 断开连接
> status                  # 查看状态
> quit                    # 退出
```

### WiFi 配置

```bash
# 检查当前 WiFi 状态
python check_wifi.py

# 设置新的 WiFi 网络
python set_wifi.py MyNetwork MyPassword

# 重启设备
python reboot_2548.py
```

---

## 依赖要求

```txt
bleak>=0.19.0
```

安装所有依赖：

```bash
pip install -r requirements.txt
```

---

## 脚本详细说明

### ble.py

BLE 主脚本，提供基础的设备连接和数据交互功能。

**用法：**
```bash
python ble.py [OPTIONS] [ADDRESS]
```

**选项：**
- `--scan` - 扫描附近的 BLE 设备
- `--help` - 显示帮助信息

### ble_console.py

交互式 BLE 控制台，提供命令行界面进行设备管理。

**可用命令：**
- `scan` - 扫描设备
- `connect <address>` - 连接设备
- `disconnect` - 断开连接
- `status` - 查看状态
- `quit` - 退出控制台

### ble_close.py

关闭当前活动的 BLE 连接。

**用法：**
```bash
python ble_close.py
```

### ble_unbind.py

解绑已绑定的设备。

**用法：**
```bash
python ble_unbind.py <DEVICE_ADDRESS>
```

### check_wifi.py

检查设备的 WiFi 连接状态。

**用法：**
```bash
python check_wifi.py
```

### set_wifi.py

配置设备的 WiFi 网络连接。

**用法：**
```bash
python set_wifi.py <SSID> <PASSWORD>
```

**参数：**
- `SSID` - WiFi 网络名称
- `PASSWORD` - WiFi 密码

### reboot_2548.py

重启指定的 IonBridge 设备。

**用法：**
```bash
python reboot_2548.py [DEVICE_ADDRESS]
```

### know.py

查询设备的各种信息。

**用法：**
```bash
python know.py [OPTIONS]
```

---

## 故障排除

### 无法扫描到设备

- 确认设备已开机
- 确认设备在蓝牙范围内
- 检查系统蓝牙权限
- 尝试重启蓝牙适配器

### 连接失败

- 检查设备地址是否正确
- 确认设备未被其他应用连接
- 尝试重启设备
- 检查蓝牙适配器状态

### WiFi 配置失败

- 确认 WiFi 网络名称和密码正确
- 检查设备是否支持 WiFi
- 尝试重启设备后重新配置

---

## 注意事项

⚠️ **使用提示**

- 确保在使用前了解设备的功能和限制
- 遵循当地法律法规使用这些工具
- 不要用于未经授权的设备
- 保护好敏感信息（如 WiFi 密码）

---

## 许可证

本项目采用 MIT 许可证 - 详见项目根目录 [LICENSE](../../LICENSE) 文件

---

## 相关文档

- [主项目 README](../../README.md)
- [Web 控制器](../web-controller/ionbridge-ble-controller/README.md)
- [Arduino 固件](../../hardware/arduino/README.md)

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

</div>
