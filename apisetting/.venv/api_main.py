from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json
import re
import pandas as pd
from fastapi import FastAPI, HTTPException

# Resolve project paths from this file:
# apisetting/.venv/api_main.py -> project root -> GasStationfinder/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_ROOT / "GasStationfinder"
CSV_PATH = ENGINE_DIR / "stations_california_clean_5_columns.csv"
OUT_JSON_PATH = ENGINE_DIR / "fuel_advisor_results.json"

# Import the recommendation engine from your existing script.
import sys

sys.path.insert(0, str(ENGINE_DIR))
from fuel_advisor_demo_haversine import run_from_payload, stable_station_id  # type: ignore

app = FastAPI()


def ensure_unique_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: Dict[str, int] = {}
    for item in items:
        base = str(item.get("id", "")).strip() or "station"
        count = seen.get(base, 0)
        item["id"] = base if count == 0 else f"{base}-{count+1}"
        seen[base] = count + 1
    return items


def _normalize_station_id(raw_id: str) -> str:
    s = str(raw_id).strip()
    m = re.match(r"^([0-9a-f]{16})(?:-\d+)?$", s)
    if m:
        return m.group(1)
    return s


def _resolve_station_id_from_payload_id(raw_id: str) -> str:
    # Supports direct station id, dedupe-suffixed id (xxxx-2), or 1-based index
    # from latest fuel_advisor_results.json.
    rid = str(raw_id).strip()
    if rid.isdigit() and OUT_JSON_PATH.exists():
        try:
            arr = json.loads(OUT_JSON_PATH.read_text(encoding="utf-8"))
            idx = int(rid) - 1
            if isinstance(arr, list) and 0 <= idx < len(arr):
                rid = str(arr[idx].get("id", rid))
        except Exception:
            pass
    return _normalize_station_id(rid)


@app.post("/recommend")
async def recommend_endpoint(payload: Dict[str, Any]):
    if not CSV_PATH.exists():
        raise HTTPException(status_code=500, detail=f"CSV not found: {CSV_PATH}")

    try:
        results = run_from_payload(
            payload=payload,
            csv_path=str(CSV_PATH),
            out_json=str(OUT_JSON_PATH),
        )
        results = ensure_unique_ids(results)
        with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except SystemExit as e:
        message = str(e)
        if message.startswith("400"):
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failure: {e}")

    # Returns 200 OK with JSON array of stations.
    return results


@app.post("/update-price")
async def price_update_endpoint(payload: Dict[str, Any]):
    if not CSV_PATH.exists():
        raise HTTPException(status_code=500, detail=f"CSV not found: {CSV_PATH}")

    id_raw = payload.get("id", payload.get("stationId"))
    if id_raw is None:
        raise HTTPException(status_code=400, detail='Missing required field: "id" or "stationId"')

    price_raw = payload.get("price", payload.get("price:", payload.get("newPrice")))
    if price_raw is None:
        raise HTTPException(status_code=400, detail='Missing required field: "price" (or "price:" / "newPrice")')

    try:
        new_price = float(price_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail='Invalid "price": must be numeric')
    if new_price <= 0:
        raise HTTPException(status_code=400, detail='Invalid "price": must be > 0')

    req_id = str(id_raw).strip()
    station_id = _resolve_station_id_from_payload_id(req_id)
    if not station_id:
        raise HTTPException(status_code=400, detail='Invalid "id"')

    try:
        df = pd.read_csv(CSV_PATH)
        needed = {"name", "address", "latitude", "longitude", "price"}
        missing = [c for c in needed if c not in df.columns]
        if missing:
            raise HTTPException(status_code=500, detail=f"CSV missing columns: {missing}")

        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["_stationId"] = df.apply(
            lambda r: stable_station_id(str(r["name"]), str(r["address"]), float(r["latitude"]), float(r["longitude"]))
            if pd.notna(r["latitude"]) and pd.notna(r["longitude"]) else "",
            axis=1,
        )

        mask = df["_stationId"] == station_id
        updated_rows = int(mask.sum())
        if updated_rows == 0:
            raise HTTPException(status_code=404, detail=f'Station id not found: "{req_id}"')

        df.loc[mask, "price"] = f"${new_price:.2f}"
        df = df.drop(columns=["_stationId"])
        df.to_csv(CSV_PATH, index=False)

        return {
            "ok": True,
            "id": req_id,
            "resolvedStationId": station_id,
            "updatedRows": updated_rows,
            "newPrice": round(new_price, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price update failure: {e}")
