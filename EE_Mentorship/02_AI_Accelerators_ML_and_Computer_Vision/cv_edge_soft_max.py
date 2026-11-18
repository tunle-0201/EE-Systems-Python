"""
================================================================================
          MODULE H: EMBEDDED EDGE AI VISION TENSORS & ACCELERATION
              MILESTONE H.3: HÀM CHUẨN HÓA XÁC SUẤT ĐA LỚP SOFTMAX ENGINE
================================================================================

TẠI SAO CẦN HÀM SOFTMAX Ở LỚP CUỐI CỦA MẠNG AI PHÂN LOẠI ĐA LỚP?
Khi AI nhận diện 3 vật thể (0: Cây cối, 1: Xe hơi, 2: Con người):
- Lớp Output cho ra 3 con số thô (Logits - Ví dụ [2.0, 1.0, 0.1]).
- Sơ đồ chuyển đổi xác suất số học ổn định (Numerically Stable Softmax):

  Raw Logits (z) ────> [ 2.0,  1.0,  0.1 ]
                             │
                             ▼  (Trừ max(z) = 2.0 chống tràn số float32)
  Shifted (z - max) ──> [ 0.0, -1.0, -1.9 ]
                             │
                             ▼  (Lấy hàm mũ exp)
  Numerators ─────────> [ 1.0, 0.3679, 0.1496 ]
                             │
                             ▼  (Chia cho tổng sum = 1.5175)
  Probabilities P ────> [ 0.659, 0.242, 0.099 ]  ===>  Tổng = 1.0 (100%)

- Công thức toán học (Dạng chữ phẳng):
                  exp(z_i - max(z))
  Softmax(z_i) = ────────────────────
                 sum(exp(z_j - max(z)))
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
