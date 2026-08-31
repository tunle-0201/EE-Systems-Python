"""
================================================================================
          MODULE T CAPSTONE FINALE: FIRMWARE ENGINE CHO CHIP NHÚNG ARM CORTEX-M
================================================================================

TÍCH HỢP TOÀN BỘ HARDWARE DRIVER STACK: DMA CIRCULAR + SPI MASTER + NVIC IRQ QUEUE
"""

from dma_edge_circular_channel import HardwareDMAChannel
from dma_edge_spi_master_driver import SPIMasterDriver
from dma_edge_nvic_irq_queue import InterruptPriorityQueue

def run_embedded_firmware_engine():
    # 1. Khởi tạo kênh DMA đọc dữ liệu cảm biến
    dma = HardwareDMAChannel(buffer_size=8)
    for i in range(8):
        dma.transfer_byte(i * 5)

    # 2. SPI đọc thanh ghi WHO_AM_I của IMU
    spi = SPIMasterDriver(clock_hz=8_000_000)
    spi.chip_select(True)
    who_am_i = spi.transfer_byte(0x75)
    spi.chip_select(False)

    # 3. NVIC ưu tiên xử lý ngắt DMA_TC trước UART
    nvic = InterruptPriorityQueue()
    nvic.trigger_irq("UART_RX", priority=3)
    nvic.trigger_irq("DMA_TC",  priority=0)
    first_irq = nvic.service_next_irq()

    return dma.transfer_complete_flag, who_am_i, first_irq


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE T CAPSTONE: ARM CORTEX-M EMBEDDED FIRMWARE ENGINE")
    print("=========================================================\n")

    dma_done, spi_resp, irq = run_embedded_firmware_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI FIRMWARE ENGINE PHAN CUNG:")
    print(f"   -> DMA Transfer Complete : {dma_done}")
    print(f"   -> SPI WHO_AM_I Response : 0x{spi_resp:02X}")
    print(f"   -> IRQ Xu ly dau tien   : {irq}")

    assert dma_done == True and spi_resp == 0x8A and irq == "DMA_TC", "Loi Capstone Firmware!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE T: EMBEDDED HARDWARE DRIVERS!")
    print("=========================================================")
