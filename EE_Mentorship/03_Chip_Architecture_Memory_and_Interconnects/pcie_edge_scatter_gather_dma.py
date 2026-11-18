"""
================================================================================
          MODULE AB: EMBEDDED PCIE & HARDWARE ACCELERATOR INTERCONNECTS
              MILESTONE AB.2: KÊNH DMA PHÂN TÁN (SCATTER-GATHER DMA CHAINING)
================================================================================

TẠI SAO BỘ NHỚ ẢO (VIRTUAL MEMORY) BẮT BUỘC DÙNG SCATTER-GATHER DMA?
Trong hệ điều hành Linux/RTOS:
- Bộ nhớ được cấp phát theo từng trang (Page 4KB) nằm rải rác không liền kề trong RAM vật lý.
- DMA tuyến tính thông thường sẽ bắt CPU phải can thiệp sau mỗi 4KB gây nghẽn cổ chai!
- Thuật toán **Scatter-Gather DMA**:
  + Xâu chuỗi các mô tả (Descriptors) thành một danh sách liên kết phần cứng (Hardware Linked List).
  + Mỗi Descriptor gồm: `[buffer_address, byte_count, next_desc_ptr]`.
  + DMA tự động nhảy từ trang này sang trang khác mà CPU không tốn 1% tải!
"""

class DmaDescriptor:
    def __init__(self, buffer_addr: int, length: int, is_last: bool = False):
        self.buffer_addr = buffer_addr
        self.length = length
        self.is_last = is_last

class ScatterGatherDmaEngine:
    def __init__(self):
        self.total_transferred_bytes = 0
        self.completed_descriptors = 0

    def execute_chain(self, descriptor_chain: list) -> int:
        """
        Trò đóng vai Kỹ sư Phần cứng DMA Engine:
        - Quét qua từng descriptor trong danh sách
        - Tích lũy total_transferred_bytes += desc.length
        - Dừng lại khi gặp desc.is_last == True
        - Trả về: total_transferred_bytes
        """
        self.total_transferred_bytes = 0
        self.completed_descriptors = 0
        
        for desc in descriptor_chain:
            self.total_transferred_bytes += desc.length
            self.completed_descriptors += 1
            if desc.is_last:
                break
        return self.total_transferred_bytes


if __name__ == "__main__":
    print("=========================================================")
    print("   PCIE INTERCONNECT: SCATTER-GATHER DMA CONTROLLER")
    print("=========================================================\n")

    # Chuỗi 3 trang bộ nhớ rải rác trong RAM: 4096 bytes, 4096 bytes, 2048 bytes
    chain = [
        DmaDescriptor(buffer_addr=0x10000000, length=4096, is_last=False),
        DmaDescriptor(buffer_addr=0x20000000, length=4096, is_last=False),
        DmaDescriptor(buffer_addr=0x30000000, length=2048, is_last=True)
    ]

    dma = ScatterGatherDmaEngine()
    total_bytes = dma.execute_chain(chain)

    print("1. KET QUA THUC THI CHUOI MO TA SCATTER-GATHER DMA:")
    print(f"   -> So Descriptor da thuc thi   : {dma.completed_descriptors}")
    print(f"   -> Tong so Bytes chuyen vao GPU: {total_bytes} bytes (10KB)")

    assert total_bytes == 10240 and dma.completed_descriptors == 3, "Loi Scatter-Gather DMA!"
    print("\n[THANH CONG] DA HOAN THANH ENGINE DMA SCATTER-GATHER KHONG TON TAI CPU!")
