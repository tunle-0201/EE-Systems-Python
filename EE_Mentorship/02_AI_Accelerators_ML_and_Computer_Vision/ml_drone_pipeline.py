"""
================================================================================
          MODULE B CAPSTONE FINALE: PIPELINE AI HOÀN CHỈNH CHO DRONE
================================================================================

TÍCH HỢP TẤT CẢ KIẾN THỨC HÔM NAY VÀO MỘT ĐƯỜNG ỐNG (PIPELINE) AI CHUYÊN NGHIỆP:

Quy trình 3 bước của một AI Engineer:
1. Chuẩn hóa dữ liệu thô X bằng `StandardScaler()` -> Thu được X_scaled và scaler
2. Huấn luyện AI DecisionTree trên dữ liệu đã chuẩn hóa (X_scaled, y)
3. Khi gói tin mới tới: 
   - Bước A: Thu nhỏ gói mới bằng `scaler.transform(gói_mới)`
   - Bước B: Cho AI dự đoán bằng `model.predict(gói_mới_đã_scaled)`

Nhiệm vụ của trò (LẦN CUỐI CÙNG TRONG NGÀY):
Tự tay hoàn thành hàm `build_scaled_drone_ai_pipeline(dataset, new_packet)`!
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# Tập dữ liệu bay thô (100 mẫu x 4 thuộc tính: Roll, Pitch, Alt, Battery, Label)
np.random.seed(42)
normal_flights = np.random.normal(loc=[5.0, 2.0, 50.0, 80.0, 0], scale=[3.0, 2.0, 10.0, 10.0, 0], size=(80, 5))
crash_flights = np.random.normal(loc=[50.0, 45.0, 3.0, 8.0, 1], scale=[10.0, 10.0, 2.0, 3.0, 0], size=(20, 5))
raw_dataset = np.vstack([normal_flights, crash_flights])
np.random.shuffle(raw_dataset)


def build_scaled_drone_ai_pipeline(dataset, new_packet):
    """
    Trò tự tay viết 4 dòng code đỉnh cao của Kỹ sư AI:
    1. Tách X, y từ dataset
    2. Chuẩn hóa X thành X_scaled bằng StandardScaler (dùng fit_transform)
    3. Huấn luyện model DecisionTreeClassifier() trên (X_scaled, y)
    4. Chuẩn hóa new_packet bằng scaler.transform(new_packet) rồi dự đoán bằng model.predict()
    - Trả về: prediction (0 hoặc 1)
    """
    # GÕ CODE PIPELINE CỦA TRÒ VÀO ĐÂY:
    X = dataset[:, 0:4]
    y = dataset[:, 4]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = DecisionTreeClassifier()
    model.fit(X_scaled, y)

    new_packet_scaled = scaler.transform(new_packet)
    prediction = model.predict(new_packet_scaled)

    return prediction


if __name__ == "__main__":
    print("=========================================================")
    print("   AI PIPELINE FINALE: CHUẨN HÓA & DỰ ĐOÁN SHUTDOWN DRONE")
    print("=========================================================\n")
    
    # 1 Gói tin nguy hiểm mới vừa bắn về từ cảm biến Drone
    # [Roll=60.0°, Pitch=40.0°, Alt=2.0m, Battery=5.0%]
    incoming_danger_packet = np.array([[60.0, 40.0, 2.0, 5.0]])
    
    pred = build_scaled_drone_ai_pipeline(raw_dataset, incoming_danger_packet)
    
    if pred is not None:
        result_text = "NGUY CƠ CRASH -> KÍCH HOẠT HẠ CÁNH KHẨN CẤP! 🚨" if pred[0] == 1 else "AN TOÀN 🟢"
        print(f"[TRẠM MẶT ĐẤT] Kết quả phân tích Pipeline AI: {result_text}")
        
        print("\n=========================================================")
        print("🎉 CHÚC MỪNG TRÒ ĐÃ TỐT NGHIỆP MODULE B: MACHINE LEARNING & NUMPY!")
        print("=========================================================")
