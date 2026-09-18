"""
================================================================================
          MODULE AL: EMBEDDED POWER ELECTRONICS & DIGITAL POWER SYSTEMS
              MILESTONE AL.3: THUẬT TOÁN ĐIỀU KHIỂN ĐIỂM CÔNG SUẤT CỰC ĐẠI MPPT
================================================================================

TẠI SAO VỆ TINH VÀ DRONE MẶT TRỜI BẮT BUỘC PHẢI CÓ THUẬT TOÁN MPPT?
Trên vệ tinh CubeSat không gian hoặc máy bay không người lái năng lượng mặt trời:
- Pin mặt trời (Solar PV Array) có đặc tính dòng-áp (I-V) và công suất (P-V) cực kỳ phi tuyến.
- Có một điểm duy nhất pin mặt trời phát ra công suất lớn nhất: Maximum Power Point (MPP).
- Nếu vi điều khiển chỉ giữ cố định điện áp, khi góc chiếu mặt trời hoặc nhiệt độ thay đổi,
  vệ tinh sẽ mất đến 40% - 60% năng lượng quý giá!

GIẢI PHÁP DSP NHÚNG: THUẬT TOÁN PERTURB & OBSERVE (P&O MPPT ALGORITHM):
Vi điều khiển định kỳ "nhử" (perturb) điện áp hoạt động và "quan sát" (observe) công suất:
1. Đo dòng và áp: P[n] = V[n] * I[n].
2. Tính đạo hàm sai phân:
                 Delta_P = P[n] - P[n-1]
                 Delta_V = V[n] - V[n-1]

                 Delta_P
        Slope = ─────────
                 Delta_V

3. Luật phán đoán:
   - Nếu Slope > 0: Đang ở bên trái đỉnh MPP -> Tăng tiếp điện áp (V_ref += step).
   - Nếu Slope < 0: Đã vượt quá đỉnh MPP sang phải -> Giảm bớt điện áp (V_ref -= step).
   - Nếu Slope ~ 0: Đã bám khóa chính xác điểm cực đại công suất MPP!
"""

import numpy as np

class SimulatedSolarPanel:
    """Mô hình pin mặt trời phi tuyến tính với bức xạ mặt trời (Irradiance) thay đổi"""
    def __init__(self, v_oc: float = 36.0, i_sc: float = 5.0, v_mpp: float = 29.5, i_mpp: float = 4.5):
        self.v_oc = v_oc      # Điện áp hở mạch (Open Circuit Voltage)
        self.i_sc = i_sc      # Dòng điện ngắn mạch (Short Circuit Current)
        self.v_mpp = v_mpp    # Điện áp tại điểm công suất cực đại lý thuyết
        self.i_mpp = i_mpp    # Dòng điện tại điểm công suất cực đại lý thuyết
        self.p_max_ideal = v_mpp * i_mpp  # ~ 132.75 W

    def get_current(self, voltage: float, sun_irradiance: float = 1.0) -> float:
        """Đặc tính đường cong I-V phi tuyến của tế bào quang điện"""
        if voltage <= 0.0:
            return float(self.i_sc * sun_irradiance)
        if voltage >= self.v_oc:
            return 0.0

        # Mô phỏng đường cong I-V chuẩn
        # Dòng giữ phẳng từ 0 đến V_mpp, sau đó sụt nhanh về 0 tại V_oc
        v_norm = voltage / self.v_oc
        i = self.i_sc * sun_irradiance * (1.0 - (v_norm ** 7))
        return float(max(0.0, i))


class PerturbAndObserveMPPT:
    def __init__(self, initial_voltage: float = 20.0, step_size: float = 0.25, v_min: float = 10.0, v_max: float = 35.0):
        self.v_ref = initial_voltage
        self.step = step_size
        self.v_min = v_min
        self.v_max = v_max

        self.prev_v = initial_voltage
        self.prev_p = 0.0

    def update(self, v_measured: float, i_measured: float) -> tuple:
        """
        Thực hiện 1 chu kỳ lặp giải thuật Perturb & Observe (P&O):
        Trả về: (v_ref_new, current_power, dP)
        """
        current_power = v_measured * i_measured
        delta_p = current_power - self.prev_p
        delta_v = v_measured - self.prev_v

        # Luật P&O thích nghi
        if abs(delta_v) < 1e-5:
            direction = 1.0  # Bước kích hoạt ban đầu
        else:
            if delta_p >= 0:
                direction = 1.0 if delta_v > 0 else -1.0
            else:
                direction = -1.0 if delta_v > 0 else 1.0

        self.v_ref += direction * self.step

        # Giới hạn an toàn
        self.v_ref = max(self.v_min, min(self.v_max, self.v_ref))

        self.prev_v = v_measured
        self.prev_p = current_power

        return float(self.v_ref), float(current_power), float(delta_p)


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED POWER: PERTURB & OBSERVE (P&O) MPPT TRACKER")
    print("=========================================================\n")

    solar_pv = SimulatedSolarPanel(v_oc=36.0, i_sc=5.0, v_mpp=29.5, i_mpp=4.5)
    mppt = PerturbAndObserveMPPT(initial_voltage=18.0, step_size=0.3)

    # Đỉnh công suất lý thuyết tại ánh sáng 100%
    # Quét nhanh tìm đỉnh thực tế của mô hình
    test_v_sweep = np.linspace(15.0, 35.0, 1000)
    test_p_sweep = [v * solar_pv.get_current(v, sun_irradiance=1.0) for v in test_v_sweep]
    best_p_idx = np.argmax(test_p_sweep)
    p_peak_target = test_p_sweep[best_p_idx]
    v_peak_target = test_v_sweep[best_p_idx]

    print(f"1. DIEM CONG SUAT CUC DAI LY THUYET (MAX POWER POINT):")
    print(f"   -> Dien ap dinh MPP ly tuong    : {v_peak_target:.2f} V")
    print(f"   -> Cong suat toi da (P_max)     : {p_peak_target:.2f} W\n")

    # Giả lập vòng điều khiển MPPT thời gian thực 80 chu kỳ
    v_op = 18.0  # Bắt đầu tại mức thấp 18V
    tracked_powers = []
    tracked_voltages = []

    for k in range(80):
        current_i = solar_pv.get_current(v_op, sun_irradiance=1.0)
        v_next_ref, p_meas, _ = mppt.update(v_measured=v_op, i_measured=current_i)

        tracked_powers.append(p_meas)
        tracked_voltages.append(v_op)
        v_op = v_next_ref

    final_v = np.mean(tracked_voltages[-10:])
    final_p = np.mean(tracked_powers[-10:])
    mppt_efficiency = (final_p / p_peak_target) * 100.0

    print("2. KET QUA BAM DUOI CUA BO DIEU KHIEN P&O MPPT:")
    print(f"   -> Cong suat ban dau (chua bam) : {tracked_powers[0]:.2f} W")
    print(f"   -> Cong suat sau khi hoi tu     : {final_p:.2f} W")
    print(f"   -> Dien ap khoa thanh cong      : {final_v:.2f} V (Sat moc {v_peak_target:.2f}V)")
    print(f"   -> Hieu suat thu hoi MPPT       : {mppt_efficiency:.2f}% (Tieu chuan khong gian > 98%)\n")

    assert mppt_efficiency > 98.0, "Hieu suat thu hoi nang luong MPPT chua dat yeu cau!"
    assert abs(final_v - v_peak_target) < 1.0, "Dien ap khoa lech qua xa diem MPP!"

    print("[THANH CONG] THUAT TOAN P&O MPPT BAM DINH CONG SUAT MAT TROI CHINH XAC 99%!")
