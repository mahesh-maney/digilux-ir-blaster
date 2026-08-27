"""
Step 3: Clone IRremoteESP8266 and extract AC protocol capabilities.

Constants in this library use: const uint8_t kXxx = value;
(not #define — different from what most assume)

Extracts min/max temp, modes, fan speeds per brand.
Output: data/processed/ac_protocols.csv
"""

import os
import re
import csv
import git
from tqdm import tqdm

RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw/IRremoteESP8266")
OUT_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/ac_protocols.csv")
REPO_URL = "https://github.com/crankyoldgit/IRremoteESP8266.git"

SCHEMA = [
    "source", "brand", "device_type", "protocol_class",
    "constant_name", "capability_type", "value", "notes"
]

# Map header filename → brand name (only files that actually exist)
AC_PROTOCOL_MAP = {
    "ir_Daikin.h":          "Daikin",
    "ir_Mitsubishi.h":      "Mitsubishi",
    "ir_MitsubishiHeavy.h": "Mitsubishi Heavy",
    "ir_Fujitsu.h":         "Fujitsu",
    "ir_LG.h":              "LG",
    "ir_Samsung.h":         "Samsung",
    "ir_Panasonic.h":       "Panasonic",
    "ir_Toshiba.h":         "Toshiba",
    "ir_Haier.h":           "Haier",
    "ir_Gree.h":            "Gree",
    "ir_Midea.h":           "Midea",
    "ir_Hitachi.h":         "Hitachi",
    "ir_Sharp.h":           "Sharp",
    "ir_Voltas.h":          "Voltas",
    "ir_Whirlpool.h":       "Whirlpool",
    "ir_Electra.h":         "Electra",
    "ir_Carrier.h":         "Carrier",
    "ir_Coolix.h":          "Coolix",
    "ir_Tcl.h":             "TCL",
    "ir_Argo.h":            "Argo",
    "ir_Delonghi.h":        "DeLonghi",
    "ir_Amcor.h":           "Amcor",
    "ir_Vestel.h":          "Vestel",
    "ir_Teco.h":            "Teco",
    "ir_Neoclima.h":        "Neoclima",
    "ir_Rhoss.h":           "Rhoss",
    "ir_Kelon.h":           "Kelon",
    "ir_Goodweather.h":     "Goodweather",
    "ir_Truma.h":           "Truma",
    "ir_York.h":            "York",
    "ir_Ecoclim.h":         "Ecoclim",
    "ir_Airton.h":          "Airton",
    "ir_Airwell.h":         "Airwell",
    "ir_Bosch.h":           "Bosch",
    "ir_Corona.h":          "Corona",
    "ir_Eurom.h":           "Eurom",
    "ir_Kelvinator.h":      "Kelvinator",
    "ir_NEC.h":             "NEC",
    "ir_Sanyo.h":           "Sanyo",
    "ir_Technibel.h":       "Technibel",
    "ir_Trotec.h":          "Trotec",
}

# Match: const uint8_t / uint16_t / uint32_t kXxx = value;
CONST_PATTERN = re.compile(
    r'const\s+\w+\s+(k\w+)\s*=\s*(0x[\da-fA-F]+|\d+(?:\.\d+)?)\s*;'
    r'(?:\s*//\s*(.*))?',
    re.IGNORECASE
)

# Capability classification by constant name keywords
def classify(name: str) -> str:
    n = name.lower()
    if "mintemp" in n or "min_temp" in n or "mintempf" in n:
        return "min_temp"
    if "maxtemp" in n or "max_temp" in n or "maxtempf" in n:
        return "max_temp"
    if any(x in n for x in ["auto", "cool", "heat", "dry", "fan"]) and "mode" not in n and "fan" not in n:
        if any(x in n for x in ["auto", "cool", "heat", "dry"]):
            return "mode"
    if "fanlow" in n or "fanmed" in n or "fanhi" in n or "fanauto" in n or "fanmax" in n or "fanmin" in n or "fanturbo" in n or "fanquiet" in n:
        return "fan_speed"
    if re.search(r'k\w+(auto|cool|heat|dry|fan)\b', n):
        return "mode"
    if "swing" in n:
        return "swing"
    if "sleep" in n:
        return "sleep_mode"
    if "turbo" in n:
        return "turbo_mode"
    if "quiet" in n:
        return "quiet_mode"
    if "timer" in n:
        return "timer"
    return "other"


def clone_or_update():
    if os.path.exists(os.path.join(RAW_DIR, ".git")):
        print(f"[IRremote] Repo exists, pulling latest...")
        repo = git.Repo(RAW_DIR)
        repo.remotes.origin.pull()
    else:
        print(f"[IRremote] Cloning from {REPO_URL} ...")
        git.Repo.clone_from(REPO_URL, RAW_DIR, depth=1)
    print("[IRremote] Done.")


def parse_ac_header(filepath: str, brand: str) -> list[dict]:
    rows = []
    protocol_class = os.path.splitext(os.path.basename(filepath))[0]

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        seen = set()
        for match in CONST_PATTERN.finditer(content):
            name, value, comment = match.group(1), match.group(2), (match.group(3) or "").strip()

            cap_type = classify(name)
            # Only keep meaningful capabilities
            if cap_type == "other":
                continue

            key = (name, value)
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "source": "IRremoteESP8266",
                "brand": brand,
                "device_type": "AC",
                "protocol_class": protocol_class,
                "constant_name": name,
                "capability_type": cap_type,
                "value": value,
                "notes": comment,
            })

    except Exception as e:
        print(f"  [WARN] Failed to parse {filepath}: {e}")

    return rows


def run():
    clone_or_update()

    src_dir = os.path.join(RAW_DIR, "src")
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    total_rows = 0
    brand_summary = {}

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
        writer.writeheader()

        for filename, brand in tqdm(AC_PROTOCOL_MAP.items(), desc="AC protocol headers"):
            filepath = os.path.join(src_dir, filename)
            if not os.path.exists(filepath):
                print(f"  [SKIP] {filename} not found")
                continue
            rows = parse_ac_header(filepath, brand)
            writer.writerows(rows)
            brand_summary[brand] = len(rows)
            total_rows += len(rows)

    print(f"\n[IRremote] Done. {total_rows} capability rows written to {OUT_FILE}")
    print(f"\nBrand breakdown:")
    for brand, count in sorted(brand_summary.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {brand:25s} {count} constants")

    print(f"\n[NOTE] ac_protocols.csv is a CAPABILITY MAP, not raw IR codes.")
    print(f"       Use IRremoteESP8266 library at runtime to GENERATE actual IR signals.")


if __name__ == "__main__":
    run()
