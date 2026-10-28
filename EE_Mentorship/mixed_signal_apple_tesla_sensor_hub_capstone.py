"""
Chuyen de AT: Mach Tin hieu Hon hop Mixed-Signal & Bo chuyen doi ADC/DAC Toc do cao
Bai 131 (Milestone AT.4 - Capstone Project): Dong co Mixed-Signal Sensor Hub Apple va Tesla FSD HW4 Capstone

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Xay dung dong co he thong tin hieu hon hop Mixed-Signal AFE & ADC hoan chinh cho chip Apple Silicon
          va cum cam bien quan tinh IMU / Radar xe tu hanh Tesla FSD HW4. Tich hop tang khuech dai do luong PGA,
          mo hinh khu nhieu dong pha CMRR > 100 dB, bo chuyen doi SAR ADC 16-bit 10 MSPS, bo tu dong hieu chuan
          Auto-Calibration va bo phan tich pho dong hoc SINAD / ENOB / SFDR.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class AnalogFrontEndPGA:
    """
    Tang tuong tu dau vao vi sai hoan toan Fully-Differential Programmable Gain Amplifier (PGA).
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Tin hieu vi sai:   V_diff = V_in_pos - V_in_neg      │
    │   Tin hieu dong pha: V_cm   = (V_in_pos + V_in_neg) / 2│
    │                                                        │
    │   He so khu dong pha CMRR:                             │
    │                   A_diff                               │
    │   CMRR (dB) = 20 * log10( ────── )                     │
    │                   A_cm                                 │
    │                                                        │
    │   Nhiet nhieu Johnson-Nyquist:                         │
    │   V_noise_rms = sqrt( 4 * k_B * T * R * Delta_f )      │
    │                                                        │
    │   V_out_diff = Gain * ( V_diff + V_cm / 10^(CMRR/20) ) │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        gain: float = 16.0,
        cmrr_db: float = 105.0,
        bandwidth_hz: float = 5.0e6,
        r_source_ohm: float = 500.0,
        temperature_kelvin: float = 300.0
    ):
        self.gain = float(gain)
        self.cmrr_db = float(cmrr_db)
        self.bandwidth_hz = float(bandwidth_hz)
        self.r_source_ohm = float(r_source_ohm)
        self.temperature = float(temperature_kelvin)

        # Hang so Boltzmann k_B = 1.380649e-23 J/K
        k_b = 1.380649e-23
        # Dien ap nhieu nhiet Johnson-Nyquist RMS
        self.v_thermal_noise_rms = math.sqrt(4.0 * k_b * self.temperature * self.r_source_ohm * self.bandwidth_hz)
        self.a_cm = self.gain / (10.0 ** (self.cmrr_db / 20.0))

    def amplify_differential_signal(
        self,
        v_pos: float,
        v_neg: float,
        noise_seed: float = 0.0
    ) -> float:
        """
        Khuech dai tin hieu vi sai, triet tieu nhieu dong pha CMRR va bo sung nhieu nhiet.
        """
        v_diff = v_pos - v_neg
        v_cm = (v_pos + v_neg) / 2.0
        
        # Nhieu dong pha xuyen vao vi sai
        cm_leakage = v_cm * (10.0 ** (-self.cmrr_db / 20.0))
        
        # Gia lap thanh phan nhieu nhiet co dinh theo seed
        thermal_perturbation = self.v_thermal_noise_rms * math.sin(noise_seed * 1337.1)

        v_out_diff = self.gain * (v_diff + cm_leakage + thermal_perturbation)
        return v_out_diff


class CalibratedSARADC16Bit:
    """
    Bo chuyen doi SAR ADC 16-bit 10 MSPS voi kha nang tu dong hieu chuan Offset & Gain.
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Hieu chuan so (Digital Calibration):                 │
    │                                                        │
    │   V_corrected = (V_raw - V_offset) * (1 / Gain_error)  │
    │                                                        │
    │   Do phan giai 16-bit: 65,536 muc luong tu             │
    │   V_ref vi sai: [-1.25V, +1.25V] (V_FS = 2.5V)         │
    │   LSB Delta = 2.5V / 65536 = 38.147 uV                 │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        v_ref: float = 1.25,
        aperture_jitter_sec: float = 250e-15,  # 250 femtoseconds
        raw_offset_mv: float = 3.5,            # Sai so 0 ban dau
        raw_gain_error_pct: float = 1.2        # Sai so do loi ban dau
    ):
        self.num_bits = 16
        self.v_ref = float(v_ref)
        self.v_fs = 2.0 * self.v_ref
        self.num_levels = 1 << self.num_bits
        self.delta = self.v_fs / float(self.num_levels)
        self.jitter_sec = float(aperture_jitter_sec)

        # Sai so phan cung chua hieu chuan
        self.hardware_offset = raw_offset_mv * 1e-3
        self.hardware_gain_factor = 1.0 + (raw_gain_error_pct / 100.0)

        # Tham so hieu chuan luu trong EEPROM / eFuse
        self.cal_offset = 0.0
        self.cal_gain_factor = 1.0
        self.is_calibrated = False

    def perform_factory_calibration(self, zero_sample_volts: float, full_scale_sample_volts: float):
        """
        Thuc hien hieu chuan 2 diem (Two-Point Offset & Gain Calibration).
        """
        # Do dien ap khi dau vao vi sai = 0.0 V
        self.cal_offset = zero_sample_volts
        
        # Do dien ap khi dau vao vi sai = V_ref
        measured_span = full_scale_sample_volts - zero_sample_volts
        ideal_span = self.v_ref
        self.cal_gain_factor = measured_span / ideal_span
        self.is_calibrated = True

    def convert_sample(self, v_in_diff: float, t_sample: float) -> Tuple[int, float]:
        """
        Chuyen doi tin hieu vi sai sang ma 16-bit va dien ap khoi phuc.
        """
        # Mo hinh sai so phan cung
        v_hw = (v_in_diff * self.hardware_gain_factor) + self.hardware_offset

        # Bù tru hieu chuan neu da duoc calibrate
        if self.is_calibrated:
            v_cal = (v_hw - self.cal_offset) / self.cal_gain_factor
        else:
            v_cal = v_hw

        # Luong tu hoa 16-bit
        v_clamped = max(-self.v_ref, min(self.v_ref - 1e-9, v_cal))
        raw_code = int(math.floor((v_clamped + self.v_ref) / self.delta))
        code = max(0, min(self.num_levels - 1, raw_code))
        v_reconstructed = -self.v_ref + (code + 0.5) * self.delta

        return code, v_reconstructed


class MixedSignalDynamicSpectralAnalyzer:
    """
    Bo phan tich pho dong hoc SINAD, ENOB, SFDR, THD dung thuat toan DFT.
    
    Phan tich chi so chat luong:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │                   P_signal                             │
    │   SINAD (dB) = 10 * log10( ─────────────────────── )   │
    │                            P_noise + P_distortion      │
    │                                                        │
    │            SINAD - 1.76                                │
    │   ENOB   = ────────────                                │
    │                6.02                                    │
    │                                                        │
    │                  P_signal                              │
    │   SFDR (dBc) = 10 * log10( ────────── )                │
    │                            P_spur_max                  │
    │                                                        │
    │                 Tong(P_harmonics)                      │
    │   THD (dB)   = 10 * log10( ───────────────── )         │
    │                            P_signal                    │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def analyze_spectrum(
        samples: List[float],
        fund_freq_hz: float,
        f_sample_hz: float
    ) -> Dict[str, float]:
        n = len(samples)
        half_n = n // 2
        
        # Tinh DFT pho cong suat
        power_bins: List[float] = []
        for k in range(half_n):
            real_sum = 0.0
            imag_sum = 0.0
            omega = 2.0 * math.pi * k / float(n)
            for idx, x in enumerate(samples):
                real_sum += x * math.cos(omega * idx)
                imag_sum -= x * math.sin(omega * idx)
            # Bien do
            mag = (math.sqrt(real_sum * real_sum + imag_sum * imag_sum) * 2.0) / float(n)
            power_bins.append(mag * mag)

        # Tim bin cua song hai chinh (Fundamental)
        bin_fund = int(round(fund_freq_hz * n / f_sample_hz))
        bin_fund = max(1, min(half_n - 1, bin_fund))
        p_fund = power_bins[bin_fund]

        # Tim cac song hai bac 2, 3, 4, 5
        harmonic_bins = []
        p_harmonics = 0.0
        for h in range(2, 6):
            bin_h = int(round(h * fund_freq_hz * n / f_sample_hz))
            if bin_h < half_n:
                harmonic_bins.append(bin_h)
                p_harmonics += power_bins[bin_h]

        # Tong cong suat nhieu (tat ca cac bin tru DC va song hai chinh)
        p_noise_dist = 0.0
        spurious_powers = []
        for k in range(1, half_n):
            if k == bin_fund:
                continue
            p_noise_dist += power_bins[k]
            spurious_powers.append(power_bins[k])

        p_noise_dist = max(1e-15, p_noise_dist)
        p_harmonics = max(1e-15, p_harmonics)
        max_spur = max(spurious_powers) if spurious_powers else 1e-15

        sinad_db = 10.0 * math.log10(p_fund / p_noise_dist)
        enob = (sinad_db - 1.7609) / 6.0206
        sfdr_dbc = 10.0 * math.log10(p_fund / max_spur)
        thd_db = 10.0 * math.log10(p_harmonics / p_fund)

        return {
            "sinad_db": sinad_db,
            "enob": enob,
            "sfdr_dbc": sfdr_dbc,
            "thd_db": thd_db,
            "fundamental_power": p_fund
        }


class AppleTeslaMixedSignalSensorHub:
    """
    Dong co he thong Sensor Hub Mixed-Signal tich hop hoan chinh.
    """
    def __init__(self, target_application: str = "Tesla_FSD_HW4_IMU"):
        self.app_name = target_application
        # PGA Gain = 8.0, CMRR = 110 dB, Anti-Aliasing Bandwidth = 1.0 MHz
        self.pga = AnalogFrontEndPGA(gain=8.0, cmrr_db=110.0, bandwidth_hz=1.0e6)
        # SAR ADC 16-bit voi Aperture Jitter 200 fs
        self.adc = CalibratedSARADC16Bit(v_ref=1.25, aperture_jitter_sec=200e-15)

    def calibrate_subsystem(self):
        """Thuc hien can chinh tu dong truoc khi van hanh."""
        # Dua tin hieu test 0V va 0.15625V (de qua PGA 8x ra 1.25V)
        v_zero_raw = (0.0 * self.adc.hardware_gain_factor) + self.adc.hardware_offset
        v_fs_raw = (1.25 * self.adc.hardware_gain_factor) + self.adc.hardware_offset
        self.adc.perform_factory_calibration(v_zero_raw, v_fs_raw)

    def process_sensor_stream(
        self,
        v_diff_stream: List[float],
        v_common_noise_stream: List[float],
        f_sample_hz: float
    ) -> Dict[str, any]:
        """
        Xu ly toan bo chuoi tin hieu tu cam bien qua AFE -> ADC -> DSP Spectrum Analyzer.
        """
        pga_outputs: List[float] = []
        adc_codes: List[int] = []
        adc_voltages: List[float] = []

        dt = 1.0 / f_sample_hz
        for idx, (vd, vcm) in enumerate(zip(v_diff_stream, v_common_noise_stream)):
            # Chuyen doi qua tin hieu vi sai
            v_p = (vd / 2.0) + vcm
            v_n = (-vd / 2.0) + vcm

            # Qua tang PGA
            v_amplified = self.pga.amplify_differential_signal(v_p, v_n, noise_seed=float(idx))
            pga_outputs.append(v_amplified)

            # Qua ADC 16-bit
            code, v_rec = self.adc.convert_sample(v_amplified, t_sample=idx * dt)
            adc_codes.append(code)
            adc_voltages.append(v_rec)

        return {
            "pga_outputs": pga_outputs,
            "adc_codes": adc_codes,
            "adc_voltages": adc_voltages
        }


def test_mixed_signal_sensor_hub_capstone():
    print("================================================================================")
    print("TEST SUITE CAPSTONE: DONG CO MIXED-SIGNAL SENSOR HUB APPLE & TESLA FSD HW4")
    print("================================================================================")

    # 1. Kiem tra tang PGA vi sai hoan toan va ti le triet nhieu dong pha CMRR
    # Ban rong bo loc chong chong pho (Anti-Aliasing Filter) 1.0 MHz de toi uu nhieu nhiet
    pga = AnalogFrontEndPGA(gain=8.0, cmrr_db=110.0, bandwidth_hz=1.0e6)
    # Tín hiệu vi sai 50 mV (V_diff = 0.05V) kem theo nhieu dong pha dong co 2.0V (V_cm = 2.0V)
    v_pos = 1.025
    v_neg = 0.975
    # V_diff = 0.05 V, V_cm = 1.0 V
    v_out = pga.amplify_differential_signal(v_pos, v_neg, noise_seed=0.0)
    ideal_out = 8.0 * 0.05  # 0.40 V
    print(f"[1] Kiem tra Tang AFE PGA (Gain=8.0, CMRR=110 dB):")
    print(f"    V_diff=50 mV kem V_cm=1.0 V -> V_out = {v_out:.5f} V (Ky vong = {ideal_out:.5f} V)")
    assert abs(v_out - ideal_out) < 0.001, "Loi khuech dai PGA hoac xuyen nhieu CMRR vuot muc"

    # 2. Kiem tra Auto-Calibration cua SAR ADC 16-bit
    adc = CalibratedSARADC16Bit(v_ref=1.25, raw_offset_mv=5.0, raw_gain_error_pct=2.0)
    # Truoc khi calibrate
    code_uncal, v_uncal = adc.convert_sample(0.0, t_sample=0.0)
    print(f"\n[2] Kiem tra Tu dong Hieu chuan (Auto-Calibration):")
    print(f"    Truoc hieu chuan: V_in = 0.0V -> Do duoc = {v_uncal*1000:.2f} mV (Bi lech 5 mV)")
    assert abs(v_uncal) > 0.004, "Phan cung phai co offset 5 mV"

    # Tien hanh hieu chuan 2 diem
    v_zero_raw = (0.0 * adc.hardware_gain_factor) + adc.hardware_offset
    v_fs_raw = (1.25 * adc.hardware_gain_factor) + adc.hardware_offset
    adc.perform_factory_calibration(v_zero_raw, v_fs_raw)

    code_cal, v_cal = adc.convert_sample(0.0, t_sample=0.0)
    print(f"    Sau hieu chuan 2 diem: V_in = 0.0V -> Do duoc = {v_cal*1000:.3f} mV (Triet tieu offset ve 0)")
    assert abs(v_cal) < adc.delta, "Sau hieu chuan offset phai be hon 1 LSB"

    # 3. Kiem tra toan bo chuoi he thong Mixed-Signal Sensor Hub voi tin hieu thuc te
    f_s = 10.0e6  # 10 MSPS
    f_sig = 156250.0  # 156.25 kHz (chinh xac 4 chu ky tren 256 mau de khong can cua so FFT)
    num_pts = 256
    t_arr = [i / f_s for i in range(num_pts)]

    # Tin hieu vi sai cam bien goc quay banh xe Tesla IMU bien do 100 mV (0.1 V)
    # Qua PGA 8x se thanh 0.8 V tren V_ref = 1.25 V
    diff_stream = [0.1 * math.sin(2.0 * math.pi * f_sig * t) for t in t_arr]
    # Nhieu dong pha cao tan do bien tan SiC dong co phat ra (bien do 1.5V)
    cm_noise_stream = [1.5 * math.cos(2.0 * math.pi * 500e3 * t) for t in t_arr]

    sensor_hub = AppleTeslaMixedSignalSensorHub(target_application="Tesla_FSD_HW4_IMU")
    # Dat dai thong AFE sensor hub xuong 1 MHz chong nhieu
    sensor_hub.pga.bandwidth_hz = 1.0e6
    sensor_hub.calibrate_subsystem()
    results = sensor_hub.process_sensor_stream(diff_stream, cm_noise_stream, f_sample_hz=f_s)

    # 4. Phan tich pho dong hoc SINAD, ENOB, SFDR, THD
    metrics = MixedSignalDynamicSpectralAnalyzer.analyze_spectrum(
        samples=results["adc_voltages"],
        fund_freq_hz=f_sig,
        f_sample_hz=f_s
    )

    print(f"\n[3] Ket qua Kiem chuan Pho Dong hoc Mixed-Signal Hub (256 FFT Bins):")
    print(f"    - SINAD: {metrics['sinad_db']:.2f} dB")
    print(f"    - ENOB:  {metrics['enob']:.2f} bits (Tieu chuan ASIL-D / Apple Bio: >= 13.0 bits)")
    print(f"    - SFDR:  {metrics['sfdr_dbc']:.2f} dBc (Dai dong khong tap am)")
    print(f"    - THD:   {metrics['thd_db']:.2f} dB (Meo song hai toan phan)")

    assert metrics["enob"] >= 13.0, f"ENOB he thong qua thap: {metrics['enob']}"
    assert metrics["sfdr_dbc"] >= 80.0, f"SFDR qua thap: {metrics['sfdr_dbc']}"
    print("    -> Dat chuan do luong tin hieu hon hop cho Apple Neural Sensor va Tesla FSD HW4!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AT.4 CAPSTONE DA THANH CONG 100%!")


if __name__ == "__main__":
    test_mixed_signal_sensor_hub_capstone()
