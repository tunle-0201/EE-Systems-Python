"""
================================================================================
          MODULE U: EMBEDDED RTOS POWER MANAGEMENT & HARDWARE TIMERS
              MILESTONE U.2: CHẾ ĐỘ TIẾT KIỆM NĂNG LƯỢNG (TICKLESS IDLE DEEP SLEEP)
================================================================================

TẠI SAO CÁC THIẾT BỊ IOT VÀ DRONE CẦN CHẾ ĐỘ TICKLESS IDLE TRONG FREERTOS?
Khi không có tác vụ nào cần chạy (Idle State):
- Nếu tiếp tục kích hoạt ngắt SysTick mỗi 1ms, CPU liên tục bị đánh thức gây hao pin.
- Cơ chế **Tickless Idle**:
  + Tính toán khoảng thời gian rảnh rỗi dự kiến (expected_idle_ticks).
  + Tắt ngắt định kỳ SysTick, lập trình bộ hẹn giờ tiết kiệm điện (Low-Power Timer LPTIM).
  + Đưa CPU vào chế độ ngủ sâu (WFI - Wait For Interrupt) giúp tiết kiệm đến 80% năng lượng pin!
"""

class TicklessIdlePowerManager:
    def __init__(self, current_tick: int = 0):
        self.current_tick = current_tick
        self.is_sleeping = False
        self.sleep_duration_ticks = 0

    def enter_tickless_idle(self, next_wake_time: int) -> int:
        """
        Trò đóng vai Kỹ sư Điện lực Nhúng:
        - Tính khoảng thời gian ngủ: expected_idle = next_wake_time - self.current_tick
        - Nếu expected_idle > 2 ticks:
          + Bật cờ is_sleeping = True
          + Gán sleep_duration_ticks = expected_idle
          + Trả về số ticks đã ngủ để cấu hình timer LPTIM
        - Nếu không: Trả về 0 (không bõ công vào Deep Sleep)
        """
        expected_idle = next_wake_time - self.current_tick
        if expected_idle > 2:
            self.is_sleeping = True
            self.sleep_duration_ticks = expected_idle
            return expected_idle
        return 0

    def wake_up(self):
        """Đánh thức CPU và bù lại thời gian hệ thống."""
        if self.is_sleeping:
            self.current_tick += self.sleep_duration_ticks
            self.is_sleeping = False
            self.sleep_duration_ticks = 0


if __name__ == "__main__":
    print("=========================================================")
    print("   RTOS POWER MANAGEMENT: TICKLESS IDLE DEEP SLEEP")
    print("=========================================================\n")

    pm = TicklessIdlePowerManager(current_tick=100)
    
    # Tác vụ tiếp theo chỉ cần chạy ở tick thứ 150 (rảnh 50 ms)
    sleep_ticks = pm.enter_tickless_idle(next_wake_time=150)
    print("1. KET QUA KHOI TAO CHE DO NGU TIET KIEM PIN (WFI):")
    print(f"   -> Thoi gian ngu du kien   : {sleep_ticks} ms")
    print(f"   -> Trang thai Deep Sleep   : {pm.is_sleeping}")

    # Đánh thức hệ thống sau giấc ngủ sâu
    pm.wake_up()
    print("\n2. KET QUA SAU KHI DANH THUC VA BU THOI GIAN:")
    print(f"   -> System Tick sau khi ngu : {pm.current_tick} ms")
    print(f"   -> Trang thai Sleep hien tai: {pm.is_sleeping}")

    assert sleep_ticks == 50 and pm.current_tick == 150 and pm.is_sleeping == False, "Loi Tickless Idle!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE TICKLESS IDLE TIET KIEM 80% PIN CHO THIET BI IOT!")
