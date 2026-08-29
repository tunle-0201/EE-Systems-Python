"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
              MILESTONE R.2: BỘ LỌC VÙNG QUAN TÂM 3D (PASSTHROUGH ROI FILTER)
================================================================================

TẠI SAO CẦN PASSTHROUGH FILTER CHO XE TỰ HÀNH & DRONE?
Trong không gian 3D:
- Các điểm quá xa (> 50m) hoặc các điểm mặt đất (Z < -0.2m) không phải là vật cản nguy hiểm.
- Bộ lọc Passthrough Filter:
  + Cắt tỉa (Crop) vùng không gian hình hộp [x_min..x_max, y_min..y_max, z_min..z_max].
  + Loại bỏ 100% điểm mặt đất và nhiễu viễn thông!
"""

import numpy as np

def apply_passthrough_filter(points_3d: np.ndarray, x_limits=(-10, 10), y_limits=(0, 20), z_limits=(-0.5, 5)) -> np.ndarray:
    """
    Trò đóng vai Kỹ sư Xử lý Điểm mây 3D:
    - mask = (x >= x_min) & (x <= x_max) & (y >= y_min) & (y <= y_max) & (z >= z_min) & (z <= z_max)
    - Trả về: points_3d[mask]
    """
    x, y, z = points_3d[:, 0], points_3d[:, 1], points_3d[:, 2]
    mask = (
        (x >= x_limits[0]) & (x <= x_limits[1]) &
        (y >= y_limits[0]) & (y <= y_limits[1]) &
        (z >= z_limits[0]) & (z <= z_limits[1])
    )
    return points_3d[mask]


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: PASSTHROUGH ROI FILTER")
    print("=========================================================\n")
    
    # 4 điểm: Điểm 1 trong vùng an toàn, Điểm 2 dưới mặt đất, Điểm 3 quá xa, Điểm 4 sau lưng
    test_points = np.array([
        [0.0, 5.0, 1.0],   # Hợp lệ (phía trước 5m, cao 1m)
        [0.0, 5.0, -1.5],  # Dưới mặt đất -> Loại
        [0.0, 50.0, 1.0],  # Quá xa -> Loại
        [0.0, -5.0, 1.0]   # Sau lưng -> Loại
    ], dtype=np.float32)
    
    roi_points = apply_passthrough_filter(test_points, x_limits=(-10, 10), y_limits=(0, 20), z_limits=(-0.5, 5))
    
    print("1. KET QUA LOC VUNG QUAN TAM ROI TRUOC MAT DRONE:")
    print(f"   -> Diem hop le sau loc ROI : {roi_points}")
    
    assert len(roi_points) == 1 and roi_points[0, 1] == 5.0, "Loi Passthrough Filter!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC VUNG KHONG GIAN ROI PHAT HIEN VAT CAN CHO DRONE!")
