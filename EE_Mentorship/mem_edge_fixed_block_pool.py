"""
================================================================================
          MODULE V: EMBEDDED MEMORY MANAGEMENT & AVIONICS HEAP
              MILESTONE V.1: BỘ CẤP PHÁT BỘ NHỚ KHỐI CỐ ĐỊNH (FIXED BLOCK POOL)
================================================================================

TẠI SAO HỆ THỐNG ĐIỀU KHIỂN BAY (NASA/TESLA) CẤM DÙNG HÀM MALLOC/FREE THÔNG THƯỜNG?
Hàm malloc() tiêu chuẩn:
- Gây phân mảnh bộ nhớ (Heap Fragmentation) sau vài giờ hoạt động -> Tràn RAM sập Drone!
- Thời gian tìm kiếm khối trống là O(N), không bảo đảm tính tiền định Real-time.
- Giải pháp **Fixed-Size Memory Pool**:
  + Cắt RAM thành các khối cố định (ví dụ: 64 bytes).
  + Dùng danh sách liên kết Free List quản lý các ô rảnh: Cấp phát O(1), Giải phóng O(1).
  + Triệt tiêu 100% phân mảnh bộ nhớ!
"""

class FixedBlockMemoryPool:
    def __init__(self, block_size: int = 64, num_blocks: int = 4):
        self.block_size = block_size
        self.num_blocks = num_blocks
        self.free_list = list(range(num_blocks))  # Danh sach chi so cac block ranh
        self.allocated_blocks = set()

    def allocate(self) -> int:
        """
        Trò đóng vai Kỹ sư Bộ nhớ Nhúng:
        - Nếu free_list còn phần tử:
          + Lấy ra 1 block_id bằng self.free_list.pop()
          + Thêm vào self.allocated_blocks
          + Trả về block_id
        - Nếu hết block: Trả về -1 (Out of Memory)
        """
        if self.free_list:
            block_id = self.free_list.pop()
            self.allocated_blocks.add(block_id)
            return block_id
        return -1

    def deallocate(self, block_id: int) -> bool:
        """Giải phóng block và trả về Free List O(1)."""
        if block_id in self.allocated_blocks:
            self.allocated_blocks.remove(block_id)
            self.free_list.append(block_id)
            return True
        return False


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS MEMORY: FIXED BLOCK POOL ALLOCATOR O(1)")
    print("=========================================================\n")

    pool = FixedBlockMemoryPool(block_size=64, num_blocks=2)

    b1 = pool.allocate()
    b2 = pool.allocate()
    b3 = pool.allocate()  # Vuot qua gioi han

    print("1. KET QUA CAP PHAT BO NHO O(1):")
    print(f"   -> Block 1 duoc cap : ID {b1}")
    print(f"   -> Block 2 duoc cap : ID {b2}")
    print(f"   -> Block 3 duoc cap : {b3} (Out of Memory dung quy chuan!)")

    # Giai phong block 1
    freed = pool.deallocate(b1)
    b_new = pool.allocate()
    print(f"   -> Giai phong Block 1 thanh cong: {freed}")
    print(f"   -> Block moi duoc tai su dung   : ID {b_new}")

    assert b1 != -1 and b2 != -1 and b3 == -1 and freed == True and b_new == b1, "Loi Fixed Pool Allocator!"
    print("\n[THANH CONG] DA HOAN THANH BO CAP PHAT BO NHO O(1) ZERO-FRAGMENTATION CHO DRONE!")
