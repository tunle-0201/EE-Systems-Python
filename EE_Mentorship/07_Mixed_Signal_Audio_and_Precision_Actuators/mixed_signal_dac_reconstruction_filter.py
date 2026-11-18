"""
Chuyen de AT: Mach Tin hieu Hon hop Mixed-Signal & Bo chuyen doi ADC/DAC Toc do cao
Bai 130 (Milestone AT.3): Bo chuyen doi DAC R-2R suy hao ZOH va loc tai tao anh pho Nyquist

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu mang dien tro R-2R Ladder, hieu ro suy hao sinc roll-off cua khoi Zero-Order Hold (ZOH),
          xac dinh cac tan so anh pho Nyquist Image va thiet ke bo loc tai tao tuong tu tich cuc Sallen-Key.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class R2RLadderDAC:
    """
    Mo hinh mang dien tro R-2R Ladder DAC N-bit.
    
    Phan tich toan hoc & phan chia dong dien:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │         V_ref                                          │
    │          │                                             │
    │         [2R]       [2R]       [2R]         [2R]        │
    │          │          │          │            │          │
    │    ───/\/\/\───*──/\/\/\───*──/\/\/\───*──/\/\/\─── V_out
    │         R      │    R      │    R      │    R          │
    │               [b3]        [b2]        [b1] [b0]        │
    │                                                        │
    │                 N-1                                    │
    │                 ───     b_k                            │
    │   V_out = V_ref ─── ───────────                        │
    │                 k=0   2^(N - k)                        │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, num_bits: int = 8, v_ref: float = 3.3, r_nominal_ohm: float = 10000.0):
        if num_bits < 2 or num_bits > 16:
            raise ValueError("So bit ho tro tu 2 den 16")
        self.num_bits = num_bits
        self.v_ref = float(v_ref)
        self.r_ohm = float(r_nominal_ohm)
        self.num_levels = 1 << num_bits
        self.lsb_voltage = self.v_ref / float(self.num_levels)

    def convert_code_to_voltage(self, code: int) -> float:
        """Chuyen doi ma so nguyen code [0, 2^N - 1] thanh dien ap tuong tu."""
        code_clamped = max(0, min(self.num_levels - 1, code))
        # Tinh tong dong dien/dien ap qua tung nhanh bit
        v_out = 0.0
        for bit_idx in range(self.num_bits):
            if (code_clamped >> bit_idx) & 1:
                # Bit trong so 2^bit_idx
                weight = 1.0 / (1 << (self.num_bits - bit_idx))
                v_out += self.v_ref * weight
        return v_out

    def generate_staircase_waveform(self, codes: List[int]) -> List[float]:
        """Tao dang song dien ap bac thang (staircase) tu day ma so."""
        return [self.convert_code_to_voltage(c) for c in codes]


class ZeroOrderHoldAnalyzer:
    """
    Phan tich dap ung tan so sinc roll-off va anh pho Nyquist Image do khoi giu bac 0 (ZOH).
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │                         | sin(pi * f / f_s) |          │
    │   |H_ZOH(f)| =          ─────────────────────          │
    │                            pi * f / f_s                │
    │                                                        │
    │   Suy hao tai bien Nyquist (f = f_s / 2):              │
    │   |H_ZOH(f_s/2)| = 2 / pi = 0.6366 (-3.922 dB)         │
    │                                                        │
    │   Tan so anh pho Nyquist (Spectral Images):            │
    │   f_image = |k * f_s +/- f_signal|, voi k = 1, 2, ...  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def sinc_magnitude(f_hz: float, f_sample_hz: float) -> float:
        """Tinh bien do dap ung tan so cua ham sinc ZOH."""
        if f_hz == 0.0:
            return 1.0
        x = math.pi * f_hz / f_sample_hz
        return abs(math.sin(x) / x)

    @staticmethod
    def sinc_attenuation_db(f_hz: float, f_sample_hz: float) -> float:
        """Tinh do suy hao tinh bang dB cua ZOH."""
        mag = ZeroOrderHoldAnalyzer.sinc_magnitude(f_hz, f_sample_hz)
        return 20.0 * math.log10(max(1e-12, mag))

    @staticmethod
    def calculate_nyquist_images(f_signal_hz: float, f_sample_hz: float, max_k: int = 3) -> List[Dict[str, float]]:
        """
        Xac dinh vi tri va bien do cua cac anh pho Nyquist do DAC tao ra.
        """
        images = []
        for k in range(1, max_k + 1):
            f_img_minus = abs(k * f_sample_hz - f_signal_hz)
            f_img_plus = k * f_sample_hz + f_signal_hz

            mag_minus_db = ZeroOrderHoldAnalyzer.sinc_attenuation_db(f_img_minus, f_sample_hz)
            mag_plus_db = ZeroOrderHoldAnalyzer.sinc_attenuation_db(f_img_plus, f_sample_hz)

            images.append({
                "k": k,
                "type": "k*fs - fsig",
                "frequency_hz": f_img_minus,
                "sinc_attenuation_db": mag_minus_db
            })
            images.append({
                "k": k,
                "type": "k*fs + fsig",
                "frequency_hz": f_img_plus,
                "sinc_attenuation_db": mag_plus_db
            })
        return images


class ActiveSallenKeyReconstructionFilter:
    """
    Bo loc tai tao tuong tu tich cuc Sallen-Key Low-Pass bac 2 (Butterworth, Q = 1/sqrt(2)).
    
    Phan tich mach tuong tu:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │                  C1                                    │
    │            ┌─────||─────┐                              │
    │            │            │                              │
    │     R1     │     R2     │     |\                       │
    │  ──/\/\/\──*───/\/\/\───*────|+ \                      │
    │                         │    |   >──*───*── V_out      │
    │                        ===   |  /   │   │          │
    │                     C2  │  ┌─|-/    │   │          │
    │                        GND │  |/    │   │          │
    │                            └────────┘   │          │
    │                                         │          │
    │                                                    │
    │   Tan so cat: f_c = 1 / (2 * pi * sqrt(R1 * R2 * C1 * C2))
    │                                                        │
    │   Dap ung bien do Butterworth bac 2:                   │
    │                               1                        │
    │   |H(f)| = ─────────────────────────────────────────   │
    │            sqrt( 1 + (f / f_c)^4 )                     │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, f_cutoff_hz: float):
        if f_cutoff_hz <= 0.0:
            raise ValueError("Tan so cat f_c phai duong")
        self.f_cutoff = float(f_cutoff_hz)

    def magnitude_response(self, f_hz: float) -> float:
        """Tinh do loi bien do cua bo loc Butterworth bac 2 o tan so f_hz."""
        ratio = f_hz / self.f_cutoff
        return 1.0 / math.sqrt(1.0 + (ratio ** 4))

    def magnitude_response_db(self, f_hz: float) -> float:
        """Tinh do loi bien do bang dB."""
        mag = self.magnitude_response(f_hz)
        return 20.0 * math.log10(max(1e-12, mag))

    def filter_waveform_time_domain(
        self,
        samples: List[float],
        dt: float
    ) -> List[float]:
        """
        Mo phong loc mien thoi gian bang phuong trinh vi phan bac 2 (RK4 hoac vi phan roi rac).
        y'' + (omega_0 / Q) y' + omega_0^2 y = omega_0^2 u
        """
        omega_0 = 2.0 * math.pi * self.f_cutoff
        q = 1.0 / math.sqrt(2.0)  # Butterworth damping
        
        y = samples[0] if samples else 0.0
        y_dot = 0.0
        filtered: List[float] = []

        for u in samples:
            # Tinh gia toc y_ddot
            y_ddot = (omega_0 ** 2) * (u - y) - (omega_0 / q) * y_dot
            # Tich phan so Euler-Cromer on dinh
            y_dot += y_ddot * dt
            y += y_dot * dt
            filtered.append(y)

        return filtered


def test_dac_reconstruction_and_filter():
    print("================================================================================")
    print("TEST SUITE: BO CHUYEN DOI DAC R-2R, SUY HAO ZOH VA BO LOC TAI TAO SALLEN-KEY")
    print("================================================================================")

    # 1. Kiem tra mang dien tro R-2R Ladder DAC 8-bit
    v_ref = 3.3
    dac_8b = R2RLadderDAC(num_bits=8, v_ref=v_ref, r_nominal_ohm=10000.0)
    print(f"[1] Khoi tao R-2R DAC 8-bit: V_ref={v_ref}V | LSB = {dac_8b.lsb_voltage*1000:.3f} mV")

    # Kiem tra ma 0, ma giua (128 = 0b10000000), va ma max (255)
    v_zero = dac_8b.convert_code_to_voltage(0)
    v_mid = dac_8b.convert_code_to_voltage(128)
    v_max = dac_8b.convert_code_to_voltage(255)

    print(f"    Code 0 -> {v_zero:.4f}V | Code 128 -> {v_mid:.4f}V (Ky vong {v_ref/2:.4f}V)")
    print(f"    Code 255 -> {v_max:.4f}V (Ky vong {v_ref * 255/256:.4f}V)")
    assert abs(v_zero) < 1e-6, "Code 0 phai ra 0V"
    assert abs(v_mid - (v_ref / 2.0)) < 1e-4, "Code 128 phai bang nua V_ref"
    assert abs(v_max - (v_ref * 255.0 / 256.0)) < 1e-4, "Code 255 phai sat V_ref"

    # 2. Kiem tra suy hao ZOH tai bien Nyquist f_s / 2
    f_s = 10.0e6  # 10 MSPS
    f_nyquist = f_s / 2.0  # 5 MHz
    sinc_nyquist_db = ZeroOrderHoldAnalyzer.sinc_attenuation_db(f_nyquist, f_s)
    expected_sinc_db = 20.0 * math.log10(2.0 / math.pi)  # -3.922 dB
    print(f"\n[2] Kiem tra suy hao ZOH sinc roll-off:")
    print(f"    - Tai f = 0 Hz: {ZeroOrderHoldAnalyzer.sinc_attenuation_db(0, f_s):.2f} dB")
    print(f"    - Tai bien Nyquist f = 5 MHz: {sinc_nyquist_db:.3f} dB (Ly thuyet: {expected_sinc_db:.3f} dB)")
    assert abs(sinc_nyquist_db - expected_sinc_db) < 0.01, "Loi suy hao sinc tai bien Nyquist"

    # 3. Kiem tra vi tri anh pho Nyquist Image
    f_sig = 2.0e6  # 2 MHz
    images = ZeroOrderHoldAnalyzer.calculate_nyquist_images(f_signal_hz=f_sig, f_sample_hz=f_s, max_k=2)
    print(f"\n[3] Phat hien cac anh pho Nyquist Image cua tin hieu {f_sig/1e6:.1f} MHz (f_s={f_s/1e6:.1f} MHz):")
    for img in images:
        print(f"    Image [{img['type']}]: f = {img['frequency_hz']/1e6:.2f} MHz | Suy hao sinc: {img['sinc_attenuation_db']:.2f} dB")
    
    # Anh pho dau tien phai nam tai 8 MHz (10 - 2) va 12 MHz (10 + 2)
    assert abs(images[0]['frequency_hz'] - 8.0e6) < 1e-3, "Loi vi tri anh pho dau tien"
    assert abs(images[1]['frequency_hz'] - 12.0e6) < 1e-3, "Loi vi tri anh pho thu hai"

    # 4. Kiem tra bo loc tai tao tich cuc Sallen-Key
    # Thiet ke bo loc co tan so cat f_c = 3.0 MHz (de tin hieu 2 MHz di qua va triet tieu 8 MHz)
    f_c = 3.0e6
    filter_sk = ActiveSallenKeyReconstructionFilter(f_cutoff_hz=f_c)
    gain_passband_db = filter_sk.magnitude_response_db(f_sig)
    gain_image1_db = filter_sk.magnitude_response_db(8.0e6)
    attenuation_image = gain_passband_db - gain_image1_db
    print(f"\n[4] Bo loc tai tao Sallen-Key Butterworth f_c = {f_c/1e6:.1f} MHz:")
    print(f"    - Do loi tai tin hieu goc (2 MHz): {gain_passband_db:.2f} dB")
    print(f"    - Do loi tai anh pho Nyquist (8 MHz): {gain_image1_db:.2f} dB")
    print(f"    - Do triet tieu anh pho (Rejection Ratio): {attenuation_image:.2f} dB")
    assert attenuation_image > 15.0, "Bo loc bac 2 phai triet tieu anh pho it nhat 15 dB o 8 MHz"

    # 5. Kiem tra loc mien thoi gian lam min song bac thang
    dt_sim = 1.0 / (100.0 * f_sig)
    num_pts = 200
    staircase = [1.65 + 1.0 * math.sin(2.0 * math.pi * f_sig * (i * dt_sim)) for i in range(num_pts)]
    smooth_out = filter_sk.filter_waveform_time_domain(staircase, dt=dt_sim)
    print(f"\n[5] Loc lam min song bac thang: {len(smooth_out)} mau thoi gian duoc loc thanh cong")
    assert len(smooth_out) == num_pts, "So luong mau loc phai dong nhat"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AT.3 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_dac_reconstruction_and_filter()
