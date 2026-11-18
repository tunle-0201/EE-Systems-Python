"""
================================================================================
          MODULE V CAPSTONE FINALE: HỆ THỐNG QUẢN TRỊ BỘ NHỚ AVIONICS TỐI THƯỢNG
================================================================================

TÍCH HỢP TOÀN BỘ AVIONICS MEMORY STACK: FIXED POOL + STACK CANARY + HARDWARE ALIGNMENT
"""

from mem_edge_fixed_block_pool import FixedBlockMemoryPool
from mem_edge_stack_watermark import TaskStackGuard
from mem_edge_alignment_allocator import align_memory_address

def run_avionics_memory_engine():
    # 1. Cấp phát gói tin Telemetry từ Fixed Pool O(1)
    pool = FixedBlockMemoryPool(block_size=64, num_blocks=4)
    packet_id = pool.allocate()

    # 2. Căn chỉnh địa chỉ đệm cho bộ truyền DMA (16-byte Aligned)
    raw_buffer_ptr = 0x20000003
    aligned_dma_ptr = align_memory_address(raw_buffer_ptr, alignment_bytes=16)

    # 3. Kiểm tra an toàn Stack Task
    stack_guard = TaskStackGuard(stack_size_words=16)
    stack_guard.simulate_stack_usage(used_words=10)
    has_overflow = stack_guard.check_stack_overflow()
    free_watermark = stack_guard.get_high_watermark()

    return packet_id, aligned_dma_ptr, has_overflow, free_watermark


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE V CAPSTONE: MISSION-CRITICAL MEMORY ENGINE")
    print("=========================================================\n")

    pkt_id, dma_ptr, overflow, watermark = run_avionics_memory_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI AVIONICS MEMORY CAPSTONE:")
    print(f"   -> Telemetry Packet Block ID : {pkt_id}")
    print(f"   -> Aligned DMA Buffer Addr   : 0x{dma_ptr:08X}")
    print(f"   -> Stack Overflow Detected   : {overflow}")
    print(f"   -> Free Stack Watermark      : {watermark} words")

    assert pkt_id != -1 and dma_ptr % 16 == 0 and overflow == False and watermark == 6, "Loi Capstone Memory Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE V: EMBEDDED MEMORY MANAGEMENT!")
    print("=========================================================")
