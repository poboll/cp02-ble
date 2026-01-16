import asyncio
import struct
import sys
from bleak import BleakClient, BleakScanner

# ========== 🎯 配置区域 ==========
TARGET_NAME = "CP02-002548"
TOKEN = 0xFE  # 你的 Token (161)
# ===============================

# 蓝牙 UUID
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea" # 发送
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea" # 接收

# 指令集
CMD_TURN_ON_PORT  = 0x4C
CMD_TURN_OFF_PORT = 0x4D
CMD_GET_ALL_STATS = 0x4A 

def build_packet(service, payload_bytes):
    """构建指令包 (Flag=2 ACK模式)"""
    version = 0; id_val = 1; sequence = 0; flags = 2 
    full_payload = bytes([TOKEN]) + bytes(payload_bytes)
    size_bytes = [0, 0, len(full_payload)]
    header_raw = [version, id_val, service, sequence, flags] + size_bytes
    checksum = sum(header_raw) & 0xFF
    return bytes(header_raw + [checksum]) + full_payload

def parse_stats(data):
    """解析电压电流数据"""
    if len(data) < 10: return
    payload = data[10:]
    
    # 假设每端口 8 字节
    chunk_size = 8
    num_ports = len(payload) // chunk_size
    
    print(f"\n{'端口':<6} | {'状态':<6} | {'电压 (V)':<10} | {'电流 (A)':<10} | {'功率 (W)':<10}")
    print("-" * 52)
    
    for i in range(num_ports):
        chunk = payload[i*chunk_size : (i+1)*chunk_size]
        if len(chunk) < 8: continue
        
        try:
            # 格式解析: <BBHHH (小端序)
            # B(状态) B(协议) H(电压mV) H(电流mA) H(功率0.1W?)
            status, proto, vol_raw, cur_raw, pwr_raw = struct.unpack('<BBHHH', chunk)
            
            # 数据转换 (基于常见 PD 协议猜测)
            vol_v = vol_raw / 1000.0  # mV -> V
            cur_a = cur_raw / 1000.0  # mA -> A (也可能是 10mA，视读数而定)
            pwr_w = pwr_raw / 100.0   # 10mW -> W (猜测)
            
            # 状态判断 (0x0F=开启, 0xFF=关闭)
            is_on = (status & 0x0F) == 0x0F
            status_str = "🟢 ON" if is_on else "🔴 OFF"
            
            # 显示
            print(f"Port {i:<2} | {status_str:<6} | {vol_v:<10.2f} | {cur_a:<10.2f} | {pwr_w:<10.2f}")
            
        except Exception as e:
            print(f"解析错误 Port {i}: {e}")
    print("-" * 52 + "\n")

async def input_loop(client):
    """处理用户输入"""
    print("\n🎮 控制台已就绪！可用指令：")
    print("   on 0      -> 打开端口 0")
    print("   off 0     -> 关闭端口 0")
    print("   stat      -> 读取一次数据")
    print("   watch     -> 持续监控 (按 Ctrl+C 退出)")
    print("   exit      -> 退出程序")

    loop = asyncio.get_running_loop()
    
    while True:
        # 使用 asyncio 兼容的方式获取输入
        cmd = await loop.run_in_executor(None, input, ">>> ")
        cmd = cmd.strip().lower()
        parts = cmd.split()
        
        if not parts: continue
        
        op = parts[0]
        
        if op == 'exit' or op == 'q':
            print("👋 再见")
            break
            
        elif op == 'on':
            port = int(parts[1]) if len(parts) > 1 else 0
            print(f"🚀 打开端口 {port}...")
            await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_TURN_ON_PORT, [port]), response=True)
            
        elif op == 'off':
            port = int(parts[1]) if len(parts) > 1 else 0
            print(f"🚀 关闭端口 {port}...")
            await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_TURN_OFF_PORT, [port]), response=True)
            
        elif op == 'stat':
            print("📊 读取数据...")
            await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_GET_ALL_STATS, []), response=True)
            # 等待一会，确保回调打印出来再显示提示符
            await asyncio.sleep(0.5)
            
        elif op == 'watch':
            print("👀 进入监控模式 (按 Ctrl+C 停止)...")
            try:
                while True:
                    await client.write_gatt_char(CHAR_RX_UUID, build_packet(CMD_GET_ALL_STATS, []), response=True)
                    await asyncio.sleep(2.0) # 每 2 秒刷新一次
            except KeyboardInterrupt:
                print("\n⏹ 停止监控")
                
        else:
            print("❌ 未知指令")

async def main():
    print(f"🔍 正在连接 {TARGET_NAME} ...")
    
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and TARGET_NAME in d.name
    )

    if not device:
        print("❌ 找不到设备 (请关闭手机蓝牙)")
        return

    async with BleakClient(device) as client:
        print("✅ 连接成功！(Token: 0xA1)")
        
        # 注册回调，收到数据自动打印
        await client.start_notify(CHAR_TX_UUID, lambda s, d: parse_stats(d))
        
        # 进入输入循环
        await input_loop(client)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass