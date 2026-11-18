"""
================================================================================
          MODULE AF CAPSTONE FINALE: HỆ THỐNG VIỄN THÔNG VŨ TRỤ SÂU CHO NASA
================================================================================

TÍCH HỢP TOÀN BỘ DEEP SPACE SATCOM STACK: LINK BUDGET + REED-SOLOMON FEC + CCSDS
"""

from satcom_edge_friis_path_loss import calculate_satellite_link_budget
from satcom_edge_reedsolomon_fec import ReedSolomonSimulator
from satcom_edge_ccsds_space_packet import encode_ccsds_primary_header

def run_deep_space_comms_pipeline():
    # 1. Tính toán Link Budget từ quỹ đạo Sao Hỏa (Mars Distance 1,000,000 km)
    fspl, p_rx, margin = calculate_satellite_link_budget(
        dist_km=1000.0, freq_mhz=8400.0, p_tx_dbm=43.0, g_tx_dbi=35.0, g_rx_dbi=60.0, rx_sens_dbm=-120.0
    )

    # 2. Đóng gói CCSDS Space Packet
    payload = b"MARS_SAMPLE_RETURN_SCIENCE_DATA"
    ccsds_hdr = encode_ccsds_primary_header(apid=0x300, seq_count=1, payload_length=len(payload))
    packet = ccsds_hdr + payload

    # 3. Mã hóa sửa lỗi tiến trình Reed-Solomon RS(255, 223)
    rs = ReedSolomonSimulator(n=255, k=223)
    encoded_frame = rs.encode(packet)

    return margin, len(ccsds_hdr), len(encoded_frame)


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AF CAPSTONE: DEEP-SPACE SATCOM ENGINE")
    print("=========================================================\n")

    link_margin, hdr_len, frame_len = run_deep_space_comms_pipeline()

    print("1. KET QUA HOAT DONG TOAN CHUOI DEEP-SPACE SATCOM:")
    print(f"   -> Link Budget Margin         : {link_margin:.2f} dB (Dat chuan vien thong)")
    print(f"   -> CCSDS Space Header Length  : {hdr_len} bytes")
    print(f"   -> Reed-Solomon Encoded Frame : {frame_len} bytes")

    assert link_margin > 3.0 and hdr_len == 6 and frame_len == 255, "Loi Capstone SatCom!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AF: SPACE SATELLITE COMMUNICATIONS!")
    print("=========================================================")
