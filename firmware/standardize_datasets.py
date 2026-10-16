"""
Dataset Acoustic Standardization Engine
Predictive Maintenance (PdM) SideProject - Samsung WW10TP44DSX

This script standardizes acoustic RMS telemetry across all recorded session CSVs,
prediction datasets, and live snapshots to ensure 100% consistent feature scaling
for Machine Learning model training and inference.
"""

import csv
import json
import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REAL_DIR = DATA_DIR / "real_sessions"
TEST_DIR = DATA_DIR / "testing_data"

FIRMWARE_RATIO = 256000.0 / 16384.0  # 15.625

def standardize_csv_file(filepath: Path) -> bool:
    """Standardizes audio_rms column in a CSV if it was recorded with amplified scale."""
    if not filepath.is_file():
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader or "audio_rms" not in reader[0]:
        return False

    rms_vals = [float(r["audio_rms"]) for r in reader if r.get("audio_rms")]
    if not rms_vals:
        return False

    # Detect if amplified scale is present (mean > 1200 or median > 1000)
    median_val = sorted(rms_vals)[len(rms_vals) // 2]
    if median_val < 1000.0 and sum(rms_vals) / len(rms_vals) < 1200.0:
        print(f"[SKIP] {filepath.name}: Already on canonical scale (median={median_val:.1f}).")
        return False

    # Backup original
    backup_path = filepath.with_suffix(".csv.bak_unscaled")
    if not backup_path.exists():
        shutil.copy2(filepath, backup_path)
        print(f"[BACKUP] Preserved {backup_path.name}")

    # Standardize
    fieldnames = list(reader[0].keys())
    for r in reader:
        try:
            val = float(r["audio_rms"])
            r["audio_rms"] = f"{val / FIRMWARE_RATIO:.1f}"
        except (ValueError, TypeError):
            pass

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    new_rms = [float(r["audio_rms"]) for r in reader]
    print(f"[OK] {filepath.name}: Standardized {len(reader)} rows. New median: {sorted(new_rms)[len(new_rms)//2]:.1f} RMS (was {median_val:.1f}).")
    return True

def standardize_prediction_dataset():
    """Standardizes data/pdm_multimodal_prediction_dataset.csv and recalculates health indices."""
    dataset_file = DATA_DIR / "pdm_multimodal_prediction_dataset.csv"
    if not dataset_file.is_file():
        return

    with open(dataset_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        return

    backup_path = dataset_file.with_suffix(".csv.bak_unscaled")
    if not backup_path.exists():
        shutil.copy2(dataset_file, backup_path)

    fieldnames = list(reader[0].keys())
    modified = False

    for r in reader:
        rms = float(r.get("audio_rms", 0.0))
        if rms > 1200.0:
            rms_standardized = round(rms / FIRMWARE_RATIO, 1)
            r["audio_rms"] = str(rms_standardized)
            modified = True

            # Recalculate health indices with standardized RMS
            pwr = float(r.get("power_w", 0.0))
            parasitic_pct = float(r.get("parasitic_drag_pct", 0.0))
            ay = float(r.get("accel_y", 1.4))
            vibe = float(r.get("vibe_magnitude", 9.81))
            rpm = float(r.get("target_rpm", 0))

            bearing_penalty = 0.0
            if rms_standardized > 220.0:
                bearing_penalty += (rms_standardized - 220.0) * 0.12
            if parasitic_pct > 15.0:
                bearing_penalty += parasitic_pct * 0.4
            bearing_health = round(max(15.0, min(100.0, 100.0 - bearing_penalty)), 1)

            damper_penalty = 0.0
            if abs(ay) > 18.0:
                damper_penalty += (abs(ay) - 18.0) * 2.5
            if vibe > 25.0 and rpm >= 1000:
                damper_penalty += (vibe - 25.0) * 1.5
            damper_health = round(max(20.0, min(100.0, 100.0 - damper_penalty)), 1)

            machine_health = round((bearing_health * 0.6) + (damper_health * 0.4), 1)

            r["bearing_health_index"] = str(bearing_health)
            r["damper_health_index"] = str(damper_health)
            r["machine_health_index"] = str(machine_health)

    if modified:
        with open(dataset_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)
        print(f"[OK] Standardized {dataset_file.name} (Restored bearing health & machine health).")

def standardize_snapshot():
    """Standardizes live_multimodal_pdm_snapshot.json."""
    snapshot_file = DATA_DIR / "live_multimodal_pdm_snapshot.json"
    if not snapshot_file.is_file():
        return

    with open(snapshot_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    esp = data.get("esp32", {})
    rms = esp.get("audio_rms", 0.0)
    if rms > 1200.0:
        norm_rms = round(rms / FIRMWARE_RATIO, 1)
        esp["audio_rms"] = norm_rms
        data["esp32"]["audio_rms"] = norm_rms

        # Recalculate PDM analytics
        pdm = data.get("pdm_prognostics", {})
        bearing_penalty = 0.0
        if norm_rms > 220.0:
            bearing_penalty += (norm_rms - 220.0) * 0.12
        parasitic_pct = pdm.get("parasitic_drag_pct", 0.0)
        if parasitic_pct > 15.0:
            bearing_penalty += parasitic_pct * 0.4
        bearing_health = round(max(15.0, min(100.0, 100.0 - bearing_penalty)), 1)
        damper_health = pdm.get("damper_health_index", 100.0)
        machine_health = round((bearing_health * 0.6) + (damper_health * 0.4), 1)

        pdm["bearing_health_index"] = bearing_health
        pdm["machine_health_index"] = machine_health

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[OK] Standardized {snapshot_file.name} (audio_rms: {rms} -> {norm_rms}, bearing_health: {bearing_health}%).")

def main():
    print("=" * 65)
    print("   STANDARDIZING MULTIMODAL PDM DATASETS TO CANONICAL SCALE   ")
    print("=" * 65)
    
    # 1. Standardize real sessions
    for p in REAL_DIR.glob("*.csv"):
        standardize_csv_file(p)

    # 2. Standardize testing sessions
    for p in TEST_DIR.glob("*.csv"):
        standardize_csv_file(p)

    # 3. Standardize ML prediction dataset
    standardize_prediction_dataset()

    # 4. Standardize live snapshot
    standardize_snapshot()

    print("=" * 65)
    print("   ALL DATASETS ARE NOW UNIFIED AND READY FOR ML TRAINING!     ")
    print("=" * 65)

if __name__ == "__main__":
    main()
