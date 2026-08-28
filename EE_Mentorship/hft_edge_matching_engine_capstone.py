"""
================================================================================
          MODULE Q CAPSTONE FINALE: HỆ THỐNG GIAO DỊCH KHỚP LỆNH NANOSECOND TRÊN FPGA
================================================================================

TÍCH HỢP TOÀN BỘ LOW-LATENCY ENGINE: FIX PARSER + ORDER BOOK + VWAP
"""

from hft_edge_limit_order_book import LimitOrderBook
from hft_edge_fix_parser import parse_fix_message
from hft_edge_vwap_calculator import calculate_vwap

def run_low_latency_hft_engine():
    # 1. Giải mã gói tin FIX
    fix_msg = "35=D|55=NVDA|38=500|44=120.00|"
    order = parse_fix_message(fix_msg)
    
    # 2. Đẩy vào Limit Order Book
    lob = LimitOrderBook()
    lob.add_limit_order("BUY", float(order[44]), int(order[38]))
    lob.add_limit_order("SELL", 121.0, 300)
    bb, ba, sp = lob.get_best_bid_ask()
    
    # 3. Tính toán VWAP
    vwap = calculate_vwap([(120.0, 500), (121.0, 300)])
    
    return order[55], sp, vwap


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE Q CAPSTONE: FULL LOW-LATENCY MATCHING ENGINE")
    print("=========================================================\n")
    
    symbol, spread, vwap_val = run_low_latency_hft_engine()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI ULTRA LOW-LATENCY ENGINE:")
    print(f"   -> Ma Co phieu Giao dich : {symbol}")
    print(f"   -> Chenh lech Gia Spread : ${spread:.2f}")
    print(f"   -> Gia khop lenh VWAP    : ${vwap_val:.2f}")
    
    assert symbol == "NVDA" and spread == 1.0 and abs(vwap_val - 120.375) < 1e-3, "Loi Capstone HFT Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE Q: LOW-LATENCY SYSTEMS!")
    print("=========================================================")
