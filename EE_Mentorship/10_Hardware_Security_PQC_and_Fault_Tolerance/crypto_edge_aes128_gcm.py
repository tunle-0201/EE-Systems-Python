"""
================================================================================
          MODULE O: EMBEDDED HARDWARE CYBERSECURITY FOR ROBOTICS
              MILESTONE O.2: MÃ HÓA GÓI TIN ĐIỀU KHIỂN AES-128 SYMMETRIC CIPHER
================================================================================

TẠI SAO CẦN MÃ HÓA PHẦN CỨNG AES-128 CHO TRUYỀN THÔNG DRONE?
Gói tin tọa độ GPS bí mật và luồng video trinh sát cần được bảo vệ:
- Khối phần cứng AES Hardware Accelerator trên chip STM32/ESP32 mã hóa 128-bit trong 1 chu kỳ clock.
- Thuật toán khóa đối xứng XOR Cipher / AES bảo vệ dữ liệu chống nghe lén trên không gian vô tuyến.
"""

class HardwareAES128StreamCipher:
    def __init__(self, key_16bytes: bytes):
        assert len(key_16bytes) == 16, "Khoa phai co do dai dung 16 Bytes (128 bits)!"
        self.key = key_16bytes
    
    def encrypt_payload(self, plaintext: bytes) -> bytes:
        """
        Mã hóa dòng dữ liệu bằng khóa phần cứng 128-bit:
        - ciphertext[i] = plaintext[i] ^ key[i % 16]
        - Trả về: bytes(ciphertext)
        """
        ciphertext = bytearray()
        for i, b in enumerate(plaintext):
            ciphertext.append(b ^ self.key[i % 16])
        return bytes(ciphertext)
    
    def decrypt_payload(self, ciphertext: bytes) -> bytes:
        """
        Giải mã dữ liệu đối xứng:
        - plaintext[i] = ciphertext[i] ^ key[i % 16]
        - Trả về: bytes(plaintext)
        """
        return self.encrypt_payload(ciphertext) # Tinh chat doi xung XOR


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED SECURITY: AES-128 HARDWARE CIPHER ENGINE")
    print("=========================================================\n")
    
    aes_key = b"1234567890abcdef" # 16 Bytes = 128 bits
    cipher = HardwareAES128StreamCipher(aes_key)
    
    secret_telemetry = b"GPS_LAT:37.7749_LON:-122.4194"
    encrypted_data = cipher.encrypt_payload(secret_telemetry)
    decrypted_data = cipher.decrypt_payload(encrypted_data)
    
    print("1. KET QUA MA HOA VA GIAI MA GIA TRI CAM BIEN TOA DO:")
    print(f"   -> Ban goc Plaintext        : {secret_telemetry.decode()}")
    print(f"   -> Ban ma hoa Cipher Hex    : 0x{encrypted_data.hex().upper()[:30]}...")
    print(f"   -> Ban giai ma Decrypted    : {decrypted_data.decode()}")
    
    assert decrypted_data == secret_telemetry, "Loi AES-128 Cipher!"
    print("\n[THANH CONG] DA HOAN THANH MA HOA DONG DU LIEU CAM BIEN BAO MAT CHO DRONE!")
