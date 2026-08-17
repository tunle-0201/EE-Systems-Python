"""
================================================================================
          MODULE F: EMBEDDED REAL-TIME DRONE FLIGHT CONTROL & ROBOTICS
              MILESTONE F.1: THUẬT TOÁN ĐIỀU KHIỂN PID (CLOSED-LOOP PID CONTROLLER)
================================================================================

TẠI SAO CẦN THUẬT TOÁN ĐIỀU KHIỂN PID TRÊN DRONE?
Để giữ cho Drone cân bằng tuyệt đối khi có gió thổi cuộn:
1. P (Proportional - Tỷ lệ): Phản ứng mạnh dựa trên sai số góc nghiêng hiện tại.
2. I (Integral - Tích phân): Tích lũy sai số theo thời gian để triệt tiêu lệch tĩnh.
3. D (Derivative - Đạo hàm): Phản ứng với tốc độ thay đổi sai số để chống quá đà (Overshoot).

Công thức PID:
  output = Kp * error + Ki * integral + Kd * derivative
"""

import numpy as np

class PIDController:
    def __init__(self, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0.0
        self.integral = 0.0
    
    def compute(self, target, current, dt=0.01):
        error = target - current
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        self.prev_error = error
        
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        return output


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED SYSTEM: CLOSED-LOOP PID CONTROLLER")
    print("=========================================================\n")
    
    pid = PIDController(Kp=2.0, Ki=0.5, Kd=0.1)
    thrust_adjustment = pid.compute(target=0.0, current=5.0, dt=0.01)
    
    print("1. KET QUA PHAN UONG MACH DIEU KHIEN PID REAL-TIME:")
    print(f"   -> Tin hieu Dieu chinh Thrust : {thrust_adjustment:.2f}")
    
    assert thrust_adjustment < 0, "Loi mach PID!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN PID GIU CAN BANG CHO DRONE!")
