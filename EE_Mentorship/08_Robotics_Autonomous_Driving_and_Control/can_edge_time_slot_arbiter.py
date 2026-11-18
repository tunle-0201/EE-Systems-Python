"""
================================================================================
          MODULE Y: EMBEDDED TIME-TRIGGERED BUS & AEROSPACE AVIONICS
              MILESTONE Y.3: BỘ ĐIỀU PHỐI KHE THỜI GIAN CỐ ĐỊNH (TDMA TIME SLOTS)
================================================================================

TẠI SAO HỆ THỐNG ĐIỀU KHIỂN BAY KHÔNG ĐƯỢC PHÉP XẢY RA XUNG ĐỘT ĐƯỜNG TRUYỀN?
Cơ chế TDMA (Time-Division Multiple Access):
- Chu kỳ bus (Cycle Period = 10ms) được băm thành các khe thời gian Time Slots (1ms/slot).
- Mỗi nút (Node) chỉ được phép phát sóng trong ĐÚNG KHE THỜI GIAN ĐƯỢC CHỈ ĐỊNH:
  + Slot 0: IMU Flight Sensor
  + Slot 1: ESC Motor Controller
  + Slot 2: Actuator Rudder
- Triệt tiêu 100% va chạm gói tin và độ trễ ngẫu nhiên!
"""

class TDMABusArbiter:
    def __init__(self, cycle_period_ms: int = 10, slot_duration_ms: int = 1):
        self.cycle_period_ms = cycle_period_ms
        self.slot_duration_ms = slot_duration_ms
        self.slot_schedule = {} # {slot_id: node_name}

    def assign_slot(self, slot_id: int, node_name: str):
        self.slot_schedule[slot_id] = node_name

    def get_active_transmitter(self, current_time_ms: int) -> str:
        """
        Trò đóng vai Kỹ sư Điều phối Bus TDMA:
        - Tính thời điểm trong chu kỳ: time_in_cycle = current_time_ms % self.cycle_period_ms
        - Tính slot hiện tại: current_slot = time_in_cycle // self.slot_duration_ms
        - Trả về tên nút được quyền phát sóng, nếu không có ai trả về "IDLE_BUS"
        """
        time_in_cycle = current_time_ms % self.cycle_period_ms
        current_slot = time_in_cycle // self.slot_duration_ms
        return self.slot_schedule.get(current_slot, "IDLE_BUS")


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE AVIONICS: TDMA TIME-TRIGGERED BUS ARBITER")
    print("=========================================================\n")

    arbiter = TDMABusArbiter(cycle_period_ms=10, slot_duration_ms=2)
    arbiter.assign_slot(0, "IMU_NAVIGATION")      # [0ms .. 2ms)
    arbiter.assign_slot(1, "ESC_MOTOR_THRUST")    # [2ms .. 4ms)
    arbiter.assign_slot(2, "ACTUATOR_FINS")       # [4ms .. 6ms)

    node_at_1ms = arbiter.get_active_transmitter(1)
    node_at_3ms = arbiter.get_active_transmitter(3)
    node_at_7ms = arbiter.get_active_transmitter(7)

    print("1. KET QUA DIEU PHOI KHE THOI GIAN TDMA REAL-TIME:")
    print(f"   -> [1ms] Quyen phat thuoc ve : {node_at_1ms}")
    print(f"   -> [3ms] Quyen phat thuoc ve : {node_at_3ms}")
    print(f"   -> [7ms] Quyen phat thuoc ve : {node_at_7ms}")

    assert node_at_1ms == "IMU_NAVIGATION" and node_at_3ms == "ESC_MOTOR_THRUST" and node_at_7ms == "IDLE_BUS", "Loi TDMA Slot!"
    print("\n[THANH CONG] DA HOAN THANH BO DIEU PHOI KHE THOI GIAN TDMA ZERO-JITTER CHO FLIGHT BUS!")
