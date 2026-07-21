"""
================================================================================
          SPEEDRUN CAPSTONE: DRONE FLIGHT CONTROLLER & STATE ENGINE
================================================================================
"""

import asyncio
from typing import List, Optional
from protocol import TelemetryFrame, unpack_telemetry, pack_telemetry, HEADER_MAGIC

class DroneStateEngine:
    """Bộ não quản lý trạng thái bay và giám sát an toàn của Drone"""
    def __init__(self, drone_id: str):
        self.drone_id = drone_id
        self.current_frame: Optional[TelemetryFrame] = None
        self.telemetry_history: List[TelemetryFrame] = []
        self.is_armed: bool = False
        self.warnings: List[str] = []

    def arm(self):
        """Bật nguồn động cơ (ARM)"""
        self.is_armed = True
        print(f"[ENGINE] Drone {self.drone_id} đã BẬT ĐỘNG CƠ (ARMED)!")

    def disarm(self):
        """Tắt nguồn động cơ (DISARM)"""
        self.is_armed = False
        print(f"[ENGINE] Drone {self.drone_id} đã TẮT ĐỘNG CƠ (DISARMED)!")

    def process_binary_packet(self, packet_bytes: bytes) -> TelemetryFrame:
        """Nhận gói tin 16-Bytes nhị phân thô, giải mã và cập nhật State"""
        frame = unpack_telemetry(packet_bytes)
        self.current_frame = frame
        self.telemetry_history.append(frame)
        
        # Giám sát an toàn phần cứng (Safety Monitor)
        self._check_safety(frame)
        return frame

    def _check_safety(self, frame: TelemetryFrame):
        """Quét các nguy cơ đe dọa an toàn bay"""
        self.warnings.clear()
        
        # 1. Cảnh báo Pin yếu (< 20%)
        if frame.battery < 20:
            self.warnings.append("⚠️ NGUY HIỂM: PIN YẾU DƯỚI 20%!")
            
        # 2. Cảnh báo Rơi tự do (Độ cao < 2m khi đang ARMED)
        if self.is_armed and frame.altitude < 2.0:
            self.warnings.append("⚠️ CẢNH BÁO: NGUY CƠ VA CHẠM MẶT ĐẤT!")
            
        # 3. Cảnh báo Lật nghiêng quá mức (Roll/Pitch > 450 -> 45.0°)
        if abs(frame.roll) > 450 or abs(frame.pitch) > 450:
            self.warnings.append("⚠️ CẢNH BÁO: NGIÊNG QUÁ MỨC (MẤT BẰNG)!")

    def get_dashboard_status(self) -> str:
        """Xuất bảng điều khiển trạng thái cho Trạm mặt đất"""
        if not self.current_frame:
            return f"Drone {self.drone_id}: CHƯA CÓ TÍN HIỆU TELEMETRY"
            
        f = self.current_frame
        status_str = (
            f"\n=== DASHBOARD DRONE [{self.drone_id}] ===\n"
            f"Trạng thái Động cơ: {'ARMED 🟢' if self.is_armed else 'DISARMED 🔴'}\n"
            f"Độ cao: {f.altitude:.2f} m\n"
            f"Góc nghiêng (Roll/Pitch/Yaw): {f.roll/10:.1f}° / {f.pitch/10:.1f}° / {f.yaw/10:.1f}°\n"
            f"Dung lượng Pin: {f.battery}%\n"
        )
        if self.warnings:
            status_str += "CẢNH BÁO HỆ THỐNG:\n" + "\n".join(self.warnings) + "\n"
        status_str += "===================================\n"
        return status_str
