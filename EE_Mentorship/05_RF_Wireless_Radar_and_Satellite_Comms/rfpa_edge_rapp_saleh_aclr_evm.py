"""
EE MENTORSHIP PROGRAM - MODULE BM (NHOM 52) - BAI 204 (MILESTONE BM.1)
================================================================================
MO HINH PHI TUYEN KHUCH DAI CONG SUAT CAO TAN RF PA (RAPP AM-AM, SALEH AM-PM)
PHAN TICH PAPR SONG MANG OFDM 64-QAM, BUNG PHO ACLR VA SAI SO EVM
CHO APPLE 5G MODEM & SPACEX STARLINK KU-BAND PHASED ARRAY
================================================================================

Nguyen ly vat ly ban dan RF & Toan hoc cot loi:
1. Nghich ly PAPR va Hieu suat Cong suat them PAE (Power-Added Efficiency):
   - Tin hieu OFDM 64-QAM co hang tram song mang con cong pha ngau nhien nen dinh
     song cao gap 8-11 dB so voi cong suat trung binh (PAPR = 9..11 dB).
   - Neu keo PA chay lui sau IBO = 10 dB (Class AB) de tranh bao hoa phi tuyến:
     PA chi dat PAE < 20% (> 80% dien nang pin iPhone/Ve tinh bien thanh nhiet!).
   - Nguoc lai, day PA chay gan bao hoa (IBO = 1.5 dB) nang PAE > 44%, nhung
     meo phi tuyen sinh song hai bac 3/5 (IMD3, IMD5) lam bung pho lan kenh lan can!

2. Mo hinh Toan hoc PA Phi tuyen co Nho (Rapp AM-AM + Saleh AM-PM + Memory):
   - Bien do (Rapp):
                         G_0 * |x|
     A(|x|) = ───────────────────────────────  (Voi he so tron p = 2.0)
               (1 + (G_0 * |x| / V_sat)^(2p))^(1/(2p))

   - Meo pha (Saleh):
                 alpha_phi * |x|^2
     Phi(|x|) = ───────────────────   (Lich pha nang tai dinh cong suat!)
                 1 + beta_phi * |x|^2

3. Chi tieu Kiem chuan FCC / 3GPP:
   - ACLR (Adjacent Channel Leakage Ratio) = 10*log10(P_adj / P_inband) < -45 dBc.
   - EVM (Error Vector Magnitude %) = sqrt( mean(|S_rx - alpha*S_tx|^2) / mean(|S_tx|^2) ) * 100%.
--------------------------------------------------------------------------------
"""

import cmath
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


class Radix2FFT:
    """Dong co bien doi Fourier nhanh Cooley-Tukey Radix-2 thuan Python."""

    @staticmethod
    def fft(x: List[complex]) -> List[complex]:
        n = len(x)
        buf = [complex(v) for v in x]
        j = 0
        for i in range(1, n):
            bit = n >> 1
            while j & bit:
                j ^= bit
                bit >>= 1
            j ^= bit
            if i < j:
                buf[i], buf[j] = buf[j], buf[i]
        length = 2
        while length <= n:
            half = length >> 1
            w_step = cmath.rect(1.0, -2.0 * math.pi / length)
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
    def ifft(cls, spec: List[complex]) -> List[complex]:
        n = len(spec)
        return [v.conjugate() / n for v in cls.fft([s.conjugate() for s in spec])]


class OFDM64QAMGenerator:
    """Bo phat song da song mang 64-QAM OFDM 4x Oversampled (160 song mang / 1024 FFT)."""

    N_FFT = 1024
    HALF_ACTIVE = 80  # Tong 160 song mang hoat dong [-80..-1, +1..+80]

    @classmethod
    def generate_symbols(cls, num_ofdm_syms: int = 8, seed: int = 204) -> Tuple[List[complex], List[List[complex]]]:
        rng = random.Random(seed)
        levels = [-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0]
        norm_64qam = math.sqrt(42.0)  # Cong suat trung binh chuan hoa = 1.0

        td_stream: List[complex] = []
        freq_frames: List[List[complex]] = []

        for _ in range(num_ofdm_syms):
            grid = [0.0j] * cls.N_FFT
            for k in range(1, cls.HALF_ACTIVE + 1):
                grid[k] = complex(rng.choice(levels), rng.choice(levels)) / norm_64qam
                grid[cls.N_FFT - k] = complex(rng.choice(levels), rng.choice(levels)) / norm_64qam
            freq_frames.append(grid)

            # IFFT & chuan hoa nang luong ve RMS = 1.0 trong mien thoi gian (bu he so 1/N cua IFFT)
            td = Radix2FFT.ifft(grid)
            scale = cls.N_FFT / math.sqrt(2.0 * cls.HALF_ACTIVE)
            td_norm = [v * scale for v in td]
            td_stream.extend(td_norm)

        return td_stream, freq_frames


@dataclass
class RFPAConfig:
    g0: float = 1.0                 # Do loi dien ap chuan hoa
    v_sat: float = 2.60             # Muc bao hoa Rapp V_sat (= V_dd Class AB)
    rapp_p: float = 2.5             # Do cong uon Rapp (Smoothness factor)
    alpha_phi: float = 0.12         # He so meo pha Saleh AM-PM chuan hoa theo V_sat (rad)
    beta_phi: float = 0.65          # He so bao hoa pha Saleh
    memory_taps: Tuple[complex, ...] = (0.98 + 0.0j, 0.015 - 0.006j, 0.005 + 0.002j)
    v_dd_fixed: float = 2.60        # Dien ap nguon co dinh Class-AB bang V_sat (V)
    i_quiescent: float = 0.12       # Dong tinh Class-AB (A)
    power_gain_lin: float = 16.0    # Do loi cong suat tang PA (12 dB)


class NonlinearMemoryRFPA:
    """Bo khuech dai cong suat cao tan co meo bien do (Rapp), pha (Saleh) & hieu ung nho (Memory)."""

    def __init__(self, cfg: RFPAConfig):
        self.cfg = cfg

    def memoryless_transfer(self, x: complex) -> complex:
        r = abs(x)
        if r < 1e-12:
            return 0.0j
        r_norm = (self.cfg.g0 * r) / self.cfg.v_sat
        denom = (1.0 + (r_norm ** (2.0 * self.cfg.rapp_p))) ** (1.0 / (2.0 * self.cfg.rapp_p))
        amp_out = (self.cfg.g0 * r) / denom
        phi_shift = (self.cfg.alpha_phi * (r_norm ** 2)) / (1.0 + self.cfg.beta_phi * (r_norm ** 2))
        return cmath.rect(amp_out, cmath.phase(x) + phi_shift)

    def amplify_and_measure_pae(self, x_in: List[complex], input_scale: float) -> Tuple[List[complex], float]:
        """Khuech dai chuoi mau phuc va tinh Hieu suat PAE (%) theo vat ly Class-AB (gioi han ly thuyet pi/4)."""
        scaled_in = [v * input_scale for v in x_in]
        nl_seq = [self.memoryless_transfer(v) for v in scaled_in]

        y_out: List[complex] = []
        taps = self.cfg.memory_taps
        for n in range(len(nl_seq)):
            acc = 0.0j
            for m, tap in enumerate(taps):
                if n - m >= 0:
                    acc += tap * nl_seq[n - m]
            y_out.append(acc)

        p_rf_out = 0.5 * (sum(abs(v) ** 2 for v in y_out) / len(y_out))
        p_rf_in = 0.5 * (sum(abs(v) ** 2 for v in scaled_in) / len(scaled_in)) / self.cfg.power_gain_lin
        i_dc_avg = self.cfg.i_quiescent + (2.0 / math.pi) * (sum(abs(v) for v in y_out) / len(y_out))
        p_dc = max(1e-9, self.cfg.v_dd_fixed * i_dc_avg)
        pae_pct = max(0.0, ((p_rf_out - p_rf_in) / p_dc) * 100.0)
        return y_out, pae_pct


class RFSpectralAnalyzer:
    """Do pho ACLR (Adjacent Channel Leakage Ratio), PAPR & EVM 64-QAM OFDM."""

    @staticmethod
    def compute_papr_db(samples: List[complex]) -> Tuple[float, float]:
        powers = [abs(s) ** 2 for s in samples]
        mean_p = sum(powers) / len(powers)
        peak_p = max(powers)
        sorted_p = sorted(powers)
        p_999 = sorted_p[int(0.999 * (len(sorted_p) - 1))]
        return 10.0 * math.log10(peak_p / mean_p), 10.0 * math.log10(p_999 / mean_p)

    @staticmethod
    def measure_aclr_and_evm(
        x_tx: List[complex], y_rx: List[complex], freq_frames: List[List[complex]]
    ) -> Dict[str, float]:
        n_fft = OFDM64QAMGenerator.N_FFT
        half = OFDM64QAMGenerator.HALF_ACTIVE
        num_syms = len(freq_frames)

        # Tich luy PSD tren tat ca cac khung FFT de do ACLR chinh xac
        p_inband = 0.0
        p_adj_low = 0.0
        p_adj_high = 0.0

        # Dong bo pha & do loi phuc toi uu (Scalar LS Gain Alignment) cho EVM
        num_ls = sum(x.conjugate() * y for x, y in zip(x_tx, y_rx))
        den_ls = sum(abs(x) ** 2 for x in x_tx)
        g_eq = num_ls / max(1e-12, den_ls)

        err_sq = 0.0
        ref_sq = 0.0
        scale = n_fft / math.sqrt(2.0 * half)

        for sym_idx in range(num_syms):
            seg_y = y_rx[sym_idx * n_fft : (sym_idx + 1) * n_fft]
            spec_y = Radix2FFT.fft(seg_y)

            # Cong suat kenh chinh [-80..-1, +1..+80] va kenh lan can [81..240]
            for k in range(1, half + 1):
                p_inband += (abs(spec_y[k]) ** 2 + abs(spec_y[n_fft - k]) ** 2)
            for k in range(half + 1, 3 * half + 1):
                p_adj_high += abs(spec_y[k]) ** 2
                p_adj_low += abs(spec_y[n_fft - k]) ** 2

            # Tinh EVM tren cac song mang du lieu 64-QAM sau khi bu g_eq
            ref_grid = freq_frames[sym_idx]
            for k in range(1, half + 1):
                for bin_idx in (k, n_fft - k):
                    rx_sym = spec_y[bin_idx] / (scale * g_eq)
                    tx_sym = ref_grid[bin_idx]
                    err_sq += abs(rx_sym - tx_sym) ** 2
                    ref_sq += abs(tx_sym) ** 2

        p_adj_max = max(p_adj_low, p_adj_high)
        aclr_dbc = 10.0 * math.log10(max(1e-15, p_adj_max / max(1e-15, p_inband)))
        evm_pct = math.sqrt(err_sq / max(1e-15, ref_sq)) * 100.0
        return {"aclr_dbc": aclr_dbc, "evm_pct": evm_pct}


def test_rapp_saleh_aclr_evm():
    """Chuong trinh kiem thu mo hinh RF PA phi tuyen, PAPR, ACLR & EVM."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BM (NHOM 52) - BAI 204 (MILESTONE BM.1)")
    print("MO HINH RF PA PHI TUYEN RAPP/SALEH, PAPR 64-QAM OFDM, ACLR & EVM")
    print("=" * 80)

    x_tx, freq_frames = OFDM64QAMGenerator.generate_symbols(num_ofdm_syms=16, seed=204)
    papr_peak_db, papr_01pct_db = RFSpectralAnalyzer.compute_papr_db(x_tx)

    print(f"\n[1] Kiem thu thong ke dinh song 64-QAM OFDM (16 symbols x 1024 FFT):")
    print(f"  * PAPR Cuc dai (Peak/Avg)  : {papr_peak_db:5.2f} dB (>= 8.5 dB)")
    print(f"  * PAPR muc 0.1% CCDF       : {papr_01pct_db:5.2f} dB (>= 7.5 dB)")
    assert papr_peak_db >= 8.5 and papr_01pct_db >= 7.5
    print("  -> Ket luan: Song OFDM 64-QAM co dinh song PAPR rat cao (PASS)!")

    # 2. Quet IBO (Input Back-Off): 11.5 dB (Tuyen tinh nhung PAE thap) -> 1.5 dB (PAE cao nhung bung ACLR)
    print("\n[2] Quet muc kich thich PA tu Back-Off 11.5 dB -> Bao hoa 1.5 dB (P_sat = V_sat):")
    cfg = RFPAConfig()
    pa = NonlinearMemoryRFPA(cfg)

    results = {}
    for ibo_db in (11.5, 5.0, 1.5):
        # Muc RMS chuan theo V_sat / 10^(IBO/20)
        drive_scale = cfg.v_sat * (10.0 ** (-ibo_db / 20.0))
        y_rx, pae_pct = pa.amplify_and_measure_pae(x_tx, drive_scale)
        spec_res = RFSpectralAnalyzer.measure_aclr_and_evm(x_tx, y_rx, freq_frames)
        results[ibo_db] = (pae_pct, spec_res["aclr_dbc"], spec_res["evm_pct"])
        status = "DAT CHUAN FCC" if spec_res["aclr_dbc"] < -45.0 else "VI PHAM MAT NA PHO!"
        print(
            f"  * IBO = {ibo_db:4.1f} dB | PAE = {pae_pct:5.2f}% | "
            f"ACLR = {spec_res['aclr_dbc']:6.2f} dBc | EVM = {spec_res['evm_pct']:5.2f}% -> {status}"
        )

    assert results[11.5][1] < -45.0 and results[11.5][0] < 20.0
    assert results[1.5][0] > 42.0 and results[1.5][1] > -28.0 and results[1.5][2] > 6.0
    print("  -> Ket luan: PA chay gan bao hoa dat PAE > 42% nhung bung ACLR vi pham (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 204: RF PA PHI TUYEN RAPP/SALEH HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_rapp_saleh_aclr_evm()
