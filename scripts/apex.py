#!/usr/bin/env python3
"""Apex CLI — deterministic bookkeeping for the Apex Claude Code plugin.

Stdlib only, Python 3.9+. Run `python3 apex.py --help`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Fast path: hooks run on every tool call, so import only what they need.
    if len(sys.argv) == 3 and sys.argv[1] == "hook":
        from apex_core.hooks import run  # noqa: E402

        sys.exit(run(sys.argv[2]))
    from apex_core.cli import main  # noqa: E402

    sys.exit(main())
