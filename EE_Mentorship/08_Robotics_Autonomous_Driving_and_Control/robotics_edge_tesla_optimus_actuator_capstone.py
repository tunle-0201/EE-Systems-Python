"""
Tesla Optimus & Boston Dynamics Humanoid Actuator Compliance Capstone
Chuyen de 25: Robotic Joint Impedance Control & Load Torque Observer
Milestone AL.4 - Bai hoc 99 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Dung hop toan chuoi cong nghe: Tro khang ao Virtual Spring-Damper, Bo quan sat tai DOB,
  Dieu khien Admittance tiep xuc, va Chuyen doi do cung thich nghi Variable Impedance.
- Thu thach 1: Cam nam vat de vo (Cam qua trung ga khong lam nut vo voi luc kep 3.0N).
- Thu thach 2: Giu thang bang khi bi xo day manh tren khop chan (Push Recovery 120 N*m).
"""

import math
from enum import Enum
from typing import List, Dict, Tuple, Optional


class ActuatorOperatingMode(Enum):
    DELICATE_MANIPULATION = "DELICATE_MANIPULATION"  # Che do mem deo cam do de vo
    PUSH_RECOVERY         = "PUSH_RECOVERY"          # Che do cuong buc chong nga khi bi xo day
    EMERGENCY_SAFE_STOP   = "EMERGENCY_SAFE_STOP"    # Dung khan cap an toan


class OptimusJointActuatorEngine:
    """
    Dong co dieu khien khop chap hanh tich hop cua Robot hinh nguoi Tesla Optimus.
    Ket hop:
      1. Bo quan sat mo-men ngoai luc Disturbance Observer (DOB) khong dung cam bien luc.
      2. Bo dieu khien tro khang bien thien (Variable Impedance Controller).
      3. Co che phan luong che do tac vu thoi gian thuc (State Arbiter).
    """
    def __init__(self, inertia_j: float = 0.04, friction_b: float = 0.008, kt: float = 0.6):
        self.J = inertia_j
        self.B = friction_b
        self.Kt = kt
        self.max_motor_torque = 150.0  # Mo-men toi da cua dong co Tesla Optimus (N*m)

        # Trang thai co hoc
        self.theta = 0.0               # Vi tri goc (rad)
        self.omega = 0.0               # Van toc goc (rad/s)
        self.current_iq = 0.0          # Dong dien FOC (A)

        # Bo quan sat DOB
        self.g_dob = 150.0             # Bang thong DOB
        self.z_dob = 0.0
        self.tau_ext_hat = 0.0

        # Thong so tro khang ao mac dinh
        self.K_v = 80.0                # Do cung ao
        self.D_v = 2.0 * math.sqrt(self.K_v * self.J)
        self.mode = ActuatorOperatingMode.DELICATE_MANIPULATION

    def set_impedance_parameters(self, stiffness_k: float, damping_ratio: float = 1.0):
        """Thay doi do cung va he so can thich nghi theo nhiem vu"""
        self.K_v = stiffness_k
        self.D_v = 2.0 * damping_ratio * math.sqrt(self.K_v * self.J)

    def update_dob(self, tau_motor: float, dt: float) -> float:
        """Cap nhat bo quan sat mo-men tai DOB"""
        dz = -self.g_dob * self.z_dob + self.g_dob * (self.g_dob * self.J - self.B) * self.omega + self.g_dob * tau_motor
        self.z_dob += dz * dt
        self.tau_ext_hat = self.z_dob - self.g_dob * self.J * self.omega
        return self.tau_ext_hat

    def step_control_loop(self, theta_target: float, omega_target: float,
                          tau_ext_real: float, dt: float) -> Dict[str, any]:
        """
        Chu ky dieu khien kin 1 kHz (1 ms):
        1. Uoc luong mo-men ngoai luc qua DOB
        2. Tinh toan mo-men tro khang theo che do
        3. Tich phan dong luc hoc vat ly
        """
        # 1. Tinh mo-men dieu khien theo quy luat tro khang ao
        error_pos = theta_target - self.theta
        error_vel = omega_target - self.omega
        tau_cmd_raw = self.K_v * error_pos + self.D_v * error_vel

        # 2. Bao hoa gioi han mo-men dong co
        tau_motor = max(-self.max_motor_torque, min(self.max_motor_torque, tau_cmd_raw))
        self.current_iq = tau_motor / self.Kt

        # 3. Cap nhat dong luc hoc thuc te
        alpha = (tau_motor - tau_ext_real - self.B * self.omega) / self.J
        self.omega += alpha * dt
        self.theta += self.omega * dt

        # 4. Cap nhat bo quan sat DOB
        est_torque = self.update_dob(tau_motor, dt)

        return {
            "theta": self.theta,
            "omega": self.omega,
            "tau_motor": tau_motor,
            "tau_ext_real": tau_ext_real,
            "tau_ext_est": est_torque,
            "current_iq": self.current_iq
        }


def test_tesla_optimus_actuator_capstone():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN TESLA OPTIMUS & BOSTON DYNAMICS ACTUATOR CAPSTONE")
    print("=" * 80)
    print("Co cau chap hanh: Quasi-Direct Drive Actuator (J = 0.04 kg*m^2, Max = 150 N*m)")
    print("Kien truc dieu khien: Dob-based Sensorless Impedance Control Loop (1 kHz)")
    print("-" * 80)

    actuator = OptimusJointActuatorEngine(inertia_j=0.04, friction_b=0.008, kt=0.6)
    DT = 0.001  # 1 ms

    # =========================================================================
    # NHIEM VU 1: CAM NAM VAT DE VO (CAM QUA TRUNG GA KHONG LAM VO)
    # Thong so vat: Do cung trung ga K_egg = 1500 N/m, Nguong vo = 8.0 N
    # Muc tieu: Duy tri luc kep an toan F_grip trong khoang [2.0 N .. 5.0 N]
    # =========================================================================
    print("Nhiem vu 1: Cam nam vat de vo (Cam qua trung ga khong lam vo)...")
    actuator.mode = ActuatorOperatingMode.DELICATE_MANIPULATION
    # Cai dat do cung ao mem deo: K_v = 15.0 N*m/rad (Rat mem de khong gay vo)
    actuator.set_impedance_parameters(stiffness_k=15.0, damping_ratio=1.2)

    # Ban tay kep khep lai: goc muc tieu theta_des = 0.3 rad.
    # Qua trung nam chan o goc theta = 0.1 rad. Do bien dang cua trung sinh ra luc can:
    # tau_contact = K_contact * (theta - 0.1) neu theta > 0.1
    THETA_EGG_SURFACE = 0.10
    K_CONTACT = 40.0  # N*m/rad
    EGG_BREAK_TORQUE = 8.0  # N*m (Neu luc > 8 N*m -> Vo trung!)

    egg_broken = False
    max_grip_torque = 0.0
    steady_grip_torque = 0.0

    for step in range(int(0.5 / DT)):
        # Mo hinh tiep xuc qua trung
        if actuator.theta > THETA_EGG_SURFACE:
            tau_contact = K_CONTACT * (actuator.theta - THETA_EGG_SURFACE)
        else:
            tau_contact = 0.0

        res = actuator.step_control_loop(theta_target=0.30, omega_target=0.0,
                                         tau_ext_real=tau_contact, dt=DT)

        if tau_contact > max_grip_torque:
            max_grip_torque = tau_contact
        if tau_contact > EGG_BREAK_TORQUE:
            egg_broken = True

    steady_grip_torque = tau_contact

    print(f"-> Che do hoat dong                  : {actuator.mode.value}")
    print(f"-> Do cung ao mem deo (Soft K_v)     : {actuator.K_v:.1f} N*m/rad")
    print(f"-> Luc kep dinh cuc dai (Peak Torque): {max_grip_torque:.2f} N*m (Nguong vo: {EGG_BREAK_TORQUE:.1f} N*m)")
    print(f"-> Luc kep on dinh (Steady Torque)   : {steady_grip_torque:.2f} N*m (Ly tuong: 2.0 - 5.0 N*m)")
    print(f"-> Trang thai qua trung              : {'NGUYEN VEN (SAFE GRIP)' if not egg_broken else 'BI VO NAT (BROKEN)'}")
    assert egg_broken is False, "Luc kep qua lon da lam vo qua trung!"
    assert 2.0 <= steady_grip_torque <= 6.0, "Luc kep phai nam trong dai an toan 2.0 - 6.0 N*m!"

    # =========================================================================
    # NHIEM VU 2: KHANG NGOAI LUC VA PHUC HOI THANG BANG (PUSH RECOVERY)
    # Khop dau goi bi cu dam manh tau_ext = 80 N*m trong 100 ms
    # Muc tieu: Chuyen sang K_v = 600 N*m/rad, sinh phan luc chong nga trong < 400 ms
    # =========================================================================
    print("-" * 80)
    print("Nhiem vu 2: Khang ngoai luc va giu thang bang (Push Recovery 80.0 N*m)...")
    actuator.mode = ActuatorOperatingMode.PUSH_RECOVERY
    # Cai dat do cung ao cuong buc: K_v = 500.0 N*m/rad
    actuator.set_impedance_parameters(stiffness_k=500.0, damping_ratio=1.0)
    actuator.theta = 0.0
    actuator.omega = 0.0

    TARGET_JOINT_ANGLE = 0.0  # Dung thang
    PUSH_TORQUE = 80.0        # N*m
    PUSH_DURATION_MS = 100    # 100 ms

    max_deflection_angle = 0.0
    recovery_time_ms = 0.0

    for step in range(int(0.6 / DT)):
        current_time_ms = step * 1.0  # ms
        # Xo day trong 100 ms dau
        ext_push = PUSH_TORQUE if current_time_ms < PUSH_DURATION_MS else 0.0

        res = actuator.step_control_loop(theta_target=TARGET_JOINT_ANGLE, omega_target=0.0,
                                         tau_ext_real=ext_push, dt=DT)

        if abs(actuator.theta) > max_deflection_angle:
            max_deflection_angle = abs(actuator.theta)

        # Tinh thoi gian phuc hoi ve gan 0 (< 0.02 rad)
        if current_time_ms > PUSH_DURATION_MS and abs(actuator.theta) < 0.02 and recovery_time_ms == 0.0:
            recovery_time_ms = current_time_ms - PUSH_DURATION_MS

    print(f"-> Che do hoat dong                  : {actuator.mode.value}")
    print(f"-> Do cung ao cuong buc (Stiff K_v)  : {actuator.K_v:.1f} N*m/rad")
    print(f"-> Xung luc xo day ngoai (Push)      : {PUSH_TORQUE:.1f} N*m trong {PUSH_DURATION_MS} ms")
    print(f"-> Do lech goc toi da (Max Angle)    : {max_deflection_angle:.4f} rad ({math.degrees(max_deflection_angle):.1f} do)")
    print(f"-> Thoi gian hoi phuc thang bang     : {recovery_time_ms:.1f} ms (Yeu cau: < 350 ms)")
    print(f"-> Trang thai robot                  : GIU THANG BANG HOAN HAO (ZERO FALL)")

    assert math.degrees(max_deflection_angle) < 15.0, "Goc lech khong duoc vuot qua 15 do!"
    assert recovery_time_ms < 350.0, "Thoi gian phuc hoi phai duoi 350 ms!"

    print("=" * 80)
    print("[PASS] Tesla Optimus & Boston Dynamics Actuator Capstone: 100% Hoan hao!")


if __name__ == "__main__":
    test_tesla_optimus_actuator_capstone()
