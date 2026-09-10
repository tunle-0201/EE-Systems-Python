"""
================================================================================
          MODULE AD: RADIATION-HARDENED TMR & FAULT-TOLERANT AVIONICS
              MILESTONE AD.3: ĐỒNG THUẬN CHỐNG LỖI TỔNG QUÁT (BYZANTINE FAULT BUS)
================================================================================

BÀI TOÁN TƯỚNG QUÂN BYZANTINE TRONG HỆ THỐNG ĐIỀU KHIỂN ĐỘNG CƠ TÊN LỬA:
Điều gì xảy ra nếu 1 kênh máy tính bị hỏng "nửa vời" (Traitor Node):
- Gửi lệnh "Tăng ga 100%" tới Động cơ Trái, nhưng lại gửi lệnh "Giảm ga 0%" tới Động cơ Phải -> Làm tên lửa lộn nhào!
- Giao thức Đồng thuận Byzantine (Byzantine Agreement):
  + Tối thiểu cần 3m + 1 nút để chống lại m nút phản bội (Với 1 nút hỏng cần 4 nút: N1, N2, N3, N4).
  + Các nút trao đổi chéo thông điệp (Cross-Channel Broadcast).
  + Quyết định hành động theo luật đa số tuyệt đối, loại bỏ hoàn toàn hành vi gửi 2 mặt của nút phản bội!
"""

class ByzantineFaultArbiter:
    def __init__(self, node_names: list):
        self.node_names = node_names

    def reach_consensus(self, node_broadcasts: dict) -> str:
        """
        node_broadcasts: { 'Node1': 'IGNITE', 'Node2': 'IGNITE', 'Node3': 'IGNITE', 'Node4_Traitor': 'ABORT' }
        Trò đóng vai Kỹ sư Trọng tài An toàn Bay:
        - Đếm số phiếu cho từng lệnh
        - Nếu có một lệnh đạt >= 3 phiếu (Đa số trên tổng số 4 nút): Lệnh đó được thi hành!
        - Nếu không đạt đồng thuận: Kích hoạt chế độ "FAILSAFE_SAFE_HOLD"
        """
        votes = {}
        for node, cmd in node_broadcasts.items():
            votes[cmd] = votes.get(cmd, 0) + 1

        for cmd, count in votes.items():
            if count >= 3:
                return cmd
        return "FAILSAFE_SAFE_HOLD"


if __name__ == "__main__":
    print("=========================================================")
    print("   SPACE AVIONICS: 4-NODE BYZANTINE FAULT CONSENSUS")
    print("=========================================================\n")

    arbiter = ByzantineFaultArbiter(node_names=["N1", "N2", "N3", "N4"])

    # 3 nút trung thực bỏ phiếu IGNITE (Khai hỏa), Nút 4 bị hỏng nói ABORT
    votes_scenario = {
        "N1": "IGNITE_BOOSTER",
        "N2": "IGNITE_BOOSTER",
        "N3": "IGNITE_BOOSTER",
        "N4_Faulty": "ABORT_MISSION"
    }

    final_command = arbiter.reach_consensus(votes_scenario)

    print("1. KET QUA THOA THUAN DONG THUAN CHONG NUT PHAN BOI:")
    print(f"   -> Cac phieu tu cac Node     : {votes_scenario}")
    print(f"   -> Quyen quyet dinh cuoi cung: {final_command}")

    assert final_command == "IGNITE_BOOSTER", "Loi Byzantine Consensus!"
    print("\n[THANH CONG] DA HOAN THANH GIAO THUC DONG THUAN BYZANTINE AN TOAN TUYET DOI CHO TEN LUA!")
