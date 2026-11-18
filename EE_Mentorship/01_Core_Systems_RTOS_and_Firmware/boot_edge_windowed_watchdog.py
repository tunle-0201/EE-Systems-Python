"""
================================================================================
          MODULE X: MISSION-CRITICAL EMBEDDED BOOTLOADER & WATCHDOG
              MILESTONE X.1: HARDWARE WINDOWED WATCHDOG TIMER (WWDG)
================================================================================

TAI SAO WATCHDOG THONG THUONG KHONG DU AN TOAN CHO HE THONG DIEU KHIEN BAY & O TO?
Trong tieu chuan an toan hang khong (DO-254 / DO-178C DAL-A) va o to (ISO 26262 ASIL-D):
- Mach Watchdog doc lap thong thuong (IWDG - Independent Watchdog):
  Chi don gian dem nguoc ve 0. Neu tac vu bi loi roi vao mot vong lap dot bien (Runaway Loop)
  hoac ngat con tro ham bat thuong ma vo tinh van goi ham da cho an (Watchdog Kick),
  IWDG se KHONG THE PHAT HIEN DUOC va he thong tiep tuc treo nguy hiem!

CO CHE PHONG VE KHUNG CUA SO THOI GIAN CUA WINDOWED WATCHDOG (WWDG):
Mach WWDG dinh nghia mot khung cua so thoi gian nghiem ngat [T_min .. T_max]:

SO DO KHUNG CUA SO THOI GIAN WATCHDOG (ASCII TIMING DIAGRAM):

   0 ms                    T_min (20 ms)                  T_max (80 ms)             Thoi gian
   +─────────────────────────+───────────────────────────────+─────────────────────────>
   |   KICK SOM -> RESET     |      CUA SO HOP LE CHO AN     |    TIMEOUT -> RESET     |
   | (Vong lap roi loan/PPL) |   (Chu ky tac vu danh dinh)   | (Treo he thong/Deadlock)|
   +─────────────────────────+───────────────────────────────+─────────────────────────+

LUAT PHAN XU AN TOAN PHAN CUNG:
1. Da cho an qua som (delta_t < T_min): Kich hoat Reset phan cung ngay lap tuc!
2. Da cho an qua tre (delta_t > T_max): Kich hoat Reset phan cung do qua han!
3. Chi khi T_min <= delta_t <= T_max: He thong xac nhan chu trinh thoi gian thuc hoan hao!
"""

from typing import Tuple, List, Dict, Any, Optional


class WindowedWatchdogTimer:
    """
    Mo hinh phan cung Windowed Watchdog Timer (WWDG) tren vi dieu khien STM32 / TMS570
    Kiem soat nghiem ngat tinh dung han ve mat thoi gian (Temporal Determinism)
    """
    def __init__(self, window_min_ms: int = 20, window_max_ms: int = 80):
        self.window_min_ms = window_min_ms
        self.window_max_ms = window_max_ms
        self.last_refresh_ms = 0
        self.system_reset_triggered = False
        self.reset_reason: Optional[str] = None

    def kick(self, current_time_ms: int) -> bool:
        """
        Thuc hien thao tac da cho an (Watchdog Refresh / Petting):
        - current_time_ms: Thoi gian he thong tinh bang mili-giay
        Tra ve: True neu da watchdog hop le trong khung cua so; False neu vi pham va bi Reset
        """
        delta = current_time_ms - self.last_refresh_ms

        # 1. Vi pham da qua som (Early Kick Hazard)
        if delta < self.window_min_ms:
            self.system_reset_triggered = True
            self.reset_reason = f"RESET_EARLY_KICK (delta={delta}ms < T_min={self.window_min_ms}ms)"
            return False

        # 2. Vi pham da qua tre (Late Kick Timeout)
        if delta > self.window_max_ms:
            self.system_reset_triggered = True
            self.reset_reason = f"RESET_TIMEOUT (delta={delta}ms > T_max={self.window_max_ms}ms)"
            return False

        # 3. Hop le trong khung cua so [T_min .. T_max]
        self.last_refresh_ms = current_time_ms
        self.system_reset_triggered = False
        self.reset_reason = None
        return True

    def reset_hardware_latch(self, initial_time_ms: int = 0) -> None:
        """Reset lai mach chot phan cung sau khi khoi dong lai"""
        self.last_refresh_ms = initial_time_ms
        self.system_reset_triggered = False
        self.reset_reason = None


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS SAFETY: HARDWARE WINDOWED WATCHDOG (WWDG)")
    print("=========================================================\n")

    wwdg = WindowedWatchdogTimer(window_min_ms=20, window_max_ms=80)

    # 1. Kich ban 1: Da qua som tai 10ms (< 20ms) do code bi vong lap bat thuong
    ok_early = wwdg.kick(10)
    print("1. TEST VI PHAM DA CHO AN QUA SOM (EARLY KICK DETECTION):")
    print(f"   -> Da tai t = 10ms (< 20ms)   : Hop le = {ok_early}")
    print(f"   -> Trang thai Reset he thong : {wwdg.system_reset_triggered}")
    print(f"   -> Ly do Reset               : {wwdg.reset_reason}")

    assert ok_early is False, "Da qua som phai bi phat hien va tu choi!"
    assert wwdg.system_reset_triggered is True, "Phan cung phai phat lenh Reset khi da qua som!"
    print("   -> Ket qua                   : CHINH XAC (Da ngan chan vong lap runaway)\n")

    # 2. Kich ban 2: Khoi phuc va da dung khung gio tai 50ms (20ms .. 80ms)
    wwdg.reset_hardware_latch(initial_time_ms=0)
    ok_valid = wwdg.kick(50)
    print("2. TEST DA CHO AN DUNG KHUNG CUA SO (NOMINAL KICK):")
    print(f"   -> Da tai t = 50ms (20..80ms) : Hop le = {ok_valid}")
    print(f"   -> Trang thai Reset he thong : {wwdg.system_reset_triggered}")

    assert ok_valid is True, "Da dung cua so phai duoc chap thuan!"
    assert wwdg.system_reset_triggered is False, "Khong duoc gay reset khi chay dung chu ky!"
    print("   -> Ket qua                   : CHINH XAC (Chu ky tac vu on dinh)\n")

    # 3. Kich ban 3: Tac vu bi ket deadlock, lan da tiep theo tai 150ms (delta = 100ms > 80ms)
    ok_late = wwdg.kick(150)
    print("3. TEST VI PHAM DA CHO AN QUA TRE (TIMEOUT DEADLOCK):")
    print(f"   -> Da tai t = 150ms (delta=100ms > 80ms): Hop le = {ok_late}")
    print(f"   -> Trang thai Reset he thong            : {wwdg.system_reset_triggered}")
    print(f"   -> Ly do Reset                          : {wwdg.reset_reason}")

    assert ok_late is False, "Da qua tre phai bi kich hoat Timeout Reset!"
    assert wwdg.system_reset_triggered is True, "Phan cung phai reset khi bi deadlock!"

    print("\n[THANH CONG] MACH WINDOWED WATCHDOG BAO VE TOAN DIEN CA HAI CHIEU THOI GIAN DUNG HAN!")
