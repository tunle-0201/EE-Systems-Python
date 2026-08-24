"""
================================================================================
          MODULE M: EMBEDDED CAN-BUS & VEHICLE NETWORK PROTOCOLS
              MILESTONE M.1: ĐÓNG GÓI KHUNG TIN CHUẨN CAN-BUS 2.0A (11-BIT ID)
================================================================================

TẠI SAO CAN-BUS LÀ CHUẨN TRUYỀN THÔNG SỐ 1 TRONG Ô TÔ VÀ AEROSPACE (TESLA, BOEING)?
Chuẩn CAN-Bus (Controller Area Network) dùng 2 dây xoắn (CAN_H và CAN_L) chống nhiễu điện từ:
- Mỗi khung tin CAN gồm:
  + ID định danh 11-bit (Ví dụ 0x100: Motor Control, 0x200: Battery Status).
  + Chiều dài dữ liệu DLC (Data Length Code: 0..8 bytes).
  + Mảng dữ liệu tải Payload (tối đa 8 bytes).
"""

import struct

def encode_can_standard_frame(can_id: int, payload_bytes: bytes) -> bytes:
    """
    Trò đóng vai Kỹ sư phần cứng CAN-Bus:
    - can_id: 11-bit (0x000 đến 0x7FF)
    - payload_bytes: tối đa 8 bytes
    - DLC = len(payload_bytes)
    - header = struct.pack('>HB', can_id, DLC)
    - frame = header + payload_bytes
    - Trả về: frame
    """
    dlc = len(payload_bytes)
    header = struct.pack('>HB', can_id, dlc)
    frame = header + payload_bytes
    return frame


if __name__ == "__main__":
    print("=========================================================")
    print("   VEHICLE EE SYSTEMS: CAN-BUS 2.0A STANDARD FRAME PACKER")
    print("=========================================================\n")
    
    # Gói tin điều khiển Motor ESC 1: ID=0x120, Payload = 4 bytes (RPM = 5000)
    payload = struct.pack('>I', 5000)
    can_frame = encode_can_standard_frame(can_id=0x120, payload_bytes=payload)
    
    print("1. KET QUA DONG GOI KHUNG TIN CHUAN CAN-BUS REAL-TIME:")
    print(f"   -> Do dai Khung CAN Frame : {len(can_frame)} Bytes")
    print(f"   -> Du lieu Hex Header/DLC : 0x{can_frame[:3].hex().upper()}")
    
    assert len(can_frame) == 7 and can_frame[0] == 0x01 and can_frame[1] == 0x20, "Loi CAN Frame Encoder!"
    print("\n[THANH CONG] DA HOAN THANH CHUAN TRUYEN THONG KHUNG TIN CAN-BUS CHO O TO VA DRONE!")
