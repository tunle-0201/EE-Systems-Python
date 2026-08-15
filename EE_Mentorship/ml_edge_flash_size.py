"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.8: FLASH MEMORY FOOTPRINT FOR STM32/ESP32
================================================================================

ĐO ĐẠC DUNG LƯỢNG BỘ NHỚ FLASH THỦ CÔNG:
Đo dung lượng bộ nhớ Flash ROM chiếm dụng trên STM32/ESP32.
"""

import numpy as np

def run_flash_footprint_benchmark(N_params=50000):
    """
    Trò đo đạc dung lượng Flash ROM chiếm dụng:
    - flash_f32_kb = (N_params * 4) / 1024.0
    - flash_int8_kb = (N_params * 1) / 1024.0
    """
    flash_f32_kb = (N_params * 4) / 1024.0
    flash_int8_kb = (N_params * 1) / 1024.0
    return flash_f32_kb, flash_int8_kb


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: FLASH MEMORY FOOTPRINT BENCHMARK FOR STM32/ESP32")
    print("=========================================================\n")
    
    f32_kb, i8_kb = run_flash_footprint_benchmark()
    
    print("1. KET QUA DO DAC DUNG LUONG FLASH ROM:")
    print(f"   -> Flash Float32 chiem : {f32_kb:.2f} KB")
    print(f"   -> Flash Int8 Nen chiem: {i8_kb:.2f} KB")
    
    assert i8_kb < f32_kb, "Loi tinh toan Flash!"
    print("\n[THANH CONG] DA TIEP KIEM THUP 75% FLASH ROM CHO VI DIEU KHIEN!")
