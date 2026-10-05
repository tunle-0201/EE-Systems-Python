"""
================================================================================
          MODULE X: MISSION-CRITICAL EMBEDDED BOOTLOADER & WATCHDOG
              MILESTONE X.3: AUTOMATED FIRMWARE ROLLBACK GUARD & BOOT COUNTER
================================================================================

DIEU GIKHI FIRMWARE MOI BI CRASH LIEN TUC NGAY SAU KHI BOOT?
Tren ve tinh khong gian hoac xe tu hanh:
- Neu firmware moi nạp qua OTA bi loi an (HardFault handler loop, Null pointer,
  hoac tran bo nho RAM khi khoi dong ngoai vi):
- Thiet bi boot vao -> Crash -> Watchdog reset -> Boot lai vao ban loi -> Vong lap chet!
- Khong co ky su nao co the cam cap ST-Link/JTAG ngoai khong gian de nap lai!

CO CHE PHONG VE BO DEM KHOI DONG VA ROLLBACK (BOOT COUNTER & ROLLBACK GUARD):
1. Bien dem `boot_attempts` duoc luu trong thanh ghi luu tru khong mat dien
   (Battery-backed Backup SRAM / RTC Domain).
2. Moi lan vi dieu khien khoi dong vao ban firmware moi, Bootloader tang:
         boot_attempts += 1
3. Firmware phai thuc hien quy trinh tu kiem tra phan cung BIST (Built-In Self Test):
   - Kiem tra RAM, cam bien IMU, nguon dien, truyen thong CAN.
   - Neu toan bo OK, firmware goi ham `mark_firmware_valid()` de xoa bien dem ve 0.
4. Neu bi crash lien tiep qua nguong cho phep (vi du `boot_attempts > 3`) ma chua xac thuc:
   Bootloader LAP TUC HOAN NGUYEN (AUTOMATIC ROLLBACK) VE SLOT A (GOLDEN IMAGE)!

SO DO TRANG THAI PHONG VE ROLLBACK (ASCII STATE MACHINE):

   [ Power-On Reset ]
           |
           v
   [ Read Boot Counter ] ──(attempts > MAX_ATTEMPTS)──> [ ROLLBACK TO SLOT A ]
           |                                                   |
    (attempts <= MAX)                                          v
           |                                             [ Boot Golden Image ]
           v
   [ Boot Target Slot ]
           |
           v
   [ Run Hardware BIST ] ──(Pass All Checks)──> [ mark_firmware_valid() ]
           |                                    (Reset Counter = 0, Stable=True)
      (Crash / Reset)
           |
           v
   (Loop Back to Power-On)
"""

from typing import Tuple, List, Dict, Any, Optional


class FirmwareRollbackGuard:
    """
    Co che phong ve chong bien thiet bi thanh cuc gach bang Boot Counter & Rollback
    """
    def __init__(self, max_attempts: int = 3, initial_active_slot: str = "SLOT_B"):
        self.max_attempts = max_attempts
        self.boot_attempts = 0
        self.is_stable = False
        self.active_slot = initial_active_slot
        self.slot_status = {
            "SLOT_A": "VALID_GOLDEN",
            "SLOT_B": "UNVERIFIED_NEW"
        }

    def on_boot(self) -> str:
        """
        Thao tac xu ly cua Bootloader tai thoi diem khoi dong:
        - Tang so lan thu boot_attempts += 1
        - Neu vuot qua max_attempts: Danh dau ban moi bi loi va Rollback ve Slot A
        """
        self.boot_attempts += 1

        if self.boot_attempts > self.max_attempts:
            # Phat hien Firmware Slot B bi crash lap lai -> Rollback ve Slot A
            self.slot_status[self.active_slot] = "CORRUPT_ROLLBACKED"
            self.active_slot = "SLOT_A"
            self.boot_attempts = 0
            self.is_stable = True  # Slot A la Golden Image luon on dinh
            return "ROLLBACK_TRIGGERED"

        return "BOOT_NORMAL"

    def mark_firmware_valid(self) -> bool:
        """
        Goi boi phan mem ung dung sau khi vuot qua kiem tra BIST phan cung thanh cong
        """
        self.is_stable = True
        self.boot_attempts = 0
        self.slot_status[self.active_slot] = "CONFIRMED_STABLE"
        return True


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS BOOTLOADER: FIRMWARE ROLLBACK GUARD")
    print("=========================================================\n")

    guard = FirmwareRollbackGuard(max_attempts=3, initial_active_slot="SLOT_B")
    print(f"1. TRANG THAI BAN DAU: Active Slot = {guard.active_slot} (Status: {guard.slot_status['SLOT_B']})")

    # 1. Gia lap 3 lan khoi dong lien tiep deu bi Crash (Watchdog timeout / HardFault)
    s1 = guard.on_boot()
    s2 = guard.on_boot()
    s3 = guard.on_boot()

    print("\n2. TIEN TRINH BOOT CRASH LIEN TIEP:")
    print(f"   -> Lan 1 : Ket qua = {s1} (So lan thu = 1)")
    print(f"   -> Lan 2 : Ket qua = {s2} (So lan thu = 2)")
    print(f"   -> Lan 3 : Ket qua = {s3} (So lan thu = 3)")
    print(f"   -> Slot hien tai: {guard.active_slot} (Van tiep tuc thu nghiem)")

    assert guard.active_slot == "SLOT_B", "Trong 3 lan dau van cho phep thu o Slot B!"

    # 2. Lan boot thu 4: Vuot qua gioi han max_attempts = 3 -> Bat buoc phai Rollback ve Slot A!
    s4 = guard.on_boot()
    print("\n3. PHAN XU TAI LAN BOOT THU 4 (VUOT NGUONG AN TOAN):")
    print(f"   -> Ket qua khoi dong      : {s4}")
    print(f"   -> Slot sau khi Rollback  : {guard.active_slot} (Golden Image)")
    print(f"   -> Trang thai Slot B bi loi: {guard.slot_status['SLOT_B']}")

    assert s4 == "ROLLBACK_TRIGGERED", "Phai phat lenh ROLLBACK_TRIGGERED o lan boot thu 4!"
    assert guard.active_slot == "SLOT_A", "Slot hoat dong phai quay ve SLOT_A an toan!"

    # 3. Kich ban phan hoi khi firmware hoat dong on dinh (Happy Path)
    print("\n4. TEST KICH BAN FIRMWARE ON DINH (BIST PASS):")
    guard_happy = FirmwareRollbackGuard(max_attempts=3, initial_active_slot="SLOT_B")
    guard_happy.on_boot()
    guard_happy.mark_firmware_valid()

    print(f"   -> Trang thai sau khi xac nhan: Stable = {guard_happy.is_stable}")
    print(f"   -> Trang thai Slot B          : {guard_happy.slot_status['SLOT_B']}")
    assert guard_happy.is_stable is True and guard_happy.boot_attempts == 0

    print("\n[THANH CONG] DA HOAN THANH CO CHE TU DONG ROLLBACK CUU HO THIET BI TRUOC FIRMWARE LOI!")
