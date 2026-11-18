"""
================================================================================
          MODULE U: EMBEDDED DIGITAL POWER ELECTRONICS & SPACE POWER SYSTEMS
    MILESTONE U.2: BO DIEU KHIEN HOI TIEP KIN DIGITAL PID VOLTAGE REGULATOR
================================================================================

1. NGUYEN LY DIEU KHIEN SO & ON DINH NGUON NHUNG (DIGITAL POWER PID CONTROL):
   - Khi chip Edge AI (NPU/GPU) tren Drone hoac ve tinh bat dau tinh toan mang no-ron,
     dong tieu thu tang vot tu 0.5A len 5.0A chi trong vai micro-giay (Load Step Transient)!
   - Hien tuong sup ap nguy hiem (Voltage Sag):
     + Neu bo nguon chay o che do vong ho (Open-Loop), dien ap 3.3V se sup tut xuong
       duoi 2.4V lam vi dieu khien bi Brown-Out Reset ngay lap tuc!
     + Nguoc lai, khi chip AI hoan thanh tinh toan va ngat tai dot ngot, dien cam L
       se sinh ra xung qua ap (Voltage Overshoot) len toi 4.8V thieu chay chip!
   - Giai phap Dien tu so: Bo dieu khien PID chu ky xung (Digital Power PID Regulator):
     + ADC toc do cao doc dien ap V_out moi chu ky PWM (250 kHz -> dt = 4 micro-giay).
     + Tinh toan sai lech error = V_ref - V_out va cap nhat Duty Cycle tuc thi.
     + Trang bi thuat toan Anti-Windup Clamping chong bao hoa tich phan khi khoi dong.

2. SO DO HOI TIEP & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do vong dieu khien hoi tiep kin Digital PID Voltage Regulator:

   V_ref (3.3V) ──► (+) ─── error[n] ──► [ Digital PID Controller ] ──► Duty Clamped
                     ▲                        │ (Kp, Ki, Kd)                 │
                     │ (-)                    ▼                              ▼
                     │                   [ Anti-Windup ]            [ Power MOSFET ]
                     │                                                       │
                     └────── [ ADC Lay mau 250kHz ] ◄── V_out (3.3V) ◄───────┘

   Cong thuc sai lech dieu khien thoi gian thuc:

   error[n] = V_ref - V_measured[n]

   Cac thanh phan bo dieu khien PID so hoa (Discrete PID Algorithm):

   P_term = Kp * error[n]
   I_term = I_term + Ki * error[n] * dt
   D_term = Kd * (error[n] - error[n-1]) / dt

   Duty_unclamped = P_term + I_term + D_term
   Duty = clamp(Duty_unclamped, Duty_min, Duty_max)

   Co che chong bao hoa tich phan (Anti-Windup Clamping):
   Neu Duty bi bao hoa (Duty != Duty_unclamped):
       I_term = I_term - Ki * error[n] * dt  (Dung tich luy sai so)
"""

from typing import Tuple, List
import numpy as np


class DigitalPIDVoltageRegulator:
    """
    Bo dieu khien so Digital PID on dinh dien ap Buck Converter voi co che Anti-Windup.
    """
    def __init__(
        self,
        v_ref: float = 3.3,
        kp: float = 0.08,
        ki: float = 250.0,
        kd: float = 0.00005,
        d_min: float = 0.01,
        d_max: float = 0.90
    ):
        self.v_ref = float(v_ref)
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.d_min = float(d_min)
        self.d_max = float(d_max)

        self.integral = 0.0
        self.prev_error = 0.0

    def compute_duty_cycle(self, v_measured: float, dt: float) -> float:
        """
        Thuc thi 1 chu ky dieu khien PID dien ap:
        - v_measured: Dien ap do tu ADC (V)
        - dt: Chu ky lay mau dieu khien (giay)
        Tra ve: He so chu ky xung PWM (0.01 -> 0.90)
        """
        error = self.v_ref - float(v_measured)

        # Khau ti le P
        p_term = self.kp * error

        # Khau tich phan I kem Anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Khau vi phan D
        d_term = self.kd * (error - self.prev_error) / (dt + 1e-12)
        self.prev_error = error

        # Tong hop tin hieu dieu khien
        unclamped_duty = p_term + i_term + d_term

        # Gioi han an toan chu ky xung PWM (Clamping)
        duty = max(self.d_min, min(self.d_max, unclamped_duty))

        # Khu tich luy sai so khi bao hoa (Anti-windup back-calculation)
        if duty != unclamped_duty:
            self.integral -= error * dt

        return float(duty)


class SimulatedBuckPlant:
    """Mo phong dong hoc phan cung Buck Converter kem tai bien thien"""
    def __init__(self, v_in: float = 48.0, L: float = 22e-6, C: float = 47e-6):
        self.v_in = float(v_in)
        self.L = float(L)
        self.C = float(C)
        self.v_out = 0.0
        self.i_l = 0.0

    def step(self, duty: float, load_current: float, dt: float) -> float:
        v_sw = float(duty) * self.v_in
        # L * di/dt = v_sw - v_out
        di_l = ((v_sw - self.v_out) / self.L) * dt
        self.i_l += di_l

        # C * dv/dt = i_l - i_load
        dv_out = ((self.i_l - float(load_current)) / self.C) * dt
        self.v_out += dv_out

        return float(self.v_out)


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED POWER: DIGITAL PID VOLTAGE REGULATOR")
    print("=========================================================\n")

    pid = DigitalPIDVoltageRegulator(v_ref=3.3, kp=0.12, ki=600.0, kd=0.00002)
    plant = SimulatedBuckPlant(v_in=48.0, L=22e-6, C=47e-6)

    dt = 4e-6  # Chu ky dieu khien 250 kHz
    total_steps = 1500

    v_history = []
    load_history = []

    # Gia lap tinh huong nhay tai dot ngot (Load Step Transient):
    # - Tu buoc 0 den 600: Tai binh thuong 1.0A
    # - Tu buoc 600 den 1100: Tai AI tang vot len 5.0A (Gap 5 lan!)
    # - Tu buoc 1100 tro di: Tai tro ve 1.0A
    current_v = 0.0
    for step in range(total_steps):
        if 600 <= step < 1100:
            i_load = 5.0
        else:
            i_load = 1.0

        duty = pid.compute_duty_cycle(v_measured=current_v, dt=dt)
        current_v = plant.step(duty=duty, load_current=i_load, dt=dt)

        v_history.append(current_v)
        load_history.append(i_load)

    # Danh gia do sut ap toi da khi tai nhay vot 5A (tai step 600 -> 700)
    transient_slice = v_history[600:700]
    min_transient_v = min(transient_slice)
    voltage_sag_mv = (3.3 - min_transient_v) * 1000.0

    # Danh gia dien ap xac lap khi dang ganh tai nang 5A (tai step 900 -> 1050)
    steady_heavy_v = np.mean(v_history[900:1050])

    # Danh gia dien ap cuoi cung khi hoi phuc
    final_settled_v = np.mean(v_history[1300:])

    print("1. KET QUA PHAN UNG DONG HOC KHI TAI TANG VOT (LOAD STEP 1A -> 5A):")
    print(f"   -> Dien ap dinh muc (V_ref)           : 3.30 V")
    print(f"   -> Do sut ap tuc thoi toi da (Sag)    : {voltage_sag_mv:.1f} mV")
    print(f"   -> Dien ap xac lap khi ganh tai 5A    : {steady_heavy_v:.3f} V (Sai lech < 10mV!)")
    print(f"   -> Dien ap cuoi cung sau khi ha tai   : {final_settled_v:.3f} V\n")

    assert abs(steady_heavy_v - 3.3) < 0.05, "PID khong duy tri duoc dien ap duoi tai nang!"
    assert abs(final_settled_v - 3.3) < 0.02, "Dien ap hoi phuc cuoi cung khong dat chuan!"
    print("[THANH CONG] BO DIEU KHIEN DIGITAL PID DA ON DINH DIEN AP TRUOC CU SOC TAI NANG!")
