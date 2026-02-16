#!/usr/bin/env python3
"""
Fuel Advisor - terminal demo for retrieval + ranking (with real coordinates).

This script reads a CSV of gas stations and prints ranked recommendations given a user "query" consisting of:
  1) mode: emergency | budget | comfort
  2) scale (mode-aware slider/value)
  3) max distance (miles)
  4) priority: cheapest | closest | balanced
  5) brand (optional string)

Unlike the earlier demo, distance is computed using Haversine distance from the user's latitude/longitude
to each station's latitude/longitude (straight-line distance in miles).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd


# Default to the cleaned CA-only file you generated with coords.
CSV_DEFAULT = "stations_california_clean_5_columns.csv"


def parse_price(x: str) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("inf")
    s = str(x).strip()
    # extract first float-like token
    m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else float("inf")


def normalize(series: List[float]) -> List[float]:
    lo = min(series)
    hi = max(series)
    if hi == lo:
        return [0.0 for _ in series]
    return [(v - lo) / (hi - lo) for v in series]


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points (miles)."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@dataclass
class Query:
    user_lat: float
    user_lon: float
    mode: str               # emergency | budget | comfort
    scale: float            # mode-aware: emergency/comfort 0..1, budget $/gal
    max_distance: float     # miles
    priority: str           # cheapest | closest | balanced
    brand: Optional[str]    # optional


def weights_for(mode: str, priority: str) -> Dict[str, float]:
    """
    Base mode weights, then nudged by priority toggle.

    Score is minimized. Price/distance are normalized 0..1.
    """
    mode = mode.lower()
    priority = priority.lower()

    if mode == "emergency":
        w = {"price": 0.25, "distance": 0.55, "amenity": 0.0, "brand": 0.0, "urgency": 0.20}
    elif mode == "budget":
        w = {"price": 0.65, "distance": 0.35, "amenity": 0.0, "brand": 0.0, "urgency": 0.00}
    elif mode == "comfort":
        w = {"price": 0.35, "distance": 0.30, "amenity": 0.25, "brand": 0.10, "urgency": 0.00}
    else:
        w = {"price": 0.45, "distance": 0.45, "amenity": 0.0, "brand": 0.0, "urgency": 0.10}

    # Priority toggle nudges weights (kept simple & explainable)
    if priority == "cheapest":
        w["price"] += 0.15
        w["distance"] -= 0.10
    elif priority == "closest":
        w["distance"] += 0.15
        w["price"] -= 0.10

    # clamp and renormalize
    for k in w:
        w[k] = max(0.0, w[k])
    s = sum(w.values())
    if s == 0:
        return {"price": 0.5, "distance": 0.5, "amenity": 0.0, "brand": 0.0, "urgency": 0.0}
    return {k: v / s for k, v in w.items()}


def build_reason(row: dict, q: Query, cohort_min_price: float, cohort_min_dist: float) -> str:
    reasons = []
    if abs(row["price"] - cohort_min_price) < 1e-9:
        reasons.append(f"Cheapest within {q.max_distance:.0f} mi")
    if abs(row["distance"] - cohort_min_dist) < 1e-9:
        reasons.append("Closest option")
    if q.mode == "budget" and row["price"] <= q.scale:
        reasons.append(f"Within budget (${q.scale:.2f}/gal)")
    if q.brand and row["brand_match"]:
        reasons.append("Matches preferred brand")
    if q.mode == "emergency" and q.scale >= 0.7 and row["distance"] <= min(q.max_distance, cohort_min_dist + 1.0):
        reasons.append("Good when urgency is high")
    if not reasons:
        reasons.append("Good balance of price + distance")
    return " | ".join(reasons)


def rank_stations(df: pd.DataFrame, q: Query, top_k: int = 10) -> pd.DataFrame:
    out = df.copy()

    # Basic parsing + validation
    out["price"] = out["price"].apply(parse_price)

    # Drop stations missing coordinates
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    out = out.dropna(subset=["latitude", "longitude"]).copy()

    # Real distance (Haversine)
    out["distance"] = out.apply(
        lambda r: haversine_miles(q.user_lat, q.user_lon, float(r["latitude"]), float(r["longitude"])),
        axis=1
    )

    # Optional brand match
    out["brand_match"] = False
    if q.brand:
        b = q.brand.strip().lower()
        out["brand_match"] = out["name"].astype(str).str.lower().str.contains(re.escape(b))

    # FILTERS
    out = out[out["distance"] <= q.max_distance].copy()
    if q.brand:
        # Brand is a hard filter when provided.
        out = out[out["brand_match"]].copy()
    if q.mode == "budget":
        # In budget mode, scale means max acceptable price per gallon (hard filter).
        out = out[out["price"] <= q.scale].copy()

    if len(out) == 0:
        return out

    # Keep one row per station/location to avoid repeated recommendations.
    # If duplicates exist, prefer lower price then shorter distance.
    out = out.sort_values(["price", "distance"], ascending=[True, True]).drop_duplicates(
        subset=["name", "address"],
        keep="first",
    ).copy()

    # Normalize for scoring
    out["norm_price"] = normalize(out["price"].tolist())
    out["norm_dist"] = normalize(out["distance"].tolist())

    w = weights_for(q.mode, q.priority)

    # Mode-aware scale behavior:
    # - emergency: scale is urgency 0..1
    # - budget: scale is $/gal budget, no urgency term
    # - comfort: scale controls amenity/brand influence (0..1)
    emergency_urgency = q.scale if q.mode == "emergency" else 0.0
    comfort_scale = q.scale if q.mode == "comfort" else 0.5

    # urgency penalty: penalize farther stations superlinearly when urgency is high
    out["urgency_penalty"] = emergency_urgency * (out["norm_dist"] ** 2)

    # Comfort mode: simple amenity proxy from name (same as before)
    def amenity_proxy(name: str) -> float:
        n = str(name).lower()
        score = 0.0
        if "7-eleven" in n or "chevron" in n or "shell" in n:
            score += 1.0
        if "costco" in n:
            score += 0.5
        return score

    out["amenity_proxy"] = out["name"].apply(amenity_proxy)
    out["norm_amenity"] = normalize(out["amenity_proxy"].tolist())
    out["amenity_bonus"] = -0.10 * out["norm_amenity"]

    out["brand_bonus"] = 0.0
    if q.brand:
        out["brand_bonus"] = out["brand_match"].apply(lambda x: -0.07 if x else 0.0)

    amenity_multiplier = (0.5 + comfort_scale) if q.mode == "comfort" else 1.0
    brand_multiplier = (0.5 + comfort_scale) if q.mode == "comfort" else 1.0

    out["score"] = (
        w["price"] * out["norm_price"]
        + w["distance"] * out["norm_dist"]
        + w["urgency"] * out["urgency_penalty"]
        + w["amenity"] * amenity_multiplier * out["amenity_bonus"]
        + w["brand"] * brand_multiplier * out["brand_bonus"]
    )

    if q.priority == "cheapest":
        # Price-first ranking: score and distance act as tie-breakers.
        out = out.sort_values(["price", "score", "distance"], ascending=[True, True, True]).head(top_k).copy()
    elif q.priority == "closest":
        # Distance-first ranking: score and price act as tie-breakers.
        out = out.sort_values(["distance", "score", "price"], ascending=[True, True, True]).head(top_k).copy()
    else:
        out = out.sort_values("score", ascending=True).head(top_k).copy()

    cohort_min_price = out["price"].min()
    cohort_min_dist = out["distance"].min()
    out["why"] = out.apply(lambda r: build_reason(r.to_dict(), q, cohort_min_price, cohort_min_dist), axis=1)
    return out


def print_results(ranked: pd.DataFrame, q: Query) -> None:
    print("\n=== Fuel Advisor: Retrieval + Ranking Demo ===")
    print(f"User location: ({q.user_lat:.6f}, {q.user_lon:.6f})")
    if q.mode == "budget":
        scale_label = f"Scale (Budget): ${q.scale:.2f}/gal"
    elif q.mode == "comfort":
        scale_label = f"Scale (Comfort): {q.scale:.2f}"
    else:
        scale_label = f"Scale (Urgency): {q.scale:.2f}"
    print(
        f"Mode: {q.mode} | {scale_label} | Max Distance: {q.max_distance:.1f} mi | Priority: {q.priority}"
        + (f" | Brand: {q.brand}" if q.brand else "")
    )
    print("Distance note: straight-line miles via Haversine (not driving distance).\n")

    if len(ranked) == 0:
        print("No stations matched your filters (try increasing max distance or removing brand).")
        return

    # Defensive dedupe/sanitize at render time to avoid repeated console rows
    # when source rows differ only by hidden control characters/spacing.
    display = ranked.copy()
    for col in ["name", "address", "why"]:
        if col in display.columns:
            display[col] = (
                display[col]
                .astype(str)
                .str.replace(r"[\x00-\x1F\x7F]", "", regex=True)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
    display["distance_display"] = display["distance"].round(1)
    display["price_display"] = display["price"].round(2)
    display = display.drop_duplicates(
        subset=["name", "address", "distance_display", "price_display"],
        keep="first",
    ).copy()

    for i, row in enumerate(display.itertuples(index=False), start=1):
        print(f"{i:>2}. {row.name} - {row.distance:.1f} mi - ${row.price:.2f}")
        print(f"    Why: {row.why}")
        print(f"    Addr: {row.address}")

    print("\n(Showing top results only.)\n")


def _parse_location_arg(location: Optional[str]) -> Optional[Tuple[float, float]]:
    """Accepts 'lat,lon' (or 'lat lon') and returns (lat, lon)."""
    if not location:
        return None
    s = location.strip()
    # allow comma or whitespace
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
    else:
        parts = s.split()
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
        return lat, lon
    except ValueError:
        return None


def _build_query(
    *,
    user_lat: float,
    user_lon: float,
    mode: str,
    scale: Optional[float],
    max_distance: float,
    priority: str,
    brand: Optional[str],
) -> Query:
    mode = str(mode).strip().lower()
    priority = str(priority).strip().lower()
    if mode not in {"emergency", "budget", "comfort"}:
        raise SystemExit('Invalid mode. Use one of: "emergency", "budget", "comfort".')
    if priority not in {"cheapest", "closest", "balanced"}:
        raise SystemExit('Invalid priority. Use one of: "cheapest", "closest", "balanced".')

    user_lat = float(user_lat)
    user_lon = float(user_lon)
    if not (-90.0 <= user_lat <= 90.0):
        raise SystemExit("Latitude must be in range [-90, 90].")
    if not (-180.0 <= user_lon <= 180.0):
        raise SystemExit("Longitude must be in range [-180, 180].")

    if scale is None:
        if mode == "budget":
            scale = 5.0
        elif mode == "comfort":
            scale = 0.5
        else:
            scale = 0.7
    scale = float(scale)
    if mode == "budget":
        scale = max(0.1, scale)
    else:
        scale = max(0.0, min(1.0, scale))

    clean_brand = str(brand).strip() if brand is not None else ""
    return Query(
        user_lat=user_lat,
        user_lon=user_lon,
        mode=mode,
        scale=scale,
        max_distance=max(0.1, float(max_distance)),
        priority=priority,
        brand=(clean_brand if clean_brand else None),
    )


def _load_query_from_json(path: str, default_csv: str, default_top: int) -> Tuple[Query, str, int]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"JSON file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {path}: {e}")

    if not isinstance(payload, dict):
        raise SystemExit("JSON root must be an object.")

    loc = _parse_location_arg(str(payload["location"])) if "location" in payload else None
    if loc is not None:
        user_lat, user_lon = loc
    elif "user_lat" in payload and "user_lon" in payload:
        user_lat, user_lon = payload["user_lat"], payload["user_lon"]
    elif "lat" in payload and "lon" in payload:
        user_lat, user_lon = payload["lat"], payload["lon"]
    else:
        raise SystemExit(
            'JSON must include either "location" ("lat,lon"), '
            '"user_lat"+"user_lon", or "lat"+"lon".'
        )

    query = _build_query(
        user_lat=float(user_lat),
        user_lon=float(user_lon),
        mode=payload.get("mode", "emergency"),
        scale=payload.get("scale", payload.get("urgency")),
        max_distance=payload.get("max_distance", 6.0),
        priority=payload.get("priority", "balanced"),
        brand=payload.get("brand"),
    )
    csv_path = str(payload.get("csv", default_csv))
    top_k = int(payload.get("top", default_top))
    if top_k < 1:
        raise SystemExit("Top must be >= 1.")
    return query, csv_path, top_k


def main():
    ap = argparse.ArgumentParser(description="Fuel Advisor terminal ranking demo (with coordinates)")
    ap.add_argument("--csv", default=CSV_DEFAULT, help=f"Path to stations CSV (default: {CSV_DEFAULT})")
    ap.add_argument(
        "--query-json",
        default=None,
        help="Path to JSON file with query values (location, mode, scale, max_distance, priority, brand, top, csv).",
    )

    # Either --location "lat,lon" OR --lat/--lon
    ap.add_argument("--location", default=None, help='User location as "lat,lon" e.g. "33.8670,-117.9981"')
    ap.add_argument("--lat", type=float, default=None, help="User latitude (if not using --location)")
    ap.add_argument("--lon", type=float, default=None, help="User longitude (if not using --location)")

    ap.add_argument("--mode", choices=["emergency", "budget", "comfort"], default="emergency")
    ap.add_argument("--scale", type=float, default=None, help="Mode-aware scale. emergency/comfort: 0..1, budget: $/gal")
    ap.add_argument("--urgency", type=float, default=None, help="Legacy alias for --scale (deprecated)")
    ap.add_argument("--max-distance", type=float, default=6.0, help="Max distance in miles")
    ap.add_argument("--priority", choices=["cheapest", "closest", "balanced"], default="balanced")
    ap.add_argument("--brand", default=None, help='Optional brand filter, e.g. "Arco"')
    ap.add_argument("--top", type=int, default=10, help="How many results to display")
    args = ap.parse_args()

    if args.query_json:
        q, csv_path, top_k = _load_query_from_json(args.query_json, args.csv, args.top)
    else:
        loc = _parse_location_arg(args.location)
        if loc is not None:
            user_lat, user_lon = loc
        else:
            if args.lat is None or args.lon is None:
                raise SystemExit('Provide either --location "lat,lon" OR both --lat and --lon.')
            user_lat, user_lon = float(args.lat), float(args.lon)
        q = _build_query(
            user_lat=user_lat,
            user_lon=user_lon,
            mode=args.mode,
            scale=(args.scale if args.scale is not None else args.urgency),
            max_distance=args.max_distance,
            priority=args.priority,
            brand=args.brand,
        )
        csv_path = args.csv
        top_k = int(args.top)
        if top_k < 1:
            raise SystemExit("Top must be >= 1.")

    df = pd.read_csv(csv_path)
    for col in ["name", "address", "price", "latitude", "longitude"]:
        if col not in df.columns:
            raise SystemExit(f"CSV missing required column: {col}")

    ranked = rank_stations(df, q, top_k=top_k)
    print_results(ranked, q)


if __name__ == "__main__":
    main()
