"""
================================================================================
          MODULE L CAPSTONE FINALE: HỆ THỐNG DSP CHẨN ĐOÁN SỨC KHỎE DRONE REAL-TIME
================================================================================

TÍCH HỢP TOÀN BỘ DSP: FIR FILTER + FFT SPECTRUM ANALYZER + IIR EMA FILTER
"""

from dsp_edge_fir_filter import DigitalFIRLowPassFilter
from dsp_edge_fft_vibration import compute_fft_dominant_frequency
from dsp_edge_moving_average_iir import ExponentialMovingAverageIIR
import numpy as np

def run_drone_dsp_diagnostics_pipeline():
    # 1. Lọc nhiễu cảm biến góc nghiêng bằng FIR
    fir = DigitalFIRLowPassFilter([0.33, 0.34, 0.33])
    fir_out = fir.process_sample(25.0)
    
    # 2. Phân tích phổ FFT phát hiện lỗi rung động
    t = np.linspace(0, 1.0, 500, endpoint=False)
    vib = np.sin(2 * np.pi * 80.0 * t)
    peak_f, peak_m = compute_fft_dominant_frequency(vib, sampling_rate_hz=500.0)
    
    # 3. Lọc dòng điện motor bằng IIR
    iir = ExponentialMovingAverageIIR(0.5)
    iir.process_sample(10.0)
    iir_out = iir.process_sample(20.0)
    
    return fir_out, peak_f, iir_out


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE L CAPSTONE: REAL-TIME DSP HEALTH MONITOR")
    print("=========================================================\n")
    
    fir_val, peak_freq, iir_val = run_drone_dsp_diagnostics_pipeline()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI EMBEDDED DSP PIPELINE:")
    print(f"   -> FIR Filter Gyro Output : {fir_val:.2f}")
    print(f"   -> FFT Propeller Frequency: {peak_freq:.1f} Hz")
    print(f"   -> IIR Motor Current Draw : {iir_val:.2f} A")
    
    assert abs(peak_freq - 80.0) < 1.0, "Loi Capstone DSP Pipeline!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE L: EMBEDDED DSP!")
    print("=========================================================")
