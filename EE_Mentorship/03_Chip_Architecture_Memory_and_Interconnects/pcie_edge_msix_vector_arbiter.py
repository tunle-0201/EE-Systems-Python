"""
================================================================================
          MODULE AB: EMBEDDED PCIE & HARDWARE ACCELERATOR INTERCONNECTS
              MILESTONE AB.3: ĐIỀU PHỐI NGẮT ĐA NHÂN (MSI-X VECTOR TABLE ARBITER)
================================================================================

TẠI SAO NGẮT MSI-X VƯỢT TRỘI HOÀN TOÀN SO VỚI ĐƯỜNG DÂY NGẮT CỔ ĐIỂN (LEGACY INTx)?
Đường dây ngắt truyền thống (INTA, INTB...): Chung đường dây, CPU phải đi hỏi từng thiết bị.
- Cơ chế MSI-X (Message Signaled Interrupts Extended):
  + Bản chất ngắt KHÔNG PHẢI LÀ DÂY ĐIỆN, mà là một gói tin ghi vào bộ nhớ RAM (Memory Write TLP)!
  + Bảng MSI-X Table hỗ trợ lên tới 2048 vector ngắt riêng biệt.
  + Mỗi kênh DMA có thể gửi ngắt thẳng tới đích danh một Core CPU cụ thể (Core Affinity),
    loại bỏ hoàn toàn tranh chấp khóa (Lock Contention) trên hệ thống đa nhân!
"""

class MsixVectorEntry:
    def __init__(self, msg_addr: int, msg_data: int, masked: bool = False):
        self.msg_addr = msg_addr
        self.msg_data = msg_data
        self.masked = masked

class MsixTableArbiter:
    def __init__(self, num_vectors: int = 16):
        self.vectors = [MsixVectorEntry(0xFEE00000 + i*0x1000, 0x100 + i) for i in range(num_vectors)]

    def mask_vector(self, vector_id: int, mask: bool):
        self.vectors[vector_id].masked = mask

    def trigger_interrupt(self, vector_id: int):
        """
        Trò đóng vai Kỹ sư Điều khiển Ngắt PCIe:
        - Nếu self.vectors[vector_id].masked == True: Trả về None (Bị chặn)
        - Nếu không bị chặn: Trả về tuple (msg_addr, msg_data) để bắn gói TLP Memory Write
        """
        vec = self.vectors[vector_id]
        if vec.masked:
            return None
        return vec.msg_addr, vec.msg_data


if __name__ == "__main__":
    print("=========================================================")
    print("   PCIE INTERCONNECT: MSI-X VECTOR INTERRUPT ARBITER")
    print("=========================================================\n")

    arbiter = MsixTableArbiter(num_vectors=4)

    # Vector 0 gửi tới Core 0 (0xFEE00000, Data 0x100)
    irq_0 = arbiter.trigger_interrupt(0)

    # Vector 1 bị Mask (Chặn tạm thời)
    arbiter.mask_vector(1, mask=True)
    irq_1 = arbiter.trigger_interrupt(1)

    print("1. KET QUA DIEU PHOI NGAT MSI-X TOAN HE THONG:")
    print(f"   -> Vector 0 (Hop le)   : Address = 0x{irq_0[0]:08X}, Data = 0x{irq_0[1]:04X}")
    print(f"   -> Vector 1 (Bi Mask)  : {irq_1} (Chan ngat thanh cong!)")

    assert irq_0 is not None and irq_1 is None and irq_0[1] == 0x100, "Loi MSI-X Arbiter!"
    print("\n[THANH CONG] DA HOAN THANH BO DIEU PHOI NGAT MSI-X DIRECT-TO-CORE CHO PCIE!")
