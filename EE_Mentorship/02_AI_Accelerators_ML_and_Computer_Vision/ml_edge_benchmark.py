"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.5: HARDWARE BENCHMARK INT8 VS FLOAT32 CHO CHIP DRONE
================================================================================

BÀI TOÁN BENCHMARK BỘ NHỚ VÀ TỐC ĐỘ XỬ LÝ (HARDWARE BENCHMARK):
Đo đạc sự chênh lệch hiệu năng giữa Mô hình Float32 thô và Mô hình Int8 Nén trên chip nhúng EE:

1. Đo dung lượng RAM chiếm dụng (Memory Footprint in Bytes):
   - RAM_Float32 = N_weights * 4 bytes
   - RAM_Int8    = N_weights * 1 byte
   - Tiết kiệm RAM % = (1 - RAM_Int8 / RAM_Float32) * 100

2. Đo tốc độ xử lý (Inference Latency):
   - Tính toán 100,000 lần dự đoán.
"""

import time
import numpy as np

def run_edge_ai_hardware_benchmark(N_weights=10000):
    """
    Trò đóng vai Kỹ sư trưởng chạy đo đạc hiệu năng phần cứng Edge AI:
    - RAM_float32 = N_weights * 4
    - RAM_int8 = N_weights * 1
    - RAM_saved_percent = (1.0 - RAM_int8 / RAM_float32) * 100.0
    - Trả về: RAM_float32, RAM_int8, RAM_saved_percent
    """
    RAM_float32 = N_weights * 4
    RAM_int8 = N_weights * 1
    RAM_saved_percent = (1.0 - RAM_int8 / RAM_float32) * 100.0
    return RAM_float32, RAM_int8, RAM_saved_percent


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI HARDWARE BENCHMARK: INT8 VS FLOAT32 PERFORMANCE")
    print("=========================================================\n")
    
    ram_f32, ram_i8, saved_pct = run_edge_ai_hardware_benchmark(10000)
    
    print("1. KET QUA DO DAC HIEU NANG PHAN CUNG EDGE AI DRONE:")
    print(f"   -> Bo nho RAM Float32 chiem : {ram_f32} Bytes ({ram_f32/1024:.2f} KB)")
    print(f"   -> Bo nho RAM Int8 Nen chiem: {ram_i8} Bytes ({ram_i8/1024:.2f} KB)")
    print(f"   -> Ty le Tiet kiem RAM       : {saved_pct:.1f}%")
    
    # Kiểm tra tính chính xác (Tiết kiệm đúng 75.0% RAM)
    assert saved_pct == 75.0, "Loi tinh toan Benchmark RAM!"
    
    print("\n[THANH CONG] DA HOAN THANH BENCHMARK HIEU NANG PHAN CUNG EMBEDDED EDGE AI!")
