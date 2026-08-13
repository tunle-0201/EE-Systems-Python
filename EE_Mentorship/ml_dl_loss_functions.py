"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.6: ĐO ĐẠC SAI SỐ HÀM LOSS (MSE & BINARY CROSS-ENTROPY)
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ HÀM TỔN THẤT (LOSS TOOLBOX)

1. Mean Squared Error (MSE Loss):
   - mse = np.mean((y_pred - y_true) ** 2)
2. Binary Cross-Entropy (BCE Loss):
   - bce = -np.mean(y_true * np.log(y_pred + 1e-15) + (1 - y_true) * np.log(1 - y_pred + 1e-15))

BÀI TOÁN THỰC TẾ:
Cho y_true = [1, 0], y_pred = [0.9, 0.1].

Nhiệm vụ của Kỹ sư trưởng trong hàm `compute_losses(y_true, y_pred)`:
1. Tính mse = np.mean((y_pred - y_true) ** 2)
2. Tính bce = -np.mean(y_true * np.log(y_pred + 1e-15) + (1 - y_true) * np.log(1 - y_pred + 1e-15))
3. Trả về: mse, bce
"""

import numpy as np

def compute_losses(y_true, y_pred):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Loss từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - mse = np.mean((y_pred - y_true) ** 2)
    - bce = -np.mean(y_true * np.log(y_pred + 1e-15) + (1 - y_true) * np.log(1 - y_pred + 1e-15))
    - Trả về: mse, bce
    """
    mse = np.mean((y_pred - y_true) ** 2)
    bce = -np.mean(y_true * np.log(y_pred + 1e-15) + (1 - y_true) * np.log(1 - y_pred + 1e-15))
    return mse, bce



if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: LOSS FUNCTIONS COMPUTATION (MSE & BCE)")
    print("=========================================================\n")
    
    y_t = np.array([1.0, 0.0])
    y_p = np.array([0.9, 0.1]) # Dự đoán chuẩn 90%
    
    mse, bce = compute_losses(y_t, y_p)
    
    if mse is not None:
        print(f"1. KẾT QUẢ ĐO ĐẠC SAI SỐ CỦA MẠNG NƠ-RON AI:")
        print(f"   -> MSE Loss (Mean Squared Error)     : {mse:.4f}")
        print(f"   -> BCE Loss (Binary Cross Entropy)   : {bce:.4f} (Rất nhỏ sát 0!)")
        
        # Kiểm tra tính chính xác
        assert mse < 0.05 and bce < 0.15, "Lỗi tính toán hàm Loss!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ LÀM CHỦ CẢ 2 HÀM SAI SỐ TỔN THẤT MSE VÀ BCE DÀNH CHO DEEP LEARNING!")
