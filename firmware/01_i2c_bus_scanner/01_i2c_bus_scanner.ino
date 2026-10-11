// =========================================================================
// 01_i2c_bus_scanner.ino
// Multimodal PdM Project: Step 1 - Hardware Verification
// Scans the I2C bus on GPIO 21 (SDA) and GPIO 22 (SCL) to detect MPU-6050
// Expected Result: "I2C device found at address 0x68"
// =========================================================================

#include <Wire.h>

#define I2C_SDA 21
#define I2C_SCL 22

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("\n--- ESP32 I2C Bus Scanner ---");
  Serial.printf("Initializing I2C on SDA: GPIO %d, SCL: GPIO %d\n", I2C_SDA, I2C_SCL);
  
  Wire.begin(I2C_SDA, I2C_SCL);
}

void loop() {
  byte error, address;
  int nDevices = 0;

  Serial.println("\nScanning I2C bus...");

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf(" [SUCCESS] I2C device found at address: 0x%02X", address);
      if (address == 0x68) {
        Serial.print("  <-- MPU-6050 Detected! (AD0 to GND)");
      } else if (address == 0x69) {
        Serial.print("  <-- MPU-6050 Detected! (AD0 to 3V3)");
      }
      Serial.println();
      nDevices++;
    } else if (error == 4) {
      Serial.printf(" [ERROR] Unknown error at address 0x%02X\n", address);
    }
  }

  if (nDevices == 0) {
    Serial.println(" [WARNING] No I2C devices found.");
    Serial.println(" Check: 1) Is VCC connected to 3V3? 2) Is GND connected? 3) Are SDA/SCL swapped?");
  } else {
    Serial.printf("Scan complete. Total devices found: %d\n", nDevices);
  }

  delay(5000); // Rescan every 5 seconds
}
