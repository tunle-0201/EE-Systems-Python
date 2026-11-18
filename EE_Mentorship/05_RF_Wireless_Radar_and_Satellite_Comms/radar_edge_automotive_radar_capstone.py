"""
================================================================================
          MODULE T CAPSTONE FINALE: FULL REAL-TIME 77GHz AUTOMOTIVE
                   FMCW RADAR BASEBAND DSP & AEB ENGINE
================================================================================

1. KIEN TRUC HE THONG RADAR O TO TU LAI & AEB (FULL 2D RADAR PIPELINE):
   Day la kien truc xu ly tin hieu radar 77GHz milimet wave thoi gian thuc tren cac he thong
   xe tu hanh cap do cao (Tesla Hardware 4, Waymo Driver, Mercedes-Benz Drive Pilot Level 3):
   - Khi camera bi mu boi sương mu, mua bao, tuyet roi hoac anh den pha chieu loa,
     Radar 77GHz la he thong giam sat duy nhat cuu mang hanh khach!
   - Chuoi xu ly 4 buoc Baseband Radar DSP:
     + Buoc 1: Range-FFT tren truc thoi gian nhanh (Fast-Time) do khoang cach.
     + Buoc 2: Doppler-FFT tren truc thoi gian cham (Slow-Time) do van toc tuong doi.
     + Buoc 3: Bo do thich nghi 2D CA-CFAR (Cell-Averaging CFAR) loc sach tap am Clutter.
     + Buoc 4: He thong phanh khan cap tu dong AEB (Autonomous Emergency Braking):
               Uoc luong thoi gian va cham (Time-To-Collision - TTC). Kich hoat phanh
               gap khi TTC < 2.5 giay de ngan chan tai nan thảm khoc!

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   Ma tran du lieu Radar 2 chieu (2D Radar Data Cube):

                     Fast-Time (N mau ADC / 1 Chirp -> Do Cu ly)
                    ┌──────────────────────────────────────────────┐
     Chirp 0        │ Sample 0,  Sample 1,  ... , Sample N-1       │
     Chirp 1        │ Sample 0,  Sample 1,  ... , Sample N-1       │  Slow-Time
        ...         │                      ...                     │  (M Chirps
     Chirp M-1      │ Sample 0,  Sample 1,  ... , Sample N-1       │  -> Do Van toc)
                    └──────────────────────────────────────────────┘

   So do chuoi xu ly 2D Range-Doppler Map & AEB Decision Engine:

   [ Raw 2D Frame ] ──► [ Range-FFT (Hang) ] ──► [ Doppler-FFT (Cot) ]
                                                            │
                                                            ▼
                                                [ 2D Range-Doppler Map ]
                                                            │
                                                            ▼
                                                [ Bo do 2D CA-CFAR ]
                                                            │
                                                            ▼
                                                [ Danh sach muc tieu (R, v) ]
                                                            │
                                                            ▼
                                                [ AEB Collision Safety Engine ]

   Cong thuc tinh Thoi gian va cham (Time-To-Collision - TTC):

                        Cu ly Range
         TTC = ─────────────────────────────
               Toc do tiep can (-Velocity)

   Dieu kien kich hoat phanh khan cap AEB:
   TTC < 2.5 giay  va  Range < 50.0 m  ===► KICH HOAT PHANH KHAN CAP!
"""

from typing import List, Dict, Any
import numpy as np


class RealtimeAutomotiveRadarEngine:
    """
    Dong co xu ly tin hieu Radar 77GHz FMCW thoi gian thuc va he thong phanh khan cap AEB.
    """
    def __init__(
        self,
        f_carrier: float = 77e9,
        bandwidth: float = 1e9,
        chirp_duration: float = 40e-6,
        fs: float = 25e6,
        num_chirps: int = 64
    ):
        self.c = 3e8
        self.fc = float(f_carrier)
        self.B = float(bandwidth)
        self.Tc = float(chirp_duration)
        self.fs = float(fs)
        self.num_chirps = int(num_chirps)
        self.slope = self.B / self.Tc
        self.num_samples = int(self.Tc * self.fs)
        self.wavelength = self.c / self.fc

        # Tam do va do phan giai
        self.range_res = self.c / (2.0 * self.B)
        self.max_range = (self.c * (self.fs / 2.0)) / (2.0 * self.slope)
        self.vel_res = self.wavelength / (2.0 * self.num_chirps * self.Tc)
        self.max_vel = self.wavelength / (4.0 * self.Tc)

        # Truc vat ly
        self.range_axis = (self.c * np.fft.rfftfreq(self.num_samples, d=1.0 / self.fs)) / (2.0 * self.slope)
        doppler_freqs = np.fft.fftshift(np.fft.fftfreq(self.num_chirps, d=self.Tc))
        self.velocity_axis = (self.wavelength * doppler_freqs) / 2.0

    def generate_simulated_frame(self, targets: List[Dict[str, Any]], snr_db: float = 18.0) -> np.ndarray:
        """
        Tao khung du lieu 2D Radar gia lap (num_chirps, num_samples)
        """
        frame = np.zeros((self.num_chirps, self.num_samples), dtype=np.float32)
        fast_time = np.linspace(0, self.Tc, self.num_samples, endpoint=False)

        for m in range(self.num_chirps):
            slow_t = m * self.Tc
            for tgt in targets:
                r0 = float(tgt['range'])
                v0 = float(tgt['velocity'])
                rcs = float(tgt.get('rcs', 1.0))

                # Khoang cach tuc thoi cua muc tieu tai chirp thu m
                r_instant = r0 + v0 * slow_t
                tau = 2.0 * r_instant / self.c
                f_beat = self.slope * tau
                f_doppler = (2.0 * v0) / self.wavelength

                phase = 2.0 * np.pi * (f_beat * fast_time + f_doppler * slow_t + (2.0 * self.fc * r0 / self.c))
                frame[m, :] += rcs * np.cos(phase).astype(np.float32)

        # Them nhieu trang nhiet RF
        noise_std = 10.0 ** (-snr_db / 20.0)
        noise = noise_std * np.random.randn(*frame.shape).astype(np.float32)
        return frame + noise

    def compute_range_doppler_map(self, raw_frame: np.ndarray) -> np.ndarray:
        """
        Thuc hien chuoi 2D-FFT tao ma tran Range-Doppler Map:
        1. Range-FFT theo tung hang (truc Fast-Time) kem cua so Hanning
        2. Doppler-FFT theo tung cot (truc Slow-Time) kem cua so Hanning + fftshift
        """
        # Buoc 1: Windowing va Range-FFT
        window_fast = np.hanning(self.num_samples)
        range_fft_data = np.zeros((self.num_chirps, len(self.range_axis)), dtype=np.complex64)
        for m in range(self.num_chirps):
            windowed_chirp = raw_frame[m, :] * window_fast
            range_fft_data[m, :] = np.fft.rfft(windowed_chirp)

        # Buoc 2: Windowing va Doppler-FFT
        window_slow = np.hanning(self.num_chirps)[:, np.newaxis]
        windowed_range = range_fft_data * window_slow
        doppler_fft_data = np.fft.fftshift(np.fft.fft(windowed_range, axis=0), axes=0)

        # Ma tran cong suat Range-Doppler Map (dB)
        rd_map_db = 20.0 * np.log10(np.abs(doppler_fft_data) + 1e-12)
        return rd_map_db

    def process_and_detect_targets(
        self,
        rd_map_db: np.ndarray,
        cfar_guard: int = 1,
        cfar_train: int = 4,
        threshold_offset: float = 12.0
    ) -> List[Dict[str, Any]]:
        """
        Bo do thich nghi 2D CA-CFAR tren ban do Range-Doppler:
        Phat hien toa do cac muc tieu va tinh toan Time-To-Collision (TTC)
        """
        num_d, num_r = rd_map_db.shape
        detections = []
        w_d = cfar_guard + cfar_train
        w_r = cfar_guard + cfar_train

        for d in range(w_d, num_d - w_d):
            for r in range(w_r, num_r - w_r):
                cut_val = rd_map_db[d, r]

                # Lay vung cua so huan luyen hinh chu nhat
                sub_window = rd_map_db[d - w_d : d + w_d + 1, r - w_r : r + w_r + 1]
                total_cells = sub_window.size

                # Vung bao ve o giua
                guard_window = rd_map_db[d - cfar_guard : d + cfar_guard + 1, r - cfar_guard : r + cfar_guard + 1]
                guard_cells = guard_window.size

                train_sum = np.sum(sub_window) - np.sum(guard_window)
                num_train = total_cells - guard_cells

                noise_floor = train_sum / num_train
                thresh = noise_floor + threshold_offset

                if cut_val > thresh:
                    # Kiem tra dinh cuc dai cuc bo 3x3
                    local_3x3 = rd_map_db[d - 1 : d + 2, r - 1 : r + 2]
                    if cut_val == np.max(local_3x3):
                        tgt_range = float(self.range_axis[r])
                        tgt_velocity = float(self.velocity_axis[d])
                        snr = float(cut_val - noise_floor)

                        # Tinh toan Time-To-Collision (TTC)
                        # v < 0 nghia la muc tieu dang lao ve phia xe minh (closing velocity)
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

    # Gia lap tinh huong giao thong thuc te:
    # Xe 1 (Moi de doa truc dien): Cach 24.0m, dang phanh gap va tien gan voi van toc -10.0 m/s (-36.0 km/h) -> TTC = 2.4s < 2.5s (KICH HOAT AEB!)
    # Xe 2 (Xe chay cung chieu an toan): Cach 50.0m, dang chay nhanh hon voi van toc +6.0 m/s (+21.6 km/h) -> TTC = vo cung
    np.random.seed(42)
    traffic_targets = [
        {'range': 24.0, 'velocity': -10.0, 'rcs': 2.0},
        {'range': 50.0, 'velocity': 6.0, 'rcs': 1.5}
    ]

    # Sinh khung du lieu RF
    raw_frame = radar_engine.generate_simulated_frame(traffic_targets, snr_db=18.0)

    # Bien doi 2D Range-Doppler Map
    rd_map = radar_engine.compute_range_doppler_map(raw_frame)

    # Do muc tieu 2D CA-CFAR
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

    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE T: AUTOMOTIVE FMCW RADAR!")
    print("=========================================================")
