"""Runs R analysis scripts through Rscript, exchanging data as JSON files."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .base import AnalysisError, Runner, RunnerOutput

R_SCRIPTS_DIR = Path(os.environ.get("KSP_R_SCRIPTS_DIR", Path(__file__).resolve().parents[3] / "r"))
RSCRIPT = os.environ.get("KSP_RSCRIPT", "Rscript")


class RScriptRunner(Runner):
    """Runs `r/<script>` as `Rscript <script> <input.json> <output.json>`.

    The script writes an envelope {"status", "result" | "error", "environment"}
    (see r/common.R); R console output is never parsed.
    """

    def __init__(self, script: str, timeout: int = 600) -> None:
        self.script = script
        self.timeout = timeout

    def run(self, payload: dict) -> RunnerOutput:
        script = R_SCRIPTS_DIR / self.script
        if not script.is_file():
            raise AnalysisError(f"R script not found: {script}")

        with tempfile.TemporaryDirectory(prefix="ksp-") as workdir:
            input_path = Path(workdir) / "input.json"
            output_path = Path(workdir) / "output.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            try:
                process = subprocess.run(
                    [RSCRIPT, str(script), str(input_path), str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as error:
                raise AnalysisError(f"{self.script} did not finish within {self.timeout} s.") from error

            if not output_path.is_file():
                raise AnalysisError(f"{self.script} crashed:\n{process.stderr.strip()}")
            envelope = json.loads(output_path.read_text(encoding="utf-8"))

        if envelope.get("status") != "ok":
            raise AnalysisError(f"{self.script}: {envelope.get('error', 'unknown error')}")
        return RunnerOutput(result=envelope["result"], environment=envelope["environment"])
