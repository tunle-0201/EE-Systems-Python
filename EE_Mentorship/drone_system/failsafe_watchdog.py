"""
================================================================================
          MODULE F: EMBEDDED REAL-TIME DRONE FLIGHT CONTROL & ROBOTICS
              MILESTONE F.3: MẠCH PHÒNG VỆ WATCHDOG FAILSAFE CHO DRONE
================================================================================

TẠI SAO CẦN HARDWARE WATCHDOG FAILSAFE?
Nếu chương trình AI hoặc bộ điều khiển bị treo (Freeze):
- Hardware Watchdog Timer sẽ hết giờ (Timeout).
- Kích hoạt quy trình hạ cánh khẩn cấp Failsafe Emergency Landing để tránh rơi tự do.
"""

class DroneFailsafeSystem:
    def __init__(self, timeout_ms=500):
        self.timeout_ms = timeout_ms
        self.last_heartbeat = 0
    
    def check_failsafe(self, current_time_ms, battery_pct):
        if battery_pct < 10.0:
            return "CRITICAL_LANDING" # Pin quá yếu
        if (current_time_ms - self.last_heartbeat) > self.timeout_ms:
            return "LOST_SIGNAL_FAILSAFE" # Mất kết nối tay cầm
        return "NORMAL"


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED SYSTEM: FAILSAFE WATCHDOG MONITOR")
    print("=========================================================\n")
    
    failsafe = DroneFailsafeSystem(timeout_ms=500)
    status = failsafe.check_failsafe(current_time_ms=1000, battery_pct=5.0)
    
    print("1. KET QUA HOAT DONG MACH PROTECTION FAILSAFE:")
    print(f"   -> Trang thai Mach bao ve Failsafe : {status}")
    
    assert status == "CRITICAL_LANDING", "Loi mach Failsafe!"
    print("\n[THANH CONG] DA HOAN THANH MACH WATCHDOG FAILSAFE BAO VE DRONE!")
