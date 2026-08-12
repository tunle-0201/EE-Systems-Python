"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.5: SO SÁNH CÁC HÀM KÍCH HOẠT (ACTIVATION FUNCTIONS)
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ HÀM KÍCH HOẠT (ACTIVATION TOOLBOX)

Trong Mạng Nơ-ron Deep Learning, có 3 Hàm kích hoạt phổ biến nhất:
1. Sigmoid: Ép tín hiệu về dải (0.0 đến 1.0) -> Dùng ở lớp Output tính Xác suất.
   - Sigmoid(z) = 1.0 / (1.0 + np.exp(-z))
2. ReLU (Rectified Linear Unit): Triệt tiêu số âm về 0, giữ nguyên số dương -> Dùng ở các Lớp Ẩn (Hidden Layers).
   - ReLU(z) = np.maximum(0, z)
3. Leaky ReLU: Khắc phục sự cố Nơ-ron chết (Dying ReLU) bằng cách nhân 0.01 với số âm.
   - LeakyReLU(z) = np.where(z > 0, z, 0.01 * z)

BÀI TOÁN THỰC TẾ:
Cho mảng tín hiệu đầu vào Z = [-5.0, 0.0, 3.0].

Nhiệm vụ của Kỹ sư trưởng trong hàm `compute_activations(Z)`:
1. Tính sig = 1.0 / (1.0 + np.exp(-Z))
2. Tính relu = np.maximum(0, Z)
3. Tính leaky_relu = np.where(Z > 0, Z, 0.01 * Z)
4. Trả về: sig, relu, leaky_relu
"""

import numpy as np

def compute_activations(Z):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Activation từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - sig = 1.0 / (1.0 + np.exp(-Z))
    - relu = np.maximum(0, Z)
    - leaky_relu = np.where(Z > 0, Z, 0.01 * Z)
    - Trả về: sig, relu, leaky_relu
    """
    sig = 1.0 / (1.0 + np.exp(-Z))
    relu = np.maximum(0, Z)
    leaky_relu = np.where(Z > 0, Z, 0.01 * Z)
    return sig, relu, leaky_relu



if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: ACTIVATION FUNCTIONS COMPARISON")
    print("=========================================================\n")
    
    Z_signal = np.array([-5.0, 0.0, 3.0])
    
    sig, relu, leaky = compute_activations(Z_signal)
    
    if sig is not None:
        print(f"1. KẾT QUẢ SO SÁNH 3 HÀM KÍCH HOẠT TRÊN TÍN HIỆU [-5.0, 0.0, 3.0]:")
        print(f"   -> Sigmoid    (Dải 0..1) : {sig}")
        print(f"   -> ReLU       (Dải 0..Z) : {relu}")
        print(f"   -> Leaky ReLU (Tránh chết): {leaky}")
        
        # Kiểm tra tính chính xác
        assert relu[0] == 0.0 and relu[2] == 3.0, "Lỗi hàm ReLU!"
        assert leaky[0] == -0.05, "Lỗi hàm Leaky ReLU!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ LÀM CHỦ BỘ 3 HÀM KÍCH HOẠT CỐT LÕI CỦA DEEP LEARNING!")
