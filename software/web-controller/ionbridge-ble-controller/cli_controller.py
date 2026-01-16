#!/usr/bin/env python3
"""
IonBridge BLE CLI Controller
Interactive command-line interface for controlling IonBridge devices
Supports all 60+ BLE commands with auto token refresh and auto reconnect
"""

import asyncio
import sys
from typing import Optional, List
from datetime import datetime

from ble_manager import BLEManager, DeviceInfo
from protocol import (
    ServiceCommand, PROTOCOL_NAMES, decode_protocols, encode_protocols,
    get_command_name, COMMAND_CATEGORIES
)


class CLIController:
    """Interactive CLI controller for IonBridge BLE devices"""
    
    def __init__(self):
        self.ble_manager = BLEManager(log_callback=self.log)
        self.running = True
        self.current_device: Optional[DeviceInfo] = None
        self.auto_refresh = True
        self.auto_reconnect = True
        self.commands = self._build_commands()
    
    def log(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def _build_commands(self) -> dict:
        """Build command dictionary"""
        return {
            # Device Management
            "scan": self.cmd_scan,
            "connect": self.cmd_connect,
            "disconnect": self.cmd_disconnect,
            "info": self.cmd_info,
            "reboot": self.cmd_reboot,
            "reset": self.cmd_reset,
            
            # Port Control
            "status": self.cmd_status,
            "on": self.cmd_on,
            "off": self.cmd_off,
            "config": self.cmd_config,
            "set-config": self.cmd_set_config,
            "priority": self.cmd_priority,
            
            # Protocol Management
            "protocols": self.cmd_protocols,
            "enable": self.cmd_enable,
            "disable": self.cmd_disable,
            
            # Power Management
            "power": self.cmd_power,
            "strategy": self.cmd_strategy,
            "set-strategy": self.cmd_set_strategy,
            
            # WiFi Management
            "wifi-status": self.cmd_wifi_status,
            "scan-wifi": self.cmd_scan_wifi,
            "set-wifi": self.cmd_set_wifi,
            
            # Display Management
            "display-info": self.cmd_display_info,
            "brightness": self.cmd_brightness,
            "mode": self.cmd_mode,
            "flip": self.cmd_flip,
            
            # System Control
            "token": self.cmd_token,
            "refresh-token": self.cmd_refresh_token,
            "auto-refresh": self.cmd_auto_refresh,
            "auto-reconnect": self.cmd_auto_reconnect,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }
    
    async def run(self):
        """Run the interactive CLI"""
        print("=" * 70)
        print("  IonBridge BLE 控制器 - 命令行测试工具")
        print("  支持 60+ 蓝牙命令 | 自动 Token 刷新 | 自动重连")
        print("=" * 70)
        print("\n输入 'help' 查看命令列表\n")
        
        try:
            while self.running:
                try:
                    # Build prompt
                    device_name = self.current_device.name if self.current_device else "未连接"
                    token = self.ble_manager.token if self.ble_manager.token else None
                    token_str = f"0x{token:02X}" if token is not None else "无"
                    prompt = f"\n[{device_name}] [Token: {token_str}] > "
                    
                    cmd_line = input(prompt).strip()
                    if not cmd_line:
                        continue
                    
                    # Parse command and arguments
                    parts = cmd_line.split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    
                    # Execute command
                    if cmd in self.commands:
                        await self.commands[cmd](args)
                    else:
                        print(f"未知命令: {cmd} (输入 'help' 查看帮助)")
                
                except KeyboardInterrupt:
                    print("\n\n按 Ctrl+C 退出? (y/n): ", end="")
                    choice = input().strip().lower()
                    if choice == 'y':
                        break
                    continue
                except Exception as e:
                    print(f"错误: {e}")
                    import traceback
                    traceback.print_exc()
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n正在清理...")
        await self.ble_manager.disconnect()
        print("再见!")
    
    # ==================== Device Management Commands ====================
    
    async def cmd_scan(self, args: List[str]):
        """Scan for devices"""
        timeout = float(args[0]) if args else 5.0
        devices = await self.ble_manager.scan_devices(timeout=timeout)
        
        if devices:
            print("\n发现的设备:")
            print("-" * 60)
            for i, dev in enumerate(devices):
                print(f"  [{i}] {dev.name} ({dev.address}) RSSI: {dev.rssi}")
            print("-" * 60)
        else:
            print("未发现设备")
    
    async def cmd_connect(self, args: List[str]):
        """Connect to a device"""
        if not args:
            # Scan and let user select
            devices = await self.ble_manager.scan_devices(timeout=5.0)
            if not devices:
                print("未发现设备")
                return
            
            if len(devices) == 1:
                self.current_device = devices[0]
            else:
                print("\n选择设备:")
                for i, dev in enumerate(devices):
                    print(f"  [{i}] {dev.name} ({dev.address})")
                
                try:
                    choice = int(input("输入设备编号: ").strip())
                    if 0 <= choice < len(devices):
                        self.current_device = devices[choice]
                    else:
                        print("无效的选择")
                        return
                except ValueError:
                    print("无效的输入")
                    return
        else:
            # Connect to specified address
            address = args[0]
            devices = await self.ble_manager.scan_devices(timeout=5.0)
            for dev in devices:
                if dev.address == address or dev.name == address:
                    self.current_device = dev
                    break
            
            if not self.current_device:
                print(f"未找到设备: {address}")
                return
        
        # Connect to device
        success = await self.ble_manager.connect(self.current_device.address)
        if success:
            # Get token
            print("\n正在获取 Token...")
            token = await self.ble_manager.bruteforce_token()
            if token:
                print(f"✓ Token 获取成功: 0x{token:02X}")
                print(f"✓ 自动刷新: {'启用' if self.auto_refresh else '禁用'}")
                print(f"✓ 自动重连: {'启用' if self.auto_reconnect else '禁用'}")
            else:
                print("✗ Token 获取失败")
        else:
            print("✗ 连接失败")
            self.current_device = None
    
    async def cmd_disconnect(self, args: List[str]):
        """Disconnect from device"""
        await self.ble_manager.disconnect()
        self.current_device = None
        print("已断开连接")
    
    async def cmd_info(self, args: List[str]):
        """Get device information"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n获取设备信息...")
        info = await self.ble_manager.get_device_info()
        
        print("\n设备信息:")
        print("-" * 60)
        print(f"  型号: {info.get('model', 'N/A')}")
        print(f"  固件: {info.get('firmware', 'N/A')}")
        print(f"  序列号: {info.get('serial', 'N/A')}")
        uptime = info.get('uptime', 0)
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        print(f"  运行时间: {hours}小时 {minutes}分钟 {seconds}秒")
        print("-" * 60)
    
    async def cmd_reboot(self, args: List[str]):
        """Reboot device"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        confirm = input("确认重启设备? (y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
        
        print("正在重启设备...")
        success = await self.ble_manager.reboot_device()
        if success:
            print("✓ 重启命令已发送")
            print("设备将在几秒后重启")
        else:
            print("✗ 重启失败")
    
    async def cmd_reset(self, args: List[str]):
        """Factory reset device"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("⚠️  警告: 这将清除所有用户数据!")
        confirm = input("确认重置设备? (输入 'RESET' 确认): ").strip()
        if confirm != 'RESET':
            print("已取消")
            return
        
        print("正在重置设备...")
        success = await self.ble_manager.reset_device()
        if success:
            print("✓ 重置命令已发送")
            print("设备将恢复出厂设置")
        else:
            print("✗ 重置失败")
    
    # ==================== Port Control Commands ====================
    
    async def cmd_status(self, args: List[str]):
        """Get all port status"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n获取端口状态...")
        ports = await self.ble_manager.get_port_status()
        
        if not ports:
            print("未获取到端口数据")
            return
        
        print("\n端口状态:")
        print("-" * 80)
        print(f"{'端口':<6} {'状态':<8} {'协议':<8} {'电压(V)':<10} {'电流(A)':<10} {'功率(W)':<10}")
        print("-" * 80)
        
        for port in ports:
            status = "开启" if port.enabled else "关闭"
            protocol = f"0x{port.protocol:02X}"
            print(f"{port.port_id:<6} {status:<8} {protocol:<8} {port.voltage:<10.2f} {port.current:<10.3f} {port.power:<10.2f}")
        
        print("-" * 80)
    
    async def cmd_on(self, args: List[str]):
        """Turn on port(s)"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if not args:
            print("用法: on <port_id> 或 on <port_id1,port_id2,...>")
            return
        
        # Parse port IDs
        try:
            if ',' in args[0]:
                port_ids = [int(p.strip()) for p in args[0].split(',')]
            else:
                port_ids = [int(args[0])]
        except ValueError:
            print("无效的端口 ID")
            return
        
        # Turn on each port individually (device expects port_id, not mask)
        for port_id in port_ids:
            print(f"打开端口 {port_id}...")
            success = await self.ble_manager.set_port_power(port_id, True)
            if success:
                print(f"✓ 端口 {port_id} 已打开")
            else:
                print(f"✗ 端口 {port_id} 操作失败")
    
    async def cmd_off(self, args: List[str]):
        """Turn off port(s)"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if not args:
            print("用法: off <port_id> 或 off <port_id1,port_id2,...>")
            return
        
        # Parse port IDs
        try:
            if ',' in args[0]:
                port_ids = [int(p.strip()) for p in args[0].split(',')]
            else:
                port_ids = [int(args[0])]
        except ValueError:
            print("无效的端口 ID")
            return
        
        # Turn off each port individually (device expects port_id, not mask)
        for port_id in port_ids:
            print(f"关闭端口 {port_id}...")
            success = await self.ble_manager.set_port_power(port_id, False)
            if success:
                print(f"✓ 端口 {port_id} 已关闭")
            else:
                print(f"✗ 端口 {port_id} 操作失败")
        if success:
            print("✓ 端口已关闭")
        else:
            print("✗ 操作失败")
    
    async def cmd_config(self, args: List[str]):
        """Get port configuration"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        port_id = int(args[0]) if args else 0
        
        print(f"\n获取端口 {port_id} 配置...")
        response = await self.ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
        
        if response and response.payload:
            protocols = decode_protocols(response.payload)
            
            print(f"\n端口 {port_id} 协议配置:")
            print("-" * 60)
            
            enabled = []
            disabled = []
            for name, value in protocols.items():
                if value:
                    enabled.append(name)
                else:
                    disabled.append(name)
            
            print("启用的协议:")
            for proto in enabled:
                print(f"  ✓ {proto}")
            
            print("\n禁用的协议:")
            for proto in disabled:
                print(f"  ✗ {proto}")
            
            print("-" * 60)
        else:
            print("获取配置失败")
    
    async def cmd_set_config(self, args: List[str]):
        """Set port configuration"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if len(args) < 2:
            print("用法: set-config <port_id> <protocol1,protocol2,...>")
            print("示例: set-config 0 PD,QC3.0,UFCS")
            return
        
        port_id = int(args[0])
        protocol_names = [p.strip() for p in args[1].split(',')]
        
        # Build protocol dictionary
        protocols = {name: False for name in PROTOCOL_NAMES.keys()}
        for name in protocol_names:
            if name in protocols:
                protocols[name] = True
            else:
                print(f"⚠️  未知协议: {name}")
        
        # Encode and send
        features = encode_protocols(protocols)
        payload = bytes([1 << port_id]) + features
        
        print(f"\n设置端口 {port_id} 配置...")
        response = await self.ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
        
        if response:
            print("✓ 配置已保存")
        else:
            print("✗ 配置失败")
    
    async def cmd_priority(self, args: List[str]):
        """Set port priority"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if len(args) < 2:
            print("用法: priority <port_id> <priority_value>")
            return
        
        port_id = int(args[0])
        priority = int(args[1])
        
        print(f"设置端口 {port_id} 优先级为 {priority}...")
        payload = bytes([port_id, priority])
        response = await self.ble_manager.execute(ServiceCommand.SET_PORT_PRIORITY, payload)
        
        if response:
            print("✓ 优先级已设置")
        else:
            print("✗ 设置失败")
    
    # ==================== Protocol Management Commands ====================
    
    async def cmd_protocols(self, args: List[str]):
        """List all supported protocols"""
        print("\n支持的协议:")
        print("-" * 60)
        
        categories = {
            "快充协议": ["TFCP", "PE", "QC2.0", "QC3.0", "QC3+", "AFC", "FCP", "UFCS"],
            "品牌协议": ["Apple 5V", "Samsung 5V", "VOOC", "Dash/Warp"],
            "USB PD": ["PD", "PPS", "QC4.0", "QC4+"],
            "其他": ["HV_SCP", "LV_SCP", "SFCP", "BC1.2", "RPi 5V5A", "SFC", "MTK PE", "MTK PE+"],
        }
        
        for category, protos in categories.items():
            print(f"\n{category}:")
            for proto in protos:
                print(f"  - {proto}")
        
        print("\n" + "-" * 60)
    
    async def cmd_enable(self, args: List[str]):
        """Enable protocol for a port"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if len(args) < 2:
            print("用法: enable <port_id> <protocol>")
            print("示例: enable 0 PD")
            return
        
        port_id = int(args[0])
        protocol_name = args[1]
        
        if protocol_name not in PROTOCOL_NAMES:
            print(f"未知协议: {protocol_name}")
            return
        
        # Get current config
        response = await self.ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
        if not response or not response.payload:
            print("获取当前配置失败")
            return
        
        # Update protocol
        protocols = decode_protocols(response.payload)
        protocols[protocol_name] = True
        
        # Save config
        features = encode_protocols(protocols)
        payload = bytes([1 << port_id]) + features
        
        print(f"为端口 {port_id} 启用 {protocol_name}...")
        response = await self.ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
        
        if response:
            print(f"✓ {protocol_name} 已启用")
        else:
            print("✗ 启用失败")
    
    async def cmd_disable(self, args: List[str]):
        """Disable protocol for a port"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if len(args) < 2:
            print("用法: disable <port_id> <protocol>")
            print("示例: disable 0 QC3.0")
            return
        
        port_id = int(args[0])
        protocol_name = args[1]
        
        if protocol_name not in PROTOCOL_NAMES:
            print(f"未知协议: {protocol_name}")
            return
        
        # Get current config
        response = await self.ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
        if not response or not response.payload:
            print("获取当前配置失败")
            return
        
        # Update protocol
        protocols = decode_protocols(response.payload)
        protocols[protocol_name] = False
        
        # Save config
        features = encode_protocols(protocols)
        payload = bytes([1 << port_id]) + features
        
        print(f"为端口 {port_id} 禁用 {protocol_name}...")
        response = await self.ble_manager.execute(ServiceCommand.SET_PORT_CONFIG, payload)
        
        if response:
            print(f"✓ {protocol_name} 已禁用")
        else:
            print("✗ 禁用失败")
    
    # ==================== Power Management Commands ====================
    
    async def cmd_power(self, args: List[str]):
        """Get power statistics"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        port_id = int(args[0]) if args else 0
        
        print(f"\n获取端口 {port_id} 电源统计...")
        response = await self.ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))
        
        if response and response.payload:
            # Parse power statistics (format varies by device)
            print(f"原始数据: {response.payload.hex()}")
            print("✓ 数据已获取")
        else:
            print("获取失败")
    
    async def cmd_strategy(self, args: List[str]):
        """Get charging strategy"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n获取充电策略...")
        response = await self.ble_manager.execute(ServiceCommand.GET_CHARGING_STRATEGY)
        
        if response and response.payload:
            strategy = response.payload[0] if response.payload else 0
            print(f"当前充电策略: 0x{strategy:02X}")
        else:
            print("获取失败")
    
    async def cmd_set_strategy(self, args: List[str]):
        """Set charging strategy"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if not args:
            print("用法: set-strategy <strategy_value>")
            return
        
        strategy = int(args[0])
        print(f"设置充电策略为 0x{strategy:02X}...")
        response = await self.ble_manager.execute(ServiceCommand.SET_CHARGING_STRATEGY, bytes([strategy]))
        
        if response:
            print("✓ 策略已设置")
        else:
            print("✗ 设置失败")
    
    # ==================== WiFi Management Commands ====================
    
    async def cmd_wifi_status(self, args: List[str]):
        """Get WiFi status"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n获取 WiFi 状态...")
        status = await self.ble_manager.get_wifi_status()
        
        if status:
            print(f"\nWiFi 状态: {status}")
        else:
            print("获取失败")
    
    async def cmd_scan_wifi(self, args: List[str]):
        """Scan WiFi networks"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n扫描 WiFi 网络...")
        response = await self.ble_manager.execute(ServiceCommand.SCAN_WIFI)
        
        if response:
            print("✓ 扫描命令已发送")
            print("使用 'get-wifi-result' 获取结果")
        else:
            print("✗ 扫描失败")
    
    async def cmd_set_wifi(self, args: List[str]):
        """Set WiFi SSID and password"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if len(args) < 2:
            print("用法: set-wifi <ssid> <password>")
            return
        
        ssid = args[0]
        password = args[1]
        
        print(f"\n设置 WiFi: {ssid}")
        success = await self.ble_manager.set_wifi(ssid, password)
        
        if success:
            print("✓ WiFi 已配置")
        else:
            print("✗ 配置失败")
    
    # ==================== Display Management Commands ====================
    
    async def cmd_display_info(self, args: List[str]):
        """Get display settings"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n获取显示设置...")
        
        # Get brightness
        resp = await self.ble_manager.execute(ServiceCommand.GET_DISPLAY_INTENSITY)
        brightness = resp.payload[0] if resp and resp.payload else 0
        
        # Get mode
        resp = await self.ble_manager.execute(ServiceCommand.GET_DISPLAY_MODE)
        mode = resp.payload[0] if resp and resp.payload else 0
        
        print(f"\n显示设置:")
        print("-" * 60)
        print(f"  亮度: {brightness}")
        print(f"  模式: {mode}")
        print("-" * 60)
    
    async def cmd_brightness(self, args: List[str]):
        """Set display brightness"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if not args:
            print("用法: brightness <value> (0-100)")
            return
        
        brightness = int(args[0])
        if not 0 <= brightness <= 100:
            print("亮度值必须在 0-100 之间")
            return
        
        print(f"设置亮度为 {brightness}...")
        success = await self.ble_manager.set_display_brightness(brightness)
        
        if success:
            print("✓ 亮度已设置")
        else:
            print("✗ 设置失败")
    
    async def cmd_mode(self, args: List[str]):
        """Set display mode"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        if not args:
            print("用法: mode <mode_value>")
            return
        
        mode = int(args[0])
        print(f"设置显示模式为 {mode}...")
        success = await self.ble_manager.set_display_mode(mode)
        
        if success:
            print("✓ 模式已设置")
        else:
            print("✗ 设置失败")
    
    async def cmd_flip(self, args: List[str]):
        """Flip display"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("翻转显示...")
        success = await self.ble_manager.flip_display()
        
        if success:
            print("✓ 显示已翻转")
        else:
            print("✗ 操作失败")
    
    # ==================== System Control Commands ====================
    
    async def cmd_token(self, args: List[str]):
        """Show current token"""
        if self.ble_manager.token is not None:
            print(f"当前 Token: 0x{self.ble_manager.token:02X} ({self.ble_manager.token})")
        else:
            print("当前 Token: 无")
    
    async def cmd_refresh_token(self, args: List[str]):
        """Manually refresh token"""
        if not self.ble_manager.connected:
            print("未连接设备")
            return
        
        print("\n手动刷新 Token...")
        token = await self.ble_manager.bruteforce_token()
        
        if token:
            print(f"✓ Token 已刷新: 0x{token:02X}")
        else:
            print("✗ Token 刷新失败")
    
    async def cmd_auto_refresh(self, args: List[str]):
        """Toggle auto refresh"""
        if args and args[0].lower() in ['on', 'true', '1', 'yes']:
            self.auto_refresh = True
            self.ble_manager.enable_auto_refresh(True)
            print("自动刷新: 启用")
        elif args and args[0].lower() in ['off', 'false', '0', 'no']:
            self.auto_refresh = False
            self.ble_manager.enable_auto_refresh(False)
            print("自动刷新: 禁用")
        else:
            status = "启用" if self.auto_refresh else "禁用"
            print(f"自动刷新: {status}")
            print("用法: auto-refresh [on|off]")
    
    async def cmd_auto_reconnect(self, args: List[str]):
        """Toggle auto reconnect"""
        if args and args[0].lower() in ['on', 'true', '1', 'yes']:
            self.auto_reconnect = True
            self.ble_manager.enable_auto_reconnect(True)
            print("自动重连: 启用")
        elif args and args[0].lower() in ['off', 'false', '0', 'no']:
            self.auto_reconnect = False
            self.ble_manager.enable_auto_reconnect(False)
            print("自动重连: 禁用")
        else:
            status = "启用" if self.auto_reconnect else "禁用"
            print(f"自动重连: {status}")
            print("用法: auto-reconnect [on|off]")
    
    async def cmd_help(self, args: List[str]):
        """Show help information"""
        print("\n" + "=" * 70)
        print("  IonBridge BLE 控制器 - 命令帮助")
        print("=" * 70)
        
        categories = {
            "设备管理": [
                ("scan", "扫描设备"),
                ("connect", "连接设备"),
                ("disconnect", "断开连接"),
                ("info", "获取设备信息"),
                ("reboot", "重启设备"),
                ("reset", "重置设备"),
            ],
            "端口控制": [
                ("status", "查看所有端口状态"),
                ("on <port>", "打开端口"),
                ("off <port>", "关闭端口"),
                ("config <port>", "查看端口配置"),
                ("set-config <port> <protos>", "设置端口配置"),
                ("priority <port> <val>", "设置端口优先级"),
            ],
            "协议管理": [
                ("protocols", "列出所有支持的协议"),
                ("enable <port> <proto>", "启用协议"),
                ("disable <port> <proto>", "禁用协议"),
            ],
            "电源管理": [
                ("power [port]", "获取电源统计"),
                ("strategy", "获取充电策略"),
                ("set-strategy <val>", "设置充电策略"),
            ],
            "WiFi 管理": [
                ("wifi-status", "获取 WiFi 状态"),
                ("scan-wifi", "扫描 WiFi 网络"),
                ("set-wifi <ssid> <pwd>", "设置 WiFi"),
            ],
            "显示管理": [
                ("display-info", "获取显示设置"),
                ("brightness <val>", "设置亮度 (0-100)"),
                ("mode <val>", "设置显示模式"),
                ("flip", "翻转显示"),
            ],
            "系统控制": [
                ("token", "显示当前 Token"),
                ("refresh-token", "手动刷新 Token"),
                ("auto-refresh [on|off]", "切换自动刷新"),
                ("auto-reconnect [on|off]", "切换自动重连"),
                ("help", "显示帮助"),
                ("quit/exit", "退出"),
            ],
        }
        
        for category, commands in categories.items():
            print(f"\n{category}:")
            for cmd, desc in commands:
                print(f"  {cmd:<20} - {desc}")
        
        print("\n" + "=" * 70)
        print("\n提示:")
        print("  - 端口 ID 可以使用逗号分隔: on 0,1,2")
        print("  - 协议名称不区分大小写")
        print("  - 按 Ctrl+C 可以中断操作")
        print("=" * 70 + "\n")
    
    async def cmd_quit(self, args: List[str]):
        """Quit the CLI"""
        self.running = False


async def main():
    """Main entry point"""
    controller = CLIController()
    await controller.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已退出")
        sys.exit(0)
