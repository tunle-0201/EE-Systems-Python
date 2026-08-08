"""
================================================================================
          SPEEDRUN CAPSTONE: AUTOMATED TEST SUITE (PYTEST)
================================================================================

Tệp kiểm thử tự động cho hệ thống Drone Telemetry & State Engine.
Chạy test bằng lệnh: pytest EE_Mentorship/drone_system/test_drone.py
"""

from EE_Mentorship.drone_system import engine
import pytest
import sys
import os

# Nạp thư mục chứa code vào Python path
sys.path.append(os.path.dirname(__file__))

from protocol import TelemetryFrame, pack_telemetry, unpack_telemetry, HEADER_MAGIC
from engine import DroneStateEngine


def test_binary_packet_pack_unpack_success():
    """Test 1: Kiểm tra tính toàn vẹn khi mã hóa và giải mã Binary Struct 16-Bytes"""
    original_frame = TelemetryFrame(
        header=HEADER_MAGIC,
        roll=150,       # 15.0°
        pitch=-50,      # -5.0°
        yaw=1800,       # 180.0°
        altitude=120.5, # 120.5m
        battery=85,     # 85%
        checksum=0
    )
    
    # 1. Mã hóa thành nhị phân
    binary_bytes = pack_telemetry(original_frame)
    assert len(binary_bytes) == 16, "Gói tin nhị phân phải đúng 16 Bytes!"
    
    # 2. Giải mã ngược lại
    unpacked_frame = unpack_telemetry(binary_bytes)
    
    # 3. Kiểm tra tính trùng khớp
    assert unpacked_frame.roll == 150
    assert unpacked_frame.pitch == -50
    assert unpacked_frame.yaw == 1800
    assert abs(unpacked_frame.altitude - 120.5) < 0.01
    assert unpacked_frame.battery == 85


def test_corrupted_checksum_rejection():
    """Test 2: Kiểm tra khả năng phát hiện và từ chối gói tin nhị phân bị nhiễu/lỗi Checksum"""
    frame = TelemetryFrame(HEADER_MAGIC, 0, 0, 0, 10.0, 50, 0)
    valid_bytes = pack_telemetry(frame)
    
    # Làm nhiễu 1 byte trong gói tin (Mô phỏng nhiễu từ trường vô tuyến)
    corrupted_bytes = bytearray(valid_bytes)
    corrupted_bytes[3] ^= 0xFF  # Biến đổi bit dữ liệu
    
    # Hệ thống bắt buộc phải quăng ra lỗi ValueError từ chối gói tin
    with pytest.raises(ValueError, match="Lỗi Checksum"):
        unpack_telemetry(bytes(corrupted_bytes))


def test_safety_monitor_low_battery_warning():
    """Test 3: Kiểm tra bộ não Safety Monitor phát hiện cảnh báo Pin yếu"""
    engine = DroneStateEngine(drone_id="ALPHA-1")
    engine.arm()
    
    # Gói tin với Pin yếu 15%
    low_bat_frame = TelemetryFrame(HEADER_MAGIC, 0, 0, 0, 50.0, 15, 0)
    packet_bytes = pack_telemetry(low_bat_frame)
    
    engine.process_binary_packet(packet_bytes)
    
    # Kiểm tra xem hệ thống có tự động bật Cảnh báo hay không
    assert len(engine.warnings) > 0
    assert "PIN YẾU DƯỚI 20%" in engine.warnings[0]


def test_critical_battery_emergency_landing():
    engine = DroneStateEngine(drone_id="TEST-EMERGENCY")
    engine.arm()
    
    # Tạo gói tin pin cực yếu (5%)
    critical_frame = TelemetryFrame(HEADER_MAGIC, 0, 0, 0, 20.0, 5, 0)
    packet_bytes = pack_telemetry(critical_frame)
    
    # Nạp gói tin vào máy chủ
    engine.process_binary_packet(packet_bytes)
    
    # Bắt pytest kiểm tra tự động:
    assert engine.is_armed == False, "Động cơ phải tự động DISARM!"
    assert engine.is_emergency_landed == True, "Phải bật cờ hạ cánh khẩn cấp!"
    