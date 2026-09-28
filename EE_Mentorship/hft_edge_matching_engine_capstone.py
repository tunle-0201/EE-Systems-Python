"""
================================================================================
          MODULE Q CAPSTONE FINALE: HE THONG GIAO DICH KHOP LENH
           NANOSECOND TREN FPGA TICH HOP (ULTRA LOW-LATENCY ENGINE)
================================================================================

1. KIEN TRUC HE THONG KHOP LENH TAI CHINH TOC DO CAO (HFT MATCHING PIPELINE):
   Day la kien truc he thong tieu chuan duoc trien khai tren cac san giao dich
   chung khoan Nasdaq/CME va cac quy giao dich dinh luong toan cau:
   - Giai doan 1: Giai ma dong goi tin FIX Protocol (Tag=Value) bang bo dem phan cung.
   - Giai doan 2: Nap va cap nhat so lenh Limit Order Book (LOB) theo nguyen tac
                  Price-Time Priority (Uu tien Gia tot nhat va Thoi gian den truoc).
   - Giai doan 3: Khop lenh tuc thi khi Bids vuot Asks va cap nhat chi so VWAP thoi gian thuc.

2. SO DO LUONG DU LIEU DIEU KHIEN REAL-TIME (ASCII ARCHITECTURE):

  +──────────────────────────────────────────────────────────────────────────+
  |        ULTRA LOW-LATENCY HFT MATCHING ENGINE PIPELINE (FPGA/ASIC)        |
  +──────────────────────────────────────────────────────────────────────────+
  |                                                                          |
  |  [ FIX Packet Stream ] ──► [ Fast Tag=Value Parser ]                     |
  |                                     │ Decoded: Symbol, Side, Qty, Price  |
  |                                     ▼                                    |
  |                         [ Limit Order Book BRAM ]                        |
  |                                     │ Price-Time Priority Matching       |
  |                                     ▼                                    |
  |                         [ Execution & VWAP Tracker ]                     |
  |                                     │ Trade Executed, Slippage, VWAP     |
  |                                     ▼                                    |
  |                         [ Risk & Audit Blackbox ]                        |
  +──────────────────────────────────────────────────────────────────────────+
"""

from typing import Tuple, List, Dict, Any
from hft_edge_limit_order_book import LimitOrderBook
from hft_edge_fix_parser import parse_fix_message, FixOrderDecoder
from hft_edge_vwap_calculator import calculate_vwap, OnlineVwapTracker


class MatchingEngineCapstone:
    """
    Dong co khop lenh Low-Latency tich hop FIX Parser + LOB + VWAP Tracker.
    """
    def __init__(self):
        self.books: Dict[str, LimitOrderBook] = {}
        self.trackers: Dict[str, OnlineVwapTracker] = {}
        self.decoder = FixOrderDecoder()

    def get_or_create_book(self, symbol: str) -> LimitOrderBook:
        if symbol not in self.books:
            self.books[symbol] = LimitOrderBook()
            self.trackers[symbol] = OnlineVwapTracker()
        return self.books[symbol]

    def process_fix_packet(self, fix_raw: str) -> Dict[str, Any]:
        order_info = self.decoder.decode(fix_raw)
        symbol = order_info["symbol"]
        side = order_info["side"]
        qty = order_info["quantity"]
        price = order_info["price"]

        book = self.get_or_create_book(symbol)
        tracker = self.trackers[symbol]

        # Nap lenh vao so lenh
        book.add_limit_order(side, price, qty)
        bb, ba, spread = book.get_best_bid_ask()

        # Cap nhat vao tracking giao dich
        cur_vwap = tracker.update(price, qty)

        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "best_bid": bb,
            "best_ask": ba,
            "spread": spread,
            "vwap": cur_vwap
        }


def run_low_latency_hft_engine():
    """
    Ham backward-compatible giu nguyen chu ky kiem thu Milestone Q Capstone:
    1. Giai ma goi tin FIX dat mua co phieu NVDA
    2. Day vao Limit Order Book va tinh do lech Spread
    3. Tinh toan chi so VWAP chuan xac
    """
    # 1. Giai ma goi tin FIX
    fix_msg = "35=D|55=NVDA|38=500|44=120.00|"
    order = parse_fix_message(fix_msg)

    # 2. Day vao Limit Order Book
    lob = LimitOrderBook()
    lob.add_limit_order("BUY", float(order[44]), int(order[38]))
    lob.add_limit_order("SELL", 121.0, 300)
    bb, ba, sp = lob.get_best_bid_ask()

    # 3. Tinh toan VWAP
    # (120.0 * 500 + 121.0 * 300) / 800 = (60000 + 36300) / 800 = 96300 / 800 = 120.375 USD
    vwap = calculate_vwap([(120.0, 500), (121.0, 300)])

    return order[55], sp, vwap


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Q CAPSTONE: FULL LOW-LATENCY MATCHING ENGINE")
    print("=========================================================\n")

    symbol, spread, vwap_val = run_low_latency_hft_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI ULTRA LOW-LATENCY ENGINE:")
    print(f"   -> Ma Co phieu Giao dich : {symbol}")
    print(f"   -> Chenh lech Gia Spread : {spread:.2f} USD")
    print(f"   -> Gia khop lenh VWAP    : {vwap_val:.3f} USD")

    assert symbol == "NVDA" and spread == 1.0 and abs(vwap_val - 120.375) < 1e-3, "Loi Capstone HFT Engine!"

    # 2. Thu nghiem Dong co MatchingEngineCapstone voi dong goi tin streaming
    engine = MatchingEngineCapstone()
    res1 = engine.process_fix_packet("8=FIX.4.2|35=D|55=NVDA|54=1|38=500|44=120.00|10=100|")
    res2 = engine.process_fix_packet("8=FIX.4.2|35=D|55=NVDA|54=2|38=300|44=121.00|10=105|")

    print("\n2. KET QUA KHOP LENH TRUC TIEP QUA PIPELINE FIX CAPSTONE:")
    print(f"   -> NVDA Best Bid : {res2['best_bid']:.2f} USD")
    print(f"   -> NVDA Best Ask : {res2['best_ask']:.2f} USD")
    print(f"   -> NVDA Spread   : {res2['spread']:.2f} USD")
    print(f"   -> NVDA VWAP     : {res2['vwap']:.3f} USD")

    assert res2["spread"] == 1.0 and abs(res2["vwap"] - 120.375) < 1e-3

    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE Q: LOW-LATENCY SYSTEMS!")
    print("=========================================================")
