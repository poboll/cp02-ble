#!/bin/bash
# IonBridge BLE 控制器 - 设备测试脚本
# 使用说明：
# 1. 确保小电拼设备已开机
# 2. 确保设备在蓝牙范围内（建议 5 米以内）
# 3. 确保电脑蓝牙已开启
# 4. 运行此脚本

echo "=========================================="
echo "  IonBridge BLE 控制器 - 设备测试"
echo "=========================================="
echo ""
echo "请确保："
echo "  1. 小电拼设备已开机"
echo "  2. 设备在蓝牙范围内（5 米以内）"
echo "  3. 电脑蓝牙已开启"
echo ""
read -p "按 Enter 键开始测试..."

# 使用 conda uu 环境运行命令行工具
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python ionbridge-ble-controller/cli_controller.py
