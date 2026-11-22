"""Provera paketa Q-matrice v0.1.

Radi dve stvari:
  1. proveru prema JSON Schema (paket-qm.schema.json),
  2. provere koje šema ne može da izrazi (dimenzije matrice, jedinstveni id, reference...).

Upotreba:
    python proveri.py paket.json [paket2.json ...]
    python proveri.py --json paket.json        # odgovor primaoca u JSON obliku

Zavisnost: pip install jsonschema
Izlazni kod: 0 ako su svi paketi provereni, 1 ako je bar jedan odbijen.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).with_name("paket-qm.schema.json")


def _path(parts) -> str:
    return "/".join(str(p) for p in parts) or "<koren>"


def schema_errors(validator: Draft202012Validator, data) -> list[dict]:
    errors = sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    return [{"path": _path(e.absolute_path), "message": e.message} for e in errors]


def _is_datetime(value: str) -> bool:
    if "T" not in value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def semantic_errors(data: dict) -> list[dict]:
    """Provere van šeme. Pretpostavlja da je paket već prošao šemu."""
    errors = []

    def err(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    items = [it["id"] for it in data["items"]]
    comps = [c["id"] for c in data["competencies"]]

    for name, ids in (("items", items), ("competencies", comps)):
        repeated = sorted({x for x in ids if ids.count(x) > 1})
        if repeated:
            err(name, f"ponovljeni id: {', '.join(repeated)}")

    matrix = data["matrix"]
    if len(matrix) != len(items):
        err("matrix", f"broj redova je {len(matrix)}, a broj stavki {len(items)}")
    for r, row in enumerate(matrix):
        if len(row) != len(comps):
            err(f"matrix/{r}", f"red ima {len(row)} vrednosti, a kompetencija ima {len(comps)}")

    item_set, comp_set = set(items), set(comps)
    for k, ann in enumerate(data.get("cell_annotations", [])):
        if ann["item_id"] not in item_set:
            err(f"cell_annotations/{k}/item_id", f"nepoznata stavka: {ann['item_id']}")
        if ann["competency_id"] not in comp_set:
            err(f"cell_annotations/{k}/competency_id", f"nepoznata kompetencija: {ann['competency_id']}")

    structure = data["structure"]
    if structure["revision_of"] is not None and structure["revision_of"] == structure["id"]:
        err("structure/revision_of", "struktura ne može biti revizija same sebe")

    for path, value in (
        ("package/created_at", data["package"]["created_at"]),
        ("provenance/generated_at", data["provenance"]["generated_at"]),
    ):
        if value is not None and not _is_datetime(value):
            err(path, f"nije datum i vreme u ISO 8601 obliku: {value!r}")

    return errors


def check(path: Path, validator: Draft202012Validator) -> dict:
    response = {"file": path.name, "structure_id": None, "status": "odbijeno", "errors": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        response["errors"].append({"path": "<fajl>", "message": f"ne može da se pročita kao JSON: {e}"})
        return response

    if isinstance(data, dict) and isinstance(data.get("structure"), dict):
        response["structure_id"] = data["structure"].get("id")

    errors = schema_errors(validator, data)
    if not errors:
        errors = semantic_errors(data)

    response["errors"] = errors
    response["status"] = "odbijeno" if errors else "provereno"
    return response


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konzola inače puca na č, ć, š...

    parser = argparse.ArgumentParser(description="Provera paketa Q-matrice v0.1")
    parser.add_argument("files", nargs="+", type=Path, help="JSON paketi za proveru")
    parser.add_argument("--json", action="store_true", help="ispiši odgovor primaoca kao JSON")
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    responses = [check(p, validator) for p in args.files]

    if args.json:
        print(json.dumps(responses, ensure_ascii=False, indent=2))
    else:
        for r in responses:
            print(f"{r['file']}: {r['status'].upper()}")
            for e in r["errors"]:
                print(f"    {e['path']}: {e['message']}")

    sys.exit(0 if all(r["status"] == "provereno" for r in responses) else 1)


if __name__ == "__main__":
    main()
