"""
================================================================================
          MODULE AI: EMBEDDED DSP ADAPTIVE FILTERING & NOISE CANCELLATION
              MILESTONE AI.4: CAPSTONE FULL REAL-TIME DSP ANC ENGINE
================================================================================

KIẾN TRÚC HỆ THỐNG TRIỆT TIÊU TIẾNG ỒN CHỦ ĐỘNG (ACTIVE NOISE CONTROL - ANC ENGINE):
Trong các hệ thống nhúng thời gian thực (như mũ bay phi công tiêm kích F-35, tai nghe
chống ồn máy bay không người lái drone VTOL), động cơ sinh ra cả nhiễu dải hẹp (hài âm
cánh quạt) và nhiễu dải rộng (luồng gió xé).

HỆ THỐNG DSP ANC ENGINE TÍCH HỢP ĐẦY ĐỦ 4 KHỐI:
1. Bộ đệm vòng Circular Buffer tối ưu bộ nhớ đệm SRAM nhúng.
2. Bộ phát hiện tiếng nói Voice Activity Detector (VAD) dựa trên tỷ số năng lượng tức thời:
   - Nếu năng lượng micro chính vượt ngưỡng: Đóng băng cập nhật W để tránh méo giọng nói.
   - Nếu trong trạng thái im lặng/chỉ có ồn: Cho phép NLMS cập nhật nhanh.
3. Bộ lọc thích nghi Normalized LMS (NLMS) bậc cao khử hài âm động cơ.
4. Bộ giám sát vi sai âm học (SNR Improvement & dB Attenuation Telemetry).

CÔNG THỨC TOÁN HỌC DẠNG ASCII TEXT:
- Năng lượng khung tín hiệu:
  E_frame = sum(x[n]^2) / N

- Tỷ lệ suy giảm nhiễu (Noise Attenuation Ratio):
                          P_noisy
  Attenuation_dB = 10 * log10 ─────────
                          P_clean
"""

import numpy as np

class DualMicPowerRatioVAD:
    """
    Bộ phát hiện giọng nói tỷ số công suất 2 Micro (Dual-Mic Power Ratio VAD):
    - Tích hợp bộ đếm trễ (Hangover Timer) để giữ trạng thái khi giọng nói đi qua điểm 0 (zero-crossing)
    """
    def __init__(self, frame_size: int = 16, ratio_threshold: float = 0.65, hangover_frames: int = 70):
        self.frame_size = frame_size
        self.threshold = ratio_threshold
        self.hangover_frames = hangover_frames
        self.hangover_count = 0
        self.primary_history = []
        self.ref_history = []

    def is_speech_active(self, primary_sample: float, ref_sample: float) -> bool:
        self.primary_history.append(primary_sample)
        self.ref_history.append(ref_sample)
        if len(self.primary_history) > self.frame_size:
            self.primary_history.pop(0)
            self.ref_history.pop(0)

        if len(self.primary_history) < self.frame_size:
            return False

        p_primary = sum(s * s for s in self.primary_history) / self.frame_size
        p_ref = sum(s * s for s in self.ref_history) / self.frame_size
        ratio = p_primary / (p_ref + 1e-6)

        if ratio > self.threshold:
            self.hangover_count = self.hangover_frames
            return True
        elif self.hangover_count > 0:
            self.hangover_count -= 1
            return True
        return False


class RealtimeDSPEngineANC:
    """
    Trọng tâm Capstone: Động cơ xử lý tín hiệu số DSP khử nhiễu chủ động thời gian thực
    """
    def __init__(self, filter_order: int = 12, mu_step: float = 0.25, eps: float = 1e-5):
        self.order = filter_order
        self.mu = mu_step
        self.eps = eps
        self.weights = np.zeros(filter_order, dtype=np.float32)
        self.ref_buffer = np.zeros(filter_order, dtype=np.float32)
        self.vad = DualMicPowerRatioVAD(frame_size=16, ratio_threshold=0.60, hangover_frames=80)

    def process_sample(self, primary_mic: float, ref_noise_mic: float) -> dict:
        """
        Xử lý từng mẫu âm thanh vào từ ADC phần cứng:
        - primary_mic: Tín hiệu tại tai nghe / micro đàm thoại (chứa giọng nói + ồn dội)
        - ref_noise_mic: Tín hiệu tại vỏ động cơ / ngoài tai nghe (nhiễu tham chiếu)
        """
        # 1. Đẩy mẫu vào bộ đệm vòng
        self.ref_buffer[1:] = self.ref_buffer[:-1]
        self.ref_buffer[0] = ref_noise_mic

        # 2. Ước lượng tín hiệu tiếng ồn dội vào vị trí nghe
        estimated_noise = float(np.dot(self.weights, self.ref_buffer))

        # 3. Tính tín hiệu âm thanh sạch (Anti-noise cancellation)
        cleaned_signal = float(primary_mic - estimated_noise)

        # 4. Kiểm tra VAD để quyết định cập nhật thích nghi
        speech_active = self.vad.is_speech_active(primary_mic, ref_noise_mic)

        # 5. Cập nhật NLMS khi không có giọng nói để bảo vệ chống méo tiếng
        if not speech_active:
            energy = float(np.dot(self.ref_buffer, self.ref_buffer))
            norm_step = self.mu / (self.eps + energy)
            self.weights += norm_step * cleaned_signal * self.ref_buffer

        return {
            "cleaned_signal": cleaned_signal,
            "estimated_noise": estimated_noise,
            "speech_active": speech_active
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: EMBEDDED DSP REAL-TIME ACTIVE NOISE CONTROL")
    print("=========================================================\n")

    dsp_engine = RealtimeDSPEngineANC(filter_order=10, mu_step=0.3)

    # Mo phong kenh truyen am hoc khong gian (Acoustic Impulse Response)
    true_acoustic_path = np.array([0.05, 0.35, 0.45, -0.25, 0.15, -0.08, 0.04, -0.02, 0.01, -0.005], dtype=np.float32)
    path_delay_buffer = np.zeros(10, dtype=np.float32)

    n_samples = 600
    noisy_history = []
    cleaned_history = []
    clean_voice_truth = []

    np.random.seed(42)

    # Giai doan 1 (0 -> 250): Khoi tao he thong va thich nghi triet de tieng on dong co
    # Giai doan 2 (250 -> 600): Phi cong bat dau dam thoai voi trung tam dieu khien bay
    for n in range(n_samples):
        # Tieng on dong co canh quat drone: Ket hop song co ban 120Hz + hai am 240Hz + gio trang
        noise_source = float(np.sin(0.12 * np.pi * n) + 0.4 * np.sin(0.24 * np.pi * n) + 0.1 * np.random.randn())

        # Tieng on truyen qua khong gian vao micro chinh
        path_delay_buffer[1:] = path_delay_buffer[:-1]
        path_delay_buffer[0] = noise_source
        ambient_noise_at_pilot = float(np.dot(true_acoustic_path, path_delay_buffer))

        # Giong noi thuc su cua phi cong
        pilot_voice = float(1.2 * np.sin(0.03 * np.pi * n)) if n >= 250 else 0.0

        # Micro chinh thu toan bo
        mic_input = pilot_voice + ambient_noise_at_pilot

        # Xu ly thoi gian thuc boi DSP Engine
        telemetry = dsp_engine.process_sample(primary_mic=mic_input, ref_noise_mic=noise_source)

        noisy_history.append(mic_input)
        cleaned_history.append(telemetry["cleaned_signal"])
        clean_voice_truth.append(pilot_voice)

    # Kiem tra do suy giam nhiễu truoc khi phi cong noi (mẫu 150 -> 240)
    pre_speech_slice = slice(150, 240)
    raw_noise_seg = np.array(noisy_history)[pre_speech_slice]
    filtered_noise_seg = np.array(cleaned_history)[pre_speech_slice]

    p_raw = float(np.mean(raw_noise_seg ** 2))
    p_filtered = float(np.mean(filtered_noise_seg ** 2))
    attenuation_db = float(10 * np.log10(p_raw / (p_filtered + 1e-12)))

    # Kiem tra bao toan tin hieu giong noi sau khi co hoi thoai (mẫu 350 -> 550)
    speech_slice = slice(350, 550)
    recovered_speech = np.array(cleaned_history)[speech_slice]
    original_speech = np.array(clean_voice_truth)[speech_slice]
    speech_mse = float(np.mean((recovered_speech - original_speech) ** 2))

    print("1. TELEMETRY HIEN TRUONG - HE THONG KHU TIENG ON DSP:")
    print(f"   -> Cong suat tieng on ban dau            : {p_raw:.5f}")
    print(f"   -> Cong suat tieng on con lai sau loc    : {p_filtered:.6f}")
    print(f"   -> Muc do giam on thuc te (Attenuation)  : {attenuation_db:.2f} dB")
    print(f"   -> Sai so giong noi phuc hoi (MSE)       : {speech_mse:.6f}")

    assert attenuation_db > 18.0, "Attenuation DB chua dat muc tieu he thong ANC Capstone!"
    assert speech_mse < 0.05, "Giong noi phi cong bi meo qua muc cho phep!"
    print("\n[THANH CONG] CAPSTONE DSP ANC ENGINE HOAN TAT XUAT SAC CHI TIEU EMBEDDED SYSTEMS!")
