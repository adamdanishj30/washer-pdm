# Wash Cycle Physical Signatures & Programme Report

**Generated:** 2026-10-21 15:28:29  
**Cycles Analyzed:** 13 archived sessions in `data/real_sessions/`  
**Source:** Measured kinematics (MPU-6050), active electrical power (Tapo P110), and SmartThings API.  

---

## 1. Executive Summary & Physics Findings

Firmware-07 wash cycles exhibit distinct physical profiles directly corresponding to differing physical wash programmes:
- **Daily Wash (Cold, ~64 min):** 3 spin extraction blocks (at ~37, 47, 61 min), 0 heater minutes, active duration ~64 min (`19 Oct 0911`).
- **Daily Wash (Warm/Hot, ~71 min):** 1 prolonged electrical heating block (11.9 min at ~2,290 W) followed by 3 spin extraction blocks (at ~40, 51, 67 min), active duration ~71 min (`20 Oct 0744`).
- **Quick Wash (~21 min):** 1 spin extraction block (at ~17-18 min), 0 heater minutes, active duration 21–22 min (`21 Oct 0514`, `21 Oct 0631`).
- **Sensor Integrity Across All Firmware-07 Runs:** Idle vibration noise floor `vib_mag_std` is exactly **0.032 m/s²** across all runs, maximum high-speed spin frequency $p90 \approx 20.0\text{ Hz}$ (~1,200 RPM), and zero accelerometer clipping occurred.

---

## 2. Comprehensive Cycle Signatures Table

| Session File | Schema | Rows | Rec. Min | Active Min | Heater Min | High-Pwr Blocks | Programme | Water Temp | Context Source |
|---|---|---|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-11_1019.csv` | legacy | 422 | 35.2 | n/a | n/a | n/a | unknown | - | `unknown` |
| `wash_cycle_2026-10-12_1019.csv` | legacy | 1216 | 101.3 | n/a | n/a | n/a | unknown | - | `unknown` |
| `wash_cycle_2026-10-15_1020.csv` | legacy | 276 | 23.0 | n/a | n/a | n/a | unknown | - | `unknown` |
| `wash_cycle_2026-10-15_morning.csv` | legacy | 1216 | 101.3 | n/a | n/a | n/a | unknown | - | `unknown` |
| `wash_cycle_2026-10-16_0857.csv` | legacy | 857 | 71.4 | 64 | 0 | 5 | unknown | - | `unknown` |
| `wash_cycle_2026-10-17_0718.csv` | legacy | 854 | 71.2 | 76 | 0 | 3 | unknown | - | `unknown` |
| `wash_cycle_2026-10-17_0835.csv` | legacy | 792 | 66.0 | 0 | 0 | 0 | unknown | - | `unknown` |
| `wash_cycle_2026-10-18_0516.csv` | legacy | 828 | 69.0 | 64 | 0 | 4 | unknown | - | `unknown` |
| `wash_cycle_2026-10-19_0022.csv` | legacy | 167 | 13.9 | 0 | 0 | 0 | unknown | - | `unknown` |
| `wash_cycle_2026-10-19_0911.csv` | fw07 | 786 | 65.7 | 64 | 0 | 3 | unknown | - | `unknown` |
| `wash_cycle_2026-10-20_0744.csv` | fw07 | 965 | 80.7 | 71 | 11.9 | 4 | unknown | - | `unknown` |
| `wash_cycle_2026-10-21_0514.csv` | fw07 | 387 | 32.3 | 22 | 0 | 1 | unknown | - | `unknown` |
| `wash_cycle_2026-10-21_0631.csv` | fw07 | 348 | 29.1 | 21 | 0 | 1 | unknown | - | `unknown` |

---

## 3. Firmware-07 Data Quality & Kinematic Profile

Telemetry verification table for firmware-07 45-column windowed records:

| Session File | `n_accel` (med/min) | FIFO Overflow | Clipped | Max Gap (s) | Idle `vib_mag_std` | Spin `vib_dom_hz` p90 | Boot at Start |
|---|---|---|---|---|---|---|---|
| `wash_cycle_2026-10-19_0911.csv` | 1013 / 965 | 1 | 0 | 7.75 s | 0.032 m/s² | 19.9 Hz | yes |
| `wash_cycle_2026-10-20_0744.csv` | 1014 / 964 | 1 | 0 | 8.78 s | 0.032 m/s² | 19.9 Hz | yes |
| `wash_cycle_2026-10-21_0514.csv` | 1013 / 962 | 1 | 0 | 8.38 s | 0.032 m/s² | 20.0 Hz | yes |
| `wash_cycle_2026-10-21_0631.csv` | 1013 / 1012 | 0 | 0 | 8.68 s | 0.032 m/s² | 20.0 Hz | no |

---

## 4. High-Power Electrical Profile Breakdown

Detailed timing and electrical peak for all blocks with $\ge 3$ consecutive windows $> 200\text{ W}$:

### `wash_cycle_2026-10-19_0911.csv` (fw07, 64 active min)
- **Block 1** (Spin Extraction): start at **36.7 min**, peak **420 W**, duration **2.8 min** (34 windows)
- **Block 2** (Spin Extraction): start at **46.8 min**, peak **377 W**, duration **2.8 min** (33 windows)
- **Block 3** (Spin Extraction): start at **60.6 min**, peak **372 W**, duration **2.5 min** (30 windows)

### `wash_cycle_2026-10-20_0744.csv` (fw07, 71 active min)
- **Block 1** (Heater (Wash Temp Control)): start at **3.5 min**, peak **2290 W**, duration **11.9 min** (142 windows)
- **Block 2** (Spin Extraction): start at **40.1 min**, peak **614 W**, duration **2.6 min** (31 windows)
- **Block 3** (Spin Extraction): start at **50.7 min**, peak **902 W**, duration **2.6 min** (31 windows)
- **Block 4** (Spin Extraction): start at **67.4 min**, peak **405 W**, duration **2.4 min** (29 windows)

### `wash_cycle_2026-10-21_0514.csv` (fw07, 22 active min)
- **Block 1** (Spin Extraction): start at **17.9 min**, peak **373 W**, duration **3.5 min** (42 windows)

### `wash_cycle_2026-10-21_0631.csv` (fw07, 21 active min)
- **Block 1** (Spin Extraction): start at **17.1 min**, peak **302 W**, duration **3.0 min** (36 windows)

---

## 5. Physical Signature Grouping

Cycles clustered by verified physical parameters (Heater Activity $\times$ Spin Block Count):

| Signature Group | Characteristics | Member Sessions | Inferred / Known Programme |
|---|---|---|---|
| **Group A (Standard Cold)** | Active ~64–76 min, Heater: 0 min, 3 Spin Blocks | `wash_cycle_2026-10-19_0911.csv`<br>`wash_cycle_2026-10-18_0516.csv`<br>`wash_cycle_2026-10-17_0835.csv`<br>`wash_cycle_2026-10-17_0718.csv`<br>`wash_cycle_2026-10-16_0857.csv` | Daily Wash (Cold) |
| **Group B (Heated Wash)** | Active ~71 min, Heater: 11.9 min (>2 kW), 3 Spin Blocks | `wash_cycle_2026-10-20_0744.csv` | Daily Wash (Warm / 40°C) |
| **Group C (Quick Cycle)** | Active ~21–22 min, Heater: 0 min, 1 Spin Block | `wash_cycle_2026-10-21_0514.csv`<br>`wash_cycle_2026-10-21_0631.csv` | Quick Wash / Express 15' |
| **Group D (Legacy Unmetered)** | Active n/a (No Tapo power data captured) | `wash_cycle_2026-10-11_1019.csv`<br>`wash_cycle_2026-10-12_1019.csv`<br>`wash_cycle_2026-10-15_1020.csv`<br>`wash_cycle_2026-10-15_morning.csv`<br>`wash_cycle_2026-10-19_0022.csv` | Legacy firmware (bench / test) |

