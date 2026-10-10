# WS4 Runtime-Confirmation Reproduction (box setup)

The WS4 cross-dimension live runtime confirmations (Resource via `ros2_control`,
Signature via `tf2`) were run on a throwaway GPU box (Ubuntu 22.04, ROS 2 Humble,
ros2_control 2.54.0). The box has been released; this directory records how it was
built so the experiments reproduce on any fresh Ubuntu 22.04 host.

## 1. Install ROS 2 Humble + ros2_control + tf2 (`setup_box.sh` below)

The only non-obvious step: the official `raw.githubusercontent.com/ros/rosdistro/.../ros.key`
is often unreachable from mainland-China hosts, leaving the repo unsigned and all
`ros-humble-*` packages "Unable to locate". Use the TUNA mirror for the repo and fetch
the key with fallbacks.

```bash
#!/usr/bin/env bash
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl gnupg lsb-release software-properties-common locales
locale-gen en_US en_US.UTF-8
add-apt-repository -y universe
KEY=/usr/share/keyrings/ros-archive-keyring.gpg
for url in \
  "https://raw.githubusercontent.com/ros/rosdistro/master/ros.key" \
  "https://ghproxy.net/https://raw.githubusercontent.com/ros/rosdistro/master/ros.key" \
  "https://gitee.com/mirrors/rosdistro/raw/master/ros.key"; do
  curl -fsSL --connect-timeout 15 "$url" -o "$KEY" && [ -s "$KEY" ] && break
done
CODE=$(. /etc/os-release && echo $VERSION_CODENAME)   # jammy
echo "deb [arch=amd64 signed-by=$KEY] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu $CODE main" \
  > /etc/apt/sources.list.d/ros2.list
apt-get update -y
apt-get install -y ros-humble-ros-base ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-controller-manager ros-humble-forward-command-controller \
  ros-humble-joint-state-broadcaster ros-humble-joint-trajectory-controller \
  ros-humble-tf2-ros ros-humble-tf-transformations ros-humble-rmw-cyclonedds-cpp \
  python3-colcon-common-extensions python3-pip
```

Note: the Resource experiment uses `mock_components/GenericSystem` (ships with
`ros-humble-ros2-control`), so **Gazebo is not required**.

## 2. Environment (`ros_env.sh`)

```bash
unset PYTHONPATH; conda deactivate 2>/dev/null || true
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

## 3. Run the experiments

The experiment files are in `../ws4_res_conflict/`:
- Resource: `res_robot.urdf` + `res_controllers.yaml` + `run_res_conflict.sh`
  → two `ForwardCommandController`s both claiming `joint1/position`; the controller
  manager rejects the second with `Resource conflict ... 'joint1/position' is already claimed`.
- Signature: `frame_mismatch.py` → publishes a `base_link`→`camera` static transform,
  looks up and transforms a point through the real `tf2` stack, and reports the
  1.30 m error a frame-ignoring consumer would incur.

Captured output is in `../ws4_res_conflict/cm.log` and `../ws4_res_conflict/ws4_res_conflict_evidence.txt`.
