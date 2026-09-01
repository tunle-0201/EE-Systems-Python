"""
================================================================================
          MODULE U: EMBEDDED RTOS POWER MANAGEMENT & HARDWARE TIMERS
              MILESTONE U.1: BỘ ĐẾM SYSTICK TIMER PHẦN CỨNG (SYSTICK SCHEDULER)
================================================================================

TẠI SAO BỘ ĐẾM SYSTICK LÀ NHỊP TIM CỦA MỌI HỆ ĐIỀU HÀNH THỜI GIAN THỰC (RTOS)?
Bộ đếm SysTick (System Tick Timer) tích hợp sẵn trong nhân ARM Cortex-M:
- Đếm ngược từ giá trị nạp trước (Reload Value) về 0 theo xung nhịp CPU.
- Mỗi lần về 0 -> Kích hoạt ngắt phần cứng SysTick_Handler() cập nhật hệ thống:
  + Tăng biến đếm thời gian hệ thống: system_ticks += 1
  + Cung cấp mốc thời gian (timestamp) chuẩn mili-giây cho toàn bộ tác vụ.
"""

class HardwareSysTickTimer:
    def __init__(self, cpu_freq_hz: int = 168_000_000, tick_rate_hz: int = 1000):
        self.cpu_freq_hz = cpu_freq_hz
        self.tick_rate_hz = tick_rate_hz
        self.reload_value = cpu_freq_hz // tick_rate_hz
        self.current_value = self.reload_value
        self.system_ticks = 0
        self.interrupt_triggered = False

    def clock_cycle(self, cycles: int):
        """
        Trò đóng vai Kỹ sư Hệ thống Vi điều khiển:
        - Giảm current_value đi một lượng cycles.
        - Nếu current_value <= 0:
          + Kích hoạt ngắt interrupt_triggered = True
          + Tăng system_ticks += 1
          + Nạp lại current_value = reload_value + current_value
        """
        self.current_value -= cycles
        self.interrupt_triggered = False
        
        while self.current_value <= 0:
            self.system_ticks += 1
            self.interrupt_triggered = True
            self.current_value += self.reload_value


if __name__ == "__main__":
    print("=========================================================")
    print("   RTOS HARDWARE TIMERS: ARM CORTEX SYSTICK SCHEDULER")
    print("=========================================================\n")

    # CPU STM32F4 chạy 168 MHz, nhịp SysTick 1000 Hz (1 tick = 1 ms = 168,000 chu kỳ)
    systick = HardwareSysTickTimer(cpu_freq_hz=168_000_000, tick_rate_hz=1000)
    
    # Giả lập trôi qua 336,000 chu kỳ xung nhịp CPU (tương đương 2 mili-giây)
    systick.clock_cycle(336_000)

    print("1. KET QUA HOAT DONG SYSTICK PHAN CUNG REAL-TIME:")
    print(f"   -> Gia tri nap Reload Value : {systick.reload_value} cycles")
    print(f"   -> Tong so Ticks he thong   : {systick.system_ticks} ms")
    print(f"   -> Trang thai Ngat SysTick  : {systick.interrupt_triggered}")

    assert systick.system_ticks == 2 and systick.interrupt_triggered == True, "Loi SysTick Timer!"
    print("\n[THANH CONG] DA HOAN THANH BO DEM SYSTICK NHIP TIM HE THIEU HANH RTOS CHO DRONE!")
