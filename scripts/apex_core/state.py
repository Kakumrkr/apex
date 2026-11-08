"""config.json / state.json, the scoring rubric, and tier hysteresis."""
from __future__ import annotations

import json
import os

from . import SCHEMA_VERSION
from .paths import ApexPaths, write_text

# Weighted rubric (must sum to 100). Keys are the scorecard dimension ids.
RUBRIC = {
    "core_loop": 20,
    "data_integrity": 15,
    "ux_onboarding": 15,
    "code_health": 10,
    "resilience": 10,
    "performance": 10,
    "testing": 10,
    "security": 10,
}
RUBRIC_LABELS = {
    "core_loop": "Core loop & functionality",
    "data_integrity": "Data & schema integrity",
    "ux_onboarding": "UX states & onboarding",
    "code_health": "Type safety & code health",
    "resilience": "Error handling & resilience",
    "performance": "Performance",
    "testing": "Tests & CI",
    "security": "Security & privacy",
}
BROKEN_BUILD_CAP = 4.5
SCORE_TOLERANCE = 0.15
BIG_DELTA = 1.5

# Tier floors: Tier 1 = 1.0-4.5, Tier 2 = 4.6-7.5, Tier 3 = 7.6-10.0
TIER_FLOORS = {2: 4.6, 3: 7.6}
TIER_NAMES = {
    1: "Tier 1 · Foundations (core loop, schema, type safety)",
    2: "Tier 2 · Reliability (UX states, errors, edge cases)",
    3: "Tier 3 · Market leader (differentiators, micro-delighters)",
}

DEFAULT_CONFIG = {
    "schema_version": SCHEMA_VERSION,
    "stack": [],
    "package_manager": None,
    "health_checks": [],
    "research": {"enabled": True, "refresh_days": 28},
    "tier_hysteresis": 0.3,
    "banner": True,
    "stale_audit_days": 14,
}

DEFAULT_STATE = {
    "schema_version": SCHEMA_VERSION,
    "last_audit_sha": None,
    "last_audit_date": None,
    "last_mode": None,
    "tier": None,
    "score": None,
    "history": [],
}


def load_json(path: str, default: dict) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except FileNotFoundError:
        return json.loads(json.dumps(default))
    merged = json.loads(json.dumps(default))
    merged.update(data)
    return merged


def save_json(path: str, data: dict) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_config(p: ApexPaths) -> dict:
    return load_json(p.config, DEFAULT_CONFIG)


def load_state(p: ApexPaths) -> dict:
    return load_json(p.state, DEFAULT_STATE)


def weighted_score(dimensions: dict) -> float:
    total = sum(RUBRIC.values())
    return sum(float(dimensions[k]) * w for k, w in RUBRIC.items()) / total


def raw_tier(score: float) -> int:
    if score >= TIER_FLOORS[3]:
        return 3
    if score >= TIER_FLOORS[2]:
        return 2
    return 1


def next_tier(score: float, previous: int | None, hysteresis: float = 0.3) -> int:
    """Tier with a dead-band so a project hovering at a boundary doesn't flip-flop.

    Promote into tier N only when score >= floor(N) + h; demote out of tier N
    only when score < floor(N) - h. First audit uses the raw tier.
    """
    if previous not in (1, 2, 3):
        return raw_tier(score)
    tier = previous
    while tier < 3 and score >= TIER_FLOORS[tier + 1] + hysteresis:
        tier += 1
    while tier > 1 and score < TIER_FLOORS[tier] - hysteresis:
        tier -= 1
    return tier


def migrate(p: ApexPaths) -> list[str]:
    """Bring config/state up to the current schema. Returns change notes."""
    notes = []
    for path, default in ((p.config, DEFAULT_CONFIG), (p.state, DEFAULT_STATE)):
        if not os.path.exists(path):
            continue
        data = load_json(path, default)
        ver = data.get("schema_version") or 0
        if ver > SCHEMA_VERSION:
            notes.append(f"{os.path.basename(path)}: schema v{ver} is newer than this Apex (v{SCHEMA_VERSION}); upgrade the plugin")
            continue
        if ver < SCHEMA_VERSION:
            data["schema_version"] = SCHEMA_VERSION
            save_json(path, data)
            notes.append(f"{os.path.basename(path)}: migrated v{ver} -> v{SCHEMA_VERSION}")
    return notes
