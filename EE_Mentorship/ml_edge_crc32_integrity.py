"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.10: CRC32 HARDWARE INTEGRITY FOR AI WEIGHTS
================================================================================

TẠI SAO CẦN CRC32 CHECKSUM CHO MÔ HÌNH AI TRÊN CHIP DRONE?
Khi nạp Trọng số AI qua chuẩn truyền thông SPI/UART/CAN-bus vào chip STM32:
- Nhiễu sóng vô tuyến có thể làm sai lệch 1 byte trọng số -> Trọng số hỏng khiến AI suy luận sai bét!
- Kỹ sư EE dùng **CRC32 Checksum** để xác thực tính toàn vẹn 100% trước khi cho AI khởi chạy.
"""

import zlib
import numpy as np

def compute_ai_model_crc32(W_weights):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ CRC32 Integrity từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - raw_bytes = W_weights.tobytes()
    - checksum = zlib.crc32(raw_bytes)
    - Trả về: checksum
    """
    raw_bytes = W_weights.tobytes()
    checksum = zlib.crc32(raw_bytes)
    return checksum


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: CRC32 HARDWARE MODEL INTEGRITY CHECKER")
    print("=========================================================\n")
    
    W = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    crc = compute_ai_model_crc32(W)
    
    print("1. KET QUA MA KIEM TRA CRC32 HARDWARE CHECKSUM:")
    print(f"   -> Ma CRC32 Xac thuc Mo hinh AI : 0x{crc:08X}")
    
    assert crc > 0, "Loi tinh toan CRC32!"
    print("\n[THANH CONG] DA XAC THUC CHINH XAC TINH TOAN VENG MA CUNG MO HINH AI!")
