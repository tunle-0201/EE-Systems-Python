"""
================================================================================
          MODULE AF: SATELLITE COMMUNICATIONS & SPACE LINK BUDGET
              MILESTONE AF.1: PHƯƠNG TRÌNH FRIIS TÍNH HAO PHÍ ĐƯỜNG TRUYỀN (FSPL)
================================================================================

TẠI SAO MỌI KỸ SƯ VIỄN THÔNG VỆ TINH PHẢI TÍNH TOÁN LINK BUDGET (NGÂN SÁCH ĐƯỜNG TRUYỀN)?
Sóng vô tuyến truyền từ Vệ tinh quỹ đạo thấp LEO (500km) xuống Trạm mặt đất:
- Năng lượng sóng bị suy hao theo khoảng cách bình phương (Free-Space Path Loss - FSPL).
- Phương trình truyền sóng Friis (tính theo dB):
  FSPL(dB) = 20*log10(d_km) + 20*log10(f_MHz) + 32.44
- Độ dự trữ năng lượng đường truyền (Link Margin):
  Link_Margin = P_tx + G_tx + G_rx - FSPL - P_rx_sensitivity
  (Yêu cầu Link Margin >= 3.0 dB để bảo đảm không bị rớt mạng khi trời mưa bão!)
"""

import numpy as np

def calculate_satellite_link_budget(dist_km: float, freq_mhz: float, p_tx_dbm: float, g_tx_dbi: float, g_rx_dbi: float, rx_sens_dbm: float):
    """
    Trò đóng vai Kỹ sư Viễn thông Vũ trụ:
    - Tính tổn hao không gian tự do: fspl_db = 20*log10(dist_km) + 20*log10(freq_mhz) + 32.44
    - Công suất thu được tại mặt đất: p_rx_dbm = p_tx_dbm + g_tx_dbi + g_rx_dbi - fspl_db
    - Độ dự phòng đường truyền: margin_db = p_rx_dbm - rx_sens_dbm
    - Trả về: (fspl_db, p_rx_dbm, margin_db)
    """
    fspl_db = 20.0 * np.log10(dist_km) + 20.0 * np.log10(freq_mhz) + 32.44
    p_rx_dbm = p_tx_dbm + g_tx_dbi + g_rx_dbi - fspl_db
    margin_db = p_rx_dbm - rx_sens_dbm
    return fspl_db, p_rx_dbm, margin_db


if __name__ == "__main__":
    print("=========================================================")
    print("   SATCOM AVIONICS: FRIIS FREE-SPACE PATH LOSS BUDGET")
    print("=========================================================\n")

    # Vệ tinh LEO cự ly 500km, tần số băng S 2200 MHz (2.2 GHz)
    # P_tx = 30 dBm (1 Watt), G_tx = 6 dBi, Chảo mặt đất G_rx = 25 dBi, Độ nhạy thu = -110 dBm
    fspl, p_rx, margin = calculate_satellite_link_budget(
        dist_km=500.0, freq_mhz=2200.0, p_tx_dbm=30.0, g_tx_dbi=6.0, g_rx_dbi=25.0, rx_sens_dbm=-110.0
    )

    print("1. KET QUA TINH TOAN LINK BUDGET TU QUY DAO VE TINH:")
    print(f"   -> Hao phi khong gian FSPL : {fspl:.2f} dB")
    print(f"   -> Cong suat thu tai Chao  : {p_rx:.2f} dBm")
    print(f"   -> Do du phong Link Margin : {margin:.2f} dB (Tieu chuan >= 3.0 dB)")

    assert fspl > 150.0 and margin > 3.0, "Loi SatCom Link Budget!"
    print("\n[THANH CONG] DA HOAN THANH TINH TOAN NGAN SACH DUONG TRUYEN SONG VE TINH!")
