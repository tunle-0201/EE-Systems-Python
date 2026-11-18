"""
================================================================================
          MODULE AK: HARDWARE DATA STRUCTURES & SYSTEMS ALGORITHMS
              MILESTONE AK.3: CẤU TRÚC DỮ LIỆU MIN-HEAP & BỘ LẬP LỊCH TÁC VỤ RTOS
================================================================================

TẠI SAO BỘ LẬP LỊCH HỆ ĐIỀU HÀNH THỜI GIAN THỰC (RTOS) PHẢI DÙNG MIN-HEAP?
Trong FreeRTOS, Zephyr RTOS hoặc hệ thống điều khiển bay Drone:
- Hàng chục tác vụ (Task) tranh chấp CPU: Điều khiển cân bằng, Đọc cảm biến IMU, Gửi telemetry.
- Mỗi tác vụ có thời hạn chót (Deadline) hoặc Mức ưu tiên (Priority).

TẠI SAO KHÔNG DÙNG MẢNG TUẦN TỰ (FLAT ARRAY)?
1. Mảng chưa sắp xếp:
   - Thêm task mới: O(1)
   - Tìm task ưu tiên cao nhất để chạy: O(N) (Duyệt toàn bộ mảng -> Gây giật xung nhịp Jitter!)
2. Mảng đã sắp xếp:
   - Lấy task ưu tiên cao nhất: O(1)
   - Thêm task mới: O(N) (Phải dịch chuyển hàng trăm byte RAM!)

GIẢI PHÁP TỐI ƯU CỦA KỸ SƯ HỆ THỐNG: CẤU TRÚC DỮ LIỆU MIN-HEAP (ARRAY-BASED HEAP):
Biểu diễn cây nhị phân hoàn chỉnh trực tiếp trên 1 Mảng phẳng (Không tốn con trỏ RAM):
- Nút cha của i      : (i - 1) // 2
- Con trái của i     : 2 * i + 1
- Con phải của i     : 2 * i + 2

ĐỘ PHỨC TẠP BIG-O THỜI GIAN THỰC:
- Xem task ưu tiên nhất (Peek Root)      : O(1) chu kỳ CPU
- Thêm task mới (Push & Sift-Up)         : O(log N) chu kỳ CPU
- Rút task chạy xong (Pop & Sift-Down)   : O(log N) chu kỳ CPU
"""

class RTOSPriorityTaskQueue:
    """
    Hàng đợi ưu tiên Min-Heap mảng phẳng mô phỏng lõi Scheduler của FreeRTOS
    Mỗi phần tử là tuple: (priority_level, deadline_us, task_name)
    Ưu tiên nhỏ hơn = Mức độ khẩn cấp cao hơn (Priority 0 là ngắt tối cao).
    """
    def __init__(self, max_capacity: int = 16):
        self.capacity = max_capacity
        self.heap = []

    def is_empty(self) -> bool:
        return len(self.heap) == 0

    def peek_highest_priority_task(self) -> tuple:
        """
        Lấy task ưu tiên cao nhất trong O(1) thời gian mà không xóa khỏi hàng đợi
        """
        if self.is_empty():
            return None
        return self.heap[0]

    def _sift_up(self, index: int):
        """
        Đẩy phần tử mới lên trên cây nhị phân nếu nó có độ ưu tiên cao hơn nút cha: O(log N)
        """
        child_idx = index
        while child_idx > 0:
            parent_idx = (child_idx - 1) // 2
            # So sánh độ ưu tiên: (priority, deadline)
            if self.heap[child_idx][0] < self.heap[parent_idx][0]:
                # Hoán vị 2 nút (Swap in-place)
                self.heap[child_idx], self.heap[parent_idx] = self.heap[parent_idx], self.heap[child_idx]
                child_idx = parent_idx
            else:
                break

    def _sift_down(self, index: int):
        """
        Hạ phần tử gốc xuống dưới cây nhị phân để tái lập tính chất Min-Heap: O(log N)
        """
        parent_idx = index
        n = len(self.heap)

        while True:
            smallest_idx = parent_idx
            left_child = 2 * parent_idx + 1
            right_child = 2 * parent_idx + 2

            if left_child < n and self.heap[left_child][0] < self.heap[smallest_idx][0]:
                smallest_idx = left_child

            if right_child < n and self.heap[right_child][0] < self.heap[smallest_idx][0]:
                smallest_idx = right_child

            if smallest_idx != parent_idx:
                self.heap[parent_idx], self.heap[smallest_idx] = self.heap[smallest_idx], self.heap[parent_idx]
                parent_idx = smallest_idx
            else:
                break

    def push_task(self, priority: int, deadline_us: int, task_name: str) -> bool:
        """
        Thêm task mới vào Scheduler: O(log N)
        """
        if len(self.heap) >= self.capacity:
            return False  # Hàng đợi đầy, chống tràn RAM

        item = (priority, deadline_us, task_name)
        self.heap.append(item)
        self._sift_up(len(self.heap) - 1)
        return True

    def pop_task(self) -> tuple:
        """
        Rút task có độ ưu tiên cao nhất ra để CPU thực thi: O(log N)
        """
        if self.is_empty():
            return None

        highest_task = self.heap[0]
        last_task = self.heap.pop()

        if len(self.heap) > 0:
            self.heap[0] = last_task
            self._sift_down(0)

        return highest_task


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DSA: RTOS MIN-HEAP PRIORITY QUEUE SCHEDULER")
    print("=========================================================\n")

    scheduler = RTOSPriorityTaskQueue(max_capacity=10)

    # Nạp các tác vụ bay với độ ưu tiên bất kỳ
    tasks_to_add = [
        (3, 5000, "GUI_Telemetry_Display"),
        (0, 100,  "EMERGENCY_PARACHUTE"),
        (2, 1000, "GPS_Navigation_Update"),
        (1, 250,  "FOC_Motor_Current_Loop"),
        (0, 50,   "CRITICAL_BATTERY_FAILSAFE"),
    ]

    print("1. DUA CAC TAC VU VAO HANG DOI SCHEDULER (PUSH O(log N)):")
    for prio, dl, name in tasks_to_add:
        scheduler.push_task(priority=prio, deadline_us=dl, task_name=name)
        print(f"   -> Enqueue: [{name:27s}] | Priority: {prio} | Deadline: {dl:4d} us")

    # Kiểm tra O(1) Peek
    top_task = scheduler.peek_highest_priority_task()
    print(f"\n2. XEM TRUOC TAC VU KHAN CAP NHAT (PEEK O(1)):")
    print(f"   -> Task tai goc Min-Heap: {top_task[2]} (Priority: {top_task[0]})")
    assert top_task[0] == 0, "Loi Min-Heap Peek O(1)!"

    # Lần lượt rút các task ra theo đúng thứ tự ưu tiên
    print("\n3. CPU THUC THI TAC VU THEO DUNG THU TU UU TIEN (POP O(log N)):")
    executed_order = []
    while not scheduler.is_empty():
        task = scheduler.pop_task()
        executed_order.append(task)
        print(f"   -> [DISPATCH] Priority {task[0]} | Deadline {task[1]:4d} us | Executing: {task[2]}")

    # Kiểm tra tính đúng đắn của Min-Heap: Độ ưu tiên phải tăng dần
    priorities_executed = [t[0] for t in executed_order]
    print(f"\n   -> Day Priority da thuc thi: {priorities_executed}")
    assert priorities_executed == sorted(priorities_executed), "Loi sap xep Min-Heap Priority Queue!"
    assert executed_order[0][0] == 0, "Task khau cap nhat phai duoc thuc thi dau tien!"

    print("\n[THANH CONG] CAU TRUC DU LIEU MIN-HEAP DUNG CHO RTOS TASK SCHEDULER HOAN TAT CHUAN XAC!")
