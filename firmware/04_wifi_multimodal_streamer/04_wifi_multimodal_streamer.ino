// =========================================================================
// 04_wifi_multimodal_streamer.ino
// Multimodal PdM Project: Step 4 - Wireless Telemetry & Web Dashboard
// Hardware: ESP32 + MPU-6050 (Direct I2C) + INMP441 (I2S DMA)
// Streams UDP packets to laptop & serves live web dashboard on port 80
// =========================================================================

#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <math.h>

// --- WiFi Credentials ---
const char* WIFI_SSID = "leo";
const char* WIFI_PASS = "jj67680205";

// Fallback Hotspot if Home WiFi is unavailable
const char* AP_SSID = "Washer-PdM-Rig";
const char* AP_PASS = "pdm123456";

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

#define I2S_SCK_PIN   33   // Serial Clock (BCLK)
#define I2S_WS_PIN    25   // Word Select (LRCLK)
#define I2S_SD_PIN    32   // Serial Data (DIN)

// --- I2S Configuration ---
#define I2S_PORT          I2S_NUM_0
#define AUDIO_SAMPLE_RATE 16000
#define AUDIO_BUFFER_LEN  128

int32_t audio_buffer[AUDIO_BUFFER_LEN];

// Telemetry State
volatile float last_ax = 0.0;
volatile float last_ay = 0.0;
volatile float last_az = 0.0;
volatile float last_rms = 0.0;
unsigned long sample_counter = 0;

// Embedded HTML Dashboard
const char DASHBOARD_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Washer PdM Live Dashboard</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 15px; }
    .card { background: #1e293b; border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid #334155; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
    .status { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; background: #059669; color: #ecfdf5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 15px; }
    .metric { background: #0f172a; padding: 10px; border-radius: 8px; border: 1px solid #1e293b; text-align: center; }
    .metric .val { font-size: 22px; font-weight: bold; font-family: monospace; margin-top: 4px; }
    .val-x { color: #38bdf8; }
    .val-y { color: #f59e0b; }
    .val-z { color: #10b981; }
    .val-rms { color: #ec4899; }
    canvas { width: 100%; height: 180px; background: #0f172a; border-radius: 8px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <h2 style="margin: 0; font-size: 18px;">Samsung Washer PdM Monitor</h2>
        <span style="font-size: 12px; color: #94a3b8;">Multimodal Rig: MPU-6050 + INMP441</span>
      </div>
      <div id="conn-status" class="status">LIVE STREAMING</div>
    </div>
    
    <div class="grid">
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel X</div><div id="m-ax" class="val val-x">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel Y</div><div id="m-ay" class="val val-y">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Accel Z</div><div id="m-az" class="val val-z">0.00</div></div>
      <div class="metric"><div style="font-size: 11px; color: #94a3b8;">Audio RMS</div><div id="m-rms" class="val val-rms">0.0</div></div>
    </div>

    <canvas id="chart"></canvas>
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
      } catch (e) {
        document.getElementById('conn-status').innerText = 'RECONNECTING...';
        document.getElementById('conn-status').style.background = '#e11d48';
      }
    }, 100);
  </script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", DASHBOARD_HTML);
}

void handleData() {
  char json[128];
  snprintf(json, sizeof(json), "{\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"rms\":%.1f,\"cnt\":%lu}", 
           last_ax, last_ay, last_az, last_rms, sample_counter);
  server.send(200, "application/json", json);
}

void initMPU() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  delay(100);

  // Wake up MPU-6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission();

  // Set Range to ±16g
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x18);
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
  Serial.printf("\nConnecting to WiFi SSID: %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[CONNECTED] Home WiFi Connected!");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WARNING] Home WiFi connection timed out. Starting Backup Hotspot...");
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("Backup Hotspot IP: ");
    Serial.println(WiFi.softAPIP());
  }

  if (MDNS.begin("washer-pdm")) {
    Serial.println("[MDNS] Dashboard URL: http://washer-pdm.local");
  }

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.begin();
  Serial.println("[HTTP] Web Dashboard running on port 80.");
  
  udp.begin(UDP_PORT);
  Serial.printf("[UDP] Broadcast streamer active on port %d.\n", UDP_PORT);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Multimodal WiFi Telemetry Rig ===");

  initMPU();
  initI2S();
  setupWiFi();
}

void loop() {
  server.handleClient();

  // 1. Read MPU-6050 Acceleration
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  if (Wire.available() >= 6) {
    int16_t rawX = (Wire.read() << 8) | Wire.read();
    int16_t rawY = (Wire.read() << 8) | Wire.read();
    int16_t rawZ = (Wire.read() << 8) | Wire.read();

    last_ax = (rawX / 2048.0) * 9.81;
    last_ay = (rawY / 2048.0) * 9.81;
    last_az = (rawZ / 2048.0) * 9.81;
  }

  // 2. Read INMP441 Microphone Chunk
  size_t bytes_read = 0;
  i2s_read(I2S_PORT, (char *)audio_buffer, sizeof(audio_buffer), &bytes_read, 0);

  if (bytes_read > 0) {
    int samples = bytes_read / sizeof(int32_t);
    double sum = 0.0;
    for (int i = 0; i < samples; i++) {
      int32_t s = audio_buffer[i] >> 8;
      sum += ((double)s * (double)s);
    }
    last_rms = sqrt(sum / (samples > 0 ? samples : 1)) / 1000.0;
  }

  sample_counter++;

  // 3. Broadcast UDP Telemetry Packet (~50 Hz)
  char packet[96];
  snprintf(packet, sizeof(packet), "%lu,%.2f,%.2f,%.2f,%.1f\n", 
           millis(), last_ax, last_ay, last_az, last_rms);

  udp.beginPacket(broadcastIP, UDP_PORT);
  udp.write((const uint8_t*)packet, strlen(packet));
  udp.endPacket();

  delay(20); // ~50 Hz cycle
}
