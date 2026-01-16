#!/usr/bin/env python3
"""
测试协议名称映射
验证从IonBridge-main/data_types.h提取的协议定义是否正确
"""

from protocol import FAST_CHARGING_PROTOCOLS, get_protocol_name

# 测试所有协议值
print("=" * 60)
print("协议名称映射测试")
print("=" * 60)

# 测试已知协议
test_protocols = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 0xFF
]

for protocol in test_protocols:
    name = get_protocol_name(protocol)
    print(f"协议值 {protocol:3d} (0x{protocol:02X}): {name}")

print("\n" + "=" * 60)
print("测试用户报告的问题：协议16")
print("=" * 60)

protocol_16 = get_protocol_name(16)
print(f"协议16应该显示: PD 高压")
print(f"实际显示: {protocol_16}")
print(f"测试结果: {'✓ 通过' if protocol_16 == 'PD 高压' else '✗ 失败'}")

print("\n" + "=" * 60)
print("测试未知协议")
print("=" * 60)

unknown_protocol = 99
name = get_protocol_name(unknown_protocol)
print(f"协议99应该显示: 未知(99)")
print(f"实际显示: {name}")
print(f"测试结果: {'✓ 通过' if name == '未知(99)' else '✗ 失败'}")

print("\n" + "=" * 60)
print("所有测试完成！")
print("=" * 60)
