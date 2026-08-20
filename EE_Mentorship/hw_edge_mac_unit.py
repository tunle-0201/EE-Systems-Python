"""
================================================================================
          MODULE J: EMBEDDED HARDWARE ACCELERATION & NPU ARCHITECTURE
              MILESTONE J.1: KHỐI PHẦN CỨNG NHÂN - CỘNG (MULTIPLY-ACCUMULATE MAC UNIT)
================================================================================

TẠI SAO KHỐI MAC LÀ TRÁI TIM CỦA MỌI CHIP AI (NPU, TPU, GPU)?
Trong Mạng Nơ-ron, 99% phép tính là:
  Output = X * W + b (Nhân X với W rồi Cộng dồn vào thanh ghi Tích lũy).
Khối phần cứng Multiply-Accumulate (MAC Unit) thực hiện phép tính:
  Accumulator = Accumulator + (Input * Weight)
trong đúng 1 chu kỳ xung nhịp Clock (1 Clock Cycle)!
"""

class HardwareMACUnit:
    def __init__(self):
        self.accumulator = 0.0
    
    def reset(self):
        self.accumulator = 0.0
    
    def process_mac(self, x_val: float, w_val: float) -> float:
        """
        Trò đóng vai Kỹ sư thiết kế chip EE lập trình khối MAC:
        - self.accumulator += x_val * w_val
        - Trả về: self.accumulator
        """
        self.accumulator += x_val * w_val
        return self.accumulator


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE AI: MULTIPLY-ACCUMULATE (MAC) UNIT SIMULATOR")
    print("=========================================================\n")
    
    mac = HardwareMACUnit()
    
    # Giả lập dòng tín hiệu cảm biến đi qua chip
    inputs = [2.0, 3.0, 4.0]
    weights = [0.5, -1.0, 2.0]
    
    # 2.0*0.5 + 3.0*(-1.0) + 4.0*2.0 = 1.0 - 3.0 + 8.0 = 6.0
    for x, w in zip(inputs, weights):
        mac.process_mac(x, w)
    
    print("1. KET QUA PHAN CUNG THANH GHI TICH LUY MAC ACCUMULATOR:")
    print(f"   -> Gia tri Tich luy sau 3 xung Clock : {mac.accumulator:.2f}")
    
    assert abs(mac.accumulator - 6.0) < 1e-5, "Loi khoi MAC Unit!"
    print("\n[THANH CONG] DA MO PHONG CHINH XAC NGUYEN LY MACH PHAN CUNG MAC UNIT TRONG CHIP AI!")
