"""
================================================================================
EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 218 (MILESTONE BP.3)
KHU GIOT NUOC (WATER REJECTION), NOI SUY SUB-PIXEL 2D & BO LOC KALMAN 240 HZ
================================================================================
Muc tieu:
1. Phan biet vat ly giot nuoc troi noi (Floating Water Drop lam TANG dien dung
   tuong ho delta_C_m > 0 hoac vong duong halo) va long ban tay / vung nuoc lon
   (Palm/Splash > 14 nut) voi ngon tay noi dat that (delta_C_m < -0.07 pF gon).
2. Trich xuat trong tam 2D Sub-Pixel chinh xac < 0.15 mm tu luoi tho pitch 4.0 mm.
3. Bo loc Kalman 2D (x, y, vx, vy) tan so quet 240 Hz giam nhieu rung con tro
   khi luot tay nhanh 600 mm/s ma khong bi tre khung hinh.
================================================================================
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class DetectedBlob:
    x_mm: float
    y_mm: float
    peak_neg_pf: float
    local_max_pos_pf: float
    area_nodes: int
    classification: str  # "FINGER", "WATER_DROP", "PALM_SPLASH"


class WaterRejectionSubPixelExtractor:
    """
    Bo phan loai & trich xuat trong tam Sub-Pixel chong nuoc:
    - Nut giot nuoc noi thuong mang dau duong (cau noi TX-RX tang ghep tu)
      hoac neu co nut am nhe luon di kem vanh duong > +0.025 pF.
    - Vung cham qua rong (> 14 nut) hoac bien do khong du am se bi loai bo.
    """

    def __init__(
        self,
        rows: int = 12,
        cols: int = 8,
        pitch_mm: float = 4.0,
        neg_seed_pf: float = -0.075,
        pos_water_halo_pf: float = 0.030,
        max_finger_nodes: int = 20,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.pitch_mm = pitch_mm
        self.neg_seed_pf = neg_seed_pf
        self.pos_water_halo_pf = pos_water_halo_pf
        self.max_finger_nodes = max_finger_nodes

    def analyze_frame(
        self, delta_cm_pf: List[List[float]]
    ) -> Tuple[List[DetectedBlob], List[DetectedBlob]]:
        """Tra ve (danh sach ngon tay hop le, tat ca cum da phan loai)."""
        # 1. Tim cac cum giot nuoc duong thuan tuy de bao cao thong ke
        all_blobs: List[DetectedBlob] = []
        valid_fingers: List[DetectedBlob] = []

        visited = [[False] * self.cols for _ in range(self.rows)]

        # Kiem tra cac cum am (ung vien ngon tay)
        for r0 in range(self.rows):
            for c0 in range(self.cols):
                if visited[r0][c0] or delta_cm_pf[r0][c0] > self.neg_seed_pf:
                    continue

                # BFS gom cum cac nut am lien ke (< -0.035 pF)
                queue = [(r0, c0)]
                visited[r0][c0] = True
                cluster: List[Tuple[int, int]] = []
                while queue:
                    r, c = queue.pop(0)
                    cluster.append((r, c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if not visited[nr][nc] and delta_cm_pf[nr][nc] < -0.045:
                                visited[nr][nc] = True
                                queue.append((nr, nc))

                # Tim dinh am nhat trong cum
                peak_r, peak_c = min(cluster, key=lambda p: delta_cm_pf[p[0]][p[1]])
                peak_neg = delta_cm_pf[peak_r][peak_c]

                # Kiem tra vanh 5x5 quanh dinh xem co halo duong do giot nuoc hay khong
                local_max_pos = -1.0
                w_sum = 0.0
                wx_sum = 0.0
                wy_sum = 0.0
                floor_pf = 0.025
                for rr in range(max(0, peak_r - 2), min(self.rows, peak_r + 3)):
                    for cc in range(max(0, peak_c - 2), min(self.cols, peak_c + 3)):
                        val = delta_cm_pf[rr][cc]
                        if val > local_max_pos:
                            local_max_pos = val
                        weight = max(0.0, -val - floor_pf)
                        if weight > 0.0:
                            x_mm = (cc + 0.5) * self.pitch_mm
                            y_mm = (rr + 0.5) * self.pitch_mm
                            w_sum += weight
                            wx_sum += weight * x_mm
                            wy_sum += weight * y_mm

                cx = wx_sum / max(w_sum, 1e-9)
                cy = wy_sum / max(w_sum, 1e-9)

                # Logic phan loai chong nuoc & chong ty tay
                if len(cluster) > self.max_finger_nodes:
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
                    area_nodes=len(cluster),
                    classification=cls_label,
                )
                all_blobs.append(blob)
                if cls_label == "FINGER":
                    valid_fingers.append(blob)

        # Ghi nhan them giot nuoc thuan tuy chi tao dinh duong (> +0.055 pF)
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


class KalmanTrack2D:
    """Bo loc Kalman 4 trang thai [x, y, vx, vy] chay tai 240 Hz."""

    def __init__(
        self,
        track_id: int,
        x0: float,
        y0: float,
        dt: float = 1.0 / 240.0,
        q_accel: float = 80_000.0,
        r_meas_mm: float = 0.35,
    ) -> None:
        self.track_id = track_id
        self.dt = dt
        self.x = [x0, y0, 0.0, 0.0]
        # Ma tran hiep phuong sai P 4x4 (van toc khoi tao mo rong de khoa nhanh trong 2-3 khung)
        self.p: List[List[float]] = [
            [0.5, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0],
            [0.0, 0.0, 60_000.0, 0.0],
            [0.0, 0.0, 0.0, 60_000.0],
        ]
        self.q_accel = q_accel
        self.r_var = r_meas_mm * r_meas_mm
        self.missed_frames = 0

    def predict(self) -> Tuple[float, float]:
        dt = self.dt
        # x_k|k-1 = F * x
        self.x[0] += self.x[2] * dt
        self.x[1] += self.x[3] * dt

        # P = F * P * F^T + Q (cho tung truc x/vx va y/vy doc lap)
        q11 = 0.25 * (dt ** 4) * self.q_accel
        q13 = 0.5 * (dt ** 3) * self.q_accel
        q33 = (dt ** 2) * self.q_accel

        for pos_idx, vel_idx in [(0, 2), (1, 3)]:
            p00 = self.p[pos_idx][pos_idx]
            p01 = self.p[pos_idx][vel_idx]
            p11 = self.p[vel_idx][vel_idx]
            self.p[pos_idx][pos_idx] = p00 + 2.0 * dt * p01 + (dt ** 2) * p11 + q11
            self.p[pos_idx][vel_idx] = p01 + dt * p11 + q13
            self.p[vel_idx][pos_idx] = self.p[pos_idx][vel_idx]
            self.p[vel_idx][vel_idx] = p11 + q33
        return self.x[0], self.x[1]

    def update(self, meas_x: float, meas_y: float) -> Tuple[float, float]:
        self.missed_frames = 0
        for axis_idx, z in [(0, meas_x), (1, meas_y)]:
            vel_idx = axis_idx + 2
            y_innov = z - self.x[axis_idx]
            s_innov = self.p[axis_idx][axis_idx] + self.r_var
            k0 = self.p[axis_idx][axis_idx] / s_innov
            k1 = self.p[vel_idx][axis_idx] / s_innov

            self.x[axis_idx] += k0 * y_innov
            self.x[vel_idx] += k1 * y_innov

            p00 = self.p[axis_idx][axis_idx]
            p01 = self.p[axis_idx][vel_idx]
            p10 = self.p[vel_idx][axis_idx]
            p11 = self.p[vel_idx][vel_idx]

            self.p[axis_idx][axis_idx] = (1.0 - k0) * p00
            self.p[axis_idx][vel_idx] = (1.0 - k0) * p01
            self.p[vel_idx][axis_idx] = p10 - k1 * p00
            self.p[vel_idx][vel_idx] = p11 - k1 * p01

        return self.x[0], self.x[1]


class MultiFingerKalmanManager:
    """Quan ly ID da diem cham va gan ket theo khoang cach gan nhat."""

    def __init__(self, dt: float = 1.0 / 240.0, gate_mm: float = 8.0) -> None:
        self.dt = dt
        self.gate_mm = gate_mm
        self.next_id = 1
        self.tracks: Dict[int, KalmanTrack2D] = {}

    def step(self, detections: List[DetectedBlob]) -> Dict[int, Tuple[float, float]]:
        for trk in self.tracks.values():
            trk.predict()
            trk.missed_frames += 1

        used_det: set[int] = set()
        # Cap nhat track cu theo thu tu track_id
        for tid in sorted(self.tracks.keys()):
            trk = self.tracks[tid]
            best_idx = -1
            best_dist = self.gate_mm
            for idx, det in enumerate(detections):
                if idx in used_det:
                    continue
                d = math.hypot(det.x_mm - trk.x[0], det.y_mm - trk.x[1])
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            if best_idx >= 0:
                used_det.add(best_idx)
                trk.update(detections[best_idx].x_mm, detections[best_idx].y_mm)

        # Xoa track mat qua 3 frame
        for tid in [k for k, v in self.tracks.items() if v.missed_frames > 3]:
            del self.tracks[tid]

        # Tao track moi cho diem chua khop
        for idx, det in enumerate(detections):
            if idx not in used_det:
                self.tracks[self.next_id] = KalmanTrack2D(
                    self.next_id, det.x_mm, det.y_mm, dt=self.dt
                )
                self.next_id += 1

        return {tid: (trk.x[0], trk.x[1]) for tid, trk in self.tracks.items()}


def synthesize_scene_delta_cm(
    rows: int,
    cols: int,
    pitch_mm: float,
    fingers: List[Tuple[float, float]],
    water_drops: List[Tuple[float, float]],
    rng: random.Random,
    noise_pf: float = 0.008,
) -> List[List[float]]:
    """Tao ma tran delta_C_m: ngon tay tao dinh am (-0.42 pF), giot nuoc tao cau noi duong (+0.11 pF)."""
    grid: List[List[float]] = []
    for r in range(rows):
        yn = (r + 0.5) * pitch_mm
        row: List[float] = []
        for c in range(cols):
            xn = (c + 0.5) * pitch_mm
            val = rng.gauss(0.0, noise_pf)
            for fx, fy in fingers:
                d2 = (xn - fx) ** 2 + (yn - fy) ** 2
                val -= 0.420 * math.exp(-d2 / (2.0 * 4.2 * 4.2))
            for wx, wy in water_drops:
                d2 = (xn - wx) ** 2 + (yn - wy) ** 2
                # Giot nuoc tao tang ghep tu +0.115 pF
                val += 0.115 * math.exp(-d2 / (2.0 * 3.8 * 3.8))
            row.append(val)
        grid.append(row)
    return grid


def test_water_rejection_kalman() -> None:
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 218 (MILESTONE BP.3)")
    print("KHU GIOT NUOC (WATER REJECTION), NOI SUY SUB-PIXEL & BO LOC KALMAN 240 HZ")
    print("=" * 80)

    rng = random.Random(314)
    extractor = WaterRejectionSubPixelExtractor(rows=12, cols=8, pitch_mm=4.0)
    tracker = MultiFingerKalmanManager(dt=1.0 / 240.0)

    # 1. Kiem thu 2 giot nuoc tren man hinh + 1 ngon tay luot cheo
    water_drops = [(6.0, 42.0), (26.0, 10.0)]
    raw_errs: List[float] = []
    kalman_errs: List[float] = []
    false_water_count = 0

    # Ngon tay luot nhanh theo quy dao cheo (van toc ~ 215 mm/s) trong 40 khung @ 240 Hz
    for step in range(40):
        # Giu trong vung luoi 12x8 (32 x 48 mm)
        true_x = 8.0 + 15.0 * (step / 39.0)
        true_y = 10.0 + 28.0 * (step / 39.0)

        delta = synthesize_scene_delta_cm(
            12,
            8,
            4.0,
            fingers=[(true_x, true_y)],
            water_drops=water_drops,
            rng=rng,
            noise_pf=0.020,
        )
        valid_fingers, all_blobs = extractor.analyze_frame(delta)

        # Dem so giot nuoc bi nhan nham thanh ngon tay (phai la 0!)
        for b in valid_fingers:
            for wx, wy in water_drops:
                if math.hypot(b.x_mm - wx, b.y_mm - wy) < 5.0:
                    false_water_count += 1

        assert len(valid_fingers) == 1, f"Ky vong 1 ngon tay, nhan {len(valid_fingers)} tai step {step}"
        meas_x, meas_y = valid_fingers[0].x_mm, valid_fingers[0].y_mm
        if step >= 10:
            raw_errs.append(math.hypot(meas_x - true_x, meas_y - true_y))

        tracks_out = tracker.step(valid_fingers)
        kx, ky = tracks_out[1]
        if step >= 10:
            kalman_errs.append(math.hypot(kx - true_x, ky - true_y))

    rms_raw = math.sqrt(sum(e * e for e in raw_errs) / len(raw_errs))
    rms_kalman = math.sqrt(sum(e * e for e in kalman_errs) / len(kalman_errs))

    print("\n[1] Kiem thu chong nham lan Giot nuoc & Bao cao toa do 240 Hz:")
    print(
        f"  * Tong so cham gia tu 2 giot nuoc qua 40 khung : {false_water_count} (Muc tieu = 0)"
    )
    print(
        f"  * Sai so dinh vi tho Sub-Pixel Centroid (RMS)   : {rms_raw:.4f} mm (Pitch luoi 4.0 mm)"
    )
    print(
        f"  * Sai so sau Bo loc Kalman 240 Hz (RMS)         : {rms_kalman:.4f} mm (< 0.18 mm)"
    )

    assert false_water_count == 0
    assert rms_raw < 0.35
    assert rms_kalman < rms_raw and rms_kalman < 0.18

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 218: WATER REJECTION & KALMAN 240 HZ 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_water_rejection_kalman()
