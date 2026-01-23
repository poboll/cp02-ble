#!/usr/bin/env python3
"""
小电拼充电站监控 - BLE版本
基于 Charging-Station-WebS 的精美 UI，使用 BLE 获取数据
完整功能版本，支持所有 78 个 BLE 命令
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware  # 引入 Gzip

from ble_manager import BLEManager
from protocol import (
    ServiceCommand, 
    parse_port_pd_status_response,
    decode_protocols, encode_protocols, PROTOCOL_NAMES,
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
    parse_power_historical_stats_response,
    parse_start_charge_timestamp_response
)

# 创建FastAPI应用
app = FastAPI(title="小电拼充电站监控 (BLE版本)", version="1.1.0")

class ConnectRequest(BaseModel):
    address: Optional[str] = None

# 1. 启用 Gzip 压缩，提升传输效率
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
ble_manager: Optional[BLEManager] = None
websocket_clients: List[WebSocket] = []
shutdown_event = asyncio.Event()

# 静态文件服务 - 将在所有路由定义后挂载到根目录
static_path = Path(__file__).parent


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global ble_manager
    print("=" * 60)
    print("  ⚡ 小电拼充电站监控 (BLE极致优化版)")
    print("  🚀 服务端口: 5223")
    print("  📱 访问地址: http://127.0.0.1:5223")
    print("=" * 60)
    
    # 创建BLE管理器，启用自动重连优化
    # 修复类型错误：log_callback 不需要返回值
    def log_wrapper(msg: str):
        asyncio.create_task(broadcast_log(msg))
        
    ble_manager = BLEManager(log_callback=log_wrapper)
    # 预设更合理的重连参数
    ble_manager.set_refresh_interval(300) # 5分钟刷新一次Token



@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("\n[关闭] 正在关闭BLE充电站监控...")
    
    # 断开BLE连接
    if ble_manager and ble_manager.connected:
        print("[关闭] 正在断开BLE连接...")
        try:
            await ble_manager.disconnect()
            print("[关闭] BLE连接已断开")
        except Exception as e:
            print(f"[错误] 断开BLE连接时出错: {e}")
    
    # 关闭所有WebSocket连接
    print("[关闭] 正在关闭WebSocket连接...")
    for ws in websocket_clients:
        try:
            await ws.close()
        except:
            pass
    websocket_clients.clear()
    
    print("[关闭] BLE充电站监控已关闭")


async def broadcast_log(message: str):
    """广播日志消息到所有WebSocket客户端"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)  # 同时输出到控制台
    
    for ws in websocket_clients:
        try:
            await ws.send_json({"type": "log", "message": log_message})
        except:
            pass


async def broadcast_status():
    """广播连接状态到所有WebSocket客户端"""
    status = {
        "type": "status",
        "data": {
            "connected": ble_manager.connected if ble_manager else False,
            "device": ble_manager.device.name if ble_manager and ble_manager.device else None,
            "address": ble_manager.device.address if ble_manager and ble_manager.device else None,
            "token": ble_manager.token if ble_manager else None,
        }
    }
    
    for ws in websocket_clients:
        try:
            await ws.send_json(status)
        except:
            pass



@app.get("/api/port-status")
async def get_port_status():
    """获取端口状态 - 主要数据接口"""
    if not ble_manager or not ble_manager.connected:
        # 返回空数据而不是503错误，避免前端频繁报错
        return JSONResponse(
            status_code=200,  # 改为200，让前端正常处理
            content={
                "ports": [
                    {"state": 0, "protocol": 0, "current": 0, "voltage": 0, "power": 0,
                     "cablePid": None, "manufacturerVid": None, "manufacturerPid": None,
                     "batteryVid": None, "batteryLastFullCapacity": 0,
                     "batteryPresentCapacity": 0, "batteryDesignCapacity": 0}
                    for _ in range(5)
                ],
                "totalPower": 0,
                "averageVoltage": 0,
                "totalCurrent": 0,
                "activePorts": 0,
                "system": {"wifiSignal": -100, "freeHeap": 0},
                "connected": False,
                "message": "BLE设备未连接，请先连接设备",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    try:
        # 从缓存构建数据，不再实时请求
        ports = []
        total_power = 0
        total_current = 0
        max_voltage = 0
        active_ports = 0
        
        for port_id in range(5):
            cache = ble_manager.port_states.get(port_id, {})
            
            voltage_mv = int(cache.get("voltage", 0) * 1000)
            current_ma = int(cache.get("current", 0) * 1000)
            power_w = cache.get("power", 0)
            
            # 解析 PD 数据
            pd_data = {}
            if "pd_raw" in cache:
                pd_data = parse_port_pd_status_response(cache["pd_raw"])
            
            # 提取信息
            cable_pid = None
            if 'cable' in pd_data:
                cable_pid = pd_data['cable'].get('pid')
            
            battery_info = pd_data.get('battery', {})
            
            port_data = {
                "state": cache.get("state", 0),
                "protocol": cache.get("protocol", 0),
                "current": current_ma,
                "voltage": voltage_mv,
                "power": round(power_w, 2),
                "cablePid": cable_pid,
                "manufacturerVid": None, 
                "manufacturerPid": None,
                "batteryVid": battery_info.get('vid'),
                "batteryLastFullCapacity": int(battery_info.get('last_full_capacity', 0) * 100),
                "batteryPresentCapacity": int(battery_info.get('present_capacity', 0) * 100),
                "batteryDesignCapacity": int(battery_info.get('design_capacity', 0) * 100),
            }
            
            # 尝试解析制造商信息
            if "pd_raw" in cache and len(cache["pd_raw"]) >= 24:
                try:
                    port_data["manufacturerVid"] = int.from_bytes(cache["pd_raw"][20:22], 'little')
                    port_data["manufacturerPid"] = int.from_bytes(cache["pd_raw"][22:24], 'little')
                except:
                    pass

            ports.append(port_data)
            
            total_power += power_w
            total_current += current_ma
            max_voltage = max(max_voltage, voltage_mv)
            
            if current_ma > 0:
                active_ports += 1
        
        # 获取 BLE RSSI
        wifi_signal = -100
        try:
            if ble_manager and ble_manager.device and hasattr(ble_manager.device, 'rssi'):
                wifi_signal = ble_manager.device.rssi
        except:
            pass
        
        result = {
            "ports": ports,
            "totalPower": round(total_power, 2),  # W
            "averageVoltage": max_voltage / 1000,  # V
            "totalCurrent": total_current / 1000,  # A
            "activePorts": active_ports,
            "system": {
                "wifiSignal": wifi_signal,
                "freeHeap": 0  # BLE模式下不获取此信息
            },
            "connected": True,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=result)
    
    except Exception as e:
        print(f"[错误] 获取端口状态失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"获取端口状态失败: {str(e)}", "connected": ble_manager.connected if ble_manager else False}
        )


async def get_port_pd_status_internal(port_id: int) -> Dict[str, Any]:
    """内部函数：获取端口PD状态"""
    result = {}
    try:
        response = await ble_manager.execute(ServiceCommand.GET_PORT_PD_STATUS, bytes([port_id]))
        if response and response.payload:
            pd_data = parse_port_pd_status_response(response.payload)
            
            # 提取关键信息
            if 'cable' in pd_data:
                result["cable_pid"] = pd_data['cable'].get('pid')
            if 'battery' in pd_data:
                result["battery_vid"] = pd_data['battery'].get('vid')
                # 容量单位转换：0.1 WH -> mWh (乘以 100)
                result["battery_design_capacity"] = int(pd_data['battery'].get('design_capacity', 0) * 100)
                result["battery_last_full_capacity"] = int(pd_data['battery'].get('last_full_capacity', 0) * 100)
                result["battery_present_capacity"] = int(pd_data['battery'].get('present_capacity', 0) * 100)
            
            # 制造商信息（从响应中解析）
            if len(response.payload) >= 24:
                manufacturer_vid = int.from_bytes(response.payload[20:22], 'little')
                manufacturer_pid = int.from_bytes(response.payload[22:24], 'little')
                result["manufacturer_vid"] = f"0x{manufacturer_vid:04X}"
                result["manufacturer_pid"] = f"0x{manufacturer_pid:04X}"
    except Exception as e:
        pass  # PD状态获取失败不影响主要功能
    
    return result



async def perform_connection(address: Optional[str] = None):
    """执行连接逻辑（供 API 和 WebSocket 复用）"""
    if not ble_manager:
        return {"error": "BLE管理器未初始化", "connected": False}
    
    try:
        print(f"[连接] 请求连接: {address if address else '自动选择'}")
        success = await ble_manager.connect(address)
        
        if success:
            # 获取Token
            try:
                token = await ble_manager.ensure_token()
                print(f"[连接] Token获取成功: {token}")
            except Exception as e:
                print(f"[警告] Token获取失败: {e}")
            
            return {"success": True, "message": "连接成功", "connected": True}
        else:
            return {"error": "连接失败", "connected": False}
            
    except Exception as e:
        print(f"[错误] 连接异常: {e}")
        return {"error": str(e), "connected": False}


@app.post("/api/scan")
async def scan_devices_endpoint():
    """扫描BLE设备"""
    if not ble_manager:
        return JSONResponse(status_code=500, content={"error": "BLE管理器未初始化"})
    
    try:
        devices = await ble_manager.scan_devices(timeout=5.0)
        # 转换为 JSON 可序列化格式
        result = [
            {"name": d.name, "address": d.address, "rssi": d.rssi} for d in devices
        ]
        return JSONResponse(content={"devices": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/connect")
async def connect_device_endpoint(data: Optional[ConnectRequest] = None):
    """连接BLE设备"""
    address = data.address if data else None
    result = await perform_connection(address)
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(status_code=400, content=result)

    
    try:
        # 扫描设备
        print("\n[扫描] 正在扫描BLE设备...")
        devices = await ble_manager.scan_devices()
        
        if not devices:
            return JSONResponse(
                status_code=404,
                content={"error": "未找到BLE设备", "connected": False}
            )
        
        # 找到第一个CP02设备
        device = None
        for dev in devices:
            if dev.name and dev.name.startswith("CP02-"):
                device = dev
                break
        
        if not device:
            return JSONResponse(
                status_code=404,
                content={"error": "未找到CP02设备", "connected": False}
            )
        
        print(f"[扫描] 找到设备: {device.name} ({device.address}) RSSI: {device.rssi}")
        
        # 连接设备
        print(f"[连接] 正在连接 {device.name}...")
        success = await ble_manager.connect(device.address)
        
        if success:
            # 获取Token（先尝试从存储加载，失败则暴力破解）
            token = await ble_manager.ensure_token()
            
            print(f"[连接] BLE设备已连接")
            print(f"[Token] 当前Token: 0x{token:02X}" if token else "[Token] Token获取失败")
            
            await broadcast_status()
            
            return JSONResponse(
                content={
                    "success": True,
                    "device": device.name,
                    "address": device.address,
                    "token": token,
                    "connected": True
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "连接失败", "connected": False}
            )
    
    except Exception as e:
        print(f"[错误] 连接设备失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"连接失败: {str(e)}", "connected": ble_manager.connected if ble_manager else False}
        )



@app.post("/api/disconnect")
async def disconnect_device():
    """断开BLE连接"""
    if not ble_manager:
        return JSONResponse(
            status_code=500,
            content={"error": "BLE管理器未初始化", "connected": False}
        )
    
    try:
        success = await ble_manager.disconnect()
        if success:
            return JSONResponse(content={"success": True, "message": "已断开连接", "connected": False})
        else:
            return JSONResponse(content={"success": False, "message": "断开连接失败", "connected": ble_manager.connected})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "connected": False}
        )
    
    try:
        await ble_manager.disconnect()
        await broadcast_status()
        return JSONResponse(
            content={"success": True, "connected": False}
        )
    
    except Exception as e:
        print(f"[错误] 断开设备失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"断开失败: {str(e)}", "connected": ble_manager.connected if ble_manager else False}
        )


@app.get("/api/status")
async def get_status():
    """获取BLE连接状态"""
    if not ble_manager:
        return JSONResponse(
            content={"connected": False, "device": None, "token": None}
        )
    
    return JSONResponse(
        content={
            "connected": ble_manager.connected,
            "device": ble_manager.device.name if ble_manager.device else None,
            "address": ble_manager.device.address if ble_manager.device else None,
            "token": ble_manager.token,
            "auto_refresh": ble_manager.token_manager.auto_refresh,
            "auto_reconnect": ble_manager._auto_reconnect_enabled,
        }
    )


@app.get("/api/device-info")
async def get_device_info():
    """获取设备信息"""
    if not ble_manager or not ble_manager.connected:
        return JSONResponse(
            status_code=503,
            content={"error": "BLE设备未连接"}
        )
    
    try:
        info = await ble_manager.get_device_info()
        return JSONResponse(content={"success": True, "data": info})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/port/{port_id}/power")
async def set_port_power(port_id: int, enable: bool = True):
    """控制端口开关"""
    if not ble_manager or not ble_manager.connected:
        return JSONResponse(
            status_code=503,
            content={"error": "BLE设备未连接"}
        )
    
    try:
        success = await ble_manager.set_port_power(port_id, enable)
        action = "打开" if enable else "关闭"
        if success:
            return JSONResponse(content={"success": True, "message": f"端口{port_id}已{action}"})
        else:
            return JSONResponse(
                status_code=500,
                content={"error": f"端口{port_id}{action}失败"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/port/{port_id}/on")
async def turn_on_port(port_id: int):
    """打开端口"""
    return await set_port_power(port_id, True)


@app.get("/api/port/{port_id}/off")
async def turn_off_port(port_id: int):
    """关闭端口"""
    return await set_port_power(port_id, False)


@app.get("/api/scan")
async def scan_devices():
    """扫描BLE设备"""
    if not ble_manager:
        return JSONResponse(
            status_code=500,
            content={"error": "BLE管理器未初始化"}
        )
    
    try:
        devices = await ble_manager.scan_devices()
        return JSONResponse(
            content={
                "success": True,
                "devices": [
                    {"name": d.name, "address": d.address, "rssi": d.rssi}
                    for d in devices
                ]
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/token/bruteforce")
async def bruteforce_token():
    """暴力破解Token"""
    if not ble_manager or not ble_manager.connected:
        return JSONResponse(
            status_code=503,
            content={"error": "BLE设备未连接"}
        )
    
    try:
        token = await ble_manager.bruteforce_token(save_to_storage=True)
        if token is not None:
            return JSONResponse(content={"success": True, "token": token})
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Token暴力破解失败"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/token/set")
async def set_token(token: int):
    """手动设置Token"""
    if not ble_manager:
        return JSONResponse(
            status_code=500,
            content={"error": "BLE管理器未初始化"}
        )
    
    if token < 0 or token > 255:
        return JSONResponse(
            status_code=400,
            content={"error": "Token必须在0-255之间"}
        )
    
    try:
        await ble_manager.manual_set_token(token, save_to_storage=True)
        return JSONResponse(content={"success": True, "token": token})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/display/brightness/{value}")
async def set_brightness(value: int):
    """设置显示亮度"""
    if not ble_manager or not ble_manager.connected:
        return JSONResponse(
            status_code=503,
            content={"error": "BLE设备未连接"}
        )
    
    try:
        success = await ble_manager.set_display_brightness(max(0, min(100, value)))
        return JSONResponse(content={"success": success})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/reboot")
async def reboot_device():
    """重启设备"""
    if not ble_manager or not ble_manager.connected:
        return JSONResponse(
            status_code=503,
            content={"error": "BLE设备未连接"}
        )
    
    try:
        success = await ble_manager.reboot_device()
        return JSONResponse(content={"success": success, "message": "设备重启中..."})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )



# --- Enhanced Action Handlers (Ported from IonBridge Controller) ---

async def check_connected() -> bool:
    """Check if device is connected"""
    if not ble_manager or not ble_manager.connected:
        return False
    return True

async def handle_get_device_model(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_MODEL)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_device_model_response(resp.payload)
    return {"success": True, "data": data}

async def handle_get_device_serial(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_SERIAL_NO)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_device_serial_response(resp.payload)
    return {"success": True, "data": data}

async def handle_get_ap_version(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_AP_VERSION)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    return {"success": True, "data": {"version": version}}

async def handle_get_ble_addr(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_BLE_ADDR)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    return {"success": True, "data": {"ble_addr": resp.payload.hex()}}

async def handle_get_device_uptime(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEVICE_UPTIME)
    if not resp or not resp.payload or len(resp.payload) < 4: return {"success": False, "message": "Failed"}
    data = parse_device_uptime_response(resp.payload)
    return {"success": True, "data": data}

async def handle_get_wifi_status(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_STATUS)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_wifi_status_response(resp.payload)
    return {"success": True, "data": data}

async def handle_scan_wifi(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.SCAN_WIFI)
    if not resp: return {"success": False, "message": "Scan command failed"}
    await asyncio.sleep(3)
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_SCAN_RESULT)
    if not resp or not resp.payload: return {"success": False, "message": "Get scan results failed"}
    
    networks = []
    payload = resp.payload
    if len(payload) > 1:
        count = payload[0]
        offset = 1
        for _ in range(count):
            if offset >= len(payload): break
            ssid_len = payload[offset] if offset < len(payload) else 0
            offset += 1
            if offset + ssid_len > len(payload): break
            ssid = payload[offset:offset + ssid_len].decode('utf-8', errors='replace')
            offset += ssid_len
            rssi = payload[offset] - 256 if offset < len(payload) and payload[offset] > 127 else (payload[offset] if offset < len(payload) else 0)
            offset += 1
            auth = payload[offset] if offset < len(payload) else 0
            offset += 1
            stored = payload[offset] if offset < len(payload) else 0
            offset += 1
            networks.append({'ssid': ssid, 'rssi': rssi, 'auth': auth, 'stored': bool(stored)})
            
    return {"success": True, "data": {"networks": networks}}

async def handle_set_wifi(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    ssid = params.get("ssid", "")
    password = params.get("password", "")
    payload = f"{ssid}\0{password}\0".encode('utf-8')
    resp = await ble_manager.execute(ServiceCommand.SET_WIFI_SSID_AND_PASSWORD, payload)
    return {"success": resp is not None}

async def handle_get_display_settings(params: dict) -> dict:
    settings = {}
    if await check_connected():
        resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_INTENSITY)
        if resp and resp.payload: settings["brightness"] = parse_display_settings_response(resp.payload).get("brightness", 0)
        resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_MODE)
        if resp and resp.payload: settings["mode"] = parse_display_settings_response(resp.payload).get("mode", 0)
        resp = await ble_manager.execute(ServiceCommand.GET_DISPLAY_FLIP)
        if resp and resp.payload: settings["flip"] = parse_display_settings_response(resp.payload).get("flip", 0)
    return {"success": True, "data": settings}

async def handle_set_display_brightness(params: dict) -> dict:
    brightness = params.get("brightness", 100)
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_INTENSITY, bytes([brightness]))
    return {"success": resp is not None}

async def handle_set_display_mode(params: dict) -> dict:
    mode = params.get("mode", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_MODE, bytes([mode]))
    return {"success": resp is not None}

async def handle_flip_display(params: dict) -> dict:
    resp = await ble_manager.execute(ServiceCommand.SET_DISPLAY_FLIP)
    return {"success": resp is not None}

async def handle_get_charging_strategy(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_CHARGING_STRATEGY)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_charging_strategy_extended_response(resp.payload)
    return {"success": True, "data": data}

async def handle_set_charging_strategy(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    strategy = params.get("strategy", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_CHARGING_STRATEGY, bytes([strategy]))
    return {"success": resp is not None}

async def handle_get_port_config(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_port_config_response(resp.payload)
    return {"success": True, "data": data}

async def handle_set_port_config(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_mask = params.get("port_mask", 0xFF)
    protocols = params.get("protocols", {})
    features = encode_protocols(protocols)
    payload = bytes([port_mask]) + features
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
    return {"success": resp is not None}

async def handle_set_port_priority(params: dict) -> dict:
    port_id = params.get("port_id", 0)
    priority = params.get("priority", 0)
    payload = bytes([port_id, priority])
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_PRIORITY, payload)
    return {"success": resp is not None}

async def handle_get_port_pd_status(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_PD_STATUS, bytes([port_id]))
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_port_pd_status_response(resp.payload)
    data["port_id"] = port_id
    return {"success": True, "data": data}

async def handle_get_power_historical_stats(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    offset = params.get("offset", 0)
    payload = bytes([port_id, offset & 0xFF, (offset >> 8) & 0xFF])
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_HISTORICAL_STATS, payload)
    if not resp or not resp.payload: return {"success": False, "message": "Failed"}
    data = parse_power_historical_stats_response(resp.payload)
    return {"success": True, "data": data}

async def handle_get_port_temperature(params: dict) -> dict:
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))
    if not resp or not resp.payload or len(resp.payload) < 4: return {"success": False, "message": "Failed"}
    return {"success": True, "data": {"temperature": resp.payload[3]}}

async def handle_ble_echo_test(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    data = params.get("data", "test").encode('utf-8')
    resp = await ble_manager.execute(ServiceCommand.BLE_ECHO_TEST, data)
    return {"success": True, "data": {"echo": resp.payload.decode('utf-8') if resp and resp.payload else ""}}

async def handle_get_debug_log(params: dict) -> dict:
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_DEBUG_LOG)
    return {"success": True, "data": {"log": resp.payload.decode('utf-8') if resp and resp.payload else ""}}

async def handle_reboot_device(params: dict) -> dict:
    resp = await ble_manager.execute(ServiceCommand.REBOOT_DEVICE)
    return {"success": resp is not None}

async def handle_reset_device(params: dict) -> dict:
    resp = await ble_manager.execute(ServiceCommand.RESET_DEVICE)
    return {"success": resp is not None}

async def handle_get_device_info(params: dict) -> dict:
    # Aggregated info
    return await handle_get_device_model(params) # simplified

# ============ 新增功能: 端口电源控制 ============

async def handle_get_port_priority(params: dict) -> dict:
    """Get port priority"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_PRIORITY)
    if not resp or not resp.payload: return {"success": False, "message": "获取端口优先级失败"}
    priorities = list(resp.payload[:5]) if len(resp.payload) >= 5 else list(resp.payload)
    while len(priorities) < 5: priorities.append(len(priorities))
    return {"success": True, "data": {"priorities": priorities}}

async def handle_get_power_supply_status(params: dict) -> dict:
    """Get power supply status"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_SUPPLY_STATUS)
    if not resp or not resp.payload: return {"success": False, "message": "获取电源供应状态失败"}
    # Parse basic status
    input_voltage = int.from_bytes(resp.payload[0:2], 'little') if len(resp.payload) >= 2 else 0
    input_current = int.from_bytes(resp.payload[2:4], 'little') if len(resp.payload) >= 4 else 0
    return {"success": True, "data": {"input_voltage": input_voltage, "input_current": input_current, "raw_data": resp.payload.hex()}}

async def handle_get_power_statistics(params: dict) -> dict:
    """Get power statistics for a port"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))
    if not resp or not resp.payload: return {"success": False, "message": "获取电源统计失败"}
    # Parse: [fc_protocol, amperage, voltage, temperature]
    fc_protocol = resp.payload[0] if len(resp.payload) > 0 else 0
    amperage = resp.payload[1] if len(resp.payload) > 1 else 0
    voltage = resp.payload[2] if len(resp.payload) > 2 else 0
    temperature = resp.payload[3] if len(resp.payload) > 3 else 0
    return {"success": True, "data": {"port_id": port_id, "fc_protocol": fc_protocol, "amperage": amperage, "voltage": voltage, "temperature": temperature}}

async def handle_get_charging_status(params: dict) -> dict:
    """Get charging status"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_CHARGING_STATUS)
    if not resp or not resp.payload: return {"success": False, "message": "获取充电状态失败"}
    return {"success": True, "data": {"status": resp.payload[0] if resp.payload else 0, "raw_data": resp.payload.hex()}}

async def handle_set_port_power(params: dict) -> dict:
    """Set port power on/off"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    enable = params.get("enable", True)
    service = ServiceCommand.TURN_ON_PORT if enable else ServiceCommand.TURN_OFF_PORT
    resp = await ble_manager.execute(service, bytes([port_id]))
    return {"success": resp is not None}

async def handle_turn_on_port(params: dict) -> dict:
    """Turn on port"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.TURN_ON_PORT, bytes([port_id]))
    return {"success": resp is not None}

async def handle_turn_off_port(params: dict) -> dict:
    """Turn off port"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.TURN_OFF_PORT, bytes([port_id]))
    return {"success": resp is not None}

# ============ 新增功能: 功率配置 ============

async def handle_get_max_power(params: dict) -> dict:
    """Get max power"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_MAX_POWER)
    if not resp or not resp.payload: return {"success": False, "message": "获取最大功率失败"}
    max_power = resp.payload[0] if resp.payload else 0
    return {"success": True, "data": {"max_power": max_power}}

async def handle_set_max_power(params: dict) -> dict:
    """Set max power"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    power = params.get("power", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_MAX_POWER, bytes([int(power)]))
    return {"success": resp is not None}

async def handle_get_port_max_power(params: dict) -> dict:
    """Get port max power"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    resp = await ble_manager.execute(ServiceCommand.GET_PORT_MAX_POWER, bytes([port_id]))
    if not resp or not resp.payload: return {"success": False, "message": "获取端口最大功率失败"}
    max_power = resp.payload[0] if resp.payload else 0
    return {"success": True, "data": {"port_id": port_id, "max_power": max_power}}

async def handle_set_port_max_power(params: dict) -> dict:
    """Set port max power"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    port_id = params.get("port_id", 0)
    max_power = params.get("max_power", 0)
    payload = bytes([port_id, max_power])
    resp = await ble_manager.execute(ServiceCommand.SET_PORT_MAX_POWER, payload)
    return {"success": resp is not None}

# ============ 新增功能: 夜间模式 ============

async def handle_get_night_mode(params: dict) -> dict:
    """Get night mode"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_NIGHT_MODE)
    if not resp or not resp.payload or len(resp.payload) < 5: return {"success": False, "message": "获取夜间模式失败"}
    return {"success": True, "data": {
        "enabled": resp.payload[0] == 1,
        "start_hour": resp.payload[1], "start_minute": resp.payload[2],
        "end_hour": resp.payload[3], "end_minute": resp.payload[4]
    }}

async def handle_set_night_mode(params: dict) -> dict:
    """Set night mode"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    enabled = params.get("enabled", False)
    start_hour = params.get("start_hour", 22)
    start_minute = params.get("start_minute", 0)
    end_hour = params.get("end_hour", 7)
    end_minute = params.get("end_minute", 0)
    payload = bytes([1 if enabled else 0, start_hour, start_minute, end_hour, end_minute])
    resp = await ble_manager.execute(ServiceCommand.SET_NIGHT_MODE, payload)
    return {"success": resp is not None}

# ============ 新增功能: 语言设置 ============

async def handle_get_language(params: dict) -> dict:
    """Get language"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_LANGUAGE)
    if not resp or not resp.payload: return {"success": False, "message": "获取语言设置失败"}
    language = resp.payload[0] if resp.payload else 0
    return {"success": True, "data": {"language": language}}

async def handle_set_language(params: dict) -> dict:
    """Set language"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    language = params.get("language", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_LANGUAGE, bytes([language]))
    return {"success": resp is not None}

# ============ 新增功能: LED模式 ============

async def handle_get_led_mode(params: dict) -> dict:
    """Get LED mode"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_LED_MODE)
    if not resp or not resp.payload: return {"success": False, "message": "获取LED模式失败"}
    mode = resp.payload[0] if resp.payload else 0
    return {"success": True, "data": {"mode": mode}}

async def handle_set_led_mode(params: dict) -> dict:
    """Set LED mode"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    mode = params.get("mode", 0)
    resp = await ble_manager.execute(ServiceCommand.SET_LED_MODE, bytes([mode]))
    return {"success": resp is not None}

# ============ 新增功能: 自动关闭 ============

async def handle_get_auto_off(params: dict) -> dict:
    """Get auto off"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_AUTO_OFF)
    if not resp or not resp.payload or len(resp.payload) < 2: return {"success": False, "message": "获取自动关闭设置失败"}
    enabled = resp.payload[0] == 1
    timeout = resp.payload[1]
    return {"success": True, "data": {"enabled": enabled, "timeout": timeout}}

async def handle_set_auto_off(params: dict) -> dict:
    """Set auto off"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    enabled = params.get("enabled", False)
    timeout = params.get("timeout", 30)
    payload = bytes([1 if enabled else 0, timeout])
    resp = await ble_manager.execute(ServiceCommand.SET_AUTO_OFF, payload)
    return {"success": resp is not None}

# ============ 新增功能: 屏保 ============

async def handle_get_screen_saver(params: dict) -> dict:
    """Get screen saver"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_SCREEN_SAVER)
    if not resp or not resp.payload or len(resp.payload) < 2: return {"success": False, "message": "获取屏保设置失败"}
    enabled = resp.payload[0] == 1
    timeout = resp.payload[1]
    return {"success": True, "data": {"enabled": enabled, "timeout": timeout}}

async def handle_set_screen_saver(params: dict) -> dict:
    """Set screen saver"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    enabled = params.get("enabled", False)
    timeout = params.get("timeout", 60)
    payload = bytes([1 if enabled else 0, timeout])
    resp = await ble_manager.execute(ServiceCommand.SET_SCREEN_SAVER, payload)
    return {"success": resp is not None}

# ============ 新增功能: 温度模式 ============

async def handle_set_temperature_mode(params: dict) -> dict:
    """Set temperature mode"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    mode = params.get("mode", 0)  # 0: Power Priority, 1: Temperature Priority
    resp = await ble_manager.execute(ServiceCommand.SET_TEMPERATURE_MODE, bytes([mode]))
    if resp is not None:
        return {"success": True, "data": {"mode": mode, "mode_name": "功率优先" if mode == 0 else "温度优先"}}
    return {"success": False, "message": "设置温度模式失败"}

# ============ 新增功能: 版本信息 ============

async def handle_get_bp_version(params: dict) -> dict:
    """Get BP (SW3566 MCU) version"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_BP_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3: return {"success": False, "message": "获取BP版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}

async def handle_get_fpga_version(params: dict) -> dict:
    """Get FPGA version"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_FPGA_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3: return {"success": False, "message": "获取FPGA版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}

async def handle_get_zrlib_version(params: dict) -> dict:
    """Get ZRLIB version"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_ZRLIB_VERSION)
    if not resp or not resp.payload or len(resp.payload) < 3: return {"success": False, "message": "获取ZRLIB版本失败"}
    v = resp.payload
    return {"success": True, "data": {"version": f"{v[0]}.{v[1]}.{v[2]}"}}

async def handle_get_mcu_version(params: dict) -> dict:
    """Get MCU version"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_MCU_VERSION)
    if not resp or not resp.payload: return {"success": False, "message": "获取MCU版本失败"}
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    return {"success": True, "data": {"version": version}}

async def handle_get_sw3566_version(params: dict) -> dict:
    """Get SW3566 version"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_SW3566_VERSION)
    if not resp or not resp.payload: return {"success": False, "message": "获取SW3566版本失败"}
    version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
    return {"success": True, "data": {"version": version}}

# ============ 新增功能: 网络测试 ============

async def handle_ping_mqtt(params: dict) -> dict:
    """Ping MQTT telemetry"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.PING_MQTT_TELEMETRY)
    return {"success": resp is not None, "data": {"status": "command_ok" if resp else "command_failed", "note": "此结果仅表示命令执行状态，请检查WiFi状态确认网络连接"}}

async def handle_ping_http(params: dict) -> dict:
    """Ping HTTP"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    url = params.get("url", "")
    if not url: return {"success": False, "message": "请提供HTTP URL参数"}
    resp = await ble_manager.execute(ServiceCommand.PING_HTTP, url.encode('utf-8'), timeout=15.0)
    return {"success": resp is not None, "data": {"status": "command_ok" if resp else "command_failed", "url": url}}

# ============ 新增功能: OTA固件更新 ============

async def handle_wifi_ota(params: dict) -> dict:
    """Start WiFi OTA update"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    url = params.get("url", "")
    if not url: return {"success": False, "message": "请提供OTA URL"}
    resp = await ble_manager.execute(ServiceCommand.PERFORM_WIFI_OTA, url.encode('utf-8'))
    return {"success": resp is not None, "message": "OTA更新已启动" if resp else "OTA启动失败"}

async def handle_get_ota_progress(params: dict) -> dict:
    """Get OTA progress"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_WIFI_OTA_PROGRESS)
    if not resp or not resp.payload: return {"success": False, "message": "获取OTA进度失败"}
    progress = resp.payload[0] if len(resp.payload) > 0 else 0
    return {"success": True, "data": {"progress": progress}}

async def handle_confirm_ota(params: dict) -> dict:
    """Confirm OTA update"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.CONFIRM_OTA)
    return {"success": resp is not None}

# ============ 新增功能: 设备管理 ============

async def handle_associate_device(params: dict) -> dict:
    """Associate device (no token required)"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.ASSOCIATE_DEVICE)
    return {"success": resp is not None}

async def handle_unbind_device(params: dict) -> dict:
    """Unbind device"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.UNBIND_DEVICE)
    return {"success": resp is not None}

async def handle_factory_reset(params: dict) -> dict:
    """Factory reset device"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.FACTORY_RESET)
    return {"success": resp is not None}

async def handle_get_start_charge_timestamp(params: dict) -> dict:
    """Get start charge timestamp"""
    if not await check_connected(): return {"success": False, "message": "Not connected"}
    resp = await ble_manager.execute(ServiceCommand.GET_START_CHARGE_TIMESTAMP)
    if not resp or not resp.payload: return {"success": False, "message": "获取开始充电时间戳失败"}
    # Parse timestamps for each port
    timestamps = []
    for i in range(0, len(resp.payload), 4):
        if i + 4 <= len(resp.payload):
            ts = int.from_bytes(resp.payload[i:i+4], 'little')
            timestamps.append(ts)
    return {"success": True, "data": {"timestamps": timestamps}}

async def handle_get_status(params: dict) -> dict:
    """Get current connection status"""
    return {
        "success": True,
        "data": {
            "connected": ble_manager.connected if ble_manager else False,
            "token": ble_manager.token if ble_manager else None,
            "device": ble_manager.device.name if ble_manager and ble_manager.device else None,
        }
    }

ACTION_HANDLERS = {
    "get_status": handle_get_status,
    "get_device_model": handle_get_device_model,
    "get_device_serial": handle_get_device_serial,
    "get_ap_version": handle_get_ap_version,
    "get_ble_addr": handle_get_ble_addr,
    "get_device_uptime": handle_get_device_uptime,
    "get_device_info": handle_get_device_info,
    "get_wifi_status": handle_get_wifi_status,
    "scan_wifi": handle_scan_wifi,
    "set_wifi": handle_set_wifi,
    "get_display_settings": handle_get_display_settings,
    "set_display_brightness": handle_set_display_brightness,
    "set_display_mode": handle_set_display_mode,
    "flip_display": handle_flip_display,
    "get_charging_strategy": handle_get_charging_strategy,
    "set_charging_strategy": handle_set_charging_strategy,
    "get_port_config": handle_get_port_config,
    "set_port_config": handle_set_port_config,
    "set_port_priority": handle_set_port_priority,
    "get_port_priority": handle_get_port_priority,
    "get_port_pd_status": handle_get_port_pd_status,
    "get_power_historical_stats": handle_get_power_historical_stats,
    "get_port_temperature": handle_get_port_temperature,
    "ble_echo_test": handle_ble_echo_test,
    "get_debug_log": handle_get_debug_log,
    "reboot_device": handle_reboot_device,
    "reset_device": handle_reset_device,
    "get_power_supply_status": handle_get_power_supply_status,
    "get_power_statistics": handle_get_power_statistics,
    "get_charging_status": handle_get_charging_status,
    "set_port_power": handle_set_port_power,
    "turn_on_port": handle_turn_on_port,
    "turn_off_port": handle_turn_off_port,
    "get_max_power": handle_get_max_power,
    "set_max_power": handle_set_max_power,
    "get_port_max_power": handle_get_port_max_power,
    "set_port_max_power": handle_set_port_max_power,
    "get_night_mode": handle_get_night_mode,
    "set_night_mode": handle_set_night_mode,
    "get_language": handle_get_language,
    "set_language": handle_set_language,
    "get_led_mode": handle_get_led_mode,
    "set_led_mode": handle_set_led_mode,
    "get_auto_off": handle_get_auto_off,
    "set_auto_off": handle_set_auto_off,
    "get_screen_saver": handle_get_screen_saver,
    "set_screen_saver": handle_set_screen_saver,
    "set_temperature_mode": handle_set_temperature_mode,
    "get_bp_version": handle_get_bp_version,
    "get_fpga_version": handle_get_fpga_version,
    "get_zrlib_version": handle_get_zrlib_version,
    "get_mcu_version": handle_get_mcu_version,
    "get_sw3566_version": handle_get_sw3566_version,
    "ping_mqtt": handle_ping_mqtt,
    "ping_http": handle_ping_http,
    "wifi_ota": handle_wifi_ota,
    "get_ota_progress": handle_get_ota_progress,
    "confirm_ota": handle_confirm_ota,
    "associate_device": handle_associate_device,
    "unbind_device": handle_unbind_device,
    "factory_reset": handle_factory_reset,
    "get_start_charge_timestamp": handle_get_start_charge_timestamp,
}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点 - 用于实时通信"""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    print(f"[WebSocket] 客户端已连接 (当前连接数: {len(websocket_clients)})")
    
    # 发送当前状态
    await websocket.send_json({
        "type": "status",
        "data": {
            "connected": ble_manager.connected if ble_manager else False,
            "device": ble_manager.device.name if ble_manager and ble_manager.device else None,
            "token": ble_manager.token if ble_manager else None,
        }
    })
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            msg_type = message.get("type")
            action = message.get("action")
            
            if action and action in ACTION_HANDLERS:
                # 处理通用操作
                handler = ACTION_HANDLERS[action]
                params = message.get("params", {})
                
                try:
                    result = await handler(params)
                    await websocket.send_json({
                        "type": "response",
                        "action": action,
                        "success": result.get("success", False),
                        "data": result.get("data", {}),
                        "message": result.get("message", "")
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "response",
                        "action": action,
                        "success": False,
                        "message": str(e)
                    })
            
            elif msg_type == "connect":
                # 连接设备
                address = message.get("address")
                result = await perform_connection(address)
                await websocket.send_json({"type": "connect_result", "data": result})
            
            elif msg_type == "disconnect":
                # 断开设备
                result = await disconnect_device()
                # Handle bytes vs JSON response body
                body = result.body
                if not isinstance(body, bytes):
                    body = bytes(body)
                await websocket.send_json({"type": "disconnect_result", "data": json.loads(body.decode())})
            
            elif msg_type == "get_port_status":
                # 获取端口状态
                result = await get_port_status()
                body = result.body
                if not isinstance(body, bytes):
                    body = bytes(body)
                await websocket.send_json({"type": "port_status", "data": json.loads(body.decode())})
            
            elif msg_type == "ping":
                # 心跳
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "port_power":
                # 端口电源控制
                port_id = message.get("port_id", 0)
                enable = message.get("enable", True)
                if ble_manager and ble_manager.connected:
                    success = await ble_manager.set_port_power(port_id, enable)
                    await websocket.send_json({"type": "port_power_result", "success": success, "port_id": port_id, "enable": enable})
    
    except WebSocketDisconnect:
        print(f"[WebSocket] 客户端断开连接")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
    finally:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)
        print(f"[WebSocket] 客户端已移除 (当前连接数: {len(websocket_clients)})")



# 必须放在最后：挂载静态文件到根目录
# html=True 表示访问 / 时自动服务 index.html
app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("  小电拼充电站监控 - BLE版本")
    print("  启动中...")
    print("=" * 60 + "\n")
    
    # 优化 Uvicorn 配置
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5223,          # 修改端口为 5223
        log_level="info",
        ws_ping_interval=20, # 保持 WebSocket 连接活跃
        ws_ping_timeout=20,
        timeout_keep_alive=30
    )
