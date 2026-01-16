#!/usr/bin/env python3
"""
IonBridge BLE 综合测试脚本
测试所有主要的BLE命令，确认设备功能是否正常

目标设备: CP02-0002A0
Token: 0x2F (47) - 不会重置（除非发送重置指令）
"""

import asyncio
import sys
from ble_manager import BLEManager, TokenManager
from protocol import ServiceCommand, BLEFlags

# ============ 响应解析函数 ============

def parse_device_model(payload):
    """解析设备型号响应"""
    if len(payload) >= 4:
        model = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
        return model
    return "未知"

def parse_device_info(payload):
    """解析设备信息响应"""
    info = {}
    if len(payload) >= 4:
        info['firmware'] = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
    if len(payload) >= 8:
        info['serial'] = payload[4:8].decode('utf-8', errors='ignore').strip('\x00')
    return info

def parse_device_serial(payload):
    """解析设备序列号响应"""
    if len(payload) >= 4:
        serial = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
        return serial
    elif len(payload) > 0:
        # 如果不是4字节，尝试直接解码
        return payload.decode('utf-8', errors='ignore').strip('\x00')
    return "未知"

def parse_wifi_status(payload):
    """解析WiFi状态响应"""
    if len(payload) >= 1:
        status = payload[0]
        status_names = {
            0: "未配置",
            1: "失败",
            2: "连接中",
            3: "已连接",
            4: "断开连接中"
        }
        status_name = status_names.get(status, f"未知状态({status})")
        result = {'status': status, 'status_name': status_name}
        
        # 如果已连接，解析IP地址
        if status == 3 and len(payload) >= 5:
            ip = '.'.join(str(b) for b in payload[1:5])
            result['ip'] = ip
        
        return result
    return None

def parse_port_config(payload):
    """解析端口配置响应"""
    if len(payload) >= 4:
        port_id = payload[0]
        power_features = payload[1:4]
        
        # 协议名称列表（按bit顺序）
        protocol_names = [
            'TFCP', 'PE', 'QC2.0', 'QC3.0', 'QC3+', 'AFC', 'FCP', 'HV_SCP',
            'LV_SCP', 'SFCP', 'Apple 5V', 'Samsung 5V', 'BC1.2', 'UFCS', 'RPi 5V5A', 'VOOC',
            'PD', 'PPS', 'QC4.0', 'QC4+', 'Dash/Warp', 'SFC', 'MTK PE', 'MTK PE+'
        ]
        
        # 解析支持的协议
        protocols = []
        for i, protocol_name in enumerate(protocol_names):
            byte_index = i // 8
            bit_index = i % 8
            if byte_index < len(power_features):
                if power_features[byte_index] & (1 << bit_index):
                    protocols.append(protocol_name)
        
        return {
            'port_id': port_id,
            'power_features': power_features.hex(),
            'protocols': protocols
        }
    return None

def parse_charging_status(payload):
    """解析充电状态响应"""
    if len(payload) >= 1:
        num_ports = payload[0]
        ports = []
        for i in range(num_ports):
            offset = 1 + i * 4
            if offset + 4 <= len(payload):
                port_id = payload[offset]
                voltage = (payload[offset + 1] << 8) | payload[offset + 2]
                current = payload[offset + 3]
                ports.append({
                    'port_id': port_id,
                    'voltage': voltage / 1000.0,  # mV to V
                    'current': current / 1000.0  # mA to A
                })
        return {'num_ports': num_ports, 'ports': ports}
    return None

def parse_charging_strategy(payload):
    """解析充电策略响应"""
    if len(payload) >= 1:
        strategy = payload[0]
        strategy_names = {
            0: "自动分配",
            1: "固定分配",
            2: "优先级分配"
        }
        strategy_name = strategy_names.get(strategy, f"未知策略({strategy})")
        return {'strategy': strategy, 'strategy_name': strategy_name}
    return None

def parse_display_settings(payload):
    """解析显示设置响应"""
    if len(payload) >= 2:
        brightness = payload[0]
        mode = payload[1]
        mode_names = {
            0: "默认",
            1: "简洁",
            2: "详细"
        }
        mode_name = mode_names.get(mode, f"未知模式({mode})")
        return {
            'brightness': brightness,
            'mode': mode,
            'mode_name': mode_name
        }
    return None

def parse_power_statistics(payload):
    """解析功率统计响应"""
    if len(payload) >= 5:
        port_id = payload[0]
        
        # 根据实际响应长度解析
        if len(payload) >= 9:
            voltage = (payload[1] << 8) | payload[2]
            current = (payload[3] << 8) | payload[4]
            power = (payload[5] << 8) | payload[6]
            temperature = payload[7]
            uptime = (payload[8] << 24) | (payload[9] << 16) | (payload[10] << 8) | payload[11] if len(payload) >= 12 else 0
            
            return {
                'port_id': port_id,
                'voltage': voltage / 1000.0,  # mV to V
                'current': current / 1000.0,  # mA to A
                'power': power / 1000.0,  # mW to W
                'temperature': temperature,
                'uptime': uptime
            }
        elif len(payload) >= 5:
            # 简短格式：port_id + 4字节
            voltage = (payload[1] << 8) | payload[2]
            current = (payload[3] << 8) | payload[4]
            power = voltage * current / 1000.0  # W
            
            return {
                'port_id': port_id,
                'voltage': voltage / 1000.0,  # mV to V
                'current': current / 1000.0,  # mA to A
                'power': power,
                'temperature': 0,
                'uptime': 0
            }
    return None

def parse_machine_info(payload):
    """解析机器信息响应"""
    if len(payload) >= 8:
        uptime = (payload[0] << 24) | (payload[1] << 16) | (payload[2] << 8) | payload[3]
        total_power = (payload[4] << 24) | (payload[5] << 16) | (payload[6] << 8) | payload[7]
        return {
            'uptime': uptime,
            'total_power': total_power / 1000.0  # mWh to Wh
        }
    return None

def parse_power_supply_status(payload):
    """解析供电状态响应"""
    if len(payload) >= 1:
        port_mask = payload[0]
        active_ports = []
        for i in range(8):
            if port_mask & (1 << i):
                active_ports.append(i)
        return {
            'port_mask': port_mask,
            'active_ports': active_ports
        }
    return None

# ============ 测试函数 ============

async def test_device_commands(ble_manager, token_manager):
    """测试设备命令"""
    print("\n" + "="*60)
    print("🧪 测试设备管理命令")
    print("="*60)
    
    # 测试获取设备型号
    print("\n1️⃣  测试获取设备型号 (GET_DEVICE_MODEL)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_MODEL, bytes([token_manager.token]))
    if response and response.size > 0:
        model = parse_device_model(response.payload)
        print(f"✅ 设备型号: {model}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取设备型号失败")
    
    # 测试获取设备信息（使用GET_AP_VERSION）
    print("\n2️⃣  测试获取AP版本 (GET_AP_VERSION)...")
    response = await ble_manager.send_command(ServiceCommand.GET_AP_VERSION, bytes([token_manager.token]))
    if response and response.size > 0:
        firmware = response.payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
        print(f"✅ AP版本:")
        print(f"   固件版本: {firmware}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取AP版本失败")
    
    # 测试获取设备序列号
    print("\n3️⃣  测试获取设备序列号 (GET_DEVICE_SERIAL_NO)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_SERIAL_NO, bytes([token_manager.token]))
    if response and response.size > 0:
        serial = parse_device_serial(response.payload)
        print(f"✅ 设备序列号: {serial}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取设备序列号失败")

async def test_port_commands(ble_manager, token_manager):
    """测试端口命令"""
    print("\n" + "="*60)
    print("🧪 测试端口管理命令")
    print("="*60)
    
    # 测试获取供电状态
    print("\n1️⃣  测试获取供电状态 (GET_POWER_SUPPLY_STATUS)...")
    response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token_manager.token]))
    if response and response.size > 0:
        status = parse_power_supply_status(response.payload)
        print(f"✅ 供电状态:")
        print(f"   端口掩码: 0x{status['port_mask']:02X}")
        print(f"   活动端口: {status['active_ports']}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取供电状态失败")
    
    # 测试获取端口配置
    print("\n2️⃣  测试获取端口配置 (GET_PORT_CONFIG)...")
    for port_id in range(4):
        payload = bytes([token_manager.token, port_id])
        response = await ble_manager.send_command(ServiceCommand.GET_PORT_CONFIG, payload)
        if response and response.size > 0:
            config = parse_port_config(response.payload)
            print(f"✅ 端口 {port_id} 配置:")
            print(f"   Power Features: {config['power_features']}")
            print(f"   支持协议: {', '.join(config['protocols'][:5])}{'...' if len(config['protocols']) > 5 else ''}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print(f"❌ 获取端口 {port_id} 配置失败")
    
    # 测试获取充电状态
    print("\n3️⃣  测试获取充电状态 (GET_CHARGING_STATUS)...")
    response = await ble_manager.send_command(ServiceCommand.GET_CHARGING_STATUS, bytes([token_manager.token]))
    if response and response.size > 0:
        status = parse_charging_status(response.payload)
        print(f"✅ 充电状态:")
        print(f"   端口数量: {status['num_ports']}")
        for port in status['ports']:
            print(f"   端口 {port['port_id']}: {port['voltage']:.2f}V, {port['current']:.3f}A")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取充电状态失败")

async def test_power_commands(ble_manager, token_manager):
    """测试电源命令"""
    print("\n" + "="*60)
    print("🧪 测试电源管理命令")
    print("="*60)
    
    # 测试获取充电策略
    print("\n1️⃣  测试获取充电策略 (GET_CHARGING_STRATEGY)...")
    response = await ble_manager.send_command(ServiceCommand.GET_CHARGING_STRATEGY, bytes([token_manager.token]))
    if response and response.size > 0:
        strategy = parse_charging_strategy(response.payload)
        print(f"✅ 充电策略:")
        print(f"   策略: {strategy['strategy_name']}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取充电策略失败")
    
    # 测试获取功率统计
    print("\n2️⃣  测试获取功率统计 (GET_POWER_STATISTICS)...")
    for port_id in range(4):
        payload = bytes([token_manager.token, port_id])
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_STATISTICS, payload)
        if response and response.size > 0:
            stats = parse_power_statistics(response.payload)
            print(f"✅ 端口 {port_id} 功率统计:")
            print(f"   电压: {stats['voltage']:.2f}V")
            print(f"   电流: {stats['current']:.3f}A")
            print(f"   功率: {stats['power']:.2f}W")
            print(f"   温度: {stats['temperature']}°C")
            print(f"   运行时间: {stats['uptime']}秒")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print(f"❌ 获取端口 {port_id} 功率统计失败")

async def test_display_commands(ble_manager, token_manager):
    """测试显示命令"""
    print("\n" + "="*60)
    print("🧪 测试显示管理命令")
    print("="*60)
    
    # 测试获取显示亮度
    print("\n1️⃣  测试获取显示亮度 (GET_DISPLAY_INTENSITY)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DISPLAY_INTENSITY, bytes([token_manager.token]))
    if response and response.size > 0:
        brightness = response.payload[0] if len(response.payload) >= 1 else 0
        print(f"✅ 显示亮度:")
        print(f"   亮度: {brightness}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取显示亮度失败")
    
    # 测试获取显示模式
    print("\n2️⃣  测试获取显示模式 (GET_DISPLAY_MODE)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DISPLAY_MODE, bytes([token_manager.token]))
    if response and response.size > 0:
        mode = response.payload[0] if len(response.payload) >= 1 else 0
        mode_names = {
            0: "默认",
            1: "简洁",
            2: "详细"
        }
        mode_name = mode_names.get(mode, f"未知模式({mode})")
        print(f"✅ 显示模式:")
        print(f"   模式: {mode_name}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取显示模式失败")

async def test_system_commands(ble_manager, token_manager):
    """测试系统命令"""
    print("\n" + "="*60)
    print("🧪 测试系统管理命令")
    print("="*60)
    
    # 测试获取设备运行时间
    print("\n1️⃣  测试获取设备运行时间 (GET_DEVICE_UPTIME)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_UPTIME, bytes([token_manager.token]))
    if response and response.size > 0:
        uptime = (response.payload[0] << 24) | (response.payload[1] << 16) | (response.payload[2] << 8) | response.payload[3]
        print(f"✅ 设备运行时间:")
        print(f"   运行时间: {uptime}秒")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取设备运行时间失败")
    
    # 测试获取设备信息
    print("\n2️⃣  测试获取设备信息 (GET_DEVICE_INFO)...")
    response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_INFO, bytes([token_manager.token]))
    if response and response.size > 0:
        print(f"✅ 设备信息响应: {response.payload.hex()}")
    else:
        print("❌ 获取设备信息失败")

async def test_wifi_commands(ble_manager, token_manager):
    """测试WiFi命令"""
    print("\n" + "="*60)
    print("🧪 测试WiFi管理命令")
    print("="*60)
    
    # 测试获取WiFi状态
    print("\n1️⃣  测试获取WiFi状态 (GET_WIFI_STATUS)...")
    response = await ble_manager.send_command(ServiceCommand.GET_WIFI_STATUS, bytes([token_manager.token]))
    if response and response.size > 0:
        status = parse_wifi_status(response.payload)
        print(f"✅ WiFi状态:")
        print(f"   状态: {status['status_name']}")
        if 'ip' in status:
            print(f"   IP地址: {status['ip']}")
        print(f"   原始数据: {response.payload.hex()}")
    else:
        print("❌ 获取WiFi状态失败")

async def test_feature_commands(ble_manager, token_manager):
    """测试功能命令"""
    print("\n" + "="*60)
    print("🧪 测试功能管理命令")
    print("="*60)
    
    # 测试管理电源配置
    print("\n1️⃣  测试管理电源配置 (MANAGE_POWER_CONFIG)...")
    response = await ble_manager.send_command(ServiceCommand.MANAGE_POWER_CONFIG, bytes([token_manager.token, 0x00]))
    if response and response.size > 0:
        print(f"✅ 电源配置响应: {response.payload.hex()}")
    else:
        print("❌ 管理电源配置失败")
    
    # 测试管理功能开关
    print("\n2️⃣  测试管理功能开关 (MANAGE_FEATURE_TOGGLE)...")
    response = await ble_manager.send_command(ServiceCommand.MANAGE_FEATURE_TOGGLE, bytes([token_manager.token, 0x00]))
    if response and response.size > 0:
        print(f"✅ 功能开关响应: {response.payload.hex()}")
    else:
        print("❌ 管理功能开关失败")

async def test_port_control(ble_manager, token_manager):
    """测试端口控制命令"""
    print("\n" + "="*60)
    print("🧪 测试端口控制命令")
    print("="*60)
    
    # 测试打开端口0
    print("\n1️⃣  测试打开端口0 (TURN_ON_PORT)...")
    payload = bytes([token_manager.token, 0x00])  # 端口0
    response = await ble_manager.send_command(ServiceCommand.TURN_ON_PORT, payload)
    if response:
        print(f"✅ 端口0打开成功")
    else:
        print("❌ 打开端口0失败")
    
    # 等待一下
    await asyncio.sleep(1)
    
    # 检查供电状态
    print("\n2️⃣  检查供电状态...")
    response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token_manager.token]))
    if response and response.size > 0:
        status = parse_power_supply_status(response.payload)
        print(f"✅ 当前活动端口: {status['active_ports']}")
    
    # 测试关闭端口0
    print("\n3️⃣  测试关闭端口0 (TURN_OFF_PORT)...")
    payload = bytes([token_manager.token, 0x00])  # 端口0
    response = await ble_manager.send_command(ServiceCommand.TURN_OFF_PORT, payload)
    if response:
        print(f"✅ 端口0关闭成功")
    else:
        print("❌ 关闭端口0失败")
    
    # 再次检查供电状态
    print("\n4️⃣  再次检查供电状态...")
    response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token_manager.token]))
    if response and response.size > 0:
        status = parse_power_supply_status(response.payload)
        print(f"✅ 当前活动端口: {status['active_ports']}")

async def main():
    print("="*60)
    print("IonBridge BLE 综合测试")
    print("="*60)
    print("目标设备: CP02-0002A0")
    print("Token: 0x2F (47)")
    print("="*60)
    
    # 创建BLE管理器
    ble_manager = BLEManager()
    token_manager = TokenManager(ble_manager)
    
    try:
        # 扫描设备
        print("\n1️⃣  扫描设备...")
        devices = await ble_manager.scan_devices()
        if not devices:
            print("❌ 未找到设备")
            return
        
        print(f"✅ 找到 {len(devices)} 个设备:")
        for i, device in enumerate(devices):
            print(f"   {i+1}. {device.name} ({device.address}) RSSI: {device.rssi}")
        
        # 查找目标设备 CP02-0002A0
        target_device = None
        for device in devices:
            if "0002A0" in device.name:
                target_device = device
                break
        
        if target_device is None:
            print("\n⚠️  未找到目标设备 CP02-0002A0，使用第一个设备")
            target_device = devices[0]
        else:
            print(f"\n✅ 找到目标设备: {target_device.name}")
        
        # 连接设备
        print("\n2️⃣  连接设备...")
        print(f"连接到 {target_device.address}...")
        success = await ble_manager.connect(target_device.address)
        if not success:
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        
        # 设置已知Token（不需要暴力破解）
        print("\n3️⃣  设置Token...")
        token_manager.token = 0x2F  # 已知Token
        print(f"✅ Token: 0x{token_manager.token:02X} ({token_manager.token})")
        
        # 测试各类命令
        await test_device_commands(ble_manager, token_manager)
        await test_port_commands(ble_manager, token_manager)
        await test_power_commands(ble_manager, token_manager)
        await test_display_commands(ble_manager, token_manager)
        await test_system_commands(ble_manager, token_manager)
        await test_wifi_commands(ble_manager, token_manager)
        await test_feature_commands(ble_manager, token_manager)
        await test_port_control(ble_manager, token_manager)
        
        # 断开连接
        print("\n" + "="*60)
        print("断开连接...")
        await ble_manager.disconnect()
        print("✅ 已断开连接")
        
        print("\n" + "="*60)
        print("✅ 综合测试完成！")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ble_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
