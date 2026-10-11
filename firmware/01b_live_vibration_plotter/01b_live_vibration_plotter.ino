// =========================================================================
// 01b_live_vibration_plotter.ino
// Multimodal PdM Project: Step 1b - Direct Live 3-Axis Vibration Streamer
// Direct I2C register read (Pure Wire.h, zero third-party library hangs)
// =========================================================================

#include <Wire.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define MPU_ADDR 0x68

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Direct MPU-6050 Vibration Plotter ---");

  Wire.begin(I2C_SDA, I2C_SCL);

  // Wake up MPU-6050 (Register 0x6B = PWR_MGMT_1, set to 0 to wake from sleep)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("[SUCCESS] MPU-6050 Woken up and streaming data!");
  } else {
    Serial.printf("[ERROR] I2C communication failed with error code: %d\n", error);
  }
}

void loop() {
  // Request 6 registers starting at 0x3B (ACCEL_XOUT_H)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  if (Wire.available() >= 6) {
    int16_t rawX = (Wire.read() << 8) | Wire.read();
    int16_t rawY = (Wire.read() << 8) | Wire.read();
    int16_t rawZ = (Wire.read() << 8) | Wire.read();

    // Convert raw values to m/s^2 (Standard ±2g sensitivity: 16384 LSB/g)
    float ax = (rawX / 16384.0) * 9.81;
    float ay = (rawY / 16384.0) * 9.81;
    float az = (rawZ / 16384.0) * 9.81;

    // Format for Arduino Serial Plotter & Monitor
    Serial.print("Accel_X:");
    Serial.print(ax);
    Serial.print(",Accel_Y:");
    Serial.print(ay);
    Serial.print(",Accel_Z:");
    Serial.println(az);
  }

  delay(30); // ~33 Hz smooth refresh rate
}
