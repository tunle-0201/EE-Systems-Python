"""
================================================================================
          MODULE AD: MISSION-CRITICAL AEROSPACE AVIONICS PROTOCOLS
          MILESTONE AD.1: MIL-STD-1553B DUAL-REDUNDANT COMMAND-RESPONSE BUS
================================================================================

TAI SAO GIAO THUC MIL-STD-1553B DUOC DUNG TREN SPACEX STARSHIP VA NASA ORION?
- MIL-STD-1553B la tieu chuan mang may tinh bay quan su va vu tru tin cay bac nhat
  lich su hang khong (Space Shuttle, ISS, F-16/F-35, SpaceX Dragon, Falcon 9).
- Moi truong vu tru va ten lua co nhiễu dien tu cuc manh (EMI) tu dong co day va
  tia set khi phong xuyen qua tang khi quyen:
  1. Su dung cap xoan doi co vo boc kim (Shielded Twisted Pair) truyen vi sai.
  2. Ma hoa Manchester II Bi-Phase-L: Tu dong bo xung nhip, triet tieu thanh phan
     mot chieu (Zero DC bias), khong bao gio bi troi dien ap phan cuc.
  3. Kien truc chu - to (Command-Response): Chi co duy nhat Bus Controller (BC)
     duoc phep khoi mao duong truyen, loai bo 100% nguy co xung dot goi tin (Collision-Free).

SO DO DANG SONG MA HOA MANCHESTER II VA SYNC PULSE (ASCII DIAGRAM):

   Bit 1: Cao xuong Thap         Bit 0: Thap len Cao       Sync Command/Status (3 bits):
     +───+                         +───+                    +───────+
     |   |                         |   |                    |       | (1.5 bit Cao)
   ──+   +───                    ──+   +───               ──+       +───────+
     |   |                         |   |                            |       | (1.5 bit Thap)
     Cao Thap                      Thap Cao                         +───────+

TOAN HOC CAU TRUC TU 20-BIT MIL-STD-1553B (ASCII MATH BLOCKS):

1. Cau truc mot tu 20-bit (Moi bit dai dung 1.0 micro-giay tren cong 1.0 Mbps):
   +────────────────+──────────────────────────────────+────────────+
   |  Sync (3 bits) |     Du lieu Payload (16 bits)     | Parity (1) |
   +────────────────+──────────────────────────────────+────────────+
   - Sync: Dang song 3-bit khong hop le trong Manchester de nhan dien dau tu.
     + Command/Status Sync: 1.5 bit Cao tiep theo 1.5 bit Thap.
     + Data Sync: 1.5 bit Thap tiep theo 1.5 bit Cao.

2. Bit Parity le (Odd Parity Bit):
   Tong so bit 1 trong 16-bit Payload va bit Parity phai la mot so LE:
   Odd_Parity = 1 - (sum_bits(Payload) % 2)

3. Ba loai tu chinh trong giao thuc:
   - Command Word : RT_Address (5b) | T/R (1b) | Subaddress (5b) | Word_Count (5b)
   - Data Word    : Du lieu 16-bit payload (0x0000 - 0xFFFF)
   - Status Word  : RT_Address (5b) | Message_Error (1b) | Flags... | Parity (1b)

4. Thoi gian dap ung hop le cua Remote Terminal (RT):
   4.0 microseconds <= t_response <= 12.0 microseconds
"""

from typing import Tuple, List, Dict, Any, Optional


def compute_odd_parity(data16: int) -> int:
    """
    Tinh bit Parity le cho tu du lieu 16-bit:
    Tong so bit 1 trong data16 va bit parity phai la so LE.
    """
    ones_count = bin(data16 & 0xFFFF).count('1')
    return 0 if (ones_count % 2 == 1) else 1


def verify_odd_parity(data16: int, parity_bit: int) -> bool:
    """
    Kiem tra tinh hop le cua Parity le:
    Tra ve True neu tong so bit 1 la so LE.
    """
    total_ones = bin(data16 & 0xFFFF).count('1') + (1 if parity_bit == 1 else 0)
    return total_ones % 2 == 1


class CommandWord:
    """
    Tu lenh (Command Word) do Bus Controller (BC) phat di.
    - rt_address: Dia chi Remote Terminal (5 bits: 0 - 31, 31 la Broadcast)
    - tr_bit: 1 = Transmit (RT gui du lieu ve), 0 = Receive (RT nhan du lieu tu BC)
    - subaddress: Dia chi phan he (5 bits: 1 - 30)
    - word_count: So luong tu du lieu (5 bits: 1 - 31, 0 dai dien cho 32 words)
    """

    def __init__(self, rt_address: int, tr_bit: int, subaddress: int, word_count: int):
        self.rt_address = int(rt_address) & 0x1F
        self.tr_bit = int(tr_bit) & 0x01
        self.subaddress = int(subaddress) & 0x1F
        self.word_count = int(word_count) & 0x1F
        self.raw_16bit = (self.rt_address << 11) | (self.tr_bit << 10) | (self.subaddress << 5) | self.word_count
        self.parity = compute_odd_parity(self.raw_16bit)

    @classmethod
    def from_raw(cls, raw_16bit: int, parity_bit: int) -> "CommandWord":
        if not verify_odd_parity(raw_16bit, parity_bit):
            raise ValueError("Loi Parity trong Command Word!")
        rt_addr = (raw_16bit >> 11) & 0x1F
        tr = (raw_16bit >> 10) & 0x01
        subaddr = (raw_16bit >> 5) & 0x1F
        wc = raw_16bit & 0x1F
        return cls(rt_addr, tr, subaddr, wc)


class DataWord:
    """
    Tu du lieu (Data Word) mang 16-bit thong tin cam bien hoac lenh co cau chap hanh.
    """

    def __init__(self, data_value: int):
        self.raw_16bit = int(data_value) & 0xFFFF
        self.parity = compute_odd_parity(self.raw_16bit)

    @classmethod
    def from_raw(cls, raw_16bit: int, parity_bit: int) -> "DataWord":
        if not verify_odd_parity(raw_16bit, parity_bit):
            raise ValueError("Loi Parity trong Data Word!")
        return cls(raw_16bit)


class StatusWord:
    """
    Tu trang thai (Status Word) do Remote Terminal (RT) phan hoi ve Bus Controller.
    - rt_address: Dia chi RT (5 bits)
    - message_error: Co bao loi goi tin (1 bit: 1 = Loi)
    - busy: Co bao ban (1 bit: 1 = RT dang ban xu ly)
    """

    def __init__(self, rt_address: int, message_error: int = 0, busy: int = 0):
        self.rt_address = int(rt_address) & 0x1F
        self.message_error = int(message_error) & 0x01
        self.busy = int(busy) & 0x01
        self.raw_16bit = (self.rt_address << 11) | (self.message_error << 10) | (self.busy << 3)
        self.parity = compute_odd_parity(self.raw_16bit)

    @classmethod
    def from_raw(cls, raw_16bit: int, parity_bit: int) -> "StatusWord":
        if not verify_odd_parity(raw_16bit, parity_bit):
            raise ValueError("Loi Parity trong Status Word!")
        rt_addr = (raw_16bit >> 11) & 0x1F
        msg_err = (raw_16bit >> 10) & 0x01
        busy = (raw_16bit >> 3) & 0x01
        return cls(rt_addr, msg_err, busy)


class RemoteTerminal:
    """
    Mo phong mot thiet bi Remote Terminal (RT) tren tau vu tru (vi du: May tinh Gimbal TVC).
    """

    def __init__(self, address: int):
        self.address = int(address) & 0x1F
        self.memory: Dict[int, List[int]] = {i: [0] * 32 for i in range(1, 31)}
        self.last_status: Optional[StatusWord] = None

    def receive_command_and_data(
        self,
        cmd: CommandWord,
        data_words: List[DataWord],
        response_time_us: float = 6.0
    ) -> Tuple[StatusWord, float]:
        """
        Nhan lenh Receive tu Bus Controller, ghi du lieu vao bo nho va tra ve Status Word.
        """
        # Kiem tra dia chi RT co khop khong
        if cmd.rt_address != self.address and cmd.rt_address != 31:  # 31 la broadcast
            raise ValueError(f"Dia chi RT khong khop! Nhan {cmd.rt_address}, can {self.address}")

        # Kiem tra thoi gian dap ung chuan 1553B: 4.0 us <= t <= 12.0 us
        if not (4.0 <= response_time_us <= 12.0):
            status = StatusWord(self.address, message_error=1)
            self.last_status = status
            return status, response_time_us

        # Kiem tra so luong tu du lieu
        expected_count = 32 if cmd.word_count == 0 else cmd.word_count
        if len(data_words) != expected_count:
            status = StatusWord(self.address, message_error=1)
            self.last_status = status
            return status, response_time_us

        # Ghi vao bo nho subaddress
        subaddr = cmd.subaddress
        if subaddr in self.memory:
            self.memory[subaddr] = [dw.raw_16bit for dw in data_words]

        status = StatusWord(self.address, message_error=0, busy=0)
        self.last_status = status
        return status, response_time_us


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS: MIL-STD-1553B COMMAND-RESPONSE DUAL BUS")
    print("=========================================================\n")

    # 1. Kiem tra tinh toan va kiem tra Odd Parity chuan xac
    test_val = 0x1234  # Nhị phân: 0001 0010 0011 0100 (Có 5 bit 1 -> Là số LẺ)
    parity_calc = compute_odd_parity(test_val)
    print("1. KIEM TRA CO CHE ODD PARITY CUA TU 20-BIT:")
    print(f"   -> Gia tri Payload 16-bit    : 0x{test_val:04X} (So bit 1: {bin(test_val).count('1')})")
    print(f"   -> Bit Odd Parity duoc tao   : {parity_calc} (Tong so bit 1: {bin(test_val).count('1') + parity_calc})")
    assert parity_calc == 0, "Do da co 5 bit 1 (so le), bit parity phai bang 0!"
    assert verify_odd_parity(test_val, parity_calc), "Kiem tra Parity phai tra ve True!"
    print("   -> Ket qua                   : CHINH XAC (Dung tieu chuan Odd Parity 1553B)\n")

    # 2. Tao Command Word dieu khien goc lai dong co ten lua TVC (RT Address = 5, Subaddress = 12, 2 Data Words)
    # T/R bit = 0 (Receive - BC gui du lieu xuong RT)
    cmd_tvc = CommandWord(rt_address=5, tr_bit=0, subaddress=12, word_count=2)
    print("2. DONG GOI TU LENH (COMMAND WORD):")
    print(f"   -> Dia chi RT (RT Address)   : {cmd_tvc.rt_address} (Thiet bi Gimbal dong co #5)")
    print(f"   -> Huong truyen (T/R)        : {cmd_tvc.tr_bit} (0 = BC gui xuong RT)")
    print(f"   -> Subaddress                : {cmd_tvc.subaddress}")
    print(f"   -> So luong tu (Word Count)  : {cmd_tvc.word_count} tu")
    print(f"   -> Ma 16-bit Command Word    : 0x{cmd_tvc.raw_16bit:04X}")
    print(f"   -> Bit Parity le             : {cmd_tvc.parity}\n")

    # 3. Tao 2 Data Words mang goc lai Gimbal Pitch va Yaw
    pitch_angle_raw = 0x05DC  # Gia lap ma goc Pitch +15.0 do
    yaw_angle_raw = 0xFA24    # Gia lap ma goc Yaw -15.0 do
    dw_pitch = DataWord(pitch_angle_raw)
    dw_yaw = DataWord(yaw_angle_raw)
    print("3. DONG GOI TU DU LIEU (DATA WORDS):")
    print(f"   -> Data Word #1 (Pitch)      : 0x{dw_pitch.raw_16bit:04X} (Parity: {dw_pitch.parity})")
    print(f"   -> Data Word #2 (Yaw)        : 0x{dw_yaw.raw_16bit:04X} (Parity: {dw_yaw.parity})\n")

    # 4. Mo phong Remote Terminal #5 nhan lenh va phan hoi Status Word
    gimbal_rt = RemoteTerminal(address=5)
    status_resp, t_resp = gimbal_rt.receive_command_and_data(
        cmd=cmd_tvc,
        data_words=[dw_pitch, dw_yaw],
        response_time_us=6.5  # Nam trong dai chuan 4.0 - 12.0 us
    )

    print("4. KET QUA GIAO TIEP VA PHAN HOI TU REMOTE TERMINAL (RT #5):")
    print(f"   -> Thoi gian dap ung (t_resp): {t_resp:.1f} us (Hop le trong dai 4.0 - 12.0 us)")
    print(f"   -> RT Address trong Status   : {status_resp.rt_address}")
    print(f"   -> Message Error Bit         : {status_resp.message_error} (0 = Khong co loi)")
    print(f"   -> Du lieu ghi vao Subaddr 12: {[hex(x) for x in gimbal_rt.memory[12][:2]]}")

    assert status_resp.message_error == 0, "Giao tiep phai thanh cong khong co loi!"
    assert gimbal_rt.memory[12][0] == pitch_angle_raw
    assert gimbal_rt.memory[12][1] == yaw_angle_raw

    # 5. Kiem tra tinh huong bien: Loi Parity (Do nhieu tia set hoac EMI)
    print("\n5. KIEM TRA PHAT HIEN LOI PARITY (NOISE DETECTION):")
    corrupted_data = 0x1234
    corrupted_parity = 1  # Co tinh lam sai Parity
    parity_valid = verify_odd_parity(corrupted_data, corrupted_parity)
    print(f"   -> Kiem tra Parity bi loi    : Hop le = {parity_valid}")
    assert not parity_valid, "He thong phai phat hien Parity bi loi!"
    print("   -> Ket luan                   : PHAT HIEN LOI BIT THANH CONG!")

    print("\n[THANH CONG] DA HOAN THANH GIAO THUC MANG MAY TINH BAY MIL-STD-1553B CHO TAU VU TRU!")
