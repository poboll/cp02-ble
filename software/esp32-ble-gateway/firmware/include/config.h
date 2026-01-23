/**
 * ESP32 BLE Gateway Configuration
 * 
 * Configuration for connecting ESP32-S3 to CP02 chargers via BLE
 * and publishing data to MQTT broker
 * 
 * Enhanced Features:
 * - WiFiManager for easy WiFi configuration via captive portal
 * - OTA (Over-The-Air) firmware updates
 * - Persistent configuration storage
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============ Device Configuration ============
#define DEVICE_NAME         "ESP32-BLE-GW"
#define DEVICE_VERSION      "2.0.0"

// Unique gateway ID - change this for each ESP32 device
// Will be appended to MQTT topics
#define GATEWAY_ID          "gw01"

// ============ BLE Configuration ============
// CP02 Charger BLE UUIDs (from protocol.py)
#define CP02_SERVICE_UUID   "048e3f2e-e1a6-4707-9e74-a930e898a1ea"
#define CP02_CHAR_TX_UUID   "148e3f2e-e1a6-4707-9e74-a930e898a1ea"  // Notify (device -> app)
#define CP02_CHAR_RX_UUID   "248e3f2e-e1a6-4707-9e74-a930e898a1ea"  // Write (app -> device)

// Device name prefix to scan for
#define CP02_DEVICE_PREFIX  "CP02-"

// BLE scan parameters
#define BLE_SCAN_DURATION   5       // Scan duration in seconds
#define BLE_SCAN_INTERVAL   100     // Scan interval in 0.625ms units
#define BLE_SCAN_WINDOW     99      // Scan window in 0.625ms units

// BLE connection parameters
#define BLE_CONNECT_TIMEOUT 10000   // Connection timeout in ms
#define BLE_RECONNECT_DELAY 5000    // Delay before reconnect attempt in ms
#define BLE_MAX_RECONNECT   5       // Maximum reconnect attempts

// ============ WiFi Configuration ============
// Default WiFi credentials (used if WiFiManager is disabled)
// Leave empty to force WiFiManager portal on first boot
#define WIFI_SSID           ""      // Leave empty for WiFiManager
#define WIFI_PASSWORD       ""      // Leave empty for WiFiManager

// WiFiManager portal configuration
#define WIFI_PORTAL_NAME    "ESP32-BLE-Gateway"
#define WIFI_PORTAL_TIMEOUT 180     // Portal timeout in seconds (0 = no timeout)
#define WIFI_PORTAL_PASSWORD ""     // Password for config portal (empty = open)

// WiFi reconnection
#define WIFI_RECONNECT_DELAY 5000   // Delay before WiFi reconnect in ms
#define WIFI_CONNECT_TIMEOUT 30000  // WiFi connection timeout in ms

// ============ MQTT Configuration ============
// Default MQTT Broker settings (can be changed via WiFiManager)
#define MQTT_HOST           "192.168.1.100"  // Default MQTT broker IP
#define MQTT_PORT           1883
#define MQTT_USER           ""              // Leave empty if no auth
#define MQTT_PASSWORD       ""              // Leave empty if no auth

// MQTT Client ID - will be appended with gateway ID
#define MQTT_CLIENT_PREFIX  "esp32-ble-gw-"

// MQTT Topics
// Format: cp02/{gateway_id}/{topic}
#define MQTT_TOPIC_BASE     "cp02"

// Telemetry topics (device -> server)
#define MQTT_TOPIC_STATUS       "status"        // Gateway status
#define MQTT_TOPIC_PORTS        "ports"         // Port data
#define MQTT_TOPIC_DEVICE_INFO  "device_info"   // Charger device info
#define MQTT_TOPIC_HEARTBEAT    "heartbeat"     // Keep-alive

// Command topics (server -> device)
#define MQTT_TOPIC_CMD          "cmd"           // Commands from server
#define MQTT_TOPIC_CMD_RESPONSE "cmd_response"  // Command responses

// MQTT QoS levels
#define MQTT_QOS_TELEMETRY  0   // At most once for frequent data
#define MQTT_QOS_COMMAND    1   // At least once for commands
#define MQTT_QOS_STATUS     1   // At least once for status

// MQTT connection parameters
#define MQTT_KEEPALIVE      60      // Keep-alive interval in seconds
#define MQTT_RECONNECT_DELAY 5000   // Delay before MQTT reconnect in ms

// ============ OTA Configuration ============
// Enable/Disable OTA updates
#define OTA_ENABLED         1       // Set to 0 to disable OTA

// OTA port and password
#define OTA_PORT            3232
#define OTA_PASSWORD        ""      // Empty = no password required

// OTA hostname (will be gateway ID if empty)
#define OTA_HOSTNAME        ""

// HTTP OTA settings (for downloading firmware from server)
#define OTA_UPDATE_CHECK_INTERVAL 3600000  // Check for updates every hour (ms)

// ============ Data Collection Configuration ============
// Polling intervals in milliseconds
#define POLL_INTERVAL_PORTS     3000    // Port status polling interval
#define POLL_INTERVAL_DEVICE    30000   // Device info polling interval
#define POLL_INTERVAL_HEARTBEAT 10000   // Heartbeat interval

// ============ Token Configuration ============
// Token for CP02 authentication (0-255)
// Will be bruteforced if not set
#define CP02_TOKEN          0xFF    // 0xFF means auto-discover

// Token bruteforce parameters
#define TOKEN_TEST_TIMEOUT  300     // Timeout for each token test in ms
#define TOKEN_TEST_DELAY    20      // Delay between token tests in ms

// ============ Debug Configuration ============
#define DEBUG_SERIAL        1       // Enable serial debug output
#define DEBUG_BLE           1       // Enable BLE debug messages
#define DEBUG_MQTT          1       // Enable MQTT debug messages
#define DEBUG_OTA           1       // Enable OTA debug messages
#define DEBUG_WIFI          1       // Enable WiFi debug messages

// Serial baud rate
#define SERIAL_BAUD         115200

// ============ LED Configuration ============
// Built-in LED for status indication
#define LED_BUILTIN_PIN     2       // Change if your board uses different pin
#define LED_ENABLED         1       // Set to 0 to disable LED status

// LED blink patterns (in ms)
#define LED_BLINK_WIFI      500     // Connecting to WiFi
#define LED_BLINK_BLE       250     // Scanning BLE
#define LED_BLINK_MQTT      1000    // Connecting to MQTT
#define LED_BLINK_OTA       100     // OTA update in progress
#define LED_SOLID_CONNECTED 0       // Solid when all connected

// ============ Watchdog Configuration ============
#define WDT_ENABLED         1       // Enable watchdog timer
#define WDT_TIMEOUT         30      // Watchdog timeout in seconds

// ============ Reset Button Configuration ============
#define RESET_BUTTON_PIN    0       // GPIO0 (BOOT button on most boards)
#define RESET_BUTTON_HOLD   5000    // Hold for 5 seconds to reset WiFi settings

// ============ Persistent Storage ============
// Preferences namespace for storing configuration
#define PREFS_NAMESPACE     "ble-gw-config"

#endif // CONFIG_H
