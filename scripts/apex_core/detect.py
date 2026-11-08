"""Detect the project stack and propose non-destructive health checks.

Supported in v0.1: JavaScript/TypeScript (npm, pnpm, yarn, bun) and Python.
"""
from __future__ import annotations

import json
import os
import re

from .paths import read_text

LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
    ("package-lock.json", "npm"),
)
# script name -> (check name, required)
JS_SCRIPTS = (
    ("typecheck", "typecheck", True),
    ("type-check", "typecheck", True),
    ("types", "typecheck", True),
    ("lint", "lint", False),
    ("test", "test", False),
    ("build", "build", True),
)
WATCH_HINTS = re.compile(r"\b(--watch|-w\b|watch\b|vitest(?!\s+run)\s*$)")


def _run_script(pm: str, script: str) -> str:
    if pm == "npm":
        return "npm test --silent" if script == "test" else f"npm run {script} --silent"
    return f"{pm} run {script}"


def _exec(pm: str, tool: str) -> str:
    return {"npm": f"npx --no-install {tool}", "pnpm": f"pnpm exec {tool}",
            "yarn": f"yarn exec {tool}", "bun": f"bun x --no-install {tool}"}.get(pm, f"npx --no-install {tool}")


def detect_js(root: str) -> dict | None:
    pkg_path = os.path.join(root, "package.json")
    if not os.path.isfile(pkg_path):
        return None
    try:
        pkg = json.loads(read_text(pkg_path) or "{}")
    except json.JSONDecodeError:
        pkg = {}
    pm = "npm"
    for name, manager in LOCKFILES:
        if os.path.exists(os.path.join(root, name)):
            pm = manager
            break
    declared = str(pkg.get("packageManager") or "")
    for manager in ("pnpm", "yarn", "bun", "npm"):
        if declared.startswith(manager + "@"):
            pm = manager
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    scripts = pkg.get("scripts") or {}
    stack = ["javascript"]
    ts = "typescript" in deps or os.path.exists(os.path.join(root, "tsconfig.json"))
    if ts:
        stack.append("typescript")
    for fw in ("next", "react", "vue", "svelte", "@sveltejs/kit", "nuxt", "astro",
               "express", "fastify", "@nestjs/core", "remix", "@remix-run/react", "vite"):
        if fw in deps:
            stack.append(fw.lstrip("@").split("/")[0])
    checks, seen = [], set()
    for script, name, required in JS_SCRIPTS:
        if script in scripts and name not in seen:
            body = str(scripts[script])
            if WATCH_HINTS.search(body):
                continue  # never run watch-mode scripts
            seen.add(name)
            checks.append({"name": name, "cmd": _run_script(pm, script), "required": required,
                           "timeout": 600 if name == "build" else 300})
    if ts and "typecheck" not in seen:
        checks.insert(0, {"name": "typecheck", "cmd": _exec(pm, "tsc --noEmit"),
                          "required": True, "timeout": 300})
    if "eslint" in deps and "lint" not in seen:
        checks.append({"name": "lint", "cmd": _exec(pm, "eslint ."), "required": False, "timeout": 300})
    return {"stack": stack, "package_manager": pm, "health_checks": checks}


def detect_python(root: str) -> dict | None:
    markers = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile")
    if not any(os.path.exists(os.path.join(root, m)) for m in markers):
        return None
    pyproject = read_text(os.path.join(root, "pyproject.toml"))
    reqs = read_text(os.path.join(root, "requirements.txt")) + read_text(
        os.path.join(root, "requirements-dev.txt"))
    blob = (pyproject + "\n" + reqs).lower()
    py = "python"
    for venv in (".venv", "venv"):
        cand = os.path.join(venv, "bin", "python")
        if os.path.exists(os.path.join(root, cand)):
            py = cand
            break
    stack = ["python"]
    for fw in ("django", "fastapi", "flask", "streamlit", "pydantic", "sqlalchemy"):
        if re.search(rf"\b{fw}\b", blob):
            stack.append(fw)
    checks = []
    has_tests = any(os.path.isdir(os.path.join(root, d)) for d in ("tests", "test"))
    if "pytest" in blob or has_tests:
        checks.append({"name": "test", "cmd": f"{py} -m pytest -q", "required": False, "timeout": 600})
    if "ruff" in blob or os.path.exists(os.path.join(root, "ruff.toml")):
        checks.append({"name": "lint", "cmd": f"{py} -m ruff check .", "required": False, "timeout": 120})
    if "mypy" in blob or os.path.exists(os.path.join(root, "mypy.ini")):
        checks.append({"name": "typecheck", "cmd": f"{py} -m mypy .", "required": True, "timeout": 300})
    elif os.path.exists(os.path.join(root, "pyrightconfig.json")) or "pyright" in blob:
        checks.append({"name": "typecheck", "cmd": "pyright", "required": True, "timeout": 300})
    checks.insert(0, {"name": "compile", "cmd": f"{py} -m compileall -q -x '(\\.venv|venv|node_modules|\\.git)' .",
                      "required": True, "timeout": 120})
    return {"stack": stack, "package_manager": "pip", "health_checks": checks}


def detect(root: str) -> dict:
    result = {"stack": [], "package_manager": None, "health_checks": [], "notes": []}
    for fn in (detect_js, detect_python):
        found = fn(root)
        if not found:
            continue
        result["stack"] += found["stack"]
        result["package_manager"] = result["package_manager"] or found["package_manager"]
        names = {c["name"] for c in result["health_checks"]}
        for c in found["health_checks"]:
            if c["name"] in names:
                c = dict(c, name=f"{c['name']}-{found['stack'][0][:2]}")
            result["health_checks"].append(c)
    if not result["stack"]:
        result["notes"].append("No package.json or Python project files found; add health checks to .apex/config.json manually.")
    for other in ("go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "composer.json"):
        if os.path.exists(os.path.join(root, other)):
            result["notes"].append(f"Found {other}: this stack isn't auto-detected yet; add its checks to config.json by hand.")
    return result
