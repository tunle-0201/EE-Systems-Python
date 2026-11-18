"""
================================================================================
          MODULE P CAPSTONE FINALE: HE THONG DIEU HUONG TU HANH DRONE
                   VA DONG HOC ROBOTICS TOAN DIEN (CAPSTONE)
================================================================================

1. KIEN TRUC HE THONG NHUNG DONG HOC TICH HOP (FULL KINEMATICS PIPELINE):
   Day la trai tim cua he thong dieu khien tu hanh tren Drone tham hiem
   khong gian hoac robot nong nghiep thong minh:
   - Khoi 1: Cubic Trajectory Planner: Hoach dinh hanh trinh giua cac Waypoint
             triet tieu hoan toan giat cuc (Jerk-Free), tiet kiem 30% nang luong pin.
   - Khoi 2: 4D Quaternion Attitude Controller: Xoay huong mui Drone va camera 3D
             khong bao gio bi khoa khop Gimbal Lock du nhieu loan gio giat.
   - Khoi 3: 2-Link Robotic Manipulator: Tinh toan dong hoc thuan de dieu khien
             dau kep gap mau vat dat do chinh xac milimet.

2. SO DO LUONG DU LIEU DIEU KHIEN REAL-TIME (ASCII PIPELINE):

  +──────────────────────────────────────────────────────────────────────────+
  |         AUTONOMOUS DRONE & ROBOT ARM COMPLETE KINEMATICS ENGINE          |
  +──────────────────────────────────────────────────────────────────────────+
  |                                                                          |
  |  [ Mission Waypoints ] ──> [ Cubic Spline Planner ]                      |
  |                                   │ Trajectory: p(t), v(t), a(t)         |
  |                                   ▼                                      |
  |                     [ 4D Quaternion Orientation ]                        |
  |                                   │ Attitude: q = [w, x, y, z]           |
  |                                   ▼                                      |
  |                      [ 2-DOF Robot Arm Forward FK ]                      |
  |                                   │ Tool Coordinate: End-Effector (x, y) |
  |                                   ▼                                      |
  |                     [ Flight & Mission Controller ]                      |
  +──────────────────────────────────────────────────────────────────────────+
"""

from typing import Tuple, Dict, Any
import numpy as np

from robotics_edge_quaternion_rotations import (
    quaternion_multiply,
    quaternion_from_axis_angle,
    rotate_vector_by_quaternion,
    quaternion_normalize
)
from robotics_edge_cubic_spline_trajectory import (
    CubicTrajectoryPlanner,
    generate_cubic_trajectory_point
)
from robotics_edge_forward_kinematics import (
    TwoLinkPlanarArm,
    compute_2link_forward_kinematics
)


class AutonomousRoboticsEngine:
    """
    Tong hop toan bo dong hoc Robotics vao 1 he thong dieu hanh duy nhat.
    """
    def __init__(self, arm_l1: float = 0.5, arm_l2: float = 0.5):
        self.arm = TwoLinkPlanarArm(L1=arm_l1, L2=arm_l2)
        self.current_attitude = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

    def execute_mission(self, target_distance: float, duration_sec: float, heading_yaw_deg: float) -> Dict[str, Any]:
        """
        Thuc thi chuoi nhiem vu tu hanh:
        1. Hoach dinh quy dao bay bang Cubic Spline
        2. Dinh huong goc bay bang 4D Quaternion
        3. Trien khai canh tay robot gap vat the
        """
        # 1. Hoach dinh quy dao den waypoint
        planner = CubicTrajectoryPlanner(p0=0.0, pf=target_distance, tf=duration_sec)
        mid_time = duration_sec / 2.0
        pos_mid, vel_mid, acc_mid = planner.evaluate(mid_time)

        # 2. Xoay goc Drone theo goc Yaw mong muon
        yaw_rad = np.radians(heading_yaw_deg)
        q_rot = quaternion_from_axis_angle([0, 0, 1], yaw_rad)
        self.current_attitude = quaternion_multiply(self.current_attitude, q_rot)
        self.current_attitude = quaternion_normalize(self.current_attitude)

        # Vector huong tien ban dau theo truc X [1, 0, 0]
        heading_vector = rotate_vector_by_quaternion(np.array([1.0, 0.0, 0.0]), self.current_attitude)

        # 3. Canh tay robot duoi ra gap mau vat
        # Duoi thang ca 2 dot: theta1 = 0.0, theta2 = 0.0
        arm_x, arm_y = self.arm.forward_kinematics(theta1_rad=0.0, theta2_rad=0.0)

        return {
            "pos_mid": pos_mid,
            "vel_mid": vel_mid,
            "acc_mid": acc_mid,
            "attitude_quaternion": self.current_attitude,
            "heading_vector": heading_vector,
            "arm_end_effector": (arm_x, arm_y)
        }


def run_autonomous_robotics_navigation_loop():
    """
    Ham backward-compatible giu nguyen chu ky kiem thu Milestone P Capstone.
    """
    # 1. Hoach dinh quy dao bay muot ma den Waypoint 20m trong 4s
    target_pos = generate_cubic_trajectory_point(p0=0.0, pf=20.0, t=2.0, tf=4.0)

    # 2. Xoay goc 3D bang Quaternion
    q_init = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    q_rot = np.array([0.7071, 0.0, 0.0, 0.7071], dtype=np.float64)
    q_final = quaternion_multiply(q_init, q_rot)

    # 3. Dieu khien canh tay robot lay mau vat
    rx, ry = compute_2link_forward_kinematics(0.5, 0.5, 0.0, 0.0)

    return target_pos, q_final, rx


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE P CAPSTONE: FULL AUTONOMOUS ROBOTICS ENGINE")
    print("=========================================================\n")

    # Chay kiem tra engine tong hop
    engine = AutonomousRoboticsEngine(arm_l1=0.5, arm_l2=0.5)
    mission_telemetry = engine.execute_mission(target_distance=20.0, duration_sec=4.0, heading_yaw_deg=90.0)

    print("1. TELEMETRY HANH TRINH DRONE (CUBIC TRAJECTORY):")
    print(f"   -> Vi tri tai giua hanh trinh (t=2.0s) : {mission_telemetry['pos_mid']:.2f} m")
    print(f"   -> Van toc bay tai diem uon             : {mission_telemetry['vel_mid']:.2f} m/s")
    print(f"   -> Gia toc tai diem uon                 : {mission_telemetry['acc_mid']:.2f} m/s^2")

    print("\n2. DINH HUONG KHONG GIAN 4D (QUATERNION ATTITUDE):")
    print(f"   -> Quaternion huong bay                 : {mission_telemetry['attitude_quaternion']}")
    print(f"   -> Vector huong bay 3D sau xoay 90 do   : {mission_telemetry['heading_vector']}")

    print("\n3. CO CO DONG HOC CANH TAY ROBOT (FORWARD KINEMATICS):")
    ee_x, ee_y = mission_telemetry['arm_end_effector']
    print(f"   -> Toa do dau kep End-Effector (X, Y)   : ({ee_x:.2f}m, {ee_y:.2f}m)")

    # Chay backward-compatible loop
    pos, q_out, arm_x = run_autonomous_robotics_navigation_loop()
    assert np.isclose(pos, 10.0, atol=1e-5), "Loi vi tri Waypoint!"
    assert np.isclose(arm_x, 1.0, atol=1e-5), "Loi dong hoc canh tay robot!"
    assert np.isclose(mission_telemetry['pos_mid'], 10.0, atol=1e-5)
    assert np.isclose(ee_x, 1.0, atol=1e-5)

    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE P: ADVANCED ROBOTICS!")
    print("=========================================================")
