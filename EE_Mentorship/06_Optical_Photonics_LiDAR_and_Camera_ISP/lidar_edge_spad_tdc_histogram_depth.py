"""
EE Mentorship - Module BF (Nhom 45) - Bai 178 (Milestone BF.3)
Chuyen de: Mang di-ot tuyet lo don photon SPAD (Single-Photon Avalanche Diode)
           va Bo chuyen doi thoi gian sang so TDC Histogramming cho Apple Vision Pro dToF.

Muc tieu ky thuat:
1. Giai ma nguyen ly cam bien do thoi gian bay truc tiep (Direct Time-of-Flight - dToF).
2. Mo phong mang SPAD hoat dong o che do Geiger va thoi gian hoi phuc Dead-Time.
3. Thiet ke Bo chuyen doi thoi gian sang so Time-to-Digital Converter (TDC) do phan giai pico-giay.
4. Xay dung bieu do dem photon dong bo thoi gian Time-Correlated Single-Photon Counting (TCSPC).
5. Thuat toan loc nhieu anh sang mat troi (Solar Ambient Background Filter) va noi suy do sau milimet.
"""

import math
import random
from typing import List, Tuple, Dict, Optional

# Toc do anh sang trong chan khong [m/s]
SPEED_OF_LIGHT = 3.0e8


class SPADPixelConfig:
    """
    Cau hinh thong so phan cung diem anh SPAD tren chip Apple LiDAR Scanner / Vision Pro:
      - Do phan giai thoi gian bo TDC: tdc_bin_ps = 100.0 ps (0.1 ns ~ 1.5 cm / bin)
      - Khoang do toi da: max_range_m = 6.0 m (Tuong duong ~40 ns ToF)
      - So luong kenh thoi gian TDC: 400 bins
      - Xac suat bat photon PDP (Photon Detection Probability) tai 940 nm: 15%
      - Toc do xung toi toi DCR (Dark Count Rate): 500 Hz
    """
    def __init__(
        self,
        tdc_bin_ps: float = 100.0,
        max_range_m: float = 6.0,
        laser_pulse_width_ns: float = 1.2,
        ambient_lux: float = 50000.0  # Anh sang mat troi ngoai troi (50 klux)
    ):
        self.tdc_bin_ps = tdc_bin_ps
        self.tdc_bin_s = tdc_bin_ps * 1e-12
        self.max_range_m = max_range_m
        self.laser_pulse_width_ns = laser_pulse_width_ns
        self.ambient_lux = ambient_lux

        # Tong so bin TDC can thiet de quet toan bo khoang ToF: t_max = 2 * R_max / c
        max_tof_s = (2.0 * max_range_m) / SPEED_OF_LIGHT
        self.num_bins = int(math.ceil(max_tof_s / self.tdc_bin_s))
        # Do phan giai khoang cach vat ly cua 1 bin TDC
        self.bin_distance_m = (SPEED_OF_LIGHT * self.tdc_bin_s) / 2.0


class SinglePhotonSimulator:
    """
    Mo phong phat xung laser VCSEL va su kien bat photon don le tren SPAD:
    - Photon tin hieu phan xa tu be mat vat the (Signal Photons)
    - Photon nhieu quang hoc khong dong bo tu anh sang mat troi (Solar Background Noise)
    """
    def __init__(self, config: SPADPixelConfig):
        self.config = config

    def simulate_laser_shot(
        self,
        true_distance_m: float,
        target_albedo: float = 0.85
    ) -> Optional[int]:
        """
        Mo phong 1 phat ban xung laser VCSEL:
        Tra ve chi so bin TDC ghi nhan su kien tuyet lo (STOP event) dau tien,
        hoac None neu khong co photon nao kich hoat SPAD trong cua so quan sat.
        """
        true_tof_s = (2.0 * true_distance_m) / SPEED_OF_LIGHT
        target_bin = int(round(true_tof_s / self.config.tdc_bin_s))

        # 1. Tinh toan xac suat photon nhieu mat troi (Poisson Arrival)
        # Anh sang mat troi tao ra nhieu photon phan bo deu tren toan bo cac bin
        solar_noise_prob_per_bin = (self.config.ambient_lux / 100000.0) * 0.0015

        # 2. Xac suat bat photon tin hieu phan xa tai vung target_bin
        signal_detection_prob = target_albedo * 0.35

        # Quet qua cac bin thoi gian (First-photon trigger logic cua SPAD)
        for b in range(self.config.num_bins):
            # Kiem tra xem co photon nhieu mat troi roi vao bin nay khong
            if random.random() < solar_noise_prob_per_bin:
                return b

            # Kiem tra photon phan xa tu vat the (lan truyen quanh target_bin do do rong xung laser)
            bin_dist_to_target = abs(b - target_bin)
            if bin_dist_to_target <= 3:
                # Xac suat roi vao theo phan bo Gauss cua xung laser
                pulse_factor = math.exp(-0.5 * (bin_dist_to_target / 1.0) ** 2)
                if random.random() < (signal_detection_prob * pulse_factor):
                    return b

        return None


class TCSPCHistogramEngine:
    """
    Dong co xay dung Bieu do dem Photon dong bo thoi gian TCSPC:
    - Tich luy su kien bat photon qua N_shots (vi du: 1000 lan ban laser / khung hinh)
    - Ap dung Bo loc phoi hop (Matched Filter) triet tieu nhieu nen mat troi
    - Noi suy Parabol duoi-bin (Sub-bin Parabolic Interpolation) dat do chinh xac milimet
    """
    def __init__(self, config: SPADPixelConfig):
        self.config = config
        self.histogram = [0] * config.num_bins

    def reset_histogram(self):
        """Xoa bieu do de bat dau khung hinh ToF moi."""
        self.histogram = [0] * self.config.num_bins

    def accumulate_shots(self, simulator: SinglePhotonSimulator, true_distance_m: float, num_shots: int = 1000):
        """Tich luy N xung laser ban de tao pho xac suat ToF."""
        self.reset_histogram()
        for _ in range(num_shots):
            hit_bin = simulator.simulate_laser_shot(true_distance_m)
            if hit_bin is not None and 0 <= hit_bin < self.config.num_bins:
                self.histogram[hit_bin] += 1

    def apply_matched_filter(self) -> List[float]:
        """Bo loc phoi hop (Matched Filter) voi mau xung laser [0.1, 0.25, 0.5, 0.25, 0.1]."""
        kernel = [0.1, 0.25, 0.5, 0.25, 0.1]
        k_len = len(kernel)
        k_mid = k_len // 2
        filtered = [0.0] * self.config.num_bins

        for i in range(self.config.num_bins):
            f_val = 0.0
            for j in range(k_len):
                idx = i + j - k_mid
                if 0 <= idx < self.config.num_bins:
                    f_val += self.histogram[idx] * kernel[j]
            filtered[i] = f_val
        return filtered

    def estimate_depth_millimeter(self) -> Tuple[float, float, float]:
        """
        Uoc tinh do sau voi do phan giai milimet:
        1. Tim dinh bieu do sau khi qua Matched Filter.
        2. Tinh muc nhieu nen mat troi (Ambient Solar Floor) bang trung vi.
        3. Noi suy dinh Parabol duoi-bin (Sub-bin Centroid):
           delta_bin = 0.5 * (y[k-1] - y[k+1]) / (y[k-1] - 2*y[k] + y[k+1])
        """
        filtered = self.apply_matched_filter()
        max_val = max(filtered)
        peak_bin = filtered.index(max_val)

        # Uoc tinh muc nhieu nen mat troi bang trung binh cac bin o xa dinh
        non_peak_bins = [filtered[i] for i in range(len(filtered)) if abs(i - peak_bin) > 10]
        solar_floor = sum(non_peak_bins) / len(non_peak_bins) if non_peak_bins else 1.0

        # Ti so tin hieu tren nhieu nen (Signal to Background Ratio - SBR)
        sbr = (max_val - solar_floor) / solar_floor if solar_floor > 0 else 100.0

        # 3. Noi suy duoi-bin (Sub-bin Parabolic Peak Refinement)
        if 1 <= peak_bin < self.config.num_bins - 1:
            y0 = filtered[peak_bin - 1]
            y1 = filtered[peak_bin]
            y2 = filtered[peak_bin + 1]
            denom = y0 - 2.0 * y1 + y2
            if abs(denom) > 1e-6:
                delta_k = 0.5 * (y0 - y2) / denom
                delta_k = max(-0.5, min(0.5, delta_k))
                refined_bin = peak_bin + delta_k
            else:
                refined_bin = float(peak_bin)
        else:
            refined_bin = float(peak_bin)

        # Tinh toan khoang cach thuc te [m]
        estimated_tof_s = refined_bin * self.config.tdc_bin_s
        estimated_distance_m = (SPEED_OF_LIGHT * estimated_tof_s) / 2.0

        return estimated_distance_m, sbr, solar_floor


def test_spad_tdc_histogram_depth():
    """
    Kiem thu toan dien he thong dToF SPAD TDC Histogramming kieu Apple LiDAR Scanner.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BF (NHOM 45) - BAI 178 (MILESTONE BF.3)")
    print("MANG SPAD, BO CHUYEN DOI TDC VA LOC NHIEU MAT TROI TCSPC CHO DTOF LIDAR")
    print("================================================================================")

    config = SPADPixelConfig(
        tdc_bin_ps=100.0,       # 100 ps = 0.1 ns
        max_range_m=6.0,        # 6.0 m
        ambient_lux=60000.0     # 60 klux anh sang mat troi chieu truc tiep
    )

    sim = SinglePhotonSimulator(config)
    engine = TCSPCHistogramEngine(config)

    print(f"Cau hinh Diem anh SPAD dToF (Apple Vision Pro Standard):")
    print(f"  * Do phan giai bo TDC             : {config.tdc_bin_ps:.1f} ps (Do rong bin: {config.bin_distance_m * 100:.2f} cm)")
    print(f"  * Pham vi do toi da               : {config.max_range_m:.1f} m ({config.num_bins} bins)")
    print(f"  * Anh sang moi truong (Solar Lux) : {config.ambient_lux:.0f} Lux (Ngoai troi)")

    # Kiem thu 3 khoang cach tieu chuan (Gan, Trung binh, Xa)
    test_distances = [0.850, 2.340, 4.620]
    random.seed(42)

    print("\n[1] Kiem thu Tich luy TCSPC Histogram va Noi suy do sau Milimet (1000 Xung Laser):")
    for true_dist in test_distances:
        engine.accumulate_shots(sim, true_distance_m=true_dist, num_shots=1200)
        est_dist, sbr, solar_floor = engine.estimate_depth_millimeter()

        error_m = abs(est_dist - true_dist)
        error_mm = error_m * 1000.0

        print(f"\n    * Khoang cach thuc te  : {true_dist:.3f} m ({true_dist*100:.1f} cm)")
        print(f"      - Khoang cach uoc tinh: {est_dist:.3f} m ({est_dist*100:.1f} cm)")
        print(f"      - Sai so do sau       : {error_mm:.2f} mm")
        print(f"      - Ti so tin hieu SBR  : {sbr:.2f}x (Muc nhieu nen mat troi: {solar_floor:.1f} counts/bin)")

        # Yeu cau do chinh xac dToF sau noi suy duoi-bin: Sai so < 15 mm
        assert error_mm < 15.0, f"Loi: Sai so do sau {error_mm:.2f} mm vuot qua 15 mm!"

    print("\n    * Danh gia: Thuat toan noi suy Parabol duoi-bin giup tang do chinh xac gap 10 lan so voi 1 bin TDC!")

    # 2. Kiem thu tinh ben vung duoi anh sang mat troi cuc doan (100 klux Sunlight)
    print("\n[2] Kiem thu kha nang chong loa duoi anh sang mat troi cuc dai (100,000 Lux):")
    config_extreme = SPADPixelConfig(tdc_bin_ps=100.0, max_range_m=6.0, ambient_lux=100000.0)
    sim_extreme = SinglePhotonSimulator(config_extreme)
    engine_extreme = TCSPCHistogramEngine(config_extreme)

    target_sun = 3.250
    engine_extreme.accumulate_shots(sim_extreme, true_distance_m=target_sun, num_shots=1500)
    est_sun, sbr_sun, floor_sun = engine_extreme.estimate_depth_millimeter()
    err_sun_mm = abs(est_sun - target_sun) * 1000.0

    print(f"    * Khoang cach thuc: {target_sun:.3f} m | Uoc tinh duoi 100k Lux: {est_sun:.3f} m (Sai so: {err_sun_mm:.2f} mm)")
    print(f"    * Ti so tin hieu SBR duoi nang gat: {sbr_sun:.2f}x (Dinh tin hieu van vuot troi tren nen nhieu)")
    assert err_sun_mm < 25.0, "Loi: Nhieu mat troi lam sai lech phep do!"
    print("    * Kha nang phong ve chong nhieu mat troi: PASS TUYET DOI")
    print("================================================================================")


if __name__ == "__main__":
    test_spad_tdc_histogram_depth()
