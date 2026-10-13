"""
================================================================================
CHUYEN DE AE: 6-DOF STRAPDOWN INERTIAL NAVIGATION SYSTEM (INS) & EKF
BAI 4: DONG CO DINH VI DAN DUONG TAU VU TRU VA DUNG HOP EKF CAPSTONE
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tich hop toan chuoi dan duong SpaceX Starship / Falcon 9 Autonomous Landing
Ngon ngu: Python 3 thuan tuy, kien truc Module huong doi tuong thoi gian thuc
================================================================================
"""

import math
import random
from typing import Tuple, List, Dict, Optional

from ins_edge_strapdown_mechanization import (
    StrapdownINS, quat_to_euler, vec3_norm, vec3_sub
)
from ins_edge_zupt_drift_correction import ZUPTDetector
from ins_edge_extended_kalman_filter import ErrorStateEKF

# ------------------------------------------------------------------------------
# 1. TRANG THAI CHE DO DAN DUONG (NAVIGATION MODES)
# ------------------------------------------------------------------------------

class NavStateMode:
    NOMINAL_FUSION   = "NOMINAL_FUSION"     # Day du IMU 100 Hz + GNSS 10 Hz
    GNSS_BLACKOUT    = "GNSS_BLACKOUT"      # Mat GNSS (Inertial Coasting tu bu bias)
    TOUCHDOWN_ZUPT   = "TOUCHDOWN_ZUPT"     # Tiep dat bệ ha canh, kich hoat ZUPT
    LANDED_SAFE      = "LANDED_SAFE"        # Hoan thanh ha canh an toan

# ------------------------------------------------------------------------------
# 2. DONG CO DAN DUONG TAU VU TRU TOAN CHUOI (SPACECRAFT NAVIGATION ENGINE)
# ------------------------------------------------------------------------------

class SpacecraftNavEngine:
    """
    Dong co dan duong tau vu tru tich hop:
    - Bo loc 15-State ES-EKF (Predict IMU 100 Hz, Update GNSS 10 Hz)
    - Bo phat hien tiep dat ZUPT (Touchdown detector)
    - Co che Fail-operational khi mat tin hieu GNSS (Inertial Coasting)
    """
    def __init__(self,
                 init_pos: Tuple[float, float, float] = (0.0, 0.0, -65.0), # Cao do 65m (-Z la Up trong NED)
                 init_vel: Tuple[float, float, float] = (0.0, 0.0, 8.0)):   # Ha canh xuong 8 m/s (+Z la Down)
        self.ekf = ErrorStateEKF(init_pos=init_pos, init_vel=init_vel)
        # Tang toc do hoc bias cho EKF
        for i in range(3):
            self.ekf.P[i+9][i+9] = 0.05
            self.ekf.Q_diag[i+9] = 0.001

        self.zupt_detector = ZUPTDetector(accel_thresh=0.4, gyro_thresh=0.2, window_size=5)
        self.mode = NavStateMode.NOMINAL_FUSION
        self.flight_time = 0.0
        self.gnss_blackout_active = False

    def process_imu_sample(self,
                           accel_meas: Tuple[float, float, float],
                           gyro_meas: Tuple[float, float, float],
                           dt: float) -> None:
        """
        Xu ly mau IMU o tan so cao (100 Hz):
        - Predict trang thai sai so va nominal kinematics
        - Kiem tra dieu kien tiep dat (Touchdown ZUPT)
        """
        self.flight_time += dt

        # EKF Time Update (Prediction)
        self.ekf.predict(accel_meas, gyro_meas, dt)

        # Kiem tra tiep dat
        if self.mode == NavStateMode.TOUCHDOWN_ZUPT or self.mode == NavStateMode.LANDED_SAFE:
            is_stance = self.zupt_detector.update(accel_meas, gyro_meas)
            if is_stance:
                # Khoa van toc tuyet doi ve 0
                self.ekf.ins.vel = (0.0, 0.0, 0.0)
                self.mode = NavStateMode.LANDED_SAFE

    def process_gnss_sample(self,
                            gnss_pos: Optional[Tuple[float, float, float]],
                            gnss_noise_std: float = 0.2) -> None:
        """
        Xu ly phep do GNSS o tan so thap (10 Hz):
        - Neu co tin hieu: EKF Measurement Update va duy tri che do NOMINAL_FUSION
        - Neu mat tin hieu (Blackout): Chuyen sang che do GNSS_BLACKOUT
        """
        if gnss_pos is not None and not self.gnss_blackout_active:
            self.ekf.update_gnss_position(gnss_pos, gnss_noise_std=gnss_noise_std)
            if self.mode != NavStateMode.TOUCHDOWN_ZUPT and self.mode != NavStateMode.LANDED_SAFE:
                self.mode = NavStateMode.NOMINAL_FUSION
        else:
            if self.mode != NavStateMode.TOUCHDOWN_ZUPT and self.mode != NavStateMode.LANDED_SAFE:
                self.mode = NavStateMode.GNSS_BLACKOUT

    def set_blackout(self, active: bool) -> None:
        """Kich hoat hoac tat tinh trang mat tin hieu GNSS."""
        self.gnss_blackout_active = active
        if active and self.mode == NavStateMode.NOMINAL_FUSION:
            self.mode = NavStateMode.GNSS_BLACKOUT

    def trigger_touchdown(self) -> None:
        """Cam bien tiep xuc chan ha canh (Landing Leg Contact Switch) cham mat dat."""
        self.mode = NavStateMode.TOUCHDOWN_ZUPT

    @property
    def current_state(self) -> Dict[str, any]:
        pos = self.ekf.ins.pos
        vel = self.ekf.ins.vel
        r, p, y = quat_to_euler(self.ekf.ins.quat)
        return {
            "pos": pos,
            "vel": vel,
            "attitude_euler_deg": (math.degrees(r), math.degrees(p), math.degrees(y)),
            "accel_bias": self.ekf.accel_bias,
            "mode": self.mode
        }

# ------------------------------------------------------------------------------
# 3. KICH BAN MO PHONG CAPSTONE: STARSHIP AUTONOMOUS DESCENT & LANDING
# ------------------------------------------------------------------------------

def run_spacecraft_landing_simulation():
    """
    Mo phong kịch bản hạ cánh tàu vũ trụ Starship kéo dài 16 giây:
    - Giai doan 1 (0s - 6s): Ha canh danh dinh co du ca IMU 100 Hz va GNSS 10 Hz (Hoc bias gia toc).
    - Giai doan 2 (6s - 10s): PLASMA / GNSS BLACKOUT trong 4 giay! Chay Inertial Coasting tu bu bias.
    - Giai doan 3 (10s - 13.5s): GNSS khoi phuc tro lai, EKF khoa lai vi tri.
    - Giai doan 4 (13.5s - 16s): Tau tiep dat nhe nhang tren Landing pad (Touchdown ZUPT Lock).
    """
    random.seed(101)
    nav_engine = SpacecraftNavEngine(
        init_pos=(0.0, 0.0, -65.0), # Cao do 65m (NED -Z)
        init_vel=(0.0, 0.0, 8.0)    # Roi xuong 8.0 m/s (NED +Z)
    )

    dt_imu = 0.01   # 100 Hz
    dt_gnss = 0.10  # 10 Hz
    total_duration = 16.0
    steps = int(total_duration / dt_imu)

    # Phan cung IMU co bias:
    true_accel_bias = (0.10, -0.06, 0.04) # m/s^2

    # Ground truth
    true_pos = [0.0, 0.0, -65.0]
    true_vel = [0.0, 0.0, 8.0]

    gnss_timer = 0.0
    telemetry_log: List[Dict[str, any]] = []

    print("================================================================================")
    print("BAT DAU MO PHONG SPACECRAFT DESCENT & AUTONOMOUS LANDING (CAPSTONE)")
    print("================================================================================")
    print("Thoi gian: 16 giay | IMU: 100 Hz | GNSS: 10 Hz | Blackout: tu giay 6.0 den giay 10.0")
    print("--------------------------------------------------------------------------------")

    for step in range(steps):
        t = step * dt_imu

        # Cap nhat che do theo thoi gian:
        if 6.0 <= t < 10.0:
            nav_engine.set_blackout(True)
        elif 10.0 <= t < 13.5:
            nav_engine.set_blackout(False)
        elif t >= 13.5:
            nav_engine.set_blackout(False)
            nav_engine.trigger_touchdown()

        # Động học vật lý chân thực của tàu:
        if t < 13.5:
            # Gia tốc hãm Z nhẹ nhàng a_cmd_z = -0.55 m/s^2
            a_cmd_z = -0.55
            true_vel[2] = max(0.1, true_vel[2] + a_cmd_z * dt_imu)
            true_pos[2] += true_vel[2] * dt_imu
            accel_true_body = (0.0, 0.0, -9.80665 + a_cmd_z)
            gyro_true_body = (0.0, 0.0, 0.0)
        else:
            # Tiếp đất nhẹ nhàng tại bệ Z = 0
            true_vel = [0.0, 0.0, 0.0]
            true_pos[2] = min(0.0, true_pos[2])
            accel_true_body = (0.0, 0.0, -9.80665)
            gyro_true_body = (0.0, 0.0, 0.0)

        # Cảm biến IMU: Thực + Bias + Nhiễu
        noise_a = (random.gauss(0, 0.02), random.gauss(0, 0.02), random.gauss(0, 0.02))
        noise_w = (random.gauss(0, 0.003), random.gauss(0, 0.003), random.gauss(0, 0.003))

        accel_meas = (
            accel_true_body[0] + true_accel_bias[0] + noise_a[0],
            accel_true_body[1] + true_accel_bias[1] + noise_a[1],
            accel_true_body[2] + true_accel_bias[2] + noise_a[2]
        )
        gyro_meas = (
            gyro_true_body[0] + noise_w[0],
            gyro_true_body[1] + noise_w[1],
            gyro_true_body[2] + noise_w[2]
        )

        # 1. IMU 100 Hz
        nav_engine.process_imu_sample(accel_meas, gyro_meas, dt_imu)

        # 2. GNSS 10 Hz
        gnss_timer += dt_imu
        if gnss_timer >= dt_gnss:
            gnss_timer = 0.0
            if nav_engine.gnss_blackout_active:
                nav_engine.process_gnss_sample(None)
            else:
                noise_gnss = (random.gauss(0, 0.2), random.gauss(0, 0.2), random.gauss(0, 0.2))
                gnss_meas = (
                    true_pos[0] + noise_gnss[0],
                    true_pos[1] + noise_gnss[1],
                    true_pos[2] + noise_gnss[2]
                )
                nav_engine.process_gnss_sample(gnss_meas, gnss_noise_std=0.2)

        # Ghi log Telemetry moi 1.0 giay
        if step % int(1.0 / dt_imu) == 0 or step == steps - 1:
            state = nav_engine.current_state
            pos_err = vec3_norm(vec3_sub(state["pos"], tuple(true_pos)))
            telemetry_log.append({
                "time": t,
                "mode": state["mode"],
                "true_pos": tuple(true_pos),
                "est_pos": state["pos"],
                "pos_err": pos_err,
                "est_bias": state["accel_bias"]
            })

    # In bang thong ke Telemetry
    print(f"{'Time(s)':<8} | {'Mode':<16} | {'True Pos Z(m)':<14} | {'Est Pos Z(m)':<14} | {'Pos Err(m)':<10} | {'Bias X(m/s^2)':<12}")
    print("-" * 84)
    for entry in telemetry_log:
        print(f"{entry['time']:<8.1f} | {entry['mode']:<16} | {entry['true_pos'][2]:<14.2f} | {entry['est_pos'][2]:<14.2f} | {entry['pos_err']:<10.3f} | {entry['est_bias'][0]:<12.3f}")

    print("--------------------------------------------------------------------------------")
    final_entry = telemetry_log[-1]
    blackout_peak_err = max(e["pos_err"] for e in telemetry_log if 6.0 <= e["time"] <= 10.0)

    print(f"-> Sai so vi tri cuc dai trong suot 4 giay GNSS Blackout: {blackout_peak_err:.3f} m (Tieu chuan < 2.0 m)")
    print(f"-> Sai so vi tri cuoi cung khi ha canh (Touchdown):       {final_entry['pos_err']:.3f} m (Tieu chuan < 0.35 m)")
    print(f"-> Che do cuoi cung cua he thong:                        {final_entry['mode']}")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi Capstone nghiem ngat:
    # 1. Trong thoi gian Blackout mat GNSS 4s, nho hoc duoc bias truoc do, sai so giu duoc duoi 2.0m
    assert blackout_peak_err < 2.0, f"Loi: Blackout drift vuot nguong: {blackout_peak_err} m"
    # 2. Sai so cuoi cung khi tiep dat phai cuc ky chuan xac (< 0.35 m)
    assert final_entry["pos_err"] < 0.35, f"Loi: Sai so tiep dat lon: {final_entry['pos_err']} m"
    # 3. He thong phai ket thuc o trang thai LANDED_SAFE
    assert final_entry["mode"] == NavStateMode.LANDED_SAFE, "Loi: Khong kich hoat duoc LANDED_SAFE!"
    print("[PASS] Capstone Spacecraft Navigation Engine: Thuc thi xuat sac kich ban ha canh Starship!")

if __name__ == "__main__":
    run_spacecraft_landing_simulation()
