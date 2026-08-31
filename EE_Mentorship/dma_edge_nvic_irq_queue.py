"""
================================================================================
          MODULE T: EMBEDDED HARDWARE DRIVERS & DMA ACCELERATION
              MILESTONE T.3: BỘ QUẢN LÝ HÀNG ĐỢI NGẮT (INTERRUPT PRIORITY QUEUE)
================================================================================

TẠI SAO HỆ THỐNG NGẮT NVIC TRÊN ARM CORTEX-M LÀ TRÁI TIM ĐIỀU PHỐI THỜI GIAN THỰC?
NVIC (Nested Vectored Interrupt Controller) quản lý hàng đợi ngắt phần cứng:
- Mỗi ngắt có mức ưu tiên Priority (0 = cao nhất, 255 = thấp nhất).
- DMA Transfer Complete (Priority 0) luôn chen hàng trước UART Receive (Priority 2).
- Bảo đảm dữ liệu cảm biến IMU 1000Hz không bao giờ bị mất!
"""

import heapq

class InterruptPriorityQueue:
    def __init__(self):
        self._queue = []  # heap: (priority, seq, name)
        self._seq = 0

    def trigger_irq(self, name: str, priority: int):
        """
        Trò đóng vai Kỹ sư RTOS thiết kế bộ điều phối ngắt:
        - Dùng heapq.heappush để đẩy (priority, self._seq, name) vào hàng đợi
        - Tăng self._seq lên 1 sau mỗi lần push (tránh xung đột khi priority bằng nhau)
        """
        heapq.heappush(self._queue, (priority, self._seq, name))
        self._seq += 1

    def service_next_irq(self) -> str:
        """Lấy và xử lý ngắt có mức ưu tiên cao nhất (priority thấp nhất)."""
        if self._queue:
            _, _, name = heapq.heappop(self._queue)
            return name
        return "NO_IRQ"


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: NVIC INTERRUPT PRIORITY QUEUE")
    print("=========================================================\n")

    nvic = InterruptPriorityQueue()
    nvic.trigger_irq("UART_RX",         priority=3)
    nvic.trigger_irq("DMA_TC",          priority=0)  # Uu tien cao nhat
    nvic.trigger_irq("TIMER_UPDATE",    priority=2)

    order = [nvic.service_next_irq(), nvic.service_next_irq(), nvic.service_next_irq()]

    print("1. KET QUA DIEU PHOI NGAT PHAN CUNG NVIC THEO THU TU UU TIEN:")
    for i, irq in enumerate(order):
        print(f"   -> [{i+1}] Xu ly ngat: {irq}")

    assert order[0] == "DMA_TC" and order[1] == "TIMER_UPDATE" and order[2] == "UART_RX", "Loi NVIC Queue!"
    print("\n[THANH CONG] DA HOAN THANH BO DIEU PHOI NGAT PHAN CUNG NVIC THOI GIAN THUC CHO ARM CORTEX!")
