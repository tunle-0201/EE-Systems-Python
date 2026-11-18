"""
================================================================================
          MODULE Q: HIGH-FREQUENCY SYSTEMS & ULTRA LOW-LATENCY ENGINES
    MILESTONE Q.2: BO GIAI MA GIAO THUC TAI CHINH CHUAN FIX PROTOCOL (TAG=VALUE)
================================================================================

1. NGUYEN LY GIAO THUC & PHAN CUNG NHUNG (FINANCIAL PROTOCOL ARCHITECTURE):
   - Giao thuc FIX (Financial Information eXchange) la tieu chuan quoc te so 1
     ket noi tat ca cac ngan hang dau tu, san chung khoan va quy giao dich toan cau.
   - Dac diem cau truc goi tin FIX:
     + Chuoi du lieu gom cac cap Tag=Value phan tach boi ky tu dac biet SOH (ASCII 1).
     + Khi log ra file hoac mo phong, SOH thuong duoc the hien bang dau gach dung '|'.
   - Cac the (Tags) cot loi trong he thong:
     + Tag 8  : BeginString (Phien ban FIX, vi du: FIX.4.2)
     + Tag 35 : MsgType (Loai thong diep: 'D' = New Order Single, '8' = Execution Report)
     + Tag 55 : Symbol (Ma co phieu: 'AAPL', 'TSLA', 'NVDA')
     + Tag 54 : Side ('1' = Mua/Buy, '2' = Ban/Sell)
     + Tag 38 : OrderQty (Khoi luong co phieu muon giao dich)
     + Tag 44 : Price (Muc gia gioi han)
     + Tag 10 : Checksum (3 chu so kiem tra toan ven goi tin bang ma hoa Modulo 256)

2. SO DO HINH HOC GOI TIN & HOP CONG CU (ASCII DATA STREAM):

   So do giai ma dong byte FIX tren Chip phan cung FPGA:

   Byte Stream tu Card Mang 10GbE ──► [ FPGA Parser State Machine ]
                                                 │
      ┌──────────────────────────────────────────┴──────────────────────────┐
      ▼                                                                     ▼
   8=FIX.4.2 | 35=D | 55=TSLA | 38=100 | 44=250.50 | 10=128 |
   │           │      │         │        │           │
   │           │      │         │        │           └─► Tag 10: Checksum
   │           │      │         │        └─────────────► Tag 44: Price (250.50 USD)
   │           │      │         └──────────────────────► Tag 38: OrderQty (100 CP)
   │           │      └────────────────────────────────► Tag 55: Symbol (TSLA)
   │           └───────────────────────────────────────► Tag 35: MsgType (Dat lenh moi)
   └───────────────────────────────────────────────────► Tag 8 : Phien ban FIX

   Phep toan tinh Checksum (Doi chieu Tag 10):
   
                  ( Tong ma ASCII cua moi byte truoc Tag 10 )
   Checksum =  ─────────────────────────────────────────────  (Lay phan du Modulo 256)
                                    256
"""

from typing import Dict, Any


def parse_fix_message(fix_str: str, delimiter: str = "|") -> Dict[int, str]:
    """
    Giai ma chuoi thong diep FIX protocol thanh bang anh xa {Tag: Value}.
    Trang bi logic kiem tra hop le va loc bo token rong.
    """
    parsed: Dict[int, str] = {}
    tokens = fix_str.split(delimiter)
    for token in tokens:
        token = token.strip()
        if "=" in token:
            tag_str, val = token.split("=", 1)
            try:
                tag_int = int(tag_str)
                parsed[tag_int] = val
            except ValueError:
                continue
    return parsed


def compute_fix_checksum(raw_bytes_str: str, delimiter: str = "|") -> int:
    """
    Tinh ma kiem tra Checksum chuan cua goi tin FIX (Modulo 256):
    Truong 10 luon nam o cuoi cung, ta tinh tong byte cua phan dau truoc truong 10.
    """
    # Lay phan noi dung truoc Tag 10
    if "10=" in raw_bytes_str:
        header_body = raw_bytes_str.split("10=")[0]
    else:
        header_body = raw_bytes_str
    
    ascii_sum = sum(ord(c) for c in header_body)
    return ascii_sum % 256


class FixOrderDecoder:
    """
    Bo giai ma goi tin giao dich FIX tu dong trich xuat thong so nghiep vu.
    """
    def __init__(self, delimiter: str = "|"):
        self.delimiter = delimiter

    def decode(self, fix_raw: str) -> Dict[str, Any]:
        tags = parse_fix_message(fix_raw, self.delimiter)
        
        # Anh xa cac truong du lieu thong dung
        symbol = tags.get(55, "UNKNOWN")
        qty = int(tags.get(38, 0))
        price = float(tags.get(44, 0.0))
        side_code = tags.get(54, "1")
        side = "BUY" if side_code == "1" else "SELL"
        msg_type = tags.get(35, "")

        return {
            "symbol": symbol,
            "quantity": qty,
            "price": price,
            "side": side,
            "msg_type": msg_type,
            "raw_tags": tags
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   LOW-LATENCY SYSTEMS: FAST FIX PROTOCOL PARSER")
    print("=========================================================\n")

    # Goi tin dat lenh mua 100 co phieu Tesla o gia 250.50 USD
    raw_fix = "8=FIX.4.2|35=D|55=TSLA|38=100|44=250.50|10=128|"
    order = parse_fix_message(raw_fix, delimiter="|")

    print("1. KET QUA GIAI MA GIAO THUC FIX PROTOCOL REAL-TIME:")
    print(f"   -> Ma Co phieu (Tag 55) : {order[55]}")
    print(f"   -> So luong dat (Tag 38) : {order[38]} CP")
    print(f"   -> Muc gia dat  (Tag 44) : {order[44]} USD")

    assert order[55] == "TSLA" and order[38] == "100" and order[44] == "250.50", "Loi FIX Parser!"

    # 2. Thu nghiem Bo giai ma nang cao FixOrderDecoder
    decoder = FixOrderDecoder(delimiter="|")
    decoded_info = decoder.decode(raw_fix)
    print("\n2. TRICH XUAT THONG TIN NGHIEP VU:")
    print(f"   -> Lenh : {decoded_info['side']} {decoded_info['quantity']} {decoded_info['symbol']} @ {decoded_info['price']} USD")
    assert decoded_info['symbol'] == "TSLA" and decoded_info['price'] == 250.50

    print("\n[THANH CONG] DA HOAN THANH BO GIAI MA GIAO THUC TAI CHINH SIEU TOC FIX CHO HE THONG!")
