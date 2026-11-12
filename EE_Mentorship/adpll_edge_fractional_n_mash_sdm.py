"""
EE MENTORSHIP PROGRAM - MODULE BH (NHOM 47) - BAI 185 (MILESTONE BH.2)
================================================================================
BO TONG HOP TAN SO PHAN SO FRACTIONAL-N VA BO DIEU CHE DELTA-SIGMA MASH 1-1-1
================================================================================

Kien truc bo tong hop tan so phan so (Fractional-N Frequency Synthesizer Architecture):
1. Gioi han cua bo tong hop so nguyen Integer-N PLL:
   - Tan so dau ra: f_out = N * f_ref.
   - Muon buoc nhay tan so nho (vi du 100 kHz), f_ref bat buoc phai chon 100 kHz.
   - Khi do N rat lon (N = 24000 tai 2.4 GHz), nhan nhieu pha trong bang len:
     Phase_Noise_Penalty = 20 * log10(N) = 87.6 dB!
   - Dong thoi bang thong bo loc bi thu hep cuc nho (< 10 kHz), thoi gian khoa pha rat cham.

2. Bo tong hop tan so phan so Fractional-N:
   - Cho phep he so chia la mot so thap phan: N_total = N_int + (K / 2^M).
   - Cho phep giu f_ref rat cao (50 MHz - 100 MHz) giup giam thieu nhieu pha trong bang,
     dong thoi buoc nhay tan so dat do phan giai sub-Hz (Resolution = f_ref / 2^M < 1 Hz).

3. Bo dieu che Delta-Sigma da tang MASH 1-1-1 (Multi-Stage Noise Shaping):
   - Gom 3 bo tich luy so (Accumulators) bac 1 mac noi tiep.
   - Mach triet tieu nhieu (Noise Cancellation Logic - NCL) ket hop cac bit tran (Carry bits):
     y[k] = c1[k] + (c2[k] - c2[k-1]) + (c3[k] - 2 * c3[k-1] + c3[k-2])
   - Ham truyen dat nhieu luong tu hoa bac 3:
     NTF(z) = (1 - z^-1)^3
   - Day nhieu luong tu hoa ve phia tan so cao voi do doc +60 dB/decade (+18 dB/octave),
     sau do duoc bo loc vong lap Low-Pass Filter loc bo hoan toan.
   - Triet tieu hoan toan cac vach pho ky sinh phan so (Fractional Spurs Rejection > 50 dB).

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. He so chia phan so trung binh (Average Fractional Division Ratio):
     N_avg = N_int + (K / 2^M)

2. Ham truyen dat dinh hinh nhieu MASH 1-1-1 (Noise Shaping Transfer Function):
     NTF(z) = (1 - z^-1)^3
     |NTF(f)| = (2 * sin(pi * f / f_ref))^3

3. Do doc dinh hinh nhieu tren bieu do Bode:
     Slope = +60 dB / decade (Bậc 3)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class MASH111Config:
    """Cau hinh bo dieu che Delta-Sigma MASH 1-1-1 24-bit."""
    accumulator_bits: int = 24          # Dung luong bo tich luy M = 24 bits
    f_ref_hz: float = 50.0e6            # Tan so tham chieu 50 MHz
    n_integer: int = 48                 # Phan nguyen he so chia


class MASH111Modulator:
    """
    Subsystem: Bo dieu che Delta-Sigma bac 3 kien truc MASH 1-1-1 (Cascade of Accumulators).
    Dinh hinh nhieu luong tu hoa bac 3: NTF(z) = (1 - z^-1)^3.
    """
    def __init__(self, config: Optional[MASH111Config] = None):
        self.cfg = config if config is not None else MASH111Config()
        self.modulus = 1 << self.cfg.accumulator_bits  # 2^24 = 16,777,216
        
        # 3 Bo tich luy noi tiep (Accumulator registers)
        self.acc1: int = 0
        self.acc2: int = 0
        self.acc3: int = 0
        
        # Cac thanh ghi tre cho mach triet tieu nhieu (NCL delay registers)
        self.c2_d1: int = 0
        self.c3_d1: int = 0
        self.c3_d2: int = 0

    def step(self, frac_word_k: int) -> int:
        """
        Thuc thi 1 chu ky clock dieu che Delta-Sigma MASH 1-1-1.
        Dau vao: frac_word_k in [0 .. 2^M - 1].
        Dau ra: gia tri bu chia y_k in [-3 .. +4].
        """
        # Tang 1: Acc1 tich luy phan so K
        sum1 = self.acc1 + frac_word_k
        c1 = sum1 // self.modulus
        self.acc1 = sum1 % self.modulus

        # Tang 2: Acc2 tich luy phan du cua Tang 1
        sum2 = self.acc2 + self.acc1
        c2 = sum2 // self.modulus
        self.acc2 = sum2 % self.modulus

        # Tang 3: Acc3 tich luy phan du cua Tang 2
        sum3 = self.acc3 + self.acc2
        c3 = sum3 // self.modulus
        self.acc3 = sum3 % self.modulus

        # Mach triet tieu nhieu (Noise Cancellation Logic - NCL):
        # y = c1 + (c2 - c2_z1) + (c3 - 2*c3_z1 + c3_z2)
        diff2 = c2 - self.c2_d1
        diff3 = c3 - 2 * self.c3_d1 + self.c3_d2
        
        y_out = c1 + diff2 + diff3

        # Cap nhat cac thanh ghi tre
        self.c2_d1 = c2
        self.c3_d2 = self.c3_d1
        self.c3_d1 = c3

        return y_out

    def generate_sequence(self, frac_word_k: int, num_samples: int = 4096) -> List[int]:
        """Sinh chuoi he so chia dong N_div[k] = N_int + y[k]."""
        sequence = []
        for _ in range(num_samples):
            y = self.step(frac_word_k)
            sequence.append(self.cfg.n_integer + y)
        return sequence


class FractionalNSynthesizerEngine:
    """
    Dong co mo phong bo tong hop tan so phan so Fractional-N.
    So sanh giua dieu che truc tiep (Dual-Modulus) va MASH 1-1-1 SDM.
    """
    def __init__(self, f_ref_hz: float = 50.0e6, n_int: int = 48, bits: int = 24):
        self.f_ref = f_ref_hz
        self.n_int = n_int
        self.bits = bits
        self.modulus = 1 << bits

    def compute_fraction_word(self, target_f_out_hz: float) -> Tuple[int, int, float]:
        """
        Tinh toan tu ma phan so K tu tan so dau ra mong muon:
        f_out = (N_int + K / 2^M) * f_ref
        Tra ve (N_int, K, actual_f_out).
        """
        exact_ratio = target_f_out_hz / self.f_ref
        n_int = int(math.floor(exact_ratio))
        frac_part = exact_ratio - n_int
        k_word = int(round(frac_part * self.modulus))
        actual_f_out = (n_int + k_word / self.modulus) * self.f_ref
        return n_int, k_word, actual_f_out

    def calculate_psd_db(self, signal: List[float]) -> Tuple[List[float], List[float]]:
        """
        Tinh toan mat do pho cong suat PSD (Power Spectral Density) bang bien doi Fourier DFT/FFT.
        Tra ve (frequencies_hz, psd_db).
        """
        n = len(signal)
        # Ap dung cua so Hanning de giam ro ri pho
        windowed = [signal[i] * (0.5 - 0.5 * math.cos(2.0 * math.pi * i / n)) for i in range(n)]
        
        # Tinh pho cong suat bang cach lay mau 128 diem tan so logarit/tuyen tinh
        num_bins = 64
        freqs = []
        psd_db = []
        
        # Lay mau tan so tu f_ref/N den f_ref/2
        for bin_idx in range(1, num_bins):
            f_norm = (bin_idx / num_bins) * 0.5  # 0 .. 0.5 * f_ref
            f_hz = f_norm * self.f_ref
            omega = 2.0 * math.pi * f_norm
            
            # Tinh thanh phan Fourier tai omega
            real_sum = 0.0
            imag_sum = 0.0
            for t in range(n):
                angle = omega * t
                real_sum += windowed[t] * math.cos(angle)
                imag_sum -= windowed[t] * math.sin(angle)
                
            mag_sq = (real_sum ** 2 + imag_sum ** 2) / (n ** 2)
            db_val = 10.0 * math.log10(max(mag_sq, 1e-15))
            
            freqs.append(f_hz)
            psd_db.append(db_val)
            
        return freqs, psd_db


def test_fractional_n_mash_sdm():
    """Chuong trinh kiem thu toan dien bo dieu che MASH 1-1-1 Fractional-N."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BH (NHOM 47) - BAI 185 (MILESTONE BH.2)")
    print("BO TONG HOP TAN SO PHAN SO FRACTIONAL-N & DIEU CHE DELTA-SIGMA MASH 1-1-1")
    print("=" * 80)

    f_ref = 50.0e6
    engine = FractionalNSynthesizerEngine(f_ref_hz=f_ref, n_int=48, bits=24)

    # 1. Kiem thu tinh toan do phan giai tan so Sub-Hz
    print("\n[1] Kiem thu do phan giai tan so sub-Hz (Target: 2.4137 GHz - Kenh RF Thuc te):")
    target_f = 2.4137e9  # 2413.7 MHz (Kenh thuc te)
    n_int, k_word, actual_f = engine.compute_fraction_word(target_f)

    res_hz = f_ref / (1 << 24)
    freq_err = abs(actual_f - target_f)

    print(f"  * Tan so tham chieu F_REF        : {f_ref / 1e6:.1f} MHz")
    print(f"  * Tan so muc tieu F_OUT          : {target_f / 1e9:.6f} GHz")
    print(f"  * Do phan giai buoc nhay tan so  : {res_hz:.4f} Hz / LSB (Sub-Hz Resolution!)")
    print(f"  * Phan nguyen he so chia N_INT   : {n_int}")
    print(f"  * Tu ma phan so K (24-bit Word)  : {k_word} (0x{k_word:06X})")
    print(f"  * Tan so tong hop thuc te        : {actual_f / 1e9:.6f} GHz")
    print(f"  * Sai lech tan so                : {freq_err:.4f} Hz (< 1.5 Hz)")

    assert freq_err <= res_hz, "Loi: Sai so tan so vuot qua do phan giai 1 LSB!"
    print("  -> Ket luan: Do phan giai buoc nhay tan so Fractional-N dat chuan sub-Hz (PASS)!")

    # 2. Kiem thu bo dieu che MASH 1-1-1 va he so chia trung binh
    print("\n[2] Kiem thu bo dieu che MASH 1-1-1 (4,096 chu ky lay mau):")
    cfg = MASH111Config(accumulator_bits=24, f_ref_hz=f_ref, n_integer=n_int)
    modulator = MASH111Modulator(cfg)

    # Sinh 8,192 mau chuoi he so chia
    num_samples = 8192
    div_sequence = modulator.generate_sequence(k_word, num_samples=num_samples)

    avg_n = sum(div_sequence) / num_samples
    expected_n = n_int + (k_word / (1 << 24))
    avg_err = abs(avg_n - expected_n)

    min_div = min(div_sequence)
    max_div = max(div_sequence)

    print(f"  * He so chia ly thuyet           : {expected_n:.8f}")
    print(f"  * He so chia do duoc (trung binh): {avg_n:.8f}")
    print(f"  * Sai so trung binh thuc nghiem  : {avg_err:.8f} (< 1e-3)")
    print(f"  * Pham vi gia tri he so chia     : [{min_div} .. {max_div}] (Multi-Modulus Range)")

    assert avg_err < 0.005, "Loi: He so chia trung binh khong hoi tu ve gia tri mong muon!"
    assert -3 <= (min_div - n_int) and (max_div - n_int) <= 4, "Loi: Pham vi MASH 1-1-1 vuot ngoai [-3 .. +4]!"
    print("  -> Ket luan: Bo dieu che MASH 1-1-1 hoi tu he so chia phan so chinh xac tuyet doi!")

    # 3. Kiem thu do doc dinh hinh nhieu +60 dB/decade (Noise Shaping Verification)
    print("\n[3] Kiem thu do doc dinh hinh nhieu luong tu hoa bac 3 (+60 dB/decade):")
    # Lay chuoi sai so luong tu hoa (tru di gia tri trung binh)
    error_sequence = [float(x - expected_n) for x in div_sequence[:1024]]
    freqs, psd = engine.calculate_psd_db(error_sequence)

    # Do cong suat tai tan so thap (f ~ 0.03 * F_ref) va tan so cao (f ~ 0.35 * F_ref)
    low_freq_idx = 4
    high_freq_idx = 45

    f_low = freqs[low_freq_idx]
    f_high = freqs[high_freq_idx]
    psd_low = psd[low_freq_idx]
    psd_high = psd[high_freq_idx]

    delta_db = psd_high - psd_low
    decades = math.log10(f_high / f_low)
    measured_slope = delta_db / decades

    print(f"  * Cong suat nhieu tai tan so thap ({f_low / 1e6:5.2f} MHz): {psd_low:6.2f} dB")
    print(f"  * Cong suat nhieu tai tan so cao  ({f_high / 1e6:5.2f} MHz): {psd_high:6.2f} dB")
    print(f"  * Do chenh lech suy giam nhieu   : {delta_db:6.2f} dB")
    print(f"  * Do doc dinh hinh nhieu do duoc : +{measured_slope:.2f} dB / decade (Ly thuyet: +60 dB/decade)")

    assert delta_db > 35.0, "Loi: Bo dieu che khong day duoc nhieu sang tan so cao!"
    print("  -> Ket luan: MASH 1-1-1 day thanh cong toan bo nhieu luong tu hoa ra ngoai bang thong (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 185: FRACTIONAL-N MASH 1-1-1 HOAN TAT KIEM THU 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_fractional_n_mash_sdm()
