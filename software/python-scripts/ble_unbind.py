import asyncio
from bleak import BleakClient, BleakScanner

# 目标设备
TARGET_NAME = "CP02-0002A0"

# UUID
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea" # Write (发送)
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea" # Notify (接收)

# 指令: ASSOCIATE_DEVICE (0x10)
# 这个指令专门用于配对/绑定，通常会重置之前的绑定关系
CMD_ASSOCIATE = 0x10

def build_packet():
    """
    构造 ASSOCIATE 指令包
    因为 0x10 不需要 Token 验证，我们发送空 Payload 或 00 都可以
    """
    version = 0
    id_val = 1
    service = CMD_ASSOCIATE
    sequence = 0
    flags = 5 # SYN_ACK
    
    # Payload 为空或者 0x00
    payload = bytes([0x00]) 
    payload_size = len(payload)
    
    # Header construction (Size 3 bytes)
    size_bytes = [0, 0, payload_size]
    
    # 组合 Header
    header_raw = [version, id_val, service, sequence, flags] + size_bytes
    
    # 计算校验和
    checksum = sum(header_raw) & 0xFF
    
    # 完整包
    packet = bytes(header_raw + [checksum]) + payload
    return packet

async def main():
    print(f"🔓 正在尝试强制解绑 {TARGET_NAME} ...")
    
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and TARGET_NAME in d.name
    )
    
    if not device:
        print("❌ 找不到设备，请确保设备通电且就在旁边")
        return

    async with BleakClient(device) as client:
        print("✅ 连接成功！准备发送重置指令...")
        
        # 监听回复：设备应该会返回一个新的 Token
        async def callback(sender, data):
            print(f"\n✨✨✨ 收到设备响应！ ✨✨✨")
            print(f"数据: {data.hex()}")
            if len(data) >= 10:
                new_token = data[9] # Payload 的第一个字节通常是 Token
                print(f"🔑 设备返回的新 Token: 0x{new_token:02X} (十进制: {new_token})")
                print("⚠️ 请立即打开小程序尝试搜索！")

        await client.start_notify(CHAR_TX_UUID, callback)
        
        # 发送解绑/配对请求
        pkt = build_packet()
        print(f"🚀 发送 ASSOCIATE_DEVICE (0x10): {pkt.hex()}")
        await client.write_gatt_char(CHAR_RX_UUID, pkt, response=True)
        
        print("⏳ 等待 5 秒，请观察设备是否有滴声或灯光变化...")
        await asyncio.sleep(5)
        
        print("\n🏁 操作完成。")
        print("👉 如果上面显示了新 Token，说明重置成功。")
        print("👉 现在请断开 Python 连接，立刻去 App 里搜索！")

if __name__ == "__main__":
    asyncio.run(main())