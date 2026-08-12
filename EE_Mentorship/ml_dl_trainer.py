"""
================================================================================
          MODULE D CAPSTONE SPRINT: VÒNG LẶP HUẤN LUYỆN MẠNG NƠ-RON (TRAINING LOOP)
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ VÒNG LẶP HUẤN LUYỆN (TRAINING LOOP TOOLBOX)

Để AI học thành thạo, ta cho nó lặp lại 100 lần (100 Epochs):
1. Vòng lặp `for epoch in range(100):`
2. Dự đoán `y_pred = X * W`
3. Tính sai số `loss = (y_pred - y) ** 2`
4. Tính đạo hàm `dL_dW = 2 * (y_pred - y) * X`
5. Cập nhật `W = W - lr * dL_dW`

BÀI TOÁN THỰC TẾ:
Cảm biến X = 2.0, Đáp án thực tế y = 10.0.
Cho AI chạy 100 Epochs để tự động học ra Trọng số W tối ưu (W_optimal = 5.0)!

Nhiệm vụ của Kỹ sư trưởng trong hàm `train_drone_ai_model(X, y, epochs=100, lr=0.01)`:
1. Khởi tạo W = 0.0
2. Chạy vòng lặp `for epoch in range(epochs):`
   - y_pred = X * W
   - loss = (y_pred - y) ** 2
   - dL_dW = 2 * (y_pred - y) * X
   - W = W - lr * dL_dW
3. Trả về: W, loss
"""

import numpy as np

def train_drone_ai_model(X, y, epochs=100, lr=0.01):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Vòng lặp Huấn luyện để lập trình hàm này từ con số 0:
    - Khởi tạo W = 0.0
    - Lặp range(epochs):
      + y_pred = X * W
      + loss = (y_pred - y) ** 2
      + dL_dW = 2 * (y_pred - y) * X
      + W = W - lr * dL_dW
    - Trả về: W, loss
    """
    W = 0.0
    for epoch in range(epochs):
        y_pred = X * W
        loss = (y_pred - y) ** 2
        dL_dW = 2 * (y_pred - y) * X
        W = W - lr * dL_dW
    return W, loss


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: 100-EPOCH NEURAL NETWORK TRAINING LOOP")
    print("=========================================================\n")
    
    X_sensor = 2.0
    y_target = 10.0
    
    W_final, final_loss = train_drone_ai_model(X_sensor, y_target, epochs=100, lr=0.01)
    
    if W_final is not None:
        print(f"1. KẾT QUẢ QUÁ TRÌNH HUẤN LUYỆN 100 EPOCHS CỦA AI:")
        print(f"   -> Sai số Loss cuối cùng          : {final_loss:.6f} (Gần sát 0!)")
        print(f"   -> Trọng số W học được (W_final)  : {W_final:.4f} (Đã chạm sát mốc chuẩn 5.0000!)")
        print(f"   -> AI dự đoán mới với W_final     : {X_sensor * W_final:.4f}")
        
        # Kiểm tra tính chính xác (AI phải học được W sát mốc 5.0)
        assert abs(W_final - 5.0) < 0.1, "Lỗi huấn luyện chưa hội tụ!"
        
        print("\n=========================================================")
        print("🎉 CHÚC MỪNG TRÒ ĐÃ HOÀN THÀNH SPRINT TẢO THANH NẮC XANH ĐẬM GITHUB!")
        print("=========================================================")
