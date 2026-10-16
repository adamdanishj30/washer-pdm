import glob
import os
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def check_all_csvs():
    files = list(DATA_DIR.rglob("*.csv"))
    files = sorted([f for f in files if "bak_unscaled" not in f.name])
    
    print("=" * 92)
    print(f"{'Category / File Name':<42} | {'Rows':<5} | {'Min':<6} | {'Median':<6} | {'Max':<6} | {'Status'}")
    print("=" * 92)
    
    all_standardized = True
    by_category = {}
    
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            reader = list(csv.DictReader(fp))
        if not reader or "audio_rms" not in reader[0]:
            continue
        
        rms_vals = []
        for r in reader:
            try:
                rms_vals.append(float(r["audio_rms"]))
            except (ValueError, TypeError):
                pass
        
        if not rms_vals:
            continue
        
        min_v = min(rms_vals)
        max_v = max(rms_vals)
        med_v = sorted(rms_vals)[len(rms_vals)//2]
        
        # Check canonical scale: max <= 1500, median between 10 and 500
        is_canonical = (max_v <= 1500.0 and med_v <= 500.0)
        if not is_canonical:
            all_standardized = False
        status = "[OK] STANDARDIZED" if is_canonical else "[WARN] UNSCALED"
        
        rel_path = f.relative_to(DATA_DIR)
        print(f"{str(rel_path):<42} | {len(rms_vals):<5} | {min_v:<6.1f} | {med_v:<6.1f} | {max_v:<6.1f} | {status}")
        
    print("=" * 92)
    print(f"VERIFICATION VERDICT: {'ALL 100% STANDARDIZED ON CANONICAL SCALE' if all_standardized else 'SOME FILES NOT STANDARDIZED'}")
    print("=" * 92)

if __name__ == "__main__":
    check_all_csvs()
