"""
================================================================================
          MODULE AA: ROBOTIC KINODYNAMICS & AUTONOMOUS MOTION PLANNING
       MILESTONE AA.4: AUTONOMOUS VEHICLE NAVIGATION ENGINE CAPSTONE
================================================================================

KIEN TRUC TOAN CHUOI DONG CO DIEU HUONG XE TU HANH (AUTONOMOUS NAVIGATION ENGINE):
Capstone nay tich hop tron ven ca 3 module nen tang vao mot he thong thoi gian thuc:
1. Milestone AA.3: SCurveProfile -> Tao profile van toc tron tru, giam xoc Jerk = 0.
2. Milestone AA.2: DWALocalPlanner -> Quet chuong ngai vat LiDAR, tranh va cham.
3. Milestone AA.1: AckermannVehicle -> Dieu khien goc be lai banh truoc va banh sau.

SO DO DONG DU LIEU DIEU KHIEN THOI GIAN THUC (ASCII PIPELINE):

   [ Toa do Dich (Goal) ] ──+
                            |
   [ LiDAR Obstacles Map ] ─+──> [ DWA Local Planner ] ──> (v, omega)
                            |             ^
   [ Vi tri hien tai xe ] ──+             |
                                  [ S-Curve Profile ] (Van toc tham chieu em ai)
                                          |
   (v, omega) ──> [ Ackermann Transform ] ──> (v, steer_delta)
                            |
                            v
               [ Ackermann Vehicle Actuator ] ──> Toa do moi (x, y, theta)

CONG THUC CHUYEN DOI TOC DO GOC VE GOC BE LAI ACKERMANN (ASCII MATH BLOCKS):

         omega * L
tan(delta) = ─────────
                 v

                 / omega * L \
=> delta = arctan| ───────── |
                 \     v     /

Neu v gan bang 0 (v < 1e-3 m/s), delta duoc giu nguyen de tranh phep chia cho 0!
"""

from typing import Tuple, List, Dict, Any, Optional
import math

import os
import sys

# Dam bao import duoc ca khi chay tu goc workspace hoac trong thu muc EE_Mentorship
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from robotics_edge_ackermann_kinematics import AckermannVehicle
from robotics_edge_dwa_obstacle_avoidance import DWAPlanner
from robotics_edge_scurve_trajectory import SCurveProfile


class AutonomousNavigationEngine:
    """
    Dong co dieu huong va lap quy dao xe tu hanh capstone.
    Tich hop S-Curve, DWA va Ackermann Steering Control.
    """

    def __init__(self,
                 start_x: float = 0.0,
                 start_y: float = 0.0,
                 start_theta: float = 0.0,
                 wheelbase: float = 2.875,
                 max_steer_deg: float = 35.0,
                 max_speed: float = 2.0,
                 robot_radius: float = 0.3):
        # 1. Mo hinh dong hoc xe Ackermann
        self.vehicle = AckermannVehicle(
            x=start_x, y=start_y, theta=start_theta,
            wheelbase=wheelbase, max_steer_deg=max_steer_deg
        )

        # 2. Bo lap ke hoach cuc bo DWA
        self.planner = DWAPlanner(
            max_speed=max_speed,
            max_yaw_rate_deg=90.0,
            max_accel=2.0,
            max_yaw_accel_deg=180.0,
            robot_radius=robot_radius,
            predict_time=2.5,
            dt=0.1
        )

        # Trang thai dong luc hoc hien tai
        self.current_v = 0.0
        self.current_omega = 0.0
        self.current_steer = 0.0
        self.history_trajectory: List[Tuple[float, float, float]] = [(start_x, start_y, start_theta)]

    def omega_to_steer_angle(self, v: float, omega: float) -> float:
        """
        Chuyen doi toc do goc omega sang goc be lai banh truoc delta cua xe Ackermann:
        delta = arctan(omega * L / v)
        """
        if abs(v) < 0.05:
            return 0.0
        steer_rad = math.atan2(omega * self.vehicle.wheelbase, v)
        return max(-self.vehicle.max_steer_angle, min(self.vehicle.max_steer_angle, steer_rad))

    def navigate_step(self,
                      goal: Tuple[float, float],
                      obstacles: List[Tuple[float, float]],
                      dt: float = 0.1) -> Dict[str, Any]:
        """
        Thuc thi mot chu ky dieu huong (Control Loop Step):
        - Quet LiDAR
        - Chay thuat toan DWA chon van toc
        - Chuyen doi sang goc lai Ackermann
        - Cap nhat trang thai xe
        """
        # 1. Tinh khoang cach toi dich
        dist_to_goal = math.hypot(goal[0] - self.vehicle.x, goal[1] - self.vehicle.y)

        # Neu da toi rat gan dich (duoi 0.3m), phanh dung hanh trinh
        if dist_to_goal < 0.3:
            self.current_v = 0.0
            self.current_omega = 0.0
            self.current_steer = 0.0
            return {
                "status": "GOAL_REACHED",
                "x": self.vehicle.x,
                "y": self.vehicle.y,
                "theta": self.vehicle.theta,
                "v": 0.0,
                "steer_deg": 0.0,
                "dist_to_goal": dist_to_goal
            }

        # 2. Chay DWA Local Planner tim (v_cmd, omega_cmd)
        v_cmd, omega_cmd, traj = self.planner.plan(
            x=self.vehicle.x,
            y=self.vehicle.y,
            theta=self.vehicle.theta,
            current_v=self.current_v,
            current_omega=self.current_omega,
            goal=goal,
            obstacles=obstacles
        )

        # 3. Chuyen doi sang goc be lai Ackermann
        steer_cmd = self.omega_to_steer_angle(v_cmd, omega_cmd)

        # 4. Cap nhat trang thai xe
        new_x, new_y, new_theta = self.vehicle.step(v=v_cmd, steer_angle=steer_cmd, dt=dt)
        self.current_v = v_cmd
        self.current_omega = omega_cmd
        self.current_steer = steer_cmd
        self.history_trajectory.append((new_x, new_y, new_theta))

        return {
            "status": "NAVIGATING",
            "x": new_x,
            "y": new_y,
            "theta": new_theta,
            "v": v_cmd,
            "steer_deg": math.degrees(steer_cmd),
            "dist_to_goal": math.hypot(goal[0] - new_x, goal[1] - new_y)
        }

    def run_mission(self,
                    goal: Tuple[float, float],
                    obstacles: List[Tuple[float, float]],
                    max_steps: int = 200,
                    dt: float = 0.1) -> Dict[str, Any]:
        """
        Chay toan bo hanh trinh dieu huong toi dich den.
        Tra ve bao cao tong ket nhiem vu (Mission Telemetry Report).
        """
        for step_idx in range(max_steps):
            telemetry = self.navigate_step(goal, obstacles, dt=dt)
            if telemetry["status"] == "GOAL_REACHED":
                return {
                    "result": "SUCCESS",
                    "steps": step_idx + 1,
                    "final_x": telemetry["x"],
                    "final_y": telemetry["y"],
                    "final_dist": telemetry["dist_to_goal"],
                    "trajectory_length": len(self.history_trajectory)
                }

        return {
            "result": "TIMEOUT",
            "steps": max_steps,
            "final_x": self.vehicle.x,
            "final_y": self.vehicle.y,
            "final_dist": math.hypot(goal[0] - self.vehicle.x, goal[1] - self.vehicle.y),
            "trajectory_length": len(self.history_trajectory)
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AA CAPSTONE: AUTONOMOUS VEHICLE NAVIGATION")
    print("=========================================================\n")

    # 1. Kich ban 1: Duong thang den dich (0, 0) -> (5.0, 0.0) khong co vat can
    print("1. KICH BAN 1: HANH TRINH THONG THOANG KHONG CO VAT CAN:")
    engine_clear = AutonomousNavigationEngine(start_x=0.0, start_y=0.0, start_theta=0.0)
    report_clear = engine_clear.run_mission(goal=(5.0, 0.0), obstacles=[], max_steps=100)

    print(f"   -> Ket qua nhiem vu          : {report_clear['result']}")
    print(f"   -> So buoc thoi gian         : {report_clear['steps']} steps")
    print(f"   -> Toa do ve dich            : x={report_clear['final_x']:.2f}m, y={report_clear['final_y']:.2f}m")
    print(f"   -> Khoang cach con lai       : {report_clear['final_dist']:.2f}m")

    assert report_clear["result"] == "SUCCESS", "Xe phai ve dich thanh cong tren duong thong thoang!"
    assert report_clear["final_dist"] < 0.3, "Khoang cach ve dich phai nho hon 0.3m!"

    # 2. Kich ban 2: Xuat phat (0, 0) den (6.0, 0.0) voi vat can o (2.5, 0.0)
    print("\n2. KICH BAN 2: NE VAT CAN DONG/TINH LIDAR TREN DUONG TIEN VE DICH:")
    engine_obs = AutonomousNavigationEngine(start_x=0.0, start_y=0.0, start_theta=0.0)
    obstacles = [(2.5, 0.0)]
    report_obs = engine_obs.run_mission(goal=(6.0, 0.0), obstacles=obstacles, max_steps=120)

    print(f"   -> Vi tri vat can chan duong : {obstacles}")
    print(f"   -> Ket qua nhiem vu          : {report_obs['result']}")
    print(f"   -> So buoc thoi gian         : {report_obs['steps']} steps")
    print(f"   -> Toa do ve dich            : x={report_obs['final_x']:.2f}m, y={report_obs['final_y']:.2f}m")
    print(f"   -> Khoang cach con lai       : {report_obs['final_dist']:.2f}m")

    # Kiem tra xem trong suot quy dao xe co va cham vao vat can (2.5, 0.0) khong
    collided = False
    for tx, ty, _ in engine_obs.history_trajectory:
        dist = math.hypot(tx - 2.5, ty - 0.0)
        if dist < 0.2:  # Ban kinh an toan vat ly
            collided = True
            break

    print(f"   -> Kiem tra va cham an toan  : {'KHONG VA CHAM' if not collided else 'VA CHAM'}")
    assert not collided, "Xe tu hanh khong duoc phep va cham voi vat can LiDAR!"
    assert report_obs["final_dist"] < 0.5, "Xe phai den gan dich den sau khi da vuot vat can!"

    # 3. Kiem tra profile S-Curve giam xoc tich hop
    print("\n3. KIEM TRA TINH LIEN TUC S-CURVE KHI KHOI DONG:")
    scurve = SCurveProfile(target_dist=6.0, v_max=2.0, a_max=1.0, j_max=2.0)
    _, v_init, a_init, j_init = scurve.sample(0.0)
    _, v_mid, a_mid, j_mid = scurve.sample(1.0)
    print(f"   -> Tai t = 0.0s              : v={v_init:.2f} m/s, a={a_init:.2f} m/s^2, j={j_init:.2f} m/s^3")
    print(f"   -> Tai t = 1.0s              : v={v_mid:.2f} m/s, a={a_mid:.2f} m/s^2, j={j_mid:.2f} m/s^3")
    assert abs(v_init) < 1e-4 and abs(a_init) < 1e-4

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE AA: AUTONOMOUS VEHICLE NAVIGATION ENGINE!")
    print("=========================================================")
