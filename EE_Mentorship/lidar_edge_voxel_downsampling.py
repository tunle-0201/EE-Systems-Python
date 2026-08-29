"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
              MILESTONE R.1: NÉN ĐÁM MÂY ĐIỂM BẰNG LƯỚI KHÔNG GIAN (VOXEL GRID DOWNSAMPLING)
================================================================================

TẠI SAO CẦN VOXEL GRID TRONG XỬ LÝ DỮ LIỆU LIDAR 3D (WAYMO, TESLA)?
Cảm biến LiDAR 3D quét ra 300.000 điểm mỗi giây (x, y, z):
- CPU/NPU trên Drone không thể xử lý thời gian thực lượng điểm khổng lồ này.
- Thuật toán **Voxel Grid Filter**:
  + Chia không gian 3D thành các khối lập phương nhỏ (Voxel) kích thước d = 0.5m.
  + Gom tất cả các điểm rơi vào cùng 1 Voxel thành đúng 1 điểm đại diện (Centroid).
  + Giảm 85% số điểm nhưng vẫn giữ nguyên hình dạng vật cản!
"""

import numpy as np

def voxel_grid_downsample(points_3d: np.ndarray, voxel_size: float = 0.5) -> np.ndarray:
    """
    points_3d: mảng Nx3 gồm các điểm (x, y, z)
    Trò đóng vai Kỹ sư LiDAR thiết kế bộ lọc Voxel Grid:
    - voxel_coords = np.floor(points_3d / voxel_size).astype(np.int32)
    - Nhóm các điểm có cùng voxel_coord và tính điểm trung bình centroid
    """
    voxel_coords = np.floor(points_3d / voxel_size).astype(np.int32)
    
    unique_voxels = {}
    for pt, coord in zip(points_3d, voxel_coords):
        key = tuple(coord)
        if key not in unique_voxels:
            unique_voxels[key] = []
        unique_voxels[key].append(pt)
        
    downsampled = [np.mean(pts, axis=0) for pts in unique_voxels.values()]
    return np.array(downsampled, dtype=np.float32)


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: LIDAR VOXEL GRID FILTER")
    print("=========================================================\n")
    
    # 6 điểm nằm sát nhau trong cùng 1 khối Voxel [0..0.5m]
    raw_points = np.array([
        [0.1, 0.1, 0.1],
        [0.12, 0.15, 0.11],
        [0.2, 0.2, 0.2],
        [2.0, 2.0, 2.0], # Voxel khác
        [2.1, 2.1, 2.1],
        [5.0, 5.0, 5.0]  # Voxel khác
    ], dtype=np.float32)
    
    filtered_points = voxel_grid_downsample(raw_points, voxel_size=0.5)
    
    print("1. KET QUA NEN DAM MAY DIEM LIDAR VOXEL GRID:")
    print(f"   -> So luong diem ban dau : {len(raw_points)} diem")
    print(f"   -> So luong diem sau loc : {len(filtered_points)} diem (Giam 50%!)")
    
    assert len(filtered_points) == 3, "Loi Voxel Grid Downsampling!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC KHONG GIAN VOXEL GRID CHO LIDAR DRONE!")
