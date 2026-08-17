"""
================================================================================
          MODULE F: EMBEDDED REAL-TIME DRONE FLIGHT CONTROL & ROBOTICS
              MILESTONE F.2: VÒNG ĐỆM RING BUFFER FIFO UART TRUYỀN DỮ LIỆU TỐC ĐỘ CAO
================================================================================

TẠI SAO CẦN RING BUFFER FIFO CHO TRUYỀN THÔNG DRONE?
Khi truyền gói tin Telemetry 100Hz qua UART DMA:
- Nếu CPU bận xử lý AI, dữ liệu từ cảm biến gửi về sẽ bị tràn RAM (Overflow).
- Kỹ sư EE dùng **Ring Buffer (Vòng đệm tròn FIFO)** để lưu tạm gói tin tốc độ cao.
"""

class UARTDMABytesRingBuffer:
    def __init__(self, capacity=1024):
        self.capacity = capacity
        self.buffer = bytearray(capacity)
        self.head = 0
        self.tail = 0
        self.size = 0
    
    def write(self, data: bytes):
        for b in data:
            self.buffer[self.head] = b
            self.head = (self.head + 1) % self.capacity
            if self.size < self.capacity:
                self.size += 1
            else:
                self.tail = (self.tail + 1) % self.capacity # Ghi đè cũ nhất
    
    def read(self, length: int) -> bytes:
        read_bytes = bytearray()
        for _ in range(min(length, self.size)):
            read_bytes.append(self.buffer[self.tail])
            self.tail = (self.tail + 1) % self.capacity
            self.size -= 1
        return bytes(read_bytes)


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE EMBEDDED SYSTEM: UART DMA RING BUFFER FIFO")
    print("=========================================================\n")
    
    rb = UARTDMABytesRingBuffer(capacity=64)
    rb.write(b"DRONE_TELEMETRY_PACKET_OK")
    read_data = rb.read(25)
    
    print("1. KET QUA QUAN LY VONG DEM RING BUFFER REAL-TIME:")
    print(f"   -> Du lieu doc tu UART DMA Buffer : {read_data.decode()}")
    
    assert read_data == b"DRONE_TELEMETRY_PACKET_OK", "Loi Ring Buffer!"
    print("\n[THANH CONG] DA HOAN THANH VONG DEM RING BUFFER TRUYEN DU LIEU NOC DO CAO!")
