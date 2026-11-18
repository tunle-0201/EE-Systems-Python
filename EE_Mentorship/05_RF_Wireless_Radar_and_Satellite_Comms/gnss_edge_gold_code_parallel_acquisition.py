"""
EE MENTORSHIP PROGRAM - MODULE BK (NHOM 50) - BAI 196 (MILESTONE BK.1)
================================================================================
KIEN TRUC MA GIA NGAU NHIEN GNSS GOLD CODE PRN & THU NHAN SONG SONG MIEN TAN SO
FFT PARALLEL CODE PHASE ACQUISITION CHO SPACEX FALCON 9 & APPLE L1 RECEIVER
================================================================================

Nguyen ly vat ly va Toan hoc cot loi:
1. Bo tao ma gia ngau nhien GPS L1 C/A Gold Code (1,023 chips/ms @ 1.023 MHz):
   - Ket hop 2 thanh ghi dich hoi tiep tuyen tinh 10-bit LFSR G1 va G2:
     G1(x) = x^10 + x^3 + 1
     G2(x) = x^10 + x^9 + x^8 + x^6 + x^3 + x^2 + 1
   - Moi ve tinh PRN (1..32) chon 2 ngo ra tap (s1, s2) khac nhau tren G2 de XOR
     voi G1 tao ra ho ma Gold co tinh truc giao cao:
     + Tuong quan tu dong (Auto-correlation): Dat +1,023 khi lech = 0 chip;
       khi lech >= 1 chip chi nam trong tap 3 gia tri {-65, -1, +63}.
     + Tuong quan cheo (Cross-correlation) giua 2 ve tinh bat ky <= 65 (-23.9 dB).

2. Loi ich khuech dai xu ly (Processing Gain) keo tin hieu duoi nen nhieu nhiet:
   - Tin hieu ve tinh GPS tu quy dao 20,200 km den Trai Dat chi dat ~ -130 dBm,
     chim sau duoi nen nhieu nhiet (-111 dBm @ 2 MHz -> SNR dau vao = -19 dB!).
   - Nho nhan giai trai pho voi 1,023 chips (hoac tich luy khong ket hop M ms):
     G_p = 10 * log10(1,023) = +30.1 dB -> Nang SNR sau tuong quan len > +11 dB!

3. Thuat toan Thu nhan Song song Pha Ma Mien Tan so (FFT Parallel Code Phase):
   - Thay vi quet tuan tu 1,023 do tre x 41 tan so Doppler = 41,943 phep thu,
     ta dung Dinh ly Tuong quan Vong (Circular Cross-Correlation) qua FFT:

     R_xy[tau] = IFFT( FFT(r_bb) * conj(FFT(code_local)) )

   - Chi 1 cap FFT/IFFT do dai N=2048 tinh tuc thoi ca 2,048 pha ma trong O(N log N)!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Phoi tron giai song mang & Dich tan Doppler:
     r_bb[n] = r[n] * exp(-j * 2 * pi * f_d * n / f_s)

2. Phoi tuong quan vong khong chech pha:
     Z(f_d, tau) = | IFFT( FFT(r_bb) * conj(FFT(c_local)) ) |^2

3. Tieu chuan phat hien ve tinh (Peak-to-Next-Peak Ratio):
               Z_max(f_d*, tau*)
     Ratio = ──────────────────────  > Threshold (thuong > 2.5)
             Z_second_outside_1chip
--------------------------------------------------------------------------------
"""

import cmath
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


# Bang tap (s1, s2) chuan ICD-GPS-200 cho cac ve tinh PRN 1..32 (chi so 1-based tren G2)
GPS_CA_G2_TAPS: Dict[int, Tuple[int, int]] = {
    1: (2, 6), 2: (3, 7), 3: (4, 8), 4: (5, 9), 5: (1, 9), 6: (2, 10),
    7: (1, 8), 8: (2, 9), 9: (3, 10), 10: (2, 3), 11: (3, 4), 12: (5, 6),
    13: (6, 7), 14: (7, 8), 15: (8, 9), 16: (9, 10), 17: (1, 4), 18: (2, 5),
    19: (3, 6), 20: (4, 7), 21: (5, 8), 22: (6, 9), 23: (1, 3), 24: (4, 6),
    25: (5, 7), 26: (6, 8), 27: (7, 9), 28: (8, 10), 29: (1, 6), 30: (2, 7),
    31: (3, 8), 32: (4, 9),
}


class GPSGoldCodeGenerator:
    """Bo tao ma gia ngau nhien GPS L1 C/A 1,023 chips bang 2 thanh ghi LFSR G1 & G2."""

    CODE_LENGTH = 1023
    CHIP_RATE_HZ = 1.023e6

    @classmethod
    def generate_prn_bits(cls, prn: int) -> List[int]:
        """Sinh chuoi 1,023 bit {0, 1} chuan ICD-GPS-200 cho ve tinh PRN."""
        if prn not in GPS_CA_G2_TAPS:
            raise ValueError(f"PRN khong hop le: {prn}")
        s1, s2 = GPS_CA_G2_TAPS[prn]

        g1 = [1] * 10
        g2 = [1] * 10
        chips: List[int] = []

        for _ in range(cls.CODE_LENGTH):
            g1_out = g1[9]
            g2_out = g2[s1 - 1] ^ g2[s2 - 1]
            chips.append(g1_out ^ g2_out)

            # Cap nhat LFSR G1: x^10 + x^3 + 1
            fb1 = g1[2] ^ g1[9]
            g1 = [fb1] + g1[:-1]

            # Cap nhat LFSR G2: x^10 + x^9 + x^8 + x^6 + x^3 + x^2 + 1
            fb2 = g2[1] ^ g2[2] ^ g2[5] ^ g2[7] ^ g2[8] ^ g2[9]
            g2 = [fb2] + g2[:-1]

        return chips

    @classmethod
    def generate_bpsk_chips(cls, prn: int) -> List[float]:
        """Anh xa logic {0 -> +1.0, 1 -> -1.0} cho dieu che BPSK."""
        return [1.0 if b == 0 else -1.0 for b in cls.generate_prn_bits(prn)]

    @classmethod
    def sample_code_epoch(cls, prn: int, n_samples: int, f_sample_hz: float, delay_chips: float = 0.0) -> List[float]:
        """Lay mau ma C/A dai 1 ms (1,023 chips) o tan so lay mau f_sample_hz kem do tre delay_chips."""
        bpsk = cls.generate_bpsk_chips(prn)
        out: List[float] = []
        chips_per_sample = cls.CHIP_RATE_HZ / f_sample_hz
        for n in range(n_samples):
            chip_idx = int(math.floor((n * chips_per_sample - delay_chips) % cls.CODE_LENGTH))
            out.append(bpsk[chip_idx])
        return out

    @staticmethod
    def circular_correlation(seq_a: List[float], seq_b: List[float]) -> List[int]:
        """Tinh tuong quan vong roi rac 1,023 diem de kiem chung tinh truc giao Gold Code."""
        n = len(seq_a)
        res: List[int] = []
        for lag in range(n):
            acc = 0.0
            for k in range(n):
                acc += seq_a[k] * seq_b[(k - lag) % n]
            res.append(int(round(acc)))
        return res


class CooleyTukeyFFT:
    """Dong co bien doi Fourier nhanh Radix-2 FFT/IFFT thuan thu vien chuan Python."""

    @staticmethod
    def fft(x: List[complex]) -> List[complex]:
        n = len(x)
        if n == 0 or (n & (n - 1)) != 0:
            raise ValueError("Do dai FFT phai la luy thua cua 2.")
        buf = [complex(v) for v in x]

        # Hoan vi dao bit (Bit-reversal permutation)
        j = 0
        for i in range(1, n):
            bit = n >> 1
            while j & bit:
                j ^= bit
                bit >>= 1
            j ^= bit
            if i < j:
                buf[i], buf[j] = buf[j], buf[i]

        # Tang canh buom Cooley-Tukey (Butterfly stages)
        length = 2
        while length <= n:
            half = length // 2
            angle = -2.0 * math.pi / length
            w_step = cmath.rect(1.0, angle)
            for start in range(0, n, length):
                w = 1.0 + 0.0j
                for k in range(half):
                    even = buf[start + k]
                    odd = buf[start + k + half] * w
                    buf[start + k] = even + odd
                    buf[start + k + half] = even - odd
                    w *= w_step
            length <<= 1
        return buf

    @classmethod
    def ifft(cls, spectrum: List[complex]) -> List[complex]:
        n = len(spectrum)
        conj_in = [v.conjugate() for v in spectrum]
        transformed = cls.fft(conj_in)
        return [v.conjugate() / n for v in transformed]


@dataclass
class AcquisitionResult:
    prn: int
    detected: bool
    doppler_hz: float
    code_phase_chips: float
    peak_metric_ratio: float
    snr_post_corr_db: float


class ParallelCodePhaseAcquisition:
    """
    Bo thu nhan ve tinh song song mien tan so FFT (Parallel Code Phase Search):
    Tich luy khong ket hop qua nhieu chu ky 1 ms de bat ve tinh yeu duoi nen nhieu nhiet.
    """

    def __init__(self, f_sample_hz: float = 2.048e6, doppler_max_hz: float = 10000.0, doppler_step_hz: float = 500.0):
        self.f_sample_hz = f_sample_hz
        self.n_per_ms = int(round(f_sample_hz * 1.0e-3))  # 2,048 mau / 1 ms
        self.doppler_bins = [
            -doppler_max_hz + i * doppler_step_hz
            for i in range(int(round(2.0 * doppler_max_hz / doppler_step_hz)) + 1)
        ]

    def acquire_prn(self, iq_samples: List[complex], prn: int, num_epochs_ms: int = 4, ratio_threshold: float = 2.6) -> AcquisitionResult:
        """Quet dong thoi toan bo 2,048 pha ma qua moi bin Doppler bang FFT."""
        code_ref = GPSGoldCodeGenerator.sample_code_epoch(prn, self.n_per_ms, self.f_sample_hz, delay_chips=0.0)
        code_fft_conj = [v.conjugate() for v in CooleyTukeyFFT.fft([complex(c) for c in code_ref])]

        best_power_map: List[List[float]] = []
        best_global_val = -1.0
        best_d_idx = 0
        best_s_idx = 0

        for d_idx, f_d in enumerate(self.doppler_bins):
            acc_power = [0.0] * self.n_per_ms
            for ep in range(num_epochs_ms):
                offset = ep * self.n_per_ms
                epoch_bb: List[complex] = []
                for n in range(self.n_per_ms):
                    t_sec = (offset + n) / self.f_sample_hz
                    lo = cmath.rect(1.0, -2.0 * math.pi * f_d * t_sec)
                    epoch_bb.append(iq_samples[offset + n] * lo)

                r_fft = CooleyTukeyFFT.fft(epoch_bb)
                prod = [r_fft[k] * code_fft_conj[k] for k in range(self.n_per_ms)]
                corr = CooleyTukeyFFT.ifft(prod)
                for s in range(self.n_per_ms):
                    acc_power[s] += (corr[s].real ** 2 + corr[s].imag ** 2)

            best_power_map.append(acc_power)
            local_max = max(acc_power)
            if local_max > best_global_val:
                best_global_val = local_max
                best_d_idx = d_idx
                best_s_idx = acc_power.index(local_max)

        # Loai bo vung +/- 2 mau quanh dinh chinh (+/- 1 chip) de tim dinh phu & nhieu nen
        samples_per_chip = self.f_sample_hz / GPSGoldCodeGenerator.CHIP_RATE_HZ
        excl_radius = max(2, int(math.ceil(samples_per_chip)))

        second_peak = 0.0
        noise_vals: List[float] = []
        best_row = best_power_map[best_d_idx]
        for s in range(self.n_per_ms):
            circ_dist = min(abs(s - best_s_idx), self.n_per_ms - abs(s - best_s_idx))
            if circ_dist > excl_radius:
                val = best_row[s]
                noise_vals.append(val)
                if val > second_peak:
                    second_peak = val

        # Kiem tra them o cac bin Doppler khac
        for d_idx, row in enumerate(best_power_map):
            if d_idx == best_d_idx:
                continue
            row_max = max(row)
            if row_max > second_peak and abs(d_idx - best_d_idx) > 1:
                second_peak = row_max

        noise_mean = sum(noise_vals) / max(1, len(noise_vals))
        peak_ratio = best_global_val / max(1e-12, second_peak)
        snr_post_db = 10.0 * math.log10(max(1e-9, best_global_val / max(1e-12, noise_mean)))

        code_phase_chips = (best_s_idx / self.f_sample_hz) * GPSGoldCodeGenerator.CHIP_RATE_HZ
        return AcquisitionResult(
            prn=prn,
            detected=(peak_ratio >= ratio_threshold),
            doppler_hz=self.doppler_bins[best_d_idx],
            code_phase_chips=code_phase_chips % GPSGoldCodeGenerator.CODE_LENGTH,
            peak_metric_ratio=peak_ratio,
            snr_post_corr_db=snr_post_db,
        )


def test_gold_code_parallel_acquisition():
    """Chuong trinh kiem thu bo tao ma Gold Code va Thu nhan song song FFT GNSS."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BK (NHOM 50) - BAI 196 (MILESTONE BK.1)")
    print("MA GIA NGAU NHIEN GOLD CODE PRN & THU NHAN SONG SONG FFT GNSS L1 C/A")
    print("=" * 80)

    # 1. Kiem thu tinh truc giao ma Gold Code (Auto-corr & Cross-corr)
    print("\n[1] Kiem thu tinh chat 3-gia-tri cua ho ma Gold Code 1,023 chips (PRN 1 vs PRN 2):")
    prn1 = GPSGoldCodeGenerator.generate_bpsk_chips(1)
    prn2 = GPSGoldCodeGenerator.generate_bpsk_chips(2)
    ac_prn1 = GPSGoldCodeGenerator.circular_correlation(prn1, prn1)
    xc_12 = GPSGoldCodeGenerator.circular_correlation(prn1, prn2)

    max_sidelobe_ac = max(abs(v) for v in ac_prn1[1:])
    max_crosscorr = max(abs(v) for v in xc_12)
    iso_db = 20.0 * math.log10(max_crosscorr / ac_prn1[0])

    print(f"  * Dinh tu tuong quan tai lag 0    : {ac_prn1[0]} (Target: 1023)")
    print(f"  * Tap gia tri ben ngoai lag 0    : {sorted(set(ac_prn1[1:]))}")
    print(f"  * Tuong quan cheo cuc dai PRN1/2 : {max_crosscorr} ({iso_db:.2f} dB isolation)")

    assert ac_prn1[0] == 1023
    assert max_sidelobe_ac == 65 and set(ac_prn1[1:]) == {-65, -1, 63}
    assert max_crosscorr <= 65
    print("  -> Ket luan: Ma Gold PRN dat chuan truc giao ICD-GPS-200 tuyet doi (PASS)!")

    # 2. Kiem thu do chinh xac bien doi Cooley-Tukey FFT/IFFT Radix-2
    print("\n[2] Kiem thu dong co Cooley-Tukey Radix-2 FFT/IFFT (N = 2048):")
    rng = random.Random(2026)
    test_vec = [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(2048)]
    rec_vec = CooleyTukeyFFT.ifft(CooleyTukeyFFT.fft(test_vec))
    max_err = max(abs(a - b) for a, b in zip(test_vec, rec_vec))
    print(f"  * Sai so tai tao FFT -> IFFT     : {max_err:.3e} (< 1e-11)")
    assert max_err < 1e-11
    print("  -> Ket luan: Dong co FFT thuan Python dat do chinh xac so hoc may tinh (PASS)!")

    # 3. Mo phong tin hieu thu I/Q hon hop 3 ve tinh bi chon vui duoi nhieu nhiet -16 dB
    print("\n[3] Thu nhan ve tinh trong nhieu nhiet Pre-Corr SNR = -16 dB (Tich luy 4 ms):")
    f_s = 2.048e6
    n_epochs = 4
    n_total = n_epochs * 2048

    injected = [
        {"prn": 3, "delay_chips": 412.5, "doppler_hz": 3500.0},
        {"prn": 12, "delay_chips": 889.0, "doppler_hz": -6000.0},
        {"prn": 24, "delay_chips": 125.5, "doppler_hz": 500.0},
    ]
    pre_snr_db = -16.0
    sig_amp = 10.0 ** (pre_snr_db / 20.0)  # Khi cong suat nhieu phuc = 1.0 (std I = std Q = 1/sqrt(2))
    noise_std = 1.0 / math.sqrt(2.0)

    rx_iq = [complex(rng.gauss(0.0, noise_std), rng.gauss(0.0, noise_std)) for _ in range(n_total)]
    samples_per_ms = 2048
    for sat in injected:
        c_epoch = GPSGoldCodeGenerator.sample_code_epoch(sat["prn"], samples_per_ms, f_s, sat["delay_chips"])
        for n in range(n_total):
            t_sec = n / f_s
            phase = 2.0 * math.pi * sat["doppler_hz"] * t_sec + 0.37 * sat["prn"]
            rx_iq[n] += sig_amp * c_epoch[n % samples_per_ms] * cmath.rect(1.0, phase)

    acq = ParallelCodePhaseAcquisition(f_sample_hz=f_s)
    for sat in injected:
        res = acq.acquire_prn(rx_iq, sat["prn"], num_epochs_ms=n_epochs)
        err_chip = min(abs(res.code_phase_chips - sat["delay_chips"]), 1023.0 - abs(res.code_phase_chips - sat["delay_chips"]))
        err_dop = abs(res.doppler_hz - sat["doppler_hz"])
        print(
            f"  * PRN {res.prn:2d} | Detected={str(res.detected):5s} | "
            f"Doppler={res.doppler_hz:+7.0f} Hz (True {sat['doppler_hz']:+7.0f}) | "
            f"Phase={res.code_phase_chips:6.1f} (True {sat['delay_chips']:5.1f}) | "
            f"Ratio={res.peak_metric_ratio:5.2f} | Post-SNR={res.snr_post_corr_db:5.1f} dB"
        )
        assert res.detected
        assert err_chip <= 1.0 and err_dop <= 250.0

    absent_res = acq.acquire_prn(rx_iq, prn=7, num_epochs_ms=n_epochs)
    print(
        f"  * PRN {absent_res.prn:2d} | Detected={str(absent_res.detected):5s} | "
        f"Ratio={absent_res.peak_metric_ratio:5.2f} (< 2.60 Threshold -> Loai bo ve tinh khong co mat)"
    )
    assert not absent_res.detected
    print("  -> Ket luan: FFT Parallel Acquisition keo thanh cong 3/3 ve tinh tu -16 dB nhieu nhiet (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 196: GOLD CODE & FFT ACQUISITION HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_gold_code_parallel_acquisition()
