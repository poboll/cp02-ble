"""
IonBridge BLE Protocol Definitions
Based on: https://github.com/ifanrx/IonBridge
Complete protocol implementation with all 60+ commands
"""

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Dict, List

# BLE UUIDs
SERVICE_UUID = "048e3f2e-e1a6-4707-9e74-a930e898a1ea"
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea"  # Notify (device -> app)
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea"  # Write (app -> device)

# Device name prefix
DEVICE_PREFIX = "CP02-"


class BLEFlags(IntEnum):
    """BLE message flags"""
    NONE = 0x0
    SYN = 0x1
    ACK = 0x2
    FIN = 0x3
    RST = 0x4
    SYN_ACK = 0x5


class ServiceCommand(IntEnum):
    """Service commands from service.h - Complete list"""
    # Test commands (0x00-0x09)
    BLE_ECHO_TEST = 0x00
    GET_DEBUG_LOG = 0x01
    GET_SECURE_BOOT_DIGEST = 0x02
    PING_MQTT_TELEMETRY = 0x03
    PING_HTTP = 0x04
    GET_DEVICE_PASSWORD = 0x05
    MANAGE_POWER_ALLOCATOR_ENABLED = 0x09
    
    # Device management (0x10-0x1F)
    ASSOCIATE_DEVICE = 0x10  # No token required!
    REBOOT_DEVICE = 0x11
    RESET_DEVICE = 0x12
    GET_DEVICE_SERIAL_NO = 0x13
    GET_DEVICE_UPTIME = 0x14
    GET_AP_VERSION = 0x15
    GET_BP_VERSION = 0x16  # SW3566 MCU version
    GET_FPGA_VERSION = 0x17  # FPGA version
    GET_ZRLIB_VERSION = 0x18  # ZRLIB version
    GET_DEVICE_BLE_ADDR = 0x19
    SWITCH_DEVICE = 0x1a
    GET_DEVICE_SWITCH = 0x1b
    GET_DEVICE_MODEL = 0x1c
    PUSH_LICENSE = 0x1d
    GET_BLE_RSSI = 0x1e
    GET_BLE_MTU = 0x1f
    
    # OTA commands (0x20-0x2F)
    PERFORM_BLE_OTA = 0x20
    PERFORM_WIFI_OTA = 0x21
    GET_WIFI_OTA_PROGRESS = 0x22
    CONFIRM_OTA = 0x23
    
    # WiFi commands (0x30-0x3F)
    SCAN_WIFI = 0x30
    GET_WIFI_SCAN_RESULT = 0x31
    SET_WIFI_SSID = 0x32
    RESET_WIFI = 0x33
    GET_WIFI_STATUS = 0x34
    GET_DEVICE_WIFI_ADDR = 0x35
    SET_WIFI_SSID_AND_PASSWORD = 0x36
    GET_WIFI_RECORDS = 0x37
    OPERATE_WIFI_RECORD = 0x38
    GET_WIFI_STATE_MACHINE = 0x39
    SET_WIFI_STATE_MACHINE = 0x3a
    
    # Power commands (0x40-0x5F)
    TOGGLE_PORT_POWER = 0x40
    GET_POWER_STATISTICS = 0x41
    GET_POWER_SUPPLY_STATUS = 0x42
    SET_CHARGING_STRATEGY = 0x43
    GET_CHARGING_STATUS = 0x44
    GET_POWER_HISTORICAL_STATS = 0x45
    SET_PORT_PRIORITY = 0x46
    GET_PORT_PRIORITY = 0x47
    GET_CHARGING_STRATEGY = 0x48
    GET_PORT_PD_STATUS = 0x49
    GET_ALL_POWER_STATISTICS = 0x4a
    GET_START_CHARGE_TIMESTAMP = 0x4b
    TURN_ON_PORT = 0x4c
    TURN_OFF_PORT = 0x4d
    SET_STATIC_ALLOCATOR = 0x55
    GET_STATIC_ALLOCATOR = 0x56
    SET_PORT_CONFIG = 0x57
    GET_PORT_CONFIG = 0x58
    SET_PORT_COMPATIBILITY_SETTINGS = 0x59
    GET_PORT_COMPATIBILITY_SETTINGS = 0x5a
    SET_TEMPERATURE_MODE = 0x5b
    SET_TEMPORARY_ALLOCATOR = 0x5c
    SET_PORT_CONFIG1 = 0x5d
    GET_PORT_CONFIG1 = 0x5e
    
    # Display commands (0x70-0x7F)
    SET_DISPLAY_INTENSITY = 0x70
    SET_DISPLAY_MODE = 0x71
    GET_DISPLAY_INTENSITY = 0x72
    GET_DISPLAY_MODE = 0x73
    SET_DISPLAY_FLIP = 0x74
    GET_DISPLAY_FLIP = 0x75
    SET_DISPLAY_CONFIG = 0x76
    SET_DISPLAY_STATE = 0x77
    GET_DISPLAY_STATE = 0x78
    
    # System commands (0x90-0x9F)
    START_TELEMETRY_STREAM = 0x90
    STOP_TELEMETRY_STREAM = 0x91
    GET_DEVICE_INFO = 0x92
    SET_BLE_STATE = 0x98
    SET_SYSLOG_STATE = 0x99
    SET_SYSTEM_TIME = 0x9a
    START_OTA = 0x9c
    
    # Feature management (0x0a-0x0c)
    MANAGE_POWER_CONFIG = 0x0a
    MANAGE_FEATURE_TOGGLE = 0x0b
    ENABLE_RELEASE_MODE = 0x0c


# Protocol bit definitions for PowerFeatures (3 bytes)
class ProtocolBits:
    """Protocol bit positions in PowerFeatures"""
    # Byte 0
    TFCP = (0, 0)
    PE = (0, 1)
    QC2_0 = (0, 2)
    QC3_0 = (0, 3)
    QC3_PLUS = (0, 4)
    AFC = (0, 5)
    FCP = (0, 6)
    HV_SCP = (0, 7)
    
    # Byte 1
    LV_SCP = (1, 0)
    SFCP = (1, 1)
    APPLE_5V = (1, 2)
    SAMSUNG_5V = (1, 3)
    BC1_2 = (1, 4)
    UFCS = (1, 5)
    RPI_5V5A = (1, 6)  # 树莓派 5V5A
    VOOC = (1, 7)      # OPPO VOOC
    
    # Byte 2
    PD = (2, 0)
    PPS = (2, 1)       # USB PD PPS
    QC4 = (2, 2)       # QC4.0
    QC4_PLUS = (2, 3)  # QC4+
    DASH = (2, 4)      # OnePlus Dash/Warp
    SFC = (2, 5)       # Super Fast Charging
    MTKPE = (2, 6)     # MTK Pump Express
    MTKPE_PLUS = (2, 7) # MTK PE+


# Protocol bit positions in PowerFeatures (for port config)
PROTOCOL_NAMES = {
    'TFCP': ProtocolBits.TFCP,
    'PE': ProtocolBits.PE,
    'QC2.0': ProtocolBits.QC2_0,
    'QC3.0': ProtocolBits.QC3_0,
    'QC3+': ProtocolBits.QC3_PLUS,
    'AFC': ProtocolBits.AFC,
    'FCP': ProtocolBits.FCP,
    'HV_SCP': ProtocolBits.HV_SCP,
    'LV_SCP': ProtocolBits.LV_SCP,
    'SFCP': ProtocolBits.SFCP,
    'Apple 5V': ProtocolBits.APPLE_5V,
    'Samsung 5V': ProtocolBits.SAMSUNG_5V,
    'BC1.2': ProtocolBits.BC1_2,
    'UFCS': ProtocolBits.UFCS,
    'RPi 5V5A': ProtocolBits.RPI_5V5A,
    'VOOC': ProtocolBits.VOOC,
    'PD': ProtocolBits.PD,
    'PPS': ProtocolBits.PPS,
    'QC4.0': ProtocolBits.QC4,
    'QC4+': ProtocolBits.QC4_PLUS,
    'Dash/Warp': ProtocolBits.DASH,
    'SFC': ProtocolBits.SFC,
    'MTK PE': ProtocolBits.MTKPE,
    'MTK PE+': ProtocolBits.MTKPE_PLUS,
}

# Fast charging protocol enum values (from data_types.h)
# These are the actual protocol values returned by the device
FAST_CHARGING_PROTOCOLS = {
    0: "无",
    1: "QC2.0",
    2: "QC3.0",
    3: "QC3+",
    4: "SFCP",
    5: "AFC",
    6: "FCP",
    7: "SCP",
    8: "VOOC1.0",
    9: "VOOC4.0",
    10: "SuperVOOC2.0",
    11: "TFCP",
    12: "UFCS",
    13: "PE1.0",
    14: "PE2.0",
    15: "PD 5V",
    16: "PD 高压",
    17: "PD SPR AVS",
    18: "PD PPS",
    19: "PD EPR 高压",
    20: "PD AVS",
    0xFF: "未充电"
}

def get_protocol_name(protocol_value: int) -> str:
    """Get protocol name from protocol value"""
    return FAST_CHARGING_PROTOCOLS.get(protocol_value, f"未知({protocol_value})")


# Charging strategy types (from strategy.cpp)
class StrategyType(IntEnum):
    """Charging strategy types"""
    SLOW_CHARGING = 0      # 慢充模式
    STATIC_CHARGING = 1     # 固定分配模式
    TEMPORARY_CHARGING = 2  # 临时分配模式
    USBA_CHARGING = 3        # USB-A模式


# PowerConfig structure (from power_config.h)
@dataclass
class PowerConfig:
    """Power allocation configuration"""
    version: int = 1
    max_power: int = 240  # Maximum power budget in watts
    cooldown_period: int = 5  # Cooldown period in seconds
    apply_period: int = 1  # Apply period in seconds
    temperature_mode: int = 0  # 0: Power priority, 1: Temperature priority


# CompatibilitySettings structure (from power_handler.cpp)
@dataclass
class CompatibilitySettings:
    """Port protocol compatibility settings"""
    isTfcpEnabled: bool = False   # whether to enable tfcp
    isFcpEnabled: bool = False    # whether to enable FCP
    isUfcsEnabled: bool = False   # whether to enable ufcs
    isHvScpEnabled: bool = False  # whether to enable high voltage scp
    isLvScpEnabled: bool = False  # whether to enable low voltage scp


# Predefined compatibility modes (from user requirements)
COMPATIBILITY_MODES = {
    "native": {
        "name": "原生模式",
        "description": "出厂默认的标准兼容状态，兼顾各种设备",
        "settings": CompatibilitySettings(
            isTfcpEnabled=True,
            isFcpEnabled=True,
            isUfcsEnabled=True,
            isHvScpEnabled=True,
            isLvScpEnabled=True
        )
    },
    "huawei": {
        "name": "华为模式",
        "description": "优先握手华为的私有快充协议（SCP/FCP），可能会屏蔽PD协议",
        "settings": CompatibilitySettings(
            isTfcpEnabled=False,
            isFcpEnabled=True,
            isUfcsEnabled=False,
            isHvScpEnabled=True,
            isLvScpEnabled=True
        )
    },
    "android": {
        "name": "安卓模式",
        "description": "默认开启并优化双档位PPS协议，适用于三星、Pixel等安卓旗舰机",
        "settings": CompatibilitySettings(
            isTfcpEnabled=True,
            isFcpEnabled=True,
            isUfcsEnabled=True,
            isHvScpEnabled=True,
            isLvScpEnabled=True
        )
    },
    "apple": {
        "name": "苹果全家桶模式",
        "description": "专为iPhone+iPad+MacBook组合优化",
        "settings": CompatibilitySettings(
            isTfcpEnabled=True,
            isFcpEnabled=True,
            isUfcsEnabled=True,
            isHvScpEnabled=True,
            isLvScpEnabled=True
        )
    },
    "sleep": {
        "name": "睡眠模式/养生模式",
        "description": "慢充保护，降低输出功率上限",
        "settings": CompatibilitySettings(
            isTfcpEnabled=True,
            isFcpEnabled=True,
            isUfcsEnabled=False,
            isHvScpEnabled=False,
            isLvScpEnabled=False
        )
    },
    "small_appliance": {
        "name": "小家电模式",
        "description": "屏蔽低电流自动关机功能",
        "settings": CompatibilitySettings(
            isTfcpEnabled=True,
            isFcpEnabled=True,
            isUfcsEnabled=True,
            isHvScpEnabled=True,
            isLvScpEnabled=True
        )
    }
}


def encode_compatibility_settings(settings: CompatibilitySettings) -> bytes:
    """Encode compatibility settings to 1 byte"""
    value = 0
    if settings.isTfcpEnabled:
        value |= (1 << 0)
    if settings.isFcpEnabled:
        value |= (1 << 1)
    if settings.isUfcsEnabled:
        value |= (1 << 2)
    if settings.isHvScpEnabled:
        value |= (1 << 3)
    if settings.isLvScpEnabled:
        value |= (1 << 4)
    return bytes([value])


def decode_compatibility_settings(data: bytes) -> CompatibilitySettings:
    """Decode 1 byte to compatibility settings"""
    if len(data) < 1:
        return CompatibilitySettings()
    
    value = data[0]
    return CompatibilitySettings(
        isTfcpEnabled=bool(value & (1 << 0)),
        isFcpEnabled=bool(value & (1 << 1)),
        isUfcsEnabled=bool(value & (1 << 2)),
        isHvScpEnabled=bool(value & (1 << 3)),
        isLvScpEnabled=bool(value & (1 << 4))
    )


def parse_power_config_response(payload: bytes) -> dict:
    """Parse power config response"""
    if len(payload) < 1 + len(PowerConfig().__dataclass_fields__):
        return {'error': 'Response too short'}
    
    version = payload[0]
    if version != 1:
        return {'error': f'Unsupported version: {version}'}
    
    # Parse PowerConfig structure (version 1)
    # Structure: version(1) + max_power(1) + cooldown_period(4) + apply_period(4) + temperature_mode(1)
    if len(payload) < 11:
        return {'error': 'Response too short for PowerConfig v1'}
    
    max_power = payload[1]
    cooldown_period = int.from_bytes(payload[2:6], 'little')
    apply_period = int.from_bytes(payload[6:10], 'little')
    temperature_mode = payload[10]
    
    return {
        'version': version,
        'max_power': max_power,
        'cooldown_period': cooldown_period,
        'apply_period': apply_period,
        'temperature_mode': temperature_mode,
        'temperature_mode_name': 'Power Priority' if temperature_mode == 0 else 'Temperature Priority'
    }


def parse_charging_strategy_extended_response(payload: bytes) -> dict:
    """Parse charging strategy response with strategy type"""
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    strategy = payload[0]
    strategy_names = {
        0: "慢充模式",
        1: "固定分配模式",
        2: "临时分配模式",
        3: "USB-A模式"
    }
    strategy_name = strategy_names.get(strategy, f"未知策略({strategy})")
    
    return {
        'strategy': strategy,
        'strategy_name': strategy_name
    }


# Command categories for easy reference
COMMAND_CATEGORIES = {
    "Test Commands": [
        ServiceCommand.BLE_ECHO_TEST,
        ServiceCommand.GET_DEBUG_LOG,
        ServiceCommand.GET_SECURE_BOOT_DIGEST,
        ServiceCommand.PING_MQTT_TELEMETRY,
        ServiceCommand.PING_HTTP,
        ServiceCommand.GET_DEVICE_PASSWORD,
        ServiceCommand.MANAGE_POWER_ALLOCATOR_ENABLED,
    ],
    "Device Management": [
        ServiceCommand.ASSOCIATE_DEVICE,
        ServiceCommand.REBOOT_DEVICE,
        ServiceCommand.RESET_DEVICE,
        ServiceCommand.GET_DEVICE_SERIAL_NO,
        ServiceCommand.GET_DEVICE_UPTIME,
        ServiceCommand.GET_AP_VERSION,
        ServiceCommand.GET_DEVICE_BLE_ADDR,
        ServiceCommand.SWITCH_DEVICE,
        ServiceCommand.GET_DEVICE_SWITCH,
        ServiceCommand.GET_DEVICE_MODEL,
        ServiceCommand.PUSH_LICENSE,
        ServiceCommand.GET_BLE_RSSI,
        ServiceCommand.GET_BLE_MTU,
    ],
    "OTA Commands": [
        ServiceCommand.PERFORM_BLE_OTA,
        ServiceCommand.PERFORM_WIFI_OTA,
        ServiceCommand.GET_WIFI_OTA_PROGRESS,
        ServiceCommand.CONFIRM_OTA,
        ServiceCommand.START_OTA,
    ],
    "WiFi Management": [
        ServiceCommand.SCAN_WIFI,
        ServiceCommand.GET_WIFI_SCAN_RESULT,
        ServiceCommand.SET_WIFI_SSID,
        ServiceCommand.RESET_WIFI,
        ServiceCommand.GET_WIFI_STATUS,
        ServiceCommand.GET_DEVICE_WIFI_ADDR,
        ServiceCommand.SET_WIFI_SSID_AND_PASSWORD,
        ServiceCommand.GET_WIFI_RECORDS,
        ServiceCommand.OPERATE_WIFI_RECORD,
        ServiceCommand.GET_WIFI_STATE_MACHINE,
        ServiceCommand.SET_WIFI_STATE_MACHINE,
    ],
    "Power Management": [
        ServiceCommand.TOGGLE_PORT_POWER,
        ServiceCommand.GET_POWER_STATISTICS,
        ServiceCommand.GET_POWER_SUPPLY_STATUS,
        ServiceCommand.SET_CHARGING_STRATEGY,
        ServiceCommand.GET_CHARGING_STATUS,
        ServiceCommand.GET_POWER_HISTORICAL_STATS,
        ServiceCommand.SET_PORT_PRIORITY,
        ServiceCommand.GET_PORT_PRIORITY,
        ServiceCommand.GET_CHARGING_STRATEGY,
        ServiceCommand.GET_PORT_PD_STATUS,
        ServiceCommand.GET_ALL_POWER_STATISTICS,
        ServiceCommand.GET_START_CHARGE_TIMESTAMP,
        ServiceCommand.TURN_ON_PORT,
        ServiceCommand.TURN_OFF_PORT,
        ServiceCommand.SET_STATIC_ALLOCATOR,
        ServiceCommand.GET_STATIC_ALLOCATOR,
        ServiceCommand.SET_PORT_CONFIG,
        ServiceCommand.GET_PORT_CONFIG,
        ServiceCommand.SET_PORT_COMPATIBILITY_SETTINGS,
        ServiceCommand.GET_PORT_COMPATIBILITY_SETTINGS,
        ServiceCommand.SET_TEMPERATURE_MODE,
        ServiceCommand.SET_TEMPORARY_ALLOCATOR,
        ServiceCommand.SET_PORT_CONFIG1,
        ServiceCommand.GET_PORT_CONFIG1,
    ],
    "Display Management": [
        ServiceCommand.SET_DISPLAY_INTENSITY,
        ServiceCommand.SET_DISPLAY_MODE,
        ServiceCommand.GET_DISPLAY_INTENSITY,
        ServiceCommand.GET_DISPLAY_MODE,
        ServiceCommand.SET_DISPLAY_FLIP,
        ServiceCommand.GET_DISPLAY_FLIP,
        ServiceCommand.SET_DISPLAY_CONFIG,
        ServiceCommand.SET_DISPLAY_STATE,
        ServiceCommand.GET_DISPLAY_STATE,
    ],
    "System Commands": [
        ServiceCommand.START_TELEMETRY_STREAM,
        ServiceCommand.STOP_TELEMETRY_STREAM,
        ServiceCommand.GET_DEVICE_INFO,
        ServiceCommand.SET_BLE_STATE,
        ServiceCommand.SET_SYSLOG_STATE,
        ServiceCommand.SET_SYSTEM_TIME,
    ],
    "Feature Management": [
        ServiceCommand.MANAGE_POWER_CONFIG,
        ServiceCommand.MANAGE_FEATURE_TOGGLE,
        ServiceCommand.ENABLE_RELEASE_MODE,
    ],
}


@dataclass
class BLEResponse:
    """Parsed BLE response"""
    version: int
    msg_id: int
    service: int
    sequence: int
    flags: int
    size: int
    checksum: int
    payload: bytes
    raw: bytes
    success: bool = True
    error: Optional[str] = None


@dataclass
class PortInfo:
    """Port information"""
    port_id: int
    status: int
    protocol: int
    voltage: float  # V
    current: float  # A
    power: float    # W
    charging: bool
    enabled: bool


@dataclass
class DeviceInfo:
    """Device information"""
    model: str
    firmware: str
    serial: str
    uptime: int
    ble_addr: str
    wifi_addr: str


def calc_checksum(header_bytes: bytes) -> int:
    """Calculate checksum: sum of all header bytes (excluding checksum itself)"""
    return sum(header_bytes[:-1]) & 0xFF


def build_message(version: int, msg_id: int, service: int, sequence: int,
                  flags: int, payload: bytes) -> bytes:
    """Build a complete BLE message with header and payload."""
    payload_size = len(payload)
    
    # Size is 3 bytes, big-endian for version 0
    size_bytes = struct.pack('>I', payload_size)[1:]
    
    header = bytes([
        version,
        msg_id,
        service & 0xFF,
        sequence,
        flags,
        size_bytes[0],
        size_bytes[1],
        size_bytes[2],
        0  # Placeholder for checksum
    ])
    
    checksum = calc_checksum(header)
    header = header[:-1] + bytes([checksum])
    
    return header + payload


def parse_response(data: bytes) -> BLEResponse:
    """Parse a BLE response message"""
    if len(data) < 9:
        return BLEResponse(
            version=0, msg_id=0, service=0, sequence=0, flags=0,
            size=0, checksum=0, payload=b'', raw=data,
            success=False, error="Response too short"
        )
    
    version = data[0]
    msg_id = data[1]
    service = struct.unpack('b', bytes([data[2]]))[0]  # Signed byte
    sequence = data[3]
    flags = data[4]
    
    # Parse size (3 bytes, big-endian for version 0)
    if version == 0:
        size = (data[5] << 16) | (data[6] << 8) | data[7]
    else:
        size = data[5] | (data[6] << 8) | (data[7] << 16)
    
    checksum = data[8]
    payload = data[9:9+size] if len(data) > 9 else b''
    
    return BLEResponse(
        version=version,
        msg_id=msg_id,
        service=service,
        sequence=sequence,
        flags=flags,
        size=size,
        checksum=checksum,
        payload=payload,
        raw=data
    )


def encode_protocols(protocols: dict) -> bytes:
    """Encode protocol settings to 3-byte PowerFeatures"""
    features = [0, 0, 0]
    
    for name, enabled in protocols.items():
        if enabled and name in PROTOCOL_NAMES:
            byte_idx, bit_idx = PROTOCOL_NAMES[name]
            features[byte_idx] |= (1 << bit_idx)
    
    return bytes(features)


def decode_protocols(data: bytes) -> dict:
    """Decode 3-byte PowerFeatures to protocol settings"""
    if len(data) < 3:
        data = data + b'\x00' * (3 - len(data))
    
    protocols = {}
    for name, (byte_idx, bit_idx) in PROTOCOL_NAMES.items():
        protocols[name] = bool(data[byte_idx] & (1 << bit_idx))
    
    return protocols


def parse_port_statistics(data: bytes) -> List[PortInfo]:
    """Parse port statistics from GET_ALL_POWER_STATISTICS response
    
    Response format per port (8 bytes):
    - fc_protocol (1 byte): Fast charging protocol
    - amperage (1 byte): Current, actual = value / 32 A
    - voltage (1 byte): Voltage, actual = value / 8 V
    - temperature (1 byte): Temperature in degrees
    - battery_last_full_charge_capacity (2 bytes, little-endian)
    - battery_present_capacity (2 bytes, little-endian)
    """
    ports = []
    chunk_size = 8  # Each port is 8 bytes
    
    # Skip first byte if it looks like a status/version byte
    # Response format: [status_byte] [port0_data...] [port1_data...] ...
    if len(data) > 0 and data[0] == 0x00:
        data = data[1:]
    
    for i in range(len(data) // chunk_size):
        chunk = data[i * chunk_size : (i + 1) * chunk_size]
        if len(chunk) < 8:
            continue
        
        try:
            # Parse according to actual firmware format
            fc_protocol = chunk[0]
            amperage_scaled = chunk[1]
            voltage_scaled = chunk[2]
            temperature = chunk[3]
            battery_last_full = struct.unpack('<H', chunk[4:6])[0]
            battery_present = struct.unpack('<H', chunk[6:8])[0]
            
            # Convert scaled values to actual values
            # voltage: actual = value / 8 V (from ScaleVoltage: voltage * 8 / 1000)
            # amperage: actual = value / 32 A (from ScaleAmperage: amperage * 32 / 1000)
            voltage = voltage_scaled / 8.0  # V
            current = amperage_scaled / 32.0  # A
            power = voltage * current  # W
            
            # Port is enabled if it has valid data (protocol != 0xFF or has voltage/current)
            # 0xFF is the default/invalid value
            is_on = fc_protocol != 0xFF or voltage > 0 or current > 0
            
            ports.append(PortInfo(
                port_id=i,
                status=fc_protocol,
                protocol=fc_protocol,
                voltage=round(voltage, 2),
                current=round(current, 3),
                power=round(power, 2),
                charging=current > 0.01,
                enabled=is_on
            ))
        except Exception as e:
            continue
    
    return ports


def get_command_name(service: int) -> str:
    """Get the name of a service command"""
    for name, value in ServiceCommand.__members__.items():
        if value == service:
            return name
    return f"UNKNOWN(0x{service:02X})"


def get_command_category(service: int) -> Optional[str]:
    """Get the category of a service command"""
    for category, commands in COMMAND_CATEGORIES.items():
        if service in commands:
            return category
    return None


def needs_token(service: int) -> bool:
    """Check if a service command requires token"""
    return service != ServiceCommand.ASSOCIATE_DEVICE


# ============ 完整响应解析函数 ============

def parse_wifi_status_response(payload: bytes) -> dict:
    """解析WiFi状态响应"""
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    status = payload[0]
    status_names = {
        0: "未配置",
        1: "失败",
        2: "连接中",
        3: "已连接",
        4: "断开连接中"
    }
    status_name = status_names.get(status, f"未知状态({status})")
    
    result = {
        'status': status,
        'status_name': status_name
    }
    
    # 如果已连接，解析IP地址
    if status == 3 and len(payload) >= 5:
        ip = '.'.join(str(b) for b in payload[1:5])
        result['ip'] = ip
    
    return result


def parse_charging_strategy_response(payload: bytes) -> dict:
    """解析充电策略响应"""
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    strategy = payload[0]
    strategy_names = {
        0: "自动分配",
        1: "固定分配",
        2: "优先级分配"
    }
    strategy_name = strategy_names.get(strategy, f"未知策略({strategy})")
    
    return {
        'strategy': strategy,
        'strategy_name': strategy_name
    }


def parse_display_settings_response(payload: bytes) -> dict:
    """解析显示设置响应"""
    if len(payload) < 2:
        return {'error': 'Response too short'}
    
    brightness = payload[0]
    mode = payload[1]
    mode_names = {
        0: "默认",
        1: "简洁",
        2: "详细"
    }
    mode_name = mode_names.get(mode, f"未知模式({mode})")
    
    return {
        'brightness': brightness,
        'mode': mode,
        'mode_name': mode_name
    }


def parse_port_config_response(payload: bytes) -> dict:
    """解析端口配置响应"""
    if len(payload) < 4:
        return {'error': 'Response too short'}
    
    port_id = payload[0]
    power_features = payload[1:4]
    
    # 解析支持的协议
    protocol_names = [
        'TFCP', 'PE', 'QC2.0', 'QC3.0', 'QC3+', 'AFC', 'FCP', 'HV_SCP',
        'LV_SCP', 'SFCP', 'Apple 5V', 'Samsung 5V', 'BC1.2', 'UFCS', 'RPi 5V5A', 'VOOC',
        'PD', 'PPS', 'QC4.0', 'QC4+', 'Dash/Warp', 'SFC', 'MTK PE', 'MTK PE+'
    ]
    
    protocols = []
    for i, protocol_name in enumerate(protocol_names):
        byte_index = i // 8
        bit_index = i % 8
        if byte_index < len(power_features):
            if power_features[byte_index] & (1 << bit_index):
                protocols.append(protocol_name)
    
    return {
        'port_id': port_id,
        'power_features': power_features.hex(),
        'protocols': protocols
    }


def parse_power_statistics_response(payload: bytes) -> dict:
    """解析功率统计响应
    
    响应格式（根据power_handler.cpp的GetPowerStats）:
    - port_id (1 byte)
    - fc_protocol (1 byte): 快充协议
    - amperage_scaled (1 byte): 电流，实际值 = value / 32 A
    - voltage_scaled (1 byte): 电压，实际值 = value / 8 V
    - temperature (1 byte): 温度（摄氏度）
    - battery_last_full_charge_capacity (2 bytes, little-endian)
    - battery_present_capacity (2 bytes, little-endian)
    """
    if len(payload) < 5:
        return {'error': 'Response too short'}
    
    port_id = payload[0]
    
    # 根据实际响应长度解析
    if len(payload) >= 8:
        fc_protocol = payload[1]
        amperage_scaled = payload[2]
        voltage_scaled = payload[3]
        temperature = payload[4]
        
        # 转换为实际值
        voltage = voltage_scaled / 8.0  # V
        current = amperage_scaled / 32.0  # A
        power = voltage * current  # W
        
        # 如果有电池容量数据，也解析出来
        battery_last_full = 0
        battery_present = 0
        if len(payload) >= 8:
            battery_last_full = int.from_bytes(payload[5:7], 'little')
            battery_present = int.from_bytes(payload[7:9], 'little')
        
        return {
            'port_id': port_id,
            'fc_protocol': fc_protocol,
            'voltage': round(voltage, 2),
            'current': round(current, 3),
            'power': round(power, 2),
            'temperature': temperature,
            'battery_last_full': battery_last_full,
            'battery_present': battery_present
        }
    elif len(payload) >= 5:
        # 简化版本，只有基本的电压电流数据
        voltage = (payload[1] << 8) | payload[2]
        current = (payload[3] << 8) | payload[4]
        power = voltage * current / 1000.0  # W
        
        return {
            'port_id': port_id,
            'fc_protocol': 0,
            'voltage': voltage / 1000.0,  # mV to V
            'current': current / 1000.0,  # mA to A
            'power': round(power, 2),
            'temperature': 0,
            'battery_last_full': 0,
            'battery_present': 0
        }
    else:
        return {'error': 'Response too short'}


def parse_charging_status_response(payload: bytes) -> dict:
    """解析充电状态响应"""
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    num_ports = payload[0]
    ports = []
    
    for i in range(num_ports):
        offset = 1 + i * 4
        if offset + 4 <= len(payload):
            port_id = payload[offset]
            voltage = (payload[offset + 1] << 8) | payload[offset + 2]
            current = payload[offset + 3]
            ports.append({
                'port_id': port_id,
                'voltage': voltage / 1000.0,  # mV to V
                'current': current / 1000.0  # mA to A
            })
    
    return {
        'num_ports': num_ports,
        'ports': ports
    }


def parse_power_supply_status_response(payload: bytes) -> dict:
    """解析供电状态响应"""
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    port_mask = payload[0]
    
    # 解析哪些端口是打开的
    open_ports = []
    for i in range(8):
        if port_mask & (1 << i):
            open_ports.append(i)
    
    return {
        'port_mask': port_mask,
        'open_ports': open_ports
    }


def parse_device_info_response(payload: bytes) -> dict:
    """解析设备信息响应"""
    if len(payload) >= 4:
        firmware = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
    else:
        firmware = ''
    
    if len(payload) >= 8:
        serial = payload[4:8].decode('utf-8', errors='ignore').strip('\x00')
    else:
        serial = ''
    
    result = {'firmware': firmware}
    if serial:
        result['serial'] = serial
    
    return result


def parse_device_model_response(payload: bytes) -> dict:
    """解析设备型号响应"""
    if len(payload) >= 4:
        model = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
    else:
        model = ''
    
    return {'model': model}


def parse_device_serial_response(payload: bytes) -> dict:
    """解析设备序列号响应"""
    if len(payload) >= 4:
        serial = payload[0:4].decode('utf-8', errors='ignore').strip('\x00')
    else:
        serial = ''
    
    return {'serial': serial}


def parse_device_uptime_response(payload: bytes) -> dict:
    """解析设备运行时间响应"""
    if len(payload) < 4:
        return {'error': 'Response too short'}
    
    uptime = (payload[0] << 24) | (payload[1] << 16) | (payload[2] << 8) | payload[3]
    
    return {'uptime': uptime}


def parse_power_historical_stats_response(payload: bytes) -> dict:
    """解析历史功率统计响应
    
    响应格式（根据power_handler.cpp的GetPowerHistoricalStats）:
    请求: [port_id, offset_low, offset_high] (可选offset)
    响应: PortStatsData数组（每个4字节：voltage, amperage, temperature, vin_value）
    
    PortStatsData结构:
    - voltage (1 byte): 电压，实际值 = value / 8 V
    - amperage (1 byte): 电流，实际值 = value / 32 A
    - temperature (1 byte): 温度（摄氏度）
    - vin_value (1 byte): 输入电压，实际值 = value / 8 V
    """
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    port_id = payload[0]
    stats_data = payload[1:]
    
    # 每个历史数据点4字节
    stats = []
    chunk_size = 4
    
    for i in range(len(stats_data) // chunk_size):
        chunk = stats_data[i * chunk_size : (i + 1) * chunk_size]
        if len(chunk) < 4:
            continue
        
        voltage_scaled = chunk[0]
        amperage_scaled = chunk[1]
        temperature = chunk[2]
        vin_scaled = chunk[3]
        
        # 转换为实际值
        voltage = voltage_scaled / 8.0  # V
        current = amperage_scaled / 32.0  # A
        power = voltage * current  # W
        vin = vin_scaled / 8.0  # V
        
        stats.append({
            'index': i,
            'voltage': round(voltage, 2),
            'current': round(current, 3),
            'power': round(power, 2),
            'temperature': temperature,
            'vin': round(vin, 2)
        })
    
    return {
        'port_id': port_id,
        'stats': stats,
        'count': len(stats)
    }


def parse_port_pd_status_response(payload: bytes) -> dict:
    """解析端口PD状态响应 - 支持可变长度响应"""
    result = {'raw': payload.hex()}
    n = len(payload)

    if n < 2:
        result['error'] = 'Response too short'
        return result

    # 安全读取函数
    def get_byte(offset, default=0):
        return payload[offset] if offset < n else default

    def get_word(offset, default=0):
        return int.from_bytes(payload[offset:offset+2], 'little') if offset + 1 < n else default

    # 电池信息
    result['battery'] = {
        'vid': f"0x{get_word(0):04X}",
        'pid': f"0x{get_word(2):04X}",
        'design_capacity': get_word(4) / 10.0,
        'last_full_capacity': get_word(6) / 10.0,
        'present_capacity': get_word(8) / 10.0,
        'present': bool(get_byte(10) & 0x02),
        'status_name': {0: "充电中", 1: "放电中", 2: "空闲"}.get((get_byte(10) >> 2) & 0x03, "未知")
    }

    # 线缆信息
    cable_flags = get_byte(10)
    cable_voltage_flags = get_byte(11)
    cable_speed_flags = get_byte(12)
    result['cable'] = {
        'is_active': bool(cable_flags & 0x04),
        'epr_mode_capable': bool(cable_flags & 0x10),
        'phy_type': "光缆" if (cable_flags >> 5) & 0x01 else "铜缆",
        'length': {0: "<1m", 1: "~1m", 2: "~2m", 3: "~3m"}.get((cable_flags >> 6) & 0x0F, ">3m"),
        'max_voltage': {0: "20V", 1: "30V", 2: "40V", 3: "50V"}.get(cable_voltage_flags & 0x03, "未知"),
        'max_current': {0: "未知", 1: "3A", 2: "5A"}.get((cable_voltage_flags >> 2) & 0x03, "未知"),
        'usb_speed': {0: "USB 2.0", 1: "USB 3.2 Gen1", 2: "USB 3.2 Gen2", 3: "USB4 Gen3"}.get(cable_speed_flags & 0x07, "未知"),
        'vid': f"0x{get_word(14):04X}",
        'pid': f"0x{get_word(16):04X}"
    }

    # 操作信息
    op_current_low = get_byte(34)
    op_current_high = get_byte(35)
    op_current = ((op_current_high & 0x03) << 8) | op_current_low
    op_current_amps = op_current / 100.0
    op_voltage = ((get_byte(38) << 8) | get_byte(37)) & 0x7FFF
    op_voltage_volts = op_voltage / 100.0
    op_flags = get_byte(36)

    result['operating'] = {
        'current': round(op_current_amps, 2),
        'voltage': round(op_voltage_volts, 2),
        'power': round(op_current_amps * op_voltage_volts, 2),
        'pd_revision': {0: "1.0", 1: "2.0", 3: "3.0"}.get((op_current_high >> 2) & 0x03, "未知"),
        'pps_charging_supported': bool(op_flags & 0x01),
        'has_battery': bool(op_flags & 0x02),
        'has_emarker': bool(op_flags & 0x08)
    }

    # 状态温度
    result['status'] = {'temperature': get_byte(33)}

    return result


def parse_port_priority_response(payload: bytes) -> dict:
    """解析端口优先级响应
    
    响应格式（根据power_handler.cpp的GetPortPriority）:
    - [priority0, priority1, ...] (每个端口一个字节)
    """
    priorities = list(payload)
    
    return {
        'priorities': priorities,
        'count': len(priorities)
    }


def parse_start_charge_timestamp_response(payload: bytes) -> dict:
    """解析开始充电时间戳响应
    
    响应格式（根据power_handler.cpp的GetStartChargeTimestamp）:
    - timestamp (4 bytes, little-endian): Unix时间戳
    """
    if len(payload) < 4:
        return {'error': 'Response too short'}
    
    timestamp = int.from_bytes(payload[0:4], 'little')
    
    return {
        'timestamp': timestamp
    }


def parse_temperature_mode_response(payload: bytes) -> dict:
    """解析温度模式响应
    
    响应格式（根据power_allocator.h的TemperatureMode）:
    - mode (1 byte): 0=POWER_PRIORITY, 1=TEMPERATURE_PRIORITY
    """
    if len(payload) < 1:
        return {'error': 'Response too short'}
    
    mode = payload[0]
    mode_names = {
        0: "功率优先",
        1: "温度优先"
    }
    mode_name = mode_names.get(mode, f"未知模式({mode})")
    
    return {
        'mode': mode,
        'mode_name': mode_name
    }
