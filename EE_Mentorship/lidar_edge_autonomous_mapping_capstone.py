"""
================================================================================
          MODULE R CAPSTONE FINALE: HE THONG CAM NHAN 3D VA BAN DO
               TU HANH CHO DRONE (3D LIDAR PERCEPTION CAPSTONE)
================================================================================

1. KIEN TRUC HE THONG CAM NHAN 3D TICH HOP (FULL LIDAR PERCEPTION PIPELINE):
   Day la kien truc he thong dinh vi va nhan thuc 3D thoi gian thuc tren cac he thong
   Drone khong nguoi lai va xe tu hanh dat chuan SAE Level 4 (Waymo, Tesla, Skydio):
   - Tang 1: Voxel Grid Downsampling - Nen dam may diem tho, giam 85% ap luc RAM va bus DMA.
   - Tang 2: Passthrough 3D ROI Filter - Cat tia mat dat, loai bo tia laser phan xa mat duong.
   - Tang 3: ICP Scan Matching Odometry - Tinh toan vector dich chuyen chinh xac khong can GPS.
   - Tang 4: Obstacle Mapping - Trich xuat toa do cac cum vat can nguy hiem de ne tranh.

2. SO DO LUONG DU LIEU DIEU KHIEN REAL-TIME (ASCII ARCHITECTURE):

  +──────────────────────────────────────────────────────────────────────────+
  |        AUTONOMOUS DRONE 3D LIDAR PERCEPTION & MAPPING PIPELINE           |
  +──────────────────────────────────────────────────────────────────────────+
  |                                                                          |
  |  [ Raw 3D Point Cloud ] (300,000 pts/sec tu cam bien Ouster / Velodyne)  |
  |             │                                                            |
  |             ▼                                                            |
  |  [ Voxel Grid Downsampling ] (Centroid Hash Bucket -> Nén 85% diem)      |
  |             │                                                            |
  |             ▼                                                            |
  |  [ Passthrough ROI Filter ] (Cat bo mat dat z < -0.5m & vat xa > 30m)    |
  |             │                                                            |
  |             ▼                                                            |
  |  [ ICP Scan Matching Odometry ] (Khop 2 Frame -> Uoc luong dx, dy, dz)   |
  |             │                                                            |
  |             ▼                                                            |
  |  [ Flight Engine Navigation ] (Dua vao bo dieu khien tranh va cham)      |
  +──────────────────────────────────────────────────────────────────────────+
"""

from typing import Tuple, Dict, Any
import numpy as np

from lidar_edge_voxel_downsampling import VoxelGridFilter, voxel_grid_downsample
from lidar_edge_passthrough_filter import PassthroughFilter3D, apply_passthrough_filter
from lidar_edge_icp_odometry import LidarIcpOdometry, estimate_translation_icp


class AutonomousLidarPipeline:
    """
    Tong hop toan bo xu ly diem may 3D LiDAR thanh he thong khep kin.
    """
    def __init__(
        self,
        voxel_size: float = 0.5,
        x_limits: Tuple[float, float] = (-20.0, 20.0),
        y_limits: Tuple[float, float] = (0.0, 30.0),
        z_limits: Tuple[float, float] = (-1.0, 5.0)
    ):
        self.voxel_filter = VoxelGridFilter(voxel_size=voxel_size)
        self.roi_filter = PassthroughFilter3D(x_limits=x_limits, y_limits=y_limits, z_limits=z_limits)
        self.odometry = LidarIcpOdometry()

    def process_frame(self, raw_cloud: np.ndarray) -> np.ndarray:
        """
        Xu ly mot khung quet LiDAR: Voxel Downsample -> Passthrough ROI
        """
        downsampled = self.voxel_filter.filter(raw_cloud)
        roi_points = self.roi_filter.filter(downsampled)
        return roi_points

    def track_motion(self, raw_cloud_t1: np.ndarray, raw_cloud_t2: np.ndarray) -> Dict[str, Any]:
        """
        Xu ly 2 khung quet lien tiep de tinh toan dich chuyen va vat can:
        """
        pts1 = self.process_frame(raw_cloud_t1)
        pts2 = self.process_frame(raw_cloud_t2)

        translation, mse_error = self.odometry.estimate_motion(pts1, pts2)

        return {
            "obstacle_count": len(pts1),
            "obstacle_positions": pts1,
            "translation": translation,
            "alignment_mse": mse_error
        }


def run_autonomous_lidar_3d_pipeline(raw_cloud_t1: np.ndarray, raw_cloud_t2: np.ndarray) -> Tuple[int, np.ndarray]:
    """
    Ham backward-compatible giu nguyen chu ky kiem thu Milestone R Capstone.
    """
    # 1. Nen Voxel Grid
    v_t1 = voxel_grid_downsample(raw_cloud_t1, voxel_size=0.5)
    v_t2 = voxel_grid_downsample(raw_cloud_t2, voxel_size=0.5)

    # 2. Loc vung quan tam ROI
    roi_t1 = apply_passthrough_filter(v_t1, (-20, 20), (0, 30), (-1, 5))
    roi_t2 = apply_passthrough_filter(v_t2, (-20, 20), (0, 30), (-1, 5))

    # 3. Tinh toan di chuyen ICP Odometry
    delta_pos = estimate_translation_icp(roi_t1, roi_t2)
    return len(roi_t1), delta_pos


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE R CAPSTONE: AUTONOMOUS 3D LIDAR PERCEPTION")
    print("=========================================================\n")

    # Dam may diem tho thoi diem t1 (2 diem dau gan nhau cung 1 voxel, 1 diem xa hon, 1 diem ngoai vung)
    cloud1 = np.array([
        [0.0, 10.0, 1.0],
        [0.1, 10.1, 1.0],
        [5.0, 15.0, 2.0],
        [0.0, 100.0, 1.0]  # Ngoai ROI (> 30m)
    ], dtype=np.float32)

    # Dam may diem tho thoi diem t2 (Drone tien ve phia truoc theo truc Y dung 1.0m)
    cloud2 = cloud1 + np.array([0.0, 1.0, 0.0], dtype=np.float32)

    num_obstacles, translation = run_autonomous_lidar_3d_pipeline(cloud1, cloud2)

    print("1. KET QUA HOAT DONG TOAN CHUOI LIDAR PERCEPTION REAL-TIME:")
    print(f"   -> So cum vat can phat hien : {num_obstacles} cum vat can")
    print(f"   -> Do dich chuyen uoc luong : DY = {translation[1]:.2f} m")

    assert num_obstacles == 2 and abs(translation[1] - 1.0) < 1e-5, "Loi Capstone LiDAR Engine!"

    # 2. Kiem thu bang Pipeline nang cao
    pipeline = AutonomousLidarPipeline()
    result = pipeline.track_motion(cloud1, cloud2)

    print("\n2. TELEMETRY DINH VI KHONG GIAN 3D TU DONG:")
    print(f"   -> Vector dich chuyen Drone : DX = {result['translation'][0]:.2f}m, DY = {result['translation'][1]:.2f}m, DZ = {result['translation'][2]:.2f}m")
    print(f"   -> Sai so khop mo phong     : {result['alignment_mse']:.6f} m^2")

    assert abs(result['translation'][1] - 1.0) < 1e-5

    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE R: ADVANCED 3D LIDAR PERCEPTION!")
    print("=========================================================")
