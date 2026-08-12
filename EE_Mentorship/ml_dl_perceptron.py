"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.1: MÔ HÌNH NƠ-RON ĐƠN BỎI (SINGLE PERCEPTRON)
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ NƠ-RON VẬT LÝ (TOOLBOX MASTERY)

Mối Nơ-ron AI (Perceptron) mô phỏng lại Tế bào thần kinh sinh học:
1. Nhận tín hiệu đầu vào: Vector X = [Cảm biến 1, Cảm biến 2...]
2. Mỗi cảm biến được nhân với Trọng số (Weight W): Đại diện cho độ tin cậy của cảm biến.
3. Cộng thêm Độ lệch (Bias b): Ngưỡng kích hoạt ban đầu.
4. Tổng tổng hợp tín hiệu: Z = Sum(W * X) + b
5. Cho qua Hàm kích hoạt Sigmoid (Activation Function):
   - Ép tổng Z về dải xác suất từ 0.0 (An toàn) đến 1.0 (Nguy hiểm):
     
     Sigmoid(Z) = 1 / (1 + e^(-Z))

BÀI TOÁN THỰC TẾ:
Cảm biến Drone gửi về: Speed = 85km/h, Distance_to_obstacle = 2.0m.
Cho Trọng số W = [0.05, -1.2] và Bias b = 0.5.

Nhiệm vụ của Kỹ sư trưởng trong hàm `single_neuron_drone_warning(speed, distance, W, b)`:
1. Tạo vector tín hiệu X = np.array([speed, distance])
2. Tính tổng tín hiệu: Z = np.dot(X, W) + b
3. Cho qua hàm Sigmoid: probability = 1.0 / (1.0 + np.exp(-Z))
4. Trả về: probability (Con số xác suất từ 0.0 đến 1.0)
"""

import numpy as np

def single_neuron_drone_warning(speed, distance, W, b):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Nơ-ron từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tạo vector X từ speed và distance
    - Tính tổng Z bằng tích vô hướng np.dot(X, W) + b
    - Tính xác suất qua Sigmoid: 1.0 / (1.0 + np.exp(-Z))
    - Trả về: probability
    """
    X = np.array([speed, distance])
    Z = np.dot(X, W) + b
    probability = 1.0 / (1.0 + np.exp(-Z))
    return probability


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: SINGLE PERCEPTRON DRONE WARNING SYSTEM")
    print("=========================================================\n")
    
    # Trọng số học được của AI: Tốc độ cao -> Tăng nguy hiểm (+0.05)
    #                             Khoảng cách ngắn -> Tăng nguy hiểm cực đại (-1.2)
    W_weights = np.array([0.05, -1.2])
    b_bias = 0.5
    
    prob = single_neuron_drone_warning(85.0, 2.0, W_weights, b_bias)
    
    if prob is not None:
        print(f"1. KẾT QUẢ TÍNH TOÁN CỦA TẾ BÀO NƠ-RON AI:")
        print(f"   -> Tổng tín hiệu tích tụ (Z)      : {np.log(prob / (1 - prob)):.2f}")
        print(f"   -> Xác suất Cảnh báo Va chạm     : {prob * 100:.1f}%")
        
        status = "🚨 NGUY HIỂM: NÊ VẬT CẢN KHẨN CẤP!" if prob > 0.5 else "AN TOÀN 🟢"
        print(f"   -> Trạng thái Nơ-ron AI          : {status}")
        
        # Kiểm tra tính chính xác (Tốc độ 85km/h, Khoảng cách 2m -> Nguy hiểm > 90%)
        assert prob > 0.8, "Lỗi tính toán Nơ-ron!"
        
        print("\n[THÀNH CÔNG] NƠ-RON AI ĐẦU TIÊN CỦA TRÒ ĐÃ TÍNH TOÁN XÁC SUẤT NGUY HIỂM CHÍNH XÁC!")
