"""
================================================================================
          MODULE AJ: EMBEDDED AUTOMOTIVE FMCW RADAR BASEBAND DSP
              MILESTONE AJ.4: CAPSTONE FULL REAL-TIME 77GHz RADAR DSP ENGINE
================================================================================

KIẾN TRÚC TRỌNG TÂM: ĐỘNG CƠ XỬ LÝ TÍN HIỆU RADAR Ô TÔ TỰ LÁI THỜI GIAN THỰC
Trong các xe tự hành cấp độ cao (Tesla Hardware 4 / Waymo), radar 77GHz quét liên tục
để phát hiện chướng ngại vật trong sương mù, mưa lớn và bụi bẩn khi camera bị lóa:

MA TRẬN DỮ LIỆU RADAR KHÔNG GIAN 2 CHIỀU:
                  Fast-Time (Mẫu ADC trong 1 Chirp -> Đo Cự ly)
                 ┌──────────────────────────────────────────────┐
  Chirp 0        │ Sample 0,  Sample 1,  ... , Sample N-1       │
  Chirp 1        │ Sample 0,  Sample 1,  ... , Sample N-1       │  Slow-Time
     ...         │                      ...                     │  (M Chirps
  Chirp M-1      │ Sample 0,  Sample 1,  ... , Sample N-1       │  -> Đo Vận tốc)
                 └──────────────────────────────────────────────┘

CHUỖI XỬ LÝ ĐỒNG BỘ 4 BƯỚC (BASEBAND RADAR DSP PIPELINE):
1. 2D Range-Doppler Map:
   - Chiều 1: Range-FFT theo từng hàng (Fast-time).
   - Chiều 2: Doppler-FFT theo từng cột (Slow-time).
2. Phát hiện thích nghi 2D CA-CFAR (Cell-Averaging Constant False Alarm Rate).
3. Trích xuất thuộc tính vật lý: Cự ly (m), Vận tốc tương đối (m/s, km/h), SNR (dB).
4. Hệ thống phanh khẩn cấp tự động AEB (Autonomous Emergency Braking):
   Tính thời gian va chạm Time-To-Collision (TTC):
                       Cự ly Range
          TTC = ───────────────────────────
                Tốc độ tiếp cận (-Velocity)
   Kích hoạt còi báo động và lệnh phanh khẩn cấp nếu TTC < 2.5 giây!
"""

import numpy as np

class RealtimeAutomotiveRadarEngine:
    def __init__(self, f_carrier: float = 77e9, bandwidth: float = 1e9, chirp_duration: float = 40e-6, fs: float = 25e6, num_chirps: int = 64):
        self.c = 3e8
        self.fc = f_carrier
        self.B = bandwidth
        self.Tc = chirp_duration
        self.fs = fs
        self.num_chirps = num_chirps
        self.slope = bandwidth / chirp_duration
        self.num_samples = int(chirp_duration * fs)  # 1000 samples per chirp
        self.wavelength = self.c / f_carrier

        # Tầm đo và độ phân giải
        self.range_res = self.c / (2.0 * self.B)
        self.max_range = (self.c * (fs / 2.0)) / (2.0 * self.slope)
        self.vel_res = self.wavelength / (2.0 * num_chirps * chirp_duration)
        self.max_vel = self.wavelength / (4.0 * chirp_duration)

        # Trục vật lý
        self.range_axis = (self.c * np.fft.rfftfreq(self.num_samples, d=1.0 / fs)) / (2.0 * self.slope)
        doppler_freqs = np.fft.fftshift(np.fft.fftfreq(num_chirps, d=chirp_duration))
        self.velocity_axis = (self.wavelength * doppler_freqs) / 2.0

    def generate_simulated_frame(self, targets: list, snr_db: float = 18.0) -> np.ndarray:
        """
        Tạo khung dữ liệu 2D Radar giả lập dạng thực (num_chirps, num_samples)
        targets: Danh sách dict [{'range': float, 'velocity': float, 'rcs': float}]
        """
        frame = np.zeros((self.num_chirps, self.num_samples), dtype=np.float32)
        fast_time = np.linspace(0, self.Tc, self.num_samples, endpoint=False)

        for m in range(self.num_chirps):
            slow_t = m * self.Tc
            for tgt in targets:
                r0 = tgt['range']
                v0 = tgt['velocity']
                rcs = tgt.get('rcs', 1.0)

                # Khoảng cách tức thời của mục tiêu tại chirp thứ m
                r_instant = r0 + v0 * slow_t
                tau = 2.0 * r_instant / self.c
                f_beat = self.slope * tau
                f_doppler = (2.0 * v0) / self.wavelength

                phase = 2.0 * np.pi * (f_beat * fast_time + f_doppler * slow_t + (2.0 * self.fc * r0 / self.c))
                frame[m, :] += rcs * np.cos(phase).astype(np.float32)

        # Thêm nhiễu trắng nhiệt RF
        noise_std = 10.0 ** (-snr_db / 20.0)
        noise = noise_std * np.random.randn(*frame.shape).astype(np.float32)
        return frame + noise

    def compute_range_doppler_map(self, raw_frame: np.ndarray) -> np.ndarray:
        """
        Thực hiện chuỗi 2D-FFT để tạo ma trận Range-Doppler Map:
        1. Range-FFT theo từng hàng (trục Fast-Time) kèm cửa sổ Hanning
        2. Doppler-FFT theo từng cột (trục Slow-Time) kèm cửa sổ Hanning + fftshift
        """
        # Bước 1: Windowing và Range-FFT
        window_fast = np.hanning(self.num_samples)
        range_fft_data = np.zeros((self.num_chirps, len(self.range_axis)), dtype=np.complex64)
        for m in range(self.num_chirps):
            windowed_chirp = raw_frame[m, :] * window_fast
            range_fft_data[m, :] = np.fft.rfft(windowed_chirp)

        # Bước 2: Windowing và Doppler-FFT
        window_slow = np.hanning(self.num_chirps)[:, np.newaxis]
        windowed_range = range_fft_data * window_slow
        doppler_fft_data = np.fft.fftshift(np.fft.fft(windowed_range, axis=0), axes=0)

        # Ma trận công suất Range-Doppler Map (dB)
        rd_map_db = 20.0 * np.log10(np.abs(doppler_fft_data) + 1e-12)
        return rd_map_db

    def process_and_detect_targets(self, rd_map_db: np.ndarray, cfar_guard: int = 1, cfar_train: int = 4, threshold_offset: float = 12.0) -> list:
        """
        Bộ dò thích nghi 2D CA-CFAR trên bản đồ Range-Doppler:
        Phát hiện tọa độ các mục tiêu và tính toán Time-To-Collision (TTC)
        """
        num_d, num_r = rd_map_db.shape
        detections = []
        w_d = cfar_guard + cfar_train
        w_r = cfar_guard + cfar_train

        for d in range(w_d, num_d - w_d):
            for r in range(w_r, num_r - w_r):
                cut_val = rd_map_db[d, r]

                # Lấy vùng cửa sổ huấn luyện hình chữ nhật
                sub_window = rd_map_db[d - w_d : d + w_d + 1, r - w_r : r + w_r + 1]
                total_cells = sub_window.size

                # Vùng bảo vệ ở giữa
                guard_window = rd_map_db[d - cfar_guard : d + cfar_guard + 1, r - cfar_guard : r + cfar_guard + 1]
                guard_cells = guard_window.size

                train_sum = np.sum(sub_window) - np.sum(guard_window)
                num_train = total_cells - guard_cells

                noise_floor = train_sum / num_train
                thresh = noise_floor + threshold_offset

                if cut_val > thresh:
                    # Kiểm tra đỉnh cực đại cục bộ 3x3
                    local_3x3 = rd_map_db[d - 1 : d + 2, r - 1 : r + 2]
                    if cut_val == np.max(local_3x3):
                        tgt_range = float(self.range_axis[r])
                        tgt_velocity = float(self.velocity_axis[d])
                        snr = float(cut_val - noise_floor)

                        # Tính toán Time-To-Collision (TTC)
                        # v < 0 nghĩa là mục tiêu đang lao về phía xe mình (closing velocity)
                        ttc = (tgt_range / (-tgt_velocity)) if tgt_velocity < -0.5 else float('inf')
                        aeb_warning = bool(ttc < 2.5 and tgt_range < 50.0)

                        detections.append({
                            'range_m': tgt_range,
                            'velocity_ms': tgt_velocity,
                            'velocity_kmh': tgt_velocity * 3.6,
                            'snr_db': snr,
                            'ttc_sec': ttc,
                            'aeb_warning': aeb_warning
                        })

        return detections


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: FULL 77GHz AUTOMOTIVE FMCW RADAR BASEBAND DSP")
    print("=========================================================\n")

    radar_engine = RealtimeAutomotiveRadarEngine(f_carrier=77e9, bandwidth=1e9, chirp_duration=40e-6, fs=25e6, num_chirps=64)

    print("1. THONG SO HE THONG RADAR CAPSTONE 77GHz:")
    print(f"   -> Bang thong quet (B)            : {radar_engine.B / 1e9:.2f} GHz")
    print(f"   -> Tam do xa nhat (Max Range)     : {radar_engine.max_range:.1f} m")
    print(f"   -> Do phan giai cuc ly (Delta R)  : {radar_engine.range_res * 100:.1f} cm")
    print(f"   -> Van toc do toi da (Max Vel)    : {radar_engine.max_vel:.1f} m/s ({radar_engine.max_vel * 3.6:.1f} km/h)")
    print(f"   -> Do phan giai van toc (Delta v) : {radar_engine.vel_res:.2f} m/s ({radar_engine.vel_res * 3.6:.1f} km/h)\n")

    # Giả lập tình huống giao thông thực tế:
    # Xe 1 (Mối đe dọa trực diện): Cách 24.0m, đang phanh gấp và tiến gần với vận tốc -10.0 m/s (-36.0 km/h) -> TTC = 2.4s < 2.5s (KÍCH HOẠT AEB!)
    # Xe 2 (Xe chạy cùng chiều an toàn): Cách 50.0m, đang chạy nhanh hơn với vận tốc +6.0 m/s (+21.6 km/h) -> TTC = vô cùng
    np.random.seed(42)
    traffic_targets = [
        {'range': 24.0, 'velocity': -10.0, 'rcs': 2.0},
        {'range': 50.0, 'velocity': 6.0, 'rcs': 1.5}
    ]

    # Sinh khung dữ liệu RF
    raw_frame = radar_engine.generate_simulated_frame(traffic_targets, snr_db=18.0)

    # Biến đổi 2D Range-Doppler Map
    rd_map = radar_engine.compute_range_doppler_map(raw_frame)

    # Dò mục tiêu 2D CA-CFAR
    detected_targets = radar_engine.process_and_detect_targets(rd_map, cfar_guard=1, cfar_train=4, threshold_offset=25.0)

    print("2. KET QUA NHAN DIEN VA PHAN TICH AN TOAN GIAO THONG (AEB TELEMETRY):")
    for i, tgt in enumerate(detected_targets, 1):
        print(f"   [MUC TIEU #{i}]")
        print(f"      - Cuc ly (Range)      : {tgt['range_m']:5.1f} m")
        print(f"      - Van toc (Velocity)  : {tgt['velocity_ms']:5.1f} m/s ({tgt['velocity_kmh']:5.1f} km/h)")
        print(f"      - Ti so tin-nhieu SNR : {tgt['snr_db']:5.1f} dB")
        if tgt['ttc_sec'] < 100.0:
            print(f"      - Thoi gian va cham   : {tgt['ttc_sec']:5.2f} giay")
        else:
            print(f"      - Thoi gian va cham   : An toan (Khong co nguy co)")
        print(f"      - Canh bao phanh AEB  : {'[DANGER] PHANH KHAN CAP!' if tgt['aeb_warning'] else '[SAFE] An toan'}")

    # Kiem tra logic an toan
    threat_targets = [t for t in detected_targets if t['aeb_warning']]
    assert len(threat_targets) == 1, "He thong phai phat hien dung 1 muc tieu gay nguy hiem va kich hoat AEB!"
    assert threat_targets[0]['range_m'] < 30.0, "Cuc ly xe phanh gap khong chinh xac!"
    assert threat_targets[0]['ttc_sec'] < 2.5, "Canh bao TTC phai duoc kich hoat duoi 2.5s!"

    print("\n[THANH CONG] CAPSTONE AUTOMOTIVE FMCW RADAR BASEBAND ENGINE HOAN TAT XUAT SAC!")
