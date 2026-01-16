import asyncio
from bleak import BleakClient, BleakScanner

# ========== 🎯 目标设备配置 ==========
# 你的新设备名称
TARGET_NAME = "CP02-002548" 
# 既然你确认了 Token 是 0xA1 (161)
TOKEN = 0xA1
# ===================================

# 小电拼固定 UUID
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea" # 发送 (Write)
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea" # 监听 (Notify)

# 指令码: REBOOT_DEVICE
CMD_REBOOT = 0x11

def build_reboot_packet(token):
    """
    构造重启数据包
    Header: [Ver, ID, Service(0x11), Seq, Flags, Size(3), Checksum]
    Payload: [Token]
    """
    version = 0
    id_val = 1
    service = CMD_REBOOT
    sequence = 0
    flags = 5 # SYN_ACK
    
    # Payload
    payload = bytes([token])
    
    # Size (3 bytes, Big-Endian for Version 0)
    size_bytes = [0, 0, len(payload)]
    
    # Header 原始数据 (不含 Checksum)
    header_raw = [version, id_val, service, sequence, flags] + size_bytes
    
    # 计算 Checksum
    checksum = sum(header_raw) & 0xFF
    
    # 拼接完整包
    packet = bytes(header_raw + [checksum]) + payload
    return packet

async def main():
    print(f"💀 准备对 {TARGET_NAME} 执行远程重启...")
    print(f"🔑 使用 Token: 0x{TOKEN:02X} (161)")

    # 1. 扫描设备
    print("🔍 正在搜索设备信号...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and TARGET_NAME in d.name
    )

    if not device:
        print(f"❌ 找不到 {TARGET_NAME}，请确保设备通电且就在电脑旁边。")
        return

    print(f"🔗 发现设备 {device.address}，正在连接...")

    async with BleakClient(device) as client:
        print("✅ 连接成功！")
        
        # 订阅通知（虽然重启时设备可能来不及回复，但加上保险）
        try:
            await client.start_notify(CHAR_TX_UUID, lambda s, d: print(f"   [设备反馈] {d.hex()}"))
        except:
            pass

        # 2. 构造并发送重启包
        packet = build_reboot_packet(TOKEN)
        print(f"🚀 发送重启指令 (Hex): {packet.hex()}")
        
        try:
            await client.write_gatt_char(CHAR_RX_UUID, packet, response=True)
            print("✅ 指令发送完毕！")
        except Exception as e:
            # 如果发送瞬间设备断开，可能会报错，属正常现象
            print(f"⚠️ 发送时连接断开 (可能已重启): {e}")

        # 3. 验证结果
        print("⏳ 等待 5 秒确认状态...")
        await asyncio.sleep(5)
        
        if not client.is_connected:
            print("\n🎉 成功！设备已断开连接，正在重启中...")
            print("👉 请等待 15-20 秒，然后去 App 搜索连接。")
            print("👉 如果 App 询问密码，请尝试输入：0161")
        else:
            print("\n⚠️ 设备依然在线，未重启。")
            print("   如果 Token 确实是 0xA1，那可能是固件卡死，建议物理拔插头。")

if __name__ == "__main__":
    asyncio.run(main())