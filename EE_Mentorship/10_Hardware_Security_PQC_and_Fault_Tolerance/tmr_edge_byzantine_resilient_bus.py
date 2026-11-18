"""
================================================================================
          MODULE Z: RADIATION-HARDENED TMR & FAULT-TOLERANT SPACE AVIONICS
              MILESTONE Z.3: 4-NODE BYZANTINE FAULT-TOLERANT CONSENSUS BUS
================================================================================

BAI TOAN TUONG QUAN BYZANTINE TRONG MANG DIEU KHIEN TEN LUA DAY (BYZANTINE GENERALS):
Dieu gi xay ra neu 1 kenh may tinh bi hong "hai mat" (Byzantine Traitor Node)?
- Mach so bi loi chap chon phat tin hieu trai nguoc:
  + Gui lenh "Khai hoa 100%" toi Dong co 1, nhung lai gui lenh "Tat dong co 0%" toi Dong co 2!
  + Gay ra lech luc day nghiem trong lam ten lua bi vo ket cau chi sau 0.5 giay!

DINH LY LAMPORT VE NGUONG DONG THUAN BYZANTINE (ASCII TEXT BLOCK):
De dung thu duoc m nut bi loi Byzantine tuy y, he thong phai co toi thieu:

         N >= 3 * m + 1   (Voi m = 1 nut hong -> Can toi thieu N = 4 nut)

         Nguong da so tuyet doi (Quorum Threshold) = 2 * m + 1 = 3 / 4 nut

SO DO MANG DONG THUAN GIAO CHEO 4 NUT (ASCII BUS DIAGRAM):

   [ Node 1 (Master 1) ] ───+
                            |
   [ Node 2 (Master 2) ] ───+──> [ Cross-Channel Broadcast Bus ] ──> [ Byzantine Arbiter ]
                            |                                               |
   [ Node 3 (Master 3) ] ───+                                               v
                            |                                      [ Kiem phieu Consensus ]
   [ Node 4 (Traitor)   ] ───+ (Phat tin sai lech)                  (>= 3 phieu -> Chap thuan)
                                                                    (< 3 phieu  -> Safe-Hold)
"""

from typing import Tuple, List, Dict, Any, Optional


class ByzantineFaultArbiter:
    """
    Bo phan xu dong thuan chong loi Byzantine (Byzantine Agreement Protocol) cho mang may tinh bay
    """
    def __init__(self, node_names: List[str]):
        self.node_names = list(node_names)
        self.quorum_threshold = 3  # Toi thieu 3/4 nut cho m=1 loi
        self.detected_traitors: List[str] = []

    def reach_consensus(self, node_broadcasts: Dict[str, str]) -> str:
        """
        Kiem phieu va ra quyet dinh dong thuan:
        - node_broadcasts: Dict chua lenh phat ra tu cac nut { 'Node1': 'CMD_A', ... }
        Tra ve: Lenh duoc da so dong thuan hoac "FAILSAFE_SAFE_HOLD"
        """
        self.detected_traitors.clear()
        votes: Dict[str, int] = {}
        for node, cmd in node_broadcasts.items():
            votes[cmd] = votes.get(cmd, 0) + 1

        winning_cmd: Optional[str] = None
        for cmd, count in votes.items():
            if count >= self.quorum_threshold:
                winning_cmd = cmd
                break

        if winning_cmd is not None:
            # Phat hien va ghi nhan nut nao co hanh vi phan boi / sai lech
            for node, cmd in node_broadcasts.items():
                if cmd != winning_cmd:
                    self.detected_traitors.append(node)
            return winning_cmd

        return "FAILSAFE_SAFE_HOLD"

    def get_traitor_report(self) -> List[str]:
        """Danh sach cac nut bi phat hien co hanh vi sai lech can cach ly"""
        return list(self.detected_traitors)


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: 4-NODE BYZANTINE FAULT CONSENSUS")
    print("=========================================================\n")

    arbiter = ByzantineFaultArbiter(node_names=["N1", "N2", "N3", "N4"])

    # 1. Kich ban 3 nut dong thuan Khai hoa (IGNITE_BOOSTER), Nut 4 bi loi keu huy (ABORT_MISSION)
    votes_scenario = {
        "N1": "IGNITE_BOOSTER",
        "N2": "IGNITE_BOOSTER",
        "N3": "IGNITE_BOOSTER",
        "N4_Faulty": "ABORT_MISSION"
    }

    final_command = arbiter.reach_consensus(votes_scenario)
    traitors = arbiter.get_traitor_report()

    print("1. KET QUA THOA THUAN DONG THUAN CHONG NUT PHAN BOI:")
    print(f"   -> Cac phieu tu cac Node     : {votes_scenario}")
    print(f"   -> Quyen quyet dinh cuoi cung: {final_command}")
    print(f"   -> Nut bi phat hien sai lech : {traitors}")

    assert final_command == "IGNITE_BOOSTER", "Lenh dong thuan phai la IGNITE_BOOSTER!"
    assert traitors == ["N4_Faulty"], "Phai phat hien dung nut N4_Faulty!"
    print("   -> Ket qua                   : CHINH XAC (Loai bo hoan toan anh huong cua N4)\n")

    # 2. Kich ban phan liet phieu khong dat nguong 3/4 (Tie-break deadlock)
    split_scenario = {
        "N1": "IGNITE_BOOSTER",
        "N2": "IGNITE_BOOSTER",
        "N3": "ABORT_MISSION",
        "N4": "ABORT_MISSION"
    }
    split_decision = arbiter.reach_consensus(split_scenario)
    print("2. TEST KICH BAN PHAN LIET PHIEU KHONG DAT QUORUM (2 vs 2):")
    print(f"   -> Quyen quyet dinh          : {split_decision}")

    assert split_decision == "FAILSAFE_SAFE_HOLD", "Khong du 3/4 phieu phai chuyen Safe-Hold!"

    print("\n[THANH CONG] DA HOAN THANH GIAO THUC DONG THUAN BYZANTINE AN TOAN TUYET DOI CHO TEN LUA!")
