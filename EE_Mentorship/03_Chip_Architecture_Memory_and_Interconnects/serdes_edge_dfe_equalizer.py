"""
================================================================================
          MODULE AB: HIGH-SPEED SERDES & SIGNAL INTEGRITY ARCHITECTURE
          MILESTONE AB.3: RX EQUALIZATION: CTLE FILTER & 2-TAP DFE EQUALIZER
================================================================================

TAI SAO BO CAN BANG DFE (DECISION FEEDBACK EQUALIZER) LA TRAI TIM CUA SERDES?
- O Milestone AB.2, chung ta chung minh rang duong truyen PCB bi ton hao khien
  tong ISI (|h1| + |h2|) vuot qua Main Cursor (h0), lam bieu do mat bi dong kin
  va gay loi bit nghiem trong.
- Tai sao khong chi dung bo loc tuyen tinh (CTLE - Continuous-Time Linear Equalizer)?
  CTLE la bo loc nang tan so cao (High-Frequency Peaking). Neu kenh suy hao qua nang
  (-25 dB tai tan so Nyquist), CTLE se khuech dai ca nhieu nhiet trang len 25 dB
  (Hien tuong Noise Enhancement), lam hong ty le tin hieu tren nhieu (SNR).
- Giai phap dot pha: Bo can bang hoi tiep quyet dinh DFE (Decision Feedback Equalizer):
  1. DFE khong bao gio khuech dai nhieu!
  2. DFE lay gia tri bit da duoc luong tu hoa sach se (Slicer Decision: d_hat in {-1, +1}),
     nhan voi he so trong so tap (w1, w2) va TRU truc tiep vao tin hieu tuong tu den.
  3. Triet tieu 100% nang luong nhiễu tran Post-Cursor ISI!

SO DO KHOI BO CAN BANG RX: CTLE + DFE 2-TAP (ASCII DIAGRAM):

   Tin hieu den r[k]
   ──────────────────> [ CTLE Filter ] ──(+)───> [ Slicer ] ───> Bit quyet dinh d_hat[k]
                                          ^          |
                                         (-)         +──────+
                                          |                 |
                                          |           [ Z^-1 ] (Tre 1 bit)
                                          |                 |
                                          +─── [ w1 ] <─────+ (d_hat[k-1])
                                          |                 |
                                          |           [ Z^-1 ] (Tre 2 bit)
                                          |                 |
                                          +─── [ w2 ] <─────+ (d_hat[k-2])

TOAN HOC TRIET TIEU POST-CURSOR ISI CUA DFE (ASCII MATH BLOCKS):

1. Phuong trinh can bang DFE:
   y_eq[k] = r_ctle[k] - (w_1 * d_hat[k-1] + w_2 * d_hat[k-2])

2. Quyet dinh bit cua bo so sanh Slicer:
   d_hat[k] = +1   neu y_eq[k] >= 0
   d_hat[k] = -1   neu y_eq[k] <  0

3. Hieu qua triet tieu tuyet doi khi w1 = h1 va w2 = h2:
   Neu r[k] = h_0 * x[k] + h_1 * x[k-1] + h_2 * x[k-2]
   Thi:
   y_eq[k] = (h_0 * x[k] + h_1 * x[k-1] + h_2 * x[k-2]) - (h_1 * x[k-1] + h_2 * x[k-2])
           = h_0 * x[k]
   -> ISI BI TRIET TIEU HOAN TOAN!
   -> Bien do tin hieu duoc khoi phuc tro lai dung h_0, bieu do mat mo rong hoan hao!

4. Thuat toan thich nghi trong so LMS (Least Mean Squares):
   error[k] = y_eq[k] - (h_0 * d_hat[k])
   w_1[k+1] = w_1[k] + mu * error[k] * d_hat[k-1]
   w_2[k+1] = w_2[k] + mu * error[k] * d_hat[k-2]
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import random


class CTLEFilter:
    """
    Bo loc can bang tuyen tinh thoi gian lien tuc CTLE (Discrete Approximation).
    Bo loc peaking bac nhat tang cuong bien do tan so cao bi suy hao:
    y_ctle[k] = y[k] - alpha * y[k-1]
    """

    def __init__(self, alpha: float = 0.25):
        self.alpha = float(alpha)
        self.prev_sample = 0.0

    def process(self, samples: List[float]) -> List[float]:
        output = []
        prev = 0.0
        for s in samples:
            # Bo loc nang tan so cao (Peaking)
            filtered = s - self.alpha * prev
            output.append(filtered)
            prev = s
        return output


class DecisionFeedbackEqualizer:
    """
    Bo can bang hoi tiep quyet dinh DFE 2-Tap (2-Tap DFE).
    - w1: Trong so triet tieu post-cursor 1
    - w2: Trong so triet tieu post-cursor 2
    - target_h0: Bien do muc tieu cua Main-cursor
    """

    def __init__(self, w1: float = 0.35, w2: float = 0.20, target_h0: float = 0.50):
        self.w1 = float(w1)
        self.w2 = float(w2)
        self.target_h0 = float(target_h0)

    def equalize(self, rx_samples: List[float]) -> Tuple[List[float], List[int]]:
        """
        Thuc thi thuat toan DFE tren chuoi mau tin hieu nhan duoc:
        Tra ve (equalized_samples, recovered_bits).
        """
        eq_samples = []
        recovered_bits = []

        d_prev1 = 0.0
        d_prev2 = 0.0

        for r in rx_samples:
            # 1. Tru truc tiep uoc luong ISI tu cac bit truoc
            isi_estimate = (self.w1 * d_prev1) + (self.w2 * d_prev2)
            y_eq = r - isi_estimate
            eq_samples.append(y_eq)

            # 2. Slicer ra quyet dinh bit
            bit_decision = 1 if y_eq >= 0.0 else 0
            recovered_bits.append(bit_decision)

            # 3. Chuyen doi sang NRZ bipolar {-1.0, +1.0} cho vong hoi tiep
            d_hat = 1.0 if bit_decision == 1 else -1.0
            d_prev2 = d_prev1
            d_prev1 = d_hat

        return eq_samples, recovered_bits

    def adapt_lms(self, rx_samples: List[float], mu: float = 0.01) -> Tuple[List[float], List[int]]:
        """
        Thuat toan DFE tu dong thich nghi trong so w1, w2 bang giai thuat LMS.
        """
        eq_samples = []
        recovered_bits = []

        d_prev1 = 0.0
        d_prev2 = 0.0

        for r in rx_samples:
            isi_estimate = (self.w1 * d_prev1) + (self.w2 * d_prev2)
            y_eq = r - isi_estimate
            eq_samples.append(y_eq)

            bit_decision = 1 if y_eq >= 0.0 else 0
            recovered_bits.append(bit_decision)

            d_hat = 1.0 if bit_decision == 1 else -1.0

            # Tinh sai so du bao so voi muc tieu target_h0 * d_hat
            error = y_eq - (self.target_h0 * d_hat)

            # Cap nhat trong so theo gradient descent
            self.w1 += mu * error * d_prev1
            self.w2 += mu * error * d_prev2

            d_prev2 = d_prev1
            d_prev1 = d_hat

        return eq_samples, recovered_bits


if __name__ == "__main__":
    print("=========================================================")
    print("   SERDES HARDWARE: RX EQUALIZATION CTLE & 2-TAP DFE")
    print("=========================================================\n")

    # 1. Tai lap kenh bi dong mat tu Milestone AB.2
    # h0 = 0.50V, h1 = 0.35V, h2 = 0.20V
    # Mau bit xau nhat: [0, 0, 1] khien tin hieu am xuong -0.05V
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from serdes_edge_channel_loss_isi import PCBChannelModel
    from serdes_edge_prbs_generator import PRBS7Generator, BitErrorRateTester

    channel = PCBChannelModel(h0=0.50, h1=0.35, h2=0.20, noise_std=0.01)

    # 2. Phat 1000 bit PRBS-7 qua kenh bi suy hao
    prbs = PRBS7Generator(seed=0x3F)
    tx_bits = prbs.generate_sequence(1000)
    rx_raw = channel.transmit(tx_bits)

    # Do ty le loi bit khi KHONG CO EQUALIZATION (Un-equalized)
    raw_bits = channel.slice_decisions(rx_raw)
    raw_errs, _, raw_ber = BitErrorRateTester.calculate_ber(tx_bits, raw_bits)

    print("1. KET QUA KHI KHONG DUNG BO CAN BANG (NO EQUALIZATION):")
    print(f"   -> So bit loi ghi nhan       : {raw_errs} / 1000 bits")
    print(f"   -> Ty le loi bit (BER)       : {raw_ber:.4f} ({raw_ber * 100:.2f}%)")
    assert raw_errs > 0, "Kenh bi dong mat bat buoc phai co loi bit neu khong can bang!"
    print("   -> Trang thai                : MAT TIN HIEU / LOI NANG (Kenh dong kin)\n")

    # 3. Kich hoat bo can bang DFE 2-Tap (w1 = 0.35, w2 = 0.20)
    dfe = DecisionFeedbackEqualizer(w1=0.35, w2=0.20, target_h0=0.50)
    eq_samples, dfe_bits = dfe.equalize(rx_raw)
    dfe_errs, _, dfe_ber = BitErrorRateTester.calculate_ber(tx_bits, dfe_bits)

    print("2. KET QUA KHI KICH HOAT BO CAN BANG DFE 2-TAP (EQUALIZED):")
    print(f"   -> Trong so tap w1           : {dfe.w1:.2f} V (Triet tieu h1 = 0.35V)")
    print(f"   -> Trong so tap w2           : {dfe.w2:.2f} V (Triet tieu h2 = 0.20V)")
    print(f"   -> So bit loi sau DFE        : {dfe_errs} / 1000 bits")
    print(f"   -> Ty le loi bit sau DFE     : {dfe_ber:.6f} ({dfe_ber * 100:.4f}%)")

    assert dfe_errs == 0, "Bo can bang DFE phai triet tieu 100% loi bit do ISI gay ra!"
    print("   -> Ket luan                   : HOAN HAO (DFE da mo lai bieu do mat va diet sach loi bit!)\n")

    # 4. Kiem tra thuat toan thich nghi LMS (Tap Adaptive Tuning)
    # Khoi tao DFE voi trong so ban dau bang 0.0 (chua biet kenh), de LMS tu hoc
    dfe_adaptive = DecisionFeedbackEqualizer(w1=0.0, w2=0.0, target_h0=0.50)
    _, adapt_bits = dfe_adaptive.adapt_lms(rx_raw, mu=0.02)
    print("3. KET QUA BO CAN BANG DFE TU DONG HOC LMS (ADAPTIVE LMS):")
    print(f"   -> Trong so w1 hoc duoc      : {dfe_adaptive.w1:.3f} V (Hoi tu ve 0.35V)")
    print(f"   -> Trong so w2 hoc duoc      : {dfe_adaptive.w2:.3f} V (Hoi tu ve 0.20V)")
    assert abs(dfe_adaptive.w1 - 0.35) < 0.1, "LMS phai hoi tu trong so w1 gan bang 0.35V!"
    assert abs(dfe_adaptive.w2 - 0.20) < 0.1, "LMS phai hoi tu trong so w2 gan bang 0.20V!"

    print("\n[THANH CONG] DA HOAN THANH BO CAN BANG DFE MO LAI BIEU DO MAT CHO CHIP APPLE/TESLA!")
