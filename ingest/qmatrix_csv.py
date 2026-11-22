"""Prepare a labelled CSV Q-matrix as a validated package v0.1.

Run from the repository root with ``python -m ingest.qmatrix_csv --help``.
Metadata supplies identities and provenance; this module never infers them.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .contracts.qmatrix_v0_1.proveri import SCHEMA_PATH, schema_errors, semantic_errors

PRODUCER = "qmatrix-csv-importer 0.1.0"
METADATA_FIELDS = ("structure", "items", "competencies", "provenance", "cell_annotations")


class PreparationError(ValueError):
    """The source or its metadata cannot be converted without guessing."""


@cache
def package_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@cache
def metadata_validator() -> Draft202012Validator:
    """Reuse the shared entity/provenance rules; add only CSV settings."""
    package_schema = package_validator().schema
    schema = {
        "$schema": package_schema["$schema"],
        "$defs": package_schema["$defs"],
        "type": "object",
        "additionalProperties": False,
        "required": ["csv", "structure", "items", "competencies", "provenance"],
        "properties": {
            **{name: package_schema["properties"][name] for name in METADATA_FIELDS},
            "csv": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item_column", "values"],
                "properties": {
                    "item_column": {"type": "string", "minLength": 1},
                    "delimiter": {"type": "string", "enum": [",", ";", "\t"]},
                    "values": {
                        "type": "object",
                        "minProperties": 1,
                        "additionalProperties": {"enum": [0, 1, None]},
                    },
                },
            },
        },
    }
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _reject_errors(errors: list[dict], context: str) -> None:
    if errors:
        details = "\n".join(f"  {error['path']}: {error['message']}" for error in errors)
        raise PreparationError(f"{context}:\n{details}")


def _label_map(entities: list[dict], field: str) -> dict[str, dict]:
    result = {}
    ids = set()
    for index, entity in enumerate(entities):
        label = entity.get("source_label")
        if not isinstance(label, str) or not label.strip():
            raise PreparationError(f"metadata/{field}/{index}/source_label must name its CSV row or column.")
        if label in result:
            raise PreparationError(f"metadata/{field}: duplicate source_label {label!r}.")
        if entity["id"] in ids:
            raise PreparationError(f"metadata/{field}: duplicate id {entity['id']!r}.")
        result[label] = entity
        ids.add(entity["id"])
    return result


def _check_llm_details(provenance: dict) -> None:
    """The shared draft schema alone permits empty model/prompt details."""
    if provenance["origin_type"] != "llm":
        return
    models = [agent for agent in provenance["agents"] if agent["kind"] == "software"]
    if not any(isinstance(agent["version"], str) and agent["version"].strip() for agent in models):
        raise PreparationError("metadata/provenance/agents: an LLM needs a non-empty exact model version.")
    prompt = provenance["plan"].get("text")
    if not isinstance(prompt, str) or not prompt.strip():
        raise PreparationError("metadata/provenance/plan/text: an LLM needs the prompt text.")


def prepare_package(
    source_bytes: bytes,
    source_name: str,
    metadata: dict,
    *,
    created_at: datetime | None = None,
) -> dict:
    """Keep CSV row/column order and validate before returning a package."""
    _reject_errors(schema_errors(metadata_validator(), metadata), "Invalid metadata")
    item_map = _label_map(metadata["items"], "items")
    competency_map = _label_map(metadata["competencies"], "competencies")
    _check_llm_details(metadata["provenance"])
    settings = metadata["csv"]

    try:
        text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise PreparationError("CSV must use UTF-8 (an optional BOM is accepted).") from error
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=settings.get("delimiter", ","), strict=True)
    items, matrix = [], []
    seen_items = set()
    used_aliases = {}
    try:
        header = next(reader, None)
        if not header or len(header) < 2:
            raise PreparationError("CSV needs a header with an item column and at least one competency.")
        if header[0] != settings["item_column"]:
            raise PreparationError(f"First CSV column must be {settings['item_column']!r}.")
        if len(set(header)) != len(header):
            raise PreparationError("CSV header contains duplicate column names.")
        columns = header[1:]
        missing = sorted(set(competency_map) - set(columns))
        extra = sorted(set(columns) - set(competency_map))
        if missing or extra:
            raise PreparationError(f"CSV competency columns differ from metadata; missing={missing}, unexpected={extra}.")
        competencies = [copy.deepcopy(competency_map[label]) for label in columns]

        for row in reader:
            line = reader.line_num
            if len(row) != len(header):
                raise PreparationError(f"CSV line {line}: expected {len(header)} fields, got {len(row)}.")
            label = row[0]
            if label not in item_map:
                raise PreparationError(f"CSV line {line}: unknown item label {label!r}.")
            if label in seen_items:
                raise PreparationError(f"CSV line {line}: duplicate item row {label!r}.")
            seen_items.add(label)
            items.append(copy.deepcopy(item_map[label]))
            values = []
            for column, token in zip(columns, row[1:]):
                if token not in settings["values"]:
                    raise PreparationError(
                        f"CSV line {line}, column {column!r}: unsupported value {token!r}; "
                        "declare its meaning in metadata/csv/values."
                    )
                value = settings["values"][token]
                values.append(value)
                if token != json.dumps(value):
                    used_aliases[token] = value
            matrix.append(values)
    except csv.Error as error:
        raise PreparationError(f"Invalid CSV near line {reader.line_num}: {error}") from error

    missing_items = sorted(set(item_map) - seen_items)
    if missing_items:
        raise PreparationError(f"CSV is missing item rows declared in metadata: {missing_items}.")
    timestamp = created_at if created_at is not None else datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise PreparationError("Package creation time must include a timezone.")
    transformations = [
        "Mapped CSV row/column source_label values to declared local IDs; preserved source row/column order."
    ]
    transformations.extend(
        f"CSV value {json.dumps(token, ensure_ascii=False)} converted to {json.dumps(value)}."
        for token, value in used_aliases.items()
    )
    package = {
        "schema_version": "0.1",
        "package": {
            "created_at": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "producer": PRODUCER,
            "source_file": {"name": source_name, "sha256": hashlib.sha256(source_bytes).hexdigest()},
            "transformations": transformations,
        },
        "structure": copy.deepcopy(metadata["structure"]),
        "items": items,
        "competencies": competencies,
        "matrix": matrix,
        "provenance": copy.deepcopy(metadata["provenance"]),
    }
    if "cell_annotations" in metadata:
        package["cell_annotations"] = copy.deepcopy(metadata["cell_annotations"])
    errors = schema_errors(package_validator(), package)
    if not errors:
        errors = semantic_errors(package)
    _reject_errors(errors, "Package rejected by the shared v0.1 validator")
    return package


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError(f"Metadata JSON contains a duplicate key: {key!r}.")
        result[key] = value
    return result


def _invalid_constant(token: str) -> None:
    raise PreparationError(f"Metadata JSON contains a non-JSON number: {token}.")


def _write_package(path: Path, package: dict) -> None:
    """Replace the output only once the complete validated JSON is ready."""
    text = json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare an expert/LLM CSV Q-matrix as a validated v0.1 JSON package.")
    parser.add_argument("--input", required=True, type=Path, help="Labelled UTF-8 CSV Q-matrix")
    parser.add_argument("--metadata", required=True, type=Path, help="JSON identities, CSV settings and provenance")
    parser.add_argument("--output", required=True, type=Path, help="Destination JSON package")
    args = parser.parse_args(argv)
    try:
        for source in (args.input, args.metadata):
            if args.output.resolve() == source.resolve() or (
                args.output.exists() and source.exists() and args.output.samefile(source)
            ):
                raise PreparationError("Output must not overwrite the CSV or metadata source.")
        metadata = json.loads(
            args.metadata.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
        package = prepare_package(args.input.read_bytes(), args.input.name, metadata)
        _write_package(args.output, package)
    except (PreparationError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(
        f"Created {args.output}: {len(package['items'])} items x {len(package['competencies'])} competencies; "
        "validated against package v0.1."
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
