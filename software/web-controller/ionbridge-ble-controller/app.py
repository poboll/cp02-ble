"""
IonBridge BLE Controller - FastAPI Backend (Enhanced)
Web application for controlling IonBridge (小电拼) devices via Bluetooth
Supports all 78 BLE commands with auto token refresh and auto reconnect
"""

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ble_manager import BLEManager, DeviceInfo
from protocol import (
    ServiceCommand, decode_protocols, encode_protocols, PROTOCOL_NAMES,
    parse_port_statistics, get_command_name,
    parse_wifi_status_response, parse_charging_strategy_response,
    parse_display_settings_response, parse_port_config_response,
    parse_power_statistics_response, parse_charging_status_response,
    parse_power_supply_status_response, parse_device_info_response,
    parse_device_model_response, parse_device_serial_response,
    parse_device_uptime_response, parse_power_config_response,
    parse_charging_strategy_extended_response, StrategyType,
    CompatibilitySettings, COMPATIBILITY_MODES,
    encode_compatibility_settings, decode_compatibility_settings,
    parse_port_pd_status_response, parse_power_historical_stats_response,
    parse_start_charge_timestamp_response
)


# Global BLE manager instance
ble_manager: Optional[BLEManager] = None
websocket_clients: List[WebSocket] = []
shutdown_event = asyncio.Event()


async def broadcast_log(message: str):
    """Broadcast log message to all connected clients"""
    for ws in websocket_clients:
        try:
            await ws.send_json({
                "type": "log",
                "message": message
            })
        except:
            pass


async def broadcast_status():
    """Broadcast status update to all connected clients"""
    status = {
        "connected": ble_manager.connected if ble_manager else False,
        "token": ble_manager.token if ble_manager else None,
        "device": ble_manager.device.name if ble_manager and ble_manager.device else None,
        "auto_refresh": ble_manager.token_manager.auto_refresh if ble_manager else False,
        "auto_reconnect": ble_manager._auto_reconnect_enabled if ble_manager else False,
    }
    
    for ws in websocket_clients:
        try:
            await ws.send_json({
                "type": "status",
                "data": status
            })
        except:
            pass


async def graceful_shutdown():
    """Gracefully shutdown the application"""
    print("正在优雅关闭应用...")
    
    # 断开BLE连接
    if ble_manager and ble_manager.connected:
        print("正在断开BLE连接...")
        try:
            await ble_manager.disconnect()
            print("BLE连接已断开")
        except Exception as e:
            print(f"断开BLE连接时出错: {e}")
    
    # 关闭所有WebSocket连接
    print("正在关闭WebSocket连接...")
    for ws in websocket_clients:
        try:
            await ws.close()
        except:
            pass
    websocket_clients.clear()
    
    # 设置关闭事件
    shutdown_event.set()
    print("应用已优雅关闭")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"收到信号 {signum}，正在优雅关闭...")
    # 使用asyncio.create_task来避免阻塞
    asyncio.create_task(graceful_shutdown())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global ble_manager
    ble_manager = BLEManager(log_callback=lambda msg: asyncio.create_task(broadcast_log(msg)))
    try:
        yield
    finally:
        # 优雅关闭
        if ble_manager and ble_manager.connected:
            print("应用关闭时正在断开BLE连接...")
            try:
                await ble_manager.disconnect()
                print("BLE连接已断开")
            except Exception as e:
                print(f"断开BLE连接时出错: {e}")
        
        # 关闭所有WebSocket连接
        print("应用关闭时正在关闭WebSocket连接...")
        for ws in websocket_clients:
            try:
                await ws.close()
            except:
                pass
        websocket_clients.clear()
        print("应用已优雅关闭")


app = FastAPI(title="IonBridge BLE Controller", lifespan=lifespan)

# 注册信号处理器
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Serve static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def index():
    """Serve the main page"""
    return FileResponse(static_path / "index.html")


# WebSocket message handlers
async def handle_scan_devices(params: dict) -> dict:
    """Scan for BLE devices"""
    timeout = params.get("timeout", 5.0)
    devices = await ble_manager.scan_devices(timeout=timeout)
    return {
        "success": True,
        "data": {
            "devices": [{"name": d.name, "address": d.address, "rssi": d.rssi} for d in devices]
        }
    }


async def check_connected() -> bool:
    """Check if device is connected, return error if not"""
    if not ble_manager.connected:
        return False
    return True


async def handle_connect(params: dict) -> dict:
    """Connect to a device"""
    address = params.get("address")
    if not address:
        return {"success": False, "message": "缺少设备地址"}
    
    success = await ble_manager.connect(address)
    if success:
        # Check if manual token is provided
        manual_token = params.get("token")
        bruteforce = params.get("bruteforce", False)
        
        if manual_token is not None:
            # Use manual token
            await ble_manager.manual_set_token(manual_token, save_to_storage=True)
            token = manual_token
        elif bruteforce:
            # Bruteforce token
            token = await ble_manager.bruteforce_token(save_to_storage=True)
        else:
            # Try to load from storage first, then bruteforce
            token = await ble_manager.ensure_token()
        
        await broadcast_status()
        
        return {
            "success": True,
            "data": {
                "address": address,
                "token": token
            }
        }
    return {"success": False, "message": "连接失败"}


async def handle_disconnect(params: dict) -> dict:
    """Disconnect from device"""
    success = await ble_manager.disconnect()
    await broadcast_status()
    return {"success": success}


async def handle_refresh_token(params: dict) -> dict:
    """Refresh the token"""
    token = await ble_manager.bruteforce_token()
    await broadcast_status()
    return {
        "success": token is not None,
        "data": {"token": token}
    }


async def handle_set_manual_token(params: dict) -> dict:
    """Set token manually"""
    token = params.get("token")
    if token is None or not isinstance(token, int) or token < 0 or token > 255:
        return {"success": False, "message": "Token 必须在 0-255 之间"}
    
    ble_manager.token_manager.set_token(token, save_to_storage=True)
    await broadcast_status()
    return {"success": True, "data": {"token": token}}

async def handle_manual_bruteforce_token(params: dict) -> dict:
    """Manually bruteforce token and save to storage"""
    save_to_storage = params.get("save_to_storage", True)
    token = await ble_manager.bruteforce_token(save_to_storage=save_to_storage)
    await broadcast_status()
    
    if token is not None:
        return {"success": True, "data": {"token": token}}
    else:
        return {"success": False, "message": "Token 暴力破解失败"}

async def handle_get_stored_tokens(params: dict) -> dict:
    """Get all stored tokens"""
    tokens = ble_manager.token_manager.get_stored_tokens()
    return {"success": True, "data": {"tokens": tokens}}

async def handle_load_token_from_storage(params: dict) -> dict:
    """Load token for a specific device from storage"""
    device_address = params.get("device_address")
    if not device_address:
        return {"success": False, "message": "缺少设备地址"}
    
    token = ble_manager.token_manager.load_token_from_storage(device_address)
    await broadcast_status()
    
    if token is not None:
        return {"success": True, "data": {"token": token}}
    else:
        return {"success": False, "message": "未找到该设备的Token"}

async def handle_clear_token_storage(params: dict) -> dict:
    """Clear all stored tokens"""
    ble_manager.token_manager.get_stored_tokens()  # Just to trigger loading
    # Clear storage file
    import os
    token_file = "token_storage.json"
    if os.path.exists(token_file):
        os.remove(token_file)
        await broadcast_log("Token 存储已清空")
    return {"success": True, "data": {"message": "Token 存储已清空"}}


async def handle_get_status(params: dict) -> dict:
    """Get current connection status"""
    return {
        "success": True,
        "data": {
            "connected": ble_manager.connected if ble_manager else False,
            "token": ble_manager.token if ble_manager else None,
            "device": ble_manager.device.name if ble_manager and ble_manager.device else None,
            "auto_refresh": ble_manager.token_manager.auto_refresh if ble_manager else False,
            "auto_reconnect": ble_manager._auto_reconnect_enabled if ble_manager else False,
        }
    }


async def handle_set_auto_refresh(params: dict) -> dict:
    """Set auto refresh"""
    enabled = params.get("enabled", True)
    ble_manager.enable_auto_refresh(enabled)
    await broadcast_status()
    return {"success": True, "data": {"enabled": enabled}}


async def handle_set_auto_reconnect(params: dict) -> dict:
    """Set auto reconnect"""
    enabled = params.get("enabled", True)
    ble_manager.enable_auto_reconnect(enabled)
    await broadcast_status()
    return {"success": True, "data": {"enabled": enabled}}


async def handle_get_device_info(params: dict) -> dict:
    """Get device information"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    info = {}
    
    # Get model
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_MODEL)
    if resp and resp.payload:
        info["model"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    # Get firmware version
    resp = await ble_manager.execute(ServiceCommand.GET_AP_VERSION)
    if resp and resp.payload:
        info["firmware"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    # Get serial number
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_SERIAL_NO)
    if resp and resp.payload:
        info["serial"] = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    # Get uptime (确保获取到数据)
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_UPTIME)
    if resp and resp.payload and len(resp.payload) >= 8:
        uptime_us = int.from_bytes(resp.payload[:8], 'little')
        uptime_sec = uptime_us // 1000000  # 微秒转秒
        info["uptime"] = uptime_sec
        # 格式化运行时间
        hours = uptime_sec // 3600
        minutes = (uptime_sec % 3600) // 60
        seconds = uptime_sec % 60
        info["uptime_formatted"] = f"{hours}h {minutes}m {seconds}s"
    else:
        # 如果无法获取uptime，设置默认值
        info["uptime"] = 0
        info["uptime_formatted"] = "0h 0m 0s"
    
    # Get BLE address
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_BLE_ADDR)
    if resp and resp.payload:
        info["ble_addr"] = resp.payload.hex()
    
    return {"success": True, "data": info}


async def handle_get_port_status(params: dict) -> dict:
    """Get all port status"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    ports = await ble_manager.get_port_status()
    
    return {
        "success": True,
        "data": {
            "ports": [
                {
                    "port_id": p.port_id,
                    "status": p.status,
                    "protocol": p.protocol,
                    "voltage": p.voltage,
                    "current": p.current,
                    "power": p.power,
                    "charging": p.charging,
                    "enabled": p.enabled,
                }
                for p in ports
            ]
        }
    }


async def handle_set_port_power(params: dict) -> dict:
    """Turn port on or off"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_mask = params.get("port_mask", 0)
    enable = params.get("enable", True)
    
    if isinstance(port_mask, int):
        port_mask = bytes([port_mask])
    else:
        port_mask = bytes(port_mask)
    
    service = ServiceCommand.TURN_ON_PORT if enable else ServiceCommand.TURN_OFF_PORT
    resp = await ble_manager.execute(service, port_mask)
    
    return {"success": resp is not None}


async def handle_get_port_config(params: dict) -> dict:
    """Get port protocol configuration"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
    
    if not resp or not resp.payload or len(resp.payload) < 3:
        return {"success": False, "message": "获取端口配置失败"}
    
    # Parse port config with complete parsing
    data = parse_port_config_response(resp.payload)
    return {
        "success": True,
        "data": data
    }


async def handle_set_port_config(params: dict) -> dict:
    """Set port protocol configuration"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_mask = params.get("port_mask", 0xFF)
    protocols = params.get("protocols", {})
    
    features = encode_protocols(protocols)
    payload = bytes([port_mask]) + features
    
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
    return {"success": resp is not None}


async def handle_enable_protocol(params: dict) -> dict:
    """Enable protocol for a port"""
    port_id = params.get("port_id", 0)
    protocol_name = params.get("protocol")
    
    if protocol_name not in PROTOCOL_NAMES:
        return {"success": False, "message": f"未知协议: {protocol_name}"}
    
    # Get current config
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
    if not resp or not resp.payload:
        return {"success": False, "message": "获取当前配置失败"}
    
    # Update protocol
    protocols = decode_protocols(resp.payload)
    protocols[protocol_name] = True
    
    # Save config
    features = encode_protocols(protocols)
    payload = bytes([1 << port_id]) + features
    
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
    return {"success": resp is not None}


async def handle_disable_protocol(params: dict) -> dict:
    """Disable protocol for a port"""
    port_id = params.get("port_id", 0)
    protocol_name = params.get("protocol")
    
    if protocol_name not in PROTOCOL_NAMES:
        return {"success": False, "message": f"未知协议: {protocol_name}"}
    
    # Get current config
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
    if not resp or not resp.payload:
        return {"success": False, "message": "获取当前配置失败"}
    
    # Update protocol
    protocols = decode_protocols(resp.payload)
    protocols[protocol_name] = False
    
    # Save config
    features = encode_protocols(protocols)
    payload = bytes([1 << port_id]) + features
    
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
    return {"success": resp is not None}


async def handle_get_power_statistics(params: dict) -> dict:
    """Get power statistics"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取电源统计失败"}
    
    # Parse power statistics with complete parsing
    data = parse_power_statistics_response(resp.payload)
    data["port_id"] = port_id
    data["raw_data"] = resp.payload.hex()
    
    return {
        "success": True,
        "data": data
    }


async def handle_get_charging_strategy(params: dict) -> dict:
    """Get charging strategy"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    resp = await ble_manager.execute(ServiceCommand.GET_CHARGING_STRATEGY)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取充电策略失败"}
    
    # Parse charging strategy with complete parsing
    data = parse_charging_strategy_extended_response(resp.payload)
    return {"success": True, "data": data}


async def handle_set_charging_strategy(params: dict) -> dict:
    """Set charging strategy"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    strategy = params.get("strategy", 0)
    
    resp = await ble_manager.execute(ServiceCommand.SET_CHARGING_STRATEGY, bytes([strategy]))
    return {"success": resp is not None}


async def handle_get_wifi_status(params: dict) -> dict:
    """Get WiFi status"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_STATUS)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 WiFi 状态失败"}
    
    # Parse WiFi status with complete parsing
    data = parse_wifi_status_response(resp.payload)
    return {"success": True, "data": data}


async def handle_set_wifi(params: dict) -> dict:
    """Set WiFi SSID and password"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    ssid = params.get("ssid", "")
    password = params.get("password", "")
    
    # Format: ssid\0password\0
    payload = f"{ssid}\0{password}\0".encode('utf-8')
    
    resp = await ble_manager.execute(ServiceCommand.SET_WIFI_SSID_AND_PASSWORD, payload)
    return {"success": resp is not None}


async def handle_scan_wifi(params: dict) -> dict:
    """Scan WiFi networks"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}

    # Step 1: Trigger WiFi scan
    resp = await ble_manager.execute(ServiceCommand.SCAN_WIFI)
    if not resp:
        return {"success": False, "message": "WiFi扫描命令失败"}

    # Step 2: Get scan results
    await asyncio.sleep(3)  # Wait for scan to complete
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_SCAN_RESULT)
    if not resp or not resp.payload:
        return {"success": False, "message": "获取WiFi扫描结果失败"}

    # Parse WiFi scan results
    networks = []
    payload = resp.payload
    if len(payload) > 1:
        count = payload[0]
        offset = 1
        for _ in range(count):
            if offset >= len(payload):
                break
            ssid_len = payload[offset] if offset < len(payload) else 0
            offset += 1
            if offset + ssid_len > len(payload):
                break
            ssid = payload[offset:offset + ssid_len].decode('utf-8', errors='replace')
            offset += ssid_len
            rssi = payload[offset] - 256 if offset < len(payload) and payload[offset] > 127 else (payload[offset] if offset < len(payload) else 0)
            offset += 1
            auth = payload[offset] if offset < len(payload) else 0
            offset += 1
            stored = payload[offset] if offset < len(payload) else 0
            offset += 1
            networks.append({'ssid': ssid, 'rssi': rssi, 'auth': auth, 'stored': bool(stored)})

    return {"success": True, "data": {"networks": networks, "count": len(networks)}}


async def handle_reboot_device(params: dict) -> dict:
    """Reboot the device"""
    resp = await ble_manager.execute(ServiceCommand.REBOOT_DEVICE)
    return {"success": resp is not None}


async def handle_reset_device(params: dict) -> dict:
    """Factory reset the device"""
    resp = await ble_manager.execute(ServiceCommand.RESET_DEVICE)
    return {"success": resp is not None}


async def handle_get_display_settings(params: dict) -> dict:
    """Get display settings"""
    settings = {}
    
    resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_INTENSITY)
    if resp and resp.payload:
        brightness_data = parse_display_settings_response(resp.payload)
        settings["brightness"] = brightness_data.get("brightness", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_MODE)
    if resp and resp.payload:
        mode_data = parse_display_settings_response(resp.payload)
        settings["mode"] = mode_data.get("mode", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_FLIP)
    if resp and resp.payload:
        flip_data = parse_display_settings_response(resp.payload)
        settings["flip"] = flip_data.get("flip", 0)
    
    return {"success": True, "data": settings}


async def handle_set_display_brightness(params: dict) -> dict:
    """Set display brightness"""
    brightness = params.get("brightness", 100)
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_INTENSITY, bytes([brightness]))
    return {"success": resp is not None}


async def handle_set_display_mode(params: dict) -> dict:
    """Set display mode"""
    mode = params.get("mode", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_MODE, bytes([mode]))
    return {"success": resp is not None}


async def handle_flip_display(params: dict) -> dict:
    """Flip the display"""
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_FLIP)
    return {"success": resp is not None}


async def handle_set_port_priority(params: dict) -> dict:
    """Set port priority"""
    port_id = params.get("port_id", 0)
    priority = params.get("priority", 0)
    
    payload = bytes([port_id, priority])
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_PRIORITY, payload)
    return {"success": resp is not None}


async def handle_get_port_priority(params: dict) -> dict:
    """Get all port priorities"""
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_PRIORITY)

    if not resp or not resp.payload:
        return {"success": False, "message": "获取端口优先级失败"}

    # 返回所有端口的优先级数组
    priorities = list(resp.payload[:5]) if len(resp.payload) >= 5 else list(resp.payload)
    # 确保返回5个端口的优先级
    while len(priorities) < 5:
        priorities.append(len(priorities))

    return {
        "success": True,
        "data": {"priorities": priorities}
    }


async def handle_get_charging_status(params: dict) -> dict:
    """Get charging status"""
    resp = await ble_manager.execute(ServiceCommand.GET_CHARGING_STATUS)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取充电状态失败"}
    
    # Parse charging status with complete parsing
    data = parse_charging_status_response(resp.payload)
    data["raw_data"] = resp.payload.hex()
    
    return {
        "success": True,
        "data": data
    }


# Additional handlers for more BLE commands
async def handle_get_power_supply_status(params: dict) -> dict:
    """Get power supply status"""
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_SUPPLY_STATUS)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取电源供应状态失败"}
    
    # Parse power supply status with complete parsing
    data = parse_power_supply_status_response(resp.payload)
    data["raw_data"] = resp.payload.hex()
    
    return {"success": True, "data": data}


async def handle_get_device_model(params: dict) -> dict:
    """Get device model"""
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_MODEL)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取设备型号失败"}
    
    # Parse device model with complete parsing
    data = parse_device_model_response(resp.payload)
    
    return {"success": True, "data": data}


async def handle_get_device_serial(params: dict) -> dict:
    """Get device serial number"""
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_SERIAL_NO)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取设备序列号失败"}
    
    # Parse device serial with complete parsing
    data = parse_device_serial_response(resp.payload)
    
    return {"success": True, "data": data}


async def handle_get_device_uptime(params: dict) -> dict:
    """Get device uptime"""
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_UPTIME)
    
    if not resp or not resp.payload or len(resp.payload) < 4:
        return {"success": False, "message": "获取设备运行时间失败"}
    
    # Parse device uptime with complete parsing
    data = parse_device_uptime_response(resp.payload)
    
    return {"success": True, "data": data}


async def handle_get_ap_version(params: dict) -> dict:
    """Get AP firmware version"""
    resp = await ble_manager.execute(ServiceCommand.GET_AP_VERSION)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取固件版本失败"}
    
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    return {"success": True, "data": {"version": version}}


async def handle_get_ble_addr(params: dict) -> dict:
    """Get device BLE address"""
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_BLE_ADDR)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 BLE 地址失败"}
    
    ble_addr = resp.payload.hex()
    
    return {"success": True, "data": {"ble_addr": ble_addr}}


async def handle_associate_device(params: dict) -> dict:
    """Associate device (no token required)"""
    resp = await ble_manager.execute(ServiceCommand.ASSOCIATE_DEVICE)
    
    return {"success": resp is not None}


async def handle_unbind_device(params: dict) -> dict:
    """Unbind device"""
    resp = await ble_manager.execute(ServiceCommand.UNBIND_DEVICE)
    
    return {"success": resp is not None}


async def handle_factory_reset(params: dict) -> dict:
    """Factory reset device"""
    resp = await ble_manager.execute(ServiceCommand.FACTORY_RESET)
    
    return {"success": resp is not None}


async def handle_get_mcu_version(params: dict) -> dict:
    """Get MCU version"""
    resp = await ble_manager.execute(ServiceCommand.GET_MCU_VERSION)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 MCU 版本失败"}
    
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    return {"success": True, "data": {"version": version}}


async def handle_get_fpga_version(params: dict) -> dict:
    """Get FPGA version"""
    resp = await ble_manager.execute(ServiceCommand.GET_FPGA_VERSION)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 FPGA 版本失败"}
    
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    return {"success": True, "data": {"version": version}}


async def handle_get_sw3566_version(params: dict) -> dict:
    """Get SW3566 version"""
    resp = await ble_manager.execute(ServiceCommand.GET_SW3566_VERSION)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 SW3566 版本失败"}
    
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    
    return {"success": True, "data": {"version": version}}


async def handle_set_max_power(params: dict) -> dict:
    """Set max power"""
    power = params.get("power", 0)
    
    if isinstance(power, int):
        payload = bytes([power])
    else:
        payload = bytes([int(power)])
    
    resp = await ble_manager.execute(ServiceCommand.SET_MAX_POWER, payload)
    
    return {"success": resp is not None}


async def handle_get_max_power(params: dict) -> dict:
    """Get max power"""
    resp = await ble_manager.execute(ServiceCommand.GET_MAX_POWER)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取最大功率失败"}
    
    max_power = resp.payload[0] if resp.payload else 0
    
    return {"success": True, "data": {"max_power": max_power}}


async def handle_set_port_max_power(params: dict) -> dict:
    """Set port max power"""
    port_id = params.get("port_id", 0)
    max_power = params.get("max_power", 0)
    
    payload = bytes([port_id, max_power])
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_MAX_POWER, payload)
    
    return {"success": resp is not None}


async def handle_get_port_max_power(params: dict) -> dict:
    """Get port max power"""
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_MAX_POWER, bytes([port_id]))
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取端口最大功率失败"}
    
    max_power = resp.payload[0] if resp.payload else 0
    
    return {"success": True, "data": {"port_id": port_id, "max_power": max_power}}


async def handle_get_port_temperature(params: dict) -> dict:
    """Get port temperature - uses GET_POWER_STATISTICS which includes temperature"""
    port_id = params.get("port_id", 0)

    # GET_POWER_STATISTICS returns: [fc_protocol, amperage, voltage, temperature]
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))

    if not resp or not resp.payload or len(resp.payload) < 4:
        return {"success": False, "message": "获取端口温度失败"}

    temperature = resp.payload[3]  # 4th byte is temperature

    return {"success": True, "data": {"port_id": port_id, "temperature": temperature}}


async def handle_set_night_mode(params: dict) -> dict:
    """Set night mode"""
    enabled = params.get("enabled", False)
    start_hour = params.get("start_hour", 22)
    start_minute = params.get("start_minute", 0)
    end_hour = params.get("end_hour", 7)
    end_minute = params.get("end_minute", 0)
    
    payload = bytes([1 if enabled else 0, start_hour, start_minute, end_hour, end_minute])
    resp = await ble_manager.execute(ServiceCommand.SET_NIGHT_MODE, payload)
    
    return {"success": resp is not None}


async def handle_get_night_mode(params: dict) -> dict:
    """Get night mode"""
    resp = await ble_manager.execute(ServiceCommand.GET_NIGHT_MODE)
    
    if not resp or not resp.payload or len(resp.payload) < 5:
        return {"success": False, "message": "获取夜间模式失败"}
    
    enabled = resp.payload[0] == 1
    start_hour = resp.payload[1]
    start_minute = resp.payload[2]
    end_hour = resp.payload[3]
    end_minute = resp.payload[4]
    
    return {
        "success": True,
        "data": {
            "enabled": enabled,
            "start_hour": start_hour,
            "start_minute": start_minute,
            "end_hour": end_hour,
            "end_minute": end_minute
        }
    }


async def handle_set_language(params: dict) -> dict:
    """Set language"""
    language = params.get("language", 0)
    
    resp = await ble_manager.execute(ServiceCommand.SET_LANGUAGE, bytes([language]))
    
    return {"success": resp is not None}


async def handle_get_language(params: dict) -> dict:
    """Get language"""
    resp = await ble_manager.execute(ServiceCommand.GET_LANGUAGE)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取语言设置失败"}
    
    language = resp.payload[0] if resp.payload else 0
    
    return {"success": True, "data": {"language": language}}


async def handle_set_led_mode(params: dict) -> dict:
    """Set LED mode"""
    mode = params.get("mode", 0)
    
    resp = await ble_manager.execute(ServiceCommand.SET_LED_MODE, bytes([mode]))
    
    return {"success": resp is not None}


async def handle_get_led_mode(params: dict) -> dict:
    """Get LED mode"""
    resp = await ble_manager.execute(ServiceCommand.GET_LED_MODE)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取 LED 模式失败"}
    
    mode = resp.payload[0] if resp.payload else 0
    
    return {"success": True, "data": {"mode": mode}}


async def handle_set_auto_off(params: dict) -> dict:
    """Set auto off"""
    enabled = params.get("enabled", False)
    timeout = params.get("timeout", 30)
    
    payload = bytes([1 if enabled else 0, timeout])
    resp = await ble_manager.execute(ServiceCommand.SET_AUTO_OFF, payload)
    
    return {"success": resp is not None}


async def handle_get_auto_off(params: dict) -> dict:
    """Get auto off"""
    resp = await ble_manager.execute(ServiceCommand.GET_AUTO_OFF)
    
    if not resp or not resp.payload or len(resp.payload) < 2:
        return {"success": False, "message": "获取自动关闭设置失败"}
    
    enabled = resp.payload[0] == 1
    timeout = resp.payload[1]
    
    return {
        "success": True,
        "data": {
            "enabled": enabled,
            "timeout": timeout
        }
    }


async def handle_set_screen_saver(params: dict) -> dict:
    """Set screen saver"""
    enabled = params.get("enabled", False)
    timeout = params.get("timeout", 60)
    
    payload = bytes([1 if enabled else 0, timeout])
    resp = await ble_manager.execute(ServiceCommand.SET_SCREEN_SAVER, payload)
    
    return {"success": resp is not None}


async def handle_get_screen_saver(params: dict) -> dict:
    """Get screen saver"""
    resp = await ble_manager.execute(ServiceCommand.GET_SCREEN_SAVER)
    
    if not resp or not resp.payload or len(resp.payload) < 2:
        return {"success": False, "message": "获取屏保设置失败"}
    
    enabled = resp.payload[0] == 1
    timeout = resp.payload[1]
    
    return {
        "success": True,
        "data": {
            "enabled": enabled,
            "timeout": timeout
        }
    }


# Power config handlers (must be defined before ACTION_HANDLERS)
async def handle_get_power_config(params: dict) -> dict:
    """Get power config"""
    resp = await ble_manager.execute(ServiceCommand.MANAGE_POWER_CONFIG, bytes([0]))
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取电源配置失败"}
    
    # Parse power config
    data = parse_power_config_response(resp.payload)
    return {"success": True, "data": data}


async def handle_set_power_config(params: dict) -> dict:
    """Set power config"""
    max_power = params.get("max_power", 240)
    cooldown_period = params.get("cooldown_period", 5)
    apply_period = params.get("apply_period", 1)
    temperature_mode = params.get("temperature_mode", 0)
    
    # Build PowerConfig payload (version 1)
    # Structure: version(1) + max_power(1) + cooldown_period(4) + apply_period(4) + temperature_mode(1)
    payload = bytes([1, max_power]) + cooldown_period.to_bytes(4, 'little') + apply_period.to_bytes(4, 'little') + bytes([temperature_mode])
    
    resp = await ble_manager.execute(ServiceCommand.MANAGE_POWER_CONFIG, bytes([1]) + payload)
    return {"success": resp is not None}


async def handle_set_slow_charging_strategy(params: dict) -> dict:
    """Set slow charging strategy"""
    resp = await ble_manager.execute(ServiceCommand.SET_TEMPORARY_ALLOCATOR, bytes([StrategyType.SLOW_CHARGING.value]))
    return {"success": resp is not None}


async def handle_set_static_charging_strategy(params: dict) -> dict:
    """Set static charging strategy"""
    resp = await ble_manager.execute(ServiceCommand.SET_STATIC_ALLOCATOR, bytes([StrategyType.STATIC_CHARGING.value]))
    return {"success": resp is not None}


async def handle_set_temporary_charging_strategy(params: dict) -> dict:
    """Set temporary charging strategy"""
    resp = await ble_manager.execute(ServiceCommand.SET_TEMPORARY_ALLOCATOR, bytes([StrategyType.TEMPORARY_CHARGING.value]))
    return {"success": resp is not None}


async def handle_set_usba_charging_strategy(params: dict) -> dict:
    """Set USB-A charging strategy"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    resp = await ble_manager.execute(ServiceCommand.SET_TEMPORARY_ALLOCATOR, bytes([StrategyType.USBA_CHARGING.value]))
    return {"success": resp is not None}


async def handle_get_compatibility_modes(params: dict) -> dict:
    """Get all predefined compatibility modes"""
    modes = {}
    for mode_id, mode_info in COMPATIBILITY_MODES.items():
        settings = mode_info['settings']
        modes[mode_id] = {
            'name': mode_info['name'],
            'description': mode_info['description'],
            'settings': {
                'isTfcpEnabled': settings.isTfcpEnabled,
                'isFcpEnabled': settings.isFcpEnabled,
                'isUfcsEnabled': settings.isUfcsEnabled,
                'isHvScpEnabled': settings.isHvScpEnabled,
                'isLvScpEnabled': settings.isLvScpEnabled
            }
        }
    return {"success": True, "data": {"modes": modes}}


async def handle_set_compatibility_mode(params: dict) -> dict:
    """Set compatibility mode by predefined mode name"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    mode_id = params.get("mode_id", "native")
    if mode_id not in COMPATIBILITY_MODES:
        return {"success": False, "message": f"未知模式: {mode_id}"}
    
    settings = COMPATIBILITY_MODES[mode_id]['settings']
    payload = encode_compatibility_settings(settings)
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_COMPATIBILITY_SETTINGS, payload)
    
    if resp is not None:
        return {
            "success": True,
            "data": {
                "mode_id": mode_id,
                "mode_name": COMPATIBILITY_MODES[mode_id]['name']
            }
        }
    return {"success": False, "message": "设置失败"}


async def handle_get_compatibility_settings(params: dict) -> dict:
    """Get current compatibility settings"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_COMPATIBILITY_SETTINGS)
    if not resp or not resp.payload:
        return {"success": False, "message": "获取设置失败"}
    
    settings = decode_compatibility_settings(resp.payload)
    return {
        "success": True,
        "data": {
            "isTfcpEnabled": settings.isTfcpEnabled,
            "isFcpEnabled": settings.isFcpEnabled,
            "isUfcsEnabled": settings.isUfcsEnabled,
            "isHvScpEnabled": settings.isHvScpEnabled,
            "isLvScpEnabled": settings.isLvScpEnabled
        }
    }


async def handle_set_custom_compatibility_settings(params: dict) -> dict:
    """Set custom compatibility settings"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    settings = CompatibilitySettings(
        isTfcpEnabled=params.get("isTfcpEnabled", True),
        isFcpEnabled=params.get("isFcpEnabled", True),
        isUfcsEnabled=params.get("isUfcsEnabled", True),
        isHvScpEnabled=params.get("isHvScpEnabled", True),
        isLvScpEnabled=params.get("isLvScpEnabled", True)
    )
    
    payload = encode_compatibility_settings(settings)
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_COMPATIBILITY_SETTINGS, payload)
    
    return {"success": resp is not None}


# Additional BLE command handlers
async def handle_get_power_historical_stats(params: dict) -> dict:
    """Get power historical statistics"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    offset = params.get("offset", 0)
    
    # Build payload: [port_id, offset_low, offset_high]
    payload = bytes([port_id, offset & 0xFF, (offset >> 8) & 0xFF])
    
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_HISTORICAL_STATS, payload)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取历史功率统计失败"}
    
    data = parse_power_historical_stats_response(resp.payload)
    return {"success": True, "data": data}


async def handle_get_port_pd_status(params: dict) -> dict:
    """Get port PD status"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_PD_STATUS, bytes([port_id]))
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取端口PD状态失败"}
    
    data = parse_port_pd_status_response(resp.payload)
    data["port_id"] = port_id  # Include port_id in response
    return {"success": True, "data": data}


async def handle_get_start_charge_timestamp(params: dict) -> dict:
    """Get start charge timestamp"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    resp = await ble_manager.execute(ServiceCommand.GET_START_CHARGE_TIMESTAMP)
    
    if not resp or not resp.payload:
        return {"success": False, "message": "获取开始充电时间戳失败"}
    
    data = parse_start_charge_timestamp_response(resp.payload)
    return {"success": True, "data": data}


async def handle_turn_on_port(params: dict) -> dict:
    """Turn on port"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.TURN_ON_PORT, bytes([port_id]))
    
    return {"success": resp is not None}


async def handle_turn_off_port(params: dict) -> dict:
    """Turn off port"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    
    port_id = params.get("port_id", 0)
    
    resp = await ble_manager.execute(ServiceCommand.TURN_OFF_PORT, bytes([port_id]))
    
    return {"success": resp is not None}


async def handle_set_temperature_mode(params: dict) -> dict:
    """Set temperature mode"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}

    mode = params.get("mode", 0)  # 0: Power Priority, 1: Temperature Priority

    resp = await ble_manager.execute(ServiceCommand.SET_TEMPERATURE_MODE, bytes([mode]))

    if resp is not None:
        return {"success": True, "data": {"mode": mode, "mode_name": "功率优先" if mode == 0 else "温度优先"}}
    return {"success": False, "message": "设置温度模式失败"}


# ============ 新增功能: 版本信息 ============

async def handle_get_bp_version(params: dict) -> dict:
    """Get BP (SW3566 MCU) version"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.GET_BP_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3:
        return {"success": False, "message": "获取BP版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}


async def handle_get_fpga_version(params: dict) -> dict:
    """Get FPGA version"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.GET_FPGA_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3:
        return {"success": False, "message": "获取FPGA版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}


async def handle_get_zrlib_version(params: dict) -> dict:
    """Get ZRLIB version"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.GET_ZRLIB_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3:
        return {"success": False, "message": "获取ZRLIB版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}


# ============ 新增功能: 调试/测试 ============

async def handle_ble_echo_test(params: dict) -> dict:
    """BLE echo test"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    test_data = params.get("data", "test").encode('utf-8')
    resp = await ble_manager.execute(ServiceCommand.BLE_ECHO_TEST, test_data)
    if not resp or not resp.payload:
        return {"success": False, "message": "BLE回显测试失败"}
    return {"success": True, "data": {"echo": resp.payload.decode('utf-8', errors='replace')}}


async def handle_get_debug_log(params: dict) -> dict:
    """Get debug log"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEBUG_LOG)
    if not resp or not resp.payload:
        return {"success": False, "message": "获取调试日志失败"}
    return {"success": True, "data": {"log": resp.payload.decode('utf-8', errors='replace')}}


async def handle_ping_mqtt(params: dict) -> dict:
    """Ping MQTT telemetry - 返回命令执行状态，不代表网络连接状态"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.PING_MQTT_TELEMETRY)
    # 注意: 此命令返回ESP_OK表示命令执行成功，不代表MQTT实际连接成功
    # 需要检查WiFi状态来确认网络连接
    return {"success": resp is not None, "data": {"status": "command_ok" if resp else "command_failed", "note": "此结果仅表示命令执行状态，请检查WiFi状态确认网络连接"}}


async def handle_ping_http(params: dict) -> dict:
    """Ping HTTP - 需要提供URL参数"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    url = params.get("url", "")
    if not url:
        return {"success": False, "message": "请提供HTTP URL参数", "data": {"note": "此命令需要URL参数才能测试HTTP连接"}}
    resp = await ble_manager.execute(ServiceCommand.PING_HTTP, url.encode('utf-8'), timeout=15.0)
    return {"success": resp is not None, "data": {"status": "command_ok" if resp else "command_failed", "url": url}}


# ============ 新增功能: OTA固件更新 ============

async def handle_wifi_ota(params: dict) -> dict:
    """Start WiFi OTA update"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    url = params.get("url", "")
    if not url:
        return {"success": False, "message": "请提供OTA URL"}
    resp = await ble_manager.execute(ServiceCommand.PERFORM_WIFI_OTA, url.encode('utf-8'))
    return {"success": resp is not None, "message": "OTA更新已启动" if resp else "OTA启动失败"}


async def handle_get_ota_progress(params: dict) -> dict:
    """Get OTA progress"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_OTA_PROGRESS)
    if not resp or not resp.payload:
        return {"success": False, "message": "获取OTA进度失败"}
    progress = resp.payload[0] if len(resp.payload) > 0 else 0
    return {"success": True, "data": {"progress": progress}}


async def handle_confirm_ota(params: dict) -> dict:
    """Confirm OTA update"""
    if not await check_connected():
        return {"success": False, "message": "未连接设备"}
    resp = await ble_manager.execute(ServiceCommand.CONFIRM_OTA)
    return {"success": resp is not None}


# Action handlers mapping
ACTION_HANDLERS = {
    "scan_devices": handle_scan_devices,
    "connect": handle_connect,
    "disconnect": handle_disconnect,
    "refresh_token": handle_refresh_token,
    "set_manual_token": handle_set_manual_token,
    "manual_bruteforce_token": handle_manual_bruteforce_token,
    "get_stored_tokens": handle_get_stored_tokens,
    "load_token_from_storage": handle_load_token_from_storage,
    "clear_token_storage": handle_clear_token_storage,
    "get_status": handle_get_status,
    "set_auto_refresh": handle_set_auto_refresh,
    "set_auto_reconnect": handle_set_auto_reconnect,
    "get_device_info": handle_get_device_info,
    "get_port_status": handle_get_port_status,
    "set_port_power": handle_set_port_power,
    "get_port_config": handle_get_port_config,
    "set_port_config": handle_set_port_config,
    "enable_protocol": handle_enable_protocol,
    "disable_protocol": handle_disable_protocol,
    "get_power_statistics": handle_get_power_statistics,
    "get_charging_strategy": handle_get_charging_strategy,
    "set_charging_strategy": handle_set_charging_strategy,
    "get_wifi_status": handle_get_wifi_status,
    "set_wifi": handle_set_wifi,
    "scan_wifi": handle_scan_wifi,
    "reboot_device": handle_reboot_device,
    "reset_device": handle_reset_device,
    "get_display_settings": handle_get_display_settings,
    "set_display_brightness": handle_set_display_brightness,
    "set_display_mode": handle_set_display_mode,
    "flip_display": handle_flip_display,
    "set_port_priority": handle_set_port_priority,
    "get_port_priority": handle_get_port_priority,
    "get_charging_status": handle_get_charging_status,
    # Additional handlers
    "get_power_supply_status": handle_get_power_supply_status,
    "get_device_model": handle_get_device_model,
    "get_device_serial": handle_get_device_serial,
    "get_device_uptime": handle_get_device_uptime,
    "get_ap_version": handle_get_ap_version,
    "get_ble_addr": handle_get_ble_addr,
    "associate_device": handle_associate_device,
    "unbind_device": handle_unbind_device,
    "factory_reset": handle_factory_reset,
    "get_mcu_version": handle_get_mcu_version,
    "get_fpga_version": handle_get_fpga_version,
    "get_sw3566_version": handle_get_sw3566_version,
    "set_max_power": handle_set_max_power,
    "get_max_power": handle_get_max_power,
    "set_port_max_power": handle_set_port_max_power,
    "get_port_max_power": handle_get_port_max_power,
    "get_port_temperature": handle_get_port_temperature,
    "set_night_mode": handle_set_night_mode,
    "get_night_mode": handle_get_night_mode,
    "set_language": handle_set_language,
    "get_language": handle_get_language,
    "set_led_mode": handle_set_led_mode,
    "get_led_mode": handle_get_led_mode,
    "set_auto_off": handle_set_auto_off,
    "get_auto_off": handle_get_auto_off,
    "set_screen_saver": handle_set_screen_saver,
    "get_screen_saver": handle_get_screen_saver,
    # Power config handlers
    "get_power_config": handle_get_power_config,
    "set_power_config": handle_set_power_config,
    "set_slow_charging_strategy": handle_set_slow_charging_strategy,
    "set_static_charging_strategy": handle_set_static_charging_strategy,
    "set_temporary_charging_strategy": handle_set_temporary_charging_strategy,
    "set_usba_charging_strategy": handle_set_usba_charging_strategy,
    # Compatibility settings handlers
    "get_compatibility_modes": handle_get_compatibility_modes,
    "set_compatibility_mode": handle_set_compatibility_mode,
    "get_compatibility_settings": handle_get_compatibility_settings,
    "set_custom_compatibility_settings": handle_set_custom_compatibility_settings,
    # Additional BLE command handlers
    "get_power_historical_stats": handle_get_power_historical_stats,
    "get_port_pd_status": handle_get_port_pd_status,
    "get_start_charge_timestamp": handle_get_start_charge_timestamp,
    "turn_on_port": handle_turn_on_port,
    "turn_off_port": handle_turn_off_port,
    "set_temperature_mode": handle_set_temperature_mode,
    # 新增: 版本信息
    "get_bp_version": handle_get_bp_version,
    "get_fpga_version": handle_get_fpga_version,
    "get_zrlib_version": handle_get_zrlib_version,
    # 新增: 调试/测试
    "ble_echo_test": handle_ble_echo_test,
    "get_debug_log": handle_get_debug_log,
    "ping_mqtt": handle_ping_mqtt,
    "ping_http": handle_ping_http,
    # 新增: OTA固件更新
    "wifi_ota": handle_wifi_ota,
    "get_ota_progress": handle_get_ota_progress,
    "confirm_ota": handle_confirm_ota,
}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "response",
            "action": "get_status",
            **await handle_get_status({})
        })
        
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            params = data.get("params", {})
            
            handler = ACTION_HANDLERS.get(action)
            if handler:
                try:
                    result = await handler(params)
                    # Check if websocket is still connected before sending
                    try:
                        await websocket.send_json({
                            "type": "response",
                            "action": action,
                            **result
                        })
                    except RuntimeError:
                        # Connection already closed, break the loop
                        break
                except Exception as e:
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "action": action,
                            "message": str(e)
                        })
                    except RuntimeError:
                        # Connection already closed, break the loop
                        break
            else:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知操作: {action}"
                    })
                except RuntimeError:
                    # Connection already closed, break the loop
                    break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass  # Handle any other exceptions
    finally:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=2222)
