"""
================================================================================
          MODULE L: EMBEDDED DIGITAL SIGNAL PROCESSING (DSP) FOR DRONES
              MILESTONE L.3: MẠCH LỌC IIR (EXPONENTIAL MOVING AVERAGE FILTER)
================================================================================

TẠI SAO CẦN MẠCH LỌC SỐ IIR CHO VI ĐIỀU KHIỂN CÓ ÍT BỘ NHỚ RAM?
Khác với mạch FIR cần lưu trữ 50 mẫu trong mảng buffer:
- Mạch lọc số IIR (Infinite Impulse Response) chỉ cần **1 biến duy nhất trong RAM**!
- Công thức:
  output = alpha * raw_sample + (1.0 - alpha) * prev_output
- Cực kỳ nhẹ, xử lý trong đúng 2 lệnh vi xử lý!
"""

class ExponentialMovingAverageIIR:
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.prev_output = 0.0
        self.initialized = False
    
    def process_sample(self, raw_sample: float) -> float:
        if not self.initialized:
            self.prev_output = raw_sample
            self.initialized = True
            return raw_sample
        
        output = self.alpha * raw_sample + (1.0 - self.alpha) * self.prev_output
        self.prev_output = output
        return output


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: EXPONENTIAL MOVING AVERAGE (IIR) FILTER")
    print("=========================================================\n")
    
    ema = ExponentialMovingAverageIIR(alpha=0.2)
    s1 = ema.process_sample(100.0)
    s2 = ema.process_sample(110.0) # 0.2*110 + 0.8*100 = 22 + 80 = 102.0
    
    print("1. KET QUA LOC DU LIEU SIEU NHE IIR REAL-TIME:")
    print(f"   -> Tin hieu sau loc IIR Filter Output : {s2:.2f}")
    
    assert abs(s2 - 102.0) < 1e-5, "Loi mach loc IIR!"
    print("\n[THANH CONG] DA HOAN THANH MACH LOC SO IIR SIEU TIET KIEM RAM CHO VI DIEU KHIEN!")
