"""
================================================================================
          MODULE T: EMBEDDED HARDWARE DRIVERS & DMA ACCELERATION
              MILESTONE T.1: KÊNH TRUYỀN BỘ NHỚ TRỰC TIẾP (CIRCULAR DMA CONTROLLER)
================================================================================

TẠI SAO CÁC CHIP ARM CORTEX (STM32, ESP32) DÙNG DMA ĐỂ TIẾT KIỆM 100% CPU?
DMA (Direct Memory Access):
- Tự động chuyển các khối dữ liệu từ Ngoại vi (UART/SPI) vào RAM mà không cần CPU can thiệp.
- Chế độ Circular Mode: Khi đầy mảng, DMA tự động cuộn lại ô đầu tiên và kích hoạt cờ ngắt Half-Transfer / Transfer-Complete!
"""

class HardwareDMAChannel:
    def __init__(self, buffer_size=128):
        self.buffer_size = buffer_size
        self.buffer = bytearray(buffer_size)
        self.dma_pointer = 0
        self.half_transfer_flag = False
        self.transfer_complete_flag = False
    
    def transfer_byte(self, incoming_byte: int):
        self.buffer[self.dma_pointer] = incoming_byte
        self.dma_pointer += 1
        
        if self.dma_pointer == self.buffer_size // 2:
            self.half_transfer_flag = True
        elif self.dma_pointer >= self.buffer_size:
            self.transfer_complete_flag = True
            self.dma_pointer = 0 # Cuộn tròn Circular Mode


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: CIRCULAR DMA CONTROLLER SIMULATOR")
    print("=========================================================\n")
    
    dma = HardwareDMAChannel(buffer_size=10)
    
    # Bơm 10 bytes dữ liệu cảm biến vào DMA
    for b in range(10):
        dma.transfer_byte(b * 10)
    
    print("1. KET QUA HOAT DONG KENH DMA PHAN CUNG REAL-TIME:")
    print(f"   -> Half Transfer Flag (HT) : {dma.half_transfer_flag}")
    print(f"   -> Transfer Complete (TC)  : {dma.transfer_complete_flag}")
    print(f"   -> Pointer sau khi cuon    : {dma.dma_pointer}")
    
    assert dma.half_transfer_flag == True and dma.transfer_complete_flag == True and dma.dma_pointer == 0, "Loi DMA Channel!"
    print("\n[THANH CONG] DA HOAN THANH MO PHONG KENH PHAN CUNG DMA CIRCULAR ZERO-CPU CHO DRONE!")
