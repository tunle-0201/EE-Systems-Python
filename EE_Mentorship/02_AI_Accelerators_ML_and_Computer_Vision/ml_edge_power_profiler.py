"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.11: MILLIWATT POWER PROFILER FOR DRONE EDGE AI
================================================================================

ĐO ĐẠC TIÊU THỤ NĂNG LƯỢNG PIN CỦA CHIP AI:
Đo công suất milliwatt (mW) và năng lượng Micro-Joules (uJ) cho 1 phép suy luận AI.

Công thức:
  energy_uJ = voltage_V * current_mA * time_ms
"""

import numpy as np

def profile_mcu_power_consumption(voltage_V=3.3, current_mA=45.0, inference_time_ms=2.5):
    """
    Trò đo đạc mức tiêu thụ pin của vi điều khiển cho 1 phép suy luận AI:
    - power_mW = voltage_V * current_mA
    - energy_uJ = power_mW * inference_time_ms
    - Trả về: power_mW, energy_uJ
    """
    power_mW = voltage_V * current_mA
    energy_uJ = power_mW * inference_time_ms
    return power_mW, energy_uJ


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: MILLIWATT POWER & ENERGY PROFILER")
    print("=========================================================\n")
    
    p_mw, e_uj = profile_mcu_power_consumption(3.3, 45.0, 2.5)
    
    print("1. KET QUA DO DAC CONG SUAT TIEU THU PIN:")
    print(f"   -> Cong suat Hoat dong MCU     : {p_mw:.2f} mW")
    print(f"   -> Nang luong 1 phep Inference : {e_uj:.2f} uJ (Sieu tiet kiem pin!)")
    
    assert abs(p_mw - 148.5) < 0.1, "Loi tinh toan Power Profiler!"
    print("\n[THANH CONG] DA DO DAC TIET KIEM PIN OPTIMIZED CHO DRONE EMBEDDED CHIP!")
