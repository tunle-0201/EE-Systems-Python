"""
================================================================================
          MODULE Y: EMBEDDED HARDWARE DRIVERS & ZERO-CPU DMA ACCELERATION
              MILESTONE Y.4: CAPSTONE ARM CORTEX-M EMBEDDED FIRMWARE ENGINE
================================================================================

KIEN TRUC NEN TANG TRINH DIEU KHIEN PHAN CUNG EMBEDDED FIRMWARE ENGINE:
Tren cac thiet bi bay khong gian va he thong tu hanh hien dai (ARM Cortex-M4/M7):
- Tich hop toan bo 3 tang dieu khien phan cung cap thap vao mot dong co dong bo:
  1. High-Speed SPI Master: Giao tiep doc/ghi thanh ghi cam bien IMU o tan so 8 MHz.
  2. Circular DMA Channel: Nhan du lieu cam bien toc do cao vao RAM voi 0% CPU Load.
  3. Hardware NVIC Queue: Phan xu ngat long nhau theo muc uu tien nghiem ngat, dam bao
     ngat DMA Transfer Complete luon duoc phuc vu truoc ngat truyen thong UART/CAN.

SO DO KHOI TICH HOP HE THONG PHAN CUNG (ASCII ARCHITECTURE DIAGRAM):

   +───────────────────────────────────────────────────────────────────────────+
   |             ARM CORTEX-M EMBEDDED HARDWARE FIRMWARE STACK                 |
   +───────────────────────────────────────────────────────────────────────────+
          |                                   |                    |
          v                                   v                    v
   [ SPI Master Driver ]             [ Circular DMA ]     [ NVIC Priority Queue ]
   - 8 MHz Full-Duplex               - Ping-Pong SRAM     - Min-Heap O(log N)
   - Read WHO_AM_I (0x75)            - Zero-CPU Stream    - Preemption Priority
   - Chip Select (CS Active Low)     - HT & TC Flags      - DMA_TC (Pri 0) > UART (Pri 3)
          |                                   |                    |
          +───────────────────────────────────+────────────────────+
                                              |
                                              v
                              [ Flight Engine Task Loop ]
                              (Sensor Fusion & Real-Time Control)
"""

from typing import Tuple, List, Dict, Any, Optional

from dma_edge_circular_channel import HardwareDMAChannel
from dma_edge_spi_master_driver import SPIMasterDriver
from dma_edge_nvic_irq_queue import InterruptPriorityQueue


class EmbeddedFirmwareEngine:
    """
    Dong co dieu hanh trinh dieu khien phan cung ARM Cortex-M
    Tich hop dong bo SPI Master, Circular DMA va NVIC Priority Queue
    """
    def __init__(self, dma_buffer_size: int = 16, spi_clock_hz: int = 8_000_000):
        self.dma = HardwareDMAChannel(buffer_size=dma_buffer_size)
        self.spi = SPIMasterDriver(clock_hz=spi_clock_hz)
        self.nvic = InterruptPriorityQueue()
        self.system_healthy = False

    def initialize_and_test_imu(self, who_am_i_reg: int = 0x75) -> int:
        """Kiem tra ket noi vat ly SPI toi cam bien IMU"""
        self.spi.chip_select(True)
        response = self.spi.transfer_byte(who_am_i_reg)
        self.spi.chip_select(False)
        return response

    def stream_telemetry_via_dma(self, telemetry_bytes: bytes) -> bool:
        """Truyen chuoi du lieu cam bien qua kenh DMA phan cung"""
        for b in telemetry_bytes:
            self.dma.transfer_byte(b)
        return self.dma.transfer_complete_flag

    def schedule_system_interrupts(self) -> str:
        """Kich hoat cac ngat he thong va lay ngat duoc uu tien xu ly dau tien"""
        self.nvic.trigger_irq("UART_RX", priority=3)
        self.nvic.trigger_irq("DMA_TC",  priority=0)  # Uu tien toi cao
        self.nvic.trigger_irq("TIMER_MS", priority=2)
        return self.nvic.service_next_irq()


def run_embedded_firmware_engine() -> Tuple[bool, int, str]:
    """
    Ham wrapper capstone dong bo toan chuoi kiem thu cac milestone Y.1, Y.2, Y.3
    Tra ve: (dma_transfer_complete, spi_who_am_i_response, first_serviced_irq)
    """
    # 1. Khoi tao kenh DMA doc du lieu cam bien (8 bytes)
    dma = HardwareDMAChannel(buffer_size=8)
    for i in range(8):
        dma.transfer_byte(i * 5)

    # 2. SPI doc thanh ghi WHO_AM_I cua IMU (0x75 -> 0x8A)
    spi = SPIMasterDriver(clock_hz=8_000_000)
    spi.chip_select(True)
    who_am_i = spi.transfer_byte(0x75)
    spi.chip_select(False)

    # 3. NVIC uu tien xu ly ngat DMA_TC truoc UART_RX
    nvic = InterruptPriorityQueue()
    nvic.trigger_irq("UART_RX", priority=3)
    nvic.trigger_irq("DMA_TC",  priority=0)
    first_irq = nvic.service_next_irq()

    return bool(dma.transfer_complete_flag), int(who_am_i), str(first_irq)


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Y CAPSTONE: ARM CORTEX-M EMBEDDED FIRMWARE ENGINE")
    print("=========================================================\n")

    # 1. Kiem tra toan chuoi qua ham wrapper
    dma_done, spi_resp, irq = run_embedded_firmware_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI FIRMWARE ENGINE PHAN CUNG:")
    print(f"   -> DMA Transfer Complete : {dma_done}")
    print(f"   -> SPI WHO_AM_I Response : 0x{spi_resp:02X}")
    print(f"   -> IRQ Xu ly dau tien   : {irq}\n")

    assert dma_done is True, "DMA phai hoan tat du chu trinh!"
    assert spi_resp == 0x8A, "Phan hoi SPI WHO_AM_I phai dung 0x8A!"
    assert irq == "DMA_TC", "Ngat DMA_TC priority 0 phai duoc NVIC phuc vu dau tien!"

    # 2. Mo phong bang dong co he thong toan dien (Full Firmware Engine Simulation)
    engine = EmbeddedFirmwareEngine(dma_buffer_size=16, spi_clock_hz=8_000_000)
    sensor_id = engine.initialize_and_test_imu(who_am_i_reg=0x75)
    dma_status = engine.stream_telemetry_via_dma(bytes(range(16)))
    top_irq = engine.schedule_system_interrupts()

    print("2. TELEMETRY DONG CO FIRMWARE HE THONG (SYSTEM STACK):")
    print(f"   -> Kiem tra ID Cam bien IMU  : 0x{sensor_id:02X} (Giao tiep thanh cong)")
    print(f"   -> Nap mang Circular DMA     : {'HOAN TAT VA CUON TRON' if dma_status else 'CHUA DAY'}")
    print(f"   -> Ngat chien luoc dau tien  : {top_irq} (Priority 0 Preempted)")

    assert sensor_id == 0x8A and dma_status is True and top_irq == "DMA_TC"

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE Y: EMBEDDED HARDWARE DRIVERS!")
    print("=========================================================")
