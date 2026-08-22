"""
================================================================================
          MODULE K: EMBEDDED REAL-TIME OS (FREERTOS) & MULTI-TASKING
              MILESTONE K.2: KHÓA MUTEX VÀ SEMAPHORE BẢO VỆ CẢM BIẾN DÙNG CHUNG
================================================================================

TẠI SAO CẦN MUTEX TRONG HỆ THỐNG ĐA NHIỆM DRONE?
Khi cả 2 luồng (Luồng Lái Drone và Luồng Ghi Hộp đen) cùng đọc ghi bus I2C của Cảm biến IMU:
- Xung đột tài nguyên (Race Condition) làm vỡ dữ liệu góc nghiêng.
- Kỹ sư EE dùng **Khóa Mutex (Mutual Exclusion Lock)**:
  + Tác vụ nào giữ Mutex mới được truy cập bus I2C.
  + Tác vụ khác phải đợi đến khi Mutex được giải phóng (Unlock).
"""

class HardwareMutexLock:
    def __init__(self):
        self.is_locked = False
        self.owner = None
    
    def lock(self, task_name: str) -> bool:
        if not self.is_locked:
            self.is_locked = True
            self.owner = task_name
            return True
        return False # Đang bị chiếm giữ
    
    def unlock(self, task_name: str) -> bool:
        if self.is_locked and self.owner == task_name:
            self.is_locked = False
            self.owner = None
            return True
        return False


if __name__ == "__main__":
    print("=========================================================")
    print("   FREERTOS EMBEDDED: MUTEX SENSOR BUS PROTECTION LOCK")
    print("=========================================================\n")
    
    i2c_mutex = HardwareMutexLock()
    
    # 1. Luồng Motor chiếm khóa I2C
    ok1 = i2c_mutex.lock("MOTOR_TASK")
    # 2. Luồng AI Vision cố chiếm khóa I2C -> Bị từ chối!
    ok2 = i2c_mutex.lock("AI_VISION_TASK")
    
    print("1. KET QUA PHAN QUYEN KHOA MUTEX TREN BUS CAM BIEN:")
    print(f"   -> Motor Task chiem khoa : {ok1} (Thanh cong!)")
    print(f"   -> AI Task chiem khoa    : {ok2} (Bi chan an toan!)")
    
    assert ok1 == True and ok2 == False, "Loi Mutex Lock!"
    print("\n[THANH CONG] DA BAO VE THANH CONG TAI NGUYEN CAM BIEN TRANH XUNG DOT RACE CONDITION!")
