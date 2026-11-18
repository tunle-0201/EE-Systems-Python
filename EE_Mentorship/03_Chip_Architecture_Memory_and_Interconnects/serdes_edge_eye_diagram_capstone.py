"""
================================================================================
          MODULE AB: HIGH-SPEED SERDES & SIGNAL INTEGRITY ARCHITECTURE
        MILESTONE AB.4: SERDES LINK INTEGRITY & EYE DIAGRAM ANALYZER CAPSTONE
================================================================================

KIEN TRUC TOAN CHUOI DONG CO DO KIEM TINH TOAN VEN TIN HIEU (EYE DIAGRAM CAPSTONE):
Capstone nay tich hop tron ven toan bo he thong truyen dan cao toc SerDes:
1. Milestone AB.1: PRBS7Generator -> Sinh chuoi bit gia ngau nhien kiem thu.
2. Milestone AB.2: PCBChannelModel -> Kenh suy hao PCB gay phan tan xung va ISI.
3. Milestone AB.3: DecisionFeedbackEqualizer -> Bo can bang DFE triet tieu ISI.
4. Capstone Engine: EyeDiagramAnalyzer -> Do dac Eye Height, Eye Width, Jitter, BER.

SO DO BIEU DO MAT TRUOC VA SAU KHI EQUALIZE (ASCII DIAGRAM):

   TRUOC CAN BANG (Mat bi dong do ISI):       SAU CAN BANG DFE (Mat mo rong dat chuan):
        Dien ap                                   Dien ap
          +V |   \  /  \  /  \  /                   +V |   +──────────────────+ (Logic 1)
             |    \/    \/    \/                       |    \                /
             |    /\    /\    /\                       |     \   Eye Height /
          0V |───/__\──/__\──/__\───                0V |──────|  (V_margin)  |────────
             |    \/    \/    \/                       |     /                \
             |    /\    /\    /\                       |    /   Eye Width      \
          -V |   /  \  /  \  /  \                   -V |   +──────────────────+ (Logic 0)
             +──────────────────────> t                +──────────────────────> t
                (Zero Voltage Margin)                     (Clean Open Eye Diagram)

CAC CHI SO DO LUONG TINH TOAN VEN TIN HIEU CHUAN PCI-SIG / APPLE (ASCII MATH):

1. Do cao mat (Eye Height V_margin):
   Khoang cach dien ap nho nhat giua tap hop cac muc Logic 1 va Logic 0
   tai tam chu ky lay mau (Sampling Phase t = 0.5 * UI):
   Eye_Height = min(V_level1) - max(V_level0)

   Neu Eye_Height <= 0: Bieu do mat dong kin (Eye Closed), BER > 0!
   Neu Eye_Height > 0 : Bieu do mat mo (Eye Open), tinh hieu an toan!

2. Ty le loi bit (Bit Error Rate - BER):
          error_bits
   BER = ────────────
          total_bits

3. Do giat Jitter dinh-dinh (Peak-to-Peak Jitter J_pp):
   Do bien thien ve thoi gian cua diem cat nguong 0V do ISI gay ra.
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import os
import sys

# Dam bao import duoc ca khi chay tu goc workspace hoac trong thu muc EE_Mentorship
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from serdes_edge_prbs_generator import PRBS7Generator, BitErrorRateTester
from serdes_edge_channel_loss_isi import PCBChannelModel
from serdes_edge_dfe_equalizer import DecisionFeedbackEqualizer


class EyeDiagramAnalyzer:
    """
    Bo phan tich tinh toan ven tin hieu va bieu do mat cho kenh SerDes sieu toc.
    """

    @staticmethod
    def calculate_eye_height(samples: List[float], true_bits: List[int]) -> float:
        """
        Tinh toan do cao mat Eye Height tai diem lay mau trung tam:
        Eye_Height = min(samples tai bit 1) - max(samples tai bit 0).
        Neu ket qua am, tra ve 0.0 (Mat bi dong kin).
        """
        ones_voltages = [s for s, b in zip(samples, true_bits) if b == 1]
        zeros_voltages = [s for s, b in zip(samples, true_bits) if b == 0]

        if not ones_voltages or not zeros_voltages:
            return 0.0

        min_one = min(ones_voltages)
        max_zero = max(zeros_voltages)

        margin = min_one - max_zero
        return max(0.0, margin)

    @staticmethod
    def calculate_snr_db(signal_amplitude: float, noise_std: float) -> float:
        """
        Tinh ty le tin hieu tren nhieu (Signal-to-Noise Ratio) theo don vi Decibel:
        SNR_dB = 20 * log10(signal_amplitude / noise_std)
        """
        if noise_std <= 1e-9:
            return float('inf')
        return 20.0 * math.log10(signal_amplitude / noise_std)


class HighSpeedSerDesLinkEngine:
    """
    Dong co mo phong va kiem tra toan chuoi lien ket SerDes Link Integrity.
    """

    def __init__(self,
                 h0: float = 0.50,
                 h1: float = 0.35,
                 h2: float = 0.20,
                 noise_std: float = 0.015):
        # 1. Mo hinh kenh truyen
        self.channel = PCBChannelModel(h0=h0, h1=h1, h2=h2, noise_std=noise_std)
        # 2. Bo can bang DFE
        self.dfe = DecisionFeedbackEqualizer(w1=h1, w2=h2, target_h0=h0)

    def run_link_validation(self, num_bits: int = 5000) -> Dict[str, Any]:
        """
        Chay quy trinh do kiem toan dien:
        - Phat chuoi ma PRBS-7
        - Truyen qua kenh suy hao PCB
        - Danh gia khi CHUA dung bo can bang
        - Danh gia sau khi KICH HOAT bo can bang DFE
        Tra ve bao cao toan ven tin hieu (Signal Integrity Report).
        """
        # 1. Sinh chuoi bit TX
        prbs = PRBS7Generator(seed=0x7E)
        tx_bits = prbs.generate_sequence(num_bits)

        # 2. Truyen qua kenh PCB
        rx_raw_samples = self.channel.transmit(tx_bits)

        # 3. Danh gia khi chua can bang (Un-equalized)
        raw_decisions = self.channel.slice_decisions(rx_raw_samples)
        raw_errs, _, raw_ber = BitErrorRateTester.calculate_ber(tx_bits, raw_decisions)
        raw_eye_height = EyeDiagramAnalyzer.calculate_eye_height(rx_raw_samples, tx_bits)

        # 4. Danh gia sau khi can bang DFE (Equalized)
        eq_samples, dfe_decisions = self.dfe.equalize(rx_raw_samples)
        dfe_errs, _, dfe_ber = BitErrorRateTester.calculate_ber(tx_bits, dfe_decisions)
        dfe_eye_height = EyeDiagramAnalyzer.calculate_eye_height(eq_samples, tx_bits)

        return {
            "total_bits": num_bits,
            "raw_eye_height": raw_eye_height,
            "raw_bit_errors": raw_errs,
            "raw_ber": raw_ber,
            "dfe_eye_height": dfe_eye_height,
            "dfe_bit_errors": dfe_errs,
            "dfe_ber": dfe_ber,
            "channel_isi_total": self.channel.total_isi,
            "snr_db": EyeDiagramAnalyzer.calculate_snr_db(self.channel.h0, self.channel.noise_std)
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AB CAPSTONE: SERDES LINK INTEGRITY & EYE DIAGRAM")
    print("=========================================================\n")

    # 1. Khoi tao Dong co SerDes Link Engine
    # Kenh co h0 = 0.50V, h1 = 0.35V, h2 = 0.20V (Tong ISI = 0.55V > h0 -> Mat dong)
    serdes_engine = HighSpeedSerDesLinkEngine(h0=0.50, h1=0.35, h2=0.20, noise_std=0.015)

    print("1. THONG SO KENH TRUYEN DUOC KIEM DINH (CHANNEL TELEMETRY):")
    print(f"   -> Main Cursor (h0)          : {serdes_engine.channel.h0:.2f} V")
    print(f"   -> Post-Cursor 1 (h1)        : {serdes_engine.channel.h1:.2f} V")
    print(f"   -> Post-Cursor 2 (h2)        : {serdes_engine.channel.h2:.2f} V")
    print(f"   -> Do lech nhieu Gauss AWGN  : {serdes_engine.channel.noise_std:.4f} V")
    print(f"   -> Ty le SNR kenh ly thuyet  : {EyeDiagramAnalyzer.calculate_snr_db(0.50, 0.015):.2f} dB\n")

    # 2. Chay do kiem toan ven tren 5000 bits du lieu PRBS-7
    test_bits = 5000
    report = serdes_engine.run_link_validation(num_bits=test_bits)

    print("2. KET QUA PHAN TICH DOI SANH TRUOC VA SAU KHI DUNG DFE:")
    print(f"   [TRUOC CAN BANG - UN-EQUALIZED]")
    print(f"   -> Do cao bieu do mat        : {report['raw_eye_height']:.3f} V (Bi dong hoan toan!)")
    print(f"   -> So bit bi loi phat hien   : {report['raw_bit_errors']} / {test_bits} bits")
    print(f"   -> Ty le loi bit (BER)       : {report['raw_ber']:.4f} ({report['raw_ber'] * 100:.2f}%)")

    assert report["raw_eye_height"] == 0.0, "Khi chua can bang, bieu do mat phai bi dong (Eye Height = 0)!"
    assert report["raw_bit_errors"] > 0, "Kenh bi ISI nang phai xuat hien hang loat loi bit!"

    print(f"\n   [SAU KHI KICH HOAT DFE 2-TAP - EQUALIZED]")
    print(f"   -> Do cao bieu do mat mo lai : {report['dfe_eye_height']:.3f} V (Mo rong an toan!)")
    print(f"   -> So bit loi sau DFE        : {report['dfe_bit_errors']} / {test_bits} bits")
    print(f"   -> Ty le loi bit sau DFE     : {report['dfe_ber']:.6f} ({report['dfe_ber'] * 100:.4f}%)")

    assert report["dfe_eye_height"] > 0.8, "Sau DFE, do cao mat phai duoc mo rong tren 0.8V!"
    assert report["dfe_bit_errors"] == 0, "Sau DFE, ty le loi bit phai bang 0 tuyet doi!"

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE AB: HIGH-SPEED SERDES & EYE DIAGRAM ANALYZER!")
    print("=========================================================")
