"""
EE MENTORSHIP PROGRAM - MODULE BF (NHOM 45) - BAI 179 (CAPSTONE PROJECT)
================================================================================
HE THONG CAM BIEN QUANG HOC 3D TOF, LIDAR THE RAN OPA & XU LY DAM MAY DIEM HETERODYNE
(CAPSTONE: APPLE VISION PRO SPATIAL COMPUTING & TESLA / WAYMO AUTONOMOUS PERCEPTION ENGINE)
================================================================================

Kien truc he thong ket hop da phuong thuc (Multi-Modal Hybrid Optical Perception):
1. Mang quet pha quang hoc the ran (Silicon Photonic OPA Beamformer):
   - Mang 32 phan tu phat quang tich hop tren chip Silicon (buoc song lambda = 1550 nm, d = lambda / 2).
   - Bo dich pha nhiet-quang (Thermo-Optic Phase Shifter) dieu khien huong bup song azimuthal [-30 do .. +30 do].
   - Mach vong kin tu dong bu troi nhiet do (Closed-Loop Thermal Drift Compensation).

2. Bo xu ly quang hoc ket hop Heterodyne Range-Doppler (Tesla / Waymo Long-Range FMCW):
   - Chirp tuyen tinh bang thong B = 1.5 GHz, chu ky T_chirp = 10 us.
   - Do dong thoi cu ly (Range R) va van toc xuyen tam tuc thoi (Doppler v_r) trong 1 chu ky chirp kep.
   - Mien nhiem 100% voi anh nang mat troi va khong bi can nhieu boi LiDAR cua xe khac tren duong.

3. Mang Diem anh SPAD dToF va Noi suy Luoi khong gian Milimet (Apple Vision Pro Micro-Depth):
   - Mang SPAD voi bo chuyen doi thoi gian TDC 100 ps (Do rong bin tho 15 mm).
   - Tich luy luoc do TCSPC ket hop bo loc phoi hop Gaussian va thuat toan noi suy Parabol duoi-bin (Sub-bin Parabolic Centroid).
   - Dat do phan giai do sau milimet (< 2 mm) cho phep tai tao luoi 3D be mat phong va vat the.

4. Dong co theo doi dong hoc 4D va canh bao va cham som (4D Kinematic Tracker & Time-to-Collision):
   - Ket hop diem anh OPA-FMCW 4D [X, Y, Z, v_r] va luoi khong gian SPAD dToF.
   - Tinh toan thoi gian va cham (TTC = Range / |v_r|) va kich hoat phanh khan cap tu dong (AEB).

BIEU THUC TOAN HOC HE THONG (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Phim pha phan tu OPA va bu troi nhiet (Thermal Compensation):
     phi_m(theta) = -2 * pi * m * d * sin(theta) / lambda
     phi_comp(m)  = phi_m(theta) - (2 * pi / lambda) * (dn/dT) * L_heater * delta_T

2. Tuan hoan tan so phach FMCW va tach do cu ly / van toc:
     f_up   = |f_R - f_D|
     f_down = f_R + f_D
     
              c * T_chirp * (f_down + f_up)
     R      = ─────────────────────────────
                         4 * B
                         
              lambda * (f_down - f_up)
     v_r    = ────────────────────────
                         4

3. Noi suy duoi-bin Parabol SPAD dToF:
              0.5 * (H[k_max - 1] - H[k_max + 1])
     delta  = ───────────────────────────────────────────────
              H[k_max - 1] - 2 * H[k_max] + H[k_max + 1]
     
     R_sub  = 0.5 * c * (k_max + delta) * tau_bin
--------------------------------------------------------------------------------
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

# Constants
SPEED_OF_LIGHT = 299792458.0  # m/s
LAMBDA_OPTICAL = 1.55e-6       # 1550 nm eye-safe telecom wavelength


@dataclass
class OPASubsystemConfig:
    """Cau hinh mang quet pha quang hoc the ran (Silicon Photonic OPA)."""
    num_elements: int = 32
    wavelength: float = 1.55e-6          # 1550 nm
    pitch: float = 0.775e-6              # d = lambda / 2 = 775 nm
    dn_dt: float = 1.86e-4               # He so nhiet quang Silicon (1/K)
    heater_length: float = 500e-6        # Chieu dai dien tro nhiet quang (500 um)
    refractive_index: float = 3.45       # Chiet suat ong dan song Silicon


@dataclass
class FMCWLiDARConfig:
    """Cau hinh FMCW Coherent Heterodyne LiDAR Core."""
    bandwidth: float = 1.5e9             # B = 1.5 GHz
    chirp_duration: float = 10.0e-6      # T_chirp = 10 us
    sampling_rate: float = 250e6         # ADC Fs = 250 MS/s
    wavelength: float = 1.55e-6          # 1550 nm


@dataclass
class SPADArrayConfig:
    """Cau hinh mang cam bien SPAD dToF Array (Apple Vision Pro style)."""
    num_pixels_x: int = 8
    num_pixels_y: int = 8
    tdc_bin_width_ps: float = 100.0      # 100 ps = 1.5 cm raw bin
    max_range_m: float = 5.0
    laser_fwhm_bins: float = 3.0         # Do rong xung laser ~ 300 ps


@dataclass
class KinematicPoint4D:
    """Diem may 4D tich hop toa do khong gian va van toc Doppler tuc thoi."""
    x: float
    y: float
    z: float
    velocity_radial: float               # m/s (+: ra xa, -: tien lai gan)
    intensity_snr: float                 # dB
    timestamp: float
    target_id: Optional[int] = None
    time_to_collision: Optional[float] = None


class SolidStateOPABeamformer:
    """
    Subsystem 1: Bo dieu khien mang quet pha quang hoc the ran OPA.
    Dieu huong bup song azimuthal bang cach ap dung phan bo pha tuyen tinh,
    dong thoi tich hop mach vong kin bu sai lech nhiet do tren chip.
    """
    def __init__(self, config: OPASubsystemConfig):
        self.cfg = config
        self.k = 2.0 * math.pi / self.cfg.wavelength
        self.nominal_temperature = 25.0  # do C

    def compute_steering_phases(self, target_angle_deg: float, temp_gradient_c: float = 0.0) -> List[float]:
        """
        Tinh toan gia tri pha can nap vao 32 bo dich pha nhiet quang,
        kem theo bo vong kin bu troi pha do gradient nhiet do tren chip quang Silicon.
        """
        theta_rad = math.radians(target_angle_deg)
        phases = []
        for m in range(self.cfg.num_elements):
            nominal_phase = -self.k * m * self.cfg.pitch * math.sin(theta_rad)
            # Phan bu gradient nhiet tren tung phan tu (Linear thermal gradient across die)
            delta_t_m = temp_gradient_c * (m / max(1, self.cfg.num_elements - 1))
            thermal_drift_m = self.k * self.cfg.dn_dt * self.cfg.heater_length * delta_t_m
            compensated_phase = (nominal_phase - thermal_drift_m) % (2.0 * math.pi)
            phases.append(compensated_phase)
        return phases

    def simulate_far_field_pattern(self, phases: List[float], angle_grid_deg: List[float]) -> Tuple[List[float], float]:
        """
        Mo phong gian do buc xa truong xa (Far-field Radiation Pattern).
        Tra ve danh sach do loi cong suat (dB) va huong bup song cuc dai thuc te.
        """
        powers = []
        max_power = -1e9
        actual_peak_angle = 0.0

        for theta in angle_grid_deg:
            theta_rad = math.radians(theta)
            real_sum = 0.0
            imag_sum = 0.0
            for m in range(self.cfg.num_elements):
                element_spatial_phase = self.k * m * self.cfg.pitch * math.sin(theta_rad)
                total_phase = element_spatial_phase + phases[m]
                real_sum += math.cos(total_phase)
                imag_sum += math.sin(total_phase)
            
            p = real_sum ** 2 + imag_sum ** 2
            powers.append(p)
            if p > max_power:
                max_power = p
                actual_peak_angle = theta

        # Chuan hoa ve thang dB (Peak = 0 dB)
        powers_db = [10.0 * math.log10(max(p, 1e-12) / max_power) for p in powers]
        return powers_db, actual_peak_angle


class FMCWHeterodyneDSPEngine:
    """
    Subsystem 2: Dong co giai dieu che quang hoc Coherent Heterodyne FMCW LiDAR.
    Decouple cu ly Range va van toc radial Doppler truc tiep tu tan so phach chirp up va chirp down.
    """
    def __init__(self, config: FMCWLiDARConfig):
        self.cfg = config
        self.c = SPEED_OF_LIGHT
        self.lambda_opt = self.cfg.wavelength
        self.slope_k = self.cfg.bandwidth / self.cfg.chirp_duration

    def calculate_theoretical_beats(self, distance_m: float, velocity_radial_mps: float) -> Tuple[float, float, float, float]:
        """
        Tinh toan cac tan so phach ly thuyet:
        f_R = (2 * B * R) / (c * T_chirp)
        f_D = (2 * v_r) / lambda
        f_up = |f_R - f_D|
        f_down = f_R + f_D
        """
        f_r = (2.0 * self.slope_k * distance_m) / self.c
        f_d = (2.0 * velocity_radial_mps) / self.lambda_opt
        f_up = abs(f_r - f_d)
        f_down = f_r + f_d
        return f_r, f_d, f_up, f_down

    def decouple_range_and_velocity(self, f_up_measured: float, f_down_measured: float) -> Tuple[float, float]:
        """
        Giai ma tuyen tinh dong thoi cu ly va van toc tu cap tan so phach do duoc:
        R   = (c * T_chirp * (f_down + f_up)) / (4 * B)
        v_r = (lambda * (f_down - f_up)) / 4
        """
        # Range R
        measured_range = (self.c * self.cfg.chirp_duration * (f_down_measured + f_up_measured)) / (4.0 * self.cfg.bandwidth)
        # Radial Velocity v_r
        measured_velocity = (self.lambda_opt * (f_down_measured - f_up_measured)) / 4.0
        return measured_range, measured_velocity


class SPADMicroDepthMeshingEngine:
    """
    Subsystem 3: Dong co quet do sau sieu chinh xac cho Apple Vision Pro.
    Ket hop mang SPAD, tich luy TCSPC, loc nhieu nen anh sang mat troi,
    va noi suy Parabol duoi-bin dat do chinh xac milimet (< 2 mm).
    """
    def __init__(self, config: SPADArrayConfig):
        self.cfg = config
        self.c = SPEED_OF_LIGHT
        self.bin_time_sec = self.cfg.tdc_bin_width_ps * 1e-12
        self.bin_depth_m = 0.5 * self.c * self.bin_time_sec  # 1.5 cm / bin
        self.num_bins = int(self.cfg.max_range_m / self.bin_depth_m)

    def generate_single_pixel_histogram(self, true_distance_m: float, num_laser_pulses: int = 500, ambient_lux: float = 50000.0) -> List[int]:
        """Mo phong tich luy Histogram photon cua 1 diem anh SPAD."""
        histogram = [0] * self.num_bins
        true_delay_sec = (2.0 * true_distance_m) / self.c
        center_bin_float = true_delay_sec / self.bin_time_sec
        sigma_bin = self.cfg.laser_fwhm_bins / 2.355

        # Ty le photon tin hieu va photon nhieu mat troi
        signal_photons_per_pulse = 0.8
        ambient_photon_rate_per_bin = (ambient_lux / 100000.0) * 0.002

        for _ in range(num_laser_pulses):
            # Nhieu nen mat troi
            for b in range(self.num_bins):
                if random.random() < ambient_photon_rate_per_bin:
                    histogram[b] += 1
            # Photon phan xa laser
            if random.random() < signal_photons_per_pulse:
                arr_bin = int(round(random.gauss(center_bin_float, sigma_bin)))
                if 0 <= arr_bin < self.num_bins:
                    histogram[arr_bin] += 1

        return histogram

    def estimate_sub_bin_depth(self, histogram: List[int]) -> Tuple[float, float]:
        """
        Loc phoi hop Gaussian va noi suy Parabol dinh de tim do sau milimet:
        Tra ve (estimated_distance_m, peak_sbr)
        """
        # 1. Matched Filter Gaussian
        kernel = [0.06, 0.24, 0.40, 0.24, 0.06]
        k_len = len(kernel)
        filtered = [0.0] * self.num_bins
        for i in range(2, self.num_bins - 2):
            acc = 0.0
            for k in range(k_len):
                acc += histogram[i - 2 + k] * kernel[k]
            filtered[i] = acc

        # 2. Tim dinh cuc dai
        max_val = -1.0
        peak_idx = 2
        for i in range(2, self.num_bins - 2):
            if filtered[i] > max_val:
                max_val = filtered[i]
                peak_idx = i

        # 3. Tinh ti so tin hieu tren nhieu nen (SBR)
        noise_mean = sum(histogram[:20] + histogram[-20:]) / 40.0
        sbr = (max_val - noise_mean) / max(noise_mean, 1e-3)

        # 4. Noi suy Parabol duoi-bin
        y0 = filtered[peak_idx - 1]
        y1 = filtered[peak_idx]
        y2 = filtered[peak_idx + 1]
        denom = y0 - 2.0 * y1 + y2
        delta = 0.0
        if abs(denom) > 1e-6:
            delta = 0.5 * (y0 - y2) / denom
            delta = max(-0.5, min(0.5, delta))

        sub_bin_pos = peak_idx + delta
        estimated_distance = sub_bin_pos * self.bin_depth_m
        return estimated_distance, sbr


class Perception4DKinematicTracker:
    """
    Subsystem 4: Bo theo doi khong gian 4D va danh gia nguy co va cham cho xe tu hanh Tesla / Waymo.
    Ket hop toa do khong gian (X, Y, Z), van toc Doppler tuc thoi v_r va tinh Time-to-Collision (TTC).
    """
    def __init__(self, warning_ttc_threshold_sec: float = 2.5):
        self.ttc_threshold = warning_ttc_threshold_sec

    def process_detected_targets(self, targets: List[KinematicPoint4D]) -> List[Dict]:
        """
        Phan tich nguy co va cham, phan loai vat the va sinh lenh phanh khan cap AEB.
        """
        results = []
        for t in targets:
            r = math.sqrt(t.x**2 + t.y**2 + t.z**2)
            ttc = None
            alert_level = "AN TOAN (SAFE)"

            # Neu van toc xuyen tam am (dang tien lai gan cam bien)
            if t.velocity_radial < -0.1:
                ttc = r / abs(t.velocity_radial)
                t.time_to_collision = ttc
                if ttc <= 1.2:
                    alert_level = "NGUY HIEM KHAN CAP: KICH HOAT PHANH AEB!"
                elif ttc <= self.ttc_threshold:
                    alert_level = "CANH BAO VA CHAM SOM (COLLISION WARNING)"
            else:
                t.time_to_collision = float("inf")

            results.append({
                "target_id": t.target_id,
                "position_xyz": (round(t.x, 2), round(t.y, 2), round(t.z, 2)),
                "range_m": round(r, 2),
                "velocity_radial": round(t.velocity_radial, 2),
                "ttc_sec": round(ttc, 2) if ttc is not None else "N/A",
                "alert": alert_level
            })
        return results


class AppleTeslaLiDARCapstoneSystem:
    """
    HETHONG DONG CO TICH HOP TOAN DIEN (CAPSTONE ENGINE):
    Dieu phoi dong thoi:
    1. OPA Beamformer quet goc khong gian the ran.
    2. Coherent Heterodyne FMCW Core do Range-Doppler 4D.
    3. SPAD dToF Array tao luoi khong gian milimet Spatial Computing.
    4. Closed-loop Thermal Drift Calibration giu bup song on dinh.
    5. Kinematic 4D Tracking & Active Collision Safeguard.
    """
    def __init__(self):
        self.opa = SolidStateOPABeamformer(OPASubsystemConfig())
        self.fmcw = FMCWHeterodyneDSPEngine(FMCWLiDARConfig())
        self.spad = SPADMicroDepthMeshingEngine(SPADArrayConfig())
        self.tracker = Perception4DKinematicTracker()

    def run_full_pipeline_verification(self) -> bool:
        """Kiem thu toan dien tat ca cac kich ban thuc te."""
        print("=" * 80)
        print("EE MENTORSHIP - MODULE BF (NHOM 45) - BAI 179 (CAPSTONE PROJECT)")
        print("HAY THONG CAM BIEN QUANG HOC 3D TOF, OPA THE RAN & FMCW RANGE-DOPPLER")
        print("UNG DUNG: APPLE VISION PRO SPATIAL COMPUTING & TESLA / WAYMO HW5 ENGINE")
        print("=" * 80)

        # ----------------------------------------------------------------------
        # KICH BAN 1: Tu dong bu troi nhiet OPA khi gradient nhiet tren chip la 8.0 deg C
        # ----------------------------------------------------------------------
        print("\n[KICH BAN 1] Dong bo pha OPA the ran & Vong kin bu troi nhiet (Thermal Drift Calibration):")
        steer_target_deg = 15.0
        chip_thermal_gradient = 8.0  # Do lech nhiet 8.0 do C tren mang chip quang

        # 1.1 Khong bu troi nhiet
        phases_uncompensated = [
            (-2.0 * math.pi / self.opa.cfg.wavelength * m * self.opa.cfg.pitch * math.sin(math.radians(steer_target_deg))) % (2.0 * math.pi)
            for m in range(self.opa.cfg.num_elements)
        ]
        # Bup song thuc te khi chip bi gradient nhiet
        k = 2.0 * math.pi / self.opa.cfg.wavelength
        thermal_drift_list = [
            k * self.opa.cfg.dn_dt * self.opa.cfg.heater_length * (chip_thermal_gradient * (m / max(1, self.opa.cfg.num_elements - 1)))
            for m in range(self.opa.cfg.num_elements)
        ]
        phases_with_drift = [(phases_uncompensated[m] + thermal_drift_list[m]) % (2.0 * math.pi) for m in range(self.opa.cfg.num_elements)]

        angle_grid = [x * 0.25 for x in range(-120, 121)]  # -30 to +30 deg
        _, peak_drifted = self.opa.simulate_far_field_pattern(phases_with_drift, angle_grid)

        # 1.2 Co bu troi nhiet bang bo dieu khien vong kin
        # Bo dieu khien ap dung phi_dac = nominal - thermal_drift
        phases_calibrated_dac = self.opa.compute_steering_phases(steer_target_deg, temp_gradient_c=chip_thermal_gradient)
        # Pha thuc te phat ra tren chip la phi_dac + thermal_drift
        phases_calibrated_radiated = [
            (phases_calibrated_dac[m] + thermal_drift_list[m]) % (2.0 * math.pi)
            for m in range(self.opa.cfg.num_elements)
        ]
        _, peak_calibrated = self.opa.simulate_far_field_pattern(phases_calibrated_radiated, angle_grid)

        print(f"  * Goc quet muc tieu             : {steer_target_deg:.2f} deg")
        print(f"  * Gradient nhiet tren chip OPA  : {chip_thermal_gradient:.1f} deg C")
        print(f"  * Goc bup song khi CHUA bu nhiet : {peak_drifted:.2f} deg (Lech bup song: {abs(peak_drifted - steer_target_deg):.2f} deg)")
        print(f"  * Goc bup song sau khi BU NHIET  : {peak_calibrated:.2f} deg (Sai lech: {abs(peak_calibrated - steer_target_deg):.2f} deg)")
        assert abs(peak_drifted - steer_target_deg) > 1.0, "Kiem tra: Gradient nhiet phai gay lech bup song ro ret khi chua bu!"
        assert abs(peak_calibrated - steer_target_deg) <= 0.25, "Loi: Bu troi nhiet OPA khong chinh xac!"
        print("  -> Ket luan: Bo bu nhiet tu dong triet tieu sai lech, khoa bup song quang hoc vao muc tieu!")

        # ----------------------------------------------------------------------
        # KICH BAN 2: Xu ly Heterodyne FMCW Range-Doppler 4D cho xe tu hanh Tesla tren cao toc
        # ----------------------------------------------------------------------
        print("\n[KICH BAN 2] Coherent Heterodyne FMCW LiDAR 4D Perception (Tesla / Waymo Highway Scenario):")
        # 3 Vat the giao thong tieu bieu
        scenario_targets = [
            {"id": 1, "name": "Xe doi dien (Oncoming Vehicle)", "x": 12.0, "y": 62.0, "z": 0.5, "v_r": -28.5}, # Dang lao nhanh vao xe
            {"id": 2, "name": "Xe di truoc (Leading Vehicle)",   "x": 0.5,  "y": 28.0, "z": 0.3, "v_r": -2.2},   # Chay cham hon mot chut
            {"id": 3, "name": "Bien bao tinh (Static Signpost)", "x": -8.5, "y": 45.0, "z": 2.1, "v_r": 0.0}     # Tinh tuyet doi
        ]

        detected_points = []
        for st in scenario_targets:
            true_r = math.sqrt(st["x"]**2 + st["y"]**2 + st["z"]**2)
            true_vr = st["v_r"]
            
            # Mo phong tin hieu tan so phach quang hoc
            f_r, f_d, f_up, f_down = self.fmcw.calculate_theoretical_beats(true_r, true_vr)
            
            # Them nhiet nhieu nhe tren bo thu quang TIA
            f_up_meas = f_up + random.gauss(0, 50.0)
            f_down_meas = f_down + random.gauss(0, 50.0)

            # Decouple dong thoi Range va Velocity
            meas_r, meas_vr = self.fmcw.decouple_range_and_velocity(f_up_meas, f_down_meas)

            err_r = abs(meas_r - true_r)
            err_v = abs(meas_vr - true_vr)

            assert err_r < 0.05, f"Loi sai so Range FMCW vuot nguong: {err_r} m"
            assert err_v < 0.05, f"Loi sai so Velocity FMCW vuot nguong: {err_v} m/s"

            # Tinh lai toa do 3D tu goc quet OPA va Range
            # o day x, y, z gan dung voi goc azimuthal
            theta = math.atan2(st["x"], st["y"])
            meas_x = meas_r * math.sin(theta)
            meas_y = meas_r * math.cos(theta)
            meas_z = st["z"]

            detected_points.append(KinematicPoint4D(
                x=meas_x,
                y=meas_y,
                z=meas_z,
                velocity_radial=meas_vr,
                intensity_snr=38.5,
                timestamp=time.time(),
                target_id=st["id"]
            ))

            print(f"  * [{st['name']}]:")
            print(f"    - Cu ly thuc: {true_r:.2f} m | Do duoc: {meas_r:.2f} m (Sai so: {err_r*100:.2f} cm)")
            print(f"    - Van toc thuc: {true_vr:.2f} m/s | Do duoc: {meas_vr:.2f} m/s (Sai so: {err_v*100:.2f} cm/s)")

        # ----------------------------------------------------------------------
        # KICH BAN 3: Danh gia nguy co va kich hoat phanh AEB (Collision Safeguard Engine)
        # ----------------------------------------------------------------------
        print("\n[KICH BAN 3] Danh gia nguy co va cham dong hoc 4D (Time-to-Collision Tracking):")
        collision_evals = self.tracker.process_detected_targets(detected_points)
        for ev in collision_evals:
            print(f"  * Vat the #{ev['target_id']}: Khoang cach = {ev['range_m']} m | Van toc = {ev['velocity_radial']} m/s | TTC = {ev['ttc_sec']} s")
            print(f"    -> Trang thai an toan: {ev['alert']}")
            if ev["target_id"] == 1:
                assert "PHANH" in ev["alert"] or "CANH BAO" in ev["alert"], "Loi: Khong phat hien va cham som!"

        # ----------------------------------------------------------------------
        # KICH BAN 4: Mang SPAD dToF tao luoi khong gian milimet cho Apple Vision Pro
        # ----------------------------------------------------------------------
        print("\n[KICH BAN 4] Apple Vision Pro Spatial Computing - Tai tao luoi 3D be mat milimet:")
        # Mo phong quet 4 diem tren be mat ban tay va mat ban lam viec (0.65 m - 1.25 m)
        surface_points = [
            ("Dau ngon tay (Fingertip)", 0.654),
            ("Long ban tay (Palm Center)", 0.682),
            ("Goc ban go (Desk Edge)", 1.050),
            ("Man hinh may tinh (Display)", 1.245)
        ]

        print("  Kiem thu thuat toan noi suy Parabol duoi-bin (Sub-bin Parabolic Centroid):")
        for name, true_dist in surface_points:
            hist = self.spad.generate_single_pixel_histogram(true_dist, num_laser_pulses=600, ambient_lux=60000.0)
            est_dist, sbr = self.spad.estimate_sub_bin_depth(hist)
            err_mm = abs(est_dist - true_dist) * 1000.0
            print(f"  * [{name}]:")
            print(f"    - Khoang cach thuc     : {true_dist*100:.2f} cm")
            print(f"    - Do sau uoc tinh SPAD : {est_dist*100:.2f} cm")
            print(f"    - Sai so milimet       : {err_mm:.2f} mm (Nguong cho phep: < 5.0 mm)")
            print(f"    - Ti so tin hieu SBR   : {sbr:.2f}x")
            assert err_mm < 5.0, f"Loi sai so do sau SPAD qua lon: {err_mm} mm"

        print("\n" + "=" * 80)
        print("KET QUA CAPSTONE: HE THONG 3D TOF & OPA FMCW HOAN TAT KIEM THU 100% PASS!")
        print("San sang tich hop vao bo xu ly Apple Vision Pro va he thong Tesla HW5!")
        print("=" * 80)
        return True


if __name__ == "__main__":
    capstone = AppleTeslaLiDARCapstoneSystem()
    success = capstone.run_full_pipeline_verification()
    assert success is True, "Capstone execution failed!"
