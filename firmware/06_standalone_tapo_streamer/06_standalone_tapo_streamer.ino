// =========================================================================
// 06_standalone_tapo_streamer.ino
// Multimodal IoT PdM Rig: True Standalone ESP32 + Tapo P110 + Firebase RTDB
// 
// Hardware:
//   - ESP32 NodeMCU / DevKit (Dual-Core 240 MHz)
//   - MPU-6050 3-Axis Accelerometer (Direct I2C, Core 1 @ 50 Hz)
//   - INMP441 MEMS Microphone (I2S DMA, Core 1 @ 16 kHz)
//   - TP-Link Tapo P110 Smart Energy Socket (Local KLAP, Core 0 @ 1 Hz)
// 
// Dual-Core FreeRTOS Discipline:
//   Core 1: Uninterrupted high-frequency sensor acquisition (Vibration + Sound)
//   Core 0: Network processing (Wi-Fi, Tapo KLAP polling, Firebase HTTPS, OTA)
// 
// Zero PC Required: Completely autonomous and "Dad-Proof"!
// =========================================================================

#include <WiFi.h>
#include <WiFiUdp.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <math.h>

#include "tapo_device.h"

// --- Credentials & Configuration ---
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  const char* WIFI_SSID = "leo";
  const char* WIFI_PASS = "jj67680205";
  const char* FIREBASE_HOST = "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app";
  const char* FIREBASE_AUTH = "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V";
  
  // Tapo P110 Configuration (set in secrets.h)
  const char* TAPO_IP = "192.168.0.45";       // Will be updated from Tapo App
  const char* TAPO_USER = "admin";            // Device Account username
  const char* TAPO_PASS = "pdm123456";        // Device Account password
#endif

// --- Web Server & OTA ---
WebServer server(80);

// --- Pin Definitions ---
#define I2C_SDA_PIN   21
#define I2C_SCL_PIN   22
#define MPU_ADDR      0x68

#define I2S_SCK_PIN   33   // BCLK
#define I2S_WS_PIN    25   // LRCLK
#define I2S_SD_PIN    32   // DIN

// --- I2S Configuration ---
#define I2S_PORT          I2S_NUM_0
#define AUDIO_SAMPLE_RATE 16000
#define AUDIO_BUFFER_LEN  128

int32_t audio_buffer[AUDIO_BUFFER_LEN];

// --- Thread-Safe Shared Telemetry State ---
portMUX_TYPE telemetryMux = portMUX_INITIALIZER_UNLOCKED;
volatile float g_ax = 0.0;
volatile float g_ay = 0.0;
volatile float g_az = 0.0;
volatile float g_rms = 0.0;
volatile float g_power_w = 0.0;
volatile float g_today_wh = 0.0;
volatile unsigned long g_sample_count = 0;

// Session Tracking
char session_id[48];
unsigned long boot_time_ms = 0;
bool g_ntp_synced = false;
bool g_session_locked = false;

// Tapo Client Object
TapoDevice tapo;
bool g_tapo_initialized = false;

// -------------------------------------------------------------------------
// Sensor Inits (Runs on Core 1)
// -------------------------------------------------------------------------
void initMPU() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 400000); // Fast I2C 400 kHz
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1
  Wire.write(0x00); // Wake up MPU
  Wire.endTransmission(true);

  // Set Accelerometer to ±16g for high-speed centrifugal spin
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C); // ACCEL_CONFIG
  Wire.write(0x18); // ±16g
  Wire.endTransmission(true);
  Serial.println("[MPU-6050] Initialized at ±16g.");
}

void initI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = AUDIO_SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = AUDIO_BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD_PIN
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  Serial.println("[INMP441] I2S DMA Initialized at 16 kHz.");
}

// -------------------------------------------------------------------------
// Core 0 Task: Wi-Fi, Tapo P110 Polling, Firebase HTTPS, and OTA
// -------------------------------------------------------------------------
void cloudTask(void* parameter) {
  WiFiClientSecure client;
  client.setInsecure(); // Skip root CA validation for fast RTDB HTTPS

  unsigned long last_firebase_live = 0;
  unsigned long last_firebase_batch = 0;
  unsigned long last_tapo_poll = 0;
  unsigned long batch_counter = 0;

  Serial.println("[CLOUD TASK] Core 0 network handler started.");

  // Connect Tapo Plug via KLAP local protocol
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[TAPO] Connecting to Tapo P110 at %s via KLAP...\n", TAPO_IP);
    g_tapo_initialized = tapo.begin(TAPO_IP, TAPO_USER, TAPO_PASS);
    if (g_tapo_initialized) {
      Serial.println("[TAPO OK] Local KLAP connection established!");
    } else {
      Serial.println("[TAPO WARN] Handshake failed, background task will retry.");
    }
  }

  while (true) {
    server.handleClient();
    ArduinoOTA.handle();

    // 1. Background NTP sync for collision-free date/time session ID
    if (!g_ntp_synced && WiFi.status() == WL_CONNECTED) {
      struct tm timeinfo;
      if (getLocalTime(&timeinfo, 500)) {
        strftime(session_id, sizeof(session_id), "wash_%Y-%m-%d_%H%M%S", &timeinfo);
        g_ntp_synced = true;
        Serial.printf("\n[NTP SYNCED] Real-World Session ID: %s\n", session_id);
      }
    }

    // 2. Poll Tapo P110 Active Watts every 1.0 second
    if (WiFi.status() == WL_CONNECTED && millis() - last_tapo_poll >= 1000) {
      last_tapo_poll = millis();
      
      if (!g_tapo_initialized) {
        g_tapo_initialized = tapo.begin(TAPO_IP, TAPO_USER, TAPO_PASS);
      }

      if (g_tapo_initialized) {
        float pwr = tapo.get_power_w();
        if (pwr >= 0.0f) {
          portENTER_CRITICAL(&telemetryMux);
          g_power_w = pwr;
          portEXIT_CRITICAL(&telemetryMux);
        } else {
          // Re-handshake on failure
          g_tapo_initialized = false;
        }
      }
    }

    // 3. Push Unified Live Telemetry to Firebase /live.json every 2.0 seconds
    if (WiFi.status() == WL_CONNECTED && millis() - last_firebase_live >= 2000) {
      last_firebase_live = millis();

      float ax, ay, az, rms, pwr, wh;
      unsigned long cnt;
      portENTER_CRITICAL(&telemetryMux);
      ax = g_ax; ay = g_ay; az = g_az; rms = g_rms;
      pwr = g_power_w; wh = g_today_wh;
      cnt = g_sample_count;
      portEXIT_CRITICAL(&telemetryMux);

      float vibe_mag = sqrt(ax * ax + ay * ay + az * az);
      const char* machine_state = "IDLE";
      if (fabs(vibe_mag - 9.81) > 2.5 || rms > 150.0 || pwr > 50.0) machine_state = "RUNNING";
      if (fabs(vibe_mag - 9.81) > 8.0 || pwr > 400.0) machine_state = "SPIN_CYCLE";

      char liveJson[384];
      snprintf(liveJson, sizeof(liveJson),
        "{\"ts\":{\".sv\":\"timestamp\"},\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"vibe\":%.2f,\"rms\":%.1f,\"power\":%.1f,\"state\":\"%s\",\"session\":\"%s\",\"cnt\":%lu,\"uptime\":%lu}",
        ax, ay, az, vibe_mag, rms, pwr, machine_state, session_id, cnt, (millis() - boot_time_ms) / 1000);

      HTTPClient https;
      char url[220];
      snprintf(url, sizeof(url), "%s/live.json?auth=%s", FIREBASE_HOST, FIREBASE_AUTH);
      if (https.begin(client, url)) {
        https.addHeader("Content-Type", "application/json");
        https.PUT(liveJson);
        https.end();
      }
    }

    // 4. Push Unified Wash Batch to Firebase /sessions/<session_id>/<batch_id>.json every 5.0 seconds
    if (WiFi.status() == WL_CONNECTED && millis() - last_firebase_batch >= 5000) {
      last_firebase_batch = millis();
      batch_counter++;
      g_session_locked = true;

      float ax, ay, az, rms, pwr;
      portENTER_CRITICAL(&telemetryMux);
      ax = g_ax; ay = g_ay; az = g_az; rms = g_rms; pwr = g_power_w;
      portEXIT_CRITICAL(&telemetryMux);

      char batchJson[256];
      snprintf(batchJson, sizeof(batchJson),
        "{\"t\":%lu,\"ts\":{\".sv\":\"timestamp\"},\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"rms\":%.1f,\"pwr\":%.1f}",
        millis(), ax, ay, az, rms, pwr);

      HTTPClient https;
      char batchUrl[260];
      snprintf(batchUrl, sizeof(batchUrl), "%s/sessions/%s/%u.json?auth=%s", FIREBASE_HOST, session_id, batch_counter, FIREBASE_AUTH);
      if (https.begin(client, batchUrl)) {
        https.addHeader("Content-Type", "application/json");
        https.PUT(batchJson);
        https.end();
      }
    }

    vTaskDelay(30 / portTICK_PERIOD_MS); // Yield CPU on Core 0
  }
}

// -------------------------------------------------------------------------
// Setup (Initializes Sensors on Core 1 & Launches Core 0 Cloud Task)
// -------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Autonomous Standalone PdM Rig (ESP32 + Tapo + Firebase) ===");

  boot_time_ms = millis();
  snprintf(session_id, sizeof(session_id), "wash_offline_%08X", (unsigned int)esp_random());

  initMPU();
  initI2S();

  // Wi-Fi Connection
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("[WIFI] Connecting to %s", WIFI_SSID);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 25) {
    delay(300);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI OK] IP: %s\n", WiFi.localIP().toString().c_str());

    // Synchronize NTP date and time (UTC+8)
    configTime(8 * 3600, 0, "pool.ntp.org", "time.google.com", "time.cloudflare.com");
    struct tm timeinfo;
    for (int i = 0; i < 12; i++) {
      if (getLocalTime(&timeinfo, 300)) {
        strftime(session_id, sizeof(session_id), "wash_%Y-%m-%d_%H%M%S", &timeinfo);
        g_ntp_synced = true;
        Serial.printf("[NTP OK] Session ID: %s\n", session_id);
        break;
      }
      delay(200);
    }

    // Wireless OTA Flashing Setup
    ArduinoOTA.setHostname("washer-pdm-rig");
    ArduinoOTA.begin();
    Serial.println("[OTA OK] Wireless flashing enabled on washer-pdm-rig.");
  }

  // Pin Cloud Task to Core 0 (12KB stack)
  xTaskCreatePinnedToCore(
    cloudTask,
    "CloudTask",
    12000,
    NULL,
    1,
    NULL,
    0 // Core 0
  );
  Serial.println("[SYSTEM] Core 0 (Cloud/Tapo) and Core 1 (Sensors) running in parallel!");
}

// -------------------------------------------------------------------------
// Main Loop (Runs on Core 1: 50 Hz Sensor Sampling)
// -------------------------------------------------------------------------
void loop() {
  static unsigned long last_sample_time = 0;

  // Enforce precise 50 Hz (20ms interval) sampling on Core 1
  if (millis() - last_sample_time >= 20) {
    last_sample_time = millis();

    // 1. Read MPU-6050 Accelerometer
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

    if (Wire.available() >= 6) {
      int16_t raw_ax = (Wire.read() << 8) | Wire.read();
      int16_t raw_ay = (Wire.read() << 8) | Wire.read();
      int16_t raw_az = (Wire.read() << 8) | Wire.read();

      // Convert raw to m/s^2 (±16g sensitivity is 2048 LSB/g, 1g = 9.80665 m/s^2)
      float ax = (float)raw_ax / 2048.0 * 9.80665;
      float ay = (float)raw_ay / 2048.0 * 9.80665;
      float az = (float)raw_az / 2048.0 * 9.80665;

      // 2. Read INMP441 Microphone DMA Buffer (Standardized Scale: Matches Firmware 05 & ML Dataset)
      size_t bytes_read = 0;
      float rms = 0.0;
      i2s_read(I2S_PORT, (char *)audio_buffer, sizeof(audio_buffer), &bytes_read, 0);

      if (bytes_read > 0) {
        int samples = bytes_read / sizeof(int32_t);
        double sum = 0.0;
        for (int i = 0; i < samples; i++) {
          int32_t s = audio_buffer[i] >> 8;
          sum += ((double)s * (double)s);
        }
        rms = sqrt(sum / (samples > 0 ? samples : 1)) / 1000.0;
      }

      // Update Shared State Thread-Safely
      portENTER_CRITICAL(&telemetryMux);
      g_ax = ax;
      g_ay = ay;
      g_az = az;
      g_rms = rms;
      g_sample_count++;
      portEXIT_CRITICAL(&telemetryMux);
    }
  }
}
