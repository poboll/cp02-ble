#!/usr/bin/env python3
"""
ESP32 BLE Gateway - API 测试脚本
用于验证后端 API 是否正常工作
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5225"
TIMEOUT = 10

# 测试结果
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

async def test_health():
    """测试健康检查端点"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/health", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                data = await resp.json()
                assert resp.status == 200, f"状态码 {resp.status}"
                assert data.get("status") == "healthy", "状态不健康"
                return True, f"健康检查通过 - 版本 {data.get('version', 'unknown')}"
        except Exception as e:
            return False, str(e)

async def test_config():
    """测试配置端点"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/config", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                data = await resp.json()
                assert resp.status == 200, f"状态码 {resp.status}"
                assert "mqtt_host" in data, "缺少 mqtt_host"
                return True, f"配置获取成功 - MQTT: {data.get('mqtt_host')}:{data.get('mqtt_port')}"
        except Exception as e:
            return False, str(e)

async def test_gateways():
    """测试网关列表端点"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/gateways", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                data = await resp.json()
                assert resp.status == 200, f"状态码 {resp.status}"
                gateway_count = len(data.get("gateways", []))
                return True, f"网关列表获取成功 - {gateway_count} 个网关"
        except Exception as e:
            return False, str(e)

async def test_port_status():
    """测试端口状态端点"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/port-status", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                data = await resp.json()
                assert resp.status == 200, f"状态码 {resp.status}"
                ports = data.get("ports", [])
                total_power = data.get("totalPower", 0)
                return True, f"端口状态获取成功 - {len(ports)} 个端口, 总功率 {total_power}W"
        except Exception as e:
            return False, str(e)

async def test_status():
    """测试系统状态端点"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/status", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                data = await resp.json()
                assert resp.status == 200, f"状态码 {resp.status}"
                mqtt_connected = data.get("mqtt_connected", False)
                gateway_count = data.get("gateway_count", 0)
                return True, f"系统状态获取成功 - MQTT: {'在线' if mqtt_connected else '离线'}, 网关: {gateway_count}"
        except Exception as e:
            return False, str(e)

async def test_static_files():
    """测试静态文件服务"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                content = await resp.text()
                assert resp.status == 200, f"状态码 {resp.status}"
                assert "<html" in content.lower() or "<!doctype" in content.lower(), "不是有效的 HTML"
                return True, "静态文件服务正常"
        except Exception as e:
            return False, str(e)

async def test_js_file():
    """测试 JavaScript 文件服务"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/script.js", timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
                content = await resp.text()
                assert resp.status == 200, f"状态码 {resp.status}"
                assert "ChargingStationMonitor" in content, "JavaScript 内容无效"
                return True, "JavaScript 文件服务正常"
        except Exception as e:
            return False, str(e)

async def test_command_endpoint():
    """测试命令端点格式(不需要真实网关)"""
    async with aiohttp.ClientSession() as session:
        try:
            # 测试发送到不存在的网关 - 应该返回404或超时
            async with session.post(
                f"{BASE_URL}/api/gateway/test-gw/cmd",
                json={"command": "get_device_info", "params": {}},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT)
            ) as resp:
                # 只要端点能响应就算通过
                if resp.status in [200, 404, 500, 503]:
                    return True, f"命令端点响应正常 (状态码 {resp.status})"
                return False, f"意外状态码 {resp.status}"
        except Exception as e:
            return False, str(e)

async def run_test(name: str, test_func):
    """运行单个测试"""
    print(f"  [{name}] ", end="", flush=True)
    try:
        passed, message = await test_func()
        if passed:
            print(f"✅ {message}")
            results["passed"].append(name)
        else:
            print(f"❌ {message}")
            results["failed"].append(name)
    except Exception as e:
        print(f"❌ 异常: {e}")
        results["failed"].append(name)

async def main():
    print("\n" + "=" * 60)
    print("  ESP32 BLE Gateway - API 测试")
    print(f"  目标: {BASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    # 先检查服务是否可用
    print("📡 检查服务可用性...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"\n❌ 服务不可用 (状态码 {resp.status})")
                    print("请先启动后端服务: cd backend && python app.py")
                    sys.exit(1)
    except aiohttp.ClientConnectorError:
        print(f"\n❌ 无法连接到 {BASE_URL}")
        print("请先启动后端服务: cd backend && python app.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 连接错误: {e}")
        sys.exit(1)
    
    print("✅ 服务可用\n")
    print("🧪 运行测试...\n")
    
    tests = [
        ("健康检查", test_health),
        ("配置获取", test_config),
        ("网关列表", test_gateways),
        ("端口状态", test_port_status),
        ("系统状态", test_status),
        ("静态文件", test_static_files),
        ("JavaScript", test_js_file),
        ("命令端点", test_command_endpoint),
    ]
    
    for name, test_func in tests:
        await run_test(name, test_func)
    
    print("\n" + "=" * 60)
    print("  测试结果摘要")
    print("=" * 60)
    print(f"  ✅ 通过: {len(results['passed'])}")
    print(f"  ❌ 失败: {len(results['failed'])}")
    print(f"  ⏭️  跳过: {len(results['skipped'])}")
    
    if results['failed']:
        print(f"\n  失败的测试: {', '.join(results['failed'])}")
    
    print("=" * 60 + "\n")
    
    return len(results['failed']) == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
