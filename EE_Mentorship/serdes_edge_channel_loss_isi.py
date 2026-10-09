"""
================================================================================
          MODULE AB: HIGH-SPEED SERDES & SIGNAL INTEGRITY ARCHITECTURE
          MILESTONE AB.2: PCB TRANSMISSION CHANNEL LOSS & ISI DISPERSION
================================================================================

TAI SAO DUONG MACH DONG PCB TAN SO CAO GAY DONG BIEU DO MAT (EYE CLOSURE)?
- O toc do sieu cao (10 Gbps - 32 Gbps tren chip Apple Silicon / Tesla FSD):
  Moi bit du lieu chi ton tai trong khoang thoi gian cuc ngan (Unit Interval - UI):
  UI = 1 / 10 Gbps = 100 picoseconds (ps)!
- Khi truyen qua duong mach dong tren bo mach FR4 / Megtron:
  1. Hieu ung be mat (Skin Effect): Dong dien tan so cao bi day ra lop vo ngoai
     cua day dan lam dien tro tang theo can bac hai cua tan so: R ~ sqrt(f).
  2. Ton hao dien moi (Dielectric Loss): Nang luong bi tieu tan thanh nhiet
     trong chat dien moi theo ham tuyen tinh: Loss ~ f.
- Hau qua vat ly: Duong truyen PCB hoat dong nhu mot bo loc thong thap (Low-Pass Filter)
  khien mot xung vuong sac net bi xoe rong ve thoi gian (Pulse Dispersion).
  Nang luong cua bit truoc tran sang de bop nghet bit sau, gay nen hien tuong
  Nhiễu xuyen ky tu (Inter-Symbol Interference - ISI).

SO DO PHAN TAN XUNG VA NHIEU XUYEN KY TU ISI (ASCII DIAGRAM):

   Dau vao TX (Xung bit sach)            Dau ra RX (Xung bi xoe rong do suy hao)
       +──────+                                      ^
       |      |                                    /   \   (h0: Main Cursor)
   ────+      +────                           ────+     \─────+
                                                        (h1)  (h2) Post-Cursors
                                                        (Nang luong tran sang bit sau)

TOAN HOC MO HINH DAP UNG KENH TRUYEN VA ISI (ASCII MATH BLOCKS):

1. Dap ung xung roi rac cua kenh truyen (Discrete Channel Impulse Response):
   h = [h_0, h_1, h_2]
   - h_0 : Main-cursor (Nang luong bit hien tai, vi du: 0.60V)
   - h_1 : Post-cursor 1 (Nhiễu tran sang bit tiep theo k+1, vi du: 0.35V)
   - h_2 : Post-cursor 2 (Nhiễu tran sang bit k+2, vi du: 0.15V)

2. Tin hieu thu duoc tai bo lay mau RX (Received Signal with ISI):
   y[k] = h_0 * x[k] + h_1 * x[k-1] + h_2 * x[k-2] + noise[k]

   Trong do:
   - x[k] in {-1.0, +1.0} la muc dien ap ky tu truyen NRZ (Bipolar).
   - Thanh phan mong muon: h_0 * x[k]
   - Thanh phan nhiễu ISI: (h_1 * x[k-1] + h_2 * x[k-2])

3. Tinh huong xau nhat (Worst-Case ISI & Eye Closure Condition):
   Khi bit hien tai la +1, nhung hai bit truoc do la -1:
   y_worst = h_0 * (+1) - |h_1| - |h_2| = h_0 - (|h_1| + |h_2|)

   Neu (|h_1| + |h_2|) >= h_0:
   -> y_worst <= 0V!
   -> Mac du TX truyen bit +1, bo so sanh RX lai nhan duoc dien ap am <= 0V
      va quyet dinh sai thanh bit 0! Bieu do mat dong hoan toan (Eye Closed)!
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import random


class PCBChannelModel:
    """
    Mo hinh kenh truyen dan cao tan PCB kem suy hao va phan tan xung ISI.
    - impulse_response: Danh sach cac he so [h_0, h_1, h_2, ...]
    - noise_std: Do lech chuan cua nhiễu trang Gauss (AWGN)
    """

    def __init__(self,
                 h0: float = 0.60,
                 h1: float = 0.35,
                 h2: float = 0.15,
                 noise_std: float = 0.02):
        self.h0 = float(h0)
        self.h1 = float(h1)
        self.h2 = float(h2)
        self.noise_std = float(noise_std)

    @property
    def total_isi(self) -> float:
        """
        Tong bien do nhiễu ISI xau nhat: |h1| + |h2|
        """
        return abs(self.h1) + abs(self.h2)

    @property
    def worst_case_eye_opening(self) -> float:
        """
        Do mo mat xau nhat truoc khi co nhieu:
        Eye_Opening = 2 * (h0 - (|h1| + |h2|))
        Neu ket qua <= 0, mat bi dong hoan toan do ISI vuot qua Main Cursor!
        """
        margin = self.h0 - self.total_isi
        return max(0.0, 2.0 * margin)

    @property
    def is_eye_closed(self) -> bool:
        """
        Kiem tra xem bieu do mat co bi dong hoan toan khong.
        """
        return self.total_isi >= self.h0

    def transmit(self, bit_stream: List[int]) -> List[float]:
        """
        Truyen chuoi bit [0, 1] qua kenh suy hao PCB:
        1. Anh xa bit 1 -> +1.0V, bit 0 -> -1.0V (NRZ Bipolar).
        2. Tich chap voi dap ung xung cua kenh: y[k] = h0*x[k] + h1*x[k-1] + h2*x[k-2].
        3. Cong them nhiễu nhiet Gauss AWGN.
        Tra ve chuoi mau tin hieu tuong tu y[k].
        """
        if not bit_stream:
            return []

        # Chuyen doi sang NRZ bipolar {-1.0, +1.0}
        nrz_symbols = [1.0 if b == 1 else -1.0 for b in bit_stream]
        rx_samples = []

        x_prev1 = 0.0
        x_prev2 = 0.0

        for x_curr in nrz_symbols:
            # Tinh toan tin hieu co nhiễu ISI
            y_clean = (self.h0 * x_curr) + (self.h1 * x_prev1) + (self.h2 * x_prev2)
            noise = random.gauss(0.0, self.noise_std)
            rx_samples.append(y_clean + noise)

            # Cap nhat bo nho luu tru cac bit truoc
            x_prev2 = x_prev1
            x_prev1 = x_curr

        return rx_samples

    def slice_decisions(self, rx_samples: List[float], threshold: float = 0.0) -> List[int]:
        """
        Bo so sanh Slicer tai bo thu RX:
        Dien ap >= threshold -> Quyet dinh bit 1
        Dien ap <  threshold -> Quyet dinh bit 0
        """
        return [1 if sample >= threshold else 0 for sample in rx_samples]


if __name__ == "__main__":
    print("=========================================================")
    print("   SERDES HARDWARE: PCB CHANNEL LOSS & ISI DISPERSION")
    print("=========================================================\n")

    # 1. Khoi tao kenh truyen bi suy hao nang (Lossy Channel)
    # Main cursor h0 = 0.50V, h1 = 0.35V, h2 = 0.20V
    # Tong ISI = 0.35 + 0.20 = 0.55V > h0 (0.50V) -> Mat bi dong hoan toan!
    lossy_channel = PCBChannelModel(h0=0.50, h1=0.35, h2=0.20, noise_std=0.01)

    print("1. PHAN TICH NANG LUONG TICH CHAP XUNG & ISI:")
    print(f"   -> Main cursor (h0)          : {lossy_channel.h0:.2f} V")
    print(f"   -> Post-cursor 1 (h1)        : {lossy_channel.h1:.2f} V")
    print(f"   -> Post-cursor 2 (h2)        : {lossy_channel.h2:.2f} V")
    print(f"   -> Tong nang luong ISI (|h1|+|h2|) : {lossy_channel.total_isi:.2f} V")
    print(f"   -> Trang thai bieu do mat    : {'BI DONG HOAN TOAN (CLOSED)' if lossy_channel.is_eye_closed else 'CON MO'}")

    assert lossy_channel.is_eye_closed, "Kenh nay phai bi dong mat vi tong ISI (0.55V) lon hon h0 (0.50V)!"

    # 2. Thu nghiem mau bit xau nhat (Worst-case Bit Pattern)
    # Chuoi bit: [..., 0, 0, 1] -> Bipolar: [..., -1, -1, +1]
    # Bit hien tai la +1, nhung 2 bit truoc la -1.
    worst_pattern = [0, 0, 1]
    rx_analog = lossy_channel.transmit(worst_pattern)
    print("\n2. PHAN TICH MAU BIT GAY SAP NGUONG DIEN AP (WORST-CASE PATTERN):")
    print(f"   -> Chuoi bit phat di (TX)    : {worst_pattern}")
    print(f"   -> Dien ap thu duoc tai bit 3: {rx_analog[2]:.3f} V")

    # Tinh toan ly thuyet tai bit 3: h0*(+1) + h1*(-1) + h2*(-1) = 0.50 - 0.35 - 0.20 = -0.05V
    # Dien ap bi am du bit phat la bit 1!
    decisions = lossy_channel.slice_decisions(rx_analog)
    print(f"   -> Bit quyet dinh boi Slicer : {decisions}")
    assert decisions[2] == 0, "Bo so sanh phai bi danh lua thanh bit 0 do dien ap bi keo xuong am!"
    print("   -> Ket luan                   : PHAT HIEN LOI BIT! (Bit +1 bi nhan thanh bit 0 do ISI)\n")

    # 3. Kiem tra kenh chat luong cao (Low-loss Channel)
    # h0 = 0.80V, h1 = 0.10V, h2 = 0.05V -> Tong ISI = 0.15V << h0
    clean_channel = PCBChannelModel(h0=0.80, h1=0.10, h2=0.05, noise_std=0.01)
    eye_open = clean_channel.worst_case_eye_opening
    print("3. DOI SANH KENH SUY HAO THAP (LOW-LOSS CHANNEL):")
    print(f"   -> Main cursor (h0)          : {clean_channel.h0:.2f} V")
    print(f"   -> Tong ISI                  : {clean_channel.total_isi:.2f} V")
    print(f"   -> Do mo mat xau nhat        : {eye_open:.2f} V")
    assert not clean_channel.is_eye_closed, "Kenh chat luong tot phai giu duoc bieu do mat mo!"
    assert eye_open > 1.0, "Do mo mat phai lon hon 1.0V!"

    print("\n[THANH CONG] DA HOAN THANH MO HINH HOA KENH TRUYEN PCB VA HIEN TUONG NHIEU XUYEN KY TU ISI!")
