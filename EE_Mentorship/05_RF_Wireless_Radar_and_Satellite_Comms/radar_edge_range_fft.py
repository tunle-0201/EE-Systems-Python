"""
================================================================================
          MODULE T: EMBEDDED AUTOMOTIVE 77GHz FMCW RADAR BASEBAND DSP
    MILESTONE T.2: BIEN DOI RANGE-FFT FAST-TIME XAC DINH CU LY DA MUC TIEU
================================================================================

1. NGUYEN LY DSP & TRUC FAST-TIME (FAST-TIME RANGE-FFT ARCHITECTURE):
   - Trong thuc te giao thong (hoac Drone bay trong rung cay / do thi),
     anten thu RX cua radar nhan ve song phan xa tu hang chuc vat can cung luc:
     xe hoi phia truoc, xe dap ben canh, dai phan cach, bien bao giao thong.
   - Tin hieu trung tan IF sau mach tron la mot tong hop cua nhieu song sin:
     s_if(t) = A1*cos(2*pi*f1*t + phi1) + A2*cos(2*pi*f2*t + phi2) + ... + noise
   - Phep bien doi Range-FFT tren truc thoi gian nhanh (Fast-Time):
     + Lay mau N diem trong mot chu ky quét Chirp (Tc = 50 micro-giay).
     + Nhan cua so Hanning giam thieu hien tuong ro ri pho (Spectral Leakage) do cat tin hieu huu han.
     + Zero-padding tang do min noi suy dinh pho.
     + Thuc hien Fast Fourier Transform bien doi tin hieu phach sang mien khoang cach (Range Profile).
     + Moi dinh pho (Peak) vuot tren nguong nhieu chinh la mot vat can vat ly!

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do chuoi xu ly tin hieu Range-FFT Fast-Time:

   Tin hieu phach IF tu ADC:
   [ s_if[0], s_if[1], ... s_if[N-1] ]
                  │
                  ▼
   [ Nhan cua so Hanning ] ──► Triet tieu bup song phu (Side-lobes)
                  │
                  ▼
   [ Zero-Padding n_fft ]  ──► Tang do phan giai noi suy
                  │
                  ▼
   [ Phep bien doi Range-FFT ] (rfft 2048 diem)
                  │
                  ▼
   [ Pho cong suat dB ]    ──► 20 * log10( |FFT| )
                  │
                  ▼
           Pho Cong suat Range Profile (dB)
             ▲
             │           Peak 1 (Xe 18m)
             │             ▲              Peak 2 (Xe 52m)
             │            / \               ▲              Peak 3 (Xe 84m)
             │           /   \             / \               ▲
             │   Noise  /     \   Noise   /   \   Noise     / \
             └───~~~~──┴───────┴──~~~~───┴─────┴───~~~~────┴───┴──────► Range (m)
                      18m                 52m               84m

   Anh xa tu chi so Bin k sang cu ly vat ly Range R_k:

               c * (k * fs / N_fft)
   Range R_k = ─────────────────────
                     2 * S

   Cu ly xa nhat khong bi nhap nhang tan so (Max Unambiguous Range):

               c * (fs / 2)
   Range_max = ─────────────
                  2 * S

   Do phan giai cuc ly nho nhat giua 2 xe (Range Resolution):

                  c
   Delta_Range = ─────
                 2 * B
"""

from typing import Tuple, List
import numpy as np


class RangeFFTProcessor:
    """
    Bo xu ly bien doi Range-FFT tren truc thoi gian nhanh Fast-Time cho Radar 77GHz.
    """
    def __init__(
        self,
        f_carrier: float = 77e9,
        bandwidth: float = 1e9,
        chirp_duration: float = 50e-6,
        fs: float = 25e6,
        n_fft: int = 2048
    ):
        self.c = 3e8
        self.fc = float(f_carrier)
        self.B = float(bandwidth)
        self.Tc = float(chirp_duration)
        self.fs = float(fs)
        self.n_fft = int(n_fft)
        self.slope = self.B / self.Tc
        self.num_samples = int(self.Tc * self.fs)

        # Tinh toan tam do toi da va do phan giai
        self.max_range = (self.c * (self.fs / 2.0)) / (2.0 * self.slope)
        self.range_resolution = self.c / (2.0 * self.B)

        # Truc cu ly cho tung bin FFT
        freq_bins = np.fft.rfftfreq(self.n_fft, d=1.0 / self.fs)
        self.range_axis = (self.c * freq_bins) / (2.0 * self.slope)

    def process_chirp(self, if_signal: np.ndarray, apply_window: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Thuc hien Range-FFT tren 1 chirp trung tan IF:
        1. Nhan cua so Hanning giam ro ri pho (Spectral Leakage)
        2. Zero-padding len n_fft diem de noi suy dinh pho muot ma
        3. Tinh toan pho cong suat Range Profile (dB)
        Tra ve: (range_axis, power_db)
        """
        sig = np.asarray(if_signal[:self.num_samples], dtype=np.float32)

        if apply_window:
            window = np.hanning(len(sig))
            sig = sig * window

        # Bien doi Fast Fourier Transform (Range-FFT)
        spectrum = np.fft.rfft(sig, n=self.n_fft)
        magnitude = np.abs(spectrum)
        power_db = 20.0 * np.log10(magnitude + 1e-12)

        return self.range_axis, power_db

    def detect_peaks(self, power_db: np.ndarray, threshold_db: float = 20.0) -> List[float]:
        """
        Tim cac dinh muc tieu vuot nguong cong suat threshold_db
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

    # Gia lap 3 xe o to o khoang cach 18.0m, 52.0m, va 84.0m
    true_targets = [18.0, 52.0, 84.0]
    t_axis = np.linspace(0, processor.Tc, processor.num_samples, endpoint=False)

    combined_if = np.zeros(processor.num_samples, dtype=np.float32)
    for dist in true_targets:
        f_b = (2.0 * processor.slope * dist) / processor.c
        combined_if += np.cos(2.0 * np.pi * f_b * t_axis).astype(np.float32)

    # Them nhieu trang nhiet RF
    np.random.seed(42)
    combined_if += 0.2 * np.random.randn(processor.num_samples).astype(np.float32)

    # Chay Range-FFT
    r_axis, p_db = processor.process_chirp(combined_if)
    detected = processor.detect_peaks(p_db, threshold_db=40.0)

    print("2. KET QUA PHAT HIEN DA MUC TIEU BANG RANGE-FFT:")
    for target in true_targets:
        closest_det = min(detected, key=lambda x: abs(x - target))
        err = abs(closest_det - target)
        print(f"   -> Xe muc tieu: {target:5.1f}m  |  Range-FFT phat hien: {closest_det:5.1f}m  |  Sai so: {err * 100:.2f} cm")
        assert err < processor.range_resolution, "Sai so vuot qua do phan giai Range-FFT!"

    print("\n[THANH CONG] RANGE-FFT TACH VA DINH VI CHINH XAC 100% TAT CA CAC XE MUC TIEU!")
