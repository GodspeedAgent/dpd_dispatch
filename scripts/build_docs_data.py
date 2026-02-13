#!/usr/bin/env python3
"""Generate static JSON artifacts for GitHub Pages under /docs.

This script is meant to be run manually (or later via CI). It fetches data
from Dallas OpenData via Socrata and writes JSON snapshots that the static
frontend can render.

Current outputs:
- docs/data/active_calls_snapshot.json
- docs/data/references.json
- docs/data/beat_zip_reference.json (only when requested via env vars)
- docs/data/zip_beat_reference.json (only when requested via env vars)
- docs/data/historical_snapshot.json (only when requested via env vars)
- docs/data/historical_snapshot.geojson (only when requested via env vars)
- docs/data/beats/<beat>.json (only when requested via env vars)

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


def _get_beats_for_zip(
    *,
    zip_code: str,
    days: int = 365,
    min_pct: float = 10.0,
    top_beats_per_zip: int = 10,
) -> List[str]:
    """Infer likely beats for a ZIP using historical incidents."""
    from datetime import date, timedelta

    app_token = os.getenv("DALLAS_APP_TOKEN")
    client = DallasIncidentsClient(preset="police_incidents", app_token=app_token)

    end = date.today()
    start = end - timedelta(days=days)

    where = (
        f"date1 >= '{start.isoformat()}T00:00:00.000' AND "
        f"date1 <= '{end.isoformat()}T23:59:59.999' AND "
        f"zip_code = '{zip_code}' AND beat IS NOT NULL"
    )

    total_rows = client.client.get(client.config.dataset_id, select="count(1) as n", where=where, limit=1)
    total = int(total_rows[0].get("n", 0)) if total_rows else 0
    if total <= 0:
        return []

    rows = client.client.get(
        client.config.dataset_id,
        select="beat, count(1) as n",
        where=where,
        group="beat",
        order="n DESC",
        limit=top_beats_per_zip,
    )

    beats = []
    for r in rows:
        beat = str(r.get("beat") or "").strip()
        n = int(r.get("n", 0) or 0)
        if not beat:
            continue
        pct = n / total * 100.0
        if pct + 1e-9 < min_pct:
            continue
        beats.append(beat)

    return beats


def build_active_calls_snapshot(limit: int = 500, beats: List[str] | None = None, zip_code: str | None = None) -> Dict[str, Any]:
    app_token = os.getenv("DALLAS_APP_TOKEN")

    # Uses preset dataset_id 9fxf-t2tr (active calls all divisions)
    client = DallasIncidentsClient(preset="active_calls_all", app_token=app_token)

    q = IncidentQuery(limit=limit)
    resp = client.get_incidents(q)

    calls_raw: List[Dict[str, Any]] = resp.data if hasattr(resp, "data") else resp  # type: ignore

    # Optional: infer beats from ZIP for active calls filtering (heuristic)
    inferred_beats: List[str] = []
    if zip_code:
        inferred_beats = _get_beats_for_zip(zip_code=zip_code, days=365, min_pct=10.0)

    beats_set = set([b.strip() for b in (beats or []) if b and b.strip()])
    if inferred_beats:
        beats_set = set(inferred_beats)

    calls: List[Dict[str, Any]] = []
    by_beat: Dict[str, int] = {}

    for row in calls_raw:
        beat = str(_safe_get(row, "beat") or "").strip()
        if beats_set and beat not in beats_set:
            continue

        nature = _safe_get(row, "nature_of_call", "nature")
        block = _safe_get(row, "block")
        location = _safe_get(row, "location")
        unit = _safe_get(row, "unit_number", "unit")

        address = " ".join([p for p in [str(block).strip() if block else None, str(location).strip() if location else None] if p])

        nature_str = str(nature) if nature is not None else ""
        nature_code = None
        nature_desc = None
        if " - " in nature_str:
            a, b = nature_str.split(" - ", 1)
            nature_code = a.strip() or None
            nature_desc = b.strip() or None

        calls.append(
            {
                "unit": unit,
                "nature": nature,
                "nature_code": nature_code,
                "nature_desc": nature_desc,
                "beat": beat or None,
                "address": address or None,
                "unit_number": unit,
                "block": block,
                "location": location,
                "nature_of_call": nature,
            }
        )

        if beat:
            by_beat[beat] = by_beat.get(beat, 0) + 1

    by_region_beat = [
        {"region": None, "beat": beat, "count": count}
        for beat, count in sorted(by_beat.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    note = "Active Calls dataset does not include timestamps; generated_at is when the snapshot was built."
    if zip_code:
        note += f" Filtered heuristically to beats most associated with ZIP {zip_code} (365d, >=10% threshold)."
    elif beats_set:
        note += " Filtered to selected beats."

    return {
        "summary": {
            "generated_at": utc_now_iso(),
            "total_calls": len(calls),
            "dataset": "active_calls_all",
            "dataset_id": "9fxf-t2tr",
            "filter": {
                "beats": sorted(list(beats_set)) if beats_set else None,
                "zip": zip_code,
            },
            "note": note,
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

    # Active calls snapshot (optional beat/zip filtering)
    active_zip = os.getenv("ACTIVE_ZIP") or None
    active_beats = None
    if os.getenv("ACTIVE_BEATS"):
        active_beats = [b.strip() for b in os.getenv("ACTIVE_BEATS", "").split(",") if b.strip()]

    active = build_active_calls_snapshot(beats=active_beats, zip_code=active_zip)
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

    def build_zip_beat_reference(days: int = 365, min_pct: float = 10.0, top_beats_per_zip: int = 10) -> Dict[str, Any]:
        """Infer ZIP → beat mapping from historical incident records.

        For each ZIP, include beats that account for >= min_pct of incidents in that ZIP.
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

        # Aggregate counts by (zip, beat)
        offset = 0
        limit = 50000
        rows: List[Dict[str, Any]] = []
        while True:
            params = {
                "select": "zip_code, beat, count(1) as n",
                "where": where,
                "group": "zip_code, beat",
                "order": "zip_code, n DESC",
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

        zip_totals: Dict[str, int] = {}
        zip_beats: Dict[str, List[Dict[str, Any]]] = {}

        for r in rows:
            zipc = str(r.get("zip_code") or "").strip()
            beat = str(r.get("beat") or "").strip()
            try:
                n = int(r.get("n") or 0)
            except Exception:
                n = 0
            if not zipc or not beat:
                continue
            zip_totals[zipc] = zip_totals.get(zipc, 0) + n
            zip_beats.setdefault(zipc, []).append({"beat": beat, "count": n})

        out_zips = []
        for zipc, blist in zip_beats.items():
            total = zip_totals.get(zipc, 0)
            if total <= 0:
                continue
            blist_sorted = sorted(blist, key=lambda x: (-x["count"], x["beat"]))
            beats_out = []
            for item in blist_sorted[:top_beats_per_zip]:
                pct = item["count"] / total * 100.0
                if pct + 1e-9 < min_pct:
                    continue
                beats_out.append({**item, "pct": round(pct, 1)})
            out_zips.append({"zip": zipc, "total": total, "beats": beats_out})

        out_zips.sort(key=lambda x: x["zip"])

        return {
            "summary": {
                "generated_at": utc_now_iso(),
                "dataset": "police_incidents",
                "dataset_id": "qv6i-rri7",
                "window_days": days,
                "min_pct": min_pct,
                "note": "Inferred from incident records; ZIPs and beats overlap imperfectly; use as a heuristic.",
            },
            "zips": out_zips,
        }

    # ZIP→beat inference is generated ONLY when explicitly requested.
    # Set ZIPBEAT_ENABLE=1. Optional: ZIPBEAT_DAYS=365, ZIPBEAT_MINPCT=10.
    if os.getenv("ZIPBEAT_ENABLE") == "1":
        days = int(os.getenv("ZIPBEAT_DAYS", "365"))
        min_pct = float(os.getenv("ZIPBEAT_MINPCT", "10"))
        zipbeat = build_zip_beat_reference(days=days, min_pct=min_pct)
        zipbeat_path = DOCS_DATA / "zip_beat_reference.json"
        zipbeat_path.write_text(json.dumps(zipbeat, indent=2), encoding="utf-8")
        print(f"Wrote {zipbeat_path}")

    def build_beat_profile(beat: str, windows: List[int] = [7, 30, 90], top_n: int = 15) -> Dict[str, Any]:
        """Build a multi-window profile for a single beat."""
        from datetime import date, timedelta

        app_token = os.getenv("DALLAS_APP_TOKEN")
        client = DallasIncidentsClient(preset="police_incidents", app_token=app_token)
        dataset_id = client.config.dataset_id

        out: Dict[str, Any] = {
            "summary": {
                "generated_at": utc_now_iso(),
                "dataset": "police_incidents",
                "dataset_id": dataset_id,
                "beat": beat,
                "windows": windows,
                "note": "Aggregations inferred from Police Incidents; counts depend on dataset freshness.",
            },
            "windows": {},
        }

        today = date.today()

        for days in windows:
            end = today
            start = end - timedelta(days=days)
            where = (
                f"date1 >= '{start.isoformat()}T00:00:00.000' AND "
                f"date1 <= '{end.isoformat()}T23:59:59.999' AND "
                f"beat = '{beat}'"
            )

            # Total incidents
            total_rows = client.client.get(dataset_id, select="count(1) as n", where=where, limit=1)
            total = int(total_rows[0].get("n", 0)) if total_rows else 0

            def _humanize_offense(s: str | None) -> str | None:
                if not s:
                    return s
                t = str(s).strip()
                if t == "BMV":
                    return "Burglary of Motor Vehicle"
                t = t.replace("(ATT)", "(Attempt)")
                t = t.replace(" - ATTEMPT", " (Attempt)")
                t = t.replace(" - ", ": ")
                # Title-case, but keep a few acronyms
                keep = {"DWI", "UCR", "NIBRS", "PC"}
                out = []
                for w in t.split():
                    up = w.upper()
                    if up in keep:
                        out.append(up)
                    else:
                        out.append(w[:1].upper() + w[1:].lower())
                return " ".join(out)

            # Top offenses
            top_off = client.client.get(
                dataset_id,
                select="offincident, count(1) as n",
                where=where,
                group="offincident",
                order="n DESC",
                limit=top_n,
            )
            top_offenses = [
                {
                    "offincident": r.get("offincident"),
                    "offincident_label": _humanize_offense(r.get("offincident")),
                    "count": int(r.get("n", 0)),
                }
                for r in top_off
            ]

            # Top ZIPs
            top_zip = client.client.get(
                dataset_id,
                select="zip_code, count(1) as n",
                where=where + " AND zip_code IS NOT NULL",
                group="zip_code",
                order="n DESC",
                limit=top_n,
            )
            top_zips = []
            for r in top_zip:
                n = int(r.get("n", 0))
                pct = (n / total * 100.0) if total else 0.0
                top_zips.append({"zip": r.get("zip_code"), "count": n, "pct": round(pct, 1)})

            # Daily counts (dataset stores date1 as text-like timestamp; grouping by date1 works)
            daily = client.client.get(
                dataset_id,
                select="date1, count(1) as n",
                where=where,
                group="date1",
                order="date1 ASC",
                limit=5000,
            )
            daily_counts = [{"day": r.get("date1"), "count": int(r.get("n", 0))} for r in daily]

            def build_narrative_90d() -> Dict[str, Any] | None:
                """Build an analysis-style narrative.

                Per your spec, we only generate this for the 90-day window.

                Includes:
                - total + rate
                - delta vs previous 90-day window
                - outlier/spike days + what drove them
                - offense mix shift vs previous window
                - time patterns (watch + day-of-week)
                - NIBRS framing (crimeagainst / type / group)
                """

                if days != 90:
                    return None

                if total == 0:
                    return {
                        "headline": f"Beat {beat}: no incidents in the last 90 days",
                        "text": "No incidents were returned for this window.",
                        "bullets": [],
                    }

                # --- Baseline comparison: previous 90 days ---
                prev_end = start
                prev_start = prev_end - timedelta(days=90)
                prev_where = (
                    f"date1 >= '{prev_start.isoformat()}T00:00:00.000' AND "
                    f"date1 <= '{prev_end.isoformat()}T23:59:59.999' AND "
                    f"beat = '{beat}'"
                )
                prev_total_rows = client.client.get(dataset_id, select="count(1) as n", where=prev_where, limit=1)
                prev_total = int(prev_total_rows[0].get("n", 0)) if prev_total_rows else 0

                rate = round(total / 90.0, 2)
                prev_rate = round(prev_total / 90.0, 2) if prev_total else 0.0
                delta = total - prev_total
                pct = round((delta / prev_total * 100.0), 1) if prev_total else None

                # --- Spike days (top 3) ---
                spike_days = sorted(daily_counts, key=lambda x: -x["count"])[:3]
                spike_details = []
                for sd in spike_days:
                    day = sd.get("day")
                    if not day:
                        continue
                    # attribute drivers by top offenses on that day
                    day_where = prev_where.replace(prev_start.isoformat(), prev_start.isoformat())  # no-op to keep formatting stable
                    day_where = (
                        f"date1 = '{day}' AND beat = '{beat}'"
                    )
                    drivers = client.client.get(
                        dataset_id,
                        select="offincident, count(1) as n",
                        where=day_where,
                        group="offincident",
                        order="n DESC",
                        limit=5,
                    )
                    spike_details.append(
                        {
                            "day": str(day)[:10],
                            "count": sd.get("count"),
                            "top_offenses": [
                                {
                                    "offincident": r.get("offincident"),
                                    "offincident_label": _humanize_offense(r.get("offincident")),
                                    "count": int(r.get("n", 0)),
                                }
                                for r in drivers
                            ],
                        }
                    )

                # --- Offense mix shift (current vs prev) ---
                # Pull a moderately-sized distribution for both windows.
                dist_limit = 250
                cur_dist = client.client.get(
                    dataset_id,
                    select="offincident, count(1) as n",
                    where=where,
                    group="offincident",
                    order="n DESC",
                    limit=dist_limit,
                )
                prev_dist = client.client.get(
                    dataset_id,
                    select="offincident, count(1) as n",
                    where=prev_where,
                    group="offincident",
                    order="n DESC",
                    limit=dist_limit,
                )
                cur_map = {r.get("offincident"): int(r.get("n", 0)) for r in cur_dist if r.get("offincident")}
                prev_map = {r.get("offincident"): int(r.get("n", 0)) for r in prev_dist if r.get("offincident")}
                keys = set(cur_map) | set(prev_map)
                movers = []
                for k in keys:
                    c = cur_map.get(k, 0)
                    p = prev_map.get(k, 0)
                    # share change (percentage points)
                    cs = (c / total * 100.0) if total else 0.0
                    ps = (p / prev_total * 100.0) if prev_total else 0.0
                    movers.append({"offincident": k, "cur": c, "prev": p, "share_pp": round(cs - ps, 2)})
                movers.sort(key=lambda x: -abs(x["share_pp"]))
                top_mix_shift = movers[:8]

                # --- Time patterns (watch + day-of-week) ---
                watch_rows = client.client.get(
                    dataset_id,
                    select="watch, count(1) as n",
                    where=where + " AND watch IS NOT NULL",
                    group="watch",
                    order="n DESC",
                    limit=50,
                )
                watch_counts = [{"watch": r.get("watch"), "count": int(r.get("n", 0))} for r in watch_rows]

                dow_rows = client.client.get(
                    dataset_id,
                    select="day1, count(1) as n",
                    where=where + " AND day1 IS NOT NULL",
                    group="day1",
                    order="n DESC",
                    limit=50,
                )
                dow_counts = [{"day": r.get("day1"), "count": int(r.get("n", 0))} for r in dow_rows]

                # --- NIBRS framing ---
                ca_rows = client.client.get(
                    dataset_id,
                    select="nibrs_crimeagainst, count(1) as n",
                    where=where + " AND nibrs_crimeagainst IS NOT NULL",
                    group="nibrs_crimeagainst",
                    order="n DESC",
                    limit=50,
                )
                crimeagainst = [{"name": r.get("nibrs_crimeagainst"), "count": int(r.get("n", 0))} for r in ca_rows]

                type_rows = client.client.get(
                    dataset_id,
                    select="nibrs_type, count(1) as n",
                    where=where + " AND nibrs_type IS NOT NULL",
                    group="nibrs_type",
                    order="n DESC",
                    limit=50,
                )
                nibrs_type = [{"name": r.get("nibrs_type"), "count": int(r.get("n", 0))} for r in type_rows]

                group_rows = client.client.get(
                    dataset_id,
                    select="nibrs_group, count(1) as n",
                    where=where + " AND nibrs_group IS NOT NULL",
                    group="nibrs_group",
                    order="n DESC",
                    limit=50,
                )
                nibrs_group = [{"name": r.get("nibrs_group"), "count": int(r.get("n", 0))} for r in group_rows]

                # --- Bullets + narrative text ---
                bullets: List[str] = []

                top_off1 = top_offenses[0] if top_offenses else None
                if top_off1:
                    bullets.append(f"Top offense driver: {top_off1.get('offincident_label') or top_off1['offincident']} ({top_off1['count']})")

                if prev_total:
                    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
                    if pct is None:
                        bullets.append(f"Versus prior 90d: {direction} by {abs(delta)} incidents")
                    else:
                        bullets.append(f"Versus prior 90d: {direction} by {abs(delta)} incidents ({pct:+}%)")
                else:
                    bullets.append("No prior-window baseline available (previous period returned 0)")

                bullets.append(f"Pace: {rate} incidents/day (prev {prev_rate}/day)")

                if spike_details:
                    bullets.append(
                        "Spike days: " + ", ".join([f"{s['day']} ({s['count']})" for s in spike_details])
                    )

                # Mix shift: highlight top 2 movers
                if top_mix_shift:
                    m = top_mix_shift[0]
                    bullets.append(f"Largest mix shift: {m['offincident']} ({m['share_pp']} pp)")

                # Compose paragraph
                mix3 = ", ".join([f"{x['offincident']} ({x['count']})" for x in top_offenses[:3]]) if top_offenses else "—"
                time1 = watch_counts[0]["watch"] if watch_counts else None
                dow1 = dow_counts[0]["day"] if dow_counts else None

                baseline_line = (
                    f"Compared with the prior 90-day window, activity is {'higher' if delta>0 else 'lower' if delta<0 else 'about the same'} "
                    f"({delta:+} incidents" + (f", {pct:+}%" if pct is not None else "") + ")."
                )

                spike_line = ""
                if spike_details:
                    drivers = []
                    for s in spike_details[:2]:
                        if s.get('top_offenses'):
                            d0 = s['top_offenses'][0]
                            drivers.append(f"{s['day']} was led by {(d0.get('offincident_label') or d0['offincident'])} ({d0['count']})")
                    if drivers:
                        spike_line = " Spike attribution: " + "; ".join(drivers) + "."

                time_line = ""
                if time1 or dow1:
                    parts = []
                    if time1:
                        parts.append(f"most common watch: {time1}")
                    if dow1:
                        parts.append(f"most common weekday label: {dow1}")
                    time_line = " Time pattern: " + ", ".join(parts) + "."

                nibrs_line = ""
                if crimeagainst:
                    ca0 = crimeagainst[0]
                    nibrs_line = f" NIBRS framing: mostly {ca0['name']} ({ca0['count']})."

                text = (
                    f"Beat {beat} logged {total} incidents over the last 90 days ({rate}/day). "
                    f"Top offense types were: {mix3}. {baseline_line}{spike_line}{time_line}{nibrs_line}"
                )

                return {
                    "headline": f"Beat {beat} — 90-day analysis",
                    "text": text,
                    "bullets": bullets,
                    "baseline": {
                        "current_total": total,
                        "previous_total": prev_total,
                        "delta": delta,
                        "pct": pct,
                        "current_rate_per_day": rate,
                        "previous_rate_per_day": prev_rate,
                    },
                    "spikes": spike_details,
                    "mix_shift": top_mix_shift,
                    "time_patterns": {"watch": watch_counts, "day_of_week": dow_counts},
                    "nibrs": {"crimeagainst": crimeagainst, "type": nibrs_type, "group": nibrs_group},
                }

            narrative = build_narrative_90d()

            out["windows"][str(days)] = {
                "days": days,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "total_incidents": total,
                "top_offenses": top_offenses,
                "top_zips": top_zips,
                "daily_counts": daily_counts,
                "narrative": narrative,
            }

        return out

    # Beat profile is generated ONLY when explicitly requested.
    # Set BEATPROFILE_ENABLE=1 and BEATPROFILE_BEAT=<beat>. Optional: BEATPROFILE_TOP=15.
    if os.getenv("BEATPROFILE_ENABLE") == "1":
        beat = os.getenv("BEATPROFILE_BEAT")
        if not beat:
            raise SystemExit("BEATPROFILE_ENABLE=1 requires BEATPROFILE_BEAT")
        top_n = int(os.getenv("BEATPROFILE_TOP", "15"))
        profile = build_beat_profile(str(beat).strip(), windows=[7, 30, 90], top_n=top_n)
        beats_dir = DOCS_DATA / "beats"
        beats_dir.mkdir(parents=True, exist_ok=True)
        out_path = beats_dir / f"{str(beat).strip()}.json"
        out_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")

        # Pointer for the UI: most recently generated beat
        cur_path = DOCS_DATA / "beat_profile_current.json"
        cur_path.write_text(
            json.dumps({"beat": str(beat).strip(), "generated_at": utc_now_iso()}, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {cur_path}")

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
