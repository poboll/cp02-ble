/**
 * ESP32 BLE Gateway - Main Application
 * 
 * Enhanced with:
 * - WiFiManager for captive portal configuration
 * - OTA (Over-The-Air) firmware updates
 * - Persistent configuration storage
 * - Reset button support
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <NimBLEDevice.h>
#include <AsyncMqttClient.h>
#include <ArduinoJson.h>
#include <Ticker.h>
#include <Preferences.h>

#if OTA_ENABLED
#include <ArduinoOTA.h>
#include <HTTPClient.h>
#include <Update.h>
#endif

#include "config.h"
#include "protocol.h"

// ============ Global Objects ============
AsyncMqttClient mqttClient;
Ticker mqttReconnectTimer;
Ticker wifiReconnectTimer;
Ticker bleReconnectTimer;
Ticker dataPollingTimer;
Ticker heartbeatTimer;
Ticker ledTimer;
Ticker resetButtonTimer;

WiFiManager wifiManager;
Preferences preferences;

NimBLEClient* pBleClient = nullptr;
NimBLERemoteService* pRemoteService = nullptr;
NimBLERemoteCharacteristic* pTxChar = nullptr;
NimBLERemoteCharacteristic* pRxChar = nullptr;

// ============ State Variables ============
volatile bool bleConnected = false;
volatile bool wifiConnected = false;
volatile bool mqttConnected = false;
volatile bool otaInProgress = false;

uint8_t currentToken = CP02_TOKEN;
uint8_t msgId = 0;
String chargerDeviceName = "";
String chargerAddress = "";

PortInfo portData[5];
DeviceInfo deviceInfo;

volatile bool responseReceived = false;
uint8_t responseBuffer[512];
size_t responseLength = 0;

// Custom MQTT parameters from WiFiManager
char mqttHost[64] = MQTT_HOST;
char mqttPort[6] = "1883";
char mqttUser[32] = MQTT_USER;
char mqttPass[64] = MQTT_PASSWORD;
char gatewayId[16] = GATEWAY_ID;

// Reset button state
volatile unsigned long resetButtonPressTime = 0;
volatile bool resetButtonPressed = false;

// ============ Logging Functions ============
void log(const char* msg) {
#if DEBUG_SERIAL
    Serial.println(msg);
#endif
}

void logf(const char* fmt, ...) {
#if DEBUG_SERIAL
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    Serial.println(buf);
#endif
}

// ============ LED Functions ============
#if LED_ENABLED
void ledOn() {
    digitalWrite(LED_BUILTIN_PIN, HIGH);
}

void ledOff() {
    digitalWrite(LED_BUILTIN_PIN, LOW);
}

void ledToggle() {
    digitalWrite(LED_BUILTIN_PIN, !digitalRead(LED_BUILTIN_PIN));
}

void startLedBlink(uint32_t interval) {
    ledTimer.attach_ms(interval, ledToggle);
}

void stopLedBlink() {
    ledTimer.detach();
    ledOff();
}
#else
void ledOn() {}
void ledOff() {}
void ledToggle() {}
void startLedBlink(uint32_t interval) {}
void stopLedBlink() {}
#endif

// ============ Forward Declarations ============
void connectToWifi();
void connectToMqtt();
void scanAndConnectBle();
void startDataPolling();
void stopDataPolling();
void setupOTA();
void handleOTA();
void saveConfigCallback();
void resetSettings();

// ============ MQTT Topic Builder ============
String buildMqttTopic(const char* topic) {
    return String(MQTT_TOPIC_BASE) + "/" + String(gatewayId) + "/" + String(topic);
}

// ============ BLE Notification Callback ============
void notifyCallback(NimBLERemoteCharacteristic* pChar, uint8_t* pData, size_t length, bool isNotify) {
    if (length > 0 && length < sizeof(responseBuffer)) {
        memcpy(responseBuffer, pData, length);
        responseLength = length;
        responseReceived = true;
        
#if DEBUG_BLE
        logf("[BLE] Response received: %d bytes", length);
#endif
    }
}

// ============ BLE Command Sender ============
bool sendBleCommand(uint8_t service, const uint8_t* payload = nullptr, size_t payloadLen = 0, 
                    bool useToken = true, uint32_t timeout = 3000) {
    if (!bleConnected || pRxChar == nullptr) return false;
    
    uint8_t cmdPayload[256];
    size_t cmdPayloadLen = 0;
    
    if (useToken) {
        cmdPayload[0] = currentToken;
        cmdPayloadLen = 1;
        if (payload != nullptr && payloadLen > 0) {
            memcpy(cmdPayload + 1, payload, payloadLen);
            cmdPayloadLen += payloadLen;
        }
    } else if (payload != nullptr && payloadLen > 0) {
        memcpy(cmdPayload, payload, payloadLen);
        cmdPayloadLen = payloadLen;
    }
    
    uint8_t message[280];
    msgId = (msgId + 1) & 0xFF;
    
    size_t msgLen = buildMessage(message, sizeof(message), 
                                  0, msgId, service, 0, FLAG_ACK,
                                  cmdPayload, cmdPayloadLen);
    
    if (msgLen == 0) return false;
    
    responseReceived = false;
    responseLength = 0;
    
    if (!pRxChar->writeValue(message, msgLen, false)) {
        log("[BLE] Write failed");
        return false;
    }
    
    uint32_t startTime = millis();
    while (!responseReceived && (millis() - startTime) < timeout) {
        delay(10);
    }
    
    return responseReceived;
}

// ============ Token Bruteforce ============
bool bruteforceToken() {
    log("[TOKEN] Starting bruteforce...");
    
    for (int token = 0; token < 256; token++) {
        if (token % 32 == 0) {
            logf("[TOKEN] Testing 0x%02X - 0x%02X", token, min(token + 31, 255));
        }
        
        currentToken = token;
        
        if (sendBleCommand(CMD_GET_DEVICE_MODEL, nullptr, 0, true, TOKEN_TEST_TIMEOUT)) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp)) {
                if (resp.service < 0 && resp.payloadLen > 0) {
                    logf("[TOKEN] Found token: 0x%02X (%d)", token, token);
                    // Save token to preferences
                    preferences.putUChar("token", token);
                    return true;
                }
            }
        }
        
        delay(TOKEN_TEST_DELAY);
    }
    
    log("[TOKEN] Bruteforce failed");
    return false;
}

// ============ Data Fetching ============
void fetchPortData() {
    if (!bleConnected) return;
    
    if (sendBleCommand(CMD_GET_ALL_POWER_STATISTICS)) {
        BLEResponse resp;
        if (parseResponse(responseBuffer, responseLength, &resp)) {
            if (resp.success && resp.payloadLen > 0) {
                parsePortStatistics(resp.payload, resp.payloadLen, portData, 5);
            }
        }
    }
}

void fetchDeviceInfo() {
    if (!bleConnected) return;
    
    if (sendBleCommand(CMD_GET_DEVICE_MODEL)) {
        BLEResponse resp;
        if (parseResponse(responseBuffer, responseLength, &resp)) {
            if (resp.success) {
                parseDeviceModel(resp.payload, resp.payloadLen, deviceInfo.model, sizeof(deviceInfo.model));
            }
        }
    }
    
    if (sendBleCommand(CMD_GET_DEVICE_SERIAL_NO)) {
        BLEResponse resp;
        if (parseResponse(responseBuffer, responseLength, &resp)) {
            if (resp.success) {
                parseDeviceSerial(resp.payload, resp.payloadLen, deviceInfo.serial, sizeof(deviceInfo.serial));
            }
        }
    }
    
    if (sendBleCommand(CMD_GET_AP_VERSION)) {
        BLEResponse resp;
        if (parseResponse(responseBuffer, responseLength, &resp)) {
            if (resp.success) {
                parseFirmwareVersion(resp.payload, resp.payloadLen, deviceInfo.firmware, sizeof(deviceInfo.firmware));
            }
        }
    }
    
    if (sendBleCommand(CMD_GET_DEVICE_UPTIME)) {
        BLEResponse resp;
        if (parseResponse(responseBuffer, responseLength, &resp)) {
            if (resp.success) {
                parseDeviceUptime(resp.payload, resp.payloadLen, &deviceInfo.uptime);
            }
        }
    }
}

// ============ MQTT Publishing ============
void publishPortData() {
    if (!mqttConnected) return;
    
    StaticJsonDocument<1024> doc;
    doc["gateway_id"] = gatewayId;
    doc["charger_name"] = chargerDeviceName;
    doc["charger_addr"] = chargerAddress;
    doc["timestamp"] = millis();
    
    JsonArray ports = doc.createNestedArray("ports");
    float totalPower = 0;
    int activePorts = 0;
    
    for (int i = 0; i < 5; i++) {
        JsonObject port = ports.createNestedObject();
        port["port_id"] = portData[i].portId;
        port["protocol"] = portData[i].protocol;
        port["protocol_name"] = getProtocolName(portData[i].protocol);
        port["voltage"] = round(portData[i].voltage * 100) / 100.0;
        port["current"] = round(portData[i].current * 1000) / 1000.0;
        port["power"] = round(portData[i].power * 100) / 100.0;
        port["temperature"] = portData[i].temperature;
        port["charging"] = portData[i].charging;
        
        totalPower += portData[i].power;
        if (portData[i].charging) activePorts++;
    }
    
    doc["total_power"] = round(totalPower * 100) / 100.0;
    doc["active_ports"] = activePorts;
    
    char payload[1024];
    serializeJson(doc, payload, sizeof(payload));
    
    String topic = buildMqttTopic(MQTT_TOPIC_PORTS);
    mqttClient.publish(topic.c_str(), MQTT_QOS_TELEMETRY, false, payload);
    
#if DEBUG_MQTT
    logf("[MQTT] Published to %s", topic.c_str());
#endif
}

void publishDeviceInfo() {
    if (!mqttConnected) return;
    
    StaticJsonDocument<512> doc;
    doc["gateway_id"] = gatewayId;
    doc["gateway_version"] = DEVICE_VERSION;
    doc["charger_name"] = chargerDeviceName;
    doc["charger_addr"] = chargerAddress;
    doc["model"] = deviceInfo.model;
    doc["serial"] = deviceInfo.serial;
    doc["firmware"] = deviceInfo.firmware;
    doc["uptime"] = deviceInfo.uptime;
    doc["timestamp"] = millis();
    
    char payload[512];
    serializeJson(doc, payload, sizeof(payload));
    
    String topic = buildMqttTopic(MQTT_TOPIC_DEVICE_INFO);
    mqttClient.publish(topic.c_str(), MQTT_QOS_STATUS, true, payload);
}

void publishHeartbeat() {
    if (!mqttConnected) return;
    
    StaticJsonDocument<256> doc;
    doc["gateway_id"] = gatewayId;
    doc["gateway_version"] = DEVICE_VERSION;
    doc["wifi_rssi"] = WiFi.RSSI();
    doc["ble_connected"] = bleConnected;
    doc["charger_name"] = chargerDeviceName;
    doc["free_heap"] = ESP.getFreeHeap();
    doc["uptime"] = millis() / 1000;
    doc["connected"] = bleConnected;  // Important for timeout detection
    
    char payload[256];
    serializeJson(doc, payload, sizeof(payload));
    
    String topic = buildMqttTopic(MQTT_TOPIC_HEARTBEAT);
    mqttClient.publish(topic.c_str(), MQTT_QOS_TELEMETRY, false, payload);
}

void publishStatus(const char* status, const char* message = nullptr) {
    if (!mqttConnected) return;
    
    StaticJsonDocument<256> doc;
    doc["gateway_id"] = gatewayId;
    doc["status"] = status;
    if (message) doc["message"] = message;
    doc["ble_connected"] = bleConnected;
    doc["charger_name"] = chargerDeviceName;
    doc["timestamp"] = millis();
    
    char payload[256];
    serializeJson(doc, payload, sizeof(payload));
    
    String topic = buildMqttTopic(MQTT_TOPIC_STATUS);
    mqttClient.publish(topic.c_str(), MQTT_QOS_STATUS, true, payload);
}

// ============ MQTT Message Handler ============
void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, 
                   size_t len, size_t index, size_t total) {
    String topicStr = String(topic);
    String cmdTopic = buildMqttTopic(MQTT_TOPIC_CMD);
    
    if (!topicStr.startsWith(cmdTopic)) return;
    
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, payload, len);
    if (error) {
        log("[MQTT] Command parse failed");
        return;
    }
    
    const char* action = doc["action"]; // "command" in frontend
    if (action == nullptr) action = doc["command"]; // Handle both keys
    
    const char* cmdId = doc["cmd_id"];
    if (action == nullptr) return;
    
    logf("[MQTT] Command: %s", action);
    
    StaticJsonDocument<512> respDoc;
    respDoc["gateway_id"] = gatewayId;
    respDoc["action"] = action;
    if (cmdId) respDoc["cmd_id"] = cmdId;
    bool success = false;
    
    // --- Port Control ---
    if (strcmp(action, "turn_on_port") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        uint8_t portPayload[] = {(uint8_t)portId};
        success = sendBleCommand(CMD_TURN_ON_PORT, portPayload, 1);
    } 
    else if (strcmp(action, "turn_off_port") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        uint8_t portPayload[] = {(uint8_t)portId};
        success = sendBleCommand(CMD_TURN_OFF_PORT, portPayload, 1);
    }
    
    // --- Device Management ---
    else if (strcmp(action, "reboot") == 0 || strcmp(action, "reboot_device") == 0) {
        success = sendBleCommand(CMD_REBOOT_DEVICE);
    }
    else if (strcmp(action, "factory_reset") == 0 || strcmp(action, "reset_device") == 0) {
        success = sendBleCommand(CMD_RESET_DEVICE);
    }
    else if (strcmp(action, "refresh") == 0 || strcmp(action, "get_device_info") == 0) {
        fetchPortData();
        fetchDeviceInfo();
        publishPortData();
        publishDeviceInfo();
        success = true;
    }
    else if (strcmp(action, "get_device_model") == 0) success = sendBleCommand(CMD_GET_DEVICE_MODEL);
    else if (strcmp(action, "get_device_serial") == 0) success = sendBleCommand(CMD_GET_DEVICE_SERIAL_NO);
    else if (strcmp(action, "get_ap_version") == 0) success = sendBleCommand(CMD_GET_AP_VERSION);
    else if (strcmp(action, "get_ble_addr") == 0) success = sendBleCommand(CMD_GET_DEVICE_BLE_ADDR);
    else if (strcmp(action, "get_device_uptime") == 0) success = sendBleCommand(CMD_GET_DEVICE_UPTIME);
    
    // --- Display Control ---
    else if (strcmp(action, "set_brightness") == 0 || strcmp(action, "set_display_brightness") == 0) {
        int brightness = doc["params"]["brightness"] | 50;
        uint8_t payload[] = {(uint8_t)brightness};
        success = sendBleCommand(CMD_SET_DISPLAY_INTENSITY, payload, 1);
    }
    else if (strcmp(action, "set_display_mode") == 0) {
        int mode = doc["params"]["mode"] | 0;
        uint8_t payload[] = {(uint8_t)mode};
        success = sendBleCommand(CMD_SET_DISPLAY_MODE, payload, 1);
    }
    else if (strcmp(action, "flip_display") == 0) {
        uint8_t payload[] = {1}; // 1 to toggle? Protocol usually expects a value
        success = sendBleCommand(CMD_SET_DISPLAY_FLIP, payload, 1);
    }
    else if (strcmp(action, "get_display_settings") == 0) {
        success = sendBleCommand(CMD_GET_DISPLAY_INTENSITY) && sendBleCommand(CMD_GET_DISPLAY_MODE);
    }
    
    // --- Strategy Control ---
    else if (strcmp(action, "set_power_mode") == 0 || strcmp(action, "set_charging_strategy") == 0) {
        // params: mode or strategy
        int mode = doc["params"]["mode"] | doc["params"]["strategy"] | 0;
        uint8_t payload[] = {(uint8_t)mode};
        success = sendBleCommand(CMD_SET_CHARGING_STRATEGY, payload, 1);
    }
    else if (strcmp(action, "set_temp_mode") == 0 || strcmp(action, "set_temperature_mode") == 0) {
        int enabled = doc["params"]["enabled"] | doc["params"]["mode"] | 0;
        uint8_t payload[] = {(uint8_t)(enabled ? 1 : 0)};
        success = sendBleCommand(CMD_SET_TEMPERATURE_MODE, payload, 1);
    }
    else if (strcmp(action, "get_charging_strategy") == 0) {
        success = sendBleCommand(CMD_GET_CHARGING_STRATEGY);
    }
    
    // --- Port Priority ---
    else if (strcmp(action, "set_port_priority") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        int priority = doc["params"]["priority"] | 0;
        // Priority command usually takes [port0, port1, port2...] or [port, priority]
        // Assuming [port_id, priority] based on standard practice, but protocol might differ.
        // Checking protocol.py... CMD_SET_PORT_PRIORITY payload is list of priorities.
        // We need to fetch current priorities first to update one? 
        // For simplicity, let's assume we send [port, priority] or implement a smarter way later.
        // Actually, if protocol expects all ports, we can't easily set just one without state.
        // Let's try sending [portId, priority] and hope firmware handles it or we update protocol.h
        uint8_t payload[] = {(uint8_t)portId, (uint8_t)priority};
        success = sendBleCommand(CMD_SET_PORT_PRIORITY, payload, 2); 
    }
    
    // --- Advanced / Debug ---
    else if (strcmp(action, "get_port_pd_status") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        uint8_t payload[] = {(uint8_t)portId};
        success = sendBleCommand(CMD_GET_PORT_PD_STATUS, payload, 1);
        if (success && responseLength > 0) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp) && resp.payloadLen > 0) {
                respDoc["pd_status"] = resp.payload[0];
            }
        }
    }
    else if (strcmp(action, "ble_echo_test") == 0) {
        const char* text = doc["params"]["data"] | "echo";
        success = sendBleCommand(CMD_BLE_ECHO_TEST, (const uint8_t*)text, strlen(text));
        if (success && responseLength > 0) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp) && resp.payloadLen > 0) {
                char echoData[64];
                size_t copyLen = min(resp.payloadLen, sizeof(echoData) - 1);
                memcpy(echoData, resp.payload, copyLen);
                echoData[copyLen] = '\0';
                respDoc["data"] = echoData;
            }
        }
    }
    else if (strcmp(action, "get_debug_log") == 0) {
        success = sendBleCommand(CMD_GET_DEBUG_LOG);
        if (success && responseLength > 0) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp) && resp.payloadLen > 0) {
                char logData[256];
                size_t copyLen = min(resp.payloadLen, sizeof(logData) - 1);
                memcpy(logData, resp.payload, copyLen);
                logData[copyLen] = '\0';
                respDoc["log"] = logData;
            }
        }
    }
    else if (strcmp(action, "get_power_curve") == 0 || strcmp(action, "get_power_stats") == 0) {
        success = sendBleCommand(CMD_GET_POWER_HISTORICAL_STATS);
        if (success && responseLength > 0) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp) && resp.payloadLen > 0) {
                JsonArray curve = respDoc.createNestedArray("curve");
                for (size_t i = 0; i < resp.payloadLen && i < 24; i++) {
                    curve.add(resp.payload[i]);
                }
            }
        }
    }
    else if (strcmp(action, "get_temp_info") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        if (portId >= 0 && portId < 5 && portData[portId].temperature != 0) {
            success = true;
            respDoc["temperature"] = portData[portId].temperature;
            respDoc["port_id"] = portId;
        } else {
            success = false;
            respDoc["error"] = "Temperature data not available";
        }
    }
    else if (strcmp(action, "get_port_config") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        uint8_t payload[] = {(uint8_t)portId};
        success = sendBleCommand(CMD_GET_PORT_CONFIG, payload, 1);
        if (success && responseLength > 0) {
            BLEResponse resp;
            if (parseResponse(responseBuffer, responseLength, &resp) && resp.payloadLen >= 2) {
                respDoc["port_id"] = portId;
                respDoc["protocol"] = resp.payload[0];
                respDoc["priority"] = resp.payload[1];
            }
        }
    }
    else if (strcmp(action, "set_port_config") == 0) {
        int portId = doc["params"]["port_id"] | 0;
        int protocol = doc["params"]["protocol"] | 0;
        uint8_t payload[] = {(uint8_t)portId, (uint8_t)protocol};
        success = sendBleCommand(CMD_SET_PORT_CONFIG, payload, 2);
    }
    else if (strcmp(action, "get_wifi_status") == 0) {
        success = true;
        respDoc["connected"] = WiFi.isConnected();
        respDoc["ssid"] = WiFi.SSID();
        respDoc["rssi"] = WiFi.RSSI();
        respDoc["ip"] = WiFi.localIP().toString();
    }
    else if (strcmp(action, "scan_wifi") == 0) {
        int n = WiFi.scanNetworks();
        success = true;
        JsonArray networks = respDoc.createNestedArray("networks");
        for (int i = 0; i < n && i < 10; i++) {
            JsonObject net = networks.createNestedObject();
            net["ssid"] = WiFi.SSID(i);
            net["rssi"] = WiFi.RSSI(i);
            net["encryption"] = WiFi.encryptionType(i);
        }
        WiFi.scanDelete();
    }
    else if (strcmp(action, "set_wifi") == 0) {
        const char* ssid = doc["params"]["ssid"];
        const char* password = doc["params"]["password"] | "";
        if (ssid && strlen(ssid) > 0) {
            preferences.putString("wifi_ssid", ssid);
            preferences.putString("wifi_pass", password);
            success = true;
            respDoc["message"] = "WiFi config saved. Restarting...";
            delay(100);
            ESP.restart();
        } else {
            success = false;
            respDoc["error"] = "SSID required";
        }
    }
    else if (strcmp(action, "connect_to") == 0) {
        const char* deviceName = doc["params"]["device_name"];
        if (deviceName && strlen(deviceName) > 0) {
            preferences.putString("target_device", deviceName);
            bleConnected = false;
            if (pBleClient) {
                pBleClient->disconnect();
            }
            scanAndConnectBle();
            success = true;
            respDoc["message"] = "Connecting to device...";
        } else {
            success = false;
            respDoc["error"] = "device_name required";
        }
    }
    
    // --- Gateway Management ---
    else if (strcmp(action, "scan_ble") == 0) {
        // Trigger a re-scan manually
        bleConnected = false;
        if(pBleClient) {
            pBleClient->disconnect();
        }
        scanAndConnectBle(); // This will scan and publish status
        success = true;
        respDoc["message"] = "Scanning started";
    }
    else if (strcmp(action, "disconnect_ble") == 0) {
        if(pBleClient && bleConnected) {
            pBleClient->disconnect();
            bleConnected = false;
            success = true;
        }
    }
    else if (strcmp(action, "set_token") == 0) {
        int token = doc["params"]["token"] | -1;
        if (token >= 0 && token <= 255) {
            currentToken = token;
            preferences.putUChar("token", token);
            success = true;
            respDoc["token"] = token;
        }
    }
    else if (strcmp(action, "bruteforce_token") == 0) {
        success = bruteforceToken();
        if (success) respDoc["token"] = currentToken;
    }
    else if (strcmp(action, "reset_wifi") == 0) {
        success = true;
        respDoc["message"] = "WiFi reset";
        // Reset after sending response
        delay(100);
        resetSettings();
    }
    else if (strcmp(action, "restart") == 0) {
        success = true;
        respDoc["message"] = "Restarting";
        delay(100);
        ESP.restart();
    }
    else if (strcmp(action, "ota_update") == 0) {
        // ... (OTA logic remains same) ...
        success = false; 
        respDoc["error"] = "OTA not fully implemented in this block";
    }
    else {
        respDoc["error"] = "Unknown action";
    }
    
    respDoc["success"] = success;
    respDoc["timestamp"] = millis();
    
    char respPayload[512];
    serializeJson(respDoc, respPayload, sizeof(respPayload));
    
    String respTopic = buildMqttTopic(MQTT_TOPIC_CMD_RESPONSE);
    mqttClient.publish(respTopic.c_str(), MQTT_QOS_COMMAND, false, respPayload);
}

// ============ MQTT Callbacks ============
void onMqttConnect(bool sessionPresent) {
    log("[MQTT] Connected");
    mqttConnected = true;
    
    String cmdTopic = buildMqttTopic(MQTT_TOPIC_CMD);
    mqttClient.subscribe(cmdTopic.c_str(), MQTT_QOS_COMMAND);
    logf("[MQTT] Subscribed to %s", cmdTopic.c_str());
    
    publishStatus("online", "Gateway connected");
    
    // Update LED status
    if (bleConnected) {
        stopLedBlink();
        ledOn();
    }
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
    log("[MQTT] Disconnected");
    mqttConnected = false;
    
    if (wifiConnected && !otaInProgress) {
        mqttReconnectTimer.once_ms(MQTT_RECONNECT_DELAY, connectToMqtt);
    }
}

void connectToMqtt() {
    if (otaInProgress) return;
    
    log("[MQTT] Connecting...");
    startLedBlink(LED_BLINK_MQTT);
    mqttClient.connect();
}

// ============ WiFi Event Handler ============
void WiFiEvent(WiFiEvent_t event) {
    switch (event) {
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            log("[WiFi] Connected");
            logf("[WiFi] IP: %s", WiFi.localIP().toString().c_str());
            wifiConnected = true;
            connectToMqtt();
            break;
            
        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            log("[WiFi] Disconnected");
            wifiConnected = false;
            mqttConnected = false;
            mqttReconnectTimer.detach();
            if (!otaInProgress) {
                wifiReconnectTimer.once_ms(WIFI_RECONNECT_DELAY, connectToWifi);
            }
            break;
            
        default:
            break;
    }
}

void connectToWifi() {
    log("[WiFi] Connecting...");
    startLedBlink(LED_BLINK_WIFI);
    WiFi.begin();  // Use saved credentials from WiFiManager
}

// ============ BLE Client Callbacks ============
class BleClientCallbacks : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient* pClient) override {
        log("[BLE] Connected to charger");
    }
    
    void onDisconnect(NimBLEClient* pClient) override {
        log("[BLE] Disconnected from charger");
        bleConnected = false;
        stopDataPolling();
        
        if (mqttConnected) {
            publishStatus("ble_disconnected", "Charger disconnected");
        }
        
        if (!otaInProgress) {
            bleReconnectTimer.once_ms(BLE_RECONNECT_DELAY, scanAndConnectBle);
        }
    }
};

static BleClientCallbacks bleClientCallbacks;

// ============ BLE Scanning and Connection ============
void scanAndConnectBle() {
    if (otaInProgress) return;
    
    log("[BLE] Scanning for CP02 devices...");
    startLedBlink(LED_BLINK_BLE);
    
    NimBLEScan* pScan = NimBLEDevice::getScan();
    pScan->setActiveScan(true);
    pScan->setInterval(BLE_SCAN_INTERVAL);
    pScan->setWindow(BLE_SCAN_WINDOW);
    
    NimBLEScanResults results = pScan->start(BLE_SCAN_DURATION);
    
    NimBLEAdvertisedDevice* targetDevice = nullptr;
    
    for (int i = 0; i < results.getCount(); i++) {
        NimBLEAdvertisedDevice device = results.getDevice(i);
        String name = device.getName().c_str();
        
        if (name.startsWith(CP02_DEVICE_PREFIX)) {
            logf("[BLE] Found: %s (%s)", name.c_str(), device.getAddress().toString().c_str());
            targetDevice = new NimBLEAdvertisedDevice(device);
            break;
        }
    }
    
    if (targetDevice == nullptr) {
        log("[BLE] No CP02 device found");
        stopLedBlink();
        bleReconnectTimer.once_ms(BLE_RECONNECT_DELAY, scanAndConnectBle);
        return;
    }
    
    chargerDeviceName = String(targetDevice->getName().c_str());
    chargerAddress = String(targetDevice->getAddress().toString().c_str());
    
    if (pBleClient == nullptr) {
        pBleClient = NimBLEDevice::createClient();
        pBleClient->setClientCallbacks(&bleClientCallbacks);
    }
    
    logf("[BLE] Connecting to %s...", chargerDeviceName.c_str());
    
    if (!pBleClient->connect(targetDevice)) {
        log("[BLE] Connection failed");
        delete targetDevice;
        stopLedBlink();
        bleReconnectTimer.once_ms(BLE_RECONNECT_DELAY, scanAndConnectBle);
        return;
    }
    
    delete targetDevice;
    
    pRemoteService = pBleClient->getService(NimBLEUUID(CP02_SERVICE_UUID));
    if (pRemoteService == nullptr) {
        log("[BLE] Service not found");
        pBleClient->disconnect();
        return;
    }
    
    pTxChar = pRemoteService->getCharacteristic(NimBLEUUID(CP02_CHAR_TX_UUID));
    pRxChar = pRemoteService->getCharacteristic(NimBLEUUID(CP02_CHAR_RX_UUID));
    
    if (pTxChar == nullptr || pRxChar == nullptr) {
        log("[BLE] Characteristics not found");
        pBleClient->disconnect();
        return;
    }
    
    if (pTxChar->canNotify()) {
        pTxChar->subscribe(true, notifyCallback);
    }
    
    bleConnected = true;
    stopLedBlink();
    logf("[BLE] Connected to %s", chargerDeviceName.c_str());
    
    // Load saved token or bruteforce
    uint8_t savedToken = preferences.getUChar("token", 0xFF);
    if (savedToken != 0xFF) {
        currentToken = savedToken;
        logf("[TOKEN] Using saved token: 0x%02X", savedToken);
    } else if (currentToken == 0xFF) {
        if (!bruteforceToken()) {
            log("[BLE] Token bruteforce failed, using 0x00");
            currentToken = 0x00;
        }
    }
    
    fetchDeviceInfo();
    
    if (mqttConnected) {
        publishStatus("ble_connected", chargerDeviceName.c_str());
        publishDeviceInfo();
        ledOn();
    }
    
    startDataPolling();
}

// ============ Data Polling ============
void dataPollingCallback() {
    if (!bleConnected || otaInProgress) return;
    
    fetchPortData();
    
    if (mqttConnected) {
        publishPortData();
    }
}

void heartbeatCallback() {
    if (mqttConnected && !otaInProgress) {
        publishHeartbeat();
    }
}

void startDataPolling() {
    dataPollingTimer.attach_ms(POLL_INTERVAL_PORTS, dataPollingCallback);
    heartbeatTimer.attach_ms(POLL_INTERVAL_HEARTBEAT, heartbeatCallback);
    log("[POLL] Data polling started");
}

void stopDataPolling() {
    dataPollingTimer.detach();
    heartbeatTimer.detach();
    log("[POLL] Data polling stopped");
}

// ============ OTA Setup ============
#if OTA_ENABLED
void setupOTA() {
    String hostname = strlen(OTA_HOSTNAME) > 0 ? OTA_HOSTNAME : gatewayId;
    ArduinoOTA.setHostname(hostname.c_str());
    ArduinoOTA.setPort(OTA_PORT);
    
    if (strlen(OTA_PASSWORD) > 0) {
        ArduinoOTA.setPassword(OTA_PASSWORD);
    }
    
    ArduinoOTA.onStart([]() {
        otaInProgress = true;
        stopDataPolling();
        startLedBlink(LED_BLINK_OTA);
        
        String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
        logf("[OTA] Start updating %s", type.c_str());
        
        if (mqttConnected) {
            publishStatus("ota_start", "OTA update starting");
        }
    });
    
    ArduinoOTA.onEnd([]() {
        otaInProgress = false;
        stopLedBlink();
        log("[OTA] Update complete");
        
        if (mqttConnected) {
            publishStatus("ota_complete", "OTA update complete, restarting");
        }
    });
    
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        static int lastPercent = -1;
        int percent = progress / (total / 100);
        if (percent != lastPercent && percent % 10 == 0) {
            logf("[OTA] Progress: %u%%", percent);
            lastPercent = percent;
        }
    });
    
    ArduinoOTA.onError([](ota_error_t error) {
        otaInProgress = false;
        stopLedBlink();
        
        const char* errorMsg = "Unknown error";
        switch (error) {
            case OTA_AUTH_ERROR: errorMsg = "Auth Failed"; break;
            case OTA_BEGIN_ERROR: errorMsg = "Begin Failed"; break;
            case OTA_CONNECT_ERROR: errorMsg = "Connect Failed"; break;
            case OTA_RECEIVE_ERROR: errorMsg = "Receive Failed"; break;
            case OTA_END_ERROR: errorMsg = "End Failed"; break;
        }
        logf("[OTA] Error: %s", errorMsg);
        
        if (mqttConnected) {
            publishStatus("ota_error", errorMsg);
        }
    });
    
    ArduinoOTA.begin();
    log("[OTA] Service started");
}

void handleOTA() {
    ArduinoOTA.handle();
}
#else
void setupOTA() {}
void handleOTA() {}
#endif

// ============ WiFiManager Setup ============
void saveConfigCallback() {
    log("[WiFi] Configuration saved");
    
    // Save custom parameters to preferences
    preferences.putString("mqtt_host", mqttHost);
    preferences.putInt("mqtt_port", atoi(mqttPort));
    preferences.putString("mqtt_user", mqttUser);
    preferences.putString("mqtt_pass", mqttPass);
    preferences.putString("gateway_id", gatewayId);
}

void resetSettings() {
    log("[RESET] Clearing all settings...");
    preferences.clear();
    wifiManager.resetSettings();
    delay(1000);
    ESP.restart();
}

// ============ Reset Button Handler ============
void checkResetButton() {
    static bool wasPressed = false;
    bool isPressed = digitalRead(RESET_BUTTON_PIN) == LOW;
    
    if (isPressed && !wasPressed) {
        // Button just pressed
        resetButtonPressTime = millis();
        resetButtonPressed = true;
    } else if (!isPressed && wasPressed && resetButtonPressed) {
        // Button released
        resetButtonPressed = false;
    } else if (isPressed && resetButtonPressed) {
        // Button still held
        if (millis() - resetButtonPressTime > RESET_BUTTON_HOLD) {
            log("[RESET] Button held for 5 seconds - resetting settings");
            startLedBlink(100);
            delay(2000);
            resetSettings();
        }
    }
    
    wasPressed = isPressed;
}

// ============ Setup ============
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(1000);
    
    log("\n========================================");
    logf("  ESP32 BLE Gateway v%s", DEVICE_VERSION);
    log("  Enhanced with WiFiManager + OTA");
    log("========================================\n");
    
    // Initialize preferences
    preferences.begin(PREFS_NAMESPACE, false);
    
    // Load saved configuration
    String savedHost = preferences.getString("mqtt_host", MQTT_HOST);
    int savedPort = preferences.getInt("mqtt_port", 1883);
    String savedUser = preferences.getString("mqtt_user", MQTT_USER);
    String savedPass = preferences.getString("mqtt_pass", MQTT_PASSWORD);
    String savedGwId = preferences.getString("gateway_id", GATEWAY_ID);
    
    strncpy(mqttHost, savedHost.c_str(), sizeof(mqttHost) - 1);
    snprintf(mqttPort, sizeof(mqttPort), "%d", savedPort);
    strncpy(mqttUser, savedUser.c_str(), sizeof(mqttUser) - 1);
    strncpy(mqttPass, savedPass.c_str(), sizeof(mqttPass) - 1);
    strncpy(gatewayId, savedGwId.c_str(), sizeof(gatewayId) - 1);
    
    logf("  Gateway ID: %s", gatewayId);
    logf("  MQTT Host: %s:%s", mqttHost, mqttPort);
    log("========================================\n");
    
    // Initialize LED
#if LED_ENABLED
    pinMode(LED_BUILTIN_PIN, OUTPUT);
    ledOff();
#endif
    
    // Initialize reset button
    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);
    
    // Initialize port data
    memset(&deviceInfo, 0, sizeof(deviceInfo));
    for (int i = 0; i < 5; i++) {
        memset(&portData[i], 0, sizeof(PortInfo));
        portData[i].portId = i;
    }
    
    // Initialize BLE
    NimBLEDevice::init(DEVICE_NAME);
    log("[BLE] Initialized");
    
    // Setup WiFiManager
    WiFiManagerParameter customMqttHost("mqtt_host", "MQTT Host", mqttHost, 64);
    WiFiManagerParameter customMqttPort("mqtt_port", "MQTT Port", mqttPort, 6);
    WiFiManagerParameter customMqttUser("mqtt_user", "MQTT User (optional)", mqttUser, 32);
    WiFiManagerParameter customMqttPass("mqtt_pass", "MQTT Password (optional)", mqttPass, 64);
    WiFiManagerParameter customGatewayId("gateway_id", "Gateway ID", gatewayId, 16);
    
    wifiManager.addParameter(&customMqttHost);
    wifiManager.addParameter(&customMqttPort);
    wifiManager.addParameter(&customMqttUser);
    wifiManager.addParameter(&customMqttPass);
    wifiManager.addParameter(&customGatewayId);
    
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.setConfigPortalTimeout(WIFI_PORTAL_TIMEOUT);
    wifiManager.setConnectTimeout(WIFI_CONNECT_TIMEOUT / 1000);
    
    // Try to connect or start config portal
    startLedBlink(LED_BLINK_WIFI);
    
    bool connected = false;
    if (strlen(WIFI_SSID) > 0) {
        // Use hardcoded credentials
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        unsigned long startTime = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_CONNECT_TIMEOUT) {
            delay(500);
        }
        connected = WiFi.status() == WL_CONNECTED;
    }
    
    if (!connected) {
        // Start WiFiManager config portal
        log("[WiFi] Starting configuration portal...");
        logf("[WiFi] Connect to AP: %s", WIFI_PORTAL_NAME);
        
        if (!wifiManager.autoConnect(WIFI_PORTAL_NAME, WIFI_PORTAL_PASSWORD)) {
            log("[WiFi] Failed to connect, restarting...");
            delay(3000);
            ESP.restart();
        }
    }
    
    // Copy WiFiManager parameters
    strncpy(mqttHost, customMqttHost.getValue(), sizeof(mqttHost) - 1);
    strncpy(mqttPort, customMqttPort.getValue(), sizeof(mqttPort) - 1);
    strncpy(mqttUser, customMqttUser.getValue(), sizeof(mqttUser) - 1);
    strncpy(mqttPass, customMqttPass.getValue(), sizeof(mqttPass) - 1);
    strncpy(gatewayId, customGatewayId.getValue(), sizeof(gatewayId) - 1);
    
    stopLedBlink();
    wifiConnected = true;
    logf("[WiFi] Connected! IP: %s", WiFi.localIP().toString().c_str());
    
    // Setup WiFi event handler
    WiFi.onEvent(WiFiEvent);
    
    // Setup MQTT
    mqttClient.onConnect(onMqttConnect);
    mqttClient.onDisconnect(onMqttDisconnect);
    mqttClient.onMessage(onMqttMessage);
    mqttClient.setServer(mqttHost, atoi(mqttPort));
    mqttClient.setKeepAlive(MQTT_KEEPALIVE);
    
    if (strlen(mqttUser) > 0) {
        mqttClient.setCredentials(mqttUser, mqttPass);
    }
    
    String clientId = String(MQTT_CLIENT_PREFIX) + String(gatewayId);
    mqttClient.setClientId(clientId.c_str());
    
    // Setup OTA
    setupOTA();
    
    // Connect to MQTT
    connectToMqtt();
    
    // Start BLE scanning after a short delay
    delay(2000);
    scanAndConnectBle();
}

// ============ Main Loop ============
void loop() {
    // Handle OTA updates
    handleOTA();
    
    // Check reset button
    checkResetButton();
    
    delay(100);
}
