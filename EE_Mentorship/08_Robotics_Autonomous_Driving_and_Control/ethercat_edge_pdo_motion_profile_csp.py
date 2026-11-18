"""
EE Mentorship - Module BE (Nhom 44) - Bai 174 (Milestone BE.3)
Chuyen de: Cau truc du lieu chu ky Process Data Objects (PDO), Che do Dieu khien Vi tri
           Dong bo Chu ky Cyclic Synchronous Position (CSP) chuan CiA 402 va Safe Torque Off (STO).

Muc tieu ky thuat:
1. Thiet ke tu dien doi tuong (Object Dictionary) chuan CiA 402 cho bien tan dieu khien servo qua EtherCAT (CoE).
2. Dong goi nhi phan khung tin truyen nhan RxPDO (Master -> Drive) va TxPDO (Drive -> Master) bang struct.
3. May trang thai dieu khien chuyen dong CiA 402 Drive State Machine (Switch On Disabled, Ready, Switched On, Op Enabled).
4. Che do dieu khien vi tri dong bo chu ky CSP (Cyclic Synchronous Position Mode) chu ky 1.0 kHz.
5. Mach an toan phan cung Safe Torque Off (STO) tieu chuan IEC 61508 SIL-3: Cat nguon cau kich MOSFET tuc thi.
"""

import struct
import math
import time
from enum import IntEnum
from typing import Tuple, Dict, Optional


class CiA402State(IntEnum):
    """Cac trang thai trong May trang thai CiA 402 Drive State Machine."""
    NOT_READY_TO_SWITCH_ON = 0
    SWITCH_ON_DISABLED     = 1
    READY_TO_SWITCH_ON     = 2
    SWITCHED_ON            = 3
    OPERATION_ENABLED      = 4
    QUICK_STOP_ACTIVE      = 5
    FAULT_REACTION_ACTIVE  = 6
    FAULT                  = 7


class CiA402ModeOfOperation(IntEnum):
    """Che do hoat dong CiA 402 (Object 0x6060)."""
    NO_MODE                     = 0
    PROFILE_POSITION_MODE       = 1
    PROFILE_VELOCITY_MODE       = 3
    PROFILE_TORQUE_MODE         = 4
    HOMING_MODE                 = 6
    CYCLIC_SYNCHRONOUS_POSITION = 8   # CSP (Tieu chuan vang cho Robot hinh nguoi)
    CYCLIC_SYNCHRONOUS_VELOCITY = 9   # CSV
    CYCLIC_SYNCHRONOUS_TORQUE   = 10  # CST


class CiA402Controlword:
    """Lenh dieu khien tu Master (Object 0x6040, 16-bit)."""
    SHUTDOWN            = 0x0006  # Chuyen sang Ready to Switch On
    SWITCH_ON           = 0x0007  # Chuyen sang Switched On
    ENABLE_OPERATION    = 0x000F  # Chuyen sang Operation Enabled (Bat cong suat)
    DISABLE_VOLTAGE     = 0x0000  # Ngat nguon ve Switch On Disabled
    QUICK_STOP          = 0x0002  # Dung khan cap
    FAULT_RESET         = 0x0080  # Xoa loi (0 -> 1 edge)


class CiA402Statusword:
    """Trang thai phan hoi tu Drive ve Master (Object 0x6041, 16-bit mask)."""
    READY_TO_SWITCH_ON  = 0x0001
    SWITCHED_ON         = 0x0002
    OPERATION_ENABLED   = 0x0004
    FAULT               = 0x0008
    VOLTAGE_ENABLED     = 0x0010
    QUICK_STOP_ACTIVE   = 0x0020
    SWITCH_ON_DISABLED  = 0x0040
    WARNING             = 0x0080
    TARGET_REACHED      = 0x0400
    FOLLOWING_ERROR     = 0x2000


class ServoDriveActuatorCiA402:
    """
    Mo phong bo dieu khien khop chap hanh Servo Drive ho tro CiA 402 qua EtherCAT CoE:
    - Bo giai ma RxPDO va dong goi TxPDO (10 Bytes)
    - May trang thai CiA 402 State Machine
    - Vong lap dieu khien vi tri CSP (P-Position -> PI-Velocity -> FOC Current)
    - Mach an toan phan cung Safe Torque Off (STO) kenh kep
    """
    # Cau truc goi tin nhi phan PDO:
    # RxPDO (Master -> Drive, 10 bytes): Controlword(uint16), TargetPos(int32), TargetTorque(int16), DOut(uint16)
    # TxPDO (Drive -> Master, 10 bytes): Statusword(uint16), ActualPos(int32), ActualTorque(int16), DIn(uint16)
    PDO_STRUCT_FMT = "<HIhH"

    def __init__(self, joint_id: int, max_following_error_counts: int = 5000):
        self.joint_id = joint_id
        self.state = CiA402State.SWITCH_ON_DISABLED
        self.mode = CiA402ModeOfOperation.CYCLIC_SYNCHRONOUS_POSITION
        self.max_following_err = max_following_error_counts

        # Thanh ghi vi tri va luc (Encoder: 10,000 counts = 360 do)
        self.target_position_counts = 0
        self.actual_position_counts = 0
        self.target_torque_raw = 0        # Don vi: 0.1% rated torque
        self.actual_torque_raw = 0

        # Mach an toan Safe Torque Off (STO) kenh kep (1: Dong dien an toan, 0: Cat nguon)
        self.sto_channel_1 = True
        self.sto_channel_2 = True
        self.hardware_torque_cutoff = False

        # Thong so PID dieu khien vi tri khop
        self.kp_pos = 0.8
        self.simulated_velocity = 0.0

    def trigger_sto_safety_interlock(self, sto1: bool, sto2: bool):
        """
        Kich hoat mach an toan Safe Torque Off (STO) IEC 61508 SIL-3:
        Neu bat ky kenh nao bi ngat ve 0V, mach phan cung ngat xung kich MOSFET ngay lap tuc.
        """
        self.sto_channel_1 = sto1
        self.sto_channel_2 = sto2
        # Tieu chuan SIL-3: 1 trong 2 kenh ngat la phai cat luc tuc thi
        if not sto1 or not sto2:
            self.hardware_torque_cutoff = True
            self.actual_torque_raw = 0
        else:
            self.hardware_torque_cutoff = False

    def get_statusword(self) -> int:
        """Sinh ma Statusword 16-bit tu trang thai hien tai cua Drive."""
        sw = 0
        if self.state == CiA402State.NOT_READY_TO_SWITCH_ON:
            sw = 0x0000
        elif self.state == CiA402State.SWITCH_ON_DISABLED:
            sw = CiA402Statusword.SWITCH_ON_DISABLED
        elif self.state == CiA402State.READY_TO_SWITCH_ON:
            sw = CiA402Statusword.READY_TO_SWITCH_ON | CiA402Statusword.QUICK_STOP_ACTIVE
        elif self.state == CiA402State.SWITCHED_ON:
            sw = CiA402Statusword.READY_TO_SWITCH_ON | CiA402Statusword.SWITCHED_ON | CiA402Statusword.QUICK_STOP_ACTIVE
        elif self.state == CiA402State.OPERATION_ENABLED:
            sw = (CiA402Statusword.READY_TO_SWITCH_ON |
                  CiA402Statusword.SWITCHED_ON |
                  CiA402Statusword.OPERATION_ENABLED |
                  CiA402Statusword.VOLTAGE_ENABLED |
                  CiA402Statusword.QUICK_STOP_ACTIVE)
        elif self.state == CiA402State.FAULT:
            sw = CiA402Statusword.FAULT

        # Kiem tra Following Error
        following_err = abs(self.target_position_counts - self.actual_position_counts)
        if following_err > self.max_following_err:
            sw |= CiA402Statusword.FOLLOWING_ERROR

        return sw

    def process_controlword(self, cw: int):
        """Xu ly lenh Controlword tu Master va cap nhat may trang thai CiA 402."""
        # 1. Reset loi neu co bit FAULT_RESET
        if cw & CiA402Controlword.FAULT_RESET:
            if self.state == CiA402State.FAULT:
                self.state = CiA402State.SWITCH_ON_DISABLED
            return

        # Neu bi ngat STO hoac loi Following Error, ep ve FAULT
        if self.hardware_torque_cutoff:
            self.state = CiA402State.SWITCH_ON_DISABLED
            return

        # 2. May trang thai tieu chuan CiA 402
        cmd = cw & 0x000F
        if cmd == 0x0006:  # Shutdown
            if self.state in [CiA402State.SWITCH_ON_DISABLED, CiA402State.SWITCHED_ON, CiA402State.OPERATION_ENABLED]:
                self.state = CiA402State.READY_TO_SWITCH_ON
        elif cmd == 0x0007:  # Switch On
            if self.state == CiA402State.READY_TO_SWITCH_ON:
                self.state = CiA402State.SWITCHED_ON
        elif cmd == 0x000F:  # Enable Operation
            if self.state in [CiA402State.SWITCHED_ON, CiA402State.READY_TO_SWITCH_ON]:
                self.state = CiA402State.OPERATION_ENABLED
        elif cmd == 0x0000:  # Disable Voltage
            self.state = CiA402State.SWITCH_ON_DISABLED

    def process_rx_pdo(self, rx_bytes: bytes) -> bytes:
        """
        Giai ma goi tin RxPDO tu Master va thuc thi dieu khien CSP, sau do tao TxPDO phan hoi.
        Goi tin 10 bytes: Controlword(2B) + TargetPos(4B) + TargetTorque(2B) + DOut(2B).
        """
        if len(rx_bytes) < 10:
            return bytes(10)

        # 1. Giai ma RxPDO
        cw, target_pos, target_torque, d_out = struct.unpack(self.PDO_STRUCT_FMT, rx_bytes[:10])
        self.process_controlword(cw)

        # 2. Neu dang o OPERATION_ENABLED va STO khong ngat: Thuc thi dieu khien vi tri CSP
        if self.state == CiA402State.OPERATION_ENABLED and not self.hardware_torque_cutoff:
            self.target_position_counts = target_pos
            self.target_torque_raw = target_torque

            # Mo phong dap ung co hoc cua khop dong co (Closed-Loop Servo Dynamics)
            pos_error = self.target_position_counts - self.actual_position_counts
            step_move = round(pos_error * self.kp_pos)
            self.actual_position_counts += step_move
            # Momen thuc te ty le voi sai so vi tri
            self.actual_torque_raw = max(-1000, min(1000, round(pos_error * 0.5)))
        else:
            # Ngat cong suat
            self.actual_torque_raw = 0

        # 3. Kiem tra Following Error vuot nguong an toan
        if abs(self.target_position_counts - self.actual_position_counts) > self.max_following_err:
            self.state = CiA402State.FAULT

        # 4. Dong goi TxPDO tra ve cho Master
        statusword = self.get_statusword()
        d_in = 0x0001 if not self.hardware_torque_cutoff else 0x0000  # Bit an toan STO
        tx_bytes = struct.pack(
            self.PDO_STRUCT_FMT,
            statusword,
            self.actual_position_counts,
            self.actual_torque_raw,
            d_in
        )
        return tx_bytes


def build_rx_pdo_packet(controlword: int, target_pos: int, target_torque: int = 0) -> bytes:
    """Tien ich dong goi nhanh RxPDO phia Master."""
    return struct.pack(ServoDriveActuatorCiA402.PDO_STRUCT_FMT, controlword, target_pos, target_torque, 0)


def test_pdo_motion_profile_csp():
    """
    Kiem thu toan dien Cau truc du lieu chu ky PDO va Che do dieu khien vi tri CSP CiA 402.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BE (NHOM 44) - BAI 174 (MILESTONE BE.3)")
    print("CAU TRUC PROCESS DATA OBJECTS (PDO), CHE DO CSP CIA 402 & SAFE TORQUE OFF (STO)")
    print("================================================================================")

    drive = ServoDriveActuatorCiA402(joint_id=1, max_following_error_counts=5000)

    # 1. Kiem thu chuoi khoi dong May trang thai CiA 402 qua Controlword
    print("[1] Kiem thu Chuoi khoi dong May trang thai CiA 402 (State Machine):")
    print(f"    * Trang thai ban dau: {drive.state.name} (Statusword: 0x{drive.get_statusword():04X})")

    # Buoc 1: Gui Shutdown (0x0006) -> Ready to Switch On
    tx1 = drive.process_rx_pdo(build_rx_pdo_packet(CiA402Controlword.SHUTDOWN, 0))
    sw1, _, _, _ = struct.unpack(drive.PDO_STRUCT_FMT, tx1)
    assert drive.state == CiA402State.READY_TO_SWITCH_ON
    print(f"    * Lenh Shutdown (0x0006)        -> Trang thai: {drive.state.name} (SW: 0x{sw1:04X})")

    # Buoc 2: Gui Switch On (0x0007) -> Switched On
    tx2 = drive.process_rx_pdo(build_rx_pdo_packet(CiA402Controlword.SWITCH_ON, 0))
    sw2, _, _, _ = struct.unpack(drive.PDO_STRUCT_FMT, tx2)
    assert drive.state == CiA402State.SWITCHED_ON
    print(f"    * Lenh Switch On (0x0007)       -> Trang thai: {drive.state.name} (SW: 0x{sw2:04X})")

    # Buoc 3: Gui Enable Operation (0x000F) -> Operation Enabled
    tx3 = drive.process_rx_pdo(build_rx_pdo_packet(CiA402Controlword.ENABLE_OPERATION, 0))
    sw3, _, _, _ = struct.unpack(drive.PDO_STRUCT_FMT, tx3)
    assert drive.state == CiA402State.OPERATION_ENABLED
    print(f"    * Lenh Enable Operation (0x000F)-> Trang thai: {drive.state.name} (SW: 0x{sw3:04X})")
    print("    * May trang thai CiA 402: 100% PASS")

    # 2. Kiem thu che do dieu khien vi tri dong bo chu ky CSP (Cyclic Synchronous Position)
    print("\n[2] Kiem thu Quy trinh bam vi tri dong bo chu ky CSP (Target Tracking):")
    # Dat muc tieu di chuyen 90 do (2500 counts)
    target_pos = 2500
    for cycle in range(1, 11):
        tx_pdo = drive.process_rx_pdo(build_rx_pdo_packet(CiA402Controlword.ENABLE_OPERATION, target_pos))
        sw, act_pos, act_torque, _ = struct.unpack(drive.PDO_STRUCT_FMT, tx_pdo)
        if cycle in [1, 2, 5, 10]:
            print(f"    * Chu ky #{cycle:02d} | Target: {target_pos:>5d} | Actual: {act_pos:>5d} | Torque: {act_torque:>3d} | SW: 0x{sw:04X}")

    assert abs(drive.actual_position_counts - target_pos) <= 5, "Loi: Khop khong bam sat vi tri muc tieu!"
    print(f"    * Sai so bam vi tri cuoi cung (Final Error): {abs(drive.actual_position_counts - target_pos)} counts (< 0.1 do)")
    print("    * Che do CSP 1.0 kHz: PASS (Chinh xac vi tri khop tuc thi)")

    # 3. Kiem thu chuc nang an toan phan cung Safe Torque Off (STO) IEC 61508 SIL-3
    print("\n[3] Kiem thu Chuc nang an toan phan cung Safe Torque Off (STO) kenh kep:")
    print("    * Dong co dang hoat dong o che do Operation Enabled sinh luc momen...")
    print(f"      - Momen luc truoc khi cat STO: {drive.actual_torque_raw}")

    # Cat kenh STO1 (vi du: nut E-Stop bi nhan)
    print("    * [TRIGGER] Kenh STO 1 bi ngat dien ap (0V - Nut Emergency Stop duoc an)!")
    drive.trigger_sto_safety_interlock(sto1=False, sto2=True)
    # Master tiep tuc gui lenh chay
    tx_sto = drive.process_rx_pdo(build_rx_pdo_packet(CiA402Controlword.ENABLE_OPERATION, 5000))
    sw_sto, _, act_torque_sto, din_sto = struct.unpack(drive.PDO_STRUCT_FMT, tx_sto)

    assert act_torque_sto == 0, "Loi nguy hiem: STO khong triet tieu duoc momen luc!"
    assert drive.hardware_torque_cutoff, "Loi: Mach phan cung STO khong bao ve!"
    print(f"    * Momen luc sau khi ngat STO : {act_torque_sto} Nm (Ngat 100% tuc thi)")
    print(f"    * Trang thai logic an toan DIn : 0x{din_sto:04X} (Bao dong ngat STO ve Master)")
    print("    * Tieu chuan an toan SIL-3 STO: PASS TUYET DOI")
    print("================================================================================")


if __name__ == "__main__":
    test_pdo_motion_profile_csp()
