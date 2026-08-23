"""
================================================================================
          MODULE L: EMBEDDED DIGITAL SIGNAL PROCESSING (DSP) FOR DRONES
              MILESTONE L.2: PHÂN TÍCH PHỔ TẦN SỐ FFT (FAST FOURIER TRANSFORM)
================================================================================

TẠI SAO CẦN BIẾN ĐỔI FOURIER NHANH (FFT) ĐỂ BẮT LỖI CÁNH QUẠT DRONE?
Khi cánh quạt bị mẻ hoặc cong vênh:
- Nó tạo ra rung động cực mạnh ở đúng tần số quay chính (Peak Frequency).
- Thuật toán **FFT (Fast Fourier Transform)** chuyển tín hiệu từ Miền Thời gian (Time Domain) sang Miền Tần số (Frequency Domain).
- Phát hiện trước nguy cơ gãy cánh quạt để hạ cánh bảo trì!
"""

import numpy as np

def compute_fft_dominant_frequency(signal_samples, sampling_rate_hz=1000.0):
    """
    Trò đóng vai Kỹ sư DSP thiết kế bộ phân tích phổ FFT:
    - N = len(signal_samples)
    - fft_vals = np.abs(np.fft.rfft(signal_samples))
    - freqs = np.fft.rfftfreq(N, 1.0 / sampling_rate_hz)
    - peak_idx = np.argmax(fft_vals[1:]) + 1 # Bỏ thành phần DC 0Hz
    - Trả về: freqs[peak_idx], fft_vals[peak_idx]
    """
    N = len(signal_samples)
    fft_vals = np.abs(np.fft.rfft(signal_samples))
    freqs = np.fft.rfftfreq(N, 1.0 / sampling_rate_hz)
    peak_idx = np.argmax(fft_vals[1:]) + 1
    return freqs[peak_idx], fft_vals[peak_idx]


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED DSP: FFT FREQUENCY SPECTRUM ANALYZER")
    print("=========================================================\n")
    
    # Giả lập tín hiệu rung động 150 Hz của cánh quạt bị lỗi
    Fs = 1000.0
    t = np.linspace(0, 1.0, int(Fs), endpoint=False)
    vibration_signal = np.sin(2 * np.pi * 150.0 * t)
    
    peak_freq, peak_mag = compute_fft_dominant_frequency(vibration_signal, sampling_rate_hz=Fs)
    
    print("1. KET QUA PHAN TICH PHO TAN SO FFT REAL-TIME:")
    print(f"   -> Tan so rung dong manh nhat Peak : {peak_freq:.1f} Hz (Phat hien loi canh quat 150Hz!)")
    
    assert abs(peak_freq - 150.0) < 1.0, "Loi thuat toan FFT!"
    print("\n[THANH CONG] DA HOAN THANH PHAN TICH PHO FFT CHAN DOAN SU CO CO KHI CHO DRONE!")
