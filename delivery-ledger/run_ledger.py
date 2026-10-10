"""Run the retained ledger algorithm through explicit, sealed delivery paths."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from types import ModuleType
from typing import Any

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REFERENCE_PINS = {'build_ledger.py': '3670e44b7fd80b8660cabdbcac28f30d931f2e997d9f07700e69c3dcb73295e0', 'source-sha256.json': 'a61ff336a075cadff09834b40069d307eb347f8013e0423d4801ca7c7e3e9063', 'mechanism-ledger.json': '95106da0790b6fa737bfc9b657df725809e89bf55e9d42fb93d4dd09d3bcd38b', 'credit-case-index.json': 'd6de827c853f60a8a9b2b85f44ed78c2d6c67b47b41f02c5bee7f059ab6f97d6'}
PUBLIC_INPUTS_SHA = '8626d3a21cd1fb440afefd42a57782ba528add2053d173d099b11d92421ee3fb'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Invalid relative input path")
    return path


def create_output(path: Path, inputs: list[Path]) -> Path:
    if os.path.lexists(path):
        raise FileExistsError("Output already exists, including symlinks")
    parent = path.parent.resolve(strict=True)
    output = parent / path.name
    if any(output.is_relative_to(root.resolve()) for root in inputs):
        raise ValueError("Output cannot be inside an input directory")
    output.mkdir(mode=0o700)
    return output


def verify_pins(pins: dict[Path, str]) -> None:
    for path, expected in pins.items():
        if not path.is_file() or digest(path) != expected:
            raise ValueError("Input hash mismatch: " + str(path))


def input_paths(rows: list[dict[str, str]], roots: dict[str, Path]) -> dict[Path, str]:
    pins: dict[Path, str] = {}
    for row in rows:
        root = roots[row["root"]]
        relative = safe_relative(row["relative"])
        path = (root / str(relative)).resolve(strict=True)
        if not path.is_relative_to(root) or path in pins:
            raise ValueError("Escaping or duplicate input path")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Invalid input hash")
        pins[path] = row["sha256"]
    return pins


def legacy_key(path: str) -> tuple[str, str]:
    marker = "/V32-EMSE/replication_package/"
    if marker in path:
        return "package", path.split(marker, 1)[1]
    match = re.search(r"/s2_work/tasks/(u\d+)/snapshot/(.+)$", path)
    if match:
        return "retained", f"{match[1]}/snapshot/{match[2]}"
    raise ValueError("Unrecognized historical input identity")


def historical_aliases(hashes: dict[str, str], rows: list[dict[str, str]],
                       roots: dict[str, Path]) -> dict[str, str]:
    expected = {(r["root"], r["relative"]): r["sha256"] for r in rows}
    actual = {legacy_key(path): h for path, h in hashes.items()}
    if actual != expected or len(hashes) != len(rows):
        raise ValueError("Historical input inventory differs from public seal")
    return {path: str((roots[key[0]] / key[1]).resolve())
            for path in hashes for key in [legacy_key(path)]}


def normalize(value: Any, aliases: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {aliases.get(k, k): normalize(v, aliases) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v, aliases) for v in value]
    return aliases.get(value, value) if isinstance(value, str) else value


def pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def differences(expected: Any, actual: Any, pointer: str = "") -> list[dict[str, Any]]:
    if type(expected) is not type(actual):
        return [{"pointer": pointer, "expected": expected, "actual": actual}]
    if isinstance(expected, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            location = pointer + "/" + pointer_token(key)
            if key not in expected or key not in actual:
                result.append({"pointer": location, "expected_present": key in expected,
                               "actual_present": key in actual})
            else:
                result.extend(differences(expected[key], actual[key], location))
        return result
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [{"pointer": pointer, "expected_length": len(expected),
                     "actual_length": len(actual)}]
        return [item for i, (old, new) in enumerate(zip(expected, actual))
                for item in differences(old, new, pointer + "/" + str(i))]
    return [] if expected == actual else [{"pointer": pointer, "expected": expected,
                                          "actual": actual}]


def path_changes(value: Any, aliases: dict[str, str], pointer: str = "") -> list[dict[str, str]]:
    changes = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in aliases and aliases[key] != key:
                changes.append({"pointer": pointer, "kind": "dictionary_key",
                                "historical": key, "delivery": aliases[key]})
            changes.extend(path_changes(child, aliases, pointer + "/" + pointer_token(key)))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            changes.extend(path_changes(child, aliases, pointer + "/" + str(i)))
    elif isinstance(value, str) and value in aliases and aliases[value] != value:
        changes.append({"pointer": pointer, "kind": "string_value",
                        "historical": value, "delivery": aliases[value]})
    return changes


def adapt_source(source: str) -> tuple[str, list[dict[str, str]]]:
    """Change three path-binding statements; keep every algorithm line otherwise."""
    header = source.splitlines()[2]
    candidates = "candidates=[B/'s2_work/tasks'/task/'snapshot'/path,ROOT/'experiments/pathb_v2/s2_work/tasks'/task/'snapshot'/path,ROOT/'V32-EMSE/replication_package/posthoc_review_v28/source-extracts'/task/path]"
    artifacts = "candidates=[B/'s2_work/tasks'/task/path,ROOT/'experiments/pathb_v2/s2_work/tasks'/task/path]+candidates"
    pairs = [(header, "ROOT=_package;B=_package/'experiments/pathb_v2';O=_output;sys.dont_write_bytecode=True;AG=_load_guard(B/'adjudication_guard.py')"),
             (candidates, "candidates=_snapshot_candidates(task,path)"),
             (artifacts, "candidates=_artifact_candidates(task)+candidates")]
    edits = []
    for old, new in pairs:
        if source.count(old) != 1:
            raise ValueError("Retained path-binding source does not match")
        source = source.replace(old, new, 1)
        edits.append({"original": old, "delivery": new})
    return source, edits


class ReadOnlyInputs:
    """Protect input roots and permit filesystem writes only in the new output."""
    def __init__(self, output: Path, roots: list[Path], pins: dict[Path, str]) -> None:
        self.output = output.resolve()
        self.roots = [root.resolve() for root in roots]
        self.root_aliases = [(root.absolute(), root.resolve()) for root in roots]
        self.root_aliases.extend((root, root) for root in self.roots)
        self.pins = {path.resolve(): value for path, value in pins.items()}
        self.scientific_reads: set[Path] = set()

    def __call__(self, event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            lexical = Path(os.fsdecode(args[0])).absolute()
            path = lexical.resolve()
            mode, flags = args[1:3]
            writing = (bool((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                       or (isinstance(mode, str) and any(c in mode for c in "wax+")))
            if writing and not path.is_relative_to(self.output):
                raise PermissionError("Write outside new output is forbidden")
            requested_roots = [resolved for alias, resolved in self.root_aliases
                               if lexical.is_relative_to(alias)]
            if not writing and any(not path.is_relative_to(root) for root in requested_roots):
                raise PermissionError("Input read escapes protected root: " + str(lexical))
            if not writing and (requested_roots or any(path.is_relative_to(r) for r in self.roots)):
                if path not in self.pins:
                    raise PermissionError("Unsealed input read: " + str(path))
                self.scientific_reads.add(path)
        if event.startswith(("socket.", "subprocess.", "ctypes.")) or event in {
            "os.system", "os.remove", "os.rmdir", "os.rename", "os.symlink", "os.link",
            "os.mkdir", "os.truncate", "os.chmod", "os.utime", "os.exec", "os.posix_spawn",
        }:
            raise PermissionError("Forbidden runtime side effect: " + event)


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def run(config_path: Path, output_path: Path) -> int:
    config_path = config_path.resolve(strict=True)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    roots = {name: Path(config[name]).resolve(strict=True)
             for name in ("package", "retained", "supplement")}
    if any(not p.is_dir() for p in roots.values()):
        raise ValueError("Configured input roots must be directories")
    output = create_output(output_path, [*roots.values(), HERE, config_path.parent])
    config_sha = hashlib.sha256(config_bytes).hexdigest()
    pins = {config_path: config_sha}
    receipt: dict[str, Any] = {"status": "started", "config_sha256": config_sha,
                              "configured_roots": {k: str(v) for k, v in roots.items()},
                              "algorithm_source_sha256": REFERENCE_PINS["build_ledger.py"]}
    write_new(output / "attempt.json", receipt)
    try:
        manifest = HERE / "public-inputs.json"
        pins[manifest] = PUBLIC_INPUTS_SHA
        for name, expected in REFERENCE_PINS.items():
            reference = (roots["supplement"] / name).resolve(strict=True)
            if not reference.is_relative_to(roots["supplement"]):
                raise ValueError("Reference input escapes supplement root")
            pins[reference] = expected
        verify_pins(pins)
        rows = read_json(manifest)["files"]
        if len(rows) != 702:
            raise ValueError("Expected the retained 702-input inventory")
        pins.update(input_paths(rows, roots))
        verify_pins(pins)
        reference_hashes = read_json(roots["supplement"] / "source-sha256.json")
        aliases = historical_aliases(reference_hashes, rows, roots)
        base = roots["package"] / "experiments/pathb_v2"
        historical_base = next(p.rsplit("/", 1)[0] for p in reference_hashes if p.endswith("/pathb_v2/scoring.py"))
        aliases[historical_base] = str(base)
        protected_roots = [*roots.values(), HERE, config_path.parent]
        guard = ReadOnlyInputs(output, protected_roots, pins)
        sys.addaudithook(guard)
        script = roots["supplement"] / "build_ledger.py"
        adapted, edits = adapt_source(script.read_text())

        def load_guard(path: Path) -> ModuleType:
            module = ModuleType("delivery_ledger_adjudication_guard")
            module.__file__ = str(path)
            exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
            return module

        def candidates(task: str, relative: str, kind: str) -> list[Path]:
            key = task + ("/snapshot/" if kind == "retained" else "/") + relative
            path = roots["retained"] / key if kind == "retained" else base / "s2_work/tasks" / key
            return [path] if path.resolve() in pins else []

        namespace = {"_package": roots["package"], "_output": output, "_load_guard": load_guard,
                     "_snapshot_candidates": lambda t, p: candidates(t, p, "retained"),
                     "_artifact_candidates": lambda t: candidates(t, "artifact.txt", "package")}
        with (output / "generator.stdout.txt").open("x", encoding="utf-8") as stream:
            with redirect_stdout(stream):
                exec(compile(adapted, str(script), "exec"), namespace)
        verify_pins(pins)
        comparisons, failures = {}, []
        for name in ("mechanism-ledger.json", "credit-case-index.json", "source-sha256.json"):
            old = read_json(roots["supplement"] / name)
            new = read_json(output / name)
            expected = normalize(old, aliases)
            metadata = []
            if name == "mechanism-ledger.json":
                metadata = [{"pointer": "/generated_utc", "historical": old["generated_utc"],
                             "delivery": new["generated_utc"]}]
                expected["generated_utc"] = new["generated_utc"]
            delta = differences(expected, new)
            comparisons[name] = {"nonpath_differences": delta, "path_changes": path_changes(old, aliases),
                                 "metadata_changes": metadata, "equal_after_declared_mapping": not delta}
            failures.extend(delta)
        write_new(output / "comparison.json", comparisons)
        if failures:
            raise ValueError("Retained ledger fields differ after declared path/time mapping")
        verify_pins(pins)
        receipt.update(status="success", scientific_inputs=702, source_reads=len(guard.scientific_reads),
                       input_hashes_unchanged=True, adaptations=edits,
                       all_three_json_outputs_match=True, source_only_guard_loader=True,
                       output_sha256={p.name: digest(p) for p in output.iterdir() if p.is_file()},
                       configured_roots={k: str(v) for k, v in roots.items()})
        write_new(output / "receipt.json", receipt)
        return 0
    except Exception as error:
        receipt.update(status="failure", error_type=type(error).__name__, error=str(error))
        write_new(output / "failure.json", receipt)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    return run(args.config, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
