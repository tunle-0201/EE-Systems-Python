"""
================================================================================
          MODULE G CAPSTONE FINALE: BỘ NÃO THỊ GIÁC TỰ HÀNH CHO DRONE (AUTONOMOUS CV)
================================================================================

TÍCH HỢP TOÀN BỘ HỆ THỐNG THỊ GIÁC EMBEDDED COMPUTER VISION:
Tích hợp Optical Flow + ArUco Landing + Stereo Depth vào 1 Bộ não Tự hành.
"""

from cv_edge_optical_flow import estimate_drone_optical_flow_velocity
from cv_edge_aruco_landing import compute_aruco_landing_offset
from cv_edge_stereo_depth import compute_stereo_depth_map
import numpy as np

def run_autonomous_vision_guidance_system():
    # 1. Optical Flow velocity
    p1 = np.array([[10.0, 10.0]])
    p2 = np.array([[12.0, 10.0]])
    vel = estimate_drone_optical_flow_velocity(p1, p2, 0.033, 2.0)
    
    # 2. ArUco Landing offset
    corners = np.array([[300.0, 220.0], [340.0, 220.0], [340.0, 260.0], [300.0, 260.0]])
    dx, dy, err = compute_aruco_landing_offset(corners)
    
    # 3. Stereo Depth
    depth = compute_stereo_depth_map(disparity_pixel=25.0)
    
    return vel, err, depth


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE G CAPSTONE: AUTONOMOUS DRONE CV GUIDANCE ENGINE")
    print("=========================================================\n")
    
    v, e, d = run_autonomous_vision_guidance_system()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI COMPUTER VISION:")
    print(f"   -> Optical Flow Velocity Vx : {v[0]:.4f} m/s")
    print(f"   -> ArUco Landing Error      : {e:.2f} pixels")
    print(f"   -> Stereo Obstacle Depth    : {d:.2f} meters")
    
    assert abs(d - 2.0) < 0.01, "Loi Capstone Vision Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE G: COMPUTER VISION GUIDANCE!")
    print("=========================================================")
