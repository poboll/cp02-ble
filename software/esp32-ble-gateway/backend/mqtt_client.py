#!/usr/bin/env python3
"""
ESP32 BLE Gateway - MQTT Client
Subscribes to gateway topics and stores data in memory.
Forwards commands to specific gateways via MQTT.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import defaultdict

import aiomqtt

logger = logging.getLogger(__name__)


@dataclass
class PortData:
    """Port data from gateway."""
    port_id: int = 0
    state: int = 0
    protocol: int = 0
    voltage_mv: int = 0
    current_ma: int = 0
    power_w: float = 0.0
    temperature: int = 0
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port_id": self.port_id,
            "state": self.state,
            "protocol": self.protocol,
            "voltage": self.voltage_mv,
            "current": self.current_ma,
            "power": self.power_w,
            "temperature": self.temperature,
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class GatewayInfo:
    """Gateway information and status."""
    gateway_id: str
    device_name: Optional[str] = None
    device_address: Optional[str] = None
    firmware_version: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    uptime_seconds: int = 0
    rssi: int = 0
    connected: bool = False
    last_heartbeat: datetime = field(default_factory=datetime.now)
    ports: Dict[int, PortData] = field(default_factory=dict)
    total_power: float = 0.0
    active_ports: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_id": self.gateway_id,
            "device_name": self.device_name,
            "device_address": self.device_address,
            "firmware_version": self.firmware_version,
            "model": self.model,
            "serial": self.serial,
            "uptime_seconds": self.uptime_seconds,
            "rssi": self.rssi,
            "connected": self.connected,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "ports": {k: v.to_dict() for k, v in self.ports.items()},
            "total_power": self.total_power,
            "active_ports": self.active_ports
        }


class GatewayDataStore:
    """In-memory storage for gateway data."""

    def __init__(self):
        self._gateways: Dict[str, GatewayInfo] = {}
        self._command_responses: Dict[str, asyncio.Future] = {}
        self._subscribers: List[Callable[[str, str, Any], None]] = []

    def get_gateway(self, gateway_id: str) -> Optional[GatewayInfo]:
        """Get gateway info by ID."""
        return self._gateways.get(gateway_id)

    def get_all_gateways(self) -> Dict[str, GatewayInfo]:
        """Get all gateways."""
        return self._gateways.copy()

    def get_gateway_list(self) -> List[Dict[str, Any]]:
        """Get list of all gateways with basic info."""
        return [
            {
                "gateway_id": gw.gateway_id,
                "device_name": gw.device_name,
                "connected": gw.connected,
                "total_power": gw.total_power,
                "active_ports": gw.active_ports,
                "last_heartbeat": gw.last_heartbeat.isoformat()
            }
            for gw in self._gateways.values()
        ]

    def update_ports(self, gateway_id: str, ports_data: List[Dict[str, Any]]) -> None:
        """Update port data for a gateway."""
        if gateway_id not in self._gateways:
            self._gateways[gateway_id] = GatewayInfo(gateway_id=gateway_id)

        gw = self._gateways[gateway_id]
        total_power = 0.0
        active_ports = 0

        for port_data in ports_data:
            port_id = port_data.get("port_id", 0)
            port = PortData(
                port_id=port_id,
                state=port_data.get("state", 0),
                protocol=port_data.get("protocol", 0),
                voltage_mv=port_data.get("voltage", 0),
                current_ma=port_data.get("current", 0),
                power_w=port_data.get("power", 0.0),
                temperature=port_data.get("temperature", 0),
                updated_at=datetime.now()
            )
            gw.ports[port_id] = port
            total_power += port.power_w
            if port.current_ma > 0:
                active_ports += 1

        gw.total_power = round(total_power, 2)
        gw.active_ports = active_ports
        gw.connected = True
        self._notify_subscribers(gateway_id, "ports", gw.to_dict())

    def update_device_info(self, gateway_id: str, info: Dict[str, Any]) -> None:
        """Update device info for a gateway."""
        if gateway_id not in self._gateways:
            self._gateways[gateway_id] = GatewayInfo(gateway_id=gateway_id)

        gw = self._gateways[gateway_id]
        gw.device_name = info.get("device_name", gw.device_name)
        gw.device_address = info.get("device_address", gw.device_address)
        gw.firmware_version = info.get("firmware_version", gw.firmware_version)
        gw.model = info.get("model", gw.model)
        gw.serial = info.get("serial", gw.serial)
        gw.uptime_seconds = info.get("uptime", gw.uptime_seconds)
        gw.connected = True
        self._notify_subscribers(gateway_id, "device_info", gw.to_dict())

    def update_heartbeat(self, gateway_id: str, heartbeat: Dict[str, Any]) -> None:
        """Update heartbeat for a gateway."""
        if gateway_id not in self._gateways:
            self._gateways[gateway_id] = GatewayInfo(gateway_id=gateway_id)

        gw = self._gateways[gateway_id]
        gw.last_heartbeat = datetime.now()
        gw.uptime_seconds = heartbeat.get("uptime", gw.uptime_seconds)
        gw.rssi = heartbeat.get("rssi", gw.rssi)
        gw.connected = heartbeat.get("connected", True)
        self._notify_subscribers(gateway_id, "heartbeat", gw.to_dict())

    def update_status(self, gateway_id: str, status: Dict[str, Any]) -> None:
        """Update connection status for a gateway."""
        if gateway_id not in self._gateways:
            self._gateways[gateway_id] = GatewayInfo(gateway_id=gateway_id)

        gw = self._gateways[gateway_id]
        gw.connected = status.get("connected", False)
        gw.device_name = status.get("device_name", gw.device_name)
        gw.device_address = status.get("device_address", gw.device_address)
        self._notify_subscribers(gateway_id, "status", gw.to_dict())

    def handle_command_response(self, gateway_id: str, response: Dict[str, Any]) -> None:
        """Handle command response from gateway."""
        cmd_id = response.get("cmd_id")
        if cmd_id and cmd_id in self._command_responses:
            future = self._command_responses.pop(cmd_id)
            if not future.done():
                future.set_result(response)
        self._notify_subscribers(gateway_id, "cmd_response", response)

    def register_command(self, cmd_id: str) -> asyncio.Future:
        """Register a command and return a future for the response."""
        future = asyncio.get_event_loop().create_future()
        self._command_responses[cmd_id] = future
        return future

    def subscribe(self, callback: Callable[[str, str, Any], None]) -> None:
        """Subscribe to gateway updates."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, str, Any], None]) -> None:
        """Unsubscribe from gateway updates."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, gateway_id: str, event_type: str, data: Any) -> None:
        """Notify all subscribers of an update."""
        for callback in self._subscribers:
            try:
                callback(gateway_id, event_type, data)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")


class MQTTClient:
    """MQTT client for ESP32 BLE Gateway backend."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        topic_prefix: str = "cp02",
        keepalive: int = 60
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.keepalive = keepalive
        self.data_store = GatewayDataStore()
        self._client: Optional[aiomqtt.Client] = None
        self._running = False
        self._reconnect_interval = 5

    async def start(self) -> None:
        """Start MQTT client and subscribe to topics."""
        self._running = True
        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    username=self.username,
                    password=self.password,
                    keepalive=self.keepalive
                ) as client:
                    self._client = client
                    logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")

                    # Subscribe to all gateway topics
                    await client.subscribe(f"{self.topic_prefix}/+/ports")
                    await client.subscribe(f"{self.topic_prefix}/+/device_info")
                    await client.subscribe(f"{self.topic_prefix}/+/heartbeat")
                    await client.subscribe(f"{self.topic_prefix}/+/status")
                    await client.subscribe(f"{self.topic_prefix}/+/cmd_response")

                    logger.info(f"Subscribed to {self.topic_prefix}/+/* topics")

                    async for message in client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT connection error: {e}")
                if self._running:
                    logger.info(f"Reconnecting in {self._reconnect_interval} seconds...")
                    await asyncio.sleep(self._reconnect_interval)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if self._running:
                    await asyncio.sleep(self._reconnect_interval)

    async def stop(self) -> None:
        """Stop MQTT client."""
        self._running = False
        self._client = None

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Handle incoming MQTT message."""
        try:
            topic = str(message.topic)
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)

            # Parse topic: cp02/{gateway_id}/{type}
            parts = topic.split("/")
            if len(parts) < 3:
                return

            gateway_id = parts[1]
            msg_type = parts[2]

            logger.debug(f"Received {msg_type} from {gateway_id}: {data}")

            if msg_type == "ports":
                self.data_store.update_ports(gateway_id, data.get("ports", []))
            elif msg_type == "device_info":
                self.data_store.update_device_info(gateway_id, data)
            elif msg_type == "heartbeat":
                self.data_store.update_heartbeat(gateway_id, data)
            elif msg_type == "status":
                self.data_store.update_status(gateway_id, data)
            elif msg_type == "cmd_response":
                self.data_store.handle_command_response(gateway_id, data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def send_command(
        self,
        gateway_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """Send command to gateway and wait for response."""
        if not self._client:
            raise RuntimeError("MQTT client not connected")

        import uuid
        cmd_id = str(uuid.uuid4())[:8]

        cmd_payload = {
            "cmd_id": cmd_id,
            "command": command,
            "params": params or {}
        }

        # Register command for response
        future = self.data_store.register_command(cmd_id)

        # Publish command
        topic = f"{self.topic_prefix}/{gateway_id}/cmd"
        await self._client.publish(topic, json.dumps(cmd_payload))
        logger.info(f"Sent command {command} to {gateway_id}")

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Command {command} to {gateway_id} timed out")
            return None

    async def turn_on_port(self, gateway_id: str, port_id: int) -> Optional[Dict[str, Any]]:
        """Turn on a port on the gateway."""
        return await self.send_command(gateway_id, "turn_on_port", {"port_id": port_id})

    async def turn_off_port(self, gateway_id: str, port_id: int) -> Optional[Dict[str, Any]]:
        """Turn off a port on the gateway."""
        return await self.send_command(gateway_id, "turn_off_port", {"port_id": port_id})

    async def set_brightness(self, gateway_id: str, brightness: int) -> Optional[Dict[str, Any]]:
        """Set display brightness on the gateway."""
        return await self.send_command(gateway_id, "set_brightness", {"brightness": brightness})

    async def reboot_device(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """Reboot the device connected to the gateway."""
        return await self.send_command(gateway_id, "reboot")

    async def request_device_info(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """Request device info from the gateway."""
        return await self.send_command(gateway_id, "get_device_info")


# Singleton instance
_mqtt_client: Optional[MQTTClient] = None


def get_mqtt_client() -> MQTTClient:
    """Get or create MQTT client singleton."""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient()
    return _mqtt_client


async def main():
    """Test MQTT client."""
    logging.basicConfig(level=logging.DEBUG)
    client = MQTTClient(broker_host="localhost")
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
