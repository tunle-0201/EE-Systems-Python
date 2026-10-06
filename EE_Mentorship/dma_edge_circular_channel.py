"""
================================================================================
          MODULE Y: EMBEDDED HARDWARE DRIVERS & ZERO-CPU DMA ACCELERATION
              MILESTONE Y.1: DIRECT MEMORY ACCESS (DMA) CIRCULAR CONTROLLER
================================================================================

TAI SAO CAC CHIP ARM CORTEX (STM32, NXP, TI) DUNG DMA DE TIET KIEM 100% CPU?
Trong he thong nhung toc do cao (LiDAR 3D, Radar 77GHz, IMU 1000Hz, Audio DSP):
- Neu CPU xu ly ngat tren tung byte du lieu (Byte-by-Byte Interrupt):
  O toc do 10 Mbps, CPU se ton 100% thoi gian de Cat/Phuc hoi thanh ghi tren Stack
  (Context Switch Thrashing), khong con chu ky nao de chay thuat toan dieu khien bay!

GIAI PHAP BO DIEU KHIEN TRUY CAP BO NHO TRUC TIEP (DMA HARDWARE ACCELERATOR):
- DMA la mot vi xu ly phu phan cung doc lap chiem quyen Bus Master:
- Tu dong chuyen cac khoi du lieu tu thanh ghi Ngoai vi (SPI_DR / UART_RDR) thang vao
  vung nho SRAM ma CPU khong can thuc thi mot dong lenh Assembly nao (0% CPU Load)!

CO CHE VONG DEM DOI PING-PONG TRONG CHE DO CIRCULAR MODE (ASCII DIAGRAM):

   [ Ngoai vi UART/SPI ] ──(DMA Hardware Stream)──> [ Circular Buffer SRAM ]
                                                               |
        [ Ngat nua mang: Half-Transfer (HT) ] <────────────────+── Vung Ping [0 .. N/2 - 1]
                                                               |   (CPU doc khi DMA ghi Pong)
        [ Ngat day mang: Transfer-Complete (TC) ] <────────────+── Vung Pong [N/2 .. N - 1]
                                                                   (CPU doc khi DMA ghi Ping)

NGUYEN LY HOAT DONG:
1. Khi DMA nap day nua mang dau: Kich hoat co HT -> CPU xu ly phan dau.
2. DMA tiep tuc chay tu dong nap nua mang sau.
3. Khi day mang: Kich hoat co TC -> CPU xu ly phan sau, DMA tu dong cuon lai o dau!
"""

from typing import Tuple, List, Dict, Any, Optional


class HardwareDMAChannel:
    """
    Mo phong kenh truyen bo nho truc tiep Circular DMA Channel tren ARM Cortex-M
    Tich hop co bao ngat Half-Transfer (HT) va Transfer-Complete (TC)
    """
    def __init__(self, buffer_size: int = 128):
        self.buffer_size = buffer_size
        self.buffer = bytearray(buffer_size)
        self.dma_pointer = 0
        self.half_transfer_flag = False
        self.transfer_complete_flag = False
        self.total_transferred_bytes = 0

    def transfer_byte(self, incoming_byte: int) -> None:
        """
        Nhan 1 byte tu ngoai vi va ghi truc tiep vao RAM khong qua CPU
        """
        self.buffer[self.dma_pointer] = incoming_byte & 0xFF
        self.dma_pointer += 1
        self.total_transferred_bytes += 1

        # 1. Kiem tra nguong nua mang (Half Transfer)
        if self.dma_pointer == self.buffer_size // 2:
            self.half_transfer_flag = True

        # 2. Kiem tra nguong day mang (Transfer Complete) va cuon Circular
        elif self.dma_pointer >= self.buffer_size:
            self.transfer_complete_flag = True
            self.dma_pointer = 0  # Cuon lai vi tri dau mang trong Circular Mode

    def clear_flags(self) -> None:
        """Xoa co ngat sau khi trinh phuc vu ngat ISR da xu ly xong"""
        self.half_transfer_flag = False
        self.transfer_complete_flag = False

    def get_ping_buffer(self) -> bytes:
        """Lay nua mang dau (Ping buffer)"""
        half = self.buffer_size // 2
        return bytes(self.buffer[:half])

    def get_pong_buffer(self) -> bytes:
        """Lay nua mang sau (Pong buffer)"""
        half = self.buffer_size // 2
        return bytes(self.buffer[half:])


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: CIRCULAR DMA CONTROLLER SIMULATOR")
    print("=========================================================\n")

    dma = HardwareDMAChannel(buffer_size=10)
    print(f"1. KHOI TAO KENH DMA: Buffer Size = {dma.buffer_size} bytes (Circular Mode)")

    # 1. Nap 5 bytes dau tien (0, 10, 20, 30, 40) -> Cham nguong nua mang HT
    for b in range(5):
        dma.transfer_byte(b * 10)

    print("\n2. TIEN TRINH NAP NUA MANG DAU (PING BUFFER):")
    print(f"   -> Pointer hien tai         : {dma.dma_pointer}")
    print(f"   -> Half Transfer Flag (HT)  : {dma.half_transfer_flag}")
    print(f"   -> Transfer Complete (TC)   : {dma.transfer_complete_flag}")
    print(f"   -> Du lieu Ping Buffer      : {list(dma.get_ping_buffer())}")

    assert dma.half_transfer_flag is True, "Phai bat co HT khi nap du 5 bytes!"
    assert dma.transfer_complete_flag is False, "Khong duoc bat co TC khi chua day mang!"

    # 2. Nap tiep 5 bytes sau (50, 60, 70, 80, 90) -> Cham nguong day mang TC va cuon tron
    for b in range(5, 10):
        dma.transfer_byte(b * 10)

    print("\n3. TIEN TRINH NAP NUA MANG SAU VA CUON CIRCULAR (PONG BUFFER):")
    print(f"   -> Pointer sau khi cuon tron: {dma.dma_pointer} (Da cuon ve 0)")
    print(f"   -> Transfer Complete (TC)   : {dma.transfer_complete_flag}")
    print(f"   -> Du lieu Pong Buffer      : {list(dma.get_pong_buffer())}")
    print(f"   -> Tong so byte da nap      : {dma.total_transferred_bytes}")

    assert dma.transfer_complete_flag is True, "Phai bat co TC khi nap day 10 bytes!"
    assert dma.dma_pointer == 0, "Pointer phai cuon ve 0 sau khi cham cuoi mang!"

    print("\n[THANH CONG] DA HOAN THANH MO PHONG KENH PHAN CUNG DMA CIRCULAR ZERO-CPU CHO DRONE!")
