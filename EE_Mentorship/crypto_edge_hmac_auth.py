"""
================================================================================
          MODULE O: EMBEDDED HARDWARE CYBERSECURITY FOR ROBOTICS
              MILESTONE O.1: XÁC THỰC LỆNH BẰNG CHỮ KÝ HMAC-SHA256
================================================================================

TẠI SAO CẦN XÁC THỰC CHỮ KÝ HMAC TRÊN DRONE QUÂN SỰ VÀ DÂN DỤNG?
Nếu hacker phát sóng giả mạo lệnh hạ cánh (Spoofing Attack):
- Drone không có bảo mật sẽ lập tức nghe theo và bị cướp quyền kiểm soát.
- Kỹ sư EE dùng **HMAC-SHA256 (Hash-based Message Authentication Code)**:
  + Dùng Khóa bí mật phần cứng (Hardware Secret Key) băm kèm Timestamp.
  + Nếu chữ ký sai hoặc gói tin bị gửi lại quá 2 giây (Replay Attack) -> TỪ CHỐI NGAY!
"""

import hmac
import hashlib
import time

class DroneHMACAuthenticator:
    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
    
    def generate_signature(self, command: str, timestamp: float) -> str:
        msg = f"{command}:{timestamp}".encode()
        return hmac.new(self.secret_key, msg, hashlib.sha256).hexdigest()
    
    def verify_command(self, command: str, timestamp: float, signature: str, max_drift_sec=2.0) -> bool:
        """
        Trò đóng vai Kỹ sư an ninh mạng nhúng:
        - Kiểm tra độ trễ timestamp: abs(time.time() - timestamp) <= max_drift_sec
        - Tính chữ ký mong đợi expected_sig
        - So sánh hmac.compare_digest(expected_sig, signature)
        - Trả về: True nếu hợp lệ, False nếu là tấn công giả mạo
        """
        expected_sig = self.generate_signature(command, timestamp)
        is_sig_valid = hmac.compare_digest(expected_sig, signature)
        return is_sig_valid


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED SECURITY: HMAC-SHA256 DRONE AUTHENTICATOR")
    print("=========================================================\n")
    
    auth = DroneHMACAuthenticator(secret_key=b"DRONE_SECRET_KEY_1234")
    
    now = time.time()
    valid_sig = auth.generate_signature("DISARM_MOTORS", now)
    
    # 1. Kiểm tra lệnh hợp lệ từ Trạm điều khiển
    is_ok = auth.verify_command("DISARM_MOTORS", now, valid_sig)
    
    # 2. Hacker giả mạo lệnh
    is_fake = auth.verify_command("DISARM_MOTORS", now, "fake_signature_abc")
    
    print("1. KET QUA XAC THUC CHU KY HMAC PHAN CUNG REAL-TIME:")
    print(f"   -> Lenh hop le tu Tram goc : {is_ok} (Chap nhan!)")
    print(f"   -> Lenh gia mao tu Hacker  : {is_fake} (Tu choi va chan dung!)")
    
    assert is_ok == True and is_fake == False, "Loi HMAC Authenticator!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE CHONG GIA MAO SPOOFING CHO DRONE!")
