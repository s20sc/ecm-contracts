"""Diagnose the delivery count of the matched pair in the Path A QoS demo.

demo_qos.py publishes for a fixed 4 s window at 20 Hz and destroys the node as soon as
the window closes; the matched RELIABLE/RELIABLE pair reports 79 of 80. This probe tags
each message with its sequence number to show which message is missing, and re-runs both
pairs under three harness variants:

  original      same timing as demo_qos.py (timer starts immediately, fixed 4 s window)
  warmup        wait until the publisher sees a matched subscription (max 2 s), then
                publish exactly 80 messages
  warmup_drain  as warmup, then keep spinning for 1 s after the last publish

Prints one JSON object per run.
Usage: python3 qos_window_probe.py [repeats]
"""
import json
import os
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

RATE_HZ = 20.0
WINDOW_S = 4.0
N_MSGS = 80
VARIANTS = ("original", "warmup", "warmup_drain")
PAIRS = (("incompatible", ReliabilityPolicy.BEST_EFFORT, ReliabilityPolicy.RELIABLE),
         ("matched", ReliabilityPolicy.RELIABLE, ReliabilityPolicy.RELIABLE))


def run(pub_rel, sub_rel, variant):
    rclpy.init()
    node = Node("qos_window_probe")
    pub_q = QoSProfile(depth=10)
    pub_q.reliability = pub_rel
    sub_q = QoSProfile(depth=10)
    sub_q.reliability = sub_rel
    pub = node.create_publisher(String, "qos_probe", pub_q)
    got = []
    node.create_subscription(String, "qos_probe", lambda m: got.append(int(m.data)), sub_q)

    matched_after = None
    if variant != "original":
        t0 = time.time()
        while time.time() - t0 < 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)
            if pub.get_subscription_count() > 0:
                matched_after = round(time.time() - t0, 3)
                break

    sent = []

    def tick():
        if variant != "original" and len(sent) >= N_MSGS:
            return
        msg = String()
        msg.data = str(len(sent))
        pub.publish(msg)
        sent.append(len(sent))

    timer = node.create_timer(1.0 / RATE_HZ, tick)
    t0 = time.time()
    if variant == "original":
        while time.time() - t0 < WINDOW_S:
            rclpy.spin_once(node, timeout_sec=0.05)
    else:
        while len(sent) < N_MSGS and time.time() - t0 < WINDOW_S + 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)
    timer.cancel()

    if variant == "warmup_drain":
        t1 = time.time()
        while time.time() - t1 < 1.0:
            rclpy.spin_once(node, timeout_sec=0.05)

    node.destroy_node()
    rclpy.shutdown()
    return {"variant": variant, "sent": len(sent), "received": len(got),
            "missing_seq": sorted(set(sent) - set(got)), "matched_after_s": matched_after}


def main():
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    env = {"ros_distro": os.environ.get("ROS_DISTRO"),
           "rmw": os.environ.get("RMW_IMPLEMENTATION", "default")}
    for pair, pub_rel, sub_rel in PAIRS:
        for variant in VARIANTS:
            for rep in range(repeats):
                out = run(pub_rel, sub_rel, variant)
                print(json.dumps({"pair": pair, "repeat": rep, **out, **env}), flush=True)


if __name__ == "__main__":
    main()
