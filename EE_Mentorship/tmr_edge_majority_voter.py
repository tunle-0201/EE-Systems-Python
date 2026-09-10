"""
================================================================================
          MODULE AD: RADIATION-HARDENED TMR & FAULT-TOLERANT AVIONICS
              MILESTONE AD.1: BỘ BIỂU QUYẾT ĐA SỐ 2/3 (TRIPLE MODULAR REDUNDANCY)
================================================================================

TẠI SAO CÁC TÀU VŨ TRỤ SPACEX DRAGON VÀ NASA CẦN TMR (TRIPLE MODULAR REDUNDANCY)?
Trong môi trường vũ trụ, tia vũ trụ (Cosmic Rays) bắn phá CPU:
- Kỹ thuật TMR chạy 3 kênh máy tính điều khiển bay song song độc lập (Kênh A, B, C).
- Bộ biểu quyết phần cứng (Hardware Majority Voter):
  + Nếu cả 3 kênh giống nhau -> Đồng thuận 100% (Consensus).
  + Nếu 1 kênh bị tia vũ trụ bắn sai số -> Bộ biểu quyết lấy kết quả 2 kênh còn lại (2-out-of-3)!
  + Tự động cô lập kênh hỏng và cảnh báo thay thế!
"""

def tmr_majority_voter(out_a, out_b, out_c):
    """
    Trò đóng vai Kỹ sư Thiết kế Máy tính Điều khiển Bay Tàu Vũ trụ:
    - Nếu out_a == out_b: Trả về (out_a, "HEALTHY" nếu out_b == out_c else "CHANNEL_C_FAULT")
    - Nếu out_a == out_c: Trả về (out_a, "CHANNEL_B_FAULT")
    - Nếu out_b == out_c: Trả về (out_b, "CHANNEL_A_FAULT")
    - Nếu cả 3 kênh khác nhau hoàn toàn: Trả về (None, "CRITICAL_TMR_BREAKDOWN")
    """
    if out_a == out_b:
        status = "HEALTHY" if out_b == out_c else "CHANNEL_C_FAULT"
        return out_a, status
    elif out_a == out_c:
        return out_a, "CHANNEL_B_FAULT"
    elif out_b == out_c:
        return out_b, "CHANNEL_A_FAULT"
    else:
        return None, "CRITICAL_TMR_BREAKDOWN"


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: 2-OUT-OF-3 TMR MAJORITY VOTER")
    print("=========================================================\n")

    # Lệnh điều khiển góc lái tên lửa: A=15 độ, B=15 độ, Kênh C bị tia vũ trụ làm sai lệch (-99 độ)
    cmd_a, cmd_b, cmd_c = 15.0, 15.0, -99.0
    voted_cmd, system_health = tmr_majority_voter(cmd_a, cmd_b, cmd_c)

    print("1. KET QUA BIEU QUYET DA SO PHAN CUNG TMR:")
    print(f"   -> Lenh goc kenh A, B, C    : A={cmd_a}, B={cmd_b}, C={cmd_c}")
    print(f"   -> Lenh sau bieu quyet TMR  : {voted_cmd} do")
    print(f"   -> Trang thai he thong      : {system_health}")

    assert voted_cmd == 15.0 and system_health == "CHANNEL_C_FAULT", "Loi TMR Majority Voter!"
    print("\n[THANH CONG] DA HOAN THANH BO BIEU QUYET TMR 2-OUT-OF-3 CHONG TIA VU TRU CHO SPACEX!")
