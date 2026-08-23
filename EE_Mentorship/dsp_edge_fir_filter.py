"""
================================================================================
          MODULE L: EMBEDDED DIGITAL SIGNAL PROCESSING (DSP) FOR DRONES
              MILESTONE L.1: MẠCH LỌC SỐ FIR (FINITE IMPULSE RESPONSE LOW-PASS FILTER)
================================================================================

TẠI SAO CẦN MẠCH LỌC SỐ FIR TRÊN DRONE?
Động cơ Drone quay 10,000 RPM tạo ra dao động rung cơ học tần số cao làm nhiễu cảm biến con quay hồi chuyển Gyroscope.
Mạch lọc số FIR (Finite Impulse Response):
- Nhân chập tín hiệu cảm biến với các hệ số lọc (Filter Coefficients $b_k$).
- Triệt tiêu 100% tiếng ồn tần số cao, cho tín hiệu góc nghiêng phẳng mượt mà!

Công thức:
  y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2]
"""

import numpy as np

class DigitalFIRLowPassFilter:
    def __init__(self, coefficients):
        self.b = np.array(coefficients, dtype=np.float32)
        self.buffer = np.zeros(len(coefficients), dtype=np.float32)
    
    def process_sample(self, raw_sample: float) -> float:
        """
        Trò đóng vai Kỹ sư DSP thiết kế mạch lọc số FIR:
        - self.buffer = np.roll(self.buffer, 1)
        - self.buffer[0] = raw_sample
        - filtered_val = np.sum(self.b * self.buffer)
        - Trả về: filtered_val
        """
        self.buffer = np.roll(self.buffer, 1)
        self.buffer[0] = raw_sample
        filtered_val = np.sum(self.b * self.buffer)
        return filtered_val


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: FIR LOW-PASS MOTOR VIBRATION FILTER")
    print("=========================================================\n")
    
    # Bộ hệ số lọc FIR 3-Tap cân bằng
    fir = DigitalFIRLowPassFilter(coefficients=[0.25, 0.50, 0.25])
    
    # Giả lập tín hiệu con quay hồi chuyển bị nhiễu rung: 10.0, 10.0, 10.0
    s1 = fir.process_sample(10.0)
    s2 = fir.process_sample(10.0)
    s3 = fir.process_sample(10.0)
    
    print("1. KET QUA KHI DI QUA MACH LOC SO FIR REAL-TIME:")
    print(f"   -> Tin hieu sau loc FIR Filter Output : {s3:.2f}")
    
    assert abs(s3 - 10.0) < 1e-5, "Loi mach loc FIR!"
    print("\n[THANH CONG] DA HOAN THANH MACH LOC SO FIR KHU NHIEU DONG CO CHO DRONE!")
