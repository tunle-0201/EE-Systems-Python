"""
================================================================================
          MODULE T: EMBEDDED AUTOMOTIVE 77GHz FMCW RADAR BASEBAND DSP
    MILESTONE T.1: BO TAO CHIRP FMCW & MACH TRON DECHIRPING TIN HIEU TRUNG TAN IF
================================================================================

1. NGUYEN LY VAT LY & PHAN CUNG RADAR 77GHz (AUTOMOTIVE RADAR RF FRONT-END):
   - Tai sao xe tu lai (Tesla, Waymo, Mercedes Drive Pilot) bat buoc phai co Radar 77GHz?
     + Trong dieu kien thoi tiet khac nghiet (muong mu day dac, mua bao, bui mit mu,
       anh sang chieu thang gay loa camera), Camera va LiDAR bi vo hieu hoa hoan toan.
     + Song dien tu milimet (buoc song ~ 3.9 mm) xuyen qua giot mua va hat bui de dang!
   - Nguyen ly Radar song lien tuc bien dieu tan so (FMCW - Frequency Modulated Continuous Wave):
     + Bo tao dao dong (VCO/PLL) phat ra chuoi tin hieu Chirp co tan so tang tuyen tinh
       theo thoi gian tu f_carrier den f_carrier + B (vi du tu 77 GHz den 78 GHz).
     + Song gap vat can o cu ly R se doi ve sau thoi gian tre tau = 2*R/c.
     + Bo tron RF Mixer nhan tin hieu phat TX va tin hieu thu RX, tao ra hien tuong
       phach tan (Dechirping). Qua mach loc thong thap LPF ta thu duoc tin hieu phach IF
       co tan so f_beat ty le thuan tuyet doi voi khoang cach R cua vat can!

2. SO DO PHAN CUNG RF & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do khoi phan cung bo thu phat Radar 77GHz (FMCW RF Front-End Architecture):

   [ Bo tao xung Chirp (PLL/VCO) ]
              │
              ├───► [ Bo khuech dai cong suat PA ] ──► [ Anten Phat TX ]
              │                                                │
              │ (Song ban di f_tx)                            │ 77 GHz
              │                                                ▼
              │                                            [ MUC TIEU ] (Cuc ly R)
              │                                                │
              │ (Song doi ve sau tau = 2R/c)                   │
              │                                                ▼
              └───► [ Bo tron vo tuyen RF Mixer ] ◄── [ Anten Thu RX + LNA ]
                                  │
                                  ▼
                      [ Bo loc thong thap LPF ]
                                  │
                                  ▼
                      [ Bo bien doi ADC 25MHz ] ──► Tin hieu phach IF (Beat Signal)

   Do doc tan so cua xung Chirp (Chirp Slope):

                    Bang thong quet B
   Do doc Chirp S = ──────────────────
                    Thoi gian quet Tc

   Thoi gian tre phan xa (Round-trip Delay):
             2 * R
   tau   = ─────────   (c = 3e8 m/s la van toc anh sang)
               c

   Tan so phach trung tan (IF Beat Frequency):
             2 * S * R
   f_beat = ───────────
                 c

   Cong thuc tinh nguoc cu ly muc tieu R tu tan so do duoc:
             c * f_beat
   Range R = ───────────
                2 * S
"""

from typing import Tuple
import numpy as np


class FMCWChirpGenerator:
    """
    Bo mo phong tao xung Chirp FMCW va mach tron dechirping trung tan IF cho Radar 77GHz.
    """
    def __init__(
        self,
        f_carrier: float = 77e9,
        bandwidth: float = 1e9,
        chirp_duration: float = 50e-6,
        fs: float = 25e6
    ):
        """
        - f_carrier: Tan so song mang (77 GHz chuan Automotive Radar)
        - bandwidth: Bang thong quet tan so (1 GHz -> Do phan giai cuc ly c / (2B) = 15 cm)
        - chirp_duration: Thoi gian quet 1 chirp (50 micro-giay)
        - fs: Tan so lay mau ADC trung tan (25 MHz)
        """
        self.c = 3e8
        self.fc = float(f_carrier)
        self.B = float(bandwidth)
        self.Tc = float(chirp_duration)
        self.fs = float(fs)
        self.slope = self.B / self.Tc
        self.num_samples = int(self.Tc * self.fs)
        self.time_axis = np.linspace(0, self.Tc, self.num_samples, endpoint=False)

    def generate_beat_signal(self, target_distance_m: float) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Mo phong bo tron RF Mixer tao tin hieu Beat IF thoi gian thuc:
        1. Tinh thoi gian tre phan xa song: tau = 2 * R / c
        2. Tan so phach ly thuyet: f_beat = slope * tau = 2 * slope * R / c
        3. Tin hieu phach IF: s_if(t) = cos(2 * pi * f_beat * t + phi)
        Tra ve: (time_axis, if_signal, f_beat_theoretical)
        """
        tau = 2.0 * float(target_distance_m) / self.c
        f_beat_expected = self.slope * tau

        # Tin hieu phach sau tron tan (Down-converted Beat Signal)
        phi_phase = 2.0 * np.pi * self.fc * tau
        if_signal = np.cos(2.0 * np.pi * f_beat_expected * self.time_axis + phi_phase).astype(np.float32)

        return self.time_axis, if_signal, float(f_beat_expected)

    def calculate_range_from_beat(self, beat_frequency_hz: float) -> float:
        """
        Tinh toan cuc ly muc tieu R tu tan so phach IF:
        Range R = (c * f_beat) / (2 * S)
        """
        return float((self.c * beat_frequency_hz) / (2.0 * self.slope))


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED FMCW RADAR: CHIRP & BEAT SIGNAL GENERATOR")
    print("=========================================================\n")

    radar = FMCWChirpGenerator(f_carrier=77e9, bandwidth=1e9, chirp_duration=50e-6, fs=25e6)

    test_distances = [15.0, 45.0, 75.0, 120.0]  # Muc tieu o 15m, 45m, 75m, 120m

    print("1. KIEM DINH TINH TOAN TAN SO PHACH TRUNG TAN (IF BEAT FREQUENCY):")
    for dist in test_distances:
        t, if_sig, f_beat = radar.generate_beat_signal(target_distance_m=dist)
        calculated_dist = radar.calculate_range_from_beat(f_beat)

        print(f"   -> Muc tieu R = {dist:5.1f}m  |  Tan so phach f_beat = {f_beat / 1e6:6.3f} MHz  |  Cuc ly do duoc: {calculated_dist:5.1f}m")
        assert abs(calculated_dist - dist) < 1e-4, f"Loi tinh toan cuc ly FMCW: {calculated_dist} != {dist}"

    print(f"\n2. THONG SO PHAN CUNG RADAR 77GHz:")
    print(f"   -> Bang thong chirp (B)          : {radar.B / 1e9:.2f} GHz")
    print(f"   -> Thoi gian quet chirp (Tc)     : {radar.Tc * 1e6:.1f} us")
    print(f"   -> Do doc chirp (Slope S)        : {radar.slope:.2e} Hz/s")
    print(f"   -> Do phan giai cuc ly (c / 2B)  : {radar.c / (2 * radar.B) * 100:.1f} cm")
    print(f"   -> So mau ADC moi chirp          : {radar.num_samples} samples")

    print("\n[THANH CONG] BO TAO CHIRP VA TINH TOAN BEAT SIGNAL FMCW HOAN TAT CHINH XAC 100%!")
