#include "protocol.h"
#include <string.h>

const char* CP02_SERVICE_UUID = "048e3f2e-e1a6-4707-9e74-a930e898a1ea";
const char* CP02_CHAR_TX_UUID = "148e3f2e-e1a6-4707-9e74-a930e898a1ea";
const char* CP02_CHAR_RX_UUID = "248e3f2e-e1a6-4707-9e74-a930e898a1ea";
const char* CP02_DEVICE_PREFIX = "CP02-";

static const char* PROTOCOL_NAMES[] = {
    "无", "QC2.0", "QC3.0", "QC3+", "SFCP", "AFC", "FCP", "SCP",
    "VOOC1.0", "VOOC4.0", "SuperVOOC2.0", "TFCP", "UFCS", "PE1.0", "PE2.0",
    "PD 5V", "PD HV", "PD SPR AVS", "PD PPS", "PD EPR HV", "PD AVS"
};

const char* getProtocolName(uint8_t protocol) {
    if (protocol == 0xFF) return "未充电";
    if (protocol < sizeof(PROTOCOL_NAMES) / sizeof(PROTOCOL_NAMES[0])) {
        return PROTOCOL_NAMES[protocol];
    }
    return "未知";
}

uint8_t calcChecksum(const uint8_t* header, size_t len) {
    uint8_t sum = 0;
    for (size_t i = 0; i < len - 1; i++) {
        sum += header[i];
    }
    return sum & 0xFF;
}

size_t buildMessage(uint8_t* buffer, size_t bufferSize,
                    uint8_t version, uint8_t msgId, uint8_t service,
                    uint8_t sequence, uint8_t flags,
                    const uint8_t* payload, size_t payloadLen) {
    if (bufferSize < 9 + payloadLen) return 0;
    
    buffer[0] = version;
    buffer[1] = msgId;
    buffer[2] = service;
    buffer[3] = sequence;
    buffer[4] = flags;
    buffer[5] = (payloadLen >> 16) & 0xFF;
    buffer[6] = (payloadLen >> 8) & 0xFF;
    buffer[7] = payloadLen & 0xFF;
    buffer[8] = 0;
    
    buffer[8] = calcChecksum(buffer, 9);
    
    if (payloadLen > 0 && payload != nullptr) {
        memcpy(buffer + 9, payload, payloadLen);
    }
    
    return 9 + payloadLen;
}

bool parseResponse(const uint8_t* data, size_t len, BLEResponse* response) {
    if (len < 9 || response == nullptr) return false;
    
    response->version = data[0];
    response->msgId = data[1];
    response->service = (int8_t)data[2];
    response->sequence = data[3];
    response->flags = data[4];
    
    if (response->version == 0) {
        response->size = ((uint32_t)data[5] << 16) | ((uint32_t)data[6] << 8) | data[7];
    } else {
        response->size = data[5] | ((uint32_t)data[6] << 8) | ((uint32_t)data[7] << 16);
    }
    
    response->checksum = data[8];
    response->payload = (len > 9) ? (uint8_t*)(data + 9) : nullptr;
    response->payloadLen = (len > 9) ? (len - 9) : 0;
    response->success = (response->service < 0);
    
    return true;
}

int parsePortStatistics(const uint8_t* payload, size_t len, PortInfo* ports, int maxPorts) {
    if (payload == nullptr || ports == nullptr || len == 0) return 0;
    
    const uint8_t* data = payload;
    if (len > 0 && data[0] == 0x00) {
        data++;
        len--;
    }
    
    int portCount = 0;
    const int CHUNK_SIZE = 8;
    
    while (len >= CHUNK_SIZE && portCount < maxPorts) {
        uint8_t fcProtocol = data[0];
        uint8_t amperageScaled = data[1];
        uint8_t voltageScaled = data[2];
        int8_t temperature = (int8_t)data[3];
        
        float voltage = voltageScaled / 8.0f;
        float current = amperageScaled / 32.0f;
        float power = voltage * current;
        
        ports[portCount].portId = portCount;
        ports[portCount].protocol = fcProtocol;
        ports[portCount].voltage = voltage;
        ports[portCount].current = current;
        ports[portCount].power = power;
        ports[portCount].temperature = temperature;
        ports[portCount].charging = (current > 0.01f);
        ports[portCount].enabled = (fcProtocol != 0xFF || voltage > 0 || current > 0);
        
        data += CHUNK_SIZE;
        len -= CHUNK_SIZE;
        portCount++;
    }
    
    return portCount;
}

bool parseDeviceModel(const uint8_t* payload, size_t len, char* model, size_t modelSize) {
    if (payload == nullptr || model == nullptr || len == 0 || modelSize == 0) return false;
    
    size_t copyLen = (len < modelSize - 1) ? len : (modelSize - 1);
    memcpy(model, payload, copyLen);
    model[copyLen] = '\0';
    
    for (size_t i = 0; i < copyLen; i++) {
        if (model[i] == '\0') break;
        if (model[i] < 32 || model[i] > 126) model[i] = ' ';
    }
    
    return true;
}

bool parseDeviceSerial(const uint8_t* payload, size_t len, char* serial, size_t serialSize) {
    return parseDeviceModel(payload, len, serial, serialSize);
}

bool parseDeviceUptime(const uint8_t* payload, size_t len, uint32_t* uptime) {
    if (payload == nullptr || uptime == nullptr || len < 8) return false;
    
    uint64_t uptimeUs = 0;
    for (int i = 0; i < 8; i++) {
        uptimeUs |= ((uint64_t)payload[i]) << (i * 8);
    }
    
    *uptime = (uint32_t)(uptimeUs / 1000000ULL);
    return true;
}

bool parseFirmwareVersion(const uint8_t* payload, size_t len, char* version, size_t versionSize) {
    return parseDeviceModel(payload, len, version, versionSize);
}

const char* getCommandName(uint8_t service) {
    switch (service) {
        case CMD_GET_DEVICE_MODEL: return "GET_DEVICE_MODEL";
        case CMD_GET_ALL_POWER_STATISTICS: return "GET_ALL_POWER_STATISTICS";
        case CMD_GET_PORT_PD_STATUS: return "GET_PORT_PD_STATUS";
        case CMD_TURN_ON_PORT: return "TURN_ON_PORT";
        case CMD_TURN_OFF_PORT: return "TURN_OFF_PORT";
        case CMD_REBOOT_DEVICE: return "REBOOT_DEVICE";
        case CMD_GET_DEVICE_UPTIME: return "GET_DEVICE_UPTIME";
        case CMD_GET_AP_VERSION: return "GET_AP_VERSION";
        case CMD_GET_DEVICE_SERIAL_NO: return "GET_DEVICE_SERIAL_NO";
        default: return "UNKNOWN";
    }
}

bool needsToken(uint8_t service) {
    return service != CMD_ASSOCIATE_DEVICE;
}
