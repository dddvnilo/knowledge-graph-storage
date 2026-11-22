"""Semantic and CLI checks for CSV -> package v0.1, without R or Virtuoso."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from ingest.contracts.qmatrix_v0_1.proveri import check
from ingest.qmatrix_csv import PreparationError, main, package_validator, prepare_package

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "ingest" / "qmatrix"
CREATED_AT = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def metadata(kind="expert"):
    return json.loads((EXAMPLES / f"{kind}.metadata.json").read_text(encoding="utf-8"))


def prepare(kind="expert", source=None, details=None):
    return prepare_package(
        (EXAMPLES / f"{kind}.csv").read_bytes() if source is None else source,
        f"{kind}.csv",
        metadata(kind) if details is None else details,
        created_at=CREATED_AT,
    )


class PreparationTests(unittest.TestCase):
    def test_expert_values_identity_provenance_and_file_hash(self):
        details = metadata()
        before = copy.deepcopy(details)
        result = prepare(details=details)
        self.assertEqual(result["matrix"], [[1, 0], [1, 1], [1, None]])
        self.assertEqual([item["id"] for item in result["items"]], ["z1", "z2", "z3"])
        self.assertEqual(result["items"], details["items"])
        self.assertEqual(result["structure"], details["structure"])
        self.assertEqual(result["provenance"], details["provenance"])
        self.assertIsNone(result["provenance"]["generated_at"])
        self.assertEqual(result["package"]["created_at"], "2026-11-22T12:00:00Z")
        self.assertEqual(
            result["package"]["source_file"]["sha256"],
            hashlib.sha256((EXAMPLES / "expert.csv").read_bytes()).hexdigest(),
        )
        self.assertIn('CSV value "?" converted to null.', result["package"]["transformations"])
        self.assertEqual(details, before)

    def test_llm_keeps_model_prompt_parameters_and_cell_annotations(self):
        details = metadata("llm")
        result = prepare("llm", details=details)
        self.assertEqual(result["matrix"], [[1, 0], [1, 0], [1, 1]])
        self.assertEqual(result["provenance"], details["provenance"])
        self.assertEqual(result["cell_annotations"], details["cell_annotations"])
        self.assertNotEqual(result["structure"]["id"], metadata()["structure"]["id"])
        self.assertEqual(result["structure"]["test_id"], metadata()["structure"]["test_id"])

    def test_csv_order_changes_without_changing_cell_meanings(self):
        result = prepare(source=b"zadatak,K2,K1\nZadatak 3,?,x\nZadatak 1,-,x\nZadatak 2,x,x\n")
        self.assertEqual([item["id"] for item in result["items"]], ["z3", "z1", "z2"])
        self.assertEqual([skill["id"] for skill in result["competencies"]], ["skracivanje", "sabiranje"])
        self.assertEqual(result["matrix"], [[None, 1], [0, 1], [1, 1]])

    def test_unmapped_values_are_rejected_instead_of_becoming_zero(self):
        original = (EXAMPLES / "expert.csv").read_bytes()
        for token in (b"", b"2", b" x", b"unknown"):
            with self.subTest(token=token), self.assertRaisesRegex(PreparationError, "unsupported value"):
                prepare(source=original.replace(b"x,?", b"x," + token))

    def test_empty_cell_can_explicitly_mean_unknown(self):
        details = metadata()
        details["csv"]["values"][""] = None
        result = prepare(source=(EXAMPLES / "expert.csv").read_bytes().replace(b"x,?", b"x,"), details=details)
        self.assertIsNone(result["matrix"][2][1])
        self.assertIn('CSV value "" converted to null.', result["package"]["transformations"])

    def test_malformed_or_incomplete_csv_is_rejected(self):
        samples = {
            "no header": b"",
            "wrong item column": b"item,K1,K2\nZadatak 1,x,-\n",
            "duplicate column": b"zadatak,K1,K1\nZadatak 1,x,-\n",
            "missing competency": b"zadatak,K1\nZadatak 1,x\n",
            "extra competency": b"zadatak,K1,K2,K3\nZadatak 1,x,-,x\n",
            "short row": b"zadatak,K1,K2\nZadatak 1,x\n",
            "long row": b"zadatak,K1,K2\nZadatak 1,x,-,x\n",
            "unknown item": b"zadatak,K1,K2\nOther,x,-\n",
            "duplicate item": b"zadatak,K1,K2\nZadatak 1,x,-\nZadatak 1,x,-\n",
            "missing items": b"zadatak,K1,K2\nZadatak 1,x,-\n",
            "blank row": b"zadatak,K1,K2\n\n",
            "invalid quoting": b'zadatak,K1,K2\n"Zadatak 1,x,-\n',
            "invalid encoding": b"zadatak,K1,K2\n\xff,x,-\n",
        }
        for label, source in samples.items():
            with self.subTest(label=label), self.assertRaises(PreparationError):
                prepare(source=source)

    def test_ambiguous_metadata_is_rejected(self):
        for field in ("items", "competencies"):
            for key in ("source_label", "id"):
                details = metadata()
                details[field][1][key] = details[field][0][key]
                with self.subTest(field=field, key=key), self.assertRaises(PreparationError):
                    prepare(details=details)
        details = metadata()
        del details["items"][0]["source_label"]
        with self.assertRaisesRegex(PreparationError, "source_label"):
            prepare(details=details)

    def test_llm_requires_actual_prompt_text_and_nonblank_model_identifier(self):
        for missing in ("prompt", "model"):
            details = metadata("llm")
            if missing == "prompt":
                details["provenance"]["plan"].pop("text")
            else:
                details["provenance"]["agents"][0]["version"] = "  "
            with self.subTest(missing=missing), self.assertRaises(PreparationError):
                prepare("llm", details=details)

    def test_shared_validator_rejects_invalid_annotation_reference(self):
        details = metadata("llm")
        details["cell_annotations"][0]["item_id"] = "missing-item"
        with self.assertRaisesRegex(PreparationError, "cell_annotations/0/item_id"):
            prepare("llm", details=details)

    def test_unknown_metadata_fields_are_not_silently_dropped(self):
        details = metadata()
        details["unhandled_source_information"] = "must not disappear"
        with self.assertRaisesRegex(PreparationError, "Invalid metadata"):
            prepare(details=details)

    def test_bom_crlf_and_declared_separator(self):
        details = metadata()
        details["csv"]["delimiter"] = ";"
        source = "\ufeffzadatak;K1;K2\r\nZadatak 1;x;-\r\nZadatak 2;x;x\r\nZadatak 3;x;?\r\n".encode("utf-8")
        result = prepare(source=source, details=details)
        self.assertEqual(result["matrix"], [[1, 0], [1, 1], [1, None]])
        self.assertEqual(result["package"]["source_file"]["sha256"], hashlib.sha256(source).hexdigest())

    def test_committed_packages_match_their_current_sources(self):
        for kind in ("expert", "llm"):
            with self.subTest(kind=kind):
                actual = prepare(kind)
                example = json.loads((EXAMPLES / "generated" / f"{kind}-package.json").read_text(encoding="utf-8"))
                actual["package"].pop("created_at")
                example["package"].pop("created_at")
                self.assertEqual(actual, example)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "input matrix.csv"
        self.details = self.root / "metadata.json"
        self.output = self.root / "output" / "package.json"
        self.source.write_bytes((EXAMPLES / "expert.csv").read_bytes())
        self.details.write_text(json.dumps(metadata(), ensure_ascii=False), encoding="utf-8")

    def run_command(self, output=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([
                "--input", str(self.source), "--metadata", str(self.details),
                "--output", str(self.output if output is None else output),
            ])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_success_is_accepted_by_the_original_shared_validator(self):
        code, stdout, stderr = self.run_command()
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("3 items x 2 competencies", stdout)
        result = check(self.output, package_validator())
        self.assertEqual(result["status"], "provereno")
        package = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(package["package"]["source_file"]["name"], "input matrix.csv")

    def test_invalid_source_does_not_create_or_replace_output(self):
        self.source.write_bytes(b"zadatak,K1,K2\nZadatak 1,2,0\n")
        self.assertEqual(self.run_command()[0], 1)
        self.assertFalse(self.output.exists())
        self.output.parent.mkdir()
        self.output.write_bytes(b"existing package")
        code, _, stderr = self.run_command()
        self.assertEqual(code, 1)
        self.assertIn("unsupported value", stderr)
        self.assertEqual(self.output.read_bytes(), b"existing package")

    def test_sources_cannot_be_overwritten(self):
        for output in (self.source, self.details):
            original = output.read_bytes()
            with self.subTest(output=output):
                code, _, stderr = self.run_command(output=output)
                self.assertEqual(code, 1)
                self.assertIn("must not overwrite", stderr)
                self.assertEqual(output.read_bytes(), original)

    def test_duplicate_json_keys_and_nonjson_numbers_are_rejected(self):
        original = self.details.read_text(encoding="utf-8")
        malformed = (
            original.replace('"csv": {', '"csv": {}, "csv": {', 1),
            original.replace('"parameters": {}', '"parameters": {"bad": NaN}', 1),
        )
        for text in malformed:
            self.details.write_text(text, encoding="utf-8")
            with self.subTest(text=text[:50]):
                code, _, stderr = self.run_command()
                self.assertEqual(code, 1)
                self.assertTrue(stderr)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
