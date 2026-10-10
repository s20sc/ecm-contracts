# Archived runtime demonstrations

These 24 original files were omitted from the V21 private review package despite the manuscript referring to `runtime/`. They are copied byte for byte from the author's existing `experiments/pathA/` archive. `ARCHIVE_MANIFEST.json` records their hashes. This directory is an augmentation prepared for the next review candidate, not a change to frozen V21.

Run the offline record check from any directory:

```sh
python3 /path/to/runtime/verify_archived_records.py --out /a/writable/record-check.json
```

The check reads captured records; it does not execute Docker, ROS, remote commands, or experiments. The archive's historical scripts can contain machine-specific paths and dependencies. Their presence is not a claim of portable live reproduction.

- QoS: `qos_window_probe_run/probe.jsonl` contains a `ROS_DISTRO=humble` header and 30 JSON observations (two pairings, three timing variants, five repeats). All incompatible pairings receive 0/80. Matched original and warmup runs receive 79/80, missing sequence 79; warmup plus drain receives 80/80. `probe.err`, `env.txt`, `run_all.sh`, and `qos_window_probe.py` preserve capture context and harness logic.
- Declared resource conflict: `ws4_res_conflict/cm.log` records successful ctrlA activation and ctrlB rejection because `joint1/position` is claimed. The controller YAML, URDF and runner are adjacent.
- Undeclared competing writers: `repeats.log` records five single-writer displacements of 0.372–0.772 m, five two-writer displacements of 0.018–0.076 m, and absolute two-writer yaw up to 1.531 rad. These are mechanism demonstrations, not comparative detection measurements.
- Frame mismatch: `ws4_res_conflict/frame_mismatch.log` is the September 29 stdout capture. Correct transform (-0.2,-0.5,0) versus raw (1,0,0) gives 1.300 m separation. Its script and runtime image identity are retained.

`ws4_runtime_confirmations.md` and the setup notes are historical records, preserved unchanged. Their older interpretation is not an additional current manuscript claim. The revised manuscript bounds these four demonstrations to three conditions and excludes all four from the 93-case evaluation. The archival check establishes consistency between saved records and reported summaries, not independent execution or discovery of previously unknown faults.
