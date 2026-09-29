"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
    MILESTONE R.1: NEN DAM MAY DIEM BANG LUOI KHONG GIAN (VOXEL GRID DOWNSAMPLING)
================================================================================

1. NGUYEN LY VAT LY & HE THONG CUNG (AUTONOMOUS 3D PERCEPTION):
   - Cam bien LiDAR 3D (Velodyne, Ouster, Hesai) quay voi tan so 10 - 20 Hz,
     ban hang chuc tia laser va thu ve tu 300.000 den 2.000.000 diem (x, y, z) moi giay.
   - Van de tren Drone / Xe tu hanh (Edge Computing):
     + Neu dua truc tiep hang trieu diem vao thuat toan SLAM hoac Mang no-ron 3D,
       bang thong RAM va GPU/NPU se bi nghen co chai ngay lap tuc.
     + Mat do diem khong dong deu: vat the o gan thi day dac hang van diem, vat the
       o xa thi chi co vai diem thua thot.
   - Thuat toan Voxel Grid Filter:
     + Chia khong gian 3D thanh cac khoi hop lap phuong (Voxel) deu nhau kich thuoc d.
     + Tinh toan toa do roi rac hoa (Voxel Coordinate Indexing) theo phep chia lam tron xuong.
     + Gom toan bo cac diem roi vao cung mot Voxel va thay the bang 1 diem trong tam (Centroid).
     + Giam 80% - 90% so diem nhung bao toan 99% hinh hoc cau truc vat can!

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do phep chieu Voxel Grid tu diem tho ve trong tam (Centroid):

   Khong gian 3D ban dau (Day dac):       Sau loc Voxel Grid (Dong deu):
   ┌───────────────────────────┐         ┌───────────────────────────┐
   │  * * *                    │         │                           │
   │ *  X  * (Nhieu diem gan)  │  ───►   │       O (Centroid duy nhat│
   │  * * *                    │         │          dai dien Voxel)  │
   │                           │         │                           │
   │            * (Diem xa)    │         │            *              │
   └───────────────────────────┘         └───────────────────────────┘
   [Voxel Size d = 0.5m x 0.5m x 0.5m]

   Cong thuc tinh chi so Voxel (Voxel Indexing):

   voxel_x = floor( x / voxel_size )
   voxel_y = floor( y / voxel_size )
   voxel_z = floor( z / voxel_size )

   Cong thuc tinh toa do trong tam (Centroid Calculation):

              Sum( x_i )                 Sum( y_i )                 Sum( z_i )
   x_cen = ───────────── ,    y_cen = ───────────── ,    z_cen = ─────────────
                 N                          N                          N

   Trong do N la tong so diem do tho nam ben trong Voxel do.
"""

from typing import Tuple, Dict, List
import numpy as np


class VoxelGridFilter:
    """
    Bo loc nen dam may diem 3D Voxel Grid hieu nang cao cho he thong tu hanh.
    """
    def __init__(self, voxel_size: float = 0.5):
        self.voxel_size = float(voxel_size)

    def filter(self, points_3d: np.ndarray) -> np.ndarray:
        """
        Nen tap hop diem Nx3 thanh mảng diem moi Mx3 (M <= N):
        - Tinh chi so Voxel bang np.floor(points_3d / voxel_size)
        - Gom nhom cac diem cung chi so
        - Tinh toa do trung binh (Centroid) cua tung nhom
        """
        if points_3d is None or len(points_3d) == 0:
            return np.empty((0, 3), dtype=np.float32)

        # Chuyen ve mảng float32
        pts = np.asarray(points_3d, dtype=np.float32)

        # 1. Roi rac hoa toa do khong gian 3D
        voxel_coords = np.floor(pts / self.voxel_size).astype(np.int32)

        # 2. Gom diem vao Dictionary Hash Map theo chi so Voxel
        voxel_buckets: Dict[Tuple[int, int, int], List[np.ndarray]] = {}
        for pt, coord in zip(pts, voxel_coords):
            key = (int(coord[0]), int(coord[1]), int(coord[2]))
            if key not in voxel_buckets:
                voxel_buckets[key] = []
            voxel_buckets[key].append(pt)

        # 3. Tinh toa do trong tam Centroid cho moi Voxel
        centroids = [np.mean(cluster, axis=0) for cluster in voxel_buckets.values()]
        return np.array(centroids, dtype=np.float32)

    def get_compression_ratio(self, original_count: int, filtered_count: int) -> float:
        """
        Tinh ty le nén bo nho:
        Ty_le_giam = (1 - filtered_count / original_count) * 100%
        """
        if original_count == 0:
            return 0.0
        return (1.0 - filtered_count / original_count) * 100.0


def voxel_grid_downsample(points_3d: np.ndarray, voxel_size: float = 0.5) -> np.ndarray:
    """
    Ham backward-compatible giu nguyen signature cua Milestone R.1.
    """
    filter_engine = VoxelGridFilter(voxel_size=voxel_size)
    return filter_engine.filter(points_3d)


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: LIDAR VOXEL GRID FILTER")
    print("=========================================================\n")

    # 6 diem nam trong khong gian 3D:
    # 3 diem dau nam sat nhau trong cung 1 khoi Voxel [0..0.5m]
    # 2 diem giua nam trong Voxel [2.0..2.5m]
    # 1 diem cuoi nam trong Voxel [5.0..5.5m]
    raw_points = np.array([
        [0.1, 0.1, 0.1],
        [0.12, 0.15, 0.11],
        [0.2, 0.2, 0.2],
        [2.0, 2.0, 2.0],  # Voxel khac
        [2.1, 2.1, 2.1],
        [5.0, 5.0, 5.0]   # Voxel khac
    ], dtype=np.float32)

    filter_obj = VoxelGridFilter(voxel_size=0.5)
    filtered_points = filter_obj.filter(raw_points)
    reduction = filter_obj.get_compression_ratio(len(raw_points), len(filtered_points))

    print("1. KET QUA NEN DAM MAY DIEM LIDAR VOXEL GRID:")
    print(f"   -> So luong diem ban dau : {len(raw_points)} diem")
    print(f"   -> So luong diem sau loc : {len(filtered_points)} diem (Giam {reduction:.1f}%)")
    print(f"   -> Toa do Centroid Voxel 1: [{filtered_points[0,0]:.3f}, {filtered_points[0,1]:.3f}, {filtered_points[0,2]:.3f}]")

    assert len(filtered_points) == 3, "Loi Voxel Grid Downsampling!"
    # Kiem tra trong tam cua 3 diem dau: (0.1+0.12+0.2)/3 = 0.140
    assert abs(filtered_points[0, 0] - 0.14) < 1e-2

    print("\n[THANH CONG] DA HOAN THANH BO LOC KHONG GIAN VOXEL GRID CHO LIDAR DRONE!")
