"""
================================================================================
          MODULE V: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE V.3: PASSIVE SHUNT CELL BALANCING ALGORITHM
================================================================================

TAI SAO BAT BUOC PHAI CAN BANG CELL TREN PACK PIN XE DIEN 96S (400V / 800V)?
Trong khoang pin ghep noi tiep (4S tren Drone, 96S tren Tesla Model 3 hoac 192S tren Porsche Taycan):
- Do sai so che tao dien cuc va chech lech nhiet do giua cac vi tri trong pack,
  toc do tu xa (Self-Discharge) va dung luong cac cell khong the giong nhau 100%.
- Hieu ung "Thung go thung" (The Barrel Effect):
  + Khi sac: Cell day som nhat cham nguong 4.20V, buoc BMS phai dung sac ngay lap tuc
    trong khi cac cell khac moi chi dat 80% (mat 20% quang duong di chuyen!).
  + Neu khong ngat: Cell do bi qua ap (Over-Voltage) gay phu pin va chay no nhiet!

GIAI PHAP EMBEDDED BMS: THUAT TOAN CAN BANG THU DONG (PASSIVE SHUNT BALANCING):
Moi cell pin duoc mac song song voi mot mach nhanh goom dien tro xa R_bleed (30 Ohm)
noi tiep voi mot transistor MOSFET dieu khien boi IC do chuyen dung (LTC6811 / BQ76952):

SO DO NGUYEN LY MACH XA CAN BANG SHUNT (ASCII CIRCUIT BLOCK):

            (+) ───────────┬──────────────────────┬─────────── (+)
                           │                      │
                           │                     [ ] R_bleed (30 Ohm)
                      [ Cell Li-ion ]             │
                      (Vi du: 4.19V)             ---  N-MOSFET (Switch)
                           │                    / |
                           │    Gate Drive <───'  |
                           │                      │
            (-) ───────────┴──────────────────────┴─────────── (-)

QUY TRINH DIEU KHIEN CAN BANG TRONG MOI CHU KY QUET ADC:
1. Xac dinh cuc tieu, cuc dai va do lech dien ap:
         V_min = min(cell_voltages)
         V_max = max(cell_voltages)
         Delta_V = V_max - V_min

2. Neu Delta_V > Threshold (vi du 10 mV = 0.010V):
   - Kich hoat dong MOSFET xa cho bat ky cell nao co:
         V_cell > V_min + Margin (5 mV)
   - Dong xa can bang:
                     V_cell
         I_bleed = ───────────   (Vi du: 4.19V / 30 Ohm ~ 140 mA)
                     R_bleed

   - Xa bot dien tich cac cell cao cho den khi toan bo pack dong deu duoi 10 mV!
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np


class PassiveCellBalancer:
    """
    Thuat toan can bang dien ap cell thu dong bang dien tro xa Shunt Bleed Resistor
    Chong hao ton nang luong bang cach chi kich hoat khi xe dang cam sac (is_charging=True).
    """
    def __init__(
        self,
        num_cells: int = 4,
        r_bleed_ohm: float = 30.0,
        balance_thresh_v: float = 0.010,
        margin_v: float = 0.005
    ):
        """
        - num_cells: So cell mac noi tiep trong pack
        - r_bleed_ohm: Dien tro xa nhiet can bang (30 Ohm -> I_bleed ~ 140 mA)
        - balance_thresh_v: Nguong sai lech toi thieu de bat can bang (10 mV)
        - margin_v: Do lech cho phep so voi cell thap nhat V_min (5 mV)
        """
        self.n = num_cells
        self.r_bleed = r_bleed_ohm
        self.threshold = balance_thresh_v
        self.margin = margin_v
        self.switch_states: List[bool] = [False] * num_cells

    def compute_balancing_actions(self, cell_voltages: List[float], is_charging: bool = True) -> List[bool]:
        """
        Xac dinh trang thai dong / ngat MOSFET can bang cho tung cell trong pack:
        Chi cho phep can bang khi dang cam sac de khong lam giam dung luong khi xe dang van hanh.
        """
        if not is_charging:
            self.switch_states = [False] * self.n
            return self.switch_states

        v_min = min(cell_voltages)
        v_max = max(cell_voltages)
        delta_v = v_max - v_min

        # Neu pack da can bang duoi nguong an toan -> Tat toan bo MOSFET
        if delta_v <= self.threshold:
            self.switch_states = [False] * self.n
            return self.switch_states

        # Bat dien tro xa cho tat ca cac cell co dien ap vuot V_min + margin
        target_cutoff = v_min + self.margin
        for i in range(self.n):
            if cell_voltages[i] > target_cutoff:
                self.switch_states[i] = True
            else:
                self.switch_states[i] = False

        return self.switch_states

    def simulate_balancing_step(
        self,
        cell_voltages: List[float],
        dt_sec: float,
        cell_capacity_ah: float = 2.5
    ) -> List[float]:
        """
        Mo phong dong hoc sut giam dien ap cua cac cell duoc bat dien tro xa
        """
        updated_v = list(cell_voltages)
        # Dien dung tuong duong cua cell tinh theo C_eff = Q_total / Delta_V_range
        c_eff = (cell_capacity_ah * 3600.0) / 1.2

        for i in range(self.n):
            if self.switch_states[i]:
                # Dong xa qua tro bleed: I = V / R
                i_bleed = updated_v[i] / self.r_bleed
                # Sut ap tuong ung: dv = (I * dt) / C_eff
                dv = (i_bleed * dt_sec) / c_eff
                updated_v[i] -= dv

        return updated_v


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: PASSIVE SHUNT CELL BALANCING ALGORITHM")
    print("=========================================================\n")

    balancer = PassiveCellBalancer(
        num_cells=4,
        r_bleed_ohm=30.0,
        balance_thresh_v=0.010,
        margin_v=0.005
    )

    # Gia lap pack pin 4S bi lech dien ap nghiem trong (Cell Imbalance)
    # Cell 1 = 4.18V, Cell 2 = 4.08V (cell yeu nhat), Cell 3 = 4.19V, Cell 4 = 4.14V
    pack_v = [4.180, 4.080, 4.190, 4.140]

    v_min_init = min(pack_v)
    v_max_init = max(pack_v)
    delta_init = v_max_init - v_min_init

    print("1. TRANG THAI PACK PIN 4S BAN DAU (TRUOC CAN BANG):")
    print(f"   -> Dien ap tung cell       : {[round(v, 3) for v in pack_v]} V")
    print(f"   -> Chenh lech cuc dai (dV) : {delta_init * 1000.0:.1f} mV (Vuot qua nguong 10.0 mV!)\n")

    # Kiem tra thuat toan kich hoat logic MOSFET
    switches = balancer.compute_balancing_actions(pack_v, is_charging=True)
    print("2. QUYET DINH DONG NGAT MOSFET XA CAN BANG:")
    for idx, (v, state) in enumerate(zip(pack_v, switches), 1):
        print(f"   -> Cell #{idx} ({v:.3f}V) : {'[BAT XA NHIET R_BLEED]' if state else '[KHONG XA]'}")

    assert switches[0] is True, "Cell 1 cao phai duoc xac dinh can bat xa!"
    assert switches[1] is False, "Cell 2 thap nhat tuyet doi khong duoc xa!"
    assert switches[2] is True, "Cell 3 cao nhat phai duoc bat xa!"

    # Mo phong qua trinh xa can bang trong 60 phut (moi buoc 60 giay)
    current_pack = list(pack_v)
    for step in range(60):
        balancer.compute_balancing_actions(current_pack, is_charging=True)
        current_pack = balancer.simulate_balancing_step(current_pack, dt_sec=60.0, cell_capacity_ah=0.5)

    final_delta = max(current_pack) - min(current_pack)
    print("\n3. KET QUA SAU KHI XA CAN BANG PASSIVE BALANCING:")
    print(f"   -> Dien ap cac cell da deu : {[round(v, 3) for v in current_pack]} V")
    print(f"   -> Do lech sau can bang    : {final_delta * 1000.0:.2f} mV (Giam ve duoi nguong an toan!)")

    assert final_delta < delta_init, "Do lech sau can bang phai giam ro ret so voi ban dau!"
    assert final_delta < 0.010, "Do lech sau can bang phai duoi nguong 10 mV!"

    print("\n[THANH CONG] THUAT TOAN PASSIVE BALANCING DA DONG DEU HOA CAC CELL PIN AN TOAN!")
