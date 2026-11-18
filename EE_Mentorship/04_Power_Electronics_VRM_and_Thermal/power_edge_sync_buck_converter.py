"""
================================================================================
          MODULE U: EMBEDDED DIGITAL POWER ELECTRONICS & SPACE POWER SYSTEMS
    MILESTONE U.1: MACH CHUYEN DOI HA AP DONG BO (SYNCHRONOUS BUCK CONVERTER)
================================================================================

1. NGUYEN LY DIEN TU CONG SUAT & NGUON NHUNG (POWER ELECTRONICS FOUNDATION):
   - Tai sao kien truc 48V tren xe dien Tesla (Cybertruck) va ve tinh bat buoc
     phai dung Bo ha ap dong bo (Synchronous Buck)?
     + Dien ap bus chinh cao (V_in = 48V hoac 28V) de giam dong dien truyen dan,
       tu do giam thiet hai toa nhiet tren day dan theo dinh luat Joule (P_loss = I^2 * R).
     + Tuy nhien, vi dieu khien nhung ARM Cortex-M, cam bien va chip Edge AI
       chi hoat dong o dien ap V_out = 3.3V hoac 1.2V (Dong len toi 5A - 10A).
     + Neu dung IC on ap tuyen tinh LDO (nhu LM7805):
       Hieu suat chi dat: eta = 3.3V / 48V = 6.8%! Toan bo 93.2% nang luong bien
       thanh nhiet thieu chay bo mach ngay tuc thi!
     + Bo ha ap xung dong bo Synchronous Buck: dung 2 van Power MOSFET dong cat o tan
       so cao (250 kHz), thay the diode flyback bang MOSFET Q2 duoi de giam sup ap,
       dat hieu suat vuot troi tren 92%!

2. SO DO PHAN CUNG & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do mach ha ap dong bo Synchronous Buck (2 MOSFETs + LC Filter):

   V_in (48V) ──► [ Top MOSFET Q1 ] ──┬── [ Cuon cam L ] ──┬────► V_out (3.3V)
                        ▲             │                    │
                   PWM1 │             ▼                    ▼
                        │     [ Bottom MOSFET Q2 ]    [ Tu C ]   [ Tai R ]
                   PWM2 │             │                    │        │
                        │             ▼                    ▼        ▼
                  [ Dead-time ]      GND                  GND      GND

   He so chu ky xung dong cat (Duty Cycle D):

                  V_out
   Duty Cycle D = ─────
                  V_in

   Do gon dong dien qua cuon cam L (Inductor Current Ripple):

                  (V_in - V_out) * D
   Delta_I_L    = ──────────────────
                       L * f_sw

   Do gon dien ap ngo ra tren tu C (Output Voltage Ripple):

                    Delta_I_L
   Delta_V_out  = ────────────────
                  8 * C_out * f_sw

   Che do dan lien tuc (Continuous Conduction Mode - CCM):
   Dieu kien de dong khong bi ve 0: I_load > (Delta_I_L / 2)
"""

from typing import Dict, List, Any
import numpy as np


class SynchronousBuckConverter:
    """
    Mo hinh mach chuyen doi ha ap dong bo Synchronous Buck DC-DC Converter.
    """
    def __init__(
        self,
        v_in: float = 48.0,
        v_out: float = 3.3,
        f_sw: float = 250e3,
        inductance: float = 22e-6,
        capacitance: float = 47e-6
    ):
        """
        - v_in: Dien ap bus nguon vao (48V)
        - v_out: Dien ap dich cap cho vi dieu khien (3.3V)
        - f_sw: Tan so dong cat xung PWM (250 kHz)
        - inductance: Cuon cam loc cong suat L (22 uH)
        - capacitance: Tu dien loc phang ngo ra C (47 uF)
        """
        self.v_in = float(v_in)
        self.v_out = float(v_out)
        self.f_sw = float(f_sw)
        self.L = float(inductance)
        self.C = float(capacitance)
        self.t_period = 1.0 / self.f_sw

    def calculate_steady_state_metrics(self, load_current: float = 2.0) -> Dict[str, Any]:
        """
        Tinh toan cac thong so dien tu cong suat o trang thai xac lap:
        - Duty cycle D
        - Do gon dong cuon cam Delta_I_L
        - Do gon ap ngo ra Delta_V_out
        - Trang thai dan lien tuc (CCM) hay gian doan (DCM)
        """
        # 1. Tinh Duty Cycle ly thuyet
        duty_cycle = self.v_out / self.v_in

        # 2. Tinh do gon dong cuon cam
        t_on = duty_cycle * self.t_period
        delta_i_l = ((self.v_in - self.v_out) * t_on) / self.L

        # 3. Tinh do gon ap ngo ra tren tu dien
        delta_v_out = delta_i_l / (8.0 * self.C * self.f_sw)

        # 4. Kiem tra che do dan: CCM neu I_load > Delta_I_L / 2
        is_ccm = bool(load_current > (delta_i_l / 2.0))

        return {
            "duty_cycle": float(duty_cycle),
            "delta_i_l_amps": float(delta_i_l),
            "delta_v_out_mv": float(delta_v_out * 1000.0),
            "is_ccm": is_ccm
        }

    def simulate_step_response(
        self,
        initial_voltage: float = 0.0,
        target_duty: float = 0.06875,
        sim_steps: int = 100
    ) -> List[float]:
        """
        Mo phong dong hoc nap xa vi phan (L-C Filter) theo tung chu ky dong cat
        """
        dt = self.t_period
        v_c = float(initial_voltage)
        i_l = 0.0
        v_history = []

        for _ in range(sim_steps):
            # Dien ap trung binh sau chuyen mach MOSFET
            v_sw_avg = target_duty * self.v_in

            # Phuong trinh vi phan trang thai cuon cam va tu dien:
            # L * di/dt = v_sw - v_c
            # C * dv/dt = i_l - v_c / R_load (tai R = 3.3V / 2A = 1.65 Ohm)
            r_load = 1.65
            di_l = ((v_sw_avg - v_c) / self.L) * dt
            i_l += di_l

            dv_c = ((i_l - v_c / r_load) / self.C) * dt
            v_c += dv_c

            v_history.append(float(v_c))

        return v_history


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED POWER: SYNCHRONOUS BUCK DC-DC CONVERTER")
    print("=========================================================\n")

    buck = SynchronousBuckConverter(v_in=48.0, v_out=3.3, f_sw=250e3, inductance=22e-6, capacitance=47e-6)
    metrics = buck.calculate_steady_state_metrics(load_current=2.0)

    print("1. THONG SO THIET KE DIEN TU CONG SUAT (STEADY-STATE):")
    print(f"   -> Dien ap nguon vao (V_in)       : {buck.v_in:.1f} V")
    print(f"   -> Dien ap ha muc tieu (V_out)    : {buck.v_out:.2f} V")
    print(f"   -> Tan so dong cat (f_sw)         : {buck.f_sw / 1e3:.1f} kHz")
    print(f"   -> He so chu ky xung (Duty Cycle) : {metrics['duty_cycle'] * 100:.2f}%")
    print(f"   -> Do gon dong cuon cam (dI_L)    : {metrics['delta_i_l_amps']:.3f} A")
    print(f"   -> Do gon dien ap ngo ra (dV_out) : {metrics['delta_v_out_mv']:.2f} mV (Tieu chuan nhung < 50mV)")
    print(f"   -> Che do dan lien tuc (CCM)      : {'DAT CHUAN CCM' if metrics['is_ccm'] else 'CANH BAO DCM'}\n")

    assert abs(metrics['duty_cycle'] - (3.3 / 48.0)) < 1e-4, "Loi tinh Duty Cycle!"
    assert metrics['delta_v_out_mv'] < 50.0, "Do gon ap qua lon, gay hong vi dieu khien!"
    assert metrics['is_ccm'] is True, "Mach phai hoat dong trong che do CCM!"

    # Mo phong dong hoc qua do L-C
    v_curve = buck.simulate_step_response(initial_voltage=0.0, target_duty=metrics['duty_cycle'], sim_steps=300)
    v_final = v_curve[-1]
    print("2. DONG HOC KHOI DONG MEM (SOFT-START LC SIMULATION):")
    print(f"   -> Dien ap cuoi cung dat duoc     : {v_final:.2f} V (Muc tieu 3.30 V)")
    assert abs(v_final - 3.3) < 0.05, "Dien ap ngo ra khong on dinh quanh 3.3V!"

    print("\n[THANH CONG] BO CHUYEN DOI HA AP DONG BO SYNCHRONOUS BUCK HOAN TAT CHINH XAC!")
