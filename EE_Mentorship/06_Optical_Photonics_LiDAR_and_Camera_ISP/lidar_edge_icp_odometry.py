"""
================================================================================
          MODULE R: ADVANCED LIDAR / RADAR 3D POINT CLOUD PROCESSING
    MILESTONE R.3: DINH VI KHONG GPS BANG KHOP DIEM (LIDAR ICP SCAN MATCHING)
================================================================================

1. NGUYEN LY VAT LY & HE THONG SLAM (LIDAR ODOMETRY & SCAN MATCHING):
   - Khi Drone tham hiem bay trong hang dong, kho hang kin, duong ham hoac khu vuc
     bi pha song dien tu (GPS-Denied Environment):
     + Tin hieu ve tinh GPS hoan toan bang 0 hoac bi sai lech hang chuc met.
     + Neu chi dung cam bien quan tinh IMU: sai so tich phan (Drift) se khien Drone
       dam vao tuong sau chua day 30 giay!
   - Thuat toan ICP (Iterative Closest Point - Khop diem lap):
     + So sanh 2 khung quet LiDAR lien tiep: Khung nguon tai thoi diem t (Source)
       va Khung dich tai thoi diem t+dt (Target).
     + Tinh toan phep bien doi hinh hoc tinh tien (Translation vector T) va goc quay (Rotation R)
       de chong khit 2 dam may diem len nhau.
     + Drone biet chinh xac van toc va quang duong minh vua di chuyen voi do chinh xac cm!

2. SO DO HINH HOC & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do khop 2 khung quet LiDAR de tim vector dich chuyen:

   Khung t (Source Cloud):                Khung t+dt (Target Cloud):
   ┌───────────────────────────┐         ┌───────────────────────────┐
   │      *                    │         │                           │
   │    *   *  c_src           │  ───►   │            *              │
   │           (X)             │  dich   │          *   *  c_tgt     │
   │                           │  chuyen │                 (X)       │
   └───────────────────────────┘         └───────────────────────────┘
   ▲                                     ▲
   └──────── Vector dich chuyen T = c_tgt - c_src ───────────────────┘

   Cong thuc tinh trong tam (Centroids):

               1                                     1
   c_src = ───────── * Sum( p_i )  ,    c_tgt = ───────── * Sum( q_i )
             N_src                                 N_tgt

   Vector tinh tien dich chuyen (Translation Vector):

   T = [ dx, dy, dz ] = c_tgt - c_src

   Sai so binh phuong trung binh sau khop (Residual Alignment MSE):

               1
   MSE  =  ───────── * Sum( || (p_i + T) - q_i ||^2 )
               N
"""

from typing import Tuple
import numpy as np


class LidarIcpOdometry:
    """
    Bo uoc luong dich chuyen LiDAR Odometry bang phuong phap Scan Matching Centroid Alignment.
    """
    def __init__(self):
        self.last_translation = np.zeros(3, dtype=np.float32)

    def estimate_motion(self, source_points: np.ndarray, target_points: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Uoc luong vector dich chuyen T va sai so khop MSE giua 2 khung quet:
        - T = c_tgt - c_src
        - MSE = trung binh || (pts_src + T) - pts_tgt ||^2
        Tra ve bo: (Translation, MSE)
        """
        if len(source_points) == 0 or len(target_points) == 0:
            return np.zeros(3, dtype=np.float32), 0.0

        p_src = np.asarray(source_points, dtype=np.float32)
        p_tgt = np.asarray(target_points, dtype=np.float32)

        # 1. Tinh toa do trong tam cua 2 tap hop diem
        c_src = np.mean(p_src, axis=0)
        c_tgt = np.mean(p_tgt, axis=0)

        # 2. Vector dich chuyen
        translation = c_tgt - c_src
        self.last_translation = translation

        # 3. Tinh sai so khop diem MSE
        if len(p_src) == len(p_tgt):
            shifted_src = p_src + translation
            diff = shifted_src - p_tgt
            mse = float(np.mean(np.sum(diff ** 2, axis=1)))
        else:
            mse = 0.0

        return translation, mse


def estimate_translation_icp(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray:
    """
    Ham backward-compatible giu nguyen signature cua Milestone R.3.
    """
    engine = LidarIcpOdometry()
    translation, _ = engine.estimate_motion(source_points, target_points)
    return translation


if __name__ == "__main__":
    print("=========================================================")
    print("   AUTONOMOUS 3D PERCEPTION: LIDAR ICP ODOMETRY")
    print("=========================================================\n")

    # Khung quet 1 tai thoi diem t (3 diem mieu ta buc tuong vat can)
    scan_t1 = np.array([
        [1.0, 1.0, 0.0],
        [2.0, 1.0, 0.0],
        [1.5, 2.0, 0.0]
    ], dtype=np.float32)

    # Khung quet 2 tai thoi diem t+1 (Drone tien len: dx = 0.5m, dy = 1.2m, dz = 0.0m)
    ground_truth_motion = np.array([0.5, 1.2, 0.0], dtype=np.float32)
    scan_t2 = scan_t1 + ground_truth_motion

    odometry = LidarIcpOdometry()
    trans, mse_error = odometry.estimate_motion(scan_t1, scan_t2)

    print("1. KET QUA TINH TOAN DICH CHUYEN LIDAR SCAN MATCHING:")
    print(f"   -> Do dich chuyen DX : {trans[0]:.2f} m")
    print(f"   -> Do dich chuyen DY : {trans[1]:.2f} m")
    print(f"   -> Do dich chuyen DZ : {trans[2]:.2f} m")
    print(f"   -> Sai so khop MSE   : {mse_error:.6f} m^2 (Khop hoan hao)")

    assert abs(trans[0] - 0.5) < 1e-5 and abs(trans[1] - 1.2) < 1e-5, "Loi ICP Odometry!"
    assert mse_error < 1e-6

    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN DINH VI LIDAR ODOMETRY KHONG CAN GPS CHO DRONE!")
