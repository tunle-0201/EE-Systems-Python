"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
    MILESTONE Q.1: SO LENH GIOI HAN LIMIT ORDER BOOK (LOB) DO TRE NANOSECOND
================================================================================

1. NGUYEN LY HE THONG PHAN CUNG & HFT (FPGA & LOW-LATENCY SYSTEMS):
   - Tai sao Ky su Phan cung (Electrical & Computer Engineers) duoc cac quy HFT hang
     dau (Jane Street, Citadel, Jump Trading) san don voi muc luong trieu USD?
     + Cac san giao dich chung khoan (NYSE, NASDAQ, CME) khop lenh o toc do Nanosecond (10^-9 giay).
     + Stack mang he dieu hanh truyen thong (Linux TCP Kernel, CPU context switch)
       gay tre toi 5 - 20 microsecond -> Qua cham, bi doi thu "front-run"!
     + Ky su EE lap trinh truc tiep tren chip FPGA (Xilinx UltraScale+, Intel Stratix 10)
       va ASIC: nhan goi tin quang 10GbE/100GbE qua cong SFP+, giai ma bang phan cung
       va quan ly So lenh Limit Order Book ngay trong On-Chip Block RAM (BRAM).
   - So lenh Limit Order Book (LOB) quan ly 2 hang doi:
     + Bids (Phia Mua): Cac lenh cho mua, sap xep uu tien theo Gia cao nhat (Best Bid).
     + Asks (Phia Ban): Cac lenh cho ban, sap xep uu tien theo Gia thap nhat (Best Ask).
     + Do lech gia (Spread): Khoang cach giua Best Ask va Best Bid.

2. SO DO HINH HOC SO LENH & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do cau truc So lenh 2 phia (Two-Sided Limit Order Book Structure):

          ASKS (LENH BAN - Sap xep tang dan tu Best Ask tro len)
          ┌─────────────┬─────────────┐
          │  Gia (USD)  │  Khoi luong │
          ├─────────────┼─────────────┤
          │   101.50    │     30      │
          │   101.20    │     80      │ ◄── BEST ASK (Gia ban re nhat thi truong)
          └─────────────┴─────────────┘
  ─────── [ SPREAD = Best Ask - Best Bid = 101.20 - 100.80 = 0.40 USD ] ───────
          ┌─────────────┬─────────────┐
          │   100.80    │    100      │ ◄── BEST BID (Gia mua cao nhat thi truong)
          │   100.50    │     50      │
          └─────────────┴─────────────┘
          BIDS (LENH MUA - Sap xep giam dan tu Best Bid tro xuong)

   Cong thuc tinh Do lech gia (Spread) va Gia trung vi (Mid-Price):

   Spread = Best Ask - Best Bid

                 Best Bid + Best Ask
   Mid Price = ───────────────────────
                          2
"""

from typing import Tuple, Dict, List


class LimitOrderBook:
    """
    So lenh gioi han sieu toc mo phong kien truc BRAM tren FPGA.
    """
    def __init__(self):
        # Bang băm luu muc gia va khoi luong tich luy tai moi muc gia
        self.bids: Dict[float, int] = {}  # {price: volume}
        self.asks: Dict[float, int] = {}  # {price: volume}

    def add_limit_order(self, side: str, price: float, volume: int) -> None:
        """
        Nap lenh gioi han vao so lenh:
        - side: 'BUY' (Bids) hoac 'SELL' (Asks)
        - price: Muc gia dat
        - volume: So luong co phieu
        """
        book = self.bids if side.upper() == "BUY" else self.asks
        price_key = round(float(price), 4)
        book[price_key] = book.get(price_key, 0) + int(volume)

    def cancel_order(self, side: str, price: float, volume: int) -> bool:
        """
        Huy lenh hoac giam bot khoi luong tai muc gia.
        """
        book = self.bids if side.upper() == "BUY" else self.asks
        price_key = round(float(price), 4)
        if price_key in book:
            if book[price_key] <= volume:
                del book[price_key]
            else:
                book[price_key] -= volume
            return True
        return False

    def get_best_bid_ask(self) -> Tuple[float, float, float]:
        """
        Truy xuat gia Mua cao nhat (Best Bid), gia Ban re nhat (Best Ask) va Spread:
        Spread = Best Ask - Best Bid
        """
        best_bid = max(self.bids.keys()) if self.bids else 0.0
        best_ask = min(self.asks.keys()) if self.asks else 0.0
        spread = (best_ask - best_bid) if (best_bid > 0.0 and best_ask > 0.0) else 0.0
        return best_bid, best_ask, spread

    def get_mid_price(self) -> float:
        """
        Tinh gia trung vi (Mid-Price) giua 2 phia:
        Mid Price = (Best Bid + Best Ask) / 2
        """
        best_bid, best_ask, _ = self.get_best_bid_ask()
        if best_bid > 0.0 and best_ask > 0.0:
            return (best_bid + best_ask) / 2.0
        return best_bid if best_bid > 0.0 else best_ask

    def get_market_depth(self, depth: int = 3) -> Dict[str, List[Tuple[float, int]]]:
        """
        Xem do sau so lenh L2 (Market Depth): Top N muc gia tot nhat moi ben.
        """
        sorted_bids = sorted(self.bids.items(), key=lambda item: item[0], reverse=True)[:depth]
        sorted_asks = sorted(self.asks.items(), key=lambda item: item[0], reverse=False)[:depth]
        return {"BIDS": sorted_bids, "ASKS": sorted_asks}


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: LIMIT ORDER BOOK (LOB) ENGINE")
    print("=========================================================\n")

    lob = LimitOrderBook()
    # 1. Nap cac lenh mua vao so Bids
    lob.add_limit_order("BUY", price=100.50, volume=50)
    lob.add_limit_order("BUY", price=100.80, volume=100)  # Best Bid

    # 2. Nap cac lenh ban vao so Asks
    lob.add_limit_order("SELL", price=101.20, volume=80)  # Best Ask
    lob.add_limit_order("SELL", price=101.50, volume=30)

    bb, ba, sp = lob.get_best_bid_ask()
    mid = lob.get_mid_price()

    print("1. KET QUA QUAN LY SO LENH LIMIT ORDER BOOK:")
    print(f"   -> Best Bid (Gia Mua cao nhat) : {bb:.2f} USD")
    print(f"   -> Best Ask (Gia Ban thap nhat): {ba:.2f} USD")
    print(f"   -> Chenh lech Gia (Spread)     : {sp:.2f} USD")
    print(f"   -> Gia trung vi (Mid-Price)    : {mid:.2f} USD")

    assert bb == 100.8 and ba == 101.2 and abs(sp - 0.4) < 1e-5, "Loi Order Book!"
    assert abs(mid - 101.0) < 1e-5, "Loi Mid Price!"

    # 3. Kiem tra do sau so lenh L2 Depth
    depth_view = lob.get_market_depth(depth=2)
    print("\n2. DO SAU SO LENH L2 (TOP 2 MUC GIA TOT NHAT):")
    print(f"   -> ASKS (Ban): {depth_view['ASKS']}")
    print(f"   -> BIDS (Mua): {depth_view['BIDS']}")

    print("\n[THANH CONG] DA HOAN THANH SO LENH GIAO DICH SIEU TOC TREN FPGA CHO HE THONG!")
