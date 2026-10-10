# QoS window probe: why the matched pair delivers 79 of 80

Question (reviewer): in the Path A QoS demo the matched RELIABLE→RELIABLE composition delivers 79 of 80 messages. Which message is missing, and why?

## Setup

- Host: office-rog, Ubuntu 24.04.5 LTS, Docker 29.1.3 (see `env.txt`).
- Image: `ros@sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138` (`ros:humble-ros-base`), default RMW.
- `run_all.sh`: the unchanged `demo_qos.py` five times (`original_demo.txt`), then `qos_window_probe.py 5` (`probe.jsonl`, stderr in `probe.err`).
- The probe tags each message with its sequence number and runs three harness variants per composition, five repeats each: `original` (same timing as `demo_qos.py`), `warmup` (wait until the publisher sees a matched subscription, then publish exactly 80), `warmup_drain` (as `warmup`, then spin 1 s after the last publish).

## Result (run 2026-09-24)

| Composition | original | warmup | warmup_drain |
|---|---|---|---|
| matched (RELIABLE → RELIABLE) | 79/80, missing seq 79 (5/5 runs) | 79/80, missing seq 79 (5/5) | 80/80 (5/5) |
| incompatible (BEST_EFFORT → RELIABLE) | 0/80 (5/5) | 0/80 (5/5) | 0/80 (5/5) |

The unchanged `demo_qos.py` reproduces its original figures on this host: 0/80 and 79/80 in all five runs.

## Reading

The missing message is always the last one (sequence 79). It is published in the final timer callback, and the harness stops spinning and destroys the node before the subscription callback for it runs. Waiting for discovery before the first publish does not change the count, so the first message is not the one lost; spinning for one more second after the last publish delivers all 80. The 79 is therefore an artifact of the measurement window, not a delivery failure. The incompatible composition delivers no message under any variant, including with the drain, so the contract's prediction does not depend on the window.
