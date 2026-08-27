"""
Step 4: Query GlobalCaché IR Database API for IR codes not covered by Steps 1-3.

API Base: https://irdb.globalcache.com:8081/
Auth:     POST /api/account/login → apikey (session-scoped, not durable)

Flow:
  1. Login → get apikey
  2. GET /api/brands → list all brands
  3. GET /api/brands/{brand}/types/{type}/models → get models
  4. GET /api/codesets/{setid}/functions → list functions
  5. GET /api/codesets/{setid}/functions/{fn}/codes?output=direct&format=hex → get code

Usage:
  python 04_globalcache_api.py --email EMAIL --password PASSWORD
  python 04_globalcache_api.py --email EMAIL --password PASSWORD --brand Samsung --device-type TV
  python 04_globalcache_api.py --email EMAIL --password PASSWORD --fill-gaps

Output: data/processed/globalcache.csv
"""

import os
import csv
import time
import argparse
import requests

API_BASE = "https://irdb.globalcache.com:8081"
OUT_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/globalcache.csv")
MASTER_CSV = os.path.join(os.path.dirname(__file__), "../data/processed/master.csv")

SCHEMA = ["source", "brand", "device_type", "model", "command", "protocol", "frequency_khz", "raw_data", "format"]

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

# Target brands for Indian smart home market
TARGET_BRANDS = [
    ("Samsung", "TV"), ("LG", "TV"), ("Sony", "TV"), ("Panasonic", "TV"),
    ("Philips", "TV"), ("TCL", "TV"), ("Hisense", "TV"), ("Vu", "TV"),
    ("Samsung", "AC"), ("LG", "AC"), ("Daikin", "AC"), ("Hitachi", "AC"),
    ("Whirlpool", "AC"), ("Panasonic", "AC"), ("Voltas", "AC"),
    ("Tata Sky", "STB"), ("Airtel", "STB"), ("DEN", "STB"),
    ("Usha", "Fan"), ("Havells", "Fan"), ("Orient", "Fan"), ("Crompton", "Fan"),
]

# GlobalCaché special char escaping
def gc_escape(s: str) -> str:
    return (s
        .replace("&", "xampx")
        .replace("/", "xfslx")
        .replace(">", "xgtx")
        .replace("<", "xltx")
        .replace(":", "xcolx")
        .replace("?", "xquex")
        .replace("%", "xmodx")
        .replace("+", "xaddx"))


def login(email: str, password: str) -> str:
    resp = SESSION.post(f"{API_BASE}/api/account/login",
                        json={"Email": email, "Password": password}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("Status") != "success":
        raise Exception(f"Login failed: {data.get('Message')}")
    apikey = data["Account"]["ApiKey"]
    print(f"[GlobalCaché] Logged in. ApiKey: {apikey[:8]}...")
    return apikey


def register(email: str, password: str) -> str:
    resp = SESSION.post(f"{API_BASE}/api/account/register",
                        json={"Email": email, "Password": password}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("Status") == "success":
        print(f"[GlobalCaché] Account registered successfully.")
        return data["Account"]["ApiKey"]
    raise Exception(f"Registration failed: {data.get('Message')}")


def logout(apikey: str):
    try:
        SESSION.post(f"{API_BASE}/api/account/logout?apikey={apikey}", timeout=10)
        print("[GlobalCaché] Logged out.")
    except Exception:
        pass


def get_brands(apikey: str) -> list[str]:
    resp = SESSION.get(f"{API_BASE}/api/brands?apikey={apikey}", timeout=15)
    resp.raise_for_status()
    return [b["Name"] for b in resp.json()]


def get_models(apikey: str, brand: str, device_type: str) -> list[dict]:
    b = gc_escape(brand)
    t = gc_escape(device_type)
    resp = SESSION.get(f"{API_BASE}/api/brands/{b}/types/{t}/models?apikey={apikey}", timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def get_functions(apikey: str, setid: str) -> list[dict]:
    resp = SESSION.get(f"{API_BASE}/api/codesets/{setid}/functions?apikey={apikey}", timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def get_code(apikey: str, setid: str, function: str) -> str | None:
    fn = gc_escape(function)
    url = f"{API_BASE}/api/codesets/{setid}/functions/{fn}/codes?apikey={apikey}&output=direct&format=hex"
    resp = SESSION.get(url, timeout=15)
    if resp.status_code in (404, 429):
        return None
    resp.raise_for_status()
    data = resp.json()
    if data.get("Status") != "success":
        return None
    code = data.get("Code1") or data.get("HexCode1") or ""
    return code.strip() if code else None


def pronto_frequency_khz(pronto: str) -> str:
    try:
        parts = pronto.strip().split()
        if len(parts) >= 2:
            freq_word = int(parts[1], 16)
            if freq_word > 0:
                freq_hz = 1000000 / (freq_word * 0.241246)
                return str(round(freq_hz / 1000, 1))
    except Exception:
        pass
    return "38"


def fetch_brand_type(apikey: str, brand: str, device_type: str, writer: csv.DictWriter) -> int:
    print(f"  [{brand} / {device_type}] Fetching models...")
    models = get_models(apikey, brand, device_type)
    if not models:
        print(f"  [{brand} / {device_type}] No models found.")
        return 0

    count = 0
    for model in models:
        setid = model.get("ID", "")
        model_name = model.get("Name", "Unknown")
        if not setid:
            continue

        functions = get_functions(apikey, setid)
        time.sleep(0.1)

        for fn_obj in functions:
            function = fn_obj.get("Function", "")
            if not function:
                continue

            code = get_code(apikey, setid, function)
            time.sleep(0.15)  # respect daily rate limit

            if not code:
                continue

            writer.writerow({
                "source": "GlobalCaché",
                "brand": brand,
                "device_type": device_type.upper(),
                "model": model_name,
                "command": function,
                "protocol": "PRONTO",
                "frequency_khz": pronto_frequency_khz(code),
                "raw_data": code,
                "format": "pronto_hex",
            })
            count += 1

    print(f"  [{brand} / {device_type}] {count} codes fetched.")
    return count


def get_missing_brands() -> list[tuple[str, str]]:
    if not os.path.exists(MASTER_CSV):
        return TARGET_BRANDS

    existing = set()
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add((row["brand"].lower(), row["device_type"].upper()))

    return [(b, d) for b, d in TARGET_BRANDS if (b.lower(), d.upper()) not in existing]


def run(email: str, password: str, brand: str = None, device_type: str = None, fill_gaps: bool = False):
    # Try login first, register if account not found
    try:
        apikey = login(email, password)
    except Exception as e:
        print(f"[GlobalCaché] Login failed ({e}). Attempting registration...")
        apikey = register(email, password)

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    total = 0

    try:
        with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=SCHEMA)
            writer.writeheader()

            if fill_gaps:
                missing = get_missing_brands()
                print(f"[GlobalCaché] {len(missing)} brand/device combos to fill...")
                for b, d in missing:
                    total += fetch_brand_type(apikey, b, d, writer)
            elif brand and device_type:
                total += fetch_brand_type(apikey, brand, device_type, writer)
            else:
                print("Provide --brand + --device-type or use --fill-gaps")
    finally:
        logout(apikey)

    print(f"\n[GlobalCaché] Done. {total} rows written to {OUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch IR codes from GlobalCaché IR Database")
    parser.add_argument("--email", required=True, help="GlobalCaché account email")
    parser.add_argument("--password", required=True, help="GlobalCaché account password")
    parser.add_argument("--brand", help="Specific brand (e.g. Samsung)")
    parser.add_argument("--device-type", help="Device type (e.g. TV, AC, Fan, STB)")
    parser.add_argument("--fill-gaps", action="store_true", help="Auto-fill missing brands from master.csv")
    args = parser.parse_args()

    run(args.email, args.password, args.brand, args.device_type, args.fill_gaps)
