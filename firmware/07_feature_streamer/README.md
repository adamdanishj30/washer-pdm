# Firmware 07: windowed feature streamer

Replaces 06 as the rig firmware. Same wiring (see `CLAUDE.md`), same Tapo P110 local client, same Firebase project.

## Why

Firmware 05/06 uploaded **one instantaneous accelerometer sample and one 8 ms audio RMS every 5 s**. More than 99% of what the sensors measured never left the ESP32. Bearing-type evidence (impulsiveness, high-band energy) and drum-speed vibration (1× order) could not be computed from that data.

Firmware 07 processes **every** sample on the ESP32 and uploads one compact feature vector per 5.024 s window:

| Source | Sampling | Per-window features |
|---|---|---|
| INMP441 audio | 16 kHz, continuous, 512-sample blocks | RMS, peak, crest factor, kurtosis, 2 kHz high-pass RMS + kurtosis, block-RMS max and p90, spectral centroid, RMS in 6 bands (0–250 Hz … 4–8 kHz) |
| MPU-6050 | **200 Hz** hardware FIFO with **44 Hz anti-alias filter** (DLPF_CFG = 3) | per-axis mean, std and peak-to-peak; std of \|a\|; dominant frequency 0.5–45 Hz (≈ drum speed) and its RMS; RMS in 0.5–5, 5–15, 15–30, 30–60 Hz |
| Tapo P110 | 1 Hz (local KLAP) | mean, min, max, std of power |

The DSP lives in `pdm_dsp.h` (pure C++). `ml/tests/test_dsp_parity.py` compiles it on a PC and checks it against `ml/dsp_features.py`: worst relative error is 1e-7.

## Firebase quota (Spark plan: 10 GB/month download, 1 GB stored, 100 connections)

On Spark, Firebase doesn't bill you when a cap is hit. The database is **restricted until the quota resets or you upgrade**, which would silently stop data collection mid-study. Firebase bills downloaded data **including connection and TLS overhead**, and every REST write echoes the written data back unless the request uses `print=silent`.

Old setup, if left powered 24/7 (estimates; a new TLS handshake is about 5 KB):

| Source | Requests/day | Rough download |
|---|---|---|
| 06 `/live` PUT every 2 s, new TLS each time, echo | 43,200 | ~240 MB/day |
| 06 batch PUT every 5 s | 17,280 | ~95 MB/day |
| daemon polling `/live` every 5 s (urllib, new TLS each time) | 17,280 | ~95 MB/day |
| `tapo_firebase_streamer.py` (if running): 2 writes/s | 172,800 | ~950 MB/day |
| `cloud_downloader.py` | every run downloaded **all** sessions | grows with history |

That is about **10 GB/month from the rig + daemon alone**, which is at the Spark cap, and well over it if the Tapo PC bridge ran too.

Firmware 07 and the updated PC scripts:

| Change | Effect |
|---|---|
| `?print=silent` on every write (firmware and `firebase_rest.py`) | 204 responses, nothing echoed |
| One persistent TLS connection (`HTTPClient::setReuse`, `http.client` keep-alive) | handshakes only on reconnect |
| 6 windows per PATCH (every 30 s) | 6× fewer requests than 06 |
| Session gating: upload only while running (power > 8 W, or vibration if Tapo is down); 60 s heartbeat when idle | idle cost ~0.5–8 MB/day (upper value if the server closes idle connections) |
| Daemon: polls every 30 s during a wash, every 2 min idle; downloads each finished session **once**; never re-downloads archived ones | ~2–20 MB/day |
| SmartThings phases saved locally, so archiving does not re-download them | |
| Raw audio clips only over LAN (`/clip.wav`, `collect_audio_clips.py`) | 0 Firebase |
| Optional `--prune-archived` | deletes a session from Firebase after its CSV is verified on disk |

Expected total: **roughly 0.1–1 GB/month** of download, and about 0.6 MB of storage per 90-minute cycle (around 1,600 cycles before the 1 GB storage cap). Check the real figure in Firebase console → Realtime Database → Usage after a week. `data/.firebase_usage.json` tallies what the PC scripts received (body bytes only).

## Firebase layout written by 07

```
/live                          small status object, PUT every 10 s (washing) / 60 s (idle)
/session_meta/<sid>            {start, start_epoch_ms, fw, schema: 3, tapo, ... end, n_windows, end_reason, tags/...}
/sessions/<sid>/w000123        one window (compact keys; mapping in firmware/session_export.py V3_KEY_MAP)
/session_phases/<sid>/<ts>     SmartThings checkpoints (written by the PC daemon)
```

Keys `t, rms, ax, ay, az, pwr` match 05/06, so older tools still read the basics. Window keys are prefixed with `w` because Firebase can turn numeric-looking keys into arrays.

## Session gating

* A session opens after 2 consecutive "active" windows (power > 8 W; if Tapo is unavailable, \|a\| std > 0.08 m/s²). The previous 30 s of idle windows are prepended.
* It closes after 120 consecutive idle windows (10 min, which covers soak and fill pauses). The `end` marker is uploaded only after every window of the session.
* Session id: `wash_YYYY-MM-DD_HHMMSS` (NTP, UTC+8).
* `/tag?name=unbalanced_load` attaches a label to the running session. Use it for safe, reversible perturbation experiments (Layer B validation).

## Local endpoints (LAN only)

| URL | What |
|---|---|
| `http://washer-pdm.local/` | status page |
| `/window.json` | latest window, same format as Firebase |
| `/data` | `{ax, ay, az, rms, cnt}`, compatible with the 05/06 dashboards |
| `/clip.wav?sec=2` | 2 s of raw 16 kHz audio (64 kB of heap; returns 507 if the heap is short) |
| `/accel.csv` | last 2.56 s of raw 200 Hz acceleration |
| `/tag?name=...` | label the running session |

## Build and flash

1. Add to the project `.env`: `WIFI_SSID, WIFI_PASS, FIREBASE_HOST, FIREBASE_AUTH, TAPO_IP, TAPO_DEVICE_USER, TAPO_DEVICE_PASS`, and preferably `OTA_PASS`.
2. `py -3.12 firmware/07_feature_streamer/flash_firmware.py --compile --port COM3`
3. Run the PC side: `py firmware/auto_drive_sync_daemon.py`, plus optionally `py firmware/collect_audio_clips.py`.

### Hardware Verification & Runtime Status (Verified 2026-10-19)

- [x] **Compiled with `esp32:esp32@3.3.12`**: Initial DRAM overflow (`dram0_0_seg overflowed by 11632 bytes`) solved by reducing `OUTBOX_CAPACITY` from 120 to 48 (~4 min offline buffer in RAM), batch JSON buffer from 8192 to 4096 bytes, and converting diagnostic CSV snapshot buffer to dynamic allocation.
- [x] **Flashed & Running**: Flashed over USB COM6 (`ESP32-D0WD-V3`, MAC: `30:76:f5:e5:4d:70`). Running stably on external power.
- [x] **Sensors & Network**: I2C MPU-6050 (200 Hz FIFO, 44 Hz DLPF) and I2S INMP441 (16 kHz DMA) active. NTP time synchronized, Tapo P110 paired via local KLAP, Wi-Fi connected (`rssi: -67 dBm`).
- [x] **Free Heap Stability**: Free heap maintains steady ~52 kB to 99 kB. Zero queue drops (`drops: 0`), zero outbox drops (`outbox: 0`).
- [x] **Dynamic Vibration Verification**: Physical motion and tapping tests confirmed `vib_std` surges from 0.033 m/s² (baseline resting noise) to 1.726 m/s² (dynamic vibration), while static mean acceleration `ax, ay, az` remains at gravitational tilt (~9.52 m/s²) due to AC cancellation over 1,005 samples.
- [x] **Firebase Schema 3 Telemetry**: Streams live heartbeat to `/live.json` (60s idle, 10s active) and batches 5-second feature windows (6 windows = 30s) to `/sessions/<id>/`.
- [x] **PC Downloader & Daemon**: Tested and confirmed downloading finished sessions to Drive (`wash_cycle_2026-10-19_0107.csv`, 127 windows).

## Security notes

* No credentials in source any more. `secrets.h` is generated from `.env`, and the build fails if it is missing.
* **Rotate the Firebase database secret and the Wi-Fi password.** Both were hard-coded in 04/05/06 and the Python scripts. They remain in Google Drive version history and in the old compiled `.bin` files under each `build/` folder.
* `setInsecure()` skips certificate validation, as in 06. It is acceptable on a home network, but pin the Google root CA before any township deployment.
* The legacy database secret grants full read and write access. For deployment, move to Firebase Auth with security rules that let the device write only `/live`, `/sessions/<own>` and `/session_meta/<own>`.
