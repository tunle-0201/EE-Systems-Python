"""
================================================================================
          MODULE G: ADVANCED EDGE CV & AUTONOMOUS DRONE GUIDANCE
              MILESTONE G.1: LUCAS-KANADE OPTICAL FLOW POSITION HOLD FOR DRONES
================================================================================

TẠI SAO CẦN OPTICAL FLOW TRONG MÔI TRƯỜNG KHÔNG CÓ GPS (GPS-DENIED)?
Khi Drone bay trong nhà, hầm mỏ hoặc tán cây che khuất vệ tinh GPS:
- Camera nhìn xuống đất (Downward-facing camera) liên tục chụp ảnh.
- Thuật toán **Optical Flow (Dòng chảy Quang học Lucas-Kanade)** theo dõi sự dịch chuyển của các điểm đặc trưng (Features) giữa 2 khung hình liên tiếp.
- Vận tốc Drone = (Dịch chuyển Pixel / dt) * Độ cao bay.
"""

import numpy as np

def estimate_drone_optical_flow_velocity(prev_pts, curr_pts, dt=0.033, altitude_m=2.0):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Optical Flow từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - delta = curr_pts - prev_pts
    - avg_pixel_shift = np.mean(delta, axis=0)
    - velocity_m_s = (avg_pixel_shift / dt) * (altitude_m / 500.0)
    - Trả về: velocity_m_s (vx, vy)
    """
    delta = curr_pts - prev_pts
    avg_pixel_shift = np.mean(delta, axis=0)
    velocity_m_s = (avg_pixel_shift / dt) * (altitude_m / 500.0)
    return velocity_m_s


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED CV: OPTICAL FLOW VELOCITY ESTIMATOR")
    print("=========================================================\n")
    
    # Khung hình 1: 3 điểm đặc trưng ở tọa độ (100, 100), (200, 200), (300, 300)
    pts1 = np.array([[100.0, 100.0], [200.0, 200.0], [300.0, 300.0]])
    # Khung hình 2 (sau 33ms): Drone trôi sang phải 5px, xuống 2px
    pts2 = np.array([[105.0, 102.0], [205.0, 202.0], [305.0, 302.0]])
    
    vel = estimate_drone_optical_flow_velocity(pts1, pts2, dt=0.033, altitude_m=2.0)
    
    print("1. KET QUA UOC LUONG VAN TOC HOAT DONG REAL-TIME:")
    print(f"   -> Van toc troi ngang Vx : {vel[0]:.4f} m/s")
    print(f"   -> Van toc troi doc   Vy : {vel[1]:.4f} m/s")
    
    assert vel[0] > 0.5 and vel[1] > 0.2, "Loi Optical Flow!"
    print("\n[THANH CONG] DA HOAN THANH GIAI THUAT OPTICAL FLOW CHO DRONE PHONG CHONG MAT GPS!")
