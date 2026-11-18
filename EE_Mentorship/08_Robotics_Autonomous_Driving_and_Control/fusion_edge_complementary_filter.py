"""
================================================================================
          MODULE N: SENSOR FUSION & 6-DOF ATTITUDE ESTIMATION
              MILESTONE N.1: BỘ LỌC PHÙ TRỢ COMPLEMENTARY FILTER (GYRO + ACCEL)
================================================================================

TẠI SAO CẦN COMPLEMENTARY FILTER ĐỂ ĐO GÓC NGHIÊNG DRONE?
- Cảm biến Gia tốc Accelerometer: Đo góc chính xác về lâu dài (Static Angle), nhưng bị nhiễu động học khi Drone rung.
- Cảm biến Con quay Gyroscope: Đo tốc độ quay cực nhanh và mượt, nhưng bị trôi góc theo thời gian (Drift).
- Bộ lọc Complementary Filter kết hợp ưu điểm của cả hai:

Sơ đồ khối dung hợp cảm biến bù trừ (Complementary Sensor Fusion Architecture):

  Gyroscope (Tốc độ quay deg/s) ──> [ Tích phân dt ] ──> [ High-Pass (* alpha) ] ──┐
                                                                                   ▼
                                                                                 [ + ] ──> Góc ước lượng (Angle)
                                                                                   ▲
  Accelerometer (Góc trọng lực) ─────────────────────────> [ Low-Pass (* 1-alpha)] ─┘

Công thức tính góc nghiêng (Dạng chữ phẳng):
  angle = alpha * (angle + gyro_rate * dt) + (1.0 - alpha) * accel_angle
"""

class ComplementaryFilter:
    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.angle = 0.0
        self.initialized = False
    
    def update(self, gyro_rate: float, accel_angle: float, dt=0.01) -> float:
        """
        Trò đóng vai Kỹ sư Sensor Fusion thiết kế bộ lọc Complementary Filter:
        - Khởi tạo góc ban đầu theo cảm biến gia tốc
        - self.angle = self.alpha * (self.angle + gyro_rate * dt) + (1.0 - self.alpha) * accel_angle
        - Trả về: self.angle
        """
        if not self.initialized:
            self.angle = accel_angle
            self.initialized = True
            return self.angle
        self.angle = self.alpha * (self.angle + gyro_rate * dt) + (1.0 - self.alpha) * accel_angle
        return self.angle


if __name__ == "__main__":
    print("=========================================================")
    print("   SENSOR FUSION: 6-DOF COMPLEMENTARY FILTER (IMU)")
    print("=========================================================\n")
    
    fusion = ComplementaryFilter(alpha=0.98)
    
    # Giả lập 50 chu kỳ cập nhật cảm biến khi Drone giữ thăng bằng tại góc 5.0 độ
    for _ in range(50):
        estimated_angle = fusion.update(gyro_rate=0.0, accel_angle=5.0, dt=0.01)
    
    print("1. KET QUA UOC LUONG GOC NGHIENG FUSION REAL-TIME:")
    print(f"   -> Goc nghieng sau loc Complementary : {estimated_angle:.2f} do")
    
    assert abs(estimated_angle - 5.0) < 0.5, "Loi Complementary Filter!"
    print("\n[THANH CONG] DA KET HOP HOAN HAO CAM BIEN GYRO VA GIA TOC BANG COMPLEMENTARY FILTER!")
