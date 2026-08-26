"""
================================================================================
          MODULE O CAPSTONE FINALE: BỘ PHÒNG THỦ KHÔNG GIAN MẠNG CHO DRONE
================================================================================

TÍCH HỢP TOÀN BỘ BẢO MẬT PHẦN CỨNG: SECURE BOOT + HMAC AUTH + AES-128 CIPHER
"""

from crypto_edge_hmac_auth import DroneHMACAuthenticator
from crypto_edge_aes128_gcm import HardwareAES128StreamCipher
from crypto_edge_secure_boot_ecdsa import SecureBootVerifier
import hashlib
import time

def run_drone_military_security_pipeline():
    # 1. Secure Boot kiểm tra Flash
    fw = b"DRONE_SECURE_OS_V3.0"
    bootloader = SecureBootVerifier(hashlib.sha256(fw).hexdigest())
    boot_status = bootloader.verify_flash_memory(fw)
    
    # 2. HMAC Xác thực lệnh
    auth = DroneHMACAuthenticator(b"SECRET_KEY_12345")
    t_now = time.time()
    sig = auth.generate_signature("RETURN_TO_HOME", t_now)
    cmd_verified = auth.verify_command("RETURN_TO_HOME", t_now, sig)
    
    # 3. AES-128 Mã hóa dữ liệu bay
    cipher = HardwareAES128StreamCipher(b"0123456789abcdef")
    secret_bytes = cipher.encrypt_payload(b"SECRET_WAYPOINT_XYZ")
    decrypted = cipher.decrypt_payload(secret_bytes)
    
    return boot_status, cmd_verified, decrypted.decode()


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE O CAPSTONE: MILITARY-GRADE DRONE CYBER DEFENSE")
    print("=========================================================\n")
    
    boot_ok, cmd_ok, dec_text = run_drone_military_security_pipeline()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI CYBER DEFENSE REAL-TIME:")
    print(f"   -> Secure Boot Status   : {boot_ok}")
    print(f"   -> HMAC Auth Command    : {cmd_ok}")
    print(f"   -> AES Decrypted Message: {dec_text}")
    
    assert boot_ok == True and cmd_ok == True and dec_text == "SECRET_WAYPOINT_XYZ", "Loi Capstone Security!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE O: EMBEDDED CYBERSECURITY!")
    print("=========================================================")
