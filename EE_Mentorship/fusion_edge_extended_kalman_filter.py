"""
================================================================================
          MODULE N: SENSOR FUSION & 6-DOF ATTITUDE ESTIMATION
              MILESTONE N.2: BỘ LỌC KALMAN TỐI ƯU 1D (STATE ESTIMATION KALMAN FILTER)
================================================================================

TẠI SAO BỘ LỌC KALMAN LÀ TIÊU CHUẨN VÀNG TRONG HÀNG KHÔNG VŨ TRỤ (APOLLO, SPACEX)?
Kalman Filter dự đoán và cập nhật trạng thái tối ưu theo hiệp phương sai nhiễu:
1. Dự đoán (Predict): x_hat = x_hat, P = P + Q
2. Tính Kalman Gain: K = P / (P + R)
3. Cập nhật đo lường (Update): x_hat = x_hat + K * (measurement - x_hat)
4. Cập nhật hiệp phương sai: P = (1 - K) * P
"""

class Simple1DKalmanFilter:
    def __init__(self, process_noise_q=0.01, measurement_noise_r=0.1):
        self.q = process_noise_q
        self.r = measurement_noise_r
        self.x = 0.0 # Trạng thái ước lượng
        self.p = 1.0 # Hiệp phương sai sai số
    
    def update(self, measurement: float) -> float:
        # 1. Dự đoán
        self.p = self.p + self.q
        
        # 2. Hệ số Kalman Gain
        k = self.p / (self.p + self.r)
        
        # 3. Cập nhật trạng thái
        self.x = self.x + k * (measurement - self.x)
        
        # 4. Cập nhật hiệp phương sai
        self.p = (1.0 - k) * self.p
        
        return self.x


if __name__ == "__main__":
    print("=========================================================")
    print("   SENSOR FUSION: 1D OPTIMAL KALMAN FILTER (ALTITUDE)")
    print("=========================================================")
    
    kf = Simple1DKalmanFilter(process_noise_q=0.01, measurement_noise_r=0.5)
    
    # Giả lập 20 phép đo độ cao khí áp kế bị nhiễu quanh mức 10.0m
    measurements = [10.2, 9.8, 10.5, 9.7, 10.1, 10.0, 9.9, 10.3, 9.6, 10.2]
    
    for m in measurements:
        est_alt = kf.update(m)
    
    print("1. KET QUA UOC LUONG DO CAO KALMAN FILTER REAL-TIME:")
    print(f"   -> Do cao toi uu sau Kalman Filter : {est_alt:.2f} m")
    
    assert abs(est_alt - 10.0) < 0.3, "Loi Kalman Filter!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC KALMAN FILTER TOI UU TRIET TIEU NHIEU CAM BIEN!")
