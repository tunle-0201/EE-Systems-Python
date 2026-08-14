"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.1: NÉN MÔ HÌNH AI INT8 QUANTIZATION FOR CHIP NHÚNG
================================================================================

TẠI SAO CẦN QUANTIZATION TRÊN CHIP PHẦN CỨNG DRONE / EMBEDDED SYSTEMS?
Các chip vi xử lý nhúng (như STM32, ESP32, Jetson Nano):
- Không có GPU mạnh để xử lý số thực 32-bit (Float32).
- Kỹ sư Edge AI NÉN Trọng số từ Float32 (4 bytes) xuống Số nguyên Int8 (1 byte):
  -> Tiết kiệm 75% bộ nhớ RAM và tăng tốc 400%!

Công thức Nén Int8:
  scale = max(abs(W)) / 127.0
  W_int8 = np.round(W / scale).astype(np.int8)

Nhiệm vụ của Kỹ sư trưởng trong hàm `quantize_weights_int8(W)`:
1. Tính scale = np.max(np.abs(W)) / 127.0
2. Tính W_int8 = np.round(W / scale).astype(np.int8)
3. Trả về: W_int8, scale
"""

import numpy as np

def quantize_weights_int8(W):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Quantization từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - scale = np.max(np.abs(W)) / 127.0
    - W_int8 = np.round(W / scale).astype(np.int8)
    - Trả về: W_int8, scale
    """
    scale = np.max(np.abs(W)) / 127.0
    W_int8 = np.round(W / scale).astype(np.int8)
    return W_int8, scale


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: INT8 WEIGHT QUANTIZATION FOR EMBEDDED CHIPS")
    print("=========================================================\n")
    
    W_float32 = np.array([-2.5, 0.0, 1.25, 5.0])
    
    W_int8, scale_factor = quantize_weights_int8(W_float32)
    
    if W_int8 is not None:
        print("1. KET QUA NEN MO HINH AI INT8 CHO CHIP EMBEDDED:")
        print(f"   -> Trong so Float32 ban dau (4 Bytes/so) : {W_float32}")
        print(f"   -> Trong so Int8 sau nen (1 Byte/so)    : {W_int8}")
        print(f"   -> He so Ty le Nen (Scale Factor)       : {scale_factor:.4f}")
        
        # Kiểm tra tính chính xác (5.0 / (5.0/127) = 127)
        assert W_int8[3] == 127 and W_int8[0] == -64, "Loi nen Int8!"
        
        print("\n[THANH CONG] TRO DA NEN THANH CONG MO HINH AI TIET KIEM 75% RAM CHO DRONE!")
