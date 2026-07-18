#!/usr/bin/env python3
"""Deterministic release checks not covered by the unit-test suite."""

from __future__ import annotations

import compileall
import os
import re
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify_python() -> None:
    if not compileall.compile_dir(ROOT / "app", quiet=1):
        raise SystemExit("Python compilation failed")


def verify_routes() -> None:
    os.environ["DB_PATH"] = "/tmp/austin-floodops-verify.sqlite3"
    os.environ["HEARTBEAT_ENABLED"] = "false"
    from app.main import app

    route_keys = []
    for route in app.routes:
        for method in getattr(route, "methods", set()) or set():
            route_keys.append((method, route.path))
    duplicates = sorted(key for key, count in Counter(route_keys).items() if count > 1)
    if duplicates:
        raise SystemExit(f"Duplicate API routes: {duplicates}")


def verify_inline_javascript() -> None:
    index = (ROOT / "app" / "static" / "index.html").read_text()
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", index, flags=re.DOTALL | re.IGNORECASE)
    inline = [script for script in scripts if script.strip()]
    if not inline:
        raise SystemExit("No inline dashboard JavaScript found")
    for number, script in enumerate(inline, start=1):
        command = ["node", "--check", "-"]
        if re.search(r"^\s*(?:import|export)\s", script, flags=re.MULTILINE):
            command = ["node", "--input-type=module", "--check", "-"]
        result = subprocess.run(
            command,
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise SystemExit(f"Dashboard JavaScript block {number} failed syntax validation:\n{result.stderr}")


if __name__ == "__main__":
    verify_python()
    verify_routes()
    verify_inline_javascript()
    print("Python compilation, route uniqueness, and dashboard JavaScript checks passed.")
