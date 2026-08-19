"""
================================================================================
          MODULE H: EMBEDDED EDGE AI VISION TENSORS & ACCELERATION
              MILESTONE H.1: PHÉP CUỘN MA TRẬN 2D CONVOLUTION KERNEL ENGINE
================================================================================

TẠI SAO PHÉP CUỘN 2D CONVOLUTION LÀ TRÁI TIM CỦA COMPUTER VISION AI (CNN)?
Mô hình CNN trượt một cửa sổ con dấu nhỏ (Kernel $3 \times 3$) khắp bức ảnh:
- Trích xuất các cạnh đường viền (Edge Detection), góc nhọn, và kết cấu vật thể.
- Công thức tại mỗi vị trí (i, j):
  output[i, j] = np.sum(image_patch * kernel)
"""

import numpy as np

def apply_2d_convolution(image_2d, kernel_3x3):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ 2D Convolution từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - H, W = image_2d.shape
    - output = np.zeros((H-2, W-2))
    - Lặp i từ 0 đến H-2, lặp j từ 0 đến W-2:
      + patch = image_2d[i:i+3, j:j+3]
      + output[i, j] = np.sum(patch * kernel_3x3)
    - Trả về: output
    """
    H, W = image_2d.shape
    output = np.zeros((H-2, W-2))
    for i in range(H-2):
        for j in range(W-2):
            patch = image_2d[i:i+3, j:j+3]
            output[i, j] = np.sum(patch * kernel_3x3)
    return output


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: 2D MATRIX CONVOLUTION KERNEL ENGINE")
    print("=========================================================\n")
    
    # Bức ảnh 5x5 giả lập
    img = np.array([
        [10, 10, 10, 0, 0],
        [10, 10, 10, 0, 0],
        [10, 10, 10, 0, 0],
        [10, 10, 10, 0, 0],
        [10, 10, 10, 0, 0]
    ], dtype=np.float32)
    
    # Kernel Sobel phát hiện đường viền dọc (Vertical Edge Detection)
    kernel = np.array([
        [1, 0, -1],
        [1, 0, -1],
        [1, 0, -1]
    ], dtype=np.float32)
    
    conv_res = apply_2d_convolution(img, kernel)
    
    print("1. KET QUA PHAP CUON MA TRAN 2D CONVOLUTION:")
    print(f"   -> Ma tran dac trung output shape: {conv_res.shape}")
    print(f"   -> Gia tri cuon tai vi tri trung tam: {conv_res[1, 1]:.1f}")
    
    assert conv_res.shape == (3, 3) and conv_res[1, 1] == 30.0, "Loi 2D Convolution!"
    print("\n[THANH CONG] DA HOAN THANH PHAP CUON MA TRAN 2D CONVOLUTION TRICH XUAT DAC TRUNG AI!")
