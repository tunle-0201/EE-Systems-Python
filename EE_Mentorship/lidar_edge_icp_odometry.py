"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
              MILESTONE R.3: ĐỊNH VỊ KHÔNG GPS BẰNG KHỚP ĐIỂM (ICP SCAN MATCHING)
================================================================================

TẠI SAO CÁC XE TỰ HÀNH & ROBOT DÙNG ICP ĐỂ ĐỊNH VỊ TỌA ĐỘ KHI MẤT GPS?
Khi xe chạy vào hầm hoặc Drone bay trong nhà kín (GPS-Denied):
- Thuật toán **ICP (Iterative Closest Point)** so sánh 2 khung quét LiDAR liên tiếp (Frame t và Frame t+1).
- Tính toán vector tịnh tiến dịch chuyển (dx, dy) giữa 2 đám mây điểm.
- Giúp Drone tự biết mình đã bay được bao nhiêu mét mà không cần GPS!
"""

import numpy as np

def estimate_translation_icp(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray:
    """
    Trò đóng vai Kỹ sư Định vị LiDAR Odometry:
    - Tính trọng tâm (Centroid) của 2 tập điểm: c_src = np.mean(source_points, axis=0), c_tgt = np.mean(target_points, axis=0)
    - Vector dịch chuyển: translation = c_tgt - c_src
    - Trả về: translation
    """
    c_src = np.mean(source_points, axis=0)
    c_tgt = np.mean(target_points, axis=0)
    translation = c_tgt - c_src
    return translation


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: LIDAR ICP ODOMETRY")
    print("=========================================================\n")
    
    # Khung quét 1 tại thời điểm t
    scan_t1 = np.array([[1.0, 1.0, 0.0], [2.0, 1.0, 0.0], [1.5, 2.0, 0.0]])
    
    # Khung quét 2 tại thời điểm t+1 (Drone đã dịch chuyển dx=0.5m, dy=1.2m)
    scan_t2 = scan_t1 + np.array([0.5, 1.2, 0.0])
    
    trans = estimate_translation_icp(scan_t1, scan_t2)
    
    print("1. KET QUA TINH TOAN DICH CHUYEN LIDAR SCAN MATCHING:")
    print(f"   -> Do dich chuyen DX : {trans[0]:.2f} m")
    print(f"   -> Do dich chuyen DY : {trans[1]:.2f} m")
    
    assert abs(trans[0] - 0.5) < 1e-5 and abs(trans[1] - 1.2) < 1e-5, "Loi ICP Odometry!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN DINH VI LIDAR ODOMETRY KHONG CAN GPS CHO DRONE!")
