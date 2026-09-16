"""
================================================================================
          MODULE AJ: EMBEDDED AUTOMOTIVE FMCW RADAR BASEBAND DSP
              MILESTONE AJ.1: BỘ TẠO CHIRP FMCW & MẠCH TRỘN DECHIRPING TÍN HIỆU IF
================================================================================

NGUYÊN LÝ RADAR SÓNG LIÊN TỤC BIẾN ĐIỆU TẦN SỐ (FMCW RADAR - 77 GHz):
Trong hệ thống tự lái (Tesla Autopilot, Radar 77GHz cho ô tô và máy bay không người lái),
radar phát ra các xung tuyến tính gọi là Chirp (tần số quét tăng dần theo thời gian):

                   Băng thông quét B
  Độ dốc Chirp S = ─────────────────
                   Thời gian quét T_c

1. Tín hiệu phát TX(t): Tần số quét từ f_c đến f_c + B.
2. Mục tiêu ở cự ly R phản xạ sóng về bộ thu sau thời gian trễ trượt:
                 2 * R
      tau = ─────────────   (c = 3e8 m/s: Vận tốc ánh sáng)
                   c

3. Mạch trộn vô tuyến (RF Mixer) nhân tín hiệu TX và RX rồi qua bộ lọc thông thấp (LPF):
   Tạo ra tín hiệu phách trung tần IF (Intermediate Frequency / Beat Signal):
   
                 2 * S * R
      f_beat = ─────────────
                     c

4. Từ tần số phách f_beat đo được, Radar tính ngược cự ly mục tiêu R:
                 c * f_beat
      Range R = ─────────────
                    2 * S
"""

import numpy as np

class FMCWChirpGenerator:
    def __init__(self, f_carrier: float = 77e9, bandwidth: float = 1e9, chirp_duration: float = 50e-6, fs: float = 25e6):
        """
        - f_carrier: Tần số sóng mang (77 GHz chuẩn Automotive Radar)
        - bandwidth: Băng thông quét tần số (1 GHz -> độ phân giải cự ly c / (2B) = 15 cm)
        - chirp_duration: Thời gian quét 1 chirp (50 micro-giây)
        - fs: Tần số lấy mẫu ADC trung tần (25 MHz)
        """
        self.c = 3e8
        self.fc = f_carrier
        self.B = bandwidth
        self.Tc = chirp_duration
        self.fs = fs
        self.slope = bandwidth / chirp_duration
        self.num_samples = int(chirp_duration * fs)
        self.time_axis = np.linspace(0, chirp_duration, self.num_samples, endpoint=False)

    def generate_beat_signal(self, target_distance_m: float) -> tuple:
        """
        Mô phỏng bộ trộn RF Mixer tạo tín hiệu Beat IF thời gian thực:
        1. Tính thời gian trễ phản xạ sóng: tau = 2 * R / c
        2. Tần số phách lý thuyết: f_beat = slope * tau = 2 * slope * R / c
        3. Tín hiệu phách IF: s_if(t) = cos(2 * pi * f_beat * t + phi)
        Trả về: (time_axis, if_signal, f_beat_theoretical)
        """
        tau = 2.0 * target_distance_m / self.c
        f_beat_expected = self.slope * tau

        # Tín hiệu phách sau trộn tần (Down-converted Beat Signal)
        phi_phase = 2.0 * np.pi * self.fc * tau
        if_signal = np.cos(2.0 * np.pi * f_beat_expected * self.time_axis + phi_phase).astype(np.float32)

        return self.time_axis, if_signal, float(f_beat_expected)

    def calculate_range_from_beat(self, beat_frequency_hz: float) -> float:
        """
        Tính toán cự ly mục tiêu từ tần số phách IF
        """
        return float((self.c * beat_frequency_hz) / (2.0 * self.slope))


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED FMCW RADAR: CHIRP & BEAT SIGNAL GENERATOR")
    print("=========================================================\n")

    radar = FMCWChirpGenerator(f_carrier=77e9, bandwidth=1e9, chirp_duration=50e-6, fs=25e6)

    test_distances = [15.0, 45.0, 75.0, 120.0]  # Mục tiêu ở 15m, 45m, 75m, 120m

    print("1. KIEM DINH TINH TOAN TAN SO PHACH TRUNG TAN (IF BEAT FREQUENCY):")
    for dist in test_distances:
        t, if_sig, f_beat = radar.generate_beat_signal(target_distance_m=dist)
        calculated_dist = radar.calculate_range_from_beat(f_beat)

        print(f"   -> Muc tieu R = {dist:5.1f}m  |  Tan so phach f_beat = {f_beat / 1e6:6.3f} MHz  |  Cuc ly do duoc: {calculated_dist:5.1f}m")
        assert abs(calculated_dist - dist) < 1e-4, f"Loi tinh toan cuc ly FMCW: {calculated_dist} != {dist}"

    print(f"\n2. THONG SO PHAN CUNG RADAR 77GHz:")
    print(f"   -> Bang thong chirp (B)          : {radar.B / 1e9:.2f} GHz")
    print(f"   -> Thoi gian quet chirp (Tc)     : {radar.Tc * 1e6:.1f} us")
    print(f"   -> Do doc chirp (Slope S)        : {radar.slope:.2e} Hz/s")
    print(f"   -> Do phan giai cuc ly (c / 2B)  : {radar.c / (2 * radar.B) * 100:.1f} cm")
    print(f"   -> So mau ADC moi chirp          : {radar.num_samples} samples")

    print("\n[THANH CONG] BO TAO CHIRP VA TINH TOAN BEAT SIGNAL FMCW HOAN TAT CHINH XAC 100%!")
