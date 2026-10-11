// =========================================================================
// 02_multimodal_telemetry_test.ino
// Multimodal PdM Project: Step 2 - Synchronous Vibration & Acoustic Stream
// Hardware: ESP32 + MPU-6050 (Direct I2C) + INMP441 (I2S DMA)
// Pure Wire.h register read (100% clone compatible, zero hang)
// =========================================================================

#include <Wire.h>
#include <driver/i2s.h>
#include <math.h>

// --- Pin Definitions ---
#define I2C_SDA_PIN   21
#define I2C_SCL_PIN   22
#define MPU_ADDR      0x68

#define I2S_SCK_PIN   33   // Serial Clock (BCLK)
#define I2S_WS_PIN    25   // Word Select (LRCLK)
#define I2S_SD_PIN    32   // Serial Data (DIN)

// --- I2S DMA Configuration ---
#define I2S_PORT          I2S_NUM_0
#define AUDIO_SAMPLE_RATE 16000     // 16 kHz sample rate
#define AUDIO_BUFFER_LEN  128       // Buffer chunk size

int32_t audio_buffer[AUDIO_BUFFER_LEN];

void initMPU() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  delay(100);

  // Wake up MPU-6050 (Register 0x6B = PWR_MGMT_1, set to 0 to wake)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("[OK] MPU-6050 Accelerometer initialized via direct I2C.");
  } else {
    Serial.printf("[ERROR] MPU-6050 I2C error code: %d\n", error);
  }

  // Set Accelerometer Range to ±16g for heavy washing machine spin (Register 0x1C: 0x18 = ±16g)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x18);
  Wire.endTransmission();
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

  esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Failed to install I2S driver: %d\n", err);
  }

  err = i2s_set_pin(I2S_PORT, &pin_config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Failed to set I2S pins: %d\n", err);
  }

  i2s_start(I2S_PORT);
  Serial.println("[OK] INMP441 I2S DMA Audio Driver initialized.");
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n--- Multimodal Telemetry System: Vibration + Acoustics ---");
  initMPU();
  initI2S();
  
  Serial.println("\nStreaming live synchronized telemetry (Plotter compatible):");
  delay(500);
}

void loop() {
  // 1. Read MPU-6050 Vibration (Burst read 6 registers from 0x3B)
  float ax = 0.0, ay = 0.0, az = 0.0;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  if (Wire.available() >= 6) {
    int16_t rawX = (Wire.read() << 8) | Wire.read();
    int16_t rawY = (Wire.read() << 8) | Wire.read();
    int16_t rawZ = (Wire.read() << 8) | Wire.read();

    // ±16g sensitivity scale factor: 2048 LSB/g -> m/s^2
    ax = (rawX / 2048.0) * 9.81;
    ay = (rawY / 2048.0) * 9.81;
    az = (rawZ / 2048.0) * 9.81;
  }

  // 2. Read I2S Microphone Chunk via DMA
  size_t bytes_read = 0;
  i2s_read(I2S_PORT, (char *)audio_buffer, sizeof(audio_buffer), &bytes_read, portMAX_DELAY);

  // 3. Compute Audio Root Mean Square (RMS) Energy
  int samples_read = bytes_read / sizeof(int32_t);
  double sum_squares = 0.0;
  for (int i = 0; i < samples_read; i++) {
    // INMP441 outputs 24-bit audio in 32-bit slot; shift right by 8
    int32_t sample = audio_buffer[i] >> 8;
    sum_squares += ((double)sample * (double)sample);
  }
  double audio_rms = sqrt(sum_squares / (samples_read > 0 ? samples_read : 1));

  // 4. Output Telemetry formatted for Serial Plotter
  Serial.print("Accel_X:");
  Serial.print(ax);
  Serial.print(",Accel_Y:");
  Serial.print(ay);
  Serial.print(",Accel_Z:");
  Serial.print(az);
  Serial.print(",Audio_RMS:");
  Serial.println(audio_rms / 1000.0); // Scaled for balanced visual plotting alongside acceleration

  delay(20); // ~50 Hz update rate
}
