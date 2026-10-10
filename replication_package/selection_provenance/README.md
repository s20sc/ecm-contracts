# ROBUST C1 selection reconstruction

This supplement, added on 3 October 2026, reproduces the selection of the 92 retained C1 records from all 221 upstream ROBUST `.bug` records. It does not change the selected records, their ordering, any S1/S2/adjudication label, the original protocol, or its freeze manifest.

The upstream repository is `https://github.com/robust-rosin/robust`, pinned to commit `521fe75319c256995fae6f5a4b756f0bfa4bf65e`. `selection-lock.json` records the exact archive URL/hash and the individual hashes of all 221 records. It also pins the historical extractor, restored at the path named by the original protocol: `experiments/pathb/extract_robust.py`.

That extractor is preserved byte for byte from the workspace copy. Its original comments claiming prior commitment, blinding and third-party gold labels are historical assertions, not evidence that this reconstruction verifies. The `gold_dimension` fields are legacy selection metadata, not independently human-validated failure labels for the current study.

## Run the independent selection check

Use Python with PyYAML, as required by the historical extractor. Obtain the exact archive at the URL in `selection-lock.json`, then run from the replication-package root:

```sh
python3 selection_provenance/verify_robust_selection.py \
  --archive /path/to/upstream.tar.gz \
  --output /path/to/selection-verification.json
```

The verifier uses no network and never extracts or executes upstream repository files. It checks the archive, extractor and individual record hashes, applies the original fault-code crosswalk and classification-tag fallback, and compares every selected record field with the retained input. Comparison is insensitive to the top-level case ordering but preserves JSON scalar types, missing fields and nested array ordering. Neither the selected input nor the scientific results are rewritten.

The reconstruction gives 92 identical records and seven tag-fallback cases. Those cases could not be reconstructed from `robust_cases.json` alone because that file retains `fault_codes` but omits upstream `classification` strings. The report records the seven original classification strings and their resulting legacy dimensions. Confidential or absent fix information is preserved; it is not grounds for removing records before the eligibility funnel.

This check establishes reproducibility against the pinned upstream revision. It does not establish that this was the upstream revision used historically, when the selector was committed, whether selection was blinded, or the correctness of subsequent model-written specifications. The retained array matches the traversal order of the pinned archive. The verifier compares records independently of top-level ordering; the original array is retained unchanged.

The main `reproduce.py` entry point starts from the retained selected inputs and remains unchanged. Run this additional check to verify the upstream selection step. The upstream archive is not bundled here; public deposition and licensing review of the overall revision remain pending.
