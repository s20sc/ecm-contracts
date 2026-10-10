"""Self-test for contract_checker. Verifies each dimension's check fires AND the
honest baseline contrasts the revision depends on. Run: python3 selftest.py

Crucially asserts the ADVERSARIAL-FIX facts:
 (a) a pure-QoS Beh case is ALSO caught by schema+QoS  -> ECM has NO QoS marginal
     (so Beh's real marginal must come from non-QoS sub-properties),
 (b) a frame mismatch is NOT caught by schema-only OR schema+QoS -> real Sig marginal,
 (c) a Ver interface-field-break upgrade is missed by semver-only -> real Ver marginal,
 (d) rate_starvation (non-QoS Beh) is missed by schema+QoS       -> the Beh that survives.
"""
from contract_checker import (
    ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY, predicts, all_findings)

PASS, FAIL = 0, 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


def flagged(case, method):
    return predicts(case, method)["flagged"]


print("== Sig: frame mismatch (ECM real marginal over BOTH baselines) ==")
frame_case = {
    "type": "PAIR", "gold_dimension": "Sig",
    "producer": {"outputs": [{"role": "scan", "msg_type": "sensor_msgs/LaserScan", "frame": "map"}]},
    "consumer": {"inputs": [{"role": "scan", "msg_type": "sensor_msgs/LaserScan", "frame": "base_link"}]},
    "edge": {"out_role": "scan", "in_role": "scan"},
}
check("ECM-full flags frame mismatch", flagged(frame_case, ECM_FULL))
check("schema-only MISSES frame mismatch (type identical)", not flagged(frame_case, SCHEMA_ONLY))
check("schema+QoS MISSES frame mismatch (no frame check)", not flagged(frame_case, SCHEMA_QOS))
check("ECM attributes to Sig", predicts(frame_case, ECM_FULL)["attributed"])

print("== Beh QoS reliability (HONEST: schema+QoS ALSO catches it) ==")
qos_case = {
    "type": "PAIR", "gold_dimension": "Beh",
    "producer": {"outputs": [{"role": "t", "msg_type": "std_msgs/String",
                              "qos": {"reliability": "best_effort"}}]},
    "consumer": {"inputs": [{"role": "t", "msg_type": "std_msgs/String",
                             "qos": {"reliability": "reliable"}}]},
    "edge": {"out_role": "t", "in_role": "t"},
}
check("ECM-full flags QoS reliability", flagged(qos_case, ECM_FULL))
check("schema-only MISSES QoS (type only)", not flagged(qos_case, SCHEMA_ONLY))
check("schema+QoS CATCHES QoS  <-- ECM has NO marginal here", flagged(qos_case, SCHEMA_QOS))

print("== Beh non-QoS: rate starvation (the Beh that SURVIVES vs schema+QoS) ==")
rate_case = {
    "type": "PAIR", "gold_dimension": "Beh",
    "producer": {"outputs": [{"role": "scan", "msg_type": "sensor_msgs/LaserScan", "rate_hz": 2}]},
    "consumer": {"inputs": [{"role": "scan", "msg_type": "sensor_msgs/LaserScan", "min_rate_hz": 15}]},
    "edge": {"out_role": "scan", "in_role": "scan"},
}
check("ECM-full flags rate starvation", flagged(rate_case, ECM_FULL))
check("schema+QoS MISSES rate starvation (non-QoS Beh) <-- ECM real Beh marginal",
      not flagged(rate_case, SCHEMA_QOS))

print("== Res: exclusive lock conflict (ECM-only) ==")
res_case = {
    "type": "CONCURRENT", "gold_dimension": "Res",
    "producer": {"exclusive": ["/cmd_vel"], "outputs": [{"role": "c", "msg_type": "geometry_msgs/Twist"}]},
    "consumer": {"exclusive": ["/cmd_vel"], "inputs": [{"role": "c", "msg_type": "geometry_msgs/Twist"}]},
    "edge": {"out_role": "c", "in_role": "c"},
}
check("ECM-full flags /cmd_vel lock conflict", flagged(res_case, ECM_FULL))
check("schema-only MISSES lock conflict", not flagged(res_case, SCHEMA_ONLY))
check("schema+QoS MISSES lock conflict", not flagged(res_case, SCHEMA_QOS))

print("== Ver: interface-field-break upgrade (a renamed/changed field the consumer reads; semver-only fooled) ==")
ver_case = {
    "type": "UPGRADE", "gold_dimension": "Ver",
    "old": {"interface_hash": "aaa", "semver": "1.0.0"},
    "new": {"interface_hash": "bbb", "semver": "1.1.0", "changed_fields": ["pose"]},
    "consumer_reads": ["pose"],
}
check("ECM-full flags breaking upgrade", flagged(ver_case, ECM_FULL))
check("semver-only MISSES it (minor bump trusted) <-- ECM real Ver marginal",
      not flagged(ver_case, SEMVER_ONLY))
ecm_checks = set(predicts(ver_case, ECM_FULL)["check_types"])
check("ECM uses field_break (a named changed field is read by the consumer)", {"field_break"} <= ecm_checks)

print("== Shared baseline floor: a plain type mismatch is caught by ALL ==")
type_case = {
    "type": "PAIR", "gold_dimension": "Sig",
    "producer": {"outputs": [{"role": "x", "msg_type": "sensor_msgs/Image"}]},
    "consumer": {"inputs": [{"role": "x", "msg_type": "sensor_msgs/LaserScan"}]},
    "edge": {"out_role": "x", "in_role": "x"},
}
check("ECM-full flags type mismatch", flagged(type_case, ECM_FULL))
check("schema-only flags type mismatch", flagged(type_case, SCHEMA_ONLY))
check("schema+QoS flags type mismatch", flagged(type_case, SCHEMA_QOS))

print("== Negative control: a fully-compatible pair is accepted by ECM ==")
good_case = {
    "type": "PAIR", "gold_dimension": None,
    "producer": {"outputs": [{"role": "t", "msg_type": "std_msgs/String", "frame": "map",
                              "qos": {"reliability": "reliable"}, "rate_hz": 30}]},
    "consumer": {"inputs": [{"role": "t", "msg_type": "std_msgs/String", "frame": "map",
                             "qos": {"reliability": "reliable"}, "min_rate_hz": 10}]},
    "edge": {"out_role": "t", "in_role": "t"},
}
check("ECM-full ACCEPTS the good pair (no false positive)", not flagged(good_case, ECM_FULL))

print(f"\n==== {PASS} passed, {FAIL} failed ====")
import sys
sys.exit(1 if FAIL else 0)
