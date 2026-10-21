// =========================================================================
// 07_feature_streamer.ino
// Washer PdM Rig - Firmware 07: on-device window features + low-bandwidth cloud
//
// WHAT CHANGED VS FIRMWARE 05/06 (and why)
//   05/06 uploaded ONE instantaneous accelerometer sample and ONE 8 ms audio
//   RMS every 5 s, i.e. >99% of what the sensors measured was thrown away.
//   07 keeps every sample on the ESP32 and uploads a feature vector that
//   summarises the WHOLE 5 s window:
//     * Audio (16 kHz, continuous): RMS, peak, crest factor, kurtosis,
//       2 kHz high-pass RMS + kurtosis (impulsive / bearing band), block-RMS
//       max & p90, spectral centroid, 6 band RMS values.
//     * Vibration (MPU-6050 FIFO @ 200 Hz with 44 Hz anti-alias DLPF):
//       per-axis mean / std / peak-to-peak, |a| std, dominant frequency
//       (~drum speed) and its amplitude, 4 band RMS values.
//     * Power (Tapo P110 @ 1 Hz, local KLAP): mean / min / max / std.
//
// FIREBASE QUOTA DISCIPLINE (Spark plan: 10 GB/month download, 1 GB stored)
//   * Every write uses ?print=silent -> server answers 204 with no body.
//     (Without it, every PUT echoes the written JSON back = billed download.)
//   * One persistent TLS connection (HTTPClient::setReuse) instead of a new
//     TLS handshake per request. Firebase bills TLS/connection overhead.
//   * Windows are batched: one PATCH per 6 windows (30 s) instead of 6 PUTs.
//   * Upload only while the washer is actually running (session gating);
//     while idle only a small /live heartbeat goes out once a minute.
//   * Failed uploads are kept in a RAM outbox (~10 min) and retried with
//     exponential backoff, so Wi-Fi blips do not lose data and an outage
//     does not turn into a retry storm.
//   * Raw audio clips (for envelope / spall analysis) are served on the LAN
//     at http://washer-pdm.local/clip.wav and NEVER go through Firebase.
//
// CORE AFFINITY (FreeRTOS)
//   Core 1 (Arduino loop): I2S audio read + DSP, MPU FIFO read + DSP.
//                          Hands one WindowRecord per 5 s to Core 0 (queue).
//   Core 0 (cloudTask)   : Wi-Fi, NTP, Tapo polling, session state machine,
//                          outbox + Firebase REST, web server, OTA.
//
// Board: ESP32 Dev Module, core esp32:esp32@3.3.x, partition min_spiffs.
// Pinout unchanged from 05/06 (see CLAUDE.md).
// =========================================================================

// -------------------------------------------------------------------------
// SECTION 1: Includes
// -------------------------------------------------------------------------
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <time.h>
#include <math.h>
#include <stdarg.h>

#include "pdm_dsp.h"      // portable feature extraction (unit-tested on PC)

// -------------------------------------------------------------------------
// SECTION 2: Credentials - ONLY from secrets.h (never hard-coded here)
// -------------------------------------------------------------------------
// Copy secrets.h.example -> secrets.h and fill it in. The build fails on
// purpose if it is missing, so credentials can never silently fall back to
// values baked into a source file that syncs to Google Drive.
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #error "secrets.h missing: copy secrets.h.example to secrets.h and fill in your credentials"
#endif

// -------------------------------------------------------------------------
// SECTION 3: Build-time configuration
// -------------------------------------------------------------------------
#define FW_VERSION              "07.0.0"
#define SCHEMA_VERSION          3          // Firebase record schema (ml/feature_fusion.py reads this)

#ifndef USE_TAPO
  #define USE_TAPO              1          // 1 = poll Tapo P110 locally from the ESP32
#endif
#if USE_TAPO
  #include "tapo_device.h"
#endif

// --- Pins (unchanged) ---
#define I2C_SDA_PIN             21
#define I2C_SCL_PIN             22
#define MPU_ADDR                0x68
#define I2S_SCK_PIN             33         // BCLK
#define I2S_WS_PIN              25         // LRCLK
#define I2S_SD_PIN              32         // DIN
#define I2S_PORT                I2S_NUM_0

// --- Windowing ---
#define WINDOW_AUDIO_BLOCKS     157        // 157 x 512 samples = 80,384 samples = 5.024 s

// --- Upload cadence ---
#define BATCH_WINDOWS           6          // windows per Firebase PATCH (6 x 5 s = 30 s)
#define BATCH_MAX_AGE_MS        60000      // flush a partial batch after 60 s anyway
#define LIVE_ACTIVE_MS          10000      // /live.json period while washing
#define LIVE_IDLE_MS            60000      // /live.json heartbeat while idle
#define OUTBOX_CAPACITY         48         // windows kept in RAM if offline (= 4 min, ~10 kB)
#define BACKOFF_MIN_MS          2000
#define BACKOFF_MAX_MS          300000     // 5 min ceiling between retries

// --- Session gating (when is the washer "running"?) ---
#define ACTIVE_POWER_W          8.0f       // WW10TP44DSX standby is ~1-6 W (LCD on)
#define ACTIVE_VIB_MAG_STD      0.08f      // m/s^2, fallback when Tapo is unavailable
#define START_CONFIRM_WINDOWS   2          // consecutive active windows to open a session
#define IDLE_TIMEOUT_WINDOWS    120        // consecutive idle windows to close (10 min; covers soak pauses)
#define PREROLL_WINDOWS         6          // idle windows kept and uploaded at session start (30 s)

// --- Raw audio clip endpoint (LAN only) ---
#define CLIP_MAX_SECONDS        2          // 2 s x 16 kHz x 2 B = 64 kB of heap (no PSRAM on DevKit)

// -------------------------------------------------------------------------
// SECTION 4: Data structures
// -------------------------------------------------------------------------

// One 5-second window, produced on Core 1, completed (power, epoch) on Core 0.
struct WindowRecord {
  uint32_t idx;              // window counter since boot
  uint32_t t_ms;             // millis() at window end
  uint64_t epoch_ms;         // wall-clock (NTP) at window end, 0 if unknown
  uint16_t fifo_ovf;         // MPU FIFO overflows during the window (data gaps)
  uint16_t vib_clip;         // accel samples at full scale (sensor saturation)
  pdm::AudioFeatures a;
  pdm::VibFeatures v;
  // power (filled on Core 0 from the 1 Hz Tapo samples during the window)
  float p_mean, p_min, p_max, p_std;
  uint16_t p_n;
};

// Outbox entry = window + the session it belongs to.
struct OutboxItem {
  char sid[32];
  WindowRecord w;
};

// Pending session-meta write (start / end / tag).
struct MetaOp {
  char sid[32];
  char path_suffix[24];      // "" = session root, "tags" = tags list, etc.
  char method[6];            // "PUT" or "PATCH"
  char body[256];
};

// -------------------------------------------------------------------------
// SECTION 5: Globals shared between cores
// -------------------------------------------------------------------------
static QueueHandle_t g_window_queue = nullptr;      // Core 1 -> Core 0
static portMUX_TYPE  g_mux = portMUX_INITIALIZER_UNLOCKED;

// DSP engines (large: static storage, not stack)
static pdm::AudioWindow g_audio;
static pdm::VibWindow   g_vib;
static int32_t g_i2s_buf[pdm::AUDIO_BLOCK];

// Latest finished window (for /window.json and /data); guarded by g_mux
static WindowRecord g_latest;
static volatile bool g_have_latest = false;

// Diagnostics counters
static volatile uint32_t g_queue_drops = 0;          // Core 0 too slow (should stay 0)
static uint32_t g_outbox_drops = 0;                  // outbox overflowed while offline
static uint32_t g_upload_ok = 0, g_upload_fail = 0;

// Raw clip capture (Core 0 requests, Core 1 fills)
enum ClipState : uint8_t { CLIP_IDLE = 0, CLIP_FILLING = 1, CLIP_READY = 2 };
static volatile uint8_t  g_clip_state = CLIP_IDLE;
static int16_t*          g_clip_buf = nullptr;
static volatile uint32_t g_clip_len = 0;              // samples requested
static volatile uint32_t g_clip_pos = 0;              // samples captured

// Core-0-only state
static WebServer server(80);
static WiFiClientSecure g_tls;
static HTTPClient g_http;
static bool g_ntp_ok = false;
static uint32_t g_boot_ms = 0;

#if USE_TAPO
static TapoDevice g_tapo;
static bool g_tapo_ok = false;
static uint32_t g_tapo_next_try_ms = 0;
#endif
// power accumulators for the window currently being collected
static double   g_p_sum = 0, g_p_sumsq = 0;
static float    g_p_min = 1e9f, g_p_max = -1e9f;
static uint16_t g_p_n = 0;
static float    g_last_power = NAN;

// Session state machine
static bool     g_session_active = false;
static char     g_sid[32] = "";
static uint32_t g_session_windows = 0;
static int      g_active_streak = 0;
static int      g_idle_streak = 0;
static WindowRecord g_preroll[PREROLL_WINDOWS];
static int      g_preroll_count = 0, g_preroll_head = 0;

// Outbox (ring buffer) + meta queue
static OutboxItem g_outbox[OUTBOX_CAPACITY];
static int      g_ob_head = 0, g_ob_count = 0;
static MetaOp   g_meta[6];
static int      g_meta_count = 0;
static uint32_t g_next_net_try_ms = 0, g_backoff_ms = BACKOFF_MIN_MS;
static uint32_t g_oldest_unsent_ms = 0;

// Pending tag from /tag?name=... (attached to the active session's meta)
static char g_pending_tag[48] = "";

// =========================================================================
// SECTION 6: MPU-6050 low-level (Core 1)
// =========================================================================

static void mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission(true);
}

static uint8_t mpuRead8(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)1, true);
  return Wire.available() ? Wire.read() : 0;
}

static uint16_t mpuFifoCount() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x72);                                   // FIFO_COUNT_H
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)2, true);
  if (Wire.available() < 2) return 0;
  const uint16_t hi = Wire.read();
  const uint16_t lo = Wire.read();
  return (hi << 8) | lo;
}

static void mpuFifoReset() {
  mpuWrite(0x6A, 0x04);                               // USER_CTRL: FIFO_RESET
  delayMicroseconds(50);
  mpuWrite(0x6A, 0x40);                               // USER_CTRL: FIFO_EN
}

// Configure: accel only, 200 Hz output, 44 Hz DLPF (anti-alias), +/-16 g, FIFO on.
static void initMPU() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 400000);      // 400 kHz fast mode
  delay(50);
  mpuWrite(0x6B, 0x00);                               // PWR_MGMT_1: wake, internal 8 MHz clock
  delay(10);
  mpuWrite(0x6C, 0x07);                               // PWR_MGMT_2: gyro X/Y/Z standby (not used)
  mpuWrite(0x1A, 0x03);                               // CONFIG: DLPF_CFG=3 -> accel BW 44 Hz, 1 kHz internal
  mpuWrite(0x19, 0x04);                               // SMPLRT_DIV=4 -> 1 kHz / (1+4) = 200 Hz
  mpuWrite(0x1C, 0x18);                               // ACCEL_CONFIG: +/-16 g (2048 LSB/g), same as 06
  mpuWrite(0x38, 0x00);                               // INT_ENABLE: none (we poll)
  mpuWrite(0x23, 0x08);                               // FIFO_EN: ACCEL only (6 bytes/sample)
  mpuFifoReset();
  Serial.printf("[MPU] WHO_AM_I=0x%02X, 200 Hz FIFO, DLPF 44 Hz, +/-16 g\n", mpuRead8(0x75));
}

// Drain the FIFO into the vibration accumulator. Returns samples read.
// Counters are passed by reference so the caller owns them per window.
static int drainMpuFifo(uint16_t& ovf, uint16_t& clip) {
  // INT_STATUS bit 4 = FIFO_OFLOW (cleared on read). Overflow = lost samples.
  if (mpuRead8(0x3A) & 0x10) { ovf++; mpuFifoReset(); return 0; }
  uint16_t count = mpuFifoCount();
  if (count >= 1008) { ovf++; mpuFifoReset(); return 0; }   // 1024-byte FIFO almost full
  int samples = count / 6;
  int done = 0;
  const float k = 9.80665f / 2048.0f;                        // counts -> m/s^2 at +/-16 g
  while (samples > 0) {
    const int chunk = samples > 20 ? 20 : samples;           // 20 x 6 = 120 B < 128 B Wire buffer
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x74);                                        // FIFO_R_W (streams FIFO bytes)
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)(chunk * 6), true);
    for (int i = 0; i < chunk && Wire.available() >= 6; ++i) {
      const int16_t rx = (int16_t)((Wire.read() << 8) | Wire.read());
      const int16_t ry = (int16_t)((Wire.read() << 8) | Wire.read());
      const int16_t rz = (int16_t)((Wire.read() << 8) | Wire.read());
      if (abs(rx) > 32700 || abs(ry) > 32700 || abs(rz) > 32700) clip++;
      g_vib.addSample(rx * k, ry * k, rz * k);
      ++done;
    }
    samples -= chunk;
  }
  return done;
}

// =========================================================================
// SECTION 7: INMP441 I2S setup (Core 1)
// =========================================================================
static void initI2S() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = pdm::AUDIO_FS;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;           // L/R pin tied to GND
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;                                     // 8 x 512 samples = 256 ms of slack
  cfg.dma_buf_len = pdm::AUDIO_BLOCK;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = false;
  cfg.fixed_mclk = 0;

  i2s_pin_config_t pins = {};
  pins.bck_io_num = I2S_SCK_PIN;
  pins.ws_io_num = I2S_WS_PIN;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = I2S_SD_PIN;

  i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
  i2s_set_pin(I2S_PORT, &pins);
  Serial.println("[I2S] INMP441 continuous 16 kHz capture, 512-sample DMA blocks");
}

// =========================================================================
// SECTION 8: Small helpers (formatting, time)
// =========================================================================

// Append printf-style text to a fixed buffer; returns false if it would overflow.
static bool appendf(char* buf, size_t cap, size_t& len, const char* fmt, ...) {
  if (len >= cap) return false;
  va_list ap;
  va_start(ap, fmt);
  const int n = vsnprintf(buf + len, cap - len, fmt, ap);
  va_end(ap);
  if (n < 0 || (size_t)n >= cap - len) { buf[len] = '\0'; return false; }
  len += (size_t)n;
  return true;
}

// JSON number with 5 significant digits; NaN/Inf -> null (valid JSON).
static void jnum(char* out, size_t cap, float v) {
  if (!isfinite(v)) snprintf(out, cap, "null");
  else snprintf(out, cap, "%.5g", v);
}

static uint64_t epochMs() {
  const time_t s = time(nullptr);
  if (s < 1700000000) return 0;                              // NTP not synced yet
  return (uint64_t)s * 1000ULL + (uint64_t)(millis() % 1000);
}

// =========================================================================
// SECTION 9: Core 1 - acquisition + DSP (Arduino loop)
// =========================================================================
static uint32_t g_window_idx = 0;
static int      g_blocks_in_window = 0;
static uint16_t g_win_ovf = 0, g_win_clip = 0;

void loop() {
  // --- 9a: one 512-sample audio block (blocks ~32 ms, yields the CPU) ---
  size_t bytes = 0;
  i2s_read(I2S_PORT, (char*)g_i2s_buf, sizeof(g_i2s_buf), &bytes, portMAX_DELAY);
  const int n = (int)(bytes / sizeof(int32_t));
  if (n <= 0) return;
  g_audio.processBlock(g_i2s_buf, n);

  // --- 9b: raw clip capture for /clip.wav (int16 = top 16 of the 24 bits) ---
  if (g_clip_state == CLIP_FILLING && g_clip_buf != nullptr) {
    uint32_t pos = g_clip_pos;
    for (int i = 0; i < n && pos < g_clip_len; ++i) g_clip_buf[pos++] = (int16_t)(g_i2s_buf[i] >> 16);
    g_clip_pos = pos;
    if (pos >= g_clip_len) g_clip_state = CLIP_READY;
  }

  // --- 9c: vibration samples that accumulated during this block (~6) ---
  drainMpuFifo(g_win_ovf, g_win_clip);

  // --- 9d: window boundary -> finish features, hand to Core 0 ---
  if (++g_blocks_in_window >= WINDOW_AUDIO_BLOCKS) {
    WindowRecord rec;
    memset(&rec, 0, sizeof(rec));
    rec.idx = ++g_window_idx;
    rec.t_ms = millis();
    rec.fifo_ovf = g_win_ovf;
    rec.vib_clip = g_win_clip;
    g_audio.finish(rec.a);
    g_vib.finish(rec.v);
    if (xQueueSend(g_window_queue, &rec, 0) != pdTRUE) {
      g_queue_drops = g_queue_drops + 1;
    }
    g_blocks_in_window = 0;
    g_win_ovf = g_win_clip = 0;
  }
}

// =========================================================================
// SECTION 10: Firebase REST (Core 0) - persistent TLS, print=silent
// =========================================================================

// Perform one request. Returns the HTTP status (or a negative error code).
static int firebaseRequest(const char* method, const char* path, const char* body, size_t len) {
  static char url[256];
  snprintf(url, sizeof(url), "%s/%s.json?auth=%s&print=silent", FIREBASE_HOST, path, FIREBASE_AUTH);
  if (!g_http.begin(g_tls, url)) return -100;
  g_http.addHeader("Content-Type", "application/json");
  const int code = g_http.sendRequest(method, (uint8_t*)body, len);
  g_http.end();                                       // with setReuse(true) the socket stays open
  return code;
}

static bool httpOk(int code) { return code == 200 || code == 204; }

// Back off after a failure (doubles up to BACKOFF_MAX_MS), reset on success.
static void noteNetResult(bool ok, int code) {
  if (ok) {
    g_backoff_ms = BACKOFF_MIN_MS;
    g_next_net_try_ms = 0;
    g_upload_ok++;
    return;
  }
  g_upload_fail++;
  // 401/403 = bad secret or rules: retrying fast cannot help, wait longest.
  if (code == 401 || code == 403) g_backoff_ms = BACKOFF_MAX_MS;
  g_next_net_try_ms = millis() + g_backoff_ms;
  g_backoff_ms = (g_backoff_ms * 2 > BACKOFF_MAX_MS) ? BACKOFF_MAX_MS : g_backoff_ms * 2;
  Serial.printf("[NET] request failed (code %d), next try in %lu ms\n", code, (unsigned long)g_backoff_ms);
}

// =========================================================================
// SECTION 11: Outbox + meta queue (Core 0)
// =========================================================================

static void outboxPush(const char* sid, const WindowRecord& w) {
  if (g_ob_count == OUTBOX_CAPACITY) {             // full: drop the OLDEST, keep newest
    g_ob_head = (g_ob_head + 1) % OUTBOX_CAPACITY;
    g_ob_count--;
    g_outbox_drops++;
  }
  const int slot = (g_ob_head + g_ob_count) % OUTBOX_CAPACITY;
  strncpy(g_outbox[slot].sid, sid, sizeof(g_outbox[slot].sid) - 1);
  g_outbox[slot].sid[sizeof(g_outbox[slot].sid) - 1] = '\0';
  g_outbox[slot].w = w;
  if (g_ob_count == 0) g_oldest_unsent_ms = millis();
  g_ob_count++;
}

static void metaPush(const char* sid, const char* suffix, const char* method, const char* body) {
  if (g_meta_count >= (int)(sizeof(g_meta) / sizeof(g_meta[0]))) return;   // tiny queue; drop extra tags
  MetaOp& m = g_meta[g_meta_count++];
  strncpy(m.sid, sid, sizeof(m.sid) - 1); m.sid[sizeof(m.sid) - 1] = '\0';
  strncpy(m.path_suffix, suffix, sizeof(m.path_suffix) - 1); m.path_suffix[sizeof(m.path_suffix) - 1] = '\0';
  strncpy(m.method, method, sizeof(m.method) - 1); m.method[sizeof(m.method) - 1] = '\0';
  strncpy(m.body, body, sizeof(m.body) - 1); m.body[sizeof(m.body) - 1] = '\0';
}

// Serialise one window as a compact JSON object (short keys; mapping lives
// in firmware/session_export.py -> V3_KEY_MAP). Keys "t", "rms", "ax", "ay",
// "az", "pwr" deliberately match firmware 05/06 so old tools keep working.
static bool appendWindowJson(char* buf, size_t cap, size_t& len, const WindowRecord& w) {
  char f[48][16];
  int i = 0;
  // audio
  jnum(f[i++], 16, w.a.rms);       jnum(f[i++], 16, w.a.peak);     jnum(f[i++], 16, w.a.crest);
  jnum(f[i++], 16, w.a.kurtosis);  jnum(f[i++], 16, w.a.hp_rms);   jnum(f[i++], 16, w.a.hp_kurt);
  jnum(f[i++], 16, w.a.blk_max);   jnum(f[i++], 16, w.a.blk_p90);  jnum(f[i++], 16, w.a.centroid_hz);
  for (int b = 0; b < pdm::AUDIO_N_BANDS; ++b) jnum(f[i++], 16, w.a.band[b]);       // i = 15
  // vibration
  for (int a = 0; a < 3; ++a) jnum(f[i++], 16, w.v.mean[a]);                        // 15..17
  for (int a = 0; a < 3; ++a) jnum(f[i++], 16, w.v.std[a]);                         // 18..20
  for (int a = 0; a < 3; ++a) jnum(f[i++], 16, w.v.ptp[a]);                         // 21..23
  jnum(f[i++], 16, w.v.mag_std);   jnum(f[i++], 16, w.v.dom_hz);   jnum(f[i++], 16, w.v.dom_rms);  // 24..26
  for (int b = 0; b < pdm::VIB_N_BANDS; ++b) jnum(f[i++], 16, w.v.band[b]);        // 27..30
  // power
  jnum(f[i++], 16, w.p_mean); jnum(f[i++], 16, w.p_min); jnum(f[i++], 16, w.p_max); jnum(f[i++], 16, w.p_std); // 31..34

  return appendf(buf, cap, len,
    "\"w%06lu\":{\"t\":%lu,\"e\":%llu,\"na\":%lu,\"nv\":%lu,\"np\":%u,\"ov\":%u,\"vc\":%u,"
    "\"rms\":%s,\"apk\":%s,\"acr\":%s,\"aku\":%s,\"ahr\":%s,\"ahk\":%s,\"abm\":%s,\"ab9\":%s,\"acn\":%s,"
    "\"ab0\":%s,\"ab1\":%s,\"ab2\":%s,\"ab3\":%s,\"ab4\":%s,\"ab5\":%s,"
    "\"ax\":%s,\"ay\":%s,\"az\":%s,\"sx\":%s,\"sy\":%s,\"sz\":%s,\"px\":%s,\"py\":%s,\"pz\":%s,"
    "\"sm\":%s,\"vdf\":%s,\"vdr\":%s,\"vb0\":%s,\"vb1\":%s,\"vb2\":%s,\"vb3\":%s,"
    "\"pwr\":%s,\"pmn\":%s,\"pmx\":%s,\"psd\":%s}",
    (unsigned long)w.idx, (unsigned long)w.t_ms, (unsigned long long)w.epoch_ms,
    (unsigned long)w.a.n, (unsigned long)w.v.n, (unsigned)w.p_n, (unsigned)w.fifo_ovf, (unsigned)w.vib_clip,
    f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8],
    f[9], f[10], f[11], f[12], f[13], f[14],
    f[15], f[16], f[17], f[18], f[19], f[20], f[21], f[22], f[23],
    f[24], f[25], f[26], f[27], f[28], f[29], f[30],
    f[31], f[32], f[33], f[34]);
}

// Try to send pending meta ops, then one batch of windows. Called often;
// does nothing while backing off, offline, or when there is nothing due.
static void serviceUploads() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (g_next_net_try_ms != 0 && (int32_t)(millis() - g_next_net_try_ms) < 0) return;

  // --- 11a: session meta first (start record must exist before windows) ---
  // Exception: an END marker waits until every window of that session is
  // uploaded, so the PC daemon never archives a session with a missing tail.
  bool meta_blocked = false;
  if (g_meta_count > 0 && strcmp(g_meta[0].method, "PATCH") == 0 && g_meta[0].path_suffix[0] == '\0') {
    for (int k = 0; k < g_ob_count; ++k) {
      if (strcmp(g_outbox[(g_ob_head + k) % OUTBOX_CAPACITY].sid, g_meta[0].sid) == 0) { meta_blocked = true; break; }
    }
  }
  if (g_meta_count > 0 && !meta_blocked) {
    MetaOp& m = g_meta[0];
    char path[80];
    if (m.path_suffix[0]) snprintf(path, sizeof(path), "session_meta/%s/%s", m.sid, m.path_suffix);
    else snprintf(path, sizeof(path), "session_meta/%s", m.sid);
    const int code = firebaseRequest(m.method, path, m.body, strlen(m.body));
    const bool ok = httpOk(code);
    noteNetResult(ok, code);
    if (!ok) return;
    for (int i = 1; i < g_meta_count; ++i) g_meta[i - 1] = g_meta[i];
    g_meta_count--;
    return;                                         // one request per call keeps Core 0 responsive
  }

  // --- 11b: windows, batched per session ---
  if (g_ob_count == 0) return;
  const bool batch_full = g_ob_count >= BATCH_WINDOWS;
  const bool batch_old = (millis() - g_oldest_unsent_ms) >= BATCH_MAX_AGE_MS;
  if (!batch_full && !batch_old && g_session_active) return;   // wait for a full batch while washing

  static char body[4096];
  size_t len = 0;
  appendf(body, sizeof(body), len, "{");
  const char* sid = g_outbox[g_ob_head].sid;
  int taken = 0;
  for (int k = 0; k < g_ob_count && taken < BATCH_WINDOWS; ++k) {
    const OutboxItem& it = g_outbox[(g_ob_head + k) % OUTBOX_CAPACITY];
    if (strcmp(it.sid, sid) != 0) break;            // never mix two sessions in one PATCH
    const size_t mark = len;
    if (taken > 0 && !appendf(body, sizeof(body), len, ",")) { len = mark; break; }
    if (!appendWindowJson(body, sizeof(body), len, it.w)) { len = mark; body[len] = '\0'; break; }
    taken++;
  }
  appendf(body, sizeof(body), len, "}");
  if (taken == 0) return;

  char path[64];
  snprintf(path, sizeof(path), "sessions/%s", sid);
  const int code = firebaseRequest("PATCH", path, body, len);   // PATCH merges children
  const bool ok = httpOk(code);
  noteNetResult(ok, code);
  if (ok) {
    g_ob_head = (g_ob_head + taken) % OUTBOX_CAPACITY;
    g_ob_count -= taken;
    g_oldest_unsent_ms = millis();
  }
}

// =========================================================================
// SECTION 12: Session state machine (Core 0)
// =========================================================================

static bool windowIsActive(const WindowRecord& w) {
#if USE_TAPO
  if (g_tapo_ok && w.p_n > 0 && isfinite(w.p_mean)) return w.p_mean > ACTIVE_POWER_W;
#endif
  // Fallback without a working power meter: vibration level only.
  return isfinite(w.v.mag_std) && w.v.mag_std > ACTIVE_VIB_MAG_STD;
}

static void makeSessionId(char* out, size_t cap) {
  struct tm ti;
  if (g_ntp_ok && getLocalTime(&ti, 10)) strftime(out, cap, "wash_%Y-%m-%d_%H%M%S", &ti);
  else snprintf(out, cap, "wash_up%lu_%04X", (unsigned long)(millis() / 1000), (unsigned)(esp_random() & 0xFFFF));
}

static void openSession() {
  makeSessionId(g_sid, sizeof(g_sid));
  g_session_active = true;
  g_session_windows = 0;
  char body[256];
  snprintf(body, sizeof(body),
           "{\"start\":{\".sv\":\"timestamp\"},\"start_epoch_ms\":%llu,\"fw\":\"%s\",\"schema\":%d,"
           "\"window_s\":5.024,\"fs_audio\":16000,\"fs_accel\":200,\"tapo\":%s}",
           (unsigned long long)epochMs(), FW_VERSION, SCHEMA_VERSION,
#if USE_TAPO
           g_tapo_ok ? "true" : "false"
#else
           "false"
#endif
  );
  metaPush(g_sid, "", "PUT", body);
  // flush the pre-roll so the session starts ~30 s before activity was confirmed
  for (int i = 0; i < g_preroll_count; ++i) {
    const int j = (g_preroll_head + i) % PREROLL_WINDOWS;
    outboxPush(g_sid, g_preroll[j]);
    g_session_windows++;
  }
  g_preroll_count = 0;
  Serial.printf("[SESSION] opened %s\n", g_sid);
}

static void closeSession(const char* reason) {
  char body[200];
  snprintf(body, sizeof(body),
           "{\"end\":{\".sv\":\"timestamp\"},\"end_epoch_ms\":%llu,\"n_windows\":%lu,"
           "\"outbox_drops\":%lu,\"queue_drops\":%lu,\"end_reason\":\"%s\"}",
           (unsigned long long)epochMs(), (unsigned long)g_session_windows,
           (unsigned long)g_outbox_drops, (unsigned long)g_queue_drops, reason);
  metaPush(g_sid, "", "PATCH", body);
  Serial.printf("[SESSION] closed %s (%lu windows, %s)\n", g_sid, (unsigned long)g_session_windows, reason);
  g_session_active = false;
  g_sid[0] = '\0';
  g_active_streak = g_idle_streak = 0;
}

static void handleWindow(WindowRecord& w) {
  const bool active = windowIsActive(w);
  g_active_streak = active ? g_active_streak + 1 : 0;
  g_idle_streak = active ? 0 : g_idle_streak + 1;

  if (!g_session_active) {
    if (g_active_streak >= START_CONFIRM_WINDOWS) {
      openSession();
      outboxPush(g_sid, w);
      g_session_windows++;
    } else {
      // keep a short pre-roll of idle windows
      const int slot = (g_preroll_head + g_preroll_count) % PREROLL_WINDOWS;
      g_preroll[slot] = w;
      if (g_preroll_count < PREROLL_WINDOWS) g_preroll_count++;
      else g_preroll_head = (g_preroll_head + 1) % PREROLL_WINDOWS;
    }
  } else {
    outboxPush(g_sid, w);
    g_session_windows++;
    if (g_pending_tag[0]) {
      char body[96];
      snprintf(body, sizeof(body), "{\"w%06lu\":\"%s\"}", (unsigned long)w.idx, g_pending_tag);
      metaPush(g_sid, "tags", "PATCH", body);
      g_pending_tag[0] = '\0';
    }
    if (g_idle_streak >= IDLE_TIMEOUT_WINDOWS) closeSession("idle_timeout");
  }
}

// =========================================================================
// SECTION 13: /live.json heartbeat (Core 0)
// =========================================================================
static void maybeSendLive() {
  static uint32_t last = 0;
  const uint32_t period = g_session_active ? LIVE_ACTIVE_MS : LIVE_IDLE_MS;
  if (last != 0 && millis() - last < period) return;
  if (WiFi.status() != WL_CONNECTED) return;
  if (g_next_net_try_ms != 0 && (int32_t)(millis() - g_next_net_try_ms) < 0) return;
  last = millis();

  WindowRecord w;
  bool have;
  portENTER_CRITICAL(&g_mux);
  have = g_have_latest;
  w = g_latest;
  portEXIT_CRITICAL(&g_mux);

  char ax[16], ay[16], az[16], rms[16], vib[16], pwr[16], vibe[16];
  // "vibe" = |mean acceleration| (~9.8 m/s^2), the field the 05/06 dashboards plot
  const float vmag = have ? sqrtf(w.v.mean[0] * w.v.mean[0] + w.v.mean[1] * w.v.mean[1] + w.v.mean[2] * w.v.mean[2]) : NAN;
  jnum(vibe, 16, vmag);
  jnum(ax, 16, have ? w.v.mean[0] : NAN); jnum(ay, 16, have ? w.v.mean[1] : NAN);
  jnum(az, 16, have ? w.v.mean[2] : NAN); jnum(rms, 16, have ? w.a.rms : NAN);
  jnum(vib, 16, have ? w.v.mag_std : NAN); jnum(pwr, 16, g_last_power);

  char body[480];
  snprintf(body, sizeof(body),
    "{\"ts\":{\".sv\":\"timestamp\"},\"fw\":\"%s\",\"schema\":%d,\"uptime\":%lu,\"cnt\":%lu,"
    "\"session\":\"%s\",\"active\":%s,\"state\":\"%s\",\"ax\":%s,\"ay\":%s,\"az\":%s,\"rms\":%s,"
    "\"vibe\":%s,\"vib_std\":%s,\"power\":%s,\"outbox\":%d,\"drops\":%lu,\"rssi\":%d,\"heap\":%lu}",
    FW_VERSION, SCHEMA_VERSION, (unsigned long)((millis() - g_boot_ms) / 1000), (unsigned long)(have ? w.idx : 0),
    g_sid, g_session_active ? "true" : "false", g_session_active ? "RUNNING" : "IDLE",
    ax, ay, az, rms, vibe, vib, pwr, g_ob_count, (unsigned long)(g_outbox_drops + g_queue_drops),
    (int)WiFi.RSSI(), (unsigned long)ESP.getFreeHeap());
  const int code = firebaseRequest("PUT", "live", body, strlen(body));
  noteNetResult(httpOk(code), code);
}

// =========================================================================
// SECTION 14: Local web server (LAN only)
// =========================================================================

// GET /  -> tiny status page (no heavy dashboard: saves flash and CPU)
static void handleRoot() {
  char html[900];
  snprintf(html, sizeof(html),
    "<!doctype html><meta name=viewport content='width=device-width'><title>Washer PdM 07</title>"
    "<body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:16px'>"
    "<h3>Washer PdM rig &middot; fw %s</h3>"
    "<p>Session: <b>%s</b> | outbox %d | uploads ok %lu / fail %lu | drops %lu</p>"
    "<p><a style='color:#38bdf8' href='/window.json'>latest window</a> &middot; "
    "<a style='color:#38bdf8' href='/clip.wav?sec=2'>2 s audio clip</a> &middot; "
    "<a style='color:#38bdf8' href='/accel.csv'>accel ring (2.56 s)</a></p>"
    "<p>Tag the running session: /tag?name=unbalanced_load</p></body>",
    FW_VERSION, g_session_active ? g_sid : "(idle)", g_ob_count,
    (unsigned long)g_upload_ok, (unsigned long)g_upload_fail, (unsigned long)(g_outbox_drops + g_queue_drops));
  server.send(200, "text/html", html);
}

// GET /window.json -> latest window in the same compact format as Firebase
static void handleWindowJson() {
  WindowRecord w;
  bool have;
  portENTER_CRITICAL(&g_mux); have = g_have_latest; w = g_latest; portEXIT_CRITICAL(&g_mux);
  if (!have) { server.send(503, "application/json", "{\"error\":\"no window yet\"}"); return; }
  static char body[1400];
  size_t len = 0;
  appendf(body, sizeof(body), len, "{");
  appendWindowJson(body, sizeof(body), len, w);
  appendf(body, sizeof(body), len, ",\"session\":\"%s\"}", g_sid);
  server.send(200, "application/json", body);
}

// GET /data -> backwards compatible with 05/06 dashboards {ax,ay,az,rms,cnt}
static void handleData() {
  WindowRecord w;
  bool have;
  portENTER_CRITICAL(&g_mux); have = g_have_latest; w = g_latest; portEXIT_CRITICAL(&g_mux);
  char body[160];
  snprintf(body, sizeof(body), "{\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"rms\":%.1f,\"cnt\":%lu}",
           have ? w.v.mean[0] : 0.0f, have ? w.v.mean[1] : 0.0f, have ? w.v.mean[2] : 0.0f,
           have ? w.a.rms : 0.0f, (unsigned long)(have ? w.idx : 0));
  server.send(200, "application/json", body);
}

// GET /tag?name=xyz -> attach a label to the running session (for safe,
// reversible perturbation experiments, e.g. unbalanced_load, soft_mat).
static void handleTag() {
  if (!server.hasArg("name")) { server.send(400, "text/plain", "use /tag?name=label"); return; }
  String name = server.arg("name");
  name.replace("\"", ""); name.replace("\\", "");
  strncpy(g_pending_tag, name.c_str(), sizeof(g_pending_tag) - 1);
  g_pending_tag[sizeof(g_pending_tag) - 1] = '\0';
  server.send(200, "text/plain", g_session_active ? "tag queued for running session" : "no session running (tag kept for next one)");
}

// GET /accel.csv -> last 2.56 s of raw 200 Hz acceleration (diagnostics)
static void handleAccelCsv() {
  float (*snap)[3] = (float (*)[3])malloc(sizeof(float) * pdm::VIB_FFT * 3);
  if (!snap) {
    server.send(503, "text/plain", "out of memory");
    return;
  }
  int n;
  portENTER_CRITICAL(&g_mux);           // short copy; Core 1 may write mid-copy at worst one sample
  n = g_vib.snapshot(snap, pdm::VIB_FFT);
  portEXIT_CRITICAL(&g_mux);
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "text/csv", "i,ax,ay,az\n");
  char line[64];
  for (int i = 0; i < n; ++i) {
    snprintf(line, sizeof(line), "%d,%.4f,%.4f,%.4f\n", i, snap[i][0], snap[i][1], snap[i][2]);
    server.sendContent(line);
  }
  server.sendContent("");
  free(snap);
}

// GET /clip.wav?sec=2 -> raw mono 16-bit 16 kHz WAV, captured live on Core 1
static void handleClip() {
  uint32_t sec = server.hasArg("sec") ? (uint32_t)server.arg("sec").toInt() : 2;
  if (sec < 1) sec = 1;
  if (sec > CLIP_MAX_SECONDS) sec = CLIP_MAX_SECONDS;
  const uint32_t ns = sec * pdm::AUDIO_FS;
  if (g_clip_state != CLIP_IDLE) { server.send(409, "text/plain", "clip already in progress"); return; }
  if (ESP.getMaxAllocHeap() < ns * 2 + 16384) { server.send(507, "text/plain", "not enough heap"); return; }
  g_clip_buf = (int16_t*)malloc(ns * 2);
  if (!g_clip_buf) { server.send(507, "text/plain", "malloc failed"); return; }
  g_clip_pos = 0;
  g_clip_len = ns;
  g_clip_state = CLIP_FILLING;                       // Core 1 starts copying from the next block
  const uint32_t t0 = millis();
  while (g_clip_state != CLIP_READY && millis() - t0 < sec * 1000 + 2000) vTaskDelay(pdMS_TO_TICKS(20));
  if (g_clip_state != CLIP_READY) {
    g_clip_state = CLIP_IDLE; free(g_clip_buf); g_clip_buf = nullptr;
    server.send(504, "text/plain", "capture timeout");
    return;
  }
  // 44-byte canonical WAV header
  uint8_t hdr[44];
  const uint32_t data_bytes = ns * 2, rate = pdm::AUDIO_FS, byte_rate = rate * 2;
  memcpy(hdr, "RIFF", 4);  const uint32_t riff = 36 + data_bytes; memcpy(hdr + 4, &riff, 4);
  memcpy(hdr + 8, "WAVEfmt ", 8);
  const uint32_t fmt_len = 16; memcpy(hdr + 16, &fmt_len, 4);
  const uint16_t pcm = 1, ch = 1, align = 2, bits = 16;
  memcpy(hdr + 20, &pcm, 2); memcpy(hdr + 22, &ch, 2); memcpy(hdr + 24, &rate, 4);
  memcpy(hdr + 28, &byte_rate, 4); memcpy(hdr + 32, &align, 2); memcpy(hdr + 34, &bits, 2);
  memcpy(hdr + 36, "data", 4); memcpy(hdr + 40, &data_bytes, 4);

  server.setContentLength(44 + data_bytes);
  server.sendHeader("X-Session", g_sid);
  server.send(200, "audio/wav", "");
  server.sendContent((const char*)hdr, 44);
  const uint8_t* p = (const uint8_t*)g_clip_buf;
  for (uint32_t off = 0; off < data_bytes; off += 4096) {
    const uint32_t chunk = (data_bytes - off) > 4096 ? 4096 : (data_bytes - off);
    server.sendContent((const char*)(p + off), chunk);
  }
  free(g_clip_buf);
  g_clip_buf = nullptr;
  g_clip_state = CLIP_IDLE;
}

// =========================================================================
// SECTION 15: Core 0 task - network, power, sessions
// =========================================================================
static void cloudTask(void*) {
  g_tls.setInsecure();               // NOTE: no certificate pinning (see README security notes)
  g_http.setReuse(true);             // keep ONE TLS connection alive across requests
  g_http.setTimeout(8000);

  for (;;) {
    server.handleClient();
    ArduinoOTA.handle();

    // --- 15a: NTP (needed for session IDs and window epoch timestamps) ---
    if (!g_ntp_ok && WiFi.status() == WL_CONNECTED && time(nullptr) > 1700000000) {
      g_ntp_ok = true;
      Serial.println("[NTP] synced");
    }

    // --- 15b: Tapo P110 power, 1 Hz, with 10 s backoff after a failure ---
#if USE_TAPO
    static uint32_t last_tapo = 0;
    if (WiFi.status() == WL_CONNECTED && millis() - last_tapo >= 1000 &&
        (int32_t)(millis() - g_tapo_next_try_ms) >= 0) {
      last_tapo = millis();
      if (!g_tapo_ok) g_tapo_ok = g_tapo.begin(TAPO_IP, TAPO_USER, TAPO_PASS);
      if (g_tapo_ok) {
        const float pw = g_tapo.get_power_w();
        if (pw >= 0.0f) {
          g_last_power = pw;
          g_p_sum += pw; g_p_sumsq += (double)pw * pw; g_p_n++;
          if (pw < g_p_min) g_p_min = pw;
          if (pw > g_p_max) g_p_max = pw;
        } else {
          g_tapo_ok = false;
          g_tapo_next_try_ms = millis() + 10000;
        }
      } else {
        g_tapo_next_try_ms = millis() + 10000;
      }
    }
#endif

    // --- 15c: consume finished windows from Core 1 ---
    WindowRecord w;
    while (xQueueReceive(g_window_queue, &w, 0) == pdTRUE) {
      w.epoch_ms = epochMs();
      if (g_p_n > 0) {
        const double mu = g_p_sum / g_p_n;
        w.p_mean = (float)mu;
        w.p_std = (float)sqrt(fmax(0.0, g_p_sumsq / g_p_n - mu * mu));
        w.p_min = g_p_min; w.p_max = g_p_max; w.p_n = g_p_n;
      } else {
        w.p_mean = w.p_std = w.p_min = w.p_max = NAN; w.p_n = 0;
      }
      g_p_sum = g_p_sumsq = 0; g_p_n = 0; g_p_min = 1e9f; g_p_max = -1e9f;

      portENTER_CRITICAL(&g_mux);
      g_latest = w; g_have_latest = true;
      portEXIT_CRITICAL(&g_mux);

      handleWindow(w);
    }

    // --- 15d: uploads (meta, batched windows, heartbeat) ---
    serviceUploads();
    maybeSendLive();

    // --- 15e: Wi-Fi watchdog ---
    static uint32_t last_reconnect = 0;
    if (WiFi.status() != WL_CONNECTED && millis() - last_reconnect > 15000) {
      last_reconnect = millis();
      WiFi.reconnect();
    }

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

// =========================================================================
// SECTION 16: setup()
// =========================================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.printf("\n=== Washer PdM firmware %s (windowed features) ===\n", FW_VERSION);
  g_boot_ms = millis();

  // --- 16a: DSP engines and the Core1->Core0 queue ---
  g_audio.init();
  g_vib.init();
  g_window_queue = xQueueCreate(8, sizeof(WindowRecord));

  // --- 16b: sensors ---
  initMPU();
  initI2S();

  // --- 16c: Wi-Fi (station only; no open fallback hotspot) ---
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; ++i) delay(250);
  Serial.printf("[WIFI] %s\n", WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "not connected yet (will retry)");

  // --- 16d: NTP (UTC+8), mDNS, OTA, web routes ---
  configTime(8 * 3600, 0, "pool.ntp.org", "time.google.com", "time.cloudflare.com");
  MDNS.begin("washer-pdm");
  ArduinoOTA.setHostname("washer-pdm-rig");
#ifdef OTA_PASS
  ArduinoOTA.setPassword(OTA_PASS);
#endif
  ArduinoOTA.begin();
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/window.json", handleWindowJson);
  server.on("/tag", handleTag);
  server.on("/accel.csv", handleAccelCsv);
  server.on("/clip.wav", handleClip);
  server.begin();

  // --- 16e: network task on Core 0 (16 kB stack: TLS + JSON buffers are static) ---
  xTaskCreatePinnedToCore(cloudTask, "cloudTask", 16384, nullptr, 1, nullptr, 0);
  Serial.println("[SYSTEM] Core 1 = acquisition/DSP, Core 0 = network");
}
