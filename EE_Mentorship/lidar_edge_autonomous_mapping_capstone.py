"""
================================================================================
          MODULE R CAPSTONE FINALE: HỆ THỐNG CẢM NHẬN 3D VÀ BẢN ĐỒ TỰ HÀNH CHO DRONE
================================================================================

TÍCH HỢP TOÀN BỘ 3D LIDAR PIPELINE: VOXEL GRID + PASSTHROUGH ROI + ICP ODOMETRY
"""

from lidar_edge_voxel_downsampling import voxel_grid_downsample
from lidar_edge_passthrough_filter import apply_passthrough_filter
from lidar_edge_icp_odometry import estimate_translation_icp
import numpy as np

def run_autonomous_lidar_3d_pipeline(raw_cloud_t1, raw_cloud_t2):
    # 1. Nén Voxel Grid
    v_t1 = voxel_grid_downsample(raw_cloud_t1, voxel_size=0.5)
    v_t2 = voxel_grid_downsample(raw_cloud_t2, voxel_size=0.5)
    
    # 2. Lọc vùng quan tâm ROI
    roi_t1 = apply_passthrough_filter(v_t1, (-20, 20), (0, 30), (-1, 5))
    roi_t2 = apply_passthrough_filter(v_t2, (-20, 20), (0, 30), (-1, 5))
    
    # 3. Tính toán di chuyển ICP Odometry
    delta_pos = estimate_translation_icp(roi_t1, roi_t2)
    return len(roi_t1), delta_pos


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE R CAPSTONE: AUTONOMOUS 3D LIDAR PERCEPTION")
    print("=========================================================\n")
    
    # Đám mây điểm thô t1
    cloud1 = np.array([
        [0.0, 10.0, 1.0],
        [0.1, 10.1, 1.0],
        [5.0, 15.0, 2.0],
        [0.0, 100.0, 1.0] # Ngoài ROI
    ], dtype=np.float32)
    
    # Đám mây điểm thô t2 (Drone tiến lên 1.0m)
    cloud2 = cloud1 + np.array([0.0, 1.0, 0.0])
    
    num_obstacles, translation = run_autonomous_lidar_3d_pipeline(cloud1, cloud2)
    
    print("1. KET QUA HOAT DONG TOAN CHUOI LIDAR PERCEPTION REAL-TIME:")
    print(f"   -> So cum vat can phat hien : {num_obstacles} vat can")
    print(f"   -> Do dich chuyen uoc luong : DY = {translation[1]:.2f} m")
    
    assert num_obstacles == 2 and abs(translation[1] - 1.0) < 1e-5, "Loi Capstone LiDAR Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE R: ADVANCED 3D LIDAR PERCEPTION!")
    print("=========================================================")
