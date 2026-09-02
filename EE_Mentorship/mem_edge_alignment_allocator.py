"""
================================================================================
          MODULE V: EMBEDDED MEMORY MANAGEMENT & AVIONICS HEAP
              MILESTONE V.3: CĂN CHỈNH ĐỊA CHỈ BỘ NHỚ PHẦN CỨNG (MEMORY ALIGNMENT)
================================================================================

TẠI SAO PHẦN CỨNG DMA VÀ VECTOR SIMD ĐÒI HỎI ĐỊA CHỈ PHẢI CĂN CHỈNH (ALIGNMENT)?
Trong vi xử lý ARM Cortex và chip NPU/GPU:
- Lệnh nạp Vector 128-bit yêu cầu địa chỉ phải chia hết cho 16 bytes (16-byte Aligned).
- Truy cập địa chỉ không căn chỉnh (Unaligned Access):
  + Làm giảm 50% thông lượng băng thông bộ nhớ.
  + Thậm chí kích hoạt ngắt phần cứng nghiêm trọng HardFault Exception!
- Công thức căn chỉnh địa chỉ lên bội số của `alignment` (với alignment là lũy thừa của 2):
  aligned_addr = (raw_addr + (alignment - 1)) & ~(alignment - 1)
"""

def align_memory_address(raw_address: int, alignment_bytes: int = 16) -> int:
    """
    Trò đóng vai Kỹ sư Tối ưu hóa Bộ nhớ Phần cứng:
    - Áp dụng phép toán bitmask: (raw_address + alignment_bytes - 1) & ~(alignment_bytes - 1)
    - Trả về: aligned_address
    """
    mask = alignment_bytes - 1
    return (raw_address + mask) & ~mask


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS MEMORY: HARDWARE 16-BYTE ALIGNED ALLOCATOR")
    print("=========================================================\n")

    # Địa chỉ thô chưa căn chỉnh: 0x20000005 (không chia hết cho 16)
    raw_addr = 0x20000005
    aligned_16 = align_memory_address(raw_addr, alignment_bytes=16)
    aligned_64 = align_memory_address(raw_addr, alignment_bytes=64)

    print("1. KET QUA CAN CHINH DIA CHI CHO DMA & VECTOR SIMD:")
    print(f"   -> Dia chi tho ban dau       : 0x{raw_addr:08X} (dec: {raw_addr})")
    print(f"   -> Dia chi can chinh 16-byte : 0x{aligned_16:08X} (Chia het cho 16: {aligned_16 % 16 == 0})")
    print(f"   -> Dia chi can chinh 64-byte : 0x{aligned_64:08X} (Chia het cho 64: {aligned_64 % 64 == 0})")

    assert aligned_16 % 16 == 0 and aligned_16 == 0x20000010 and aligned_64 % 64 == 0, "Loi Memory Alignment!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN CAN CHINH BO NHO BITMASK CHO PHAN CUNG!")
