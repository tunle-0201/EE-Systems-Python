"""
================================================================================
          SPEEDRUN CAPSTONE: DRONE TELEMETRY BINARY PROTOCOL
================================================================================

Định dạng Binary Struct gói tin Telemetry (Chuẩn 16 Bytes Big-Endian `>`):
 ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
 │ Header   │ Roll     │ Pitch    │ Yaw      │ Altitude │ Battery  │ Checksum │
 │ 2 bytes  │ 2 bytes  │ 2 bytes  │ 2 bytes  │ 4 bytes  │ 2 bytes  │ 2 bytes  │
 │ (0xAA55) │ (int16)  │ (int16)  │ (int16)  │ (float)  │ (uint16) │ (uint16) │
 └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
 Total: 2 + 2 + 2 + 2 + 4 + 2 + 2 = 16 Bytes.
"""

import struct
from dataclasses import dataclass

HEADER_MAGIC = 0xAA55

@dataclass
class TelemetryFrame:
    header: int
    roll: int       # Góc nghiêng ngang (signed int16: -1800 đến 1800 -> -180.0° đến 180.0°)
    pitch: int      # Góc nghiêng dọc (signed int16: -900 đến 900 -> -90.0° đến 90.0°)
    yaw: int        # Hướng quay (signed int16: 0 đến 3600 -> 0.0° đến 360.0°)
    altitude: float # Độ cao tính bằng mét (Float32: 4 bytes)
    battery: int    # Phần trăm pin (unsigned uint16: 0-100%)
    checksum: int   # Mã kiểm lỗi XOR (unsigned uint16: 2 bytes)

def calculate_checksum(data_bytes: bytes) -> int:
    """Tính mã kiểm lỗi Checksum đơn giản bằng phép XOR từng byte"""
    chk = 0
    for b in data_bytes:
        chk ^= b
    return chk

def pack_telemetry(frame: TelemetryFrame) -> bytes:
    """Mã hóa TelemetryFrame thành 16-Bytes nhị phân"""
    # 1. Đóng gói dữ liệu (HhhhfH = 14 bytes)
    # H: Header (uint16)
    # h: roll, pitch, yaw (int16 signed)
    # f: altitude (float32)
    # H: battery (uint16)
    raw = struct.pack(
        ">HhhhfH",
        HEADER_MAGIC,
        frame.roll,
        frame.pitch,
        frame.yaw,
        frame.altitude,
        frame.battery
    )
    # 2. Tính checksum trên 14 bytes đầu
    chk = calculate_checksum(raw)
    # 3. Đóng gói nốt checksum 2-bytes (H) vào cuối -> Tổng 16 bytes
    return raw + struct.pack(">H", chk)

def unpack_telemetry(packet_bytes: bytes) -> TelemetryFrame:
    """Giải mã 16-Bytes nhị phân về lại TelemetryFrame"""
    if len(packet_bytes) != 16:
        raise ValueError(f"Độ dài gói tin không hợp lệ: {len(packet_bytes)} bytes (Yêu cầu 16 bytes)")
    
    # 1. Kiểm tra Checksum 2 bytes cuối
    payload = packet_bytes[:14]
    expected_chk = struct.unpack(">H", packet_bytes[14:])[0]
    actual_chk = calculate_checksum(payload)
    
    if expected_chk != actual_chk:
        raise ValueError(f"Lỗi Checksum! Kỳ vọng {expected_chk}, thực tế {actual_chk}")
    
    # 2. Giải mã 14 bytes đầu
    header, roll, pitch, yaw, alt, bat = struct.unpack(">HhhhfH", payload)
    
    if header != HEADER_MAGIC:
        raise ValueError(f"Header ma thuật không hợp lệ: {hex(header)}")
        
    return TelemetryFrame(
        header=header,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
        altitude=alt,
        battery=bat,
        checksum=actual_chk
    )
