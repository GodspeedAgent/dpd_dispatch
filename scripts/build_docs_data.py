#!/usr/bin/env python3
"""Generate static JSON artifacts for GitHub Pages under /docs.

This script is meant to be run manually (or later via CI). It fetches data
from Dallas OpenData via Socrata and writes JSON snapshots that the static
frontend can render.

Current outputs:
- docs/data/active_calls_snapshot.json
- docs/data/references.json
- docs/data/beat_zip_reference.json (only when requested via env vars)
- docs/data/historical_snapshot.json (only when requested via env vars)
- docs/data/historical_snapshot.geojson (only when requested via env vars)

Env:
- DALLAS_APP_TOKEN: optional Socrata app token
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path when running as a script
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dallas_incidents import DallasIncidentsClient, IncidentQuery


DOCS_DATA = ROOT / "docs" / "data"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_get(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def build_active_calls_snapshot(limit: int = 500) -> Dict[str, Any]:
    app_token = os.getenv("DALLAS_APP_TOKEN")

    # Uses preset dataset_id 9fxf-t2tr (active calls all divisions)
    client = DallasIncidentsClient(preset="active_calls_all", app_token=app_token)

    q = IncidentQuery(limit=limit)
    resp = client.get_incidents(q)

    calls_raw: List[Dict[str, Any]] = resp.data if hasattr(resp, "data") else resp  # type: ignore

    calls: List[Dict[str, Any]] = []
    by_beat: Dict[str, int] = {}

    for row in calls_raw:
        beat = str(_safe_get(row, "beat") or "").strip()
        nature = _safe_get(row, "nature_of_call", "nature")
        block = _safe_get(row, "block")
        location = _safe_get(row, "location")
        unit = _safe_get(row, "unit_number", "unit")

        address = " ".join([p for p in [str(block).strip() if block else None, str(location).strip() if location else None] if p])

        calls.append(
            {
                # Frontend expects these keys
                "call_number": unit,  # dataset does not expose call #; unit is the best available identifier
                "nature": nature,
                "beat": beat or None,
                "address": address or None,
                "time": None,  # active calls dataset lacks timestamps

                # Keep raw-ish fields for debugging
                "unit_number": unit,
                "block": block,
                "location": location,
                "nature_of_call": nature,
            }
        )

        if beat:
            by_beat[beat] = by_beat.get(beat, 0) + 1

    # Region mapping isn't defined in the dataset; we keep region as null for now.
    by_region_beat = [
        {"region": None, "beat": beat, "count": count}
        for beat, count in sorted(by_beat.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    return {
        "summary": {
            "generated_at": utc_now_iso(),
            "total_calls": len(calls),
            "dataset": "active_calls_all",
            "dataset_id": "9fxf-t2tr",
            "note": "Active Calls dataset does not include timestamps; generated_at is when the snapshot was built.",
        },
        "by_region_beat": by_region_beat,
        "calls": calls,
    }


def build_references() -> Dict[str, Any]:
    # Import from repo mappings (not live dataset introspection)
    from dallas_incidents.models import DatasetPreset
    from dallas_incidents.offense_categories import OFFENSE_KEYWORDS, OFFENSE_TYPE_MAP

    presets = [
        {
            "name": "police_incidents",
            "dataset_id": DatasetPreset.POLICE_INCIDENTS.value,
            "kind": "historical",
            "notes": "2014–present; has timestamps, coordinates, NIBRS/UCR, etc.",
        },
        {
            "name": "active_calls_all",
            "dataset_id": DatasetPreset.ACTIVE_CALLS_ALL.value,
            "kind": "active",
            "notes": "Real-time citywide active calls; no timestamps/coords.",
        },
        {
            "name": "active_calls_northeast",
            "dataset_id": DatasetPreset.ACTIVE_CALLS_NORTHEAST.value,
            "kind": "active",
            "notes": "Real-time active calls (Northeast division); no timestamps/coords.",
        },
    ]

    offense_categories = []
    offense_type_map = []

    # OFFENSE_TYPE_MAP keys are OffenseCategory enums
    for cat, types in OFFENSE_TYPE_MAP.items():
        keywords = sorted(list(OFFENSE_KEYWORDS.get(cat, set())))
        offense_categories.append(
            {
                "category": cat.value if hasattr(cat, "value") else str(cat),
                "keyword_count": len(keywords),
                "type_count": len(types),
            }
        )
        offense_type_map.append(
            {
                "category": cat.value if hasattr(cat, "value") else str(cat),
                "keywords": keywords,
                "offense_types": types,
            }
        )

    offense_categories.sort(key=lambda x: x["category"])
    offense_type_map.sort(key=lambda x: x["category"])

    return {
        "generated_at": utc_now_iso(),
        "presets": presets,
        "offense_categories": offense_categories,
        "offense_type_map": offense_type_map,
    }


def build_historical_snapshot(
    *,
    title: str,
    days: int,
    beat: str | None = None,
    offense_keyword: str | None = None,
    offense_category: str | None = None,
    extra_where: str | None = None,
    limit: int = 5000,
) -> Dict[str, Any]:
    """Build a historical snapshot for the last N days.

    Uses the Police Incidents dataset (qv6i-rri7).

    No hardcoded phrase→query mappings are used. The caller must pass query
    parameters explicitly (keyword/category/extra_where), which we can construct
    on-the-fly from a user request.
    """

    from datetime import date, timedelta

    app_token = os.getenv("DALLAS_APP_TOKEN")

    client = DallasIncidentsClient(preset="police_incidents", app_token=app_token)

    end = date.today()
    start = end - timedelta(days=days)

    from dallas_incidents.models import DateRange

    q = IncidentQuery(
        beats=[beat] if beat else None,
        date_range=DateRange(start=start, end=end),
        limit=limit,
        order_by="date1 DESC",
        select_fields=[
            "date1",
            "incidentnum",
            "offincident",
            "ucr_offense",
            "nibrs_code",
            "nibrs_crime",
            "beat",
            "division",
            "incident_address",
        ],
        offense_keyword=offense_keyword,
        offense_category=offense_category,
        extra_where=extra_where,
    )

    resp = client.get_incidents(q)
    rows: List[Dict[str, Any]] = resp.data

    # Aggregates
    by_beat: Dict[str, int] = {}
    by_offincident: Dict[str, int] = {}

    for r in rows:
        b = str(r.get("beat") or "").strip()
        off = str(r.get("offincident") or "").strip()
        if b:
            by_beat[b] = by_beat.get(b, 0) + 1
        if off:
            by_offincident[off] = by_offincident.get(off, 0) + 1

    top_beats = [
        {"beat": k, "count": v}
        for k, v in sorted(by_beat.items(), key=lambda kv: (-kv[1], kv[0]))
    ][:50]

    top_offenses = [
        {"offincident": k, "count": v}
        for k, v in sorted(by_offincident.items(), key=lambda kv: (-kv[1], kv[0]))
    ][:50]

    simplified = []
    for r in rows[:200]:
        simplified.append(
            {
                "date1": r.get("date1"),
                "incidentnum": r.get("incidentnum"),
                "offincident": r.get("offincident"),
                "ucr_offense": r.get("ucr_offense"),
                "nibrs_code": r.get("nibrs_code"),
                "nibrs_crime": r.get("nibrs_crime"),
                "beat": r.get("beat"),
                "division": r.get("division"),
                "incident_address": r.get("incident_address"),
            }
        )

    return {
        "summary": {
            "generated_at": utc_now_iso(),
            "dataset": "police_incidents",
            "dataset_id": "qv6i-rri7",
            "title": title,
            "days": days,
            "beat": beat,
            "total_incidents": len(rows),
            "query": {
                "offense_keyword": offense_keyword,
                "offense_category": offense_category,
                "extra_where": extra_where,
            },
            "note": "Historical dataset updates daily; this snapshot is built on-demand.",
        },
        "top_beats": top_beats,
        "top_offenses": top_offenses,
        "incidents": simplified,
    }


def build_beat_zip_reference(days: int = 365, top_zips_per_beat: int = 5) -> Dict[str, Any]:
    """Infer beat → ZIP mapping from historical incident records.

    Returns a per-beat list of ZIPs ranked by incident count in the window.
    """

    from datetime import date, timedelta

    app_token = os.getenv("DALLAS_APP_TOKEN")
    client = DallasIncidentsClient(preset="police_incidents", app_token=app_token)

    end = date.today()
    start = end - timedelta(days=days)

    where = (
        f"date1 >= '{start.isoformat()}T00:00:00.000' AND "
        f"date1 <= '{end.isoformat()}T23:59:59.999' AND "
        "beat IS NOT NULL AND zip_code IS NOT NULL"
    )

    # Pull aggregated counts (beat, zip_code). Paginate to be safe.
    offset = 0
    limit = 50000
    rows: List[Dict[str, Any]] = []

    while True:
        params = {
            "select": "beat, zip_code, count(1) as n",
            "where": where,
            "group": "beat, zip_code",
            "order": "beat, n DESC",
            "limit": limit,
            "offset": offset,
        }
        batch = client.client.get(client.config.dataset_id, **params)
        if not batch:
            break
        rows.extend(batch)
        offset += limit
        if len(batch) < limit:
            break

    # Build per-beat totals and ZIP breakdowns
    beat_totals: Dict[str, int] = {}
    beat_zips: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        beat = str(r.get("beat") or "").strip()
        zipc = str(r.get("zip_code") or "").strip()
        try:
            n = int(r.get("n") or 0)
        except Exception:
            n = 0

        if not beat or not zipc:
            continue

        beat_totals[beat] = beat_totals.get(beat, 0) + n
        beat_zips.setdefault(beat, []).append({"zip": zipc, "count": n})

    # Sort and compute percentages
    beats_out = []
    for beat, zlist in beat_zips.items():
        total = beat_totals.get(beat, 0)
        zlist_sorted = sorted(zlist, key=lambda x: (-x["count"], x["zip"]))
        top = []
        for item in zlist_sorted[:top_zips_per_beat]:
            pct = (item["count"] / total * 100.0) if total else 0.0
            top.append({**item, "pct": round(pct, 1)})
        beats_out.append(
            {
                "beat": beat,
                "total": total,
                "top_zips": top,
            }
        )

    beats_out.sort(key=lambda x: x["beat"])

    return {
        "summary": {
            "generated_at": utc_now_iso(),
            "dataset": "police_incidents",
            "dataset_id": "qv6i-rri7",
            "window_days": days,
            "note": "Inferred from incident records: beats and ZIPs overlap imperfectly; use as a heuristic.",
        },
        "beats": beats_out,
    }


def main() -> None:
    DOCS_DATA.mkdir(parents=True, exist_ok=True)

    active = build_active_calls_snapshot()
    out_path = DOCS_DATA / "active_calls_snapshot.json"
    out_path.write_text(json.dumps(active, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    refs = build_references()
    refs_path = DOCS_DATA / "references.json"
    refs_path.write_text(json.dumps(refs, indent=2), encoding="utf-8")
    print(f"Wrote {refs_path}")

    # Beat→ZIP inference is generated ONLY when explicitly requested.
    # Set BEATZIP_ENABLE=1. Optional: BEATZIP_DAYS=365, BEATZIP_TOP=5.
    if os.getenv("BEATZIP_ENABLE") == "1":
        days = int(os.getenv("BEATZIP_DAYS", "365"))
        topn = int(os.getenv("BEATZIP_TOP", "5"))
        beatzip = build_beat_zip_reference(days=days, top_zips_per_beat=topn)
        beatzip_path = DOCS_DATA / "beat_zip_reference.json"
        beatzip_path.write_text(json.dumps(beatzip, indent=2), encoding="utf-8")
        print(f"Wrote {beatzip_path}")

    # Historical snapshot is generated ONLY when explicitly requested.
    # Set HISTORICAL_ENABLE=1 and provide at least one of:
    # - HISTORICAL_OFFENSE_KEYWORD
    # - HISTORICAL_OFFENSE_CATEGORY (matches OffenseCategory enum values)
    # - HISTORICAL_EXTRA_WHERE (raw SoQL, use carefully)
    if os.getenv("HISTORICAL_ENABLE") == "1":
        title = os.getenv("HISTORICAL_TITLE", "Historical query")
        days = int(os.getenv("HISTORICAL_DAYS", "30"))
        beat = os.getenv("HISTORICAL_BEAT") or None
        offense_keyword = os.getenv("HISTORICAL_OFFENSE_KEYWORD") or None
        offense_category = os.getenv("HISTORICAL_OFFENSE_CATEGORY") or None
        extra_where = os.getenv("HISTORICAL_EXTRA_WHERE") or None

        if not any([offense_keyword, offense_category, extra_where]):
            raise SystemExit(
                "HISTORICAL_ENABLE=1 requires HISTORICAL_OFFENSE_KEYWORD or "
                "HISTORICAL_OFFENSE_CATEGORY or HISTORICAL_EXTRA_WHERE"
            )

        hist = build_historical_snapshot(
            title=title,
            days=days,
            beat=beat,
            offense_keyword=offense_keyword,
            offense_category=offense_category,
            extra_where=extra_where,
        )
        hist_path = DOCS_DATA / "historical_snapshot.json"
        hist_path.write_text(json.dumps(hist, indent=2), encoding="utf-8")
        print(f"Wrote {hist_path}")

        # Optional: also emit GeoJSON for mapping in the static site
        if os.getenv("HISTORICAL_GEOJSON") == "1":
            from dallas_incidents.models import DateRange, OutputFormat
            from datetime import date, timedelta

            app_token = os.getenv("DALLAS_APP_TOKEN")
            client = DallasIncidentsClient(preset="police_incidents", app_token=app_token)

            end = date.today()
            start = end - timedelta(days=days)

            q = IncidentQuery(
                beats=[beat] if beat else None,
                date_range=DateRange(start=start, end=end),
                limit=min(5000, int(os.getenv("HISTORICAL_GEO_LIMIT", "2000"))),
                order_by="date1 DESC",
                format=OutputFormat.GEOJSON,
                offense_keyword=offense_keyword,
                offense_category=offense_category,
                extra_where=extra_where,
            )

            geo_resp = client.get_incidents(q)
            features = geo_resp.data
            fc = {
                "type": "FeatureCollection",
                "generated_at": utc_now_iso(),
                "title": title,
                "days": days,
                "beat": beat,
                "query": {
                    "offense_keyword": offense_keyword,
                    "offense_category": offense_category,
                    "extra_where": extra_where,
                },
                "features": features,
            }
            geo_path = DOCS_DATA / "historical_snapshot.geojson"
            geo_path.write_text(json.dumps(fc, indent=2), encoding="utf-8")
            print(f"Wrote {geo_path}")


if __name__ == "__main__":
    main()
