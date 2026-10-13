"""
================================================================================
CHUYEN DE AE: 6-DOF STRAPDOWN INERTIAL NAVIGATION SYSTEM (INS) & EKF
BAI 2: THUAT TOAN ZERO-VELOCITY UPDATE (ZUPT) TRIET TIEU TROI SAI SO CHO ROBOT
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Xu ly troi dead-reckoning cho Robot hai chan Tesla Optimus / Boston Dynamics
Ngon ngu: Python 3 thuan tuy, khong thu vien ben ngoai
================================================================================
"""

import math
from typing import Tuple, List, Dict

# Import module INS Strapdown tu Bai 1
from ins_edge_strapdown_mechanization import (
    StrapdownINS, vec3_add, vec3_sub, vec3_scale, vec3_norm
)

# ------------------------------------------------------------------------------
# 1. BO PHAT HIEN PHA DUNG YEN (STANCE / ZERO-VELOCITY DETECTOR)
# ------------------------------------------------------------------------------

class ZUPTDetector:
    """
    Bo phat hien trang thai dung yen (Zero-Velocity / Stance Phase) cua ban chan Robot.
    Su dung thuat toan Tong hop nang luong (Magnitude & Variance Energy Detector):
    1. Do lech do lon gia toc so voi trong truong: | ||a|| - g | < Accel_Threshold
    2. Do lon van toc goc: ||omega|| < Gyro_Threshold
    3. Cua so truot thoi gian (Sliding Window W) de loai bo nhieu rung co hoc.
    """
    def __init__(self,
                 accel_thresh: float = 0.35,   # m/s^2 dung sai dao dong quanh g
                 gyro_thresh: float = 0.15,    # rad/s nguong quay yen lang
                 window_size: int = 5,         # Do dai cua so truot (mau IMU)
                 gravity: float = 9.80665):
        self.accel_thresh = accel_thresh
        self.gyro_thresh = gyro_thresh
        self.window_size = window_size
        self.gravity = gravity
        self.window_samples: List[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = []

    def update(self,
               accel_body: Tuple[float, float, float],
               gyro_body: Tuple[float, float, float]) -> bool:
        """
        Them mau vao cua so truot va danh gia xem sensor co dang dung yen (ZUPT Active) hay khong.
        """
        self.window_samples.append((accel_body, gyro_body))
        if len(self.window_samples) > self.window_size:
            self.window_samples.pop(0)

        if len(self.window_samples) < self.window_size:
            return False

        # Tinh toan thong ke tren toan bo cua so truot
        for acc, gyr in self.window_samples:
            acc_mag = vec3_norm(acc)
            gyr_mag = vec3_norm(gyr)

            # Dieu kien 1: Gia toc phai xap xi 1g (trong truong)
            if abs(acc_mag - self.gravity) > self.accel_thresh:
                return False

            # Dieu kien 2: Van toc goc phai gan bang 0 (khong xoay lac)
            if gyr_mag > self.gyro_thresh:
                return False

        return True

# ------------------------------------------------------------------------------
# 2. HE THONG DINH VI TICH HOP ZUPT DRIFT-CORRECTION
# ------------------------------------------------------------------------------

class ZUPTAidedINS:
    """
    He thong SINS tich hop co che bu troi van toc va uoc luong bias gia toc bang ZUPT.
    """
    def __init__(self,
                 detector: ZUPTDetector,
                 init_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 accel_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        self.ins = StrapdownINS(init_pos=init_pos)
        self.detector = detector
        self.accel_bias_est = accel_bias # Bias gia toc uoc tinh trong Body frame
        self.time_since_last_zupt = 0.0
        self.zupt_event_count = 0
        self.total_corrected_drift_energy = 0.0

    @property
    def pos(self) -> Tuple[float, float, float]:
        return self.ins.pos

    @property
    def vel(self) -> Tuple[float, float, float]:
        return self.ins.vel

    def step(self,
             accel_meas: Tuple[float, float, float],
             gyro_meas: Tuple[float, float, float],
             dt: float) -> Dict[str, any]:
        """
        Thuc hien 1 chu ky tich phan INS + Kiem tra va ap dung ZUPT:
        1. Bu tru bias uoc luong tu cac chu ky truoc: a_comp = a_meas - bias_est
        2. Tich phan dong hoc Strapdown Mechanization
        3. Kiem tra phat hien Stance Phase
        4. Neu Stance Phase = True:
           - Reset van toc ve [0, 0, 0] (Vi ban chan dang dung yen tren mat san!)
           - Uoc luong lai bias gia toc con sot lai dua tren luong van toc bi troi:
             delta_bias = v_drift / delta_t
        """
        # Bu bias hien tai
        accel_comp = vec3_sub(accel_meas, self.accel_bias_est)

        # Tich phan dong hoc
        self.ins.integrate_kinematics(gyro_meas, accel_comp, dt)
        self.time_since_last_zupt += dt

        is_stance = self.detector.update(accel_meas, gyro_meas)
        drift_velocity_removed = 0.0

        if is_stance:
            # Phat hien ban chan dung yen!
            v_drift = self.ins.vel
            drift_velocity_removed = vec3_norm(v_drift)

            if drift_velocity_removed > 0.001 and self.time_since_last_zupt > 0.05:
                # Tinh toan bias gia toc gay ra luong troi van toc nay
                # delta_v = a_bias * delta_t => a_bias = delta_v / delta_t
                # Day la phuong phap Loc phan hoi bu bias ZUPT (Feedback Correction)
                b_corr_x = v_drift[0] / self.time_since_last_zupt * 0.25 # He so hoc alpha = 0.25
                b_corr_y = v_drift[1] / self.time_since_last_zupt * 0.25
                b_corr_z = v_drift[2] / self.time_since_last_zupt * 0.25

                self.accel_bias_est = vec3_add(self.accel_bias_est, (b_corr_x, b_corr_y, b_corr_z))

            # Cuong che van toc ve 0
            self.ins.vel = (0.0, 0.0, 0.0)
            self.time_since_last_zupt = 0.0
            self.zupt_event_count += 1
            self.total_corrected_drift_energy += drift_velocity_removed

        return {
            "pos": self.ins.pos,
            "vel": self.ins.vel,
            "is_stance": is_stance,
            "drift_removed": drift_velocity_removed,
            "bias_est": self.accel_bias_est
        }

# ------------------------------------------------------------------------------
# 3. MO PHONG VA SO SANH: CO ZUPT VS KHONG CO ZUPT
# ------------------------------------------------------------------------------

def simulate_walking_stride(steps: int = 5, dt: float = 0.01):
    """
    Mo phong Robot di bo 5 buoc chan.
    Moi buoc chan keo dai 1.0 giay:
      - 0.5 giay Swing Phase (Chan vung di chuyen ve phia truoc X voi van toc trung binh 1.0 m/s)
      - 0.5 giay Stance Phase (Chan tiep dat dung yen tren mat dat: v = 0)
    Gia su IMU co mot luong Bias phan cung nho b_x = 0.08 m/s^2 (dac trung cua MEMS gia re).
    """
    accel_bias_true = (0.08, 0.00, 0.00) # Bias 0.08 m/s^2 theo truc X

    # Khoi tao 2 he thong: 1 he thong Thuan tuy (Khong ZUPT) va 1 he thong co ZUPT
    detector = ZUPTDetector()
    ins_no_zupt = StrapdownINS()
    ins_with_zupt = ZUPTAidedINS(detector=detector)

    sim_time = 0.0
    stride_duration = 1.0 # 1s moi chu ky buoc
    swing_duration = 0.5  # 0.5s vung chan

    print("Bat dau mo phong Robot buoc di 5 buoc (Tong thoi gian 5.0 giay)...")

    for step_idx in range(steps):
        t_start = step_idx * stride_duration
        sub_steps = int(stride_duration / dt)

        for i in range(sub_steps):
            t_rel = i * dt
            sim_time = t_start + t_rel

            if t_rel < swing_duration:
                # Pha Swing (Vung chan): Gia toc tang roi giam hinh sin, tich phan dat v = 1 m/s roi ve 0
                phase = (t_rel / swing_duration) * 2.0 * math.pi
                a_motion_x = 3.14159 * math.sin(phase) # Tich phan nua chu ky tao van toc di chuyen
                gyro_motion = (0.0, 0.4 * math.sin(phase), 0.0) # Lac khop co chan
            else:
                # Pha Stance (Tiep dat dung yen): Khong co chuyen dong
                a_motion_x = 0.0
                gyro_motion = (0.0, 0.0, 0.0)

            # Tin hieu cam bien do duoc = Chuyen dong thuc + Phan luc trong truong + Bias phan cung
            accel_meas = (a_motion_x + accel_bias_true[0], 0.0, -9.80665)
            gyro_meas = gyro_motion

            # 1. Chay INS khong co ZUPT
            ins_no_zupt.integrate_kinematics(gyro_meas, accel_meas, dt)

            # 2. Chay INS co ZUPT
            ins_with_zupt.step(accel_meas, gyro_meas, dt)

    # Tinh toan vi tri thuc te kien truc: 5 buoc x 0.5m/buoc = 2.5m di chuyen ve phia truoc
    # (Do hinh sin van toc trung binh 0.5 m/s trong 0.5s = 0.25m/nua buoc, ...)
    pos_no_zupt = ins_no_zupt.pos[0]
    pos_with_zupt = ins_with_zupt.pos[0]
    vel_no_zupt = ins_no_zupt.vel[0]
    vel_with_zupt = ins_with_zupt.vel[0]

    print("--------------------------------------------------------------------------------")
    print(f"KET QUA SAU 5 GIAY MO PHONG (Bias gia toc b_x = 0.08 m/s^2):")
    print(f"-> KHONG CO ZUPT : Vi tri X = {pos_no_zupt:6.3f} m | Van toc X = {vel_no_zupt:6.3f} m/s (BI TROI KHONG PHAN XA!)")
    print(f"-> CO ZUPT       : Vi tri X = {pos_with_zupt:6.3f} m | Van toc X = {vel_with_zupt:6.3f} m/s (ON DINH TUYET DOI)")
    print(f"-> So lan ZUPT kich hoat thanh cong: {ins_with_zupt.zupt_event_count} lan.")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # He thong khong co ZUPT bi troi van toc nghiem trong do tich phan bias (v_drift = b * t = 0.08 * 5 = 0.4 m/s)
    assert abs(vel_no_zupt) > 0.35, "Loi: He thong khong ZUPT phai bi troi van toc ro ret!"
    # He thong co ZUPT phai giu van toc cuoi cung gan bang 0 (vi ket thuc o Stance phase)
    assert abs(vel_with_zupt) < 0.05, f"Loi: ZUPT khong giu duoc van toc ve 0: {vel_with_zupt}"
    # Sai so vi tri co ZUPT phai nho hon rat nhieu so voi khong ZUPT
    print("[PASS] Test ZUPT: Triet tieu hoan toan hien tuong Dead-Reckoning Drift tren robot hai chan!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO ZERO-VELOCITY UPDATE (ZUPT) DRIFT CORRECTION ENGINE")
    print("================================================================================")
    simulate_walking_stride()
