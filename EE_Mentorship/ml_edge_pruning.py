"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.2: KỸ THUẬT TỈA NHÁNH MẠNG NƠ-RON (WEIGHT PRUNING)
================================================================================

TẠI SAO CẦN WEIGHT PRUNING (TỈA NHÁNH) TRÊN CHIP DRONE?
Trong Mạng Nơ-ron AI, có nhiều Trọng số W rất nhỏ gần bằng 0 (ví dụ 0.001, -0.002).
Những trọng số này không đóng góp gì cho kết quả nhưng vẫn làm tốn CPU.
Kỹ sư Edge AI dùng kỹ thuật **Weight Pruning (Tỉa nhánh)**:
- Gán tất cả các trọng số có giá trị tuyệt đối |W| < threshold thành 0.
- Giúp Ma trận thưa thớt (Sparse Matrix), tăng tốc nhân ma trận gấp 3 lần!

Nhiệm vụ của Kỹ sư trưởng trong hàm `prune_weights(W, threshold=0.1)`:
1. Tạo ma trận mới W_pruned = np.where(np.abs(W) < threshold, 0.0, W)
2. Trả về: W_pruned
"""

import numpy as np

def prune_weights(W, threshold=0.1):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Pruning từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tỉa các trọng số có |W| < threshold về 0.0
    - Giữ nguyên các trọng số lớn
    - Trả về: W_pruned
    """
    W_pruned = np.where(abs(W) < threshold, 0.0, W)
    return W_pruned


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: NEURAL NETWORK WEIGHT PRUNING FOR DRONES")
    print("=========================================================\n")
    
    W_dense = np.array([2.5, 0.02, -0.05, 1.8, -0.01])
    
    W_sparse = prune_weights(W_dense, threshold=0.1)
    
    if W_sparse is not None:
        print("1. KET QUA TIA NHANH TRONG SO MANG NO-RON AI:")
        print(f"   -> Trong so ban dau (Dense Weights)    : {W_dense}")
        print(f"   -> Trong so sau khi Tia (Sparse Pruned): {W_sparse}")
        
        # Kiểm tra tính chính xác (các số nhỏ hơn 0.1 phải biến thành 0.0)
        assert W_sparse[1] == 0.0 and W_sparse[2] == 0.0 and W_sparse[0] == 2.5, "Loi tia nhanh Pruning!"
        
        print("\n[THANH CONG] TRO DA TIA NHANH THANH CONG GIUP MANG AI TANG TOC 300% TREN CHIP DRONE!")
