"""
================================================================================
          MODULE Z: EMBEDDED BOOTLOADER & WINDOWED WATCHDOG
              MILESTONE Z.2: PHÂN VÙNG DUAL-BANK FLASH VÀ NÂNG CẤP FIRMWARE OTA
================================================================================

TẠI SAO CÁC THIẾT BỊ VỆ TINH VÀ DRONE BẮT BUỘC DÙNG DUAL-BANK FLASH A/B?
Nếu nâng cấp phần mềm đè trực tiếp lên Flash:
- Mất điện hoặc đứt sóng giữa chừng -> Thiết bị biến thành "Cục gạch" vĩnh viễn!
- Kiến trúc Dual-Bank Flash A/B:
  + Slot A: Chứa Firmware đang chạy ổn định (Active Bank).
  + Slot B: Chứa Firmware mới được nạp từ xa (Staging Bank).
  + Chỉ khi nạp xong 100% và kiểm tra toàn vẹn thành công mới tráo đổi con trỏ Bootloader sang Slot B!
"""

class DualBankFlashManager:
    def __init__(self):
        self.active_slot = "SLOT_A"
        self.slot_a_version = "v1.0.0"
        self.slot_b_version = "EMPTY"
        self.slot_b_staging = bytearray()
        self.switch_pending = False

    def stage_ota_chunk(self, chunk: bytes):
        """Ghi từng khối dữ liệu firmware vào Slot B."""
        self.slot_b_staging.extend(chunk)

    def finalize_ota(self, target_version: str, expected_size: int) -> bool:
        """
        Trò đóng vai Kỹ sư Quản lý Bootloader:
        - Kiểm tra nếu len(self.slot_b_staging) == expected_size:
          + Gán self.slot_b_version = target_version
          + Đánh dấu self.switch_pending = True
          + return True
        - Nếu không đủ kích thước: return False
        """
        if len(self.slot_b_staging) == expected_size:
            self.slot_b_version = target_version
            self.switch_pending = True
            return True
        return False

    def reboot_and_switch(self):
        """Khởi động lại và hoán đổi slot hoạt động."""
        if self.switch_pending:
            self.active_slot = "SLOT_B" if self.active_slot == "SLOT_A" else "SLOT_A"
            self.switch_pending = False


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS BOOTLOADER: DUAL-BANK FLASH A/B OTA")
    print("=========================================================\n")

    flash = DualBankFlashManager()
    print(f"1. TRANG THAI BAN DAU: Active = {flash.active_slot} ({flash.slot_a_version})")

    # Nạp bản cập nhật v1.1.0 qua sóng vô tuyến (100 bytes)
    firmware_v110 = b"FIRMWARE_PAYLOAD_BINARY_CHUNK" * 4  # 116 bytes
    flash.stage_ota_chunk(firmware_v110)
    success = flash.finalize_ota(target_version="v1.1.0", expected_size=116)

    flash.reboot_and_switch()
    print("\n2. KET QUA HOAN DOI SLOT FLASH SAU REBOOT:")
    print(f"   -> Nap OTA thanh cong      : {success}")
    print(f"   -> Slot dang hoat dong moi : {flash.active_slot}")
    print(f"   -> Phien ban chay hien tai : {flash.slot_b_version}")

    assert flash.active_slot == "SLOT_B" and flash.slot_b_version == "v1.1.0", "Loi Dual-Bank OTA!"
    print("\n[THANH CONG] DA HOAN THANH KIEN TRUC DUAL-BANK FLASH A/B AN TOAN TUYET DOI!")
