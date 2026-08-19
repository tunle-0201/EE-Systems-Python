"""
================================================================================
          MODULE H: EMBEDDED EDGE AI VISION TENSORS & ACCELERATION
              MILESTONE H.3: HÀM CHUẨN HÓA XÁC SUẤT ĐA LỚP SOFTMAX ENGINE
================================================================================

TẠI SAO CẦN HÀM SOFTMAX Ở LỚP CUỐI CỦA MẠNG AI PHÂN LOẠI ĐA LỚP?
Khi AI nhận diện 3 vật thể (0: Cây cối, 1: Xe hơi, 2: Con người):
- Lớp Output cho ra 3 con số thô (Logits - Ví dụ [2.0, 1.0, 0.1]).
- Hàm Softmax chuyển đổi 3 con số thô này thành **Mảng Xác suất tổng bằng 1.0 (100%)**:
  softmax(z_i) = exp(z_i) / sum(exp(z_j))
"""

import numpy as np

def compute_softmax_probabilities(logits):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Softmax từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - exp_z = np.exp(logits - np.max(logits)) # Chống tràn số Float
    - probs = exp_z / np.sum(exp_z)
    - Trả về: probs
    """
    exp_z = np.exp(logits - np.max(logits))
    probs = exp_z / np.sum(exp_z)
    return probs


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: MULTI-CLASS SOFTMAX PROBABILITY ENGINE")
    print("=========================================================\n")
    
    raw_logits = np.array([2.0, 1.0, 0.1])
    probabilities = compute_softmax_probabilities(raw_logits)
    
    print("1. KET QUA CHUAN HOA XAC SUAT DA LOP SOFTMAX:")
    print(f"   -> Tin hieu tho Logits         : {raw_logits}")
    print(f"   -> MANG XAC SUAT % (Softmax)   : {probabilities * 100.0}")
    print(f"   -> Tong xac suat 3 lop (Sum)   : {np.sum(probabilities):.4f}")
    
    assert abs(np.sum(probabilities) - 1.0) < 1e-5, "Loi Softmax!"
    print("\n[THANH CONG] DA CHUAN HOA THANH CONG XAC SUAT DA LOP SOFTMAX CHO AI!")
