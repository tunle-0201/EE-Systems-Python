"""
================================================================================
          MODULE J: EMBEDDED HARDWARE ACCELERATION & NPU ARCHITECTURE
              MILESTONE J.3: TĂNG TỐC VECTOR SIMD 128-BIT (ARM NEON / RISC-V)
================================================================================

TẠI SAO CẦN VECTOR SIMD (SINGLE INSTRUCTION, MULTIPLE DATA)?
Thay vì dùng CPU cộng 4 cặp số trong 4 nhịp Clock riêng biệt:
- Thanh ghi Vector 128-bit (ARM Neon / RISC-V Vector) nạp 4 số Float32 cùng lúc.
- Thực hiện 1 lệnh đơn nhưng tính toán song song 4 phép toán trong đúng 1 Clock!

Sơ đồ 4 làn xử lý song song (SIMD Lanes Architecture):

  Thanh ghi Vector A (128-bit):
  ┌──────────────┬──────────────┬──────────────┬──────────────┐
  │ Lane 0 (32b) │ Lane 1 (32b) │ Lane 2 (32b) │ Lane 3 (32b) │
  │   A[0] = 1.5 │   A[1] = 2.0 │   A[2] = -1.0│   A[3] = 3.0 │
  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
         │ *            │ *            │ *            │ *  (Song song 1 Clock)
  ┌──────┴───────┬──────┴───────┬──────┴───────┬──────┴───────┐
  │   B[0] = 2.0 │   B[1] = 3.0 │   B[2] = 4.0 │   B[3] = 1.0 │
  │ Lane 0 (32b) │ Lane 1 (32b) │ Lane 2 (32b) │ Lane 3 (32b) │
  └──────────────┴──────────────┴──────────────┴──────────────┘
  Thanh ghi Vector B (128-bit):
         │              │              │              │
         ▼              ▼              ▼              ▼
     [ 3.00 ]       [ 6.00 ]       [-4.00 ]       [ 3.00 ] ──> Tổng = 8.00!
"""

import numpy as np

def compute_128bit_simd_dot_product(vec_A, vec_B):
    """
    vec_A, vec_B gồm đúng 4 phần tử float32 (128 bits).
    Trò đóng vai Kỹ sư phần cứng thiết kế tập lệnh Vector SIMD:
    - mult_res = vec_A * vec_B (Thực hiện song song 4 kênh SIMD)
    - total_sum = np.sum(mult_res)
    - Trả về: total_sum
    """
    mult_res = vec_A * vec_B
    total_sum = np.sum(mult_res)
    return total_sum


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE AI: 128-BIT VECTOR SIMD (ARM NEON) ENGINE")
    print("=========================================================\n")
    
    vA = np.array([1.5, 2.0, -1.0, 3.0], dtype=np.float32)
    vB = np.array([2.0, 3.0, 4.0, 1.0], dtype=np.float32)
    
    dot_simd = compute_128bit_simd_dot_product(vA, vB)
    
    print("1. KET QUA XU LY SONG SONG VECTOR SIMD 128-BIT:")
    print(f"   -> Vector A (4x Float32)       : {vA}")
    print(f"   -> Vector B (4x Float32)       : {vB}")
    print(f"   -> Tich vo huong SIMD Dot Prod : {dot_simd:.2f}")
    
    assert abs(dot_simd - 8.0) < 1e-5, "Loi Vector SIMD Engine!"
    print("\n[THANH CONG] DA HOAN THANH MO PHONG PHAN CUNG VECTOR SIMD 128-BIT TANG TOC 400%!")
