"""`apex.py init` — create the `.apex/` workspace and lock the North Star."""
from __future__ import annotations

import datetime as _dt
import os

from . import SCHEMA_VERSION
from . import decisions as dec
from .detect import detect
from .paths import ApexPaths, read_text, write_text
from .state import DEFAULT_CONFIG, DEFAULT_STATE, save_json

GITIGNORE_LINES = ("# Apex runtime files", ".apex/.lock", ".apex/.search-log.json", ".apex/.health.json")


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.replace(";", ",").split(",") if x.strip()]
    return [str(x).strip() for x in v if str(x).strip()]


def north_star_text(spec: dict, today: str) -> str:
    comps = _as_list(spec.get("competitors"))
    goals = _as_list(spec.get("non_goals"))
    for key, val in (("audience", spec.get("audience")), ("value", spec.get("value"))):
        if not val or not str(val).strip():
            raise ValueError(f"north star field '{key}' is required")
    if not comps:
        raise ValueError("at least one competitor is required (use 'none known' if truly none)")
    if not goals:
        raise ValueError("at least one explicit non-goal is required")
    return (
        "# Product North Star\n\n"
        f"> Locked by `/apex:init` on {today}. Apex treats this as ground truth for every audit and web search.\n"
        "> Claude's Write/Edit tools are blocked on this file; re-run `/apex:init --force` to change it.\n\n"
        f"**Product:** {spec.get('product') or 'Untitled project'}\n\n"
        f"**Target audience:** {str(spec['audience']).strip()}\n\n"
        f"**Core value proposition:** {str(spec['value']).strip()}\n\n"
        f"**Top competitors:** {', '.join(comps)}\n\n"
        f"**Explicit non-goals:** {'; '.join(goals)}\n"
    )


def ensure_gitignore(root: str) -> bool:
    path = os.path.join(root, ".gitignore")
    text = read_text(path)
    missing = [l for l in GITIGNORE_LINES[1:] if l not in text.splitlines()]
    if not missing:
        return False
    block = ("\n" if text and not text.endswith("\n") else "") + ("\n" if text else "")
    block += "\n".join([GITIGNORE_LINES[0]] + missing) + "\n"
    write_text(path, text + block)
    return True


def init(p: ApexPaths, spec: dict, force: bool = False, today: str | None = None) -> dict:
    today = today or _dt.date.today().isoformat()
    created = []
    if os.path.exists(p.north_star) and not force:
        raise FileExistsError("North Star already locked; pass --force to replace it (decisions and history are kept)")
    for d in (p.apex, p.sessions_dir, p.research_dir, p.history_dir):
        os.makedirs(d, exist_ok=True)
    write_text(p.north_star, north_star_text(spec, today))
    created.append(".apex/north-star.md")
    if not os.path.exists(p.decisions):
        dec.ensure_file(p)
        created.append(".apex/decisions.md")
    detected = detect(p.root)
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(p.config):
        from .state import load_config
        cfg = load_config(p)
    cfg["schema_version"] = SCHEMA_VERSION
    cfg["stack"] = spec.get("stack") or detected["stack"]
    cfg["package_manager"] = spec.get("package_manager") or detected["package_manager"]
    if "health_checks" in spec and spec["health_checks"] is not None:
        cfg["health_checks"] = spec["health_checks"]
    elif not cfg.get("health_checks"):
        cfg["health_checks"] = detected["health_checks"]
    if "research" in spec and isinstance(spec["research"], bool):
        cfg["research"] = dict(cfg.get("research") or {}, enabled=spec["research"])
    save_json(p.config, cfg)
    created.append(".apex/config.json")
    if not os.path.exists(p.state):
        save_json(p.state, dict(DEFAULT_STATE))
        created.append(".apex/state.json")
    if ensure_gitignore(p.root):
        created.append(".gitignore (apex runtime entries)")
    return {"created": created, "config": cfg, "notes": detected.get("notes", [])}
