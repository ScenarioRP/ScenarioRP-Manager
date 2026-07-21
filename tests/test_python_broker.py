from __future__ import annotations

import unittest
from pathlib import Path

from python_broker import InvalidScriptNameError, PowerShellRunner, ScriptNotFoundError, ScriptResult


class PythonBrokerTests(unittest.TestCase):
    def test_script_result_extracts_status_lines(self) -> None:
        result = ScriptResult(
            script_name="status.ps1",
            success=True,
            exit_code=0,
            stdout="log line\nSTATUS|Environment|OK|Ready\nSTATUS|Database|Running|localhost\n",
            stderr="",
            command=("powershell",),
            duration_seconds=0.1,
        )

        self.assertEqual(
            result.status_lines,
            ("STATUS|Environment|OK|Ready", "STATUS|Database|Running|localhost"),
        )

    def test_missing_script_raises_clear_exception(self) -> None:
        runner = PowerShellRunner(scripts_dir=Path(__file__).resolve().parents[1] / "scripts")

        with self.assertRaises(ScriptNotFoundError):
            runner.run_script("missing-script.ps1")

    def test_rejects_paths_outside_scripts_dir(self) -> None:
        runner = PowerShellRunner(scripts_dir=Path(__file__).resolve().parents[1] / "scripts")

        with self.assertRaises(InvalidScriptNameError):
            runner.run_script("../outside.ps1")


if __name__ == "__main__":
    unittest.main()
