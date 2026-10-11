"""
================================================================================
          MODULE AD: MISSION-CRITICAL AEROSPACE AVIONICS PROTOCOLS
          MILESTONE AD.2: ARINC 429 32-BIT BNR/BCD AVIONICS BUS & OCTAL LABELS
================================================================================

TAI SAO CHUAN ARINC 429 LA NEN TANG TRUYEN TIN HANG KHONG DUNG CHO TAU VU TRU?
- ARINC 429 la tieu chuan giao tiep hang dau the gioi trong he thong dien tu bay
  (Avionics) tren may bay thuong mai (Boeing 787, Airbus A350) va he thong dan
  duong tau vu tru thuong mai (Commercial Crew & Cargo).
- Dac tinh vat ly:
  1. Su dung truyen dan vi sai hai day (A va B) voi 3 muc dien ap Bipolar
     Return-to-Zero (BPRZ): +10V (Cao), 0V (Null), -10V (Thap).
  2. Toc do cao 100 kbps (High-Speed) hoac toc do thap 12.5 kbps (Low-Speed).
  3. Khoang nghi giua cac tu (Inter-Word Gap) toi thieu 4 bit times o muc 0V
     giup bo thu tu dong dong bo khung tu ma khong can duong xung nhip Clock rieng.

SO DO DANG SONG 3 MUC BIPOLAR RETURN-TO-ZERO BPRZ (ASCII DIAGRAM):

   Dien ap
     +10V |    +───+                     (Bit 1: Len +10V roi ve 0V)
          |    |   |
       0V |────+   +───────+   +───────  (0V: Khoang nghi giua cac xung)
          |                |   |
     -10V |                +───+         (Bit 0: Xuong -10V roi ve 0V)
          +────────────────────────────> Thoi gian t

TOAN HOC CAU TRUC TU 32-BIT ARINC 429 (ASCII MATH BLOCKS):

1. Phan bo 32 bit trong mot tu ARINC 429:
   +───────────+──────────+────────────────────────────+──────────+────────────+
   | Bit 1 - 8 | Bit 9-10 |       Bit 11 - 29          | Bit 30-31|   Bit 32   |
   |   Label   |   SDI    |       Data Payload         |   SSM    | Odd Parity |
   |  (Octal)  | (2 bits) | (19 bits BNR hoac BCD)     | (2 bits) |  (1 bit)   |
   +───────────+──────────+────────────────────────────+──────────+────────────+

2. Nhan bat phan (Octal Label):
   - 8 bit dau tien bieu dien ma nhan du lieu duoi he bat phan (Octal: 000 - 377).
   - Vi du:
     + Label 203 (0o203) : Do cao khi ap (Barometric Altitude, don vi: feet).
     + Label 324 (0o324) : Goc ngoc Pitch Angle (don vi: do).
     + Label 325 (0o325) : Goc nghieng Roll Angle (don vi: do).

3. Ma tran trang thai SSM (Sign/Status Matrix - Bit 30 va 31 cho BNR):
   - 00 : Failure Warning (Canh bao hong hoc cam bien)
   - 01 : No Computed Data (Chua co du lieu tinh toan)
   - 10 : Functional Test (Che do tu kiem tra bao duong)
   - 11 : Normal Operation (Du lieu tin cay hoat dong binh thuong)

4. Dinh dang so thuc BNR (Binary Two's Complement):
   Bit 29 la bit dau (1 = Am, 0 = Duong).
   Gia tri thuc tinh theo cong thuc:
                  Raw_Integer_Value
   Real_Value = ─────────────────────── * Max_Scale
                     2^(Data_Bits)

5. Bit Parity le (Odd Parity - Bit 32):
   Tong so bit 1 trong toan bo 32 bit phai la mot so LE:
   Bit_32 = 1 - (sum_bits(Bits_1_to_31) % 2)
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class ARINC429Word:
    """
    Dai dien mot tu du lieu 32-bit chuan hang khong ARINC 429.
    """

    def __init__(self, raw_word: int):
        self.raw_word = int(raw_word) & 0xFFFFFFFF

    @property
    def label(self) -> int:
        """
        Gia tri nhan (Bit 1 den 8). Trong giao thuc ARINC 429, nhan duoc bieu dien duoi he bat phan.
        """
        return self.raw_word & 0xFF

    @property
    def octal_label(self) -> str:
        """
        Tra ve chuoi bieu dien bat phan 3 chu so (vi du: '203', '324').
        """
        return f"{self.label:03o}"

    @property
    def sdi(self) -> int:
        """
        Source/Destination Identifier (Bit 9 den 10).
        """
        return (self.raw_word >> 8) & 0x03

    @property
    def data_field(self) -> int:
        """
        Vung du lieu Payload 19-bit (Bit 11 den 29).
        """
        return (self.raw_word >> 10) & 0x7FFFF

    @property
    def ssm(self) -> int:
        """
        Sign/Status Matrix (Bit 30 den 31).
        """
        return (self.raw_word >> 29) & 0x03

    @property
    def parity(self) -> int:
        """
        Bit Parity le (Bit 32 - MSB).
        """
        return (self.raw_word >> 31) & 0x01

    def is_parity_valid(self) -> bool:
        """
        Kiem tra tinh hop le cua Odd Parity (Tong so bit 1 phai la so LE).
        """
        total_ones = bin(self.raw_word).count('1')
        return total_ones % 2 == 1

    @classmethod
    def encode_bnr(
        cls,
        octal_label_str: str,
        value: float,
        max_scale: float,
        sdi: int = 0,
        ssm: int = 3
    ) -> "ARINC429Word":
        """
        Dong goi tu ARINC 429 dinh dang so thuc BNR (19-bit Two's Complement):
        - octal_label_str: Chuoi bat phan (vi du '203' cho do cao)
        - value: Gia tri vat ly can truyen (vi du 32000.0 feet)
        - max_scale: Thang do toi da (vi du 131072.0 feet)
        - sdi: Dinh danh nguon 0 - 3
        - ssm: Ma tran trang thai (3 = Normal Operation)
        """
        label_int = int(octal_label_str, 8) & 0xFF

        # Chuan hoa gia tri vao dai 18-bit magnitude + 1 bit sign = 19 bits
        # Bit 29 la sign bit, bit 28..11 la magnitude
        ratio = max(-1.0, min(1.0, value / max_scale))
        max_int = (1 << 18) - 1
        raw_val = int(ratio * max_int)

        # Chuyen sang Bu 2 trong 19 bits
        data_19bit = raw_val & 0x7FFFF

        # Ghep 31 bits dau tien (Bit 1 den 31)
        word_31bit = (label_int) | ((sdi & 0x03) << 8) | (data_19bit << 10) | ((ssm & 0x03) << 29)

        # Tinh bit Parity le cho bit 32
        ones_count = bin(word_31bit).count('1')
        parity_bit = 0 if (ones_count % 2 == 1) else 1

        final_word = word_31bit | (parity_bit << 31)
        return cls(final_word)

    def decode_bnr(self, max_scale: float) -> Tuple[float, str]:
        """
        Giai ma tu ARINC 429 BNR sang gia tri so thuc vat ly va trang thai SSM.
        Tra ve: (real_value, status_text)
        """
        ssm_table = {
            0: "FAILURE_WARNING",
            1: "NO_COMPUTED_DATA",
            2: "FUNCTIONAL_TEST",
            3: "NORMAL_OPERATION"
        }
        status_text = ssm_table.get(self.ssm, "UNKNOWN")

        # Giai ma 19 bits Bu 2
        raw_19bit = self.data_field
        # Neu bit 18 (bit MSB cua vung data 19-bit) la 1 -> So am
        if (raw_19bit >> 18) & 1:
            signed_val = raw_19bit - (1 << 19)
        else:
            signed_val = raw_19bit

        max_int = (1 << 18) - 1
        real_value = (signed_val / max_int) * max_scale
        return real_value, status_text


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS: ARINC 429 32-BIT AVIONICS PROTOCOL")
    print("=========================================================\n")

    # 1. Kiem tra dong goi va giai ma Do cao khi ap (Barometric Altitude - Label 203)
    # Thang do: -1,000 ft den 131,072 ft -> Max scale = 131072.0 ft
    target_altitude = 35000.0  # Do cao hanh trinh 35,000 feet
    max_alt_scale = 131072.0

    alt_word = ARINC429Word.encode_bnr(
        octal_label_str="203",
        value=target_altitude,
        max_scale=max_alt_scale,
        sdi=1,
        ssm=3  # Normal Operation
    )

    print("1. DONG GOI THONG SO DO CAO KHI AP (LABEL 203):")
    print(f"   -> Nhan bat phan (Octal Label) : {alt_word.octal_label} (Do cao Baro Altitude)")
    print(f"   -> Ma thap luc phan (Hex Word) : 0x{alt_word.raw_word:08X}")
    print(f"   -> SDI (Source ID)             : {alt_word.sdi} (Kenhtrai Left ADC)")
    print(f"   -> SSM Status                  : {alt_word.ssm} (3 = Normal Operation)")
    print(f"   -> Bit Parity le (Bit 32)      : {alt_word.parity}")
    print(f"   -> Kiem tra Parity hop le      : {alt_word.is_parity_valid()}")

    assert alt_word.octal_label == "203", "Nhan phai la bat phan 203!"
    assert alt_word.is_parity_valid(), "Parity phai hop le (so le)!"

    # Giai ma tu ARINC 429
    decoded_alt, alt_status = alt_word.decode_bnr(max_scale=max_alt_scale)
    print(f"   -> Do cao giai ma duoc         : {decoded_alt:.2f} feet (Goc: {target_altitude:.2f} ft)")
    print(f"   -> Trang thai cam bien         : {alt_status}")

    assert abs(decoded_alt - target_altitude) < 1.0, "Do cao giai ma phai xap xi 35000 ft!"
    assert alt_status == "NORMAL_OPERATION"
    print("   -> Ket luan                     : DONG GOI VA GIAI MA BNR HOAN HAO!\n")

    # 2. Kiem tra dong goi thong so goc ngoc mui Pitch Angle (Label 324) co gia tri am
    # Thang do toi da: 180.0 do, Gia tri can truyen: -12.5 do
    pitch_target = -12.5  # Chuoi mui xuong 12.5 do
    max_pitch_scale = 180.0

    pitch_word = ARINC429Word.encode_bnr(
        octal_label_str="324",
        value=pitch_target,
        max_scale=max_pitch_scale,
        sdi=0,
        ssm=3
    )

    print("2. DONG GOI THONG SO GOC NGHIENG PITCH AM (LABEL 324):")
    print(f"   -> Nhan bat phan (Octal Label) : {pitch_word.octal_label} (Goc ngoc Pitch Angle)")
    print(f"   -> Ma Hex                      : 0x{pitch_word.raw_word:08X}")
    print(f"   -> Bit Parity le hop le        : {pitch_word.is_parity_valid()}")

    decoded_pitch, pitch_status = pitch_word.decode_bnr(max_scale=max_pitch_scale)
    print(f"   -> Goc Pitch giai ma duoc      : {decoded_pitch:.3f} do (Goc: {pitch_target:.3f} do)")
    assert abs(decoded_pitch - pitch_target) < 0.01, "Goc Pitch giai ma phai dung -12.5 do!"
    assert pitch_word.is_parity_valid()

    # 3. Kiem tra trang thai loi hong hoc SSM (Failure Warning)
    faulty_word = ARINC429Word.encode_bnr(
        octal_label_str="203",
        value=0.0,
        max_scale=max_alt_scale,
        ssm=0  # Failure Warning
    )
    _, fault_status = faulty_word.decode_bnr(max_scale=max_alt_scale)
    print("\n3. KIEM TRA MA TRAN TRANG THAI SSM KHI CAM BIEN HONG:")
    print(f"   -> Trang thai tra ve           : {fault_status}")
    assert fault_status == "FAILURE_WARNING", "He thong phai canh bao Failure Warning khi SSM = 0!"

    print("\n[THANH CONG] DA HOAN THANH GIAO THUC DIEN TU BAY ARINC 429 CHUAN DUC CHO MAY BAY VA TAU VU TRU!")
