"""
================================================================================
          MODULE AB: EMBEDDED PCIE & HARDWARE ACCELERATOR INTERCONNECTS
              MILESTONE AB.1: ĐÓNG GÓI GIAO THỨC TLP (TRANSACTION LAYER PACKET)
================================================================================

TẠI SAO GIAO THỨC PCIE LÀ XƯƠNG SỐNG KẾT NỐI GPU/NPU VỚI CPU TRÊN XE TỰ HÀNH?
PCIe (PCI Express Gen 4/5):
- Giao tiếp gói tin phân tầng (Packet-based protocol) tốc độ lên tới 32 GT/s.
- Gói tin TLP (Transaction Layer Packet) gồm:
  + Header (3 hoặc 4 Dwords = 12/16 bytes): Xác định loại lệnh (Memory Read MWr/MRd).
  + Requester ID (Bus:Device:Function - BDF): Địa chỉ xuất phát của thiết bị.
  + Target Physical Address: Địa chỉ đích trên bộ nhớ RAM hệ thống.
  + Length: Số lượng Dwords dữ liệu cần truyền.
"""

def encode_pcie_tlp_mwr_header(requester_bdf: tuple, target_address: int, length_dwords: int):
    """
    Trò đóng vai Kỹ sư Phần cứng Giao tiếp PCIe:
    - requester_bdf: (bus, dev, func) -> bdf_id = (bus << 8) | (dev << 3) | func
    - FMT/TYPE cho Memory Write 32-bit (MWr): fmt_type = 0x40 (010 00000b)
    - Trả về header dạng danh sách 3 thanh ghi 32-bit (Dwords)
    """
    bus, dev, func = requester_bdf
    requester_id = ((bus & 0xFF) << 8) | ((dev & 0x1F) << 3) | (func & 0x07)
    
    dword0 = (0x40 << 24) | (length_dwords & 0x3FF)
    dword1 = (requester_id << 16) | 0x000F  # First BE = 0xF, Last BE = 0x0
    dword2 = target_address & 0xFFFFFFFC   # 4-byte aligned address
    
    return [dword0, dword1, dword2]


if __name__ == "__main__":
    print("=========================================================")
    print("   PCIE INTERCONNECT: TLP MEMORY WRITE PACKET ENCODER")
    print("=========================================================\n")

    # GPU ở vị trí Bus 1, Device 0, Func 0 ghi 16 Dwords vào RAM tại 0x80000000
    bdf = (1, 0, 0)
    addr = 0x80000000
    len_dw = 16

    tlp_header = encode_pcie_tlp_mwr_header(bdf, addr, len_dw)

    print("1. KET QUA DONG GOI PCIE TLP HEADER 3-DWORD:")
    print(f"   -> Dword 0 (Fmt/Type/Length): 0x{tlp_header[0]:08X}")
    print(f"   -> Dword 1 (Requester BDF)  : 0x{tlp_header[1]:08X}")
    print(f"   -> Dword 2 (Target Address) : 0x{tlp_header[2]:08X}")

    assert len(tlp_header) == 3 and (tlp_header[0] & 0x3FF) == 16, "Loi PCIe TLP Encoder!"
    print("\n[THANH CONG] DA HOAN THANH BO MA HOA GOI TIN PCIE TLP MEMORY WRITE CHO GPU!")
