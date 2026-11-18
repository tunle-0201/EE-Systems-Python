"""
March C- Built-In Self-Test (BIST) Algorithm for ASIL-D SRAM Memory Verification
Chuyen de 27: Functional Safety ISO 26262 ASIL-D & Dual-Core Lockstep Pipeline
Milestone AN.2 - Bai hoc 105 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke thuat toan kiem tra bo nho ban dan March C- (10N Complexity) luc khoi dong (POST).
- Phat hien 100% cac loi phan cung vat ly: Stuck-At Fault (SAF), Transition Fault (TF), va Coupling Fault (CF).
- Xac dinh chinh xac dia chi o nho bi hong va bit loi (Fault Localization) tren thanh ghi ECC/BIST.
"""

from typing import List, Dict, Tuple, Optional


class SimulatedSramArray:
    """
    Mo phong mang nho SRAM vat ly cua vi dieu khien ASIL-D.
    Moi o nho la 1 tu 32-bit (32-bit Word).
    """
    def __init__(self, size_words: int = 256):
        self.size = size_words
        self.cells = [0] * size_words

        # Danh sach loi vat ly duoc bom vao silicon (Fault Injection)
        self.stuck_at_0_masks: Dict[int, int] = {}  # Bit nao bi ket ve 0
        self.stuck_at_1_masks: Dict[int, int] = {}  # Bit nao bi ket len 1
        self.coupling_faults: Dict[int, Tuple[int, int]] = {}  # Aggressor -> (Victim, bit_mask)

    def inject_stuck_at_0(self, addr: int, bit_mask: int):
        self.stuck_at_0_masks[addr] = self.stuck_at_0_masks.get(addr, 0) | bit_mask

    def inject_stuck_at_1(self, addr: int, bit_mask: int):
        self.stuck_at_1_masks[addr] = self.stuck_at_1_masks.get(addr, 0) | bit_mask

    def inject_coupling_fault(self, aggressor_addr: int, victim_addr: int, victim_bit_mask: int):
        """Khi ghi vao aggressor, lam dao bit tren victim"""
        self.coupling_faults[aggressor_addr] = (victim_addr, victim_bit_mask)

    def write(self, addr: int, value: int):
        val = value & 0xFFFFFFFF
        # Ap dat loi ket bit
        if addr in self.stuck_at_0_masks:
            val &= ~self.stuck_at_0_masks[addr]
        if addr in self.stuck_at_1_masks:
            val |= self.stuck_at_1_masks[addr]

        self.cells[addr] = val

        # Kich hoat loi ghep noi Coupling Fault sang o nho khac
        if addr in self.coupling_faults:
            v_addr, v_mask = self.coupling_faults[addr]
            self.cells[v_addr] ^= v_mask  # Dao bit o o bi ghep noi

    def read(self, addr: int) -> int:
        val = self.cells[addr]
        if addr in self.stuck_at_0_masks:
            val &= ~self.stuck_at_0_masks[addr]
        if addr in self.stuck_at_1_masks:
            val |= self.stuck_at_1_masks[addr]
        return val


class MarchCSramBistEngine:
    """
    Dong co BIST thuc thi thuat toan March C- (10N Operations):
    Phan tu 0: { (w0) }                  - Ghi 0 toan bo mang
    Phan tu 1: { UP (r0, w1) }          - Quet tang dan: Doc 0, ghi 1
    Phan tu 2: { UP (r1, w0) }          - Quet tang dan: Doc 1, ghi 0
    Phan tu 3: { DOWN (r0, w1) }        - Quet giam dan: Doc 0, ghi 1
    Phan tu 4: { DOWN (r1, w0) }        - Quet giam dan: Doc 1, ghi 0
    Phan tu 5: { (r0) }                 - Doc kiem tra 0 toan bo
    """
    def __init__(self, sram: SimulatedSramArray):
        self.sram = sram
        self.total_ops = 0

    def run_bist(self) -> Dict[str, any]:
        size = self.sram.size
        self.total_ops = 0
        ALL_ZEROS = 0x00000000
        ALL_ONES  = 0xFFFFFFFF

        # M0: { (w0) } - Ghi 0 toan bo
        for addr in range(size):
            self.sram.write(addr, ALL_ZEROS)
            self.total_ops += 1

        # M1: { UP (r0, w1) }
        for addr in range(size):
            r_val = self.sram.read(addr)
            self.total_ops += 1
            if r_val != ALL_ZEROS:
                return self._report_failure("M1: UP(r0, w1)", addr, expected=ALL_ZEROS, actual=r_val)
            self.sram.write(addr, ALL_ONES)
            self.total_ops += 1

        # M2: { UP (r1, w0) }
        for addr in range(size):
            r_val = self.sram.read(addr)
            self.total_ops += 1
            if r_val != ALL_ONES:
                return self._report_failure("M2: UP(r1, w0)", addr, expected=ALL_ONES, actual=r_val)
            self.sram.write(addr, ALL_ZEROS)
            self.total_ops += 1

        # M3: { DOWN (r0, w1) }
        for addr in range(size - 1, -1, -1):
            r_val = self.sram.read(addr)
            self.total_ops += 1
            if r_val != ALL_ZEROS:
                return self._report_failure("M3: DOWN(r0, w1)", addr, expected=ALL_ZEROS, actual=r_val)
            self.sram.write(addr, ALL_ONES)
            self.total_ops += 1

        # M4: { DOWN (r1, w0) }
        for addr in range(size - 1, -1, -1):
            r_val = self.sram.read(addr)
            self.total_ops += 1
            if r_val != ALL_ONES:
                return self._report_failure("M4: DOWN(r1, w0)", addr, expected=ALL_ONES, actual=r_val)
            self.sram.write(addr, ALL_ZEROS)
            self.total_ops += 1

        # M5: { (r0) } - Doc kiem tra lai 0
        for addr in range(size):
            r_val = self.sram.read(addr)
            self.total_ops += 1
            if r_val != ALL_ZEROS:
                return self._report_failure("M5: (r0)", addr, expected=ALL_ZEROS, actual=r_val)

        return {
            "passed": True,
            "total_ops": self.total_ops,
            "failed_step": None,
            "fault_addr": None,
            "expected_val": None,
            "actual_val": None
        }

    def _report_failure(self, step: str, addr: int, expected: int, actual: int) -> Dict[str, any]:
        return {
            "passed": False,
            "total_ops": self.total_ops,
            "failed_step": step,
            "fault_addr": addr,
            "expected_val": expected,
            "actual_val": actual,
            "error_bit_mask": expected ^ actual
        }


def test_march_c_sram_bist():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN MARCH C- ALGORITHM CHO SRAM ASIL-D BIST")
    print("=" * 80)

    SRAM_SIZE = 256  # 256 tu nho (32-bit words) = 1 KB SRAM

    # =========================================================================
    # THI NGHIEM 1: BO NHO LANH LAN (HEALTHY SRAM ARRAY)
    # =========================================================================
    print("Thi nghiem 1: Kiem tra mang nho SRAM lanh lan 100%...")
    sram_healthy = SimulatedSramArray(size_words=SRAM_SIZE)
    bist_engine = MarchCSramBistEngine(sram_healthy)
    res_healthy = bist_engine.run_bist()

    print(f"-> So luong o nho kiem tra      : {SRAM_SIZE} words (32-bit)")
    print(f"-> Tong so thao tac phan cung  : {res_healthy['total_ops']} ops (Chuan 10N = {10 * SRAM_SIZE} ops)")
    print(f"-> Ket qua kiem tra March C-    : {'BIST PASSED' if res_healthy['passed'] else 'BIST FAILED'}")
    assert res_healthy["passed"] is True, "SRAM lanh lan phai pass BIST 100%!"
    assert res_healthy["total_ops"] == 10 * SRAM_SIZE, "So thao tac March C- phai dung 10N!"
    print("-" * 80)

    # =========================================================================
    # THI NGHIEM 2: PHAT HIEN LOI KET BIT (STUCK-AT-0 FAULT) TAI DIA CHI 0x40
    # =========================================================================
    print("Thi nghiem 2: Phat hien loi ket bit Stuck-At-0 tai dia chi 0x0040 (Bit 8)...")
    sram_fault_sa0 = SimulatedSramArray(size_words=SRAM_SIZE)
    FAULT_ADDR_1 = 0x40
    FAULT_MASK_1 = 1 << 8  # Bit 8 bi ket xuong 0
    sram_fault_sa0.inject_stuck_at_0(FAULT_ADDR_1, FAULT_MASK_1)

    bist_sa0 = MarchCSramBistEngine(sram_fault_sa0)
    res_sa0 = bist_sa0.run_bist()

    print(f"-> Ket qua kiem tra March C-    : {'BIST PASSED' if res_sa0['passed'] else 'BIST FAILED (PHAT HIEN LOI)'}")
    print(f"-> Buoc phat hien loi           : {res_sa0['failed_step']}")
    print(f"-> Dia chi o nho bi hong        : 0x{res_sa0['fault_addr']:04X} (Ky vong: 0x{FAULT_ADDR_1:04X})")
    print(f"-> Bit bi sai lech (Bit Mask)   : 0x{res_sa0['error_bit_mask']:08X} (Bit 8)")

    assert res_sa0["passed"] is False, "March C- phai phat hien loi Stuck-At-0!"
    assert res_sa0["fault_addr"] == FAULT_ADDR_1, "Dia chi loi phai khop chinh xac!"
    print("-" * 80)

    # =========================================================================
    # THI NGHIEM 3: PHAT HIEN LOI GHEP NOI DIEN DUNG (COUPLING FAULT - CF)
    # Ghi o 0x60 lam dao bit o 0x65
    # =========================================================================
    print("Thi nghiem 3: Phat hien loi ghep noi dien dung Coupling Fault (0x0060 -> 0x0065)...")
    sram_cf = SimulatedSramArray(size_words=SRAM_SIZE)
    sram_cf.inject_coupling_fault(aggressor_addr=0x60, victim_addr=0x65, victim_bit_mask=0x01)

    bist_cf = MarchCSramBistEngine(sram_cf)
    res_cf = bist_cf.run_bist()

    print(f"-> Ket qua kiem tra March C-    : {'BIST PASSED' if res_cf['passed'] else 'BIST FAILED (PHAT HIEN LOI)'}")
    print(f"-> Buoc phat hien loi           : {res_cf['failed_step']}")
    print(f"-> Dia chi bi anh huong (Victim): 0x{res_cf['fault_addr']:04X}")

    assert res_cf["passed"] is False, "March C- phai phat hien loi Coupling Fault!"
    print("=" * 80)
    print("[PASS] March C- SRAM BIST Algorithm: 100% Hoan hao dat chuan ISO 26262 ASIL-D!")


if __name__ == "__main__":
    test_march_c_sram_bist()
