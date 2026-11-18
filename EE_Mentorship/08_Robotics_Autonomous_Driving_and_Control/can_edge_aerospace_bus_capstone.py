"""
================================================================================
          MODULE Y CAPSTONE FINALE: MẠNG TRUYỀN THÔNG AVIONICS TÊN LỬA VŨ TRỤ
================================================================================

TÍCH HỢP TOÀN BỘ DETERMINISTIC AVIONICS NETWORK: CAN-FD + TTETHERNET + TDMA ARBITER
"""

from can_edge_canfd_crc17 import compute_canfd_crc17
from can_edge_ttethernet_sync import compute_fault_tolerant_midpoint
from can_edge_time_slot_arbiter import TDMABusArbiter

def run_aerospace_avionics_network_engine():
    # 1. Đồng bộ đồng hồ toàn mạng vi-giây TTEthernet
    sensor_clocks = [50000.1, 50000.4, 49999.9, 58000.0]  # Nút 4 bị lỗi
    master_clock = compute_fault_tolerant_midpoint(sensor_clocks)

    # 2. Phân định quyền phát theo khe TDMA
    bus = TDMABusArbiter(cycle_period_ms=10, slot_duration_ms=2)
    bus.assign_slot(0, "FLIGHT_COMPUTER_PRIMARY")
    active_node = bus.get_active_transmitter(current_time_ms=1)

    # 3. Đóng gói chỉ lệnh CAN-FD kèm mã kiểm tra CRC-17
    cmd_packet = b"CRITICAL_THRUST_VECTOR_COMMAND_GIMBAL_ANGLE_SETPOINT_ALPHA_001_64B"
    crc17 = compute_canfd_crc17(cmd_packet)

    return master_clock, active_node, crc17


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Y CAPSTONE: AEROSPACE AVIONICS BUS ENGINE")
    print("=========================================================\n")

    sync_us, node, crc = run_aerospace_avionics_network_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI AEROSPACE AVIONICS NETWORK:")
    print(f"   -> Thoi gian Dong bo TTEthernet : {sync_us:.2f} us")
    print(f"   -> Nut dang phat song (TDMA)    : {node}")
    print(f"   -> Ma CRC-17 goi tin CAN-FD     : 0x{crc:05X}")

    assert abs(sync_us - 50000.0) < 1.0 and node == "FLIGHT_COMPUTER_PRIMARY" and crc > 0, "Loi Capstone Avionics Bus!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE Y: AEROSPACE AVIONICS BUS NETWORKS!")
    print("=========================================================")
