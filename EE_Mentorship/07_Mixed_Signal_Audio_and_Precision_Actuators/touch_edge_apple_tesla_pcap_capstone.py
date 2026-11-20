"""
================================================================================
EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 219 (MILESTONE BP.4 - CAPSTONE)
DONG CO CAM UNG DA DIEM & KHANG NHIEU TOAN DIEN APPLE IPHONE PRO / TESLA 17"
================================================================================
Tich hop day du 4 tang phan cung Touch ASIC:
  1. Tang Vat ly & AFE (BP.1): Luoi PCAP 14x10 (pitch 3.8 mm) + Dong bo Baseline nhiet +12 degC.
  2. Tang Chong nhieu (BP.2): Quet pho TX-OFF + Nhay tan tranh sac xung 180 kHz +
     VSYNC OLED Blanking + Giai dieu che Lock-In I/Q cua so Hann.
  3. Tang Tri tue Nhan dien (BP.3): Khu 2 giot nuoc troi noi (0 cham gia) + Noi suy Sub-Pixel.
  4. Tang Theo doi 240 Hz (BP.3): Bo loc Kalman 4 trang thai giu vung ID 2 ngon tay luot nhanh.
================================================================================
"""

from __future__ import annotations

import math
import os
import random
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from touch_edge_iq_demod_freq_hopping import (
    AdaptiveFrequencyHopper,
    IQCarrierDemodulator,
    NoiseEnvironment,
)
from touch_edge_mutual_cap_afe_integrator import (
    BaselineDriftTracker,
    MutualCapPanelPhysics,
    PCAPPanelConfig,
)
from touch_edge_water_rejection_kalman import (
    DetectedBlob,
    MultiFingerKalmanManager,
    WaterRejectionSubPixelExtractor,
)


class PinchSafeLocalMinimaExtractor(WaterRejectionSubPixelExtractor):
    """
    Mo rong WaterRejectionSubPixelExtractor voi tach cuc tieu cuc bo 3x3 (Local-Minima Watershed):
    Khi 2 ngon tay chum lai gan (~9 mm), duong dong muc -0.045 pF cua chung noi lien thanh 1 yen ngua,
    nhung 2 dinh am 3x3 van tach biet ro rang -> khong bao gio bi gop mat dau hoac nhan nham thanh Palm.
    """

    def analyze_frame(
        self, delta_cm_pf: List[List[float]]
    ) -> Tuple[List[DetectedBlob], List[DetectedBlob]]:
        valid_fingers: List[DetectedBlob] = []
        all_blobs: List[DetectedBlob] = []

        # 1. Tim tat ca cuc tieu am cuc bo 3x3 sau du nguong cham
        peaks: List[Tuple[int, int]] = []
        for r in range(self.rows):
            for c in range(self.cols):
                val = delta_cm_pf[r][c]
                if val > self.neg_seed_pf:
                    continue
                is_min = True
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if delta_cm_pf[nr][nc] < val:
                                is_min = False
                                break
                    if not is_min:
                        break
                if is_min:
                    peaks.append((r, c))

        # 2. Voi moi dinh am: phan loai nuoc/palm va tinh trong tam Sub-Pixel 3x3 chong lan cum
        for pr, pc in peaks:
            peak_neg = delta_cm_pf[pr][pc]
            local_max_pos = -1.0
            for rr in range(max(0, pr - 2), min(self.rows, pr + 3)):
                for cc in range(max(0, pc - 2), min(self.cols, pc + 3)):
                    local_max_pos = max(local_max_pos, delta_cm_pf[rr][cc])

            # Dem kich thuoc loi am sau (< 45% dinh) de phat hien Palm rong bet
            deep_thresh = 0.45 * peak_neg
            deep_count = sum(
                1
                for rr in range(max(0, pr - 3), min(self.rows, pr + 4))
                for cc in range(max(0, pc - 3), min(self.cols, pc + 4))
                if delta_cm_pf[rr][cc] < deep_thresh
            )

            # Noi suy Parabol Log-Gaussian 2D chong lech bien & khong keo cum lan can
            a_mid = max(1e-4, -delta_cm_pf[pr][pc])
            a_left = max(1e-4, -delta_cm_pf[pr][pc - 1]) if pc > 0 else 1e-4
            a_right = max(1e-4, -delta_cm_pf[pr][pc + 1]) if pc + 1 < self.cols else 1e-4
            a_up = max(1e-4, -delta_cm_pf[pr - 1][pc]) if pr > 0 else 1e-4
            a_down = max(1e-4, -delta_cm_pf[pr + 1][pc]) if pr + 1 < self.rows else 1e-4

            l_m = math.log(a_mid)
            l_l, l_r = math.log(a_left), math.log(a_right)
            l_u, l_d = math.log(a_up), math.log(a_down)

            denom_x = l_l - 2.0 * l_m + l_r
            dc_sub = 0.5 * (l_l - l_r) / denom_x if denom_x < -1e-6 else 0.0
            dc_sub = max(-0.5, min(0.5, dc_sub))

            denom_y = l_u - 2.0 * l_m + l_d
            dr_sub = 0.5 * (l_u - l_d) / denom_y if denom_y < -1e-6 else 0.0
            dr_sub = max(-0.5, min(0.5, dr_sub))

            cx = (pc + 0.5 + dc_sub) * self.pitch_mm
            cy = (pr + 0.5 + dr_sub) * self.pitch_mm

            if deep_count > 16:
                cls_label = "PALM_SPLASH"
            elif local_max_pos > self.pos_water_halo_pf and peak_neg > -0.25:
                cls_label = "WATER_DROP"
            else:
                cls_label = "FINGER"

            blob = DetectedBlob(
                x_mm=cx,
                y_mm=cy,
                peak_neg_pf=peak_neg,
                local_max_pos_pf=local_max_pos,
                area_nodes=deep_count,
                classification=cls_label,
            )
            all_blobs.append(blob)
            if cls_label == "FINGER":
                valid_fingers.append(blob)

        # 3. Quet them cac giot nuoc thuan tuy chi tao dinh duong (> +0.055 pF)
        pos_visited = [[False] * self.cols for _ in range(self.rows)]
        for r0 in range(self.rows):
            for c0 in range(self.cols):
                if pos_visited[r0][c0] or delta_cm_pf[r0][c0] < 0.055:
                    continue
                queue = [(r0, c0)]
                pos_visited[r0][c0] = True
                p_cluster: List[Tuple[int, int]] = []
                while queue:
                    r, c = queue.pop(0)
                    p_cluster.append((r, c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if not pos_visited[nr][nc] and delta_cm_pf[nr][nc] > 0.040:
                                pos_visited[nr][nc] = True
                                queue.append((nr, nc))
                pr, pc = max(p_cluster, key=lambda p: delta_cm_pf[p[0]][p[1]])
                all_blobs.append(
                    DetectedBlob(
                        x_mm=(pc + 0.5) * self.pitch_mm,
                        y_mm=(pr + 0.5) * self.pitch_mm,
                        peak_neg_pf=0.0,
                        local_max_pos_pf=delta_cm_pf[pr][pc],
                        area_nodes=len(p_cluster),
                        classification="WATER_DROP",
                    )
                )

        return valid_fingers, all_blobs


class AppleTeslaTouchControllerCapstone:
    """Bo dieu khien Cam ung Da diem Khang nhieu Hop nhat 4 tang."""

    def __init__(self, seed: int = 2026) -> None:
        self.cfg = PCAPPanelConfig(rows_tx=14, cols_rx=10, pitch_mm=3.8)
        self.rng = random.Random(seed)
        self.panel = MutualCapPanelPhysics(self.cfg, seed=seed)
        self.demod = IQCarrierDemodulator(fs_hz=1_920_000.0, n_cycles=8)
        self.hopper = AdaptiveFrequencyHopper(n_avg_frames=4)
        self.baseline = BaselineDriftTracker(
            self.cfg.rows_tx,
            self.cfg.cols_rx,
            alpha_drift=0.05,
            touch_thresh_pf=-0.075,
            release_thresh_pf=-0.040,
        )
        self.extractor = PinchSafeLocalMinimaExtractor(
            rows=self.cfg.rows_tx,
            cols=self.cfg.cols_rx,
            pitch_mm=self.cfg.pitch_mm,
            neg_seed_pf=-0.075,
            pos_water_halo_pf=0.030,
            max_finger_nodes=22,
        )
        self.kalman = MultiFingerKalmanManager(dt=1.0 / 240.0, gate_mm=7.5)
        self.active_freq_hz: float = 180_000.0

    def scan_and_hop_frequency(self, env: NoiseEnvironment) -> float:
        best_freq, _ = self.hopper.scan_quietest_frequency(self.demod, env, self.rng)
        self.active_freq_hz = best_freq
        return best_freq

    def scan_panel_via_iq_afe(
        self,
        fingers: List[Tuple[float, float, float, float]],
        water_drops: List[Tuple[float, float]],
        env: NoiseEnvironment,
        temp_delta_c: float,
    ) -> List[List[float]]:
        """
        Mo phong qua trinh quet tung nut giao (r, c) bang song mang f_tx_hz da nhay tan,
        giai dieu che Lock-In I/Q trong cua so OLED VSYNC Blanking.
        """
        cm_true = self.panel.simulate_cm_matrix_pf(fingers, temp_delta_c=temp_delta_c)
        # Cong them hieu ung cau noi duong (+0.115 pF) tu giot nuoc troi noi
        for r in range(self.cfg.rows_tx):
            yn = (r + 0.5) * self.cfg.pitch_mm
            for c in range(self.cfg.cols_rx):
                xn = (c + 0.5) * self.cfg.pitch_mm
                for wx, wy in water_drops:
                    d2 = (xn - wx) ** 2 + (yn - wy) ** 2
                    cm_true[r][c] += 0.115 * math.exp(-d2 / (2.0 * 3.8 * 3.8))

        gain = 55.0
        cm_meas: List[List[float]] = []
        for r in range(self.cfg.rows_tx):
            row_est: List[float] = []
            for c in range(self.cfg.cols_rx):
                rx_wave = self.demod.synthesize_rx_waveform(
                    f_tx_hz=self.active_freq_hz,
                    tx_enabled=True,
                    cm_pf=cm_true[r][c],
                    rc_phase_lag_rad=0.14,
                    env=env,
                    oled_blanking_active=True,
                    rng=self.rng,
                    tx_gain_mv_per_pf=gain,
                )
                _, _, mag_mv, _ = self.demod.demodulate_iq(rx_wave, self.active_freq_hz)
                row_est.append(mag_mv / gain)
            cm_meas.append(row_est)
        return cm_meas

    def calibrate_baseline(
        self, env: NoiseEnvironment, temp_delta_c: float, n_avg: int = 8
    ) -> None:
        acc = [[0.0] * self.cfg.cols_rx for _ in range(self.cfg.rows_tx)]
        for _ in range(n_avg):
            cm_idle = self.scan_panel_via_iq_afe([], [], env, temp_delta_c=temp_delta_c)
            for r in range(self.cfg.rows_tx):
                for c in range(self.cfg.cols_rx):
                    acc[r][c] += cm_idle[r][c] / n_avg
        self.baseline.initialize(acc)

    def process_touch_frame(
        self,
        fingers: List[Tuple[float, float, float, float]],
        water_drops: List[Tuple[float, float]],
        env: NoiseEnvironment,
        temp_delta_c: float,
    ) -> Tuple[Dict[int, Tuple[float, float]], int]:
        """Tra ve (tracks {id: (x_mm, y_mm)}, tong so giot nuoc/nhieu da khu bo)."""
        cm_meas = self.scan_panel_via_iq_afe(fingers, water_drops, env, temp_delta_c)
        delta_grid, _ = self.baseline.step(cm_meas)
        valid_fingers, all_blobs = self.extractor.analyze_frame(delta_grid)
        rejected_count = sum(1 for b in all_blobs if b.classification != "FINGER")
        tracks = self.kalman.step(valid_fingers)
        return tracks, rejected_count


def test_apple_tesla_pcap_capstone() -> None:
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 219 (MILESTONE BP.4 - CAPSTONE)")
    print("DONG CO CAM UNG DA DIEM APPLE IPHONE PRO / TESLA 17 INCH CAPSTONE")
    print("=" * 80)

    ctrl = AppleTeslaTouchControllerCapstone(seed=2026)
    env = NoiseEnvironment(
        charger_freq_hz=180_000.0,
        charger_amp_mv=195.0,
        mains_60hz_mv=45.0,
        oled_active_burst_mv=260.0,
        thermal_noise_mv=5.0,
    )

    # 1. Quet pho & Nhay tan tranh sac xung 180 kHz + Hieu chuan nen o +12 degC
    hopped_hz = ctrl.scan_and_hop_frequency(env)
    ctrl.calibrate_baseline(env, temp_delta_c=12.0)
    print("\n[1] Kich hoat Dong co Chong nhieu & Hieu chuan Nhiet do (+12 degC):")
    print(
        f"  * Tan so sac quay pha = 180.0 kHz -> Tu dong nhay toi kenh sach = {hopped_hz/1000:.1f} kHz"
    )
    assert abs(hopped_hz - 180_000.0) > 1_000.0

    # 2. Kich ban tra tan 35 khung @ 240 Hz:
    #    - 2 giot nuoc troi noi nam co dinh tren man hinh
    #    - 2 ngon tay luot dong thoi (Pinch/Swipe) duoi nhieu bo sac 195 mV
    water_drops = [(6.5, 44.0), (31.0, 9.0)]
    errs_f1: List[float] = []
    errs_f2: List[float] = []
    false_water_touches = 0
    total_rejected_drops = 0
    id_map: Dict[str, int] = {}
    id_swaps = 0

    n_frames = 35
    for step in range(n_frames):
        s = step / (n_frames - 1)
        f1_true = (8.5 + 8.5 * s, 10.0 + 15.0 * s)    # (8.5, 10.0) -> (17.0, 25.0)
        f2_true = (30.0 - 7.0 * s, 42.0 - 10.0 * s)   # (30.0, 42.0) -> (23.0, 32.0) -- cach >= 9.2 mm

        fingers_in = [
            (f1_true[0], f1_true[1], 0.43, 4.1),
            (f2_true[0], f2_true[1], 0.41, 4.1),
        ]
        tracks, rej_cnt = ctrl.process_touch_frame(
            fingers_in, water_drops, env, temp_delta_c=12.0
        )
        total_rejected_drops += rej_cnt

        # Kiem tra khong co diem cham nao nam gan giot nuoc
        for tid, (tx, ty) in tracks.items():
            for wx, wy in water_drops:
                if math.hypot(tx - wx, ty - wy) < 5.0:
                    false_water_touches += 1

        assert len(tracks) == 2, f"Ky vong dung 2 ngon tay tai step {step}, nhan {len(tracks)}"

        # Gan nhan ID dau tien o step 0 va kiem tra khong trao ID
        best_t1 = min(tracks.keys(), key=lambda k: math.hypot(tracks[k][0] - f1_true[0], tracks[k][1] - f1_true[1]))
        best_t2 = min(tracks.keys(), key=lambda k: math.hypot(tracks[k][0] - f2_true[0], tracks[k][1] - f2_true[1]))
        if step == 0:
            id_map["F1"] = best_t1
            id_map["F2"] = best_t2
            assert best_t1 != best_t2
        else:
            if best_t1 != id_map["F1"] or best_t2 != id_map["F2"]:
                id_swaps += 1

        if step >= 10:
            errs_f1.append(math.hypot(tracks[best_t1][0] - f1_true[0], tracks[best_t1][1] - f1_true[1]))
            errs_f2.append(math.hypot(tracks[best_t2][0] - f2_true[0], tracks[best_t2][1] - f2_true[1]))

    rms_f1 = math.sqrt(sum(e * e for e in errs_f1) / len(errs_f1))
    rms_f2 = math.sqrt(sum(e * e for e in errs_f2) / len(errs_f2))

    print("\n[2] Ket qua Kiem thu Da diem 240 Hz duoi Nhieu Sac + Nuoc mua (35 khung):")
    print(
        f"  * Tong giot nuoc da phat hien & loai bo : {total_rejected_drops} luot ({false_water_touches} cham gia!)"
    )
    print(
        f"  * Bao toan ID 2 ngon tay (Zero Swap)    : ID_Swaps={id_swaps} (ID_1={id_map['F1']}, ID_2={id_map['F2']})"
    )
    print(
        f"  * Do chinh xac theo doi Sub-Pixel (RMS) : Ngon 1={rms_f1:.4f} mm | Ngon 2={rms_f2:.4f} mm (< 0.35 mm)"
    )

    assert false_water_touches == 0
    assert total_rejected_drops >= 2 * n_frames
    assert id_swaps == 0
    assert rms_f1 < 0.35 and rms_f2 < 0.35

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 219 (CAPSTONE): APPLE / TESLA PCAP TOUCH 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_tesla_pcap_capstone()
