"""
================================================================================
CHUYEN DE AG: HARDWARE MOTOR FIELD WEAKENING & OVERMODULATION (FW & OVM)
BAI 1: BO DIEU KHIEN SUY GIAM TU THONG FIELD WEAKENING CHO DONG CO TOC DO CAO
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: He truyen dong sieu toc Tesla Model S Plaid / Khop noi Robot Optimus
Ngon ngu: Python 3 thuan tuy, mo phong dong hoc FOC va Back-EMF truc truc d-q
================================================================================
"""

import math
from typing import Tuple, Dict, List

# ------------------------------------------------------------------------------
# 1. CAC THONG SO VAT LY DONG CO DONG BO NAM CHAM VINH CUU (IPMSM)
# ------------------------------------------------------------------------------

class MotorParameters:
    """
    Thong so dong co dien dong bo nam cham vinh cuu kieu nam chim (IPMSM) Tesla Plaid:
    - Rs: Dien tro cuon day stator (Ohm)
    - Ld: Dien cam truc d (Henry)
    - Lq: Dien cam truc q (Henry, Lq > Ld do hieu ung di huong tu tro)
    - lambda_pm: Tu thong nam cham vinh cuu rotor (Weber / V.s)
    - pole_pairs (p): So cap cuc tu (p = 4 -> 8 cuc)
    - Vdc: Dien ap nguon pin DC-link (Volt, vi du pin 400V)
    - I_max: Dong dien stator dinh muc cuc dai (Ampe)
    """
    def __init__(self,
                 Rs: float = 0.05,            # 50 mOhm
                 Ld: float = 0.00025,         # 0.25 mH
                 Lq: float = 0.00060,         # 0.60 mH
                 lambda_pm: float = 0.08,     # 0.08 Wb
                 pole_pairs: int = 4,
                 Vdc: float = 400.0,
                 I_max: float = 250.0):
        self.Rs = Rs
        self.Ld = Ld
        self.Lq = Lq
        self.lambda_pm = lambda_pm
        self.pole_pairs = pole_pairs
        self.Vdc = Vdc
        self.I_max = I_max

        # Dien ap pha cuc dai trong vung tuyen tinh cua bien tan SVPWM:
        # V_max = Vdc / sqrt(3)
        self.V_max = Vdc / math.sqrt(3.0) # ~ 230.94 V

# ------------------------------------------------------------------------------
# 2. BO DIEU KHIEN SUY GIAM TU THONG FIELD WEAKENING CONTROLLER
# ------------------------------------------------------------------------------

class FieldWeakeningController:
    """
    Bo dieu khien Field Weakening (Khau phan hoi dien ap Voltage Feedback):
    Khi toc do cao lam dien ap yeu cau V_mag = sqrt(Vd^2 + Vq^2) tien gan V_max:
    Bo dieu khien bom dong am Id < 0 vao truc d de tao tu truong nguoc chieu,
    khu bot tu thong nam cham, ghim Back-EMF xuong duoi nguong gioi han V_max.
    """
    def __init__(self, motor: MotorParameters, kp_fw: float = 0.8, ki_fw: float = 20.0):
        self.motor = motor
        self.kp_fw = kp_fw
        self.ki_fw = ki_fw
        self.integrator_fw = 0.0

    def compute_id_ref(self,
                       iq_ref: float,
                       vd: float,
                       vq: float,
                       dt: float) -> Tuple[float, float]:
        """
        Dau vao:
          - iq_ref: Dong dien tao mo-men xoan yeu cau tren truc q
          - vd, vq: Dien ap thuc te dang cap boi bo dieu khien FOC
          - dt: Buoc thoi gian lay mau
        Tra ve:
          - id_ref: Dong dien suy giam tu thong tren truc d (<= 0)
          - iq_ref_limited: Dong iq sau khi kep trong vong tron dong dien gioi han
        """
        # Tinh bien do dien ap hien tai: V_mag = sqrt(Vd^2 + Vq^2)
        v_mag = math.sqrt(vd * vd + vq * vq)

        # Sai lech dien ap so voi nguong cho phep (dat nguong 98% V_max de an toan)
        v_margin = 0.98 * self.motor.V_max
        v_error = v_mag - v_margin

        # Bo dieu khien PI Field Weakening (chi kich hoat khi V_mag vuot qua nguong v_margin)
        if v_error > 0.0:
            self.integrator_fw += self.ki_fw * v_error * dt
        else:
            # Giam tich luy khi dien ap thap hon nguong
            self.integrator_fw += self.ki_fw * v_error * dt * 2.0
            if self.integrator_fw < 0.0:
                self.integrator_fw = 0.0

        # Gioi han tich luy khong vuot qua dong dien toi da cua dong co
        self.integrator_fw = min(self.motor.I_max, max(0.0, self.integrator_fw))

        # Dong id am (Id_ref <= 0)
        id_fw_mag = self.kp_fw * max(0.0, v_error) + self.integrator_fw
        id_ref = -min(self.motor.I_max, id_fw_mag)

        # Gioi han dong iq trong vong tron dong dien cuc dai:
        # Id^2 + Iq^2 <= I_max^2  ==>  Iq_max = sqrt(I_max^2 - Id^2)
        remaining_current_sq = self.motor.I_max ** 2 - id_ref ** 2
        iq_limit = math.sqrt(max(0.0, remaining_current_sq))
        iq_ref_limited = min(iq_limit, max(-iq_limit, iq_ref))

        return (id_ref, iq_ref_limited)

# ------------------------------------------------------------------------------
# 3. MO PHONG DONG CO IPMSM TRONG HE TOA DO QUAY D-Q
# ------------------------------------------------------------------------------

class IPMSMPlant:
    """
    Mo hinh trang thai dong hoc dong co IPMSM tren he truc d-q:
    Vd = Rs * Id + Ld * (dId/dt) - omega_e * Lq * Iq
    Vq = Rs * Iq + Lq * (dIq/dt) + omega_e * (Ld * Id + lambda_pm)
    """
    def __init__(self, motor: MotorParameters):
        self.m = motor
        self.id_actual = 0.0
        self.iq_actual = 0.0

    def step(self, vd: float, vq: float, speed_rpm: float, dt: float) -> Tuple[float, float, float]:
        """
        Tich phan 1 buoc thoi gian:
        Tra ve (id_actual, iq_actual, torque_Nm)
        """
        # Toc do goc dien (Electrical angular velocity): omega_e = omega_m * p
        omega_mech = speed_rpm * (2.0 * math.pi / 60.0)
        omega_e = omega_mech * self.m.pole_pairs

        # Tinh dao ham dong dien
        # dId/dt = (Vd - Rs * Id + omega_e * Lq * Iq) / Ld
        did_dt = (vd - self.m.Rs * self.id_actual + omega_e * self.m.Lq * self.iq_actual) / self.m.Ld
        # dIq/dt = (Vq - Rs * Iq - omega_e * (Ld * Id + lambda_pm)) / Lq
        diq_dt = (vq - self.m.Rs * self.iq_actual - omega_e * (self.m.Ld * self.id_actual + self.m.lambda_pm)) / self.m.Lq

        self.id_actual += did_dt * dt
        self.iq_actual += diq_dt * dt

        # Mo-men dien tu (Electromagnetic Torque):
        # Te = 1.5 * p * [ lambda_pm * Iq + (Ld - Lq) * Id * Iq ]
        torque = 1.5 * self.m.pole_pairs * (
            self.m.lambda_pm * self.iq_actual + (self.m.Ld - self.m.Lq) * self.id_actual * self.iq_actual
        )

        return (self.id_actual, self.iq_actual, torque)

# ------------------------------------------------------------------------------
# 4. MO PHONG VA KIEM CHUNG SUY GIAM TU THONG VUOT TOC
# ------------------------------------------------------------------------------

def test_field_weakening_operation():
    """
    Kiem tra hoat dong Field Weakening khi dong co quay tu 3000 RPM (Base Speed)
    len 9000 RPM (Vung suy giam tu thong Field Weakening Range).
    Dien ap pin 400V, V_max = 230.94V.
    """
    motor = MotorParameters()
    fw_ctrl = FieldWeakeningController(motor)
    plant = IPMSMPlant(motor)

    dt = 0.0001 # 100 microseconds (10 kHz PWM loop)
    total_time = 0.4 # 400 ms
    steps = int(total_time / dt)

    target_iq_cmd = 120.0 # Yeu cau dong iq = 120A tao mo-men xoan
    vd_applied = 0.0
    vq_applied = 0.0

    # Bo dieu khien PI dong dien don gian
    kp_cur = 2.0
    ki_cur = 200.0
    integ_d = 0.0
    integ_q = 0.0

    print("Bat dau mo phong Field Weakening tu 3000 RPM den 9000 RPM...")

    base_speed_vmag = 0.0
    high_speed_vmag = 0.0
    final_id = 0.0

    for step in range(steps):
        t = step * dt

        # Tang dan toc do tu 3000 len 9000 RPM
        speed_rpm = 3000.0 + (6000.0 * (t / total_time))
        omega_e = (speed_rpm * 2.0 * math.pi / 60.0) * motor.pole_pairs

        # 1. Tinh toan Id yeu cau tu bo Field Weakening
        id_ref, iq_ref = fw_ctrl.compute_id_ref(target_iq_cmd, vd_applied, vq_applied, dt)

        # 2. Bo dieu khien dong dien PI (Current Loop voi Anti-Windup)
        err_d = id_ref - plant.id_actual
        err_q = iq_ref - plant.iq_actual

        # Bu cheo FOC (Decoupling):
        vd_ff = -omega_e * motor.Lq * plant.iq_actual
        vq_ff = omega_e * (motor.Ld * plant.id_actual + motor.lambda_pm)

        vd_raw = kp_cur * err_d + integ_d + vd_ff
        vq_raw = kp_cur * err_q + integ_q + vq_ff

        # Kep dien ap tong trong gioi han bien tan V_max
        v_mag_raw = math.sqrt(vd_raw * vd_raw + vq_raw * vq_raw)
        if v_mag_raw > motor.V_max:
            scale = motor.V_max / v_mag_raw
            vd_applied = vd_raw * scale
            vq_applied = vq_raw * scale
            # Anti-windup: Khi dien ap bao hoa, khong tich luy them sai so
        else:
            vd_applied = vd_raw
            vq_applied = vq_raw
            integ_d += ki_cur * err_d * dt
            integ_q += ki_cur * err_q * dt

        v_mag_applied = math.sqrt(vd_applied * vd_applied + vq_applied * vq_applied)

        # 3. Tich phan dong hoc dong co
        plant.step(vd_applied, vq_applied, speed_rpm, dt)

        if step == int(0.05 / dt):
            base_speed_vmag = v_mag_applied
        if step == steps - 1:
            high_speed_vmag = v_mag_applied
            final_id = plant.id_actual

    print("--------------------------------------------------------------------------------")
    print(f"KET QUA MO PHONG FIELD WEAKENING CHO TESLA POWERTRAIN:")
    print(f"-> Dien ap toi da bien tan cho phep V_max: {motor.V_max:.2f} V")
    print(f"-> Dien ap tai Base Speed (3000 RPM)      : {base_speed_vmag:.2f} V (Duoi nguong)")
    print(f"-> Dien ap tai High Speed (9000 RPM)      : {high_speed_vmag:.2f} V (Ghim dung V_max)")
    print(f"-> Dong dien Id bom vao de khu tu         : {final_id:.2f} A (Id < 0 ro ret)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Khi quay o 9000 RPM, dong dien Id phai bi keo am manh de khu tu (Id < -60A)
    assert final_id < -60.0, f"Loi: Dong Id khong khu tu du manh: {final_id} A"
    # 2. Dien ap bien tan khong duoc phep vuot qua V_max
    assert high_speed_vmag <= motor.V_max + 1.0, f"Loi: Dien ap bi tran qua V_max: {high_speed_vmag} V"
    print("[PASS] Test Field Weakening: Dong co quay 9000 RPM vuot dinh muc an toan tuyet doi!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO FIELD WEAKENING CONTROLLER FOR HIGH-SPEED ELECTRIC VEHICLES")
    print("================================================================================")
    test_field_weakening_operation()
