"""
Chuyen de AU: Tuong thich Dien tu EMC/EMI & Ky thuat Tiep dia PCB Toc do cao
Bai 134 (Milestone AU.3): Ky thuat dieu bien pho trai rong xung nhip (Spread Spectrum Clocking - SSC)

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu ky thuat SSC triet tieu dinh phat xa EMI o cac hoa tan cao cua PCIe Gen 5/USB4/DDR5,
          tinh toan do suy giam dinh cong suat Peak Power Attenuation tren may thu do dai RBW,
          hieu ro co che dieu che tam giac Down-spread de khong vi pham gioi han Overclocking.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class SpreadSpectrumClockModel:
    """
    Mo hinh dieu che pho trai rong xung nhip Spread Spectrum Clocking (SSC).
    
    Phan tich toan hoc & vat ly pho:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Do lech tan so cuc dai (Frequency Deviation):     │
    │      Delta_f = delta * f_0                             │
    │                                                        │
    │      O hoa tan bac n: Delta_f_n = n * delta * f_0      │
    │                                                        │
    │   2. Che do Down-spread (PCIe Standard):               │
    │      f(t) nam trong [ f_0 * (1 - delta),  f_0 ]        │
    │      Giu cho logic so khong bao gio bi ep chay qua toc │
    │                                                        │
    │   3. Do suy giam dinh phat xa EMI tren may do RBW:     │
    │                                                        │
    │                           RBW                          │
    │      Atten (dB) = 10 * log10( ────────── )             │
    │                           Delta_f_n                    │
    │                                                        │
    │      Voi RBW chuan CISPR/FCC = 120 kHz                 │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        f0_hz: float = 100e6,           # 100 MHz clock co ban (PCIe ref clock)
        spread_percentage: float = 0.5, # 0.5% (delta = 0.005)
        f_modulation_hz: float = 31.5e3,# 31.5 kHz (tren nguong nghe thay am thanh)
        mode: str = "down_spread"       # "down_spread" hoac "center_spread"
    ):
        self.f0 = float(f0_hz)
        self.spread_ratio = float(spread_percentage) / 100.0
        self.f_mod = float(f_modulation_hz)
        self.mode = mode.lower()

        if self.mode not in ["down_spread", "center_spread"]:
            raise ValueError("Mode phai la 'down_spread' hoac 'center_spread'")

    def calculate_harmonic_deviation_hz(self, harmonic_order: int) -> float:
        """
        Tinh do rong dai tan trai rong Delta_f_n tai hoa tan thu n.
        """
        return harmonic_order * self.spread_ratio * self.f0

    def calculate_peak_attenuation_db(self, harmonic_order: int, rbw_hz: float = 120e3) -> float:
        """
        Tinh do suy giam dinh cong suat phat xa EMI tai hoa tan thu n do may thu do RBW ghi nhan.
        """
        delta_fn = self.calculate_harmonic_deviation_hz(harmonic_order)
        if delta_fn <= rbw_hz:
            return 0.0  # Chua du trai rong hon cua so RBW
        
        # Ti le giam mat do cong suat
        ratio = rbw_hz / delta_fn
        return 10.0 * math.log10(ratio)

    def instantaneous_frequency_hz(self, t_sec: float) -> float:
        """
        Tinh tan so tuc thoi f(t) theo ham song tam giac.
        """
        t_period = 1.0 / self.f_mod
        phase_in_period = (t_sec % t_period) / t_period  # [0, 1)

        # Ham tam giac chuan hoa [-1, +1]
        if phase_in_period < 0.5:
            tri = 4.0 * phase_in_period - 1.0  # -1 -> +1
        else:
            tri = 3.0 - 4.0 * phase_in_period  # +1 -> -1

        if self.mode == "down_spread":
            # [f0 * (1 - delta), f0]
            # Khi tri = -1 => f = f0 * (1 - delta)
            # Khi tri = +1 => f = f0
            norm_tri = (tri + 1.0) / 2.0  # 0 -> 1
            return self.f0 * (1.0 - self.spread_ratio * (1.0 - norm_tri))
        else:
            # Center spread: [f0 * (1 - delta/2), f0 * (1 + delta/2)]
            return self.f0 * (1.0 + (self.spread_ratio / 2.0) * tri)


class ClockSpectrumSimulator:
    """
    Mo phong dang song mien thoi gian va pho bien do FFT de so sanh
    giua Clock co dinh (CW Clock) va Clock trai pho (SSC Clock).
    """
    @staticmethod
    def simulate_clock_spectrum(
        clock_model: SpreadSpectrumClockModel,
        num_samples: int = 1024,
        t_span_sec: float = 2e-6
    ) -> Dict[str, any]:
        dt = t_span_sec / num_samples
        cw_samples = []
        ssc_samples = []

        phase_cw = 0.0
        phase_ssc = 0.0

        for i in range(num_samples):
            t = i * dt
            # Clock co dinh f0
            phase_cw += 2.0 * math.pi * clock_model.f0 * dt
            cw_samples.append(1.0 if math.sin(phase_cw) >= 0.0 else -1.0)

            # Clock SSC
            f_inst = clock_model.instantaneous_frequency_hz(t)
            phase_ssc += 2.0 * math.pi * f_inst * dt
            ssc_samples.append(1.0 if math.sin(phase_ssc) >= 0.0 else -1.0)

        return {
            "num_samples": num_samples,
            "dt": dt,
            "cw_samples": cw_samples,
            "ssc_samples": ssc_samples
        }


def test_spread_spectrum_clocking():
    print("================================================================================")
    print("TEST SUITE: DIEU BIEN PHO TRAI RONG XUNG NHIP (SSC) TRIET TIEU EMI")
    print("================================================================================")

    # 1. Kiem tra tinh toan do suy giam dinh EMI cho xung clock PCIe 100 MHz, 0.5% Down-Spread
    f0 = 100e6  # 100 MHz
    ssc = SpreadSpectrumClockModel(f0_hz=f0, spread_percentage=0.5, f_modulation_hz=31.5e3, mode="down_spread")
    rbw = 120e3 # 120 kHz chuan may thu EMI CISPR/FCC

    print(f"[1] Clock PCIe {f0/1e6:.0f} MHz voi Down-Spread 0.5% (f_mod = 31.5 kHz, RBW = 120 kHz):")
    
    # Kiem tra tai tan so co ban (n = 1):
    delta_f1 = ssc.calculate_harmonic_deviation_hz(harmonic_order=1)
    atten_f1 = ssc.calculate_peak_attenuation_db(harmonic_order=1, rbw_hz=rbw)
    print(f"    - Hoa tan co ban f0 (100 MHz):  Do lech = {delta_f1/1e3:.1f} kHz | Suy giam dinh = {atten_f1:.2f} dB")
    expected_atten_f1 = 10.0 * math.log10(120.0 / 500.0)
    assert abs(atten_f1 - expected_atten_f1) < 0.1, "Loi tinh suy giam hoa tan co ban"

    # Kiem tra tai hoa tan thu 10 (1 GHz):
    delta_f10 = ssc.calculate_harmonic_deviation_hz(harmonic_order=10)
    atten_f10 = ssc.calculate_peak_attenuation_db(harmonic_order=10, rbw_hz=rbw)
    print(f"    - Hoa tan bac 10   (1.0 GHz):  Do lech = {delta_f10/1e6:.2f} MHz  | Suy giam dinh = {atten_f10:.2f} dB")
    expected_atten_f10 = 10.0 * math.log10(120e3 / 5e6)
    assert abs(atten_f10 - expected_atten_f10) < 0.1, "Loi tinh suy giam hoa tan bac 10"

    # Kiem tra tai hoa tan bac 25 (2.5 GHz - bang tan Wi-Fi/Bluetooth):
    delta_f25 = ssc.calculate_harmonic_deviation_hz(harmonic_order=25)
    atten_f25 = ssc.calculate_peak_attenuation_db(harmonic_order=25, rbw_hz=rbw)
    print(f"    - Hoa tan bac 25   (2.5 GHz):  Do lech = {delta_f25/1e6:.2f} MHz | Suy giam dinh = {atten_f25:.2f} dB")
    assert atten_f25 < -19.0, "Tai 2.5 GHz dinh buc xa phai giam hon 19 dB!"

    # 2. Kiem tra rang buoc Down-spread khong bao gio vuot qua tan so danh dinh f0
    test_times = [i * 1e-6 for i in range(100)]
    inst_freqs = [ssc.instantaneous_frequency_hz(t) for t in test_times]
    max_f = max(inst_freqs)
    min_f = min(inst_freqs)

    print(f"\n[2] Kiem tra dac tinh Down-spread khong vi pham gioi han mach so:")
    print(f"    - Tan so cao nhat dat duoc: {max_f / 1e6:.4f} MHz (Ky vong <= 100.0000 MHz)")
    print(f"    - Tan so thap nhat dat duoc: {min_f / 1e6:.4f} MHz (Ky vong = 99.5000 MHz)")
    assert max_f <= f0 + 1e-6, "Down-spread khong duoc phep vuot qua f0"
    assert abs(min_f - f0 * 0.995) < 1e-3, "Tan so thap nhat phai la 99.5% cua f0"

    # 3. Kiem tra Center-spread [-0.25%, +0.25%]
    ssc_center = SpreadSpectrumClockModel(f0_hz=f0, spread_percentage=0.5, mode="center_spread")
    c_freqs = [ssc_center.instantaneous_frequency_hz(t) for t in test_times]
    print(f"\n[3] Kiem tra Center-spread (0.5% tong dai):")
    print(f"    - Dai tan: [{min(c_freqs)/1e6:.3f} MHz, {max(c_freqs)/1e6:.3f} MHz]")
    assert abs(min(c_freqs) - 99.75e6) < 1e5, "Center spread min phai xap xi 99.75 MHz"
    assert abs(max(c_freqs) - 100.25e6) < 1e5, "Center spread max phai xap xi 100.25 MHz"

    # 4. Kiem tra mo phong mien thoi gian
    sim_res = ClockSpectrumSimulator.simulate_clock_spectrum(ssc, num_samples=512)
    print(f"\n[4] Mo phong 512 mau clock SSC hoan thanh thanh cong.")
    assert len(sim_res["ssc_samples"]) == 512, "So mau SSC phai la 512"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AU.3 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_spread_spectrum_clocking()
