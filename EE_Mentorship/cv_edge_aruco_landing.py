"""
================================================================================
          MODULE G: ADVANCED EDGE CV & AUTONOMOUS DRONE GUIDANCE
              MILESTONE G.2: ARUCO MARKER PRECISION AUTONOMOUS LANDING
================================================================================

TẠI SAO CẦN THẺ ARUCO MARKER CHO HẠ CÁNH CHÍNH XÁC?
Để Drone tự động hạ cánh xuống trạm sạc không dây với độ chính xác milimet:
- Thẻ ArUco (Ma trận mã vạch hình vuông) được dán ở tâm trạm sạc.
- Camera phát hiện 4 góc thẻ ArUco -> Tính toán góc lệch Roll, Pitch và Khoảng cách z_distance.
"""

import numpy as np

def compute_aruco_landing_offset(marker_corners_px, image_center_px=(320, 240)):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ ArUco Landing từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - marker_center = np.mean(marker_corners_px, axis=0)
    - dx = marker_center[0] - image_center_px[0]
    - dy = marker_center[1] - image_center_px[1]
    - distance_err = np.sqrt(dx**2 + dy**2)
    - Trả về: dx, dy, distance_err
    """
    marker_center = np.mean(marker_corners_px, axis=0)
    dx = marker_center[0] - image_center_px[0]
    dy = marker_center[1] - image_center_px[1]
    distance_err = np.sqrt(dx**2 + dy**2)
    return dx, dy, distance_err


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED CV: ARUCO MARKER PRECISION LANDING")
    print("=========================================================\n")
    
    # 4 góc của thẻ ArUco phát hiện được trên khung hình (Center ~ 340, 260)
    corners = np.array([[320.0, 240.0], [360.0, 240.0], [360.0, 280.0], [320.0, 280.0]])
    
    dx, dy, err = compute_aruco_landing_offset(corners, image_center_px=(320, 240))
    
    print("1. KET QUA PHAN TICH SAI LECH HA CANH CHINHXAC:")
    print(f"   -> Sai lech truc Ngang Dx : {dx:.1f} pixels")
    print(f"   -> Sai lech truc Doc   Dy : {dy:.1f} pixels")
    print(f"   -> Khoang cach Sai so Total: {err:.2f} pixels")
    
    assert err > 20.0, "Loi ArUco Landing!"
    print("\n[THANH CONG] DA HOAN THANH HE THONG HA CANH CHINH XAC DUNG THE ARUCO MARKER!")
