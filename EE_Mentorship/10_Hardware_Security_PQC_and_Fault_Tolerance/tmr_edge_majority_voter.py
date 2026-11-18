"""
================================================================================
          MODULE Z: RADIATION-HARDENED TMR & FAULT-TOLERANT SPACE AVIONICS
              MILESTONE Z.1: HARDWARE 2-OUT-OF-3 TMR MAJORITY VOTER
================================================================================

TAI SAO CAC TAU VU TRU SPACEX DRAGON VA NASA ORION BAT BUOC PHAI DUNG TMR?
Trong moi truong khong gian quy dao sau va vanh dai buc xa Van Allen:
- Cac hat ion nang luong cao (Cosmic Rays / Solar Protons) ban xuyen qua lop vo
  kim loai, lam bien doi trang thai logic cua thanh ghi va bo so hoc ALU trong CPU.
- Kien truc 3 kenh mo-dun du thua TMR (Triple Modular Redundancy):
  + Chay 3 kenh may tinh dieu khien bay doc lap vat ly (Kenh A, Kenh B, Kenh C).
  + Thuc thi cung mot thuat toan dan duong tai cung mot chu ky xung nhip thoi gian thuc.

SO DO KHOI BO BIEU QUYET PHAN CUNG 2-OUT-OF-3 MAJORITY VOTER (ASCII DIAGRAM):

   [ Flight Computer Channel A ] ───+
                                    |
   [ Flight Computer Channel B ] ───+──> [ 2-out-of-3 Majority Voter ] ──> [ Actuator Gimbals ]
                                    |                 |
   [ Flight Computer Channel C ] ───+                 v
                                            [ Fault Isolation Flag ]
                                            (Co lap kenh bi trung tia)

LUAT PHAN XU DONG THUAN TMR (CONSENSUS VOTING RULES):
1. Neu ca 3 kenh giong nhau: Dong thuan 100% -> Trang thai HEALTHY.
2. Neu 1 kenh bi sai lech do tia vu tru:
   - Bo bieu quyet tu dong chon gia tri cua 2 kenh trung khop con lai (2-out-of-3)!
   - Bat co canh bao loi kenh hong (vi du: CHANNEL_C_FAULT) de cach ly tuc thi.
3. Neu ca 3 kenh khac nhau hoan toan: Mat dong thuan TMR -> Kich hoat che do Safe-Hold!
"""

from typing import Tuple, List, Dict, Any, Optional
import math


def tmr_majority_voter(out_a: Any, out_b: Any, out_c: Any, tolerance: float = 1e-4) -> Tuple[Any, str]:
    """
    Bo bieu quyet da so TMR 2-out-of-3 cho may tinh bay khong gian:
    - out_a, out_b, out_c: Gia tri lenh dau ra tu 3 kenh may tinh doc lap
    - tolerance: Do lech cho phep giua cac gia tri so thuc (floating point)
    Tra ve: (voted_output, system_health_status)
    """
    def is_close(val1: Any, val2: Any) -> bool:
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) <= tolerance
        return val1 == val2

    ab_match = is_close(out_a, out_b)
    ac_match = is_close(out_a, out_c)
    bc_match = is_close(out_b, out_c)

    # 1. Truong hop Kenh A va Kenh B giong nhau
    if ab_match:
        if bc_match:
            return out_a, "HEALTHY"
        return out_a, "CHANNEL_C_FAULT"

    # 2. Truong hop Kenh A va Kenh C giong nhau (Kenh B bi loi)
    elif ac_match:
        return out_a, "CHANNEL_B_FAULT"

    # 3. Truong hop Kenh B va Kenh C giong nhau (Kenh A bi loi)
    elif bc_match:
        return out_b, "CHANNEL_A_FAULT"

    # 4. Truong hop ca 3 kenh deu khac nhau (Critical Breakdown)
    else:
        return None, "CRITICAL_TMR_BREAKDOWN"


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: 2-OUT-OF-3 TMR MAJORITY VOTER")
    print("=========================================================\n")

    # 1. Kich ban 1: Kenh C bi hat mang nang luong cao ban lech goc lai tu 15 do xuong -99 do
    cmd_a, cmd_b, cmd_c = 15.0, 15.0, -99.0
    voted_cmd, health_status = tmr_majority_voter(cmd_a, cmd_b, cmd_c)

    print("1. KET QUA BIEU QUYET KHI KENH C BI BAN LECH TIA VU TRU:")
    print(f"   -> Lenh goc kenh A, B, C    : A={cmd_a}, B={cmd_b}, C={cmd_c}")
    print(f"   -> Lenh sau bieu quyet TMR  : {voted_cmd} do")
    print(f"   -> Trang thai he thong      : {health_status}")

    assert voted_cmd == 15.0, "Gia tri bieu quyet phai lay theo da so 2 kenh A va B!"
    assert health_status == "CHANNEL_C_FAULT", "Phai phat hien va cach ly kenh C!"
    print("   -> Ket qua                   : CHINH XAC (Da cach ly kenh C loi)\n")

    # 2. Kich ban 2: Ca 3 kenh dong thuan hoan hao (100% Healthy)
    voted_norm, health_norm = tmr_majority_voter(45.0, 45.0, 45.0)
    print("2. KET QUA KHI CA 3 KENH DONG THUAN HOAN HAO:")
    print(f"   -> Lenh sau bieu quyet      : {voted_norm} do (Status: {health_norm})")
    assert voted_norm == 45.0 and health_norm == "HEALTHY"

    # 3. Kich ban 3: Su co tham khoc ca 3 kenh khac nhau (Critical TMR Breakdown)
    voted_fail, health_fail = tmr_majority_voter(10.0, 20.0, 30.0)
    print("\n3. KET QUA KHI CA 3 KENH KHAC BIET HOAN TOAN:")
    print(f"   -> Lenh sau bieu quyet      : {voted_fail} (Status: {health_fail})")
    assert voted_fail is None and health_fail == "CRITICAL_TMR_BREAKDOWN"

    print("\n[THANH CONG] DA HOAN THANH BO BIEU QUYET TMR 2-OUT-OF-3 CHONG TIA VU TRU CHO SPACEX!")
