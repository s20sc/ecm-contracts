# Current active late replay method

The first historical evaluation follows the retained replay.py ROOT (project root); the second process switches only evaluate.__globals__["frozen_modules"] to the V32-EMSE replication-package path. verify_inputs retains the original project ROOT and verifies the original seven input cases, protected files, and anchors. Neither process calls main, which would write the old result.

Exact active loader used in the recorded command:

    def current_modules():
        freeze = json.loads((base / "FREEZE.json").read_text())
        hashes = {}
        for rel in ("assemble.py", "scoring.py", "baselines_v2.py", "../pathb/checker/contract_checker.py", "../pathb/checker/canonical.py"):
            hashes[rel] = sha(base / rel)
            assert hashes[rel] == freeze["files"][rel], rel
        for rel in ("qos_literal.py", "frame_literal.py"):
            hashes[rel] = sha(base / rel)
            assert hashes[rel] == freeze["ledgers"][rel]["sha256"], rel
        hashes["FREEZE.json"] = sha(base / "FREEZE.json")
        sys.path.insert(0, str(base))
        return a["load_module"]("late_current_assemble", base / "assemble.py"), a["load_module"]("late_current_scoring", base / "scoring.py"), hashes
    fn = a["evaluate"]
    fn.__globals__["frozen_modules"] = current_modules
    new = fn(inputs)

Here base is the absolute project/V32-EMSE/replication_package/experiments/pathb_v2 path. a was obtained with runpy.run_path on the original late/replay.py; sha is hashlib.sha256(path.read_bytes()).hexdigest(). This loader verifies all eight source/FREEZE hashes; it does not persist imported module.__file__ identities. Output-binding consistency is independently checkable; do not treat this method note as an instrumented import-identity receipt. The shell tool-call source is retained in the Codex conversation.

All seven row records and outcome census match the historical result; all non-pairwise aggregate fields match. The 88 other changes are pairwise inference/reporting fields, in addition to five binding changes; do not state full JSON or inference-metadata equality.
