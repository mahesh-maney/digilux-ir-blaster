"""
Step 1: Clone IRDB and normalize to standard CSV schema.

Actual IRDB structure:
  codes/{manufacturer}/{device_type}/{device},{subdevice}.csv
  Each CSV has columns: functionname, protocol, device, subdevice, function

  The filename encodes device+subdevice (e.g., "238,135.csv")
  Each row is one command (e.g., POWER ON, VOL UP)

Output: data/processed/irdb.csv
"""

import os
import csv
import glob
import git
from tqdm import tqdm

RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw/irdb")
OUT_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/irdb.csv")
IRDB_REPO = "https://github.com/probonopd/irdb.git"

SCHEMA = ["source", "brand", "device_type", "model", "command", "protocol", "frequency_khz", "raw_data", "format"]

DEVICE_TYPE_MAP = {
    "tv": "TV", "television": "TV",
    "ac": "AC", "airconditioner": "AC", "air conditioner": "AC",
    "fan": "FAN",
    "stb": "STB", "settopbox": "STB", "set top box": "STB", "cable": "STB", "satellite": "STB",
    "dvd": "DVD", "blu-ray": "DVD", "bluray": "DVD",
    "projector": "PROJECTOR",
    "amplifier": "AV_RECEIVER", "receiver": "AV_RECEIVER", "audio": "AUDIO",
    "mp3": "AUDIO", "cd": "AUDIO",
}


def normalize_device_type(raw: str) -> str:
    key = raw.lower().strip()
    for k, v in DEVICE_TYPE_MAP.items():
        if k in key:
            return v
    return raw.upper()


def clone_or_update():
    if os.path.exists(os.path.join(RAW_DIR, ".git")):
        print(f"[IRDB] Repo exists at {RAW_DIR}, pulling latest...")
        repo = git.Repo(RAW_DIR)
        repo.remotes.origin.pull()
    else:
        print(f"[IRDB] Cloning from {IRDB_REPO} ...")
        git.Repo.clone_from(IRDB_REPO, RAW_DIR, depth=1)
    print("[IRDB] Done.")


def parse_irdb_csv(filepath: str, brand: str, device_type: str) -> list[dict]:
    rows = []
    # Filename is "{device},{subdevice}.csv" — use as model identifier
    model = os.path.splitext(os.path.basename(filepath))[0]

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                functionname = row.get("functionname", "").strip()
                protocol = row.get("protocol", "").strip()
                device = row.get("device", "").strip()
                subdevice = row.get("subdevice", "").strip()
                function = row.get("function", "").strip()

                if not functionname or not protocol or not function:
                    continue

                # raw_data encodes protocol parameters for runtime code generation
                raw_data = f"device={device} subdevice={subdevice} function={function}"

                rows.append({
                    "source": "IRDB",
                    "brand": brand,
                    "device_type": normalize_device_type(device_type),
                    "model": model,
                    "command": functionname,
                    "protocol": protocol,
                    "frequency_khz": "38",  # IRDB is protocol-based, 38kHz standard
                    "raw_data": raw_data,
                    "format": "irdb_protocol",
                })
    except Exception as e:
        print(f"  [WARN] Failed to parse {filepath}: {e}")
    return rows


def run():
    clone_or_update()

    csv_files = glob.glob(os.path.join(RAW_DIR, "codes", "*", "*", "*.csv"))
    print(f"[IRDB] Found {len(csv_files)} CSV files. Parsing...")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    total_rows = 0
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
        writer.writeheader()

        for filepath in tqdm(csv_files, desc="IRDB files"):
            # Path: codes/{manufacturer}/{device_type}/{device,subdevice}.csv
            parts = filepath.replace("\\", "/").split("/")
            try:
                codes_idx = parts.index("codes")
                brand = parts[codes_idx + 1]
                device_type = parts[codes_idx + 2]
            except (ValueError, IndexError):
                brand = "Unknown"
                device_type = "Unknown"

            rows = parse_irdb_csv(filepath, brand, device_type)
            writer.writerows(rows)
            total_rows += len(rows)

    print(f"[IRDB] Done. {total_rows} rows written to {OUT_FILE}")

    # Quick summary
    brands = set()
    device_types = set()
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            brands.add(row["brand"])
            device_types.add(row["device_type"])

    print(f"[IRDB] Brands: {len(brands)} | Device types: {sorted(device_types)}")


if __name__ == "__main__":
    run()
