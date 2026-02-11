#!/usr/bin/env python3
"""Generate static JSON artifacts for GitHub Pages under /docs.

This script is meant to be run manually (or later via CI). It fetches data
from Dallas OpenData via Socrata and writes JSON snapshots that the static
frontend can render.

Current outputs:
- docs/data/active_calls_snapshot.json
- docs/data/references.json

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


if __name__ == "__main__":
    main()
