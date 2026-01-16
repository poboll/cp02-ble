#!/usr/bin/env python3
"""
IonBridge WiFi 网络连接详细检测脚本
检测 WiFi 连接状态、IP 地址等信息
"""

import asyncio
import sys
sys.path.insert(0, '.')

from ble_manager import BLEManager
from protocol import ServiceCommand

# 设备地址
DEVICE_ADDRESS = "008A2D04-84D8-5659-6574-F98AB0C75E87"

async def main():
    ble = BLEManager()
    
    print("="*60)
    print("IonBridge WiFi 网络连接详细检测")
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
    
    # 3. 检查 WiFi 状态
    print("\n3️⃣  检查 WiFi 状态...")
    wifi_status = await ble.get_wifi_status()
    
    if wifi_status is None:
        print("❌ WiFi 状态查询失败")
        print("💡 可能原因：")
        print("  - 设备未连接到 WiFi")
        print("  - WiFi 配置错误")
        print("  - 设备 WiFi 模块未启动")
    elif isinstance(wifi_status, bytes) and len(wifi_status) == 1:
        status_code = wifi_status[0]
        if status_code == 0x00:
            print("✅ WiFi 状态: 成功 (SUCCESS)")
            print("💡 设备已连接到 WiFi")
        elif status_code == 0x01:
            print("⚠️  WiFi 状态: 失败 (FAILURE)")
            print("💡 可能原因：")
            print("  - WiFi 未配置")
            print("  - WiFi 连接失败")
            print("  - WiFi 密码错误")
            print("  - WiFi 信号太弱")
            print("  - 设备需要更长时间连接")
        else:
            print(f"⚠️  WiFi 状态: 未知状态码 0x{status_code:02X}")
    else:
        # 尝试解析为字符串
        try:
            wifi_str = wifi_status.decode('utf-8', errors='replace').strip('\x00')
            if wifi_str:
                print(f"✅ WiFi 状态: {wifi_str}")
                
                # 检查是否包含 IP 地址
                if '192.168.' in wifi_str or '10.' in wifi_str or '172.' in wifi_str:
                    print("✅ 设备已连接到 WiFi 并获取到 IP 地址")
                    # 提取 IP 地址
                    import re
                    ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', wifi_str)
                    if ip_match:
                        print(f"📡 IP 地址: {ip_match.group()}")
                else:
                    print("⚠️  WiFi 状态字符串中未找到 IP 地址")
            else:
                print("⚠️  WiFi 状态字符串为空")
        except Exception as e:
            print(f"⚠️  WiFi 状态解析失败: {e}")
            print(f"   原始数据: {repr(wifi_status)}")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 4. 尝试获取 WiFi IP 地址
    print("\n4️⃣  获取 WiFi IP 地址...")
    try:
        # 使用 GET_DEVICE_WIFI_ADDR 命令
        response = await ble.execute(ServiceCommand.GET_DEVICE_WIFI_ADDR)
        if response and response.payload:
            wifi_addr = response.payload.decode('utf-8', errors='replace').strip('\x00')
            if wifi_addr:
                print(f"✅ WiFi IP 地址: {wifi_addr}")
            else:
                print("⚠️  WiFi IP 地址为空")
        else:
            print("❌ 获取 WiFi IP 地址失败")
    except Exception as e:
        print(f"⚠️  获取 WiFi IP 地址时出错: {e}")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 5. 扫描 WiFi 网络
    print("\n5️⃣  扫描 WiFi 网络...")
    try:
        # 使用 SCAN_WIFI 命令
        response = await ble.execute(ServiceCommand.SCAN_WIFI)
        if response and response.payload:
            print(f"✅ 扫描到 {len(response.payload)} 字节的 WiFi 数据")
            print(f"   原始数据: {response.payload.hex()}")
            
            # 尝试解析 WiFi 列表
            try:
                wifi_list = response.payload.decode('utf-8', errors='replace').strip('\x00')
                if wifi_list:
                    print(f"   WiFi 列表: {wifi_list}")
                    
                    # 检查是否包含我们的 WiFi
                    if "不要连很卡" in wifi_list:
                        print("✅ 找到目标 WiFi: 不要连很卡")
                    else:
                        print("⚠️  未找到目标 WiFi: 不要连很卡")
            except:
                print("   WiFi 列表解析失败，显示原始数据")
        else:
            print("⚠️  WiFi 扫描失败或无数据")
    except Exception as e:
        print(f"⚠️  WiFi 扫描时出错: {e}")
    
    # 等待 1 秒
    await asyncio.sleep(1)
    
    # 6. 获取设备运行时间
    print("\n6️⃣  获取设备运行时间...")
    try:
        response = await ble.execute(ServiceCommand.GET_DEVICE_UPTIME)
        if response and response.payload and len(response.payload) >= 4:
            uptime = int.from_bytes(response.payload[:4], 'little')
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            minutes = (uptime % 3600) // 60
            print(f"✅ 设备运行时间: {uptime} 秒")
            print(f"   约 {days} 天 {hours} 小时 {minutes} 分钟")
            
            # 检查是否最近重启过
            if uptime < 300:
                print("⚠️  设备最近刚重启（< 5 分钟）")
                print("💡 WiFi 可能还在连接中，请稍后再检查")
        else:
            print("❌ 获取运行时间失败")
    except Exception as e:
        print(f"⚠️  获取运行时间时出错: {e}")
    
    # 断开连接
    await ble.disconnect()
    
    print("\n" + "="*60)
    print("✅ WiFi 网络连接检测完成！")
    print("="*60)
    
    print("\n💡 建议：")
    print("1. 如果 WiFi 状态为 FAILURE，请检查：")
    print("   - WiFi 热点是否开启")
    print("   - WiFi 名称和密码是否正确")
    print("   - WiFi 信号强度")
    print("2. 如果设备最近刚重启，请等待 1-2 分钟后再检查")
    print("3. 可以使用 configure_device.py 重新配置 WiFi")
    
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
