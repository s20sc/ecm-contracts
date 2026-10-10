"""Single-run, read-only CPU identity receipt. No original main invocation."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import traceback
import sys
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[2]
BASE = PROJECT / "V32-EMSE/replication_package/experiments/pathb_v2"
LATE = PROJECT / "successor-evidence/V34-R1-expanded-boundary/late"
PREVIOUS = PROJECT / "successor-evidence/V40-late-binding-bridge/current-active-results.json"
RECEIPT = PROJECT / "successor-evidence/V40-late-binding-bridge/current-active-receipt.json"
OUTPUT = Path('/historical/runs/p5-v41-late-import-identity/runtime')
RELS = ("assemble.py", "scoring.py", "baselines_v2.py", "../pathb/checker/contract_checker.py", "../pathb/checker/canonical.py", "qos_literal.py", "frame_literal.py", "adjudication_guard.py")
SEAL = PROJECT / "V40-EMSE/audit/science-R1/round-001/manifest.json"
SEAL_SHA = "76ff3a3da051da6dcb7f96fde9e21d17619f97121ec774f27f934cd81d1cf8c3"
OBSERVED_IDENTITY = None
NAMES = ("baselines_v2", "contract_checker", "canonical", "qos_literal", "frame_literal", "adjudication_guard")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def differences(a, b, path="") -> list[dict]:
    if isinstance(a, dict) and isinstance(b, dict):
        changes = []
        for key in sorted(a.keys() | b.keys()):
            sub = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in a or key not in b:
                changes.append({"path": sub, "before_present": key in a, "after_present": key in b,
                                "before": a.get(key), "after": b.get(key)})
            else:
                changes.extend(differences(a[key], b[key], sub))
        return changes
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [c for i, (x,y) in enumerate(zip(a,b)) for c in differences(x,y,path+"/"+str(i))]
    return [] if type(a) is type(b) and a == b else [{"path": path, "before_present": True, "after_present": True, "before": a, "after": b}]

class ReadOnlyGuard:
    enabled = False
    def __call__(self, event: str, args: tuple) -> None:
        if not self.enabled:
            return
        if event == "open":
            mode, flags = args[1], args[2]
            if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags,int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                raise RuntimeError("Write denied during guarded replay")
        if event.startswith(("socket.", "subprocess.", "ctypes.")) or (event.startswith("os.") and event not in {"os.listdir", "os.scandir", "os.walk"}):
            raise RuntimeError("External execution, network or mutation denied: " + event)

class Identity:
    def __init__(self, expected: dict[Path, str]):
        self.expected = expected
        self.records: dict[Path, dict] = {}
    def observe(self, path: Path, module: str, is_call: bool, function: str) -> None:
        imported_file = str(path)
        path = path.resolve()
        if path not in self.expected:
            raise RuntimeError("Unfrozen runtime source: " + str(path))
        if path not in self.records:
            digest = sha(path)
            if digest != self.expected[path]:
                raise RuntimeError("Runtime identity hash mismatch: " + str(path))
            self.records[path] = {"actual_file": str(path), "actual_sha256": digest, "expected_sha256": self.expected[path], "authenticated": True, "module_names": [], "imported_file_values": [], "loaded": False, "function_calls": {}}
        rec = self.records[path]
        if module not in rec["module_names"]:
            rec["module_names"].append(module)
        if imported_file not in rec["imported_file_values"]:
            rec["imported_file_values"].append(imported_file)
        rec["loaded"] = True
        if is_call:
            rec["function_calls"][function] = rec["function_calls"].get(function,0) + 1
    def profile(self, frame, event, arg):
        if event != "call":
            return
        filename = Path(frame.f_code.co_filename).resolve()
        if not filename.is_relative_to(BASE.parent):
            return
        actual = frame.f_globals.get("__file__")
        if actual is None or Path(actual).resolve() != filename:
            raise RuntimeError("Runtime code and module __file__ disagree: " + str(filename))
        self.observe(Path(actual), frame.f_globals.get("__name__", "unknown"), frame.f_code.co_name != "<module>", frame.f_code.co_name)
    def report(self) -> list[dict]:
        out=[]
        for rel in RELS:
            path=(BASE/rel).resolve()
            rec=self.records.get(path)
            if rec is None:
                out.append({"relative_path":rel,"status":"not_loaded_or_called","function_execution_observed":False})
            else:
                out.append({"relative_path":rel,**rec,"function_execution_observed": bool(rec["function_calls"]), "status":"function_execution_observed" if rec["function_calls"] else "import_loaded_only_no_helper_call_observed"})
        return out

class SourceOnlyLoader:
    def __init__(self, path: Path):
        self.path = path.resolve()
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        module.__file__ = str(self.path)
        exec(compile(self.path.read_bytes(), str(self.path), "exec"), module.__dict__)

class SourceOnlyFinder:
    def __init__(self, sources: dict):
        self.sources = sources
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.sources:
            return None
        source = self.sources[fullname]
        return importlib.util.spec_from_loader(fullname, SourceOnlyLoader(source), origin=str(source))

def source_module(name: str, path: Path):
    spec = importlib.util.spec_from_loader(name, SourceOnlyLoader(path), origin=str(path.resolve()))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def _run_body() -> None:
    global OBSERVED_IDENTITY
    sys.dont_write_bytecode = True
    if any(name in sys.modules for name in NAMES):
        raise RuntimeError("Fresh interpreter required; target helper already imported")
    if sha(SEAL) != SEAL_SHA:
        raise RuntimeError("Prior V40 review seal changed")
    seal = read(SEAL)
    rows = [row for row in seal["files"] if Path(row["path"]).resolve() == RECEIPT.resolve()]
    if len(rows) != 1 or sha(RECEIPT) != rows[0]["sha256"]:
        raise RuntimeError("Prior receipt differs from V40 seal")
    old_receipt = read(RECEIPT)
    previous_freeze = next(row["current_sha256"] for row in old_receipt["binding_map"] if row["relative_path"] == "FREEZE.json")
    if sha(BASE / "FREEZE.json") != previous_freeze:
        raise RuntimeError("Current FREEZE differs from prior authenticated binding")
    freeze = read(BASE / "FREEZE.json")
    expected = {}
    binding = {}
    for rel in RELS:
        digest = freeze["files"].get(rel) or freeze["ledgers"][rel]["sha256"]
        path=(BASE/rel).resolve()
        if sha(path) != digest:
            raise RuntimeError("Frozen preflight mismatch: " + rel)
        expected[path] = digest
        if rel != "adjudication_guard.py":
            binding[rel] = digest
    binding["FREEZE.json"] = sha(BASE/"FREEZE.json")
    old_receipt = read(RECEIPT)
    for path, key in ((LATE/"replay.py","replay_source_sha256"),(LATE/"inputs.json","input_sha256"),(PREVIOUS,"current_result_sha256"),(LATE/"results.json","historical_result_sha256")):
        if sha(path) != old_receipt[key]:
            raise RuntimeError("Prior receipt source mismatch: " + str(path))
    data=read(LATE/"inputs.json")
    protected={LATE/"replay.py",LATE/"inputs.json",LATE/"results.json",PREVIOUS,RECEIPT,BASE/"FREEZE.json",*expected}
    protected.update(PROJECT/rel for rel in data["protected_sha256"])
    protected.update(PROJECT/source["path"] for source in data["sources"].values())
    before={str(path.resolve()):sha(path) for path in protected}
    guard=ReadOnlyGuard()
    sys.addaudithook(guard)
    identity=Identity(expected)
    OBSERVED_IDENTITY = identity
    source_paths = {Path(rel).stem: (BASE / rel).resolve() for rel in RELS if Path(rel).stem in NAMES}
    finder = SourceOnlyFinder(source_paths)
    sys.meta_path.insert(0, finder)
    guard.enabled=True
    try:
        a=runpy.run_path(str(LATE/"replay.py"),run_name="late_receipt_source")
        def current_modules():
            sys.path.insert(0,str(BASE))
            assembler=source_module("late_current_assemble",BASE/"assemble.py")
            scorer=source_module("late_current_scoring",BASE/"scoring.py")
            identity.observe(Path(assembler.__file__),assembler.__name__,False,"")
            identity.observe(Path(scorer.__file__),scorer.__name__,False,"")
            return assembler,scorer,binding.copy()
        fn=a["evaluate"]
        fn.__globals__["frozen_modules"]=current_modules
        sys.setprofile(identity.profile)
        try:
            result=fn(data)
        finally:
            sys.setprofile(None)
        for name in NAMES:
            module=sys.modules.get(name)
            if module is not None:
                identity.observe(Path(module.__file__),name,False,"")
        after={str(path.resolve()):sha(path) for path in protected}
        if before != after:
            raise RuntimeError("Protected source mutation")
    finally:
        guard.enabled=False
        sys.meta_path.remove(finder)
    previous=read(PREVIOUS)
    diff=differences(previous,result)
    old_hist=read(LATE/"results.json")
    historical_diff=differences(old_hist,result)
    receipt={"observed_utc":datetime.now(timezone.utc).isoformat(),"runtime":sys.version,"runner_sha256":sha(Path(__file__)),
             "source_only_loader":True,"bytecode_caches_not_used_for_target_modules":True,"original_main_called":False,"endpoint":"original late/replay.py evaluate; in-process frozen_modules binding only",
             "runtime_identity":identity.report(),"guard_before":before,"guard_after":after,"guard_unchanged":before==after,
             "prior_current_active_comparison":{"n_tracked":result["n_tracked"],"rows_equal":previous["rows"]==result["rows"],"census_equal":previous["outcome_census"]==result["outcome_census"],"full_json_equal":previous==result,"pairwise_equal":previous["aggregate_source_reported_failures"]["pairwise"]==result["aggregate_source_reported_failures"]["pairwise"],"changed_fields":diff},
             "historical_comparison":{"rows_equal":old_hist["rows"]==result["rows"],"census_equal":old_hist["outcome_census"]==result["outcome_census"],"full_json_equal":old_hist==result,"changed_fields":historical_diff,"pairwise_changed_fields":[d for d in historical_diff if "/pairwise/" in d["path"]]},
             "scope":"Coordinator unblinded post-outcome late descriptive replay; independent human and complete expanded-boundary gates remain open."}
    for name,obj in (("results.json",result),("receipt.json",receipt)):
        with (OUTPUT/name).open("x",encoding="utf-8") as handle:
            json.dump(obj,handle,ensure_ascii=False,indent=2)
            handle.write("\n")
    print(json.dumps({"output":str(OUTPUT),"prior_full_json_equal":previous==result,"runtime_identity_status":[{"relative_path":x["relative_path"],"status":x["status"]} for x in identity.report()]}))

def run() -> None:
    OUTPUT.mkdir(exist_ok=False)
    try:
        _run_body()
    except Exception as exc:
        with (OUTPUT / "failure.json").open("x", encoding="utf-8") as stream:
            json.dump({"status": "incomplete", "utc": datetime.now(timezone.utc).isoformat(),
                       "exception_type": type(exc).__name__, "message": str(exc),
                       "traceback": traceback.format_exc(),
                       "partial_runtime_identity": OBSERVED_IDENTITY.report() if OBSERVED_IDENTITY else []},
                      stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        raise

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",action="store_true",help="Reviewed endpoint only; no retry and output directory must be absent")
    args=parser.parse_args()
    if not args.run:
        parser.error("Explicit --run required")
    run()
