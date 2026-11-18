"""
================================================================================
          MODULE AD: MISSION-CRITICAL AEROSPACE AVIONICS PROTOCOLS
       MILESTONE AD.4: SPACECRAFT MULTI-PROTOCOL FLIGHT GATEWAY CAPSTONE
================================================================================

KIEN TRUC TOAN CHUOI DONG CO CAU NOI DIEN TU BAY TAU VU TRU (AVIONICS GATEWAY):
Capstone nay tich hop tron ven toan bo cac chuan giao tiep hang khong & vu tru:
1. Milestone AD.2: ARINC429Word -> Giai ma dong du lieu cam bien IRS (Do cao, goc Pitch).
2. Milestone AD.1: MIL-STD-1553B -> Dong goi tu lenh Command & Data Word 20-bit.
3. Milestone AD.3: DualBusRedundancyManager -> Chuyen mach du phong kep Bus A/B.
4. Capstone Engine: SpacecraftAvionicsGateway -> Dieu phoi cau noi thoi gian thuc.

SO DO CHUYEN DOI VA TRUYEN DAN DU LIEU TOAN CHUOI (ASCII PIPELINE):

   [ Cam bien Dan duong ARINC 429 ] (Label 203: Do cao, Label 324: Goc Pitch)
                   |
                   v
   [ Spacecraft Avionics Gateway ] (Bien dich he don vi & Dong goi 20-bit)
                   |
                   v
   [ Dual-Redundant MIL-STD-1553B ] ──+──> [ Bus A (Primary) ] ──+
   (Bo quan ly du phong kep Failsafe)  |                         |
                                       +──> [ Bus B (Backup) ]  ──+──> [ May tinh Gimbal TVC ]
                                                                       (Dieu khien huong phu dong co)

TOAN HOC CHUYEN DOI HE DON VI TU ARINC 429 SANG MIL-STD-1553B (ASCII BLOCKS):

1. Giai ma ARINC 429 BNR (19-bit Bu 2):
                  Signed_Integer
   Real_Angle = ────────────────── * 180.0 do
                    (2^18 - 1)

2. Ma hoa sang MIL-STD-1553B Data Word 16-bit Fixed-Point (Dinh dang 0.01 do/LSB):
   Raw_1553_Word = int(Real_Angle * 100.0) & 0xFFFF
   Vi du: +15.25 do -> 1525 = 0x05F5
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import os
import sys

# Dam bao import duoc ca khi chay tu goc workspace hoac trong thu muc EE_Mentorship
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from avionics_edge_mil1553_protocol import CommandWord, DataWord, StatusWord, RemoteTerminal
from avionics_edge_arinc429_words import ARINC429Word
from avionics_edge_dual_bus_redundancy import DualBusRedundancyManager


class SpacecraftAvionicsGateway:
    """
    Dong co cau noi dien tu bay da giao thuc giua ARINC 429 va MIL-STD-1553B.
    """

    def __init__(self, target_rt_address: int = 5):
        self.target_rt_address = target_rt_address
        self.redundancy_manager = DualBusRedundancyManager()
        self.total_cycles = 0
        self.processed_transactions: List[Dict[str, Any]] = []

    def process_flight_cycle(
        self,
        arinc_alt_word: ARINC429Word,
        arinc_pitch_word: ARINC429Word,
        subaddress: int = 10
    ) -> Dict[str, Any]:
        """
        Thuc thi mot chu ky dieu khien bay:
        1. Giai ma du lieu tu 2 tu ARINC 429 (Do cao va Goc Pitch).
        2. Kiem tra tinh toan ven Parity va SSM cua ARINC 429.
        3. Chuyen doi sang dinh dang Fixed-Point 16-bit cua MIL-STD-1553B.
        4. Dong goi Command Word va Data Words 20-bit kem Odd Parity.
        5. Truyen qua mang MIL-STD-1553B du phong kep Bus A/B.
        Tra ve bao cao chu ky bay (Flight Telemetry Report).
        """
        self.total_cycles += 1

        # 1. Kiem tra va giai ma ARINC 429
        if not arinc_alt_word.is_parity_valid() or not arinc_pitch_word.is_parity_valid():
            return {
                "cycle": self.total_cycles,
                "status": "ARINC429_PARITY_ERROR",
                "bus_used": None,
                "telemetry": None
            }

        altitude_ft, alt_status = arinc_alt_word.decode_bnr(max_scale=131072.0)
        pitch_deg, pitch_status = arinc_pitch_word.decode_bnr(max_scale=180.0)

        if alt_status != "NORMAL_OPERATION" or pitch_status != "NORMAL_OPERATION":
            return {
                "cycle": self.total_cycles,
                "status": "SENSOR_FAILURE_WARNING",
                "bus_used": None,
                "telemetry": None
            }

        # 2. Chuyen doi sang 16-bit Fixed-Point cho MIL-STD-1553B
        # Do cao: chia ti le 10 ft / LSB (vi du 35000 ft -> 3500)
        alt_16bit = int(altitude_ft / 10.0) & 0xFFFF
        # Goc Pitch: chia ti le 0.01 do / LSB (vi du 12.50 do -> 1250)
        pitch_16bit = int(pitch_deg * 100.0) & 0xFFFF

        # 3. Dong goi MIL-STD-1553B
        cmd_word = CommandWord(
            rt_address=self.target_rt_address,
            tr_bit=0,  # Receive
            subaddress=subaddress,
            word_count=2
        )
        dw_alt = DataWord(alt_16bit)
        dw_pitch = DataWord(pitch_16bit)

        # 4. Truyen qua bo quan ly du phong kep Bus A/B
        tx_result = self.redundancy_manager.execute_transaction(cmd_word, [dw_alt, dw_pitch])

        telemetry_data = {
            "altitude_ft": altitude_ft,
            "pitch_deg": pitch_deg,
            "raw_1553_alt": hex(alt_16bit),
            "raw_1553_pitch": hex(pitch_16bit)
        }

        report = {
            "cycle": self.total_cycles,
            "status": tx_result["status"],
            "bus_used": tx_result["bus_used"],
            "failover_occurred": tx_result["failover_occurred"],
            "error_reason": tx_result["error_reason"],
            "telemetry": telemetry_data
        }
        self.processed_transactions.append(report)
        return report


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AD CAPSTONE: SPACECRAFT AVIONICS FLIGHT GATEWAY")
    print("=========================================================\n")

    # 1. Khoi tao Dong co Cau noi Dien tu bay
    gateway = SpacecraftAvionicsGateway(target_rt_address=5)

    # 2. Chu ky bay #1: Tau vu tru bay len on dinh (Normal Operation tren Bus A)
    print("1. CHU KY BAY #1: BAY QUA TANG KHI QUYEN ON DINH (NORMAL BUS A):")
    alt_word_1 = ARINC429Word.encode_bnr("203", value=28000.0, max_scale=131072.0, ssm=3)
    pitch_word_1 = ARINC429Word.encode_bnr("324", value=15.50, max_scale=180.0, ssm=3)

    report_1 = gateway.process_flight_cycle(alt_word_1, pitch_word_1)
    print(f"   -> Ket qua chu ky 1          : {report_1['status']} tren {report_1['bus_used']}")
    print(f"   -> Do cao giai ma            : {report_1['telemetry']['altitude_ft']:.1f} feet")
    print(f"   -> Goc Pitch giai ma         : {report_1['telemetry']['pitch_deg']:.2f} do")
    print(f"   -> Ma 16-bit 1553B truyen di : Alt={report_1['telemetry']['raw_1553_alt']}, Pitch={report_1['telemetry']['raw_1553_pitch']}")

    assert report_1["status"] == "TRANSACTION_SUCCESS"
    assert report_1["bus_used"] == "BUS_A"
    assert not report_1["failover_occurred"]
    print("   -> Ket luan                   : CHU KY 1 TRUYEN QUA BUS A HOAN HAO!\n")

    # 3. Chu ky bay #2: Su co Max-Q rung lac lam dut cap Bus A
    print("2. CHU KY BAY #2: SU CO RUNGLAC MAX-Q LAM DUT CAP BUS A (FAILOVER BUS B):")
    gateway.redundancy_manager.bus_a.is_cable_broken = True

    alt_word_2 = ARINC429Word.encode_bnr("203", value=45000.0, max_scale=131072.0, ssm=3)
    pitch_word_2 = ARINC429Word.encode_bnr("324", value=8.25, max_scale=180.0, ssm=3)

    report_2 = gateway.process_flight_cycle(alt_word_2, pitch_word_2)
    print(f"   -> Ket qua chu ky 2          : {report_2['status']}")
    print(f"   -> Bus da cuu nguy           : {report_2['bus_used']} (Sau khi Bus A bi dut cap)")
    print(f"   -> Co chuyen mach Failover   : {report_2['failover_occurred']}")
    print(f"   -> Nguyen nhan loi Bus A     : {report_2['error_reason']}")
    print(f"   -> Do cao giai ma            : {report_2['telemetry']['altitude_ft']:.1f} feet")
    print(f"   -> Goc Pitch giai ma         : {report_2['telemetry']['pitch_deg']:.2f} do")

    assert report_2["status"] == "FAILOVER_RECOVERED_SUCCESS", "Cau noi phai tu dong chuyen sang Bus B!"
    assert report_2["bus_used"] == "BUS_B"
    assert report_2["failover_occurred"] is True
    print("   -> Ket luan                   : KHOI PHUC FAILSAFE QUA BUS B DUNG CHUAN VU TRU!\n")

    # 4. Chu ky bay #3: Tach tang ten lua va giu lien tuc tren Bus B
    print("3. CHU KY BAY #3: TACH TANG TEN LUA (DUY TRI ON DINH TREN BUS B):")
    alt_word_3 = ARINC429Word.encode_bnr("203", value=75000.0, max_scale=131072.0, ssm=3)
    pitch_word_3 = ARINC429Word.encode_bnr("324", value=0.00, max_scale=180.0, ssm=3)

    report_3 = gateway.process_flight_cycle(alt_word_3, pitch_word_3)
    print(f"   -> Ket qua chu ky 3          : {report_3['status']} tren {report_3['bus_used']}")
    print(f"   -> Do cao dat duoc           : {report_3['telemetry']['altitude_ft']:.1f} feet")
    assert report_3["status"] == "TRANSACTION_SUCCESS"
    assert report_3["bus_used"] == "BUS_B"

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE AD: SPACECRAFT AVIONICS FLIGHT GATEWAY!")
    print("=========================================================")
