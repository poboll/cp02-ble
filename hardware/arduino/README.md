# Arduino 固件

<div align="center">

![Arduino](https://img.shields.io/badge/Arduino-1.8+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**基于 BW16 (RTL8720DN) 的 BLE 蜜罐/诱捕器固件**

[快速开始](#快速开始) • [功能特性](#功能特性) • [配置说明](#配置说明)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [硬件要求](#硬件要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用说明](#使用说明)
- [故障排除](#故障排除)

---

## 项目简介

本项目实现了一个高仿真的 BLE 蜜罐设备，通过伪装成真实的"小电拼"充电器设备，诱导手机 App 连接并捕获其发送的配对 PIN 码或验证 Token。

---

## 功能特性

### 1. 高仿真广播

- 设备名称: `CP02-0002A0`
- Service UUID: `048E3F2E-E1A6-4707-9E74-A930E898A1EA`
- Manufacturer Data: `0x36E9` + `0x6C80AB0002A101`
- 完整的厂商数据伪装，防止 App 过滤

### 2. 双特征值模拟

- **特征值 1** (Notify/Read): `148E3F2E-E1A6-4707-9E74-A930E898A1EA`
  - 属性: READ | NOTIFY
  - 支持订阅事件检测
- **特征值 2** (Write): `248E3F2E-E1A6-4707-9E74-A930E898A1EA`
  - 属性: WRITE | WRITE_NO_RESPONSE
  - 捕获 App 写入的数据

### 3. 数据捕获

- 实时捕获 App 写入的数据
- 同时输出 HEX 和 ASCII 两种格式
- 显示数据长度和时间戳
- 订阅事件检测

### 4. 自动重连

- 断开连接后自动重启广播
- 无需手动复位开发板

---

## 硬件要求

- **开发板**: BW16 (RTL8720DN) - 双频 Wi-Fi + BLE 5.0
- **开发框架**: Arduino IDE
- **库依赖**: Realtek AmebaBLE (Realtek 官方库)

---

## 快速开始

### 1. 准备开发环境

1. 安装 Arduino IDE
2. 添加 Realtek Ameba Boards 支持包:
   - 打开 Arduino IDE → 文件 → 首选项
   - 在"附加开发板管理器网址"中添加:
     ```
     https://github.com/ambiot/ambd_arduino/raw/master/Arduino_package/package_realtek.com_ameba_index.json
     ```
3. 打开 工具 → 开发板 → 开发板管理器
4. 搜索 "Realtek Ameba" 并安装

### 2. 安装 AmebaBLE 库

1. 打开 Arduino IDE → 工具 → 管理库
2. 搜索 "AmebaBLE"
3. 安装 Realtek 官方的 AmebaBLE 库

### 3. 编译上传

1. 选择开发板: **Realtek Ameba ARM (Cortex-M4) Boards** → **BW16**
2. 打开 [`cp02-ble.ino`](cp02-ble.ino)
3. 点击上传按钮
4. 打开串口监视器（波特率 115200）

---

## 配置说明

所有关键参数都在代码顶部的配置区域定义，可以根据实际抓取到的参数进行修改:

```cpp
// 设备广播名称
#define DEVICE_NAME "CP02-0002A0"

// 服务 UUID
#define SERVICE_UUID "048E3F2E-E1A6-4707-9E74-A930E898A1EA"

// 特征值 UUID
#define CHARACTERISTIC_UUID_NOTIFY "148E3F2E-E1A6-4707-9E74-A930E898A1EA"
#define CHARACTERISTIC_UUID_WRITE "248E3F2E-E1A6-4707-9E74-A930E898A1EA"

// Manufacturer Data
const uint8_t MANUFACTURER_DATA[] = {
    0xE9, 0x36,             // 厂商 ID (0x36E9, 小端序)
    0x6C, 0x80, 0xAB, 0x00, // 数据部分
    0x02, 0xA1, 0x01        // 数据部分
};
```

---

## 使用说明

### 串口输出示例

```
========================================
  BLE 蜜罐/诱捕器启动中...
  目标设备: BW16 (RTL8720DN)
========================================

正在初始化BLE模块...
BLE模块初始化完成
正在创建BLE服务器...
BLE服务器创建完成
正在创建BLE服务...
服务UUID: 048E3F2E-E1A6-4707-9E74-A930E898A1EA
正在创建 BLE 特征值 1 (Notify/Read)...
特征值 1 UUID: 148E3F2E-E1A6-4707-9E74-A930E898A1EA
特征值 1 属性: READ | NOTIFY
正在创建 BLE 特征值 2 (Write)...
特征值 2 UUID: 248E3F2E-E1A6-4707-9E74-A930E898A1EA
特征值 2 属性: WRITE | WRITE_NO_RESPONSE
正在启动服务...
服务启动完成
正在配置广播参数...
正在设置 Manufacturer Data...
厂商数据 (HEX): 0xe9 0x36 0x6c 0x80 0xab 0x0 0x2 0xa1 0x1
正在启动广播...
广播已启动

========================================
  BLE 蜜罐运行中!
  设备名称: CP02-0002A0
  Service UUID: 048E3F2E-E1A6-4707-9E74-A930E898A1EA
  特征值 1 (Notify/Read): 148E3F2E-E1A6-4707-9E74-A930E898A1EA
  特征值 2 (Write): 248E3F2E-E1A6-4707-9E74-A930E898A1EA
  厂商 ID: 0x36E9
  等待手机App连接...
========================================

========== 连接事件 ==========
设备已连接
============================

========== 订阅事件 ==========
App 已订阅通知
==============================

==== 捕获到数据 ====
Recv: 0x31 0x32 0x33 0x34
ASCII: "1234"
长度: 4
时间戳: 12345
===================
```

---

## 故障排除

### 无法上传固件

- 检查 USB 连接
- 确认选择了正确的开发板
- 尝试按住 BOOT 键后点击上传

### BLE 无法启动

- 检查 AmebaBLE 库是否正确安装
- 确认开发板型号选择正确
- 检查串口监视器是否有错误信息

### 无法扫描到设备

- 确认广播已启动
- 检查设备名称和 UUID 配置
- 尝试重启开发板

---

## 文件说明

- [`cp02-ble.ino`](cp02-ble.ino) - BLE 蜜罐主程序
- [`debug.h`](debug.h) - 调试头文件
- [`wifi_cust_tx.cpp`](wifi_cust_tx.cpp) - WiFi 自定义传输实现
- [`wifi_cust_tx.h`](wifi_cust_tx.h) - WiFi 自定义传输头文件

---

## 注意事项

⚠️ **免责声明**

本项目仅供安全研究和教育目的使用。请勿用于任何非法活动。使用本工具所造成的任何后果由使用者自行承担，作者不承担任何责任。

- 请确保在使用前了解并遵守当地法律法规
- 本工具仅应在获得明确授权的环境中使用
- 不得用于未经授权的设备或网络
- 不得用于侵犯他人隐私或造成损害

---

## 许可证

本项目采用 MIT 许可证 - 详见项目根目录 [LICENSE](../../LICENSE) 文件

---

## 致谢

- Realtek Ameba 开发团队
- Arduino 社区

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

</div>
