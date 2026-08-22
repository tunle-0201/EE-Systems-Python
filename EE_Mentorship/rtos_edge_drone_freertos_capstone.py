"""
================================================================================
          MODULE K CAPSTONE FINALE: HỆ THỐNG ĐA NHIỆM REAL-TIME FREERTOS CHO DRONE
================================================================================

TÍCH HỢP TOÀN BỘ KIẾN TRÚC FREERTOS: SCHEDULER + MUTEX + MESSAGE QUEUE
"""

from rtos_edge_task_scheduler import PreemptiveTaskScheduler, RealTimeTask
from rtos_edge_mutex_semaphore import HardwareMutexLock
from rtos_edge_message_queue import FreeRTOSMessageQueue

def run_drone_freertos_capstone_engine():
    # 1. Bộ lập lịch tác vụ
    sched = PreemptiveTaskScheduler()
    sched.register_task(RealTimeTask("FLIGHT_STABILIZER", priority=10, period_ms=2))
    sched.register_task(RealTimeTask("AI_OBJECT_TRACKER", priority=2, period_ms=33))
    
    # 2. Khóa Mutex bus SPI/I2C
    spi_lock = HardwareMutexLock()
    spi_lock.lock("FLIGHT_STABILIZER")
    
    # 3. Hàng đợi giao tiếp liên luồng
    q = FreeRTOSMessageQueue(10)
    q.send({'status': 'SYSTEM_NOMINAL', 'motor_rpm': 5400})
    msg = q.receive()
    
    task_scheduled = sched.schedule_next_task(current_time_ms=33)
    return task_scheduled, spi_lock.is_locked, msg['motor_rpm']


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE K CAPSTONE: FULL MULTI-TASK FREERTOS ENGINE")
    print("=========================================================\n")
    
    t_name, locked, rpm = run_drone_freertos_capstone_engine()
    
    print("1. KET QUA HOAT DONG HE THONG FREERTOS CHO DRONE:")
    print(f"   -> Tac vu chiem quyen uu tien: {t_name}")
    print(f"   -> Trang thai Khoa Mutex     : {locked}")
    print(f"   -> Toc do Motor RPM tu Queue : {rpm}")
    
    assert t_name == "FLIGHT_STABILIZER" and locked == True and rpm == 5400, "Loi FreeRTOS Capstone!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE K: FREERTOS EMBEDDED!")
    print("=========================================================")
