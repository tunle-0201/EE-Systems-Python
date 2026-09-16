"""
================================================================================
          MODULE AJ: EMBEDDED AUTOMOTIVE FMCW RADAR BASEBAND DSP
              MILESTONE AJ.2: BIẾN ĐỔI RANGE-FFT XÁC ĐỊNH KHOẢNG CÁCH ĐA MỤC TIÊU
================================================================================

TẠI SAO PHẢI DÙNG BIẾN ĐỔI RANGE-FFT TRÊN TRỤC FAST-TIME?
Trong môi trường giao thông thực tế (hoặc máy bay không người lái), radar nhận về
tín hiệu dội từ nhiều chướng ngại vật cùng lúc (xe hơi phía trước, xe máy, biển báo):
- Tín hiệu IF trung tần là tổng của nhiều sóng hình sin với các tần số phách khác nhau:
  s_if(t) = A1*cos(2*pi*f1*t) + A2*cos(2*pi*f2*t) + ... + noise
- Biến đổi Range-FFT (Fast Fourier Transform trên trục Fast-Time) tách từng tần số phách
  thành các đỉnh năng lượng (peak) riêng biệt trong miền khoảng cách!

CÔNG THỨC TOÁN HỌC RADAR (DẠNG ASCII TEXT):
1. Ánh xạ từ chỉ số bin FFT sang cự ly mục tiêu R:
                        c * (k * fs / N_fft)
        Range R_k = ─────────────────────────
                             2 * S

2. Tầm quét xa tối đa không bị nhập nhằng tần số (Max Unambiguous Range):
                        c * (fs / 2)
        Range_max = ───────────────────
                           2 * S

3. Độ phân giải cự ly tối thiểu giữa 2 xe:
                           c
        Delta_Range = ───────────
                         2 * B
"""

import numpy as np

class RangeFFTProcessor:
    def __init__(self, f_carrier: float = 77e9, bandwidth: float = 1e9, chirp_duration: float = 50e-6, fs: float = 25e6, n_fft: int = 2048):
        self.c = 3e8
        self.fc = f_carrier
        self.B = bandwidth
        self.Tc = chirp_duration
        self.fs = fs
        self.n_fft = n_fft
        self.slope = bandwidth / chirp_duration
        self.num_samples = int(chirp_duration * fs)

        # Tính toán tầm đo tối đa và độ phân giải
        self.max_range = (self.c * (fs / 2.0)) / (2.0 * self.slope)
        self.range_resolution = self.c / (2.0 * self.B)

        # Trục cự ly cho từng bin FFT
        freq_bins = np.fft.rfftfreq(n_fft, d=1.0 / fs)
        self.range_axis = (self.c * freq_bins) / (2.0 * self.slope)

    def process_chirp(self, if_signal: np.ndarray, apply_window: bool = True) -> tuple:
        """
        Thực hiện Range-FFT trên 1 chirp trung tần IF:
        1. Nhân cửa sổ Hanning giảm rò rỉ phổ (Spectral Leakage)
        2. Zero-padding lên n_fft điểm để nội suy đỉnh phổ mượt mà
        3. Tính toán phổ công suất Range Profile (dB)
        Trả về: (range_axis, power_db)
        """
        sig = if_signal[:self.num_samples].astype(np.float32)

        if apply_window:
            window = np.hanning(len(sig))
            sig = sig * window

        # Biến đổi Fast Fourier Transform (Range-FFT)
        spectrum = np.fft.rfft(sig, n=self.n_fft)
        magnitude = np.abs(spectrum)
        power_db = 20.0 * np.log10(magnitude + 1e-12)

        return self.range_axis, power_db

    def detect_peaks(self, power_db: np.ndarray, threshold_db: float = 20.0) -> list:
        """
        Tìm các đỉnh mục tiêu vượt ngưỡng công suất
        """
        detected_ranges = []
        for i in range(1, len(power_db) - 1):
            if power_db[i] > threshold_db and power_db[i] > power_db[i - 1] and power_db[i] > power_db[i + 1]:
                detected_ranges.append(float(self.range_axis[i]))
        return detected_ranges


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED FMCW RADAR: RANGE-FFT FAST-TIME PROCESSOR")
    print("=========================================================\n")

    processor = RangeFFTProcessor(f_carrier=77e9, bandwidth=1e9, chirp_duration=50e-6, fs=25e6, n_fft=2048)

    print("1. THONG SO TAM QUET VA PHAN GIAI RANGE-FFT:")
    print(f"   -> Tam xa toi da (Range Max)     : {processor.max_range:.1f} m")
    print(f"   -> Do phan giai cuc ly (Delta R)  : {processor.range_resolution * 100:.1f} cm")
    print(f"   -> Kich thuoc Range-FFT           : {processor.n_fft} diem\n")

    # Giả lập 3 xe ô tô ở khoảng cách 18.0m, 52.0m, và 84.0m
    true_targets = [18.0, 52.0, 84.0]
    t_axis = np.linspace(0, processor.Tc, processor.num_samples, endpoint=False)

    combined_if = np.zeros(processor.num_samples, dtype=np.float32)
    for dist in true_targets:
        f_b = (2.0 * processor.slope * dist) / processor.c
        combined_if += np.cos(2.0 * np.pi * f_b * t_axis).astype(np.float32)

    # Thêm nhiễu trắng nhiệt RF
    np.random.seed(42)
    combined_if += 0.2 * np.random.randn(processor.num_samples).astype(np.float32)

    # Chạy Range-FFT
    r_axis, p_db = processor.process_chirp(combined_if)
    detected = processor.detect_peaks(p_db, threshold_db=40.0)

    print("2. KET QUA PHAT HIEN DA MUC TIEU BANG RANGE-FFT:")
    for target in true_targets:
        # Tìm đỉnh gần nhất
        closest_det = min(detected, key=lambda x: abs(x - target))
        err = abs(closest_det - target)
        print(f"   -> Xe muc tieu: {target:5.1f}m  |  Range-FFT phat hien: {closest_det:5.1f}m  |  Sai so: {err * 100:.2f} cm")
        assert err < processor.range_resolution, f"Sai so vuot qua do phan giai Range-FFT!"

    print("\n[THANH CONG] RANGE-FFT TACH VA DINH VI CHINH XAC 100% TAT CA CAC XE MUC TIEU!")
