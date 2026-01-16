#!/usr/bin/env python3
"""
IonBridge 设备配置验证脚本
验证重启后的配置是否生效
"""

import asyncio
import sys
sys.path.insert(0, '.')

from ble_manager import BLEManager

# 设备地址
DEVICE_ADDRESS = "008A2D04-84D8-5659-6574-F98AB0C75E87"

async def main():
    ble = BLEManager()
    
    print("="*60)
    print("IonBridge 设备配置验证")
    print("="*60)
    
    # 1. 连接设备
    print("\n1️⃣  连接设备...")
    success = await ble.connect(DEVICE_ADDRESS)
    if not success:
        print("❌ 连接失败")
        return False
    
    print("✅ 连接成功")
    
    # 2. 获取 Token
    print("\n2️⃣  获取 Token...")
    token = await ble.bruteforce_token()
    if not token:
        print("❌ Token 获取失败")
        return False
    
    print(f"✅ Token: 0x{token:02X}")
    
    # 验证 Token 是否还是 0xFE
    if token == 0xFE:
        print("✅ Token 未改变（设备未重置）")
    else:
        print(f"⚠️  Token 已改变（从 0xFE 变为 0x{token:02X}）")
    
    # 3. 检查端口状态
    print("\n3️⃣  检查端口状态...")
    power_status = await ble.get_power_supply_status()
    if power_status:
        status_value = int.from_bytes(power_status, 'little')
        print(f"✅ 供电状态: 0x{status_value:04X}")
        
        # 解析端口状态
        print("\n端口状态详情：")
        for i in range(8):
            if status_value & (1 << i):
                print(f"  端口 {i}: 🟢 通电中")
            else:
                print(f"  端口 {i}: ⚪ 无输出")
        
        # 检查端口 1 是否打开
        if status_value & 0x02:
            print("\n✅ 端口 1 已打开")
        else:
            print("\n⚠️  端口 1 未打开")
    else:
        print("❌ 获取端口状态失败")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 4. 检查 WiFi 状态
    print("\n4️⃣  检查 WiFi 状态...")
    wifi_status = await ble.get_wifi_status()
    
    if wifi_status is None:
        print("❌ WiFi 状态查询失败（未连接或配置错误）")
    elif isinstance(wifi_status, bytes) and len(wifi_status) == 1:
        status_code = wifi_status[0]
        if status_code == 0x00:
            print("✅ WiFi 状态: 成功")
            print("💡 设备可能已连接到 WiFi，但需要更详细的查询来获取 IP")
        elif status_code == 0x01:
            print("⚠️  WiFi 状态: 失败（可能未配置或未连接）")
            print("💡 提示：WiFi 配置可能需要更长时间生效")
        else:
            print(f"⚠️  WiFi 状态: 未知状态码 0x{status_code:02X}")
    else:
        # 尝试解析为字符串
        try:
            wifi_str = wifi_status.decode('utf-8', errors='replace').strip('\x00')
            if wifi_str:
                print(f"✅ WiFi 状态: {wifi_str}")
                # 检查是否包含 IP 地址
                if '192.168.' in wifi_str or '10.' in wifi_str:
                    print("✅ 设备已连接到 WiFi 并获取到 IP 地址")
            else:
                print("⚠️  WiFi 状态为空")
        except:
            print(f"⚠️  WiFi 状态: {repr(wifi_status)}")
    
    # 5. 获取设备信息
    print("\n5️⃣  获取设备信息...")
    device_info = await ble.get_device_info()
    if device_info:
        print("✅ 设备信息：")
        for key, value in device_info.items():
            print(f"  {key}: {value}")
    else:
        print("❌ 获取设备信息失败")
    
    # 断开连接
    await ble.disconnect()
    
    print("\n" + "="*60)
    print("✅ 验证完成！")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
