#!/usr/bin/env python3
"""
Fuel Advisor recommendation engine (file-based demo).

This script does not run an API. It reads a JSON request shaped like:
POST /recommend payload, computes recommendations, and writes the
response JSON array that the frontend expects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


CSV_DEFAULT = "stations_california_clean_5_columns.csv"
REQUEST_DEFAULT = "query_example.json"
OUT_DEFAULT = "fuel_advisor_results.json"
TOP_DEFAULT = 10

KNOWN_BRANDS = [
    "7-Eleven",
    "ARCO",
    "Chevron",
    "Shell",
    "Costco",
    "Mobil",
    "76",
    "Valero",
    "Sinclair",
    "Speedway",
    "Gulf",
    "Ralphs",
    "Thrifty",
    "Sam's Fuel",
    "USA Gasoline",
]


@dataclass
class RecommendRequest:
    mode: str
    max_distance_miles: float
    priority: str
    amenities: Dict[str, bool]
    latitude: float
    longitude: float
    urgency: float
    budget_price_cap: Optional[float]
    comfort_i_dont_care: bool
    brand: Optional[str]
    top: int


def parse_price(x: Any) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("inf")
    m = re.search(r"(\d+(?:\.\d+)?)", str(x))
    return float(m.group(1)) if m else float("inf")


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def stable_station_id(name: str, address: str, lat: float, lon: float) -> str:
    key = f"{name.strip().lower()}|{address.strip().lower()}|{lat:.6f}|{lon:.6f}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def ensure_unique_ids(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Guarantee unique IDs in one response payload."""
    seen: Dict[str, int] = {}
    for item in results:
        base = str(item.get("id", "")).strip() or "station"
        count = seen.get(base, 0)
        if count == 0:
            item["id"] = base
        else:
            item["id"] = f"{base}-{count+1}"
        seen[base] = count + 1
    return results


def infer_brand(name: str) -> str:
    n = (name or "").strip()
    lower = n.lower()
    for b in KNOWN_BRANDS:
        if b.lower() in lower:
            return b
    return n.split()[0] if n else "Unknown"


def infer_amenities_and_nearby(name: str) -> Dict[str, Any]:
    n = (name or "").lower()

    convenience = any(
        k in n
        for k in [
            "7-eleven",
            "shell",
            "chevron",
            "arco",
            "mobil",
            "76",
            "valero",
            "sinclair",
            "speedway",
            "gas",
            "fuel",
            "gulf",
        ]
    )
    food = any(
        k in n for k in ["food", "market", "mart", "7-eleven", "costco", "ralphs", "sam"]
    )
    restroom = convenience or food

    nearby: List[str] = []
    if food:
        nearby.append("Food options")
    if convenience:
        nearby.append("Convenience Store")
    if restroom:
        nearby.append("Restroom")

    return {
        "food": food,
        "restroom": restroom,
        "convenienceStore": convenience,
        "nearby": nearby,
    }


def parse_request_json(payload: Dict[str, Any]) -> RecommendRequest:
    required = ["mode", "maxDistanceMiles", "priority", "amenities", "latitude", "longitude"]
    missing = [k for k in required if k not in payload]
    if missing:
        raise SystemExit(f'400 invalid request: missing fields {missing}')

    mode = str(payload["mode"]).strip().lower()
    if mode not in {"emergency", "budget", "comfort"}:
        raise SystemExit('400 invalid request: mode must be "emergency", "budget", or "comfort"')

    priority = str(payload["priority"]).strip().lower()
    if priority not in {"cheapest", "closest", "balanced"}:
        raise SystemExit('400 invalid request: priority must be "cheapest", "closest", or "balanced"')

    try:
        lat = float(payload["latitude"])
        lon = float(payload["longitude"])
    except (TypeError, ValueError):
        raise SystemExit("400 invalid request: latitude/longitude must be numeric")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise SystemExit("400 invalid request: latitude/longitude out of range")

    try:
        max_distance = float(payload["maxDistanceMiles"])
    except (TypeError, ValueError):
        raise SystemExit("400 invalid request: maxDistanceMiles must be numeric")
    if max_distance <= 0:
        raise SystemExit("400 invalid request: maxDistanceMiles must be > 0")

    amenities = payload.get("amenities", {})
    if not isinstance(amenities, dict):
        raise SystemExit("400 invalid request: amenities must be an object")
    normalized_amenities = {
        "food": bool(amenities.get("food", False)),
        "restroom": bool(amenities.get("restroom", False)),
        "convenienceStore": bool(amenities.get("convenienceStore", False)),
    }

    urgency = float(payload.get("urgency", 0.5))
    urgency = max(0.0, min(1.0, urgency))

    budget_cap = payload.get("budgetPriceCap")
    if budget_cap is not None:
        try:
            budget_cap = float(budget_cap)
        except (TypeError, ValueError):
            raise SystemExit("400 invalid request: budgetPriceCap must be numeric")
        budget_cap = max(1.0, min(7.0, budget_cap))

    comfort_i_dont_care = bool(payload.get("comfortIDontCare", False))
    brand = payload.get("brand")
    brand = str(brand).strip() if brand is not None else ""
    brand = brand if brand else None

    top = int(payload.get("top", TOP_DEFAULT))
    if top < 1:
        top = TOP_DEFAULT

    return RecommendRequest(
        mode=mode,
        max_distance_miles=max_distance,
        priority=priority,
        amenities=normalized_amenities,
        latitude=lat,
        longitude=lon,
        urgency=urgency,
        budget_price_cap=budget_cap,
        comfort_i_dont_care=comfort_i_dont_care,
        brand=brand,
        top=top,
    )


def amenity_score(station_amenities: Dict[str, bool], requested: Dict[str, bool]) -> int:
    score = 0
    for k in ["food", "restroom", "convenienceStore"]:
        if requested.get(k, False) and station_amenities.get(k, False):
            score += 1
    return score


def mode_why(
    req: RecommendRequest,
    row: pd.Series,
    used_budget_fallback: bool,
    matched_amenities: List[str],
) -> str:
    x = req.max_distance_miles
    if req.mode == "emergency":
        return f'Open + closest within {x:.0f} mi'
    if req.mode == "budget":
        if used_budget_fallback and req.budget_price_cap is not None:
            return f'No stations under budget cap; showing closest alternatives near ${req.budget_price_cap:.2f}'
        if req.budget_price_cap is not None:
            return f'Under ${req.budget_price_cap:.2f} cap and among cheapest'
        return "Among cheapest with reasonable distance"
    if matched_amenities:
        return f'Matches amenities: {"+".join(matched_amenities)}, open, good nearby'
    return "Open, comfortable stop with decent distance"


def recommend(req: RecommendRequest, df: pd.DataFrame) -> List[Dict[str, Any]]:
    work = df.copy()
    for col in ["name", "address", "price", "latitude", "longitude"]:
        if col not in work.columns:
            raise SystemExit(f"CSV missing required column: {col}")

    work["price"] = work["price"].apply(parse_price)
    work["latitude"] = pd.to_numeric(work["latitude"], errors="coerce")
    work["longitude"] = pd.to_numeric(work["longitude"], errors="coerce")
    work = work.dropna(subset=["latitude", "longitude"]).copy()
    work["name"] = work["name"].astype(str)
    work["address"] = work["address"].astype(str)
    work["brand"] = work["name"].apply(infer_brand)
    work["isOpen"] = True

    work["distanceMiles"] = work.apply(
        lambda r: haversine_miles(req.latitude, req.longitude, float(r["latitude"]), float(r["longitude"])),
        axis=1,
    )
    work["stationId"] = work.apply(
        lambda r: stable_station_id(str(r["name"]), str(r["address"]), float(r["latitude"]), float(r["longitude"])),
        axis=1,
    )

    # 4.1 Candidate retrieval hard filters.
    work = work[work["distanceMiles"] <= req.max_distance_miles].copy()
    if req.brand:
        b = req.brand.lower()
        work = work[work["brand"].str.lower().str.contains(re.escape(b))].copy()

    if work.empty:
        return []

    used_budget_fallback = False
    if req.mode == "budget" and req.budget_price_cap is not None:
        under_cap = work[work["price"] <= req.budget_price_cap].copy()
        if under_cap.empty:
            used_budget_fallback = True
        else:
            work = under_cap

    if work.empty:
        return []

    # Station features.
    inferred = work["name"].apply(infer_amenities_and_nearby)
    work["stationFood"] = inferred.apply(lambda x: x["food"])
    work["stationRestroom"] = inferred.apply(lambda x: x["restroom"])
    work["stationConvenienceStore"] = inferred.apply(lambda x: x["convenienceStore"])
    work["nearby"] = inferred.apply(lambda x: x["nearby"])
    work["amenityScore"] = work.apply(
        lambda r: amenity_score(
            {
                "food": bool(r["stationFood"]),
                "restroom": bool(r["stationRestroom"]),
                "convenienceStore": bool(r["stationConvenienceStore"]),
            },
            req.amenities,
        ),
        axis=1,
    )

    work["normDistance"] = normalize(work["distanceMiles"].tolist())
    work["normPrice"] = normalize(work["price"].tolist())
    work["openBonus"] = work["isOpen"].apply(lambda x: 1 if x else -1)

    # 4.3 Scoring formulas (higher is better).
    if req.mode == "emergency":
        work["score"] = (
            2.0 * work["openBonus"]
            - (2.0 + 3.0 * req.urgency) * work["normDistance"]
            - 0.8 * work["normPrice"]
            + 0.2 * work["amenityScore"]
        )
    elif req.mode == "budget":
        work["score"] = (
            1.0 * work["openBonus"]
            - 3.0 * work["normPrice"]
            - 0.8 * work["normDistance"]
            + 0.1 * work["amenityScore"]
        )
        if used_budget_fallback and req.budget_price_cap is not None:
            work["score"] = work["score"] - 5.0 * (work["price"] - req.budget_price_cap).clip(lower=0.0)
    else:
        if req.comfort_i_dont_care:
            work["score"] = (
                2.5 * work["openBonus"]
                - 0.6 * work["normDistance"]
                - 0.3 * work["normPrice"]
                + 1.0 * work["amenityScore"]
            )
        else:
            work["score"] = (
                2.5 * work["openBonus"]
                - 1.2 * work["normDistance"]
                - 1.0 * work["normPrice"]
                + 0.9 * work["amenityScore"]
            )

    # 4.4 Final ordering by priority.
    if req.priority == "cheapest":
        work = work.sort_values(["price", "score", "distanceMiles"], ascending=[True, False, True])
    elif req.priority == "closest":
        work = work.sort_values(["distanceMiles", "score", "price"], ascending=[True, False, True])
    else:
        work = work.sort_values(["score"], ascending=[False])

    # Source CSV can contain repeated rows for the same station.
    # Keep the best-ranked row per stable station ID.
    work = work.drop_duplicates(subset=["stationId"], keep="first")
    work = work.head(req.top).copy()

    results: List[Dict[str, Any]] = []
    for row in work.itertuples(index=False):
        matched_amenities = []
        if req.amenities.get("food") and row.stationFood:
            matched_amenities.append("food")
        if req.amenities.get("restroom") and row.stationRestroom:
            matched_amenities.append("restroom")
        if req.amenities.get("convenienceStore") and row.stationConvenienceStore:
            matched_amenities.append("convenienceStore")

        sid = str(row.stationId)

        results.append(
            {
                "id": sid,
                "name": str(row.name),
                "brand": str(row.brand),
                "price": float(row.price) if math.isfinite(row.price) else None,
                "distanceMiles": float(round(row.distanceMiles, 3)),
                "isOpen": bool(row.isOpen),
                "why": mode_why(req, pd.Series(row._asdict()), used_budget_fallback, matched_amenities),
                "nearby": list(row.nearby) if isinstance(row.nearby, list) else [],
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
            }
        )

    return ensure_unique_ids(results)


def load_request(path: str) -> RecommendRequest:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"400 invalid request: file not found {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"400 invalid request: malformed JSON in {path}: {e}")

    if not isinstance(payload, dict):
        raise SystemExit("400 invalid request: root JSON must be an object")
    return parse_request_json(payload)


def run_from_payload(
    payload: Dict[str, Any],
    csv_path: str = CSV_DEFAULT,
    out_json: Optional[str] = OUT_DEFAULT,
) -> List[Dict[str, Any]]:
    """
    Run recommendations directly from API payload.
    Optionally writes response JSON to out_json.
    """
    req = parse_request_json(payload)
    df = pd.read_csv(csv_path)
    response = recommend(req, df)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
    return response


def main() -> None:
    ap = argparse.ArgumentParser(description="Fuel Advisor file-based recommender")
    ap.add_argument("--csv", default=CSV_DEFAULT, help=f"Path to stations CSV (default: {CSV_DEFAULT})")
    ap.add_argument(
        "--request-json",
        default=REQUEST_DEFAULT,
        help=f"Path to request JSON in frontend /recommend format (default: {REQUEST_DEFAULT})",
    )
    ap.add_argument("--out-json", default=OUT_DEFAULT, help=f"Output JSON array path (default: {OUT_DEFAULT})")
    args = ap.parse_args()

    req = load_request(args.request_json)
    response = run_from_payload(
        payload={
            "mode": req.mode,
            "maxDistanceMiles": req.max_distance_miles,
            "priority": req.priority,
            "amenities": req.amenities,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "urgency": req.urgency,
            "budgetPriceCap": req.budget_price_cap,
            "comfortIDontCare": req.comfort_i_dont_care,
            "brand": req.brand,
            "top": req.top,
        },
        csv_path=args.csv,
        out_json=args.out_json,
    )

    print(f"Wrote {len(response)} stations to {args.out_json}")


if __name__ == "__main__":
    main()
