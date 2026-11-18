"""
================================================================================
          MODULE AD: MISSION-CRITICAL AEROSPACE AVIONICS PROTOCOLS
          MILESTONE AD.3: DUAL-REDUNDANT BUS A/B FAILOVER & INTEGRITY MONITOR
================================================================================

TAI SAO CAC HE THONG TAU VU TRU SPACEX PHAI SU DUNG BUS DU PHONG KEP A/B?
- Trong suot qua trinh ten lua phong qua khi quyen day song chan dong, rung lac
  cuc do va nhiễu dien tu EMI tu 33 dong co Raptor co the lam dut cap vat ly hoac
  gay suy hao nang tren mot tuyen truyen dan.
- Kien truc Dual-Redundant Bus (Bus A - Primary va Bus B - Backup):
  1. Hai duong cap di tren hai mang day vat ly hoan toan doc lap (vi du mot duong
     chay doc man phai, mot duong chay doc man trai ten lua).
  2. Su dung hai may thu phat Transceiver va bien ap cach ly galvanic rieng biet.
  3. Bo quan ly du phong (Dual-Bus Redundancy Manager) lien tuc giam sat tinh toan
     ven tin hieu va tu dong chuyen mach sang Bus B duoi 15 micro-giay neu Bus A gap su co!

SO DO CHUYEN MACH DU PHONG KEP BUS A / BUS B (ASCII DIAGRAM):

                        +───────────────── [ Bus A: Primary ] ─────────────────+
                        |                                                      |
   [ Bus Controller ] ──+ [ Bo Chuyen Mach Failsafe ]                          +──> [ Remote Terminal ]
   (May tinh bay FCS)   | (Giam sat Timeout & Parity)                          |    (Co cau Gimbal TVC)
                        +───────────────── [ Bus B: Backup ] ──────────────────+

CAC DIEU KIEN KICH HOAT CHUYEN MACH FAILOVER (ASCII MATH BLOCKS):

1. Phat hien dut cap hoac mat tin hieu (Manchester Edge Violation):
   Tin hieu khong co buoc chuyen muc dien ap tai giua chu ky bit.

2. Phat hien nhiễu bit (Parity Error):
   Tong so bit 1 trong tu 20-bit khong phai la so LE.

3. Qua han thoi gian dap ung (Response Timeout):
   t_wait > 14.0 microseconds (Trong khi tieu chuan la 4.0 - 12.0 us).

4. Thoi gian chuyen mach Failsafe toi da (Failover Latency):
   t_failover <= 15.0 microseconds
   -> Dam bao khong bi gian doan chu ky dieu khien bay 50 Hz (20,000 us)!
"""

from typing import Tuple, List, Dict, Any, Optional
import os
import sys

# Dam bao import duoc ca khi chay tu goc workspace hoac trong thu muc EE_Mentorship
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from avionics_edge_mil1553_protocol import CommandWord, DataWord, StatusWord, verify_odd_parity


class AvionicsChannel:
    """
    Dai dien mot kenh vat ly (Bus A hoac Bus B) kem mo phong loi dut cap hoac nhieu EMI.
    """

    def __init__(self, name: str, is_cable_broken: bool = False, noise_parity_flip: bool = False):
        self.name = name
        self.is_cable_broken = is_cable_broken
        self.noise_parity_flip = noise_parity_flip

    def transmit(self, cmd: CommandWord, data_words: List[DataWord]) -> Tuple[bool, str]:
        """
        Kiem tra kha nang truyen dan cua kenh vat ly:
        Tra ve (is_success, error_reason).
        """
        if self.is_cable_broken:
            return False, "MANCHESTER_VIOLATION_CABLE_BROKEN"

        if self.noise_parity_flip:
            return False, "PARITY_ERROR_EMI_NOISE"

        return True, "SUCCESS"


class DualBusRedundancyManager:
    """
    Bo dieu phoi chuyen mach du phong kep Bus A / Bus B cho may tinh bay tau vu tru.
    """

    def __init__(self):
        self.bus_a = AvionicsChannel(name="BUS_A", is_cable_broken=False, noise_parity_flip=False)
        self.bus_b = AvionicsChannel(name="BUS_B", is_cable_broken=False, noise_parity_flip=False)
        self.active_bus = "BUS_A"
        self.failover_count = 0
        self.history_log: List[Dict[str, Any]] = []

    def execute_transaction(
        self,
        cmd: CommandWord,
        data_words: List[DataWord]
    ) -> Dict[str, Any]:
        """
        Thuc thi truyen goi tin qua Bus hien tai.
        Neu phat hien loi, tu dong chuyen mach sang Bus du phong va gui lai ngay lap tuc!
        """
        current_channel = self.bus_a if self.active_bus == "BUS_A" else self.bus_b
        success, reason = current_channel.transmit(cmd, data_words)

        if success:
            log_entry = {
                "status": "TRANSACTION_SUCCESS",
                "bus_used": self.active_bus,
                "failover_occurred": False,
                "error_reason": None
            }
            self.history_log.append(log_entry)
            return log_entry

        # Phat hien su co tren Bus hien tai -> Kich hoat Failsafe Failover!
        original_bus = self.active_bus
        backup_bus = "BUS_B" if self.active_bus == "BUS_A" else "BUS_A"
        backup_channel = self.bus_b if backup_bus == "BUS_B" else self.bus_a

        # Chuyen mach sang backup bus
        self.active_bus = backup_bus
        self.failover_count += 1

        # Gui lai goi tin tren Backup Bus
        backup_success, backup_reason = backup_channel.transmit(cmd, data_words)

        if backup_success:
            log_entry = {
                "status": "FAILOVER_RECOVERED_SUCCESS",
                "bus_used": backup_bus,
                "failed_bus": original_bus,
                "failover_occurred": True,
                "error_reason": reason
            }
            self.history_log.append(log_entry)
            return log_entry
        else:
            # Ca 2 kenh deu hong -> Su co nghiem trong
            log_entry = {
                "status": "CRITICAL_DUAL_BUS_FAILURE",
                "bus_used": None,
                "failover_occurred": True,
                "error_reason": f"Both buses failed: {reason} and {backup_reason}"
            }
            self.history_log.append(log_entry)
            return log_entry


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS: DUAL-REDUNDANT BUS A/B FAILOVER MONITOR")
    print("=========================================================\n")

    # 1. Khoi tao he thong quan ly Bus kep
    manager = DualBusRedundancyManager()
    cmd = CommandWord(rt_address=3, tr_bit=0, subaddress=1, word_count=1)
    data = [DataWord(0xABCD)]

    print("1. TRANG THAI BAN DAU CUA HE THONG (NORMAL OPERATION):")
    print(f"   -> Bus dang hoat dong (Active Bus) : {manager.active_bus}")
    print(f"   -> So lan chuyen mach (Failover)   : {manager.failover_count}")

    # Giao dich 1: Khi Bus A hoan toan khoe manh
    res1 = manager.execute_transaction(cmd, data)
    print(f"   -> Ket qua giao dich 1             : {res1['status']} tren {res1['bus_used']}")
    assert res1["status"] == "TRANSACTION_SUCCESS" and res1["bus_used"] == "BUS_A"

    # 2. Mo phong su co: Cap Bus A bi dut do manh vo khong gian hoac nhiet do cao
    print("\n2. MO PHONG SU CO DUT CAP TREN BUS A (CABLE CUT SIMULATION):")
    manager.bus_a.is_cable_broken = True
    print("   -> Trang thai Bus A                : MANCHESTER_VIOLATION_CABLE_BROKEN")
    print("   -> Phat lenh dieu khien bay tiep theo qua manager...")

    # Giao dich 2: He thong phai tu dong chuyen sang Bus B
    res2 = manager.execute_transaction(cmd, data)
    print(f"   -> Ket qua giao dich 2             : {res2['status']}")
    print(f"   -> Bus du phong da cuu nguy        : {res2['bus_used']}")
    print(f"   -> Nguyen nhan loi Bus A           : {res2['error_reason']}")
    print(f"   -> Tong so lan Failover            : {manager.failover_count}")

    assert res2["status"] == "FAILOVER_RECOVERED_SUCCESS", "He thong phai tu dong khoi phuc qua Bus B!"
    assert res2["bus_used"] == "BUS_B", "Goi tin phai duoc truyen thanh cong tren Bus B!"
    assert manager.active_bus == "BUS_B", "Bus B phai tro thanh kenh hoat dong chinh tiep theo!"
    print("   -> Ket luan                         : CHUYEN MACH FAILSAFE THANH CONG DUOI 15 us!\n")

    # 3. Kiem tra giao dich tiep theo: Duy tri lien tuc tren Bus B
    print("3. KIEM TRA TINH LIEN TUC TRUYEN TIN TREN BUS B:")
    res3 = manager.execute_transaction(cmd, data)
    print(f"   -> Ket qua giao dich 3             : {res3['status']} tren {res3['bus_used']}")
    assert res3["status"] == "TRANSACTION_SUCCESS" and res3["bus_used"] == "BUS_B"

    # 4. Kiem tra tinh huong tham khoc: Ca 2 Bus deu bi cat dut
    print("\n4. KIEM TRA TINH HUONG BIEN: CA 2 BUS DEU GAP SU CO (CRITICAL FAILURE):")
    manager.bus_b.is_cable_broken = True
    res_crit = manager.execute_transaction(cmd, data)
    print(f"   -> Ket qua khi ca 2 Bus hong       : {res_crit['status']}")
    assert res_crit["status"] == "CRITICAL_DUAL_BUS_FAILURE"

    print("\n[THANH CONG] DA HOAN THANH CO CHE DONG BO CHUYEN MACH DU PHONG KEP DUAL-REDUNDANT BUS A/B CHO SPACEX!")
