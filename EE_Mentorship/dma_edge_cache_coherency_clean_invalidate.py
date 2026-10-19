"""
Hardware D-Cache Coherency Hazards & Cache Maintenance Operations (Clean / Invalidate)
Chuyen de 24: Zero-Copy Scatter-Gather DMA & Hardware Cache Coherency
Milestone AK.2 - Bai hoc 93 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Mo phong co che hoat dong cua bo nho dem D-Cache 64-byte Cache Line (Write-Back Policy).
- Minh hoa 2 nghich ly Cache Hazard gay loi bo nho khi CPU va DMA tuong tac voi DRAM.
- Thuc thi cac thao tac phan cung chuan: Cache Clean (Flush), Cache Invalidate va Cache Clean & Invalidate.
- Phan tich tam quan trong cua can chinh bo nho 64-Byte Cache Line Alignment.
"""

from typing import Dict, Optional, Tuple


CACHE_LINE_SIZE = 64  # Kich thuoc 1 dong D-Cache chuan tren ARM Cortex-A va Apple Silicon


class CacheLine:
    """Dai dien cho 1 dong D-Cache trong CPU"""
    def __init__(self, tag: int = 0):
        self.tag = tag
        self.data = bytearray(CACHE_LINE_SIZE)
        self.valid = False
        self.dirty = False  # True neu CPU da ghi nhung chua Write-Back xuong DRAM


class CpuDataCache:
    """
    Bo dieu khien D-Cache cua CPU voi chien luoc ghi Write-Back (WB) va Write-Allocate.
    """
    def __init__(self, dram_memory: bytearray, num_lines: int = 16):
        self.dram = dram_memory
        self.num_lines = num_lines
        # Direct-mapped cache don gian cho muc dich mo phong truc quan
        self.lines: Dict[int, CacheLine] = {i: CacheLine() for i in range(num_lines)}
        self.read_hits = 0
        self.read_misses = 0

    def _get_line_idx_and_tag(self, phys_addr: int) -> Tuple[int, int, int]:
        line_offset = phys_addr % CACHE_LINE_SIZE
        line_addr = phys_addr - line_offset
        line_idx = (line_addr // CACHE_LINE_SIZE) % self.num_lines
        tag = line_addr // (CACHE_LINE_SIZE * self.num_lines)
        return line_idx, tag, line_offset

    def cpu_read(self, phys_addr: int, length: int) -> bytes:
        """CPU doc du lieu tu bo nho: Uu tien doc tu D-Cache neu Hit"""
        result = bytearray()
        for offset in range(length):
            curr_addr = phys_addr + offset
            l_idx, tag, l_offset = self._get_line_idx_and_tag(curr_addr)
            line = self.lines[l_idx]

            # Kiem tra Cache Hit
            if line.valid and line.tag == tag:
                self.read_hits += 1
                result.append(line.data[l_offset])
            else:
                # Cache Miss -> Nap 64-byte dong moi tu DRAM vao Cache
                self.read_misses += 1
                # Neu dong cu dang Dirty, phai Write-Back xuong DRAM truoc khi nap dong moi
                if line.valid and line.dirty:
                    evict_addr = (line.tag * self.num_lines + l_idx) * CACHE_LINE_SIZE
                    self.dram[evict_addr:evict_addr + CACHE_LINE_SIZE] = line.data

                # Nap tu DRAM
                base_addr = curr_addr - l_offset
                line.data[:] = self.dram[base_addr:base_addr + CACHE_LINE_SIZE]
                line.tag = tag
                line.valid = True
                line.dirty = False
                result.append(line.data[l_offset])

        return bytes(result)

    def cpu_write(self, phys_addr: int, data: bytes):
        """
        CPU ghi du lieu: Chien luoc Write-Back
        Chi ghi vao D-Cache va bat co Dirty = True, CHUA ghi vao DRAM!
        """
        for offset, byte_val in enumerate(data):
            curr_addr = phys_addr + offset
            l_idx, tag, l_offset = self._get_line_idx_and_tag(curr_addr)
            line = self.lines[l_idx]

            if not (line.valid and line.tag == tag):
                # Miss on write -> Nap dong tu DRAM vao Cache roi moi sua
                if line.valid and line.dirty:
                    evict_addr = (line.tag * self.num_lines + l_idx) * CACHE_LINE_SIZE
                    self.dram[evict_addr:evict_addr + CACHE_LINE_SIZE] = line.data
                base_addr = curr_addr - l_offset
                line.data[:] = self.dram[base_addr:base_addr + CACHE_LINE_SIZE]
                line.tag = tag
                line.valid = True

            line.data[l_offset] = byte_val
            line.dirty = True  # Danh dau dong Cache Line bi ban (Dirty)

    def cache_clean(self, phys_addr: int, length: int):
        """
        Thao tac D-Cache CLEAN (Flush / Write-Back):
        Ep dong Cache bi ban phai ghi tuc thi xuong DRAM.
        Sau do dat Dirty = False. Valid van giu nguyen.
        BAT BUOC THUC HIEN TRUOC KHI DMA TRUYEN DI (DMA-TX).
        """
        start_line = phys_addr // CACHE_LINE_SIZE
        end_line = (phys_addr + length - 1) // CACHE_LINE_SIZE

        for line_num in range(start_line, end_line + 1):
            curr_addr = line_num * CACHE_LINE_SIZE
            l_idx, tag, _ = self._get_line_idx_and_tag(curr_addr)
            line = self.lines[l_idx]
            if line.valid and line.tag == tag and line.dirty:
                # Ghi xuong DRAM
                self.dram[curr_addr:curr_addr + CACHE_LINE_SIZE] = line.data
                line.dirty = False

    def cache_invalidate(self, phys_addr: int, length: int):
        """
        Thao tac D-Cache INVALIDATE:
        Huy bo gia tri trong D-Cache (Valid = False).
        Ep CPU lan doc toi phai truy xuat truc tiep tu DRAM.
        BAT BUOC THUC HIEN TRUOC KHI CPU DOC VUNG BO DEM DMA RX.
        """
        start_line = phys_addr // CACHE_LINE_SIZE
        end_line = (phys_addr + length - 1) // CACHE_LINE_SIZE

        for line_num in range(start_line, end_line + 1):
            curr_addr = line_num * CACHE_LINE_SIZE
            l_idx, tag, _ = self._get_line_idx_and_tag(curr_addr)
            line = self.lines[l_idx]
            if line.valid and line.tag == tag:
                line.valid = False
                line.dirty = False


class HardwareDmaController:
    """
    Bo dieu khien DMA truc tiep truy xuat DRAM, hoan toan bo qua D-Cache.
    """
    def __init__(self, dram_memory: bytearray):
        self.dram = dram_memory

    def dma_transmit_from_dram(self, phys_addr: int, length: int) -> bytes:
        """DMA doc tu DRAM de truyen ra ngoai vi (DMA TX)"""
        return bytes(self.dram[phys_addr:phys_addr + length])

    def dma_receive_to_dram(self, phys_addr: int, data: bytes):
        """DMA nhan du lieu tu ngoai vi ghi thang vao DRAM (DMA RX)"""
        self.dram[phys_addr:phys_addr + len(data)] = data


def test_cache_coherency_pipeline():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN D-CACHE COHERENCY HAZARDS & CLEAN/INVALIDATE")
    print("=" * 80)

    # 1. Khoi tao DRAM vat ly 64 KB va D-Cache CPU
    dram = bytearray(64 * 1024)
    cpu_cache = CpuDataCache(dram, num_lines=16)
    dma = HardwareDmaController(dram)

    BUFFER_TX_ADDR = 0x1000  # Dia chi can chinh 64-byte (4096)
    BUFFER_RX_ADDR = 0x2000  # Dia chi can chinh 64-byte (8192)

    # =========================================================================
    # THI NGHIEM 1: NGHICH LY DMA TX (CPU GHI DU LIEU, DMA TRUYEN RA NGOAI)
    # =========================================================================
    print("THI NGHIEM 1: Nghich ly DMA-TX (Stale Data Hazard)")
    print("-" * 75)

    # Buoc A1: CPU ghi goi tin vao bo dem TX
    cpu_tx_message = b"TESLA_AUTOPILOT_CRITICAL_STEERING_PACKET_V1"
    cpu_cache.cpu_write(BUFFER_TX_ADDR, cpu_tx_message)

    # Kiem tra trong DRAM:
    dram_raw_before_clean = dma.dma_transmit_from_dram(BUFFER_TX_ADDR, len(cpu_tx_message))
    print(f"-> Du lieu CPU vua ghi vao bo nho           : {cpu_tx_message.decode('ascii')}")
    print(f"-> Du lieu thuc te trong DRAM (chua Clean)   : {dram_raw_before_clean.decode('ascii', errors='replace')}")
    print(f"-> Phat hien Hazard                          : {'DRAM BI CU (STALE DATA)!' if dram_raw_before_clean != cpu_tx_message else 'Dong bo'}")

    # Buoc A2: Neu DMA truyen ngay bay gio, ngoai vi se nhan toan byte 0x00!
    # Giai phap: CPU phai thuc hien Cache Clean
    cpu_cache.cache_clean(BUFFER_TX_ADDR, len(cpu_tx_message))
    dram_raw_after_clean = dma.dma_transmit_from_dram(BUFFER_TX_ADDR, len(cpu_tx_message))
    print(f"-> Thuc hien thao tac phan cung              : D-CACHE CLEAN (Flush to DRAM)")
    print(f"-> Du lieu trong DRAM sau khi Clean          : {dram_raw_after_clean.decode('ascii')}")
    assert dram_raw_after_clean == cpu_tx_message, "Sau khi Clean, DRAM phai chua du lieu moi nhat!"
    print("-> Ket qua DMA TX                            : THANH CONG 100% (Da dong bo DRAM)")

    # =========================================================================
    # THI NGHIEM 2: NGHICH LY DMA RX (DMA GHI VAO DRAM, CPU DOC RA)
    # =========================================================================
    print("-" * 80)
    print("THI NGHIEM 2: Nghich ly DMA-RX (Dirty/Stale Cache Read Hazard)")
    print("-" * 75)

    # Buoc B1: CPU doc vung nho RX truoc do -> D-Cache dang giu ban sao ban dau (Toan 0x00)
    old_cpu_read = cpu_cache.cpu_read(BUFFER_RX_ADDR, 32)
    print(f"-> CPU doc truoc bo dem RX (Cache dang luu)  : {bytes(old_cpu_read[:16])} (Gia tri cu)")

    # Buoc B2: DMA nhan khung anh camera moi ghi truc tiep vao DRAM
    camera_rx_frame = b"CAMERA_SENSOR_RAW12_FRAME_ID_9999"
    dma.dma_receive_to_dram(BUFFER_RX_ADDR, camera_rx_frame)
    print(f"-> Ngoai vi DMA vua nap vao DRAM            : {camera_rx_frame.decode('ascii')}")

    # Buoc B3: Neu CPU doc ma KHONG Invalidate -> CPU se doc phai du lieu cu trong D-Cache!
    stale_cpu_read = cpu_cache.cpu_read(BUFFER_RX_ADDR, len(camera_rx_frame))
    print(f"-> CPU doc ma KHONG Invalidate               : {stale_cpu_read.decode('ascii', errors='replace')}")
    print(f"-> Phat hien Hazard                          : {'CPU DOC PHAI DU LIEU CU TRONG CACHE!' if stale_cpu_read != camera_rx_frame else 'Dong bo'}")

    # Buoc B4: Giai phap - CPU phai thuc hien Cache Invalidate truoc khi doc bo dem DMA RX
    cpu_cache.cache_invalidate(BUFFER_RX_ADDR, len(camera_rx_frame))
    fresh_cpu_read = cpu_cache.cpu_read(BUFFER_RX_ADDR, len(camera_rx_frame))
    print(f"-> Thuc hien thao tac phan cung              : D-CACHE INVALIDATE")
    print(f"-> CPU doc sau khi Invalidate                : {fresh_cpu_read.decode('ascii')}")
    assert fresh_cpu_read == camera_rx_frame, "Sau khi Invalidate, CPU phai doc duoc du lieu moi tu DRAM!"
    print("-> Ket qua DMA RX                            : THANH CONG 100% (CPU da doc dung frame moi)")

    print("-" * 80)
    print("Thong ke hieu nang D-Cache:")
    print(f"-> Cache Hits  : {cpu_cache.read_hits}")
    print(f"-> Cache Misses: {cpu_cache.read_misses}")
    print("=" * 80)
    print("[PASS] Hardware D-Cache Coherency & Maintenance Pipeline: 100% Hoan hao!")


if __name__ == "__main__":
    test_cache_coherency_pipeline()
