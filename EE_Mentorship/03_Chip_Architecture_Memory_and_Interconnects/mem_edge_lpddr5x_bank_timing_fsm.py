"""
EE MENTORSHIP PROGRAM - MODULE BG (NHOM 46) - BAI 180 (MILESTONE BG.1)
================================================================================
MAY TRANG THAI FSM NGANH NHO LPDDR5X VA KIEM CHUAN RANG BUOC THOI GIAN JEDEC DRAM
================================================================================

Kien truc bo dieu khien bo nho DRAM (DRAM Memory Controller Architecture):
1. May trang thai huu han Bank State Machine (FSM):
   - IDLE        : Nganh nho dang dong, duong bitline duoc nap truoc Vdd/2.
   - ACTIVATING  : Dang kich hoat hang (Row) nap vao Sense Amplifiers (cho tRCD).
   - ACTIVE      : Hang dang mo trong Sense Amplifiers, san sang READ / WRITE (Row Hit).
   - READING     : Dang truyen burst du lieu doc ra bus DQs (cho tCL / tRL).
   - WRITING     : Dang ghi du lieu tu bus DQs vao Sense Amplifiers (cho tCWL / tWL).
   - PRECHARGING : Dang dong hang cu de chuan bi mo hang moi (cho tRP).
   - REFRESHING  : Dang nap lai dien tich cho cac tu dien nho (cho tRFC).

2. Cac rang buoc thoi gian JEDEC khac khe (JEDEC Timing Constraints):
   - tRCD (RAS-to-CAS Delay)     : Thoi gian toi thieu tu ACTIVATE den READ/WRITE.
   - tRP  (Row Precharge Time)   : Thoi gian toi thieu de PRECHARGE mot hang.
   - tRAS (Row Active Time)      : Thoi gian toi thieu mot hang phai mo truoc khi PRECHARGE.
   - tRC  (Row Cycle Time)       : tRC = tRAS + tRP (Chu ky mo lai cung 1 bank).
   - tCL  (CAS Latency)          : Thoi gian tu lenh READ den khi data xuat hien tren bus DQs.
   - tWR  (Write Recovery Time)  : Thoi gian sau burst ghi de tu dien on dinh truoc khi PRECHARGE.
   - tRRD (Row-to-Row Delay)     : Thoi gian toi thieu giua 2 lenh ACTIVATE toi 2 bank khac nhau.
   - tFAW (Four-Activate Window) : Trong khoang thoi gian tFAW, toi da chi 4 lenh ACTIVATE duoc phat.
   - tWTR (Write-to-Read Delay)  : Thoi gian chuyen doi chieu bus tu Ghi sang Doc.
   - tRTW (Read-to-Write Delay)  : Thoi gian chuyen doi chieu bus tu Doc sang Ghi (Turnaround).

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Chu ky hang toi thieu (Row Cycle Time):
     tRC = tRAS + tRP

2. Rang buoc cua so 4 lenh kich hoat (Four-Activate Window):
     Time(ACT_4) - Time(ACT_0) >= tFAW

3. Do tre tong hop khi truy xuat Bo nho (Access Latency):
     Truong hop Row Hit      : Latency = tCL
     Truong hop Row Closed   : Latency = tRCD + tCL
     Truong hop Row Conflict : Latency = tRP + tRCD + tCL
--------------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class DRAMCommandType(Enum):
    ACTIVATE = "ACTIVATE"       # Mo hang (Row) trong Bank
    READ = "READ"               # Doc du lieu tu hang dang mo
    WRITE = "WRITE"             # Ghi du lieu vao hang dang mo
    PRECHARGE = "PRECHARGE"     # Dong hang dang mo, dua Bank ve IDLE
    REFRESH = "REFRESH"         # Lam tuoi tat ca cac Bank (Auto-Refresh)


class BankState(Enum):
    IDLE = "IDLE"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    READING = "READING"
    WRITING = "WRITING"
    PRECHARGING = "PRECHARGING"
    REFRESHING = "REFRESHING"


@dataclass
class LPDDR5XTimingParams:
    """
    Thong so thoi gian tieu chuan JEDEC LPDDR5X-8533 (don vi: Clock Cycles).
    Chu ky clock tCK = 0.468 ns tai tan so 2133 MHz (8533 MT/s 4:1 bus).
    """
    tCK_ns: float = 0.46875     # Chu ky clock (ns)
    tRCD: int = 28              # ACTIVATE to READ/WRITE delay (13.1 ns)
    tRP: int = 28               # PRECHARGE time (13.1 ns)
    tRAS: int = 68              # Row Active time (31.8 ns)
    tRC: int = 96               # Row Cycle time = tRAS + tRP (45.0 ns)
    tCL: int = 28               # CAS Read Latency (13.1 ns)
    tCWL: int = 26              # CAS Write Latency (12.2 ns)
    tBL: int = 8                # Burst Length = 16 (8 clock cycles tren DQs)
    tWR: int = 34               # Write Recovery time (16.0 ns)
    tRRD: int = 6               # ACT-to-ACT delay toi cac Bank khac nhau (2.81 ns)
    tFAW: int = 32              # Four-Activate Window (15.0 ns)
    tWTR: int = 16              # Write-to-Read turnaround delay (7.5 ns)
    tRTW: int = 14              # Read-to-Write turnaround delay (6.5 ns)
    tRFC: int = 280             # Refresh Recovery time (131.25 ns)
    tREFI: int = 8320           # Refresh Interval (3.9 us)


@dataclass
class DRAMBank:
    """Mo phong 1 Nganh nho (Bank) doc lap tren chip LPDDR5X."""
    bank_id: int
    state: BankState = BankState.IDLE
    open_row: Optional[int] = None
    
    # Cac moc thoi gian chu ky ghi nhan lenh gan nhat
    last_act_cycle: int = -100000
    last_read_cycle: int = -100000
    last_write_cycle: int = -100000
    last_pre_cycle: int = -100000
    last_ref_cycle: int = -100000
    state_ready_cycle: int = 0


class LPDDR5XMemoryControllerFSM:
    """
    Dong co kiem tra rang buoc thoi gian JEDEC va may trang thai Bank FSM.
    Quan ly 16 Banks tren 1 Channel LPDDR5X (Bank Architecture 16-Bank).
    """
    def __init__(self, timing: Optional[LPDDR5XTimingParams] = None, num_banks: int = 16):
        self.timing = timing if timing is not None else LPDDR5XTimingParams()
        self.num_banks = num_banks
        self.banks = [DRAMBank(bank_id=i) for i in range(num_banks)]
        self.current_cycle: int = 0
        
        # Luu tru lich su 4 lenh ACTIVATE gan nhat tren toan chip de kiem tra tFAW
        self.act_history: List[int] = []
        
        # Thoi gian hoat dong gan nhat tren Bus DQs chung
        self.bus_last_read_cycle: int = -100000
        self.bus_last_write_cycle: int = -100000
        self.bus_busy_until: int = 0

    def step_cycle(self, cycles: int = 1) -> None:
        """Tien trinh thoi gian controller theo so chu ky clock."""
        self.current_cycle += cycles
        # Cap nhat trang thai cac Bank khi het thoi gian cho
        for b in self.banks:
            if self.current_cycle >= b.state_ready_cycle:
                if b.state == BankState.ACTIVATING:
                    b.state = BankState.ACTIVE
                elif b.state in (BankState.READING, BankState.WRITING):
                    b.state = BankState.ACTIVE
                elif b.state in (BankState.PRECHARGING, BankState.REFRESHING):
                    b.state = BankState.IDLE
                    b.open_row = None

    def can_issue_command(self, cmd: DRAMCommandType, bank_id: int, row_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Kiem tra xem lenh cmd co vi pham bat ky rang buoc thoi gian JEDEC nao khong.
        Tra ve (True, "") neu hop le, hoac (False, "Ly do vi pham") neu bi vi pham.
        """
        if not (0 <= bank_id < self.num_banks):
            return False, f"Bank ID {bank_id} ngoai pham vi [0..{self.num_banks - 1}]"
        
        b = self.banks[bank_id]

        # 1. Kiem tra tinh hop le cua lenh ACTIVATE
        if cmd == DRAMCommandType.ACTIVATE:
            if b.state != BankState.IDLE:
                return False, f"Bank {bank_id} khong o trang thai IDLE (Hien tai: {b.state.value})"
            
            # Kiem tra tRP: Khoang cach tu PRECHARGE den ACTIVATE
            if (self.current_cycle - b.last_pre_cycle) < self.timing.tRP:
                return False, f"Vi pham tRP tren Bank {bank_id}: Cho {self.timing.tRP} cycles, thuc te {self.current_cycle - b.last_pre_cycle}"
            
            # Kiem tra tRC: Khoang cach tu ACTIVATE truoc den ACTIVATE nay tren cung 1 Bank
            if (self.current_cycle - b.last_act_cycle) < self.timing.tRC:
                return False, f"Vi pham tRC tren Bank {bank_id}: Cho {self.timing.tRC} cycles, thuc te {self.current_cycle - b.last_act_cycle}"
            
            # Kiem tra tRRD: Khoang cach giua 2 lenh ACTIVATE toi cac Bank khac nhau
            for other_b in self.banks:
                if (self.current_cycle - other_b.last_act_cycle) < self.timing.tRRD:
                    return False, f"Vi pham tRRD: Cach lenh ACT truoc {self.current_cycle - other_b.last_act_cycle} cycles < tRRD={self.timing.tRRD}"
            
            # Kiem tra tFAW: Toi da 4 lenh ACTIVATE trong cua so tFAW
            recent_acts = [t for t in self.act_history if (self.current_cycle - t) < self.timing.tFAW]
            if len(recent_acts) >= 4:
                return False, f"Vi pham tFAW: Da co 4 lenh ACT trong cua so {self.timing.tFAW} cycles"

            return True, "ACTIVATE OK"

        # 2. Kiem tra tinh hop le cua lenh READ
        elif cmd == DRAMCommandType.READ:
            if b.state not in (BankState.ACTIVE, BankState.READING, BankState.WRITING):
                return False, f"Bank {bank_id} khong o trang thai ACTIVE de READ (Hien tai: {b.state.value})"
            
            # Kiem tra tRCD: Tu ACTIVATE den READ
            if (self.current_cycle - b.last_act_cycle) < self.timing.tRCD:
                return False, f"Vi pham tRCD tren Bank {bank_id}: Cho {self.timing.tRCD} cycles, thuc te {self.current_cycle - b.last_act_cycle}"
            
            # Kiem tra tWTR: Write-to-Read turnaround tren cung 1 chip
            if (self.current_cycle - self.bus_last_write_cycle) < (self.timing.tCWL + self.timing.tBL + self.timing.tWTR):
                rem = (self.timing.tCWL + self.timing.tBL + self.timing.tWTR) - (self.current_cycle - self.bus_last_write_cycle)
                return False, f"Vi pham tWTR tren Bus DQs: Con thieu {rem} cycles de doi chieu bus tu Write sang Read"
            
            # Kiem tra xung dot tren Bus du lieu DQs
            target_dq_start = self.current_cycle + self.timing.tCL
            target_dq_end = target_dq_start + self.timing.tBL
            if target_dq_start < self.bus_busy_until:
                return False, "Vi pham Bus Collision: Bus DQs dang ban truyen burst du lieu truoc"

            return True, "READ OK"

        # 3. Kiem tra tinh hop le cua lenh WRITE
        elif cmd == DRAMCommandType.WRITE:
            if b.state not in (BankState.ACTIVE, BankState.READING, BankState.WRITING):
                return False, f"Bank {bank_id} khong o trang thai ACTIVE de WRITE (Hien tai: {b.state.value})"
            
            # Kiem tra tRCD: Tu ACTIVATE den WRITE
            if (self.current_cycle - b.last_act_cycle) < self.timing.tRCD:
                return False, f"Vi pham tRCD tren Bank {bank_id}: Cho {self.timing.tRCD} cycles, thuc te {self.current_cycle - b.last_act_cycle}"
            
            # Kiem tra tRTW: Read-to-Write turnaround tren bus
            if (self.current_cycle - self.bus_last_read_cycle) < (self.timing.tCL + self.timing.tBL + self.timing.tRTW):
                rem = (self.timing.tCL + self.timing.tBL + self.timing.tRTW) - (self.current_cycle - self.bus_last_read_cycle)
                return False, f"Vi pham tRTW tren Bus DQs: Con thieu {rem} cycles de doi chieu bus tu Read sang Write"
            
            target_dq_start = self.current_cycle + self.timing.tCWL
            if target_dq_start < self.bus_busy_until:
                return False, "Vi pham Bus Collision: Bus DQs dang ban truyen burst truoc"

            return True, "WRITE OK"

        # 4. Kiem tra tinh hop le cua lenh PRECHARGE
        elif cmd == DRAMCommandType.PRECHARGE:
            if b.state in (BankState.IDLE, BankState.PRECHARGING, BankState.REFRESHING):
                return False, f"Bank {bank_id} da o trang thai IDLE hoac PRECHARGING, khong can PRECHARGE"
            
            # Kiem tra tRAS: Hang phai mo toi thieu tRAS cycles truoc khi duoc dong
            if (self.current_cycle - b.last_act_cycle) < self.timing.tRAS:
                return False, f"Vi pham tRAS tren Bank {bank_id}: Phai mo du {self.timing.tRAS} cycles, moi mo duoc {self.current_cycle - b.last_act_cycle}"
            
            # Kiem tra tWR: Sau khi WRITE, phai doi tWR de dien tich nap day vao tu
            last_write_finish = b.last_write_cycle + self.timing.tCWL + self.timing.tBL
            if (self.current_cycle - last_write_finish) < self.timing.tWR:
                rem = self.timing.tWR - (self.current_cycle - last_write_finish)
                return False, f"Vi pham tWR tren Bank {bank_id}: Con thieu {rem} cycles sau Write de tu dien luu vao cell an toan"

            return True, "PRECHARGE OK"

        # 5. Kiem tra tinh hop le cua lenh REFRESH
        elif cmd == DRAMCommandType.REFRESH:
            # Tat ca cac Bank phai o trang thai IDLE de thuc hien Auto-Refresh
            for i, other_b in enumerate(self.banks):
                if other_b.state != BankState.IDLE:
                    return False, f"Vi pham All-Bank Idle: Bank {i} dang ban ({other_b.state.value}), khong the REFRESH"
            return True, "REFRESH OK"

        return False, "Lenh khong xac dinh"

    def issue_command(self, cmd: DRAMCommandType, bank_id: int, row_id: Optional[int] = None) -> bool:
        """Phat lenh cmd toi Bank. Tra ve True neu thanh cong, False neu vi pham timing."""
        valid, reason = self.can_issue_command(cmd, bank_id, row_id)
        if not valid:
            raise ValueError(f"[CYCLE {self.current_cycle}] LOI VI PHAM JEDEC: {reason}")

        b = self.banks[bank_id]

        if cmd == DRAMCommandType.ACTIVATE:
            b.state = BankState.ACTIVATING
            b.open_row = row_id
            b.last_act_cycle = self.current_cycle
            b.state_ready_cycle = self.current_cycle + self.timing.tRCD
            self.act_history.append(self.current_cycle)

        elif cmd == DRAMCommandType.READ:
            b.state = BankState.READING
            b.last_read_cycle = self.current_cycle
            b.state_ready_cycle = self.current_cycle + self.timing.tBL
            self.bus_last_read_cycle = self.current_cycle
            dq_start = self.current_cycle + self.timing.tCL
            self.bus_busy_until = max(self.bus_busy_until, dq_start + self.timing.tBL)

        elif cmd == DRAMCommandType.WRITE:
            b.state = BankState.WRITING
            b.last_write_cycle = self.current_cycle
            b.state_ready_cycle = self.current_cycle + self.timing.tBL
            self.bus_last_write_cycle = self.current_cycle
            dq_start = self.current_cycle + self.timing.tCWL
            self.bus_busy_until = max(self.bus_busy_until, dq_start + self.timing.tBL)

        elif cmd == DRAMCommandType.PRECHARGE:
            b.state = BankState.PRECHARGING
            b.last_pre_cycle = self.current_cycle
            b.state_ready_cycle = self.current_cycle + self.timing.tRP

        elif cmd == DRAMCommandType.REFRESH:
            for other_b in self.banks:
                other_b.state = BankState.REFRESHING
                other_b.last_ref_cycle = self.current_cycle
                other_b.state_ready_cycle = self.current_cycle + self.timing.tRFC

        return True


def test_lpddr5x_bank_timing_fsm():
    """Chuong trinh kiem thu toan dien may trang thai FSM va rang buoc JEDEC."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BG (NHOM 46) - BAI 180 (MILESTONE BG.1)")
    print("MAY TRANG THAI BANK FSM VA RANG BUOC THOI GIAN JEDEC LPDDR5X-8533")
    print("=" * 80)

    fsm = LPDDR5XMemoryControllerFSM()
    t = fsm.timing

    print(f"Thong so thoi gian LPDDR5X (tCK = {t.tCK_ns:.3f} ns tai 8533 MT/s):")
    print(f"  * tRCD = {t.tRCD} cycles ({t.tRCD * t.tCK_ns:.2f} ns)  | tRP  = {t.tRP} cycles ({t.tRP * t.tCK_ns:.2f} ns)")
    print(f"  * tRAS = {t.tRAS} cycles ({t.tRAS * t.tCK_ns:.2f} ns)  | tRC  = {t.tRC} cycles ({t.tRC * t.tCK_ns:.2f} ns)")
    print(f"  * tCL  = {t.tCL} cycles ({t.tCL * t.tCK_ns:.2f} ns)  | tCWL = {t.tCWL} cycles ({t.tCWL * t.tCK_ns:.2f} ns)")
    print(f"  * tWR  = {t.tWR} cycles ({t.tWR * t.tCK_ns:.2f} ns)  | tFAW = {t.tFAW} cycles ({t.tFAW * t.tCK_ns:.2f} ns)")
    print("-" * 80)

    # 1. Kiem thu chuoi lenh chuan: ACTIVATE -> READ -> PRECHARGE
    print("\n[1] Kiem thu trinh tu Row Miss chuan: ACTIVATE -> READ -> PRECHARGE:")
    fsm.issue_command(DRAMCommandType.ACTIVATE, bank_id=0, row_id=1024)
    print(f"  * [Cycle {fsm.current_cycle:4d}] Phat lenh ACTIVATE toi Bank 0, Row 1024 -> Trang thai: {fsm.banks[0].state.value}")

    # Thu READ ngay lap tuc tai cycle 1 (phai that bai do vi pham tRCD)
    fsm.step_cycle(1)
    can_read, reason = fsm.can_issue_command(DRAMCommandType.READ, bank_id=0)
    assert not can_read, "Loi: Khong phat hien vi pham tRCD!"
    print(f"  * [Cycle {fsm.current_cycle:4d}] Kiem tra READ som: BI CHAN CHINH XAC ({reason})")

    # Cho du tRCD = 28 chu ky
    fsm.step_cycle(t.tRCD - 1)
    assert fsm.banks[0].state == BankState.ACTIVE, "Loi: Bank chua ve trang thai ACTIVE sau tRCD!"
    fsm.issue_command(DRAMCommandType.READ, bank_id=0)
    print(f"  * [Cycle {fsm.current_cycle:4d}] Phat lenh READ thanh cong sau {t.tRCD} cycles tRCD")

    # Thu PRECHARGE ngay (phai that bai do vi pham tRAS)
    can_pre, reason = fsm.can_issue_command(DRAMCommandType.PRECHARGE, bank_id=0)
    assert not can_pre, "Loi: Khong phat hien vi pham tRAS!"
    print(f"  * [Cycle {fsm.current_cycle:4d}] Kiem tra PRECHARGE som: BI CHAN CHINH XAC ({reason})")

    # Cho du tRAS = 68 chu ky ke tu khi ACTIVATE
    elapsed_since_act = fsm.current_cycle - fsm.banks[0].last_act_cycle
    fsm.step_cycle(t.tRAS - elapsed_since_act)
    fsm.issue_command(DRAMCommandType.PRECHARGE, bank_id=0)
    print(f"  * [Cycle {fsm.current_cycle:4d}] Phat lenh PRECHARGE thanh cong sau {t.tRAS} cycles tRAS")

    # Cho du tRP = 28 chu ky de ve IDLE
    fsm.step_cycle(t.tRP)
    assert fsm.banks[0].state == BankState.IDLE, "Loi: Bank chua ve IDLE sau tRP!"
    print(f"  * [Cycle {fsm.current_cycle:4d}] Bank 0 da ve trang thai IDLE, hoan tat chu ky tRC = {t.tRC} cycles")

    # 2. Kiem thu gioi han Four-Activate Window (tFAW)
    print("\n[2] Kiem thu gioi han an toan Four-Activate Window (tFAW = 32 cycles):")
    # Kich hoat 4 bank khac nhau (Bank 1, 2, 3, 4) cach nhau tRRD = 8 cycles
    for b_idx in [1, 2, 3, 4]:
        fsm.issue_command(DRAMCommandType.ACTIVATE, bank_id=b_idx, row_id=500)
        print(f"  * [Cycle {fsm.current_cycle:4d}] ACTIVATE Bank {b_idx} thanh cong")
        fsm.step_cycle(t.tRRD)

    # Thu kich hoat Bank 5 (la lenh ACT thu 5 trong cua so tFAW)
    can_act_5, reason = fsm.can_issue_command(DRAMCommandType.ACTIVATE, bank_id=5, row_id=500)
    assert not can_act_5, "Loi: Khong phat hien vi pham tFAW!"
    print(f"  * [Cycle {fsm.current_cycle:4d}] Phat lenh ACTIVATE Bank 5: BI CHAN VI PHAM tFAW ({reason})")

    # Cho den khi lenh ACT dau tien vuot qua cua so tFAW
    oldest_act = fsm.act_history[-4]
    cycles_to_wait = t.tFAW - (fsm.current_cycle - oldest_act)
    fsm.step_cycle(cycles_to_wait)
    fsm.issue_command(DRAMCommandType.ACTIVATE, bank_id=5, row_id=500)
    print(f"  * [Cycle {fsm.current_cycle:4d}] ACTIVATE Bank 5 thanh cong sau khi cua so tFAW giai toa")

    # 3. Kiem thu do tre Turnaround: Write-to-Read (tWTR) tren Bus DQs
    print("\n[3] Kiem thu phong ve chuyen doi chieu Bus DQs: Write-to-Read Turnaround (tWTR):")
    # Phat lenh WRITE toi Bank 1
    fsm.step_cycle(t.tRCD)
    fsm.issue_command(DRAMCommandType.WRITE, bank_id=1)
    print(f"  * [Cycle {fsm.current_cycle:4d}] Phat lenh WRITE toi Bank 1")

    # Thu READ ngay tren Bank 2 (Bank 2 da ACTIVE)
    can_read_b2, reason = fsm.can_issue_command(DRAMCommandType.READ, bank_id=2)
    assert not can_read_b2, "Loi: Khong phat hien vi pham tWTR tren Bus!"
    print(f"  * [Cycle {fsm.current_cycle:4d}] Thu READ ngay tren Bank 2: BI CHAN CHINH XAC DO VI PHAM tWTR ({reason})")

    # Cho du tCWL + tBL + tWTR cycles
    wait_wtr = (t.tCWL + t.tBL + t.tWTR) - (fsm.current_cycle - fsm.bus_last_write_cycle)
    fsm.step_cycle(wait_wtr)
    fsm.issue_command(DRAMCommandType.READ, bank_id=2)
    print(f"  * [Cycle {fsm.current_cycle:4d}] READ Bank 2 chap nhan sau khi hoan tat tWTR ({wait_wtr} cycles)")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 180: TAT CA 3 KICH BAN JEDEC TIMING HOAN TOAN CHINH XAC (PASS)")
    print("=" * 80)


if __name__ == "__main__":
    test_lpddr5x_bank_timing_fsm()
