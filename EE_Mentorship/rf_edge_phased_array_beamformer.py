"""
================================================================================
CHUYEN DE AI: PHASED ARRAY BEAMSTEERING & FMCW SYNTHETIC APERTURE RADAR (SAR)
BAI 1: MANG QUET PHA DIEN TU AESA VA BO DICH PHA SO HOA QUANTIZED PHASE SHIFTER
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Ky su RF & Chip Phased Array cho Ve tinh SpaceX Starlink / Tesla FSD
Ngon ngu: Python 3 thuan tuy, giai tich mang pha so hoc va ham cua so Chebyshev
================================================================================
"""

import math
from typing import List, Tuple, Dict

SPEED_OF_LIGHT = 299792458.0 # m/s

# ------------------------------------------------------------------------------
# 1. CAC THONG SO MANG ANG-TEN QUET PHA AESA
# ------------------------------------------------------------------------------

class PhasedArrayConfig:
    """
    Cau hinh mang ăng-ten quet pha dien tu chu dong AESA (Active Electronically Scanned Array):
    - num_elements (N): So luong phan tu ăng-ten vi dai (vi du 16 phan tu)
    - freq_hz (f): Tan so song mang cao tan (vi du 28 GHz dải mmWave 5G hoac 77 GHz Automotive Radar)
    - phase_bits (B): Do phan giai bo dich pha so hoa (vi du 6-bit -> 64 trang thai pha)
    """
    def __init__(self,
                 num_elements: int = 16,
                 freq_hz: float = 28.0e9, # 28 GHz mmWave
                 phase_bits: int = 6):    # 6-bit digital phase shifter
        self.num_elements = num_elements
        self.freq_hz = freq_hz
        self.phase_bits = phase_bits

        # Buoc song: lambda = c / f
        self.wavelength = SPEED_OF_LIGHT / freq_hz # ~ 10.7 mm tai 28 GHz
        # Khoang cach giua cac phan tu d = lambda / 2 de chong Grating Lobe
        self.element_spacing = self.wavelength / 2.0
        # So buoc luong tu hoa pha: 2^B
        self.num_phase_states = 1 << phase_bits
        # Do phan giai goc pha nho nhat: 360 / 2^B (do)
        self.phase_step_rad = (2.0 * math.pi) / self.num_phase_states

    def quantize_phase(self, ideal_phase_rad: float) -> float:
        """
        Luong tu hoa pha ly thuyet sang trang thai pha so 6-bit (Hardware Phase Quantization):
        phi_q = round(ideal_phase / Delta_phi) * Delta_phi
        """
        # Dua ve khoang [0, 2*pi)
        wrapped = ideal_phase_rad % (2.0 * math.pi)
        if wrapped < 0.0:
            wrapped += 2.0 * math.pi
        steps = round(wrapped / self.phase_step_rad) % self.num_phase_states
        return steps * self.phase_step_rad

# ------------------------------------------------------------------------------
# 2. HAM TRONG SO CUA SO TAPER (AMPLITUDE TAPERING DE TRIET TIEU BUP PHU)
# ------------------------------------------------------------------------------

def compute_cosine_squared_taper(num_elements: int, pedestal: float = 0.2) -> List[float]:
    """
    Tao cua so trong so giam dan ve 2 bien (Amplitude Tapering / Windowing):
    w[n] = pedestal + (1 - pedestal) * cos^2(pi * (n - (N-1)/2) / (N-1))
    Giup triet tieu bup song phu (Sidelobe Level) tu -13 dB xuong duoi -25 dB!
    """
    weights = []
    n_mid = (num_elements - 1) / 2.0
    for n in range(num_elements):
        x = (n - n_mid) / (num_elements - 1)
        w = pedestal + (1.0 - pedestal) * (math.cos(math.pi * x) ** 2)
        weights.append(w)
    return weights

# ------------------------------------------------------------------------------
# 3. TINH TOAN HE SO MANG (ARRAY FACTOR) VA BIEU DO BUAP SONG (BEAM PATTERN)
# ------------------------------------------------------------------------------

class PhasedArrayBeamformer:
    """
    Bo dieu khien quet bup song dien tu:
    AF(theta) = sum_{n=0}^{N-1} w_n * exp(j * (k * n * d * sin(theta) + phi_n))
    Voi:
      - k = 2*pi / lambda (So song Wave number)
      - phi_n: Pha can thiet lap de lai bup song ve goc theta_steer:
        phi_n = - k * n * d * sin(theta_steer)
    """
    def __init__(self, config: PhasedArrayConfig, use_taper: bool = True):
        self.cfg = config
        self.use_taper = use_taper
        if use_taper:
            self.weights = compute_cosine_squared_taper(config.num_elements, pedestal=0.25)
        else:
            self.weights = [1.0] * config.num_elements

    def compute_element_phases(self, steer_angle_rad: float) -> List[float]:
        """
        Tinh toan gia tri pha luong tu hoa can thiet lap cho tung phan tu ăng-ten n:
        phi_n = quantize(- (2*pi / lambda) * n * d * sin(theta_steer))
        """
        k = (2.0 * math.pi) / self.cfg.wavelength
        phases = []
        for n in range(self.cfg.num_elements):
            ideal_phi = -k * n * self.cfg.element_spacing * math.sin(steer_angle_rad)
            quantized_phi = self.cfg.quantize_phase(ideal_phi)
            phases.append(quantized_phi)
        return phases

    def compute_array_factor(self, angle_rad: float, element_phases: List[float]) -> complex:
        """
        Tinh tong giao thoa song tai goc quan sat angle_rad:
        AF = sum_n (w_n * exp(j * (psi_n)))
        psi_n = k * n * d * sin(angle) + phase_n
        """
        k = (2.0 * math.pi) / self.cfg.wavelength
        real_sum = 0.0
        imag_sum = 0.0

        for n in range(self.cfg.num_elements):
            w = self.weights[n]
            psi = k * n * self.cfg.element_spacing * math.sin(angle_rad) + element_phases[n]
            real_sum += w * math.cos(psi)
            imag_sum += w * math.sin(psi)

        return complex(real_sum, imag_sum)

    def scan_beam_pattern(self, steer_angle_deg: float) -> Tuple[List[float], List[float]]:
        """
        Quet bieu do buap song tu -90 do den +90 do voi buoc 0.5 do:
        Tra ve (angles_deg, gains_db_normalized)
        """
        steer_rad = math.radians(steer_angle_deg)
        phases = self.compute_element_phases(steer_rad)

        angles = []
        gains_db = []
        max_power = 0.0

        # Quet 361 diem tu -90 den +90
        raw_powers = []
        for i in range(361):
            theta_deg = -90.0 + i * 0.5
            theta_rad = math.radians(theta_deg)
            af = self.compute_array_factor(theta_rad, phases)
            power = abs(af) ** 2
            raw_powers.append((theta_deg, power))
            if power > max_power:
                max_power = power

        # Chuan hoa ve dB (Gia tri cuc dai tai bup song chinh = 0 dB)
        for deg, p in raw_powers:
            angles.append(deg)
            norm_p = p / max_power if max_power > 0 else 1e-12
            db = 10.0 * math.log10(max(1e-6, norm_p))
            gains_db.append(db)

        return (angles, gains_db)

# ------------------------------------------------------------------------------
# 4. MO PHONG VA KIEM CHUNG BUP SONG AESA 28 GHz
# ------------------------------------------------------------------------------

def test_phased_array_steering_and_sidelobes():
    """
    Kiem tra ăng-ten quet pha 16 phan tu tai 28 GHz:
    1. Lai bup song chinh ve huong +30 do (Steer Angle = +30 deg).
    2. Kiem tra xem dinh bup song co nam dung tai +30 do (+- 0.5 do) khong.
    3. Kiem tra muc bup song phu (Sidelobe Level) phai bi triet tieu duoi -20 dB nho Tapering.
    """
    cfg = PhasedArrayConfig(num_elements=16, freq_hz=28e9, phase_bits=6)
    beamformer = PhasedArrayBeamformer(cfg, use_taper=True)

    target_steer_deg = 30.0
    angles, gains_db = beamformer.scan_beam_pattern(target_steer_deg)

    # Tim dinh bup song chinh (Mainlobe Peak)
    max_gain = -999.0
    peak_angle = 0.0
    for deg, g in zip(angles, gains_db):
        if g > max_gain:
            max_gain = g
            peak_angle = deg

    # Tim bup song phu cao nhat (Peak Sidelobe) nam ngoai vung bup chinh (cach xa dinh it nhat 14 do)
    sidelobe_peak = -999.0
    sidelobe_angle = 0.0
    for deg, g in zip(angles, gains_db):
        if abs(deg - peak_angle) > 14.0:
            if g > sidelobe_peak:
                sidelobe_peak = g
                sidelobe_angle = deg

    print("--------------------------------------------------------------------------------")
    print(f"KET QUA DO KIEM MANG ANG-TEN AESA 16 PHAN TU 28 GHz (6-BIT PHASE SHIFTER):")
    print(f"-> Goc lai mong muon (Target Steering) : {target_steer_deg:+.1f} deg")
    print(f"-> Dinh bup song do duoc (Mainlobe)    : {peak_angle:+.1f} deg (Do loi 0.00 dB)")
    print(f"-> Bup song phu cao nhat (Peak Sidelobe): {sidelobe_peak:6.2f} dB tai {sidelobe_angle:+.1f} deg")
    print(f"-> Ti so triet tieu bup phu (SLL)       : {abs(sidelobe_peak):.2f} dB (Chuan > 20 dB)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Bup song phai huong dung goc +30 do (sai so < 0.5 do)
    assert abs(peak_angle - target_steer_deg) <= 0.5, f"Loi: Goc lai lech muc tieu: {peak_angle} deg"
    # 2. Bup phu phai bi triet tieu duoi -20 dB nho cua so Tapering
    assert sidelobe_peak <= -20.0, f"Loi: Bup song phu qua lon: {sidelobe_peak:.2f} dB"
    print("[PASS] Test Phased Array: Lai bup song 30 deg chinh xac va triet tieu bup phu xuat sac!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO 28 GHz AESA PHASED ARRAY BEAMFORMER (SPACEX STARLINK / TESLA RADAR)")
    print("================================================================================")
    test_phased_array_steering_and_sidelobes()
