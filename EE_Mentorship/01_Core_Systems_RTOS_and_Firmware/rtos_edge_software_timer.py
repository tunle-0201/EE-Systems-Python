"""
================================================================================
          MODULE U: EMBEDDED RTOS POWER MANAGEMENT & HARDWARE TIMERS
              MILESTONE U.3: HỆ THỐNG ĐỒNG HỒ PHẦN MỀM (SOFTWARE TIMER SERVICE)
================================================================================

TẠI SAO CẦN SOFTWARE TIMER TRONG CÁC HỆ THỐNG ĐIỀU KHIỂN BAY?
Vi điều khiển chỉ có số lượng Timer phần cứng hạn chế (TIM1, TIM2, TIM3,...):
- Software Timer cho phép tạo hàng chục bộ đếm giờ ảo không tốn chân ngoại vi.
- Có 2 chế độ chính:
  + One-shot Timer: Kích hoạt 1 lần duy nhất (ví dụ: Timeout ngắt kết nối Failsafe).
  + Auto-reload Timer: Tự động nạp lại chu kỳ (ví dụ: Đèn LED chớp 2Hz, gửi gói Telemetry 10Hz).
"""

class SoftwareTimer:
    def __init__(self, name: str, period_ticks: int, auto_reload: bool = False):
        self.name = name
        self.period_ticks = period_ticks
        self.auto_reload = auto_reload
        self.expiry_tick = 0
        self.is_active = False
        self.callback_fired = False

    def start(self, current_tick: int):
        self.expiry_tick = current_tick + self.period_ticks
        self.is_active = True
        self.callback_fired = False

    def check_and_update(self, current_tick: int) -> bool:
        """
        Trò đóng vai Kỹ sư Daemon Software Timer:
        - Kiểm tra nếu is_active và current_tick >= expiry_tick:
          + Đánh dấu callback_fired = True
          + Nếu auto_reload: nạp lại expiry_tick = current_tick + period_ticks
          + Nếu không auto_reload: is_active = False
          + Trả về True
        - Ngược lại: Trả về False
        """
        if self.is_active and current_tick >= self.expiry_tick:
            self.callback_fired = True
            if self.auto_reload:
                self.expiry_tick = current_tick + self.period_ticks
            else:
                self.is_active = False
            return True
        return False


if __name__ == "__main__":
    print("=========================================================")
    print("   RTOS SOFTWARE TIMERS: DAEMON TIMER SERVICE")
    print("=========================================================")

    # Tạo 1 Timer One-shot (Timeout 20ms) và 1 Timer Auto-reload (Chu kỳ 10ms)
    t_oneshot = SoftwareTimer(name="Watchdog_Timeout", period_ticks=20, auto_reload=False)
    t_reload  = SoftwareTimer(name="Telemetry_Beacon",  period_ticks=10, auto_reload=True)

    t_oneshot.start(current_tick=0)
    t_reload.start(current_tick=0)

    # Giả lập thời gian trôi đến tick = 10ms
    fired_10ms = t_reload.check_and_update(current_tick=10)
    
    # Giả lập thời gian trôi tiếp đến tick = 20ms
    fired_20ms_oneshot = t_oneshot.check_and_update(current_tick=20)
    fired_20ms_reload  = t_reload.check_and_update(current_tick=20)

    print("1. KET QUA KIEM TRA SOFTWARE TIMER THEO CAC MOC THOI GIAN:")
    print(f"   -> [10ms] Telemetry Reload Timer Fired  : {fired_10ms} (Active: {t_reload.is_active})")
    print(f"   -> [20ms] Watchdog One-shot Timer Fired : {fired_20ms_oneshot} (Active: {t_oneshot.is_active})")
    print(f"   -> [20ms] Telemetry Reload Timer Fired  : {fired_20ms_reload} (Active: {t_reload.is_active})")

    assert fired_10ms == True and fired_20ms_oneshot == True and t_oneshot.is_active == False and t_reload.is_active == True, "Loi Software Timer!"
    print("\n[THANH CONG] DA HOAN THANH DICH VU SOFTWARE TIMER CHO HE THIEU HANH RTOS!")
