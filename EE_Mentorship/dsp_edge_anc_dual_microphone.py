"""
================================================================================
          MODULE AI: EMBEDDED DSP ADAPTIVE FILTERING & NOISE CANCELLATION
              MILESTONE AI.3: HỆ THỐNG KHỬ TIẾNG ỒN CHỦ ĐỘNG DUAL-MICROPHONE (ANC)
================================================================================

NGUYÊN LÝ HOẠT ĐỘNG CỦA HỆ THỐNG ANC 2 MICROPHONE TRÊN DRONE / TAI NGHE CHỐNG ỒN:
1. Micro chính (Primary Mic - d[n]):
   Đặt gần miệng phi công hoặc cảm biến âm thanh buồng lái.
   Thu nhận tín hiệu hỗn hợp: d[n] = s[n] + n1[n]
   - s[n]  : Giọng nói hữu ích (Speech signal)
   - n1[n] : Tiếng ồn cánh quạt sau khi truyền qua không gian (Acoustic Path H)

2. Micro tham chiếu (Reference Mic - x[n]):
   Đặt sát động cơ drone để thu riêng tiếng ồn nguồn: x[n] = n0[n]

3. Bộ lọc thích nghi (Adaptive Canceller - W):
   - Đầu vào bộ lọc: x[n]
   - Đầu ra ước lượng tiếng ồn dội vào micro chính: y[n] = W^T * X[n]
   - Tín hiệu âm thanh sau khử ồn:
     e[n] = d[n] - y[n] = s[n] + (n1[n] - y[n])

4. Khi bộ lọc hội tụ (W tiến tới hàm truyền âm học H):
   y[n] ~ n1[n]  ===>  e[n] ~ s[n] (Triệt tiêu toàn bộ tiếng ồn, giữ nguyên giọng nói!)

SƠ ĐỒ KHỐI ASCII:
                 ┌──────────────────┐
  Tieng on x[n] ─┤ Acoustic Path H  ├──> n1[n] ───(+)──> d[n]
                 └──────────────────┘              ▲
                                            s[n] ──┘ (Giong noi)
                 ┌──────────────────┐
  Tieng on x[n] ─┤ Adaptive Filter W├──> y[n] ───(-)
                 └──────────────────┘              ▲
                                                   │
                                     e[n] = s[n] ──┴─> [RA LOA / AUDIO OUT]
"""

import numpy as np

class DualMicActiveNoiseCanceller:
    def __init__(self, filter_order: int = 16, mu_step: float = 0.2, eps: float = 1e-5):
        self.order = filter_order
        self.mu = mu_step
        self.eps = eps
        self.weights = np.zeros(filter_order, dtype=np.float32)
        self.buffer = np.zeros(filter_order, dtype=np.float32)

    def process_frame(self, primary_d: float, reference_x: float, adapt: bool = True) -> tuple:
        """
        Xử lý 1 mẫu âm thanh thời gian thực từ 2 micro:
        - primary_d: Tín hiệu micro chính (giọng nói + nhiễu dội)
        - reference_x: Tín hiệu micro phụ (nhiễu động cơ thuần túy)
        - adapt: Cho phép cập nhật trọng số (đóng băng khi phi công đang nói để tránh méo tiếng)
        Trả về:
        - cleaned_speech: e[n] tín hiệu giọng nói sau khi loại bỏ tiếng ồn
        - estimated_noise: y[n] ước lượng tiếng ồn đã được triệt tiêu
        """
        # Cập nhật buffer tham chiếu
        self.buffer[1:] = self.buffer[:-1]
        self.buffer[0] = reference_x

        # Ước lượng nhiễu tại micro chính
        estimated_noise = float(np.dot(self.weights, self.buffer))

        # Khử nhiễu: Lấy tín hiệu micro chính trừ đi ước lượng nhiễu
        cleaned_speech = float(primary_d - estimated_noise)

        # Cập nhật trọng số theo NLMS nếu adapt=True
        if adapt:
            energy = float(np.dot(self.buffer, self.buffer))
            step = self.mu / (self.eps + energy)
            self.weights += step * cleaned_speech * self.buffer

        return cleaned_speech, estimated_noise


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: DUAL-MICROPHONE ACTIVE NOISE CANCELLER")
    print("=========================================================\n")

    canceller = DualMicActiveNoiseCanceller(filter_order=8, mu_step=0.3)

    # Đường truyền âm học thực tế từ động cơ tới micro chính
    acoustic_path = np.array([0.0, 0.4, 0.3, -0.2, 0.1, 0.05, -0.02, 0.01], dtype=np.float32)
    acoustic_buffer = np.zeros(8, dtype=np.float32)

    np.random.seed(100)
    total_samples = 400

    speech_record = []
    noisy_mic_record = []
    cleaned_record = []

    for n in range(total_samples):
        # Tiếng ồn động cơ (nhiều hài âm tần số cao)
        motor_noise = float(np.sin(0.15 * np.pi * n) + 0.5 * np.cos(0.4 * np.pi * n))

        # Tiếng ồn truyền qua không gian dội vào micro chính
        acoustic_buffer[1:] = acoustic_buffer[:-1]
        acoustic_buffer[0] = motor_noise
        noise_at_mic1 = float(np.dot(acoustic_path, acoustic_buffer))

        # Giọng nói phi công (bắt đầu nói từ mẫu 150 trở đi)
        pilot_speech = float(0.8 * np.sin(0.04 * np.pi * n)) if n >= 150 else 0.0

        # Micro chính thu cả giọng nói + tiếng ồn
        primary_signal = pilot_speech + noise_at_mic1

        # Voice Activity Detection (VAD): Dong bang cap nhat khi co giong noi de chong meo tieng
        is_speech = (n >= 150)
        clean_out, est_noise = canceller.process_frame(
            primary_d=primary_signal, reference_x=motor_noise, adapt=(not is_speech)
        )

        speech_record.append(pilot_speech)
        noisy_mic_record.append(primary_signal)
        cleaned_record.append(clean_out)

    # Đo SNR cải thiện sau khi hội tụ (từ mẫu 200 đến 400)
    eval_slice = slice(200, 400)
    true_speech = np.array(speech_record)[eval_slice]
    raw_mic = np.array(noisy_mic_record)[eval_slice]
    cleaned_out = np.array(cleaned_record)[eval_slice]

    noise_raw_power = np.mean((raw_mic - true_speech) ** 2)
    residual_noise_power = np.mean((cleaned_out - true_speech) ** 2)
    noise_reduction_db = 10 * np.log10(noise_raw_power / (residual_noise_power + 1e-9))

    print("1. DANH GIA HIEU QUA KHU NHIEU (NOISE REDUCTION RATIO):")
    print(f"   -> Cong suat tieng on truoc khi loc : {noise_raw_power:.5f}")
    print(f"   -> Cong suat tieng on con lai       : {residual_noise_power:.6f}")
    print(f"   -> Do giam on dat duoc (dB)         : {noise_reduction_db:.2f} dB (Tieu chuan tai nghe ANC > 15dB)")
    print(f"   -> Sai so giua giong noi va am da loc: {np.max(np.abs(cleaned_out - true_speech)):.4f}")

    assert noise_reduction_db > 12.0, "Hieu qua giam tieng on chua dat chuan ANC!"
    print("\n[THANH CONG] HE THONG DUAL-MIC ANC DA TRIET TIEU TIENG ON VA BAO VE GIONG NOI PHI CONG!")
