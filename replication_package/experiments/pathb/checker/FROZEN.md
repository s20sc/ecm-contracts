# FROZEN CHECKER PIN (re-pinned after canonical-comparison correction)

contract_checker.py sha256: e9e0dbbfba9985924717d30265b4200514bb9d442a1429b16a49566e024673bf (v3: dropped free-text precondition check)
frozen_date: 2026-06-23
selftest: PASS
correction_log: v1 (b83a291c) used literal string comparison for frame/units, which
  produced prose-comparison false positives (e.g. two "none" frames flagged as a
  mismatch). v2 normalizes via canonical.py (per_message/none frames skip; units as
  disjoint-set conflict). This is a METHODOLOGICAL FIX, not case-fitting: it was made
  before any per-case bug scoring, and REDUCES ECM findings (removes false positives).
rule: frozen before per-case contract reconstruction; any further edit re-pins + re-logs.

## Record correction, 2026-09-24 (EMSE R1 audit; the checker code is unchanged)

- contract_checker.py sha256 is still e9e0dbbfba9985924717d30265b4200514bb9d442a1429b16a49566e024673bf; selftest.py 19 passed, 0 failed (2026-09-24).
- canonical.py is imported by the checker and was not pinned above. sha256 52ac4d84e07cb3058c5b93a131e4f28b58c92e5fe83ee63ee334a59d2925e9c3 (file mtime 2026-06-23 16:21).
- frozen_date above is the v2 freeze. File mtimes show contract_checker.py and this file last changed on 2026-06-26 16:21 (the v3 re-pin). That is after the ROBUST contract library (contract_library.json, 2026-06-23 16:08) and after the blind-brief study (blind_briefs.json, 2026-06-26 14:25). The independent re-derivations (ws1_*.json, ws1b_*.json, ws3_*.json from 2026-06-26 17:11; ws1c_*.json 2026-06-27) and the final scoring (scoreable_cases.json, canonical_numbers.json, 2026-06-30) ran on the v3 checker.
- v3 does not contain the hash-versus-semver version rule that the paper describes as removed: interface_hash is read but not used. This file does not record when that rule was removed; it was removed at or before v3.
- Both removals (free-text preconditions, hash-versus-semver) can only reduce the findings the checker produces.
- Case encodings were corrected after the v3 pin (independent-reconstruction corrections, June 2026; mechanism and faithfulness audits, September 2026).

## Current package identity clarification (successor to V24-R1b)

The historical pins and chronology above are retained as dated records. The canonical.py hash in the 2026-09-24 entry identifies its historical bytes; it is not the hash of the current packaged copy.

- Current `contract_checker.py` SHA-256: `e9e0dbbfba9985924717d30265b4200514bb9d442a1429b16a49566e024673bf` (unchanged).
- Current `canonical.py` SHA-256: `de9842449619251c6432aed2df61008e140094cdeefd354aaa63fad2c07faba0`.
- Historical `canonical.py` SHA-256: `52ac4d84e07cb3058c5b93a131e4f28b58c92e5fe83ee63ee334a59d2925e9c3`; those bytes remain in `../../pathb_v2/historical_boundary/v22_r1/pathb/checker/canonical.py`.
- The change is recorded in `../../pathb_v2/FREEZE.json` for `../pathb/checker/canonical.py` at `2026-10-02T09:42:27.116535+00:00`. Its three-line module-docstring correction describes the existing scale-pair unit rule accurately; executable statements are unchanged. This is a post-outcome documentation amendment, not a new historical freeze or a new checker result.

Use the current hashes above to identify these two packaged Python files. Use the original dated entries and the amendment history to trace their earlier identities. The package manifest separately covers the bytes of this note and the other release files.
