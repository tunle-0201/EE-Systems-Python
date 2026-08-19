"""
================================================================================
          MODULE H: EMBEDDED EDGE AI VISION TENSORS & ACCELERATION
              MILESTONE H.2: PHÉP NÉN KHÔNG GIAN MAX POOLING 2X2 ENGINE
================================================================================

TẠI SAO CẦN PHÉP NÉN MAX POOLING 2X2 TRONG MẠNG CNN?
Để giảm 75% số lượng điểm ảnh, tăng tốc AI gấp 4 lần nhưng vẫn giữ lại đặc trưng mạnh nhất:
- Trượt cửa sổ $2 \times 2$ với bước nhảy (Stride) = 2.
- Lấy giá trị lớn nhất: `output[i, j] = np.max(patch_2x2)`
"""

import numpy as np

def apply_2x2_max_pooling(feature_map):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Max Pooling từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - H, W = feature_map.shape
    - out_H, out_W = H // 2, W // 2
    - output = np.zeros((out_H, out_W))
    - Lặp i từ 0 đến out_H, lặp j từ 0 đến out_W:
      + patch = feature_map[i*2:(i+1)*2, j*2:(j+1)*2]
      + output[i, j] = np.max(patch)
    - Trả về: output
    """
    H, W = feature_map.shape
    out_H, out_W = H // 2, W // 2
    output = np.zeros((out_H, out_W))
    for i in range(out_H):
        for j in range(out_W):
            patch = feature_map[i*2:(i+1)*2, j*2:(j+1)*2]
            output[i, j] = np.max(patch)
    return output


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: 2X2 MAX POOLING DOWNSAMPLING ENGINE")
    print("=========================================================\n")
    
    fmap = np.array([
        [1.0, 3.0, 2.0, 4.0],
        [5.0, 6.0, 1.0, 2.0],
        [8.0, 7.0, 3.0, 9.0],
        [0.0, 2.0, 4.0, 1.0]
    ], dtype=np.float32)
    
    pooled = apply_2x2_max_pooling(fmap)
    
    print("1. KET QUA PHAP NEN MAX POOLING 2X2:")
    print(f"   -> Ma tran nen Output shape : {pooled.shape}")
    print(f"   -> Gia tri lon nhat gop lai : {pooled}")
    
    assert pooled.shape == (2, 2) and pooled[0, 0] == 6.0 and pooled[1, 1] == 9.0, "Loi Max Pooling!"
    print("\n[THANH CONG] DA NEN 75% DU LIEU MANG CNN TIEU THU I-O SPEEDUP 400%!")
