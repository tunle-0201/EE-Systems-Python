"""
================================================================================
          MODULE T: EMBEDDED AUTOMOTIVE 77GHz FMCW RADAR BASEBAND DSP
    MILESTONE T.3: DOPPLER-FFT SLOW-TIME & BO DO THICH NGHI CA-CFAR 1D
================================================================================

1. NGUYEN LY VAT LY & TRUC SLOW-TIME (DOPPLER VELOCITY & CA-CFAR DETECTION):
   - Tai sao chi do khoang cach Range-FFT la chua du cho xe tu hanh?
     + Trong giao thong, he thong phanh khan cap tu dong (AEB) can biet ngay lap tuc:
       Xe phia truoc dang chay cung chieu, dung yen, hay dang phanh gap lao ve phia minh!
   - Truc thoi gian cham (Slow-Time) & Hieu ung Doppler:
     + Khi phat lien tiep M chirps (vi du 64 chirps) voi chu ky lap T_rep (vi du 60 us):
       neu muc tieu chuyen dong voi van toc v, pha cua tin hieu phach se xoay mot goc
       Delta_phi = 4 * pi * v * T_rep / lambda giua cac chirp lien tiep.
     + Phep bien doi Doppler-FFT tren cot Slow-Time se tach chinh xac van toc chuyen dong.
   - Thuat toan thich nghi CA-CFAR (Cell-Averaging Constant False Alarm Rate):
     + Nhiễu phan xa mat duong (Ground Clutter), nuoc mua va nhieu nhiet bien thien khong ngung.
       Neu dung mot nguong co dinh se gay ra hang nghin bao dong gia (Ghost Targets)!
     + CA-CFAR truot mot cua so qua tung o CUT (Cell Under Test):
       Dung cac o huan luyen (Training Cells) de uoc tinh cong suat nen nhieu cuc bo,
       bo qua cac o bao ve (Guard Cells) tranh ro ri nang luong tu chinh muc tieu.
     + Nguong tu dong thich ung theo moi truong!

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do chuoi xung Chirp tren truc thoi gian cham Slow-Time:

   Chirp 0          Chirp 1          Chirp 2             Chirp M-1
   /|               /|               /|                  /|
  / |              / |              / |                 / |
 /  |             /  |             /  |                /  |
────┴─────────────┴──┴─────────────┴──┴────── ... ─────┴──┴─────► Slow-Time
 ◄──── T_rep ────►

   So do cua so truot CA-CFAR 1D (Adaptive Sliding Window):

   ┌───────────────┬─────────┬───────┬─────────┬───────────────┐
   │ Training Left │  Guard  │  CUT  │  Guard  │Training Right │
   │  (N_train o)  │ (N_g o) │(Cell) │ (N_g o) │  (N_train o)  │
   └───────────────┴─────────┴───────┴─────────┴───────────────┘
   ◄────── Uoc tinh nhieu ───►       ◄─── Uoc tinh nhieu ──────►

   Cong thuc nguong dong thich nghi (Adaptive Noise Threshold):

                  Tong cong suat cac o Training Left va Right
   Noise_Floor = ─────────────────────────────────────────────
                               2 * N_train

   Threshold = Noise_Floor + Offset_dB
   Neu Cong_suat(CUT) > Threshold ===► PHAT HIEN VAT THE HOP LE!

   Cong thuc tinh van toc tu do dich tan Doppler:

                lambda * f_doppler
   Velocity v = ──────────────────
                        2
"""

from typing import Tuple, List
import numpy as np


class DopplerCFARDetector:
    """
    Bo xu ly bien doi Doppler-FFT va bo do thich nghi CA-CFAR 1D cho Radar 77GHz.
    """
    def __init__(self, f_carrier: float = 77e9, t_rep: float = 60e-6, num_chirps: int = 64):
        self.c = 3e8
        self.fc = float(f_carrier)
        self.wavelength = self.c / self.fc  # lambda ~ 3.90 mm tai 77 GHz
        self.t_rep = float(t_rep)
        self.num_chirps = int(num_chirps)

        # Van toc toi da khong nhap nhang va do phan giai van toc
        self.v_max = self.wavelength / (4.0 * self.t_rep)
        self.v_res = self.wavelength / (2.0 * self.num_chirps * self.t_rep)

        # Truc van toc Doppler
        doppler_freqs = np.fft.fftshift(np.fft.fftfreq(self.num_chirps, d=self.t_rep))
        self.velocity_axis = (self.wavelength * doppler_freqs) / 2.0

    def compute_doppler_spectrum(self, slow_time_samples: np.ndarray) -> np.ndarray:
        """
        slow_time_samples: Mang 1D gom M gia tri phuc tai 1 Range Bin qua M chirps
        Tra ve: Pho Doppler cong suat (dB) sau khi dich goc 0 ve trung tam (fftshift)
        """
        samples = np.asarray(slow_time_samples, dtype=np.complex64)
        window = np.hanning(len(samples))
        windowed = samples * window
        fft_out = np.fft.fftshift(np.fft.fft(windowed, n=self.num_chirps))
        power_db = 20.0 * np.log10(np.abs(fft_out) + 1e-12)
        return power_db

    def ca_cfar_1d(
        self,
        power_db: np.ndarray,
        num_train: int = 8,
        num_guard: int = 2,
        threshold_offset_db: float = 10.0
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Bo do thich nghi CA-CFAR 1D:
        - num_train: So o huan luyen moi ben (Training Cells)
        - num_guard: So o bao ve moi ben (Guard Cells)
        - threshold_offset_db: Do lech nang nguong tren muc nhieu nen
        Tra ve: (threshold_profile, detected_indices)
        """
        n = len(power_db)
        threshold_profile = np.zeros(n, dtype=np.float32)
        detections = []

        window_size = num_train + num_guard

        for i in range(window_size, n - window_size):
            # Lay cac o huan luyen 2 ben (bo qua cac o bao ve)
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

    # Gia lap 2 xe di chuyen:
    # Xe 1: Tien lai gan voi van toc -8.0 m/s (-28.8 km/h)
    # Xe 2: Di cung chieu vuot len voi van toc +6.5 m/s (+23.4 km/h)
    target_velocities = [-8.0, 6.5]
    slow_time = np.arange(cfar.num_chirps) * cfar.t_rep

    combined_signal = np.zeros(cfar.num_chirps, dtype=np.complex64)
    for v in target_velocities:
        f_doppler = (2.0 * v) / cfar.wavelength
        combined_signal += np.exp(1j * 2.0 * np.pi * f_doppler * slow_time)

    # Gia lap nhieu nen Clutter
    np.random.seed(123)
    noise = 0.3 * (np.random.randn(cfar.num_chirps) + 1j * np.random.randn(cfar.num_chirps))
    combined_signal += noise

    # Thuc hien Doppler-FFT
    power_db = cfar.compute_doppler_spectrum(combined_signal)

    # Chay thuat toan CA-CFAR thich nghi
    thresh_line, detected_bins = cfar.ca_cfar_1d(power_db, num_train=6, num_guard=2, threshold_offset_db=8.0)

    print("2. KET QUA PHAT HIEN VAN TOC XE BANG DOPPLER-FFT & CA-CFAR:")
    for v_true in target_velocities:
        closest_bin = min(detected_bins, key=lambda b: abs(cfar.velocity_axis[b] - v_true))
        v_est = float(cfar.velocity_axis[closest_bin])
        err = abs(v_est - v_true)
        print(f"   -> Xe thuc te: {v_true:6.1f} m/s ({v_true * 3.6:5.1f} km/h) | CFAR do: {v_est:6.1f} m/s ({v_est * 3.6:5.1f} km/h) | Sai so: {err:.2f} m/s")
        assert err < cfar.v_res, "Sai so van toc vuot qua do phan giai Doppler-FFT!"

    print("\n[THANH CONG] DOPPLER-FFT VA CA-CFAR LOC SACH NHIEU CLUTTER VA DO CHINH XAC VAN TOC XE!")
