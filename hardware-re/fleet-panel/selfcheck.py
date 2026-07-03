"""
Self-check for the fleet panel's pure-logic modules (models.py, auth.py)
and, later in this file, main.py's HTTP routes via FastAPI's TestClient
(no pytest needed -- TestClient is a plain Python class).

Run directly: python selfcheck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# In-memory DB for every test in this file -- must be set before main.py
# (or db.py) is imported anywhere, since db.get_engine() reads this env
# var at call time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import inspect  # noqa: E402

import db  # noqa: E402

failures = 0


def check(name, actual, expected):
    global failures
    if actual == expected:
        print(f"PASS: {name}")
    else:
        failures += 1
        print(f"FAIL: {name} -- expected {expected!r}, got {actual!r}")


def check_true(name, actual):
    check(name, bool(actual), True)


# --- schema creation ---
engine = db.get_engine()
table_names = inspect(engine).get_table_names()
check("machines table exists after get_engine()", "machines" in table_names, True)

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
