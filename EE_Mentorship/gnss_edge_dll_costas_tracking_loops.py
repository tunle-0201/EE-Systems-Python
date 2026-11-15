"""
EE MENTORSHIP PROGRAM - MODULE BK (NHOM 50) - BAI 197 (MILESTONE BK.2)
================================================================================
VONG BAM MA TRE EML-DLL, VONG KHOA PHA COSTAS BAC 3 & GIAI MA BAN TIN 50 BPS
CHO TEN LUA SPACEX FALCON 9 / STARSHIP & XE TU HANH TESLA AUTOPILOT
================================================================================

Nguyen ly vat ly va Toan hoc cot loi:
1. Bo tach pha Ma tre Som-Muon (Normalized Early-Minus-Late Envelope DLL):
   - Ba nhanh tuong quan song song: Early (-delta chip), Prompt (0), Late (+delta chip).
   - Khi thuat toan su dung ham tuong quan tam giac R(e) = max(0, 1 - |e|):

               L_env - E_env
     e_chips = ───────────── * (1 - delta)   (voi |e| <= delta = 0.25 chip)
               L_env + E_env

   - Ket hop Tro luc Song mang (Carrier-Aided DLL): Vi f_L1 = 1540 * f_chip,
     van toc dich Doppler f_d tu PLL duoc chia 1540 cong thang vao Code NCO,
     loai bo 100% sai so dong luc hoc khi ten lua gia toc 4g - 6g!

2. Bo tach pha Song mang Costas 2-Goc phan tu (Costas ATAN Discriminator):
   - Du lieu ban tin dinh vi 50 bps dao dau pha (+/-1 = 180 deg) moi 20 ms.
   - Ham atan(Q_P / I_P) (khong phai atan2!) mien nhiem tuyet doi voi su dao bit
     180 deg, giup Costas PLL khoa chat pha ngay ca khi dang thu du lieu.

3. Vong khoa pha Bac 3 (3rd-Order Costas PLL) chiu gia toc ten lua:
   - Vong bac 2 bi tre pha tinh khi gia toc khac 0 (theta_ss = a / omega_n^2).
   - Vong bac 3 (3 bo tich luy Kaplan-Hegarty: B_n = 18 Hz) bam duoc ca van toc
     va gia toc ma KHONG bi sai so pha tinh, dong thoi giai ma duoc ban tin 50 bps.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Quan he tan so Song mang L1 va Tan so Ma C/A:
     f_L1 = 1575.42 MHz = 1540 * 1.023 MHz -> Code_Rate = 1.023e6 + f_d / 1540

2. Bo loc Vong Bac 3 (3rd-Order Loop Filter):
     omega_0 = B_n / 0.7845
     acc2 += omega_0^3 * phi_err * T_coh
     acc1 += (1.1 * omega_0^2 * phi_err + acc2) * T_coh
     freq_corr_rad = 2.4 * omega_0 * phi_err + acc1
--------------------------------------------------------------------------------
"""

import cmath
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict


L1_CARRIER_HZ = 1575.42e6
CA_CHIP_RATE_HZ = 1.023e6
L1_TO_CA_RATIO = 1540.0
SPEED_OF_LIGHT = 299792458.0
CHIP_METERS = SPEED_OF_LIGHT / CA_CHIP_RATE_HZ


def code_autocorr_triangle(offset_chips: float) -> float:
    """Ham tuong quan tam giac ly tuong cua ma PRN sau nen nhieu: R(tau) = max(0, 1 - |tau|)."""
    return max(0.0, 1.0 - abs(offset_chips))


class DualDLLCostasTrackingChannel:
    """
    Kenh bam ve tinh tich hop Early-Minus-Late DLL + Costas PLL (Bac 2 hoac Bac 3) +
    Carrier Aiding, chay o chu ky tich luy 1 ms (1,000 Hz).
    """

    def __init__(
        self,
        init_code_phase_chips: float,
        init_doppler_hz: float,
        pll_order: int = 3,
        pll_bw_hz: float = 18.0,
        dll_bw_hz: float = 1.0,
        dll_delta_chips: float = 0.25,
        carrier_aiding: bool = True,
    ):
        self.pll_order = pll_order
        self.delta = dll_delta_chips
        self.carrier_aiding = carrier_aiding

        # Trang thai NCO thu
        self.nco_code_phase = init_code_phase_chips
        self.nco_carrier_phase_rad = 0.0
        self.doppler_hz = init_doppler_hz
        self.nom_doppler_rad = 2.0 * math.pi * init_doppler_hz

        # He so bo loc PLL Kaplan-Hegarty
        self.pll_w0 = pll_bw_hz / 0.7845 if pll_order == 3 else pll_bw_hz / 0.53
        self.pll_acc1 = 0.0
        self.pll_acc2 = 0.0

        # He so bo loc DLL bac 2 (zeta = 0.707)
        self.dll_wn = dll_bw_hz / 0.53
        self.dll_acc = 0.0

    def step_1ms(
        self,
        true_code_delay_chips: float,
        true_carrier_phase_rad: float,
        true_doppler_hz: float,
        nav_bit: int,
        amp: float = 1.0,
        noise_std: float = 0.05,
        rng: random.Random = None,
    ) -> Dict[str, float]:
        """Thuc thi 1 chu ky tich luy 1 ms (Integrate & Dump E, P, L)."""
        t_coh = 1.0e-3
        # Sai so pha & ma trung binh trong 1 ms tich luy
        code_err = true_code_delay_chips - self.nco_code_phase
        # Sai so pha giua song mang thuc & NCO
        phi_err_true = (true_carrier_phase_rad - self.nco_carrier_phase_rad) % (2.0 * math.pi)
        if phi_err_true > math.pi:
            phi_err_true -= 2.0 * math.pi

        # 3 nhanh tuong quan som / dung / muon
        r_p = code_autocorr_triangle(code_err)
        r_e = code_autocorr_triangle(code_err + self.delta)
        r_l = code_autocorr_triangle(code_err - self.delta)

        # Tin hieu phuc sau giai dieu che (Prompt mang du lieu nav_bit = +/-1)
        data_sign = 1.0 if nav_bit == 1 else -1.0
        sinc_loss = 1.0  # Tich luy 1 ms dung tan
        n_p = complex(rng.gauss(0, noise_std), rng.gauss(0, noise_std)) if rng else 0j
        n_e = complex(rng.gauss(0, noise_std), rng.gauss(0, noise_std)) if rng else 0j
        n_l = complex(rng.gauss(0, noise_std), rng.gauss(0, noise_std)) if rng else 0j

        p_iq = amp * data_sign * sinc_loss * r_p * cmath.rect(1.0, phi_err_true) + n_p
        e_iq = amp * data_sign * sinc_loss * r_e * cmath.rect(1.0, phi_err_true) + n_e
        l_iq = amp * data_sign * sinc_loss * r_l * cmath.rect(1.0, phi_err_true) + n_l

        # 1. Bo tach pha Costas ATAN (Mien nhiem 180 deg nav bit flip!)
        disc_pll_rad = math.atan(p_iq.imag / p_iq.real) if abs(p_iq.real) > 1e-9 else math.copysign(math.pi / 2.0, p_iq.imag)

        # Cap nhat bo loc PLL
        w0 = self.pll_w0
        if self.pll_order == 3:
            self.pll_acc2 += (w0 ** 3) * disc_pll_rad * t_coh
            self.pll_acc1 += (1.1 * (w0 ** 2) * disc_pll_rad + self.pll_acc2) * t_coh
            freq_ctrl_rad = 2.4 * w0 * disc_pll_rad + self.pll_acc1
        else:
            self.pll_acc1 += (w0 ** 2) * disc_pll_rad * t_coh
            freq_ctrl_rad = 1.414 * w0 * disc_pll_rad + self.pll_acc1

        total_doppler_rad = self.nom_doppler_rad + freq_ctrl_rad
        self.doppler_hz = total_doppler_rad / (2.0 * math.pi)
        self.nco_carrier_phase_rad += total_doppler_rad * t_coh

        # 2. Bo tach pha Ma tre Normalized EML Envelope DLL
        e_env = abs(e_iq)
        l_env = abs(l_iq)
        disc_dll_chips = ((l_env - e_env) / max(1e-9, l_env + e_env)) * (1.0 - self.delta)

        wn = self.dll_wn
        self.dll_acc += (wn ** 2) * disc_dll_chips * t_coh
        code_rate_corr_chips_s = 1.414 * wn * disc_dll_chips + self.dll_acc
        aiding_chips_s = (self.doppler_hz / L1_TO_CA_RATIO) if self.carrier_aiding else 0.0

        # Cap nhat pha ma NCO cho chu ky 1 ms tiep theo
        self.nco_code_phase += (CA_CHIP_RATE_HZ + aiding_chips_s + code_rate_corr_chips_s) * t_coh

        # Ghi nhan sai so pha thuc mod pi (do Costas co da tri 180 deg sau giai bit)
        phase_err_deg = math.degrees(disc_pll_rad)
        return {
            "i_p": p_iq.real,
            "q_p": p_iq.imag,
            "code_err_chips": code_err,
            "code_err_m": code_err * CHIP_METERS,
            "phase_err_deg": phase_err_deg,
            "doppler_err_hz": true_doppler_hz - self.doppler_hz,
        }


class GPSNavMessageCodec:
    """Bo ma hoa/giai ma ban tin dinh vi GPS 50 bps (20 ms/bit) & Kiem tra Parity 30-bit Word."""

    TLM_PREAMBLE = [1, 0, 0, 0, 1, 0, 1, 1]  # 0x8B chuan ICD-GPS-200

    # 6 ma mat na parity 24-bit ICD-GPS-200 cho cac bit D25..D30 (LSB-aligned trong word 24-bit)
    PARITY_MASKS = [
        0b111011000111110011010010,  # D25
        0b011101100011111001101001,  # D26
        0b101110110001111100110100,  # D27
        0b010111011000111110011010,  # D28
        0b101011101100011111001101,  # D29
        0b001011011110101000100111,  # D30
    ]

    @classmethod
    def encode_word_30bit(cls, data_24bits: int, d29_prev: int, d30_prev: int) -> List[int]:
        """Ma hoa 24 bit du lieu thanh 30 bit Word kem 6 bit Parity chuan ICD-GPS-200."""
        d_raw = [(data_24bits >> (23 - i)) & 1 for i in range(24)]
        # Neu D30* cua tu truoc la 1, dao 24 bit du lieu truyen
        d_tx = [b ^ d30_prev for b in d_raw]

        def popcount_xor(val: int, mask: int) -> int:
            return bin(val & mask).count("1") & 1

        d25 = d29_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[0])
        d26 = d30_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[1])
        d27 = d29_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[2])
        d28 = d30_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[3])
        d29 = d30_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[4])
        d30 = d29_prev ^ popcount_xor(data_24bits, cls.PARITY_MASKS[5])
        return d_tx + [d25, d26, d27, d28, d29, d30]

    @classmethod
    def verify_and_decode_word(cls, word_30: List[int], d29_prev: int, d30_prev: int) -> Tuple[bool, int]:
        """Kiem tra Parity 30-bit Word va giai ma lai 24-bit nguyen ban."""
        d_tx = word_30[:24]
        d_raw = [b ^ d30_prev for b in d_tx]
        data_24 = 0
        for b in d_raw:
            data_24 = (data_24 << 1) | b
        re_encoded = cls.encode_word_30bit(data_24, d29_prev, d30_prev)
        return (re_encoded == word_30), data_24


def simulate_rocket_tracking(pll_order: int, carrier_aiding: bool, nav_bits: List[int]) -> Dict[str, any]:
    """
    Mo phong quy dao ten lua SpaceX Falcon 9 tang toc 4.5g (jerk -> gia toc 44.1 m/s^2)
    trong 2.4 giay (2,400 chu ky 1 ms) gom 120 bit ban tin dinh vi 50 bps.
    """
    rng = random.Random(42)
    n_ms = len(nav_bits) * 20
    t_coh = 1.0e-3

    # Dong hoc ten lua: v(t) tang tuyen tinh sau 0.2s o gia toc 4.5g = 44.1 m/s^2
    accel_ms2 = 44.145
    doppler0_hz = 2500.0
    code_phase_true = 300.0
    carrier_phase_true = 0.25  # Sai so pha ban dau tu Acquisition

    # Sai so khoi tao tu tang FFT Acquisition: lech 0.12 chip, lech 15 Hz Doppler
    ch = DualDLLCostasTrackingChannel(
        init_code_phase_chips=300.0 - 0.12,
        init_doppler_hz=2500.0 - 15.0,
        pll_order=pll_order,
        pll_bw_hz=20.0,
        dll_bw_hz=2.5,
        carrier_aiding=carrier_aiding,
    )

    code_errs_m: List[float] = []
    phase_errs_deg: List[float] = []
    ip_bits: List[int] = []
    ip_sum_20ms = 0.0

    for ms in range(n_ms):
        t = ms * t_coh
        cur_accel = accel_ms2 if t >= 0.20 else 0.0
        vel_rel = cur_accel * max(0.0, t - 0.20)
        doppler_true = doppler0_hz + (vel_rel / SPEED_OF_LIGHT) * L1_CARRIER_HZ
        code_rate_true = CA_CHIP_RATE_HZ + doppler_true / L1_TO_CA_RATIO

        bit_idx = ms // 20
        cur_bit = nav_bits[bit_idx]

        res = ch.step_1ms(
            true_code_delay_chips=code_phase_true,
            true_carrier_phase_rad=carrier_phase_true,
            true_doppler_hz=doppler_true,
            nav_bit=cur_bit,
            amp=1.0,
            noise_std=0.025,
            rng=rng,
        )

        # Tich luy 20 ms -> giai ma 1 bit 50 bps
        ip_sum_20ms += res["i_p"]
        if (ms + 1) % 20 == 0:
            ip_bits.append(1 if ip_sum_20ms >= 0.0 else 0)
            ip_sum_20ms = 0.0

        if ms >= 1400:  # Danh gia o vung xac lap giua pha tang toc 4.5g
            code_errs_m.append(res["code_err_m"])
            phase_errs_deg.append(res["phase_err_deg"])

        # Cap nhat vi tri & pha thuc cho chu ky 1 ms tiep theo
        code_phase_true += code_rate_true * t_coh
        carrier_phase_true += 2.0 * math.pi * doppler_true * t_coh

    rms_code_m = math.sqrt(sum(e * e for e in code_errs_m) / len(code_errs_m))
    mean_phase_deg = sum(phase_errs_deg) / len(phase_errs_deg)
    rms_phase_deg = math.sqrt(sum(e * e for e in phase_errs_deg) / len(phase_errs_deg))

    # Do Costas PLL co da tri pha 180 deg, kiem tra ca chuoi bit goc lan chuoi dao bit
    matches_norm = sum(1 for a, b in zip(nav_bits[20:], ip_bits[20:]) if a == b)
    matches_inv = sum(1 for a, b in zip(nav_bits[20:], ip_bits[20:]) if a == (1 - b))
    best_match = max(matches_norm, matches_inv)
    ber = 1.0 - (best_match / len(nav_bits[20:]))
    inverted_polarity = matches_inv > matches_norm

    decoded_bits = [(1 - b) if inverted_polarity else b for b in ip_bits]
    return {
        "rms_code_m": rms_code_m,
        "mean_phase_deg": mean_phase_deg,
        "rms_phase_deg": rms_phase_deg,
        "ber": ber,
        "decoded_bits": decoded_bits,
    }


def test_dll_costas_tracking_loops():
    """Chuong trinh kiem thu DLL + Costas PLL Bac 3 + Giai ma ban tin GPS 50 bps."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BK (NHOM 50) - BAI 197 (MILESTONE BK.2)")
    print("VONG BAM MA TRE EML-DLL, COSTAS PLL BAC 3 & BAN TIN 50 BPS SPACEX")
    print("=" * 80)

    # Tao 4 GPS 30-bit Words = 120 bit (Word 1 bat dau bang TLM Preamble 0x8B!)
    tlm_data_24 = (0b10001011 << 16) | 0x3A95
    w1 = GPSNavMessageCodec.encode_word_30bit(tlm_data_24, 0, 0)
    w2 = GPSNavMessageCodec.encode_word_30bit(0xA5C3F1, w1[28], w1[29])
    w3 = GPSNavMessageCodec.encode_word_30bit(0x123456, w2[28], w2[29])
    w4 = GPSNavMessageCodec.encode_word_30bit(0xDEADBE, w3[28], w3[29])
    nav_stream = w1 + w2 + w3 + w4

    # 1. So sanh 2nd-Order PLL vs 3rd-Order PLL duoi gia toc ten lua SpaceX 4.5g (44.1 m/s^2)
    print("\n[1] So sanh Costas PLL Bac 2 vs Bac 3 duoi gia toc SpaceX Falcon 9 (4.5g):")
    res_o2 = simulate_rocket_tracking(pll_order=2, carrier_aiding=False, nav_bits=nav_stream)
    res_o3 = simulate_rocket_tracking(pll_order=3, carrier_aiding=True, nav_bits=nav_stream)

    print(
        f"  * PLL Bac 2 (Khong tro luc ma) : Mean Phase Lag = {res_o2['mean_phase_deg']:+6.2f} deg | "
        f"RMS Code = {res_o2['rms_code_m']:5.2f} m"
    )
    print(
        f"  * PLL Bac 3 (Co Carrier-Aiding): Mean Phase Lag = {res_o3['mean_phase_deg']:+6.2f} deg | "
        f"RMS Phase = {res_o3['rms_phase_deg']:4.2f} deg | RMS Code = {res_o3['rms_code_m']:5.2f} m"
    )

    assert abs(res_o2["mean_phase_deg"]) > 15.0  # PLL bac 2 bi keo tre pha nang
    assert abs(res_o3["mean_phase_deg"]) < 1.0 and res_o3["rms_phase_deg"] < 3.0
    assert res_o3["rms_code_m"] < 2.0
    print("  -> Ket luan: PLL Bac 3 + Carrier Aiding triet tieu sai so pha tinh duoi 4.5g (PASS)!")

    # 2. Giai ma ban tin 50 bps & Kiem tra Parity 30-bit Word chuan ICD-GPS-200
    print("\n[2] Kiem thu giai ma ban tin 50 bps & Parity ICD-GPS-200 sau chu ky khoa pha:")
    rx_bits = res_o3["decoded_bits"]
    preamble_ok = (rx_bits[0:8] == GPSNavMessageCodec.TLM_PREAMBLE)
    # Kiem tra Parity Word 2, Word 3, Word 4 (sau khi vong khoa da hoi tu on dinh)
    p2_ok, d2 = GPSNavMessageCodec.verify_and_decode_word(rx_bits[30:60], rx_bits[28], rx_bits[29])
    p3_ok, d3 = GPSNavMessageCodec.verify_and_decode_word(rx_bits[60:90], rx_bits[58], rx_bits[59])
    p4_ok, d4 = GPSNavMessageCodec.verify_and_decode_word(rx_bits[90:120], rx_bits[88], rx_bits[89])

    print(f"  * TLM Preamble 0x8B Match : {preamble_ok}")
    print(f"  * Ty le loi bit BER       : {res_o3['ber']*100.0:.2f}% (Target: 0.00%)")
    print(f"  * Parity Check Word 2..4  : W2={p2_ok} (0x{d2:06X}), W3={p3_ok} (0x{d3:06X}), W4={p4_ok} (0x{d4:06X})")

    assert preamble_ok and res_o3["ber"] == 0.0
    assert p2_ok and d2 == 0xA5C3F1
    assert p3_ok and d3 == 0x123456
    assert p4_ok and d4 == 0xDEADBE
    print("  -> Ket luan: Costas PLL giai ma sach 100% du lieu dinh vi & pass Parity (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 197: EML-DLL & COSTAS PLL BAC 3 HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_dll_costas_tracking_loops()
