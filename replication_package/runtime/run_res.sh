#!/usr/bin/env bash
source /root/ros_env.sh; export QT_QPA_PLATFORM=offscreen
pkill -f gzserver 2>/dev/null; pkill -f 'ros2 launch' 2>/dev/null; sleep 3
xvfb-run -a ros2 launch turtlebot3_gazebo empty_world.launch.py > /root/autodl-tmp/p5_pathA/res_launch.log 2>&1 &
sleep 50
echo "=== Resource-conflict runtime demo (/cmd_vel single-owner) ==="
python3 /root/autodl-tmp/p5_pathA/demo_res.py single 2>/root/autodl-tmp/p5_pathA/res_err.log
python3 /root/autodl-tmp/p5_pathA/demo_res.py two 2>>/root/autodl-tmp/p5_pathA/res_err.log
pkill -f gzserver 2>/dev/null; pkill -f 'ros2 launch' 2>/dev/null
echo "RES_DEMO_DONE"
