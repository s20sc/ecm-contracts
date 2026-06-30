import rclpy, time, math
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped, PointStamped
from tf2_geometry_msgs import do_transform_point
rclpy.init(); node=rclpy.create_node('frame_mismatch')
br=StaticTransformBroadcaster(node); buf=Buffer(); TransformListener(buf,node)
# producer declares its output in frame 'base_link'; consumer (grasp/handover) expects 'camera'.
# real extrinsic: camera mounted at (0.5,0.2,0), yawed 90deg w.r.t base_link.
t=TransformStamped(); t.header.frame_id='base_link'; t.child_frame_id='camera'
t.transform.translation.x=0.5; t.transform.translation.y=0.2
yaw=math.pi/2; t.transform.rotation.z=math.sin(yaw/2); t.transform.rotation.w=math.cos(yaw/2)
br.sendTransform(t)
for _ in range(20): rclpy.spin_once(node,timeout_sec=0.05); time.sleep(0.03)
p=PointStamped(); p.header.frame_id='base_link'; p.point.x=1.0; p.point.y=0.0; p.point.z=0.0
tf=buf.lookup_transform('camera','base_link',rclpy.time.Time())
c=do_transform_point(p,tf)
naive=(1.0,0.0,0.0)  # consumer ignores frame, uses producer's raw coords as if already in 'camera'
err=math.sqrt((c.point.x-naive[0])**2+(c.point.y-naive[1])**2+(c.point.z-naive[2])**2)
print("producer point (declared frame=base_link): (1.000, 0.000, 0.000)")
print("correct, transformed into consumer frame 'camera': (%.3f, %.3f, %.3f)"%(c.point.x,c.point.y,c.point.z))
print("naive consumer (frame mismatch, raw coords):        (1.000, 0.000, 0.000)")
print("FRAME-MISMATCH ERROR = %.3f m  <- grasp/handover acts on a target off by this much (real tf2 stack)"%err)
node.destroy_node(); rclpy.shutdown()
