"""
================================================================================
          MODULE F CAPSTONE FINALE: HỆ THỐNG ĐIỀU KHIỂN BAY THỜI GIAN THỰC REAL-TIME
================================================================================

TÍCH HỢP TẤT CẢ MODULE EMBEDDED REAL-TIME CHO DRONE:
Tích hợp PID Controller + Ring Buffer UART + Failsafe Watchdog vào 1 hệ thống bay.
"""

from pid_controller import PIDController
from ring_buffer_uart import UARTDMABytesRingBuffer
from failsafe_watchdog import DroneFailsafeSystem

def run_realtime_flight_loop():
    pid = PIDController(2.0, 0.1, 0.05)
    rb = UARTDMABytesRingBuffer(64)
    fs = DroneFailsafeSystem(500)
    
    # 1. Nhận telemetry qua Ring Buffer
    rb.write(b"ALT_10M")
    
    # 2. Điều khiển PID
    adj = pid.compute(10.0, 9.8, 0.01)
    
    # 3. Kiêm tra Failsafe
    st = fs.check_failsafe(100, 85.0)
    
    return adj, st


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE F CAPSTONE: REAL-TIME EMBEDDED FLIGHT ENGINE")
    print("=========================================================\n")
    
    pid_adj, sys_st = run_realtime_flight_loop()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI REAL-TIME FLIGHT ENGINE:")
    print(f"   -> Tin hieu PID Adjustment : {pid_adj:.4f}")
    print(f"   -> Trang thai System Status: {sys_st}")
    
    assert sys_st == "NORMAL", "Loi Capstone Flight Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE F: DRONE FLIGHT CONTROL!")
    print("=========================================================")
