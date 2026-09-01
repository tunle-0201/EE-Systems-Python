"""
================================================================================
          MODULE U CAPSTONE FINALE: BỘ QUẢN TRỊ NĂNG LƯỢNG & SYSTICK AVIONICS
================================================================================

TÍCH HỢP TOÀN BỘ RTOS POWER PIPELINE: SYSTICK TIMER + TICKLESS IDLE + SOFTWARE TIMER
"""

from rtos_edge_systick_timer import HardwareSysTickTimer
from rtos_edge_tickless_idle import TicklessIdlePowerManager
from rtos_edge_software_timer import SoftwareTimer

def run_avionics_power_management_engine():
    # 1. Khởi tạo SysTick Timer chạy 1000Hz (1ms/tick)
    systick = HardwareSysTickTimer(cpu_freq_hz=168_000_000, tick_rate_hz=1000)
    systick.clock_cycle(168_000 * 10)  # Chạy 10ms
    current_tick = systick.system_ticks

    # 2. Khởi tạo Software Timer định kỳ 50ms
    telemetry_timer = SoftwareTimer(name="Telemetry_Beacon", period_ticks=50, auto_reload=True)
    telemetry_timer.start(current_tick=current_tick)

    # 3. Kích hoạt Tickless Idle ngủ đến khi Timer tiếp theo đến hạn
    pm = TicklessIdlePowerManager(current_tick=current_tick)
    sleep_ticks = pm.enter_tickless_idle(next_wake_time=telemetry_timer.expiry_tick)
    
    # 4. Đánh thức và kiểm tra Timer
    pm.wake_up()
    timer_fired = telemetry_timer.check_and_update(current_tick=pm.current_tick)

    return current_tick, sleep_ticks, pm.current_tick, timer_fired


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE U CAPSTONE: AVIONICS POWER & TIMER ENGINE")
    print("=========================================================\n")

    t_start, slept, t_end, fired = run_avionics_power_management_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI RTOS POWER & TIMER CAPSTONE:")
    print(f"   -> System Tick truoc khi ngu : {t_start} ms")
    print(f"   -> Thoi gian Deep Sleep (WFI) : {slept} ms")
    print(f"   -> System Tick sau khi danh thuc: {t_end} ms")
    print(f"   -> Telemetry Timer Fired     : {fired}")

    assert t_start == 10 and slept == 50 and t_end == 60 and fired == True, "Loi Capstone Power Manager!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE U: EMBEDDED RTOS POWER MANAGEMENT!")
    print("=========================================================")
