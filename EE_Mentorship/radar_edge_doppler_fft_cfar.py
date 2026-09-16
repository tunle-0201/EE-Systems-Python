"""
================================================================================
          MODULE AJ: EMBEDDED AUTOMOTIVE FMCW RADAR BASEBAND DSP
              MILESTONE AJ.3: DOPPLER-FFT & THUẬT TOÁN PHÁT HIỆN THÍCH NGHI CA-CFAR
================================================================================

TẠI SAO PHẢI CÓ TRỤC SLOW-TIME VÀ THUẬT TOÁN CA-CFAR?
1. Trục Slow-Time & Doppler-FFT:
   Khi phát liên tiếp M chirps (ví dụ 64 chirps) với chu kỳ lặp T_rep:
   - Mục tiêu chuyển động với vận tốc xuyên tâm v sẽ gây ra độ lệch pha Doppler giữa các chirp:
     Delta_phi = 4 * pi * v * T_rep / lambda
   - Biến đổi FFT theo chiều Slow-Time (Doppler-FFT) tính chính xác vận tốc xe:
                    lambda * f_doppler
       Velocity v = ──────────────────
                            2

2. Thuật toán thích nghi CA-CFAR (Cell-Averaging Constant False Alarm Rate):
   Trong thực tế, nhiễu phản xạ mặt đường (ground clutter), mưa gió và nhiễu nhiệt thay đổi
   liên tục theo cự ly và môi trường. Ngưỡng cố định sẽ gây ra hàng nghìn báo động giả (Ghost Targets)!
   - Ô kiểm tra CUT (Cell Under Test): Điểm nghi ngờ có vật cản.
   - Ô bảo vệ Guard Cells: Ngăn năng lượng của mục tiêu tràn sang vùng ước lượng.
   - Ô huấn luyện Training Cells: Tính công suất nhiễu trung bình xung quanh.
   - Ngưỡng thích nghi:
       Threshold = Noise_Floor * alpha (hoặc Noise_dB + Offset_dB)
       Nếu CUT > Threshold ===> MỤC TIÊU HỢP LỆ!
"""

import numpy as np

class DopplerCFARDetector:
    def __init__(self, f_carrier: float = 77e9, t_rep: float = 60e-6, num_chirps: int = 64):
        self.c = 3e8
        self.fc = f_carrier
        self.wavelength = self.c / f_carrier  # lambda ~ 3.89 mm tai 77 GHz
        self.t_rep = t_rep
        self.num_chirps = num_chirps

        # Van toc toi da khong nhap nhang va do phan giai van toc
        self.v_max = self.wavelength / (4.0 * t_rep)
        self.v_res = self.wavelength / (2.0 * num_chirps * t_rep)

        # Truc van toc (Doppler velocity axis)
        doppler_freqs = np.fft.fftshift(np.fft.fftfreq(num_chirps, d=t_rep))
        self.velocity_axis = (self.wavelength * doppler_freqs) / 2.0

    def compute_doppler_spectrum(self, slow_time_samples: np.ndarray) -> np.ndarray:
        """
        slow_time_samples: Mảng 1D gồm M giá trị phức tại 1 Range Bin cụ thể qua M chirps
        Trả về: Phổ Doppler công suất (dB) sau khi dịch gốc 0 về trung tâm (fftshift)
        """
        window = np.hanning(len(slow_time_samples))
        windowed = slow_time_samples * window
        fft_out = np.fft.fftshift(np.fft.fft(windowed, n=self.num_chirps))
        power_db = 20.0 * np.log10(np.abs(fft_out) + 1e-12)
        return power_db

    def ca_cfar_1d(self, power_db: np.ndarray, num_train: int = 8, num_guard: int = 2, threshold_offset_db: float = 10.0) -> tuple:
        """
        Bộ dò thích nghi CA-CFAR 1D:
        - num_train: Số ô huấn luyện mỗi bên (Training Cells)
        - num_guard: Số ô bảo vệ mỗi bên (Guard Cells)
        - threshold_offset_db: Ngưỡng nâng biên độ an toàn trên mức nền nhiễu
        Trả về: (threshold_profile, detected_indices)
        """
        n = len(power_db)
        threshold_profile = np.zeros(n, dtype=np.float32)
        detections = []

        window_size = num_train + num_guard

        for i in range(window_size, n - window_size):
            # Lấy các ô huấn luyện 2 bên (bỏ qua các ô bảo vệ)
            left_train = power_db[i - window_size : i - num_guard]
            right_train = power_db[i + num_guard + 1 : i + window_size + 1]

            training_cells = np.concatenate([left_train, right_train])
            noise_estimate = float(np.mean(training_cells))

            thresh = noise_estimate + threshold_offset_db
            threshold_profile[i] = thresh

            if power_db[i] > thresh:
                # Kiem tra dinh cuc dai cuc bo
                if power_db[i] > power_db[i - 1] and power_db[i] > power_db[i + 1]:
                    detections.append(i)

        return threshold_profile, detections


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED FMCW RADAR: DOPPLER-FFT & CA-CFAR DETECTOR")
    print("=========================================================\n")

    cfar = DopplerCFARDetector(f_carrier=77e9, t_rep=60e-6, num_chirps=64)

    print("1. THONG SO VAN TOC DOPPLER RADAR 77GHz:")
    print(f"   -> Buoc song song mang (lambda) : {cfar.wavelength * 1000:.2f} mm")
    print(f"   -> Van toc toi da (V_max)       : {cfar.v_max:.2f} m/s ({cfar.v_max * 3.6:.1f} km/h)")
    print(f"   -> Do phan giai van toc (dv)    : {cfar.v_res:.2f} m/s ({cfar.v_res * 3.6:.1f} km/h)\n")

    # Giả lập 2 xe di chuyển:
    # Xe 1: Tiến lại gần với vận tốc -8.0 m/s (-28.8 km/h)
    # Xe 2: Đi cùng chiều vượt lên với vận tốc +6.5 m/s (+23.4 km/h)
    target_velocities = [-8.0, 6.5]
    slow_time = np.arange(cfar.num_chirps) * cfar.t_rep

    combined_signal = np.zeros(cfar.num_chirps, dtype=np.complex64)
    for v in target_velocities:
        # Độ dịch tần Doppler: fd = 2 * v / lambda
        f_doppler = (2.0 * v) / cfar.wavelength
        combined_signal += np.exp(1j * 2.0 * np.pi * f_doppler * slow_time)

    # Giả lập nhiễu nền Clutter thay đổi cục bộ (Noise + Clutter)
    np.random.seed(123)
    noise = 0.3 * (np.random.randn(cfar.num_chirps) + 1j * np.random.randn(cfar.num_chirps))
    combined_signal += noise

    # Thực hiện Doppler-FFT
    power_db = cfar.compute_doppler_spectrum(combined_signal)

    # Chạy thuật toán CA-CFAR thích nghi
    thresh_line, detected_bins = cfar.ca_cfar_1d(power_db, num_train=6, num_guard=2, threshold_offset_db=8.0)

    print("2. KET QUA PHAT HIEN VAN TOC XE BANG DOPPLER-FFT & CA-CFAR:")
    for v_true in target_velocities:
        # Tìm bin vận tốc gần nhất
        closest_bin = min(detected_bins, key=lambda b: abs(cfar.velocity_axis[b] - v_true))
        v_est = float(cfar.velocity_axis[closest_bin])
        err = abs(v_est - v_true)
        print(f"   -> Xe thuc te: {v_true:6.1f} m/s ({v_true * 3.6:5.1f} km/h) | CFAR do: {v_est:6.1f} m/s ({v_est * 3.6:5.1f} km/h) | Sai so: {err:.2f} m/s")
        assert err < cfar.v_res, "Sai so van toc vuot qua do phan giai Doppler-FFT!"

    print("\n[THANH CONG] DOPPLER-FFT VA CA-CFAR LOC SACH NHIEU CLUTTER VA DO CHINH XAC VAN TOC XE!")
