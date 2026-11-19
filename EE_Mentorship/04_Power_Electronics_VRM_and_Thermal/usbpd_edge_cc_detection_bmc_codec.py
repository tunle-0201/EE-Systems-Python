"""
EE MENTORSHIP PROGRAM - MODULE BO (NHOM 54) - BAI 212 (MILESTONE BO.1)
================================================================================
TANG VAT LY USB TYPE-C CC1/CC2 ORIENTATION DETECTION, MA KHOI 4B5B &
THU PHAT BI-PHASE MARK CODING (BMC 300 KBPS) KEM HOI PHUC XUNG NHIP THICH NGHI
CHO APPLE MACBOOK PRO USB-PD & HE THONG NGUON THONG MINH
================================================================================

Nguyen ly vat ly va Giao thuc Tang 1 USB-PD:
1. Mang phan ap dien tro CC1 / CC2 xac dinh Cam nguoc dau & Dong dien toi da:
   - Nguon (Source) keo hai chan CC1, CC2 len 5.0V qua R_p chinh xac:
       R_p = 56 kOhm (Default 0.9A) | 22 kOhm (1.5A) | 10 kOhm (3.0A).
   - Thiet bi nhan (Sink) keo chan CC hoat dong xuong GND qua R_d = 5.1 kOhm.
   - Cap chu dong co chip E-Marker (100W/240W) keo chan con lai xuong qua R_a = 1.0 kOhm
     de nguon biet phai cap nguon VCONN (5V) nuoi chip trong dau cap!

2. Ma hoa Duong truyen Bi-Phase Mark Coding (BMC - 300 kbps tren 1 day CC):
   - Khong co day Clock rieng! BMC nhung xung nhip vao chinh chuoi bit:
     + Tai MOI ranh gioi bit (Bit boundary): Luon luon dao muc logic!
     + Bit '0': KHONG dao muc o giua chu ky (khoang cach 2 suon = 1.0 UI).
     + Bit '1': DAO MUC them 1 lan nua o giua chu ky (hai suon ngan 0.5 UI lien tiep).
   - Dong bo bang chuoi Preamble 64-bit (010101...), cho phep mach thu thich nghi
     voi sai so tan so thach anh RC len toi +/- 10%!

3. Ma khoi 4b5b chuan USB-PD (Table 5-2):
   - Chuyen 4-bit nibble -> 5-bit symbol khong qua 3 bit 0 lien tiep de dam bao du
     so suon chuyen trang thai + cung cap cac ma K-code (Sync-1/2/3, EOP) tach khung!
--------------------------------------------------------------------------------
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


# Bang 4b5b chuan USB Power Delivery Specification Table 5-2
USBPD_4B5B_TABLE: Dict[int, int] = {
    0x0: 0b11110, 0x1: 0b01001, 0x2: 0b10100, 0x3: 0b10101,
    0x4: 0b01010, 0x5: 0b01011, 0x6: 0b01110, 0x7: 0b01111,
    0x8: 0b10010, 0x9: 0b10011, 0xA: 0b10110, 0xB: 0b10111,
    0xC: 0b11010, 0xD: 0b11011, 0xE: 0b11100, 0xF: 0b11101,
}
USBPD_5B4B_INV: Dict[int, int] = {v: k for k, v in USBPD_4B5B_TABLE.items()}

K_SYNC1 = 0b11000
K_SYNC2 = 0b10001
K_SYNC3 = 0b00110
K_EOP = 0b01101


@dataclass
class CCStatus:
    attached: bool
    orientation: str            # "NORMAL (CC1)", "FLIPPED (CC2)", "NONE"
    advertised_current_a: float
    vconn_required: bool
    v_cc1: float
    v_cc2: float


class TypeCCCDetector:
    """Mo phong mach phat hien cam cap & dinh muc dong Source -> Sink qua CC1/CC2."""

    RP_TO_CURRENT = {56000.0: 0.9, 22000.0: 1.5, 10000.0: 3.0}

    # Nguong phan chia vRa vs vRd chuan USB Type-C Table 4-25 theo tung loai R_p
    THRESHOLDS = {
        56000.0: (0.20, 1.60),   # Ra < 0.20V < Rd < 1.60V < Open
        22000.0: (0.40, 1.60),   # Ra < 0.40V < Rd < 1.60V < Open
        10000.0: (0.80, 2.60),   # Ra < 0.80V < Rd < 2.60V < Open
    }

    @classmethod
    def sense_cc_pins(cls, r_p_ohm: float, cc1_load_ohm: float, cc2_load_ohm: float, v_src: float = 5.0) -> CCStatus:
        def divider(r_load: float) -> float:
            if r_load == float("inf"):
                return v_src
            return v_src * (r_load / (r_p_ohm + r_load))

        v1 = divider(cc1_load_ohm)
        v2 = divider(cc2_load_ohm)
        th_ra, th_open = cls.THRESHOLDS[r_p_ohm]

        def classify(v: float) -> str:
            if v < th_ra:
                return "Ra"
            if v < th_open:
                return "Rd"
            return "OPEN"

        c1, c2 = classify(v1), classify(v2)
        if c1 == "Rd" and c2 != "Rd":
            orient = "NORMAL (CC1)"
            attached = True
            vconn = (c2 == "Ra")
        elif c2 == "Rd" and c1 != "Rd":
            orient = "FLIPPED (CC2)"
            attached = True
            vconn = (c1 == "Ra")
        else:
            orient = "NONE"
            attached = False
            vconn = False

        return CCStatus(
            attached=attached,
            orientation=orient,
            advertised_current_a=cls.RP_TO_CURRENT[r_p_ohm] if attached else 0.0,
            vconn_required=vconn,
            v_cc1=v1,
            v_cc2=v2,
        )


class USBPD4b5bCodec:
    """Bo ma hoa/giai ma 4b5b + Preamble 64-bit + SOP Ordered Set + EOP (LSB-first)."""

    @staticmethod
    def _to_bits_lsb(sym5: int) -> List[int]:
        return [(sym5 >> i) & 1 for i in range(5)]

    @classmethod
    def encode_frame_bits(cls, payload_bytes: List[int]) -> List[int]:
        bits: List[int] = []
        # 1. 64-bit Preamble (0, 1 xen ke bat dau bang 0)
        for i in range(64):
            bits.append(i & 1)
        # 2. SOP Ordered Set: Sync-1, Sync-1, Sync-1, Sync-2
        for k_code in (K_SYNC1, K_SYNC1, K_SYNC1, K_SYNC2):
            bits.extend(cls._to_bits_lsb(k_code))
        # 3. Payload bytes (Low nibble truoc, High nibble sau)
        for b in payload_bytes:
            bits.extend(cls._to_bits_lsb(USBPD_4B5B_TABLE[b & 0x0F]))
            bits.extend(cls._to_bits_lsb(USBPD_4B5B_TABLE[(b >> 4) & 0x0F]))
        # 4. EOP End-of-Packet
        bits.extend(cls._to_bits_lsb(K_EOP))
        return bits

    @classmethod
    def decode_frame_bits(cls, rx_bits: List[int]) -> Tuple[bool, List[int]]:
        sop_pattern = (
            cls._to_bits_lsb(K_SYNC1)
            + cls._to_bits_lsb(K_SYNC1)
            + cls._to_bits_lsb(K_SYNC1)
            + cls._to_bits_lsb(K_SYNC2)
        )
        # Quet tim SOP 20-bit bat dau khung du lieu
        start_idx = -1
        for i in range(len(rx_bits) - 20):
            if rx_bits[i : i + 20] == sop_pattern:
                start_idx = i + 20
                break
        if start_idx < 0:
            return False, []

        nibbles: List[int] = []
        pos = start_idx
        eop_bits = cls._to_bits_lsb(K_EOP)
        while pos + 5 <= len(rx_bits):
            sym_bits = rx_bits[pos : pos + 5]
            pos += 5
            if sym_bits == eop_bits:
                if len(nibbles) % 2 != 0:
                    return False, []
                out_bytes = [nibbles[2 * j] | (nibbles[2 * j + 1] << 4) for j in range(len(nibbles) // 2)]
                return True, out_bytes
            sym_val = sum((b << k) for k, b in enumerate(sym_bits))
            if sym_val not in USBPD_5B4B_INV:
                return False, []
            nibbles.append(USBPD_5B4B_INV[sym_val])
        return False, []


class AdaptiveBMCTransceiver:
    """
    Bo thu phat BMC 300 kbps tren 1 day CC (0..1.125V) co Clock-Data Recovery:
    Chiu duoc sai lech xung nhip RC +/- 10% va nhieu duong day.
    """

    def __init__(self, samples_per_nom_ui: int = 24):
        self.spu = samples_per_nom_ui

    def transmit_waveform(
        self, bits: List[int], tx_clock_drift_pct: float = 0.0, noise_std_v: float = 0.03, seed: int = 212
    ) -> List[float]:
        rng = random.Random(seed)
        spu_actual = self.spu * (1.0 + tx_clock_drift_pct / 100.0)
        half_actual = 0.5 * spu_actual
        waveform: List[float] = []

        # Khoi dau idle Low 0.5 UI de bat duoc canh dau cua Preamble[0]
        cur_level = 0
        for _ in range(self.spu // 2):
            waveform.append(0.0 + rng.gauss(0.0, noise_std_v))

        t_samp = 0.0
        cur_time = 0.0
        for b in bits:
            # 1. Tai dau bit (t = cur_time): bat buoc dao muc
            cur_level ^= 1
            if b == 1:
                # Bit 1: Muc cur_level keo dai 0.5 UI, sau do dao tiep 0.5 UI
                mid_time = cur_time + half_actual
                end_time = cur_time + spu_actual
                while t_samp < mid_time:
                    waveform.append((1.125 if cur_level else 0.0) + rng.gauss(0.0, noise_std_v))
                    t_samp += 1.0
                cur_level ^= 1
                while t_samp < end_time:
                    waveform.append((1.125 if cur_level else 0.0) + rng.gauss(0.0, noise_std_v))
                    t_samp += 1.0
            else:
                # Bit 0: Giu nguyen muc trong suot 1.0 UI
                end_time = cur_time + spu_actual
                while t_samp < end_time:
                    waveform.append((1.125 if cur_level else 0.0) + rng.gauss(0.0, noise_std_v))
                    t_samp += 1.0
            cur_time += spu_actual

        # Chuyen canh ket thuc sau EOP (chuan USB-PD Sec 5.7) de khoa canh bit cuoi cung
        cur_level ^= 1
        for _ in range(self.spu):
            waveform.append((1.125 if cur_level else 0.0) + rng.gauss(0.0, noise_std_v))
        return waveform

    def receive_and_recover_bits(self, waveform: List[float]) -> Tuple[List[int], float]:
        """Phat hien canh chuyen bang Hysteresis Comparator -> Uoc luong T_ui tu Preamble -> Giai BMC."""
        # 1. Schmitt-Trigger Comparator chong rung nhieu (High > 0.72V, Low < 0.40V)
        digital: List[int] = []
        state = 0
        for v in waveform:
            if state == 0 and v > 0.72:
                state = 1
            elif state == 1 and v < 0.40:
                state = 0
            digital.append(state)

        # 2. Do danh sach do rong cac xung giua hai canh chuyen lien tiep (tinh bang so mau)
        edges = [i for i in range(1, len(digital)) if digital[i] != digital[i - 1]]
        if len(edges) < 20:
            return [], 0.0
        pulse_widths = [float(edges[k + 1] - edges[k]) for k in range(len(edges) - 1)]

        # 3. Tu 16 xung dau cua Preamble (xen ke 1.0 UI va hai xung 0.5 UI -> trung binh 1.0 UI = 24 mau),
        # loc ra cac xung dai (bit 0 = 1.0 UI) de hieu chuan T_ui_est thich nghi!
        long_p = [w for w in pulse_widths[:24] if w > 0.75 * max(pulse_widths[:24])]
        ui_est = sum(long_p) / max(1, len(long_p))

        # 4. Giai ma BMC: 2 xung lien tiep ngan (< 0.75 * ui_est) -> Bit '1'; 1 xung dai -> Bit '0'
        bits_out: List[int] = []
        idx = 0
        while idx < len(pulse_widths):
            w = pulse_widths[idx]
            if w < 0.75 * ui_est:
                # Nua bit dau cua bit '1', kiem tra co nua bit thu 2 ke tiep khong
                if idx + 1 < len(pulse_widths) and pulse_widths[idx + 1] < 0.75 * ui_est:
                    bits_out.append(1)
                    # Cap nhat nhe ui_est theo tong 2 nua xung (Tracking clock drift)
                    ui_est = 0.9 * ui_est + 0.1 * (w + pulse_widths[idx + 1])
                    idx += 2
                else:
                    idx += 1
            else:
                bits_out.append(0)
                ui_est = 0.9 * ui_est + 0.1 * w
                idx += 1
        return bits_out, ui_est


def test_cc_detection_bmc_codec():
    """Chuong trinh kiem thu USB Type-C CC Detection + 4b5b + BMC 300 kbps CDR."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BO (NHOM 54) - BAI 212 (MILESTONE BO.1)")
    print("PHAT HIEN CAM CAP TYPE-C CC1/CC2 & THU PHAT BMC 300 KBPS + 4B5B")
    print("=" * 80)

    # 1. Kiem thu 3 tinh huong cam cap Type-C (Nguoc dau + Cap E-Marker 240W)
    print("\n[1] Kiem thu mach phan ap CC1/CC2 nhan dien huong cam & E-Marker VCONN:")
    st_flip_emarker = TypeCCCDetector.sense_cc_pins(r_p_ohm=10000.0, cc1_load_ohm=1000.0, cc2_load_ohm=5100.0)
    st_normal_plain = TypeCCCDetector.sense_cc_pins(r_p_ohm=22000.0, cc1_load_ohm=5100.0, cc2_load_ohm=float("inf"))
    st_unplugged = TypeCCCDetector.sense_cc_pins(r_p_ohm=10000.0, cc1_load_ohm=float("inf"), cc2_load_ohm=float("inf"))

    print(
        f"  * Cam nguoc + Cap E-Marker (10k): Orient={st_flip_emarker.orientation:13s} | "
        f"I_adv={st_flip_emarker.advertised_current_a:.1f}A | VCONN={st_flip_emarker.vconn_required} "
        f"(V1={st_flip_emarker.v_cc1:.2f}V, V2={st_flip_emarker.v_cc2:.2f}V)"
    )
    print(
        f"  * Cam thuan + Cap thuong  (22k): Orient={st_normal_plain.orientation:13s} | "
        f"I_adv={st_normal_plain.advertised_current_a:.1f}A | VCONN={st_normal_plain.vconn_required}"
    )
    print(f"  * Chua cam cap                 : Attached={st_unplugged.attached} | Orient={st_unplugged.orientation}")

    assert st_flip_emarker.attached and st_flip_emarker.orientation == "FLIPPED (CC2)" and st_flip_emarker.vconn_required
    assert st_flip_emarker.advertised_current_a == 3.0
    assert st_normal_plain.attached and st_normal_plain.orientation == "NORMAL (CC1)" and not st_normal_plain.vconn_required
    assert not st_unplugged.attached
    print("  -> Ket luan: Mach CC phan biet chinh xac huong cam, dong 3.0A va cap E-Marker (PASS)!")

    # 2. Kiem thu Thu phat BMC 300 kbps + 4b5b duoi sai lech thach anh +8.5% & nhieu 35 mV
    print("\n[2] Truyen khung tin 4b5b + BMC duoi lech xung nhip RC +8.5% & nhieu 35 mV rms:")
    payload_tx = [0xA1, 0x10, 0x2C, 0x91, 0x01, 0x4B, 0x3C, 0xDE, 0xAD, 0xBE]
    tx_bits = USBPD4b5bCodec.encode_frame_bits(payload_tx)
    bmc = AdaptiveBMCTransceiver(samples_per_nom_ui=24)

    wire_wave = bmc.transmit_waveform(tx_bits, tx_clock_drift_pct=+8.5, noise_std_v=0.035)
    rx_bits, ui_tracked = bmc.receive_and_recover_bits(wire_wave)
    decode_ok, payload_rx = USBPD4b5bCodec.decode_frame_bits(rx_bits)

    drift_tracked_pct = (ui_tracked / 24.0 - 1.0) * 100.0
    print(f"  * So bit truyen (kem Preamble+SOP+EOP): {len(tx_bits)} bits")
    print(f"  * Clock Drift thuc vs CDR do duoc     : +8.50% vs {drift_tracked_pct:+.2f}% (UI={ui_tracked:.2f} mau)")
    print(f"  * Giai ma 4b5b Payload (10 Bytes)     : Match={decode_ok and payload_rx == payload_tx} | RX={[hex(b) for b in payload_rx]}")

    assert decode_ok and payload_rx == payload_tx and abs(drift_tracked_pct - 8.5) < 1.0
    print("  -> Ket luan: CDR thich nghi giai ma sach 100% khung BMC duoi sai so tan so +8.5% (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 212: USB-C CC & BMC 300 KBPS CDR HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_cc_detection_bmc_codec()
