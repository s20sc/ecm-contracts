import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String
import time

def run(pub_rel, sub_rel, secs=4.0):
    rclpy.init()
    n = Node("qos_demo")
    pub_q = QoSProfile(depth=10); pub_q.reliability = pub_rel
    sub_q = QoSProfile(depth=10); sub_q.reliability = sub_rel
    pub = n.create_publisher(String, "qos_topic", pub_q)
    got = {"n": 0}
    n.create_subscription(String, "qos_topic", lambda m: got.__setitem__("n", got["n"]+1), sub_q)
    sent = {"n": 0}
    def tick():
        m = String(); m.data = "x"; pub.publish(m); sent["n"] += 1
    n.create_timer(0.05, tick)  # 20 Hz
    t0 = time.time()
    while time.time() - t0 < secs:
        rclpy.spin_once(n, timeout_sec=0.05)
    n.destroy_node(); rclpy.shutdown()
    return sent["n"], got["n"]

R = ReliabilityPolicy.RELIABLE; BE = ReliabilityPolicy.BEST_EFFORT
s1, g1 = run(BE, R)
print(f"INCOMPATIBLE  (BEST_EFFORT pub -> RELIABLE sub): sent={s1} received={g1}")
s2, g2 = run(R, R)
print(f"MATCHED       (RELIABLE pub -> RELIABLE sub):     sent={s2} received={g2}")
