"""
================================================================================
          MODULE O: EMBEDDED HARDWARE CYBERSECURITY FOR ROBOTICS
              MILESTONE O.3: KHỞI ĐỘNG AN TOÀN SECURE BOOT & KIỂM TRA FIRMWARE
================================================================================

TẠI SAO CẦN SECURE BOOT TRÊN VI ĐIỀU KHIỂN ROBOTICS?
Khi Drone nạp bản cập nhật Firmware OTA (Over-The-Air):
- Nếu kẻ xấu nạp mã độc vào bộ nhớ Flash ROM.
- Mạch Secure Boot tính toán mã băm SHA-256 của toàn bộ vùng nhớ Flash.
- Chỉ khi chữ ký điện tử khớp với Khóa Công khai của Nhà sản xuất thì MCU mới cho phép chạy!
"""

import hashlib

class SecureBootVerifier:
    def __init__(self, authorized_firmware_sha256: str):
        self.expected_hash = authorized_firmware_sha256
    
    def verify_flash_memory(self, firmware_bytes: bytes) -> bool:
        """
        Trò đóng vai Kỹ sư an ninh nhúng lập trình Secure Boot:
        - Tính actual_hash = hashlib.sha256(firmware_bytes).hexdigest()
        - So sánh actual_hash == self.expected_hash
        - Trả về: True nếu an toàn, False nếu bị can thiệp mã độc
        """
        actual_hash = hashlib.sha256(firmware_bytes).hexdigest()
        return actual_hash == self.expected_hash


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED SECURITY: HARDWARE SECURE BOOT VERIFIER")
    print("=========================================================\n")
    
    clean_firmware = b"DRONE_FIRMWARE_V2.5_OFFICIAL_RELEASE"
    official_hash = hashlib.sha256(clean_firmware).hexdigest()
    
    bootloader = SecureBootVerifier(authorized_firmware_sha256=official_hash)
    
    # 1. Firmware chính hãng
    boot_ok = bootloader.verify_flash_memory(clean_firmware)
    
    # 2. Firmware bị chèn mã độc
    malicious_firmware = b"DRONE_FIRMWARE_V2.5_HACKED_MALWARE"
    boot_hacked = bootloader.verify_flash_memory(malicious_firmware)
    
    print("1. KET QUA KIEM TRA BO NHO FLASH BOI SECURE BOOT:")
    print(f"   -> Firmware chinh hang : {boot_ok} (Khoi dong thanh cong!)")
    print(f"   -> Firmware bi ma doc  : {boot_hacked} (Khoa chip chong hack!)")
    
    assert boot_ok == True and boot_hacked == False, "Loi Secure Boot Verifier!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE SECURE BOOT BAO VE FLASH ROM CHO DRONE!")
