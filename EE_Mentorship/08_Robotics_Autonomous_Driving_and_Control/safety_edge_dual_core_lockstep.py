"""
Dual-Core Lockstep (DCLS) Architecture with 2-Cycle Delay Core Comparison Unit (CCU)
Chuyen de 27: Functional Safety ISO 26262 ASIL-D & Dual-Core Lockstep Pipeline
Milestone AN.1 - Bai hoc 104 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke kien truc vi xu ly du phong doi xung kep Dual-Core Lockstep (DCLS) chuan ISO 26262 ASIL-D.
- Triet tieu loi nguyen nhan chung (Common-Cause Failure) bang co che tre 2 chu ky (2-Cycle Delay).
- Xay dung Bo so sanh phan cung Core Comparison Unit (CCU) phat hien bat dong trong 1 chu ky clock.
- Kich hoat ngat khan cap Non-Maskable Interrupt (NMI) dua he thong vao trang thai Fail-Safe.
"""

from typing import List, Dict, Tuple, Optional
from collections import deque


class CoreExecutionCycle:
    """Dai dien cho mot chu ky thuc thi lenh tren bus cua loi CPU"""
    def __init__(self, cycle_id: int, pc: int, address_bus: int, data_bus: int, control_bus: int):
        self.cycle_id = cycle_id
        self.pc = pc
        self.address_bus = address_bus
        self.data_bus = data_bus
        self.control_bus = control_bus

    def matches(self, other: 'CoreExecutionCycle') -> bool:
        return (self.pc == other.pc and
                self.address_bus == other.address_bus and
                self.data_bus == other.data_bus and
                self.control_bus == other.control_bus)


class SimulatedCpuCore:
    """
    Mo phong mot loi CPU (vi du ARM Cortex-R52 / Infineon TriCore).
    Co the la Primary Core (Loi chinh) hoac Checker Core (Loi kiem tra).
    """
    def __init__(self, core_id: str):
        self.core_id = core_id
        self.pc = 0x08000000
        self.registers = [0] * 16  # R0 den R15
        self.fault_injected = False

    def execute_instruction(self, cycle_id: int, instruction_op: str, operand1: int, operand2: int) -> CoreExecutionCycle:
        """Thuc thi mot lenh so hoc hoac nap/ghi bo nho"""
        ctrl_bus = 0x01  # Read/Write control
        addr_bus = 0x20000000 + (self.pc & 0xFFF)

        if instruction_op == "ADD":
            res = (operand1 + operand2) & 0xFFFFFFFF
            self.registers[0] = res
            data_bus = res
        elif instruction_op == "MUL":
            res = (operand1 * operand2) & 0xFFFFFFFF
            self.registers[0] = res
            data_bus = res
        elif instruction_op == "STEER_CALC":
            # Tinh toan goc lai phuc tap: Goc = Kp * Err_Goc + Kd * VanToc_Goc
            kp = 120
            kd = 15
            res = (operand1 * kp + operand2 * kd) & 0xFFFFFFFF
            self.registers[0] = res
            data_bus = res
        else:
            data_bus = 0

        # Neu bi ban tia buc xa (Bit-flip Fault Injection)
        if self.fault_injected:
            data_bus ^= 0x00000004  # Lat bit 2
            self.fault_injected = False  # Transient fault

        bus_cycle = CoreExecutionCycle(cycle_id, self.pc, addr_bus, data_bus, ctrl_bus)
        self.pc += 4
        return bus_cycle


class CoreComparisonUnit:
    """
    Bo so sanh phan cung Hardware Core Comparison Unit (CCU).
    Ket noi giua Primary Core va Checker Core.
    Su dung hang doi tri hoan 2 chu ky (2-Cycle Staggered Delay Pipeline).
    """
    def __init__(self, delay_cycles: int = 2):
        self.delay_cycles = delay_cycles
        # Bo dem tri hoan cho Primary Core de cho Checker Core chay toi
        self.primary_pipeline: deque = deque(maxlen=delay_cycles + 1)
        self.mismatch_detected = False
        self.error_cycle = None
        self.fail_safe_active = False

    def compare_cycle(self, primary_out: CoreExecutionCycle, checker_out: Optional[CoreExecutionCycle], cycle: int) -> bool:
        """
        Tai moi chu ky clock:
        1. Primary Core dua ket qua vao dau vao hang doi tri hoan.
        2. Sau 2 chu ky, ket qua Primary xuat hien o dau ra hang doi.
        3. So sanh truc tiep voi ket qua hien tai cua Checker Core (von dang chay tre 2 chu ky).
        """
        self.primary_pipeline.append(primary_out)

        # Neu chua du 2 chu ky tri hoan ban dau, Checker core chua co output tuong ung
        if len(self.primary_pipeline) <= self.delay_cycles or checker_out is None:
            return True  # Pipeline dang khoi dong

        # Lay ket qua cua Primary cach day 2 chu ky
        delayed_primary = self.primary_pipeline[0]

        # So sanh phan cung tung bit tren tat ca cac bus
        if not delayed_primary.matches(checker_out):
            self.mismatch_detected = True
            self.error_cycle = cycle
            self.fail_safe_active = True
            return False  # Bat dong phan cung!

        return True


class DualCoreLockstepSystem:
    """
    He thong vi xu ly DCLS hoan chinh dat chuan ISO 26262 ASIL-D.
    """
    def __init__(self):
        self.primary_core = SimulatedCpuCore("PRIMARY_CORE")
        self.checker_core = SimulatedCpuCore("CHECKER_CORE")
        self.ccu = CoreComparisonUnit(delay_cycles=2)
        self.instruction_queue = deque()  # Hang doi tri hoan lenh cho Checker Core
        self.current_cycle = 0

    def step(self, instruction_op: str, op1: int, op2: int) -> Dict[str, any]:
        self.current_cycle += 1

        # 1. Primary Core thuc thi ngay lap tuc tai chu ky hien tai
        prim_cycle = self.primary_core.execute_instruction(self.current_cycle, instruction_op, op1, op2)

        # Day lenh vao hang doi tri hoan 2 chu ky cho Checker Core
        self.instruction_queue.append((instruction_op, op1, op2))

        # 2. Checker Core chay tre 2 chu ky: Lay lenh cach day 2 chu ky ra thuc thi
        check_cycle = None
        if len(self.instruction_queue) > 2:
            delayed_op, delayed_op1, delayed_op2 = self.instruction_queue.popleft()
            check_cycle = self.checker_core.execute_instruction(self.current_cycle - 2, delayed_op, delayed_op1, delayed_op2)

        # 3. Bo so sanh CCU kiem tra tinh nhat quan
        is_ok = self.ccu.compare_cycle(prim_cycle, check_cycle, self.current_cycle)

        return {
            "cycle": self.current_cycle,
            "primary_bus": prim_cycle.data_bus,
            "checker_bus": check_cycle.data_bus if check_cycle else None,
            "is_matched": is_ok,
            "fail_safe": self.ccu.fail_safe_active
        }


def test_dual_core_lockstep():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN DUAL-CORE LOCKSTEP (DCLS) ASIL-D ARCHITECTURE")
    print("=" * 80)
    print("Kien truc vi xu ly: Dual-Core Lockstep voi 2-Cycle Staggered Delay")
    print("Muc tieu an toan  : ISO 26262 ASIL-D / Phat hien sai lech trong 1 chu ky clock")
    print("-" * 80)

    system = DualCoreLockstepSystem()

    # =========================================================================
    # GIAI DOAN 1: THUC THI BINH THUONG (NORMAL LOCKSTEP OPERATION)
    # =========================================================================
    print("Giai doan 1: Thuc thi 10 chu ky tinh toan goc lai Steer-by-Wire khong co loi...")
    for i in range(1, 11):
        err_angle = i * 2
        rate_angle = 5
        res = system.step("STEER_CALC", err_angle, rate_angle)
        print(f"Chu ky {res['cycle']:2d} | Primary Data: 0x{res['primary_bus']:08X} | Checker Data: {'0x{:08X}'.format(res['checker_bus']) if res['checker_bus'] else 'STAGGER_DELAY'} | Match: {res['is_matched']}")

    print("-> Ket qua Giai doan 1: Hai loi hoat dong dong bo hoan hao, khong co canh bao.")
    assert system.ccu.fail_safe_active is False, "Khong duoc co canh bao khi he thong hoat dong binh thuong!"
    print("-" * 80)

    # =========================================================================
    # GIAI DOAN 2: BAN TIA BUC XA LAT BIT TRAP AM (SINGLE-EVENT UPSET INJECTION)
    # =========================================================================
    print("Giai doan 2: Bom nhieu buc xa gay lat bit (SEU) tren Primary Core tai chu ky 12...")
    # Thuc thi chu ky 11
    system.step("ADD", 100, 200)

    # Bom loi lat bit tren Primary Core tai chu ky 12
    system.primary_core.fault_injected = True
    res_fault = system.step("ADD", 500, 300)
    print(f"-> Chu ky 12: Primary bi lat bit (Data Bus = 0x{res_fault['primary_bus']:08X})")

    # Do Checker Core chay tre 2 chu ky, tai chu ky 14 (12 + 2), CCU se so sanh ket qua cua chu ky 12!
    res_13 = system.step("ADD", 10, 20)
    res_14 = system.step("ADD", 10, 20)

    print(f"-> Chu ky 14: CCU so sanh Primary chu ky 12 va Checker chu ky 12...")
    print(f"   + Primary (chu ky 12 tre 2 nhip) : 0x{system.ccu.primary_pipeline[0].data_bus:08X}")
    print(f"   + Checker (thuc thi chu ky 12)   : 0x{res_14['checker_bus']:08X}")
    print(f"   + Phat hien bat dong (Mismatch)  : {'BAT DONG (MISMATCH DETECTED!)' if not res_14['is_matched'] else 'Dong nhat'}")
    print(f"   + Kich hoat ngat Fail-Safe NMI   : {'KICH HOAT FAIL-SAFE' if res_14['fail_safe'] else 'Chua kich hoat'}")

    assert res_14['is_matched'] is False, "CCU phai phat hien bat dong giua 2 loi!"
    assert res_14['fail_safe'] is True, "He thong phai lap tuc chuyen sang Fail-Safe State!"
    print("=" * 80)
    print("[PASS] Dual-Core Lockstep (DCLS) ASIL-D Architecture: 100% Hoan hao!")


if __name__ == "__main__":
    test_dual_core_lockstep()
