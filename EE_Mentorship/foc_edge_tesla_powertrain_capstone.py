"""
================================================================================
CHUYEN DE AG: HARDWARE MOTOR FIELD WEAKENING & OVERMODULATION (FW & OVM)
BAI 4: DONG CO DIEU KHIEN BIEN TAN HE TRUYEN DONG TESLA PLAID CAPSTONE
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tich hop toan chuoi FOC + MTPA + Field Weakening + Overmodulation Capstone
Ngon ngu: Python 3 thuan tuy, kien truc Module huong doi tuong thoi gian thuc
================================================================================
"""

import math
from typing import Tuple, List, Dict

from foc_edge_field_weakening_controller import (
    MotorParameters, FieldWeakeningController, IPMSMPlant
)
from foc_edge_mtpa_mtpv_trajectory import (
    MTPATrajectoryCalculator, MTPALookupTable
)
from foc_edge_svpwm_overmodulation import (
    HexagonGeometry, SpaceVectorOvermodulator
)

# ------------------------------------------------------------------------------
# 1. DONG CO DIEU KHIEN BIEN TAN TOAN CHUOI (TESLA POWERTRAIN CAPSTONE ENGINE)
# ------------------------------------------------------------------------------

class TeslaPowertrainEngine:
    """
    Dong co dieu khien bien tan FOC toan chuoi cho xe dien Tesla Model S Plaid:
    - MTPA Controller: Toi uu hoa dong dien sinh mo-men tu tro
    - Adaptive Field Weakening: Tu dong khu tu khi Back-EMF vuot nguong
    - Space Vector Overmodulation: OVM1 va OVM2 Six-Step khai thac 15.5% dien ap pin
    - Closed-loop FOC Current Regulators voi Anti-Windup
    """
    def __init__(self, motor: MotorParameters):
        self.motor = motor
        self.plant = IPMSMPlant(motor)
        self.geom = HexagonGeometry(Vdc=motor.Vdc)
        self.ovm = SpaceVectorOvermodulator(self.geom)
        self.mtpa_calc = MTPATrajectoryCalculator(motor)
        self.mtpa_lut = MTPALookupTable(self.mtpa_calc, num_points=100)
        self.fw_ctrl = FieldWeakeningController(motor, kp_fw=1.2, ki_fw=35.0)

        # Bo dieu khien PI dong dien (FOC Current Regulators)
        self.kp_cur = 2.5
        self.ki_cur = 250.0
        self.integ_d = 0.0
        self.integ_q = 0.0

        # Bien luu tru trang thai tuc thoi
        self.vd_applied = 0.0
        self.vq_applied = 0.0
        self.last_mode = "LINEAR"

    def step(self, torque_cmd: float, speed_rpm: float, dt: float) -> Dict[str, any]:
        """
        Thuc thi 1 chu ky FOC 10 kHz (dt = 0.0001s):
        1. Tra cuu MTPA de lay diem lam viec toi uu (Id_mtpa, Iq_mtpa)
        2. Tinh toan dong Field Weakening Id_fw dua tren dien ap tuc thoi
        3. Ket hop: Id_ref = Id_mtpa + Id_fw (luon <= 0)
        4. Vong lap PI dong dien + Bu cheo Decoupling
        5. Xu ly qua dieu che SVPWM Overmodulation
        6. Cap dien ap vao dong co va cap nhat trang thai
        """
        # --- BUOC 1: TRA CUU MTPA ---
        id_mtpa, iq_mtpa = self.mtpa_lut.lookup(torque_cmd)

        # --- BUOC 2: TINH TOAN DONG FIELD WEAKENING ---
        id_fw, iq_fw_lim = self.fw_ctrl.compute_id_ref(
            iq_ref=iq_mtpa,
            vd=self.vd_applied,
            vq=self.vq_applied,
            dt=dt
        )

        # Tong hop dong tren truc d: cong them luong khu tu tu FW
        id_ref = min(0.0, id_mtpa + id_fw)
        # Kep trong vong tron dong dien cuc dai I_max
        id_ref = max(-self.motor.I_max, id_ref)
        iq_max_remaining = math.sqrt(max(0.0, self.motor.I_max ** 2 - id_ref ** 2))
        iq_ref = min(iq_max_remaining, max(0.0, min(iq_mtpa, iq_fw_lim)))

        # --- BUOC 3: VONG LAP PI DONG DIEN FOC VOI ANTI-WINDUP ---
        omega_mech = speed_rpm * (2.0 * math.pi / 60.0)
        omega_e = omega_mech * self.motor.pole_pairs

        err_d = id_ref - self.plant.id_actual
        err_q = iq_ref - self.plant.iq_actual

        # Bu cheo (Cross-coupling Decoupling)
        vd_ff = -omega_e * self.motor.Lq * self.plant.iq_actual
        vq_ff = omega_e * (self.motor.Ld * self.plant.id_actual + self.motor.lambda_pm)

        vd_raw = self.kp_cur * err_d + self.integ_d + vd_ff
        vq_raw = self.kp_cur * err_q + self.integ_q + vq_ff

        # --- BUOC 4: SPACE VECTOR OVERMODULATION (OVM) ---
        # Chuyen tu he truc d-q sang alpha-beta (gia su rotor o vi tri goc theta_e)
        # Trong FOC thoi gian thuc, OVM ap dung truc tiep tren bien do dien ap:
        v_mag_raw = math.sqrt(vd_raw * vd_raw + vq_raw * vq_raw)
        phi_dq = math.atan2(vq_raw, vd_raw)

        # Dua qua bo Overmodulator
        va_mod, vb_mod, mode_str = self.ovm.process_voltage_vector(vd_raw, vq_raw)
        self.last_mode = mode_str

        self.vd_applied = va_mod
        self.vq_applied = vb_mod

        # Anti-windup cho bo tich luy PI:
        # Neu bien do raw bi bien doi boi OVM / kep bao hoa, dung tich luy
        v_mag_applied = math.sqrt(self.vd_applied ** 2 + self.vq_applied ** 2)
        if v_mag_raw <= self.geom.V_lin_max:
            self.integ_d += self.ki_cur * err_d * dt
            self.integ_q += self.ki_cur * err_q * dt

        # --- BUOC 5: TICH PHAN DONG HOC DONG CO ---
        id_act, iq_act, torque = self.plant.step(self.vd_applied, self.vq_applied, speed_rpm, dt)

        # Cong suat co hoc P_mech = Torque * omega_mech (Watt)
        p_mech_kw = (torque * omega_mech) / 1000.0

        return {
            "speed_rpm": speed_rpm,
            "id_actual": id_act,
            "iq_actual": iq_act,
            "v_mag": v_mag_applied,
            "torque_nm": torque,
            "power_kw": p_mech_kw,
            "mode": mode_str
        }

# ------------------------------------------------------------------------------
# 2. KICH BAN MO PHONG CAPSTONE: TESLA LAUNCH MODE ACCELERATION
# ------------------------------------------------------------------------------

def run_tesla_launch_mode_simulation():
    """
    Kich ban but toc bão tap Launch Mode / Ludicrous Acceleration cua xe dien Tesla:
    - Thoi gian: 1.2 giay
    - Dong co tang toc tu 0 len 15,000 RPM (tuong duong xe but toc tu 0 den 220 km/h)
    - Yeu cau mo-men xoan ban dau: 130 Nm (kich hoat MTPA Zone)
    - Chuyen tiep qua 3 vung lam viec:
      1. MTPA Zone (0 - 4500 RPM)
      2. Field Weakening Zone (4500 - 10500 RPM)
      3. Overmodulation Six-Step Zone (10500 - 15000 RPM)
    """
    motor = MotorParameters(
        Rs=0.05,
        Ld=0.00025,
        Lq=0.00060,
        lambda_pm=0.08,
        pole_pairs=4,
        Vdc=400.0,
        I_max=250.0
    )
    engine = TeslaPowertrainEngine(motor)

    dt = 0.0001 # 100 microseconds (10 kHz PWM)
    total_time = 1.2 # 1.2 giay
    steps = int(total_time / dt)

    torque_request = 130.0 # Yeu cau mo-men 130 Nm
    telemetry_log: List[Dict[str, any]] = []

    print("================================================================================")
    print("BAT DAU MO PHONG HE TRUYEN DONG TESLA MODEL S PLAID LAUNCH MODE (CAPSTONE)")
    print("================================================================================")
    print("Thoi gian: 1.2s | FOC: 10 kHz | Pin Vdc: 400V | V_lin_max: 230.9V | I_max: 250A")
    print("Tang toc: tu 0 den 15,000 RPM (But toc sieu xe dien)")
    print("--------------------------------------------------------------------------------")

    for step in range(steps):
        t = step * dt
        # Toc do dong co tang theo ham mu de mo phong but toc thuc te
        speed_rpm = 15000.0 * (t / total_time)

        state = engine.step(torque_request, speed_rpm, dt)

        # Ghi log Telemetry moi 150 ms
        if step % int(0.15 / dt) == 0 or step == steps - 1:
            telemetry_log.append({
                "time": t,
                "speed_rpm": state["speed_rpm"],
                "id": state["id_actual"],
                "iq": state["iq_actual"],
                "v_mag": state["v_mag"],
                "torque": state["torque_nm"],
                "power_kw": state["power_kw"],
                "mode": state["mode"]
            })

    # In bang thong ke Telemetry
    print(f"{'Time(s)':<8} | {'Speed(RPM)':<11} | {'Id(A)':<8} | {'Iq(A)':<8} | {'V_mag(V)':<10} | {'Torque(Nm)':<11} | {'Power(kW)':<10} | {'Mode':<10}")
    print("-" * 92)
    for e in telemetry_log:
        print(f"{e['time']:<8.2f} | {e['speed_rpm']:<11.0f} | {e['id']:<8.1f} | {e['iq']:<8.1f} | {e['v_mag']:<10.1f} | {e['torque']:<11.1f} | {e['power_kw']:<10.1f} | {e['mode']:<10}")

    print("--------------------------------------------------------------------------------")
    peak_power = max(e["power_kw"] for e in telemetry_log)
    modes_encountered = set(e["mode"] for e in telemetry_log)
    high_speed_id = telemetry_log[-1]["id"]
    high_speed_vmag = telemetry_log[-1]["v_mag"]

    print(f"-> Cong suat co hoc cuc dai dat duoc: {peak_power:.1f} kW (~{peak_power * 1.341:.0f} HP ma luc)")
    print(f"-> Cac che do bien tan da kich hoat : {modes_encountered}")
    print(f"-> Dong dien Id khu tu tai 15000 RPM : {high_speed_id:.1f} A (Khu tu cuc manh)")
    print(f"-> Dien ap bien tan tai 15000 RPM    : {high_speed_vmag:.1f} V (Khai thac dien ap Overmodulation)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi Capstone:
    # 1. Cong suat dinh phai dat tren 40 kW
    assert peak_power > 40.0, f"Loi: Cong suat dinh khong dat yeu cau: {peak_power} kW"
    # 2. Dong dien Id tai 15000 RPM phai bi keo am rat sau (Id < -100A)
    assert high_speed_id < -100.0, f"Loi: Dong Id khong khu tu du manh tai 15000 RPM: {high_speed_id} A"
    # 3. Phai chuyen tiep qua cac che do (it nhat co LINEAR va che do Overmodulation hoac SIX_STEP)
    assert "LINEAR" in modes_encountered, "Loi: Khong kich hoat duoc vung LINEAR ban dau!"
    assert any(m in modes_encountered for m in ["OVM1", "OVM2", "SIX_STEP"]), "Loi: Khong kich hoat duoc Overmodulation!"
    print("[PASS] Capstone Tesla Powertrain Engine: Thuc thi xuat sac kich ban but toc Launch Mode!")

if __name__ == "__main__":
    run_tesla_launch_mode_simulation()
