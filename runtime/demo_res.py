import rclpy, time, math, sys
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
def yaw(o):
    q=o.pose.pose.orientation
    return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
class Demo(Node):
    def __init__(self,cmds):
        super().__init__("res_demo"); self.cmds=cmds
        self.pubs=[self.create_publisher(Twist,"cmd_vel",10) for _ in cmds]
        self.x=None; self.yw=None
        self.create_subscription(Odometry,"odom",self.cb,10)
        self.create_timer(0.05,self.tick)
    def cb(self,m): self.x=m.pose.pose.position.x; self.yw=yaw(m)
    def tick(self):
        for p,c in zip(self.pubs,self.cmds):
            t=Twist(); t.linear.x=float(c[0]); t.angular.z=float(c[1]); p.publish(t)
def run(cmds,secs=4.0):
    d=Demo(cmds); t0=time.time()
    while d.x is None and time.time()-t0<6: rclpy.spin_once(d,timeout_sec=0.1)
    x0,y0=d.x,d.yw; t0=time.time()
    while time.time()-t0<secs: rclpy.spin_once(d,timeout_sec=0.05)
    x1,y1=d.x,d.yw; d.destroy_node(); return x1-x0,y1-y0
rclpy.init()
if sys.argv[1]=="single":
    dx,dy=run([(0.2,0.0)]); print(f"SINGLE writer (forward x=0.2): dx={dx:.3f}m dyaw={dy:.3f}rad",flush=True)
else:
    dx,dy=run([(0.2,0.0),(0.0,1.5)]); print(f"TWO writers /cmd_vel (forward x=0.2 || rotate yaw=1.5): dx={dx:.3f}m dyaw={dy:.3f}rad",flush=True)
rclpy.shutdown()
