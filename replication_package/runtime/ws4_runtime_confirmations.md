# WS4: Cross-Dimension Live Runtime Confirmations (new AutoDL box, RTX 5090)

Environment: Ubuntu 22.04, ROS 2 Humble, ros2_control 2.54.0, real tf2 stack.
Each experiment runs the documented failure mechanism through the ACTUAL production
ROS 2 machinery (not a mock of our own checker) and observes the failure live.
This file documents the two NEW confirmations (resource and signature). Together with the
pre-existing QoS/behavioral confirmation in the main Path A code, the live runtime evidence
now spans three dimensions (behavioral, resource, signature).

## 1. Resource dimension (ros2_control command-interface conflict)
Setup: minimal ros2_control system (mock_components/GenericSystem, one joint), two
ForwardCommandControllers (ctrlA, ctrlB) each declaring joint1/position as its command
interface (res_robot.urdf + res_controllers.yaml). Activate ctrlA, then ctrlB.

Observed (controller_manager log, cm.log):
  [INFO]  [ctrlA]: activate successful
  [ERROR] [controller_manager]: Resource conflict for controller 'ctrlB'.
          Command interface 'joint1/position' is already claimed.
  [ERROR] [controller_manager]: Could not activate controller : 'ctrlB'
Result: the real ros2_control resource manager rejects the second claimant at runtime,
exactly the "already claimed" failure documented in B-Res-02/03/04. The ECM Resource
contract (exclusive command-interface ownership) predicts this statically before deploy.

## 2. Signature dimension (coordinate-frame mismatch)
Setup: producer declares a point in frame base_link; consumer expects frame camera.
Real extrinsic (camera at (0.5,0.2,0), yaw 90 deg) published via tf2 StaticTransform-
Broadcaster; lookup + do_transform_point through the real tf2 buffer (frame_mismatch.py).

Observed:
  producer point (declared frame=base_link):           (1.000, 0.000, 0.000)
  correct, transformed into consumer frame 'camera':   (-0.200, -0.500, 0.000)
  naive consumer (frame mismatch, raw coords):          (1.000, 0.000, 0.000)
  FRAME-MISMATCH ERROR = 1.300 m
Result: a frame mismatch the ECM Signature contract (frame field) catches statically
produces a 1.30 m end-effector error at runtime through the real tf2 stack.

## Files
  ws4_res_conflict/res_robot.urdf, res_controllers.yaml, run_res_conflict.sh, cm.log
  ws4_res_conflict/frame_mismatch.py
  ws4_res_conflict_evidence.txt
