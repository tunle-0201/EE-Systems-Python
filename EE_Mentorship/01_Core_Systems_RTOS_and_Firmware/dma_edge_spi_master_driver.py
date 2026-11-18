"""
================================================================================
          MODULE Y: EMBEDDED HARDWARE DRIVERS & ZERO-CPU DMA ACCELERATION
              MILESTONE Y.2: HIGH-SPEED SPI MASTER DRIVER @ 8-50 MHz
================================================================================

TAI SAO SPI LA GIAO THUC SO 1 CHO CAM BIEN TOC DO CAO TRONG DRONE VA ROBOTICS?
Trong he thong nhung thoi gian thuc (Flight Controller STM32F4/H7, Apple Watch S-series):
- SPI (Serial Peripheral Interface) la giao thuc dong bo toan phan (Full-Duplex):
  + Toc do xung nhip vuot troi: Tu 8 MHz den 50 MHz (nhanh hon I2C gap 20 - 50 lan!).
  + 4 duong tin hieu chuan:
    1. SCLK (Serial Clock): Do Master phat de dong bo xung nhip.
    2. MOSI (Master Out Slave In): Du lieu truyen tu Master sang Slave.
    3. MISO (Master In Slave Out): Du lieu phan hoi tu Slave ve Master.
    4. CS / NSS (Chip Select): Chan chon chip tich cuc muc thap (Active Low).

SO DO GIAO TIEP PHAN CUNG SPI VOI CAM BIEN IMU (ASCII HARDWARE DIAGRAM):

   MCU SPI Master (ARM Cortex-M)             IMU Sensor Slave (MPU-6050 / ICM-42688)
   +───────────────────────────+             +─────────────────────────────────────+
   |              CS_PIN (GPIO)| ──(Active Low)───────────────────────────────────>| CS (Chip Select)     |
   |              SPI_SCK (Pin)| ──(8 MHz Clock)──────────────────────────────────>| SCLK                 |
   |             SPI_MOSI (Pin)| ──(Thanh ghi: 0x75)──────────────────────────────>| SDI / MOSI           |
   |             SPI_MISO (Pin)| <──(WHO_AM_I ID: 0x8A)────────────────────────────| SDO / MISO           |
   +───────────────────────────+             +─────────────────────────────────────+

CHE DO PHA VA CUC TINH XUNG NHIP (SPI MODES CPOL / CPHA):
- Mode 0 (CPOL=0, CPHA=0): Xung SCK o muc 0 khi nghi, chot du lieu o suon len dau tien.
- Mode 3 (CPOL=1, CPHA=1): Xung SCK o muc 1 khi nghi, chot du lieu o suon len thu hai.
"""

from typing import Tuple, List, Dict, Any, Optional


class SPIMasterDriver:
    """
    Trinh dieu khien ngoai vi SPI Master Driver toc do cao cho ARM Cortex-M
    Ho tro che do truyen don byte va doc ghi chuoi (Burst Transfer)
    """
    def __init__(self, clock_hz: int = 8_000_000, mode: int = 0):
        self.clock_hz = clock_hz
        self.mode = mode
        self.tx_history: List[int] = []
        self.rx_history: List[int] = []
        self.cs_active = False

    def chip_select(self, active: bool) -> None:
        """Kich hoat / huy kich hoat chan chon chip CS (Active Low)"""
        self.cs_active = active

    def transfer_byte(self, tx_byte: int) -> int:
        """
        Truyen va nhan dong thoi 1 byte qua giao thuc Full-Duplex:
        tx_byte: Byte Master phat di qua MOSI
        Tra ve: Byte Slave phan hoi qua duong MISO
        """
        if not self.cs_active:
            raise RuntimeError("Khong the truyen SPI khi chua keo chan CS xuong muc thap!")

        clean_tx = tx_byte & 0xFF
        self.tx_history.append(clean_tx)

        # Mo phong phan hoi phan cung cua Slave IMU (WHO_AM_I register 0x75 -> 0x8A)
        # Trong mach that: Slave dich thanh ghi Shift Register theo xung Clock
        rx_byte = (clean_tx ^ 0xFF) & 0xFF
        self.rx_history.append(rx_byte)
        return rx_byte

    def transfer_buffer(self, tx_data: bytes) -> bytes:
        """
        Truyen nhan mot chuoi byte lien tiep (Burst Read/Write):
        Thuong dung de doc dong thoi 6 truc Gia toc va Con quay hoi chuyen (Accel + Gyro)
        """
        rx_list = []
        for b in tx_data:
            rx_list.append(self.transfer_byte(b))
        return bytes(rx_list)


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DRIVERS: SPI MASTER DRIVER @ 8 MHz")
    print("=========================================================")

    spi = SPIMasterDriver(clock_hz=8_000_000, mode=0)

    # 1. Kich ban doc thanh ghi ma dinh danh WHO_AM_I (0x75)
    print("\n1. GIAO TIEP DOC THANH GHI WHO_AM_I (MPU-6050 / ICM-42688):")
    spi.chip_select(True)
    reg_addr = 0x75  # Dia chi thanh ghi WHO_AM_I
    response = spi.transfer_byte(reg_addr)
    spi.chip_select(False)

    print(f"   -> Tan so Clock SPI          : {spi.clock_hz / 1e6:.1f} MHz")
    print(f"   -> Byte Master gui qua MOSI  : 0x{reg_addr:02X}")
    print(f"   -> Byte Slave tra qua MISO   : 0x{response:02X}")

    assert response == (0x75 ^ 0xFF) & 0xFF, "Loi du lieu SPI nhan ve khong khop!"
    assert response == 0x8A, "Phan hoi phai la 0x8A (ID cam bien hop le)!"

    # 2. Kich ban doc Burst nhieu byte du lieu cam bien 6 truc
    print("\n2. TEST DOC CHUOI BURST TRANSFER 6 TRUC IMU (ACCEL + GYRO):")
    spi.chip_select(True)
    burst_tx = bytes([0x3B, 0x00, 0x00, 0x00, 0x00, 0x00])  # Dia chi goc + 5 dummy bytes
    burst_rx = spi.transfer_buffer(burst_tx)
    spi.chip_select(False)

    print(f"   -> So byte truyen nhan       : {len(burst_rx)} bytes")
    print(f"   -> Chuoi hex nhan duoc       : {[f'0x{b:02X}' for b in burst_rx]}")

    assert len(burst_rx) == 6, "Phai nhan du 6 bytes tuong ung 6 truc cam bien!"

    print("\n[THANH CONG] DA HOAN THANH BO DIEU KHIEN SPI MASTER 8MHz CHO CAM BIEN DRONE!")
