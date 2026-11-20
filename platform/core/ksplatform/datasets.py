"""Response datasets: binary respondents x items matrices loaded from CSV."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


class DatasetError(ValueError):
    """Raised when a response file is not a valid binary matrix."""


@dataclass(frozen=True)
class ResponseDataset:
    """A binary response matrix plus the hash of the file it came from.

    The SHA-256 of the original file identifies the exact data an analysis ran
    on, so a result can always be traced back to it (and the knowledge graph
    can point to it without copying the responses).
    """

    kind: ClassVar[str] = "responses"

    items: list[str]
    responses: list[list[int]]
    file_sha256: str
    source_name: str | None = None

    @property
    def content_hash(self) -> str:
        return self.file_sha256

    @property
    def n_respondents(self) -> int:
        return len(self.responses)

    @property
    def n_items(self) -> int:
        return len(self.items)

    def to_payload(self) -> dict:
        return {"items": self.items, "matrix": self.responses}

    @classmethod
    def from_csv_bytes(cls, data: bytes, source_name: str | None = None) -> "ResponseDataset":
        """Parse a CSV whose header holds item ids and whose rows hold 0/1."""
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig")))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if len(rows) < 2:
            raise DatasetError("The file needs a header row and at least one response row.")

        items = [cell.strip() for cell in rows[0]]
        if any(not item for item in items):
            raise DatasetError("Every column needs an item id in the header.")
        if len(set(items)) != len(items):
            raise DatasetError("Item ids in the header must be unique.")

        responses = []
        for line_number, row in enumerate(rows[1:], start=2):
            if len(row) != len(items):
                raise DatasetError(f"Line {line_number}: expected {len(items)} values, got {len(row)}.")
            values = [cell.strip() for cell in row]
            if any(value not in ("0", "1") for value in values):
                raise DatasetError(f"Line {line_number}: values must be 0 or 1.")
            responses.append([int(value) for value in values])

        return cls(items, responses, hashlib.sha256(data).hexdigest(), source_name)

    @classmethod
    def from_csv_file(cls, path: str | Path) -> "ResponseDataset":
        path = Path(path)
        return cls.from_csv_bytes(path.read_bytes(), source_name=path.name)
