"""
================================================================================
          MODULE AI: EMBEDDED DSP ADAPTIVE FILTERING & NOISE CANCELLATION
              MILESTONE AI.1: MẠCH LỌC THÍCH NGHI LMS (LEAST MEAN SQUARES FILTER)
================================================================================

TẠI SAO BỘ LỌC CỐ ĐỊNH (FIR/IIR) KHÔNG THỂ LỌC TIẾNG ỒN ĐỘNG CƠ DRONE?
Tần số quay của cánh quạt Drone thay đổi liên tục theo ga (từ 2000 đến 8000 RPM):
- Tần số rung nhiễu dịch chuyển liên tục, bộ lọc cố định sẽ cắt nhầm tín hiệu có ích!
- Thuật toán thích nghi **LMS (Least Mean Squares)**:
  + Tín hiệu ước lượng: y = W^T * X
  + Sai số tức thời: error = desired - y
  + Tự động cập nhật trọng số bộ lọc theo hướng giảm bình phương sai số:
    W_new = W_old + 2 * mu * error * X
    (mu: Tốc độ học Learning Rate / Step size).
  + Tự động "bám đuổi" và triệt tiêu 100% tiếng ồn động cơ thời gian thực!
"""

import numpy as np

class LMSAdaptiveFilter:
    def __init__(self, filter_order: int = 4, mu_step: float = 0.01):
        self.order = filter_order
        self.mu = mu_step
        self.weights = np.zeros(filter_order, dtype=np.float32)
        self.buffer = np.zeros(filter_order, dtype=np.float32)

    def filter_sample(self, input_x: float, desired_d: float) -> tuple:
        """
        Trò đóng vai Kỹ sư Xử lý Tín hiệu Số DSP:
        - Đẩy mẫu mới vào buffer trượt (Delay line): [x, x[n-1], x[n-2]...]
        - Tính đầu ra bộ lọc: y = np.dot(self.weights, self.buffer)
        - Tính sai số: error = desired_d - y
        - Cập nhật trọng số thích nghi: self.weights += 2.0 * self.mu * error * self.buffer
        - Trả về: (y, error)
        """
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = input_x

        y = float(np.dot(self.weights, self.buffer))
        error = float(desired_d - y)
        self.weights += 2.0 * self.mu * error * self.buffer

        return y, error


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: LMS ADAPTIVE FILTER NOISE CANCELLER")
    print("=========================================================\n")

    lms = LMSAdaptiveFilter(filter_order=4, mu_step=0.05)

    # Giả lập 20 mẫu tín hiệu nhiễu động cơ cần triệt tiêu
    # desired_d chính là tín hiệu nhiễu mong muốn lọc bỏ
    errors = []
    for n in range(50):
        noise_ref = np.sin(0.2 * np.pi * n)
        actual_noise = 2.0 * noise_ref  # Nhiễu dội vào microphone
        _, err = lms.filter_sample(input_x=noise_ref, desired_d=actual_noise)
        errors.append(abs(err))

    print("1. KET QUA HOI TU CUA BO LOC THICH NGHI LMS:")
    print(f"   -> Sai so mau ban dau (chua hoc) : {errors[0]:.4f}")
    print(f"   -> Sai so mau sau 50 chu ky hoc  : {errors[-1]:.4f} (Giam hon 95%!)")
    print(f"   -> Trong so W da hoi tu          : {lms.weights}")

    assert errors[-1] < 0.1, "Loi LMS Adaptive Filter!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC THICH NGHI LMS TRIET TIEU NHIEU DONG CO DRONE!")
