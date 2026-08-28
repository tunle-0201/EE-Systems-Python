"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
              MILESTONE Q.3: TÍNH TOÁN GIÁ KHỚP BÌNH QUÂN GIA QUYỀN (VWAP ENGINE)
================================================================================

TẠI SAO CÁC ALGORITHM TRADING ENGINE DÙNG VWAP?
VWAP (Volume-Weighted Average Price):
  VWAP = Sum(Price * Volume) / Sum(Volume)
- Đánh giá chất lượng thực thi lệnh của thuật toán so với giá bình quân của toàn bộ thị trường.
"""

import numpy as np

def calculate_vwap(trades_list):
    """
    trades_list: [(price, volume), ...]
    Trò đóng vai Kỹ sư định lượng:
    - total_dollar_volume = sum(p * v for p, v in trades_list)
    - total_shares = sum(v for p, v in trades_list)
    - vwap = total_dollar_volume / total_shares
    - Trả về: vwap
    """
    total_dollar = sum(p * v for p, v in trades_list)
    total_vol = sum(v for p, v in trades_list)
    return total_dollar / total_vol if total_vol > 0 else 0.0


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: VWAP EXECUTION ENGINE")
    print("=========================================================\n")
    
    # 3 lệnh khớp: (100$, 100CP), (105$, 200CP), (110$, 100CP)
    # Total $ = 100*100 + 105*200 + 110*100 = 10,000 + 21,000 + 11,000 = 42,000$
    # Total Vol = 400CP -> VWAP = 42,000 / 400 = 105.0$
    trades = [(100.0, 100), (105.0, 200), (110.0, 100)]
    vwap_res = calculate_vwap(trades)
    
    print("1. KET QUA TINH GIA BINH QUAN THI TRUONG VWAP:")
    print(f"   -> Gia trung binh VWAP : ${vwap_res:.2f}")
    
    assert abs(vwap_res - 105.0) < 1e-5, "Loi VWAP Calculator!"
    print("\n[THANH CONG] DA HOAN THANH ENGINE TINH TOAN VWAP SIEU TOC CHO HE THONG GIAO DICH!")
