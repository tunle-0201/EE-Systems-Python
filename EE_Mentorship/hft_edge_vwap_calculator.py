"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
    MILESTONE Q.3: TINH TOAN GIA KHOP BINH QUAN GIA QUYEN THEO KHOI LUONG (VWAP)
================================================================================

1. NGUYEN LY THUAT TOAN DINH LUONG & THUC THI LENH (QUANTITATIVE ALGORITHMS):
   - Tai sao cac quy dau tu khong lo (BlackRock, Vanguard, Citadel) khong bao gio
     mua 1 trieu co phieu cung luc bang lenh thi truong (Market Order)?
     + Mua qua lon cung luc se lam gia tang vot dot bien (Market Impact / Slippage)!
     + Ho chia nho lenh ra lam hang nghin lenh con ban tia trong ngay theo chi so VWAP.
   - Chi so VWAP (Volume-Weighted Average Price - Gia binh quan gia quyen khoi luong):
     + La thuoc do chuan muc vang de danh gia chat luong thuc thi lenh cua thuat toan.
     + Neu Mua duoc o gia THAP hon VWAP thi thuat toan chay xuat sac (Co Alpha loi nhuan).
     + Neu Mua o gia CAO hon VWAP thi bi truot gia bat loi.

2. SO DO KHONG GIAN GIA QUYEN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do phan bo Khoi luong va Gia tri giao dich theo thoi gian:

   Khoi luong (CP)
     ▲        ┌────┐
     │        │ 200│ (Lenh lon tai 105.00 USD)
     │   ┌────┤    ├────┐
     │   │ 100│    │ 100│
     └───┴────┴────┴────┴────► Thoi gian (Phien giao dich)
       100.00 105.00 110.00  (Muc gia khop)

   Cong thuc tinh VWAP tong the (Batch Formulation):

            Tong gia tri giao dich (Total Notional Value)
   VWAP  =  ──────────────────────────────────────────────
               Tong khoi luong giao dich (Total Volume)

            Sum( Gia_i * Khoi_luong_i )
   VWAP  =  ────────────────────────────
                 Sum( Khoi_luong_i )

   Cong thuc cap nhat dong Online tuc thi O(1) tren phan cung FPGA:

   Tong_Gia_tri_moi  = Tong_Gia_tri_cu  + (Gia_moi * Khoi_luong_moi)
   Tong_Khoi_luong_moi = Tong_Khoi_luong_cu + Khoi_luong_moi

                           Tong_Gia_tri_moi
   VWAP_cap_nhat     = ─────────────────────────
                          Tong_Khoi_luong_moi
"""

from typing import List, Tuple
import numpy as np


class OnlineVwapTracker:
    """
    Bo theo doi VWAP thoi gian thuc tren phan cung nhung voi do phuc tap O(1).
    """
    def __init__(self):
        self.total_notional: float = 0.0  # Tong so tien giao dich (USD)
        self.total_volume: int = 0         # Tong so co phieu

    def update(self, price: float, volume: int) -> float:
        """
        Cap nhat them 1 giao dich khop lenh moi:
        - price: Muc gia khop (USD)
        - volume: So luong co phieu
        Tra ve: VWAP tuc thi hien tai
        """
        self.total_notional += float(price) * int(volume)
        self.total_volume += int(volume)
        if self.total_volume == 0:
            return 0.0
        return self.total_notional / self.total_volume

    @property
    def current_vwap(self) -> float:
        if self.total_volume == 0:
            return 0.0
        return self.total_notional / self.total_volume


def calculate_vwap(trades_list: List[Tuple[float, int]]) -> float:
    """
    Ham backward-compatible giu nguyen signature cua Milestone Q.3:
    trades_list: [(price, volume), ...]
    """
    total_dollar = sum(p * v for p, v in trades_list)
    total_vol = sum(v for p, v in trades_list)
    return total_dollar / total_vol if total_vol > 0 else 0.0


def compute_execution_slippage(executed_price: float, benchmark_vwap: float, side: str = "BUY") -> float:
    """
    Tinh toan do truot gia (Slippage) so voi moc chuan VWAP:
    - BUY: Slippage am (< 0) la tot vi mua re hon thi truong.
    - SELL: Slippage duong (> 0) la tot vi ban dat hon thi truong.
    """
    if side.upper() == "BUY":
        return executed_price - benchmark_vwap
    else:
        return benchmark_vwap - executed_price


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: VWAP EXECUTION ENGINE")
    print("=========================================================\n")

    # 3 lenh khop: (100.00 USD, 100CP), (105.00 USD, 200CP), (110.00 USD, 100CP)
    # Tong gia tri = 100*100 + 105*200 + 110*100 = 10,000 + 21,000 + 11,000 = 42,000 USD
    # Tong khoi luong = 400CP -> VWAP = 42,000 / 400 = 105.00 USD
    trades = [(100.0, 100), (105.0, 200), (110.0, 100)]
    vwap_res = calculate_vwap(trades)

    print("1. KET QUA TINH GIA BINH QUAN THI TRUONG VWAP:")
    print(f"   -> Gia trung binh VWAP : {vwap_res:.2f} USD")
    assert abs(vwap_res - 105.0) < 1e-5, "Loi VWAP Calculator!"

    # 2. Thu nghiem Bo theo doi Online VWAP Tracker
    tracker = OnlineVwapTracker()
    for p, v in trades:
        cur = tracker.update(p, v)

    print("\n2. THEO DOI VWAP STREAMING O(1):")
    print(f"   -> Tong gia tri giao dich : {tracker.total_notional:.2f} USD")
    print(f"   -> Tong khoi luong co phieu: {tracker.total_volume} CP")
    print(f"   -> VWAP tich luy cuoi cung: {tracker.current_vwap:.2f} USD")
    assert abs(tracker.current_vwap - 105.0) < 1e-5

    # 3. Kiem tra Slippage danh gia hieu nang
    my_buy_price = 104.20
    slippage = compute_execution_slippage(my_buy_price, tracker.current_vwap, side="BUY")
    print(f"\n3. DANH GIA CHAT LUONG LENH (SLIPPAGE): {slippage:.2f} USD (Mua thap hon VWAP -> Co loi!)")
    assert slippage < 0.0

    print("\n[THANH CONG] DA HOAN THANH ENGINE TINH TOAN VWAP SIEU TOC CHO HE THONG GIAO DICH!")
