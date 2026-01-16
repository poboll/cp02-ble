#!/usr/bin/env python3
"""
IonBridge BLE 完整解析测试脚本
使用完整的响应解析函数，测试所有命令
"""

import asyncio
import sys
from ble_manager import BLEManager
from protocol import (
    ServiceCommand, BLEFlags,
    parse_wifi_status_response,
    parse_charging_strategy_response,
    parse_display_settings_response,
    parse_port_config_response,
    parse_power_statistics_response,
    parse_charging_status_response,
    parse_power_supply_status_response,
    parse_device_info_response,
    parse_device_model_response,
    parse_device_serial_response,
    parse_device_uptime_response
)

async def main():
    print("="*60)
    print("IonBridge BLE 完整解析测试")
    print("="*60)
    print("目标设备: CP02-0002A0")
    print("Token: 0x2F (47)")
    print("="*60)
    
    ble_manager = BLEManager()
    token = 0x2F
    
    try:
        # 扫描设备
        print("\n1️⃣  扫描设备...")
        devices = await ble_manager.scan_devices()
        if not devices:
            print("❌ 未找到设备")
            return
        
        # 查找目标设备 CP02-0002A0
        target_device = None
        for device in devices:
            if "0002A0" in device.name:
                target_device = device
                break
        
        if target_device is None:
            print("❌ 未找到目标设备 CP02-0002A0")
            return
        
        # 连接设备
        print(f"\n2️⃣  连接到 {target_device.name}...")
        success = await ble_manager.connect(target_device.address)
        if not success:
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        
        # ========== 设备管理命令 ==========
        print("\n" + "="*60)
        print("🧪 测试设备管理命令")
        print("="*60)
        
        # 获取设备型号
        print("\n1️⃣  获取设备型号 (GET_DEVICE_MODEL)...")
        response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_MODEL, bytes([token]))
        if response and response.size > 0:
            result = parse_device_model_response(response.payload)
            print(f"✅ 设备型号:")
            print(f"   型号: {result['model']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取设备型号失败")
        
        # 获取设备运行时间
        print("\n2️⃣  获取设备运行时间 (GET_DEVICE_UPTIME)...")
        response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_UPTIME, bytes([token]))
        if response and response.size > 0:
            result = parse_device_uptime_response(response.payload)
            uptime = result['uptime']
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            minutes = (uptime % 3600) // 60
            print(f"✅ 设备运行时间:")
            print(f"   {days}天 {hours}小时 {minutes}分钟 ({uptime}秒)")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取设备运行时间失败")
        
        # 获取设备序列号
        print("\n3️⃣  获取设备序列号 (GET_DEVICE_SERIAL_NO)...")
        response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_SERIAL_NO, bytes([token]))
        if response and response.size > 0:
            result = parse_device_serial_response(response.payload)
            print(f"✅ 设备序列号:")
            print(f"   序列号: {result['serial']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取设备序列号失败")
        
        # ========== 端口管理命令 ==========
        print("\n" + "="*60)
        print("🧪 测试端口管理命令")
        print("="*60)
        
        # 获取供电状态
        print("\n1️⃣  获取供电状态 (GET_POWER_SUPPLY_STATUS)...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            result = parse_power_supply_status_response(response.payload)
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{result['port_mask']:02X}")
            print(f"   打开的端口: {result['open_ports']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取供电状态失败")
        
        # 获取端口配置
        print("\n2️⃣  获取端口配置 (GET_PORT_CONFIG)...")
        for port_id in range(4):
            payload = bytes([token, port_id])
            response = await ble_manager.send_command(ServiceCommand.GET_PORT_CONFIG, payload)
            if response and response.size > 0:
                result = parse_port_config_response(response.payload)
                print(f"✅ 端口 {port_id} 配置:")
                print(f"   Power Features: {result['power_features']}")
                print(f"   支持协议: {', '.join(result['protocols'][:8])}")
                if len(result['protocols']) > 8:
                    print(f"   ... 还有 {len(result['protocols']) - 8} 个协议")
                print(f"   原始数据: {response.payload.hex()}")
            else:
                print(f"❌ 获取端口 {port_id} 配置失败")
        
        # 获取充电状态
        print("\n3️⃣  获取充电状态 (GET_CHARGING_STATUS)...")
        response = await ble_manager.send_command(ServiceCommand.GET_CHARGING_STATUS, bytes([token]))
        if response and response.size > 0:
            result = parse_charging_status_response(response.payload)
            print(f"✅ 充电状态:")
            print(f"   端口数量: {result['num_ports']}")
            for port in result['ports']:
                print(f"   端口 {port['port_id']}: {port['voltage']:.2f}V, {port['current']:.3f}A")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取充电状态失败")
        
        # ========== 电源管理命令 ==========
        print("\n" + "="*60)
        print("🧪 测试电源管理命令")
        print("="*60)
        
        # 获取充电策略
        print("\n1️⃣  获取充电策略 (GET_CHARGING_STRATEGY)...")
        response = await ble_manager.send_command(ServiceCommand.GET_CHARGING_STRATEGY, bytes([token]))
        if response and response.size > 0:
            result = parse_charging_strategy_response(response.payload)
            print(f"✅ 充电策略:")
            print(f"   策略: {result['strategy_name']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取充电策略失败")
        
        # 获取功率统计
        print("\n2️⃣  获取功率统计 (GET_POWER_STATISTICS)...")
        for port_id in range(4):
            payload = bytes([token, port_id])
            response = await ble_manager.send_command(ServiceCommand.GET_POWER_STATISTICS, payload)
            if response and response.size > 0:
                result = parse_power_statistics_response(response.payload)
                print(f"✅ 端口 {port_id} 功率统计:")
                print(f"   电压: {result['voltage']:.2f}V")
                print(f"   电流: {result['current']:.3f}A")
                print(f"   功率: {result['power']:.2f}W")
                print(f"   温度: {result['temperature']}°C")
                if result['uptime'] > 0:
                    days = result['uptime'] // 86400
                    hours = (result['uptime'] % 86400) // 3600
                    minutes = (result['uptime'] % 3600) // 60
                    print(f"   运行时间: {days}天 {hours}小时 {minutes}分钟")
                print(f"   原始数据: {response.payload.hex()}")
            else:
                print(f"❌ 获取端口 {port_id} 功率统计失败")
        
        # ========== 显示管理命令 ==========
        print("\n" + "="*60)
        print("🧪 测试显示管理命令")
        print("="*60)
        
        # 获取显示设置
        print("\n1️⃣  获取显示设置 (GET_DISPLAY_INTENSITY)...")
        response = await ble_manager.send_command(ServiceCommand.GET_DISPLAY_INTENSITY, bytes([token]))
        if response and response.size > 0:
            result = parse_display_settings_response(response.payload)
            print(f"✅ 显示设置:")
            print(f"   亮度: {result['brightness']}")
            print(f"   模式: {result['mode_name']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取显示设置失败")
        
        # ========== WiFi管理命令 ==========
        print("\n" + "="*60)
        print("🧪 测试WiFi管理命令")
        print("="*60)
        
        # 获取WiFi状态
        print("\n1️⃣  获取WiFi状态 (GET_WIFI_STATUS)...")
        response = await ble_manager.send_command(ServiceCommand.GET_WIFI_STATUS, bytes([token]))
        if response and response.size > 0:
            result = parse_wifi_status_response(response.payload)
            print(f"✅ WiFi状态:")
            print(f"   状态: {result['status_name']}")
            if 'ip' in result:
                print(f"   IP地址: {result['ip']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取WiFi状态失败")
        
        # ========== 端口控制测试 ==========
        print("\n" + "="*60)
        print("🧪 测试端口控制命令")
        print("="*60)
        
        # 尝试使用 TOGGLE_PORT_POWER
        print("\n1️⃣  尝试切换端口0 (TOGGLE_PORT_POWER)...")
        payload = bytes([token, 0x01])  # 端口0掩码
        response = await ble_manager.send_command(ServiceCommand.TOGGLE_PORT_POWER, payload)
        if response:
            print(f"✅ TOGGLE_PORT_POWER 命令发送成功")
            print(f"   原始数据: {response.payload.hex() if response.payload else b''}")
        else:
            print("❌ TOGGLE_PORT_POWER 命令失败")
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 再次获取供电状态
        print("\n2️⃣  再次获取供电状态...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            result = parse_power_supply_status_response(response.payload)
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{result['port_mask']:02X}")
            print(f"   打开的端口: {result['open_ports']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取供电状态失败")
        
        # 尝试切换端口1
        print("\n3️⃣  尝试切换端口1 (TOGGLE_PORT_POWER)...")
        payload = bytes([token, 0x02])  # 端口1掩码
        response = await ble_manager.send_command(ServiceCommand.TOGGLE_PORT_POWER, payload)
        if response:
            print(f"✅ TOGGLE_PORT_POWER 命令发送成功")
            print(f"   原始数据: {response.payload.hex() if response.payload else b''}")
        else:
            print("❌ TOGGLE_PORT_POWER 命令失败")
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 再次获取供电状态
        print("\n4️⃣  再次获取供电状态...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            result = parse_power_supply_status_response(response.payload)
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{result['port_mask']:02X}")
            print(f"   打开的端口: {result['open_ports']}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取供电状态失败")
        
        # 断开连接
        print("\n" + "="*60)
        print("断开连接...")
        await ble_manager.disconnect()
        print("✅ 已断开连接")
        
        print("\n" + "="*60)
        print("✅ 完整解析测试完成！")
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
