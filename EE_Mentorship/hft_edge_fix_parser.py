"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
              MILESTONE Q.2: BỘ GIẢI MÃ GIAO THỨC CHUẨN FIX PROTOCOL (TAG=VALUE)
================================================================================

TẠI SAO GIAO THỨC FIX LÀ CHUẨN TRUYỀN THÔNG SỐ 1 CỦA THỊ TRƯỜNG TÀI CHÍNH TOÀN CẦU?
Giao thức FIX (Financial Information eXchange):
- Dữ liệu dạng cặp Tag=Value phân tách bằng ký tự SOH (ASCII 1 hoặc '|'):
  + Tag 35: MsgType (D = New Order)
  + Tag 55: Symbol (AAPL, TSLA, NVDA)
  + Tag 38: OrderQty (Số lượng cổ phiếu)
  + Tag 44: Price (Mức giá đặt)
"""

def parse_fix_message(fix_str: str, delimiter="|") -> dict:
    """
    Trò đóng vai Kỹ sư giao thức nhúng Low-Latency:
    - Tách chuỗi theo ký tự phân cách delimiter
    - Với mỗi cặp tag=val, nạp vào dictionary: parsed[int(tag)] = val
    - Trả về: parsed
    """
    parsed = {}
    tokens = fix_str.split(delimiter)
    for t in tokens:
        if "=" in t:
            tag, val = t.split("=", 1)
            parsed[int(tag)] = val
    return parsed


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: FAST FIX PROTOCOL PARSER")
    print("=========================================================\n")
    
    # Gói tin đặt lệnh mua 100 cổ phiếu Tesla ở giá $250.5
    raw_fix = "8=FIX.4.2|35=D|55=TSLA|38=100|44=250.50|10=128|"
    order = parse_fix_message(raw_fix, delimiter="|")
    
    print("1. KET QUA GIAI MA GIAO THUC FIX PROTOCOL REAL-TIME:")
    print(f"   -> Ma Co phieu (Tag 55) : {order[55]}")
    print(f"   -> So luong dat (Tag 38) : {order[38]} CP")
    print(f"   -> Muc gia dat  (Tag 44) : ${order[44]}")
    
    assert order[55] == "TSLA" and order[38] == "100" and order[44] == "250.50", "Loi FIX Parser!"
    print("\n[THANH CONG] DA HOAN THANH BO GIAI MA GIAO THUC TAI CHINH SIEU TOC FIX CHO HE THONG!")
