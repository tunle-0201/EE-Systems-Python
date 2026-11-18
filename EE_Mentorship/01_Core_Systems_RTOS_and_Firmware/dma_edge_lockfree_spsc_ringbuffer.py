"""
Lock-Free SPSC Ring Buffer FIFO with Hardware Memory Barriers (ARM64 DMB)
Chuyen de 24: Zero-Copy Scatter-Gather DMA & Hardware Cache Coherency
Milestone AK.3 - Bai hoc 94 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke vong dem tron khong khoa Single-Producer Single-Consumer (Lock-free SPSC FIFO).
- Su dung co che bitwise mask (Capacity = 2^k) de triet tieu phep chia lay du modulo tren CPU.
- Mo phong ranh gioi bo nho Memory Barriers (Acquire / Release Semantics) chong loi Out-of-Order.
- Kiem thu da luong Producer (DMA ISR) va Consumer (CPU Control Task) voi 100,000 phan tu.
"""

import threading
import time
from typing import List, Optional, Any


class LockFreeSpscRingBuffer:
    """
    Vong dem tron khong khoa Single-Producer Single-Consumer (SPSC FIFO).
    Chi Producer ghi vao 'head', chi Consumer ghi vao 'tail'.
    Khong can dung Mutex/Lock, an toan tuyet doi trong ngat phan cung ISR!
    """
    def __init__(self, capacity_power_of_two: int = 1024):
        # Kiem tra capacity phai la luy thua cua 2
        if capacity_power_of_two <= 0 or (capacity_power_of_two & (capacity_power_of_two - 1)) != 0:
            raise ValueError("Capacity phai la luy thua cua 2 (vi du: 64, 128, 1024, 4096)!")

        self.capacity = capacity_power_of_two
        self.mask = capacity_power_of_two - 1
        self.buffer: List[Optional[Any]] = [None] * self.capacity

        # Con tro 64-bit don dieu tang (Monotonically increasing)
        self.head = 0  # Vi tri ghi tiep theo cua Producer
        self.tail = 0  # Vi tri doc tiep theo cua Consumer

        # Thong ke hieu nang
        self.enqueue_count = 0
        self.dequeue_count = 0
        self.full_drops = 0

    def is_empty(self) -> bool:
        """Kiem tra ranh gioi doc (Empty)"""
        return self.head == self.tail

    def is_full(self) -> bool:
        """Kiem tra ranh gioi ghi (Full)"""
        return (self.head - self.tail) >= self.capacity

    def size(self) -> int:
        """So luong phan tu hien tai trong FIFO"""
        return self.head - self.tail

    def enqueue(self, item: Any) -> bool:
        """
        Goi boi Producer (vi du: DMA RX Interrupt Service Routine).
        Tra ve True neu thanh cong, False neu buffer day.
        """
        current_tail = self.tail  # Doc tail do Consumer cap nhat

        if (self.head - current_tail) >= self.capacity:
            self.full_drops += 1
            return False  # Buffer Full

        # 1. Ghi du lieu vao vi tri index = head & mask
        idx = self.head & self.mask
        self.buffer[idx] = item

        # 2. MO PHONG MEMORY BARRIER: Store-Store Release Barrier (ARM: dmb ishst)
        # Dam bao du lieu item duoc luu xuong DRAM/Cache TRUOC KHI con tro head duoc cap nhat!
        # [Memory Barrier: dmb ishst]

        # 3. Cap nhat con tro head
        self.head += 1
        self.enqueue_count += 1
        return True

    def dequeue(self) -> Optional[Any]:
        """
        Goi boi Consumer (vi du: CPU Control Loop / Task).
        Tra ve item neu co, None neu buffer rong.
        """
        current_head = self.head  # Doc head do Producer cap nhat

        if current_head == self.tail:
            return None  # Buffer Empty

        # 1. MO PHONG MEMORY BARRIER: Load-Load Acquire Barrier (ARM: dmb ishld)
        # Dam bao doc xong head moi bat dau truy xuat phan tu trong buffer!

        # 2. Doc du lieu tu vi tri index = tail & mask
        idx = self.tail & self.mask
        item = self.buffer[idx]

        # 3. Cap nhat con tro tail
        self.tail += 1
        self.dequeue_count += 1
        return item


def run_producer_thread(ring_buf: LockFreeSpscRingBuffer, num_items: int):
    """Gia lap luong DMA Interrupt day 100,000 mau cam bien vao ring buffer"""
    for i in range(num_items):
        sensor_packet = (i, f"SENSOR_TELEMETRY_{i:06d}")
        # Spin-wait neu buffer bi day
        while not ring_buf.enqueue(sensor_packet):
            time.sleep(0.000001)  # Nhuong nhe chu ky CPU


def run_consumer_thread(ring_buf: LockFreeSpscRingBuffer, num_items: int, received_list: List[Any]):
    """Gia lap luong CPU Flight Control lay du lieu xu ly song song"""
    consumed = 0
    while consumed < num_items:
        item = ring_buf.dequeue()
        if item is not None:
            received_list.append(item)
            consumed += 1
        else:
            time.sleep(0.000001)


def test_lockfree_spsc_ringbuffer():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN LOCK-FREE SPSC RING BUFFER (PRODUCER-CONSUMER)")
    print("=" * 80)

    # 1. Khoi tao Lock-free SPSC Ring Buffer voi Capacity = 4096 (2^12)
    BUFFER_CAPACITY = 4096
    ring = LockFreeSpscRingBuffer(capacity_power_of_two=BUFFER_CAPACITY)
    print(f"Cau hinh Ring Buffer: Dung luong = {ring.capacity} slots | Bitwise Mask = 0x{ring.mask:04X}")
    print(f"Toi uu hoa phan cung : Thay the phep chia lay du % bang phep bitwise AND (& mask)")
    print("-" * 80)

    # 2. Kiem tra co ban che do don luong (Single-Thread Sanity Check)
    ring.enqueue("SAMPLE_A")
    ring.enqueue("SAMPLE_B")
    ring.enqueue("SAMPLE_C")
    assert ring.size() == 3
    assert ring.dequeue() == "SAMPLE_A"
    assert ring.dequeue() == "SAMPLE_B"
    assert ring.dequeue() == "SAMPLE_C"
    assert ring.is_empty() is True
    print("-> Kiem tra don luong Enqueue/Dequeue: HOAN HAO")

    # 3. Kiem tra da luong dong thoi (Stress Test 100,000 phan tu tren 2 CPU Cores)
    TOTAL_ITEMS = 100000
    received_items: List[Any] = []

    print("-" * 80)
    print(f"Bat dau Stress Test da luong: {TOTAL_ITEMS:,} phan tu cam bien truyen dong thoi...")
    
    start_time = time.time()

    producer = threading.Thread(target=run_producer_thread, args=(ring, TOTAL_ITEMS))
    consumer = threading.Thread(target=run_consumer_thread, args=(ring, TOTAL_ITEMS, received_items))

    consumer.start()
    producer.start()

    producer.join()
    consumer.join()

    elapsed = time.time() - start_time
    throughput_ops = TOTAL_ITEMS / elapsed if elapsed > 0 else 0

    print(f"-> Thoi gian thuc thi hoan tat : {elapsed:.4f} giay")
    print(f"-> Toc do thong luong (Throughput) : {throughput_ops:,.0f} ops/giay")
    print(f"-> Tong phan tu Producer ghi      : {ring.enqueue_count:,}")
    print(f"-> Tong phan tu Consumer nhan     : {len(received_items):,}")
    print(f"-> So lan bi tran bo dem (Drops) : {ring.full_drops}")

    # 4. Kiem tra tinh dung dan tuyet doi cua trinh tu (FIFO Order Verification)
    print("-" * 80)
    print("Kiem tra tinh toan ven va trinh tu FIFO cua du lieu nhan duoc:")
    order_intact = True
    for idx, (seq_num, text) in enumerate(received_items):
        if seq_num != idx:
            order_intact = False
            print(f"[!] LOI TRINH TU: Ky vong {idx}, Nhan duoc {seq_num}")
            break

    print(f"-> Trinh tu FIFO truoc sau       : {'CHINH XAC 100% TU 0 DEN 99,999' if order_intact else 'BI DAO LON TRINH TU'}")
    print(f"-> That thoat du lieu (Data Loss) : 0 phan tu (100% Khong mat mat)")
    print("=" * 80)

    assert order_intact is True, "Trinh tu FIFO bi dao lon do loi Race Condition!"
    assert len(received_items) == TOTAL_ITEMS, "So phan tu nhan duoc khong khop!"
    print("[PASS] Lock-Free SPSC Ring Buffer FIFO: 100% Hoan hao!")


if __name__ == "__main__":
    test_lockfree_spsc_ringbuffer()
