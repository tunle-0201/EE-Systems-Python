"""
================================================================================
          MODULE AK: HARDWARE DATA STRUCTURES & SYSTEMS ALGORITHMS
              MILESTONE AK.4: CAPSTONE FULL REAL-TIME EMBEDDED SYSTEMS DSA ENGINE
================================================================================

KIẾN TRÚC TỔNG HỢP: ĐỘNG CƠ CẤU TRÚC DỮ LIỆU & GIẢI THUẬT NHÚNG THỜI GIAN THỰC
Trong hệ thống máy tính bay (Flight Avionics Computer) hoặc ECU ô tô tự hành Tesla:
- Hàng nghìn gói tin đến mỗi giây từ cổng CAN-Bus, SPI và ADC.
- Không được phép cấp phát động RAM (No Heap Allocation).
- Thời gian trễ xử lý (Latency) phải có tính xác định tuyệt đối (Deterministic).

ĐỘNG CƠ CAPSTONE TÍCH HỢP 4 KHỐI GIẢI THUẬT CỐT LÕI:
1. Lock-Free Circular Ring Buffer O(1): Vòng đệm thu nhận DMA không khóa.
2. Bitmask Hash Filter O(1): Mặt nạ bit lọc nhanh ID cảm biến an toàn.
3. Binary Search Look-Up Table O(log N): Tra cứu bảng lực đẩy động cơ phi tuyến.
4. Min-Heap Priority Task Dispatcher O(log N): Bộ điều phối tác vụ bay khẩn cấp.

BẢNG TỔNG KẾT ĐỘ PHỨC TẠP BIG-O THỜI GIAN THỰC (ASCII TEXT):
┌───────────────────────────────┬───────────────────┬───────────────────────────┐
│ KHỐI CHỨC NĂNG PHẦN CỨNG      │ THỜI GIAN (TIME)  │ BỘ NHỚ PHỤ (AUXILIARY RAM)│
├───────────────────────────────┼───────────────────┼───────────────────────────┤
│ Circular Ring Buffer          │ O(1)              │ O(1) Static SRAM          │
│ Bitmask Hardware Filter       │ O(1)              │ O(1) Registers            │
│ Flash LUT Binary Search       │ O(log N)          │ O(1) Stack Only           │
│ Min-Heap Task Dispatcher      │ O(log N)          │ O(1) Pre-allocated Array  │
└───────────────────────────────┴───────────────────┴───────────────────────────┘
"""

class LockFreeRingBuffer:
    """Vòng đệm tròn FIFO O(1) cho dòng dữ liệu DMA"""
    def __init__(self, size: int = 16):
        self.size = size
        self.buffer = [0] * size
        self.head = 0
        self.tail = 0
        self.count = 0

    def push(self, val: int) -> bool:
        if self.count == self.size:
            return False
        self.buffer[self.tail] = val
        self.tail = (self.tail + 1) % self.size
        self.count += 1
        return True

    def pop(self) -> int:
        if self.count == 0:
            return None
        val = self.buffer[self.head]
        self.head = (self.head + 1) % self.size
        self.count -= 1
        return val


class BitmaskHardwareFilter:
    """Bộ lọc mặt nạ Bitmask O(1) lọc ID thông điệp CAN-Bus"""
    def __init__(self, accept_mask: int = 0x7F0, target_id: int = 0x120):
        self.mask = accept_mask
        self.target = target_id

    def is_accepted(self, message_id: int) -> bool:
        # Thực hiện đúng 1 phép AND bit và 1 phép so sánh: O(1)
        return bool((message_id & self.mask) == self.target)


class RealtimeAvionicsDSAEngine:
    """
    Trọng tâm Capstone: Động cơ DSA hoàn chỉnh điều khiển hệ thống bay
    """
    def __init__(self):
        self.ring_buf = LockFreeRingBuffer(size=16)
        self.can_filter = BitmaskHardwareFilter(accept_mask=0xFF0, target_id=0x100)
        
        # Bảng LUT lực đẩy động cơ: Bướm ga PWM (1000us -> 2000us) -> Lực nâng (Grams)
        self.throttle_table = [1000, 1200, 1400, 1600, 1800, 2000]
        self.thrust_table   = [0.0,  150.0, 420.0, 850.0, 1350.0, 1900.0]
        
        # Min-Heap Scheduler: (Priority, Task_ID, Task_Payload)
        self.task_heap = []

    def lookup_motor_thrust_bsearch(self, pwm_val: float) -> float:
        """Tìm kiếm nhị phân O(log N) nội suy lực đẩy động cơ"""
        x_lut = self.throttle_table
        y_lut = self.thrust_table
        n = len(x_lut)

        if pwm_val <= x_lut[0]:
            return y_lut[0]
        if pwm_val >= x_lut[-1]:
            return y_lut[-1]

        low = 0
        high = n - 1
        while low <= high:
            mid = (low + high) // 2
            if x_lut[mid] == pwm_val:
                return float(y_lut[mid])
            elif x_lut[mid] < pwm_val:
                low = mid + 1
            else:
                high = mid - 1

        # Nội suy tuyến tính
        x0, x1 = x_lut[high], x_lut[low]
        y0, y1 = y_lut[high], y_lut[low]
        return float(y0 + (y1 - y0) * (pwm_val - x0) / (x1 - x0))

    def dispatch_critical_task(self, priority: int, name: str):
        """Thêm task vào Min-Heap O(log N)"""
        item = (priority, name)
        self.task_heap.append(item)
        
        # Sift-up O(log N)
        idx = len(self.task_heap) - 1
        while idx > 0:
            p_idx = (idx - 1) // 2
            if self.task_heap[idx][0] < self.task_heap[p_idx][0]:
                self.task_heap[idx], self.task_heap[p_idx] = self.task_heap[p_idx], self.task_heap[idx]
                idx = p_idx
            else:
                break

    def execute_next_task(self) -> tuple:
        """Lấy task ưu tiên cao nhất ra chạy O(log N)"""
        if not self.task_heap:
            return None
        root = self.task_heap[0]
        last = self.task_heap.pop()
        if self.task_heap:
            self.task_heap[0] = last
            # Sift-down O(log N)
            idx = 0
            n = len(self.task_heap)
            while True:
                smallest = idx
                left = 2 * idx + 1
                right = 2 * idx + 2
                if left < n and self.task_heap[left][0] < self.task_heap[smallest][0]:
                    smallest = left
                if right < n and self.task_heap[right][0] < self.task_heap[smallest][0]:
                    smallest = right
                if smallest != idx:
                    self.task_heap[idx], self.task_heap[smallest] = self.task_heap[smallest], self.task_heap[idx]
                    idx = smallest
                else:
                    break
        return root


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: EMBEDDED HARDWARE DATA STRUCTURES ENGINE")
    print("=========================================================\n")

    engine = RealtimeAvionicsDSAEngine()

    # 1. Thu thập dữ liệu DMA qua Ring Buffer O(1)
    print("1. KIEM TRA LOCK-FREE RING BUFFER O(1):")
    for b in [0xA1, 0xB2, 0xC3, 0xD4]:
        engine.ring_buf.push(b)
    dma_readout = [engine.ring_buf.pop() for _ in range(4)]
    print(f"   -> Readout tu Ring Buffer : {[hex(x) for x in dma_readout]}")
    assert dma_readout == [0xA1, 0xB2, 0xC3, 0xD4], "Loi Ring Buffer O(1)!"

    # 2. Lọc ID phần cứng CAN-Bus bằng Bitmask O(1)
    print("\n2. KIEM TRA BITMASK HARDWARE FILTER O(1):")
    can_ids = [0x101, 0x10A, 0x205, 0x100, 0x550]
    accepted = [cid for cid in can_ids if engine.can_filter.is_accepted(cid)]
    print(f"   -> Cac goi tin CAN chap nhan (Mask 0xFF0, Target 0x100): {[hex(c) for c in accepted]}")
    assert accepted == [0x101, 0x10A, 0x100], "Loi Bitmask CAN Filter O(1)!"

    # 3. Tra cứu lực đẩy bằng Binary Search LUT O(log N)
    print("\n3. TRA CUU LUC DAY DONG CO BANG BINARY SEARCH LUT O(log N):")
    test_pwms = [1000, 1300, 1500, 1900]
    for pwm in test_pwms:
        thrust = engine.lookup_motor_thrust_bsearch(pwm)
        print(f"   -> PWM = {pwm} us  ===>  Thrust = {thrust:6.1f} grams")
    # Kiểm tra nội suy tại 1500us (nằm giữa 1400us:420g và 1600us:850g) -> 635.0g
    assert abs(engine.lookup_motor_thrust_bsearch(1500) - 635.0) < 1e-4, "Loi Binary Search LUT!"

    # 4. Lập lịch tác vụ Min-Heap Priority Task Dispatcher
    print("\n4. DIEU PHOI TAC VU AN TOAN MIN-HEAP SCHEDULER O(log N):")
    engine.dispatch_critical_task(priority=2, name="Log_Blackbox_SDCard")
    engine.dispatch_critical_task(priority=0, name="FAILSAFE_MOTOR_CUTOFF")
    engine.dispatch_critical_task(priority=1, name="Attitude_Rate_PID_Loop")

    top_task = engine.execute_next_task()
    print(f"   -> Task toi cao duoc CPU thuc thi truoc tien: [{top_task[1]}] (Priority: {top_task[0]})")
    assert top_task[0] == 0, "Task khan cap nhat phai duoc thuc thi dau tien!"

    print("\n[THANH CONG] CAPSTONE EMBEDDED DSA ENGINE HOAN TAT XUAT SAC CHI TIEU HE THONG!")
