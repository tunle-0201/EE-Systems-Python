"""
================================================================================
          MODULE AB CAPSTONE FINALE: BỘ ĐIỀU KHIỂN KẾT NỐI GPU PCIE GEN4/5
================================================================================

TÍCH HỢP TOÀN BỘ PCIE STACK: TLP ENCODER + SCATTER-GATHER DMA + MSI-X ARBITER
"""

from pcie_edge_tlp_packet_encoder import encode_pcie_tlp_mwr_header
from pcie_edge_scatter_gather_dma import DmaDescriptor, ScatterGatherDmaEngine
from pcie_edge_msix_vector_arbiter import MsixTableArbiter

def run_pcie_accelerator_interconnect_engine():
    # 1. Đóng gói TLP Memory Write 64 Dwords
    tlp = encode_pcie_tlp_mwr_header((1, 0, 0), 0x90000000, 64)

    # 2. Scatter-Gather DMA truyền 2 trang dữ liệu hình ảnh 4K
    sg_chain = [
        DmaDescriptor(0x10000000, 4096, is_last=False),
        DmaDescriptor(0x20000000, 4096, is_last=True)
    ]
    dma = ScatterGatherDmaEngine()
    transferred = dma.execute_chain(sg_chain)

    # 3. Kích hoạt ngắt MSI-X Vector 0 báo hoàn tất tới CPU Core
    msix = MsixTableArbiter(num_vectors=8)
    irq = msix.trigger_interrupt(vector_id=0)

    return len(tlp), transferred, irq[1]


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AB CAPSTONE: PCIE GPU INTERCONNECT ENGINE")
    print("=========================================================\n")

    tlp_len, dma_bytes, irq_code = run_pcie_accelerator_interconnect_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI PCIE GPU INTERCONNECT:")
    print(f"   -> Do dai TLP Header          : {tlp_len} Dwords (12 bytes)")
    print(f"   -> Scatter-Gather DMA Bytes   : {dma_bytes} bytes")
    print(f"   -> MSI-X Interrupt Vector Code: 0x{irq_code:04X}")

    assert tlp_len == 3 and dma_bytes == 8192 and irq_code == 0x100, "Loi Capstone PCIe!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AB: PCIE INTERCONNECTS!")
    print("=========================================================")
