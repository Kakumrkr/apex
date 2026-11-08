"""Run the user-confirmed health checks with timeouts and record evidence.

Commands come only from `.apex/config.json` (confirmed by the user during
`/apex:init`). They run with shell=False, CI=1, and a timeout; results go to
`.apex/.health.json` so the linter can cross-check the auditor's scorecard.
"""
from __future__ import annotations

import datetime as _dt
import os
import shlex
import shutil
import subprocess
import time

from . import gitutil
from .paths import ApexPaths
from .state import load_config, save_json


def _tail(text: str, lines: int = 30, chars: int = 3000) -> str:
    out = "\n".join((text or "").splitlines()[-lines:])
    return out[-chars:]


def run_check(root: str, check: dict) -> dict:
    cmd = check.get("cmd", "")
    started = time.monotonic()
    res = {"name": check.get("name"), "cmd": cmd, "required": bool(check.get("required")),
           "status": "error", "exit": None, "duration_s": 0.0, "tail": ""}
    try:
        argv = shlex.split(cmd)
        if not argv:
            raise ValueError("empty command")
        exe = shutil.which(argv[0], path=os.environ.get("PATH")) or (
            os.path.join(root, argv[0]) if os.path.exists(os.path.join(root, argv[0])) else None)
        if not exe:
            res["tail"] = f"command not found: {argv[0]}"
            return res
        env = dict(os.environ, CI="1", FORCE_COLOR="0", NO_COLOR="1",
                   npm_config_yes="false", NEXT_TELEMETRY_DISABLED="1")
        proc = subprocess.run([exe] + argv[1:], cwd=root, capture_output=True, text=True,
                              timeout=int(check.get("timeout") or 300), env=env,
                              stdin=subprocess.DEVNULL)
        res["exit"] = proc.returncode
        res["status"] = "pass" if proc.returncode == 0 else "fail"
        res["tail"] = _tail((proc.stdout or "") + "\n" + (proc.stderr or ""))
    except subprocess.TimeoutExpired as exc:
        res["status"] = "timeout"
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        res["tail"] = _tail(out) + f"\n[apex] timed out after {check.get('timeout')}s"
    except (OSError, ValueError) as exc:
        res["tail"] = f"{type(exc).__name__}: {exc}"
    finally:
        res["duration_s"] = round(time.monotonic() - started, 1)
    return res


def overall(results: list[dict]) -> str:
    if not results:
        return "skipped"
    if any(r["required"] and r["status"] != "pass" for r in results):
        return "fail"
    if any(r["status"] != "pass" for r in results):
        return "partial"
    return "pass"


def run(p: ApexPaths, only: list[str] | None = None) -> dict:
    cfg = load_config(p)
    checks = [c for c in cfg.get("health_checks") or [] if not only or c.get("name") in only]
    results = [run_check(p.root, c) for c in checks]
    report = {
        "sha": gitutil.head_sha(p.root),
        "dirty": bool(gitutil.dirty_files(p.root)),
        "ran_at": _dt.datetime.now().replace(microsecond=0).isoformat(),
        "status": overall(results),
        "results": results,
    }
    if p.exists():
        save_json(p.health, report)
    return report
