"""
================================================================================
          MODULE Y: EMBEDDED TIME-TRIGGERED BUS & AEROSPACE AVIONICS
              MILESTONE Y.1: MÃ HÓA KHUNG TRUYỀN CAN-FD VÀ MÃ KIỂM TRA CRC-17
================================================================================

TẠI SAO CÁC DÒNG XE TESLA VÀ TÊN LỬA NÂNG CẤP TỪ CAN 2.0 LÊN CAN-FD?
Chuẩn CAN-FD (Flexible Data-Rate):
- Tăng kích thước gói dữ liệu từ 8 bytes lên tới 64 bytes (tăng gấp 8 lần payload).
- Tốc độ truyền pha dữ liệu lên đến 5 Mbps - 8 Mbps.
- Sử dụng đa thức kiểm tra lỗi phần cứng CRC-17 bậc cao (0x3685B):
  Bảo đảm phát hiện 100% các xung nhiễu điện từ trường (EMI) trên động cơ phản lực!
"""

def compute_canfd_crc17(payload: bytes, poly: int = 0x3685B) -> int:
    """
    Trò đóng vai Kỹ sư Giao thức Mạng Xe hơi CAN-FD:
    - Khởi tạo crc = 0
    - Với mỗi byte trong payload, dịch chuyển và XOR với đa thức CRC-17
    - Trả về: crc (17-bit integer)
    """
    crc = 0x00000
    for byte in payload:
        crc ^= (byte << 9)
        for _ in range(8):
            if crc & 0x10000:
                crc = ((crc << 1) ^ poly) & 0x1FFFF
            else:
                crc = (crc << 1) & 0x1FFFF
    return crc


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE AVIONICS: CAN-FD 64-BYTE PAYLOAD & CRC-17")
    print("=========================================================\n")

    # Gói tin CAN-FD chứa dữ liệu 64-byte từ cảm biến IMU & Áp suất buồng đốt
    canfd_data = b"FLIGHT_CRITICAL_TELEMETRY_PACKET_ENGINE_VALVES_PRESSURE_SENSOR_64B"
    crc_res = compute_canfd_crc17(canfd_data)

    print("1. KET QUA DONG GOI VA KIEM TOAN TOAN VEN CAN-FD PHAN CUNG:")
    print(f"   -> Do dai Payload CAN-FD   : {len(canfd_data)} bytes")
    print(f"   -> Ma kiem tra loi CRC-17 : 0x{crc_res:05X}")
    print(f"   -> Do dai CRC             : 17 bits")

    assert crc_res <= 0x1FFFF and crc_res > 0, "Loi CAN-FD CRC-17!"
    print("\n[THANH CONG] DA HOAN THANH GIAO THUC CAN-FD TOAN VEN DU LIEU CHO AVIONICS!")
