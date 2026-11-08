#!/usr/bin/env python3
"""Apex CLI — deterministic bookkeeping for the Apex Claude Code plugin.

Stdlib only, Python 3.9+. Run `python3 apex.py --help`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apex_core.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
