"""
================================================================================
          MODULE Z: EMBEDDED BOOTLOADER & WINDOWED WATCHDOG
              MILESTONE Z.3: TỰ ĐỘNG PHỤC HỒI ROLLBACK KHI FIRMWARE LỖI
================================================================================

ĐIỀU GÌ XẢY RA KHI FIRMWARE MỚI BỊ CRASH LIÊN TỤC NGAY SAU KHI BOOT?
Cơ chế Boot Counter & Rollback Guard:
- Mỗi lần khởi động vào Firmware mới, Bootloader tăng biến đếm `boot_attempts += 1`.
- Nếu Firmware chạy qua bài tự kiểm tra phần cứng (Self-Test OK), nó gọi hàm xác nhận `mark_firmware_valid()`.
- Nếu bị crash quá 3 lần liên tiếp mà chưa kịp xác nhận (boot_attempts > 3):
  Bootloader TỰ ĐỘNG QUAY LẠI (ROLLBACK) SLOT A CŨ AN TOÀN!
"""

class FirmwareRollbackGuard:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.boot_attempts = 0
        self.is_stable = False
        self.active_slot = "SLOT_B" # Vừa cập nhật bản mới

    def on_boot(self) -> str:
        """
        Trò đóng vai Kỹ sư Bootloader Phòng thủ:
        - Tăng self.boot_attempts += 1
        - Nếu self.boot_attempts > self.max_attempts:
          + Tự động Rollback: self.active_slot = "SLOT_A"
          + Trả về "ROLLBACK_TRIGGERED"
        - Nếu không: Trả về "BOOT_NORMAL"
        """
        self.boot_attempts += 1
        if self.boot_attempts > self.max_attempts:
            self.active_slot = "SLOT_A"
            return "ROLLBACK_TRIGGERED"
        return "BOOT_NORMAL"

    def mark_firmware_valid(self):
        """Firmware mới tự kiểm tra phần cứng thành công và xác nhận ổn định."""
        self.is_stable = True
        self.boot_attempts = 0


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS BOOTLOADER: FIRMWARE ROLLBACK GUARD")
    print("=========================================================\n")

    guard = FirmwareRollbackGuard(max_attempts=3)

    # Giả lập 3 lần boot liên tiếp đều bị crash (Watchdog reset)
    s1 = guard.on_boot()
    s2 = guard.on_boot()
    s3 = guard.on_boot()
    print(f"1. TIEN TRINH BOOT CRASH: Lan 1={s1}, Lan 2={s2}, Lan 3={s3}")
    print(f"   -> Slot hien tai: {guard.active_slot} (So lan thu: {guard.boot_attempts})")

    # Lần 4 boot: Vượt quá giới hạn -> Phải Rollback về Slot A!
    s4 = guard.on_boot()
    print(f"\n2. BOOT LAN 4: Trang thai = {s4}")
    print(f"   -> Slot sau khi Rollback: {guard.active_slot}")

    assert s4 == "ROLLBACK_TRIGGERED" and guard.active_slot == "SLOT_A", "Loi Firmware Rollback!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE TU DONG ROLLBACK CUU HO DRONE TRUOC FIRMWARE LOI!")
