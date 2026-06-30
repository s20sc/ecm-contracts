# Frozen checker pin

`contract_checker.py` is frozen before any module contract is reconstructed and
before any per-case bug scoring, so the checker cannot be fitted to the cases.

- file: `contract_checker.py`
- sha256: `e9e0dbbfba9985924717d30265b4200514bb9d442a1429b16a49566e024673bf`
- selftest: PASS (`python3 selftest.py`)

Frame and unit comparison is canonical (see `canonical.py`): `per_message` / `none`
frames never conflict, and units are compared as disjoint sets, so two prose
descriptions of the same frame or unit are not reported as a mismatch. This is a
methodological choice that *reduces* the number of findings (it removes
prose-comparison false positives); it is fixed before scoring and is not tuned to
any case.

Rule: the checker is frozen before per-case contract reconstruction. Any edit
re-pins the hash here and re-runs the selftest.
