"""
================================================================================
          SPEEDRUN CAPSTONE: RUNNER HỆ THỐNG DRONE TELEMETRY
================================================================================

Chạy file này bằng lệnh:
$env:PYTHONIOENCODING="utf-8"; python EE_Mentorship/drone_system/main.py
"""

import time
import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.append(os.path.dirname(__file__))

from protocol import TelemetryFrame, pack_telemetry, HEADER_MAGIC
from engine import DroneStateEngine


def run_drone_simulation():
    print("=========================================================")
    print("   HỆ THỐNG ĐIỀU KHIỂN & KHỞI CHẠY TELEMETRY DRONE PHẦN CỨNG")
    print("=========================================================\n")
    
    # 1. Khởi tạo bộ não Trạm mặt đất
    drone = DroneStateEngine(drone_id="VANGUARD-01")
    drone.arm()  # Kích hoạt nguồn động cơ
    
    # 2. Mô phỏng Kịch bản 1: Bay bình thường ở độ cao 50m
    print("[TRẠM MẶT ĐẤT] Nhận Gói tin 1 (Bay ổn định)...")
    frame1 = TelemetryFrame(
        header=HEADER_MAGIC,
        roll=20,        # 2.0°
        pitch=10,       # 1.0°
        yaw=900,        # 90.0° (Hướng Đông)
        altitude=50.0,  # 50.0 mét
        battery=95,     # 95% Pin
        checksum=0
    )
    packet1_bytes = pack_telemetry(frame1)
    drone.process_binary_packet(packet1_bytes)
    print(drone.get_dashboard_status())
    time.sleep(1)
    
    # 3. Mô phỏng Kịch bản 2: Gặp gió mạnh, nghiêng lật 50° (Quá ngưỡng an toàn)
    print("[TRẠM MẶT ĐẤT] Nhận Gói tin 2 (Gió mạnh lật nghiêng)...")
    frame2 = TelemetryFrame(
        header=HEADER_MAGIC,
        roll=520,       # 52.0° (Lật nghiêng > 45°)
        pitch=-100,     # -10.0°
        yaw=950,        # 95.0°
        altitude=48.5,  # 48.5 mét
        battery=92,     # 92% Pin
        checksum=0
    )
    packet2_bytes = pack_telemetry(frame2)
    drone.process_binary_packet(packet2_bytes)
    print(drone.get_dashboard_status())
    time.sleep(1)

    # 4. Mô phỏng Kịch bản 3: Thảm họa cạn pin & Đang hạ cánh nguy hiểm
    print("[TRẠM MẶT ĐẤT] Nhận Gói tin 3 (Cảnh báo Cạn pin & Rơi)...")
    frame3 = TelemetryFrame(
        header=HEADER_MAGIC,
        roll=0,
        pitch=0,
        yaw=950,
        altitude=1.2,   # 1.2 mét (Quá thấp khi đang ARMED!)
        battery=12,     # 12% Pin (Yếu dưới 20%)
        checksum=0
    )
    packet3_bytes = pack_telemetry(frame3)
    drone.process_binary_packet(packet3_bytes)
    print(drone.get_dashboard_status())


if __name__ == "__main__":
    run_drone_simulation()
