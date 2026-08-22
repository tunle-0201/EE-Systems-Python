"""
================================================================================
          MODULE K: EMBEDDED REAL-TIME OS (FREERTOS) & MULTI-TASKING
              MILESTONE K.1: BỘ LẬP LỊCH TÁC VỤ ƯU TIÊN (PREEMPTIVE TASK SCHEDULER)
================================================================================

TẠI SAO CẦN REAL-TIME OPERATING SYSTEM (FREERTOS) TRÊN DRONE?
Nếu Drone dùng vòng lặp `while True` thông thường:
- Luồng AI chạy tốn 50ms sẽ chặn luồng Điều khiển Motor giữ thăng bằng (cần chạy mỗi 2ms).
- Drone sẽ bị lộn nhào rơi ngay!
- Kỹ sư EE dùng **FreeRTOS Preemptive Task Scheduler**:
  + Tác vụ Ưu tiên cao (Motor Control) luôn CẮP QUYỀN (Preempt) tác vụ ưu tiên thấp (AI Vision / Telemetry).
"""

class RealTimeTask:
    def __init__(self, name, priority, period_ms):
        self.name = name
        self.priority = priority # Số càng cao ưu tiên càng lớn
        self.period_ms = period_ms
        self.last_run_ms = 0

class PreemptiveTaskScheduler:
    def __init__(self):
        self.tasks = []
    
    def register_task(self, task: RealTimeTask):
        self.tasks.append(task)
        # Sắp xếp theo thứ tự Ưu tiên giảm dần
        self.tasks.sort(key=lambda t: t.priority, reverse=True)
    
    def schedule_next_task(self, current_time_ms):
        for task in self.tasks:
            if current_time_ms - task.last_run_ms >= task.period_ms:
                task.last_run_ms = current_time_ms
                return task.name
        return "IDLE_TASK"


if __name__ == "__main__":
    print("=========================================================")
    print("   FREERTOS EMBEDDED: PREEMPTIVE REAL-TIME TASK SCHEDULER")
    print("=========================================================\n")
    
    scheduler = PreemptiveTaskScheduler()
    scheduler.register_task(RealTimeTask("AI_VISION_TASK", priority=1, period_ms=50))
    scheduler.register_task(RealTimeTask("MOTOR_CONTROL_TASK", priority=10, period_ms=2))
    
    next_task = scheduler.schedule_next_task(current_time_ms=50)
    
    print("1. KET QUA DIEU PHOI TAC VU REAL-TIME SCHEDULER:")
    print(f"   -> Tac vu chiem quyen uu tien nhat : {next_task}")
    
    assert next_task == "MOTOR_CONTROL_TASK", "Loi Preemptive Task Scheduler!"
    print("\n[THANH CONG] DA MO PHONG CHINH XAC BO LAP LICH TAC VU REAL-TIME FREERTOS CHO DRONE!")
