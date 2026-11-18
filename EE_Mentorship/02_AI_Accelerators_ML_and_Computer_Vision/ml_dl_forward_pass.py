"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.2: MẠNG NƠ-RON MULTI-LAYER FORWARD PASS
================================================================================

BÀI TOÁN THỰC TẾ: HỆ THỐNG PHÁN ĐOÁN RỦI RO BAY ĐA CHIỀU (DRONE AVIONICS)
Một nơ-ron đơn lẻ chỉ cắt được 1 đường thẳng. Để nhận diện các tình huống bay
phức tạp (phi tuyến), chúng ta cần một Mạng Nơ-ron 2 Tầng:

1. TẦNG ẨN (HIDDEN LAYER - 4 Nơ-ron):
   - Nhận ma trận đầu vào X (N chuyến bay, mỗi chuyến có 3 cảm biến: Pitch, Roll, Alt).
   - Biến đổi tuyến tính với trọng số W1 và độ lệch b1.
   - Phá vỡ tính tuyến tính bằng hàm kích hoạt ReLU: Các giá trị âm triệt tiêu về 0,
     các giá trị dương giữ nguyên. (Đưa ra biểu diễn đặc trưng ẩn H).

2. TẦNG ĐẦU RA (OUTPUT LAYER - 1 Nơ-ron):
   - Nhận biểu diễn đặc trưng ẩn H từ tầng trước.
   - Biến đổi tuyến tính với trọng số W2 và độ lệch b2.
   - Nén kết quả về dải xác suất [0.0..1.0] bằng hàm Sigmoid để ra phán quyết cuối cùng.

YÊU CẦU CHO KỸ SƯ TRƯỞNG LÊ ĐẮC ANH TUẤN:
Tự tay viết toàn bộ logic bên trong hàm `forward_pass_neural_net` từ con số 0.
KHÔNG CÓ GỢI Ý CODE SẴN TRONG DOCSTRING!
"""

import numpy as np

def forward_pass_neural_net(X, W1, b1, W2, b2):
    """
    Tham so:
      X:  Ma tran dau vao (N mau bay x 3 cam bien)
      W1: Trong so tang an (3 x 4)
      b1: Do lech tang an (1 x 4)
      W2: Trong so tang ra (4 x 1)
      b2: Do lech tang ra (1 x 1)
      
    Tra ve:
      output: Ma tran xac suat rui ro (N mau bay x 1)
    """
    # TODO: Ky su Truong Tuan tu tay thiet ke luong Forward Pass tai day!
    
    K = np.dot(X, W1) + b1
    H = np.maximum(0, K)
    
    output2 = np.dot(H, W2) + b2
    output2 = 1/(1+np.exp(-output2))
    return output2


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: 2-LAYER NEURAL NETWORK FORWARD PASS")
    print("=========================================================\n")
    
    np.random.seed(42)
    # 2 chuyen bay: [Pitch, Roll, Altitude]
    X_input = np.array([[12.0, -5.0, 100.0], [45.0, 30.0, 5.0]]) 
    
    W1 = np.random.randn(3, 4)
    b1 = np.zeros((1, 4))
    W2 = np.random.randn(4, 1)
    b2 = np.zeros((1, 1))
    
    predictions = forward_pass_neural_net(X_input, W1, b1, W2, b2)
    
    if predictions is not None:
        print("1. KET QUA FORWARD PASS CUA MANG NO-RON 2 LOP:")
        print(f"   -> Kich thuoc ma tran Du doan (Shape) : {predictions.shape}")
        print(f"   -> Xac suat Du doan Mau 1 (An toan)  : {predictions[0, 0]*100:.1f}%")
        print(f"   -> Xac suat Du doan Mau 2 (Nguy hiem): {predictions[1, 0]*100:.1f}%")
        
        # Kiem tra tinh chinh xac
        assert predictions.shape == (2, 1), "Loi kich thuoc ma tran dau ra!"
        assert 0.0 <= predictions[0, 0] <= 1.0, "Loi gia tri Sigmoid!"
        print("\n[THANH CONG] MANG NO-RON 2 LOP DA TINH TOAN TOAN BO LUONG DU LIEU CHINH XAC!")
    else:
        print("[CHO XU LY] Ham forward_pass_neural_net dang tra ve None. Moi tro vao code!")
