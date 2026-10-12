// =========================================================================
// 05_firebase_multimodal_streamer.ino
// Multimodal PdM Project: Step 5 - Autonomous Cloud Telemetry (Firebase)
// Hardware: ESP32 + MPU-6050 (Direct I2C) + INMP441 (I2S DMA)
// Dual-Core FreeRTOS:
//   Core 1: Uninterrupted 50 Hz sensor sampling & local UDP broadcast
//   Core 0: HTTPS Firebase cloud sync, Web dashboard, and ArduinoOTA
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

// --- WiFi Credentials ---
const char* WIFI_SSID = "leo";
const char* WIFI_PASS = "jj67680205";

// Fallback Hotspot if Home WiFi is unavailable
const char* AP_SSID = "Washer-PdM-Rig";
const char* AP_PASS = "pdm123456";

// --- Firebase Configuration ---
const char* FIREBASE_HOST = "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app";
const char* FIREBASE_AUTH = "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V";

// --- UDP Configuration ---
WiFiUDP udp;
const int UDP_PORT = 5005;
IPAddress broadcastIP(192, 168, 0, 255);

// --- Web Server ---
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

// --- Telemetry State (Thread-safe shared variables) ---
portMUX_TYPE telemetryMux = portMUX_INITIALIZER_UNLOCKED;
volatile float g_ax = 0.0;
volatile float g_ay = 0.0;
volatile float g_az = 0.0;
volatile float g_rms = 0.0;
volatile unsigned long g_sample_count = 0;

// Session Tracking
char session_id[32];
unsigned long boot_time_ms = 0;

// --- Embedded Web Dashboard ---
const char DASHBOARD_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Washer PdM Cloud Rig</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 15px; }
    .card { background: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #334155; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 15px; }
    .status { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; background: #059669; color: #ecfdf5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 15px; }
    .metric { background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #1e293b; text-align: center; }
    .metric .val { font-size: 22px; font-weight: bold; font-family: monospace; margin-top: 4px; }
    .val-x { color: #38bdf8; }
    .val-y { color: #f59e0b; }
    .val-z { color: #10b981; }
    .val-rms { color: #ec4899; }
    .btn { display: inline-block; width: 100%; box-sizing: border-box; background: #2563eb; color: #fff; padding: 12px; border-radius: 8px; font-weight: bold; text-align: center; border: none; cursor: pointer; font-size: 15px; margin-top: 8px; }
    .btn-record { background: #059669; }
    .btn-stop { background: #dc2626; display: none; }
    canvas { width: 100%; height: 180px; background: #0f172a; border-radius: 8px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <h2 style="margin: 0; font-size: 18px;">Washer PdM Monitor</h2>
        <span style="font-size: 12px; color: #94a3b8;">Cloud Sync: Firebase Connected</span>
      </div>
      <div id="conn-status" class="status">LIVE (FIREBASE)</div>
    </div>
    
    <div class="grid">
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel X</div><div id="m-ax" class="val val-x">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel Y</div><div id="m-ay" class="val val-y">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel Z</div><div id="m-az" class="val val-z">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Audio RMS</div><div id="m-rms" class="val val-rms">0.0</div></div>
    </div>

    <canvas id="chart"></canvas>
    
    <button id="btn-rec" class="btn btn-record" onclick="toggleRecord()">🔴 Start Recording to Phone</button>
    <button id="btn-save" class="btn btn-stop" onclick="saveCSV()">💾 Stop & Download CSV to Phone</button>
  </div>

  <script>
    const cvs = document.getElementById('chart');
    const ctx = cvs.getContext('2d');
    cvs.width = cvs.clientWidth * window.devicePixelRatio;
    cvs.height = cvs.clientHeight * window.devicePixelRatio;
    
    const maxPts = 80;
    const dataX = new Array(maxPts).fill(0);
    const dataY = new Array(maxPts).fill(0);
    const dataZ = new Array(maxPts).fill(0);
    const dataRMS = new Array(maxPts).fill(0);

    let recording = false;
    let csvRows = ['timestamp_ms,accel_x,accel_y,accel_z,audio_rms'];

    function toggleRecord() {
      recording = true;
      csvRows = ['timestamp_ms,accel_x,accel_y,accel_z,audio_rms'];
      document.getElementById('btn-rec').style.display = 'none';
      document.getElementById('btn-save').style.display = 'block';
      document.getElementById('conn-status').innerText = 'RECORDING CSV...';
      document.getElementById('conn-status').style.background = '#dc2626';
    }

    function saveCSV() {
      recording = false;
      document.getElementById('btn-rec').style.display = 'block';
      document.getElementById('btn-save').style.display = 'none';
      document.getElementById('conn-status').innerText = 'LIVE (FIREBASE)';
      document.getElementById('conn-status').style.background = '#059669';

      const blob = new Blob([csvRows.join('\\n')], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'wash_cycle_' + new Date().toISOString().replace(/[:.]/g, '-') + '.csv';
      a.click();
    }

    function drawLine(arr, color, scale, offset) {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 * window.devicePixelRatio;
      for (let i = 0; i < arr.length; i++) {
        let x = (i / (maxPts - 1)) * cvs.width;
        let y = offset - (arr[i] * scale);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    function render() {
      ctx.clearRect(0, 0, cvs.width, cvs.height);
      const midY = cvs.height / 2;
      drawLine(dataX, '#38bdf8', 3, midY);
      drawLine(dataY, '#f59e0b', 3, midY);
      drawLine(dataZ, '#10b981', 3, midY);
      drawLine(dataRMS, '#ec4899', 0.1, cvs.height - 10);
    }

    setInterval(async () => {
      try {
        const res = await fetch('/data');
        const d = await res.json();
        document.getElementById('m-ax').innerText = d.ax.toFixed(2);
        document.getElementById('m-ay').innerText = d.ay.toFixed(2);
        document.getElementById('m-az').innerText = d.az.toFixed(2);
        document.getElementById('m-rms').innerText = d.rms.toFixed(1);
        
        dataX.shift(); dataX.push(d.ax);
        dataY.shift(); dataY.push(d.ay);
        dataZ.shift(); dataZ.push(d.az);
        dataRMS.shift(); dataRMS.push(d.rms);
        render();

        if (recording) {
          csvRows.push(`${Date.now()},${d.ax.toFixed(2)},${d.ay.toFixed(2)},${d.az.toFixed(2)},${d.rms.toFixed(1)}`);
        }
      } catch (e) {}
    }, 100);
  </script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", DASHBOARD_HTML);
}

void handleData() {
  float ax, ay, az, rms;
  unsigned long cnt;
  portENTER_CRITICAL(&telemetryMux);
  ax = g_ax;
  ay = g_ay;
  az = g_az;
  rms = g_rms;
  cnt = g_sample_count;
  portEXIT_CRITICAL(&telemetryMux);

  char json[128];
  snprintf(json, sizeof(json), "{\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"rms\":%.1f,\"cnt\":%lu}", 
           ax, ay, az, rms, cnt);
  server.send(200, "application/json", json);
}

void initMPU() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  delay(100);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission();

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x18); // ±16g
  Wire.endTransmission();
  Serial.println("[OK] MPU-6050 ready (±16g).");
}

void initI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = AUDIO_SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
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
  i2s_start(I2S_PORT);
  Serial.println("[OK] INMP441 ready (I2S DMA).");
}

void setupWiFi() {
  Serial.printf("Connecting to WiFi: %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 12000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[CONNECTED] Home WiFi Connected!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[HOTSPOT] WiFi timeout. Starting Hotspot...");
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("Hotspot IP: ");
    Serial.println(WiFi.softAPIP());
  }

  if (MDNS.begin("washer-pdm")) {
    Serial.println("[MDNS] http://washer-pdm.local");
  }

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.begin();

  udp.begin(UDP_PORT);

  // Setup Arduino OTA for wireless firmware flashing
  ArduinoOTA.setHostname("washer-pdm-rig");
  ArduinoOTA.begin();
  Serial.println("[OTA] Wireless firmware flashing ready.");
}

// -------------------------------------------------------------------------
// Core 0 Task: Background Cloud & Web Tasks (Never delays sensor sampling)
// -------------------------------------------------------------------------
void cloudTask(void* parameter) {
  WiFiClientSecure client;
  client.setInsecure(); // SSL without cert validation for speed

  unsigned long last_firebase_live = 0;
  unsigned long last_firebase_batch = 0;
  unsigned int batch_counter = 0;

  for (;;) {
    server.handleClient();
    ArduinoOTA.handle();

    // 1. Update Firebase /live.json every 2.0 seconds
    if (WiFi.status() == WL_CONNECTED && millis() - last_firebase_live >= 2000) {
      last_firebase_live = millis();

      float ax, ay, az, rms;
      unsigned long cnt;
      portENTER_CRITICAL(&telemetryMux);
      ax = g_ax; ay = g_ay; az = g_az; rms = g_rms; cnt = g_sample_count;
      portEXIT_CRITICAL(&telemetryMux);

      float vibe_mag = sqrt(ax * ax + ay * ay + az * az);
      const char* machine_state = "IDLE";
      if (fabs(vibe_mag - 9.81) > 2.5 || rms > 150.0) machine_state = "RUNNING";
      if (fabs(vibe_mag - 9.81) > 8.0) machine_state = "SPIN_CYCLE";

      char liveJson[320];
      snprintf(liveJson, sizeof(liveJson),
        "{\"ts\":{\".sv\":\"timestamp\"},\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"vibe\":%.2f,\"rms\":%.1f,\"state\":\"%s\",\"session\":\"%s\",\"cnt\":%lu,\"uptime\":%lu}",
        ax, ay, az, vibe_mag, rms, machine_state, session_id, cnt, (millis() - boot_time_ms) / 1000);

      HTTPClient https;
      char url[220];
      snprintf(url, sizeof(url), "%s/live.json?auth=%s", FIREBASE_HOST, FIREBASE_AUTH);
      if (https.begin(client, url)) {
        https.addHeader("Content-Type", "application/json");
        https.PUT(liveJson);
        https.end();
      }
    }

    // 2. Push Wash Batch to Firebase /sessions/<session_id>/batches/<id>.json every 5.0 seconds
    if (WiFi.status() == WL_CONNECTED && millis() - last_firebase_batch >= 5000) {
      last_firebase_batch = millis();
      batch_counter++;

      float ax, ay, az, rms;
      portENTER_CRITICAL(&telemetryMux);
      ax = g_ax; ay = g_ay; az = g_az; rms = g_rms;
      portEXIT_CRITICAL(&telemetryMux);

      char batchJson[220];
      snprintf(batchJson, sizeof(batchJson),
        "{\"t\":%lu,\"ts\":{\".sv\":\"timestamp\"},\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"rms\":%.1f}",
        millis(), ax, ay, az, rms);

      HTTPClient https;
      char batchUrl[260];
      snprintf(batchUrl, sizeof(batchUrl), "%s/sessions/%s/%u.json?auth=%s", FIREBASE_HOST, session_id, batch_counter, FIREBASE_AUTH);
      if (https.begin(client, batchUrl)) {
        https.addHeader("Content-Type", "application/json");
        https.PUT(batchJson);
        https.end();
      }
    }

    vTaskDelay(50 / portTICK_PERIOD_MS); // Yield CPU on Core 0
  }
}

// -------------------------------------------------------------------------
// Setup (Runs on Core 1)
// -------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Autonomous Cloud Telemetry Rig (Firebase) ===");

  boot_time_ms = millis();
  snprintf(session_id, sizeof(session_id), "wash_%lu", boot_time_ms);

  initMPU();
  initI2S();
  setupWiFi();

  // If WiFi connected, synchronize real-world NTP time (UTC+8) for collision-free sessions
  if (WiFi.status() == WL_CONNECTED) {
    configTime(8 * 3600, 0, "pool.ntp.org", "time.nist.gov");
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 3000)) {
      strftime(session_id, sizeof(session_id), "wash_%Y%m%d_%H%M%S", &timeinfo);
      Serial.printf("[NTP] Real-world Session ID created: %s\n", session_id);
    }
  }

  // Launch Cloud & Web task on Core 0
  xTaskCreatePinnedToCore(
    cloudTask,
    "CloudTask",
    10000,
    NULL,
    1,
    NULL,
    0 // Core 0
  );
  Serial.println("[SYSTEM] Core 0 (Cloud/Web) and Core 1 (Sensors) running in parallel!");
}

// -------------------------------------------------------------------------
// Main Loop (Dedicated exclusively to Core 1: 50 Hz Sensor Sampling & UDP)
// -------------------------------------------------------------------------
void loop() {
  // 1. Read MPU-6050 Acceleration
  float ax = 0.0, ay = 0.0, az = 0.0;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  if (Wire.available() >= 6) {
    int16_t rawX = (Wire.read() << 8) | Wire.read();
    int16_t rawY = (Wire.read() << 8) | Wire.read();
    int16_t rawZ = (Wire.read() << 8) | Wire.read();

    ax = (rawX / 2048.0) * 9.81;
    ay = (rawY / 2048.0) * 9.81;
    az = (rawZ / 2048.0) * 9.81;
  }

  // 2. Read INMP441 Microphone
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

  // Thread-safe update of shared variables
  portENTER_CRITICAL(&telemetryMux);
  g_ax = ax;
  g_ay = ay;
  g_az = az;
  g_rms = rms;
  g_sample_count++;
  portEXIT_CRITICAL(&telemetryMux);

  // 3. Local UDP Broadcast Packet (~50 Hz) for Laptop
  char packet[96];
  snprintf(packet, sizeof(packet), "%lu,%.2f,%.2f,%.2f,%.1f\n", 
           millis(), ax, ay, az, rms);

  udp.beginPacket(broadcastIP, UDP_PORT);
  udp.write((const uint8_t*)packet, strlen(packet));
  udp.endPacket();

  delay(20); // ~50 Hz sampling cadence
}
