"""
Step 2: Clone Flipper Zero IR DB and parse .ir files into standard CSV schema.

Flipper .ir file format:
  Filetype: IR signals file
  Version: 1
  #
  name: Power
  type: parsed
  protocol: NEC
  address: 08 00 00 00
  command: 02 00 00 00
  #
  name: Vol_up
  type: raw
  frequency: 38000
  duty_cycle: 0.330000
  data: 8966 4432 628 ...

Output: data/processed/flipper.csv (appended to master later)
"""

import os
import csv
import glob
import git
from tqdm import tqdm

RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw/flipper-irdb")
OUT_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/flipper.csv")
FLIPPER_REPO = "https://github.com/logickworkshop/Flipper-IRDB.git"

SCHEMA = ["source", "brand", "device_type", "model", "command", "protocol", "frequency_khz", "raw_data", "format"]

DEVICE_TYPE_MAP = {
    "TV": "TV",
    "TVs": "TV",
    "AC": "AC",
    "ACs": "AC",
    "Air_Conditioners": "AC",
    "Fan": "FAN",
    "Fans": "FAN",
    "STB": "STB",
    "Projectors": "PROJECTOR",
    "Audio": "AUDIO",
    "Monitors": "MONITOR",
}


def normalize_device_type(raw: str) -> str:
    for key, val in DEVICE_TYPE_MAP.items():
        if key.lower() == raw.lower():
            return val
    return raw.upper()


def clone_or_update():
    if os.path.exists(RAW_DIR):
        print(f"[Flipper] Repo exists at {RAW_DIR}, pulling latest...")
        repo = git.Repo(RAW_DIR)
        repo.remotes.origin.pull()
    else:
        print(f"[Flipper] Cloning from {FLIPPER_REPO} ...")
        git.Repo.clone_from(FLIPPER_REPO, RAW_DIR, depth=1)
    print("[Flipper] Done.")


def parse_ir_file(filepath: str, brand: str, device_type: str) -> list[dict]:
    """Parse a Flipper .ir file into a list of signal dicts."""
    rows = []
    model = os.path.splitext(os.path.basename(filepath))[0]

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Split into signal blocks by '#'
        blocks = content.split("#")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.strip().splitlines()
            signal = {}
            for line in lines:
                if ":" in line:
                    key, _, value = line.partition(":")
                    signal[key.strip().lower()] = value.strip()

            if "name" not in signal:
                continue

            sig_type = signal.get("type", "raw")
            command = signal.get("name", "unknown")

            if sig_type == "parsed":
                protocol = signal.get("protocol", "UNKNOWN")
                address = signal.get("address", "")
                cmd_val = signal.get("command", "")
                raw_data = f"address={address} command={cmd_val}"
                fmt = "flipper_parsed"
                frequency_khz = "38"
            else:
                protocol = "RAW"
                frequency = signal.get("frequency", "38000")
                frequency_khz = str(int(float(frequency) / 1000))
                raw_data = signal.get("data", "")
                fmt = "flipper_raw"

            if not raw_data:
                continue

            rows.append({
                "source": "FlipperZero",
                "brand": brand,
                "device_type": normalize_device_type(device_type),
                "model": model,
                "command": command,
                "protocol": protocol,
                "frequency_khz": frequency_khz,
                "raw_data": raw_data,
                "format": fmt,
            })

    except Exception as e:
        print(f"  [WARN] Failed to parse {filepath}: {e}")

    return rows


def run():
    clone_or_update()

    ir_files = glob.glob(os.path.join(RAW_DIR, "**", "*.ir"), recursive=True)
    print(f"[Flipper] Found {len(ir_files)} .ir files. Parsing...")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    total_rows = 0
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
        writer.writeheader()

        for filepath in tqdm(ir_files, desc="Flipper .ir files"):
            # Infer brand and device_type from path
            parts = filepath.replace("\\", "/").split("/")
            raw_idx = None
            for i, p in enumerate(parts):
                if p == "flipper-irdb":
                    raw_idx = i
                    break

            if raw_idx is not None and len(parts) > raw_idx + 2:
                device_type = parts[raw_idx + 1]
                brand = parts[raw_idx + 2]
            else:
                device_type = "Unknown"
                brand = "Unknown"

            rows = parse_ir_file(filepath, brand, device_type)
            writer.writerows(rows)
            total_rows += len(rows)

    print(f"[Flipper] Done. {total_rows} rows written to {OUT_FILE}")


if __name__ == "__main__":
    run()
