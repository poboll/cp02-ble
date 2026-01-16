#!/usr/bin/env python3
"""
IonBridge BLE Controller - Web Interface Complete Test
测试Web界面的所有功能
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ble_manager import BLEManager
from protocol import ServiceCommand


class WebInterfaceTester:
    """Web界面测试器"""

    def __init__(self):
        self.ble = None
        self.test_results = []
        self.device_address = None

    async def connect_device(self):
        """连接设备"""
        print("\n" + "="*60)
        print("步骤 1: 连接设备")
        print("="*60)

        try:
            self.ble = BLEManager()

            # 扫描设备
            print("正在扫描设备...")
            devices = await self.ble.scan_devices(timeout=5.0)

            if not devices:
                print("❌ 未找到设备")
                return False

            print(f"找到 {len(devices)} 个设备:")
            for i, device in enumerate(devices):
                print(f"  {i+1}. {device.name} ({device.address}) - RSSI: {device.rssi} dBm")

            # 选择第一个CP02设备
            cp02_devices = [d for d in devices if d.name and 'CP02' in d.name]
            if cp02_devices:
                device = cp02_devices[0]
            else:
                device = devices[0]

            self.device_address = device.address
            print(f"\n选择设备: {device.name} ({device.address})")

            # 连接设备
            print("正在连接...")
            success = await self.ble.connect(device.address)

            if success:
                print("✅ 设备已连接")
                self.test_results.append(("连接设备", True))
                return True
            else:
                print("❌ 连接失败")
                self.test_results.append(("连接设备", False))
                return False

        except Exception as e:
            print(f"❌ 连接错误: {e}")
            self.test_results.append(("连接设备", False))
            return False

    async def test_device_management(self):
        """测试设备管理功能"""
        print("\n" + "="*60)
        print("步骤 2: 测试设备管理功能")
        print("="*60)

        tests = [
            ("获取设备信息", ServiceCommand.GET_DEVICE_INFO),
            ("获取设备型号", ServiceCommand.GET_DEVICE_MODEL),
            ("获取设备序列号", ServiceCommand.GET_DEVICE_SERIAL),
            ("获取设备运行时间", ServiceCommand.GET_DEVICE_UPTIME),
            ("获取固件版本", ServiceCommand.GET_AP_VERSION),
            ("获取BLE地址", ServiceCommand.GET_BLE_ADDR),
            ("获取电源供应状态", ServiceCommand.GET_POWER_SUPPLY_STATUS),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                response = await self.ble.send_command(command)
                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    async def test_port_control(self):
        """测试端口控制功能"""
        print("\n" + "="*60)
        print("步骤 3: 测试端口控制功能")
        print("="*60)

        tests = [
            ("获取端口状态", ServiceCommand.GET_PORT_STATUS),
            ("获取端口配置", ServiceCommand.GET_PORT_CONFIG),
            ("获取端口优先级", ServiceCommand.GET_PORT_PRIORITY),
            ("获取端口最大功率", ServiceCommand.GET_PORT_MAX_POWER),
            ("获取端口温度", ServiceCommand.GET_PORT_TEMPERATURE),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                # 某些命令需要参数
                if command in [ServiceCommand.GET_PORT_CONFIG, ServiceCommand.GET_PORT_PRIORITY,
                              ServiceCommand.GET_PORT_MAX_POWER, ServiceCommand.GET_PORT_TEMPERATURE]:
                    response = await self.ble.send_command(command, port_id=0)
                else:
                    response = await self.ble.send_command(command)

                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    async def test_power_management(self):
        """测试电源管理功能"""
        print("\n" + "="*60)
        print("步骤 4: 测试电源管理功能")
        print("="*60)

        tests = [
            ("获取电源统计", ServiceCommand.GET_POWER_STATISTICS),
            ("获取充电策略", ServiceCommand.GET_CHARGING_STRATEGY),
            ("获取充电状态", ServiceCommand.GET_CHARGING_STATUS),
            ("获取最大功率", ServiceCommand.GET_MAX_POWER),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                # GET_POWER_STATISTICS 需要端口ID
                if command == ServiceCommand.GET_POWER_STATISTICS:
                    response = await self.ble.send_command(command, port_id=0)
                else:
                    response = await self.ble.send_command(command)

                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    async def test_wifi_management(self):
        """测试WiFi管理功能"""
        print("\n" + "="*60)
        print("步骤 5: 测试WiFi管理功能")
        print("="*60)

        tests = [
            ("获取WiFi状态", ServiceCommand.GET_WIFI_STATUS),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                response = await self.ble.send_command(command)
                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    async def test_display_management(self):
        """测试显示管理功能"""
        print("\n" + "="*60)
        print("步骤 6: 测试显示管理功能")
        print("="*60)

        tests = [
            ("获取显示设置", ServiceCommand.GET_DISPLAY_SETTINGS),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                response = await self.ble.send_command(command)
                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    async def test_advanced_settings(self):
        """测试高级设置功能"""
        print("\n" + "="*60)
        print("步骤 7: 测试高级设置功能")
        print("="*60)

        tests = [
            ("获取夜间模式", ServiceCommand.GET_NIGHT_MODE),
            ("获取语言设置", ServiceCommand.GET_LANGUAGE),
            ("获取LED模式", ServiceCommand.GET_LED_MODE),
            ("获取自动关闭", ServiceCommand.GET_AUTO_OFF),
            ("获取屏保设置", ServiceCommand.GET_SCREEN_SAVER),
        ]

        for test_name, command in tests:
            try:
                print(f"\n测试: {test_name}...")
                response = await self.ble.send_command(command)
                if response:
                    print(f"✅ {test_name} - 成功")
                    print(f"   响应: {response[:100] if len(response) > 100 else response}")
                    self.test_results.append((test_name, True))
                else:
                    print(f"❌ {test_name} - 失败（无响应）")
                    self.test_results.append((test_name, False))
            except Exception as e:
                print(f"❌ {test_name} - 错误: {e}")
                self.test_results.append((test_name, False))

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)

        total = len(self.test_results)
        passed = sum(1 for _, result in self.test_results if result)
        failed = total - passed

        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"成功率: {(passed/total*100):.1f}%")

        if failed > 0:
            print("\n失败的测试:")
            for test_name, result in self.test_results:
                if not result:
                    print(f"  ❌ {test_name}")

        print("\n" + "="*60)

        return failed == 0

    async def run_all_tests(self):
        """运行所有测试"""
        try:
            # 连接设备
            if not await self.connect_device():
                return False

            # 等待一下让连接稳定
            await asyncio.sleep(2)

            # 运行所有测试
            await self.test_device_management()
            await asyncio.sleep(1)

            await self.test_port_control()
            await asyncio.sleep(1)

            await self.test_power_management()
            await asyncio.sleep(1)

            await self.test_wifi_management()
            await asyncio.sleep(1)

            await self.test_display_management()
            await asyncio.sleep(1)

            await self.test_advanced_settings()

            # 打印摘要
            return self.print_summary()

        except Exception as e:
            print(f"\n❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # 断开连接
            if self.ble:
                print("\n正在断开连接...")
                await self.ble.disconnect()
                print("✅ 已断开连接")


async def main():
    """主函数"""
    print("="*60)
    print("IonBridge BLE Controller - Web Interface Complete Test")
    print("Web界面完整功能测试")
    print("="*60)

    tester = WebInterfaceTester()
    success = await tester.run_all_tests()

    if success:
        print("\n✅ 所有测试通过！Web界面功能正常。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
