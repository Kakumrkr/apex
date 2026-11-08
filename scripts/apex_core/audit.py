"""Audit lifecycle: lock, finalize (state + tier + history snapshot)."""
from __future__ import annotations

import datetime as _dt
import json
import os

from . import gitutil, lint, md
from .paths import ApexPaths, read_text, write_text
from .render import sessions_region, trend_region
from .state import load_config, load_state, next_tier, save_json, TIER_NAMES

LOCK_STALE_HOURS = 3


def lock_acquire(p: ApexPaths, mode: str = "standard") -> dict:
    if os.path.exists(p.lock):
        try:
            info = json.loads(read_text(p.lock) or "{}")
            started = _dt.datetime.fromisoformat(info.get("started_at"))
            age_h = (_dt.datetime.now() - started).total_seconds() / 3600
        except (ValueError, TypeError):
            age_h = LOCK_STALE_HOURS + 1
        if age_h < LOCK_STALE_HOURS:
            raise RuntimeError(f"another audit is running (started {info.get('started_at')}). "
                               "If it crashed, run `apex.py lock release`.")
    info = {"started_at": _dt.datetime.now().replace(microsecond=0).isoformat(), "mode": mode,
            "sha": gitutil.head_sha(p.root)}
    write_text(p.lock, json.dumps(info) + "\n")
    return info


def lock_release(p: ApexPaths) -> bool:
    if os.path.exists(p.lock):
        os.remove(p.lock)
        return True
    return False


def finalize(p: ApexPaths, today: str | None = None) -> dict:
    report = lint.run(p, require_roadmap=True)
    if report.errors:
        raise RuntimeError("lint failed, so the audit cannot be finalized:\n" + report.text())
    text = read_text(p.roadmap)
    card, _ = md.json_block(text, "scorecard")
    state, cfg = load_state(p), load_config(p)
    score = round(float(card["overall"]), 1)
    prev_tier = state.get("tier")
    tier = next_tier(score, prev_tier, float(cfg.get("tier_hysteresis", 0.3)))
    today = today or _dt.date.today().isoformat()
    sha = gitutil.head_sha(p.root)
    entry = {"date": today, "sha": sha, "score": score, "tier": tier, "mode": card.get("mode"),
             "research": card.get("research"), "dimensions": card.get("dimensions"),
             "health": (card.get("health") or {}).get("status") if isinstance(card.get("health"), dict) else card.get("health")}
    history = list(state.get("history") or []) + [entry]
    # Deterministic, generated regions.
    text = md.replace_region(text, "trend", trend_region(history))
    write_text(p.roadmap, text)
    text = md.replace_region(text, "sessions", sessions_region(p))
    write_text(p.roadmap, text)
    # Immutable snapshot.
    os.makedirs(p.history_dir, exist_ok=True)
    name, n = f"{today}-audit.md", 2
    while os.path.exists(os.path.join(p.history_dir, name)):
        name, n = f"{today}-audit-{n}.md", n + 1
    snap = (f"<!-- apex:snapshot {json.dumps({'date': today, 'sha': sha, 'score': score, 'tier': tier})} -->\n"
            f"> Immutable snapshot of `.apex/roadmap.md` written by `apex.py finalize-audit`.\n\n" + text)
    write_text(os.path.join(p.history_dir, name), snap)
    state.update({"last_audit_sha": sha, "last_audit_date": today, "last_mode": card.get("mode"),
                  "tier": tier, "score": score, "history": history})
    save_json(p.state, state)
    lock_release(p)
    prev_score = (history[-2]["score"] if len(history) > 1 else None)
    return {"score": score, "previous_score": prev_score,
            "delta": round(score - prev_score, 1) if prev_score is not None else None,
            "tier": tier, "tier_name": TIER_NAMES[tier], "tier_changed": prev_tier not in (None, tier),
            "previous_tier": prev_tier, "snapshot": f".apex/history/{name}", "sha": sha,
            "warnings": [w["message"] for w in report.warnings]}
