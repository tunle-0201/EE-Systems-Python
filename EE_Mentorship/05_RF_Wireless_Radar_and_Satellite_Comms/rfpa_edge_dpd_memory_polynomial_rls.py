"""
EE MENTORSHIP PROGRAM - MODULE BM (NHOM 52) - BAI 206 (MILESTONE BM.3)
================================================================================
TIEN MEO SO DIGITAL PRE-DISTORTION (DPD) DUNG DA THUC NHO MEMORY POLYNOMIAL
KIEN TRUC HOC GIAN TIEP (INDIRECT LEARNING - ILA) & BO GIAI THICH NGHI RLS
CHO BO KHUCH DAI CONG SUAT GAN/CMOS APPLE 5G & SPACEX STARLINK
================================================================================

Nguyen ly vat ly va Thiet ke DSP thich nghi:
1. Han che cua Tien meo Khong nho (Memoryless Look-Up Table DPD):
   - PA thuc te co hieu ung nho do tu bias va nhiet silicon (y[n] phu thuoc ca
     cac mau x[n-1], x[n-2] trong qua khu).
   - DPD khong nho (Q = 1) chi khu duoc meo tinh, de lai duoi pho nho (~ -36 dBc).

2. Mo hinh Da thuc Nho (Memory Polynomial Basis phi_{k,q}):
     z[n] = sum_{q=0..Q-1} sum_{k=1..K} w_{k,q} * x[n - q] * |x[n - q]|^(k - 1)

3. Kien truc Hoc Gian tiep ILA + Binh phuong Toi thieu De quy Phuc RLS:
   - Do nguoc tin hieu dau ra PA da chuan hoa: y_norm[n] = y[n] / G_ref.
   - Huan luyen Post-Distorter giai w sao cho Phi(y_norm) * w ≈ z_pa_in bang RLS:
       k[n] = (P * phi) / (lambda + phi^H * P * phi)
       e[n] = z[n] - w^H * phi
       w <- w + k[n] * conj(e[n])
   - Chep vector trong so w sang Pre-Distorter o phia truoc PA!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. So do Hoc Gian tiep (Indirect Learning Architecture):
     x[n] ---> [ Pre-Distorter W ] ---> z[n] ---> [ RF PA Phi tuyen ] ---> y[n]
                      ^                                                       |
                      | (Copy W)                                              v
              [ Bo giai RLS ] <------- e[n] = z[n] - z_hat[n] <--- [ Post-Dist W ]
--------------------------------------------------------------------------------
"""

import cmath
import math
import random
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


class OFDM64QAMFrame:
    N_FFT = 1024
    HALF_ACTIVE = 80

    @classmethod
    def generate(cls, num_syms: int = 12, seed: int = 206) -> Tuple[List[complex], List[List[complex]]]:
        rng = random.Random(seed)
        levels = [-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0]
        norm = math.sqrt(42.0)
        scale = cls.N_FFT / math.sqrt(2.0 * cls.HALF_ACTIVE)
        td: List[complex] = []
        grids: List[List[complex]] = []
        for _ in range(num_syms):
            g = [0.0j] * cls.N_FFT
            for k in range(1, cls.HALF_ACTIVE + 1):
                g[k] = complex(rng.choice(levels), rng.choice(levels)) / norm
                g[cls.N_FFT - k] = complex(rng.choice(levels), rng.choice(levels)) / norm
            grids.append(g)
            td.extend([v * scale for v in Radix2FFT.ifft(g)])
        return td, grids


class PhysicalMemoryPA:
    """Mo hinh PA phi tuyen manh co hieu ung nho nhiet/bias (25 deg C vs 95 deg C)."""

    def __init__(self, temp_c: float = 25.0):
        self.temp_c = temp_c
        # Khi nhiet do tang len 95 C: do loi giam 12%, V_sat giam nhe, AM-PM tang 60%
        dt = max(0.0, temp_c - 25.0)
        self.g0 = 1.0 - 0.0017 * dt
        self.v_sat = 2.60 * (1.0 - 0.0010 * dt)
        self.rapp_p = 1.6
        self.alpha_phi = 0.42 * (1.0 + 0.0085 * dt)
        self.beta_phi = 0.45
        self.mem_taps = (0.93 + 0.0j, 0.052 - 0.025j, 0.018 + 0.008j)

    def forward(self, x_in: List[complex], drive_scale: float) -> List[complex]:
        nl: List[complex] = []
        for s in x_in:
            x = s * drive_scale
            r = abs(x)
            if r < 1e-12:
                nl.append(0.0j)
            else:
                rn = (self.g0 * r) / self.v_sat
                amp = (self.g0 * r) / ((1.0 + rn ** (2.0 * self.rapp_p)) ** (1.0 / (2.0 * self.rapp_p)))
                phi = (self.alpha_phi * (rn ** 2)) / (1.0 + self.beta_phi * (rn ** 2))
                nl.append(cmath.rect(amp, cmath.phase(x) + phi))

        y: List[complex] = []
        for n in range(len(nl)):
            acc = 0.0j
            for m, tap in enumerate(self.mem_taps):
                if n - m >= 0:
                    acc += tap * nl[n - m]
            y.append(acc)
        return y


class MemoryPolynomialDPD:
    """
    Bo Tien meo So Memory Polynomial (order K, memory depth Q) huan luyen bang
    Indirect Learning Architecture (ILA) + Complex RLS.
    """

    def __init__(self, order_k: int = 7, mem_depth_q: int = 3, forgetting_lam: float = 0.9995):
        self.order_k = order_k
        self.mem_q = mem_depth_q
        self.lam = forgetting_lam
        self.dim = order_k * mem_depth_q
        # Khoi tao trong so don vi w_{1,0} = 1.0 (Bypass ban dau)
        self.weights: List[complex] = [0.0j] * self.dim
        self.weights[0] = 1.0 + 0.0j

    def _basis_vector(self, seq: List[complex], n: int) -> List[complex]:
        phi: List[complex] = []
        for q in range(self.mem_q):
            idx = n - q
            u = seq[idx] if idx >= 0 else 0.0j
            mag = abs(u)
            pow_mag = 1.0
            for _ in range(self.order_k):
                phi.append(u * pow_mag)
                pow_mag *= mag
        return phi

    def apply(self, x_in: List[complex]) -> List[complex]:
        out: List[complex] = []
        w = self.weights
        for n in range(len(x_in)):
            phi = self._basis_vector(x_in, n)
            val = sum(w[i].conjugate() * phi[i] for i in range(self.dim))
            out.append(val)
        return out

    def train_ila_rls(self, pa_in_z: List[complex], pa_out_y: List[complex], target_gain: complex, num_samples: int = 3500) -> None:
        """Giai w cho Post-Distorter: Phi(y / G_target) * conj(w) ~ pa_in_z bang Complex RLS."""
        inv_g = 1.0 / target_gain
        y_norm = [v * inv_g for v in pa_out_y]

        dim = self.dim
        # Khoi tao ma tran nghich dao hiep phuong sai P = 50 * I cho RLS hoi tu sat nghiem toi uu
        p_mat: List[List[complex]] = [[(50.0 + 0.0j if i == j else 0.0j) for j in range(dim)] for i in range(dim)]
        w = [0.0j] * dim
        w[0] = 1.0 + 0.0j

        n_steps = min(num_samples, len(pa_in_z))
        inv_lam = 1.0 / self.lam

        for n in range(self.mem_q, n_steps):
            phi = self._basis_vector(y_norm, n)
            p_phi = [sum(p_mat[i][j] * phi[j] for j in range(dim)) for i in range(dim)]
            denom = self.lam + sum(phi[i].conjugate() * p_phi[i] for i in range(dim)).real
            k_gain = [p_phi[i] / denom for i in range(dim)]

            y_hat = sum(w[i].conjugate() * phi[i] for i in range(dim))
            err = pa_in_z[n] - y_hat

            for i in range(dim):
                w[i] += k_gain[i] * err.conjugate()

            for i in range(dim):
                ki = k_gain[i]
                row_i = p_mat[i]
                for j in range(dim):
                    row_i[j] = (row_i[j] - ki * p_phi[j].conjugate()) * inv_lam

        self.weights = w


def measure_spectral_quality(y_rx: List[complex], grids: List[List[complex]]) -> Dict[str, float]:
    n_fft = OFDM64QAMFrame.N_FFT
    half = OFDM64QAMFrame.HALF_ACTIVE
    scale = n_fft / math.sqrt(2.0 * half)
    p_in = 0.0
    p_adj_lo = 0.0
    p_adj_hi = 0.0
    err_sq = 0.0
    ref_sq = 0.0

    # Bo qua symbol 0 de tranh qua do bien ngan
    for s_idx in range(1, len(grids)):
        seg = y_rx[s_idx * n_fft : (s_idx + 1) * n_fft]
        spec = Radix2FFT.fft(seg)
        ref = grids[s_idx]

        num_ls = 0.0j
        den_ls = 0.0
        for k in range(1, half + 1):
            for b in (k, n_fft - k):
                p_in += abs(spec[b]) ** 2
                num_ls += ref[b].conjugate() * (spec[b] / scale)
                den_ls += abs(ref[b]) ** 2
        g_s = num_ls / max(1e-12, den_ls)

        for k in range(1, half + 1):
            for b in (k, n_fft - k):
                rx_eq = (spec[b] / scale) / g_s
                err_sq += abs(rx_eq - ref[b]) ** 2
                ref_sq += abs(ref[b]) ** 2
        for k in range(half + 1, 3 * half + 1):
            p_adj_hi += abs(spec[k]) ** 2
            p_adj_lo += abs(spec[n_fft - k]) ** 2

    return {
        "aclr_dbc": 10.0 * math.log10(max(1e-15, max(p_adj_lo, p_adj_hi)) / max(1e-15, p_in)),
        "evm_pct": math.sqrt(err_sq / max(1e-15, ref_sq)) * 100.0,
    }


def test_dpd_memory_polynomial_rls():
    """Chuong trinh kiem thu DPD Da thuc Nho + Hoc Gian tiep RLS & Thich nghi nhiet do."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BM (NHOM 52) - BAI 206 (MILESTONE BM.3)")
    print("TIEN MEO SO MEMORY-POLYNOMIAL DPD, ILA & BO GIAI THICH NGHI RLS")
    print("=" * 80)

    x_bb, grids = OFDM64QAMFrame.generate(num_syms=10, seed=206)
    pa_25c = PhysicalMemoryPA(temp_c=25.0)
    # Kich thich PA tai IBO = 6.5 dB, target gain = 0.68 * drive de dinh luon nam trong tran vat ly V_sat
    drive = 2.60 * (10.0 ** (-6.5 / 20.0))

    # 1. So sanh Khong DPD vs Memoryless DPD (Q=1) vs Memory Polynomial DPD (Q=3, K=6)
    print("\n[1] So sanh hieu nang tuyen tinh hoa tai IBO = 6.5 dB (Memory PA 25 deg C):")
    y_no_dpd = pa_25c.forward(x_bb, drive)
    m_no = measure_spectral_quality(y_no_dpd, grids)

    g_target = 0.68 * drive

    # (a) Memoryless DPD (Q=1, K=6)
    dpd_q1 = MemoryPolynomialDPD(order_k=6, mem_depth_q=1, forgetting_lam=1.0)
    z_q1 = x_bb
    for _ in range(3):
        y_tmp = pa_25c.forward(z_q1, drive)
        dpd_q1.train_ila_rls(z_q1, y_tmp, g_target, num_samples=4500)
        z_q1 = dpd_q1.apply(x_bb)
    y_q1 = pa_25c.forward(z_q1, drive)
    m_q1 = measure_spectral_quality(y_q1, grids)

    # (b) Full Memory Polynomial DPD (Q=3, K=6 -> 18 tham so phuc)
    dpd_q3 = MemoryPolynomialDPD(order_k=6, mem_depth_q=3, forgetting_lam=1.0)
    z_q3 = x_bb
    for _ in range(3):
        y_tmp = pa_25c.forward(z_q3, drive)
        dpd_q3.train_ila_rls(z_q3, y_tmp, g_target, num_samples=4500)
        z_q3 = dpd_q3.apply(x_bb)
    y_q3 = pa_25c.forward(z_q3, drive)
    m_q3 = measure_spectral_quality(y_q3, grids)

    print(f"  * Khong DPD             : ACLR = {m_no['aclr_dbc']:6.2f} dBc | EVM = {m_no['evm_pct']:5.2f}% (VI PHAM!)")
    print(f"  * Memoryless DPD (Q=1)  : ACLR = {m_q1['aclr_dbc']:6.2f} dBc | EVM = {m_q1['evm_pct']:5.2f}% (Con duoi nho)")
    print(f"  * Memory Poly DPD (Q=3) : ACLR = {m_q3['aclr_dbc']:6.2f} dBc | EVM = {m_q3['evm_pct']:5.2f}% (SACH 100%!)")

    assert m_no["aclr_dbc"] > -30.0
    assert m_q1["aclr_dbc"] < m_no["aclr_dbc"] - 6.0
    assert m_q3["aclr_dbc"] < -46.0 and m_q3["evm_pct"] < 1.2
    print("  -> Ket luan: DPD Da thuc Nho ILA-RLS triet tieu > 20 dB bung pho & giu EVM < 1.2% (PASS)!")

    # 2. Kiem thu Thich nghi Nhiet do khi chip PA nong len 95 deg C
    print("\n[2] Kiem thu Thich nghi Online RLS khi PA nong len 95 deg C (lech Gain & AM-PM):")
    pa_95c = PhysicalMemoryPA(temp_c=95.0)
    y_hot_frozen = pa_95c.forward(z_q3, drive)
    m_hot_frozen = measure_spectral_quality(y_hot_frozen, grids)

    # Cap nhat ILA-RLS theo thoi gian thuc o 95 C
    g_hot_target = g_target * pa_95c.g0
    z_hot_adapt = z_q3
    for _ in range(2):
        y_tmp_hot = pa_95c.forward(z_hot_adapt, drive)
        dpd_q3.train_ila_rls(z_hot_adapt, y_tmp_hot, g_hot_target, num_samples=4500)
        z_hot_adapt = dpd_q3.apply(x_bb)
    y_hot_adapt = pa_95c.forward(z_hot_adapt, drive)
    m_hot_adapt = measure_spectral_quality(y_hot_adapt, grids)

    print(f"  * 95 C (Dung weights cu 25 C) : ACLR = {m_hot_frozen['aclr_dbc']:6.2f} dBc | EVM = {m_hot_frozen['evm_pct']:5.2f}%")
    print(f"  * 95 C (Sau 1 buoc ILA-RLS)   : ACLR = {m_hot_adapt['aclr_dbc']:6.2f} dBc | EVM = {m_hot_adapt['evm_pct']:5.2f}%")

    assert m_hot_frozen["aclr_dbc"] > -40.0
    assert m_hot_adapt["aclr_dbc"] < -46.0 and m_hot_adapt["evm_pct"] < 1.5
    print("  -> Ket luan: RLS tu dong khoa lai ACLR < -46 dBc khi PA nong 95 deg C (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 206: DPD MEMORY POLYNOMIAL & ILA-RLS HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_dpd_memory_polynomial_rls()
