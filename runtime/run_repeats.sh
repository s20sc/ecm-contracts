#!/usr/bin/env bash
# Run the two Path A live-ROS2 demos five times each and print their outcomes.
# Requires a sourced ROS2 Humble environment (e.g. `source /opt/ros/humble/setup.bash`)
# and, for the resource demo, the turtlebot3_gazebo simulation.
#
# Usage:  source /opt/ros/humble/setup.bash && ./run_repeats.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export QT_QPA_PLATFORM=offscreen

echo "=== QoS demo x5 (pure DDS, no gazebo) ==="
for i in 1 2 3 4 5; do
  python3 "$HERE/demo_qos.py" 2>/dev/null | grep -E "INCOMPATIBLE|MATCHED"
done

echo "=== Res demo x5 (gazebo) ==="
pkill -f gzserver 2>/dev/null; sleep 2
xvfb-run -a ros2 launch turtlebot3_gazebo empty_world.launch.py >/dev/null 2>&1 &
sleep 50
for i in 1 2 3 4 5; do
  python3 "$HERE/demo_res.py" single 2>/dev/null
  python3 "$HERE/demo_res.py" two    2>/dev/null
done
pkill -f gzserver 2>/dev/null; pkill -f "ros2 launch" 2>/dev/null
echo REPEATS_DONE
