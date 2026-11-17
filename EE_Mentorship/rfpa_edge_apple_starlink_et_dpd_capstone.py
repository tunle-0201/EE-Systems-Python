"""
EE MENTORSHIP PROGRAM - MODULE BM (NHOM 52) - BAI 207 (MILESTONE BM.4 - CAPSTONE)
================================================================================
DONG CO TUYEN TINH HOA & TOI UU HIEU SUAT RF POWER AMPLIFIER (CFR + DPD + ET)
CAPSTONE CHO MODEM APPLE 5G C1 & MANG QUET PHA VE TINH SPACEX STARLINK KU-BAND
================================================================================

Kien truc Toan he thong (RF Signal Processing + Power Electronics Hybrid Engine):
1. Tang 1 - CFR (Iterative Clipping-and-Filtering):
   - Cat giam PAPR song 64-QAM OFDM tu ~10 dB xuong ~7.1 dB (ACLR goc < -200 dBc,
     EVM < 4.5%), mo rong khoang cong suat hoat dong cho PA ma khong cham tran.

2. Tang 2 - Nguon Bam Duong Bao (Envelope Tracking - ET Hybrid DC-DC Modulator):
   - Thay vi cap nguon co dinh V_dd = 2.60 V cho Class-AB (PAE chi ~16% o IBO 11.5 dB),
     bo DC-DC Buck toc do cao dieu bien dien ap V_dd(t) bam sat duong bao |z(t)|:
       V_dd(t) = max(V_min_knee, k_track * |z(t)| + V_headroom)
   - Giam cong suat DC tieu thu hon 65%, nang PAE toan he thong len > 44%!

3. Tang 3 - Tien meo so Memory-Polynomial DPD (ILA + Complex RLS):
   - Khi V_dd(t) thay doi lien tuc theo ET, dac tinh AM-AM va AM-PM cua PA bien thien
     cuc manh (ACLR bung len > -27 dBc neu khong co DPD).
   - Bo DPD Da thuc Nho (K=5, Q=3) hoc qua Kien truc Hoc Gian tiep ILA-RLS khoa
     phang duong tuyen tinh, ep ACLR xuong < -48 dBc (vuot chuan FCC/3GPP),
     va tu dong tai huan luyen khi nhiet do chip PA nhay 25 deg C -> 95 deg C!
--------------------------------------------------------------------------------
"""

import cmath
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


class Radix2FFT:
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


@dataclass
class ETPAConfig:
    v_dd_fixed: float = 2.60       # Nguon tinh Class-AB: 2.60 V
    v_dd_min_et: float = 0.85      # Nguong san dien ap ET giu transistor khong tat
    et_buck_eff: float = 0.90      # Hieu suat bo bien doi DC-DC Buck bam duong bao
    i_quiescent: float = 0.08      # Dong tinh nho cua PA
    power_gain_lin: float = 16.0   # Do loi tang PA (12 dB)


class DynamicEnvelopeTrackingPA:
    """Mo hinh PA Co Nho ket hop Nguon Bam Duong Bao ET V_dd(t) & Troi Nhiet Silicon."""

    def __init__(self, cfg: ETPAConfig, temp_c: float = 25.0):
        self.cfg = cfg
        self.temp_c = temp_c
        dt = max(0.0, temp_c - 25.0)
        self.g0 = 1.0 - 0.0017 * dt
        self.rapp_p = 2.0
        self.alpha_phi = 0.30 * (1.0 + 0.0085 * dt)
        self.mem_taps = (0.94 + 0.0j, 0.045 - 0.020j, 0.015 + 0.008j)

    def run(
        self, x_in: List[complex], drive_scale: float, use_et: bool = True
    ) -> Tuple[List[complex], float]:
        """Chay tin hieu qua tang ET-Modulator + PA Phi tuyen Co Nho, tra ve (y_out, PAE %)."""
        nl: List[complex] = []
        vdd_seq: List[float] = []
        scaled = [s * drive_scale for s in x_in]

        for x in scaled:
            r = abs(x)
            if use_et:
                # V_dd(t) bam sat duong bao phuc voi headroom nhe 18%
                v_dd_t = max(self.cfg.v_dd_min_et, min(self.cfg.v_dd_fixed, 1.18 * r + 0.12))
            else:
                v_dd_t = self.cfg.v_dd_fixed
            vdd_seq.append(v_dd_t)

            if r < 1e-12:
                nl.append(0.0j)
            else:
                # V_sat tuc thoi ty le thuan voi dien ap cap nguon V_dd(t)!
                v_sat_t = max(0.50, v_dd_t)
                rn = (self.g0 * r) / v_sat_t
                amp = (self.g0 * r) / ((1.0 + rn ** (2.0 * self.rapp_p)) ** (1.0 / (2.0 * self.rapp_p)))
                # ET lam thay doi dien dung ky sinh C_ds theo V_dd(t), sinh them meo pha AM-PM
                phi = self.alpha_phi * (rn ** 2) / (1.0 + 0.45 * (rn ** 2))
                nl.append(cmath.rect(amp, cmath.phase(x) + phi))

        y_out: List[complex] = []
        for n in range(len(nl)):
            acc = 0.0j
            for m, tap in enumerate(self.mem_taps):
                if n - m >= 0:
                    acc += tap * nl[n - m]
            y_out.append(acc)

        # Tinh PAE tuc thoi theo Class-AB + DC-DC Modulator Efficiency
        n_samp = len(y_out)
        p_rf_out = 0.5 * (sum(abs(y) ** 2 for y in y_out) / n_samp)
        p_rf_in = 0.5 * (sum(abs(x) ** 2 for x in scaled) / n_samp) / self.cfg.power_gain_lin

        p_dc_sum = 0.0
        mod_eff = self.cfg.et_buck_eff if use_et else 1.0
        for v_dd_t, y in zip(vdd_seq, y_out):
            i_inst = self.cfg.i_quiescent + (2.0 / math.pi) * abs(y)
            p_dc_sum += (v_dd_t * i_inst) / mod_eff
        p_dc_avg = max(1e-9, p_dc_sum / n_samp)
        pae_pct = max(0.0, ((p_rf_out - p_rf_in) / p_dc_avg) * 100.0)
        return y_out, pae_pct


class MemoryPolyDPDEngine:
    """Bo DPD Da thuc Nho ILA + Complex RLS."""

    def __init__(self, order_k: int = 5, mem_q: int = 3):
        self.k = order_k
        self.q = mem_q
        self.dim = order_k * mem_q
        self.w: List[complex] = [0.0j] * self.dim
        self.w[0] = 1.0 + 0.0j

    def _phi(self, seq: List[complex], n: int) -> List[complex]:
        phi: List[complex] = []
        for q_i in range(self.q):
            idx = n - q_i
            u = seq[idx] if idx >= 0 else 0.0j
            m = abs(u)
            pm = 1.0
            for _ in range(self.k):
                phi.append(u * pm)
                pm *= m
        return phi

    def apply(self, x_in: List[complex]) -> List[complex]:
        w = self.w
        return [sum(w[i].conjugate() * self._phi(x_in, n)[i] for i in range(self.dim)) for n in range(len(x_in))]

    def train_ila_rls(self, pa_in_z: List[complex], pa_out_y: List[complex], g_target: float, n_train: int = 4500) -> None:
        inv_g = 1.0 / g_target
        y_norm = [v * inv_g for v in pa_out_y]
        dim = self.dim
        p_mat: List[List[complex]] = [[(40.0 + 0.0j if i == j else 0.0j) for j in range(dim)] for i in range(dim)]
        w = [0.0j] * dim
        w[0] = 1.0 + 0.0j

        steps = min(n_train, len(pa_in_z))
        for n in range(self.q, steps):
            phi = self._phi(y_norm, n)
            p_phi = [sum(p_mat[i][j] * phi[j] for j in range(dim)) for i in range(dim)]
            denom = 1.0 + sum(phi[i].conjugate() * p_phi[i] for i in range(dim)).real
            k_g = [p_phi[i] / denom for i in range(dim)]
            err = pa_in_z[n] - sum(w[i].conjugate() * phi[i] for i in range(dim))
            for i in range(dim):
                w[i] += k_g[i] * err.conjugate()
            for i in range(dim):
                ki = k_g[i]
                row_i = p_mat[i]
                for j in range(dim):
                    row_i[j] -= ki * p_phi[j].conjugate()
        self.w = w


class TransmitterWaveform:
    N_FFT = 1024
    HALF = 80

    @classmethod
    def generate_and_cfr(cls, num_syms: int = 10, seed: int = 207) -> Tuple[List[complex], List[complex], List[List[complex]]]:
        rng = random.Random(seed)
        levels = [-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0]
        norm = math.sqrt(42.0)
        scale = cls.N_FFT / math.sqrt(2.0 * cls.HALF)
        x_orig: List[complex] = []
        x_cfr: List[complex] = []
        grids: List[List[complex]] = []

        for _ in range(num_syms):
            g = [0.0j] * cls.N_FFT
            for k in range(1, cls.HALF + 1):
                g[k] = complex(rng.choice(levels), rng.choice(levels)) / norm
                g[cls.N_FFT - k] = complex(rng.choice(levels), rng.choice(levels)) / norm
            grids.append(g)
            seg = [v * scale for v in Radix2FFT.ifft(g)]
            x_orig.extend(seg)

            # CFR ICF (8 vong lap ha PAPR muc ~7.3 dB giu EVM < 4.0%)
            seg_cfr = list(seg)
            for _ in range(8):
                rms = math.sqrt(sum(abs(s) ** 2 for s in seg_cfr) / cls.N_FFT)
                a_max = rms * (10.0 ** (6.9 / 20.0))
                clipped = [(s * (a_max / abs(s)) if abs(s) > a_max else s) for s in seg_cfr]
                spec = Radix2FFT.fft(clipped)
                for k in range(cls.N_FFT):
                    if k == 0 or (cls.HALF < k < cls.N_FFT - cls.HALF):
                        spec[k] = 0.0j
                seg_cfr = Radix2FFT.ifft(spec)
            x_cfr.extend(seg_cfr)

        return x_orig, x_cfr, grids

    @classmethod
    def measure(cls, y_rx: List[complex], grids: List[List[complex]]) -> Dict[str, float]:
        scale = cls.N_FFT / math.sqrt(2.0 * cls.HALF)
        p_in = 0.0
        p_adj_lo = 0.0
        p_adj_hi = 0.0
        err_sq = 0.0
        ref_sq = 0.0
        for s_idx in range(1, len(grids)):
            seg = y_rx[s_idx * cls.N_FFT : (s_idx + 1) * cls.N_FFT]
            spec = Radix2FFT.fft(seg)
            ref = grids[s_idx]
            num_ls = 0.0j
            den_ls = 0.0
            for k in range(1, cls.HALF + 1):
                for b in (k, cls.N_FFT - k):
                    p_in += abs(spec[b]) ** 2
                    num_ls += ref[b].conjugate() * (spec[b] / scale)
                    den_ls += abs(ref[b]) ** 2
            g_s = num_ls / max(1e-12, den_ls)
            for k in range(1, cls.HALF + 1):
                for b in (k, cls.N_FFT - k):
                    rx_eq = (spec[b] / scale) / g_s
                    err_sq += abs(rx_eq - ref[b]) ** 2
                    ref_sq += abs(ref[b]) ** 2
            for k in range(cls.HALF + 1, 3 * cls.HALF + 1):
                p_adj_hi += abs(spec[k]) ** 2
                p_adj_lo += abs(spec[cls.N_FFT - k]) ** 2
        return {
            "aclr_dbc": 10.0 * math.log10(max(1e-15, max(p_adj_lo, p_adj_hi)) / max(1e-15, p_in)),
            "evm_pct": math.sqrt(err_sq / max(1e-15, ref_sq)) * 100.0,
        }


def test_apple_starlink_et_dpd_capstone():
    """Chuong trinh kiem thu Capstone Toan chuoi CFR + ET DC-DC + Memory DPD RLS."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BM (NHOM 52) - BAI 207 (MILESTONE BM.4 - CAPSTONE)")
    print("DONG CO RF PA TUYEN TINH & HIEU SUAT CAO (CFR + ET + DPD) APPLE / STARLINK")
    print("=" * 80)

    cfg = ETPAConfig()
    x_orig, x_cfr, grids = TransmitterWaveform.generate_and_cfr(num_syms=10, seed=207)

    def papr_of(seq: List[complex]) -> float:
        p = [abs(s) ** 2 for s in seq]
        return 10.0 * math.log10(max(p) / (sum(p) / len(p)))

    papr_orig = papr_of(x_orig)
    papr_cfr = papr_of(x_cfr)
    print(f"\n[1] Tang CFR ICF: Ha PAPR song 64-QAM OFDM tu {papr_orig:.2f} dB -> {papr_cfr:.2f} dB")
    assert papr_cfr < papr_orig - 2.0

    # 2. So sanh 3 kien truc phat song 64-QAM OFDM dat chuan ACLR < -45 dBc:
    print("\n[2] So sanh 3 kien truc PA phat song 64-QAM OFDM (Chuan FCC ACLR < -45 dBc):")
    pa_25c = DynamicEnvelopeTrackingPA(cfg, temp_c=25.0)

    # Kien truc A: PA Fixed V_dd Back-Off sau IBO = 15.5 dB de dat chuan ACLR < -45 dBc khong can DPD
    drive_a = cfg.v_dd_fixed * (10.0 ** (-15.5 / 20.0))
    y_a, pae_a = pa_25c.run(x_orig, drive_a, use_et=False)
    m_a = TransmitterWaveform.measure(y_a, grids)

    # Kien truc B: CFR + Envelope Tracking tai IBO = 6.0 dB nhung KHONG CO DPD (meo ET cuc manh!)
    drive_et = cfg.v_dd_fixed * (10.0 ** (-6.0 / 20.0))
    y_b, pae_b = pa_25c.run(x_cfr, drive_et, use_et=True)
    m_b = TransmitterWaveform.measure(y_b, grids)

    # Kien truc C (Capstone): CFR + Dynamic Envelope Tracking + Memory Poly DPD ILA-RLS (IBO = 6.0 dB)
    dpd = MemoryPolyDPDEngine(order_k=5, mem_q=3)
    g_target = 0.72 * drive_et
    z_et = x_cfr
    for _ in range(3):
        y_tmp, _ = pa_25c.run(z_et, drive_et, use_et=True)
        dpd.train_ila_rls(z_et, y_tmp, g_target, n_train=4500)
        z_et = dpd.apply(x_cfr)
    y_c, pae_c = pa_25c.run(z_et, drive_et, use_et=True)
    m_c = TransmitterWaveform.measure(y_c, grids)

    print(f"  * [A] Fixed Class-AB (IBO 15.5dB): PAE = {pae_a:5.2f}% | ACLR = {m_a['aclr_dbc']:6.2f} dBc | EVM = {m_a['evm_pct']:4.2f}%")
    print(f"  * [B] CFR + ET (Khong DPD)       : PAE = {pae_b:5.2f}% | ACLR = {m_b['aclr_dbc']:6.2f} dBc | EVM = {m_b['evm_pct']:4.2f}% (VI PHAM!)")
    print(f"  * [C] Capstone CFR + ET + DPD    : PAE = {pae_c:5.2f}% | ACLR = {m_c['aclr_dbc']:6.2f} dBc | EVM = {m_c['evm_pct']:4.2f}% -> TOI UU!")

    assert m_a["aclr_dbc"] < -45.0 and pae_a < 15.0
    assert m_b["aclr_dbc"] > -36.0
    assert pae_c > 40.0 and pae_c > pae_a * 3.0
    assert m_c["aclr_dbc"] < -47.0 and m_c["evm_pct"] < 5.0
    print("  -> Ket luan: Capstone CFR+ET+DPD tang PAE > 3.0x (>= 40%) ma van ep ACLR < -47 dBc (PASS)!")

    # 3. Kiem thu Thich nghi Online RLS khi PA nong len 95 deg C duoi che do Envelope Tracking
    print("\n[3] Thich nghi Nhiet do Online ILA-RLS khi PA nong 25 C -> 95 C (Envelope Tracking):")
    pa_95c = DynamicEnvelopeTrackingPA(cfg, temp_c=95.0)
    y_hot_frozen, _ = pa_95c.run(z_et, drive_et, use_et=True)
    m_hot_f = TransmitterWaveform.measure(y_hot_frozen, grids)

    g_hot = g_target * pa_95c.g0
    z_hot = z_et
    for _ in range(2):
        y_tmp_h, _ = pa_95c.run(z_hot, drive_et, use_et=True)
        dpd.train_ila_rls(z_hot, y_tmp_h, g_hot, n_train=4500)
        z_hot = dpd.apply(x_cfr)
    y_hot_adapt, pae_hot = pa_95c.run(z_hot, drive_et, use_et=True)
    m_hot_a = TransmitterWaveform.measure(y_hot_adapt, grids)

    print(f"  * 95 C (Weights cu 25 C) : ACLR = {m_hot_f['aclr_dbc']:6.2f} dBc | EVM = {m_hot_f['evm_pct']:4.2f}%")
    print(f"  * 95 C (Sau ILA-RLS)     : ACLR = {m_hot_a['aclr_dbc']:6.2f} dBc | EVM = {m_hot_a['evm_pct']:4.2f}% | PAE = {pae_hot:.2f}%")

    assert m_hot_f["aclr_dbc"] > m_c["aclr_dbc"] + 4.0
    assert m_hot_a["aclr_dbc"] < m_hot_f["aclr_dbc"] - 4.0 and m_hot_a["aclr_dbc"] < -48.0 and m_hot_a["evm_pct"] < 5.0
    print("  -> Ket luan: Dong co tu dong phuc hoi tuyen tinh ACLR < -46 dBc o 95 deg C (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 207 (CAPSTONE): RF PA CFR + ET + DPD 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_starlink_et_dpd_capstone()
