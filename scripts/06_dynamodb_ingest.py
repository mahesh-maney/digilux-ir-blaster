"""
Step 6: Ingest master.csv into DynamoDB table digilux_ir_profiles

Table Design:
  PK  : brand_device    — "{brand}#{device_type}"   e.g., "Samsung#TV"
  SK  : model_command   — "{model}#{command}"        e.g., "7,7#KEY_POWER"

GSI (device_type-brand-index):
  PK  : device_type     — "TV" / "AC" / "STB" / "FAN" ...
  SK  : brand           — "Samsung" / "LG" ...

Access Patterns Supported:
  1. Get all commands for a brand+device+model  → query PK=brand#device, SK begins_with model
  2. Get one specific command                   → get_item PK=brand#device, SK=model#command
  3. Browse all brands for a device type        → GSI query on device_type
  4. List all models for a brand+device         → query PK=brand#device

Usage:
  python 06_dynamodb_ingest.py                  (full ingest)
  python 06_dynamodb_ingest.py --dry-run        (validate only, no writes)
  python 06_dynamodb_ingest.py --create-table   (create table + ingest)
  python 06_dynamodb_ingest.py --limit 1000     (ingest first N rows, for testing)
"""

import os
import csv
import time
import boto3
import argparse
from decimal import Decimal
from botocore.exceptions import ClientError
from tqdm import tqdm

MASTER_CSV  = os.path.join(os.path.dirname(__file__), "../data/processed/master.csv")
TABLE_NAME  = "digilux_ir_profiles"
REGION      = "ap-south-1"
BATCH_SIZE  = 25       # DynamoDB max per BatchWriteItem
MAX_ITEM_KB = 380      # DynamoDB limit is 400KB, leave headroom
MAX_RETRIES = 5

dynamodb = boto3.resource("dynamodb", region_name=REGION)
client   = boto3.client("dynamodb", region_name=REGION)


# ─── Table Management ──────────────────────────────────────────────────────────

def create_table():
    print(f"[DynamoDB] Creating table {TABLE_NAME}...")
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "brand_device", "KeyType": "HASH"},
                {"AttributeName": "model_command", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "brand_device",  "AttributeType": "S"},
                {"AttributeName": "model_command",  "AttributeType": "S"},
                {"AttributeName": "device_type",    "AttributeType": "S"},
                {"AttributeName": "brand",          "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "device_type-brand-index",
                    "KeySchema": [
                        {"AttributeName": "device_type", "KeyType": "HASH"},
                        {"AttributeName": "brand",       "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            Tags=[
                {"Key": "project",     "Value": "digilux"},
                {"Key": "component",   "Value": "ir-blaster"},
                {"Key": "environment", "Value": "production"},
            ],
        )
        print(f"[DynamoDB] Waiting for table to become active...")
        table.wait_until_exists()
        print(f"[DynamoDB] Table {TABLE_NAME} is ready.")
        return table
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[DynamoDB] Table already exists.")
            return dynamodb.Table(TABLE_NAME)
        raise


def table_exists() -> bool:
    try:
        client.describe_table(TableName=TABLE_NAME)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


# ─── Row Processing ────────────────────────────────────────────────────────────

def build_item(row: dict) -> dict | None:
    brand       = row.get("brand", "").strip()
    device_type = row.get("device_type", "").strip().upper()
    model       = row.get("model", "").strip()
    command     = row.get("command", "").strip()
    raw_data    = row.get("raw_data", "").strip()

    # Skip invalid rows
    if not brand or not device_type or not model or not command or not raw_data:
        return None

    # Enforce item size limit (raw_data can be large for flipper_raw)
    if len(raw_data.encode("utf-8")) > MAX_ITEM_KB * 1024:
        raw_data = raw_data[: MAX_ITEM_KB * 1024].rsplit(" ", 1)[0]  # trim at word boundary

    brand_device  = f"{brand}#{device_type}"
    model_command = f"{model}#{command}"

    return {
        "brand_device":   brand_device,
        "model_command":  model_command,
        "brand":          brand,
        "device_type":    device_type,
        "model":          model,
        "command":        command,
        "source":         row.get("source", "").strip(),
        "protocol":       row.get("protocol", "").strip(),
        "frequency_khz":  row.get("frequency_khz", "38").strip(),
        "raw_data":       raw_data,
        "format":         row.get("format", "").strip(),
    }


# ─── Batch Writer ──────────────────────────────────────────────────────────────

def batch_write(table, items: list[dict], retries: int = 0):
    requests = [{"PutRequest": {"Item": item}} for item in items]
    try:
        response = dynamodb.batch_write_item(
            RequestItems={TABLE_NAME: requests}
        )
        unprocessed = response.get("UnprocessedItems", {}).get(TABLE_NAME, [])
        if unprocessed:
            if retries >= MAX_RETRIES:
                print(f"  [WARN] {len(unprocessed)} items unprocessed after {MAX_RETRIES} retries — skipping.")
                return len(items) - len(unprocessed)
            wait = 2 ** retries
            time.sleep(wait)
            batch_write(table, [r["PutRequest"]["Item"] for r in unprocessed], retries + 1)
        return len(items) - len(unprocessed)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ProvisionedThroughputExceededException" and retries < MAX_RETRIES:
            time.sleep(2 ** retries)
            return batch_write(table, items, retries + 1)
        raise


# ─── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False, create: bool = False, limit: int = None):
    if not os.path.exists(MASTER_CSV):
        print(f"[ERROR] master.csv not found at {MASTER_CSV}")
        print("        Run 05_build_master.py first.")
        return

    # Table setup
    if create:
        table = create_table()
    elif not dry_run:
        if not table_exists():
            print(f"[ERROR] Table {TABLE_NAME} does not exist.")
            print("        Run with --create-table to create it first.")
            return
        table = dynamodb.Table(TABLE_NAME)
    else:
        table = None
        print("[DRY RUN] No writes will be made.\n")

    # Count rows for progress bar
    print("[DynamoDB] Counting rows in master.csv...")
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        total_rows = sum(1 for _ in f) - 1  # subtract header
    if limit:
        total_rows = min(total_rows, limit)
    print(f"[DynamoDB] {total_rows:,} rows to process.\n")

    written     = 0
    skipped     = 0
    batch       = []
    row_count   = 0

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with tqdm(total=total_rows, desc="Ingesting", unit="rows") as pbar:
            for row in reader:
                if limit and row_count >= limit:
                    break

                item = build_item(row)
                row_count += 1

                if not item:
                    skipped += 1
                    pbar.update(1)
                    continue

                if dry_run:
                    written += 1
                    pbar.update(1)
                    continue

                batch.append(item)

                if len(batch) >= BATCH_SIZE:
                    written += batch_write(table, batch)
                    batch = []

                pbar.update(1)

            # Flush remaining
            if batch and not dry_run:
                written += batch_write(table, batch)

    print(f"\n[DynamoDB] Ingestion complete.")
    print(f"  Written : {written:,}")
    print(f"  Skipped : {skipped:,}")
    print(f"  Table   : {TABLE_NAME} ({REGION})")

    if not dry_run:
        # Final item count
        try:
            resp = client.describe_table(TableName=TABLE_NAME)
            item_count = resp["Table"].get("ItemCount", "unknown (updating...)")
            print(f"  Items in table (approx): {item_count:,}" if isinstance(item_count, int) else f"  Items in table: {item_count}")
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest master.csv into digilux_ir_profiles DynamoDB table")
    parser.add_argument("--dry-run",      action="store_true", help="Validate rows without writing to DynamoDB")
    parser.add_argument("--create-table", action="store_true", help="Create the DynamoDB table before ingesting")
    parser.add_argument("--limit",        type=int,            help="Only ingest first N rows (for testing)")
    args = parser.parse_args()

    run(dry_run=args.dry_run, create=args.create_table, limit=args.limit)
