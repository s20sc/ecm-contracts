#!/usr/bin/env bash
# Resource conflict via the real ros2_control resource manager.
# Two ForwardCommandControllers both claim joint1/position; the controller
# manager rejects the second at runtime. Run with a sourced ROS2 Humble env.
source /opt/ros/humble/setup.bash 2>/dev/null || true
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
ros2 run controller_manager ros2_control_node --ros-args \
  -p robot_description:="$(cat res_robot.urdf)" --params-file res_controllers.yaml \
  > cm.log 2>&1 &
CM=$!; sleep 6
ros2 control load_controller ctrlA --set-state inactive >/dev/null 2>&1
ros2 control load_controller ctrlB --set-state inactive >/dev/null 2>&1
echo "=== activate ctrlA (claims joint1/position) ==="; ros2 control switch_controllers --activate ctrlA 2>&1
sleep 2
echo "=== activate ctrlB (SAME joint1/position -> expect resource conflict) ==="; ros2 control switch_controllers --activate ctrlB 2>&1
sleep 2
echo "=== controller states ==="; ros2 control list_controllers 2>&1
echo "=== resource-conflict lines ==="; grep -iE "conflict|already claimed|cannot|not available" cm.log | head
kill $CM 2>/dev/null
