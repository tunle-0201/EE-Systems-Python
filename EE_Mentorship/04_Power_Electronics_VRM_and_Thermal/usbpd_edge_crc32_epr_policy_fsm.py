"""
EE MENTORSHIP PROGRAM - MODULE BO (NHOM 54) - BAI 213 (MILESTONE BO.2)
================================================================================
KIEM TOAN VEN KHUNG TRUYEN USB-PD 3.1 BANG PHAN CUNG CRC-32, XAC THUC CAP
E-MARKER (60W / 100W / 240W EPR) VA MAY TRANG THAI POLICY ENGINE FSM
================================================================================

Nguyen ly Giao thuc USB Power Delivery 3.1 Extended Power Range (EPR 240W):
1. Cau truc Khung du lieu USB-PD (Little-Endian):
   [Header 16-bit] + [Data Objects: 0..7 x 32-bit PDO/RDO] + [CRC-32 32-bit]
   - Bit trong Header: [14..12] NumDataObjects | [11..9] MessageID | [7..6] SpecRev=3.1 | [4..0] MsgType.
   - Hardware CRC-32 (IEEE 802.3 Da thuc 0x04C11DB7, phan chieu 0xEDB88320):
     Phat hien 100% loi don bit, loi doi bit va cum loi burst <= 32 bit tren day CC!

2. Khoa An toan Cap E-Marker (Bat buoc truoc khi nang ap > 20V hoac dong > 3A):
   - Truoc khi Nguon (MacBook/Charger) duoc phep day len 5A hay EPR 48V, phai gui
     goi tin SOP' (Discover Identity) hoi chip E-Marker nam trong dau cap:
     + Cap thuong (Khong E-Marker)      : Gioi han toi da 20V x 3A = 60 W.
     + Cap E-Marker cu (5A / 20V Max)   : Gioi han 20V x 5A = 100 W (CAM EPR 48V!).
     + Cap E-Marker chuan EPR (5A / 50V): Cho phep vao EPR Mode len 48V x 5A = 240 W!

3. May trang thai Thuong thao Nguon Policy Engine (PE_SRC <-> PE_SNK FSM):
   ATTACHED -> CABLE_E_MARKER_CHECK -> SRC_CAPABILITIES -> REQUEST -> ACCEPT -> PS_RDY
   -> EPR_MODE_ENTRY -> EPR_SRC_CAPABILITIES -> EPR_REQUEST(48V/5A) -> PS_RDY_240W!
--------------------------------------------------------------------------------
"""

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class USBPDCRC32:
    """Bo tinh CRC-32 phan cung theo chuan USB-PD (IEEE 802.3: Poly 0xEDB88320)."""

    POLY_REFL = 0xEDB88320

    @classmethod
    def compute(cls, data: bytes) -> int:
        crc = 0xFFFFFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ cls.POLY_REFL
                else:
                    crc >>= 1
        return crc ^ 0xFFFFFFFF


@dataclass
class FixedPDO:
    voltage_v: float
    max_current_a: float

    def encode_u32(self) -> int:
        # USB-PD Fixed Supply PDO: [19..10] Voltage (50mV units), [9..0] MaxCurrent (10mA units)
        v_units = int(round(self.voltage_v / 0.050)) & 0x3FF
        i_units = int(round(self.max_current_a / 0.010)) & 0x3FF
        return (v_units << 10) | i_units

    @staticmethod
    def decode_u32(val: int) -> "FixedPDO":
        v = ((val >> 10) & 0x3FF) * 0.050
        i = (val & 0x3FF) * 0.010
        return FixedPDO(v, i)


@dataclass
class CableEMarker:
    present: bool
    max_current_a: float
    epr_capable: bool   # Ho tro >= 50V (240W) hay chi <= 20V (100W)


class USBPDFrameCodec:
    """Dong goi & Giai ma khung tin USB-PD kem CRC-32."""

    @staticmethod
    def pack_message(msg_type: int, msg_id: int, data_objects: List[int], is_extended: bool = False) -> bytes:
        n_obj = len(data_objects) & 0x7
        # Spec Rev 3.x = 0b10 (bits 7..6)
        header = (
            ((1 if is_extended else 0) << 15)
            | (n_obj << 12)
            | ((msg_id & 0x7) << 9)
            | (0b10 << 6)
            | (msg_type & 0x1F)
        )
        body = struct.pack("<H", header) + b"".join(struct.pack("<I", obj) for obj in data_objects)
        crc = USBPDCRC32.compute(body)
        return body + struct.pack("<I", crc)

    @staticmethod
    def unpack_and_verify(raw_frame: bytes) -> Tuple[bool, int, int, List[int]]:
        if len(raw_frame) < 6:
            return False, 0, 0, []
        body = raw_frame[:-4]
        rx_crc = struct.unpack("<I", raw_frame[-4:])[0]
        calc_crc = USBPDCRC32.compute(body)
        if rx_crc != calc_crc:
            return False, 0, 0, []
        header = struct.unpack("<H", body[:2])[0]
        msg_type = header & 0x1F
        msg_id = (header >> 9) & 0x7
        n_obj = (header >> 12) & 0x7
        objs = [struct.unpack("<I", body[2 + 4 * i : 6 + 4 * i])[0] for i in range(n_obj)]
        return True, msg_type, msg_id, objs


# Ma thong diep USB-PD Control & Data Message Types
MSG_GOODCRC = 0x01
MSG_ACCEPT = 0x03
MSG_REJECT = 0x04
MSG_PS_RDY = 0x06
MSG_EPR_MODE = 0x14
MSG_SRC_CAP = 0x01
MSG_REQUEST = 0x02
MSG_EPR_SRC_CAP = 0x11
MSG_EPR_REQUEST = 0x09


class USBPDPolicyEngineFSM:
    """
    May trang thai Thuong thao Nguon USB-PD 3.1 EPR:
    Kiem tra E-Marker truoc khi cho phep cap 100W hoac kich hoat EPR 240W (48V/5A).
    """

    def __init__(self, source_max_power_w: float = 240.0):
        self.source_max_w = source_max_power_w
        self.state = "PE_DISABLED"
        self.msg_id = 0
        self.epr_active = False
        self.negotiated_v = 5.0
        self.negotiated_i = 3.0
        self.trace_log: List[str] = []

    def negotiate_with_sink(
        self, cable: CableEMarker, sink_req_v: float, sink_req_i: float
    ) -> Dict[str, any]:
        self.trace_log.clear()
        self.state = "PE_SRC_DISCOVER_CABLE"

        # Buoc 1: Query E-Marker qua kenh SOP' de khoa gioi han an toan cap
        if not cable.present:
            cable_i_cap = 3.0
            cable_epr_ok = False
        else:
            cable_i_cap = cable.max_current_a
            cable_epr_ok = cable.epr_capable

        self.trace_log.append(
            f"[SOP'] E-Marker Check: Present={cable.present}, I_cap={cable_i_cap:.1f}A, EPR_Capable={cable_epr_ok}"
        )

        # Buoc 2: Gui Source_Capabilities (SPR 5V, 9V, 15V, 20V @ min(5A, cable_i_cap))
        self.state = "PE_SRC_SEND_CAPABILITIES"
        spr_pdos = [
            FixedPDO(5.0, min(3.0, cable_i_cap)),
            FixedPDO(9.0, min(3.0, cable_i_cap)),
            FixedPDO(15.0, min(3.0, cable_i_cap)),
            FixedPDO(20.0, min(5.0, cable_i_cap)),
        ]
        pkt_cap = USBPDFrameCodec.pack_message(MSG_SRC_CAP, self.msg_id, [p.encode_u32() for p in spr_pdos])
        ok, _, _, objs_rx = USBPDFrameCodec.unpack_and_verify(pkt_cap)
        assert ok and len(objs_rx) == 4
        self.msg_id = (self.msg_id + 1) & 0x7

        # Buoc 3: Thuong thao SPR truoc (toi da 20V x cable_i_cap)
        spr_v = min(20.0, sink_req_v)
        spr_i = min(sink_req_i, cable_i_cap)
        self.negotiated_v = spr_v
        self.negotiated_i = spr_i
        self.epr_active = False
        self.state = "PE_SRC_READY_SPR"
        self.trace_log.append(f"[SPR] Negotiated {spr_v:.1f}V / {spr_i:.1f}A ({spr_v*spr_i:.0f}W) -> PS_RDY")

        # Buoc 4: Neu thiet bi yeu cau > 20V (EPR Mode: 28V, 36V, 48V), kiem tra dieu kien EPR!
        if sink_req_v > 20.0:
            self.state = "PE_SRC_EPR_WAIT_ENTRY"
            pkt_enter = USBPDFrameCodec.pack_message(MSG_EPR_MODE, self.msg_id, [0x01 << 24])
            ok_e, _, _, _ = USBPDFrameCodec.unpack_and_verify(pkt_enter)
            assert ok_e
            self.msg_id = (self.msg_id + 1) & 0x7

            if not cable_epr_ok or cable_i_cap < 5.0:
                # TU CHOI VAO EPR vi cap khong dat chuan 240W -> Giu an toan o muc SPR!
                self.state = "PE_SRC_EPR_REJECTED_STAY_SPR"
                self.trace_log.append(
                    f"[EPR REJECTED] Cap khong dat chuan EPR 50V/5A! Khoa an toan tai {self.negotiated_v:.1f}V / {self.negotiated_i:.1f}A"
                )
            else:
                # Vao che do EPR & Gui EPR_Source_Capabilities (28V, 36V, 48V @ 5.0A)
                epr_pdos = [
                    FixedPDO(28.0, 5.0),
                    FixedPDO(36.0, 5.0),
                    FixedPDO(48.0, 5.0),
                ]
                pkt_epr_cap = USBPDFrameCodec.pack_message(
                    MSG_EPR_SRC_CAP, self.msg_id, [p.encode_u32() for p in epr_pdos], is_extended=True
                )
                ok_c, _, _, epr_objs = USBPDFrameCodec.unpack_and_verify(pkt_epr_cap)
                assert ok_c and FixedPDO.decode_u32(epr_objs[-1]).voltage_v == 48.0
                self.msg_id = (self.msg_id + 1) & 0x7

                # Sink gui EPR_Request chon 48V / 5A -> Source Accept -> PS_RDY
                req_v = min(48.0, sink_req_v)
                req_i = min(5.0, sink_req_i, self.source_max_w / req_v)
                self.negotiated_v = req_v
                self.negotiated_i = req_i
                self.epr_active = True
                self.state = "PE_SRC_EPR_READY_240W"
                self.trace_log.append(f"[EPR 3.1] EPR_Enter ACK -> {req_v:.1f}V / {req_i:.1f}A ({req_v*req_i:.0f}W) PS_RDY!")

        return {
            "final_state": self.state,
            "epr_active": self.epr_active,
            "voltage_v": self.negotiated_v,
            "current_a": self.negotiated_i,
            "power_w": self.negotiated_v * self.negotiated_i,
            "log": list(self.trace_log),
        }


def test_crc32_epr_policy_fsm():
    """Chuong trinh kiem thu CRC-32 phan cung & FSM Thuong thao USB-PD 3.1 EPR 240W."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BO (NHOM 54) - BAI 213 (MILESTONE BO.2)")
    print("KHUNG TRUYEN CRC-32, XAC THUC CAP E-MARKER & POLICY ENGINE EPR 240W")
    print("=" * 80)

    # 1. Kiem thu chuan IEEE 802.3 CRC-32 & Bat loi 1-bit flip tren day CC
    print("\n[1] Kiem thu Hardware CRC-32 (Check Value '123456789' == 0xCBF43926) & Bat loi Bitflip:")
    std_crc = USBPDCRC32.compute(b"123456789")
    pdo_48v = FixedPDO(48.0, 5.0).encode_u32()
    good_frame = USBPDFrameCodec.pack_message(MSG_EPR_SRC_CAP, msg_id=3, data_objects=[pdo_48v], is_extended=True)
    ok_clean, _, _, objs = USBPDFrameCodec.unpack_and_verify(good_frame)

    # Tiem loi 1 bit vao payload
    corrupted = bytearray(good_frame)
    corrupted[3] ^= 0x08
    ok_bad, _, _, _ = USBPDFrameCodec.unpack_and_verify(bytes(corrupted))

    print(f"  * CRC-32('123456789')     : 0x{std_crc:08X} (Target: 0xCBF43926)")
    print(f"  * Goi tin 48V/5A sach     : Verify={ok_clean} | Decoded={FixedPDO.decode_u32(objs[0]).voltage_v:.1f}V / {FixedPDO.decode_u32(objs[0]).max_current_a:.1f}A")
    print(f"  * Goi tin dinh 1-bit flip : Verify={ok_bad} (Bat loi 100%, yeu cau GoodCRC Retry!)")

    assert std_crc == 0xCBF43926 and ok_clean and not ok_bad
    print("  -> Ket luan: Hardware CRC-32 chuan xac IEEE 802.3 va chan 100% khung loi (PASS)!")

    # 2. Kiem thu Policy Engine FSM tren 3 loai cap khi MacBook xin EPR 48V / 5A (240W)
    print("\n[2] Kiem thu Policy Engine FSM khi Sink yeu cau 48V/5A tren 3 loai cap khac nhau:")
    pe = USBPDPolicyEngineFSM(source_max_power_w=240.0)

    c_60w = CableEMarker(present=False, max_current_a=3.0, epr_capable=False)
    c_100w = CableEMarker(present=True, max_current_a=5.0, epr_capable=False)
    c_240w = CableEMarker(present=True, max_current_a=5.0, epr_capable=True)

    r_60 = pe.negotiate_with_sink(c_60w, sink_req_v=48.0, sink_req_i=5.0)
    r_100 = pe.negotiate_with_sink(c_100w, sink_req_v=48.0, sink_req_i=5.0)
    r_240 = pe.negotiate_with_sink(c_240w, sink_req_v=48.0, sink_req_i=5.0)

    print(f"  * Cap thuong (No E-Marker): {r_60['voltage_v']:4.1f}V / {r_60['current_a']:.1f}A = {r_60['power_w']:5.0f}W | EPR={r_60['epr_active']} ({r_60['final_state']})")
    print(f"  * Cap 100W (Non-EPR 5A)   : {r_100['voltage_v']:4.1f}V / {r_100['current_a']:.1f}A = {r_100['power_w']:5.0f}W | EPR={r_100['epr_active']} ({r_100['final_state']})")
    print(f"  * Cap 240W EPR Certified  : {r_240['voltage_v']:4.1f}V / {r_240['current_a']:.1f}A = {r_240['power_w']:5.0f}W | EPR={r_240['epr_active']} ({r_240['final_state']})")

    assert r_60["power_w"] == 60.0 and not r_60["epr_active"]
    assert r_100["power_w"] == 100.0 and not r_100["epr_active"]
    assert r_240["power_w"] == 240.0 and r_240["voltage_v"] == 48.0 and r_240["epr_active"]
    print("  -> Ket luan: Policy Engine khoa an toan cap 60W/100W va cap du 240W cho cap EPR (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 213: USB-PD 3.1 CRC-32 & EPR POLICY FSM 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_crc32_epr_policy_fsm()
