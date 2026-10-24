"""Integration check — run before every push, whatever AI agent you use:

    backend\\.venv\\Scripts\\python scripts\\check.py          (Windows)
    backend/.venv/bin/python scripts/check.py               (macOS/Linux)
    ... add --skip-frontend to skip the npm build

Checks: every API endpoint answers 200 with the shared contract (as_of, model, risk levels), taluk_risk() keeps its
shape, removed routes stay 404, and the frontend builds. Exit code 0 = safe to push.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core.risk import taluk_risk  # noqa: E402

RISK = {"critical", "high", "medium", "low"}
DATES = ["2023-08-01", "2024-03-01", None]
# (path, must contain these keys). Add your platform's new endpoints here.
ENDPOINTS = [
    ("/api/core/meta", ["taluk_count", "climate_until"]),
    ("/api/core/regions", ["taluks"]),
    ("/api/core/indicators?as_of={d}", ["as_of", "model", "taluks"]),
    ("/api/core/taluk/132?as_of={d}", ["as_of", "model", "risk", "indicators"]),
    ("/api/agri/taluk/132?as_of={d}", ["as_of", "model", "risk", "season", "crops"]),
    ("/api/urban/cities?as_of={d}", ["as_of", "model", "cities"]),
    ("/api/urban/cauvery?as_of={d}", ["as_of", "series", "storage_tmc"]),
    ("/api/industry/areas?as_of={d}", ["as_of", "model", "areas"]),
    ("/api/industry/location?lat=13.13&lon=78.13&as_of={d}", ["as_of", "model", "risk"]),
    ("/api/meta", ["ward_count"]),                      # original Bengaluru model
    ("/api/predict?as_of={d}", ["wards"]),
]
GONE = ["/api/gov/overview", "/api/reservoir/list", "/api/city/cities"]

fails = []


def fail(msg):
    fails.append(msg)
    print("  FAIL", msg)


def main_check(skip_frontend):
    c = TestClient(main.app)
    print("API endpoints")
    for path, keys in ENDPOINTS:
        for d in DATES if "{d}" in path else [None]:
            url = path.format(d=d) if d else path.replace("?as_of={d}", "").replace("&as_of={d}", "")
            r = c.get(url)
            if r.status_code != 200:
                fail(f"{url} -> {r.status_code} {r.text[:120]}")
                continue
            j = r.json()
            missing = [k for k in keys if k not in j]
            if missing:
                fail(f"{url} missing keys {missing}")
            if "risk" in j and j["risk"] not in RISK:
                fail(f"{url} risk={j['risk']!r} not in {RISK}")
        print("  ok", path)
    for path in GONE:
        if c.get(path).status_code != 404:
            fail(f"{path} should be 404")

    print("taluk_risk() contract")
    rk = taluk_risk("2024-03-01")
    for k in ("model", "levels", "score", "drought_prob", "days_low", "days_mid", "days_high", "drivers"):
        if k not in rk:
            fail(f"taluk_risk missing {k}")
    if len(rk["levels"]) != 227 or not set(rk["levels"]) <= RISK:
        fail("taluk_risk levels must be 227 values from critical/high/medium/low")
    if len(rk["score"]) != 227:
        fail("taluk_risk score must have 227 values")
    print("  ok" if not fails else "  see failures above")

    if not skip_frontend:
        print("frontend build")
        r = subprocess.run("npm run build", cwd=ROOT / "frontend", shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            fail("npm run build failed:\n" + (r.stdout + r.stderr)[-1500:])
        else:
            print("  ok")


if __name__ == "__main__":
    main_check("--skip-frontend" in sys.argv)
    print("\nRESULT:", "PASS - safe to push" if not fails else f"FAIL - {len(fails)} problem(s), fix before pushing")
    sys.exit(1 if fails else 0)
