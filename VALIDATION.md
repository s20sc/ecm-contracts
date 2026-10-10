# Validation of this publication representation

The scientific package is byte-identical to the locally validated reader edition of 9 October 2026. The complete primary numerical replay returned `verified`; later historical/current boundary replays matched their own complete seven-case reference records, and the mechanism ledger comparison had no scientific or structural differences. Validation is on the original host, not independent-machine reproduction.

The supplementary source assessment was then run against these exact package bytes. Its control, boundary, exclusion and primary-reaggregation results equal the retained source-assessment analysis in full. Only the two input/module receipt maps differ, because they use portable paths and current publication hashes and include the additional evidence inventory. See EVIDENCE_COMPLETION_RESULTS.json and EVIDENCE_COMPLETION_VALIDATION.json.

Five bounded integration tests passed, covering the baseline, tampered source, a nonverbatim quote despite an updated inventory, a missing method despite an updated inventory, and an output inside the input directory. Independent code review approved the addition and reproduced identical full output after moving both input trees to a path containing spaces and running from another working directory. Input hashes were unchanged after execution.

The existing snapshot asset's SHA256 and size were verified again before release. No new full archive was created. Browsable code, data, selected sources and documentation are ordinary Git files; the original complete source snapshot remains a separate offline input, not a ZIP of this repository.

Current inventories verify file identity and the calculations above. They do not establish historical blinding, independent human reference labels, missing historical runtime outcomes, or whole-paper acceptance. Third-party source notices and scientific model provenance remain intact.
