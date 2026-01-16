#!/usr/bin/env python3
"""
IonBridge WiFi 详细诊断脚本
帮助排查 WiFi 连接问题
"""

import asyncio
import sys
import time
sys.path.insert(0, '.')

from ble_manager import BLEManager
from protocol import ServiceCommand

# 设备地址
DEVICE_ADDRESS = "008A2D04-84D8-5659-6574-F98AB0C75E87"

async def main():
    ble = BLEManager()
    
    print("="*60)
    print("IonBridge WiFi 详细诊断")
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
    
    # 3. 检查 WiFi 状态（多次尝试）
    print("\n3️⃣  检查 WiFi 状态（多次尝试）...")
    for attempt in range(5):
        print(f"\n尝试 {attempt + 1}/5:")
        
        wifi_status = await ble.get_wifi_status()
        
        if wifi_status is None:
            print("  ❌ WiFi 状态查询失败")
        elif isinstance(wifi_status, bytes) and len(wifi_status) == 1:
            status_code = wifi_status[0]
            if status_code == 0x00:
                print("  ✅ WiFi 状态: 成功 (SUCCESS)")
                print("  💡 设备已连接到 WiFi！")
                
                # 尝试获取 IP 地址
                await asyncio.sleep(1)
                response = await ble.execute(ServiceCommand.GET_DEVICE_WIFI_ADDR)
                if response and response.payload:
                    wifi_addr = response.payload.decode('utf-8', errors='replace').strip('\x00')
                    if wifi_addr:
                        print(f"  📡 IP 地址: {wifi_addr}")
                    else:
                        print("  ⚠️  IP 地址为空")
                break
            elif status_code == 0x01:
                print("  ⚠️  WiFi 状态: 失败 (FAILURE)")
                if attempt < 4:
                    print("  💡 等待 5 秒后重试...")
                    await asyncio.sleep(5)
                else:
                    print("  ❌ 多次尝试后仍然失败")
            else:
                print(f"  ⚠️  WiFi 状态: 未知状态码 0x{status_code:02X}")
        else:
            # 尝试解析为字符串
            try:
                wifi_str = wifi_status.decode('utf-8', errors='replace').strip('\x00')
                if wifi_str:
                    print(f"  ✅ WiFi 状态: {wifi_str}")
                    if '192.168.' in wifi_str or '10.' in wifi_str:
                        print("  💡 设备已连接到 WiFi 并获取到 IP")
                    break
                else:
                    print("  ⚠️  WiFi 状态字符串为空")
            except:
                print(f"  ⚠️  WiFi 状态解析失败")
        
        if attempt < 4:
            await asyncio.sleep(2)
    
    # 4. 尝试扫描 WiFi 网络
    print("\n4️⃣  扫描 WiFi 网络...")
    for attempt in range(3):
        print(f"\n尝试 {attempt + 1}/3:")
        
        response = await ble.execute(ServiceCommand.SCAN_WIFI)
        if response and response.payload:
            print(f"  ✅ 扫描到 {len(response.payload)} 字节的 WiFi 数据")
            print(f"  原始数据: {response.payload.hex()}")
            
            # 尝试解析 WiFi 列表
            try:
                wifi_list = response.payload.decode('utf-8', errors='replace').strip('\x00')
                if wifi_list:
                    print(f"  WiFi 列表: {wifi_list}")
                    
                    # 检查是否包含我们的 WiFi
                    if "不要连很卡" in wifi_list:
                        print("  ✅ 找到目标 WiFi: 不要连很卡")
                    else:
                        print("  ⚠️  未找到目标 WiFi: 不要连很卡")
                        print("  💡 这可能是 WiFi 名称或密码错误")
                break
            except:
                print("  WiFi 列表解析失败")
        else:
            print("  ⚠️  WiFi 扫描失败")
        
        if attempt < 2:
            await asyncio.sleep(2)
    
    # 5. 获取设备信息
    print("\n5️⃣  获取设备信息...")
    device_info = await ble.get_device_info()
    if device_info:
        print("✅ 设备信息：")
        for key, value in device_info.items():
            print(f"  {key}: {value}")
    else:
        print("❌ 获取设备信息失败")
    
    # 6. 获取端口状态
    print("\n6️⃣  获取端口状态...")
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
    
    # 断开连接
    await ble.disconnect()
    
    print("\n" + "="*60)
    print("✅ WiFi 诊断完成！")
    print("="*60)
    
    print("\n💡 诊断建议：")
    print("\n如果 WiFi 状态为 FAILURE：")
    print("1. 检查 WiFi 热点是否开启")
    print("   - 确认 '不要连很卡' 热点已开启")
    print("   - 确认密码是 '00000000'")
    print("\n2. 检查 WiFi 信号强度")
    print("   - 确保设备在 WiFi 信号覆盖范围内")
    print("   - 避免距离太远或有障碍物")
    print("\n3. 尝试重新配置 WiFi")
    print("   - 运行: configure_device.py")
    print("   - 确认 SSID 和密码正确")
    print("\n4. 检查设备 WiFi 模块")
    print("   - 设备可能需要更长时间初始化 WiFi")
    print("   - 建议等待 1-2 分钟后再检查")
    print("\n5. 尝试其他 WiFi 网络")
    print("   - 可能当前 WiFi 有兼容性问题")
    print("   - 尝试连接到其他 WiFi 网络")
    
    print("\n如果 WiFi 扫描失败：")
    print("1. 设备 WiFi 模块可能未启动")
    print("2. 尝试重启设备")
    print("3. 检查设备固件版本")
    
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
