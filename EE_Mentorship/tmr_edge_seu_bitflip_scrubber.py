"""
================================================================================
          MODULE AD: RADIATION-HARDENED TMR & FAULT-TOLERANT AVIONICS
              MILESTONE AD.2: BỘ QUÉT SỬA LỖI TIA VŨ TRỤ (SEU MEMORY SCRUBBER)
================================================================================

HIỆN TƯỢNG SINGLE EVENT UPSET (SEU) TRÊN BỘ NHỚ RAM TRONG KHÔNG GIAN:
Hạt ion mang năng lượng cao từ Mặt Trời xuyên qua chip bán dẫn:
- Làm đảo ngược 1 bit bất kỳ trong RAM (từ 0 thành 1 hoặc từ 1 thành 0) -> Gây sai số hoặc crash!
- Kỹ thuật **Memory Scrubbing với mã Hamming (SEC-DED)**:
  + Bộ nhớ được quét định kỳ ngầm dưới nền phần cứng.
  + SEC (Single Error Correction): Tự động phát hiện và lật lại bit bị đảo ngược (Sửa lỗi 100%).
  + DED (Double Error Detection): Phát hiện nếu có 2 bit cùng bị hỏng và kích hoạt Failsafe!
"""

class MemoryBitflipScrubber:
    def __init__(self):
        self.corrected_flips_count = 0

    def compute_parity_bits(self, data_nibble: int) -> int:
        """Mã hóa 4-bit data thành 7-bit Hamming(7, 4): p1, p2, d1, p3, d2, d3, d4."""
        d1 = (data_nibble >> 3) & 1
        d2 = (data_nibble >> 2) & 1
        d3 = (data_nibble >> 1) & 1
        d4 = data_nibble & 1

        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4

        return (p1 << 6) | (p2 << 5) | (d1 << 4) | (p3 << 3) | (d2 << 2) | (d3 << 1) | d4

    def scrub_and_correct(self, code_7bit: int) -> tuple:
        """
        Trò đóng vai Kỹ sư Sửa lỗi Bộ nhớ Hàng không vũ trụ:
        - Tính hội chứng lỗi (Syndrome): s1, s2, s3
        - syndrome = (s3 << 2) | (s2 << 1) | s1
        - Nếu syndrome == 0: Không có lỗi bit
        - Nếu syndrome > 0: Lật lại đúng bit tại vị trí lỗi (1-indexed từ trái sang phải)
        - Trả về: (dữ liệu 4-bit gốc, số bit đã sửa)
        """
        b = [(code_7bit >> (6 - i)) & 1 for i in range(7)]  # [p1, p2, d1, p3, d2, d3, d4]

        s1 = b[0] ^ b[2] ^ b[4] ^ b[6]
        s2 = b[1] ^ b[2] ^ b[5] ^ b[6]
        s3 = b[3] ^ b[4] ^ b[5] ^ b[6]
        syndrome = (s3 << 2) | (s2 << 1) | s1

        flips = 0
        if syndrome > 0 and syndrome <= 7:
            error_pos = syndrome - 1
            b[error_pos] ^= 1  # Lật lại bit lỗi
            flips = 1
            self.corrected_flips_count += 1

        recovered_data = (b[2] << 3) | (b[4] << 2) | (b[5] << 1) | b[6]
        return recovered_data, flips


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: SEU MEMORY SCRUBBER HAMMING(7, 4)")
    print("=========================================================\n")

    scrubber = MemoryBitflipScrubber()
    original_data = 0b1011  # 11
    encoded = scrubber.compute_parity_bits(original_data)

    # Tia vũ trụ bắn trúng làm đảo ngược 1 bit (vị trí d2)
    corrupted = encoded ^ (1 << 2)
    recovered, bit_fixed = scrubber.scrub_and_correct(corrupted)

    print("1. KET QUA QUET VA SUA LOI BIT BI TIA VU TRU BAN PHAC:")
    print(f"   -> Du lieu 4-bit goc            : {bin(original_data)}")
    print(f"   -> Ma Hamming(7, 4) chuan       : {bin(encoded)}")
    print(f"   -> Ma bi loi dao bit tia vu tru : {bin(corrupted)}")
    print(f"   -> Du lieu phuc hoi sau Scrub   : {bin(recovered)}")
    print(f"   -> So bit da tu dong sua chua   : {bit_fixed} bit")

    assert recovered == original_data and bit_fixed == 1, "Loi SEU Scrubber!"
    print("\n[THANH CONG] DA HOAN THANH BO SUA LOI RAM CHONG TIA VU TRU CHO VE TINH!")
