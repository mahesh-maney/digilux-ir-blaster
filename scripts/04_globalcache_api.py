"""
Step 4: Query GlobalCaché Control Tower API for IR codes not covered by Steps 1-3.

GlobalCaché Control Tower API:
  - Base: https://irdb.globalcache.com/api
  - Free tier: 10,000 requests/month
  - Returns Pronto Hex format

Usage:
  python 04_globalcache_api.py --brand "Samsung" --device-type TV
  python 04_globalcache_api.py --fill-gaps  (queries for brands missing in master.csv)

Get your free API key at: https://irdb.globalcache.com/home/developers

Output: data/processed/globalcache.csv
"""

import os
import csv
import argparse
import requests
import time

API_BASE = "https://irdb.globalcache.com/api"
OUT_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/globalcache.csv")
MASTER_CSV = os.path.join(os.path.dirname(__file__), "../data/processed/master.csv")

SCHEMA = ["source", "brand", "device_type", "model", "command", "protocol", "frequency_khz", "raw_data", "format"]

DEVICE_TYPE_IDS = {
    "TV": 1,
    "AC": 4,
    "STB": 7,
    "FAN": 14,
    "DVD": 2,
    "AUDIO": 5,
    "PROJECTOR": 8,
}


def get_manufacturers(api_key: str, device_type_id: int) -> list[dict]:
    url = f"{API_BASE}/manufacturer/{device_type_id}"
    resp = requests.get(url, headers={"Gc-UniversalRemote-Token": api_key}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_models(api_key: str, manufacturer_id: int, device_type_id: int) -> list[dict]:
    url = f"{API_BASE}/model/{manufacturer_id}/{device_type_id}"
    resp = requests.get(url, headers={"Gc-UniversalRemote-Token": api_key}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_ir_codes(api_key: str, manufacturer_id: int, device_type_id: int, model_id: int) -> list[dict]:
    url = f"{API_BASE}/ircode/{manufacturer_id}/{device_type_id}/{model_id}"
    resp = requests.get(url, headers={"Gc-UniversalRemote-Token": api_key}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def pronto_to_frequency_khz(pronto_hex: str) -> str:
    """Extract carrier frequency from Pronto Hex string."""
    try:
        parts = pronto_hex.strip().split()
        if len(parts) >= 2:
            freq_word = int(parts[1], 16)
            if freq_word > 0:
                freq_hz = 1000000 / (freq_word * 0.241246)
                return str(round(freq_hz / 1000, 1))
    except Exception:
        pass
    return "38"


def fetch_brand(api_key: str, brand: str, device_type: str, writer: csv.DictWriter) -> int:
    device_type_id = DEVICE_TYPE_IDS.get(device_type.upper())
    if not device_type_id:
        print(f"  [WARN] Unknown device type: {device_type}")
        return 0

    print(f"[GlobalCaché] Fetching {brand} {device_type}...")
    manufacturers = get_manufacturers(api_key, device_type_id)

    # Find matching manufacturer
    matched = [m for m in manufacturers if brand.lower() in m.get("manufacturer", "").lower()]
    if not matched:
        print(f"  [WARN] Brand '{brand}' not found in GlobalCaché for device type {device_type}")
        return 0

    count = 0
    for mfr in matched:
        mfr_id = mfr["manufacturerId"]
        mfr_name = mfr["manufacturer"]

        try:
            models = get_models(api_key, mfr_id, device_type_id)
        except Exception as e:
            print(f"  [WARN] Could not fetch models for {mfr_name}: {e}")
            continue

        for model in models:
            model_id = model["modelId"]
            model_name = model.get("model", "Unknown")

            try:
                codes = get_ir_codes(api_key, mfr_id, device_type_id, model_id)
                time.sleep(0.1)  # Rate limit: be polite to the API
            except Exception as e:
                print(f"  [WARN] Could not fetch codes for {mfr_name}/{model_name}: {e}")
                continue

            for code in codes:
                pronto = code.get("irCode", "")
                command = code.get("keyName", "unknown")
                if not pronto:
                    continue

                writer.writerow({
                    "source": "GlobalCaché",
                    "brand": mfr_name,
                    "device_type": device_type.upper(),
                    "model": model_name,
                    "command": command,
                    "protocol": "PRONTO",
                    "frequency_khz": pronto_to_frequency_khz(pronto),
                    "raw_data": pronto,
                    "format": "pronto_hex",
                })
                count += 1

    return count


def get_missing_brands() -> list[tuple[str, str]]:
    """Find brand+device_type combos missing from master.csv."""
    target_brands = [
        ("Samsung", "TV"), ("LG", "TV"), ("Sony", "TV"), ("Panasonic", "TV"),
        ("Samsung", "AC"), ("LG", "AC"), ("Daikin", "AC"), ("Voltas", "AC"),
        ("Blue Star", "AC"), ("Hitachi", "AC"), ("Whirlpool", "AC"),
        ("Tata Sky", "STB"), ("Airtel", "STB"), ("DishTV", "STB"),
        ("Usha", "FAN"), ("Havells", "FAN"), ("Orient", "FAN"),
    ]

    if not os.path.exists(MASTER_CSV):
        return target_brands

    existing = set()
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add((row["brand"].lower(), row["device_type"].upper()))

    missing = [(b, d) for b, d in target_brands if (b.lower(), d.upper()) not in existing]
    return missing


def run(api_key: str, brand: str = None, device_type: str = None, fill_gaps: bool = False):
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
        writer.writeheader()

        total = 0
        if fill_gaps:
            missing = get_missing_brands()
            print(f"[GlobalCaché] {len(missing)} brand/device combos to fill...")
            for b, d in missing:
                total += fetch_brand(api_key, b, d, writer)
        elif brand and device_type:
            total += fetch_brand(api_key, brand, device_type, writer)
        else:
            print("Provide --brand + --device-type or use --fill-gaps")
            return

    print(f"[GlobalCaché] Done. {total} rows written to {OUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch IR codes from GlobalCaché Control Tower")
    parser.add_argument("--api-key", required=True, help="GlobalCaché API key")
    parser.add_argument("--brand", help="Brand name (e.g. Samsung)")
    parser.add_argument("--device-type", help="Device type: TV, AC, STB, FAN")
    parser.add_argument("--fill-gaps", action="store_true", help="Auto-fill missing brands from master.csv")
    args = parser.parse_args()

    run(args.api_key, args.brand, args.device_type, args.fill_gaps)
