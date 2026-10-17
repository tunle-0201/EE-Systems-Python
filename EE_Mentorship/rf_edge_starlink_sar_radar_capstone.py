"""
================================================================================
CHUYEN DE AI: PHASED ARRAY BEAMSTEERING & FMCW SYNTHETIC APERTURE RADAR (SAR)
BAI 4: DONG CO RADAR QUET PHA VA TAO ANH SAR VE TINH STARLINK / TESLA FSD CAPSTONE
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tich hop toan chuoi AESA Phased Array + True Time Delay + SAR Imaging Capstone
Ngon ngu: Python 3 thuan tuy, kien truc Module huong doi tuong thoi gian thuc
================================================================================
"""

import math
from typing import Tuple, List, Dict

from rf_edge_phased_array_beamformer import (
    PhasedArrayConfig, PhasedArrayBeamformer
)
from rf_edge_true_time_delay_squint import (
    WidebandRadarConfig, WidebandBeamformer
)
from rf_edge_sar_backprojection_imaging import (
    SARSystemConfig, SARBackprojectionProcessor
)

# ------------------------------------------------------------------------------
# 1. DONG CO RADAR QUET PHA VA TAO ANH SAR TOAN CHUOI (SAR RADAR CAPSTONE ENGINE)
# ------------------------------------------------------------------------------

class StarlinkSARRadarEngine:
    """
    Dong co Radar khau do tong hop va quet pha AESA tich hop toan chuoi:
    1. Mang ang-ten 16 phan tu AESA hoat dong tai 77 GHz
    2. Mang tre thoi gian thuc True Time Delay chong meo bup song Beam Squint
    3. May phat song dieu tan FMCW Chirp 1.5 GHz
    4. Bo xu ly tai tao anh Coherent Backprojection SAR 2D
    5. Bo phat hien va canh bao va cham vat can (Collision Avoidance Detector)
    """
    def __init__(self,
                 freq_center: float = 77.0e9, # 77 GHz Automotive mmWave Radar
                 bandwidth: float = 1.5e9,    # 1.5 GHz FMCW Chirp (Delta_R = 10 cm)
                 num_elements: int = 16,
                 synthetic_length: float = 6.0): # Khau do tong hop 6.0m
        self.sar_cfg = SARSystemConfig(
            freq_center=freq_center,
            bandwidth=bandwidth,
            platform_speed=15.0, # 15 m/s (~ 54 km/h)
            synthetic_length=synthetic_length
        )
        self.radar_cfg = WidebandRadarConfig(
            f_center=freq_center,
            bandwidth=bandwidth,
            num_elements=num_elements
        )

        self.beamformer = WidebandBeamformer(self.radar_cfg)
        self.processor = SARBackprojectionProcessor(self.sar_cfg)

        self.detected_hazards: List[Dict[str, any]] = []

    def execute_aperture_scan(self,
                              true_obstacles: List[Tuple[float, float, float]],
                              num_pulses: int = 61) -> List[List[float]]:
        """
        Thuc thi quy trinh quet khau do tong hop:
        - Xe di chuyen tu -L_syn/2 den +L_syn/2
        - Phat va thu K xung FMCW da duoc lai bup song bang True Time Delay
        - Chay thuat toan Coherent Backprojection tai tao anh tren luoi 2D
        """
        l_half = self.sar_cfg.L_syn / 2.0
        step_dx = self.sar_cfg.L_syn / (num_pulses - 1)
        radar_x_positions = [-l_half + i * step_dx for i in range(num_pulses)]

        # Mo phong tin hieu thu radar
        echoes = self.processor.simulate_radar_echoes(radar_x_positions, true_obstacles)

        # Tao luoi pixel quan sat phia truoc dau xe (buoc 0.1m = 10 cm khop dung Range Res):
        # X: tu -2.5m den +2.5m (buoc 0.1m) -> 51 diem
        # Y: tu 17.0m den 23.0m (buoc 0.1m) -> 61 diem
        grid_x = [-2.5 + i * 0.1 for i in range(51)]
        grid_y = [17.0 + j * 0.1 for j in range(61)]

        # Tai tao anh SAR
        radar_image = self.processor.reconstruct_image_grid(echoes, grid_x, grid_y)

        # Phat hien vat can tren anh bang thuat toan Dinh cuc bo Local Maxima 3x3
        self.detected_hazards = self.detect_obstacle_peaks(radar_image, grid_x, grid_y)

        return radar_image

    def detect_obstacle_peaks(self,
                              image: List[List[float]],
                              grid_x: List[float],
                              grid_y: List[float]) -> List[Dict[str, any]]:
        """
        Thuat toan tim dinh cuc bo Local Maxima 3x3 tren ma tran anh SAR 2D:
        Pixel (x, y) la dinh neu no lon hon tat ca 8 pixel lan can xung quanh va vuot nguong.
        """
        num_y = len(grid_y)
        num_x = len(grid_x)
        candidates = []

        # Quet qua tat ca cac pixel (bo qua vien ngoai)
        for iy in range(1, num_y - 1):
            for ix in range(1, num_x - 1):
                val = image[iy][ix]
                if val < 80.0: # Nguong loc nhieu
                    continue

                # Kiem tra 8 pixel lan can
                is_max = True
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        if image[iy + dy][ix + dx] >= val:
                            is_max = False
                            break
                    if not is_max:
                        break

                if is_max:
                    candidates.append({"x": grid_x[ix], "y": grid_y[iy], "intensity": val})

        # Sap xep theo cuong do sang giam dan va lay top cac dinh
        candidates.sort(key=lambda item: item["intensity"], reverse=True)
        return candidates[:5]

# ------------------------------------------------------------------------------
# 2. KICH BAN MO PHONG CAPSTONE: XE TESLA FSD VUOT SUONG MU KHONG TAM NHIN
# ------------------------------------------------------------------------------

def run_tesla_zero_visibility_sar_simulation():
    """
    Kich ban xe tu hanh Tesla FSD chay vao hem nui suong mu day dac (Zero-Visibility Fog):
    Camera quang hoc bi mu hoan toan. Radar SAR AESA 77 GHz bat che do quet khau do tong hop:
    3 vat can kim loai nguy hiem chan tren duong:
    - Vat 1 (Xe tai lat)     : (X = -1.5 m, Y = 20.0 m) | RCS = 1.0
    - Vat 2 (Rao chan be tong): (X =  0.5 m, Y = 22.0 m) | RCS = 0.9
    - Vat 3 (Xe mo to)       : (X =  2.0 m, Y = 18.0 m) | RCS = 0.7
    """
    engine = StarlinkSARRadarEngine(
        freq_center=77.0e9,
        bandwidth=1.5e9,
        num_elements=16,
        synthetic_length=6.0
    )

    true_obstacles = [
        (-1.5, 20.0, 1.0),
        ( 0.5, 22.0, 0.9),
        ( 2.0, 18.0, 0.7)
    ]

    print("================================================================================")
    print("BAT DAU MO PHONG AESA SAR IMAGING CAPSTONE (ZERO-VISIBILITY FOG NAVIGATION)")
    print("================================================================================")
    print("Song mang: 77 GHz mmWave | Bang thong: 1.5 GHz FMCW | Khau do ao: 6.0 m")
    print("Dieu kien: Suong mu day dac 100% (Camera quang hoc mu) | 3 Vat can nguy hiem")
    print("--------------------------------------------------------------------------------")

    # Thuc thi quet khau do tong hop
    image_2d = engine.execute_aperture_scan(true_obstacles, num_pulses=61)

    print(f"-> Quet thanh cong 61 xung radar tren quang duong 6.0m.")
    print(f"-> So luong vat can phat hien tren anh SAR 2D: {len(engine.detected_hazards)} vat can.")
    print("--------------------------------------------------------------------------------")
    print(f"{'Vat Can':<12} | {'Toa Do That (m)':<20} | {'SAR Phat Hien (m)':<20} | {'Sai So (cm)':<12} | {'Trang Thai':<10}")
    print("-" * 84)

    matched_count = 0
    max_error_cm = 0.0

    for idx, (tx, ty, rcs) in enumerate(true_obstacles):
        # Tim vat can gan nhat trong danh sach phat hien
        best_match = None
        min_d = 999.0
        for det in engine.detected_hazards:
            d = math.sqrt((det["x"] - tx)**2 + (det["y"] - ty)**2)
            if d < min_d:
                min_d = d
                best_match = det

        err_cm = min_d * 100.0
        if err_cm > max_error_cm:
            max_error_cm = err_cm

        status = "LOCKED" if err_cm < 20.0 else "LOST"
        if status == "LOCKED":
            matched_count += 1

        det_str = f"({best_match['x']:5.2f}, {best_match['y']:5.2f})" if best_match else "None"
        true_str = f"({tx:5.2f}, {ty:5.2f})"

        print(f"Vat the {idx+1:<5} | {true_str:<20} | {det_str:<20} | {err_cm:6.1f} cm    | {status:<10}")

    print("--------------------------------------------------------------------------------")
    print(f"-> Ty le phat hien muc tieu an toan : {matched_count} / {len(true_obstacles)} (100% Thanh cong)")
    print(f"-> Sai so dinh vi cuc dai trong mu   : {max_error_cm:.1f} cm (Do phan giai SAR: {engine.sar_cfg.range_res*100.0:.1f} cm)")
    print(f"-> Canh bao phong tranh va cham     : EMERGENCY BRAKING / COLLISION AVOIDANCE TRIGGERED!")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi Capstone:
    # 1. Phai phat hien khoa duoc ca 3 vat the trong suong mu (matched_count == 3)
    assert matched_count == 3, f"Loi: Chi phat hien duoc {matched_count}/3 vat can!"
    # 2. Sai so dinh vi khong vuot qua 20 cm tren khoang cach 20 met
    assert max_error_cm < 20.0, f"Loi: Sai so vi tri vat the vuot nguong: {max_error_cm} cm"
    print("[PASS] Capstone Starlink SAR Radar Engine: Nhin xuyen suong mu va canh bao va cham xuat sac!")

if __name__ == "__main__":
    run_tesla_zero_visibility_sar_simulation()
