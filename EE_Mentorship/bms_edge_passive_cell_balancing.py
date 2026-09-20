"""
================================================================================
          MODULE AM: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE AM.3: THUẬT TOÁN CÂN BẰNG ĐIỆN ÁP CELL THỤ ĐỘNG (PASSIVE BALANCING)
================================================================================

TẠI SAO BẮT BUỘC PHẢI CÂN BẰNG CELL TRÊN PACK PIN XE ĐIỆN 96S (400V / 800V)?
Trong bộ pin ghép nối tiếp (ví dụ 4S cho Drone hoặc 96S cho Tesla Model 3):
- Do dung sai sản xuất và chênh lệch nhiệt độ, các cell pin tự xả không đều nhau.
- Hiệu ứng "Thùng gỗ thủng" (Barrel Effect): Dung lượng cả pack pin bị giới hạn bởi
  cell yếu nhất!
  + Khi sạc: Cell đầy sớm nhất sẽ chạm 4.20V, ép bộ sạc phải ngắt trong khi các cell khác
    mới nạp được 80% (mất 20% quãng đường đi được!).
  + Nếu không ngắt: Cell đó sẽ bị quá áp (Over-voltage) dẫn đến bốc cháy!

GIẢI PHÁP EMBEDDED BMS: THUẬT TOÁN CÂN BẰNG THỤ ĐỘNG (PASSIVE SHUNT BALANCING):
Mỗi cell có một công tắc MOSFET nối tiếp điện trở xả R_bleed (ví dụ 33 Ohm):
1. Quét điện áp toàn bộ các cell bằng IC đo chuyên dụng (LTC6811 / BQ76952):
        V_min = min(cell_voltages)
        V_max = max(cell_voltages)
        Delta_V = V_max - V_min

2. Nếu Delta_V vượt ngưỡng lệch an toàn (ví dụ 10 mV = 0.010V):
   - Kích hoạt MOSFET đóng điện trở xả cho bất kỳ cell nào có:
        V_cell > V_min + V_margin (5 mV)
   - Dòng xả cân bằng:
                     V_cell
        I_bleed = ───────────
                    R_bleed

   - Xả bớt điện tích của các cell cao cho tới khi toàn bộ pack đồng đều dưới 5 mV!
"""

import numpy as np

class PassiveCellBalancer:
    def __init__(self, num_cells: int = 4, r_bleed_ohm: float = 33.0, balance_thresh_v: float = 0.010, margin_v: float = 0.005):
        """
        - num_cells: Số cell ghép nối tiếp (ví dụ pack 4S)
        - r_bleed_ohm: Điện trở xả nhiệt cân bằng (33 Ohm -> dòng xả ~ 120 mA)
        - balance_thresh_v: Ngưỡng kích hoạt cân bằng (10 mV)
        - margin_v: Độ chênh lệch tối thiểu so với V_min để xả (5 mV)
        """
        self.n = num_cells
        self.r_bleed = r_bleed_ohm
        self.threshold = balance_thresh_v
        self.margin = margin_v
        self.switch_states = [False] * num_cells

    def compute_balancing_actions(self, cell_voltages: list, is_charging: bool = True) -> list:
        """
        Xác định trạng thái đóng/ngắt MOSFET cân bằng cho từng cell:
        Chỉ cho phép cân bằng khi đang cắm sạc (is_charging=True) để tránh hao pin khi đang chạy!
        Trả về: list bool [True/False] tương ứng với trạng thái bật MOSFET xả
        """
        if not is_charging:
            self.switch_states = [False] * self.n
            return self.switch_states

        v_min = min(cell_voltages)
        v_max = max(cell_voltages)
        delta_v = v_max - v_min

        # Nếu độ lệch nhỏ hơn ngưỡng cho phép -> Không cần xả
        if delta_v <= self.threshold:
            self.switch_states = [False] * self.n
            return self.switch_states

        # Ngược lại, bật điện trở xả cho các cell cao hơn v_min + margin
        target_cutoff = v_min + self.margin
        for i in range(self.n):
            if cell_voltages[i] > target_cutoff:
                self.switch_states[i] = True
            else:
                self.switch_states[i] = False

        return self.switch_states

    def simulate_balancing_step(self, cell_voltages: list, dt_sec: float, cell_capacity_ah: float = 2.5) -> list:
        """
        Mô phỏng 1 bước xả điện lượng qua điện trở Shunt R_bleed
        """
        updated_v = list(cell_voltages)
        for i in range(self.n):
            if self.switch_states[i]:
                # Dòng xả I_bleed = V / R
                i_bleed = updated_v[i] / self.r_bleed
                # Điện lượng rút ra: dQ = I * dt (Coulombs)
                # Tỷ lệ sụt áp ước tính: dV = (dQ / Q_total) * (4.2V - 3.0V)
                # Hoặc tương đương điện dung cell C_eff = Q_as / Delta_V
                c_eff = (cell_capacity_ah * 3600.0) / 1.2
                dv = (i_bleed * dt_sec) / c_eff
                updated_v[i] -= dv
        return updated_v


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: PASSIVE SHUNT CELL BALANCING ALGORITHM")
    print("=========================================================\n")

    balancer = PassiveCellBalancer(num_cells=4, r_bleed_ohm=30.0, balance_thresh_v=0.010, margin_v=0.005)

    # Giả lập pack pin 4S bị lệch điện áp (Cell Imbalance)
    # Cell 1 = 4.18V, Cell 2 = 4.08V (cell yếu), Cell 3 = 4.19V, Cell 4 = 4.14V
    pack_v = [4.180, 4.080, 4.190, 4.140]

    v_min_init = min(pack_v)
    v_max_init = max(pack_v)
    delta_init = v_max_init - v_min_init

    print("1. TRANG THAI PACK PIN 4S BAN DAU (TRUOC CAN BANG):")
    print(f"   -> Dien ap tung cell       : {[round(v, 3) for v in pack_v]} V")
    print(f"   -> Chenh lech cuc dai (dV) : {delta_init * 1000.0:.1f} mV (Vuot nguong 10 mV!)\n")

    # Kiểm tra thuật toán kích hoạt MOSFET
    switches = balancer.compute_balancing_actions(pack_v, is_charging=True)
    print("2. QUYET DINH DONG NGAT MOSFET XA CAN BANG:")
    for idx, (v, state) in enumerate(zip(pack_v, switches), 1):
        print(f"   -> Cell #{idx} ({v:.3f}V) : {'[BAT XA NHIET R_BLEED]' if state else '[KHONG XA]'}")

    assert switches[0] is True, "Cell 1 cao phai duoc xac dinh can xa!"
    assert switches[1] is False, "Cell 2 thap nhat tuyet doi khong duoc xa!"
    assert switches[2] is True, "Cell 3 cao nhat phai duoc xac dinh can xa!"

    # Mô phỏng quá trình xả cân bằng trong 60 phút
    # Từng bước 60 giây
    current_pack = list(pack_v)
    for _ in range(60):
        balancer.compute_balancing_actions(current_pack, is_charging=True)
        current_pack = balancer.simulate_balancing_step(current_pack, dt_sec=60.0, cell_capacity_ah=0.5)

    final_delta = max(current_pack) - min(current_pack)
    print(f"\n3. KET QUA SAU KHI XA CAN BANG PASSIVE BALANCING:")
    print(f"   -> Dien ap cac cell da deu : {[round(v, 3) for v in current_pack]} V")
    print(f"   -> Do lech sau can bang    : {final_delta * 1000.0:.2f} mV (Giam ro ret!)")

    assert final_delta < delta_init, "Do lech sau can bang phai giam so voi ban dau!"
    print("\n[THANH CONG] THUAT TOAN PASSIVE BALANCING DA DONG DEU HOA CAC CELL PIN AN TOAN!")
