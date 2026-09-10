"""
================================================================================
          MODULE AD CAPSTONE FINALE: BỘ VI XỬ LÝ ĐIỀU KHIỂN BAY TÀU VŨ TRỤ CHỐNG BỨC XẠ
================================================================================

TÍCH HỢP TOÀN BỘ FAULT-TOLERANT SPACE AVIONICS: TMR VOTER + SEU SCRUBBER + BYZANTINE
"""

from tmr_edge_majority_voter import tmr_majority_voter
from tmr_edge_seu_bitflip_scrubber import MemoryBitflipScrubber
from tmr_edge_byzantine_resilient_bus import ByzantineFaultArbiter

def run_spacecraft_fault_tolerant_flight_engine():
    # 1. Quét sửa lỗi bộ nhớ RAM bị đảo bit do bức xạ
    scrubber = MemoryBitflipScrubber()
    clean_code = scrubber.compute_parity_bits(0b1001)
    corrupted_code = clean_code ^ (1 << 3)  # Bị tia vũ trụ đảo 1 bit
    recovered_data, fixed_bits = scrubber.scrub_and_correct(corrupted_code)

    # 2. Bộ biểu quyết đa số TMR 2-out-of-3 tính toán góc lái
    thrust_cmd, tmr_status = tmr_majority_voter(45.0, 45.0, -10.0)

    # 3. Đồng thuận Byzantine 4 nút ra quyết định tách tầng tên lửa
    arbiter = ByzantineFaultArbiter(node_names=["FC1", "FC2", "FC3", "FC4"])
    stage_decision = arbiter.reach_consensus({
        "FC1": "SEPARATE_STAGE_1",
        "FC2": "SEPARATE_STAGE_1",
        "FC3": "SEPARATE_STAGE_1",
        "FC4_Faulty": "HOLD_STAGE"
    })

    return recovered_data, thrust_cmd, tmr_status, stage_decision


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AD CAPSTONE: SPACE AVIONICS FAULT-TOLERANCE")
    print("=========================================================\n")

    data_ok, thrust, status, decision = run_spacecraft_fault_tolerant_flight_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI SPACE AVIONICS ENGINE:")
    print(f"   -> Du lieu sau khi sua loi SEU   : {bin(data_ok)}")
    print(f"   -> Goc lai sau bieu quyet TMR    : {thrust} do (Status: {status})")
    print(f"   -> Quyet dinh dong thuan Byzantine: {decision}")

    assert data_ok == 0b1001 and thrust == 45.0 and decision == "SEPARATE_STAGE_1", "Loi Capstone Space Avionics!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AD: SPACE FAULT-TOLERANT AVIONICS!")
    print("=========================================================")
