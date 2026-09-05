"""
================================================================================
          MODULE Y: EMBEDDED TIME-TRIGGERED BUS & AEROSPACE AVIONICS
              MILESTONE Y.2: ĐỒNG BỘ ĐỒNG HỒ TTEthernet (SAE AS6802 CLOCK SYNC)
================================================================================

TẠI SAO CÁC TÀU VŨ TRỤ NASA ORION VÀ SPACEX DÙNG TTETHERNET?
Trong hàng không vũ trụ:
- Mạng Ethernet thông thường (Best-Effort) có độ trễ giật cục (Jitter) không xác định.
- Chuẩn TTEthernet (Time-Triggered Ethernet / SAE AS6802):
  + Đồng bộ toàn bộ các máy tính điều khiển bay về cùng một mốc vi-giây (Microsecond Global Clock).
  + Thuật toán Trung vị Chống lỗi (Fault-Tolerant Midpoint):
    Loại bỏ các nút đồng hồ bị hỏng hoặc cố ý gửi sai lệch, giữ độ lệch toàn mạng < 1 microsecond!
"""

import numpy as np

def compute_fault_tolerant_midpoint(clock_readings_us: list) -> float:
    """
    Trò đóng vai Kỹ sư Mạng Điều khiển Bay Vũ trụ:
    - Sắp xếp các giá trị đo đồng hồ từ các máy tính phụ: sorted_clocks
    - Loại bỏ giá trị cực tiểu và cực đại (chống Byzantine Fault)
    - Tính trung điểm (Midpoint) của các nút còn lại
    """
    sorted_clocks = sorted(clock_readings_us)
    if len(sorted_clocks) >= 3:
        trimmed = sorted_clocks[1:-1]
        return float(np.mean(trimmed))
    return float(np.mean(sorted_clocks))


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE AVIONICS: TTETHERNET FAULT-TOLERANT SYNC")
    print("=========================================================\n")

    # 4 máy tính điều khiển bay gửi thời gian (us): Máy tính 4 bị hỏng cảm biến (12000 us)
    clocks = [10000.2, 10000.5, 9999.8, 12000.0]
    sync_time = compute_fault_tolerant_midpoint(clocks)

    print("1. KET QUA DONG BO DONG HO TOAN MANG AVIONICS:")
    print(f"   -> Cac so do tu cac may tinh : {clocks}")
    print(f"   -> Thoi gian chuan dong bo (us): {sync_time:.2f}")

    assert abs(sync_time - 10000.0) < 1.0, "Loi TTEthernet Clock Sync!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN DONG BO TTETHERNET CHONG LOI CHO TAU VU TRU!")
