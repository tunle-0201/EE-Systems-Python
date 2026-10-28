"""
Chuyen de AT: Mach Tin hieu Hon hop Mixed-Signal & Bo chuyen doi ADC/DAC Toc do cao
Bai 128 (Milestone AT.1): Mo hinh luong tu hoa ADC, meo DNL/INL va truyen dan rung pha Aperture Jitter

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu mo hinh vat ly chuyen doi A/D, phan tich suy giam SNR/ENOB do Clock Jitter o tan so cao,
          va phat hien ma thieu Missing Codes tren chip Apple Silicon & Tesla FSD HW4.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class ADCQuantizationModel:
    """
    Mo hinh luong tu hoa ADC N-bit vi sai [-V_ref, +V_ref].
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │                      2 * V_ref                         │
    │   Do rong buoc Delta = ─────────                       │
    │                         2^N                            │
    │                                                        │
    │                     Delta^2                            │
    │   Cong suat nhiễu P_q = ────────                       │
    │                        12                              │
    │                                                        │
    │   SNR_ideal (dB) = 6.02 * N + 1.76                     │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, num_bits: int, v_ref: float = 1.0):
        if num_bits < 2 or num_bits > 24:
            raise ValueError("So bit ADC phai tu 2 den 24")
        if v_ref <= 0.0:
            raise ValueError("Dien ap tham chieu V_ref phai duong")
            
        self.num_bits = num_bits
        self.v_ref = float(v_ref)
        self.num_levels = 1 << num_bits
        self.v_fs = 2.0 * self.v_ref  # Full-scale range [-V_ref, +V_ref]
        self.delta = self.v_fs / self.num_levels

    def ideal_snr_db(self) -> float:
        """Tinh SNR ly tuong do loi luong tu hoa."""
        return 6.0206 * self.num_bits + 1.7609

    def quantize_sample(self, v_in: float) -> Tuple[int, float]:
        """
        Luong tu hoa mot mau dien ap v_in thanh ma nhi phan va dien ap tai tao v_q.
        Clip v_in trong khoang [-V_ref, +V_ref - Delta].
        """
        # Bão hòa điện áp đầu vào
        v_clamped = max(-self.v_ref, min(self.v_ref - 1e-12, v_in))
        
        # Chuyển đổi sang mức mã số nguyên [0, num_levels - 1]
        raw_code = int(math.floor((v_clamped + self.v_ref) / self.delta))
        code = max(0, min(self.num_levels - 1, raw_code))
        
        # Điện áp tái tạo tương ứng với tâm của bước lượng tử
        v_reconstructed = -self.v_ref + (code + 0.5) * self.delta
        return code, v_reconstructed

    def quantize_waveform(self, samples: List[float]) -> Tuple[List[int], List[float], float]:
        """
        Luong tu hoa day tin hieu va tinh cong suat loi luong tu hoa RMS.
        Tra ve (danh sach ma, danh sach dien ap tai tao, rms_error).
        """
        codes: List[int] = []
        v_reconstructed: List[float] = []
        error_sq_sum = 0.0

        for s in samples:
            c, vr = self.quantize_sample(s)
            codes.append(c)
            v_reconstructed.append(vr)
            err = vr - s
            error_sq_sum += err * err

        rms_err = math.sqrt(error_sq_sum / max(1, len(samples)))
        return codes, v_reconstructed, rms_err


class ADCNonLinearityAnalyzer:
    """
    Phan tich sai so phi tuyen vi phan DNL va phi tuyen tich luy INL.
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │             W[k] - Delta                               │
    │   DNL[k] = ──────────────  (don vi LSB)                │
    │                 Delta                                  │
    │                                                        │
    │             T[k] - T_ideal[k]                          │
    │   INL[k] = ─────────────────── = Tong(DNL[0..k-1])     │
    │                    Delta                               │
    │                                                        │
    │   Neu DNL[k] <= -1.0 LSB => Ma bi thieu (Missing Code) │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, num_bits: int, nominal_delta: float):
        self.num_bits = num_bits
        self.nominal_delta = nominal_delta
        self.num_levels = 1 << num_bits

    def analyze_from_transition_voltages(self, transitions: List[float]) -> Dict[str, any]:
        """
        Phan tich DNL va INL tu danh sach dien ap nguong chuyen doi transition voltages T[1..N-1].
        """
        n_transitions = len(transitions)
        if n_transitions != self.num_levels - 1:
            raise ValueError(f"So nguong chuyen phai la {self.num_levels - 1}, nhan {n_transitions}")

        # Tinh chieu rong tung ma W[k]
        code_widths: List[float] = []
        # Khoang dau tien tu -V_ref den T[0]
        code_widths.append(transitions[0] - (-self.nominal_delta * (self.num_levels / 2.0)))
        for k in range(len(transitions) - 1):
            code_widths.append(transitions[k + 1] - transitions[k])
        # Khoang cuoi cung tu T[-1] den +V_ref
        code_widths.append((self.nominal_delta * (self.num_levels / 2.0)) - transitions[-1])

        dnl_list: List[float] = []
        missing_codes: List[int] = []
        for code_idx, w in enumerate(code_widths):
            dnl = (w - self.nominal_delta) / self.nominal_delta
            dnl_list.append(dnl)
            if dnl <= -0.9999:
                missing_codes.append(code_idx)

        # Tinh INL bang cach tich luy DNL
        inl_list: List[float] = []
        cumulative_dnl = 0.0
        for dnl in dnl_list[:-1]:
            cumulative_dnl += dnl
            inl_list.append(cumulative_dnl)

        max_dnl = max(abs(x) for x in dnl_list)
        max_inl = max(abs(x) for x in inl_list) if inl_list else 0.0

        return {
            "dnl": dnl_list,
            "inl": inl_list,
            "max_abs_dnl_lsb": max_dnl,
            "max_abs_inl_lsb": max_inl,
            "missing_codes": missing_codes,
            "is_monotonic": len(missing_codes) == 0 and min(dnl_list) > -1.0
        }


class ApertureJitterAnalyzer:
    """
    Phan tich anh huong cua rung pha lay mau Aperture Jitter len SNR va ENOB.
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │                                1                       │
    │   SNR_jitter = 20 * log10( ───────────────────── )      │
    │                            2 * pi * f_in * t_j     │
    │                                                        │
    │                                                        │
    │   SNR_total = -10 * log10( 10^(-SNR_q/10) +            │
    │                            10^(-SNR_j/10) )            │
    │                                                        │
    │             SNR_total - 1.76                           │
    │   ENOB    = ────────────────                           │
    │                   6.02                                 │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def calculate_jitter_snr_db(f_in_hz: float, t_jitter_sec: float) -> float:
        """
        Tinh gioi han SNR toi da gay ra boi Aperture Jitter.
        t_jitter_sec la sai so thoi gian RMS (vi du 500 femtoseconds = 500e-15 s).
        """
        if f_in_hz <= 0.0 or t_jitter_sec <= 0.0:
            return 999.0
        val = 2.0 * math.pi * f_in_hz * t_jitter_sec
        return -20.0 * math.log10(val)

    @staticmethod
    def calculate_effective_enob(
        num_bits: int,
        f_in_hz: float,
        t_jitter_sec: float,
        thermal_snr_db: float = 120.0
    ) -> Tuple[float, float, float]:
        """
        Tinh SNR tong hop va ENOB khi ket hop loi luong tu hoa, jitter va nhiet.
        Tra ve (snr_total_db, enob, snr_jitter_db).
        """
        snr_quant = 6.0206 * num_bits + 1.7609
        snr_jitter = ApertureJitterAnalyzer.calculate_jitter_snr_db(f_in_hz, t_jitter_sec)
        
        # Tong hop cong suat nhiễu
        p_quant = 10.0 ** (-snr_quant / 10.0)
        p_jitter = 10.0 ** (-snr_jitter / 10.0)
        p_thermal = 10.0 ** (-thermal_snr_db / 10.0)
        
        p_total = p_quant + p_jitter + p_thermal
        snr_total = -10.0 * math.log10(p_total)
        enob = (snr_total - 1.7609) / 6.0206
        return snr_total, enob, snr_jitter


def _simple_fft_real(signal: List[float]) -> Tuple[List[float], List[float]]:
    """
    Bien doi Fourier roi rac (DFT) de tinh pho cong suat ma khong can thu vien ngoai.
    Dung de phan tich SINAD, SFDR, THD.
    Tra ve (frequencies_norm, magnitude_db).
    """
    n = len(signal)
    magnitudes_db: List[float] = []
    freqs: List[float] = []

    # Tinh n // 2 bins
    half_n = n // 2
    for k in range(half_n):
        real_sum = 0.0
        imag_sum = 0.0
        omega = 2.0 * math.pi * k / n
        for t_idx, x in enumerate(signal):
            real_sum += x * math.cos(omega * t_idx)
            imag_sum -= x * math.sin(omega * t_idx)
        
        mag = math.sqrt(real_sum * real_sum + imag_sum * imag_sum) / (n / 2.0)
        mag_db = 20.0 * math.log10(max(1e-12, mag))
        magnitudes_db.append(mag_db)
        freqs.append(k / float(n))

    return freqs, magnitudes_db


def test_adc_quantization_and_jitter():
    print("================================================================================")
    print("TEST SUITE: BIEU DIEN LUONG TU HOA ADC, ME DNL/INL VA APERTURE JITTER")
    print("================================================================================")

    # 1. Kiem tra ADC Quantizer co ban 12-bit
    adc_12b = ADCQuantizationModel(num_bits=12, v_ref=1.2)
    snr_ideal_12b = adc_12b.ideal_snr_db()
    print(f"[1] ADC 12-bit V_ref=1.2V | Delta = {adc_12b.delta * 1000:.3f} mV")
    print(f"    SNR ly tuong: {snr_ideal_12b:.2f} dB")
    assert abs(snr_ideal_12b - (6.02 * 12 + 1.76)) < 0.1, "Loi tinh SNR ly tuong"

    # Luong tu hoa tin hieu sin 1.0V bien do
    num_samples = 256
    t_vals = [i / float(num_samples) for i in range(num_samples)]
    sine_wave = [1.0 * math.sin(2.0 * math.pi * 3.0 * t) for t in t_vals]
    codes, v_rec, rms_err = adc_12b.quantize_waveform(sine_wave)

    theoretical_rms_noise = adc_12b.delta / math.sqrt(12.0)
    print(f"    Thuc nghiem RMS Error = {rms_err*1000:.3f} mV | Ly thuyet Delta/sqrt(12) = {theoretical_rms_noise*1000:.3f} mV")
    assert abs(rms_err - theoretical_rms_noise) < 0.0003, "Loi sai so luong tu hoa RMS vuot muc ly thuyet"

    # 2. Kiem tra phan tich DNL / INL va phat hien Missing Code
    delta_nom = 0.1
    # Tao ADC 3-bit (8 muc, 7 nguong chuyen doi)
    # Nguong ly tuong cho 3-bit [-0.4, +0.4]: -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3
    ideal_trans = [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3]
    analyzer = ADCNonLinearityAnalyzer(num_bits=3, nominal_delta=delta_nom)
    rep_ideal = analyzer.analyze_from_transition_voltages(ideal_trans)
    print(f"[2] Kiem tra DNL/INL ly tuong: Max DNL={rep_ideal['max_abs_dnl_lsb']:.3f} LSB, Monotonic={rep_ideal['is_monotonic']}")
    assert rep_ideal['max_abs_dnl_lsb'] < 1e-4, "ADC ly tuong phai co DNL = 0"
    assert rep_ideal['is_monotonic'] is True, "ADC ly tuong phai don dieu"

    # Tao nguong co loi missing code (khoang giua bi co hep ve 0)
    # Lam cho ma thu 3 co chieu rong = 0 (T[2] trung T[3])
    faulty_trans = [-0.3, -0.2, 0.0, 0.0, 0.1, 0.2, 0.3]
    rep_faulty = analyzer.analyze_from_transition_voltages(faulty_trans)
    print(f"    Kiem tra loi Missing Code: Phat hien cac ma thieu: {rep_faulty['missing_codes']}")
    assert len(rep_faulty['missing_codes']) > 0, "Phai phat hien Missing Code khi do rong ma <= 0"
    assert rep_faulty['is_monotonic'] is False, "ADC loi khong duoc don dieu"

    # 3. Kiem tra suy giam SNR va ENOB do Aperture Jitter
    # Xet ADC 16-bit lay mau tin hieu cao tan 100 MHz
    f_in_rf = 100e6  # 100 MHz
    t_jitter_pico = 1.0e-12  # 1 picosecond jitter
    snr_tot, enob_act, snr_jit = ApertureJitterAnalyzer.calculate_effective_enob(
        num_bits=16,
        f_in_hz=f_in_rf,
        t_jitter_sec=t_jitter_pico
    )
    print(f"[3] Xet ADC 16-bit o tan so RF f_in = 100 MHz:")
    print(f"    - SNR do Jitter 1 ps: {snr_jit:.2f} dB")
    print(f"    - SNR tong hop: {snr_tot:.2f} dB (so voi ly tuong 16-bit: {6.02*16+1.76:.2f} dB)")
    print(f"    - ENOB thuc te bi sup do con: {enob_act:.2f} bits!")
    assert enob_act < 11.0, "Jitter 1 ps o 100 MHz phai lam ENOB 16-bit sup giam xuong duoi 11 bits"

    # Xet clock sieu sach Apple/Tesla: Jitter giam con 200 fs (0.2 ps)
    t_jitter_clean = 200e-15  # 200 fs
    snr_clean, enob_clean, _ = ApertureJitterAnalyzer.calculate_effective_enob(
        num_bits=16,
        f_in_hz=f_in_rf,
        t_jitter_sec=t_jitter_clean
    )
    print(f"    - Khi toi uu Clock Jitter xuong 200 fs: SNR={snr_clean:.2f} dB, ENOB phuc hoi={enob_clean:.2f} bits")
    assert enob_clean > enob_act + 2.0, "Clock 200 fs phai phuc hoi hon 2 bits ENOB"

    # 4. Kiem tra bien doi DFT / FFT phan tich pho
    _, mags = _simple_fft_real(sine_wave)
    peak_fund = max(mags)
    print(f"[4] Kiem tra pho FFT tin hieu sin 3 chu ky: Dinh song hai chinh = {peak_fund:.2f} dB")
    assert peak_fund > -5.0, "Dinh song hai chinh phai gan 0 dBFS"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AT.1 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_adc_quantization_and_jitter()
