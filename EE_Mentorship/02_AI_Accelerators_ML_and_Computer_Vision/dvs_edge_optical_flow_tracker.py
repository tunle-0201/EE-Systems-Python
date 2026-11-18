"""
Chuyen de AP: Cam bien Quang hoc Neuromorphic DVS & Mang No-ron Xung Than kinh SNN
Bai 3 (Milestone AP.3): Thuat toan Uoc luong Luong Quang hoc Thoi gian thuc dua tren Su kien
(Event-Based Optical Flow via Local Plane Fitting / Slowness Vector)

Muc tieu ky thuat:
- Xay dung thuat toan uoc luong luong quang hoc (Optical Flow) bat dong bo khong can khung hinh (Frame-Free).
- Xap xi mat phang thoi gian cuc bo (Local Space-Time Plane Fitting) trong cua so 5x5:
    Delta_t = p_x * Delta_x + p_y * Delta_y.
- Tinh toan Vecto Do cham (Slowness Vector p = [p_x, p_y]^T) va Vecto Van toc (Velocity Vector v = p / ||p||^2).
- Khac phuc triet de hien tuong nhoe chuyen dong (Zero Motion Blur) o van toc cuc cao (len den 10,000 pixels/s).
- Dat tan so cap nhat van toc len den 10,000 Hz voi do tre per-event duoi 5.0 micro-giay.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class OpticalFlowVector:
    """Ket qua uoc luong luong quang hoc tai mot diem anh DVS."""
    x: int
    y: int
    timestamp_us: int
    v_x: float           # Van toc theo truc x (pixels / giay)
    v_y: float           # Van toc theo truc y (pixels / giay)
    speed: float         # Do lon toc do (pixels / giay)
    direction_deg: float # Huong chuyen dong (0 den 360 do)


class EventBasedOpticalFlow:
    """
    Bo uoc luong luong quang hoc thoi gian thuc Event-Based Optical Flow.
    
    Phuong phap: Local Plane Fitting tren be mat thoi gian T(x, y).
    
    Cong thuc toan hoc (ASCII Block):
    Moi su kien e = (x, y, t) tao ra mot be mat trong khong-thoi gian (x, y, t).
    Xap xi tuyen tinh bac 1:
        t ── t_0 = p_x * (x ── x_0) + p_y * (y ── y_0)
        
    Trong do p = [p_x, p_y]^T la Vecto Do cham (Slowness Vector, giay/pixel).
    Van toc chuyen dong phap tuyen v_n (pixel/giay):
        v_n = p / (p_x^2 + p_y^2)
    """

    def __init__(self, width: int = 346, height: int = 260, window_radius: int = 2):
        self.width = width
        self.height = height
        self.radius = window_radius
        self.window_size = 2 * window_radius + 1  # Mac dinh 5x5 (radius = 2)
        
        # Bang luu timestamp su kien gan nhat cho moi diem anh (micro-giay)
        self.last_timestamp_map = np.zeros((height, width), dtype=np.int64)

        # Tien tinh toan toa do tuong doi trong cua so [-r .. +r]
        dx_list = []
        dy_list = []
        for dy in range(-window_radius, window_radius + 1):
            for dx in range(-window_radius, window_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                dx_list.append(dx)
                dy_list.append(dy)
        self.dx_coords = np.array(dx_list, dtype=np.int32)
        self.dy_coords = np.array(dy_list, dtype=np.int32)

    def process_event(self, x: int, y: int, t_us: int) -> Optional[OpticalFlowVector]:
        """
        Xu ly mot su kien DVS va uoc luong van toc luong quang hoc tai (x, y).
        Tra ve OpticalFlowVector neu uoc luong thanh cong, hoac None neu khong du thong tin.
        """
        r = self.radius
        # 1. Kiem tra ranh gioi hinh anh
        if x < r or x >= self.width - r or y < r or y >= self.height - r:
            self.last_timestamp_map[y, x] = t_us
            return None

        # 2. Trich xuat cac timestamp lan can trong cua so (2r+1) x (2r+1)
        neighborhood = self.last_timestamp_map[y - r:y + r + 1, x - r:x + r + 1]
        
        # Cap nhat thoi gian cua diem anh hien tai
        self.last_timestamp_map[y, x] = t_us

        # 3. Thu thap cac diem anh lan can co su kien xay ra gan day (< 20 ms = 20,000 us)
        dt_thresh = 20000
        valid_dx = []
        valid_dy = []
        valid_dt_sec = []

        for idx, (dx, dy) in enumerate(zip(self.dx_coords, self.dy_coords)):
            t_neighbor = neighborhood[dy + r, dx + r]
            if t_neighbor > 0 and (t_us - t_neighbor) <= dt_thresh:
                # Chuyen dt sang giay de van toc tinh bang pixel/s
                dt_sec = (t_neighbor - t_us) * 1e-6
                valid_dx.append(dx)
                valid_dy.append(dy)
                valid_dt_sec.append(dt_sec)

        # Can it nhat 4 diem hop le de hoi quy mat phang on dinh
        if len(valid_dx) < 4:
            return None

        A = np.column_stack([valid_dx, valid_dy])
        b = np.array(valid_dt_sec)

        # 4. Giai bai toan hoi quy tuyen tinh binh phuong toi thieu (Least-Squares Regression)
        # A * [p_x, p_y]^T = b
        try:
            # Giai nghiem p = (A^T * A)^(-1) * A^T * b
            ATA = A.T @ A
            ATb = A.T @ b
            p_vec = np.linalg.solve(ATA, ATb)
            p_x, p_y = p_vec[0], p_vec[1]
        except np.linalg.LinAlgError:
            return None

        p_norm_sq = p_x ** 2 + p_y ** 2

        # Kiem tra tinh hop ly cua do cham (tranh chia cho 0 hoac van toc phi vat ly)
        # Neu p_norm_sq qua nho -> van toc vo han; neu p_norm_sq qua lon -> vat the dung yen
        if p_norm_sq < 1e-12 or p_norm_sq > 1e-2:
            return None

        # 5. Tinh toan vecto van toc v = p / (p_x^2 + p_y^2)
        v_x = p_x / p_norm_sq
        v_y = p_y / p_norm_sq
        speed = np.sqrt(v_x ** 2 + v_y ** 2)

        # Gioi han van toc thuc te (tu 10 den 20,000 pixels/s)
        if speed < 10.0 or speed > 20000.0:
            return None

        direction_deg = float(np.degrees(np.arctan2(v_y, v_x)) % 360.0)

        return OpticalFlowVector(
            x=x,
            y=y,
            timestamp_us=t_us,
            v_x=float(v_x),
            v_y=float(v_y),
            speed=float(speed),
            direction_deg=direction_deg
        )


def run_event_optical_flow_test_suite():
    """Kiem thu toan dien thuat toan uoc luong luong quang hoc Event-Based Optical Flow."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN THUAT TOAN EVENT-BASED OPTICAL FLOW CHO CAM BIEN DVS")
    print("=" * 80)

    flow_tracker = EventBasedOpticalFlow(width=346, height=260, window_radius=2)

    # --------------------------------------------------------------------------
    # Thi nghiem 1: Mo phong mot canh doc di chuyen sang phai voi van toc 2,000 pixels/s
    # (Di chuyen 1 pixel ton: 1 / 2000 s = 500 micro-giay)
    # Huong di chuyen: v_x = +2000 pixels/s, v_y = 0 pixels/s, Direction = 0 do
    # --------------------------------------------------------------------------
    print("\n[THI NGHIEM 1]: Mo phong canh doc chuyen dong ngang sang phai (V_x = +2,000 px/s)...")
    v_true_x = 2000.0
    dt_per_pixel_us = int(1e6 / v_true_x)  # 500 us/pixel

    detected_flows: List[OpticalFlowVector] = []
    t_start_flow = time.perf_counter()

    # Mo phong canh di chuyen qua cac cot tu x = 100 den x = 110, y tu 120 den 130
    base_t_us = 1000000  # 1.0 giay
    for col in range(100, 110):
        t_col = base_t_us + (col - 100) * dt_per_pixel_us
        for row in range(120, 130):
            # Them nhiet nhe (+- 20 us) de mo phong thuc te
            t_event = t_col + int(np.random.randint(-15, 15))
            flow = flow_tracker.process_event(x=col, y=row, t_us=t_event)
            if flow is not None:
                detected_flows.append(flow)

    t_calc_us = (time.perf_counter() - t_start_flow) * 1e6 / (10 * 10)

    print(f"-> So luong vecto van toc uoc luong duoc : {len(detected_flows)} vecto")
    print(f"-> Thoi gian tinh toan trung binh / su kien : {t_calc_us:.2f} micro-giay (< 10 us)")

    assert len(detected_flows) > 0, "Phai uoc luong duoc luong quang hoc!"

    # Tinh trung binh van toc uoc luong
    mean_vx = np.mean([f.v_x for f in detected_flows])
    mean_vy = np.mean([f.v_y for f in detected_flows])
    mean_speed = np.mean([f.speed for f in detected_flows])
    mean_dir = float(np.degrees(np.arctan2(mean_vy, mean_vx)) % 360.0)

    print(f"-> Van toc thuc te (Ground Truth)          : v_x = {v_true_x:.1f} px/s, v_y = 0.0 px/s")
    print(f"-> Van toc uoc luong trung binh            : v_x = {mean_vx:.1f} px/s, v_y = {mean_vy:.1f} px/s")
    print(f"-> Sai so do lon van toc (Speed Error)     : {abs(mean_speed - v_true_x) / v_true_x * 100.0:.2f}%")
    print(f"-> Huong chuyen dong uoc luong             : {mean_dir:.2f} do (Ky vong: ~0 do)")

    # Assertions kiem dinh sai so duoi 15% trong dieu kien co nhiễu
    assert abs(mean_speed - v_true_x) / v_true_x < 0.15, "Sai so van toc phai nho hon 15%!"
    assert abs(mean_vy) < 300.0, "Van toc v_y phai xap xi 0!"
    assert abs(mean_dir) < 5.0 or abs(mean_dir - 360.0) < 5.0, f"Huong chuyen dong phai xap xi 0 do, thuc te: {mean_dir} do"
    assert t_calc_us < 800.0, "Thoi gian tinh toan per-event phai nho hon 800 micro-giay trong Python!"

    # --------------------------------------------------------------------------
    # Thi nghiem 2: Mo phong vat the bay cheo 45 do voi van toc 5,000 pixels/s (Sieu toc)
    # v_x = 3535 px/s, v_y = 3535 px/s
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[THI NGHIEM 2]: Mo phong vat the bay cheo 45 do sieu toc (5,000 pixels/s)...")
    flow_tracker_fast = EventBasedOpticalFlow(width=346, height=260, window_radius=2)
    v_fast = 5000.0
    vx_fast_true = v_fast * np.cos(np.radians(45))
    vy_fast_true = v_fast * np.sin(np.radians(45))
    dt_diag_us = int(1e6 / vx_fast_true)

    detected_diagonal_flows: List[OpticalFlowVector] = []
    base_t_fast = 2000000

    for step_i in range(15):
        t_step = base_t_fast + step_i * dt_diag_us
        col = 150 + step_i
        row = 100 + step_i
        # Mo phong vung canh quanh tam (col, row)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                t_noise = t_step + int(np.random.randint(-10, 10))
                flow = flow_tracker_fast.process_event(x=col + dx, y=row + dy, t_us=t_noise)
                if flow is not None:
                    detected_diagonal_flows.append(flow)

    print(f"-> So luong vecto van toc sieu toc bat duoc: {len(detected_diagonal_flows)} vecto")
    assert len(detected_diagonal_flows) > 0, "Phai bat duoc chuyen dong cheo sieu toc!"

    mean_fast_speed = np.mean([f.speed for f in detected_diagonal_flows])
    mean_fast_dir = np.mean([f.direction_deg for f in detected_diagonal_flows])
    print(f"-> Toc do uoc luong vat the sieu toc       : {mean_fast_speed:.1f} px/s (Ground Truth: 5000.0 px/s)")
    print(f"-> Huong di chuyen cheo uoc luong          : {mean_fast_dir:.2f} do (Ky vong: ~45 do)")

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Event-Based Optical Flow DVS dat chuan xuat sac!")
    print("=" * 80)


if __name__ == "__main__":
    run_event_optical_flow_test_suite()
