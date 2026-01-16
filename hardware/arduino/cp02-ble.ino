/*
 * BLE Honeypot for "小电拼" Device
 * Target: CP02-0002A0
 * Platform: ESP32-S3-WROOM-1-N16R8 DevKitC-1
 * Framework: Arduino ESP32
 * 
 * 基于 IonBridge 开源代码分析:
 * https://github.com/ifanrx/IonBridge
 * 
 * Manufacturer Data 结构 (8 bytes):
 * [0-1]: Company ID 0x36E9 (小端序: 0xE9 0x36)
 * [2-4]: MAC 地址后 3 字节
 * [5]: Product Family (CP02 = 0x00)
 * [6]: Device Model (pro=0x01, ultra=0x02)
 * [7]: Product Color (white=0x01)
 */

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ==================== 设备常量定义 ====================

// 设备名称 (从抓包获取)
#define DEVICE_NAME "CP02-0002A0"

// Service UUID (从 IonBridge Kconfig 确认)
#define SERVICE_UUID "048e3f2e-e1a6-4707-9e74-a930e898a1ea"

// Characteristic TX UUID (Read/Notify) - 设备发送数据给 App
#define CHAR_TX_UUID "148e3f2e-e1a6-4707-9e74-a930e898a1ea"

// Characteristic RX UUID (Write/WriteNoResp) - App 发送数据给设备
#define CHAR_RX_UUID "248e3f2e-e1a6-4707-9e74-a930e898a1ea"

// Company ID (知行小电 / ifanrx)
#define MANUFACTURER_COMPANY_ID 0x36E9

// ==================== 全局变量 ====================

BLEServer *pServer = nullptr;
BLECharacteristic *pCharTX = nullptr;  // Notify
BLECharacteristic *pCharRX = nullptr;  // Write
bool deviceConnected = false;
bool oldDeviceConnected = false;

// LED 指示
#define LED_PIN 2

// ==================== 回调函数 ====================

// Server 回调 - 处理连接和断开事件
class MyServerCallbacks : public BLEServerCallbacks
{
  void onConnect(BLEServer *pServer)
  {
    deviceConnected = true;
    Serial.println("\n========================================");
    Serial.println("[+] Client Connected!");
    Serial.println("========================================\n");

    // LED 亮表示已连接
    digitalWrite(LED_PIN, HIGH);
  }

  void onDisconnect(BLEServer *pServer)
  {
    deviceConnected = false;
    Serial.println("\n========================================");
    Serial.println("[-] Client Disconnected!");
    Serial.println("========================================\n");

    // LED 灭表示等待连接
    digitalWrite(LED_PIN, LOW);

    // 延迟后重启广播
    delay(500);

    // 重新启动广播
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->start();
    Serial.println("[*] Advertising restarted!");
  }
};

// Characteristic RX 回调 - 捕获 App 写入的数据
class RXCharacteristicCallbacks : public BLECharacteristicCallbacks
{
  void onWrite(BLECharacteristic *pCharacteristic)
  {
    String value = pCharacteristic->getValue();

    Serial.println("\n========================================");
    Serial.println("[!] Data Received from App!");
    Serial.println("========================================");

    if (value.length() > 0)
    {
      // 打印数据长度
      Serial.print("Length: ");
      Serial.print(value.length());
      Serial.println(" bytes");

      // 打印 Hex 格式
      Serial.print("Recv HEX: ");
      for (size_t i = 0; i < value.length(); i++)
      {
        Serial.print("0x");
        if (value[i] < 0x10)
        {
          Serial.print("0");
        }
        Serial.print((uint8_t)value[i], HEX);
        if (i < value.length() - 1)
        {
          Serial.print(" ");
        }
      }
      Serial.println();

      // 打印 String/ASCII 格式
      Serial.print("Recv STR: \"");
      for (size_t i = 0; i < value.length(); i++)
      {
        // 只打印可打印字符 (0x20-0x7E)
        if (value[i] >= 0x20 && value[i] <= 0x7E)
        {
          Serial.print((char)value[i]);
        }
        else
        {
          Serial.print(".");
        }
      }
      Serial.println("\"");
    }

    Serial.println("========================================\n");

    // LED 闪烁表示收到数据
    digitalWrite(LED_PIN, LOW);
    delay(100);
    digitalWrite(LED_PIN, HIGH);
  }
};

// ==================== 设置函数 ====================

void setup()
{
  // 初始化 LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // 初始化串口
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n");
  Serial.println("========================================");
  Serial.println("BLE Honeypot for '小电拼' Device");
  Serial.println("========================================");
  Serial.print("Device Name: ");
  Serial.println(DEVICE_NAME);
  Serial.print("Service UUID: ");
  Serial.println(SERVICE_UUID);
  Serial.println("========================================\n");

  // 初始化 BLE 设备
  BLEDevice::init(DEVICE_NAME);

  // 创建 BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // 创建 Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // 创建 TX Characteristic (Read/Notify) - 设备发送数据给 App
  pCharTX = pService->createCharacteristic(
      CHAR_TX_UUID,
      BLECharacteristic::PROPERTY_READ |
          BLECharacteristic::PROPERTY_NOTIFY);

  // 添加 CCC Descriptor (用于 Notify)
  pCharTX->addDescriptor(new BLE2902());

  // 创建 RX Characteristic (Write/WriteNoResp) - App 发送数据给设备
  pCharRX = pService->createCharacteristic(
      CHAR_RX_UUID,
      BLECharacteristic::PROPERTY_WRITE |
          BLECharacteristic::PROPERTY_WRITE_NR);

  // 设置回调函数
  pCharRX->setCallbacks(new RXCharacteristicCallbacks());

  // 启动 Service
  pService->start();

  // ==================== 广播数据配置 ====================
  // 基于 IonBridge 源码分析:
  // - Manufacturer Data: 8 bytes
  // - enableScanResponse(true) 是关键
  // - addServiceUUID() 添加服务 UUID
  
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();

  // 构建 Manufacturer Data (8 bytes)
  // 结构: [Company ID 2B] [MAC后3B] [Family 1B] [Model 1B] [Color 1B]
  uint8_t manufacturerData[8];
  
  // Company ID (Little Endian)
  manufacturerData[0] = MANUFACTURER_COMPANY_ID & 0xFF;        // 0xE9
  manufacturerData[1] = (MANUFACTURER_COMPANY_ID >> 8) & 0xFF; // 0x36
  
  // 从设备名 CP02-0002A0 解析 MAC 后缀
  // 0002A0 -> 0x00, 0x02, 0xA0
  manufacturerData[2] = 0x00;
  manufacturerData[3] = 0x02;
  manufacturerData[4] = 0xA0;
  
  // Product Family: CP02 = 0x00
  manufacturerData[5] = 0x00;
  
  // Device Model: 根据抓包数据，可能是 pro(0x01) 或 ultra(0x02)
  // 从你的原始数据 0x02 来看，应该是 ultra
  manufacturerData[6] = 0x02;
  
  // Product Color: white=0x01
  manufacturerData[7] = 0x01;

  // 打印 Manufacturer Data
  Serial.print("[*] Manufacturer Data: ");
  for (int i = 0; i < 8; i++) {
    Serial.print("0x");
    if (manufacturerData[i] < 0x10) Serial.print("0");
    Serial.print(manufacturerData[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  // 设置广播数据
  BLEAdvertisementData advData;
  
  // 设置 Flags
  advData.setFlags(ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT);
  
  // 设置 Manufacturer Data
  String mfrDataStr;
  for (int i = 0; i < 8; i++) {
    mfrDataStr += (char)manufacturerData[i];
  }
  advData.setManufacturerData(mfrDataStr);
  
  // 应用广播数据
  pAdvertising->setAdvertisementData(advData);

  // 设置扫描响应数据 (关键！)
  BLEAdvertisementData scanRspData;
  scanRspData.setName(DEVICE_NAME);
  scanRspData.setCompleteServices(BLEUUID(SERVICE_UUID));
  pAdvertising->setScanResponseData(scanRspData);

  // 配置广播参数
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMaxPreferred(0x12);

  // 开始广播
  pAdvertising->start();

  Serial.println("[*] BLE Honeypot Started!");
  Serial.println("[*] Advertising...");
  Serial.println("[*] Waiting for connection...\n");

  // LED 亮表示准备就绪
  digitalWrite(LED_PIN, HIGH);
}

// ==================== 主循环 ====================

void loop()
{
  // 检测连接状态变化
  if (!deviceConnected && oldDeviceConnected)
  {
    delay(500);                  // 给蓝牙栈时间
    pServer->startAdvertising(); // 重新启动广播
    Serial.println("[*] Restarting advertising...");
    oldDeviceConnected = deviceConnected;
  }

  // 更新连接状态
  if (deviceConnected && !oldDeviceConnected)
  {
    oldDeviceConnected = deviceConnected;
  }

  delay(100);
}
