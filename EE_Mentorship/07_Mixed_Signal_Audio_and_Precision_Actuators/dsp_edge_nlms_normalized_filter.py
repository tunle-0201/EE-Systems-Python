"""
================================================================================
          MODULE AI: EMBEDDED DSP ADAPTIVE FILTERING & NOISE CANCELLATION
              MILESTONE AI.2: BỘ LỌC THÍCH NGHI CHUẨN HÓA NLMS (NORMALIZED LMS)
================================================================================

TẠI SAO BỘ LỌC LMS THƯỜNG DỄ BỊ BÙNG NỔ GRADIENT TRONG THỰC TẾ?
Khi biên độ tín hiệu vào x[n] tăng vọt (ví dụ drone rồ ga đột ngột):
- ||x[n]||^2 tăng mạnh -> bước nhảy 2 * mu * e[n] * x[n] trở nên quá lớn!
- Làm bộ lọc bị phân kỳ (Divergence / Gradient Explosion).

GIẢI PHÁP DSP: NORMALIZED LMS (NLMS)
Chuẩn hóa tốc độ học theo năng lượng tức thời của vector đầu vào:

                   mu
  mu_norm = ─────────────────
            eps + ||x[n]||^2

  W[n+1] = W[n] + mu_norm * e[n] * x[n]

Trong đó:
- ||x[n]||^2 = dot(buffer, buffer) : năng lượng tức thời của cửa sổ trượt
- eps : hệ số bảo vệ chống chia cho 0 khi im lặng (silent frame)
- mu : thông số điều chỉnh tốc độ hội tụ (0 < mu < 2)
"""

import numpy as np

class NLMSAdaptiveFilter:
    def __init__(self, filter_order: int = 8, mu_step: float = 0.5, eps: float = 1e-6):
        self.order = filter_order
        self.mu = mu_step
        self.eps = eps
        self.weights = np.zeros(filter_order, dtype=np.float32)
        self.buffer = np.zeros(filter_order, dtype=np.float32)

    def filter_sample(self, input_x: float, desired_d: float) -> tuple:
        """
        Thực hiện 1 chu kỳ lọc thích nghi Normalized LMS:
        1. Đẩy mẫu mới x vào buffer trượt (FIFO delay line)
        2. Tính tín hiệu lọc ước lượng: y = W^T * X = dot(weights, buffer)
        3. Tính sai số thời gian thực: e = desired_d - y
        4. Tính năng lượng tín hiệu buffer: energy = sum(buffer^2) = dot(buffer, buffer)
        5. Chuẩn hóa bước nhảy: mu_norm = mu / (eps + energy)
        6. Cập nhật vector trọng số: W = W + mu_norm * e * buffer
        7. Trả về: (y, e)
        """
        # 1. Cap nhat FIFO buffer
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = input_x

        # 2. Uoc luong tin hieu dau ra
        y = float(np.dot(self.weights, self.buffer))

        # 3. Tinh sai so e
        error = float(desired_d - y)

        # 4. Tinh nang luong cua buffer
        energy = float(np.dot(self.buffer, self.buffer))

        # 5. Buoc nhay chuan hoa
        mu_norm = self.mu / (self.eps + energy)

        # 6. Cap nhat trong so W
        self.weights += mu_norm * error * self.buffer

        return y, error


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: NORMALIZED LMS (NLMS) ADAPTIVE FILTER")
    print("=========================================================\n")

    # Thu nghiem voi tin hieu bien do thay doi dot ngot
    nlms = NLMSAdaptiveFilter(filter_order=6, mu_step=0.8, eps=1e-5)

    # He thong thuc te can mo phong (plant): h = [0.8, -0.5, 0.3, 0.1, -0.05, 0.02]
    h_plant = np.array([0.8, -0.5, 0.3, 0.1, -0.05, 0.02], dtype=np.float32)
    plant_buffer = np.zeros(6, dtype=np.float32)

    np.random.seed(42)
    n_samples = 200
    errors = []

    for n in range(n_samples):
        # Tin hieu vao co bien do tang vot o n > 100 de kiem tra tinh on dinh
        gain = 10.0 if n > 100 else 1.0
        x = float(gain * np.random.randn())

        # Dau ra cua he thong thuc te can theo doi
        plant_buffer[1:] = plant_buffer[:-1]
        plant_buffer[0] = x
        d = float(np.dot(h_plant, plant_buffer))

        _, err = nlms.filter_sample(input_x=x, desired_d=d)
        errors.append(abs(err))

    initial_error = np.mean(errors[:20])
    converged_error = np.mean(errors[170:])

    print("1. DANH GIA ON DINH VA TOC DO HOI TU CUA NLMS:")
    print(f"   -> Sai so trung binh ban dau      : {initial_error:.4f}")
    print(f"   -> Sai so sau khi bien do x10     : {converged_error:.6f}")
    print(f"   -> Trong so W thuc te hoi tu      : {np.round(nlms.weights, 3)}")
    print(f"   -> He so he thong goc h_plant     : {h_plant}")

    # Kiem tra hoi tu vuot troi va trong so khop voi plant
    assert converged_error < 0.05, "Loi NLMS khong hoi tu!"
    assert np.allclose(nlms.weights, h_plant, atol=0.05), "Trong so NLMS khong khop voi he thong thuc te!"
    print("\n[THANH CONG] BO LOC CHUAN HOA NLMS DA HOI TU CHINH XAC VA CHONG GRADIENT EXPLOSION!")
