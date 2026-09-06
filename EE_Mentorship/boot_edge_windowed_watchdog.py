"""
================================================================================
          MODULE Z: EMBEDDED BOOTLOADER & WINDOWED WATCHDOG
              MILESTONE Z.1: BẢO VỆ CỬA SỔ WATCHDOG PHẦN CỨNG (WINDOWED WATCHDOG)
================================================================================

TẠI SAO WATCHDOG THƯỜNG KHÔNG ĐỦ AN TOÀN CHO HỆ THỐNG ĐIỀU KHIỂN BAY?
Mạch Watchdog thông thường (IWDG): Chỉ cần reset trước khi timeout.
- Nếu phần mềm bị lỗi rơi vào vòng lặp vô tận (Runaway Loop) liên tục reset watchdog
  thì Watchdog thông thường KHÔNG PHÁT HIỆN ĐƯỢC!
- Mạch Windowed Watchdog (WWDG):
  + Định nghĩa một "Khung cửa sổ thời gian" [T_min .. T_max].
  + Cho chó ăn (Refresh/Kick) quá sớm (< T_min): KÍCH HOẠT RESET PHẦN CỨNG!
  + Cho chó ăn quá trễ (> T_max): KÍCH HOẠT RESET PHẦN CỨNG!
  + Bắt buộc tác vụ phải chạy ĐÚNG CHU KỲ DANH ĐỊNH!
"""

class WindowedWatchdogTimer:
    def __init__(self, window_min_ms: int = 20, window_max_ms: int = 80):
        self.window_min_ms = window_min_ms
        self.window_max_ms = window_max_ms
        self.last_refresh_ms = 0
        self.system_reset_triggered = False

    def kick(self, current_time_ms: int) -> bool:
        """
        Trò đóng vai Kỹ sư An toàn Phần cứng:
        - Tính khoảng cách thời gian: delta = current_time_ms - self.last_refresh_ms
        - Nếu delta < self.window_min_ms (Cho chó ăn quá sớm):
          + system_reset_triggered = True; return False
        - Nếu delta > self.window_max_ms (Cho chó ăn quá trễ):
          + system_reset_triggered = True; return False
        - Nếu nằm trong cửa sổ [T_min .. T_max]:
          + self.last_refresh_ms = current_time_ms; return True
        """
        delta = current_time_ms - self.last_refresh_ms
        if delta < self.window_min_ms or delta > self.window_max_ms:
            self.system_reset_triggered = True
            return False
        
        self.last_refresh_ms = current_time_ms
        return True


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS SAFETY: HARDWARE WINDOWED WATCHDOG (WWDG)")
    print("=========================================================\n")

    wwdg = WindowedWatchdogTimer(window_min_ms=20, window_max_ms=80)

    # Lần 1: Cho ăn ở 10ms -> Quá sớm (Lỗi vòng lặp bất thường) -> Bị phạt Reset!
    ok_early = wwdg.kick(10)
    print("1. KET QUA TEST AN TOAN CUA SO WATCHDOG:")
    print(f"   -> Kick o 10ms (<20ms)   : Hop le = {ok_early} (Reset = {wwdg.system_reset_triggered})")

    # Khởi tạo lại và cho ăn đúng cửa sổ ở 50ms
    wwdg_valid = WindowedWatchdogTimer(window_min_ms=20, window_max_ms=80)
    ok_valid = wwdg_valid.kick(50)
    print(f"   -> Kick o 50ms (20..80ms): Hop le = {ok_valid} (Reset = {wwdg_valid.system_reset_triggered})")

    assert ok_early == False and ok_valid == True and wwdg_valid.system_reset_triggered == False, "Loi WWDG!"
    print("\n[THANH CONG] DA HOAN THANH MACH CUA SO WATCHDOG WWDG CHONG VONG LAP VO TAN CHO DRONE!")
