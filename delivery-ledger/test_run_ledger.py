"""Safety and comparison tests; fixtures never touch the scientific package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import run_ledger as runner


class DeliveryTests(unittest.TestCase):
    def test_output_inside_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                runner.create_output(root / "new", [root])
            self.assertFalse((root / "new").exists())

    def test_existing_and_broken_symlink_outputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "existing"
            existing.mkdir()
            link = root / "link"
            link.symlink_to(root / "absent")
            for path in (existing, link):
                with self.assertRaises(FileExistsError):
                    runner.create_output(path, [])

    def test_changed_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text("original")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            runner.verify_pins({path: expected})
            path.write_text("changed")
            with self.assertRaises(ValueError):
                runner.verify_pins({path: expected})

    def test_relative_paths_cannot_escape_roots(self) -> None:
        for relative in ("../secret", "/absolute", "a/../../secret"):
            with self.assertRaises(ValueError):
                runner.safe_relative(relative)

    def test_runtime_guard_rejects_input_writes_and_unsealed_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs", root / "output"
            inputs.mkdir()
            output.mkdir()
            pinned = inputs / "known"
            guard = runner.ReadOnlyInputs(output, [inputs], {pinned: "unused"})
            with self.assertRaises(PermissionError):
                guard("open", (str(pinned), "w", runner.os.O_WRONLY))
            with self.assertRaises(PermissionError):
                guard("open", (str(inputs / "unknown"), "r", runner.os.O_RDONLY))
            guard("open", (str(output / "receipt"), "w", runner.os.O_WRONLY))

    def test_failure_is_retained_without_running_algorithm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_dir = root / "configuration"
            config_dir.mkdir()
            roots = {name: root / name for name in ("package", "retained", "supplement")}
            for path in roots.values():
                path.mkdir()
            config = config_dir / "config.json"
            config.write_text(json.dumps({k: str(v) for k, v in roots.items()}))
            output = root / "result"
            self.assertEqual(runner.run(config, output), 1)
            failure = json.loads((output / "failure.json").read_text())
            self.assertEqual(failure["status"], "failure")
            self.assertFalse((output / "mechanism-ledger.json").exists())

    def test_runtime_guard_rejects_escaping_symlink_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs", root / "output"
            inputs.mkdir()
            output.mkdir()
            outside = root / "outside.json"
            outside.write_text("unsealed outside content")
            link = inputs / "not-in-manifest.json"
            link.symlink_to(outside)
            for pins in ({}, {outside: runner.digest(outside)}):
                guard = runner.ReadOnlyInputs(output, [inputs], pins)
                with self.assertRaises(PermissionError):
                    guard("open", (str(link), "r", runner.os.O_RDONLY))

    def test_runtime_guard_checks_resolved_input_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, output = root / "inputs", root / "output"
            inputs.mkdir()
            output.mkdir()
            known = inputs / "known.json"
            known.write_text("sealed")
            alias = root / "outside-alias.json"
            alias.symlink_to(known)
            guard = runner.ReadOnlyInputs(output, [inputs], {})
            with self.assertRaises(PermissionError):
                guard("open", (str(alias), "r", runner.os.O_RDONLY))
            guard = runner.ReadOnlyInputs(output, [inputs], {known: runner.digest(known)})
            guard("open", (str(alias), "r", runner.os.O_RDONLY))
            self.assertEqual(guard.scientific_reads, {known.resolve()})

    def test_only_exact_path_aliases_are_normalized(self) -> None:
        aliases = {"/old/input": "/new/input"}
        value = {"/old/input": ["/old/input", "quoted /old/input"]}
        self.assertEqual(runner.normalize(value, aliases),
                         {"/new/input": ["/new/input", "quoted /old/input"]})

    def test_scientific_change_and_missing_field_are_detected(self) -> None:
        expected = {"summary": {"credits": 14, "p": 0.5}, "cases": ["A"]}
        changed = {"summary": {"credits": 13, "p": 0.5}, "cases": []}
        differences = runner.differences(expected, changed)
        self.assertEqual({row["pointer"] for row in differences},
                         {"/summary/credits", "/cases"})
        self.assertTrue(runner.differences({"verified": False}, {}))

    def test_original_algorithm_edits_are_limited(self) -> None:
        original = (Path(__file__).resolve().parents[2] /
                    "successor-evidence/V40-mechanism-ledger/build_ledger.py")
        if not original.exists():
            self.skipTest("Historical source is supplied through configuration")
        source = original.read_text()
        adapted, edits = runner.adapt_source(source)
        self.assertEqual(len(edits), 3)
        self.assertEqual(len(source.splitlines()), len(adapted.splitlines()))
        for edit in edits:
            self.assertIn(edit["original"], source)
            self.assertIn(edit["delivery"], adapted)


if __name__ == "__main__":
    unittest.main()
