#!/usr/bin/env bash
source /root/ros_env.sh; export QT_QPA_PLATFORM=offscreen
echo "=== QoS demo x5 (pure DDS, no gazebo) ==="
for i in 1 2 3 4 5; do python3 /root/autodl-tmp/p5_pathA/demo_qos.py 2>/dev/null | grep -E "INCOMPATIBLE|MATCHED"; done
echo "=== Res demo x5 (gazebo) ==="
pkill -f gzserver 2>/dev/null; sleep 2
xvfb-run -a ros2 launch turtlebot3_gazebo empty_world.launch.py >/dev/null 2>&1 &
sleep 50
for i in 1 2 3 4 5; do python3 /root/autodl-tmp/p5_pathA/demo_res.py single 2>/dev/null; python3 /root/autodl-tmp/p5_pathA/demo_res.py two 2>/dev/null; done
pkill -f gzserver 2>/dev/null; pkill -f "ros2 launch" 2>/dev/null
echo REPEATS_DONE
