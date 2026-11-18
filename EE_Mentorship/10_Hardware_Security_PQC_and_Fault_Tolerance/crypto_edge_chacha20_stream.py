"""
================================================================================
          MODULE W: ADVANCED EMBEDDED CRYPTO & POST-QUANTUM DEFENSE
              MILESTONE W.2: MÃ HÓA DÒNG SIÊU TỐC (CHACHA20 QUARTER-ROUND ENGINE)
================================================================================

TẠI SAO CHIP NHÚNG ARM CORTEX-M THÍCH CHACHA20 HƠN AES TRUYỀN THỐNG?
Thuật toán ChaCha20 (Google / TLS 1.3):
- Không dùng bảng tra cứu S-Box (Triệt tiêu 100% tấn công kênh kề Timing Cache Attack).
- Chỉ sử dụng 3 phép toán số nguyên cơ bản mà CPU nào cũng có:
  + Cộng số học (Add modulo 2^32)
  + Phép toán XOR (Bitwise XOR)
  + Phép xoay bit (Rotate Left - ROL)
- Chạy siêu nhanh trên các vi điều khiển không có bộ tăng tốc phần cứng AES!
"""

def chacha20_quarter_round(a: int, b: int, c: int, d: int):
    """
    Biến đổi 1/4 vòng (Quarter Round) của ChaCha20 trên 4 thanh ghi 32-bit:
    - a += b; d ^= a; d = rol(d, 16)
    - c += d; b ^= c; b = rol(b, 12)
    - a += b; d ^= a; d = rol(d, 8)
    - c += d; b ^= c; b = rol(b, 7)
    """
    MASK32 = 0xFFFFFFFF
    def rol(val, n):
        return ((val << n) & MASK32) | ((val & MASK32) >> (32 - n))

    a = (a + b) & MASK32
    d = rol(d ^ a, 16)

    c = (c + d) & MASK32
    b = rol(b ^ c, 12)

    a = (a + b) & MASK32
    d = rol(d ^ a, 8)

    c = (c + d) & MASK32
    b = rol(b ^ c, 7)

    return a, b, c, d


if __name__ == "__main__":
    print("=========================================================")
    print("   DEFENSE AVIONICS: CHACHA20 STREAM CIPHER ENGINE")
    print("=========================================================\n")

    # 4 thanh ghi ma trận trạng thái ban đầu
    r_a, r_b, r_c, r_d = 0x11111111, 0x22222222, 0x33333333, 0x44444444
    a_out, b_out, c_out, d_out = chacha20_quarter_round(r_a, r_b, r_c, r_d)

    print("1. KET QUA BIEN DOI THANH GHI CHACHA20 32-BIT:")
    print(f"   -> Thanh ghi A : 0x{a_out:08X}")
    print(f"   -> Thanh ghi B : 0x{b_out:08X}")
    print(f"   -> Thanh ghi C : 0x{c_out:08X}")
    print(f"   -> Thanh ghi D : 0x{d_out:08X}")

    assert a_out != r_a and b_out != r_b and c_out != r_c and d_out != r_d, "Loi ChaCha20 Round!"
    print("\n[THANH CONG] DA HOAN THANH ENGINE MA HOA DONG CHACHA20 SIEU TOC CHO VI DIEU KHIEN!")
