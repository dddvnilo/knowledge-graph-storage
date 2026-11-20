#!/usr/bin/env python3
"""
cq.py - runs the competency-question queries in queries/ against the store and compares
each result with queries/expected/<name>.csv.

  python tools/cq.py                 run every query, compare, print OK / FAIL
  python tools/cq.py cq3             only queries whose file name starts with "cq3"
  python tools/cq.py cq3 --show      print the result instead of comparing

Rows are compared as sets, so ORDER BY does not matter. IRIs are written with the prefixes
below (e.g. struct:qm-expert-T1-v1); decimals are rounded to 4 places, date-times are
written in UTC as YYYY-MM-DDTHH:MM:SSZ, booleans as true/false.

Exit code 0 if every compared query matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kg  # noqa: E402

QUERIES = kg.REPO_ROOT / "queries"
EXPECTED = QUERIES / "expected"
XSD = "http://www.w3.org/2001/XMLSchema#"

# Prefixes used to write IRIs in results and expected files. The last three are the
# shorthands of examples/model-example.trig.
PREFIXES = {
    "ks": "https://example.org/ks#",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "test": "https://example.org/data/test/",
    "scheme": "https://example.org/data/scheme/",
    "struct": "https://example.org/data/structure/",
    "meta": "https://example.org/data/meta/",
    "closure": "https://example.org/data/closure/",
    "agent": "https://example.org/data/agent/",
    "plan": "https://example.org/data/plan/",
    "activity": "https://example.org/data/activity/",
    "source": "https://example.org/data/source/",
    "t1": "https://example.org/data/test/T1/item/",
    "k1": "https://example.org/data/scheme/K-T1/competency/",
    "lc": "https://example.org/data/scheme/lc-mcm/competency/",
}
LOCAL_NAME = re.compile(r"^[A-Za-z0-9_](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?$")
INTEGER = re.compile(r"^-?\d+$")
DECIMAL = re.compile(r"^-?\d*\.\d+(?:[eE][-+]?\d+)?$|^-?\d+(?:\.\d*)?[eE][-+]?\d+$")


def compact(iri: str) -> str:
    matches = [(len(ns), p) for p, ns in PREFIXES.items()
               if iri.startswith(ns) and LOCAL_NAME.match(iri[len(ns):])]
    if not matches:
        return iri
    _, prefix = max(matches)
    return f"{prefix}:{iri[len(PREFIXES[prefix]):]}"


def as_datetime(value: str) -> str | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(value: str) -> str:
    """Canonical text form of a value, used for both results and expected files."""
    if INTEGER.match(value):
        return str(int(value))
    if DECIMAL.match(value):
        return f"{float(value):.4f}"
    if "T" in value and value[:1].isdigit():
        return as_datetime(value) or value
    return value


def cell(binding: dict | None) -> str:
    if binding is None:
        return ""
    if binding["type"] == "uri":
        return compact(binding["value"])
    value, datatype = binding["value"], binding.get("datatype", "")
    if datatype == XSD + "boolean":
        return "true" if value in ("1", "true") else "false"
    if datatype in (XSD + "decimal", XSD + "double", XSD + "float"):
        return f"{float(value):.4f}"
    return normalise(value)


def run(store: kg.Store, path: Path) -> tuple[list[str], list[list[str]]]:
    res = store.select(path.read_text(encoding="utf-8"))
    cols = res["head"]["vars"]
    rows = [[cell(b.get(c)) for c in cols] for b in res["results"]["bindings"]]
    return cols, rows


def compare(cols: list[str], rows: list[list[str]], expected_path: Path) -> list[str]:
    with expected_path.open(encoding="utf-8", newline="") as f:
        lines = [r for r in csv.reader(f) if r]
    exp_cols, exp_rows = lines[0], [[normalise(v) for v in r] for r in lines[1:]]
    if cols != exp_cols:
        return [f"columns {cols}, expected {exp_cols}"]
    got, exp = {tuple(r) for r in rows}, {tuple(r) for r in exp_rows}
    problems = [f"missing    {','.join(r)}" for r in sorted(exp - got)]
    problems += [f"unexpected {','.join(r)}" for r in sorted(got - exp)]
    if not problems and len(rows) != len(exp_rows):
        problems.append(f"{len(rows)} rows, expected {len(exp_rows)} (duplicate rows)")
    return problems


def main(argv=None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("only", nargs="?", default="", help="run only queries whose name starts with this")
    parser.add_argument("--show", action="store_true", help="print results instead of comparing")
    args = parser.parse_args(argv)

    env = {**kg.read_env_file(kg.ENV_FILE), **__import__("os").environ}
    store = kg.Store(env.get("KG_ENDPOINT", "http://localhost:8890"), "dba", None)

    paths = sorted(p for p in QUERIES.glob("*.rq") if p.name.startswith(args.only))
    if not paths:
        sys.exit(f"No queries matching '{args.only}' in {QUERIES}")
    failed = 0
    for path in paths:
        cols, rows = run(store, path)
        if args.show:
            print(f"== {path.name}")
            w = csv.writer(sys.stdout, lineterminator="\n")
            w.writerow(cols)
            w.writerows(rows)
            continue
        expected = EXPECTED / f"{path.stem}.csv"
        if not expected.exists():
            print(f"SKIP  {path.name} (no {expected.relative_to(kg.REPO_ROOT).as_posix()})")
            continue
        problems = compare(cols, rows, expected)
        if problems:
            failed += 1
            print(f"FAIL  {path.name}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"OK    {path.name}  ({len(rows)} rows)")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
