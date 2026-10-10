#!/bin/bash
set -u
IMG=ros:humble-ros-base
{ echo "image: $(docker image inspect $IMG --format "{{index .RepoDigests 0}}")"; echo "host: $(hostname) $(lsb_release -ds) docker $(docker --version | cut -d" " -f3 | tr -d ,)"; date -Is; } > env.txt
for i in 1 2 3 4 5; do
  docker run --rm -v "$PWD":/w $IMG bash -lc "source /opt/ros/humble/setup.bash && python3 /w/demo_qos.py" >> original_demo.txt 2>&1
done
docker run --rm -v "$PWD":/w $IMG bash -lc "source /opt/ros/humble/setup.bash && echo ROS_DISTRO=\$ROS_DISTRO && python3 /w/qos_window_probe.py 5" > probe.jsonl 2> probe.err
echo DONE >> env.txt
