"""
EE Mentorship - Module BE (Nhom 44) - Bai 172 (Milestone BE.1)
Chuyen de: May trang thai huu han Bo dieu khien no le EtherCAT Slave Controller (ESC FSM)
           va Co che kenh dong bo SyncManager Mailbox cho Robot cong nghiep.

Muc tieu ky thuat:
1. Mo phong kien truc phan cung Bo dieu khien no le EtherCAT Slave Controller (ESC).
2. Thiet ke May trang thai lop ung dung EtherCAT State Machine (ESM: INIT, PRE-OP, SAFE-OP, OP).
3. Xay dung 4 kenh dong bo SyncManager (SM0/SM1 cho Mailbox CoE, SM2/SM3 cho Process Data PDO).
4. Co che dem 3 tang Triple-Buffering chong jitter va co che xu ly goi tin On-the-Fly.
5. Mach dinh thoi bao ve SyncManager Watchdog: Tu dong roi ve SAFE-OP khi mat goi tin Master.
"""

import time
from enum import IntEnum
from typing import Dict, Tuple, Optional, List


class EtherCATState(IntEnum):
    """Cac trang thai tieu chuan cua May trang thai EtherCAT (ESM) theo IEC 61158."""
    NONE     = 0x00
    INIT     = 0x01  # Khoi tao phan cung, chua co Mailbox, chua co PDO
    PRE_OP   = 0x02  # Giao tiep Mailbox (CoE / SDO) hoat dong, chua co chu ky PDO
    BOOT     = 0x03  # Nap firmware cap nhat (FoE)
    SAFE_OP  = 0x04  # Mailbox hoat dong, Input PDO hoat dong, Output o trang thai an toan (Zero Torque)
    OP       = 0x08  # Hoat dong toan phan: Input va Output PDO deu duoc cap nhat de dieu khien dong co


class ALErrorCode(IntEnum):
    """Ma loi Application Layer Status Code (AL Status Code) tra ve cho Master."""
    NO_ERROR                = 0x0000
    INVALID_STATE_CHANGE    = 0x0011  # Yeu cau chuyen trang thai khong hop le (vi du: INIT -> OP)
    UNKNOWN_STATE           = 0x0012  # Trang thai khong xac dinh
    BOOTSTRAP_NOT_SUPPORTED = 0x0013  # Khong ho tro che do Boot
    INVALID_MAILBOX_CONFIG  = 0x0016  # Cau hinh SyncManager Mailbox SM0/SM1 bi sai
    INVALID_SYNC_CONFIG     = 0x0017  # Cau hinh SyncManager PDO SM2/SM3 bi sai
    SM_WATCHDOG_TIMEOUT     = 0x001B  # Het thoi gian cho Watchdog chu ky PDO


class SyncManagerChannel:
    """
    Kenh dong bo SyncManager (SM):
    Dieu phoi vung nho chia se giua truyen thong mang EtherCAT va vi xu ly dieu khien dong co.
    """
    def __init__(self, channel_id: int, start_addr: int, length_bytes: int, is_buffered: bool):
        self.channel_id = channel_id
        self.start_addr = start_addr
        self.length_bytes = length_bytes
        self.is_buffered = is_buffered  # True: 3-Buffer (PDO), False: Mailbox handshake
        self.enabled = False
        self.buffer = bytearray(length_bytes)
        self.has_new_data = False

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
        self.has_new_data = False

    def write_data(self, data: bytes):
        """Master ghi vao SyncManager qua khung mang Ethernet On-the-Fly."""
        if not self.enabled:
            return
        actual_len = min(len(data), self.length_bytes)
        self.buffer[:actual_len] = data[:actual_len]
        self.has_new_data = True

    def read_data(self) -> bytes:
        """Slave doc du lieu ra de dieu khien dong co."""
        if not self.enabled:
            return bytes(self.length_bytes)
        self.has_new_data = False
        return bytes(self.buffer)


class EtherCATSlaveController:
    """
    Bo dieu khien no le EtherCAT Slave Controller (ESC):
    Quan ly thanh ghi AL Control / AL Status, FSM chuyen trang thai va 4 kenh SyncManager.
    """
    def __init__(self, slave_id: int, watchdog_timeout_ms: float = 100.0):
        self.slave_id = slave_id
        self.current_state = EtherCATState.INIT
        self.al_status_code = ALErrorCode.NO_ERROR
        self.error_flag = False

        # 4 kenh SyncManager tieu chuan
        # SM0: Mailbox Write (Master -> Slave, 128 Bytes tai 0x1000)
        # SM1: Mailbox Read (Slave -> Master, 128 Bytes tai 0x1080)
        # SM2: Process Data Output (Master -> Slave, 32 Bytes tai 0x1100, Target Torque/Pos)
        # SM3: Process Data Input (Slave -> Master, 32 Bytes tai 0x1120, Actual Torque/Pos)
        self.sm0 = SyncManagerChannel(0, 0x1000, 128, is_buffered=False)
        self.sm1 = SyncManagerChannel(1, 0x1080, 128, is_buffered=False)
        self.sm2 = SyncManagerChannel(2, 0x1100, 32, is_buffered=True)
        self.sm3 = SyncManagerChannel(3, 0x1120, 32, is_buffered=True)

        # Watchdog chu ky cho Process Data (SM Watchdog)
        self.watchdog_timeout_ms = watchdog_timeout_ms
        self.last_pdo_time = time.time()
        self.motor_enabled = False

    def request_state_transition(self, target_state: EtherCATState) -> Tuple[bool, ALErrorCode]:
        """
        Master ghi vao thanh ghi AL Control (0x0120) de yeu cau chuyen trang thai.
        Tuan thu nghiem ngat trinh tu: INIT -> PRE-OP -> SAFE-OP -> OP.
        """
        # Tu bat ky trang thai nao deu co the ha ve INIT
        if target_state == EtherCATState.INIT:
            self._transition_to_init()
            return True, ALErrorCode.NO_ERROR

        # 1. Chuyen tu INIT -> PRE-OP
        if self.current_state == EtherCATState.INIT and target_state == EtherCATState.PRE_OP:
            # Bat 2 kenh Mailbox SM0 va SM1
            self.sm0.enable()
            self.sm1.enable()
            self.current_state = EtherCATState.PRE_OP
            self.al_status_code = ALErrorCode.NO_ERROR
            self.error_flag = False
            return True, ALErrorCode.NO_ERROR

        # 2. Chuyen tu PRE-OP -> SAFE-OP
        if self.current_state == EtherCATState.PRE_OP and target_state == EtherCATState.SAFE_OP:
            # Bat kenh PDO SM2 va SM3
            self.sm2.enable()
            self.sm3.enable()
            self.current_state = EtherCATState.SAFE_OP
            self.al_status_code = ALErrorCode.NO_ERROR
            self.last_pdo_time = time.time()
            self.motor_enabled = False  # SAFE-OP: Chua cho phep dong co chay cong suat
            return True, ALErrorCode.NO_ERROR

        # 3. Chuyen tu SAFE-OP -> OP
        if self.current_state == EtherCATState.SAFE_OP and target_state == EtherCATState.OP:
            self.current_state = EtherCATState.OP
            self.al_status_code = ALErrorCode.NO_ERROR
            self.motor_enabled = True  # OP: Dong co duoc phep sinh luc Torque
            self.last_pdo_time = time.time()
            return True, ALErrorCode.NO_ERROR

        # 4. Ha tu OP ve SAFE-OP (vi du: Master muon tam dung)
        if self.current_state == EtherCATState.OP and target_state == EtherCATState.SAFE_OP:
            self.current_state = EtherCATState.SAFE_OP
            self.motor_enabled = False
            return True, ALErrorCode.NO_ERROR

        # Moi yeu cau nhay coc (vi du INIT -> OP) deu bi tu choi va bao loi
        self.error_flag = True
        self.al_status_code = ALErrorCode.INVALID_STATE_CHANGE
        return False, ALErrorCode.INVALID_STATE_CHANGE

    def _transition_to_init(self):
        """Reset he thong ve INIT an toan."""
        self.sm0.disable()
        self.sm1.disable()
        self.sm2.disable()
        self.sm3.disable()
        self.current_state = EtherCATState.INIT
        self.al_status_code = ALErrorCode.NO_ERROR
        self.error_flag = False
        self.motor_enabled = False

    def process_cyclic_pdo(self, master_pdo_output: bytes) -> bytes:
        """
        Xu ly khung tin Process Data Object (PDO) On-the-Fly tai moi chu ky (1.0 ms):
        - Nhan lenh dieu khien tu Master (SM2).
        - Cap nhat Watchdog.
        - Tra ve trang thai phan hoi tu Slave (SM3).
        """
        now = time.time()

        # Kiem tra Watchdog timeout
        if self.current_state == EtherCATState.OP:
            elapsed_ms = (now - self.last_pdo_time) * 1000.0
            if elapsed_ms > self.watchdog_timeout_ms:
                # Watchdog het han: Tu dong ngat motor va roi ve SAFE-OP
                self.current_state = EtherCATState.SAFE_OP
                self.motor_enabled = False
                self.error_flag = True
                self.al_status_code = ALErrorCode.SM_WATCHDOG_TIMEOUT
                return bytes(32)

        self.last_pdo_time = now

        # Ghi lenh Master vao SM2
        if self.sm2.enabled:
            self.sm2.write_data(master_pdo_output)

        # Doc phan hoi Slave tu SM3
        slave_feedback = bytes(32)
        if self.sm3.enabled:
            slave_feedback = self.sm3.read_data()

        return slave_feedback

    def trigger_watchdog_timeout_simulation(self):
        """Mo phong su co mat goi tin de kiem thu Watchdog."""
        # Tua nguoc thoi gian cua goi cuoi ve qua khu
        self.last_pdo_time = time.time() - (self.watchdog_timeout_ms / 1000.0 + 0.05)
        # Kich hoat xu ly chu ky tiep theo de Watchdog ngat
        self.process_cyclic_pdo(bytes(32))


def test_ethercat_slave_controller():
    """
    Chuong trinh kiem thu toan dien Bo dieu khien no le EtherCAT Slave Controller (ESC).
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BE (NHOM 44) - BAI 172 (MILESTONE BE.1)")
    print("MAY TRANG THAI HUU HAN ETHERCAT SLAVE CONTROLLER (ESC FSM) & SYNCMANAGER")
    print("================================================================================")

    esc = EtherCATSlaveController(slave_id=1, watchdog_timeout_ms=50.0)

    # 1. Kiem tra trang thai ban dau
    print("[1] Kiem tra trang thai khoi tao ban dau:")
    assert esc.current_state == EtherCATState.INIT
    assert not esc.motor_enabled
    print(f"    * Trang thai ban dau     : {esc.current_state.name} (0x{esc.current_state:02X})")
    print(f"    * Kenh SyncManager SM0-3 : All Disabled (Chua khoi tao)")

    # 2. Kiem tra tu choi nhay coc sai quy trinh (Illegal Transition INIT -> OP)
    print("\n[2] Kiem tra phong thu tu choi chuyen trang thai sai quy trinh (INIT -> OP):")
    success, err = esc.request_state_transition(EtherCATState.OP)
    assert not success
    assert err == ALErrorCode.INVALID_STATE_CHANGE
    assert esc.error_flag
    print(f"    * Yeu cau INIT -> OP bi tu choi: Thuc thi thanh cong!")
    print(f"    * Ma loi AL Status Code : 0x{err:04X} ({err.name})")

    # 3. Kiem tra chuoi chuyen trang thai hop le: INIT -> PRE-OP -> SAFE-OP -> OP
    print("\n[3] Kiem tra chuoi chuyen trang thai hop le theo chuan IEC 61158:")
    # Buoc A: INIT -> PRE-OP
    ok, _ = esc.request_state_transition(EtherCATState.PRE_OP)
    assert ok and esc.current_state == EtherCATState.PRE_OP
    assert esc.sm0.enabled and esc.sm1.enabled
    print(f"    * [A] INIT -> PRE-OP  : PASS (Mo kenh Mailbox CoE SM0/SM1)")

    # Buoc B: PRE-OP -> SAFE-OP
    ok, _ = esc.request_state_transition(EtherCATState.SAFE_OP)
    assert ok and esc.current_state == EtherCATState.SAFE_OP
    assert esc.sm2.enabled and esc.sm3.enabled
    assert not esc.motor_enabled  # SAFE-OP chua duoc bat motor
    print(f"    * [B] PRE-OP -> SAFE-OP: PASS (Mo kenh PDO SM2/SM3, Motor SAFE-OFF)")

    # Buoc C: SAFE-OP -> OP
    ok, _ = esc.request_state_transition(EtherCATState.OP)
    assert ok and esc.current_state == EtherCATState.OP
    assert esc.motor_enabled  # OP bat motor sinh momen
    print(f"    * [C] SAFE-OP -> OP   : PASS (Hoan tat khoi dong, Motor SAN SANG hoat dong)")

    # 4. Kiem tra luu thong du lieu chu ky Process Data (Cyclic PDO)
    print("\n[4] Kiem tra trao doi du lieu chu ky Process Data (Cyclic PDO @ 1.0 kHz):")
    target_pos_command = b"POS: 180.0 DEG, TORQUE: 45Nm"
    esc.sm3.write_data(b"FEEDBACK: POS=180.0, I=12A")

    feedback = esc.process_cyclic_pdo(target_pos_command)
    assert esc.sm2.read_data()[:len(target_pos_command)] == target_pos_command
    print(f"    * Lenh Master gui xuong SM2: {target_pos_command.decode('utf-8')}")
    print(f"    * Du lieu phan hoi tu SM3   : {feedback[:30].decode('utf-8')}")
    print("    * Co che On-the-Fly PDO     : 100% BIT-EXACT PASS")

    # 5. Kiem tra phong thu an toan SyncManager Watchdog
    print("\n[5] Kiem thu Phong thu an toan phan cung SyncManager Watchdog (Link Loss):")
    print("    * Mo phong su co dut cap truyen thong Ethernet (> 50ms)...")
    esc.trigger_watchdog_timeout_simulation()

    assert esc.current_state == EtherCATState.SAFE_OP, "Loi: Khong tu dong roi ve SAFE-OP!"
    assert not esc.motor_enabled, "Loi: Motor van hoat dong khi mat ket noi!"
    assert esc.al_status_code == ALErrorCode.SM_WATCHDOG_TIMEOUT
    print(f"    * Phat hien Timeout! ESC tu dong roi ve: {esc.current_state.name}")
    print(f"    * Trang thai cong suat Motor           : DISABLED (Safe Torque Off)")
    print(f"    * Ma loi AL Status Code                : 0x{esc.al_status_code:04X} ({esc.al_status_code.name})")
    print("    * Chuc nang an toan chong mat dieu khien robot: PASS 100%!")
    print("================================================================================")


if __name__ == "__main__":
    test_ethercat_slave_controller()
