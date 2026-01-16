import asyncio
from bleak import BleakClient, BleakScanner

TARGET_NAME = "CP02-002548"
TOKEN = 0xFE

CMD_GET_WIFI_STATUS = 0x34 # 查状态
CMD_GET_WIFI_IP     = 0x35 # 查IP

CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea"
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea"

def build_packet(service):
    # 简单的查询包构建
    header = [0, 1, service, 0, 2, 0, 0, 1] # Flag=2, Size=1
    checksum = sum(header) & 0xFF
    return bytes(header + [checksum, TOKEN])

def parse_response(data):
    if len(data) < 10: return
    payload = data[10:]
    print(f"🔎 收到数据 (Hex): {payload.hex()}")
    try:
        # 尝试解码字符串
        print(f"📝 尝试解码: {payload.decode('utf-8', errors='ignore')}")
    except:
        pass

async def main():
    print("👨‍⚕️ 开始 Wi-Fi 诊断...")
    device = await BleakScanner.find_device_by_filter(lambda d, ad: d.name and TARGET_NAME in d.name)
    if not device: return

    async with BleakClient(device) as client:
        print("✅ 连接成功")
        await client.start_notify(CHAR_TX_UUID, lambda s, d: parse_response(d))
        
        print("\n👉 正在询问: 你连上 Wi-Fi 了吗？(查 IP)")
        await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_GET_WIFI_IP), response=True)
        await asyncio.sleep(2)
        
        print("\n👉 正在询问: 现在的 Wi-Fi 状态咋样？")
        await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_GET_WIFI_STATUS), response=True)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())