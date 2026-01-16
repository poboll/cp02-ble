#!/usr/bin/env python3
"""
IonBridge 设备配置脚本
功能：
1. 打开指定端口
2. 配置 WiFi
3. 重启设备（不重置数据）
"""

import asyncio
import sys
sys.path.insert(0, '.')

from ble_manager import BLEManager

# WiFi 配置
WIFI_SSID = "不要连很卡"
WIFI_PASSWORD = "00000000"

# 设备地址
DEVICE_ADDRESS = "008A2D04-84D8-5659-6574-F98AB0C75E87"

async def main():
    ble = BLEManager()
    
    print("="*60)
    print("IonBridge 设备配置脚本")
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
    
    # 3. 打开端口 1
    print("\n3️⃣  打开端口 1...")
    # 端口掩码：Bit 1 = 0x02
    port_mask = 0x02
    success = await ble.set_port_power(port_mask, enable=True)
    if success:
        print(f"✅ 端口 1 已打开 (端口掩码: 0x{port_mask:02X})")
    else:
        print(f"❌ 打开端口 1 失败")
        return False
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 4. 验证端口状态
    print("\n4️⃣  验证端口状态...")
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
    else:
        print("❌ 获取端口状态失败")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 5. 配置 WiFi
    print("\n5️⃣  配置 WiFi...")
    print(f"  SSID: {WIFI_SSID}")
    print(f"  密码: {'*' * len(WIFI_PASSWORD)}")
    
    success = await ble.set_wifi(WIFI_SSID, WIFI_PASSWORD)
    if success:
        print("✅ WiFi 配置成功")
    else:
        print("❌ WiFi 配置失败")
        return False
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 6. 检查 WiFi 状态（添加错误处理）
    print("\n6️⃣  检查 WiFi 状态...")
    wifi_status = await ble.get_wifi_status()
    
    if wifi_status is None:
        print("❌ WiFi 状态查询失败（未连接或配置错误）")
        print("💡 提示：设备重启后 WiFi 配置才会生效")
    elif isinstance(wifi_status, bytes) and len(wifi_status) == 1:
        status_code = wifi_status[0]
        if status_code == 0x00:
            print("✅ WiFi 状态: 成功")
        elif status_code == 0x01:
            print("⚠️  WiFi 状态: 失败（可能未配置或未连接）")
            print("💡 提示：设备重启后 WiFi 配置才会生效")
        else:
            print(f"⚠️  WiFi 状态: 未知状态码 0x{status_code:02X}")
    else:
        print(f"✅ WiFi 状态: {repr(wifi_status)}")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 7. 重启设备（使用 REBOOT，不是 RESET）
    print("\n7️⃣  重启设备...")
    print("⚠️  注意：使用 REBOOT 命令，不会重置 Token 和 WiFi 配置")
    
    confirm = input("\n确认重启设备？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 已取消重启")
        await ble.disconnect()
        return False
    
    success = await ble.reboot_device()
    if success:
        print("✅ 重启命令已发送")
        print("\n💡 提示：")
        print("  - 设备正在重启...")
        print("  - Token 依然是 0xFE（不会改变）")
        print("  - WiFi 配置将在重启后生效")
        print("  - 请等待 30 秒后再连接设备")
    else:
        print("❌ 重启命令发送失败")
        return False
    
    # 断开连接
    await ble.disconnect()
    
    print("\n" + "="*60)
    print("✅ 配置完成！")
    print("="*60)
    print("\n下一步：")
    print("  1. 等待 30 秒让设备重启")
    print("  2. 重新连接设备")
    print("  3. 检查 WiFi 状态（应该会返回 IP 地址）")
    
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
