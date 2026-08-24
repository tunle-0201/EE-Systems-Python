"""
================================================================================
          MODULE M: EMBEDDED CAN-BUS & VEHICLE NETWORK PROTOCOLS
              MILESTONE M.3: TRANH CHẤP BUS CAN KHÔNG PHÁ HỦY (BITWISE ARBITRATION)
================================================================================

TẠI SAO CAN-BUS KHÔNG BAO GIỜ BỊ XUNG ĐỘT GÓI TIN (COLLISION)?
Cơ chế Tranh chấp Bitwise Arbitration:
- Bit 0 là Dominant (Bit Thống trị / Áp đảo).
- Bit 1 là Recessive (Bit Lép vế).
- Khi 2 thiết bị cùng truyền: Thiết bị nào có ID nhỏ hơn (nhiều bit 0 hơn) sẽ THẮNG và chiếm trọn bus CAN.
- Thiết bị thua tự động chuyển sang chế độ Lắng nghe mà không làm hỏng gói tin của thiết bị thắng!
"""

def simulate_can_bus_arbitration(node1_id: int, node2_id: int) -> int:
    """
    Trò đóng vai Kỹ sư phần cứng CAN Bus mô phỏng cơ chế tranh chấp:
    - ID càng nhỏ ưu tiên càng cao (Bit 0 dominant đè bẹp Bit 1 recessive)
    - Trả về: ID của node chiến thắng chiếm quyền bus CAN
    """
    if node1_id < node2_id:
        return node1_id
    elif node2_id < node1_id:
        return node2_id
    return node1_id


if __name__ == "__main__":
    print("=========================================================")
    print("   VEHICLE EE SYSTEMS: CAN-BUS BITWISE ARBITRATION")
    print("=========================================================\n")
    
    # Node 1: Gói tin Phanh khẩn cấp Emergency (ID = 0x010)
    # Node 2: Gói tin Báo cáo Pin Battery Status (ID = 0x250)
    id_emergency = 0x010
    id_battery = 0x250
    
    winner_id = simulate_can_bus_arbitration(id_emergency, id_battery)
    
    print("1. KET QUA TRANH CHAP QUYEN TRUYEN BUS CAN:")
    print(f"   -> Node Thang chiem quyen Bus: 0x{winner_id:03X} (Goi khan cap uu tien nhat!)")
    
    assert winner_id == 0x010, "Loi CAN Arbitration!"
    print("\n[THANH CONG] DA MO PHONG CHINH XAC NGUYEN LY TRANH CHAP BITWISE ARBITRATION CHO CAN-BUS!")
