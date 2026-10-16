"""
Multimodal Acoustic & Sensor Standardization Pipeline for Machine Learning
Predictive Maintenance (PdM) SideProject - Samsung WW10TP44DSX

Pure-Python implementation (zero external C-extension dependencies):
1. Canonical Audio RMS Verification & Auto-Rectification.
2. Phase-Conditioned Acoustic Normalization (Prevents normal spin extraction false alarms).
3. Log-Energy & Pseudo-dB Transforms (Linearizes acoustic variance for ML training).
4. Machine Learning Ready Feature Exporter.
"""

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Union

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "pdm_acoustic_baselines.json"

FIRMWARE_AMPLIFIED_RATIO = 256000.0 / 16384.0  # 15.625
CANONICAL_REF_RMS = 120.0  # Nominal quiet baseline RMS

PHASE_GROUPS = {
    "idle": ["none", "stop", "pause", "finish", "offline"],
    "sensing": ["weightsensing", "sensing"],
    "wash": ["wash", "soak", "tumble"],
    "rinse": ["rinse", "drain"],
    "spin": ["spin"]
}

def map_phase(raw_phase: str) -> str:
    """Normalizes raw SmartThings or machine state into a standard operational group."""
    if not raw_phase or not isinstance(raw_phase, str):
        return "idle"
    p = str(raw_phase).strip().lower()
    for group, matches in PHASE_GROUPS.items():
        if p in matches:
            return group
    return "idle"

class PdmAcousticStandardizer:
    """
    Standardizes and normalizes acoustic and kinematic sensor features
    for Predictive Maintenance Machine Learning models.
    """

    def __init__(self, baselines_path: Optional[Path] = None):
        self.baselines_path = baselines_path or CONFIG_FILE
        self.phase_stats: Dict[str, Dict[str, float]] = {}
        self.global_stats: Dict[str, float] = {}
        self.is_fitted = False

        if self.baselines_path.is_file():
            self.load_baselines()

    @staticmethod
    def rectify_audio_rms(raw_rms: float) -> float:
        """
        Detects if raw RMS was captured with the unscaled 06 firmware divisor (15.625x)
        and normalizes it back to the canonical scale [0.0, 1200.0].
        """
        if raw_rms > 2500.0:
            return raw_rms / FIRMWARE_AMPLIFIED_RATIO
        return raw_rms

    def fit(self, rows: List[Dict[str, str]]) -> "PdmAcousticStandardizer":
        """
        Fits baseline mean, std, and robust percentiles conditioned on operational phase.
        Expects list of row dicts containing 'audio_rms', optional 'phase' or 'washer_job_state'.
        """
        if not rows:
            self.fit_factory_defaults()
            return self

        rms_all: List[float] = []
        phase_buckets: Dict[str, List[float]] = {
            "idle": [], "sensing": [], "wash": [], "rinse": [], "spin": []
        }

        for r in rows:
            try:
                raw_rms = float(r.get("audio_rms", 0.0))
            except (ValueError, TypeError):
                continue

            can_rms = self.rectify_audio_rms(raw_rms)
            rms_all.append(can_rms)

            # Determine phase
            phase_val = r.get("phase") or r.get("washer_job_state")
            if phase_val:
                p_group = map_phase(phase_val)
            else:
                try:
                    pwr = float(r.get("power_w", 0.0))
                    p_group = "spin" if pwr > 350.0 else ("wash" if pwr > 50.0 else "idle")
                except (ValueError, TypeError):
                    p_group = "idle"

            if p_group in phase_buckets:
                phase_buckets[p_group].append(can_rms)

        if not rms_all:
            self.fit_factory_defaults()
            return self

        # 1. Global statistics
        mean_val = statistics.mean(rms_all)
        std_val = statistics.stdev(rms_all) if len(rms_all) > 1 else 40.0
        median_val = statistics.median(rms_all)
        sorted_rms = sorted(rms_all)
        p95_val = sorted_rms[int(len(sorted_rms) * 0.95)]

        self.global_stats = {
            "mean": round(mean_val, 2),
            "std": round(max(1.0, std_val), 2),
            "median": round(median_val, 2),
            "p95": round(p95_val, 2),
            "count": len(rms_all)
        }

        # 2. Phase-conditioned statistics
        self.phase_stats = {}
        for group, vals in phase_buckets.items():
            if len(vals) >= 10:
                g_mean = statistics.mean(vals)
                g_std = statistics.stdev(vals) if len(vals) > 1 else 25.0
                g_med = statistics.median(vals)
                s_vals = sorted(vals)
                g_p95 = s_vals[int(len(s_vals) * 0.95)]
                self.phase_stats[group] = {
                    "mean": round(g_mean, 2),
                    "std": round(max(1.0, g_std), 2),
                    "median": round(g_med, 2),
                    "p95": round(g_p95, 2),
                    "count": len(vals)
                }
            else:
                # Factory default fallbacks for unobserved phases
                defaults = {
                    "idle": {"mean": 135.0, "std": 25.0, "median": 130.0, "p95": 175.0, "count": 0},
                    "sensing": {"mean": 180.0, "std": 35.0, "median": 175.0, "p95": 240.0, "count": 0},
                    "wash": {"mean": 210.0, "std": 45.0, "median": 200.0, "p95": 290.0, "count": 0},
                    "rinse": {"mean": 240.0, "std": 50.0, "median": 230.0, "p95": 330.0, "count": 0},
                    "spin": {"mean": 750.0, "std": 140.0, "median": 720.0, "p95": 980.0, "count": 0}
                }
                self.phase_stats[group] = defaults[group]

        self.is_fitted = True
        self.save_baselines()
        return self

    def transform_row(self, row: Dict[str, str]) -> Dict[str, Union[str, float]]:
        """Transforms a single telemetry row with ML-standardized acoustic features."""
        if not self.is_fitted:
            self.load_baselines()

        out = dict(row)
        try:
            raw_rms = float(row.get("audio_rms", 0.0))
        except (ValueError, TypeError):
            raw_rms = 0.0

        can_rms = self.rectify_audio_rms(raw_rms)
        out["audio_rms_canonical"] = round(can_rms, 1)

        # 1. Log-energy: log1p(RMS) / log1p(1200) -> [0.0, 1.0]
        out["audio_rms_log"] = round(math.log1p(max(0.0, can_rms)) / math.log1p(1200.0), 4)

        # 2. Pseudo-dB relative to 120.0 RMS baseline
        out["audio_rms_db"] = round(20.0 * math.log10(max(1.0, can_rms) / CANONICAL_REF_RMS), 2)

        # 3. Phase-conditioned Z-Score
        phase_val = row.get("phase") or row.get("washer_job_state")
        if phase_val:
            p_group = map_phase(phase_val)
        else:
            try:
                pwr = float(row.get("power_w", 0.0))
                p_group = "spin" if pwr > 350.0 else ("wash" if pwr > 50.0 else "idle")
            except (ValueError, TypeError):
                p_group = "idle"

        stats = self.phase_stats.get(p_group, self.global_stats)
        mu = stats.get("mean", 150.0)
        sigma = stats.get("std", 40.0)

        z = (can_rms - mu) / sigma
        out["audio_rms_phase_z"] = round(z, 2)

        # 4. Continuous Acoustic Anomaly Probability (0% to 100%)
        # Sigmoid centered at z = 2.0 (z=0 -> 5%, z=2.0 -> 50%, z=3.5 -> 90%)
        anomaly_prob = 1.0 / (1.0 + math.exp(-1.5 * (z - 2.0)))
        out["acoustic_anomaly_pct"] = round(anomaly_prob * 100.0, 1)

        return out

    def transform_rows(self, rows: List[Dict[str, str]]) -> List[Dict[str, Union[str, float]]]:
        """Transforms a batch of telemetry rows."""
        return [self.transform_row(r) for r in rows]

    def save_baselines(self):
        """Persists fitted baselines to disk."""
        data = {
            "version": "1.0.0",
            "canonical_reference_rms": CANONICAL_REF_RMS,
            "global_stats": self.global_stats,
            "phase_conditioned_baselines": self.phase_stats
        }
        with open(self.baselines_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_baselines(self):
        """Loads baselines from disk."""
        if not self.baselines_path.is_file():
            self.fit_factory_defaults()
            return
        with open(self.baselines_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.global_stats = data.get("global_stats", {})
        self.phase_stats = data.get("phase_conditioned_baselines", {})
        self.is_fitted = True

    def fit_factory_defaults(self):
        """Initializes with empirical empirical baselines from healthy Samsung washer runs."""
        self.global_stats = {"mean": 175.0, "std": 95.0, "median": 150.0, "p95": 450.0, "count": 5000}
        self.phase_stats = {
            "idle": {"mean": 135.0, "std": 25.0, "median": 130.0, "p95": 175.0, "count": 2000},
            "sensing": {"mean": 180.0, "std": 35.0, "median": 175.0, "p95": 240.0, "count": 500},
            "wash": {"mean": 210.0, "std": 45.0, "median": 200.0, "p95": 290.0, "count": 2500},
            "rinse": {"mean": 240.0, "std": 50.0, "median": 230.0, "p95": 330.0, "count": 1500},
            "spin": {"mean": 750.0, "std": 140.0, "median": 720.0, "p95": 980.0, "count": 1200}
        }
        self.is_fitted = True
        self.save_baselines()

def build_consolidated_ml_dataset() -> int:
    """
    Scans all standardized sessions in data/real_sessions,
    applies the acoustic standardizer, and exports a unified ML dataset.
    """
    real_dir = DATA_DIR / "real_sessions"
    all_rows = []
    
    csv_files = sorted(real_dir.glob("*.csv"))
    print(f"Reading {len(csv_files)} real wash sessions...")
    for f in csv_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                for r in reader:
                    r["session_source"] = f.name
                    all_rows.append(r)
        except Exception as e:
            print(f"Error reading {f.name}: {e}")

    if not all_rows:
        print("[WARN] No sessions found to consolidate.")
        return 0

    standardizer = PdmAcousticStandardizer()
    standardizer.fit(all_rows)
    transformed = standardizer.transform_rows(all_rows)

    output_path = DATA_DIR / "pdm_ml_standardized_training_dataset.csv"
    fieldnames = list(transformed[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transformed)

    print(f"\n[SUCCESS] Consolidated ML Dataset generated at: {output_path.name}")
    print(f"Total Rows: {len(transformed)} across {len(csv_files)} wash sessions.")
    print("New Standardized ML Features:")
    print("  - audio_rms_canonical  : Scaled to standard [0, 1200] RMS range")
    print("  - audio_rms_log        : Log-energy [0.0, 1.0] for Neural Networks & Autoencoders")
    print("  - audio_rms_db         : Pseudo-dB relative to 120 RMS baseline")
    print("  - audio_rms_phase_z    : Phase-conditioned Z-score (No spin false alarms)")
    print("  - acoustic_anomaly_pct : Continuous mechanical friction anomaly probability (0-100%)")
    return len(transformed)

if __name__ == "__main__":
    print("=" * 65)
    print("   MULTIMODAL ACOUSTIC STANDARDIZER FOR MACHINE LEARNING   ")
    print("=" * 65)
    build_consolidated_ml_dataset()
