#!/usr/bin/env python3
"""
ESP32 BLE Gateway - Backend Server
FastAPI server for multi-gateway management with WebSocket support.

Enhanced Features:
- Static file serving for frontend
- Environment variable configuration
- Gateway timeout detection
- API key authentication
- OTA firmware upload endpoint
"""

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends, Header, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from mqtt_client import MQTTClient, get_mqtt_client
from history_store import HistoryStore, get_history_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============ Configuration ============
class Settings(BaseSettings):
    """Application settings from environment variables."""
    # MQTT Configuration
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "cp02"
    mqtt_keepalive: int = 60  # Keepalive interval in seconds
    
    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 5225
    
    # API Authentication
    api_key: str = ""  # Empty = no auth required
    api_key_header: str = "X-API-Key"
    
    # Gateway Timeout
    gateway_timeout_seconds: int = 30
    
    # OTA Configuration
    ota_upload_dir: str = "./ota_firmware"
    max_firmware_size: int = 4 * 1024 * 1024  # 4MB max
    
    # Frontend path
    frontend_path: str = "../frontend"
    
    class Config:
        env_prefix = "BLE_GW_"
        env_file = ".env"


settings = Settings()

# Ensure OTA directory exists
Path(settings.ota_upload_dir).mkdir(parents=True, exist_ok=True)


# ============ API Key Authentication ============
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
    """Verify API key if authentication is enabled."""
    if not settings.api_key:
        return True  # No auth required
    
    if api_key and secrets.compare_digest(api_key, settings.api_key):
        return True
    
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"}
    )


# ============ Request Models ============
class CommandRequest(BaseModel):
    """Command request model."""
    command: str
    params: Optional[Dict[str, Any]] = None


class PortControlRequest(BaseModel):
    """Port control request model."""
    port_id: int
    enable: bool = True


class BrightnessRequest(BaseModel):
    """Brightness control request model."""
    brightness: int


class OTAUpdateRequest(BaseModel):
    """OTA update request model."""
    gateway_id: str
    firmware_url: Optional[str] = None


# ============ Global State ============
mqtt_client: Optional[MQTTClient] = None
mqtt_task: Optional[asyncio.Task] = None
timeout_check_task: Optional[asyncio.Task] = None
websocket_clients: List[WebSocket] = []
ota_firmware_files: Dict[str, Dict[str, Any]] = {}
history_store: Optional[HistoryStore] = None


# ============ Gateway Timeout Detection ============
async def gateway_timeout_checker():
    """Background task to check for gateway timeouts."""
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        
        if not mqtt_client:
            continue
        
        now = datetime.now()
        timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
        
        for gateway_id, gateway in mqtt_client.data_store.get_all_gateways().items():
            if gateway.connected:
                time_since_heartbeat = now - gateway.last_heartbeat
                if time_since_heartbeat > timeout_threshold:
                    logger.warning(f"Gateway {gateway_id} timeout - no heartbeat for {time_since_heartbeat.total_seconds():.0f}s")
                    gateway.connected = False
                    # Notify WebSocket clients
                    await broadcast_update(gateway_id, "timeout", {
                        "gateway_id": gateway_id,
                        "connected": False,
                        "reason": "heartbeat_timeout",
                        "last_heartbeat": gateway.last_heartbeat.isoformat()
                    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_client, mqtt_task, timeout_check_task, history_store

    logger.info("=" * 60)
    logger.info("  ESP32 BLE Gateway - Backend Server (Enhanced)")
    logger.info(f"  Port: {settings.server_port}")
    logger.info(f"  MQTT: {settings.mqtt_host}:{settings.mqtt_port}")
    logger.info(f"  API Auth: {'Enabled' if settings.api_key else 'Disabled'}")
    logger.info(f"  Gateway Timeout: {settings.gateway_timeout_seconds}s")
    logger.info("=" * 60)

    history_store = get_history_store()
    await history_store.start_cleanup_task()
    logger.info("History store initialized")

    mqtt_client = MQTTClient(
        broker_host=settings.mqtt_host,
        broker_port=settings.mqtt_port,
        username=settings.mqtt_user if settings.mqtt_user else None,
        password=settings.mqtt_password if settings.mqtt_password else None,
        topic_prefix=settings.mqtt_topic_prefix,
        keepalive=settings.mqtt_keepalive
    )

    mqtt_client.data_store.subscribe(on_gateway_update)
    mqtt_task = asyncio.create_task(mqtt_client.start())
    timeout_check_task = asyncio.create_task(gateway_timeout_checker())
    logger.info("MQTT client and timeout checker started")

    yield

    logger.info("Shutting down...")
    if history_store:
        await history_store.stop()
    if mqtt_client:
        await mqtt_client.stop()
    if mqtt_task:
        mqtt_task.cancel()
        try:
            await mqtt_task
        except asyncio.CancelledError:
            pass
    if timeout_check_task:
        timeout_check_task.cancel()
        try:
            await timeout_check_task
        except asyncio.CancelledError:
            pass

    for ws in websocket_clients:
        try:
            await ws.close()
        except:
            pass
    websocket_clients.clear()
    logger.info("Server stopped")


app = FastAPI(
    title="ESP32 BLE Gateway Backend",
    description="Multi-gateway management for CP02 charging stations with enhanced features",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def on_gateway_update(gateway_id: str, event_type: str, data: Any) -> None:
    asyncio.create_task(broadcast_update(gateway_id, event_type, data))
    
    if history_store and event_type == "ports":
        ports = data.get("ports", {})
        if isinstance(ports, dict):
            port_list = list(ports.values())
        else:
            port_list = ports
        history_store.record_port_data(gateway_id, port_list)
    
    if history_store and event_type in ("status", "timeout"):
        history_store.record_event(gateway_id, event_type, data)


async def broadcast_update(gateway_id: str, event_type: str, data: Any) -> None:
    """Broadcast update to all WebSocket clients."""
    message = {
        "type": event_type,
        "gateway_id": gateway_id,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }

    disconnected = []
    for ws in websocket_clients:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in websocket_clients:
            websocket_clients.remove(ws)


# ============ Static File Serving ============
# Frontend directory path
frontend_dir = Path(__file__).parent / settings.frontend_path

if not frontend_dir.exists():
    logger.warning(f"Frontend directory not found: {frontend_dir}")


# ============ Health & Status Endpoints ============
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "mqtt_connected": mqtt_client._client is not None if mqtt_client else False,
        "gateway_count": len(mqtt_client.data_store.get_all_gateways()) if mqtt_client else 0,
        "auth_enabled": bool(settings.api_key),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config")
async def get_config():
    """Get current server configuration (non-sensitive)."""
    return {
        "mqtt_host": settings.mqtt_host,
        "mqtt_port": settings.mqtt_port,
        "gateway_timeout_seconds": settings.gateway_timeout_seconds,
        "auth_enabled": bool(settings.api_key),
        "max_firmware_size": settings.max_firmware_size,
        "version": "2.0.0"
    }


# ============ Gateway Endpoints ============
@app.get("/api/gateways")
async def list_gateways(_: bool = Depends(verify_api_key)):
    """List all connected gateways with online status."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    gateways = mqtt_client.data_store.get_gateway_list()
    
    # Add online status based on timeout
    now = datetime.now()
    timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
    
    for gw in gateways:
        last_heartbeat = datetime.fromisoformat(gw["last_heartbeat"])
        gw["online"] = (now - last_heartbeat) < timeout_threshold
        gw["seconds_since_heartbeat"] = (now - last_heartbeat).total_seconds()
    
    return JSONResponse(content={"gateways": gateways})


@app.get("/api/gateway/{gateway_id}")
async def get_gateway(gateway_id: str, _: bool = Depends(verify_api_key)):
    """Get detailed info for a specific gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    gateway = mqtt_client.data_store.get_gateway(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway {gateway_id} not found")

    data = gateway.to_dict()
    
    # Add online status
    now = datetime.now()
    timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
    data["online"] = (now - gateway.last_heartbeat) < timeout_threshold
    data["seconds_since_heartbeat"] = (now - gateway.last_heartbeat).total_seconds()
    
    return JSONResponse(content=data)


@app.get("/api/gateway/{gateway_id}/ports")
async def get_gateway_ports(gateway_id: str, _: bool = Depends(verify_api_key)):
    """Get port status for a specific gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    gateway = mqtt_client.data_store.get_gateway(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail=f"Gateway {gateway_id} not found")

    ports = [p.to_dict() for p in gateway.ports.values()]
    
    # Add online status
    now = datetime.now()
    timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
    online = (now - gateway.last_heartbeat) < timeout_threshold
    
    return JSONResponse(content={
        "gateway_id": gateway_id,
        "ports": ports,
        "total_power": gateway.total_power,
        "active_ports": gateway.active_ports,
        "connected": gateway.connected,
        "online": online
    })


@app.get("/api/port-status")
async def get_port_status(
    gateway_id: Optional[str] = Query(None),
    _: bool = Depends(verify_api_key)
):
    """
    Get port status (compatible with original BLE charging station API).
    If gateway_id is not provided, returns data from the first available gateway.
    """
    if not mqtt_client:
        return JSONResponse(content={
            "ports": [
                {"state": 0, "protocol": 0, "current": 0, "voltage": 0, "power": 0}
                for _ in range(5)
            ],
            "totalPower": 0,
            "averageVoltage": 0,
            "totalCurrent": 0,
            "activePorts": 0,
            "connected": False,
            "online": False,
            "message": "MQTT client not initialized",
            "timestamp": datetime.now().isoformat()
        })

    if gateway_id:
        gateway = mqtt_client.data_store.get_gateway(gateway_id)
    else:
        gateways = mqtt_client.data_store.get_all_gateways()
        gateway = next(iter(gateways.values()), None) if gateways else None

    if not gateway:
        return JSONResponse(content={
            "ports": [
                {"state": 0, "protocol": 0, "current": 0, "voltage": 0, "power": 0}
                for _ in range(5)
            ],
            "totalPower": 0,
            "averageVoltage": 0,
            "totalCurrent": 0,
            "activePorts": 0,
            "connected": False,
            "online": False,
            "message": "No gateway connected",
            "timestamp": datetime.now().isoformat()
        })

    ports = []
    total_current = 0
    max_voltage = 0

    for i in range(5):
        port = gateway.ports.get(i)
        if port:
            ports.append({
                "state": port.state,
                "protocol": port.protocol,
                "current": port.current_ma,
                "voltage": port.voltage_mv,
                "power": port.power_w,
                "port_id": port.port_id,
                "temperature": port.temperature,
                "cablePid": None,
                "manufacturerVid": None,
                "manufacturerPid": None,
                "batteryVid": None,
                "batteryLastFullCapacity": 0,
                "batteryPresentCapacity": 0,
                "batteryDesignCapacity": 0,
            })
            total_current += port.current_ma
            max_voltage = max(max_voltage, port.voltage_mv)
        else:
            ports.append({
                "state": 0, "protocol": 0, "current": 0, "voltage": 0, "power": 0,
                "port_id": i, "temperature": 0,
                "cablePid": None, "manufacturerVid": None, "manufacturerPid": None,
                "batteryVid": None, "batteryLastFullCapacity": 0,
                "batteryPresentCapacity": 0, "batteryDesignCapacity": 0,
            })

    # Calculate online status
    now = datetime.now()
    timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
    online = (now - gateway.last_heartbeat) < timeout_threshold

    return JSONResponse(content={
        "ports": ports,
        "totalPower": gateway.total_power,
        "averageVoltage": max_voltage / 1000 if max_voltage else 0,
        "totalCurrent": total_current / 1000 if total_current else 0,
        "activePorts": gateway.active_ports,
        "system": {
            "wifiSignal": gateway.rssi,
            "freeHeap": 0
        },
        "connected": gateway.connected,
        "online": online,
        "gateway_id": gateway.gateway_id,
        "timestamp": datetime.now().isoformat()
    })


# ============ Command Endpoints ============
@app.post("/api/gateway/{gateway_id}/cmd")
async def send_command(
    gateway_id: str,
    request: CommandRequest,
    _: bool = Depends(verify_api_key)
):
    """Send command to a specific gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        response = await mqtt_client.send_command(
            gateway_id,
            request.command,
            request.params
        )
        if response:
            return JSONResponse(content={"success": True, "response": response})
        else:
            return JSONResponse(content={"success": False, "error": "Command timeout"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gateway/{gateway_id}/port/{port_id}/power")
async def set_port_power(
    gateway_id: str,
    port_id: int,
    enable: bool = True,
    _: bool = Depends(verify_api_key)
):
    """Control port power on a specific gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        if enable:
            response = await mqtt_client.turn_on_port(gateway_id, port_id)
        else:
            response = await mqtt_client.turn_off_port(gateway_id, port_id)

        if response:
            return JSONResponse(content={"success": True, "message": f"Port {port_id} {'enabled' if enable else 'disabled'}"})
        else:
            return JSONResponse(content={"success": False, "error": "Command timeout"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gateway/{gateway_id}/port/{port_id}/on")
async def turn_on_port(gateway_id: str, port_id: int, _: bool = Depends(verify_api_key)):
    """Turn on a port."""
    return await set_port_power(gateway_id, port_id, True)


@app.get("/api/gateway/{gateway_id}/port/{port_id}/off")
async def turn_off_port(gateway_id: str, port_id: int, _: bool = Depends(verify_api_key)):
    """Turn off a port."""
    return await set_port_power(gateway_id, port_id, False)


@app.get("/api/port/{port_id}/on")
async def turn_on_port_compat(port_id: int, _: bool = Depends(verify_api_key)):
    """Turn on a port (backward compatible - uses first gateway)."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    gateways = mqtt_client.data_store.get_all_gateways()
    if not gateways:
        raise HTTPException(status_code=404, detail="No gateway connected")

    gateway_id = next(iter(gateways.keys()))
    return await set_port_power(gateway_id, port_id, True)


@app.get("/api/port/{port_id}/off")
async def turn_off_port_compat(port_id: int, _: bool = Depends(verify_api_key)):
    """Turn off a port (backward compatible - uses first gateway)."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    gateways = mqtt_client.data_store.get_all_gateways()
    if not gateways:
        raise HTTPException(status_code=404, detail="No gateway connected")

    gateway_id = next(iter(gateways.keys()))
    return await set_port_power(gateway_id, port_id, False)


@app.get("/api/gateway/{gateway_id}/display/brightness/{value}")
async def set_brightness(gateway_id: str, value: int, _: bool = Depends(verify_api_key)):
    """Set display brightness on a gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        response = await mqtt_client.set_brightness(gateway_id, max(0, min(100, value)))
        if response:
            return JSONResponse(content={"success": True})
        else:
            return JSONResponse(content={"success": False, "error": "Command timeout"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gateway/{gateway_id}/reboot")
async def reboot_device(gateway_id: str, _: bool = Depends(verify_api_key)):
    """Reboot device connected to a gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")

    try:
        response = await mqtt_client.reboot_device(gateway_id)
        return JSONResponse(content={"success": True, "message": "Reboot command sent"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ OTA Firmware Endpoints ============
@app.post("/api/ota/upload")
async def upload_firmware(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key)
):
    """Upload firmware file for OTA updates."""
    if not file.filename or not file.filename.endswith(".bin"):
        raise HTTPException(status_code=400, detail="Only .bin files are allowed")
    
    # Check file size
    contents = await file.read()
    if len(contents) > settings.max_firmware_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_firmware_size / 1024 / 1024:.1f}MB"
        )
    
    # Save file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"firmware_{timestamp}_{file.filename}"
    filepath = Path(settings.ota_upload_dir) / safe_filename
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    # Store metadata
    firmware_id = timestamp
    ota_firmware_files[firmware_id] = {
        "id": firmware_id,
        "filename": safe_filename,
        "original_name": file.filename,
        "size": len(contents),
        "uploaded_at": datetime.now().isoformat(),
        "path": str(filepath)
    }
    
    logger.info(f"Firmware uploaded: {safe_filename} ({len(contents)} bytes)")
    
    return JSONResponse(content={
        "success": True,
        "firmware_id": firmware_id,
        "filename": safe_filename,
        "size": len(contents),
        "download_url": f"/api/ota/firmware/{firmware_id}"
    })


@app.get("/api/ota/firmware")
async def list_firmware(_: bool = Depends(verify_api_key)):
    """List all uploaded firmware files."""
    return JSONResponse(content={
        "firmware": list(ota_firmware_files.values())
    })


@app.get("/api/ota/firmware/{firmware_id}")
async def download_firmware(firmware_id: str):
    """Download firmware file (no auth for ESP32 access)."""
    if firmware_id not in ota_firmware_files:
        raise HTTPException(status_code=404, detail="Firmware not found")
    
    firmware = ota_firmware_files[firmware_id]
    filepath = Path(firmware["path"])
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Firmware file not found on disk")
    
    return FileResponse(
        str(filepath),
        media_type="application/octet-stream",
        filename=firmware["original_name"]
    )


@app.post("/api/gateway/{gateway_id}/ota")
async def trigger_ota_update(
    gateway_id: str,
    request: OTAUpdateRequest,
    _: bool = Depends(verify_api_key)
):
    """Trigger OTA update on a gateway."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")
    
    try:
        # Send OTA command via MQTT
        params = {}
        if request.firmware_url:
            params["url"] = request.firmware_url
        
        response = await mqtt_client.send_command(
            gateway_id,
            "ota_update",
            params
        )
        
        if response:
            return JSONResponse(content={"success": True, "response": response})
        else:
            return JSONResponse(content={"success": False, "error": "Command timeout"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/ota/firmware/{firmware_id}")
async def delete_firmware(firmware_id: str, _: bool = Depends(verify_api_key)):
    """Delete uploaded firmware file."""
    if firmware_id not in ota_firmware_files:
        raise HTTPException(status_code=404, detail="Firmware not found")
    
    firmware = ota_firmware_files[firmware_id]
    filepath = Path(firmware["path"])
    
    if filepath.exists():
        filepath.unlink()
    
    del ota_firmware_files[firmware_id]
    
    return JSONResponse(content={"success": True, "message": "Firmware deleted"})


# ============ History Endpoints ============
@app.get("/api/gateway/{gateway_id}/history")
async def get_gateway_history(
    gateway_id: str,
    port_id: Optional[int] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(500, ge=1, le=5000),
    _: bool = Depends(verify_api_key)
):
    if not history_store:
        raise HTTPException(status_code=503, detail="History store not initialized")
    
    data = history_store.get_port_history(gateway_id, port_id, hours, limit)
    return JSONResponse(content={"history": data, "count": len(data)})


@app.get("/api/gateway/{gateway_id}/stats")
async def get_gateway_stats(
    gateway_id: str,
    hours: int = Query(24, ge=1, le=168),
    _: bool = Depends(verify_api_key)
):
    if not history_store:
        raise HTTPException(status_code=503, detail="History store not initialized")
    
    stats = history_store.get_power_stats(gateway_id, hours)
    return JSONResponse(content=stats)


@app.get("/api/gateway/{gateway_id}/hourly")
async def get_hourly_power(
    gateway_id: str,
    hours: int = Query(24, ge=1, le=168),
    _: bool = Depends(verify_api_key)
):
    if not history_store:
        raise HTTPException(status_code=503, detail="History store not initialized")
    
    data = history_store.get_hourly_power(gateway_id, hours)
    return JSONResponse(content={"hourly": data})


@app.get("/api/gateway/{gateway_id}/events")
async def get_gateway_events(
    gateway_id: str,
    event_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
    _: bool = Depends(verify_api_key)
):
    if not history_store:
        raise HTTPException(status_code=503, detail="History store not initialized")
    
    events = history_store.get_events(gateway_id, event_type, hours, limit)
    return JSONResponse(content={"events": events, "count": len(events)})


# ============ Status Endpoint ============
@app.get("/api/status")
async def get_status(_: bool = Depends(verify_api_key)):
    """Get overall system status."""
    if not mqtt_client:
        return JSONResponse(content={
            "mqtt_connected": False,
            "gateway_count": 0,
            "gateways": [],
            "online_count": 0,
            "auth_enabled": bool(settings.api_key)
        })

    gateways = mqtt_client.data_store.get_gateway_list()
    
    # Count online gateways
    now = datetime.now()
    timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
    online_count = 0
    
    for gw in gateways:
        last_heartbeat = datetime.fromisoformat(gw["last_heartbeat"])
        if (now - last_heartbeat) < timeout_threshold:
            online_count += 1
            gw["online"] = True
        else:
            gw["online"] = False
    
    return JSONResponse(content={
        "mqtt_connected": mqtt_client._client is not None,
        "gateway_count": len(gateways),
        "online_count": online_count,
        "gateways": gateways,
        "auth_enabled": bool(settings.api_key),
        "gateway_timeout_seconds": settings.gateway_timeout_seconds
    })


# ============ WebSocket Endpoint ============
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(websocket_clients)}")

    try:
        if mqtt_client:
            gateways = mqtt_client.data_store.get_all_gateways()
            
            # Add online status to each gateway
            now = datetime.now()
            timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
            
            gateway_data = []
            for gw in gateways.values():
                data = gw.to_dict()
                data["online"] = (now - gw.last_heartbeat) < timeout_threshold
                gateway_data.append(data)
            
            await websocket.send_json({
                "type": "init",
                "data": {
                    "gateway_count": len(gateways),
                    "gateways": gateway_data,
                    "auth_enabled": bool(settings.api_key)
                },
                "timestamp": datetime.now().isoformat()
            })

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "subscribe":
                    gateway_id = message.get("gateway_id")
                    if gateway_id and mqtt_client:
                        gateway = mqtt_client.data_store.get_gateway(gateway_id)
                        if gateway:
                            data = gateway.to_dict()
                            now = datetime.now()
                            timeout_threshold = timedelta(seconds=settings.gateway_timeout_seconds)
                            data["online"] = (now - gateway.last_heartbeat) < timeout_threshold
                            
                            await websocket.send_json({
                                "type": "gateway_data",
                                "gateway_id": gateway_id,
                                "data": data,
                                "timestamp": datetime.now().isoformat()
                            })

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(websocket_clients)}")


# ============ Static File Routes (MUST be last!) ============
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main index.html."""
    if frontend_dir.exists():
        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
    return HTMLResponse(content="""
        <html><body>
        <h1>ESP32 BLE Gateway Backend</h1>
        <p>Frontend not found. Please ensure frontend files are in the correct location.</p>
        <p>API Documentation: <a href="/docs">/docs</a></p>
        </body></html>
    """)


@app.get("/{file_path:path}")
async def serve_static(file_path: str):
    """Catch-all route for static files - MUST be defined last."""
    if not frontend_dir.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    
    full_path = frontend_dir / file_path
    if full_path.exists() and full_path.is_file():
        return FileResponse(str(full_path))
    
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_level="info"
    )
