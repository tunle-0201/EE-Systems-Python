"""
================================================================================
          MODULE Y: EMBEDDED HARDWARE DRIVERS & ZERO-CPU DMA ACCELERATION
              MILESTONE Y.3: HARDWARE NVIC INTERRUPT PRIORITY QUEUE
================================================================================

TAI SAO BO DIEU KHIEN NGAT NVIC TREN ARM CORTEX-M LA TRAI TIM HE THONG THOI GIAN THUC?
Trong kien truc chip vi dieu khien cao cap (STM32H7, TI C2000, NXP S32K):
- NVIC (Nested Vectored Interrupt Controller) quan ly tat ca cac dong yeu cau ngat:
  1. Do tre xac dinh (Deterministic Low-Latency Interrupt): Chi mat 12 chu ky xung nhip
     de day tu dong cac thanh ghi R0-R3, R12, LR, PC, xPSR vao Stack (Hardware Stacking).
  2. Quy tac muc uu tien nguoc (Inverted Priority Scheme):
     So nguyen Priority CANG NHO thi muc uu tien CANG CAO (Priority 0 la cao nhat!).
  3. Kha nang ngat long nhau (Preemption):
     Ngat DMA Transfer Complete (Priority 0) co quyen ngat ngang (preempt) ngat
     UART Receive (Priority 3) dang chay do de dam bao du lieu IMU 1000Hz khong bao gio mat!

BANG DANH SACH NGAT VA DIEU PHOI HEAP (ASCII PRIORITY DIAGRAM):

   +──────────────────┬──────────┬─────────────┬─────────────────────────────────+
   |   Ten Ngat IRQ   | Priority | Arrival Seq |         Phan Xu NVIC            |
   +──────────────────┼──────────┼─────────────┼─────────────────────────────────+
   | UART_RX          |    3     |      0      | Xu ly sau cung                  |
   | DMA_TC           |    0     |      1      | Uu tien so 1! Xu ly ngay lap tuc|
   | TIMER_UPDATE     |    2     |      2      | Xu ly thu hai                   |
   | CAN_RX           |    3     |      3      | Xu ly sau UART_RX (FIFO cung pri|
   +──────────────────┴──────────┴─────────────┴─────────────────────────────────+
"""

from typing import Tuple, List, Dict, Any, Optional
import heapq


class InterruptPriorityQueue:
    """
    Mo phong bo dieu phoi ngat phan cung NVIC (Nested Vectored Interrupt Controller)
    Su dung cau truc Min-Heap de dam bao do phuc tap chen/lay ngat O(log N) thoi gian thuc.
    """
    def __init__(self):
        # Heap elements: (priority, arrival_sequence, irq_name)
        self._queue: List[Tuple[int, int, str]] = []
        self._seq = 0
        self.serviced_history: List[str] = []

    def trigger_irq(self, name: str, priority: int) -> None:
        """
        Kich hoat mot ngat phan cung moi:
        - name: Ten dinh danh cua ngat (e.g. DMA_TC, UART_RX)
        - priority: Muc uu tien (0 = Cao nhat, so cang lon uu tien cang thap)
        """
        heapq.heappush(self._queue, (priority, self._seq, name))
        self._seq += 1

    def service_next_irq(self) -> str:
        """
        Lay va phuc vu ngat co muc uu tien cao nhat (Priority nho nhat trong Min-Heap)
        Neu hai ngat co cung muc uu tien, giai quyet bang FIFO theo arrival_sequence
        """
        if self._queue:
            priority, seq, name = heapq.heappop(self._queue)
            self.serviced_history.append(name)
            return name
        return "NO_IRQ"

    def pending_count(self) -> int:
        """So luong ngat dang cho phuc vu trong hang doi"""
        return len(self._queue)

    def peek_next_priority(self) -> Optional[int]:
        """Kiem tra muc uu tien cua ngat tiep theo ma khong lay ra"""
        if self._queue:
            return self._queue[0][0]
        return None


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: NVIC INTERRUPT PRIORITY QUEUE")
    print("=========================================================\n")

    nvic = InterruptPriorityQueue()

    # 1. Kich hoat cac ngat phan cung voi thu tu va muc uu tien khac nhau
    print("1. KICH HOAT CHUOI NGAT PHAN CUNG DEN DONG THOI:")
    nvic.trigger_irq("UART_RX",         priority=3)
    nvic.trigger_irq("DMA_TC",          priority=0)  # Uu tien toi cao (Priority 0)
    nvic.trigger_irq("TIMER_UPDATE",    priority=2)
    nvic.trigger_irq("CAN_BUS_RX",      priority=3)  # Cung priority 3 voi UART_RX nhung den sau

    print(f"   -> Tong so ngat dang cho (Pending): {nvic.pending_count()}")
    print(f"   -> Ngat co uu tien cao nhat toi day : Priority {nvic.peek_next_priority()}")

    # 2. Xu ly lan luot cac ngat theo chuan NVIC
    order = [
        nvic.service_next_irq(),
        nvic.service_next_irq(),
        nvic.service_next_irq(),
        nvic.service_next_irq()
    ]

    print("\n2. KET QUA DIEU PHOI NGAT PHAN CUNG NVIC THEO THU TU UU TIEN:")
    for i, irq in enumerate(order, 1):
        print(f"   -> [{i}] Phuc vu ngat: {irq}")

    # Kiem tra Assertions
    assert order[0] == "DMA_TC", "Ngat DMA_TC priority 0 phai duoc phuc vu dau tien!"
    assert order[1] == "TIMER_UPDATE", "Ngat TIMER_UPDATE priority 2 phai duoc phuc vu thu hai!"
    assert order[2] == "UART_RX", "UART_RX phai duoc phuc vu truoc CAN_BUS_RX vi den truoc (FIFO tie-break)!"
    assert order[3] == "CAN_BUS_RX", "CAN_BUS_RX phai duoc phuc vu sau cung!"

    print("\n[THANH CONG] DA HOAN THANH BO DIEU PHOI NGAT PHAN CUNG NVIC THOI GIAN THUC CHO ARM CORTEX!")
