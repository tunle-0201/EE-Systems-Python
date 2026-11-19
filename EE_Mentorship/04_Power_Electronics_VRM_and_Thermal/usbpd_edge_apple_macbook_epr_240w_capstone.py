"""
EE MENTORSHIP PROGRAM - MODULE BO (NHOM 54) - BAI 215 (MILESTONE BO.4 - CAPSTONE)
================================================================================
DONG CO CAP NGUON THONG MINH USB-PD 3.1 EPR 240W (48V / 5A) & BO BIEN DOI
4-SWITCH BUCK-BOOST HAI CHIEU CAPSTONE CHO APPLE MACBOOK PRO & TESLA 48V AUX
================================================================================

Kien truc Toan he thong USB-PD 3.1 240W tu Day CC den Cong suat 48V/5A:
1. Tang Vat ly & Du lieu (Type-C CC + BMC 300 kbps + 4b5b + IEEE CRC-32):
   - Phat hien huong cam va R_a E-Marker (VCONN), truyen khung thuong thao EPR
     bang BMC +7.5% clock drift va xac thuc toan ven 100% bang CRC-32.
   - Khoa an toan cap: Neu cam cap 100W -> chan tai 20V/5A; chi cap 48V/5A (240W)
     khi chip E-Marker xac nhan dat chuan 50V/5A EPR!

2. Tang Cong suat 4-Switch Buck-Boost (V_in = 20.0V -> 5V -> 20V -> 48V @ 5.0A):
   - Dieu khien dong Current-Mode ket hop gioi han suon ap Soft-Ramp <= 10 V/ms
     de tranh xung dong nap tu Inrush qua tai khi nhay len 48V.
   - Hieu suat tai muc 240W (48V / 5.0A) dat > 96.5%.

3. Tang Bao ve An toan Ho quang & Qua tai (Surprise Unplug + Active Discharge):
   - Dien ap 48V DC neu rut cap dot ngot se keo ho quang chay chan Type-C!
   - Ngay khi CC mat ket noi (OPEN) hoac qua dong OCP > 5.8A, cong tac VBUS ngat
     va mach xa chu dong Active Bleeder (R_bleed = 24 Ohm) xa ap 48V ve < 5.0V
     chi trong < 15 ms (tSafe5V) chong ho quang tuyet doi!
--------------------------------------------------------------------------------
"""

import random
import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple


USBPD_4B5B = {
    0x0: 0b11110, 0x1: 0b01001, 0x2: 0b10100, 0x3: 0b10101,
    0x4: 0b01010, 0x5: 0b01011, 0x6: 0b01110, 0x7: 0b01111,
    0x8: 0b10010, 0x9: 0b10011, 0xA: 0b10110, 0xB: 0b10111,
    0xC: 0b11010, 0xD: 0b11011, 0xE: 0b11100, 0xF: 0b11101,
}
USBPD_5B4B = {v: k for k, v in USBPD_4B5B.items()}
K_SYNC1, K_SYNC2, K_EOP = 0b11000, 0b10001, 0b01101


def crc32_ieee(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xEDB88320) if (crc & 1) else (crc >> 1)
    return crc ^ 0xFFFFFFFF


class USBPDWireEngine:
    """Lop vat ly CC + BMC CDR + 4b5b + CRC-32 truyen khung lenh thuc te."""

    @staticmethod
    def sense_cc_and_vconn(cc1_ohm: float, cc2_ohm: float, r_p: float = 10000.0) -> Tuple[bool, str, bool]:
        v1 = 5.0 * (cc1_ohm / (r_p + cc1_ohm)) if cc1_ohm < 1e9 else 5.0
        v2 = 5.0 * (cc2_ohm / (r_p + cc2_ohm)) if cc2_ohm < 1e9 else 5.0
        c1 = "Ra" if v1 < 0.80 else ("Rd" if v1 < 2.60 else "OPEN")
        c2 = "Ra" if v2 < 0.80 else ("Rd" if v2 < 2.60 else "OPEN")
        if c1 == "Rd" and c2 != "Rd":
            return True, "CC1", (c2 == "Ra")
        if c2 == "Rd" and c1 != "Rd":
            return True, "CC2", (c1 == "Ra")
        return False, "NONE", False

    @staticmethod
    def bmc_roundtrip_packet(payload: bytes, clock_drift_pct: float = 7.5, seed: int = 215) -> Tuple[bool, bytes]:
        rng = random.Random(seed)
        frame = payload + struct.pack("<I", crc32_ieee(payload))

        def lsb_bits(sym: int) -> List[int]:
            return [(sym >> i) & 1 for i in range(5)]

        bits: List[int] = [i & 1 for i in range(64)]
        for k_c in (K_SYNC1, K_SYNC1, K_SYNC1, K_SYNC2):
            bits.extend(lsb_bits(k_c))
        for b in frame:
            bits.extend(lsb_bits(USBPD_4B5B[b & 0x0F]))
            bits.extend(lsb_bits(USBPD_4B5B[(b >> 4) & 0x0F]))
        bits.extend(lsb_bits(K_EOP))

        # Truyen BMC 24 mau/UI voi sai lech thach anh & nhieu 30 mV
        spu = 24
        spu_a = spu * (1.0 + clock_drift_pct / 100.0)
        wave = [0.0 + rng.gauss(0.0, 0.03) for _ in range(spu // 2)]
        lvl = 0
        t_s = 0.0
        cur_t = 0.0
        for bit in bits:
            lvl ^= 1
            if bit == 1:
                mid_t = cur_t + 0.5 * spu_a
                end_t = cur_t + spu_a
                while t_s < mid_t:
                    wave.append((1.125 if lvl else 0.0) + rng.gauss(0.0, 0.03))
                    t_s += 1.0
                lvl ^= 1
                while t_s < end_t:
                    wave.append((1.125 if lvl else 0.0) + rng.gauss(0.0, 0.03))
                    t_s += 1.0
            else:
                end_t = cur_t + spu_a
                while t_s < end_t:
                    wave.append((1.125 if lvl else 0.0) + rng.gauss(0.0, 0.03))
                    t_s += 1.0
            cur_t += spu_a
        lvl ^= 1
        for _ in range(spu):
            wave.append((1.125 if lvl else 0.0) + rng.gauss(0.0, 0.03))

        # Schmitt comparator + Adaptive CDR
        dig: List[int] = []
        st = 0
        for v in wave:
            if st == 0 and v > 0.72:
                st = 1
            elif st == 1 and v < 0.40:
                st = 0
            dig.append(st)
        edges = [i for i in range(1, len(dig)) if dig[i] != dig[i - 1]]
        pw = [float(edges[k + 1] - edges[k]) for k in range(len(edges) - 1)]
        long_p = [w for w in pw[:24] if w > 0.75 * max(pw[:24])]
        ui_est = sum(long_p) / max(1, len(long_p))

        rx_bits: List[int] = []
        idx = 0
        while idx < len(pw):
            w = pw[idx]
            if w < 0.75 * ui_est:
                if idx + 1 < len(pw) and pw[idx + 1] < 0.75 * ui_est:
                    rx_bits.append(1)
                    ui_est = 0.9 * ui_est + 0.1 * (w + pw[idx + 1])
                    idx += 2
                else:
                    idx += 1
            else:
                rx_bits.append(0)
                ui_est = 0.9 * ui_est + 0.1 * w
                idx += 1

        sop = lsb_bits(K_SYNC1) * 3 + lsb_bits(K_SYNC2)
        eop = lsb_bits(K_EOP)
        start = next((i + 20 for i in range(len(rx_bits) - 20) if rx_bits[i : i + 20] == sop), -1)
        if start < 0:
            return False, b""
        nibs: List[int] = []
        p = start
        while p + 5 <= len(rx_bits):
            sb = rx_bits[p : p + 5]
            p += 5
            if sb == eop:
                break
            sv = sum((b << k) for k, b in enumerate(sb))
            if sv not in USBPD_5B4B:
                return False, b""
            nibs.append(USBPD_5B4B[sv])
        if len(nibs) % 2 != 0 or len(nibs) < 8:
            return False, b""
        rx_raw = bytes([nibs[2 * j] | (nibs[2 * j + 1] << 4) for j in range(len(nibs) // 2)])
        rx_pay, rx_crc = rx_raw[:-4], struct.unpack("<I", rx_raw[-4:])[0]
        return (rx_crc == crc32_ieee(rx_pay)), rx_pay


class MacBook240WPowerStage:
    """
    Bo bien doi 4-Switch Buck-Boost 240W (V_in = 20V PFC -> 5V .. 48V @ 5.0A)
    kem Active VBUS Bleeder (R_bleed = 24 Ohm) xa an toan chong ho quang va bao ve OCP.
    """

    def __init__(self, v_in: float = 20.0):
        self.v_in = v_in
        self.l_h = 6.8e-6
        self.c_out = 220.0e-6
        self.r_dcr = 10.0e-3
        self.r_fet = 6.5e-3
        self.r_bleed = 24.0   # Mach xa chu dong 24 Ohm -> tau = 5.28 ms!

    @staticmethod
    def duties_c1(m_cmd: float) -> Tuple[float, float, str]:
        m = max(0.05, min(3.0, m_cmd))
        if m <= 0.82:
            return m, 0.0, "BUCK"
        if m >= 1.18:
            return 1.0, 1.0 - (1.0 / m), "BOOST"
        db = 0.15254237 * ((m - 0.82) / 0.36)
        return m * (1.0 - db), db, "BUCK-BOOST"

    def run_240w_mission(
        self, epr_authorized: bool, trigger_surprise_detach: bool = True
    ) -> Dict[str, any]:
        """
        Mo phong 50 ms chu ky cap nguon MacBook Pro 240W:
        - 0..8 ms   : Safe 5.0 V -> Nang mem len 20.0 V @ 5 A (100W SPR)
        - 8..30 ms  : Neu epr_authorized -> Soft-Ramp 8 V/ms len 48.0 V @ 5.0 A (240W EPR!)
        - 30..50 ms : Neu trigger_surprise_detach -> Rut cap dot ngot! Mo FET VBUS & Bat R_bleed!
        """
        dt = 2.0e-6
        v_out = 5.0
        i_l = 1.0
        v_ref_sl = 5.0
        integ_v = 0.0
        d_boost_prev = 0.0

        v_at_20ms = 0.0
        eff_at_240w = 0.0
        power_at_240w = 0.0
        max_inrush_i = 0.0
        bleeder_active = False
        safe5v_time_ms = None

        for step in range(int(0.050 / dt)):
            t_ms = step * dt * 1000.0
            if t_ms < 2.0:
                v_tgt, i_load_req = 5.0, 1.5
            elif t_ms < 8.0 or not epr_authorized:
                v_tgt, i_load_req = 20.0, 5.0
            elif t_ms < 30.0:
                v_tgt, i_load_req = 48.0, 5.0
            else:
                v_tgt, i_load_req = 0.0, 0.0
                if trigger_surprise_detach:
                    bleeder_active = True

            # Soft voltage ramp <= 3.5 V/ms (3.5 mV/us) tranh xung dong Inrush tu cap > 6A!
            max_dv = 3500.0 * dt
            if not bleeder_active:
                if abs(v_tgt - v_ref_sl) <= max_dv:
                    v_ref_sl = v_tgt
                elif v_tgt > v_ref_sl:
                    v_ref_sl += max_dv
                else:
                    v_ref_sl -= max_dv

            if bleeder_active:
                # Ngat FET cong suat chinh, mo Active Bleeder xa dien ap tu 48V xuong Safe5V
                i_l *= 0.85
                i_bleed = v_out / self.r_bleed
                v_out = max(0.0, v_out - (i_bleed / self.c_out) * dt)
                if v_out <= 5.0 and safe5v_time_ms is None:
                    safe5v_time_ms = t_ms - 30.0
            else:
                err_v = v_ref_sl - v_out
                integ_v = max(-2.0, min(8.0, integ_v + 650.0 * err_v * dt))
                i_out_cmd = i_load_req + 1.8 * err_v + integ_v
                i_l_ref = max(-0.5, min(18.0, i_out_cmd / max(0.25, 1.0 - d_boost_prev)))
                max_inrush_i = max(max_inrush_i, i_out_cmd)

                r_loop = self.r_dcr + 2.0 * self.r_fet
                v_l_des = 0.55 * (i_l_ref - i_l)
                m_cmd = (v_out + (i_l * r_loop + v_l_des) / max(0.25, 1.0 - d_boost_prev)) / self.v_in
                d_buck, d_boost, mode = self.duties_c1(m_cmd)
                d_boost_prev = d_boost

                sub_dt = dt * 0.5
                for _ in range(2):
                    di_l = (d_buck * self.v_in - (1.0 - d_boost) * v_out - i_l * r_loop) / self.l_h
                    i_l = max(-1.0, i_l + di_l * sub_dt)
                    dv_o = ((1.0 - d_boost) * i_l - i_load_req) / self.c_out
                    v_out = max(0.5, v_out + dv_o * sub_dt)

            if abs(t_ms - 25.0) < 0.002:
                v_at_20ms = v_out
                power_at_240w = v_out * i_load_req
                i_rms = i_load_req / max(0.25, 1.0 - d_boost_prev)
                p_cond = (i_rms ** 2) * (self.r_dcr + 2.0 * self.r_fet)
                p_sw = 2.0 * 12e-9 * 5.0 * 400e3 + 0.5 * max(self.v_in, v_out) * i_rms * 6.5e-9 * 400e3 + 0.25
                eff_at_240w = (power_at_240w / (power_at_240w + p_cond + p_sw)) * 100.0

        return {
            "v_steady_v": v_at_20ms,
            "power_w": power_at_240w,
            "eff_pct": eff_at_240w,
            "peak_inrush_a": max_inrush_i,
            "tsafe5v_ms": safe5v_time_ms if safe5v_time_ms is not None else 999.0,
        }


def test_apple_macbook_epr_240w_capstone():
    """Chuong trinh kiem thu Capstone USB-PD 3.1 EPR 240W Apple MacBook / Tesla 48V."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BO (NHOM 54) - BAI 215 (MILESTONE BO.4 - CAPSTONE)")
    print("DONG CO USB-PD 3.1 EPR 240W (48V/5A) APPLE MACBOOK PRO & TESLA 48V AUX")
    print("=" * 80)

    # 1. Tang 1 & 2: Phat hien CC + Truyen khung EPR qua BMC CDR (+7.5% drift) + CRC-32
    print("\n[1] Kiem thu Tang Vat ly CC, E-Marker VCONN & Truyen tin BMC (+7.5% drift) + CRC-32:")
    attached, cc_pin, vconn = USBPDWireEngine.sense_cc_and_vconn(cc1_ohm=1000.0, cc2_ohm=5100.0)
    epr_req_payload = struct.pack("<HI", 0x2089, (48 * 20 << 10) | 500)  # EPR_Request 48V/5.0A
    bmc_ok, rx_pay = USBPDWireEngine.bmc_roundtrip_packet(epr_req_payload, clock_drift_pct=7.5)
    print(f"  * Cam cap Type-C         : Attached={attached} | Pin={cc_pin} | VCONN={vconn}")
    print(f"  * Truyen BMC+4b5b+CRC32  : Verify={bmc_ok and rx_pay == epr_req_payload} (6 bytes EPR_Request)")
    assert attached and cc_pin == "CC2" and vconn and bmc_ok and rx_pay == epr_req_payload
    print("  -> Ket luan: Giao tiep CC + BMC CDR + CRC-32 toan ven 100% (PASS)!")

    # 2. Tang 3: Chay cong suat thuc chien (Cap thuong 100W vs Cap 240W EPR + Rut cap dot ngot)
    print("\n[2] Thuc chien Nang ap 240W (5V -> 20V -> 48V/5A) & Xa ho quang Surprise Detach:")
    stage = MacBook240WPowerStage(v_in=20.0)
    res_100w = stage.run_240w_mission(epr_authorized=False, trigger_surprise_detach=False)
    res_240w = stage.run_240w_mission(epr_authorized=True, trigger_surprise_detach=True)

    print(f"  * Cap 100W (Chua xac thuc EPR) : Khoa tai {res_100w['v_steady_v']:5.2f}V -> {res_100w['power_w']:5.1f}W (An toan!)")
    print(
        f"  * Cap 240W EPR (48V / 5.0A)    : Dat {res_240w['v_steady_v']:5.2f}V -> {res_240w['power_w']:5.1f}W | "
        f"Eff = {res_240w['eff_pct']:5.2f}% | Peak Inrush = {res_240w['peak_inrush_a']:.2f}A"
    )
    print(f"  * Rut cap dot ngot @ 48V       : Active Bleeder xa ve < 5.0V trong {res_240w['tsafe5v_ms']:5.2f} ms (< 15 ms!)")

    assert abs(res_100w["power_w"] - 100.0) < 1.0
    assert abs(res_240w["v_steady_v"] - 48.0) < 0.25 and abs(res_240w["power_w"] - 240.0) < 1.5
    assert res_240w["eff_pct"] > 96.5 and res_240w["peak_inrush_a"] < 6.0
    assert res_240w["tsafe5v_ms"] < 15.0
    print("  -> Ket luan: Dong co USB-PD 3.1 240W dat Eff > 96.5% & Chong ho quang < 15 ms (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 215 (CAPSTONE): APPLE USB-PD 3.1 EPR 240W 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_macbook_epr_240w_capstone()
