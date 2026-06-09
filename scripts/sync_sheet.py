#!/usr/bin/env python3
"""
Fetches the Digizag X SGH Brands Google Sheet and writes it
to public/api/brands.json for GitHub Pages hosting.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from io import StringIO
from urllib.request import urlopen
from urllib.error import URLError

SHEET_ID = "13XVfExaeMHiV2Lw6AsuuSGEXQG_4z_Yf8pV6u6pPdeE"
GID = "0"
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/export?format=csv&gid={GID}"
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "public", "api", "brands.json"
)

COLUMNS = {
    "brand_name": 0,
    "targeting_geos": 1,
    "discount": 2,
    "discount_content": 3,
    "website": 4,
    "coupon_code": 5,
    "brand_logo": 6,
}


def fetch_csv(url: str) -> list[list[str]]:
    try:
        with urlopen(url, timeout=15) as resp:
            content = resp.read().decode("utf-8")
    except URLError as exc:
        print(f"ERROR fetching sheet: {exc}", file=sys.stderr)
        sys.exit(1)

    reader = csv.reader(StringIO(content))
    return list(reader)


def fill_down(rows: list[list[str]], col: int) -> list[list[str]]:
    """Propagate non-empty values downward to simulate merged cells."""
    last = ""
    for row in rows:
        if len(row) > col:
            if row[col].strip():
                last = row[col].strip()
            else:
                row[col] = last
    return rows


def parse_rows(rows: list[list[str]]) -> list[dict]:
    # Skip header row
    data = [list(row) for row in rows[1:] if any(cell.strip() for cell in row)]

    # Fill down brand_name and geo columns (handles merged cells in CSV export)
    fill_down(data, COLUMNS["brand_name"])

    brands: dict[str, dict] = {}

    for row in data:
        def cell(key: str) -> str:
            idx = COLUMNS[key]
            return row[idx].strip() if len(row) > idx else ""

        name = cell("brand_name")
        if not name:
            continue

        geo = cell("targeting_geos")
        discount = cell("discount")
        discount_content = cell("discount_content")
        website = cell("website")
        coupon_code = cell("coupon_code")
        brand_logo = cell("brand_logo")

        if name not in brands:
            brands[name] = {
                "brand_name": name,
                "targeting_geos": [],
                "discount": discount,
                "discount_content": discount_content,
                "website": website,
                "coupon_code": coupon_code,
                "brand_logo": brand_logo,
            }

        # Accumulate unique geos across sub-rows
        if geo and geo not in brands[name]["targeting_geos"]:
            brands[name]["targeting_geos"].append(geo)

        # Update fields if they were empty before
        for field in ("discount", "discount_content", "website", "coupon_code", "brand_logo"):
            if not brands[name][field] and cell(field):
                brands[name][field] = cell(field)

    return list(brands.values())


def main():
    print(f"Fetching sheet from: {CSV_URL}")
    rows = fetch_csv(CSV_URL)
    print(f"  {len(rows)} rows fetched (including header)")

    brands = parse_rows(rows)
    print(f"  {len(brands)} brands parsed")

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Digizag X SGH Brands",
        "total": len(brands),
        "brands": brands,
    }

    out_path = os.path.normpath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Written to {out_path}")


if __name__ == "__main__":
    main()
