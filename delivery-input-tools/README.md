# Restore the selected replay inputs

Use the existing snapshot archive and V32 scientific package. This utility
verifies the archive SHA256, selects the 51 files in the delivery runtime's
public manifest, restores 48 snapshot files from content-addressed blobs and
3 reconstructions from the scientific package, and verifies every restored
file. The current total is 181,251 bytes. It never extracts the entire archive.
No source is downloaded, no software is installed, and no archive is created.

```sh
python3 -B restore_retained.py \
  --manifest /path/to/delivery-runtime/public-inputs.json \
  --archive /path/to/existing/snapshots.zip \
  --package /path/to/replication_package \
  --out /path/to/new/retained-tasks
```

Set the runtime configuration's `retained` path to this new directory, then
run the `verify`, `prepare`, and `run` commands documented in
`../delivery-runtime/README.md`. The intake directory is distributed separately
with its CPython source and origin receipts. A successful restoration writes
`restore-receipt.json`; failure leaves the partial output and a failure receipt.
Do not reuse an incomplete output directory. Existing output directories and
symlinks are rejected.

The runtime has been tested locally with Python 3.11.2 on macOS, including the
six-cell contrast, three-cell adaptive client, and four-cell boundary replay.
It uses POSIX conventions and has not been verified on Windows or a separately
provisioned machine. Restoring source content and relocating paths does not
reproduce the historical host's installed software. Preserve original evidence
and interpret newly generated observations within their recorded environment.
