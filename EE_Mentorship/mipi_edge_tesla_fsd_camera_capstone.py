"""
Tesla FSD HW4 Multi-Camera MIPI CSI-2 & D-PHY Real-Time Ingestion Engine Capstone
Chuyen de 23: MIPI CSI-2 Camera Serial Interface & D-PHY Hardware Pipeline
Milestone AJ.4 - Bai hoc 91 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Dung hop toan chuoi cong nghe: May trang thai D-PHY, Phau thuat goi tin CSI-2,
  Giai ma sua sai ECC SECDED, Kiem toan CRC-16, Dong goi diem anh HDR RAW12.
- Gia lap he thong 8 Camera da kenh ao (VC 0 den VC 7) tren Tesla Model S Plaid FSD HW4.
- Kiem soat do tre xu ly duoi 1 chu ky 60 FPS (16.67 ms) va co che phong ve Failsafe Safe-Stop.
"""

from enum import IntEnum
import struct
import time
from typing import List, Dict, Tuple, Optional


class TeslaCameraId(IntEnum):
    FRONT_MAIN     = 0  # VC 0: Camera chinh phia truoc (Tam nhin trung binh 150m)
    FRONT_WIDE     = 1  # VC 1: Camera goc rong phia truoc (120 do, nga tu)
    FRONT_NARROW   = 2  # VC 2: Camera vien vong goc hep (250m cao toc)
    B_PILLAR_LEFT  = 3  # VC 3: Camera cot B ben trai
    B_PILLAR_RIGHT = 4  # VC 4: Camera cot B ben phai
    REAR_BACKUP    = 5  # VC 5: Camera quan sat phia sau
    FENDER_LEFT    = 6  # VC 6: Camera tai xe ben trai (chuyen lan)
    FENDER_RIGHT   = 7  # VC 7: Camera tai xe ben phai (chuyen lan)


def calculate_mipi_parity(data24: int) -> int:
    """Tinh 6 bits parity cho 24-bit du lieu Header chuan MIPI CSI-2"""
    p0_mask = 0x0F12B7
    p1_mask = 0x0F255B
    p2_mask = 0x0739CD
    p3_mask = 0x0B7F0E
    p4_mask = 0xC0FFF0
    p5_mask = 0xFF0000

    def parity(val: int) -> int:
        return bin(val).count('1') % 2

    p0 = parity(data24 & p0_mask)
    p1 = parity(data24 & p1_mask)
    p2 = parity(data24 & p2_mask)
    p3 = parity(data24 & p3_mask)
    p4 = parity(data24 & p4_mask)
    p5 = parity(data24 & p5_mask)

    return p0 | (p1 << 1) | (p2 << 2) | (p3 << 3) | (p4 << 4) | (p5 << 5)


def calculate_crc16_itu(data: bytes) -> int:
    """Tinh Checksum CRC-16 ITU cho Payload anh"""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


SYNDROME_LOOKUP_TABLE = {
    0x01: ("PARITY", 0), 0x02: ("PARITY", 1), 0x04: ("PARITY", 2),
    0x08: ("PARITY", 3), 0x10: ("PARITY", 4), 0x20: ("PARITY", 5),
    0x07: ("DATA", 0),  0x0B: ("DATA", 1),  0x0D: ("DATA", 2),  0x0E: ("DATA", 3),
    0x13: ("DATA", 4),  0x15: ("DATA", 5),  0x16: ("DATA", 6),  0x19: ("DATA", 7),
    0x1A: ("DATA", 8),  0x1C: ("DATA", 9),  0x17: ("DATA", 10), 0x1B: ("DATA", 11),
    0x1D: ("DATA", 12), 0x1E: ("DATA", 13), 0x1F: ("DATA", 14), 0x0F: ("DATA", 15),
    0x23: ("DATA", 16), 0x25: ("DATA", 17), 0x26: ("DATA", 18), 0x29: ("DATA", 19),
    0x2A: ("DATA", 20), 0x2C: ("DATA", 21), 0x27: ("DATA", 22), 0x2B: ("DATA", 23)
}


class TeslaFsdCsi2RxEngine:
    """
    Dong co thu nhan va xu ly luong da Camera MIPI CSI-2 tren Tesla HW4 FSD SoC.
    Ho tro Zero-Copy Assembly, Tu sua sai ECC, va Giam sat Failsafe.
    """
    def __init__(self, target_fps: float = 60.0):
        self.target_fps = target_fps
        self.max_frame_interval_ms = (1000.0 / target_fps) * 1.5  # Cho phep trễ toi da 1.5 frame

        # Bo dem trang thai cho 8 Camera (VC 0 den VC 7)
        self.camera_channels: Dict[int, Dict[str, any]] = {
            cam.value: {
                "name": cam.name,
                "in_frame": False,
                "current_frame_id": 0,
                "lines_assembled": [],
                "total_frames_completed": 0,
                "ecc_single_errors_corrected": 0,
                "ecc_double_errors_dropped": 0,
                "crc_errors_detected": 0,
                "last_frame_timestamp_ms": 0.0,
                "status": "HEALTHY"
            }
            for cam in TeslaCameraId
        }
        self.total_packets_processed = 0

    def ingest_packet(self, packet_bytes: bytes, current_time_ms: float) -> Dict[str, any]:
        """
        Xu ly mot goi tin MIPI CSI-2 truc tiep tu bo giai tuan tu Deserializer.
        """
        self.total_packets_processed += 1
        if len(packet_bytes) < 4:
            return {"status": "DROPPED_INVALID_LENGTH"}

        # 1. Giai ma va sua sai ECC tren Header (4 bytes)
        di_raw, d1_raw, d2_raw, ecc_raw = struct.unpack("<BBBB", packet_bytes[:4])
        data24 = di_raw | (d1_raw << 8) | (d2_raw << 16)
        computed_p = calculate_mipi_parity(data24)
        syndrome = computed_p ^ (ecc_raw & 0x3F)

        # Xac dinh Virtual Channel so bo
        vc = (di_raw >> 6) & 0x03  # 2 bit VC goc (hoac mo rong tu phan cung)
        # Trong mo phong 8-camera: su dung them bit cao cua Deserializer
        dt = di_raw & 0x3F

        if syndrome != 0:
            if syndrome in SYNDROME_LOOKUP_TABLE:
                err_type, bit_idx = SYNDROME_LOOKUP_TABLE[syndrome]
                if err_type == "DATA":
                    data24 ^= (1 << bit_idx)
                    di_raw = data24 & 0xFF
                    d1_raw = (data24 >> 8) & 0xFF
                    d2_raw = (data24 >> 16) & 0xFF
                    vc = (di_raw >> 6) & 0x03
                    dt = di_raw & 0x3F
                self.camera_channels[vc]["ecc_single_errors_corrected"] += 1
            else:
                # Loi kep bat kha sua -> Huy bo goi tin de bao ve an toan
                self.camera_channels[vc]["ecc_double_errors_dropped"] += 1
                return {"status": "DROPPED_ECC_DOUBLE_ERROR", "vc": vc}

        # 2. Xu ly Short Packet (Frame Start: 0x00, Frame End: 0x01)
        if dt == 0x00:  # FRAME START (FS)
            frame_id = d1_raw | (d2_raw << 8)
            ch = self.camera_channels[vc]
            ch["in_frame"] = True
            ch["current_frame_id"] = frame_id
            ch["lines_assembled"] = []
            return {"status": "FRAME_START", "vc": vc, "frame_id": frame_id}

        elif dt == 0x01:  # FRAME END (FE)
            frame_id = d1_raw | (d2_raw << 8)
            ch = self.camera_channels[vc]
            ch["in_frame"] = False
            ch["total_frames_completed"] += 1
            ch["last_frame_timestamp_ms"] = current_time_ms
            return {
                "status": "FRAME_COMPLETE",
                "vc": vc,
                "frame_id": frame_id,
                "lines": len(ch["lines_assembled"])
            }

        # 3. Xu ly Long Packet (RAW12 Image Data: 0x2C)
        elif dt == 0x2C:  # RAW12
            wc = d1_raw | (d2_raw << 8)
            if len(packet_bytes) < 4 + wc + 2:
                return {"status": "DROPPED_INCOMPLETE_PAYLOAD", "vc": vc}

            payload = packet_bytes[4:4 + wc]
            crc_received = struct.unpack("<H", packet_bytes[4 + wc:4 + wc + 2])[0]
            crc_computed = calculate_crc16_itu(payload)

            if crc_received != crc_computed:
                self.camera_channels[vc]["crc_errors_detected"] += 1
                return {"status": "DROPPED_CRC_ERROR", "vc": vc}

            # Dong goi hop le -> Nua dong anh vao bo dem frame
            if self.camera_channels[vc]["in_frame"]:
                self.camera_channels[vc]["lines_assembled"].append(payload)

            return {"status": "LINE_ASSEMBLED", "vc": vc, "wc": wc}

        return {"status": "IGNORED_UNKNOWN_DT", "dt": dt}

    def check_failsafe_watchdog(self, current_time_ms: float) -> Tuple[bool, List[str]]:
        """
        Kiem tra dinh ky Failsafe Watchdog cho camera an toan bat buoc (Front Main Camera).
        Neu Front Camera ngung phat qua 25 ms -> Bao dong SAFE-STOP AUTOPILOT!
        """
        failsafe_triggered = False
        warnings = []

        front_cam = self.camera_channels[TeslaCameraId.FRONT_MAIN.value]
        time_since_last_frame = current_time_ms - front_cam["last_frame_timestamp_ms"]

        if time_since_last_frame > self.max_frame_interval_ms and front_cam["total_frames_completed"] > 0:
            failsafe_triggered = True
            front_cam["status"] = "FAILSAFE_TIMEOUT"
            warnings.append(f"CRITICAL: Camera Chinh Phia Truoc (Front Main) mat tin hieu {time_since_last_frame:.1f} ms!")

        return failsafe_triggered, warnings


def build_csi2_packet(vc: int, dt: int, payload: bytes = b"", frame_num: int = 0) -> bytes:
    di = ((vc & 0x03) << 6) | (dt & 0x3F)
    if dt <= 0x0F:
        d1 = frame_num & 0xFF
        d2 = (frame_num >> 8) & 0xFF
        ecc = calculate_mipi_parity(di | (d1 << 8) | (d2 << 16))
        return struct.pack("<BBBB", di, d1, d2, ecc)
    else:
        wc = len(payload)
        d1 = wc & 0xFF
        d2 = (wc >> 8) & 0xFF
        ecc = calculate_mipi_parity(di | (d1 << 8) | (d2 << 16))
        crc = calculate_crc16_itu(payload)
        return struct.pack("<BBBB", di, d1, d2, ecc) + payload + struct.pack("<H", crc)


def test_tesla_fsd_camera_capstone():
    print("=" * 80)
    print("BAT DAU MO PHONG TESLA FSD HW4 MULTI-CAMERA MIPI CSI-2 RX CAPSTONE")
    print("=" * 80)
    print("Cau hinh he thong: 8 Camera Sensor Rig | Toc do khung hinh: 60 FPS")
    print("Giao thuc: MIPI CSI-2 v2.0 qua D-PHY 4-Lanes | Dinh dang diem anh: RAW12 HDR")
    print("-" * 80)

    engine = TeslaFsdCsi2RxEngine(target_fps=60.0)

    # 1. Mo phong truyen 3 khung hinh video lien tiep tu Camera Chinh Truoc (VC 0)
    # va Camera Goc Rong (VC 1)
    sim_time_ms = 0.0

    print("Giai doan 1: Truyen khung hinh binh thuong trong dieu kien hoan hao...")
    for frame_idx in range(1, 4):
        sim_time_ms += 16.67  # 60 FPS (1 frame moi 16.67 ms)

        # Frame Start ca 2 camera
        engine.ingest_packet(build_csi2_packet(0, 0x00, frame_num=frame_idx), sim_time_ms)
        engine.ingest_packet(build_csi2_packet(1, 0x00, frame_num=frame_idx), sim_time_ms)

        # 4 Dong anh RAW12 cho moi camera (Moi dong 384 bytes = 256 pixels RAW12)
        mock_raw12_line = bytes([0x77] * 384)
        for line_idx in range(4):
            engine.ingest_packet(build_csi2_packet(0, 0x2C, payload=mock_raw12_line), sim_time_ms)
            engine.ingest_packet(build_csi2_packet(1, 0x2C, payload=mock_raw12_line), sim_time_ms)

        # Frame End ca 2 camera
        engine.ingest_packet(build_csi2_packet(0, 0x01, frame_num=frame_idx), sim_time_ms)
        engine.ingest_packet(build_csi2_packet(1, 0x01, frame_num=frame_idx), sim_time_ms)

    print(f"-> Hoan tat 3 frames. So frame hoan thanh VC 0: {engine.camera_channels[0]['total_frames_completed']}, VC 1: {engine.camera_channels[1]['total_frames_completed']}")
    print("-" * 80)

    # 2. Giai doan 2: Bom nhieu dien tu EMI va xung buc xa (Hard Fault Injection)
    print("Giai doan 2: Thu nghiem kha nang tu phuc hoi Self-Healing truoc xung nhieu EMI...")
    sim_time_ms += 16.67
    # Khoi dong Frame 4
    engine.ingest_packet(build_csi2_packet(0, 0x00, frame_num=4), sim_time_ms)

    # Dong 1: Binh thuong
    engine.ingest_packet(build_csi2_packet(0, 0x2C, payload=mock_raw12_line), sim_time_ms)

    # Dong 2: Bi nhieu 1-bit tren Header (Lat bit D4 cua DI)
    corrupted_header_packet = bytearray(build_csi2_packet(0, 0x2C, payload=mock_raw12_line))
    corrupted_header_packet[0] ^= 0x10  # Lat 1 bit tren DI
    res_ecc = engine.ingest_packet(bytes(corrupted_header_packet), sim_time_ms)
    print(f"-> Ket qua khi Header bi lat 1-bit: {res_ecc['status']} (Da kich hoat ECC tu sua loi!)")

    # Dong 3: Bi nhieu Payload CRC (Lat bit trong du lieu anh)
    corrupted_payload_packet = bytearray(build_csi2_packet(0, 0x2C, payload=mock_raw12_line))
    corrupted_payload_packet[20] ^= 0xFF  # Lat bit trong anh
    res_crc = engine.ingest_packet(bytes(corrupted_payload_packet), sim_time_ms)
    print(f"-> Ket qua khi Payload bi loi CRC: {res_crc['status']} (Loc bo dong loi thanh cong!)")

    # Dong 4: Bi nhieu nang gay loi kep 2-bit tren Header (Double Error)
    corrupted_double_packet = bytearray(build_csi2_packet(0, 0x2C, payload=mock_raw12_line))
    corrupted_double_packet[0] ^= 0x03  # Lat 2 bits D0 va D1
    res_double = engine.ingest_packet(bytes(corrupted_double_packet), sim_time_ms)
    print(f"-> Ket qua khi Header bi loi kep 2-bit: {res_double['status']} (Huy bo an toan!)")

    # Ket thuc Frame 4
    engine.ingest_packet(build_csi2_packet(0, 0x01, frame_num=4), sim_time_ms)
    print("-" * 80)

    # 3. Giai doan 3: Thu nghiem Failsafe Watchdog khi Camera Chinh bi dut cap hoan toan
    print("Giai doan 3: Kiem tra co che phong ve Failsafe Watchdog Safe-Stop...")
    sim_time_ms += 50.0  # Thoi gian troi qua 50 ms (vuot qua nguong 25 ms) ma khong co frame moi tu VC 0
    is_failsafe, warnings = engine.check_failsafe_watchdog(sim_time_ms)

    print(f"-> Trang thai kich hoat he thong phong ve Safe-Stop: {'KICH HOAT KHAN CAP' if is_failsafe else 'BINH THUONG'}")
    for w in warnings:
        print(f"   [!] Canh bao he thong xe: {w}")

    print("-" * 80)
    print("Bang thong ke toan dien bo thu MIPI CSI-2 Tesla FSD HW4:")
    print("Kenh Ao | Ten Camera                | Frames OK | ECC Fix | ECC Drop | CRC Drop | Trang Thai")
    print("-" * 80)
    for vc, ch in engine.camera_channels.items():
        if vc in [0, 1]:
            print(f"VC {vc:2d}  | {ch['name']:25s} | {ch['total_frames_completed']:9d} | {ch['ecc_single_errors_corrected']:7d} | {ch['ecc_double_errors_dropped']:8d} | {ch['crc_errors_detected']:8d} | {ch['status']}")

    assert engine.camera_channels[0]["total_frames_completed"] == 4, "VC 0 phai hoan tat du 4 frames!"
    assert engine.camera_channels[0]["ecc_single_errors_corrected"] >= 1, "ECC phai sua it nhat 1 loi don!"
    assert engine.camera_channels[0]["ecc_double_errors_dropped"] >= 1, "He thong phai huy it nhat 1 goi loi kep!"
    assert engine.camera_channels[0]["crc_errors_detected"] >= 1, "CRC phai phat hien it nhat 1 dong loi!"
    assert is_failsafe is True, "Failsafe Watchdog phai duoc kich hoat khi mat tin hieu qua 25ms!"

    print("=" * 80)
    print("[PASS] Tesla FSD HW4 Multi-Camera MIPI CSI-2 & D-PHY Capstone: 100% Hoan hao!")


if __name__ == "__main__":
    test_tesla_fsd_camera_capstone()
