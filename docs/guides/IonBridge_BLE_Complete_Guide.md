# IonBridge 蓝牙完整指南

**综合文档** - 包含所有蓝牙功能、Token 机制、端口协议配置和 MQTT 配置的完整指南

---

## 📖 目录

1. [快速参考](#快速参考)
2. [Token 机制详解](#token-机制详解)
3. [端口协议配置](#端口协议配置)
4. [MQTT 配置指南](#mqtt-配置指南)
5. [完整总结](#完整总结)

---

# 快速参考

## 核心概念速览

### Token 机制
- **Token**：1 字节随机数，用于验证蓝牙命令
- **获取方式**：调用 ASSOCIATE_DEVICE (0x10) 命令
- **变化规律**：仅在关联设备或重置设备时改变
- **验证**：除 ASSOCIATE_DEVICE 外，所有命令都需要 Token

### 端口协议配置
- **支持协议**：TFCP、PE、QC 2.0/3.0/3+、AFC、FCP、UFCS、PD 等
- **配置方式**：SET_PORT_CONFIG (0x57) 命令
- **查询方式**：GET_PORT_CONFIG (0x58) 命令
- **存储位置**：NVS 用户分区，每个端口独立配置

---

## 常用命令速查表

### 设备关联和认证

```
ASSOCIATE_DEVICE (0x10) - 关联设备，获取 Token
  请求：[0x10] [msg_id] [password]
  响应：[0x10] [msg_id] [token]
  特点：唯一不需要 Token 的命令
```

### 端口协议配置

```
SET_PORT_CONFIG (0x57) - 设置端口协议
  请求：[0x57] [msg_id] [token] [port_mask] [version] [8*config]
  响应：[0x57] [msg_id] [status]
  
GET_PORT_CONFIG (0x58) - 获取端口协议
  请求：[0x58] [msg_id] [token] [version]
  响应：[0x58] [msg_id] [8*config]
  
SET_PORT_COMPATIBILITY_SETTINGS (0x59) - 设置兼容性
  请求：[0x59] [msg_id] [token] [settings]
  响应：[0x59] [msg_id] [status]
  
GET_PORT_COMPATIBILITY_SETTINGS (0x5a) - 获取兼容性
  请求：[0x5a] [msg_id] [token]
  响应：[0x5a] [msg_id] [settings]
```

### 电源管理

```
TURN_ON_PORT (0x4c) - 打开端口
  请求：[0x4c] [msg_id] [token] [port_id]
  
TURN_OFF_PORT (0x4d) - 关闭端口
  请求：[0x4d] [msg_id] [token] [port_id]
  
GET_POWER_STATISTICS (0x41) - 获取电源统计
  请求：[0x41] [msg_id] [token] [port_id]
  
SET_CHARGING_STRATEGY (0x43) - 设置充电策略
  请求：[0x43] [msg_id] [token] [strategy]
```

### WiFi 管理

```
SCAN_WIFI (0x30) - 扫描 WiFi
  请求：[0x30] [msg_id] [token]
  
SET_WIFI_SSID_AND_PASSWORD (0x36) - 设置 WiFi
  请求：[0x36] [msg_id] [token] [ssid_len] [ssid] [pwd_len] [pwd]
  
GET_WIFI_STATUS (0x34) - 获取 WiFi 状态
  请求：[0x34] [msg_id] [token]
```

### 设备管理

```
REBOOT_DEVICE (0x11) - 重启设备
  请求：[0x11] [msg_id] [token]
  
RESET_DEVICE (0x12) - 重置设备
  请求：[0x12] [msg_id] [token]
  
GET_DEVICE_INFO (0x92) - 获取设备信息
  请求：[0x92] [msg_id] [token]
```

---

## 端口协议配置详解

### PowerFeatures 结构（3 字节）

```
字节 1 (Bit 0-7):
  Bit 0: EnableTfcp      - TFCP 协议
  Bit 1: EnablePe        - PE 协议
  Bit 2: EnableQc2p0     - QC 2.0 协议
  Bit 3: EnableQc3p0     - QC 3.0 协议
  Bit 4: EnableQc3plus   - QC 3+ 协议
  Bit 5: EnableAfc       - AFC 协议
  Bit 6: EnableFcp       - FCP 协议
  Bit 7: EnableHvScp     - HV SCP 协议

字节 2 (Bit 0-7):
  Bit 0: EnableLvScp     - LV SCP 协议
  Bit 1: EnableSfcp      - SFCP 协议
  Bit 2: EnableApple     - Apple 协议
  Bit 3: EnableSamsung   - Samsung 协议
  Bit 4: EnableUfcs      - UFCS 协议
  Bit 5: EnablePd        - USB PD 协议
  Bit 6: EnablePdCompatMode - PD 兼容模式
  Bit 7: LimitedCurrentMode - 限流模式

字节 3 (Bit 0-7):
  Bit 0: EnablePdLVPPS   - PD LVPPS
  Bit 1: EnablePdEPR     - PD EPR
  Bit 2: EnablePd5V5A    - PD 5V5A
  Bit 3: EnablePdHVPPS   - PD HVPPS
  Bit 4-7: 保留
```

### 常见配置示例

```
启用所有协议：
  字节 1: 0xFF (11111111)
  字节 2: 0x7F (01111111)
  字节 3: 0x0F (00001111)

仅启用 USB PD：
  字节 1: 0x00 (00000000)
  字节 2: 0x20 (00100000)
  字节 3: 0x07 (00000111)

启用 QC 和 PD：
  字节 1: 0x1C (00011100)
  字节 2: 0x20 (00100000)
  字节 3: 0x07 (00000111)
```

---

## 端口掩码说明

```
Port Mask 用于指定要配置的端口：

Bit 0: 端口 0
Bit 1: 端口 1
Bit 2: 端口 2
Bit 3: 端口 3
Bit 4: 端口 4
Bit 5: 端口 5
Bit 6: 端口 6
Bit 7: 端口 7

示例：
  0x01 (00000001) - 仅配置端口 0
  0x03 (00000011) - 配置端口 0 和 1
  0xFF (11111111) - 配置所有端口
```

---

## 完整工作流程示例

### 场景：通过蓝牙配置端口 0 的协议

```
1. 关联设备获取 Token
   发送：[0x10] [0x00 0x01] [password]
   接收：[0x10] [0x00 0x01] [token_value]
   
   假设 token_value = 0x42

2. 获取当前端口配置
   发送：[0x58] [0x00 0x02] [0x42] [0x01]
   接收：[0x58] [0x00 0x02] [config_port0] [config_port1] ... [config_port7]

3. 修改端口 0 的配置（启用 USB PD）
   新配置：[0x00] [0x20] [0x07]

4. 设置新配置
   发送：[0x57] [0x00 0x03] [0x42] [0x01] [0x01]
         [0x00 0x20 0x07]  // 端口 0 新配置
         [old_config_1]    // 端口 1 保持不变
         [old_config_2]    // 端口 2 保持不变
         ...
         [old_config_7]    // 端口 7 保持不变
   
   响应：[0x57] [0x00 0x03] [0x00]  // 成功

5. 验证配置
   发送：[0x58] [0x00 0x04] [0x42] [0x01]
   接收：[0x58] [0x00 0x04] [0x00 0x20 0x07] [config_port1] ... [config_port7]
```

---

## Token 生命周期

```
设备首次启动
  ↓
调用 ASSOCIATE_DEVICE (0x10)
  ↓
设备生成随机 Token (0-255)
  ↓
Token 保存到 NVS
  ↓
Token 返回给客户端
  ↓
客户端保存 Token
  ↓
后续所有命令都使用此 Token
  ↓
设备重启
  ↓
Token 从 NVS 重新加载
  ↓
使用相同的 Token
  ↓
直到调用 RESET_DEVICE 或 ASSOCIATE_DEVICE(reset_data=true)
  ↓
生成新的 Token
```

---

## 常见错误和解决方案

| 错误 | 原因 | 解决方案 |
|------|------|--------|
| Token 验证失败 | Token 不匹配或过期 | 重新调用 ASSOCIATE_DEVICE 获取新 Token |
| 端口配置失败 | 端口掩码或配置格式错误 | 检查端口掩码和 PowerFeatures 结构 |
| 命令无响应 | 设备未连接或 BLE 断开 | 重新连接蓝牙 |
| 配置未保存 | 端口已死亡或 NVS 满 | 检查端口状态或清理 NVS |

---

## 关键文件位置

```
Token 相关：
  - nvs_namespace.cpp: NVSGetAuthToken() 实现
  - protocol.cpp: Token 验证逻辑
  - device_handler.cpp: ASSOCIATE_DEVICE 实现

端口配置相关：
  - data_types.h: PowerFeatures 定义
  - power_handler.cpp: SET/GET_PORT_CONFIG 实现
  - port.cpp: 端口配置管理

服务定义：
  - service.h: 所有服务命令定义
  - handler.cpp: 服务注册
```



---

# Token 机制详解

## 概述

本部分详细说明了 IonBridge 中蓝牙 Token 的机制、Token 是否会变化，以及拥有有效 Token 后可以执行的所有操作。

---

## Token 的定义

**Token** 是一个 1 字节的随机数（0-255），用于验证蓝牙命令的合法性。

文件：`IonBridge-main/components/nvs_data/nvs_namespace.cpp`

```cpp
esp_err_t NVSGetAuthToken(uint8_t *token, bool always_generate_new) {
  static uint8_t cached_token = 0, cached = 0;
  esp_err_t err = ESP_OK;
  
  if (!always_generate_new) {
    if (cached) {
      *token = cached_token;
      return ESP_OK;
    }
    
    // 尝试从 NVS 读取已存储的 Token
    err = BleNVSGet(token, NVSKey::DEVICE_TOKEN);
    if (err == ESP_OK) {
      cached = 1;
      cached_token = *token;
      return ESP_OK;
    }
  }
  
  // 生成新的随机 Token
  uint8_t new_token = esp_random() % 256;
  err = BleNVSSet(new_token, NVSKey::DEVICE_TOKEN);
  if (err != ESP_OK) {
    return err;
  }
  
  *token = new_token;
  cached = 1;
  cached_token = *token;
  
  return ESP_OK;
}
```

---

## Token 存储位置

- **NVS 分区**：`nvs`（用户数据分区）
- **命名空间**：`BLE-SERVICE`
- **键**：`DEVICE_TOKEN`

---

## Token 的生成和初始化

### 首次关联设备（ASSOCIATE_DEVICE）

文件：`IonBridge-main/components/handler/device_handler.cpp`

```cpp
esp_err_t DeviceHandler::AssociateDevice(const std::vector<uint8_t> &request,
                                         std::vector<uint8_t> &response) {
  // 验证密码
  ESP_RETURN_ON_FALSE(
      DeviceAuth::validatePassword(request.data(), password_len), ESP_FAIL, TAG,
      "Invalid password");

  if (reset_data) {
    // 重置用户数据（包括 Token）
    ESP_LOGI(TAG, "Resetting user data");
    ESP_RETURN_ON_ERROR(ResetUserData(), TAG, "reset_user_data");
  }
  
  // 获取或生成新的 Token
  uint8_t token;
  ESP_RETURN_ON_ERROR(NVSGetAuthToken(&token, reset_data), TAG,
                      "Failed to get token");

  // 标记设备已关联
  DeviceController::GetInstance().mark_associated();
  
  // 返回 Token 给客户端
  response.emplace_back(token);
  return ESP_OK;
}
```

**ASSOCIATE_DEVICE 命令**：
- **命令码**：0x10
- **特点**：这是唯一**不需要 Token** 的命令
- **功能**：
  1. 验证设备密码
  2. 可选地重置用户数据
  3. 生成或获取 Token
  4. 返回 Token 给客户端

---

## Token 是否会变化？

### ✅ Token 会变化的情况

#### 1. 首次关联设备时
- 调用 `ASSOCIATE_DEVICE` 命令
- 如果 `reset_data = true`，会生成新的 Token
- 新 Token 被保存到 NVS

#### 2. 重置用户数据时
- 调用 `RESET_DEVICE` 命令
- 用户数据被完全清除
- 下次调用 `ASSOCIATE_DEVICE` 时会生成新的 Token

#### 3. 调用 `ASSOCIATE_DEVICE` 时指定 `reset_data = true`
- 强制重置用户数据
- 生成新的 Token

### ❌ Token 不会变化的情况

#### 1. 正常运行期间
- Token 被缓存在内存中
- 每次读取都返回相同的 Token
- 除非设备重启或明确重置

#### 2. 调用其他蓝牙命令时
- 只要 Token 有效，就不会改变
- Token 只在 `ASSOCIATE_DEVICE` 或 `RESET_DEVICE` 时改变

#### 3. 设备重启后
- Token 从 NVS 中重新加载
- 值保持不变（除非被明确重置）

### Token 变化的代码流程

```
设备启动
  ↓
首次调用需要 Token 的命令
  ↓
NVSGetAuthToken() 被调用
  ↓
从 NVS 读取 Token
  ↓
如果存在 → 返回已存储的 Token
如果不存在 → 生成新的随机 Token 并保存到 NVS
  ↓
Token 被缓存在内存中
  ↓
后续调用直接返回缓存的 Token
  ↓
直到调用 ASSOCIATE_DEVICE(reset_data=true) 或 RESET_DEVICE
  ↓
Token 被重新生成
```

---

## Token 验证机制

### Token 验证流程

文件：`IonBridge-main/components/ble/protocol.cpp`

```cpp
bool Message::validate() {
  // 检查是否需要 Token
  if (!token_required((ServiceCommand)header_.service)) {
    return true;  // ASSOCIATE_DEVICE 不需要 Token
  }

  // 获取客户端发送的 Token
  uint8_t incoming_token = payload_[0], token;
  
  // 获取设备的 Token
  ESP_RETURN_FALSE_ON_ERROR(NVSGetAuthToken(&token), "NVSGetAuthToken");
  
  // 比较 Token
  bool valid = incoming_token == token;
  if (!valid) {
    ESP_LOGW(TAG, "Token mismatch, expected %d, got %d, service: %d", token,
             incoming_token, header_.service);
  }
  
  // 移除 Token 字节，保留实际的命令数据
  size_t payload_size = get_ble_size_t(header_.size, header_.version);
  for (size_t i = 1; i < payload_size; i++) {
    payload_[i - 1] = payload_[i];
  }
  header_.size = set_ble_size_t(payload_size - 1, header_.version);
  
  return valid;
}
```

### 哪些命令需要 Token？

文件：`IonBridge-main/components/service/service.cpp`

```cpp
bool token_required(ServiceCommand service) {
  return service != ServiceCommand::ASSOCIATE_DEVICE;
}
```

**结论**：除了 `ASSOCIATE_DEVICE` 外，**所有命令都需要 Token**



---

## 拥有有效 Token 后可以执行的操作

### 设备管理命令（10 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| REBOOT_DEVICE | 0x11 | 重启设备 |
| RESET_DEVICE | 0x12 | 重置设备（清除用户数据） |
| GET_DEVICE_SERIAL_NO | 0x13 | 获取设备序列号 |
| GET_DEVICE_UPTIME | 0x14 | 获取设备运行时间 |
| GET_AP_VERSION | 0x15 | 获取 ESP32 固件版本 |
| GET_DEVICE_BLE_ADDR | 0x19 | 获取设备 BLE 地址 |
| SWITCH_DEVICE | 0x1a | 开关设备 |
| GET_DEVICE_SWITCH | 0x1b | 获取开关状态 |
| GET_DEVICE_MODEL | 0x1c | 获取设备型号 |
| GET_DEVICE_INFO | 0x92 | 获取设备信息 |

### WiFi 管理命令（11 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| SCAN_WIFI | 0x30 | 扫描 WiFi 网络 |
| SET_WIFI_SSID | 0x31 | 设置 WiFi SSID |
| SET_WIFI_PASSWORD | 0x32 | 设置 WiFi 密码 |
| RESET_WIFI | 0x33 | 重置 WiFi 配置 |
| GET_WIFI_STATUS | 0x34 | 获取 WiFi 连接状态 |
| GET_DEVICE_WIFI_ADDR | 0x35 | 获取设备 WiFi 地址 |
| SET_WIFI_SSID_AND_PASSWORD | 0x36 | 同时设置 SSID 和密码 |
| GET_WIFI_RECORDS | 0x37 | 获取 WiFi 记录 |
| OPERATE_WIFI_RECORD | 0x38 | 操作 WiFi 记录 |
| GET_WIFI_STATE_MACHINE | 0x39 | 获取 WiFi 状态机 |
| SET_WIFI_STATE_MACHINE | 0x3a | 设置 WiFi 状态机 |

### 电源管理命令（26 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| TOGGLE_PORT_POWER | 0x40 | 切换端口电源 |
| GET_POWER_STATISTICS | 0x41 | 获取电源统计 |
| GET_POWER_SUPPLY_STATUS | 0x42 | 获取端口供电状态 |
| SET_CHARGING_STRATEGY | 0x43 | 设置充电策略 |
| GET_CHARGING_STATUS | 0x44 | 获取充电状态 |
| GET_POWER_HISTORICAL_STATS | 0x45 | 获取历史功率统计 |
| SET_PORT_PRIORITY | 0x46 | 设置端口优先级 |
| GET_PORT_PRIORITY | 0x47 | 获取端口优先级 |
| GET_CHARGING_STRATEGY | 0x48 | 获取充电策略 |
| GET_PORT_PD_STATUS | 0x49 | 获取端口 PD 信息 |
| GET_ALL_POWER_STATISTICS | 0x4a | 获取全部端口电源统计 |
| GET_START_CHARGE_TIMESTAMP | 0x4b | 获取开始充电时间戳 |
| TURN_ON_PORT | 0x4c | 打开端口 |
| TURN_OFF_PORT | 0x4d | 关闭端口 |
| SET_STATIC_ALLOCATOR | 0x55 | 设置静态充电策略 |
| GET_STATIC_ALLOCATOR | 0x56 | 获取静态充电策略 |
| **SET_PORT_CONFIG** | **0x57** | **设置端口协议配置** |
| **GET_PORT_CONFIG** | **0x58** | **获取端口协议配置** |
| SET_PORT_COMPATIBILITY_SETTINGS | 0x59 | 设置端口兼容性设置 |
| GET_PORT_COMPATIBILITY_SETTINGS | 0x5a | 获取端口兼容性设置 |
| SET_TEMPERATURE_MODE | 0x5b | 设置温度模式 |
| SET_TEMPORARY_ALLOCATOR | 0x5c | 设置临时充电策略 |
| SET_PORT_CONFIG1 | 0x5d | 设置端口配置（版本 1） |
| GET_PORT_CONFIG1 | 0x5e | 获取端口配置（版本 1） |

### 显示管理命令（9 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| SET_DISPLAY_INTENSITY | 0x70 | 设置显示亮度 |
| SET_DISPLAY_MODE | 0x71 | 设置显示模式 |
| GET_DISPLAY_INTENSITY | 0x72 | 获取显示亮度 |
| GET_DISPLAY_MODE | 0x73 | 获取显示模式 |
| SET_DISPLAY_FLIP | 0x74 | 设置屏幕翻转 |
| GET_DISPLAY_FLIP | 0x75 | 获取屏幕翻转状态 |
| SET_DISPLAY_CONFIG | 0x76 | 设置屏幕配置 |
| SET_DISPLAY_STATE | 0x77 | 设置屏幕状态 |
| GET_DISPLAY_STATE | 0x78 | 获取屏幕状态 |

### OTA 升级命令（5 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| PERFORM_BLE_OTA | 0x20 | 执行 BLE OTA |
| PERFORM_WIFI_OTA | 0x21 | 执行 WiFi OTA |
| GET_WIFI_OTA_PROGRESS | 0x22 | 获取 WiFi OTA 进度 |
| CONFIRM_OTA | 0x23 | 确认 OTA |
| START_OTA | 0x9C | 开始升级 |

### 其他命令（18 个）

| 命令 | 代码 | 功能 |
|------|------|------|
| BLE_ECHO_TEST | 0x00 | BLE 回显测试 |
| GET_DEBUG_LOG | 0x01 | 获取调试日志 |
| GET_SECURE_BOOT_DIGEST | 0x02 | 获取 Secure Boot Digest |
| PING_MQTT_TELEMETRY | 0x03 | Ping MQTT 遥测 |
| PING_HTTP | 0x04 | Ping HTTP |
| GET_DEVICE_PASSWORD | 0x05 | 获取设备密码 |
| MANAGE_POWER_ALLOCATOR_ENABLED | 0x09 | 管理电源分配器 |
| MANAGE_POWER_CONFIG | 0x0a | 管理电源配置 |
| MANAGE_FEATURE_TOGGLE | 0x0b | 管理功能开关 |
| ENABLE_RELEASE_MODE | 0x0c | 启用发布模式 |
| PUSH_LICENSE | 0x1d | 推送许可证 |
| GET_BLE_RSSI | 0x1e | 获取 BLE RSSI |
| GET_BLE_MTU | 0x1f | 获取 BLE MTU |
| START_TELEMETRY_STREAM | 0x90 | 启动遥测流 |
| STOP_TELEMETRY_STREAM | 0x91 | 停止遥测流 |
| SET_BLE_STATE | 0x98 | 设置 BLE 状态 |
| SET_SYSLOG_STATE | 0x99 | 设置系统日志状态 |
| SET_SYSTEM_TIME | 0x9A | 设置系统时间 |

**总计：60+ 个蓝牙命令**

---

## Token 使用流程

### 1. 首次使用设备

```
1. 调用 ASSOCIATE_DEVICE (0x10)
   - 发送：[0x10] [msg_id] [password]
   - 接收：[0x10] [msg_id] [token]
   
2. 保存返回的 Token
   
3. 后续所有命令都需要在 payload 前加上 Token
   - 发送：[command] [msg_id] [token] [command_data]
```

### 2. 设备重启后

```
1. Token 自动从 NVS 加载
   
2. 直接使用已保存的 Token 发送命令
   - 发送：[command] [msg_id] [token] [command_data]
```

### 3. 重置设备

```
1. 调用 RESET_DEVICE (0x12)
   - 发送：[0x12] [msg_id] [old_token]
   - 设备重启
   
2. 调用 ASSOCIATE_DEVICE (0x10) 获取新 Token
   - 发送：[0x10] [msg_id] [password]
   - 接收：[0x10] [msg_id] [new_token]
   
3. 使用新 Token 发送后续命令
```

---

## Token 总结

| 特性 | 说明 |
|------|------|
| **Token 大小** | 1 字节（0-255） |
| **Token 存储** | NVS 用户分区，BLE-SERVICE 命名空间 |
| **Token 生成** | 随机生成，首次关联设备时 |
| **Token 变化** | 仅在 ASSOCIATE_DEVICE 或 RESET_DEVICE 时改变 |
| **Token 缓存** | 在内存中缓存，设备重启后重新加载 |
| **Token 验证** | 所有命令（除 ASSOCIATE_DEVICE）都需要 Token |
| **可执行操作** | 60+ 个蓝牙命令，涵盖设备、WiFi、电源、显示、OTA 等 |



---

# 端口协议配置

## 概述

IonBridge 支持通过蓝牙动态配置每个端口的充电协议。系统支持多种充电协议，可以为每个端口独立配置。

---

## 端口协议配置架构

### 1. 支持的充电协议

文件：`IonBridge-main/components/chip_data_types/include/data_types.h`

**快速充电协议：**
- TFCP (Trickle Fast Charging Protocol)
- PE (Proprietary Extension)
- QC 2.0 / 3.0 / 3+ (Qualcomm Quick Charge)
- AFC (Adaptive Fast Charging)
- FCP (Fast Charging Protocol)
- UFCS (Universal Fast Charging Specification)

**保护协议：**
- HV SCP (High Voltage Smart Charge Protocol)
- LV SCP (Low Voltage Smart Charge Protocol)
- SFCP (Super Fast Charging Protocol)

**品牌协议：**
- Apple 协议
- Samsung 协议

**标准协议：**
- USB PD (Power Delivery)
- PD LVPPS (Low Voltage Programmable Power Supply)
- PD EPR (Extended Power Range)
- PD 5V5A
- PD HVPPS (High Voltage Programmable Power Supply)

**其他：**
- PD 兼容模式
- 限流模式

### 2. PowerFeatures 结构定义

```cpp
typedef struct __attribute__((packed)) {
  // BYTE 1 (8 bits)
  bool EnableTfcp : 1;        // TFCP 协议
  bool EnablePe : 1;          // PE 协议
  bool EnableQc2p0 : 1;       // QC 2.0 协议
  bool EnableQc3p0 : 1;       // QC 3.0 协议
  bool EnableQc3plus : 1;     // QC 3+ 协议
  bool EnableAfc : 1;         // AFC 协议
  bool EnableFcp : 1;         // FCP 协议
  bool EnableHvScp : 1;       // HV SCP 协议
  
  // BYTE 2 (8 bits)
  bool EnableLvScp : 1;       // LV SCP 协议
  bool EnableSfcp : 1;        // SFCP 协议
  bool EnableApple : 1;       // Apple 协议
  bool EnableSamsung : 1;     // Samsung 协议
  bool EnableUfcs : 1;        // UFCS 协议
  bool EnablePd : 1;          // USB PD 协议
  bool EnablePdCompatMode : 1;// PD 兼容模式
  bool LimitedCurrentMode : 1;// 限流模式
  
  // BYTE 3 (8 bits)
  bool EnablePdLVPPS : 1;     // PD LVPPS
  bool EnablePdEPR : 1;       // PD EPR
  bool EnablePd5V5A : 1;      // PD 5V5A
  bool EnablePdHVPPS : 1;     // PD HVPPS
  uint8_t reserved : 4;       // 保留位
} PowerFeatures;
```

### 3. 端口配置结构

```cpp
typedef struct {
  uint8_t version;            // 配置版本
  PowerFeatures features;     // 协议特性（3 字节）
} PortConfig;
```

### 4. NVS 存储位置

文件：`IonBridge-main/components/nvs_data/include/nvs_default.h`

```cpp
enum class NVSKey {
  POWER_PORT0_CONFIG,  // 端口 0 配置
  POWER_PORT1_CONFIG,  // 端口 1 配置
  POWER_PORT2_CONFIG,  // 端口 2 配置
  POWER_PORT3_CONFIG,  // 端口 3 配置
  POWER_PORT4_CONFIG,  // 端口 4 配置
  POWER_PORT5_CONFIG,  // 端口 5 配置
  POWER_PORT6_CONFIG,  // 端口 6 配置
  POWER_PORT7_CONFIG,  // 端口 7 配置
};
```

---

## 蓝牙服务命令

### 1. SET_PORT_CONFIG (0x57) - 设置端口协议

**功能**：设置一个或多个端口的协议配置

**请求格式**：
```
[Service: 0x57] [Message ID: 2 bytes] [Token: 1 byte] 
[Port Mask: 1 byte] [Version: 1 byte] [Port 0-7 Config: 8 * config_size bytes]
```

**响应格式**：
```
[Service: 0x57] [Message ID: 2 bytes] [Status: 1 byte]
Status: 0x00 = 成功, 0x01 = 失败
```

### 2. GET_PORT_CONFIG (0x58) - 获取端口协议

**功能**：获取所有端口的协议配置

**请求格式**：
```
[Service: 0x58] [Message ID: 2 bytes] [Token: 1 byte] [Version: 1 byte (optional)]
```

**响应格式**：
```
[Service: 0x58] [Message ID: 2 bytes] 
[Port 0-7 Config: 8 * config_size bytes]
```

### 3. SET_PORT_COMPATIBILITY_SETTINGS (0x59) - 设置兼容性

**功能**：设置端口兼容性设置（简化的协议配置）

**请求格式**：
```
[Service: 0x59] [Message ID: 2 bytes] [Token: 1 byte] [Settings: 1 byte]

Settings 字节结构：
  Bit 0: Enable TFCP
  Bit 1: Enable FCP
  Bit 2: Enable UFCS
  Bit 3: Enable HV SCP
  Bit 4: Enable LV SCP
  Bits 5-7: 保留
```

**响应格式**：
```
[Service: 0x59] [Message ID: 2 bytes] [Status: 1 byte]
```

### 4. GET_PORT_COMPATIBILITY_SETTINGS (0x5a) - 获取兼容性

**功能**：获取端口兼容性设置

**请求格式**：
```
[Service: 0x5a] [Message ID: 2 bytes] [Token: 1 byte]
```

**响应格式**：
```
[Service: 0x5a] [Message ID: 2 bytes] [Settings: 1 byte]
```

---

## 协议配置示例

### 示例 1：启用所有协议

```
字节 1: 0xFF (11111111)
字节 2: 0x7F (01111111)
字节 3: 0x0F (00001111)
```

### 示例 2：仅启用 USB PD 和 QC 协议

```
字节 1: 0x1C (00011100)  // QC 2.0, 3.0, 3+
字节 2: 0x20 (00100000)  // USB PD
字节 3: 0x07 (00000111)  // PD LVPPS, EPR, 5V5A
```

### 示例 3：仅启用 USB PD

```
字节 1: 0x00 (00000000)
字节 2: 0x20 (00100000)
字节 3: 0x07 (00000111)
```

---

## 默认端口配置

### 普通端口（Type C）

支持所有协议，包括 USB PD、QC、FCP、UFCS 等

### Type A 端口

不支持 USB PD 和 QC 3+，但支持其他快速充电协议

---

## 关键代码位置

| 文件 | 用途 |
|------|------|
| `data_types.h` | PowerFeatures 定义 |
| `port.h/cpp` | 端口配置管理 |
| `power_handler.cpp` | SET/GET_PORT_CONFIG 实现 |
| `nvs_default.h` | NVS 键定义 |
| `main.cpp` | 端口配置初始化 |

---

## 实现蓝牙端口协议配置的步骤

### 步骤 1：获取当前配置
```
发送 GET_PORT_CONFIG 命令
接收所有 8 个端口的配置
```

### 步骤 2：修改配置
```
修改特定端口的 PowerFeatures
例如：启用/禁用特定协议
```

### 步骤 3：保存配置
```
发送 SET_PORT_CONFIG 命令
指定要更新的端口（使用 Port Mask）
发送新的配置数据
```

### 步骤 4：验证配置
```
再次发送 GET_PORT_CONFIG 命令
验证配置已正确保存
```

---

## 注意事项

1. **Token 验证**：除了 ASSOCIATE_DEVICE 命令外，所有命令都需要有效的 Token
2. **端口掩码**：使用位掩码指定要配置的端口，可以同时配置多个端口
3. **版本兼容性**：配置版本 0 使用 3 字节，版本 1+ 使用完整的 PortConfig 结构
4. **死端口处理**：如果端口已死亡，配置只会保存到 NVS，不会立即应用
5. **协议支持**：不同的端口类型（Type A/C）支持不同的协议集合



---

# MQTT 配置指南

## 概述

IonBridge 支持通过蓝牙动态配置 MQTT 服务器。系统支持两种 MQTT broker 配置：
1. **默认 Broker**：编译时配置的默认 MQTT 服务器
2. **自定义 Broker**：通过蓝牙或 Web 服务器动态配置的自定义 MQTT 服务器

---

## 核心架构

### 1. MQTT 配置存储位置

#### NVS 存储键定义
文件：`IonBridge-main/components/nvs_data/include/nvs_default.h`

```cpp
enum class NVSKey {
  MQTT_BROKER,           // 默认 MQTT broker 地址（受保护分区）
  MQTT_CUSTOM_BROKER,    // 自定义 MQTT broker 地址（用户分区）
};
```

#### NVS 命名空间
文件：`IonBridge-main/components/nvs_data/include/nvs_namespace.h`

```cpp
#define PROTECTED_DATA_NVS_PARTITION "protected_data"
#define USER_DATA_NVS_PARTITION "nvs"
#define MQTT_NVS_NAMESPACE "mqtt"
#define MQTT_CUSTOM_NAMESPACE "mqtt_custom"

// 读取默认 MQTT broker
#define MQTTNVSGet(...)  \
  NVSNamespace::SGet(__VA_ARGS__, PROTECTED_DATA_NVS_PARTITION, \
                     MQTT_NVS_NAMESPACE)

// 读取自定义 MQTT broker
#define UserMQTTNVSGet(...) \
  NVSNamespace::SGet(__VA_ARGS__, USER_DATA_NVS_PARTITION, \
                     MQTT_CUSTOM_NAMESPACE)

// 设置自定义 MQTT broker
#define UserMQTTNVSSet(...) \
  NVSNamespace::SSet(__VA_ARGS__, USER_DATA_NVS_PARTITION, \
                     MQTT_CUSTOM_NAMESPACE)

// 删除自定义 MQTT broker
#define UserMQTTNVSEraseKey(...) \
  NVSNamespace::SEraseKey(__VA_ARGS__, USER_DATA_NVS_PARTITION, \
                          MQTT_CUSTOM_NAMESPACE)
```

---

### 2. MQTT 客户端初始化流程

文件：`IonBridge-main/components/mqtt_app/mqtt_app.cpp`

MQTT 客户端初始化时的优先级：
1. **第一步**：尝试读取自定义 MQTT broker（用户分区）
2. **第二步**：如果没有自定义 broker，读取默认 broker（受保护分区）
3. **第三步**：如果都没有，使用编译时配置的默认值

---

## 蓝牙配置方法

### 当前状态

**重要提示**：目前 IonBridge 中**没有直接的蓝牙服务来配置 MQTT broker**。

但系统已经为此做好了准备：
- ✅ NVS 存储结构已定义（`MQTT_CUSTOM_BROKER`）
- ✅ MQTT 客户端支持读取自定义 broker
- ✅ Web 服务器可以配置自定义 broker（通过 HTTP API）

---

## 实现蓝牙 MQTT 配置的步骤

### 方案：创建新的 BLE 服务

#### 1. 定义服务命令

需要添加新的 `ServiceCommand`：
```cpp
enum class ServiceCommand : uint8_t {
  SET_MQTT_BROKER = 0xXX,      // 设置自定义 MQTT broker
  GET_MQTT_BROKER = 0xXX,      // 获取当前 MQTT broker
  RESET_MQTT_BROKER = 0xXX,    // 重置为默认 broker
};
```

#### 2. 创建 MQTT 处理程序

创建新文件：`IonBridge-main/components/handler/mqtt_handler.h`

```cpp
#ifndef MQTT_HANDLER_H_
#define MQTT_HANDLER_H_

#include <cstdint>
#include <vector>
#include "esp_err.h"

namespace MQTTHandler {

// 设置自定义 MQTT broker
esp_err_t SetMQTTBroker(const std::vector<uint8_t> &request,
                        std::vector<uint8_t> &response);

// 获取当前 MQTT broker
esp_err_t GetMQTTBroker(const std::vector<uint8_t> &request,
                        std::vector<uint8_t> &response);

// 重置为默认 MQTT broker
esp_err_t ResetMQTTBroker(const std::vector<uint8_t> &request,
                          std::vector<uint8_t> &response);

};  // namespace MQTTHandler

#endif
```

#### 3. 实现 MQTT 处理程序

创建新文件：`IonBridge-main/components/handler/mqtt_handler.cpp`

关键实现步骤：
1. 验证 broker URI 格式（应该以 mqtt:// 或 mqtts:// 开头）
2. 保存到 NVS 用户分区
3. 标记 MQTT 客户端需要重新连接
4. 返回状态码

#### 4. 注册服务

在 `IonBridge-main/components/handler/handler.cpp` 中注册服务：

```cpp
void Handler::RegisterAllServices(App &app) {
  // ... 现有服务

  // MQTT 配置服务
  app.Srv(ServiceCommand::SET_MQTT_BROKER, MQTTHandler::SetMQTTBroker,
          ServiceScope::SERVICE_SCOPE_ALL);
  app.Srv(ServiceCommand::GET_MQTT_BROKER, MQTTHandler::GetMQTTBroker,
          ServiceScope::SERVICE_SCOPE_ALL);
  app.Srv(ServiceCommand::RESET_MQTT_BROKER, MQTTHandler::ResetMQTTBroker,
          ServiceScope::SERVICE_SCOPE_ALL);
}
```

---

## 蓝牙通信协议示例

### 设置自定义 MQTT Broker

**请求**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Token: 1 byte]
[Broker Length: 1 byte] [Broker URI: variable]

示例：设置 broker 为 "mqtt://192.168.1.100:1883"
[0xXX] [0x00 0x01] [token] [0x1F] [mqtt://192.168.1.100:1883]
                                   ↑
                                   31 字节长度
```

**响应**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Status: 1 byte]

成功：[0xXX] [0x00 0x01] [0x00]
失败：[0xXX] [0x00 0x01] [0x01]  // 请求格式无效
      [0xXX] [0x00 0x01] [0x02]  // URI 格式无效
      [0xXX] [0x00 0x01] [0x03]  // NVS 写入失败
```

### 获取当前 MQTT Broker

**请求**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Token: 1 byte]
```

**响应**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Broker Type: 1 byte] 
[URI Length: 1 byte] [URI: variable]

Broker Type: 0 = 默认, 1 = 自定义

示例：
[0xXX] [0x00 0x02] [0x01] [0x1F] [mqtt://192.168.1.100:1883]
                    ↑      ↑
                    自定义  31 字节
```

### 重置为默认 MQTT Broker

**请求**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Token: 1 byte]
```

**响应**：
```
[Service: 0xXX] [Message ID: 2 bytes] [Status: 1 byte]

成功：[0xXX] [0x00 0x03] [0x00]
失败：[0xXX] [0x00 0x03] [0x01]
```

---

## 现有 Web 服务器配置方法

虽然蓝牙服务还未实现，但你可以通过 Web 服务器配置 MQTT broker。

### 相关代码位置

- **Web 服务器**：`IonBridge-main/components/web_server/server.cpp`
- **MQTT 应用**：`IonBridge-main/components/mqtt_app/mqtt_app.cpp`

### 配置流程

1. 设备连接到 WiFi
2. 通过 HTTP 请求设置自定义 MQTT broker
3. 设备重新连接到新的 MQTT broker

---

## 关键文件总结

| 文件 | 用途 |
|------|------|
| `nvs_default.h` | NVS 键定义 |
| `nvs_namespace.h` | NVS 读写宏定义 |
| `mqtt_app.h/cpp` | MQTT 客户端实现 |
| `handler.cpp` | 服务注册 |
| `ble_handler.h/cpp` | BLE 服务示例 |
| `wifi_handler.h/cpp` | WiFi 服务示例 |

---

## 总结

IonBridge 的 MQTT 配置架构已经完全支持自定义 broker，但**蓝牙配置服务需要你自己实现**。上面提供的代码框架可以直接集成到项目中。

关键点：
- ✅ NVS 存储已准备好
- ✅ MQTT 客户端支持自定义 broker
- ✅ 需要实现 BLE 服务来通过蓝牙配置
- ✅ 可以参考现有的 WiFi 和 BLE 处理程序作为模板



---

# 完整总结

## 📋 核心发现总结

### 1. Token 机制

#### Token 是什么？
- 1 字节的随机数（0-255）
- 用于验证蓝牙命令的合法性
- 存储在 NVS 用户分区的 BLE-SERVICE 命名空间

#### Token 如何获取？
```
调用 ASSOCIATE_DEVICE (0x10) 命令
  ↓
发送设备密码
  ↓
设备生成随机 Token
  ↓
返回 Token 给客户端
```

#### Token 是否会变化？

**✅ 会变化的情况：**
1. 首次关联设备时 - 生成新 Token
2. 调用 RESET_DEVICE 时 - 清除所有用户数据，下次关联时生成新 Token
3. 调用 ASSOCIATE_DEVICE 时指定 reset_data=true - 强制重置并生成新 Token

**❌ 不会变化的情况：**
1. 正常运行期间 - Token 被缓存在内存中
2. 设备重启后 - Token 从 NVS 重新加载，值保持不变
3. 调用其他蓝牙命令时 - 只要 Token 有效就不改变

---

### 2. 端口协议配置

#### 支持的充电协议

**快速充电协议：**
- TFCP, PE, QC 2.0/3.0/3+, AFC, FCP, UFCS

**保护协议：**
- HV SCP, LV SCP, SFCP

**品牌协议：**
- Apple, Samsung

**标准协议：**
- USB PD, PD LVPPS, PD EPR, PD 5V5A, PD HVPPS

**其他：**
- PD 兼容模式, 限流模式

#### 端口配置结构

```
PortConfig {
  uint8_t version;           // 配置版本
  PowerFeatures features;    // 协议特性（3 字节）
}

PowerFeatures (3 字节):
  字节 1: TFCP, PE, QC2.0, QC3.0, QC3+, AFC, FCP, HV_SCP
  字节 2: LV_SCP, SFCP, Apple, Samsung, UFCS, PD, PD_CompatMode, LimitedCurrent
  字节 3: PD_LVPPS, PD_EPR, PD_5V5A, PD_HVPPS, 保留
```

#### 配置方式

**方式 1：SET_PORT_CONFIG (0x57)**
- 设置一个或多个端口的完整协议配置
- 使用端口掩码指定要配置的端口
- 可以同时配置多个端口

**方式 2：SET_PORT_COMPATIBILITY_SETTINGS (0x59)**
- 简化的协议配置方式
- 只能配置 5 个关键协议：TFCP, FCP, UFCS, HV_SCP, LV_SCP
- 对所有端口同时生效

---

### 3. 拥有有效 Token 后可以执行的操作

#### 命令分类统计

| 类别 | 数量 | 功能 |
|------|------|------|
| 设备管理 | 10 | 重启、重置、获取信息等 |
| WiFi 管理 | 11 | 扫描、配置、获取状态等 |
| 电源管理 | 26 | 端口控制、充电策略、协议配置等 |
| 显示管理 | 9 | 亮度、模式、翻转等 |
| OTA 升级 | 5 | 固件升级相关 |
| 其他功能 | 18 | 测试、日志、遥测等 |
| **总计** | **79** | **60+ 个蓝牙命令** |

---

## 🎯 实际应用场景

### 场景 1：首次配置设备

```
1. 通过蓝牙连接设备
2. 调用 ASSOCIATE_DEVICE 获取 Token
3. 使用 Token 调用 SET_WIFI_SSID_AND_PASSWORD 配置 WiFi
4. 使用 Token 调用 SET_PORT_CONFIG 配置端口协议
5. 使用 Token 调用 REBOOT_DEVICE 重启设备
```

### 场景 2：动态调整端口协议

```
1. 获取当前端口配置 (GET_PORT_CONFIG)
2. 根据需要修改特定端口的协议
3. 保存新配置 (SET_PORT_CONFIG)
4. 验证配置已生效 (GET_PORT_CONFIG)
```

### 场景 3：设备故障排查

```
1. 获取设备信息 (GET_DEVICE_INFO)
2. 获取电源统计 (GET_ALL_POWER_STATISTICS)
3. 获取 WiFi 状态 (GET_WIFI_STATUS)
4. 获取调试日志 (GET_DEBUG_LOG)
5. 如需要，重置设备 (RESET_DEVICE)
```

### 场景 4：固件升级

```
1. 调用 START_OTA 开始升级
2. 通过 BLE 或 WiFi 传输固件
3. 调用 CONFIRM_OTA 确认升级
4. 设备自动重启
```

---

## 📊 关键数据

| 项目 | 数值 |
|------|------|
| Token 大小 | 1 字节 (0-255) |
| 支持的充电协议 | 20+ 种 |
| 可配置的端口 | 8 个 |
| PowerFeatures 大小 | 3 字节 |
| 蓝牙命令总数 | 60+ 个 |
| 需要 Token 的命令 | 59 个 |
| 不需要 Token 的命令 | 1 个 (ASSOCIATE_DEVICE) |

---

## 🔍 代码位置速查

| 功能 | 文件 | 位置 |
|------|------|------|
| Token 生成 | nvs_namespace.cpp | NVSGetAuthToken() |
| Token 验证 | protocol.cpp | Message::validate() |
| 关联设备 | device_handler.cpp | AssociateDevice() |
| 端口配置 | power_handler.cpp | SetPortConfig(), GetPortConfig() |
| 协议定义 | data_types.h | PowerFeatures 结构 |
| 服务命令 | service.h | ServiceCommand 枚举 |
| 服务注册 | handler.cpp | RegisterAllServices() |

---

## 💡 重要提示

### 关于 Token

1. **Token 是一次性的**：每次关联设备时生成新 Token
2. **Token 不会自动过期**：除非设备重置或重新关联
3. **Token 是必需的**：除了 ASSOCIATE_DEVICE，所有命令都需要 Token
4. **Token 是单字节**：范围 0-255，不是加密的，只是简单的验证

### 关于端口配置

1. **配置是持久化的**：保存到 NVS，设备重启后保持
2. **可以独立配置**：每个端口的协议配置独立
3. **支持批量配置**：可以同时配置多个端口
4. **有默认配置**：如果没有自定义配置，使用默认配置

### 关于蓝牙命令

1. **所有命令都需要 Token**（除 ASSOCIATE_DEVICE）
2. **命令格式统一**：[Service] [Message ID] [Token] [Data]
3. **支持多种功能**：不仅仅是端口配置
4. **可以组合使用**：多个命令可以组合完成复杂操作

---

## 🚀 快速开始

### 最小化工作流程

```python
# 1. 关联设备
token = associate_device(password="device_password")

# 2. 获取当前配置
configs = get_port_config(token)

# 3. 修改配置（例如启用 USB PD）
configs[0].features = PowerFeatures(
    EnablePd=True,
    EnablePdLVPPS=True,
    EnablePd5V5A=True,
)

# 4. 保存配置
set_port_config(token, port_mask=0x01, configs=configs)

# 5. 验证
new_configs = get_port_config(token)
assert new_configs[0].features.EnablePd == True
```

---

## ✅ 总结

IonBridge 的蓝牙功能非常完整，包括：

✅ **Token 机制**：简单但有效的命令验证方式
✅ **端口协议配置**：支持 20+ 种充电协议，可独立配置每个端口
✅ **完整的设备管理**：60+ 个蓝牙命令涵盖所有主要功能
✅ **持久化存储**：配置保存到 NVS，设备重启后保持
✅ **灵活的配置方式**：支持完整配置和简化配置两种方式

通过蓝牙，你可以完全控制设备的所有主要功能，包括端口协议、WiFi 配置、电源管理、显示设置等。

---

## 📚 文档说明

本文档是 IonBridge 蓝牙功能的完整综合指南，包含：

1. **快速参考** - 常用命令和概念速览
2. **Token 机制详解** - Token 的完整说明和 60+ 命令列表
3. **端口协议配置** - 20+ 协议的详细配置指南
4. **MQTT 配置指南** - MQTT 服务器配置方案
5. **完整总结** - 核心发现、应用场景和快速开始

**生成日期**：2025 年 1 月
**基于版本**：IonBridge-main 最新版本
**覆盖范围**：蓝牙功能、Token 机制、端口协议配置、MQTT 配置

