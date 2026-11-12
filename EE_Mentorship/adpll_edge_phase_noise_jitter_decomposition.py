"""
EE MENTORSHIP PROGRAM - MODULE BH (NHOM 47) - BAI 186 (MILESTONE BH.3)
================================================================================
PHAN TICH PHO NHIEU PHA L(f) VA PHAN RA RUNG PHA JITTER CHO HIGH-SPEED SERDES
================================================================================

Kien truc phan tich do tinh khiet pho va chat luong xung nhip (Clock Purity & Jitter Analysis):
1. Pho mat do cong suat Nhieu pha L(f) (Phase Noise Spectrum in dBc/Hz):
   - Mo ta cong suat tieng on pha trong dai thong 1 Hz cach song mang mot khoang tan so offset f.
   - Cac vung dac trung cua bo dao dong DCO/VCO:
     * Vung 1/f^3 : Nhieu nhap nhay (Flicker Noise) bi bien dieu boi tinh phi tuyen.
     * Vung 1/f^2 : Nhieu nhiet trang (Thermal White Noise) trong khung cong huong LC.
     * Vung San nhieu : San nhieu nhiet cua tang dem dau ra (Noise Floor ~ -155 dBc/Hz).
   - Tich phan pho nhieu pha tinh Do rung pha can quan phuong (RMS Phase Jitter):
     sigma_phi^2 = 2 * Integral[f_low .. f_high] 10^(L(f) / 10) df
     sigma_t_rms = sqrt(sigma_phi_sq) / (2 * pi * f_0)

2. Cac chi so Rung pha mien thoi gian (Time-Domain Jitter Metrics):
   - Period Jitter (PJ)       : Do lech cua chu ky don T[k] so voi chu ky danh dinh T_0.
   - Cycle-to-Cycle (C2C)     : Do chenh lech giua 2 chu ky lien tiep: T[k+1] - T[k].
   - Time Interval Error (TIE): Sai so tich luy thoi diem suon xung so voi xung nhip vang (Golden Clock).

3. Mo hinh phan ra Rung pha Dual-Dirac (Jitter Decomposition):
   - Tong rung pha tai ty le loi bit khac khe (vi du BER = 10^-12 cho PCIe Gen 6 / SerDes 112G):
     TJ(BER) = DJ_dd + 2 * Q(BER) * RJ_rms
     Voi BER = 10^-12 thi Q = 7.0347, suy ra: TJ = DJ_dd + 14.069 * RJ_rms.
   - Random Jitter (RJ)       : Phan bo Gauss khong gioi han do chuyen dong nhiet cua electron.
   - Deterministic Jitter (DJ): Phan bo co gioi han bien do do gion song nguon dien (Supply Ripple dV/dt).

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Tich phan nhieu pha sang Rung pha thoi gian RMS (RMS Jitter Integration):
                     sqrt( 2 * Integral[f_low .. f_high] 10^(L(f)/10) df )
     sigma_t_rms = ────────────────────────────────────────────────────────
                                         2 * pi * f_0

2. Sai so khoang thoi gian (Time Interval Error - TIE):
     TIE[k] = t_edge[k] - (t_0 + k * T_nominal)

3. Tong rung pha theo mo hinh Dual-Dirac (Total Jitter):
     TJ(10^-12) = DJ_dd + 14.0694 * RJ_rms
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class PhaseNoiseProfile:
    """Cau hinh pho nhieu pha L(f) cua bo dao dong DCO 10 GHz."""
    f_carrier_hz: float = 10.0e9        # Tan so song mang 10 GHz (T_0 = 100 ps)
    # Cac diem do pho nhieu pha L(f) tieu bieu (Offset Frequency, dBc/Hz)
    # Vung 1/f^3 tai 10 kHz, 1/f^2 tai 1 MHz, San nhieu tai 100 MHz
    f_offsets_hz: List[float] = field(default_factory=lambda: [
        1.0e3, 10.0e3, 100.0e3, 1.0e6, 10.0e6, 40.0e6, 100.0e6
    ])
    l_dbc_per_hz: List[float] = field(default_factory=lambda: [
        -65.0, -92.0, -112.0, -125.0, -138.0, -148.0, -153.0
    ])


class PhaseNoiseIntegrator:
    """
    Subsystem 1: Tich phan pho nhieu pha L(f) de tinh toan RMS Jitter.
    Ap dung phuong phap hinh thang trong toa do logarit.
    """
    def __init__(self, profile: Optional[PhaseNoiseProfile] = None):
        self.prof = profile if profile is not None else PhaseNoiseProfile()

    def interpolate_l_f(self, f_target: float) -> float:
        """Noi suy tuyen tinh tren thang logarit de tinh L(f) tai bat ky tan so f_target."""
        offsets = self.prof.f_offsets_hz
        pns = self.prof.l_dbc_per_hz

        if f_target <= offsets[0]:
            # Keo dai theo do doc 1/f^3 (-30 dB/decade)
            log_ratio = math.log10(f_target / offsets[0])
            return pns[0] - 30.0 * log_ratio
        elif f_target >= offsets[-1]:
            # San nhieu phang
            return pns[-1]
        
        # Tim khoang noi suy
        for i in range(len(offsets) - 1):
            if offsets[i] <= f_target <= offsets[i + 1]:
                f1, f2 = offsets[i], offsets[i + 1]
                p1, p2 = pns[i], pns[i + 1]
                slope = (p2 - p1) / math.log10(f2 / f1)
                return p1 + slope * math.log10(f_target / f1)
        return pns[-1]

    def integrate_rms_jitter(self, f_low_hz: float = 10.0e3, f_high_hz: float = 100.0e6, num_steps: int = 2000) -> Tuple[float, float]:
        """
        Tich phan pho nhieu pha tu f_low den f_high de tinh:
        Tra ve (rms_phase_jitter_rad, rms_time_jitter_sec).
        """
        # Chia nho dai tich phan theo thang logarit
        log_low = math.log10(f_low_hz)
        log_high = math.log10(f_high_hz)
        d_log = (log_high - log_low) / num_steps

        power_integral = 0.0
        for i in range(num_steps):
            f_a = 10.0 ** (log_low + i * d_log)
            f_b = 10.0 ** (log_low + (i + 1) * d_log)
            df = f_b - f_a
            
            l_a = self.interpolate_l_f(f_a)
            l_b = self.interpolate_l_f(f_b)
            
            # Mat do cong suat tuyen tinh (Linear Power Density)
            s_a = 10.0 ** (l_a / 10.0)
            s_b = 10.0 ** (l_b / 10.0)
            
            # Tich phan hinh thang
            power_integral += 0.5 * (s_a + s_b) * df

        # Nhan doi do tinh tren dai 2 phia (Double-Sided Equivalent)
        sigma_phi_sq = 2.0 * power_integral
        sigma_phi_rad = math.sqrt(sigma_phi_sq)

        # Chuyen doi sang rung pha thoi gian RMS: sigma_t = sigma_phi / (2 * pi * f_0)
        sigma_t_sec = sigma_phi_rad / (2.0 * math.pi * self.prof.f_carrier_hz)
        return sigma_phi_rad, sigma_t_sec


class JitterSynthesizerAndAnalyzer:
    """
    Subsystem 2: Sinh chuoi xung nhip co rung pha va phan ra Jitter Dual-Dirac.
    Phan tich Period Jitter, Cycle-to-Cycle Jitter va TIE.
    """
    def __init__(self, f_carrier_hz: float = 10.0e9):
        self.f_carrier = f_carrier_hz
        self.t_nominal = 1.0 / f_carrier_hz  # 100 ps

    def generate_jittered_edges(self, num_cycles: int = 8000, rj_sigma_ps: float = 0.12, dj_pp_ps: float = 0.35) -> List[float]:
        """
        Sinh danh sach thoi diem suon xung (t_edge) gom:
        - RJ: Bien ngau nhien Gauss voi do lech chuan rj_sigma_ps.
        - DJ: Nhieu Duty Cycle Distortion (DCD) Dual-Dirac co bien do dj_pp_ps / 2.
        """
        edges = []
        dj_amp_sec = (dj_pp_ps * 1e-12) / 2.0
        rj_sigma_sec = rj_sigma_ps * 1e-12

        for k in range(num_cycles):
            ideal_time = k * self.t_nominal
            
            # Deterministic Jitter (DJ): DCD 2 trang thai (+A va -A)
            dj_component = dj_amp_sec if (k % 2 == 0) else -dj_amp_sec
            
            # Random Jitter (RJ): Bien Gauss khong gioi han
            rj_component = random.gauss(0.0, rj_sigma_sec)
            
            edge_time = ideal_time + dj_component + rj_component
            edges.append(edge_time)
            
        return edges

    def compute_jitter_metrics(self, edges: List[float]) -> Dict[str, any]:
        """
        Tinh toan cac chuoi thoi gian:
        - Period Jitter (PJ)
        - Cycle-to-Cycle Jitter (C2C)
        - Time Interval Error (TIE)
        """
        n = len(edges)
        periods = [edges[i + 1] - edges[i] for i in range(n - 1)]
        period_jitters = [(p - self.t_nominal) * 1e12 for p in periods]  # ps
        
        c2c_jitters = [(periods[i + 1] - periods[i]) * 1e12 for i in range(len(periods) - 1)]  # ps
        
        ties = [(edges[k] - (k * self.t_nominal)) * 1e12 for k in range(n)]  # ps

        # Tinh RMS va Peak-to-Peak
        pj_rms = math.sqrt(sum(x ** 2 for x in period_jitters) / len(period_jitters))
        c2c_rms = math.sqrt(sum(x ** 2 for x in c2c_jitters) / len(c2c_jitters))
        tie_rms = math.sqrt(sum(x ** 2 for x in ties) / len(ties))

        return {
            "period_jitter_rms_ps": pj_rms,
            "period_jitter_pp_ps": max(period_jitters) - min(period_jitters),
            "c2c_jitter_rms_ps": c2c_rms,
            "c2c_jitter_pp_ps": max(c2c_jitters) - min(c2c_jitters),
            "tie_rms_ps": tie_rms,
            "tie_pp_ps": max(ties) - min(ties),
            "ties_ps": ties
        }

    def decompose_dual_dirac(self, ties_ps: List[float]) -> Tuple[float, float, float]:
        """
        Phan ra Jitter theo mo hinh Dual-Dirac tu phan bo hon hop 2 dinh Gauss TIE:
        Gom 2 phan bo Gauss cach nhau khoang DJ_dd, moi phan bo co do lech chuan RJ_sigma.
        Tra ve (rj_sigma_est_ps, dj_dd_est_ps, total_jitter_1e12_ps).
        """
        n = len(ties_ps)
        ties_sorted = sorted(ties_ps)

        # Trong phan bo hon hop 50/50 Dual-Dirac:
        # P(X <= x) = 0.5 * Phi((x - mu_L) / sigma) cho nua trai
        # Voi p = 0.05 -> Phi = 0.10 -> z_05 = -1.28155
        # Voi p = 0.15 -> Phi = 0.30 -> z_15 = -0.52440
        # Do chenh lech: Delta_z = 0.75715
        delta_z = 0.75715
        z_15 = -0.52440
        
        idx_05 = int(round(0.05 * n))
        idx_15 = int(round(0.15 * n))
        idx_85 = int(round(0.85 * n))
        idx_95 = int(round(0.95 * n))

        val_05 = ties_sorted[idx_05]
        val_15 = ties_sorted[idx_15]
        val_85 = ties_sorted[idx_85]
        val_95 = ties_sorted[idx_95]

        # Uoc luong sigma_RJ tu do doc duoi trai va duoi phai
        sigma_left = (val_15 - val_05) / delta_z
        sigma_right = (val_95 - val_85) / delta_z
        rj_sigma_est = 0.5 * (sigma_left + sigma_right)

        # Uoc luong DJ_dd = Khoang cach giua 2 dinh Dirac
        # mu_L = val_15 - z_15 * sigma = val_15 + 0.52440 * sigma
        # mu_R = val_85 + z_15 * sigma = val_85 - 0.52440 * sigma
        mean_left = val_15 - z_15 * rj_sigma_est
        mean_right = val_85 + z_15 * rj_sigma_est
        dj_dd_est = max(0.0, mean_right - mean_left)

        # Tinh Total Jitter tai BER = 10^-12 (Q = 7.0347 -> 2 * Q = 14.0694)
        tj_1e12 = dj_dd_est + 14.0694 * rj_sigma_est
        return rj_sigma_est, dj_dd_est, tj_1e12


def test_phase_noise_and_jitter_decomposition():
    """Chuong trinh kiem thu toan dien pho nhieu pha va phan ra rung pha."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BH (NHOM 47) - BAI 186 (MILESTONE BH.3)")
    print("PHAN TICH PHO NHIEU PHA L(f) VA PHAN RA RUNG PHA JITTER DUAL-DIRAC")
    print("=" * 80)

    # 1. Kiem thu tich phan pho nhieu pha L(f) (10 GHz DCO Clock)
    print("\n[1] Tich phan pho nhieu pha L(f) cua bo dao dong 10 GHz DCO (10 kHz .. 100 MHz):")
    prof = PhaseNoiseProfile(f_carrier_hz=10.0e9)
    integrator = PhaseNoiseIntegrator(prof)

    rms_rad, rms_sec = integrator.integrate_rms_jitter(f_low_hz=10.0e3, f_high_hz=100.0e6)
    rms_fs = rms_sec * 1e15

    print(f"  * Tan so song mang Clock         : {prof.f_carrier_hz / 1e9:.1f} GHz (T_0 = 100 ps)")
    print(f"  * Dai tich phan tieng on        : 10 kHz den 100 MHz")
    print(f"  * Nhieu pha tich luy RMS (Pha)  : {rms_rad:.5f} rad ({rms_rad * 180.0 / math.pi:.3f} deg)")
    print(f"  * Rung pha tich luy RMS (Thoi gian): {rms_fs:.2f} femtoseconds (fs)")

    assert rms_fs < 150.0, f"Loi: Rung pha RMS vuot nguong thiet ke: {rms_fs} fs"
    print("  -> Ket luan: Xung nhip 10 GHz dat do tinh khiet pho cuc cao: sub-100 fs RMS Jitter (PASS)!")

    # 2. Sinh chuoi xung nhip co RJ va DJ, do luong cac chi so PJ, C2C va TIE
    print("\n[2] Mo phong 8,000 chu ky xung nhip va do luong cac thong so Jitter mien thoi gian:")
    random.seed(42)
    analyzer = JitterSynthesizerAndAnalyzer(f_carrier_hz=10.0e9)

    true_rj_ps = 0.12   # 120 fs Random Jitter
    true_dj_ps = 0.35   # 350 fs Deterministic Jitter do gion song nguon 50 MHz
    
    edges = analyzer.generate_jittered_edges(
        num_cycles=10000,
        rj_sigma_ps=true_rj_ps,
        dj_pp_ps=true_dj_ps
    )

    metrics = analyzer.compute_jitter_metrics(edges)

    print(f"  * Period Jitter (PJ RMS)         : {metrics['period_jitter_rms_ps']*1000.0:6.2f} fs | Peak-to-Peak: {metrics['period_jitter_pp_ps']*1000.0:6.2f} fs")
    print(f"  * Cycle-to-Cycle (C2C RMS)       : {metrics['c2c_jitter_rms_ps']*1000.0:6.2f} fs | Peak-to-Peak: {metrics['c2c_jitter_pp_ps']*1000.0:6.2f} fs")
    print(f"  * Time Interval Error (TIE RMS)  : {metrics['tie_rms_ps']*1000.0:6.2f} fs | Peak-to-Peak: {metrics['tie_pp_ps']*1000.0:6.2f} fs")

    # 3. Kiem thu mo hinh phan ra Jitter Dual-Dirac
    print("\n[3] Kiem thu mo hinh phan ra Dual-Dirac (Trich xuat RJ vs DJ):")
    est_rj, est_dj, est_tj = analyzer.decompose_dual_dirac(metrics["ties_ps"])

    err_rj = abs(est_rj - true_rj_ps)
    err_dj = abs(est_dj - true_dj_ps)

    print(f"  * Random Jitter RJ_sigma (Thuc te: {true_rj_ps*1000.0:5.1f} fs)  : {est_rj*1000.0:5.1f} fs (Sai so: {err_rj*1000.0:4.1f} fs)")
    print(f"  * Deterministic Jitter DJ_dd (Thuc te: {true_dj_ps*1000.0:5.1f} fs): {est_dj*1000.0:5.1f} fs (Sai so: {err_dj*1000.0:4.1f} fs)")
    print(f"  * Total Jitter TJ (tai BER = 10^-12)                   : {est_tj*1000.0:5.1f} fs ({est_tj:.3f} ps)")
    print(f"  * Ti le do mo mat (Eye Opening) tai 64 GT/s (UI = 15.6 ps): {(15.625 - est_tj) / 15.625 * 100.0:.2f} %")

    assert err_rj < 0.035, "Loi: Uoc luong RJ sai lech qua lon!"
    assert err_dj < 0.060, "Loi: Uoc luong DJ sai lech qua lon!"
    print("  -> Ket luan: Mo hinh Dual-Dirac tach biet hoan hao giua RJ va DJ, xac dinh do mo mat SerDes (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 186: PHO NHIEU PHA VA DUAL-DIRAC JITTER HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_phase_noise_and_jitter_decomposition()
