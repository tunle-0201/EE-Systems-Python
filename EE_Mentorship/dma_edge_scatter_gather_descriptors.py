"""
Scatter-Gather DMA Hardware Descriptors & Chained Ring Buffer Engine
Chuyen de 24: Zero-Copy Scatter-Gather DMA & Hardware Cache Coherency
Milestone AK.1 - Bai hoc 92 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Mo phong bang mo ta phan cung Scatter-Gather DMA Descriptors (SG-DMA Chained Ring).
- Quan ly chuyen giao quyen so huu bo dem giua CPU va DMA Engine qua bit OWN.
- Kiem soat truyen du lieu khong lien tuc trong bo nho vat ly DRAM (Zero-Copy Scattering/Gathering).
"""

import struct
from enum import IntFlag
from typing import List, Dict, Tuple, Optional


class DmaControlFlags(IntFlag):
    OWN = 1 << 31       # 1: Hardware DMA Engine so huu; 0: CPU / Software so huu
    IOC = 1 << 30       # Interrupt On Completion: Kich hoat ngat phan cung khi xong
    SOF = 1 << 29       # Start Of Frame: Mo ta bat dau mot khung du lieu moi
    EOF = 1 << 28       # End Of Frame: Mo ta ket thuc khung du lieu
    EOR = 1 << 27       # End Of Ring: Mo ta cuoi cung, tro nguoc ve dau vong tron
    ERROR = 1 << 26     # Co bao loi phan cung duong truyen Bus Error


class DmaDescriptor:
    """
    Cau truc Descriptor phan cung 32-byte chuan ARM AXI DMA / Synopsys DesignWare.
    Kich thuoc: 32 bytes (khop 1/2 Cache Line 64-byte).
    """
    FORMAT = "<QQIIQ"  # 8 + 8 + 4 + 4 + 8 = 32 bytes

    def __init__(self, desc_addr: int, src_addr: int, dst_addr: int, byte_count: int,
                 flags: int, next_desc_addr: int):
        self.desc_addr = desc_addr
        self.src_addr = src_addr
        self.dst_addr = dst_addr
        self.byte_count = byte_count
        self.flags = flags
        self.next_desc_addr = next_desc_addr
        self.bytes_transferred = 0

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.src_addr, self.dst_addr, self.byte_count,
                           self.flags, self.next_desc_addr)

    @classmethod
    def unpack(cls, desc_addr: int, raw_bytes: bytes) -> 'DmaDescriptor':
        src, dst, count, flags, next_addr = struct.unpack(cls.FORMAT, raw_bytes)
        return cls(desc_addr, src, dst, count, flags, next_addr)


class SimulatedPhysicalMemory:
    """
    Gia lap bo nho vat ly DRAM (Physical Address Space) cua SoC.
    Ho tro doc ghi theo dai dia chi 64-bit.
    """
    def __init__(self, size_bytes: int = 1024 * 1024):
        self.size = size_bytes
        self.memory = bytearray(size_bytes)

    def write(self, phys_addr: int, data: bytes):
        if phys_addr + len(data) > self.size:
            raise MemoryError(f"Ghi vuot qua bo nho vat ly: {phys_addr} + {len(data)} > {self.size}")
        self.memory[phys_addr:phys_addr + len(data)] = data

    def read(self, phys_addr: int, length: int) -> bytes:
        if phys_addr + length > self.size:
            raise MemoryError(f"Doc vuot qua bo nho vat ly: {phys_addr} + {length} > {self.size}")
        return bytes(self.memory[phys_addr:phys_addr + length])


class ScatterGatherDmaEngine:
    """
    Bo dieu khien phan cung Scatter-Gather DMA Controller (Hardware AXI Master).
    Tu dong duyet danh sach Descriptor trong DRAM va truyen du lieu Zero-Copy.
    """
    def __init__(self, dram: SimulatedPhysicalMemory):
        self.dram = dram
        self.current_desc_addr: Optional[int] = None
        self.is_busy = False
        self.irq_triggered = False
        self.total_bytes_moved = 0
        self.descriptors_processed = 0

    def start_transfer(self, head_desc_addr: int):
        """Kich hoat bo phan cung DMA chay tu Descriptor dau tien"""
        self.current_desc_addr = head_desc_addr
        self.is_busy = True
        self.irq_triggered = False

    def step_process_descriptor(self) -> Dict[str, any]:
        """
        Mot chu ky phan cung xu ly mot Descriptor:
        1. Fetch Descriptor tu DRAM
        2. Kiem tra co OWN
        3. Thuc hien DMA Burst Transfer tu src sang dst
        4. Xoa co OWN, cap nhat bytes_transferred
        5. Kich hoat IRQ neu bat co IOC
        6. Chuyen sang next_desc_addr
        """
        if not self.is_busy or self.current_desc_addr is None:
            return {"status": "IDLE"}

        # 1. Fetch Descriptor (32 bytes) tu DRAM
        desc_raw = self.dram.read(self.current_desc_addr, 32)
        desc = DmaDescriptor.unpack(self.current_desc_addr, desc_raw)

        # 2. Kiem tra quyen so huu (Ownership check)
        if not (desc.flags & DmaControlFlags.OWN):
            # DMA gap Descriptor do CPU quan ly -> Dung cho den khi CPU cap phat
            self.is_busy = False
            return {"status": "STALL_NOT_OWNED", "desc_addr": self.current_desc_addr}

        # 3. Thuc hien truyen du lieu Burst qua bus noi bo
        payload = self.dram.read(desc.src_addr, desc.byte_count)
        self.dram.write(desc.dst_addr, payload)
        self.total_bytes_moved += desc.byte_count
        self.descriptors_processed += 1

        # 4. Tra quyen so huu ve cho CPU (Clear OWN bit)
        desc.flags &= ~DmaControlFlags.OWN
        self.dram.write(self.current_desc_addr, desc.pack())

        # 5. Kiem tra ngat hoan tat (Interrupt On Completion)
        irq_fired = False
        if desc.flags & DmaControlFlags.IOC:
            self.irq_triggered = True
            irq_fired = True

        result = {
            "status": "DESC_TRANSFERRED",
            "desc_addr": self.current_desc_addr,
            "bytes": desc.byte_count,
            "src": desc.src_addr,
            "dst": desc.dst_addr,
            "irq_fired": irq_fired,
            "is_eof": bool(desc.flags & DmaControlFlags.EOF)
        }

        # 6. Chuyen sang Descriptor tiep theo
        self.current_desc_addr = desc.next_desc_addr

        return result


def test_scatter_gather_dma():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN SCATTER-GATHER DMA DESCRIPTORS & CHAINED RING")
    print("=" * 80)

    # 1. Khoi tao DRAM vat ly (1 MB)
    dram = SimulatedPhysicalMemory(size_bytes=1024 * 1024)

    # Dia chi co so (Base Addresses)
    DESC_RING_BASE = 0x10000  # 64 KB
    SRC_BUFFER_BASE = 0x20000 # 128 KB
    DST_BUFFER_BASE = 0x30000 # 192 KB

    # 2. Tao 4 doan du lieu nam rai rac (Scattered Blocks) trong DRAM
    # Mo phong viec tap hop du lieu tu cac vung nho khong lien tuc (Zero-Copy Gathering)
    block_sizes = [128, 256, 512, 1024]  # Tong cong 1920 bytes
    num_blocks = len(block_sizes)

    # Ghi du lieu mau vao cac vung src
    src_addrs = []
    dst_addrs = []
    current_src = SRC_BUFFER_BASE
    current_dst = DST_BUFFER_BASE

    for i, size in enumerate(block_sizes):
        src_addrs.append(current_src)
        dst_addrs.append(current_dst)
        # Tao du lieu dac trung cho tung block
        pattern = bytes([(i * 37 + j) % 256 for j in range(size)])
        dram.write(current_src, pattern)
        
        current_src += size + 64  # Cach nhau 64 byte de dam bao khong lien tuc
        current_dst += size

    # 3. Xay dung chuoi lien ket Descriptors Chained Ring trong DRAM
    desc_addrs = [DESC_RING_BASE + i * 32 for i in range(num_blocks)]

    print("Khoi tao chuoi Scatter-Gather DMA Descriptors:")
    print("STT | Desc Addr | Src Addr   | Dst Addr   | Size (B) | Flags (SOF/EOF/IOC/OWN)")
    print("-" * 75)

    for i in range(num_blocks):
        flags = DmaControlFlags.OWN  # Trao quyen cho DMA
        if i == 0:
            flags |= DmaControlFlags.SOF
        if i == num_blocks - 1:
            flags |= DmaControlFlags.EOF | DmaControlFlags.IOC | DmaControlFlags.EOR
            next_addr = desc_addrs[0]  # Tro nguoc ve dau vong tron (Chained Ring)
        else:
            next_addr = desc_addrs[i + 1]

        desc = DmaDescriptor(
            desc_addr=desc_addrs[i],
            src_addr=src_addrs[i],
            dst_addr=dst_addrs[i],
            byte_count=block_sizes[i],
            flags=flags,
            next_desc_addr=next_addr
        )
        dram.write(desc_addrs[i], desc.pack())

        flag_str = []
        if flags & DmaControlFlags.OWN: flag_str.append("OWN")
        if flags & DmaControlFlags.SOF: flag_str.append("SOF")
        if flags & DmaControlFlags.EOF: flag_str.append("EOF")
        if flags & DmaControlFlags.IOC: flag_str.append("IOC")
        print(f"{i+1:3d} | 0x{desc_addrs[i]:06X} | 0x{src_addrs[i]:06X} | 0x{dst_addrs[i]:06X} | {block_sizes[i]:8d} | {' | '.join(flag_str)}")

    print("-" * 80)

    # 4. Kich hoat Hardware DMA Engine
    dma = ScatterGatherDmaEngine(dram)
    dma.start_transfer(head_desc_addr=desc_addrs[0])

    print("Bo phan cung DMA tien hanh truyen du lieu qua cac Descriptor:")
    for step in range(num_blocks):
        res = dma.step_process_descriptor()
        print(f"-> Xu ly Desc 0x{res['desc_addr']:06X}: Chuyen {res['bytes']} bytes (Tu 0x{res['src']:06X} sang 0x{res['dst']:06X}) | IRQ={res['irq_fired']}")

    # 5. Kiem tra tinh toan ven du lieu (Data Integrity Check)
    print("-" * 80)
    print("Kiem tra tinh toan ven du lieu sau khi truyen Zero-Copy DMA:")
    total_match = True
    for i in range(num_blocks):
        src_data = dram.read(src_addrs[i], block_sizes[i])
        dst_data = dram.read(dst_addrs[i], block_sizes[i])
        is_equal = (src_data == dst_data)
        if not is_equal:
            total_match = False
        print(f"-> Block {i+1} ({block_sizes[i]} bytes): {'KHOP CHINH XAC 100%' if is_equal else 'SAI LECH DU LIEU'}")

    # 6. Kiem tra trang thai ngat phan cung va quyen so huu
    print("-" * 80)
    print("Kiem tra trang thai co phan cung va quyen so huu (Ownership):")
    print(f"-> Tong so byte DMA da truyen       : {dma.total_bytes_moved} bytes (Ky vong: {sum(block_sizes)} bytes)")
    print(f"-> Ngat phan cung IRQ da kich hoat   : {'CO (DAP UNG)' if dma.irq_triggered else 'KHONG'}")

    # Kiem tra tat ca descriptor da duoc tra ve cho CPU (OWN bit = 0)
    all_returned_to_cpu = True
    for addr in desc_addrs:
        raw = dram.read(addr, 32)
        d = DmaDescriptor.unpack(addr, raw)
        if d.flags & DmaControlFlags.OWN:
            all_returned_to_cpu = False

    print(f"-> Quyen so huu tat ca Descriptors   : {'DA TRA VE CPU (OWN=0)' if all_returned_to_cpu else 'VAN CON O DMA'}")
    print("=" * 80)

    assert total_match is True, "Du lieu truoc va sau khi DMA phai giong het nhau!"
    assert dma.total_bytes_moved == sum(block_sizes), "So luong byte truyen khong khop!"
    assert dma.irq_triggered is True, "Ngat phan cung IOC phai duoc kich hoat!"
    assert all_returned_to_cpu is True, "Bit OWN phai duoc xoa sau khi truyen!"
    print("[PASS] Scatter-Gather DMA Descriptors & Chained Ring: 100% Hoan hao!")


if __name__ == "__main__":
    test_scatter_gather_dma()
