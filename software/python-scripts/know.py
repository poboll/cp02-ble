import asyncio
import struct
from bleak import BleakClient, BleakScanner

# ========== 🎯 你的配置 ==========
TARGET_NAME = "CP02-002548"
TOKEN = 0x70  # 我们的老朋友
# ===============================

# UUID
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea"
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea"

# 指令
CMD_SET_PORT_CONFIG = 0x57
CMD_GET_PORT_CONFIG = 0x58

class PowerFeatures:
    """
    对应 C++ 结构体的位域映射
    总共 3 字节 (24 bits)
    """
    def __init__(self, data=None):
        if data:
            self.b1, self.b2, self.b3 = data[0], data[1], data[2]
        else:
            self.b1 = self.b2 = self.b3 = 0

    def to_bytes(self):
        return bytes([self.b1, self.b2, self.b3])

    def __repr__(self):
        # 解析各个位用于显示
        return (
            f"<B1: TFCP={self.get(0,0)}, PE={self.get(0,1)}, QC2={self.get(0,2)}, QC3={self.get(0,3)}, "
            f"QC3+={self.get(0,4)}, AFC={self.get(0,5)}, FCP={self.get(0,6)}, HVSCP={self.get(0,7)} | "
            f"B2: LVSCP={self.get(1,0)}, SFCP={self.get(1,1)}, Apple={self.get(1,2)}, Sam={self.get(1,3)}, "
            f"UFCS={self.get(1,4)}, PD={self.get(1,5)}, PDComp={self.get(1,6)}, Limit={self.get(1,7)} | "
            f"B3: LVPPS={self.get(2,0)}, EPR={self.get(2,1)}, 5V5A={self.get(2,2)}, HVPPS={self.get(2,3)}>"
        )

    def get(self, byte_idx, bit_idx):
        val = [self.b1, self.b2, self.b3][byte_idx]
        return 1 if (val & (1 << bit_idx)) else 0

    def set(self, byte_idx, bit_idx, enable):
        val = [self.b1, self.b2, self.b3][byte_idx]
        if enable:
            val |= (1 << bit_idx)
        else:
            val &= ~(1 << bit_idx)
            
        if byte_idx == 0: self.b1 = val
        elif byte_idx == 1: self.b2 = val
        elif byte_idx == 2: self.b3 = val

    # 快捷设置方法
    def set_pd_only(self):
        """预设：只开启 PD 相关"""
        self.b1 = 0x00 # 关闭 QC, PE, AFC, FCP 等
        self.b2 = 0x20 # 开启 EnablePd (Bit 5), 关闭其他
        self.b3 = 0x07 # 开启 LVPPS, EPR, 5V5A

    def set_all_enable(self):
        """预设：开启所有"""
        self.b1 = 0xFF
        self.b2 = 0x7F # Bit 7 (Limit) 通常不作为协议开启
        self.b3 = 0x0F

def build_packet(service, payload_content):
    version = 0; id_val = 1; sequence = 0; flags = 2
    payload = bytes([TOKEN]) + payload_content
    size_bytes = [0, 0, len(payload)]
    header_raw = [version, id_val, service, sequence, flags] + size_bytes
    checksum = sum(header_raw) & 0xFF
    return bytes(header_raw + [checksum]) + payload

def parse_config_response(data):
    if len(data) < 10: return
    payload = data[10:]
    
    # 每个端口 3 字节 (Version 0)
    # 根据文档：Version 0: 3 bytes per port
    chunk_size = 3
    num_ports = len(payload) // chunk_size
    
    print("\n📊 当前端口协议配置:")
    for i in range(num_ports):
        chunk = payload[i*chunk_size : (i+1)*chunk_size]
        if len(chunk) < 3: continue
        pf = PowerFeatures(chunk)
        print(f"Port {i}: {pf}")
    return payload

async def main():
    print(f"🔧 协议配置工具连接: {TARGET_NAME} ...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and TARGET_NAME in d.name
    )
    if not device: print("❌ 未找到"); return

    async with BleakClient(device) as client:
        print("✅ 连接成功")
        
        # 1. 获取当前配置
        print("📥 读取当前配置...")
        # GET_PORT_CONFIG: [Token] [Version=0]
        req = build_packet(CMD_GET_PORT_CONFIG, bytes([0x00]))
        
        # 我们需要捕获回调数据
        current_data = None
        def callback(s, d):
            nonlocal current_data
            current_data = parse_config_response(d)
            
        await client.start_notify(CHAR_TX_UUID, callback)
        await client.write_gatt_char(CHAR_RX_UUID, req, response=True)
        await asyncio.sleep(2)
        
        if not current_data:
            print("❌ 读取失败"); return

        # 2. 交互式修改
        print("\n👇 你想修改哪个端口？(输入 0-7，或 q 退出)")
        p_idx = input(">>> ").strip()
        if p_idx == 'q': return
        port_idx = int(p_idx)
        
        print("👇 请选择预设模式:")
        print("   1. 纯净 PD 模式 (只留 USB-PD，禁用 QC/FCP 等)")
        print("   2. 全开模式 (开启所有协议)")
        print("   3. 恢复默认 (保守配置)")
        mode = input(">>> ").strip()
        
        # 创建新的特征对象
        new_pf = PowerFeatures()
        
        if mode == '1':
            new_pf.set_pd_only()
            print("⚙️ 已选择: 纯净 PD 模式")
        elif mode == '2':
            new_pf.set_all_enable()
            print("⚙️ 已选择: 全开模式")
        else:
            print("取消操作")
            return

        # 3. 构造写入包
        # 请求格式: [Token] [PortMask] [Version] [ConfigBytes...]
        # Version 0: 每个端口 3 字节
        
        port_mask = (1 << port_idx) # 只修改选中的端口
        version = 0x00              # 使用简化版本结构
        
        # 构造 Payload:
        # 这里的关键是：虽然我们只改一个端口，但根据 mask，我们只需要发这一个端口的数据吗？
        # 根据文档 BLE_Port_Protocol_Guide: "Port 0-7 Config: 8 * config_size bytes"
        # 通常协议要求必须发完整的 8 个端口的数据结构，或者根据 Mask 发送。
        # 为了稳妥，我们将未修改的端口数据原样填回，修改的端口填新数据。
        
        new_payload_data = bytearray()
        chunk_size = 3
        
        for i in range(8): # 假设总共8个端口
            original_chunk = current_data[i*3 : (i+1)*3]
            if i == port_idx:
                new_payload_data.extend(new_pf.to_bytes()) # 用新的
            else:
                new_payload_data.extend(original_chunk)    # 用旧的
        
        # 组装指令
        # 注意：有些固件实现只读取 Mask 对应的数据，有些要求全部。
        # 这里我们发送完整的 config list，配合 mask 应该最安全。
        config_payload = bytes([port_mask, version]) + new_payload_data
        
        pkt = build_packet(CMD_SET_PORT_CONFIG, config_payload)
        
        print(f"🚀 正在写入 Port {port_idx} 配置...")
        await client.write_gatt_char(CHAR_RX_UUID, pkt, response=True)
        await asyncio.sleep(1)
        
        print("✅ 配置已发送！正在回读验证...")
        await client.write_gatt_char(CHAR_RX_UUID, req, response=True)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())