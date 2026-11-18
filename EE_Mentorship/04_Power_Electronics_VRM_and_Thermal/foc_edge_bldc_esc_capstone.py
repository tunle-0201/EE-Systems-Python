"""
================================================================================
          MODULE S CAPSTONE FINALE: BO DIEU TOC DONG CO FOC BLDC MOTOR ESC
               TICH HOP DIEN TU CONG SUAT (FIELD-ORIENTED CONTROL)
================================================================================

1. KIEN TRUC HE THONG FOC MOTOR CONTROLLER TOAN CHUOI (FULL FOC PIPELINE):
   Day la kien truc dieu khien dong co xoay chieu toc do cao va mo-men tuyet doi
   duoc su dung trong:
   - Bo bien tan luc keo (Traction Inverter) cua xe dien Tesla, Porsche Taycan.
   - Bo dieu toc ESC (Electronic Speed Controller) cua Drone cong nghiep & FPV Racing.
   - Canh tay robot cong nghiep va khop chan robot 4 chan (Boston Dynamics).

   Chu trinh khep kin (Closed-Loop FOC Algorithm):
   - Buoc 1: Doc 3 pha dong dien thuc te (Ia, Ib, Ic) tu dien tro Shunt ADC.
   - Buoc 2: Bien doi Clarke sang he truc tinh 2 chieu (I_alpha, I_beta).
   - Buoc 3: Doc goc Rotor (theta_e) tu cam bien Hall / Encoder quang hoc.
   - Buoc 4: Bien doi Park sang he toa do quay (I_d, I_q).
   - Buoc 5: Bo dieu khien PI kep:
             + I_d bam ve 0 (Tiet kiem tu thong toi da).
             + I_q bam theo lenh Mo-men tay ga (Throttle Torque command).
   - Buoc 6: Bien doi Park nguoc ra dien ap (V_alpha, V_beta).
   - Buoc 7: Bo dieu che SVPWM tinh toan thoi gian kich dong 6 van Mosfet cau H!

2. SO DO LUONG DU LIEU DIEU KHIEN REAL-TIME (ASCII ARCHITECTURE):

  +──────────────────────────────────────────────────────────────────────────+
  |             COMPLETE FOC CLOSED-LOOP MOTOR ESC CONTROLLER                |
  +──────────────────────────────────────────────────────────────────────────+
  |                                                                          |
  |  [ Motor Stator Shunts ] (Ia, Ib, Ic)                                    |
  |             │                                                            |
  |             ▼                                                            |
  |  [ Forward Clarke Transform ] ──► (I_alpha, I_beta)                      |
  |                                           │                              |
  |                                           ▼                              |
  |  [ Rotor Encoder theta_e ] ────► [ Forward Park Transform ]              |
  |                                           │                              |
  |                                           ▼                              |
  |                       (I_d, I_q) DC Equivalent Feedback                  |
  |                                           │                              |
  |                                           ▼                              |
  |                      [ Dual PI Current Controllers ]                     |
  |                       (I_d_ref -> V_d, I_q_ref -> V_q)                   |
  |                                           │                              |
  |                                           ▼                              |
  |                       [ Inverse Park Transform ]                         |
  |                                           │                              |
  |                                           ▼                              |
  |                       (V_alpha, V_beta) Stationary Frame                 |
  |                                           │                              |
  |                                           ▼                              |
  |                       [ Space Vector PWM Modulator ]                     |
  |                                           │                              |
  |                                           ▼                              |
  |                       [ 6-MOSFET Inverter Gate Signals ]                 |
  +──────────────────────────────────────────────────────────────────────────+
"""

from typing import Tuple, Dict, Any
import numpy as np

from foc_edge_clarke_transform import ClarkeTransform, compute_clarke_transform
from foc_edge_park_transform import ParkTransform, compute_park_transform
from foc_edge_svpwm_generator import SpaceVectorPWM, determine_svpwm_sector


class FieldOrientedMotorController:
    """
    Bo dieu toc FOC hoan chinh tich hop day du Clarke, Park va SVPWM.
    """
    def __init__(self, v_bus: float = 24.0, pwm_period_us: float = 50.0):
        self.clarke = ClarkeTransform()
        self.park = ParkTransform()
        self.svpwm = SpaceVectorPWM(v_bus=v_bus, pwm_period_us=pwm_period_us)

    def process_foc_cycle(
        self,
        ia: float,
        ib: float,
        ic: float,
        rotor_angle_rad: float,
        v_ref_volts: float = 12.0
    ) -> Dict[str, Any]:
        """
        Thuc thi 1 chu ky FOC thoi gian thuc tren DSP/Microcontroller:
        """
        # 1. Clarke Transform (3 pha sang Alpha-Beta)
        i_alpha, i_beta = self.clarke.forward(ia, ib, ic)

        # 2. Park Transform (Alpha-Beta sang d-q)
        i_d, i_q = self.park.forward(i_alpha, i_beta, rotor_angle_rad)

        # 3. SVPWM Modulation
        sector = self.svpwm.get_sector(rotor_angle_rad)
        duty_info = self.svpwm.compute_duty_cycles(v_ref=v_ref_volts, theta_rad=rotor_angle_rad)

        return {
            "i_alpha": i_alpha,
            "i_beta": i_beta,
            "i_d": i_d,
            "i_q": i_q,
            "sector": sector,
            "duty_timing": duty_info
        }


def run_foc_motor_controller_loop(
    ia: float,
    ib: float,
    ic: float,
    rotor_angle_rad: float
) -> Tuple[float, float, int]:
    """
    Ham backward-compatible giu nguyen chu ky kiem thu Milestone S Capstone.
    """
    # 1. Clarke Transform (3 pha -> Alpha-Beta)
    i_alpha, i_beta = compute_clarke_transform(ia, ib, ic)

    # 2. Park Transform (Alpha-Beta -> d-q)
    i_d, i_q = compute_park_transform(i_alpha, i_beta, rotor_angle_rad)

    # 3. Tinh Sector dieu che SVPWM
    sec = determine_svpwm_sector(rotor_angle_rad)

    return i_d, i_q, sec


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE S CAPSTONE: REAL-TIME FOC MOTOR ESC ENGINE")
    print("=========================================================\n")

    # 3 pha dong dien dat tai thoi diem mau: Ia = 10A, Ib = -5A, Ic = -5A
    # Goc dien rotor o 45 do (pi/4 rad)
    Ia, Ib, Ic = 10.0, -5.0, -5.0
    theta = np.deg2rad(45.0)

    id_out, iq_out, sector = run_foc_motor_controller_loop(Ia, Ib, Ic, theta)

    print("1. KET QUA HOAT DONG TOAN CHUOI FOC MOTOR ESC:")
    print(f"   -> Dong Tu hoa I_d (Flux)     : {id_out:.3f} A")
    print(f"   -> Dong Mo-men I_q (Torque)   : {iq_out:.3f} A")
    print(f"   -> Sector Dieu che PWM        : Sector {sector} (Goc 45 deg thuoc Sector 1)")

    assert abs(id_out - 7.071) < 1e-2 and abs(iq_out - (-7.071)) < 1e-2 and sector == 1, "Loi Capstone FOC!"

    # 2. Thu nghiem kiem tra bang Controller huong doi tuong
    esc = FieldOrientedMotorController(v_bus=24.0, pwm_period_us=50.0)
    cycle_telemetry = esc.process_foc_cycle(Ia, Ib, Ic, theta, v_ref_volts=10.0)

    print("\n2. TELEMETRY DIEU KHIEN ESC CUA DRONE:")
    print(f"   -> Dong I_alpha / I_beta      : ({cycle_telemetry['i_alpha']:.2f}A, {cycle_telemetry['i_beta']:.2f}A)")
    print(f"   -> Thoi gian mo van T1 / T2   : ({cycle_telemetry['duty_timing']['T1_us']:.2f}us, {cycle_telemetry['duty_timing']['T2_us']:.2f}us)")
    print(f"   -> Tong Duty Cycle PWM Mosfet : {cycle_telemetry['duty_timing']['duty_percent']:.1f}%")

    assert cycle_telemetry["sector"] == 1

    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE S: FOC MOTOR CONTROL!")
    print("=========================================================")
