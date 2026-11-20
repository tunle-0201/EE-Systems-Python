"""
================================================================================
EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 216 (MILESTONE BP.1)
MA TRAN DIEN DUNG TUONG HO (PCAP MUTUAL CAPACITANCE) & MACH TICH PHAN CHUYEN MACH TU AFE
================================================================================
Muc tieu:
1. Mo hinh hoa luoi cam ung ITO 2D (Tx x Rx) voi dien dung nen C_m0, tro khang
   duong day R_ito (suy hao RC theo khoang cach) va vat ly ngon tay noi dat
   lam GIAM dien dung tuong ho delta_C_m < 0.
2. Thiet ke mach tich phan chuyen mach tu (Switched-Capacitor Charge Integrator)
   tich hop lay mau kep tuong quan (CDS) va ADC 14-bit khuech dai dien tich.
3. Bo theo doi duong nen dong (Thermal Baseline Drift Tracking) chong troi nhiet
   do +15 degC ma khong bo sot ngon tay tran hoac deo gang tay mong.
================================================================================
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PCAPPanelConfig:
    rows_tx: int = 12
    cols_rx: int = 8
    pitch_mm: float = 4.0
    c_m0_pf: float = 2.20
    r_tx_per_node_ohm: float = 220.0
    r_rx_per_node_ohm: float = 240.0
    v_tx_pp: float = 5.0
    f_tx_hz: float = 200_000.0
    n_pulses: int = 32
    c_int_pf: float = 40.0
    v_ref_adc: float = 3.3
    adc_bits: int = 14


class MutualCapPanelPhysics:
    """Mo hinh vat ly luoi cam ung dien dung tuong ho M x N + tro khang RC."""

    def __init__(self, cfg: PCAPPanelConfig, seed: int = 42) -> None:
        self.cfg = cfg
        self.rng = random.Random(seed)
        # Sai so che tao ITO tung nut giao (+/- 2.5% quanh C_m0)
        self.static_offset_pf: List[List[float]] = [
            [self.rng.gauss(0.0, 0.035) for _ in range(cfg.cols_rx)]
            for _ in range(cfg.rows_tx)
        ]

    def node_rc_tau_sec(self, r: int, c: int) -> float:
        """Hang so thoi gian RC tich luy doc theo chieu dai duong dan Tx va Rx."""
        # Tin hieu Tx di tu cot 0 -> c, tin hieu Rx thu ve hang 0 -> r
        r_total = (c + 1) * self.cfg.r_tx_per_node_ohm + (r + 1) * self.cfg.r_rx_per_node_ohm
        c_line_load_pf = 18.0 + 1.8 * (r + c)
        return r_total * (c_line_load_pf * 1e-12)

    def simulate_cm_matrix_pf(
        self,
        fingers: List[Tuple[float, float, float, float]],
        temp_delta_c: float = 0.0,
    ) -> List[List[float]]:
        """
        Tinh ma tran C_m (pF) hien tai:
        fingers = [(x_mm, y_mm, peak_shunt_pf, sigma_mm), ...]
        Ngon tay noi dat hut bot duong suc dien truong -> C_m GIAM (delta_C_m < 0).
        Nhiet do tang lam hang so dien moi kinh tang -> C_m nen TANG deu.
        """
        thermal_factor = 1.0 + 0.0020 * temp_delta_c  # +0.2%/degC (+3.0% o +15 degC)
        mat: List[List[float]] = []

        for r in range(self.cfg.rows_tx):
            y_node = (r + 0.5) * self.cfg.pitch_mm
            row_vals: List[float] = []
            for c in range(self.cfg.cols_rx):
                x_node = (c + 0.5) * self.cfg.pitch_mm
                c_base = (self.cfg.c_m0_pf + self.static_offset_pf[r][c]) * thermal_factor

                shunt_pf = 0.0
                for fx, fy, peak_pf, sigma_mm in fingers:
                    d2 = (x_node - fx) ** 2 + (y_node - fy) ** 2
                    shunt_pf += peak_pf * math.exp(-d2 / (2.0 * sigma_mm * sigma_mm))

                # Khong cho phep hut qua 70% C_m nen trong thuc te
                shunt_pf = min(shunt_pf, 0.70 * c_base)
                row_vals.append(c_base - shunt_pf)
            mat.append(row_vals)
        return mat


class SwitchedCapChargeIntegratorAFE:
    """
    Mach tich phan chuyen mach tu (SC Charge-Transfer Integrator) kem lay mau kep CDS.
    Moi nua chu ky PWM Tx NAP dien tich Q = C_m * V_tx * (1 - exp(-t_half / tau_rc))
    vao tu C_int, sau N_pulses dem ra ADC 14-bit va bu lai he so suy hao RC.
    """

    def __init__(self, cfg: PCAPPanelConfig, seed: int = 99) -> None:
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.t_half = 0.5 / cfg.f_tx_hz
        # He so bu suy hao RC cua tung nut giao (do duoc khi hieu chuan xuong)
        self.rc_comp_gain: List[List[float]] = [
            [1.0 for _ in range(cfg.cols_rx)] for _ in range(cfg.rows_tx)
        ]

    def calibrate_rc_profile(self, panel: MutualCapPanelPhysics) -> None:
        """Tinh he so bu duong truyen 1 / (1 - exp(-t_half / tau_rc)) cho moi nut."""
        for r in range(self.cfg.rows_tx):
            for c in range(self.cfg.cols_rx):
                tau = panel.node_rc_tau_sec(r, c)
                charge_eff = 1.0 - math.exp(-self.t_half / tau)
                self.rc_comp_gain[r][c] = 1.0 / max(charge_eff, 0.25)

    def measure_raw_adc_and_cm_pf(
        self,
        panel: MutualCapPanelPhysics,
        cm_matrix_pf: List[List[float]],
        noise_uv_rms: float = 180.0,
    ) -> Tuple[List[List[int]], List[List[float]]]:
        """
        Mo phong qua trinh do CDS:
        Phase P1 (TX rise) tich +Q, Phase P2 (TX fall) dao chieu tich them +Q
        tren tu vi sai -> dien ap ngo ra = N_pulses * (C_m / C_int) * V_tx_pp * eff_rc / 4.
        (Chia he so chia ap /4 hoac scale de nam gon trong thang 0..3.3V ADC).
        """
        scale_v_per_pf = (
            0.25 * self.cfg.n_pulses * self.cfg.v_tx_pp / self.cfg.c_int_pf
        )
        full_scale_codes = (1 << self.cfg.adc_bits) - 1

        adc_grid: List[List[int]] = []
        cm_est_grid: List[List[float]] = []

        for r in range(self.cfg.rows_tx):
            adc_row: List[int] = []
            cm_row: List[float] = []
            for c in range(self.cfg.cols_rx):
                tau = panel.node_rc_tau_sec(r, c)
                charge_eff = 1.0 - math.exp(-self.t_half / tau)

                # Nhieu kT/C va 1/f da duoc CDS triet giam manh
                v_out = (
                    cm_matrix_pf[r][c] * scale_v_per_pf * charge_eff
                    + self.rng.gauss(0.0, noise_uv_rms * 1e-6)
                )
                v_clamped = max(0.0, min(self.cfg.v_ref_adc, v_out))
                code = int(round((v_clamped / self.cfg.v_ref_adc) * full_scale_codes))

                # Quy doi nguoc tu ADC code -> C_m (pF) da bu RC
                v_meas = (code / full_scale_codes) * self.cfg.v_ref_adc
                cm_est = (v_meas / scale_v_per_pf) * self.rc_comp_gain[r][c]

                adc_row.append(code)
                cm_row.append(cm_est)
            adc_grid.append(adc_row)
            cm_est_grid.append(cm_row)

        return adc_grid, cm_est_grid


class BaselineDriftTracker:
    """
    Bo theo doi duong nen dong (Dynamic Baseline Tracking):
    - Khi delta_C nam trong vung khong cham, tu dong cap nhat duong nen C_base bang EMA
      de triet tieu troi nhiet do.
    - Khi phat hien delta_C giam manh qua nguong tre (Hysteresis), khoa chat baseline
      de giu nguyen do nhay khi ngon tay giu yen lau tren man hinh.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        alpha_drift: float = 0.08,
        touch_thresh_pf: float = -0.065,
        release_thresh_pf: float = -0.035,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.alpha_drift = alpha_drift
        self.touch_thresh_pf = touch_thresh_pf
        self.release_thresh_pf = release_thresh_pf
        self.baseline_pf: List[List[float]] = [[0.0] * cols for _ in range(rows)]
        self.initialized = False
        self.touch_latched: List[List[bool]] = [[False] * cols for _ in range(rows)]

    def initialize(self, cm_meas_pf: List[List[float]]) -> None:
        self.baseline_pf = [row[:] for row in cm_meas_pf]
        self.initialized = True

    def step(
        self, cm_meas_pf: List[List[float]]
    ) -> Tuple[List[List[float]], List[List[bool]]]:
        """Tra ve (ma tran delta_C_m = C_meas - C_base, ma tran co cham True/False)."""
        if not self.initialized:
            self.initialize(cm_meas_pf)

        delta_grid: List[List[float]] = []
        active_grid: List[List[bool]] = []

        # Kiem tra toan khung co ngon tay dang cham hay khong truoc khi cho drift
        raw_min_delta = min(
            cm_meas_pf[r][c] - self.baseline_pf[r][c]
            for r in range(self.rows)
            for c in range(self.cols)
        )
        frame_has_touch = raw_min_delta < self.touch_thresh_pf

        for r in range(self.rows):
            d_row: List[float] = []
            a_row: List[bool] = []
            for c in range(self.cols):
                diff = cm_meas_pf[r][c] - self.baseline_pf[r][c]
                if not frame_has_touch and not self.touch_latched[r][c]:
                    # Cho phep baseline bam theo troi nhiet do tu tu
                    self.baseline_pf[r][c] = (
                        (1.0 - self.alpha_drift) * self.baseline_pf[r][c]
                        + self.alpha_drift * cm_meas_pf[r][c]
                    )
                    diff = cm_meas_pf[r][c] - self.baseline_pf[r][c]

                if self.touch_latched[r][c]:
                    if diff > self.release_thresh_pf:
                        self.touch_latched[r][c] = False
                else:
                    if diff < self.touch_thresh_pf:
                        self.touch_latched[r][c] = True

                d_row.append(diff)
                a_row.append(self.touch_latched[r][c])
            delta_grid.append(d_row)
            active_grid.append(a_row)

        return delta_grid, active_grid


def test_mutual_cap_afe_integrator() -> None:
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 216 (MILESTONE BP.1)")
    print("MA TRAN DIEN DUNG TUONG HO PCAP & MACH TICH PHAN CHUYEN MACH TU AFE")
    print("=" * 80)

    cfg = PCAPPanelConfig()
    panel = MutualCapPanelPhysics(cfg, seed=42)
    afe = SwitchedCapChargeIntegratorAFE(cfg, seed=99)
    afe.calibrate_rc_profile(panel)
    tracker = BaselineDriftTracker(cfg.rows_tx, cfg.cols_rx)

    # 1. Khoi tao baseline o 25 degC (khong cham)
    cm_idle = panel.simulate_cm_matrix_pf(fingers=[], temp_delta_c=0.0)
    _, cm_meas_idle = afe.measure_raw_adc_and_cm_pf(panel, cm_idle)
    tracker.initialize(cm_meas_idle)

    # Kiem tra do chinh xac bu RC tai nut goc xa nhat (11, 7)
    true_far = cm_idle[11][7]
    est_far = cm_meas_idle[11][7]
    far_err_pct = abs(est_far - true_far) / true_far * 100.0
    print("\n[1] Kiem thu do chinh xac Charge Integrator + Bu suy hao RC:")
    print(
        f"  * Nut xa nhat (11,7): C_m thuc={true_far:.4f} pF | Do AFE={est_far:.4f} pF | Sai so={far_err_pct:.2f}%"
    )
    assert far_err_pct < 0.5, f"Sai so bu RC qua lon: {far_err_pct:.2f}%"

    # 2. Mo phong nhiet do man hinh tang dan +15 degC qua 60 khung (khong cham)
    max_active_during_drift = 0
    for step_idx in range(1, 61):
        t_rise = 15.0 * (step_idx / 60.0)
        cm_hot = panel.simulate_cm_matrix_pf(fingers=[], temp_delta_c=t_rise)
        _, cm_meas_hot = afe.measure_raw_adc_and_cm_pf(panel, cm_hot)
        deltas_hot, active_hot = tracker.step(cm_meas_hot)
        n_act = sum(1 for row in active_hot for val in row if val)
        max_active_during_drift = max(max_active_during_drift, n_act)

    residual_drift_ff = (
        max(abs(v) for row in deltas_hot for v in row) * 1000.0
    )
    print("\n[2] Kiem thu chong troi nhiet do (+15 degC -> +66 fF dich chuyen nen):")
    print(
        f"  * So nut cham gia khi tang +15 degC : {max_active_during_drift} (Muc tieu = 0)"
    )
    print(
        f"  * Do lech du sau khi bam Baseline   : {residual_drift_ff:.2f} fF"
    )
    assert max_active_during_drift == 0, "Phat sinh cham gia do troi nhiet!"
    assert residual_drift_ff < 25.0, "Baseline khong bam kip troi nhiet!"

    # 3. Dat 1 ngon tay tran (-0.42 pF, sigma=4.5 mm) & 1 ngon deo gang tay (-0.125 pF)
    fingers_test = [
        (14.0, 22.0, 0.420, 4.5),   # Ngon tran gan (y_r=5, x_c=3)
        (26.0, 38.0, 0.125, 5.2),   # Ngon deo gang mong
    ]
    cm_touch = panel.simulate_cm_matrix_pf(fingers=fingers_test, temp_delta_c=15.0)
    _, cm_meas_touch = afe.measure_raw_adc_and_cm_pf(panel, cm_touch)
    deltas_touch, active_touch = tracker.step(cm_meas_touch)

    bare_peak_ff = deltas_touch[5][3] * 1000.0
    glove_peak_ff = deltas_touch[9][6] * 1000.0
    print("\n[3] Kiem thu bat tin hieu ngon tay tran & gang tay mong tai +15 degC:")
    print(
        f"  * Ngon tay tran nut (5,3) : delta_C = {bare_peak_ff:.1f} fF | Active={active_touch[5][3]}"
    )
    print(
        f"  * Ngon deo gang nut (9,6) : delta_C = {glove_peak_ff:.1f} fF | Active={active_touch[9][6]}"
    )
    assert active_touch[5][3] and bare_peak_ff < -280.0
    assert active_touch[9][6] and glove_peak_ff < -75.0

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 216: PCAP MUTUAL-CAP AFE HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_mutual_cap_afe_integrator()
