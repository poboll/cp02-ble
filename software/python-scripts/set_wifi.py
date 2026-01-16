import asyncio
from bleak import BleakClient, BleakScanner

# ========== ⚙️ 这里填你家的 WiFi ==========
WIFI_SSID = "不要连很卡"      # 你的 WiFi 名字 (2.4G)
WIFI_PASS = "00000000"  # 你的 WiFi 密码
# ========================================

# 🎯 设备配置
TARGET_NAME = "CP02-002548"
TOKEN = 0xFE  # 你的管理员 Token (161)

# 指令集 (来自 service.h)
CMD_SET_SSID = 0x31
CMD_SET_PASS = 0x32
CMD_RESET_WIFI = 0x33 # 让配置生效

CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea"
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea"

def build_packet(service, text_payload):
    """构建字符串指令包"""
    version = 0; id_val = 1; sequence = 0; flags = 2 # ACK
    
    # Payload 格式: [Token] + [字符串字节]
    # 注意：这里不需要字符串长度头，通常直接发字符串内容即可
    payload = bytes([TOKEN]) + text_payload.encode('utf-8')
    
    size_bytes = [0, 0, len(payload)]
    header_raw = [version, id_val, service, sequence, flags] + size_bytes
    checksum = sum(header_raw) & 0xFF
    return bytes(header_raw + [checksum]) + payload

async def main():
    print(f"📡 准备给 {TARGET_NAME} 配置 WiFi...")
    print(f"   SSID: {WIFI_SSID}")
    
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and TARGET_NAME in d.name
    )

    if not device:
        print("❌ 找不到设备 (请检查手机蓝牙是否关闭)")
        return

    async with BleakClient(device) as client:
        print("✅ 蓝牙已连接！")
        
        # 1. 发送 SSID
        print("🚀 发送 WiFi 名称...")
        pkt_ssid = build_packet(CMD_SET_SSID, WIFI_SSID)
        await client.write_gatt_char(CHAR_RX_UUID, pkt_ssid, response=True)
        await asyncio.sleep(0.5)
        
        # 2. 发送密码
        print("🚀 发送 WiFi 密码...")
        pkt_pass = build_packet(CMD_SET_PASS, WIFI_PASS)
        await client.write_gatt_char(CHAR_RX_UUID, pkt_pass, response=True)
        await asyncio.sleep(0.5)
        
        # 3. 触发重置/连接
        print("🔄 发送重置指令让 WiFi 生效...")
        pkt_reset = build_packet(CMD_RESET_WIFI, "") # 空 payload
        try:
            await client.write_gatt_char(CHAR_RX_UUID, pkt_reset, response=True)
        except:
            pass # 重置可能会导致断连，这是正常的
            
        print("✅ 配置完成！请等待设备连接 WiFi。")
        print("⚠️ 关键步骤：请立刻断开蓝牙连接（或关闭本脚本），否则 Web 后台可能不会启动！")

if __name__ == "__main__":
    asyncio.run(main())