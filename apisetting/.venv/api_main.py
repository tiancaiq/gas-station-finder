from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json
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
from fuel_advisor_demo_haversine import run_from_payload  # type: ignore

app = FastAPI()


def ensure_unique_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: Dict[str, int] = {}
    for item in items:
        base = str(item.get("id", "")).strip() or "station"
        count = seen.get(base, 0)
        item["id"] = base if count == 0 else f"{base}-{count+1}"
        seen[base] = count + 1
    return items


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
