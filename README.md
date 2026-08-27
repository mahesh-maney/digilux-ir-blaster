# Digilux IR Blaster — IR Code Database Pipeline

IR code ingestion pipeline for the Digilux Smart Home platform. Downloads, parses, normalizes, merges IR codes from multiple open-source and community databases, and loads them into DynamoDB.

---

## What This Does

Builds a master IR code database from 3 sources and loads into DynamoDB:

| Source | Type | Records |
|---|---|---|
| [IRDB](https://github.com/probonopd/irdb) | Protocol-based (device/subdevice/function) | 111,088 |
| [Flipper Zero IR DB](https://github.com/logickworkshop/Flipper-IRDB) | Raw pulse timings + parsed | 300,796 |
| [IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266) | AC capability map (runtime generation) | 607 |
| **master.csv (after dedup)** | | **341,468** |

---

## Device Coverage

| Device Type | Records | Notable Brands |
|---|---|---|
| TV | 3,826+ | Samsung (1,790), LG (1,383), Sony (1,149), Panasonic, Philips |
| AC | 1,296+ (29+ brands) | Daikin (83), LG (71), Hitachi (75), Samsung, Haier |
| AV Receiver | 18,174 (63 brands) | Denon, Yamaha, Marantz, Onkyo, Pioneer |
| Cable / STB | 1,378 (38 brands) | ARRIS, Amino, DishTV |
| Blu-ray / DVD | 1,449 | Samsung, LG, Panasonic, Sony |
| Audio | 4,943 (78 brands) | Sony, Bose, Apple, JBL |
| Air Purifiers | 151 | Dyson, IQAir, Blueair |

> **Note — Voltas AC:** Not present in any open-source IR database (Indian-only brand). Will be sourced via IR Learning mode (Phase 2) or GlobalCaché once account is verified.

---

## Directory Structure

```
ir-blaster/
├── README.md
├── requirements.txt
├── scripts/
│   ├── 01_download_irdb.py        — Clone IRDB, parse CSV → irdb.csv
│   ├── 02_download_flipper.py     — Clone Flipper Zero DB, parse .ir → flipper.csv
│   ├── 03_parse_irremote.py       — Clone IRremoteESP8266, extract AC capabilities → ac_protocols.csv
│   ├── 04_globalcache_api.py      — GlobalCaché API gap-filler → globalcache.csv
│   ├── 05_build_master.py         — Merge + dedup + validate → master.csv
│   ├── 06_dynamodb_ingest.py      — Load master.csv → DynamoDB digilux_ir_profiles
│   └── run_all.sh                 — One-shot pipeline runner (Steps 1–5)
└── data/
    ├── raw/                       — Cloned repos (git-ignored)
    └── processed/                 — Normalized CSVs (git-ignored)
```

---

## CSV Schema

All output CSVs share a common schema:

| Column | Description | Example |
|---|---|---|
| `source` | Origin database | `IRDB`, `FlipperZero`, `GlobalCaché` |
| `brand` | Manufacturer | `Samsung`, `Daikin`, `LG` |
| `device_type` | Device category | `TV`, `AC`, `STB`, `FAN` |
| `model` | Remote/model identifier | `7,7` or `Daikin_FTX50GV1B` |
| `command` | Button/function name | `KEY_POWER`, `Cool_24`, `Vol_up` |
| `protocol` | IR protocol | `NEC`, `Samsung32`, `RAW` |
| `frequency_khz` | Carrier frequency | `38` |
| `raw_data` | IR payload | `device=7 subdevice=7 function=2` or raw pulse timings |
| `format` | Payload format | `irdb_protocol`, `flipper_raw`, `flipper_parsed` |

`ac_protocols.csv` uses a different schema (capability map — not raw codes):

| Column | Description |
|---|---|
| `brand` | AC brand |
| `protocol_class` | C++ class name in IRremoteESP8266 |
| `constant_name` | Library constant (e.g. `kDaikinMinTemp`) |
| `capability_type` | `min_temp`, `max_temp`, `mode`, `fan_speed`, `swing` |
| `value` | Numeric value |

---

## DynamoDB Table — `digilux_ir_profiles`

### Table Design

| Key | Attribute | Example |
|---|---|---|
| Partition Key (PK) | `brand_device` = `{brand}#{device_type}` | `Samsung#TV` |
| Sort Key (SK) | `model_command` = `{model}#{command}` | `7,7#KEY_POWER` |

### GSI

| Index | PK | SK | Use Case |
|---|---|---|---|
| `device_type-brand-index` | `device_type` | `brand` | Browse all brands for a device type |

### Access Patterns

```python
# 1. Get all commands for a specific brand + device + model
table.query(KeyConditionExpression=Key("brand_device").eq("Samsung#TV") &
            Key("model_command").begins_with("7,7#"))

# 2. Get one specific command
table.get_item(Key={"brand_device": "Samsung#TV", "model_command": "7,7#KEY_POWER"})

# 3. Browse all AC brands
table.query(IndexName="device_type-brand-index",
            KeyConditionExpression=Key("device_type").eq("AC"))
```

### Validation Results (2026-08-27)

| Check | Result |
|---|---|
| Total rows ingested | 341,468 |
| Rows skipped | 0 |
| Empty `raw_data` fields | 0 |
| Oversized items (>380KB) | 0 |
| PK/SK structure valid | 100% |
| GSI status | ACTIVE |
| Ingestion time | ~9 minutes |

---

## Quick Start

### Prerequisites

```bash
pip3 install -r requirements.txt
```

### Run Full Pipeline (Steps 1–5, no API key needed)

```bash
cd scripts
./run_all.sh
```

### Load into DynamoDB (Step 6)

```bash
# Create table + full ingest
python3 06_dynamodb_ingest.py --create-table

# Dry run (validate only)
python3 06_dynamodb_ingest.py --dry-run

# Test with first 500 rows
python3 06_dynamodb_ingest.py --create-table --limit 500
```

### Run with GlobalCaché API (fills brand gaps)

```bash
# Auth: POST /api/account/login with email + password → returns apikey
# Base URL: https://irdb.globalcache.com:8081/
# Account: mahesh.maney@gmail.com (verification pending)

python3 04_globalcache_api.py --email EMAIL --password PASSWORD --fill-gaps
```

### Run Individual Steps

```bash
python3 01_download_irdb.py       # ~111K rows, IRDB
python3 02_download_flipper.py    # ~300K rows, Flipper Zero DB
python3 03_parse_irremote.py      # AC capability map (37 brands)
python3 04_globalcache_api.py --email EMAIL --password PASSWORD --fill-gaps
python3 05_build_master.py        # merge + dedup → master.csv
python3 06_dynamodb_ingest.py --create-table  # load to DynamoDB
```

---

## IR Code Sourcing Strategy

```
Priority 1: IRremoteESP8266    — ESP32 native, covers 95% of AC brands (runtime generation)
Priority 2: IRDB               — 6,000+ devices, protocol-based
Priority 3: Flipper Zero DB    — 8,900+ files, raw timings + parsed, community-driven
Priority 4: GlobalCaché API    — 200,000+ devices, gap-fill (account verification pending)
Priority 5: IR Learning mode   — User captures unknown remotes (Phase 2)
```

---

## AWS Integration

```
Controller (ESP32 + IR LED/RX)
        |
        | MQTT
        v
AWS IoT Core  (a2yxnt6tjmcgb1-ats.iot.ap-south-1.amazonaws.com)
        |
   Lambda Functions
        |
   ┌────┴──────────────────────────────┐
   │  DynamoDB (ap-south-1)            │
   │  - digilux_ir_profiles            │  ← 341,468 IR codes (this pipeline)
   │  - digilux_ir_devices             │  ← user's IR device bindings (planned)
   │  - digilux_scene_data             │  ← extended for IR actions
   └───────────────────────────────────┘
        |
   API Gateway (ds6nxf8ac5 / smarthome stage)
        |
   Alexa (alexa-redux, eu-west-1)
```

### MQTT Topics

| Topic | Direction | Purpose |
|---|---|---|
| `controllers/{id}/ir/command` | Cloud → Device | Send IR command |
| `controllers/{id}/ir/learn` | Device → Cloud | Capture unknown remote |
| `controllers/{id}/ir/ack` | Device → Cloud | Command delivery acknowledgement |

### API Endpoints (Planned)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/ir/devices/{deviceId}/command` | Send IR command |
| `POST` | `/ir/devices/learn` | Start IR learning mode |
| `GET` | `/ir/profiles?brand=Samsung&type=TV` | Search IR profiles |

---

## Phased Rollout

| Phase | Scope | Status |
|---|---|---|
| **Phase 0** | IR code database pipeline + DynamoDB ingestion | **Complete** |
| **Phase 1** | Core IR TX — Lambda + API + IoT Core → controller | Planned |
| **Phase 2** | IR Learning — capture unknown remotes (e.g. Voltas) | Planned |
| **Phase 3** | AC Structured Control — temp/mode/fan API | Planned |
| **Phase 4** | Alexa + Scene integration | Planned |

---

## AC Protocol Notes

AC IR codes are **stateful** — each transmission encodes the full AC state (temperature + mode + fan speed + swing) in a single 128–283 bit frame. These are **not** simple on/off codes.

The `IRremoteESP8266` library has reverse-engineered 37 AC brands including Daikin, LG, Samsung, Haier, Hitachi, Panasonic, Mitsubishi, Fujitsu, and more. At runtime, the ESP32 controller calls the library directly to generate protocol-correct IR frames from structured input:

```json
{ "brand": "Daikin", "temp": 24, "mode": "cool", "fan": "auto", "swing": true }
```

---

## Known Gaps

| Brand | Device | Gap | Resolution |
|---|---|---|---|
| Voltas | AC | Not in any open-source DB | IR Learning (Phase 2) or GlobalCaché |
| Tata Sky | STB | Not in GlobalCaché | IR Learning (Phase 2) |
| Havells | Fan | Not in any DB | IR Learning (Phase 2) |
| Orient | Fan | Not in any DB | IR Learning (Phase 2) |

---

## .gitignore

```
data/raw/
data/processed/
__pycache__/
*.pyc
.DS_Store
```
