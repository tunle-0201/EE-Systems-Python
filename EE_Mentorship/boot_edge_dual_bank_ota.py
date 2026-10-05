"""
================================================================================
          MODULE X: MISSION-CRITICAL EMBEDDED BOOTLOADER & WATCHDOG
              MILESTONE X.2: DUAL-BANK FLASH PARTITIONING & SEAMLESS OTA
================================================================================

TAI SAO CAC THIET BI VE TINH, DRONE VA XE DIEN BAT BUOC DUNG DUAL-BANK FLASH A/B?
Trong cac he thong nhung cap cuu mang song (Tesla Gateway, SpaceX Starlink, Flight ECU):
- Neu nang cap firmware de truc tiep len vung nho Flash duy nhat (Single-Bank In-Place):
  Khi mat dien, tuot nguon 12V hoac dut song vo tuyen giua chung -> Bang vector ngat
  (Vector Table) va ma may bi loi mot nua, thiet bi bien thanh "Cuc gach" (Bricked ECU)!

KIEN TRUC PHAN VUNG DUAL-BANK FLASH A/B (ASCII MEMORY MAP):

   0x08000000          0x08010000                 0x08100000                 0x08200000
   +────────────────────+──────────────────────────+──────────────────────────+
   |   BOOTLOADER       |       BANK A (1 MB)      |       BANK B (1 MB)      |
   | (Protected Sector) |   (Active Running FW)    |   (Staging / Target FW)  |
   |   Bang Vector Goc  |    Vector Table Remap    |    Vector Table Remap    |
   +────────────────────+──────────────────────────+──────────────────────────+

QUY TRINH 4 BUOC NANG CAP AN TOAN TUYET DOI (SEAMLESS ATOMIC OTA UPDATE):
1. Ghi tich luy (Staging): Nhan tung goi tin Binary qua mang CAN-FD / Ethernet vao Slot B.
   Firmware cu o Slot A van dang dieu khien bay hoan toan binh thuong!
2. Kiem tra toan ven (Integrity & CRC32 Check): Xac thuc du kich thuoc va dung ma checksum.
3. Kich hoat co cho hoan doi (Pending Switch Flag): Luu trang thai vao thanh ghi Backup SRAM.
4. Khoi dong lai va dao bit Flash Swap: Bootloader doc co, remap con tro VTOR (Vector Table
   Offset Register) sang Slot B chi trong 1 chu ky lenh!
"""

from typing import Tuple, List, Dict, Any, Optional
import zlib


class DualBankFlashManager:
    """
    Trinh quan ly bo nho Flash kep Dual-Bank A/B cho Bootloader hang khong
    """
    def __init__(self, slot_size_bytes: int = 1024 * 1024):
        self.slot_size = slot_size_bytes
        self.active_slot = "SLOT_A"
        self.slot_a_version = "v1.0.0"
        self.slot_b_version = "EMPTY"
        self.slot_b_staging = bytearray()
        self.switch_pending = False
        self.staging_crc32 = 0

    def stage_ota_chunk(self, chunk: bytes) -> None:
        """Ghi tung khoi du lieu firmware vao vung nho dem Slot B"""
        self.slot_b_staging.extend(chunk)

    def finalize_ota(self, target_version: str, expected_size: int, expected_crc32: Optional[int] = None) -> bool:
        """
        Kiem tra xac thuc toan ven goi tin firmware truoc khi cho phep hoan doi:
        1. Kiem tra dung luong thuc te so voi Header
        2. Kiem tra ma toan ven du lieu CRC32
        """
        actual_size = len(self.slot_b_staging)
        if actual_size != expected_size:
            return False

        if expected_crc32 is not None:
            actual_crc = zlib.crc32(self.slot_b_staging)
            if actual_crc != expected_crc32:
                return False
            self.staging_crc32 = actual_crc

        self.slot_b_version = target_version
        self.switch_pending = True
        return True

    def reboot_and_switch(self) -> str:
        """
        Khoi dong lai vi dieu khien va truyen quyen thuc thi sang Slot doi dien
        """
        if self.switch_pending:
            self.active_slot = "SLOT_B" if self.active_slot == "SLOT_A" else "SLOT_A"
            self.switch_pending = False
            return f"SWAP_SUCCESS_ACTIVE_{self.active_slot}"
        return "NO_PENDING_UPDATE"

    def get_active_version(self) -> str:
        """Tra ve phien ban firmware cua Slot dang chay thuc te"""
        return self.slot_a_version if self.active_slot == "SLOT_A" else self.slot_b_version


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS BOOTLOADER: DUAL-BANK FLASH A/B OTA")
    print("=========================================================\n")

    flash = DualBankFlashManager()
    print(f"1. TRANG THAI BAN DAU: Active Slot = {flash.active_slot} (Version: {flash.get_active_version()})")

    # 1. Mo phong nhat du lieu firmware OTA v1.1.0 (4 khoi x 29 bytes = 116 bytes)
    firmware_v110 = b"FIRMWARE_PAYLOAD_BINARY_CHUNK" * 4  # 116 bytes
    fw_crc = zlib.crc32(firmware_v110)

    flash.stage_ota_chunk(firmware_v110)
    success = flash.finalize_ota(target_version="v1.1.0", expected_size=116, expected_crc32=fw_crc)

    print("\n2. QUA TRINH XAC THUC FIRMWARE STAGING TREN SLOT B:")
    print(f"   -> Kich thuoc goi tin        : {len(flash.slot_b_staging)} bytes")
    print(f"   -> Ma kiem tra toan ven CRC32: 0x{fw_crc:08X}")
    print(f"   -> Xac thuc thanh cong       : {success}")
    print(f"   -> Co cho hoan doi (Pending) : {flash.switch_pending}")

    assert success is True, "Xac thuc firmware hop le phai thanh cong!"

    # 2. Thuc hien Reboot va truyen quyen thuc thi sang Slot B
    swap_res = flash.reboot_and_switch()
    print("\n3. KET QUA HOAN DOI SLOT FLASH SAU REBOOT:")
    print(f"   -> Trang thai Bootloader     : {swap_res}")
    print(f"   -> Slot dang hoat dong moi   : {flash.active_slot}")
    print(f"   -> Phien ban chay hien tai   : {flash.get_active_version()}")

    assert flash.active_slot == "SLOT_B", "Slot hoat dong phai duoc chuyen sang SLOT_B!"
    assert flash.get_active_version() == "v1.1.0", "Phien ban phai la v1.1.0!"

    print("\n[THANH CONG] DA HOAN THANH KIEN TRUC DUAL-BANK FLASH A/B AN TOAN TUYET DOI!")
