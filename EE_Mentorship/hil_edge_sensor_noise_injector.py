"""
================================================================================
          MODULE AG: HARDWARE-IN-THE-LOOP (HIL) & FLIGHT SIMULATION
              MILESTONE AG.2: MẠCH BƠM NHIỄU CẢM BIẾN HIL (IMU NOISE & DRIFT INJECTOR)
================================================================================

TẠI SAO PHẢI THỬ NGHIỆM PHẦN CỨNG BẰNG MÔ HÌNH HIL (HARDWARE-IN-THE-LOOP)?
Trước khi phóng tên lửa thật:
- Cắm máy tính điều khiển bay (Flight Computer) vào dàn máy giả lập HIL Testbench.
- Dàn HIL bơm tín hiệu cảm biến giả lập kèm các đặc tính nhiễu vật lý thực tế:
  + Nhiễu trắng Gauss (Gaussian White Noise): Rung động cơ học.
  + Độ trôi ngẫu nhiên (Random Walk Bias Drift): Trôi dạt cảm biến con quay hồi chuyển Gyroscope.
  + raw_measurement = true_physics_val + current_bias + white_noise
"""

import numpy as np

class HILSensorNoiseInjector:
    def __init__(self, white_noise_std: float = 0.05, bias_drift_std: float = 0.001):
        self.white_noise_std = white_noise_std
        self.bias_drift_std = bias_drift_std
        self.accumulated_bias = 0.0

    def inject_noise(self, true_value: float, seed: int = None) -> float:
        """
        Trò đóng vai Kỹ sư Kiểm thử HIL Testbench:
        - Cập nhật bias ngẫu nhiên (Random Walk): self.accumulated_bias += np.random.normal(0, self.bias_drift_std)
        - Tạo nhiễu trắng: noise = np.random.normal(0, self.white_noise_std)
        - Trả về: true_value + self.accumulated_bias + noise
        """
        if seed is not None:
            np.random.seed(seed)
            
        self.accumulated_bias += float(np.random.normal(0, self.bias_drift_std))
        white_noise = float(np.random.normal(0, self.white_noise_std))
        return true_value + self.accumulated_bias + white_noise


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE HIL: IMU NOISE & BIAS DRIFT INJECTOR")
    print("=========================================================\n")

    injector = HILSensorNoiseInjector(white_noise_std=0.1, bias_drift_std=0.01)
    
    # Giá trị gia tốc trọng trường thực tế = 9.81 m/s^2
    true_accel = 9.81
    noisy_readings = [injector.inject_noise(true_accel, seed=i) for i in range(5)]

    print("1. KET QUA BOM NHIEU VAT LY VAO CAM BIEN IMU TRONG PHONG THI NGHIEM:")
    print(f"   -> Gia tri vat ly thuc te : {true_accel} m/s2")
    print(f"   -> 5 gia tri do bom qua HIL: {[round(x, 3) for x in noisy_readings]}")
    print(f"   -> Bias drift tich luy    : {injector.accumulated_bias:.4f}")

    assert all(abs(x - true_accel) < 1.0 for x in noisy_readings), "Loi HIL Noise Injector!"
    print("\n[THANH CONG] DA HOAN THANH BO BOM NHIEU CAM BIEN HIL CHO DUC THAO PHAN CUNG BAY!")
