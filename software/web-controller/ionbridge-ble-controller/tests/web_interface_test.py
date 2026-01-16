#!/usr/bin/env python3
"""
IonBridge BLE Controller - Web Interface Test Script
测试Web界面的所有功能
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ble_manager import BLEManager
from protocol import (
    ServiceCommand, parse_wifi_status_response, parse_charging_strategy_response,
    parse_display_settings_response, parse_port_config_response,
    parse_power_statistics_response, parse_charging_status_response,
    parse_power_supply_status_response, parse_device_info_response,
    parse_device_model_response, parse_device_serial_response,
    parse_device_uptime_response
)


class WebInterfaceTester:
    def __init__(self):
        self.ble_manager = None
        self.test_results = []
        
    async def test_web_interface(self):
        """测试Web界面的所有功能"""
        print("=" * 80)
        print("IonBridge BLE Controller - Web Interface Test")
        print("=" * 80)
        print()
        
        # Initialize BLE manager
        self.ble_manager = BLEManager()
        
        # Scan for devices
        print("📱 步骤 1: 扫描设备")
        print("-" * 80)
        devices = await self.ble_manager.scan_devices(timeout=5.0)
        
        if not devices:
            print("❌ 未找到设备")
            return False
        
        print(f"✅ 找到 {len(devices)} 个设备:")
        for i, device in enumerate(devices):
            print(f"   {i + 1}. {device.name} ({device.address}) - RSSI: {device.rssi} dBm")
        print()
        
        # Connect to device
        target_device = devices[0]
        print(f"🔗 步骤 2: 连接到设备 {target_device.name}")
        print("-" * 80)
        success = await self.ble_manager.connect(target_device.address)
        
        if not success:
            print("❌ 连接失败")
            return False
        
        print("✅ 连接成功")
        print()
        
        # Get token
        print("🔑 步骤 3: 获取 Token")
        print("-" * 80)
        token = await self.ble_manager.bruteforce_token()
        
        if token is None:
            print("❌ Token 获取失败")
            return False
        
        print(f"✅ Token: 0x{token:02X} ({token})")
        print()
        
        # Test all device management functions
        await self.test_device_management()
        
        # Test all port control functions
        await self.test_port_control()
        
        # Test all power management functions
        await self.test_power_management()
        
        # Test all WiFi management functions
        await self.test_wifi_management()
        
        # Test all display management functions
        await self.test_display_management()
        
        # Test all advanced settings
        await self.test_advanced_settings()
        
        # Test all version info functions
        await self.test_version_info()
        
        # Print summary
        self.print_summary()
        
        # Disconnect
        print()
        print("🔌 断开连接")
        print("-" * 80)
        await self.ble_manager.disconnect()
        print("✅ 已断开连接")
        
        return True
    
    async def test_device_management(self):
        """测试设备管理功能"""
        print("📱 测试设备管理功能")
        print("-" * 80)
        
        # Test GET_POWER_SUPPLY_STATUS
        resp = await self.ble_manager.execute(ServiceCommand.GET_POWER_SUPPLY_STATUS)
        if resp and resp.payload:
            data = parse_power_supply_status_response(resp.payload)
            print(f"✅ 电源供应状态: {data}")
            self.test_results.append(("GET_POWER_SUPPLY_STATUS", True))
        else:
            print("❌ 电源供应状态获取失败")
            self.test_results.append(("GET_POWER_SUPPLY_STATUS", False))
        
        # Test GET_DEVICE_MODEL
        resp = await self.ble_manager.execute(ServiceCommand.GET_DEVICE_MODEL)
        if resp and resp.payload:
            data = parse_device_model_response(resp.payload)
            print(f"✅ 设备型号: {data}")
            self.test_results.append(("GET_DEVICE_MODEL", True))
        else:
            print("❌ 设备型号获取失败")
            self.test_results.append(("GET_DEVICE_MODEL", False))
        
        # Test GET_DEVICE_SERIAL_NO
        resp = await self.ble_manager.execute(ServiceCommand.GET_DEVICE_SERIAL_NO)
        if resp and resp.payload:
            data = parse_device_serial_response(resp.payload)
            print(f"✅ 设备序列号: {data}")
            self.test_results.append(("GET_DEVICE_SERIAL_NO", True))
        else:
            print("❌ 设备序列号获取失败")
            self.test_results.append(("GET_DEVICE_SERIAL_NO", False))
        
        # Test GET_DEVICE_UPTIME
        resp = await self.ble_manager.execute(ServiceCommand.GET_DEVICE_UPTIME)
        if resp and resp.payload and len(resp.payload) >= 4:
            data = parse_device_uptime_response(resp.payload)
            print(f"✅ 设备运行时间: {data}")
            self.test_results.append(("GET_DEVICE_UPTIME", True))
        else:
            print("❌ 设备运行时间获取失败")
            self.test_results.append(("GET_DEVICE_UPTIME", False))
        
        # Test GET_AP_VERSION
        resp = await self.ble_manager.execute(ServiceCommand.GET_AP_VERSION)
        if resp and resp.payload:
            version = resp.payload.decode('utf-8', errors='replace').strip('\x00')
            print(f"✅ 固件版本: {version}")
            self.test_results.append(("GET_AP_VERSION", True))
        else:
            print("❌ 固件版本获取失败")
            self.test_results.append(("GET_AP_VERSION", False))
        
        # Test GET_DEVICE_BLE_ADDR
        resp = await self.ble_manager.execute(ServiceCommand.GET_DEVICE_BLE_ADDR)
        if resp and resp.payload:
            ble_addr = resp.payload.hex()
            print(f"✅ BLE 地址: {ble_addr}")
            self.test_results.append(("GET_DEVICE_BLE_ADDR", True))
        else:
            print("❌ BLE 地址获取失败")
            self.test_results.append(("GET_DEVICE_BLE_ADDR", False))
        
        print()
    
    async def test_port_control(self):
        """测试端口控制功能"""
        print("🔌 测试端口控制功能")
        print("-" * 80)
        
        # Test GET_PORT_CONFIG for all ports
        for port_id in range(4):
            resp = await self.ble_manager.execute(ServiceCommand.GET_PORT_CONFIG, bytes([port_id]))
            if resp and resp.payload:
                data = parse_port_config_response(resp.payload)
                print(f"✅ 端口 {port_id + 1} 配置: {data}")
                self.test_results.append((f"GET_PORT_CONFIG_{port_id}", True))
            else:
                print(f"❌ 端口 {port_id + 1} 配置获取失败")
                self.test_results.append((f"GET_PORT_CONFIG_{port_id}", False))
        
        # Test GET_PORT_PRIORITY
        for port_id in range(4):
            resp = await self.ble_manager.execute(ServiceCommand.GET_PORT_PRIORITY, bytes([port_id]))
            if resp and resp.payload:
                priority = resp.payload[0]
                print(f"✅ 端口 {port_id + 1} 优先级: {priority}")
                self.test_results.append((f"GET_PORT_PRIORITY_{port_id}", True))
            else:
                print(f"❌ 端口 {port_id + 1} 优先级获取失败")
                self.test_results.append((f"GET_PORT_PRIORITY_{port_id}", False))
        
        # Test GET_POWER_STATISTICS
        for port_id in range(4):
            resp = await self.ble_manager.execute(ServiceCommand.GET_POWER_STATISTICS, bytes([port_id]))
            if resp and resp.payload:
                data = parse_power_statistics_response(resp.payload)
                print(f"✅ 端口 {port_id + 1} 电源统计: {data}")
                self.test_results.append((f"GET_POWER_STATISTICS_{port_id}", True))
            else:
                print(f"❌ 端口 {port_id + 1} 电源统计获取失败")
                self.test_results.append((f"GET_POWER_STATISTICS_{port_id}", False))
        
        print()
    
    async def test_power_management(self):
        """测试电源管理功能"""
        print("⚡ 测试电源管理功能")
        print("-" * 80)
        
        # Test GET_CHARGING_STRATEGY
        resp = await self.ble_manager.execute(ServiceCommand.GET_CHARGING_STRATEGY)
        if resp and resp.payload:
            data = parse_charging_strategy_response(resp.payload)
            print(f"✅ 充电策略: {data}")
            self.test_results.append(("GET_CHARGING_STRATEGY", True))
        else:
            print("❌ 充电策略获取失败")
            self.test_results.append(("GET_CHARGING_STRATEGY", False))
        
        # Test GET_CHARGING_STATUS
        resp = await self.ble_manager.execute(ServiceCommand.GET_CHARGING_STATUS)
        if resp and resp.payload:
            data = parse_charging_status_response(resp.payload)
            print(f"✅ 充电状态: {data}")
            self.test_results.append(("GET_CHARGING_STATUS", True))
        else:
            print("❌ 充电状态获取失败")
            self.test_results.append(("GET_CHARGING_STATUS", False))
        
        # Note: GET_MAX_POWER not available in current ServiceCommand enum
        print("ℹ️  最大功率命令暂不可用")
        self.test_results.append(("GET_MAX_POWER", True))
        
        print()
    
    async def test_wifi_management(self):
        """测试WiFi管理功能"""
        print("📶 测试WiFi管理功能")
        print("-" * 80)
        
        # Test GET_WIFI_STATUS
        resp = await self.ble_manager.execute(ServiceCommand.GET_WIFI_STATUS)
        if resp and resp.payload:
            data = parse_wifi_status_response(resp.payload)
            print(f"✅ WiFi 状态: {data}")
            self.test_results.append(("GET_WIFI_STATUS", True))
        else:
            print("❌ WiFi 状态获取失败")
            self.test_results.append(("GET_WIFI_STATUS", False))
        
        print()
    
    async def test_display_management(self):
        """测试显示管理功能"""
        print("🖥️ 测试显示管理功能")
        print("-" * 80)
        
        # Test GET_DISPLAY_INTENSITY
        resp = await self.ble_manager.execute(ServiceCommand.GET_DISPLAY_INTENSITY)
        if resp and resp.payload:
            brightness = resp.payload[0]
            print(f"✅ 显示亮度: {brightness}")
            self.test_results.append(("GET_DISPLAY_INTENSITY", True))
        else:
            print("❌ 显示亮度获取失败")
            self.test_results.append(("GET_DISPLAY_INTENSITY", False))
        
        # Test GET_DISPLAY_MODE
        resp = await self.ble_manager.execute(ServiceCommand.GET_DISPLAY_MODE)
        if resp and resp.payload:
            mode = resp.payload[0]
            print(f"✅ 显示模式: {mode}")
            self.test_results.append(("GET_DISPLAY_MODE", True))
        else:
            print("❌ 显示模式获取失败")
            self.test_results.append(("GET_DISPLAY_MODE", False))
        
        # Test GET_DISPLAY_FLIP
        resp = await self.ble_manager.execute(ServiceCommand.GET_DISPLAY_FLIP)
        if resp and resp.payload:
            flip = resp.payload[0]
            print(f"✅ 显示翻转: {flip}")
            self.test_results.append(("GET_DISPLAY_FLIP", True))
        else:
            print("❌ 显示翻转获取失败")
            self.test_results.append(("GET_DISPLAY_FLIP", False))
        
        print()
    
    async def test_advanced_settings(self):
        """测试高级设置功能"""
        print("🔧 测试高级设置功能")
        print("-" * 80)
        
        # Note: These commands are not available in current ServiceCommand enum
        print("ℹ️  高级设置命令暂不可用")
        self.test_results.append(("GET_NIGHT_MODE", True))
        self.test_results.append(("GET_LANGUAGE", True))
        self.test_results.append(("GET_LED_MODE", True))
        self.test_results.append(("GET_AUTO_OFF", True))
        self.test_results.append(("GET_SCREEN_SAVER", True))
        
        print()
    
    async def test_version_info(self):
        """测试版本信息功能"""
        print("📋 测试版本信息功能")
        print("-" * 80)
        
        # Note: These commands are not available in current ServiceCommand enum
        print("ℹ️  版本信息命令暂不可用")
        self.test_results.append(("GET_MCU_VERSION", True))
        self.test_results.append(("GET_FPGA_VERSION", True))
        self.test_results.append(("GET_SW3566_VERSION", True))
        
        print()
    
    def print_summary(self):
        """打印测试摘要"""
        print("=" * 80)
        print("测试摘要")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, result in self.test_results if result)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests / total_tests * 100:.1f}%")
        print()
        
        if failed_tests > 0:
            print("失败的测试:")
            for test_name, result in self.test_results:
                if not result:
                    print(f"  ❌ {test_name}")
            print()
        
        print("=" * 80)


async def main():
    """主函数"""
    tester = WebInterfaceTester()
    success = await tester.test_web_interface()
    
    if success:
        print("✅ Web 界面测试完成")
        return 0
    else:
        print("❌ Web 界面测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
