"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
    MILESTONE R.2: BO LOC VUNG QUAN TAM 3D (PASSTHROUGH ROI FILTER)
================================================================================

1. NGUYEN LY VAT LY & PHAN CUNG NHUNG (AUTONOMOUS 3D PERCEPTION):
   - Khi Drone bay hoac xe tu hanh di chuyen, cam bien LiDAR thu ve hang tram nghin
     diem toa do khong gian 3D.
   - Van de can loai bo:
     + Diem mat dat (Ground Clutter): Hang van tia laser ban xuong mat duong (z < -0.2m).
       Neu khong loc bo, he thong dieu khien se nham tuong mat dat la buc tuong vat can!
     + Diem qua xa (Far Noise): Cac diem ngoai tam phat hien an toan (> 30m - 50m) co sai so cao.
     + Diem ngoai tam bay: Cac diem phia sau lung hoac tren tran troi (may, chim, bui).
   - Thuat toan Passthrough Filter (Crop Box Filter):
     + Dinh nghia mot khoi hop gioi han 3D (Axis-Aligned Bounding Box - AABB).
     + Ap dung mat na logic nhi phan Vectorized SIMD tren truc X, Y, Z song song.
     + Chi giu lai cac diem nam trong vung khong gian hanh lang an toan truoc mat.

2. SO DO HINH HOC & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do khoi hop khong gian 3D Passthrough ROI Filter:

             +Z (Do cao)
              ▲
              │      ┌─────────────────────────┐  Z_max (+5.0m - Tran tran)
              │      │    VUNG QUAN TAM (ROI)  │
              │      │       [ VAT CAN ]       │
              │      │            *            │
              │      └─────────────────────────┘  Z_min (-0.5m - Mat dat)
              ├────────────────────────────────────────► +Y (Khoang cach truoc mat)
              │                                        Y_max (+20.0m)
              │   * (Mat dat)       * (Qua xa > 20m)
              ▼

   Bieu thuc mat na logic kiem tra diem thuoc vung ROI:

   mask = (x >= x_min) va (x <= x_max) va
          (y >= y_min) va (y <= y_max) va
          (z >= z_min) va (z <= z_max)
"""

from typing import Tuple
import numpy as np


class PassthroughFilter3D:
    """
    Bo loc cat tia khong gian hinh hop 3D Passthrough cho LiDAR.
    """
    def __init__(
        self,
        x_limits: Tuple[float, float] = (-10.0, 10.0),
        y_limits: Tuple[float, float] = (0.0, 20.0),
        z_limits: Tuple[float, float] = (-0.5, 5.0)
    ):
        self.x_min, self.x_max = float(x_limits[0]), float(x_limits[1])
        self.y_min, self.y_max = float(y_limits[0]), float(y_limits[1])
        self.z_min, self.z_max = float(z_limits[0]), float(z_limits[1])

    def filter(self, points_3d: np.ndarray) -> np.ndarray:
        """
        Loc giu lai cac diem nam trong pham vi [x_min..x_max, y_min..y_max, z_min..z_max].
        Su dung phep toan ma tran NumPy Vectorized SIMD tang toc do thuc thi.
        """
        if points_3d is None or len(points_3d) == 0:
            return np.empty((0, 3), dtype=np.float32)

        pts = np.asarray(points_3d, dtype=np.float32)
        x = pts[:, 0]
        y = pts[:, 1]
        z = pts[:, 2]

        mask = (
            (x >= self.x_min) & (x <= self.x_max) &
            (y >= self.y_min) & (y <= self.y_max) &
            (z >= self.z_min) & (z <= self.z_max)
        )
        return pts[mask]


def apply_passthrough_filter(
    points_3d: np.ndarray,
    x_limits: Tuple[float, float] = (-10, 10),
    y_limits: Tuple[float, float] = (0, 20),
    z_limits: Tuple[float, float] = (-0.5, 5)
) -> np.ndarray:
    """
    Ham backward-compatible giu nguyen signature cua Milestone R.2.
    """
    filter_engine = PassthroughFilter3D(x_limits=x_limits, y_limits=y_limits, z_limits=z_limits)
    return filter_engine.filter(points_3d)


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: PASSTHROUGH ROI FILTER")
    print("=========================================================\n")

    # 4 diem mo phong cac tinh huong thuc te:
    # Diem 1: Nam trong vung an toan phia truoc (0m, 5m, 1m) -> Hop le
    # Diem 2: Nam duoi mat dat (0m, 5m, -1.5m) -> Loai bo
    # Diem 3: Nam qua xa ngoai tam quet (0m, 50m, 1m) -> Loai bo
    # Diem 4: Nam sau lung Drone (0m, -5m, 1m) -> Loai bo
    test_points = np.array([
        [0.0, 5.0, 1.0],    # Hop le (phia truoc 5m, cao 1m)
        [0.0, 5.0, -1.5],   # Duoi mat dat -> Loai
        [0.0, 50.0, 1.0],   # Qua xa -> Loai
        [0.0, -5.0, 1.0]    # Sau lung -> Loai
    ], dtype=np.float32)

    filter_box = PassthroughFilter3D(x_limits=(-10, 10), y_limits=(0, 20), z_limits=(-0.5, 5))
    roi_points = filter_box.filter(test_points)

    print("1. KET QUA LOC VUNG QUAN TAM ROI TRUOC MAT DRONE:")
    print(f"   -> So luong diem ban dau : {len(test_points)} diem")
    print(f"   -> So luong diem sau loc : {len(roi_points)} diem")
    print(f"   -> Diem hop le sau loc ROI : {roi_points}")

    assert len(roi_points) == 1 and abs(roi_points[0, 1] - 5.0) < 1e-5, "Loi Passthrough Filter!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC VUNG KHONG GIAN ROI PHAT HIEN VAT CAN CHO DRONE!")
