#!/bin/bash
# Run the full IR code ingestion pipeline.
# Usage:
#   ./run_all.sh                          — Steps 1-3 + 5 (no GlobalCaché)
#   ./run_all.sh --gc-api-key <key>       — All steps including GlobalCaché

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GC_API_KEY=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --gc-api-key) GC_API_KEY="$2"; shift ;;
        *) echo "Unknown param: $1"; exit 1 ;;
    esac
    shift
done

echo "======================================"
echo " Digilux IR Code Ingestion Pipeline"
echo "======================================"

echo ""
echo "Step 1: IRDB..."
python3 01_download_irdb.py

echo ""
echo "Step 2: Flipper Zero IR DB..."
python3 02_download_flipper.py

echo ""
echo "Step 3: IRremoteESP8266 AC protocols..."
python3 03_parse_irremote.py

if [ -n "$GC_API_KEY" ]; then
    echo ""
    echo "Step 4: GlobalCaché API (fill gaps)..."
    python3 04_globalcache_api.py --api-key "$GC_API_KEY" --fill-gaps
else
    echo ""
    echo "Step 4: Skipping GlobalCaché (no --gc-api-key provided)"
fi

echo ""
echo "Step 5: Building master.csv..."
python3 05_build_master.py

echo ""
echo "Done. Check data/processed/master.csv and master_stats.txt"
