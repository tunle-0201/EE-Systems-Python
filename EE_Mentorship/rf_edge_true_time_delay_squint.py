"""
================================================================================
CHUYEN DE AI: PHASED ARRAY BEAMSTEERING & FMCW SYNTHETIC APERTURE RADAR (SAR)
BAI 2: TRIET TIEU MEO BUP SONG BEAM SQUINT BANG MANG TRE THOI GIAN THUC TRUE TIME DELAY
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Xu ly tin hieu Radar bang rong 77-81 GHz cho Tesla FSD 4D Imaging Radar
Ngon ngu: Python 3 thuan tuy, so sanh giai tich Phase Shifter vs True Time Delay
================================================================================
"""

import math
from typing import Tuple, List, Dict

SPEED_OF_LIGHT = 299792458.0 # m/s

# ------------------------------------------------------------------------------
# 1. CAC THONG SO RADAR FMCW BANG RONG 77 GHz - 81 GHz
# ------------------------------------------------------------------------------

class WidebandRadarConfig:
    """
    Cau hinh Radar bang rong song milimet (Automotive Imaging Radar):
    - f_center: Tan so trung tam 78.5 GHz
    - bandwidth: Bang thong quet FMCW Chirp 4.0 GHz (tu 76.5 GHz den 80.5 GHz)
    - num_elements (N): So luong phan tu mang ăng-ten (vi du 16 phan tu)
    """
    def __init__(self,
                 f_center: float = 78.5e9,
                 bandwidth: float = 4.0e9,
                 num_elements: int = 16):
        self.f_center = f_center
        self.bandwidth = bandwidth
        self.num_elements = num_elements

        self.f_min = f_center - (bandwidth / 2.0) # 76.5 GHz
        self.f_max = f_center + (bandwidth / 2.0) # 80.5 GHz

        # Khoang cach giua cac phan tu d = lambda_center / 2
        self.lambda_center = SPEED_OF_LIGHT / f_center # ~ 3.82 mm
        self.element_spacing = self.lambda_center / 2.0 # ~ 1.91 mm

# ------------------------------------------------------------------------------
# 2. SO SANH BEAMFORMER: PHASE SHIFTER (PS) VS TRUE TIME DELAY (TTD)
# ------------------------------------------------------------------------------

class WidebandBeamformer:
    """
    Bo lai bup song bang rong cho radar:
    1. Phase Shifter Mode: Thiet lap pha co dinh tai tan so f_center:
       phi_n = - (2*pi * f_center / c) * n * d * sin(theta_steer)
       GAY RA HIEN TUONG BEAM SQUINT KHI TAN SO THAY DOI!
    2. True Time Delay Mode: Thiet lap do tre vat ly doc lap voi tan so:
       tau_n = - (n * d * sin(theta_steer)) / c
       TRIET TIEU 100% BEAM SQUINT TREN MOI TAN SO!
    """
    def __init__(self, config: WidebandRadarConfig):
        self.cfg = config

    def compute_ps_beam_peak_angle(self, steer_angle_deg: float, test_freq_hz: float) -> float:
        """
        Xac dinh goc huong bup song thuc te theta(f) khi dung Phase Shifter:
        sin(theta(f)) = (f_center / f) * sin(theta_steer)
        """
        steer_rad = math.radians(steer_angle_deg)
        sin_steer = math.sin(steer_rad)
        sin_actual = (self.cfg.f_center / test_freq_hz) * sin_steer

        # Kẹp trong [-1.0, 1.0]
        sin_actual = max(-1.0, min(1.0, sin_actual))
        actual_rad = math.asin(sin_actual)
        return math.degrees(actual_rad)

    def compute_ttd_beam_peak_angle(self, steer_angle_deg: float, test_freq_hz: float) -> float:
        """
        Xac dinh goc huong bup song khi dung True Time Delay:
        Vi tau_n = (n * d * sin(theta_steer)) / c, goc toi luon thoa man:
        sin(theta) = c * tau_n / (n * d) = sin(theta_steer) (BAT BIEN VOI MOI TAN SO f!).
        """
        return steer_angle_deg

    def evaluate_array_gain_at_angle(self,
                                     angle_deg: float,
                                     steer_angle_deg: float,
                                     freq_hz: float,
                                     use_ttd: bool) -> float:
        """
        Tinh toan do loi mang tong hop Array Factor Power (Normalized linear scale):
        AF = sum_n (exp(j * psi_n))
        - Voi PS : psi_n = 2*pi*f/c * n * d * sin(angle) - 2*pi*f_center/c * n * d * sin(steer)
        - Voi TTD: psi_n = 2*pi*f/c * n * d * [ sin(angle) - sin(steer) ]
        """
        angle_rad = math.radians(angle_deg)
        steer_rad = math.radians(steer_angle_deg)
        d = self.cfg.element_spacing

        real_sum = 0.0
        imag_sum = 0.0

        for n in range(self.cfg.num_elements):
            if use_ttd:
                # True Time Delay: pha co dan tuyen tinh theo f
                phase_shift = (2.0 * math.pi * freq_hz / SPEED_OF_LIGHT) * (n * d * math.sin(steer_rad))
            else:
                # Phase Shifter co dinh tai f_center
                phase_shift = (2.0 * math.pi * self.cfg.f_center / SPEED_OF_LIGHT) * (n * d * math.sin(steer_rad))

            spatial_phase = (2.0 * math.pi * freq_hz / SPEED_OF_LIGHT) * (n * d * math.sin(angle_rad))
            psi = spatial_phase - phase_shift

            real_sum += math.cos(psi)
            imag_sum += math.sin(psi)

        power = (real_sum ** 2 + imag_sum ** 2) / (self.cfg.num_elements ** 2)
        return power

# ------------------------------------------------------------------------------
# 3. MO PHONG VA SO SANH: PHASE SHIFTER VS TRUE TIME DELAY
# ------------------------------------------------------------------------------

def test_beam_squint_comparison():
    """
    Kiem tra hien tuong Beam Squint khi lai bup song ve goc +45 do:
    So sanh giua bo dich pha Phase Shifter va bo tre thoi gian thuc True Time Delay
    khi tan so radar quet tu f_min (76.5 GHz) den f_max (80.5 GHz).
    """
    cfg = WidebandRadarConfig(f_center=78.5e9, bandwidth=4.0e9, num_elements=16)
    beamformer = WidebandBeamformer(cfg)

    steer_target_deg = 45.0 # Lai bup song ve 45 do

    # 1. Kiem tra tai tan so thap nhat f_min = 76.5 GHz
    ps_angle_fmin = beamformer.compute_ps_beam_peak_angle(steer_target_deg, cfg.f_min)
    ttd_angle_fmin = beamformer.compute_ttd_beam_peak_angle(steer_target_deg, cfg.f_min)

    # 2. Kiem tra tai tan so cao nhat f_max = 80.5 GHz
    ps_angle_fmax = beamformer.compute_ps_beam_peak_angle(steer_target_deg, cfg.f_max)
    ttd_angle_fmax = beamformer.compute_ttd_beam_peak_angle(steer_target_deg, cfg.f_max)

    # Do lech goc squint cuc dai
    ps_squint_error = abs(ps_angle_fmin - ps_angle_fmax)
    ttd_squint_error = abs(ttd_angle_fmin - ttd_angle_fmax)

    # Do loi tai goc muc tieu +45 do o tan so bien f_min
    gain_ps_at_target = beamformer.evaluate_array_gain_at_angle(
        angle_deg=steer_target_deg, steer_angle_deg=steer_target_deg, freq_hz=cfg.f_min, use_ttd=False
    )
    gain_ttd_at_target = beamformer.evaluate_array_gain_at_angle(
        angle_deg=steer_target_deg, steer_angle_deg=steer_target_deg, freq_hz=cfg.f_min, use_ttd=True
    )

    loss_ps_db = 10.0 * math.log10(gain_ps_at_target)
    loss_ttd_db = 10.0 * math.log10(gain_ttd_at_target)

    print("--------------------------------------------------------------------------------")
    print(f"SO SANH BEAM SQUINT TAI GOC LAI +{steer_target_deg:.1f} DEG (BANDWIDTH 4.0 GHz):")
    print(f"-> Goc bup song voi Phase Shifter tai 76.5 GHz: {ps_angle_fmin:+.2f} deg")
    print(f"-> Goc bup song voi Phase Shifter tai 80.5 GHz: {ps_angle_fmax:+.2f} deg")
    print(f"-> Do meo lech bup song Beam Squint (PS)      : {ps_squint_error:.2f} deg (BUP SONG BI NGOAY!)")
    print(f"-> Do suy hao do loi tai goc 45 deg (PS)       : {loss_ps_db:6.2f} dB (Mat tin hieu!)")
    print("--------------------------------------------------------------------------------")
    print(f"-> Goc bup song voi True Time Delay tai 76.5 GHz: {ttd_angle_fmin:+.2f} deg")
    print(f"-> Goc bup song voi True Time Delay tai 80.5 GHz: {ttd_angle_fmax:+.2f} deg")
    print(f"-> Do meo lech bup song Beam Squint (TTD)     : {ttd_squint_error:.2f} deg (BAT BIEN TUYET DOI)")
    print(f"-> Do suy hao do loi tai goc 45 deg (TTD)      : {loss_ttd_db:6.2f} dB (Bao toan 100% nang luong)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Phase Shifter phai bi meo squint it nhat 2.5 do tren bang thong 4 GHz
    assert ps_squint_error > 2.5, f"Loi: Phase Shifter phai bi squint ro ret: {ps_squint_error}"
    # 2. True Time Delay phai triet tieu squint hoan toan (sai so = 0.00 deg)
    assert ttd_squint_error < 1e-4, f"Loi: TTD bi lech goc: {ttd_squint_error}"
    # 3. TTD phai giu do loi cuc dai tai goc muc tieu (loss_ttd_db = 0.00 dB)
    assert abs(loss_ttd_db) < 1e-4, f"Loi do loi TTD: {loss_ttd_db}"
    print("[PASS] Test Beam Squint: True Time Delay triet tieu 100% hien tuong meo lech bup song!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO TRUE TIME DELAY (TTD) VS PHASE SHIFTER BEAM SQUINT MITIGATION")
    print("================================================================================")
    test_beam_squint_comparison()
