"""
================================================================================
          MODULE E CAPSTONE FINALE: HỆ THỐNG EDGE AI REAL-TIME CHO DRONE
================================================================================

TÍCH HỢP AI NÉN TRỰC TIẾP VỚI GÓI TIN CHUẨN NHỊ PHÂN 16-BYTES DRONE TELEMETRY:

Nhiệm vụ chót của Kỹ sư trưởng trong `process_telemetry_packet_with_edge_ai(raw_packet, W_int8, scale)`:
1. Giải mã gói tin nhị phân 16-Bytes bằng `struct.unpack('>HhhhfH', raw_packet)`
   -> Lấy Roll, Pitch, Alt, Battery
2. Chuẩn hóa vector tín hiệu X = np.array([Roll, Pitch, Alt, Battery])
3. Giải nén trọng số W_float = W_int8 * scale
4. Tính score = np.dot(X, W_float)
5. Dự đoán probability = 1.0 / (1.0 + np.exp(-score / 100.0))
6. Trả về: (is_crash_warning, probability)
"""

import struct
import numpy as np

def process_telemetry_packet_with_edge_ai(raw_packet, W_int8, scale):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Edge AI Telemetry để lập trình hàm này từ con số 0:
    - Giải mã 16 bytes nhị phân bằng struct.unpack
    - Nhân ma trận nơ-ron AI với vector cảm biến
    - Tính xác suất bằng hàm Sigmoid
    - Trả về: (is_crash_warning, probability)
    """
    checksum = struct.unpack(">HhhhfH", raw_packet)
    x = np.array([checksum[1], checksum[2], checksum[3], checksum[4]])
    w_float = W_int8 * scale
    score = np.dot(x, w_float)
    prob = 1.0 / (1.0 + np.exp(-score / 100.0))
    is_crash_warning = prob > 0.5
    return is_crash_warning, prob


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE E CAPSTONE: REAL-TIME EDGE AI TELEMETRY ENGINE")
    print("=========================================================\n")
    
    # Gói tin nhị phân nguy hiểm: Header=0x4141, Roll=45°, Pitch=30°, Alt=2m, Battery=5.0%
    danger_packet = struct.pack('>HhhhfH', 0x4141, 45, 30, 2, 5.0, 0x9999)
    
    # Trọng số Int8 nén AI
    W_int8_weights = np.array([64, 40, -50, -100], dtype=np.int8)
    scale_factor = 0.05
    
    is_warning, probability = process_telemetry_packet_with_edge_ai(danger_packet, W_int8_weights, scale_factor)
    
    if is_warning is not None:
        print("1. KET QUA XU LY GOI TIN 16-BYTES BANG EDGE AI TREN THOI GIAN THUC:")
        print(f"   -> Xac suat Nguy co Su co  : {probability * 100:.1f}%")
        status = "CANH BAO CRASH: HA CANH KHAN CAP! RED" if is_warning else "AN TOAN GREEN"
        print(f"   -> Trang thai Bo nao Edge AI: {status}")
        
        # Kiểm tra tính chính xác (Gói nguy hiểm -> Cảnh báo True)
        assert is_warning == True and probability > 0.5, "Loi phan tich Edge AI Telemetry!"
        
        print("\n=========================================================")
        print("CHUC MUNG TRO DA HOAN THANH TOAN BO CHUOI CUA MODULE E: EDGE AI!")
        print("=========================================================")
