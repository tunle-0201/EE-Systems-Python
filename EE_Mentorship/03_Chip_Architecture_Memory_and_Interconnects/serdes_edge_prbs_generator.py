"""
================================================================================
          MODULE AB: HIGH-SPEED SERDES & SIGNAL INTEGRITY ARCHITECTURE
          MILESTONE AB.1: PRBS-7 / PRBS-15 LFSR GENERATOR & BER TESTER
================================================================================

TAI SAO CAC KY SU PHAN CUNG APPLE VA TESLA DUNG CHUOI MA PRBS DE DO KIEM?
- Trong cac kenh truyen sieu toc SerDes (PCIe Gen 5/6, USB4, MIPI CSI-2 camera,
  Tesla FSD HW4 high-speed interconnects):
  Khong the truyen chuoi bit don dieu (nhu 101010...) vi se khong kich thich duoc
  tat ca cac che do suy hao phan tan va cong huong tan so cua duong mach PCB.
- Chuoi bit gia ngau nhien PRBS (Pseudo-Random Binary Sequence):
  1. Mang day du dac tinh thong ke cua du lieu ngau nhien thuc te.
  2. Co do rong pho tan so lien tuc (white-noise-like spectrum).
  3. Chua day du cac chuoi bit dai lien tiep (long runs of 1s or 0s) de thu thach
     hien tuong sut ap duong nguon va trôi nguong DC.

SO DO THANH GHI DICH PHAN HOI TUYEN TINH LFSR FIBONACCI (ASCII DIAGRAM):

               +-------------------------------------------+
               |                                           |
               v                                           |
            [ XOR ] <── (Bit moi)                          |
             ^   ^                                         |
             |   +──────────────+                          |
             |                  |                          |
          [ B0 ] ──> [ B1 ] ──> [ B2 ] ──> ... ──> [ B6 ] ─+──> PRBS-7 Output
         (Tap 7)                                  (Tap 6)

TOAN HOC DA THUC DAC TRUNG PRBS (ASCII MATH BLOCKS):

1. Da thuc chuan ITU-T O.150 cho PRBS-7:
   P(X) = X^7 + X^6 + 1
   -> bit_moi = bit[6] XOR bit[5] (theo chi so 0-indexed)
   -> Chu ky tuan hoan cuc dai: Period = 2^7 - 1 = 127 bits.

2. Da thuc chuan cho PRBS-15:
   P(X) = X^15 + X^14 + 1
   -> bit_moi = bit[14] XOR bit[13]
   -> Chu ky tuan hoan cuc dai: Period = 2^15 - 1 = 32,767 bits.

3. Ty le loi bit (Bit Error Rate - BER):
          error_bits
   BER = ────────────
          total_bits

4. Tinh huong bien (Edge Cases):
   - Trang thai all-zeros (0b0000000): Cam tuyet doi! Neu tat ca cac bit deu bang 0,
     phep XOR 0^0 luon ra 0 -> Thanh ghi bi treo vinh vien o muc 0.
   - Khoi tao seed phai khac 0 (Default Seed = 0x7F hoac 0x01).
"""

from typing import Tuple, List, Dict, Any, Optional
import random


class PRBS7Generator:
    """
    Bo phat chuoi bit gia ngau nhien PRBS-7 theo chuan ITU-T O.150.
    Da thuc: X^7 + X^6 + 1 (Chu ky 127 bits).
    """

    def __init__(self, seed: int = 0x7F):
        # Khoi tao thanh ghi 7-bit, dam bao khong phai all-zeros
        if seed & 0x7F == 0:
            seed = 0x7F
        self.state = seed & 0x7F
        self.initial_seed = self.state

    def step(self) -> int:
        """
        Dich thanh ghi 1 chu ky nhip (1 bit) va tra ve bit dau ra (0 hoac 1).
        XOR giua bit 6 va bit 5 (tap 7 va tap 6).
        """
        b6 = (self.state >> 6) & 1
        b5 = (self.state >> 5) & 1
        new_bit = b6 ^ b5

        # Day new_bit vao LSB, day LSB hien tai ve MSB
        output_bit = b6
        self.state = ((self.state << 1) & 0x7F) | new_bit
        return output_bit

    def generate_sequence(self, num_bits: int) -> List[int]:
        """
        Sinh ra mot chuoi num_bits gia tri nhi phan [0, 1].
        """
        return [self.step() for _ in range(num_bits)]

    def reset(self) -> None:
        """
        Dat lai trang thai ban dau.
        """
        self.state = self.initial_seed


class PRBS15Generator:
    """
    Bo phat chuoi bit gia ngau nhien PRBS-15.
    Da thuc: X^15 + X^14 + 1 (Chu ky 32,767 bits).
    """

    def __init__(self, seed: int = 0x7FFF):
        if seed & 0x7FFF == 0:
            seed = 0x7FFF
        self.state = seed & 0x7FFF
        self.initial_seed = self.state

    def step(self) -> int:
        b14 = (self.state >> 14) & 1
        b13 = (self.state >> 13) & 1
        new_bit = b14 ^ b13

        output_bit = b14
        self.state = ((self.state << 1) & 0x7FFF) | new_bit
        return output_bit

    def generate_sequence(self, num_bits: int) -> List[int]:
        return [self.step() for _ in range(num_bits)]

    def reset(self) -> None:
        self.state = self.initial_seed


class BitErrorRateTester:
    """
    Bo kiem tra ty le loi bit (BERT - Bit Error Rate Tester).
    So sanh chuoi bit thu duoc tu may thu RX voi chuoi bit mau phat tu TX.
    """

    @staticmethod
    def calculate_ber(tx_bits: List[int], rx_bits: List[int]) -> Tuple[int, int, float]:
        """
        So khop hai chuoi bit:
        Tra ve (error_bits, total_bits, BER)
        """
        if len(tx_bits) != len(rx_bits):
            raise ValueError("Do dai chuoi TX va RX phai bang nhau!")

        total_bits = len(tx_bits)
        if total_bits == 0:
            return 0, 0, 0.0

        error_bits = 0
        for tx, rx in zip(tx_bits, rx_bits):
            if tx != rx:
                error_bits += 1

        ber = float(error_bits) / float(total_bits)
        return error_bits, total_bits, ber


if __name__ == "__main__":
    print("=========================================================")
    print("   SERDES HARDWARE: PRBS-7 / PRBS-15 & BER TESTER")
    print("=========================================================\n")

    # 1. Kiem tra chu ky tuan hoan cua PRBS-7 (Dung 127 bits khong lap lai)
    prbs7 = PRBS7Generator(seed=0x5A)
    first_seq = prbs7.generate_sequence(127)
    second_seq = prbs7.generate_sequence(127)

    print("1. KIEM TRA CHU KY TUAN HOAN PRBS-7 (CYCLE LENGTH TEST):")
    print(f"   -> 16 bit dau tien cua chuoi 1 : {first_seq[:16]}")
    print(f"   -> 16 bit dau tien cua chuoi 2 : {second_seq[:16]}")
    print(f"   -> Do dai chu ky do duoc       : {len(first_seq)} bits")

    assert first_seq == second_seq, "Sau 127 bits, chuoi PRBS-7 phai lap lai giong het!"
    print("   -> Ket qua                     : CHINH XAC (Chu ky tuan hoan dung 127 bits)\n")

    # 2. Kiem tra phan bo xac suat bit 1 va bit 0 (Phan bo thong ke ngau nhien)
    # Trong chu ky 127 bit cua PRBS-7: So luong bit 1 la (2^(N-1)) = 64, so bit 0 la 63
    num_ones = sum(first_seq)
    num_zeros = 127 - num_ones
    print("2. PHAN BO THONG KE CAN BANG NGAU NHIEN:")
    print(f"   -> So luong bit 1              : {num_ones} (Ly thuyet: 64)")
    print(f"   -> So luong bit 0              : {num_zeros} (Ly thuyet: 63)")
    assert num_ones == 64 and num_zeros == 63, "PRBS-7 phai co dung 64 bit 1 va 63 bit 0!"
    print("   -> Ket qua                     : HOAN HAO (Can bang DC tuyet doi)\n")

    # 3. Kiem tra tinh huong bien: Khoi tao all-zeros (0x00)
    # Bo sinh ma phai tu dong phuc hoi ve seed hop le de tranh bi khoa chet
    prbs_zero = PRBS7Generator(seed=0x00)
    assert prbs_zero.state != 0, "Bo sinh ma phai tu dong tranh trang thai cam all-zeros!"
    print("3. KIEM TRA PHONG VE TRANG THAI CAM ALL-ZEROS:")
    print(f"   -> Seed truyen vao             : 0x00")
    print(f"   -> State sau khoi tao an toan  : 0x{prbs_zero.state:02X} (Khong bi khoa chet)\n")

    # 4. Kiem tra do luong ty le loi bit Bit Error Rate Tester (BERT)
    print("4. KIEM TRA BO DO TY LE LOI BIT (BERT TEST):")
    tx_stream = prbs7.generate_sequence(1000)
    # Gia lap truyen qua kenh co 5 bit bi loi
    rx_stream = list(tx_stream)
    corrupted_indices = [15, 120, 350, 780, 990]
    for idx in corrupted_indices:
        rx_stream[idx] ^= 1  # Dao bit tao loi

    errs, total, ber = BitErrorRateTester.calculate_ber(tx_stream, rx_stream)
    print(f"   -> Tong so bit phat di (TX)    : {total} bits")
    print(f"   -> So bit bi loi phat hien     : {errs} bits")
    print(f"   -> Ty le loi bit (BER)         : {ber:.6f} ({ber * 100:.2f}%)")

    assert errs == 5, "BERT phai phat hien chinh xac 5 bit loi!"
    assert abs(ber - 0.005) < 1e-6

    print("\n[THANH CONG] DA HOAN THANH BO SINH MA PRBS VA DO KIEM LOI BIT CHO SERDES APPLE/TESLA!")
