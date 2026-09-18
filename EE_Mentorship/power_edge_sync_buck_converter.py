"""
================================================================================
          MODULE AL: EMBEDDED POWER ELECTRONICS & DIGITAL POWER SYSTEMS
              MILESTONE AL.1: MẠCH CHUYỂN ĐỔI HẠ ÁP ĐỒNG BỘ (SYNCHRONOUS BUCK CONVERTER)
================================================================================

TẠI SAO PHẢI DÙNG BỘ HẠ ÁP ĐỒNG BỘ (SYNCHRONOUS BUCK) TRÊN MÁY TÍNH BAY & XE ĐIỆN?
Trong xe điện Tesla (kiến trúc 48V) hoặc Drone/Vệ tinh:
- Đường truyền chính có điện áp cao V_in = 48V (hoặc 24V) để giảm hao phí dòng điện I^2*R.
- Vi điều khiển nhúng, cảm biến và chip AI chỉ hoạt động ở V_out = 3.3V (hoặc 5.0V).
- Dùng IC ổn áp tuyến tính (LDO như LM7805) sẽ làm nóng bỏng bo mạch (Hiệu suất chỉ 10%!).
- Bộ hạ áp xung đồng bộ (Synchronous Buck) dùng 2 MOSFET đóng cắt tần số cao (250 kHz)
  đạt hiệu suất vượt trội trên 92%!

CÔNG THỨC ĐIỆN TỬ CÔNG SUẤT (DẠNG ASCII TEXT):
1. Hệ số chu kỳ xung điều khiển (Duty Cycle D):
                       V_out
        Duty Cycle D = ─────
                       V_in

2. Độ gợn dòng điện qua cuộn cảm L (Inductor Current Ripple):
                       (V_in - V_out) * D
        Delta_I_L    = ──────────────────
                            L * f_sw

3. Độ gợn điện áp ngõ ra tụ điện C (Output Voltage Ripple):
                          Delta_I_L
        Delta_V_out  = ────────────────
                       8 * C_out * f_sw
"""

import numpy as np

class SynchronousBuckConverter:
    def __init__(self, v_in: float = 48.0, v_out: float = 3.3, f_sw: float = 250e3, inductance: float = 22e-6, capacitance: float = 47e-6):
        """
        - v_in: Điện áp bus nguồn vào (48V)
        - v_out: Điện áp đích cấp cho vi điều khiển (3.3V)
        - f_sw: Tần số đóng cắt xung PWM (250 kHz)
        - inductance: Cuộn cảm lọc công suất L (22 uH)
        - capacitance: Tụ điện lọc phẳng ngõ ra C (47 uF)
        """
        self.v_in = v_in
        self.v_out = v_out
        self.f_sw = f_sw
        self.L = inductance
        self.C = capacitance
        self.t_period = 1.0 / f_sw

    def calculate_steady_state_metrics(self, load_current: float = 2.0) -> dict:
        """
        Tính toán các thông số điện tử công suất ở trạng thái xác lập:
        - Duty cycle D
        - Độ gợn dòng cuộn cảm Delta_I_L
        - Độ gợn áp ngõ ra Delta_V_out
        - Trạng thái dẫn liên tục (CCM) hay gián đoạn (DCM)
        """
        # 1. Tính Duty Cycle lý thuyết
        duty_cycle = self.v_out / self.v_in

        # 2. Tính độ gợn dòng cuộn cảm
        t_on = duty_cycle * self.t_period
        delta_i_l = ((self.v_in - self.v_out) * t_on) / self.L

        # 3. Tính độ gợn áp ngõ ra trên tụ điện
        delta_v_out = delta_i_l / (8.0 * self.C * self.f_sw)

        # 4. Kiểm tra chế độ dẫn: CCM nếu I_load > Delta_I_L / 2
        is_ccm = bool(load_current > (delta_i_l / 2.0))

        return {
            "duty_cycle": float(duty_cycle),
            "delta_i_l_amps": float(delta_i_l),
            "delta_v_out_mv": float(delta_v_out * 1000.0),
            "is_ccm": is_ccm
        }

    def simulate_step_response(self, initial_voltage: float = 0.0, target_duty: float = 0.06875, sim_steps: int = 100) -> list:
        """
        Mô phỏng động học nạp xả vi phân (L-C Filter) theo từng chu kỳ đóng cắt
        """
        dt = self.t_period
        v_c = initial_voltage
        i_l = 0.0
        v_history = []

        for _ in range(sim_steps):
            # Điện áp trung bình sau chuyển mạch MOSFET
            v_sw_avg = target_duty * self.v_in

            # Phương trình vi phân trạng thái cuộn cảm và tụ điện
            # L * di/dt = v_sw - v_c
            # C * dv/dt = i_l - v_c / R_load (giả sử tải R = 3.3V / 2A = 1.65 Ohm)
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

    # Mô phỏng động học quá độ L-C
    v_curve = buck.simulate_step_response(initial_voltage=0.0, target_duty=metrics['duty_cycle'], sim_steps=300)
    v_final = v_curve[-1]
    print("2. DONG HOC KHOI DONG MEM (SOFT-START LC SIMULATION):")
    print(f"   -> Dien ap cuoi cung dat duoc     : {v_final:.2f} V (Muc tieu 3.30 V)")
    assert abs(v_final - 3.3) < 0.05, "Dien ap ngo ra khong on dinh quanh 3.3V!"

    print("\n[THANH CONG] BO CHUYEN DOI HA AP DONG BO SYNCHRONOUS BUCK HOAN TAT CHINH XAC!")
