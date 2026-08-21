"""
================================================================================
          MODULE J: EMBEDDED HARDWARE ACCELERATION & NPU ARCHITECTURE
              MILESTONE J.2: MẢNG PHẦN CỨNG SYSTOLIC ARRAY MATRIX ENGINE (TPU / NPU)
================================================================================

TẠI SAO GOOGLE TPU & NPU DÙNG KIẾN TRÚC MẢNG SYSTOLIC ARRAY?
Systolic Array (Mảng co bóp như nhịp tim):
- Thay vì đọc/ghi RAM liên tục gây nghẽn cổ chai bus (Memory Wall).
- Dữ liệu được đẩy chuyền tay giữa các phần tử Processing Elements (PE) láng giềng.
- Nhân ma trận $2 \times 2$ với tốc độ phần cứng cực đại!
"""

import numpy as np

def compute_2x2_systolic_array(matrix_A, matrix_B):
    """
    Trò đóng vai Kỹ sư phần cứng thiết kế mảng Systolic Array 2x2:
    - C = np.dot(matrix_A, matrix_B)
    - Trả về: C
    """
    C = np.zeros((2, 2))
    # Mô phỏng dòng chảy dữ liệu chuyền tay giữa 4 PE (Processing Elements)
    C[0, 0] = matrix_A[0, 0]*matrix_B[0, 0] + matrix_A[0, 1]*matrix_B[1, 0]
    C[0, 1] = matrix_A[0, 0]*matrix_B[0, 1] + matrix_A[0, 1]*matrix_B[1, 1]
    C[1, 0] = matrix_A[1, 0]*matrix_B[0, 0] + matrix_A[1, 1]*matrix_B[1, 0]
    C[1, 1] = matrix_A[1, 0]*matrix_B[0, 1] + matrix_A[1, 1]*matrix_B[1, 1]
    return C


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE AI: 2X2 SYSTOLIC ARRAY MATRIX MULTIPLIER")
    print("=========================================================\n")
    
    A = np.array([[1.0, 2.0], [3.0, 4.0]])
    B = np.array([[5.0, 6.0], [7.0, 8.0]])
    
    res = compute_2x2_systolic_array(A, B)
    
    print("1. KET QUA NHAN MA TRAN TREN MANG SYSTOLIC ARRAY 2X2:")
    print(f"   -> Ma tran ket qua Output:\n{res}")
    
    assert res[0, 0] == 19.0 and res[1, 1] == 50.0, "Loi Systolic Array!"
    print("\n[THANH CONG] DA HOAN THANH MO PHONG KIEN TRUC SYSTOLIC ARRAY NHAN MA TRAN NPU!")
