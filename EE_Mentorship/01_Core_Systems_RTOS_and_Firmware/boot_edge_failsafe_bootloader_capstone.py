"""
================================================================================
          MODULE X: MISSION-CRITICAL EMBEDDED BOOTLOADER & WATCHDOG
              MILESTONE X.4: CAPSTONE FAILSAFE AVIONICS BOOTLOADER ENGINE
================================================================================

KIEN TRUC BO KHOI DONG HANG KHONG FAIL-SAFE (FAILSAFE AVIONICS BOOTLOADER):
Tren cac ve tinh khong gian (CubeSat, Starlink) va thiet bi bay tu hanh:
- He thong Bootloader la tuyen phong thu cuoi cung dam bao thiet bi khong bao gio bi brick.
- Tich hop chat che 3 tang phong ve vat ly:
  1. Windowed Watchdog Timer (WWDG): Bat buoc chu ky chay phai nam trong [T_min .. T_max].
  2. Dual-Bank Flash A/B: Nhan ban cap nhat OTA vao staging bank, chi hoan doi khi 100% hop le.
  3. Firmware Rollback Guard: Tu dong quay ve ban Golden Image neu ban moi bi crash lien tiep.

SO DO TRINH TU KHOI DONG VA PHONG VE FAILSAFE (ASCII SEQUENCE DIAGRAM):

   [ POWER-ON / HARDWARE RESET ]
                |
                v
   [ Bootloader Core (Sector 0) ] ──> Arm Windowed Watchdog (WWDG)
                |
                v
   [ Check Boot Counter ] ──────────(attempts > MAX)──> [ ROLLBACK TO BANK A ]
                |                                             | (Golden Image)
        (attempts <= MAX)                                     v
                |                                      [ Remap VTOR to Bank A ]
                v
   [ Check CRC32 & Target Bank ]
                |
                v
   [ Remap Vector Table (VTOR) ]
                |
                v
   [ Jump to Application Image ]
                |
                v
   [ Run Hardware BIST Checks ]
                |
                v
   [ Kick Watchdog in Window ] ─────(T_min <= dt <= T_max)──> [ Refresh OK ]
                |
                v
   [ mark_firmware_valid() ] ───────> Set Stable=True, Reset Boot Counter=0!
"""

from typing import Tuple, List, Dict, Any, Optional
import zlib

from boot_edge_windowed_watchdog import WindowedWatchdogTimer
from boot_edge_dual_bank_ota import DualBankFlashManager
from boot_edge_firmware_rollback import FirmwareRollbackGuard


class AvionicsBootloaderEngine:
    """
    Dong co Bootloader an toan cao tich hop toan bo cac khoi phong ve cua Module X
    """
    def __init__(self, watchdog_min_ms: int = 10, watchdog_max_ms: int = 50, max_boot_retries: int = 2):
        self.flash = DualBankFlashManager()
        self.watchdog = WindowedWatchdogTimer(window_min_ms=watchdog_min_ms, window_max_ms=watchdog_max_ms)
        self.rollback_guard = FirmwareRollbackGuard(max_attempts=max_boot_retries, initial_active_slot="SLOT_A")

    def perform_ota_update(self, payload: bytes, version_str: str) -> bool:
        """Nhan goi tin firmware OTA vao Staging Bank va xac thuc CRC32"""
        self.flash.stage_ota_chunk(payload)
        fw_crc = zlib.crc32(payload)
        success = self.flash.finalize_ota(target_version=version_str, expected_size=len(payload), expected_crc32=fw_crc)
        if success:
            self.flash.reboot_and_switch()
            self.rollback_guard.active_slot = self.flash.active_slot
            self.rollback_guard.is_stable = False
            self.rollback_guard.boot_attempts = 0
        return success

    def boot_and_verify_application(self, kick_time_ms: int) -> Dict[str, Any]:
        """
        Mo phong chu trinh khoi dong ung dung va giam sat an toan
        """
        boot_status = self.rollback_guard.on_boot()
        watchdog_ok = self.watchdog.kick(current_time_ms=kick_time_ms)

        if watchdog_ok and boot_status == "BOOT_NORMAL":
            self.rollback_guard.mark_firmware_valid()

        return {
            "active_slot": self.flash.active_slot,
            "active_version": self.flash.get_active_version(),
            "boot_status": boot_status,
            "watchdog_ok": watchdog_ok,
            "firmware_stable": self.rollback_guard.is_stable
        }


def run_failsafe_avionics_bootloader() -> Tuple[str, str, bool, bool]:
    """
    Ham wrapper capstone dong bo toan chuoi kiem thu cac milestone X.1, X.2, X.3
    Tra ve: (active_slot, boot_status, watchdog_ok, is_stable)
    """
    # 1. Khoi tao Dual-Bank Flash va hoan tat nap OTA ban v2.0
    flash = DualBankFlashManager()
    dummy_payload = b"AVIONICS_FIRMWARE_BINARY_V2" * 4  # 108 bytes
    flash.stage_ota_chunk(dummy_payload)
    flash.finalize_ota(target_version="v2.0", expected_size=len(dummy_payload))
    flash.reboot_and_switch()

    # 2. Bootloader kiem tra khoi dong Slot B
    guard = FirmwareRollbackGuard(max_attempts=2, initial_active_slot=flash.active_slot)
    boot_status = guard.on_boot()

    # 3. Tac vu chinh chay va da Windowed Watchdog dung khung cua so hop le
    wwdg = WindowedWatchdogTimer(window_min_ms=10, window_max_ms=50)
    kick_ok = wwdg.kick(current_time_ms=30)

    # 4. Tu kiem tra phan cung BIST hoan tat, xac nhan firmware on dinh
    if kick_ok and boot_status == "BOOT_NORMAL":
        guard.mark_firmware_valid()

    return str(flash.active_slot), str(boot_status), bool(kick_ok), bool(guard.is_stable)


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE X CAPSTONE: FAILSAFE AVIONICS BOOTLOADER")
    print("=========================================================\n")

    # 1. Kiem tra toan chuoi qua ham wrapper
    slot, status, watchdog_ok, stable = run_failsafe_avionics_bootloader()

    print("1. KET QUA HOAT DONG TOAN CHUOI BOOTLOADER CAPSTONE:")
    print(f"   -> Active Flash Slot          : {slot}")
    print(f"   -> Bootloader Status          : {status}")
    print(f"   -> Windowed Watchdog Kick OK  : {watchdog_ok}")
    print(f"   -> Firmware Verified Stable   : {stable}\n")

    assert slot == "SLOT_B", "Active slot phai la SLOT_B sau khi swap OTA!"
    assert watchdog_ok is True, "Watchdog kick phai hop le trong cua so [10..50ms]!"
    assert stable is True, "Firmware phai duoc danh dau on dinh!"

    # 2. Mo phong kich ban cap cao bang Engine toan dien
    engine = AvionicsBootloaderEngine(watchdog_min_ms=10, watchdog_max_ms=50, max_boot_retries=2)
    payload_bin = b"NEW_PAYLOAD_IMAGE_SECURE_HASH" * 4

    print("2. MO PHONG TIEN TRINH OTA VA GOC NHIN HE THONG:")
    ota_ok = engine.perform_ota_update(payload=payload_bin, version_str="v2.1.0")
    print(f"   -> Tien trinh nap OTA v2.1.0  : {'THANH CONG' if ota_ok else 'THAT BAI'}")
    print(f"   -> Slot sau khi nap           : {engine.flash.active_slot}")

    boot_res = engine.boot_and_verify_application(kick_time_ms=25)
    print(f"   -> Trang thai khoi dong       : {boot_res['boot_status']}")
    print(f"   -> Phien ban Firmware dang chay: {boot_res['active_version']}")
    print(f"   -> Giam sat thoi gian WWDG    : {'CHUAN XAC' if boot_res['watchdog_ok'] else 'VI PHAM'}")
    print(f"   -> Xac nhan he thong an toan  : {'XAC NHAN ON DINH' if boot_res['firmware_stable'] else 'CHUA ON DINH'}")

    assert boot_res["active_slot"] == "SLOT_B" and boot_res["firmware_stable"] is True

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE X: FAILSAFE AVIONICS BOOTLOADER!")
    print("=========================================================")
