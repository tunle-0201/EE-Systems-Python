"""
================================================================================
          MODULE G: ADVANCED EDGE CV & AUTONOMOUS DRONE GUIDANCE
              MILESTONE G.3: STEREO VISION DISPARITY MAP & 3D DEPTH ESTIMATOR
================================================================================

TẠI SAO CẦN STEREO VISION CAM DOUBLE DÀNH CHO DRONE?
Camera kép (Stereo Camera) mô phỏng 2 con mắt con người:
- Phép lệch pha (Disparity = x_left - x_right) giữa 2 bức ảnh.
- Khoảng cách 3D Z = (focal_length * baseline) / disparity.
- Giúp Drone tái tạo bản đồ 3D né vật cản trong đêm tối!
"""

import numpy as np

def compute_stereo_depth_map(disparity_pixel, focal_length_px=500.0, baseline_m=0.1):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Stereo Depth từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - depth_m = (focal_length_px * baseline_m) / (disparity_pixel + 1e-6)
    - Trả về: depth_m
    """
    depth_m = (focal_length_px * baseline_m) / (disparity_pixel + 1e-6)
    return depth_m


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED CV: STEREO DISPARITY 3D DEPTH ESTIMATOR")
    print("=========================================================\n")
    
    # Sai lech 25 pixels giua 2 mắt camera
    disp = 25.0
    depth = compute_stereo_depth_map(disp, focal_length_px=500.0, baseline_m=0.1)
    
    print("1. KET QUA TAI TAO BAN DO DO SAU 3D REAL-TIME:")
    print(f"   -> Khoang cach 3D toi Vat can Depth : {depth:.2f} meters")
    
    assert abs(depth - 2.0) < 0.01, "Loi Stereo Depth!"
    print("\n[THANH CONG] DA HOAN THANH GIAI THUAT DOCKING STEREO DEPTH MAP NE VAT CAN!")
