"""
IonBridge BLE Manager - Enhanced Version
Handles BLE device scanning, connection, and command execution
Features: Auto token refresh, auto reconnect, background tasks, token persistence
"""

import asyncio
import time
import json
import os
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from protocol import (
    SERVICE_UUID, CHAR_TX_UUID, CHAR_RX_UUID, DEVICE_PREFIX,
    BLEFlags, ServiceCommand, build_message, parse_response, BLEResponse,
    parse_port_statistics, PortInfo, needs_token
)

# Token storage file
TOKEN_STORAGE_FILE = "token_storage.json"


@dataclass
class DeviceInfo:
    """Discovered device info"""
    name: str
    address: str
    rssi: int = 0


class TokenManager:
    """Manages BLE token acquisition and refresh with auto-refresh"""
    
    def __init__(self, refresh_interval: int = 300, storage_file: str = "token_storage.json"):
        self.token: Optional[int] = None
        self.last_refresh: Optional[float] = None
        self.refresh_interval = refresh_interval  # Default: 5 minutes
        self._acquiring = False  # Prevent duplicate acquisition
        self.auto_refresh = True  # Auto-refresh enabled by default
        self.refresh_task: Optional[asyncio.Task] = None
        self.ble_manager = None  # Reference to BLEManager
        self.storage_file = storage_file  # Token storage file path
    
    def set_ble_manager(self, ble_manager):
        """Set reference to BLEManager for auto-refresh"""
        self.ble_manager = ble_manager
    
    def should_refresh(self) -> bool:
        """Check if token should be refreshed"""
        if self._acquiring:
            return False  # Already acquiring, don't refresh
        if self.token is None:
            return True
        if self.last_refresh is None:
            return True
        return (time.time() - self.last_refresh) > self.refresh_interval
    
    def set_token(self, token: int, save_to_storage: bool = False):
        """Set current token"""
        self.token = token
        self.last_refresh = time.time()
        self._acquiring = False
    
    def invalidate(self):
        """Invalidate current token"""
        self.token = None
        self.last_refresh = None
        self._acquiring = False
    
    def get_stored_tokens(self) -> dict:
        """Get all stored tokens from storage"""
        return self._load_tokens_from_storage()
    
    def start_acquiring(self):
        """Mark that we're acquiring token"""
        self._acquiring = True
    
    def stop_acquiring(self):
        """Mark that we're done acquiring"""
        self._acquiring = False
    
    async def start_auto_refresh_task(self):
        """Start auto-refresh background task"""
        if self.refresh_task and not self.refresh_task.done():
            return  # Already running
        
        self.refresh_task = asyncio.create_task(self._auto_refresh_loop())
    
    async def _auto_refresh_loop(self):
        """Background task for auto-refreshing token"""
        while self.auto_refresh:
            try:
                await asyncio.sleep(self.refresh_interval)
                if self.should_refresh() and self.ble_manager and self.ble_manager.connected:
                    self.ble_manager.log("自动刷新 Token...")
                    token = await self.ble_manager.bruteforce_token(save_to_storage=True)
                    if token:
                        self.ble_manager.log(f"Token 已刷新: 0x{token:02X}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.ble_manager.log(f"Token 自动刷新失败: {e}")
    
    async def stop_auto_refresh_task(self):
        """Stop auto-refresh background task"""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass


class BLEManager:
    """Manages BLE connection and communication with auto-reconnect"""
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.client: Optional[BleakClient] = None
        self.device: Optional[BLEDevice] = None
        self.msg_id = 0
        self.response_event = asyncio.Event()
        self.last_response: Optional[BLEResponse] = None
        self.token_manager = TokenManager(storage_file=TOKEN_STORAGE_FILE)
        self.token_manager.set_ble_manager(self)
        self.log_callback = log_callback or print
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._auto_reconnect_enabled = True
    
    def log(self, message: str):
        """Log a message"""
        self.log_callback(message)
    
    @property
    def connected(self) -> bool:
        """Check if connected to a device"""
        return self._connected and self.client is not None and self.client.is_connected
    
    @property
    def token(self) -> Optional[int]:
        """Get current token"""
        return self.token_manager.token
    
    async def scan_devices(self, timeout: float = 5.0) -> List[DeviceInfo]:
        """Scan for IonBridge devices"""
        self.log(f"扫描设备中... (超时: {timeout}秒)")
        
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        
        result = []
        for address, (device, adv_data) in devices.items():
            if device.name and device.name.startswith(DEVICE_PREFIX):
                info = DeviceInfo(
                    name=device.name,
                    address=device.address,
                    rssi=adv_data.rssi if adv_data else 0
                )
                result.append(info)
                self.log(f"发现设备: {device.name} ({device.address}) RSSI: {info.rssi}")
        
        if not result:
            self.log("未发现 CP02- 设备")
        
        return result
    
    def _notification_handler(self, sender, data: bytes):
        """Handle notifications from device"""
        self.log(f"收到响应: {data.hex()}")
        self.last_response = parse_response(data)
        self.response_event.set()
    
    async def connect(self, address: str) -> bool:
        """Connect to a device"""
        try:
            self.log(f"连接到 {address}...")
            
            # Find device first
            devices = await BleakScanner.discover(timeout=5.0)
            target = None
            for d in devices:
                if d.address == address:
                    target = d
                    break
            
            if not target:
                self.log(f"未找到设备 {address}")
                return False
            
            self.device = target
            self.client = BleakClient(address)
            await self.client.connect()
            
            # Subscribe to notifications
            await self.client.start_notify(CHAR_TX_UUID, self._notification_handler)
            
            self._connected = True
            self._reconnect_attempts = 0
            self.log(f"已连接到 {target.name}")
            
            # Start auto-refresh task
            await self.token_manager.start_auto_refresh_task()
            
            return True
            
        except Exception as e:
            self.log(f"连接失败: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from device"""
        try:
            # Stop auto-refresh task
            await self.token_manager.stop_auto_refresh_task()
            
            # Disconnect if connected
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            
            # Reset state
            self._connected = False
            self.token_manager.invalidate()
            self.log("已断开连接")
            return True
        except Exception as e:
            self.log(f"断开连接失败: {e}")
            return False
    
    async def send_command(self, service: int, payload: bytes = b'',
                           timeout: float = 5.0) -> Optional[BLEResponse]:
        """Send a command and wait for response"""
        if not self.connected:
            self.log("未连接设备")
            return None
        
        self.msg_id = (self.msg_id + 1) & 0xFF
        
        # Build message with correct flags
        # For simple commands, use ACK (0x02) to trigger immediate execution
        # For fragmented data, would need FRAG_FIRST (0x06), FRAG_MORE (0x07), FRAG_LAST (0x08)
        message = build_message(
            version=0,
            msg_id=self.msg_id,
            service=service,
            sequence=0,
            flags=BLEFlags.ACK,  # Use ACK flag (0x02) instead of SYN (0x01)
            payload=payload
        )
        
        self.log(f"发送命令: 0x{service:02X}, payload: {payload.hex() if payload else 'empty'}")
        
        self.response_event.clear()
        self.last_response = None
        
        try:
            await self.client.write_gatt_char(CHAR_RX_UUID, message, response=False)
            
            await asyncio.wait_for(self.response_event.wait(), timeout=timeout)
            return self.last_response
            
        except asyncio.TimeoutError:
            self.log("命令超时")
            return None
        except Exception as e:
            self.log(f"发送命令失败: {e}")
            return None
    
    async def bruteforce_token(self, test_service: int = ServiceCommand.GET_DEVICE_MODEL, save_to_storage: bool = True) -> Optional[int]:
        """Bruteforce token (0x00-0xFF) and optionally save to storage"""
        if self.token_manager._acquiring:
            self.log("Token 获取中，请稍候...")
            return self.token_manager.token
        
        self.token_manager.start_acquiring()
        
        self.log("开始暴力破解 Token...")
        
        try:
            for token in range(256):
                if token % 32 == 0:
                    self.log(f"测试 Token: 0x{token:02X} - 0x{min(token+31, 255):02X}")
                
                payload = bytes([token])
                response = await self.send_command(test_service, payload, timeout=0.3)
                
                if response and response.service < 0 and response.size > 0:
                    self.log(f"找到 Token: 0x{token:02X} ({token})")
                    self.token_manager.set_token(token)
                    if save_to_storage:
                        self._save_token_to_storage(token)
                    return token
                
                await asyncio.sleep(0.02)
            
            self.log("Token 暴力破解失败")
            return None
        finally:
            self.token_manager.stop_acquiring()
    
    async def manual_set_token(self, token: int, save_to_storage: bool = True):
        """Manually set token and optionally save to storage"""
        self.log(f"手动设置Token: 0x{token:02X}")
        self.token_manager.set_token(token)
        if save_to_storage:
            self._save_token_to_storage(token)
        return token
    
    async def ensure_token(self) -> Optional[int]:
        """Ensure we have a valid token - try storage first, then acquire when needed"""
        # If we have a valid token and it's not time to refresh, return it
        if self.token_manager.token is not None and not self.token_manager.should_refresh():
            return self.token_manager.token
        
        # Try to load token from storage first
        if self.device:
            stored_token = self.load_token_from_storage(self.device.address)
            if stored_token is not None:
                self.log(f"从存储加载Token: 0x{stored_token:02X}")
                self.token_manager.set_token(stored_token)
                return stored_token
        
        # Need to get a new token via bruteforce
        if self.token_manager.should_refresh():
            await self.bruteforce_token(save_to_storage=True)
        
        return self.token_manager.token
    
    async def execute(self, service: int, extra_payload: bytes = b'',
                      needs_token: bool = True, auto_reconnect: bool = True,
                      timeout: float = 5.0) -> Optional[BLEResponse]:
        """Execute a command with automatic token handling and auto-reconnect"""
        if needs_token:
            token = await self.ensure_token()
            if token is None:
                self.log("无法获取 Token")
                return None
            payload = bytes([token]) + extra_payload
        else:
            payload = extra_payload

        response = await self.send_command(service, payload, timeout=timeout)

        # If command failed and auto-reconnect is enabled, try to reconnect
        if auto_reconnect and response is None and not self.token_manager._acquiring:
            self.log("命令失败，尝试重新连接...")
            if await self.auto_reconnect():
                # Retry command after reconnecting
                if needs_token:
                    token = await self.ensure_token()
                    if token is None:
                        return None
                    payload = bytes([token]) + extra_payload
                response = await self.send_command(service, payload, timeout=timeout)
        
        return response
    
    async def auto_reconnect(self) -> bool:
        """Automatically reconnect to device"""
        if not self._auto_reconnect_enabled:
            return False
        
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self.log(f"重连失败次数过多 ({self._reconnect_attempts})，停止重连")
            return False
        
        self._reconnect_attempts += 1
        self.log(f"尝试自动重连 ({self._reconnect_attempts}/{self._max_reconnect_attempts})...")
        
        # Disconnect first
        await self.disconnect()
        await asyncio.sleep(1)
        
        # Try to reconnect to same device
        if self.device:
            success = await self.connect(self.device.address)
            if success:
                # Try to load token from storage first, then bruteforce
                stored_token = self.load_token_from_storage(self.device.address)
                if stored_token is not None:
                    self.token_manager.set_token(stored_token)
                    self._reconnect_attempts = 0  # Reset counter on success
                    self.log("自动重连成功 (使用存储的Token)")
                    return True
                else:
                    # Get new token after reconnecting
                    token = await self.bruteforce_token(save_to_storage=True)
                    if token:
                        self._reconnect_attempts = 0  # Reset counter on success
                        self.log("自动重连成功 (暴力破解Token)")
                        return True
        
        return False
    
    async def get_port_status(self) -> List[PortInfo]:
        """Get all port status"""
        response = await self.execute(ServiceCommand.GET_ALL_POWER_STATISTICS)
        if response and response.payload:
            return parse_port_statistics(response.payload)
        return []
    
    async def get_power_supply_status(self) -> Optional[bytes]:
        """Get power supply status for all ports"""
        response = await self.execute(ServiceCommand.GET_POWER_SUPPLY_STATUS)
        if response and response.payload:
            return response.payload
        return None
    
    async def get_device_model(self) -> Optional[str]:
        """Get device model"""
        response = await self.execute(ServiceCommand.GET_DEVICE_MODEL)
        if response and response.payload:
            return response.payload.decode('utf-8', errors='replace').strip('\x00')
        return None
    
    async def set_port_power(self, port_id: int, enable: bool) -> bool:
        """Turn port on or off
        
        Args:
            port_id: Port ID (0-7), NOT a bitmask
            enable: True to turn on, False to turn off
        """
        service = ServiceCommand.TURN_ON_PORT if enable else ServiceCommand.TURN_OFF_PORT
        response = await self.execute(service, bytes([port_id]))
        return response is not None
    
    async def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        info = {}
        
        # Get model
        resp = await self.execute(ServiceCommand.GET_DEVICE_MODEL)
        if resp and resp.payload:
            info["model"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
        
        # Get firmware version
        resp = await self.execute(ServiceCommand.GET_AP_VERSION)
        if resp and resp.payload:
            info["firmware"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
        
        # Get serial number
        resp = await self.execute(ServiceCommand.GET_DEVICE_SERIAL_NO)
        if resp and resp.payload:
            info["serial"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
        
        # Get uptime
        resp = await self.execute(ServiceCommand.GET_DEVICE_UPTIME)
        if resp and resp.payload and len(resp.payload) >= 4:
            uptime = int.from_bytes(resp.payload[:4], 'little')
            info["uptime"] = uptime
        
        return info
    
    async def set_wifi(self, ssid: str, password: str) -> bool:
        """Set WiFi SSID and password"""
        payload = f"{ssid}\0{password}\0".encode('utf-8')
        response = await self.execute(ServiceCommand.SET_WIFI_SSID_AND_PASSWORD, payload)
        return response is not None
    
    async def get_wifi_status(self) -> Optional[str]:
        """Get WiFi status"""
        response = await self.execute(ServiceCommand.GET_WIFI_STATUS)
        if response and response.payload:
            return response.payload.decode('utf-8', errors='replace').strip('\x00')
        return None
    
    async def reboot_device(self) -> bool:
        """Reboot device"""
        response = await self.execute(ServiceCommand.REBOOT_DEVICE)
        return response is not None
    
    async def reset_device(self) -> bool:
        """Factory reset device"""
        response = await self.execute(ServiceCommand.RESET_DEVICE)
        return response is not None
    
    async def set_display_brightness(self, brightness: int) -> bool:
        """Set display brightness (0-100)"""
        response = await self.execute(ServiceCommand.SET_DISPLAY_INTENSITY, bytes([brightness]))
        return response is not None
    
    async def set_display_mode(self, mode: int) -> bool:
        """Set display mode"""
        response = await self.execute(ServiceCommand.SET_DISPLAY_MODE, bytes([mode]))
        return response is not None
    
    async def flip_display(self) -> bool:
        """Flip display"""
        response = await self.execute(ServiceCommand.SET_DISPLAY_FLIP)
        return response is not None
    
    def enable_auto_reconnect(self, enabled: bool = True):
        """Enable or disable auto-reconnect"""
        self._auto_reconnect_enabled = enabled
    
    def enable_auto_refresh(self, enabled: bool = True):
        """Enable or disable auto token refresh"""
        self.token_manager.auto_refresh = enabled
    
    def set_refresh_interval(self, seconds: int):
        """Set token refresh interval in seconds"""
        self.token_manager.refresh_interval = seconds
    
    def _save_token_to_storage(self, token: int):
        """Save token to storage file"""
        try:
            tokens = self._load_tokens_from_storage()
            device_address = self.device.address if self.device else "unknown"
            tokens[device_address] = {
                'token': token,
                'last_used': time.time()
            }
            with open(self.token_manager.storage_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            self.log(f"Token 已保存到存储: 0x{token:02X}")
        except Exception as e:
            self.log(f"保存Token到存储失败: {e}")
    
    def _load_tokens_from_storage(self) -> dict:
        """Load tokens from storage file"""
        try:
            with open(self.token_manager.storage_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def get_stored_tokens(self) -> dict:
        """Get all stored tokens"""
        return self._load_tokens_from_storage()
    
    def load_token_from_storage(self, device_address: str) -> Optional[int]:
        """Load token for specific device from storage"""
        tokens = self._load_tokens_from_storage()
        if device_address in tokens:
            self.log(f"从存储加载Token: 0x{tokens[device_address]['token']:02X}")
            return tokens[device_address]['token']
        return None
    
    def clear_token_storage(self):
        """Clear all stored tokens"""
        try:
            if os.path.exists(self.token_manager.storage_file):
                os.remove(self.token_manager.storage_file)
                self.log("Token 存储已清空")
                return True
            return False
        except Exception as e:
            self.log(f"清空Token存储失败: {e}")
            return False
