#!/usr/bin/env python3
"""
测试设备电源状态和端口控制
"""

import asyncio
from ble_manager import BLEManager
from protocol import ServiceCommand, BLEFlags

async def main():
    print("="*60)
    print("IonBridge 设备电源状态测试")
    print("="*60)
    
    ble_manager = BLEManager()
    
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
        
        # 使用已知Token
        token = 0x2F
        print(f"\n3️⃣  使用Token: 0x{token:02X} ({token})")
        
        # 获取设备运行时间
        print("\n4️⃣  获取设备运行时间...")
        response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_UPTIME, bytes([token]))
        if response and response.size > 0:
            uptime = (response.payload[0] << 24) | (response.payload[1] << 16) | (response.payload[2] << 8) | response.payload[3]
            print(f"✅ 运行时间: {uptime}秒")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取运行时间失败")
        
        # 获取设备型号
        print("\n5️⃣  获取设备型号...")
        response = await ble_manager.send_command(ServiceCommand.GET_DEVICE_MODEL, bytes([token]))
        if response and response.size > 0:
            model = response.payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
            print(f"✅ 设备型号: {model}")
            print(f"   原始数据: {response.payload.hex()}")
        else:
            print("❌ 获取设备型号失败")
        
        # 获取供电状态
        print("\n6️⃣  获取供电状态...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            port_mask = response.payload[0]
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{port_mask:02X}")
            print(f"   原始数据: {response.payload.hex()}")
            
            # 解析哪些端口是打开的
            open_ports = []
            for i in range(8):
                if port_mask & (1 << i):
                    open_ports.append(i)
            print(f"   打开的端口: {open_ports}")
        else:
            print("❌ 获取供电状态失败")
        
        # 尝试打开端口0
        print("\n7️⃣  尝试打开端口0 (TURN_ON_PORT)...")
        payload = bytes([token, 0x00])
        response = await ble_manager.send_command(ServiceCommand.TURN_ON_PORT, payload)
        if response:
            print(f"✅ TURN_ON_PORT 命令发送成功")
            print(f"   原始数据: {response.payload.hex() if response.payload else b''}")
        else:
            print("❌ TURN_ON_PORT 命令失败")
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 再次获取供电状态
        print("\n8️⃣  再次获取供电状态...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            port_mask = response.payload[0]
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{port_mask:02X}")
            print(f"   原始数据: {response.payload.hex()}")
            
            # 解析哪些端口是打开的
            open_ports = []
            for i in range(8):
                if port_mask & (1 << i):
                    open_ports.append(i)
            print(f"   打开的端口: {open_ports}")
        else:
            print("❌ 获取供电状态失败")
        
        # 尝试使用 TOGGLE_PORT_POWER
        print("\n9️⃣  尝试使用 TOGGLE_PORT_POWER...")
        payload = bytes([token, 0x01])  # 端口0
        response = await ble_manager.send_command(ServiceCommand.TOGGLE_PORT_POWER, payload)
        if response:
            print(f"✅ TOGGLE_PORT_POWER 命令发送成功")
            print(f"   原始数据: {response.payload.hex() if response.payload else b''}")
        else:
            print("❌ TOGGLE_PORT_POWER 命令失败")
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 再次获取供电状态
        print("\n🔟  再次获取供电状态...")
        response = await ble_manager.send_command(ServiceCommand.GET_POWER_SUPPLY_STATUS, bytes([token]))
        if response and response.size > 0:
            port_mask = response.payload[0]
            print(f"✅ 供电状态:")
            print(f"   端口掩码: 0x{port_mask:02X}")
            print(f"   原始数据: {response.payload.hex()}")
            
            # 解析哪些端口是打开的
            open_ports = []
            for i in range(8):
                if port_mask & (1 << i):
                    open_ports.append(i)
            print(f"   打开的端口: {open_ports}")
        else:
            print("❌ 获取供电状态失败")
        
        # 断开连接
        print("\n" + "="*60)
        print("断开连接...")
        await ble_manager.disconnect()
        print("✅ 已断开连接")
        
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
