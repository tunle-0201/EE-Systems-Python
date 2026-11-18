"""
================================================================================
          MODULE Z: RADIATION-HARDENED TMR & FAULT-TOLERANT SPACE AVIONICS
              MILESTONE Z.2: RADIATION SEU MEMORY SCRUBBER HAMMING(7, 4)
================================================================================

HIEN TUONG SINGLE EVENT UPSET (SEU) TREN BO NHO RAM TRONG KHONG GIAN VU TRU:
Khi ve tinh bay qua vanh dai buc xa hoac gap gio bao Mat Troi (Solar Flare):
- Cac hat ion mang nang luong cao ban xuyen qua lop tiep giap ban dan silicon cua chip SRAM.
- Hien tuong dao nguoc bit bat ky (Single Event Upset - SEU):
  Bit '0' bi bien thanh '1' hoac bit '1' bien thanh '0', lam bien dang bien so dan duong!

GIAI PHAP PHAN CUNG: BO QUET SUA LOI BO NHO (SEU MEMORY SCRUBBER WITH HAMMING SEC):
Mach Memory Scrubber chay ngam duoi nen phan cung voi toc do cao:
- Doc tung o nho, kiem tra va tu dong ghi lai (Scrub & Writeback) truoc khi loi tich luy!
- Ma Hamming(7, 4):
  + Ma hoa 4 bit du lieu [d1, d2, d3, d4] bang 3 bit kiem tra chan le [p1, p2, p3].
  + Tao thanh tu ma 7-bit: [p1, p2, d1, p3, d2, d3, d4].

MA TRAN TINH HOI CHUNG LOI SYNDROME (ASCII TEXT BLOCK):

         p1 = d1 ^ d2 ^ d4
         p2 = d1 ^ d3 ^ d4
         p3 = d2 ^ d3 ^ d4

         s1 = p1 ^ d1 ^ d2 ^ d4
         s2 = p2 ^ d1 ^ d3 ^ d4
         s3 = p3 ^ d2 ^ d3 ^ d4

         Syndrome = (s3 << 2) | (s2 << 1) | s1

LUAT PHAN XU VA SUA LOI:
- Neu Syndrome == 0: Khong co loi (Du lieu toan ven 100%).
- Neu Syndrome > 0: Syndrome chi dung vi tri bit bi dao nguoc (1-indexed tu trai sang phai)!
  Mach phan cung chi can lat nguoc lai bit tai vi tri do (Single Error Correction - SEC).
"""

from typing import Tuple, List, Dict, Any, Optional


class MemoryBitflipScrubber:
    """
    Bo quet sua loi bo nho SRAM chong buc xa khong gian bang ma Hamming(7, 4) SEC
    """
    def __init__(self):
        self.corrected_flips_count = 0
        self.total_scrubbed_words = 0

    def compute_parity_bits(self, data_nibble: int) -> int:
        """
        Ma hoa 4-bit data thanh 7-bit Hamming(7, 4):
        Bit layout (tu MSB sang LSB): p1, p2, d1, p3, d2, d3, d4
        """
        d1 = (data_nibble >> 3) & 1
        d2 = (data_nibble >> 2) & 1
        d3 = (data_nibble >> 1) & 1
        d4 = data_nibble & 1

        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4

        code_7bit = (p1 << 6) | (p2 << 5) | (d1 << 4) | (p3 << 3) | (d2 << 2) | (d3 << 1) | d4
        return code_7bit

    def scrub_and_correct(self, code_7bit: int) -> Tuple[int, int]:
        """
        Kiem tra hoi chung loi Syndrome va tu dong sua loi 1-bit:
        Tra ve: (recovered_data_4bit, number_of_bits_fixed)
        """
        self.total_scrubbed_words += 1
        # Tach cac bit: b[0]=p1, b[1]=p2, b[2]=d1, b[3]=p3, b[4]=d2, b[5]=d3, b[6]=d4
        b = [(code_7bit >> (6 - i)) & 1 for i in range(7)]

        s1 = b[0] ^ b[2] ^ b[4] ^ b[6]
        s2 = b[1] ^ b[2] ^ b[5] ^ b[6]
        s3 = b[3] ^ b[4] ^ b[5] ^ b[6]
        syndrome = (s3 << 2) | (s2 << 1) | s1

        flips = 0
        if 1 <= syndrome <= 7:
            # Lat nguoc bit bi loi tai vi tri syndrome (chuyen ve 0-indexed)
            error_pos = syndrome - 1
            b[error_pos] ^= 1
            flips = 1
            self.corrected_flips_count += 1

        recovered_data = (b[2] << 3) | (b[4] << 2) | (b[5] << 1) | b[6]
        return recovered_data, flips


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: SEU MEMORY SCRUBBER HAMMING(7, 4)")
    print("=========================================================\n")

    scrubber = MemoryBitflipScrubber()
    original_data = 0b1011  # Gia tri 11
    encoded = scrubber.compute_parity_bits(original_data)

    # 1. Kich ban hat ion ban trung lam dao nguoc bit tai vi tri bit d2 (bit so 2)
    corrupted = encoded ^ (1 << 2)
    recovered, bit_fixed = scrubber.scrub_and_correct(corrupted)

    print("1. KET QUA QUET VA SUA LOI BIT BI TIA VU TRU BAN PHA:")
    print(f"   -> Du lieu 4-bit goc            : {bin(original_data)}")
    print(f"   -> Ma Hamming(7, 4) chuan       : {bin(encoded)}")
    print(f"   -> Ma bi loi dao bit tia vu tru : {bin(corrupted)}")
    print(f"   -> Du lieu phuc hoi sau Scrub   : {bin(recovered)}")
    print(f"   -> So bit da tu dong sua chua   : {bit_fixed} bit")

    assert recovered == original_data, "Du lieu phuc hoi phai khop 100% voi du lieu goc!"
    assert bit_fixed == 1, "Phai phat hien va sua dung 1 bit bi loi!"

    # 2. Kich ban du lieu sach khong bi loi (Clean word)
    clean_recovered, clean_fixed = scrubber.scrub_and_correct(encoded)
    print("\n2. TEST TU DONG KHI BO NHO KHONG BI LOI:")
    print(f"   -> Du lieu kiem tra             : {bin(clean_recovered)}")
    print(f"   -> So bit can sua               : {clean_fixed} bit")

    assert clean_recovered == original_data and clean_fixed == 0

    print("\n[THANH CONG] DA HOAN THANH BO SUA LOI RAM CHONG TIA VU TRU CHO VE TINH!")
