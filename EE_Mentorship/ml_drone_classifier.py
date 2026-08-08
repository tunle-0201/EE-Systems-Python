"""
================================================================================
          REAL MACHINE LEARNING: DRONE FLIGHT ANOMALY CLASSIFIER
================================================================================

TẠM BIỆT BÀI TẬP MẪU! ĐÂY LÀ BÀI TOÁN THỰC TẾ CỦA MỘT KỸ SƯ AI:

Bài toán:
Trò được cấp một Tập dữ liệu Lịch sử Bay gồm 100 mẫu (100 rows x 5 cols):
- Cột 0: Roll (Góc nghiêng ngang)
- Cột 1: Pitch (Góc nghiêng dọc)
- Cột 2: Altitude (Độ cao)
- Cột 3: Battery (% Pin)
- Cột 4: Label y (0 = Bay an toàn, 1 = Nguy cơ Crash rơi máy bay)

Nhiệm vụ của trò (KHÔNG CÓ GỢI Ý CÚ PHÁP TRONG COMMENT):
1. Tách ma trận dataset 100x5 thành X (4 cột đầu) và y (cột cuối cùng).
2. Khởi tạo mô hình Decision Tree Classifier từ scikit-learn và Huấn luyện (Fit) AI trên tập (X, y).
3. Sử dụng mô hình đã huấn luyện để Dự đoán (Predict) 3 gói tin telemetry mới tới:
   - Gói A: [5.0,  2.0, 50.0, 85.0]  (Bay êm)
   - Gói B: [55.0, 10.0, 40.0, 90.0]  (Lật nghiêng 55 độ)
   - Gói C: [2.0,   1.0,  1.5,  5.0]  (Sắp hết pin + Độ cao quá thấp)
"""

import numpy as np
from sklearn.tree import DecisionTreeClassifier

# Tập dữ liệu 100 chuyến bay giả lập (Đã tạo sẵn cho trò)
np.random.seed(42)
normal_flights = np.random.normal(loc=[5.0, 2.0, 50.0, 80.0, 0], scale=[3.0, 2.0, 10.0, 10.0, 0], size=(80, 5))
crash_flights = np.random.normal(loc=[50.0, 45.0, 3.0, 8.0, 1], scale=[10.0, 10.0, 2.0, 3.0, 0], size=(20, 5))
flight_dataset = np.vstack([normal_flights, crash_flights])
np.random.shuffle(flight_dataset)


def train_and_predict_drone_ai(dataset, new_incoming_packets):
    """
    Trò tự tay lập trình hàm này mà KHÔNG CÓ GỢI Ý CÚ PHÁP:
    - Bước 1: Tách X và y từ dataset
    - Bước 2: Khai báo model DecisionTreeClassifier() và huấn luyện bằng .fit(X, y)
    - Bước 3: Dự đoán 3 gói tin mới bằng .predict(new_incoming_packets)
    - Trả về: model, predictions
    """
    # GÕ CODE THỰC TẾ CỦA TRÒ VÀO ĐÂY:
    X, y = dataset[:, 0:4], dataset[:, 4]
    model = DecisionTreeClassifier()
    model.fit(X, y)
    predictions = model.predict(new_incoming_packets)
    return model, predictions

if __name__ == "__main__":
    print("=========================================================")
    print("   AI ENGINE: DRONE FLIGHT CRASH PREDICTION MODEL")
    print("=========================================================\n")
    
    # 3 gói tin telemetry mới gửi từ cảm biến Drone
    new_test_packets = np.array([
        [5.0,  2.0, 50.0, 85.0],  # Gói A
        [55.0, 10.0, 40.0, 90.0],  # Gói B
        [2.0,   1.0,  1.5,  5.0]   # Gói C
    ])
    
    model, predictions = train_and_predict_drone_ai(flight_dataset, new_test_packets)
    
    if predictions is not None:
        labels_map = {0: "AN TOÀN 🟢", 1: "NGUY CƠ CRASH 🔴"}
        print("KẾT QUẢ DỰ ĐOÁN CỦA MÔ HÌNH AI TRÊN 3 GÓI TIN MỚI:")
        print(f" -> Gói A [Bay ổn định]: {labels_map[int(predictions[0])]}")
        print(f" -> Gói B [Lật nghiêng ]: {labels_map[int(predictions[1])]}")
        print(f" -> Gói C [Cạn pin/Thấp]: {labels_map[int(predictions[2])]}")
        
        # Đánh giá độ chính xác của AI
        accuracy = model.score(flight_dataset[:, :4], flight_dataset[:, 4])
        print(f"\n -> Độ chính xác của AI trên 100 mẫu huấn luyện: {accuracy * 100:.1f}%")
        print("\n[CHÚC MỪNG] TRÒ ĐÃ TỰ TAY HUẤN LUYỆN THÀNH CÔNG MÔ HÌNH AI THỰC TẾ!")
