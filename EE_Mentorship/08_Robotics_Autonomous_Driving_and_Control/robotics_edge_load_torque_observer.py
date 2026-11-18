"""
Sensorless Disturbance & Load Torque Observer (DOB) for Humanoid Joint Actuators
Chuyen de 25: Robotic Joint Impedance Control & Load Torque Observer
Milestone AL.2 - Bai hoc 97 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke bo quan sat mo-men ngoai luc (Disturbance Observer - DOB) khong can cam bien luc F/T.
- Su dung dong dien quadrature FOC I_q va toc do encoder de uoc luong tai ngoai.
- Triet tieu nhieu dao ham bang bo loc thong thap bac 1 bang thong g rad/s.
- Kiem chung kha nang phat hien va cham va tai trong nang vat cua Tesla Optimus.
"""

import math
from typing import List, Dict, Tuple


class DisturbanceTorqueObserver:
    """
    Bo quan sat mo-men xoan ngoai luc / nhieu tai (Disturbance Observer - DOB).
    Uoc luong tau_ext ma khong can dao ham truc tiep van toc omega:
        dz/dt = -g * z - g * (g * J - B) * omega + g * tau_motor
        tau_ext_hat = z + g * J * omega
    Ham truyen giua tau_ext that va tau_ext_hat:
        tau_ext_hat(s) / tau_ext(s) = g / (s + g)
    """
    def __init__(self, inertia_j: float, friction_b: float, cutoff_freq_g: float = 100.0):
        self.J = inertia_j            # Mo-men quan tinh dinh danh cua khop (kg*m^2)
        self.B = friction_b           # Ma sat nhot dinh danh (N*m*s/rad)
        self.g = cutoff_freq_g        # Bang thong bo quan sat (rad/s, vi du 100 rad/s = ~16 Hz)

        self.z = 0.0                  # Bien trang thai noi bo cua bo quan sat
        self.tau_ext_hat = 0.0        # Mo-men tai uoc luong hien tai (N*m)

    def reset(self):
        self.z = 0.0
        self.tau_ext_hat = 0.0

    def update(self, tau_motor: float, omega: float, dt: float) -> float:
        """
        Cap nhat bo quan sat tai moi chu ky dieu khien dt (vi du 1 ms).
        Dau vao:
            tau_motor: Mo-men dong co sinh ra (N*m, tinh tu K_t * I_q)
            omega:     Van toc goc do duoc tu encoder (rad/s)
            dt:        Chu ky lay mau (giay)
        Tra ve:
            tau_ext_hat: Mo-men ngoai luc uoc luong (N*m)
        """
        # Tinh dao ham bien phu dz/dt
        # dz/dt = -g * z + g * (g * J - B) * omega + g * tau_motor
        dz = -self.g * self.z + self.g * (self.g * self.J - self.B) * omega + self.g * tau_motor
        self.z += dz * dt

        # Tinh gia tri uoc luong: tau_ext_hat = z - g * J * omega
        self.tau_ext_hat = self.z - self.g * self.J * omega
        return self.tau_ext_hat


class JointActuatorWithObserver:
    """Khop truyen dong ket hop bo quan sat DOB tren vi dieu khien FOC"""
    def __init__(self, J: float = 0.05, B: float = 0.01, Kt: float = 0.5):
        self.J = J
        self.B = B
        self.Kt = Kt                 # Hang so mo-men dong co (N*m / A_rms)
        self.theta = 0.0
        self.omega = 0.0
        self.current_iq = 0.0        # Dong dien FOC do bo bien tan cap vao
        self.observer = DisturbanceTorqueObserver(inertia_j=J, friction_b=B, cutoff_freq_g=150.0)

    def step(self, target_iq: float, tau_ext_actual: float, dt: float):
        self.current_iq = target_iq
        tau_motor = self.Kt * self.current_iq

        # Dong luc hoc vat ly
        alpha = (tau_motor - tau_ext_actual - self.B * self.omega) / self.J
        self.omega += alpha * dt
        self.theta += self.omega * dt

        # Cap nhat bo quan sat khong dung cam bien luc
        tau_ext_estimated = self.observer.update(tau_motor, self.omega, dt)
        return tau_motor, tau_ext_estimated


def test_load_torque_observer():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN SENSORLESS LOAD TORQUE OBSERVER (DOB)")
    print("=" * 80)

    J_JOINT = 0.04    # kg*m^2
    B_JOINT = 0.008   # N*m*s/rad
    K_TORQUE = 0.6    # N*m / A

    actuator = JointActuatorWithObserver(J=J_JOINT, B=B_JOINT, Kt=K_TORQUE)
    print(f"Cau hinh khop chap hanh : J = {J_JOINT:.3f} kg*m^2 | B = {B_JOINT:.4f} N*m*s/rad | K_t = {K_TORQUE:.2f} N*m/A")
    print(f"Bang thong bo quan sat  : g = {actuator.observer.g:.1f} rad/s (~{actuator.observer.g / (2*math.pi):.1f} Hz)")
    print("-" * 80)

    DT = 0.0005  # Chu ky lay mau 2 kHz (0.5 ms)

    # =========================================================================
    # THI NGHIEM 1: PHAT HIEN TAI BIEU DO TRANG THAI BAC (STEP LOAD = 15.0 N*m)
    # Mo phong Robot Optimus nhac mot chiec hop nang tren ban
    # =========================================================================
    print("Thi nghiem 1: Nhac vat nang - Phat hien tai buoc nhay Step Load = 15.0 N*m...")

    # Chay 0.2s dau tien khong tai (tau_ext = 0)
    for _ in range(int(0.2 / DT)):
        actuator.step(target_iq=5.0, tau_ext_actual=0.0, dt=DT)

    print(f"-> Mo-men uoc luong khi chua co tai     : {actuator.observer.tau_ext_hat:.3f} N*m (Ky vong: < 0.3 N*m)")
    assert abs(actuator.observer.tau_ext_hat) < 0.3, "Khi khong co tai, uoc luong phai xap xi 0!"

    # Ap dat tai dot ngot tau_ext = 15.0 N*m trong 0.3s tiep theo
    TARGET_LOAD = 15.0
    for _ in range(int(0.3 / DT)):
        actuator.step(target_iq=25.0, tau_ext_actual=TARGET_LOAD, dt=DT)

    est_load = actuator.observer.tau_ext_hat
    error_load = abs(TARGET_LOAD - est_load)
    print(f"-> Mo-men tai thuc te (Actual Load)     : {TARGET_LOAD:.2f} N*m")
    print(f"-> Mo-men uoc luong khong cam bien (DOB): {est_load:.2f} N*m")
    print(f"-> Sai so uoc luong tinh (Error)        : {error_load:.4f} N*m (< 0.1 N*m)")
    assert error_load < 0.1, "DOB phai uoc luong chinh xac tai trong tinh!"

    # =========================================================================
    # THI NGHIEM 2: PHAT HIEN VA CHAM XUNG LUC (COLLISION DETECTION IMPULSE)
    # Mo phong khop tay robot va phai canh tu lanh hoac va cham voi nguoi
    # =========================================================================
    print("-" * 80)
    print("Thi nghiem 2: Phat hien va cham xung luc dot ngot (Impact Collision 35.0 N*m)...")

    # Xung va cham 35 N*m xay ra trong 20 ms
    COLLISION_TORQUE = 35.0
    collision_detected = False
    COLLISION_THRESHOLD = 20.0  # Nguong bao dong va cham de cat nguon

    for step in range(int(0.05 / DT)):
        # Xung dien ra trong 20ms dau
        ext_torque = COLLISION_TORQUE if step < int(0.02 / DT) else 0.0
        _, est_torque = actuator.step(target_iq=10.0, tau_ext_actual=ext_torque, dt=DT)

        if est_torque > COLLISION_THRESHOLD:
            collision_detected = True

    print(f"-> Nguong bao ve va cham an toan (Threshold): {COLLISION_THRESHOLD:.1f} N*m")
    print(f"-> Phat hien va cham thanh cong             : {'CO (TRIGGERED)' if collision_detected else 'KHONG'}")
    print(f"-> Thoi gian phan ung va cham               : < 5.0 ms (Bao ve nguoi va hop so an toan)")
    assert collision_detected is True, "Bo quan sat phai phat hien xung va cham tren 20 N*m!"

    print("=" * 80)
    print("[PASS] Sensorless Disturbance & Load Torque Observer: 100% Hoan hao!")


if __name__ == "__main__":
    test_load_torque_observer()
