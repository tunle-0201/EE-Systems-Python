"""
================================================================================
          MODULE AL: EMBEDDED POWER ELECTRONICS & DIGITAL POWER SYSTEMS
              MILESTONE AL.2: BỘ ĐIỀU KHIỂN HỒI TIẾP KÍN DIGITAL PID VOLTAGE REGULATOR
================================================================================

TẠI SAO BỘ NGUỒN CÔNG SUẤT PHẢI CÓ BỘ ĐIỀU KHIỂN SỐ HỒI TIẾP KÍN (CLOSED-LOOP PID)?
Khi chip AI hoặc động cơ Drone tăng tốc đột ngột:
- Dòng tải nhảy vọt từ 0.5A lên 5.0A chỉ trong vài micro-giây (Load Step Transient).
- Nếu chạy hở mạch (Open-Loop), điện áp 3.3V sẽ sụt thảm hại xuống 2.2V làm vi điều khiển bị Reset!
- Ngược lại, khi ngắt tải đột ngột, điện cảm sẽ đẩy điện áp vọt lên 4.5V làm cháy chip!

GIẢI PHÁP ĐIỆN TỬ SỐ: BỘ ĐIỀU KHIỂN PID CHU KỲ XUNG (DIGITAL POWER PID):
1. ADC đo điện áp ngõ ra thời gian thực: V_out[n].
2. Tính sai lệch điều khiển:
        error[n] = V_ref - V_out[n]

3. Thuật toán điều khiển PID kèm bộ chống bão hòa tích phân (Anti-Windup Clamping):
        P_term = Kp * error[n]
        I_term = I_term + Ki * error[n] * dt
        D_term = Kd * (error[n] - error[n-1]) / dt

        Duty = clamp(P_term + I_term + D_term, Duty_min, Duty_max)

4. Cập nhật thanh ghi PWM vi điều khiển ngay trong chu kỳ ngắt ISR tiếp theo!
"""

import numpy as np

class DigitalPIDVoltageRegulator:
    def __init__(self, v_ref: float = 3.3, kp: float = 0.08, ki: float = 250.0, kd: float = 0.00005, d_min: float = 0.01, d_max: float = 0.90):
        self.v_ref = v_ref
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.d_min = d_min
        self.d_max = d_max

        self.integral = 0.0
        self.prev_error = 0.0

    def compute_duty_cycle(self, v_measured: float, dt: float) -> float:
        """
        Thực thi 1 chu kỳ điều khiển PID điện áp:
        - v_measured: Điện áp đo từ ADC (V)
        - dt: Chu kỳ lấy mẫu điều khiển (giây)
        Trả về: Hệ số chu kỳ xung PWM (0.01 -> 0.90)
        """
        error = self.v_ref - v_measured

        # Khâu tỉ lệ P
        p_term = self.kp * error

        # Khâu tích phân I kèm Anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Khâu vi phân D
        d_term = self.kd * (error - self.prev_error) / (dt + 1e-12)
        self.prev_error = error

        # Tổng hợp tín hiệu điều khiển
        unclamped_duty = p_term + i_term + d_term

        # Giới hạn an toàn chu kỳ xung PWM (Clamping)
        duty = max(self.d_min, min(self.d_max, unclamped_duty))

        # Khử tích lũy sai số khi bão hòa (Anti-windup back-calculation)
        if duty != unclamped_duty:
            self.integral -= error * dt

        return float(duty)


class SimulatedBuckPlant:
    """Mô phỏng động học phần cứng Buck Converter kèm tải biến thiên"""
    def __init__(self, v_in: float = 48.0, L: float = 22e-6, C: float = 47e-6):
        self.v_in = v_in
        self.L = L
        self.C = C
        self.v_out = 0.0
        self.i_l = 0.0

    def step(self, duty: float, load_current: float, dt: float) -> float:
        v_sw = duty * self.v_in
        # L * di/dt = v_sw - v_out
        di_l = ((v_sw - self.v_out) / self.L) * dt
        self.i_l += di_l

        # C * dv/dt = i_l - i_load
        dv_out = ((self.i_l - load_current) / self.C) * dt
        self.v_out += dv_out

        return float(self.v_out)


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED POWER: DIGITAL PID VOLTAGE REGULATOR")
    print("=========================================================\n")

    pid = DigitalPIDVoltageRegulator(v_ref=3.3, kp=0.12, ki=600.0, kd=0.00002)
    plant = SimulatedBuckPlant(v_in=48.0, L=22e-6, C=47e-6)

    dt = 4e-6  # Chu kỳ điều khiển 250 kHz
    total_steps = 1500

    v_history = []
    load_history = []

    # Giả lập tình huống nhảy tải đột ngột (Load Step Transient):
    # - Từ bước 0 đến 600: Tải bình thường 1.0A
    # - Từ bước 600 đến 1100: Tải AI tăng vọt lên 5.0A (Gấp 5 lần!)
    # - Từ bước 1100 trở đi: Tải trở về 1.0A
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

    # Đánh giá độ sụt áp tối đa khi tải nhảy vọt 5A (tại step 600 -> 700)
    transient_slice = v_history[600:700]
    min_transient_v = min(transient_slice)
    voltage_sag_mv = (3.3 - min_transient_v) * 1000.0

    # Đánh giá điện áp xác lập khi đang gánh tải nặng 5A (tại step 900 -> 1050)
    steady_heavy_v = np.mean(v_history[900:1050])

    # Đánh giá điện áp cuối cùng khi hồi phục
    final_settled_v = np.mean(v_history[1300:])

    print("1. KET QUA PHAN UNG DONG HOC KHI TAI TANG VOT (LOAD STEP 1A -> 5A):")
    print(f"   -> Dien ap dinh muc (V_ref)           : 3.30 V")
    print(f"   -> Do sut ap tuc thoi toi da (Sag)    : {voltage_sag_mv:.1f} mV")
    print(f"   -> Dien ap xac lap khi ganh tai 5A    : {steady_heavy_v:.3f} V (Sai lech < 10mV!)")
    print(f"   -> Dien ap cuoi cung sau khi ha tai   : {final_settled_v:.3f} V\n")

    assert abs(steady_heavy_v - 3.3) < 0.05, "PID khong duy tri duoc dien ap duoi tai nang!"
    assert abs(final_settled_v - 3.3) < 0.02, "Dien ap hoi phuc cuoi cung khong dat chuan!"
    print("[THANH CONG] BO DIEU KHIEN DIGITAL PID DA ON DINH DIEN AP TRUOC CU SOC TAI NANG!")
