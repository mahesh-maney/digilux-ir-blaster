"""
Step 5: Merge all processed CSVs into master.csv, deduplicate, and validate.

Merges:
  - data/processed/irdb.csv
  - data/processed/flipper.csv
  - data/processed/globalcache.csv  (if exists)

Excludes:
  - data/processed/ac_protocols.csv  (capability map, different schema)

Output: data/processed/master.csv + data/processed/master_stats.txt
"""

import os
import csv
from collections import defaultdict

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "../data/processed")
SOURCES = ["irdb.csv", "flipper.csv", "globalcache.csv"]
OUT_FILE = os.path.join(PROCESSED_DIR, "master.csv")
STATS_FILE = os.path.join(PROCESSED_DIR, "master_stats.txt")

SCHEMA = ["source", "brand", "device_type", "model", "command", "protocol", "frequency_khz", "raw_data", "format"]

REQUIRED_FIELDS = ["brand", "device_type", "raw_data"]


def is_valid(row: dict) -> bool:
    for field in REQUIRED_FIELDS:
        val = row.get(field, "").strip()
        if not val or val.lower() in ("unknown", "none", "null"):
            return False
    # raw_data must be non-trivial
    if len(row.get("raw_data", "")) < 5:
        return False
    return True


def make_dedup_key(row: dict) -> tuple:
    return (
        row.get("brand", "").lower().strip(),
        row.get("device_type", "").upper().strip(),
        row.get("model", "").lower().strip(),
        row.get("command", "").lower().strip(),
    )


def run():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    all_rows = []
    source_counts = {}

    for filename in SOURCES:
        filepath = os.path.join(PROCESSED_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  [SKIP] {filename} not found — run the corresponding download script first.")
            continue

        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize row to schema
                normalized = {k: row.get(k, "").strip() for k in SCHEMA}
                if is_valid(normalized):
                    all_rows.append(normalized)
                    count += 1

        source_counts[filename] = count
        print(f"  [LOAD] {filename}: {count} valid rows")

    print(f"\n[Master] Total before dedup: {len(all_rows)}")

    # Deduplicate — keep first occurrence (IRDB > Flipper > GlobalCaché priority)
    seen = {}
    deduped = []
    for row in all_rows:
        key = make_dedup_key(row)
        if key not in seen:
            seen[key] = True
            deduped.append(row)

    print(f"[Master] Total after dedup:  {len(deduped)}")

    # Write master CSV
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(deduped)

    # Stats
    stats = defaultdict(lambda: defaultdict(int))
    for row in deduped:
        stats[row["device_type"]][row["brand"]] += 1

    lines = [
        f"Master IR Code Database — Stats",
        f"================================",
        f"Total records: {len(deduped)}",
        f"",
    ]
    for dtype in sorted(stats.keys()):
        lines.append(f"{dtype}: {sum(stats[dtype].values())} records, {len(stats[dtype])} brands")
        for brand in sorted(stats[dtype].keys())[:10]:
            lines.append(f"  {brand}: {stats[dtype][brand]}")
        if len(stats[dtype]) > 10:
            lines.append(f"  ... and {len(stats[dtype]) - 10} more brands")
        lines.append("")

    stats_text = "\n".join(lines)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        f.write(stats_text)

    print(f"\n{stats_text}")
    print(f"[Master] Written to {OUT_FILE}")
    print(f"[Master] Stats written to {STATS_FILE}")


if __name__ == "__main__":
    run()
