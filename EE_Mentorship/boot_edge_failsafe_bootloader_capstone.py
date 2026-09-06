"""
================================================================================
          MODULE Z CAPSTONE FINALE: HỆ THỐNG BOOTLOADER FAILSAFE TOÀN DIỆN
================================================================================

TÍCH HỢP TOÀN BỘ AVIONICS BOOTLOADER: WINDOWED WATCHDOG + DUAL-BANK + ROLLBACK GUARD
"""

from boot_edge_windowed_watchdog import WindowedWatchdogTimer
from boot_edge_dual_bank_ota import DualBankFlashManager
from boot_edge_firmware_rollback import FirmwareRollbackGuard

def run_failsafe_avionics_bootloader():
    # 1. Khởi tạo Dual-Bank Flash và hoàn tất nạp OTA bản v2.0
    flash = DualBankFlashManager()
    dummy_payload = b"A" * 64
    flash.stage_ota_chunk(dummy_payload)
    flash.finalize_ota(target_version="v2.0", expected_size=64)
    flash.reboot_and_switch()

    # 2. Bootloader kiểm tra khởi động Slot B
    guard = FirmwareRollbackGuard(max_attempts=2)
    boot_status = guard.on_boot()

    # 3. Tác vụ chính chạy và đá Windowed Watchdog đúng khung cửa sổ
    wwdg = WindowedWatchdogTimer(window_min_ms=10, window_max_ms=50)
    kick_ok = wwdg.kick(current_time_ms=30)
    
    # 4. Tự kiểm tra hoàn tất, xác nhận firmware ổn định
    guard.mark_firmware_valid()

    return flash.active_slot, boot_status, kick_ok, guard.is_stable


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Z CAPSTONE: FAILSAFE AVIONICS BOOTLOADER")
    print("=========================================================")

    slot, status, watchdog_ok, stable = run_failsafe_avionics_bootloader()

    print("1. KET QUA HOAT DONG TOAN CHUOI BOOTLOADER CAPSTONE:")
    print(f"   -> Active Flash Slot          : {slot}")
    print(f"   -> Bootloader Status          : {status}")
    print(f"   -> Windowed Watchdog Kick OK  : {watchdog_ok}")
    print(f"   -> Firmware Verified Stable   : {stable}")

    assert slot == "SLOT_B" and watchdog_ok == True and stable == True, "Loi Capstone Bootloader!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE Z: AVIONICS BOOTLOADERS!")
    print("=========================================================")
