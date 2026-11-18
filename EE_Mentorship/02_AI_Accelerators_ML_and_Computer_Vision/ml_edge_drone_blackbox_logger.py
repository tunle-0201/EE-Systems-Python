"""
================================================================================
          MODULE E CAPSTONE FINALE: EMBEDDED FLASH BLACKBOX LOGGER FOR DRONE
================================================================================

HỘP ĐEN LƯU TRỮ NGUYÊN NÂN SỰ CỐ CỦA DRONE (CIRCULAR BUFFER BLACKBOX):
Lưu trữ 100 sự cố bay gần nhất vào bộ nhớ Flash ROM để phục vụ phân tích điều tra.
"""

import numpy as np

class DroneBlackboxLogger:
    def __init__(self, capacity=5):
        self.capacity = capacity
        self.buffer = []
    
    def log_incident(self, incident_code, severity_pct):
        if len(self.buffer) >= self.capacity:
            self.buffer.pop(0) # Đẩy sự cố cũ nhất ra ngoài
        self.buffer.append({'code': incident_code, 'severity': severity_pct})

def run_blackbox_forensics_test():
    logger = DroneBlackboxLogger(capacity=3)
    logger.log_incident(0x01, 85.0)
    logger.log_incident(0x02, 90.0)
    logger.log_incident(0x03, 95.0)
    logger.log_incident(0x04, 99.0) # Đẩy 0x01 ra khỏi buffer
    return len(logger.buffer), logger.buffer[-1]['code']


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE E CAPSTONE: EMBEDDED FLASH BLACKBOX LOGGER")
    print("=========================================================\n")
    
    buf_len, last_code = run_blackbox_forensics_test()
    
    print("1. KET QUA LUOI TRU HOP DEN BLACKBOX REAL-TIME:")
    print(f"   -> So luong Su co trong Buffer Flash : {buf_len} / 3")
    print(f"   -> Ma Su co Gan nhat (Last Incident) : 0x{last_code:02X}")
    
    assert buf_len == 3 and last_code == 0x04, "Loi thuat toan Blackbox Logger!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO NOIDUNG EDGE AI EMBEDDED!")
    print("=========================================================")
