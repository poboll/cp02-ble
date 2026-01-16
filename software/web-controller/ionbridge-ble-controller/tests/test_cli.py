#!/usr/bin/env python3
"""
Test script for CLI Controller
Tests basic functionality without requiring actual device
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol import (
    ServiceCommand, PROTOCOL_NAMES, decode_protocols, encode_protocols,
    get_command_name, COMMAND_CATEGORIES, build_message, parse_response
)

def test_protocol_encoding():
    """Test protocol encoding/decoding"""
    print("测试协议编解码...")
    
    # Test 1: Enable PD and QC3.0
    protocols = {
        'PD': True,
        'QC3.0': True,
        'PE': False,
    }
    
    encoded = encode_protocols(protocols)
    print(f"  编码结果: {encoded.hex()}")
    
    decoded = decode_protocols(encoded)
    print(f"  解码结果: {decoded}")
    
    # Verify
    assert decoded['PD'] == True, "PD should be enabled"
    assert decoded['QC3.0'] == True, "QC3.0 should be enabled"
    assert decoded['PE'] == False, "PE should be disabled"
    
    print("  ✓ 协议编解码测试通过\n")

def test_message_building():
    """Test message building"""
    print("测试消息构建...")
    
    # Build a simple message
    message = build_message(
        version=0,
        msg_id=1,
        service=ServiceCommand.GET_DEVICE_MODEL,
        sequence=0,
        flags=0x1,  # SYN
        payload=b'\x42'  # Token
    )
    
    print(f"  消息长度: {len(message)} 字节")
    print(f"  消息内容: {message.hex()}")
    
    # Parse the message
    parsed = parse_response(message)
    print(f"  版本: {parsed.version}")
    print(f"  消息ID: {parsed.msg_id}")
    print(f"  服务: {get_command_name(parsed.service)}")
    print(f"  负载: {parsed.payload.hex()}")
    
    print("  ✓ 消息构建测试通过\n")

def test_command_categories():
    """Test command categorization"""
    print("测试命令分类...")
    
    total_commands = 0
    for category, commands in COMMAND_CATEGORIES.items():
        print(f"  {category}: {len(commands)} 个命令")
        total_commands += len(commands)
    
    print(f"  总计: {total_commands} 个命令")
    print("  ✓ 命令分类测试通过\n")

def test_all_protocols():
    """Test all protocol names"""
    print("测试所有协议名称...")
    
    print(f"  支持的协议数量: {len(PROTOCOL_NAMES)}")
    
    # Test encoding all protocols enabled
    all_enabled = {name: True for name in PROTOCOL_NAMES.keys()}
    encoded = encode_protocols(all_enabled)
    print(f"  所有协议启用: {encoded.hex()}")
    
    # Test encoding all protocols disabled
    all_disabled = {name: False for name in PROTOCOL_NAMES.keys()}
    encoded = encode_protocols(all_disabled)
    print(f"  所有协议禁用: {encoded.hex()}")
    
    print("  ✓ 协议名称测试通过\n")

def main():
    """Run all tests"""
    print("=" * 70)
    print("  IonBridge BLE 控制器 - 单元测试")
    print("=" * 70)
    print()
    
    try:
        test_protocol_encoding()
        test_message_building()
        test_command_categories()
        test_all_protocols()
        
        print("=" * 70)
        print("  所有测试通过! ✓")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
