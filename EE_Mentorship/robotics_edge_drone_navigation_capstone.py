"""
================================================================================
          MODULE P CAPSTONE FINALE: HỆ THỐNG ĐIỀU HƯỚNG TỰ HÀNH & ĐỘNG HỌC ROBOTICS
================================================================================

TÍCH HỢP TOÀN BỘ KINEMATICS: QUATERNIONS + CUBIC TRAJECTORY + FORWARD KINEMATICS
"""

from robotics_edge_quaternion_rotations import quaternion_multiply
from robotics_edge_cubic_spline_trajectory import generate_cubic_trajectory_point
from robotics_edge_forward_kinematics import compute_2link_forward_kinematics
import numpy as np

def run_autonomous_robotics_navigation_loop():
    # 1. Hoạch định quỹ đạo bay mượt mà đến Waypoint 20m trong 4s
    target_pos = generate_cubic_trajectory_point(p0=0.0, pf=20.0, t=2.0, tf=4.0)
    
    # 2. Xoay góc 3D bằng Quaternion
    q_init = np.array([1.0, 0.0, 0.0, 0.0])
    q_rot = np.array([0.7071, 0.0, 0.0, 0.7071])
    q_final = quaternion_multiply(q_init, q_rot)
    
    # 3. Điều khiển cánh tay robot lấy mẫu vật
    rx, ry = compute_2link_forward_kinematics(0.5, 0.5, 0.0, 0.0)
    
    return target_pos, q_final, rx


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE P CAPSTONE: FULL AUTONOMOUS ROBOTICS ENGINE")
    print("=========================================================\n")
    
    pos, q_out, arm_x = run_autonomous_robotics_navigation_loop()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI ROBOTICS NAVIGATION ENGINE:")
    print(f"   -> Vi tri Waypoint tai 2.0s : {pos:.2f} m")
    print(f"   -> Quaternion Huong 3D     : {q_out}")
    print(f"   -> Canh tay Robot duoi dai : {arm_x:.2f} m")
    
    assert pos == 10.0 and arm_x == 1.0, "Loi Capstone Robotics Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE P: ADVANCED ROBOTICS!")
    print("=========================================================")
