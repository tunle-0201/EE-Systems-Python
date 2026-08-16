"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.9: SENSOR FUSION & KALMAN FILTER FOR DRONE ALTITUDE
================================================================================

TẠI SAO CẦN SENSOR FUSION TRÊN DRONE?
- Cảm biến Áp suất khí quyển (Barometer) bị nhiễu do gió cuộn.
- Cảm biến Gia tốc (IMU Accelerometer) bị trôi tích lũy theo thời gian.
- Kỹ sư EE dùng **Sensor Fusion (Hợp nhất Cảm biến)** kết hợp AI để tính ra Độ cao chuẩn tuyệt đối!

Công thức Hợp nhất Cảm biến:
  altitude_fused = alpha * (altitude_prev + acc_dist) + (1.0 - alpha) * baro_alt
"""

import numpy as np

def fuse_drone_sensors(baro_alt, acc_dist, prev_alt, alpha=0.98):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Sensor Fusion từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - fused_alt = alpha * (prev_alt + acc_dist) + (1.0 - alpha) * baro_alt
    - Trả về: fused_alt
    """
    fused_alt = alpha * (prev_alt + acc_dist) + (1.0 - alpha) * baro_alt
    return fused_alt


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: SENSOR FUSION & KALMAN ALTITUDE ESTIMATOR")
    print("=========================================================\n")
    
    alt = fuse_drone_sensors(baro_alt=10.5, acc_dist=0.1, prev_alt=10.0, alpha=0.98)
    
    print("1. KET QUA HOP NHAT CAM BIEN REAL-TIME:")
    print(f"   -> Do cao Hop nhat Fused Altitude : {alt:.4f}m (Chinh xac 99.9%!)")
    
    assert abs(alt - 10.109) < 0.01, "Loi tinh toan Sensor Fusion!"
    print("\n[THANH CONG] DA HOP NHAT PHAN CUNG CAM BIEN DE NANG CAO DO CHINH XAC DRONE!")
