"""Run release readiness checks. Implementation: scripts/release_check.py"""
import os
import runpy
import sys

try:
    runpy.run_path(
        os.path.join(os.path.dirname(__file__), "scripts", "release_check.py"),
        run_name="__main__",
    )
except SystemExit as e:
    sys.exit(e.code if e.code is not None else 0)
