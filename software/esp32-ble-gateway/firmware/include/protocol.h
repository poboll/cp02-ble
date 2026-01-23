/**
 * CP02 BLE Protocol Definitions
 * 
 * Ported from protocol.py - IonBridge BLE Protocol
 * Complete protocol implementation for CP02 charging station
 */

#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <Arduino.h>

// ============ BLE UUIDs ============
extern const char* SERVICE_UUID;
extern const char* CHAR_TX_UUID;
extern const char* CHAR_RX_UUID;
extern const char* DEVICE_PREFIX;

// ============ BLE Message Flags ============
enum BLEFlags {
    FLAG_NONE = 0x0,
    FLAG_SYN = 0x1,
    FLAG_ACK = 0x2,
    FLAG_FIN = 0x3,
    FLAG_RST = 0x4,
    FLAG_SYN_ACK = 0x5
};

// ============ Service Commands ============
enum ServiceCommand {
    // Test commands (0x00-0x09)
    CMD_BLE_ECHO_TEST = 0x00,
    CMD_GET_DEBUG_LOG = 0x01,
    CMD_GET_SECURE_BOOT_DIGEST = 0x02,
    CMD_PING_MQTT_TELEMETRY = 0x03,
    CMD_PING_HTTP = 0x04,
    CMD_GET_DEVICE_PASSWORD = 0x05,
    CMD_MANAGE_POWER_ALLOCATOR_ENABLED = 0x09,
    
    // Device management (0x10-0x1F)
    CMD_ASSOCIATE_DEVICE = 0x10,
    CMD_REBOOT_DEVICE = 0x11,
    CMD_RESET_DEVICE = 0x12,
    CMD_GET_DEVICE_SERIAL_NO = 0x13,
    CMD_GET_DEVICE_UPTIME = 0x14,
    CMD_GET_AP_VERSION = 0x15,
    CMD_GET_BP_VERSION = 0x16,
    CMD_GET_FPGA_VERSION = 0x17,
    CMD_GET_ZRLIB_VERSION = 0x18,
    CMD_GET_DEVICE_BLE_ADDR = 0x19,
    CMD_SWITCH_DEVICE = 0x1A,
    CMD_GET_DEVICE_SWITCH = 0x1B,
    CMD_GET_DEVICE_MODEL = 0x1C,
    CMD_PUSH_LICENSE = 0x1D,
    CMD_GET_BLE_RSSI = 0x1E,
    CMD_GET_BLE_MTU = 0x1F,
    
    // OTA commands (0x20-0x2F)
    CMD_PERFORM_BLE_OTA = 0x20,
    CMD_PERFORM_WIFI_OTA = 0x21,
    CMD_GET_WIFI_OTA_PROGRESS = 0x22,
    CMD_CONFIRM_OTA = 0x23,
    
    // WiFi commands (0x30-0x3F)
    CMD_SCAN_WIFI = 0x30,
    CMD_GET_WIFI_SCAN_RESULT = 0x31,
    CMD_SET_WIFI_SSID = 0x32,
    CMD_RESET_WIFI = 0x33,
    CMD_GET_WIFI_STATUS = 0x34,
    CMD_GET_DEVICE_WIFI_ADDR = 0x35,
    CMD_SET_WIFI_SSID_AND_PASSWORD = 0x36,
    CMD_GET_WIFI_RECORDS = 0x37,
    CMD_OPERATE_WIFI_RECORD = 0x38,
    CMD_GET_WIFI_STATE_MACHINE = 0x39,
    CMD_SET_WIFI_STATE_MACHINE = 0x3A,
    
    // Power commands (0x40-0x5F)
    CMD_TOGGLE_PORT_POWER = 0x40,
    CMD_GET_POWER_STATISTICS = 0x41,
    CMD_GET_POWER_SUPPLY_STATUS = 0x42,
    CMD_SET_CHARGING_STRATEGY = 0x43,
    CMD_GET_CHARGING_STATUS = 0x44,
    CMD_GET_POWER_HISTORICAL_STATS = 0x45,
    CMD_SET_PORT_PRIORITY = 0x46,
    CMD_GET_PORT_PRIORITY = 0x47,
    CMD_GET_CHARGING_STRATEGY = 0x48,
    CMD_GET_PORT_PD_STATUS = 0x49,
    CMD_GET_ALL_POWER_STATISTICS = 0x4A,
    CMD_GET_START_CHARGE_TIMESTAMP = 0x4B,
    CMD_TURN_ON_PORT = 0x4C,
    CMD_TURN_OFF_PORT = 0x4D,
    CMD_SET_STATIC_ALLOCATOR = 0x55,
    CMD_GET_STATIC_ALLOCATOR = 0x56,
    CMD_SET_PORT_CONFIG = 0x57,
    CMD_GET_PORT_CONFIG = 0x58,
    CMD_SET_PORT_COMPATIBILITY_SETTINGS = 0x59,
    CMD_GET_PORT_COMPATIBILITY_SETTINGS = 0x5A,
    CMD_SET_TEMPERATURE_MODE = 0x5B,
    CMD_SET_TEMPORARY_ALLOCATOR = 0x5C,
    CMD_SET_PORT_CONFIG1 = 0x5D,
    CMD_GET_PORT_CONFIG1 = 0x5E,
    
    // Display commands (0x70-0x7F)
    CMD_SET_DISPLAY_INTENSITY = 0x70,
    CMD_SET_DISPLAY_MODE = 0x71,
    CMD_GET_DISPLAY_INTENSITY = 0x72,
    CMD_GET_DISPLAY_MODE = 0x73,
    CMD_SET_DISPLAY_FLIP = 0x74,
    CMD_GET_DISPLAY_FLIP = 0x75,
    CMD_SET_DISPLAY_CONFIG = 0x76,
    CMD_SET_DISPLAY_STATE = 0x77,
    CMD_GET_DISPLAY_STATE = 0x78,
    
    // System commands (0x90-0x9F)
    CMD_START_TELEMETRY_STREAM = 0x90,
    CMD_STOP_TELEMETRY_STREAM = 0x91,
    CMD_GET_DEVICE_INFO = 0x92,
    CMD_SET_BLE_STATE = 0x98,
    CMD_SET_SYSLOG_STATE = 0x99,
    CMD_SET_SYSTEM_TIME = 0x9A,
    CMD_START_OTA = 0x9C,
    
    // Feature management (0x0A-0x0C)
    CMD_MANAGE_POWER_CONFIG = 0x0A,
    CMD_MANAGE_FEATURE_TOGGLE = 0x0B,
    CMD_ENABLE_RELEASE_MODE = 0x0C
};

// ============ Fast Charging Protocols ============
const char* getProtocolName(uint8_t protocol);

// Protocol values from data_types.h
enum FastChargingProtocol {
    PROTOCOL_NONE = 0,
    PROTOCOL_QC2_0 = 1,
    PROTOCOL_QC3_0 = 2,
    PROTOCOL_QC3_PLUS = 3,
    PROTOCOL_SFCP = 4,
    PROTOCOL_AFC = 5,
    PROTOCOL_FCP = 6,
    PROTOCOL_SCP = 7,
    PROTOCOL_VOOC1_0 = 8,
    PROTOCOL_VOOC4_0 = 9,
    PROTOCOL_SUPERVOOC2_0 = 10,
    PROTOCOL_TFCP = 11,
    PROTOCOL_UFCS = 12,
    PROTOCOL_PE1_0 = 13,
    PROTOCOL_PE2_0 = 14,
    PROTOCOL_PD_5V = 15,
    PROTOCOL_PD_HV = 16,
    PROTOCOL_PD_SPR_AVS = 17,
    PROTOCOL_PD_PPS = 18,
    PROTOCOL_PD_EPR_HV = 19,
    PROTOCOL_PD_AVS = 20,
    PROTOCOL_NOT_CHARGING = 0xFF
};

// ============ Charging Strategy Types ============
enum StrategyType {
    STRATEGY_SLOW_CHARGING = 0,
    STRATEGY_STATIC_CHARGING = 1,
    STRATEGY_TEMPORARY_CHARGING = 2,
    STRATEGY_USBA_CHARGING = 3
};

// ============ Data Structures ============

// Port information structure
struct PortInfo {
    uint8_t portId;
    uint8_t protocol;       // Fast charging protocol
    float voltage;          // Voltage in V
    float current;          // Current in A
    float power;            // Power in W
    int8_t temperature;     // Temperature in °C
    bool charging;          // Is charging
    bool enabled;           // Is enabled
};

// Device information structure
struct DeviceInfo {
    char model[16];
    char serial[32];
    char firmware[16];
    uint32_t uptime;        // Uptime in seconds
    char bleAddr[18];       // BLE address
};

// BLE Response structure
struct BLEResponse {
    uint8_t version;
    uint8_t msgId;
    int8_t service;         // Signed - negative means response
    uint8_t sequence;
    uint8_t flags;
    uint32_t size;
    uint8_t checksum;
    uint8_t* payload;
    size_t payloadLen;
    bool success;
};

// ============ Protocol Functions ============

/**
 * Calculate checksum for BLE message header
 */
uint8_t calcChecksum(const uint8_t* header, size_t len);

/**
 * Build a complete BLE message
 * Returns message length, fills buffer with message data
 */
size_t buildMessage(uint8_t* buffer, size_t bufferSize,
                    uint8_t version, uint8_t msgId, uint8_t service,
                    uint8_t sequence, uint8_t flags,
                    const uint8_t* payload, size_t payloadLen);

/**
 * Parse a BLE response message
 */
bool parseResponse(const uint8_t* data, size_t len, BLEResponse* response);

/**
 * Parse port statistics from GET_ALL_POWER_STATISTICS response
 * Returns number of ports parsed
 */
int parsePortStatistics(const uint8_t* payload, size_t len, PortInfo* ports, int maxPorts);

/**
 * Parse device model from response
 */
bool parseDeviceModel(const uint8_t* payload, size_t len, char* model, size_t modelSize);

/**
 * Parse device serial from response
 */
bool parseDeviceSerial(const uint8_t* payload, size_t len, char* serial, size_t serialSize);

/**
 * Parse device uptime from response (in seconds)
 */
bool parseDeviceUptime(const uint8_t* payload, size_t len, uint32_t* uptime);

/**
 * Parse firmware version from response
 */
bool parseFirmwareVersion(const uint8_t* payload, size_t len, char* version, size_t versionSize);

/**
 * Get command name for debugging
 */
const char* getCommandName(uint8_t service);

/**
 * Check if command requires token
 */
bool needsToken(uint8_t service);

#endif // PROTOCOL_H
