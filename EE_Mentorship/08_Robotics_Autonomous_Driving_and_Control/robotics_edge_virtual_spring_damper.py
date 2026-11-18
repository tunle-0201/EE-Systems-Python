"""
Virtual Spring-Damper Mechanical Impedance Controller for Humanoid Robot Joints
Chuyen de 25: Robotic Joint Impedance Control & Load Torque Observer
Milestone AL.1 - Bai hoc 96 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke bo dieu khien tro khang co hoc ao (Virtual Spring-Damper) cho khop Tesla Optimus.
- Mo phong dong luc hoc khop truyen dong: Quan tinh J, Ma sat nhot B, Do cung ao K_v, He so can D_v.
- Tinh toan he so can toi han (Critical Damping) de triet tieu dao dong va hap thu xung luc va cham.
"""

import math
from typing import List, Dict, Tuple


class JointPhysicalModel:
    """
    Mo hinh vat ly dong luc hoc khop truyen dong Robot (Actuator Joint Dynamics).
    Phuong trinh vi phan Newton-Euler:
        J * d(omega)/dt = tau_motor - tau_ext - B_fric * omega
    """
    def __init__(self, inertia_j: float = 0.05, viscous_friction_b: float = 0.01):
        self.J = inertia_j            # Mo-men quan tinh khop (kg*m^2)
        self.B = viscous_friction_b   # Ma sat nhot co hoc (N*m*s/rad)
        self.theta = 0.0              # Vi tri goc quay hien tai (rad)
        self.omega = 0.0              # Van toc goc quay hien tai (rad/s)

    def step(self, tau_motor: float, tau_ext: float, dt: float):
        """Tich phan Euler cap 1 cap nhat vi tri va van toc khop"""
        # Gia toc goc: alpha = (tau_motor - tau_ext - B*omega) / J
        alpha = (tau_motor - tau_ext - self.B * self.omega) / self.J
        self.omega += alpha * dt
        self.theta += self.omega * dt


class VirtualImpedanceController:
    """
    Bo dieu khien tro khang ao (Virtual Mechanical Impedance Controller).
    Tao ra dac tinh co bap nhan tao mem deo (Compliant Actuation).
    Mo-men dieu khien mong muon:
        tau_cmd = K_v * (theta_des - theta) + D_v * (omega_des - omega)
    """
    def __init__(self, stiffness_k: float, damping_d: float, max_torque_limit: float = 50.0):
        self.K_v = stiffness_k              # Do cung ao (N*m/rad)
        self.D_v = damping_d                # He so giam chan ao (N*m*s/rad)
        self.max_torque = max_torque_limit  # Gioi han mo-men an toan bao ve cuon day (N*m)

    @classmethod
    def create_critically_damped(cls, stiffness_k: float, inertia_j: float, max_torque: float = 50.0):
        """
        Tinh toan he so can toi han (Critical Damping):
        D_crit = 2 * sqrt(K_v * J)
        Dam bao he thong khong bi vot lo (Overshoot = 0%) khi tro ve diem can bang.
        """
        d_crit = 2.0 * math.sqrt(stiffness_k * inertia_j)
        return cls(stiffness_k=stiffness_k, damping_d=d_crit, max_torque_limit=max_torque)

    def compute_torque(self, theta_des: float, omega_des: float,
                       theta_actual: float, omega_actual: float) -> float:
        """Tinh toan mo-men xoan can phat boi dong co FOC"""
        error_pos = theta_des - theta_actual
        error_vel = omega_des - omega_actual

        tau_spring = self.K_v * error_pos
        tau_damper = self.D_v * error_vel
        tau_raw = tau_spring + tau_damper

        # Bao hoa mo-men bao ve co cau chap hanh (Torque Saturation)
        tau_clamped = max(-self.max_torque, min(self.max_torque, tau_raw))
        return tau_clamped


def test_virtual_spring_damper_controller():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN VIRTUAL SPRING-DAMPER IMPEDANCE CONTROLLER")
    print("=" * 80)

    # 1. Thong so khop robot Tesla Optimus (Khop khuyu tay / Dau goi)
    J_ACTUATOR = 0.05  # kg*m^2 (Rotor + Cycloidal Gearbox 1:50)
    B_FRICTION = 0.005 # N*m*s/rad
    K_VIRTUAL = 100.0  # N*m/rad (Do cung ao tuong duong 1.74 N*m/do)

    joint = JointPhysicalModel(inertia_j=J_ACTUATOR, viscous_friction_b=B_FRICTION)
    controller = VirtualImpedanceController.create_critically_damped(
        stiffness_k=K_VIRTUAL, inertia_j=J_ACTUATOR, max_torque=60.0
    )

    print(f"Thong so khop chap hanh : Quan tinh J = {J_ACTUATOR:.3f} kg*m^2")
    print(f"Do cung ao (Stiffness) : K_v = {controller.K_v:.1f} N*m/rad")
    print(f"Giam chan toi han (Damp): D_v = {controller.D_v:.3f} N*m*s/rad (D_crit = 2*sqrt(K*J))")
    print("-" * 80)

    # =========================================================================
    # GIAI DOAN 1: KHONG CO NGOAI LUC - BAM VI TRI MONG MUON (THETA_DES = 1.0 RAD)
    # =========================================================================
    print("Giai doan 1: Bam vi tri mong muon theta_des = 1.0 rad (Khong co ngoai luc)...")
    DT = 0.001  # Chu ky dieu khien 1 kHz (1 ms)
    SIM_TIME_1 = 0.5  # 500 ms

    theta_target = 1.0
    omega_target = 0.0

    steps_1 = int(SIM_TIME_1 / DT)
    for _ in range(steps_1):
        tau_cmd = controller.compute_torque(theta_target, omega_target, joint.theta, joint.omega)
        joint.step(tau_motor=tau_cmd, tau_ext=0.0, dt=DT)

    print(f"-> Vi tri sau 0.5s               : {joint.theta:.4f} rad (Ky vong: {theta_target:.4f} rad)")
    print(f"-> Sai so vi tri tinh (Steady-state): {abs(theta_target - joint.theta):.5f} rad")
    assert abs(theta_target - joint.theta) < 0.01, "Khop phai bam sat diem dat!"

    # =========================================================================
    # GIAI DOAN 2: VA CHAM VAT LY - CON NGUOI TAC DUNG NGOAI LUC DAY LECH KHOP
    # =========================================================================
    print("-" * 80)
    print("Giai doan 2: Va cham ngoai luc - Tac dung luc can tau_ext = 20.0 N*m...")
    TAU_EXT = 20.0  # N*m
    SIM_TIME_2 = 0.5

    steps_2 = int(SIM_TIME_2 / DT)
    for _ in range(steps_2):
        tau_cmd = controller.compute_torque(theta_target, omega_target, joint.theta, joint.omega)
        joint.step(tau_motor=tau_cmd, tau_ext=TAU_EXT, dt=DT)

    # Do lech vi tri ly thuyet khi can bang tinh: delta_theta = tau_ext / K_v = 20 / 100 = 0.2 rad
    expected_displacement = TAU_EXT / K_VIRTUAL
    actual_displacement = theta_target - joint.theta
    print(f"-> Vi tri bi day lech            : {joint.theta:.4f} rad")
    print(f"-> Do lech co hoc mem deo        : {actual_displacement:.4f} rad (Ly thuyet: {expected_displacement:.4f} rad)")
    print(f"-> Mo-men dong co phan hoi       : {tau_cmd:.2f} N*m (Tu dong can bang voi ngoai luc 20 N*m)")
    assert abs(actual_displacement - expected_displacement) < 0.01, "Do mem deo tro khang phai dung dinh luat Hooke!"

    # =========================================================================
    # GIAI DOAN 3: THA NGOAI LUC - HOI PHUC MEM MAI KHONG VOT LO (CRITICALLY DAMPED)
    # =========================================================================
    print("-" * 80)
    print("Giai doan 3: Tha ngoai luc (tau_ext = 0) - Quan sat qua do tro ve diem can bang...")
    SIM_TIME_3 = 0.5
    steps_3 = int(SIM_TIME_3 / DT)
    max_overshoot = 0.0

    for _ in range(steps_3):
        tau_cmd = controller.compute_torque(theta_target, omega_target, joint.theta, joint.omega)
        joint.step(tau_motor=tau_cmd, tau_ext=0.0, dt=DT)
        if joint.theta > theta_target:
            overshoot = joint.theta - theta_target
            if overshoot > max_overshoot:
                max_overshoot = overshoot

    print(f"-> Vi tri sau khi hoi phuc       : {joint.theta:.4f} rad")
    print(f"-> Do vot lo cuc dai (Overshoot) : {max_overshoot:.5f} rad (0.0 rad nho giam chan toi han)")
    print(f"-> Trang thai bao ve hop so      : HOAN TOAN AN TOAN (Khong bi soc co hoc)")
    assert max_overshoot < 0.005, "He thong suy giam toi han khong duoc co vot lo dang ke!"

    print("=" * 80)
    print("[PASS] Virtual Spring-Damper Mechanical Impedance Controller: 100% Hoan hao!")


if __name__ == "__main__":
    test_virtual_spring_damper_controller()
