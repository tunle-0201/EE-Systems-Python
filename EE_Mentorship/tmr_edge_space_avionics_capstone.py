"""
================================================================================
          MODULE Z: RADIATION-HARDENED TMR & FAULT-TOLERANT SPACE AVIONICS
              MILESTONE Z.4: CAPSTONE SPACECRAFT FAULT-TOLERANT FLIGHT ENGINE
================================================================================

KIEN TRUC MAY TINH DIEU KHIEN BAY TAU VU TRU DUNG LOI (SPACE AVIONICS ENGINE):
Tren cac tau vu tru khong nguoi lai va co nguoi lai (SpaceX Dragon, Starship, NASA Orion):
- Tich hop 3 tuyen phong ve chong buc xa va dung loi song con:
  1. Background SEU Memory Scrubber: Tu dong quet sua bitflip RAM bang ma Hamming(7, 4).
  2. Hardware TMR Majority Voter: Bieu quyet da so 2/3 cac lenh dieu khien gimbal/thrust
     theo thoi gian thuc, lap tuc cach ly kenh bi trung tia buc xa.
  3. Byzantine Fault-Tolerant Bus: Phan xu dong thuan 4 nut voi nguong >= 3 phieu
     cho cac su kien quyet dinh van menh (Tach tang ten lua Stage Separation).

SO DO KHOI TICH HOP HE THONG PHAN CUNG KHONG GIAN (ASCII ARCHITECTURE DIAGRAM):

   [ Radiation Environment (Cosmic Rays / Van Allen Belts) ]
                           |
                           v
   +───────────────────────────────────────────────────────────────────────────+
   |          SPACECRAFT FAULT-TOLERANT AVIONICS FLIGHT COMPUTER               |
   +───────────────────────────────────────────────────────────────────────────+
          |                                   |                    |
          v                                   v                    v
   [ SEU Memory Scrubber ]           [ TMR 2/3 Voter ]    [ Byzantine 4-Node Bus ]
   - Hamming(7, 4) SEC               - Channels A, B, C   - Quorum >= 3 / 4
   - Background Scrubbing            - Real-time Thrust   - Stage Separation
   - Auto Bitflip Recovery           - Fault Isolation    - Traitor Isolation
          |                                   |                    |
          +───────────────────────────────────+────────────────────+
                                              |
                                              v
                              [ Flight Critical Actuators ]
                              (Rocket Gimbals & Stage Pyro Separation)
"""

from typing import Tuple, List, Dict, Any, Optional

from tmr_edge_majority_voter import tmr_majority_voter
from tmr_edge_seu_bitflip_scrubber import MemoryBitflipScrubber
from tmr_edge_byzantine_resilient_bus import ByzantineFaultArbiter


class SpacecraftFaultTolerantAvionicsEngine:
    """
    Dong co may tinh bay tau vu tru tich hop toan bo cac khoi phong ve cua Module Z
    """
    def __init__(self, node_names: Optional[List[str]] = None):
        self.scrubber = MemoryBitflipScrubber()
        self.byzantine_arbiter = ByzantineFaultArbiter(node_names or ["FC1", "FC2", "FC3", "FC4"])
        self.total_mission_cycles = 0

    def process_flight_cycle(
        self,
        raw_memory_code_7bit: int,
        thrust_channels: Tuple[float, float, float],
        staging_votes: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Xu ly 1 chu ky dinh ky 10 ms (100 Hz) cua may tinh bay tau vu tru:
        1. Quet sua loi bo nho SEU Scrubber
        2. Bieu quyet goc lai TMR 2-out-of-3
        3. Dong thuan tach tang ten lua Byzantine 4-Node
        """
        self.total_mission_cycles += 1

        # 1. Quet sua loi bo nho RAM
        recovered_data, fixed_bits = self.scrubber.scrub_and_correct(raw_memory_code_7bit)

        # 2. Bieu quyet goc lai TMR
        voted_thrust, tmr_status = tmr_majority_voter(
            thrust_channels[0],
            thrust_channels[1],
            thrust_channels[2]
        )

        # 3. Dong thuan Byzantine cho su kien tach tang
        stage_decision = self.byzantine_arbiter.reach_consensus(staging_votes)
        traitors = self.byzantine_arbiter.get_traitor_report()

        return {
            "cycle": self.total_mission_cycles,
            "recovered_memory_nibble": recovered_data,
            "seu_fixed_bits": fixed_bits,
            "voted_thrust_deg": voted_thrust,
            "tmr_health_status": tmr_status,
            "stage_consensus_decision": stage_decision,
            "isolated_traitors": traitors
        }


def run_spacecraft_fault_tolerant_flight_engine() -> Tuple[int, float, str, str]:
    """
    Ham wrapper capstone dong bo toan chuoi kiem thu cac milestone Z.1, Z.2, Z.3
    Tra ve: (recovered_data, thrust_cmd, tmr_status, stage_decision)
    """
    # 1. Quet sua loi bo nho RAM bi dao bit do buc xa
    scrubber = MemoryBitflipScrubber()
    clean_code = scrubber.compute_parity_bits(0b1001)
    corrupted_code = clean_code ^ (1 << 3)  # Bi tia vu tru dao 1 bit
    recovered_data, fixed_bits = scrubber.scrub_and_correct(corrupted_code)

    # 2. Bo bieu quyet da so TMR 2-out-of-3 tinh toan goc lai (Kenh C bi lech -10 do)
    thrust_cmd, tmr_status = tmr_majority_voter(45.0, 45.0, -10.0)

    # 3. Dong thuan Byzantine 4 nut ra quyet dinh tach tang ten lua
    arbiter = ByzantineFaultArbiter(node_names=["FC1", "FC2", "FC3", "FC4"])
    stage_decision = arbiter.reach_consensus({
        "FC1": "SEPARATE_STAGE_1",
        "FC2": "SEPARATE_STAGE_1",
        "FC3": "SEPARATE_STAGE_1",
        "FC4_Faulty": "HOLD_STAGE"
    })

    return int(recovered_data), float(thrust_cmd), str(tmr_status), str(stage_decision)


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Z CAPSTONE: SPACE AVIONICS FAULT-TOLERANCE")
    print("=========================================================\n")

    # 1. Kiem tra toan chuoi qua ham wrapper
    data_ok, thrust, status, decision = run_spacecraft_fault_tolerant_flight_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI SPACE AVIONICS ENGINE:")
    print(f"   -> Du lieu sau khi sua loi SEU   : {bin(data_ok)}")
    print(f"   -> Goc lai sau bieu quyet TMR    : {thrust} do (Status: {status})")
    print(f"   -> Quyet dinh dong thuan Byzantine: {decision}\n")

    assert data_ok == 0b1001, "Du lieu sau khi sua loi SEU phai la 0b1001!"
    assert thrust == 45.0, "Goc lai bieu quyet TMR phai la 45.0 do!"
    assert status == "CHANNEL_C_FAULT", "Phai phat hien kenh C bi loi!"
    assert decision == "SEPARATE_STAGE_1", "Quyet dinh phai la SEPARATE_STAGE_1!"

    # 2. Kiem tra bang dong co toan dien OOP Engine
    engine = SpacecraftFaultTolerantAvionicsEngine()
    test_code = engine.scrubber.compute_parity_bits(0b1100) ^ (1 << 4)  # Bi loi bit d1
    telemetry = engine.process_flight_cycle(
        raw_memory_code_7bit=test_code,
        thrust_channels=(30.0, -99.0, 30.0),  # Kenh B bi loi
        staging_votes={
            "FC1": "IGNITE_SECOND_STAGE",
            "FC2": "IGNITE_SECOND_STAGE",
            "FC3": "IGNITE_SECOND_STAGE",
            "FC4": "ABORT"
        }
    )

    print("2. TELEMETRY MAY TINH BAY KHONG GIAN TOAN DIEN (MISSION FLIGHT ENGINE):")
    print(f"   -> Chu ky nhiem vu             : Cycle #{telemetry['cycle']}")
    print(f"   -> Du lieu RAM phuc hoi        : {bin(telemetry['recovered_memory_nibble'])}")
    print(f"   -> So bit da tu dong sua (SEU) : {telemetry['seu_fixed_bits']} bit")
    print(f"   -> Goc lai sau bieu quyet TMR  : {telemetry['voted_thrust_deg']} do")
    print(f"   -> Trang thai kenh TMR         : {telemetry['tmr_health_status']}")
    print(f"   -> Quyet dinh tach tang        : {telemetry['stage_consensus_decision']}")
    print(f"   -> Nut bi cach ly              : {telemetry['isolated_traitors']}")

    assert telemetry["recovered_memory_nibble"] == 0b1100
    assert telemetry["voted_thrust_deg"] == 30.0
    assert telemetry["tmr_health_status"] == "CHANNEL_B_FAULT"
    assert telemetry["stage_consensus_decision"] == "IGNITE_SECOND_STAGE"

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE Z: SPACE FAULT-TOLERANT AVIONICS!")
    print("=========================================================")
