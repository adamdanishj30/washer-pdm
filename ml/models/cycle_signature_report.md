# Wash Cycle Physical Signatures & Programme Report

**Generated:** 2026-10-21 19:05:25  
**Cycles Analyzed:** 13 archived sessions in `data/real_sessions/`  
**Source:** Measured kinematics (MPU-6050), active electrical power (Tapo P110), and SmartThings API.  

---

## 1. Executive Summary & Physics Findings

Archived wash cycles were classified by their measured electrical power and mechanical spin signatures into computed groups:
- **Long cold (inferred) (4 cycles):** `wash_cycle_2026-10-16_0857.csv`, `wash_cycle_2026-10-17_0718.csv`, `wash_cycle_2026-10-18_0516.csv`, `wash_cycle_2026-10-19_0911.csv`
- **Long hot (inferred) (1 cycles):** `wash_cycle_2026-10-20_0744.csv`
- **No power data (6 cycles):** `wash_cycle_2026-10-11_1019.csv`, `wash_cycle_2026-10-12_1019.csv`, `wash_cycle_2026-10-15_1020.csv`, `wash_cycle_2026-10-15_morning.csv`, `wash_cycle_2026-10-17_0835.csv`, `wash_cycle_2026-10-19_0022.csv`
- **Quick (inferred) (2 cycles):** `wash_cycle_2026-10-21_0514.csv`, `wash_cycle_2026-10-21_0631.csv`

**Measured Energy Per Wash:**
- **Long cold:** 0.10–0.11 kWh per wash
- **Long hot:** 0.55 kWh per wash
- **Quick:** 0.03–0.04 kWh per wash
- **No power data:** n/a (unmetered runs)

Energy is integrated from 1 Hz smart-plug power averaged per window. It represents the washer's total electrical draw, not a fault signal.

**Sensor Integrity Across Firmware-07 Runs:**
- Idle vibration noise floor `vib_mag_std` median is **0.032 m/s²** across all firmware-07 runs.
- Maximum spin extraction dominant frequency $p90 \approx 20.0\text{ Hz}$ (~1,200 RPM) across all spin blocks.
- Maximum sample acquisition gap is exactly **5.02 s** (measured via ESP32 hardware millisecond timer `timestamp_ms`).
- Zero accelerometer clipping samples occurred across all firmware-07 sessions.

---

## 2. Comprehensive Cycle Signatures Table

| Session File | Schema | Rows | Rec. Min | Active Min | Heater Min | Spin Blocks | High-Pwr Blocks | Energy (kWh) | Peak W | Signature (inferred from power) | Programme | Water Temp | Load (kg) | Context Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-11_1019.csv` | legacy | 422 | 35.2 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-12_1019.csv` | legacy | 1216 | 101.3 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-15_1020.csv` | legacy | 276 | 23.0 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-15_morning.csv` | legacy | 1216 | 101.3 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-16_0857.csv` | legacy | 857 | 71.4 | 64 | 0 | 3 | 5 | 0.101 | 774 | **Long cold (inferred)** | `unknown` | - | - | `smartthings_live` |
| `wash_cycle_2026-10-17_0718.csv` | legacy | 854 | 71.2 | 76 | 0 | 3 | 3 | 0.113 | 565 | **Long cold (inferred)** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-17_0835.csv` | legacy | 792 | 66.0 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-18_0516.csv` | legacy | 828 | 69.0 | 64 | 0 | 3 | 4 | 0.106 | 401 | **Long cold (inferred)** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-19_0022.csv` | legacy | 167 | 13.9 | n/a | n/a | n/a | n/a | n/a | n/a | **No power data** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-19_0911.csv` | fw07 | 786 | 65.7 | 64 | 0 | 3 | 3 | 0.112 | 420 | **Long cold (inferred)** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-20_0744.csv` | fw07 | 965 | 80.7 | 71 | 11.9 | 3 | 4 | 0.549 | 2290 | **Long hot (inferred)** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-21_0514.csv` | fw07 | 387 | 32.3 | 22 | 0 | 1 | 1 | 0.036 | 373 | **Quick (inferred)** | `unknown` | - | - | `unknown` |
| `wash_cycle_2026-10-21_0631.csv` | fw07 | 348 | 29.1 | 21 | 0 | 1 | 1 | 0.029 | 302 | **Quick (inferred)** | `unknown` | - | - | `unknown` |

---

## 3. Firmware-07 Data Quality & Kinematic Profile

Telemetry verification table for firmware-07 45-column windowed records:

| Session File | `n_accel` (med/min) | FIFO Overflow | Clipped | Max Gap (s) | Epoch Jitter Max (s) | Idle `vib_mag_std` | Spin `vib_dom_hz` p90 | Boot at Start |
|---|---|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-19_0911.csv` | 1013 / 965 | 1 | 0 | 5.02 s | 2.74 s | 0.032 m/s² | 19.9 Hz | yes |
| `wash_cycle_2026-10-20_0744.csv` | 1014 / 964 | 1 | 0 | 5.02 s | 3.75 s | 0.032 m/s² | 19.9 Hz | yes |
| `wash_cycle_2026-10-21_0514.csv` | 1013 / 962 | 1 | 0 | 5.02 s | 3.36 s | 0.032 m/s² | 20.0 Hz | yes |
| `wash_cycle_2026-10-21_0631.csv` | 1013 / 1012 | 0 | 0 | 5.02 s | 3.65 s | 0.032 m/s² | 20.0 Hz | no |

---

## 4. High-Power Electrical Profile Breakdown

Detailed timing and electrical peak for all blocks with $\ge 3$ consecutive windows $> 200\text{ W}$:

### `wash_cycle_2026-10-19_0911.csv` (fw07, 64 active min)
- **Block 1** (Spin Extraction): start at **36.7 min**, peak **420 W**, duration **2.8 min** (34 windows)
- **Block 2** (Spin Extraction): start at **46.8 min**, peak **377 W**, duration **2.8 min** (33 windows)
- **Block 3** (Spin Extraction): start at **60.6 min**, peak **372 W**, duration **2.5 min** (30 windows)

### `wash_cycle_2026-10-20_0744.csv` (fw07, 71 active min)
- **Block 1** (Heater): start at **3.5 min**, peak **2290 W**, duration **11.9 min** (142 windows)
- **Block 2** (Spin Extraction): start at **40.1 min**, peak **614 W**, duration **2.6 min** (31 windows)
- **Block 3** (Spin Extraction): start at **50.7 min**, peak **902 W**, duration **2.6 min** (31 windows)
- **Block 4** (Spin Extraction): start at **67.4 min**, peak **405 W**, duration **2.4 min** (29 windows)

### `wash_cycle_2026-10-21_0514.csv` (fw07, 22 active min)
- **Block 1** (Spin Extraction): start at **17.9 min**, peak **373 W**, duration **3.5 min** (42 windows)

### `wash_cycle_2026-10-21_0631.csv` (fw07, 21 active min)
- **Block 1** (Spin Extraction): start at **17.1 min**, peak **302 W**, duration **3.0 min** (36 windows)

---

## 5. Physical Signature Grouping

Cycles clustered dynamically by verified physical rules (Heater Minutes $\times$ Spin Block Count):

| Signature Class | Physical Decision Rule | Member Count | Member Sessions |
|---|---|---|---|
| **Long cold (inferred)** | Heater == 0 min, Spin Blocks >= 3 | 4 | `wash_cycle_2026-10-16_0857.csv`<br>`wash_cycle_2026-10-17_0718.csv`<br>`wash_cycle_2026-10-18_0516.csv`<br>`wash_cycle_2026-10-19_0911.csv` |
| **Long hot (inferred)** | Heater > 2 min (>1 kW), Spin Blocks >= 2 | 1 | `wash_cycle_2026-10-20_0744.csv` |
| **Quick (inferred)** | Heater == 0 min, Spin Blocks == 1, Active < 35 min | 2 | `wash_cycle_2026-10-21_0514.csv`<br>`wash_cycle_2026-10-21_0631.csv` |
| **No power data** | Maximum power < 50 W (legacy unmetered runs) | 6 | `wash_cycle_2026-10-11_1019.csv`<br>`wash_cycle_2026-10-12_1019.csv`<br>`wash_cycle_2026-10-15_1020.csv`<br>`wash_cycle_2026-10-15_morning.csv`<br>`wash_cycle_2026-10-17_0835.csv`<br>`wash_cycle_2026-10-19_0022.csv` |

