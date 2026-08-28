"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
              MILESTONE Q.1: SỔ LỆNH GIỚI HẠN (LIMIT ORDER BOOK MATCHING ENGINE)
================================================================================

TẠI SAO CÁC KỸ SƯ EE HỆ THỐNG / CHIP CẦN HIỂU ORDER BOOK MATCHING?
Các hệ thống giao dịch siêu tốc (High-Frequency Trading - HFT) chạy trực tiếp trên FPGA/C++:
- Sổ lệnh Limit Order Book (LOB) quản lý 2 phía: Bids (Giá Mua) và Asks (Giá Bán).
- Khớp lệnh ưu tiên Giá tốt nhất (Price-Time Priority):
  + Best Bid: Giá mua cao nhất.
  + Best Ask: Giá bán thấp nhất.
  + Spread = Best Ask - Best Bid.
"""

class LimitOrderBook:
    def __init__(self):
        self.bids = {} # {price: volume}
        self.asks = {} # {price: volume}
    
    def add_limit_order(self, side: str, price: float, volume: int):
        book = self.bids if side == "BUY" else self.asks
        book[price] = book.get(price, 0) + volume
    
    def get_best_bid_ask(self):
        best_bid = max(self.bids.keys()) if self.bids else 0.0
        best_ask = min(self.asks.keys()) if self.asks else 0.0
        spread = best_ask - best_bid if (best_bid and best_ask) else 0.0
        return best_bid, best_ask, spread


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: LIMIT ORDER BOOK (LOB) ENGINE")
    print("=========================================================\n")
    
    lob = LimitOrderBook()
    lob.add_limit_order("BUY", price=100.5, volume=50)
    lob.add_limit_order("BUY", price=100.8, volume=100) # Best Bid
    lob.add_limit_order("SELL", price=101.2, volume=80) # Best Ask
    lob.add_limit_order("SELL", price=101.5, volume=30)
    
    bb, ba, sp = lob.get_best_bid_ask()
    
    print("1. KET QUA QUAN LY SO LENH LIMIT ORDER BOOK:")
    print(f"   -> Best Bid (Gia Mua cao nhat) : ${bb:.2f}")
    print(f"   -> Best Ask (Gia Ban thap nhat): ${ba:.2f}")
    print(f"   -> Chenh lech Gia (Spread)     : ${sp:.2f}")
    
    assert bb == 100.8 and ba == 101.2 and abs(sp - 0.4) < 1e-5, "Loi Order Book!"
    print("\n[THANH CONG] DA HOAN THANH SO LENH GIAO DICH SIEU TOC TREN FPGA CHO HE THONG!")
