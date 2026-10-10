# V41 late import identity protocol

Single fresh Python 3 process with `-B`, standard library only, CPU only. Reuse the original V34 late inputs, verify_inputs, evaluate; never call original main. Authenticate V32 FREEZE source files plus adjudication_guard and the two ledger-frozen literal helpers before import and upon runtime observation. Original project ROOT remains unchanged for source and primary-label guards.

Profile actual Python function calls using executed code filename plus module globals __file__; collect import module __file__ as loaded-only evidence. Every observed dependency must resolve to its expected frozen file and SHA256. Loaded-only helpers do not establish function execution; untriggered helpers are explicitly marked. Fresh interpreter denies preloaded named dependencies. No synthetic helper calls or new cases.

During the source load/evaluate window, the audit hook rejects file-write opens, process/network/ctypes events, and os events except the read-only listing/walk events. This is a Python audit policy with before/after protected hashes, not a claim to an operating-system sandbox. Bytecode writes are disabled. The eight target modules execute complete unchanged source bytes through an explicit source-only loader/finder; existing pyc caches are not used for these modules. This loader is a disclosed harness intervention. Before/after hashes cover replay, inputs, historical and V40 results/receipt, freeze, eight module sources, all input protected paths and source paths. The old V40 receipt is authenticated against the hard-pinned V40 review manifest. Current FREEZE and both comparison results must match that receipt. A failure writes an incomplete receipt and partial identity observations without retry. Fixed external runtime output directory is created with exist_ok=False; result and receipt use exclusive creation. No retry after any failure.

Compare V40 current-active results independently for all seven rows, census, whole JSON, and pairwise fields. Also retain full path-level comparison to historical late results, with missing versus null distinguished. Report current active equality independently from historical pairwise/binding changes.

Execution prerequisites: after guard_tests.py passes and code review is approved, one `python3 -B receipt_runner.py --run` execution may be authorized. Outputs: /historical/runs/p5-v41-late-import-identity/runtime/{results,receipt}.json. Never rerun into existing output directory.

Independent human labels, deployment evidence and complete expanded-boundary results remain unclosed.
