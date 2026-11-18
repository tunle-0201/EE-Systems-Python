"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 6: ĐÓNG GÓI DỮ LIỆU NHỊ PHÂN
                  MILESTONE 6.1: STRUCT PACK & UNPACK (ENDIANNESS)
================================================================================

Chào trò! Trong bài này, trò sẽ tự tay đóng gói một gói tin Telemetry cảm biến
vệ tinh từ dạng các con số thành dãy Bytes nhị phân thô 7-bytes.

Cấu trúc gói tin Telemetry (C-Struct):
1. Device ID   : 1 byte  (unsigned char) -> Ký hiệu format: 'B'
2. Temperature : 2 bytes (short int)     -> Ký hiệu format: 'h'
3. Voltage     : 4 bytes (float)         -> Ký hiệu format: 'f'

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1: Dùng `struct.pack()` mã hóa 3 thông số thành 7 bytes dạng Big-Endian (`>`).
2. Hoàn thành TODO 2: Dùng `struct.unpack()` giải mã 7 bytes nhận được về lại các con số ban đầu.
3. Chạy file bằng lệnh:
   $env:PYTHONIOENCODING="utf-8"; python EE_Mentorship/milestone_6_1_struct.py
"""

import struct

def pack_telemetry(device_id: int, temp: int, voltage: float) -> bytes:
    """
    TODO 1: Mã hóa 3 thông số thành gói tin nhị phân 7-bytes dạng Big-Endian.
    Chuỗi format cần dùng: ">Bhf"
    - '>' : Big-Endian
    - 'B' : device_id (1 byte)
    - 'h' : temp (2 bytes)
    - 'f' : voltage (4 bytes)
    
    Hãy dùng struct.pack(fmt, device_id, temp, voltage) và trả về kết quả bytes.
    """
    return struct.pack(">Bhf", device_id, temp, voltage)

def unpack_telemetry(raw_bytes: bytes) -> tuple:
    """
    TODO 2: Giải mã gói tin nhị phân 7-bytes Big-Endian về lại tuple (device_id, temp, voltage).
    Hãy dùng struct.unpack(fmt, raw_bytes) với cùng chuỗi format ">Bhf".
    """
    return struct.unpack(">Bhf", raw_bytes)


if __name__ == "__main__":
    # Dữ liệu đọc từ cảm biến phần cứng
    sensor_id = 42        # ID thiết bị (1 byte)
    temperature = -15     # Nhiệt độ vũ trụ -15 độ C (2 bytes)
    battery_volt = 3.65   # Điện áp pin 3.65V (4 bytes)

    print("--- BẮT ĐẦU ĐÓNG GÓI DỮ LIỆU CẢM BIẾN ---")
    print(f"Dữ liệu gốc: ID={sensor_id}, Temp={temperature}°C, Volt={battery_volt}V")

    # 1. Đóng gói thành nhị phân
    binary_packet = pack_telemetry(sensor_id, temperature, battery_volt)
    
    print(f"\n[VẬT LÝ] Gói tin nhị phân thô truyền qua cáp/sóng vô tuyến:")
    print(f"   -> Giá trị Bytes: {binary_packet}")
    print(f"   -> Độ dài gói tin: {len(binary_packet)} bytes (Chuẩn xác 7 bytes!)")
    print(f"   -> Hexdump từng byte trên RAM: {[hex(b) for b in binary_packet]}")

    # 2. Giải mã tại trạm mặt đất
    rec_id, rec_temp, rec_volt = unpack_telemetry(binary_packet)
    
    print(f"\n[TRẠM MẶT ĐẤT] Giải mã gói tin thành công:")
    print(f"   -> Device ID  : {rec_id}")
    print(f"   -> Temperature: {rec_temp}°C")
    print(f"   -> Voltage    : {rec_volt:.2f}V")

    # Kiểm tra tính chính xác
    assert rec_id == sensor_id, "Lỗi giải mã ID!"
    assert rec_temp == temperature, "Lỗi giải mã Nhiệt độ!"
    assert abs(rec_volt - battery_volt) < 0.01, "Lỗi giải mã Điện áp!"
    print("\n[HỆ THỐNG] THÔNG MẠCH NHỊ PHÂN THÀNH CÔNG 100%!")
