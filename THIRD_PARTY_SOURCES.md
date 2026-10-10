# Third-party source attribution

Third-party sources retain their original copyright and license terms. The
repository's MIT license applies only where the authors have the right to
license the material. Source files and original provenance receipts remain
unchanged. The existing content-addressed snapshot asset retains upstream
license files through its per-task manifests; rebuilding a selected task must
not be described as a new grant of rights.

| Material | Source basis and notice |
| --- | --- |
| CPython 3.12 `importlib.metadata` and six helpers | Commit `0fb18b02c8ad56299d6a2910be0bab8ad601ef24`; source-intake receipts preserve exact URLs and hashes. See `third-party-notices/CPython-3.12.0-LICENSE.txt`. |
| Earlier CPython, rosidl, and ros2cli retained sources | Original task snapshots and their accompanying license files remain in `snapshots.zip` and `snapshots.json`. Delivery restoration selects unchanged source bytes, not a relicensed fork. |
| mavros visualization/distance-sensor/configuration slices | Original file headers point to the repository terms. Pinned notices describe BSD/GPLv3/LGPLv3 alternatives; the BSD text is included. Exact source revisions remain in source receipts. |
| kobuki source slices | Original BSD declaration and copyright retained; license texts fetched at tag `0.6.3` and commit `b166c93913e293c55a3faa7b298c5f52f6def964`. |
| rclpy subscription and nan_publisher | Original Apache-2.0 file headers retained; the Apache-2.0 text from the pinned rclpy source is included. |
| MoveIt and tf2 source slices | Full BSD notices and copyright are present in the retained file headers. |
| geometry2 issue #727 attached example | Original attachment URL and SHA256 retained; its `package.xml` declares `BSD`, without identifying a specific BSD variant or real author (name fields are placeholders). Preserve this limited declaration and the original source attribution; do not invent an author or a more specific license grant. The attachment was inspected in memory; no additional ZIP is stored. |

`third-party-notices/source-receipt.json` records the pinned URLs, retrieval
status, file size and SHA256 for the added notices. The issue-attachment package
metadata is retained separately. These records document the source material;
they do not certify historical runtime results or annotation correctness.
