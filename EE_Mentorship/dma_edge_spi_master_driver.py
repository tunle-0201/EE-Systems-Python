"""
================================================================================
          MODULE T: EMBEDDED HARDWARE DRIVERS & DMA ACCELERATION
              MILESTONE T.2: BỘ ĐIỀU KHIỂN SPI MASTER (SPI MASTER DRIVER)
================================================================================

TẠI SAO SPI LÀ GIAO THỨC SỐ 1 KẾT NỐI CẢM BIẾN TỐC ĐỘ CAO TRONG DRONE?
SPI (Serial Peripheral Interface):
- Tốc độ lên đến 50 MHz (nhanh hơn I2C 50 lần).
- 4 dây: SCLK (Clock), MOSI (Master Out), MISO (Master In), CS (Chip Select).
- Drone dùng SPI để đọc cảm biến IMU MPU-6050, Barometer BMP388 ở tần số 1000Hz!
"""

class SPIMasterDriver:
    def __init__(self, clock_hz=8_000_000):
        self.clock_hz = clock_hz
        self.tx_buffer = []
        self.rx_buffer = []
        self.cs_active = False

    def chip_select(self, active: bool):
        self.cs_active = active

    def transfer_byte(self, tx_byte: int) -> int:
        """
        Trò đóng vai Kỹ sư vi điều khiển:
        - Nạp byte vào tx_buffer
        - Giả lập phản hồi MISO = (tx_byte ^ 0xFF) & 0xFF
        - Nạp phản hồi vào rx_buffer
        - Trả về: rx_byte
        """
        self.tx_buffer.append(tx_byte)
        rx_byte = (tx_byte ^ 0xFF) & 0xFF
        self.rx_buffer.append(rx_byte)
        return rx_byte


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: SPI MASTER DRIVER @ 8 MHz")
    print("=========================================================\n")

    spi = SPIMasterDriver(clock_hz=8_000_000)
    spi.chip_select(True)
    
    reg_addr = 0x75  # WHO_AM_I register của IMU MPU-6050
    response = spi.transfer_byte(reg_addr)
    
    spi.chip_select(False)
    
    print("1. KET QUA GIAO TIEP SPI VOI CAM BIEN IMU MPU-6050:")
    print(f"   -> Byte gui di (TX)    : 0x{reg_addr:02X}")
    print(f"   -> Byte nhan ve (MISO) : 0x{response:02X}")
    
    assert response == (0x75 ^ 0xFF) & 0xFF, "Loi SPI Transfer!"
    print("\n[THANH CONG] DA HOAN THANH BO DIEU KHIEN SPI MASTER 8MHz CHO CAM BIEN DRONE!")
