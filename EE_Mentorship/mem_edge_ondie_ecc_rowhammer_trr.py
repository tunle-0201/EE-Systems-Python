"""
EE MENTORSHIP PROGRAM - MODULE BG (NHOM 46) - BAI 182 (MILESTONE BG.3)
================================================================================
MA SUA SAI ON-DIE ECC SECDED VA CO CHE PHONG THU TARGET ROW REFRESH CHONG ROWHAMMER
================================================================================

Kien truc an toan va do tin cay bo nho DRAM the he moi (LPDDR5X / DDR5 / HBM3e):
1. Ma sua sai tren chip On-Die ECC (SECDED Hamming Code 64/72-bit):
   - Khi tien trinh ban dan thu nho xuong duoi 12nm, dung luong tu dien nho hon 10 femto-Farad
     (chi chua vai chuc ngan electron). Nhieu nhiet va tia hat vu tru gay lat bit (Soft Errors).
   - Chuan JEDEC LPDDR5X/DDR5 bat buoc tich hop On-Die ECC (Single Error Correction,
     Double Error Detection) ngay ben trong die DRAM:
     * Du lieu: 64 bit data.
     * Ma parity: 8 bit kiem tra chan le (Check Bits).
     * Phat hien va tu dong sua loi 1-bit truoc khi truyen ra ngoai bus DQs.
     * Phat hien va bao dong loi 2-bit khong the sua (Uncorrectable Error).

2. Hien tuong va co che tan cong vat ly Rowhammer (Rowhammer Physics):
   - Khi mot "Hang Tan Cong" (Aggressor Row) bi kich hoat dong/mo lien tuc voi tan so cao
     (vi du 50,000 lan trong mot chu ky refresh tREFI).
   - Dien dung ky sinh (Parasitic Capacitance) va dong ro dien tich gay mat dien tich
     tren cac "Hang Nan Nhan" lien ke (Victim Rows: Aggressor - 1 va Aggressor + 1).
   - Dien ap tu dien cua hang nan nhan tut xuong duoi nguong V_crit lam lat bit trong RAM,
     pha vo co che bao ve phan quyen bo nho cua he dieu hanh!

3. Co che phong thu phan cung Target Row Refresh (TRR Defense):
   - Bo dieu khien bo nho tich hop Bang theo doi kich hoat hang (Leaky-Bucket Row Tracker).
   - Khi so lan kich hoat cua mot hang vuot qua nguong an toan (Hammer Threshold),
     bo dieu khien lap tuc phat lenh Target Row Refresh (TRR) de nap lai 100% dien tich
     cho 2 hang nan nhan lien ke truoc khi bi suy hao dien tich gay lat bit.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Tinh toan Vector Hoi chung loi (Syndrome Vector):
     S[i] = P_recalculated[i] XOR P_received[i]

2. Phan loai loi SECDED (Parity Check):
     Truong hop 0 loi  : S == 0  va  P_overall == 0
     Loi 1-bit sua duoc : S != 0  va  P_overall == 1  (S chi dung vi tri bit loi)
     Loi 2-bit khong sua: S != 0  va  P_overall == 0  (Bao dong Uncorrectable Error)

3. Mo hinh ro dien tich tu dien Rowhammer (Capacitor Discharge Model):
     Q(t) = Q_0 * (1 - hammer_count * coupling_leakage_factor)
     Bit flip xay ra khi: Q(t) < Q_threshold
--------------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import random


class OnDieECCEngine:
    """
    Dong co ma hoa va giai ma On-Die ECC SECDED (64-bit Data + 8-bit Parity = 72-bit Code).
    Kien truc chuan JEDEC DDR5 va LPDDR5X.
    """
    def __init__(self):
        self.data_bits = 64
        self.parity_bits = 7   # 7 parity bits cho Hamming code (2^7 = 128 > 64 + 7 + 1)
        self.total_bits = 72   # 64 data + 7 hamming + 1 overall parity = 72 bits
        
        # Xay dung ma tran kiem tra chan le Hamming (Hamming Parity Check Matrix)
        # Moi vi tri du lieu tu 0 den 63 duoc anh xa vao cac bit parity p0..p6
        self.parity_masks = self._generate_parity_masks()

    def _generate_parity_masks(self) -> List[int]:
        """Sinh mat na bitmask cho 7 bit parity theo ma tran Hamming."""
        masks = [0] * self.parity_bits
        # Cac so tu 1 den 71 ma khong phai luy thua cua 2 la cac vi tri du lieu
        data_idx = 0
        for pos in range(1, 128):
            if (pos & (pos - 1)) == 0:
                continue  # Day la vi tri cua parity bit
            if data_idx < self.data_bits:
                for p in range(self.parity_bits):
                    if (pos >> p) & 1:
                        masks[p] |= (1 << data_idx)
                data_idx += 1
        return masks

    def encode(self, data_64bit: int) -> int:
        """
        Ma hoa 64-bit data thanh tu ma 72-bit (Data 64 + Hamming 7 + Overall Parity 1).
        Tra ve so nguyen 72-bit.
        """
        # 1. Tinh 7 bit parity Hamming
        p_bits = 0
        for p in range(self.parity_bits):
            masked = data_64bit & self.parity_masks[p]
            bit_val = bin(masked).count("1") % 2
            p_bits |= (bit_val << p)

        # 2. Tinh Overall Parity (Bit 71) de ho tro DED (Double Error Detection)
        combined_71 = (p_bits << 64) | data_64bit
        overall_parity = bin(combined_71).count("1") % 2

        code_72bit = (overall_parity << 71) | (p_bits << 64) | data_64bit
        return code_72bit

    def decode(self, received_72bit: int) -> Tuple[int, str, Optional[int]]:
        """
        Giai ma va sua loi tu ma 72-bit nhan duoc:
        Tra ve: (corrected_data_64bit, status_string, flipped_bit_index)
        status_string thuoc: ["NO_ERROR", "CORRECTED_SINGLE_BIT", "UNCORRECTABLE_DOUBLE_BIT"]
        """
        data_part = received_72bit & ((1 << 64) - 1)
        p_received = (received_72bit >> 64) & ((1 << 7) - 1)
        overall_received = (received_72bit >> 71) & 1

        # 1. Tinh lai 7 parity bits tu data_part
        p_recalculated = 0
        for p in range(self.parity_bits):
            masked = data_part & self.parity_masks[p]
            bit_val = bin(masked).count("1") % 2
            p_recalculated |= (bit_val << p)

        syndrome = p_recalculated ^ p_received

        # 2. Tinh toan overall parity thuc te
        combined_71 = (p_received << 64) | data_part
        overall_recalc = bin(combined_71).count("1") % 2
        overall_error = overall_recalc ^ overall_received

        # 3. Phan loai loi SECDED
        if syndrome == 0 and overall_error == 0:
            return data_part, "NO_ERROR", None

        elif syndrome != 0 and overall_error != 0:
            # Loi 1-bit sua duoc (Single Bit Error)!
            # Tim vi tri bit data bi lat
            corrected_data = data_part
            error_data_idx = None
            
            # Kiem tra xem syndrome co trung voi vi tri data nao khong
            data_idx = 0
            for pos in range(1, 128):
                if (pos & (pos - 1)) == 0:
                    continue
                if data_idx < self.data_bits:
                    if pos == syndrome:
                        error_data_idx = data_idx
                        # Lat lai bit dung
                        corrected_data ^= (1 << data_idx)
                        break
                    data_idx += 1

            return corrected_data, "CORRECTED_SINGLE_BIT", error_data_idx

        elif syndrome != 0 and overall_error == 0:
            # Loi 2-bit khong the sua (Double Bit Error)!
            return data_part, "UNCORRECTABLE_DOUBLE_BIT", None

        else:
            # Loi lat bit o chinh bit overall parity
            return data_part, "CORRECTED_PARITY_BIT", 71


@dataclass
class DRAMRowState:
    """Trang thai dien tich va du lieu cua mot hang DRAM."""
    row_id: int
    data_value: int = 0xAAAAAAAAAAAAAAAA  # Du lieu 64-bit mac dinh
    charge_level: float = 1.0             # 1.0 = 100% dien tich (Vdd)
    activation_count: int = 0             # So lan bi kich hoat trong chu ky


class RowhammerTRRDefenseSubsystem:
    """
    Subsystem mo phong hien tuong vat ly Rowhammer va co che phong thu Target Row Refresh (TRR).
    Quan ly bo dem ro ri Leaky-Bucket de phat hien som Aggressor Row.
    """
    def __init__(self, num_rows: int = 1024, hammer_threshold: int = 1500, leakage_per_hammer: float = 0.0006):
        self.num_rows = num_rows
        self.hammer_threshold = hammer_threshold
        self.leakage_per_hammer = leakage_per_hammer
        self.critical_voltage_threshold = 0.40  # Duoi 40% dien tich -> LAT BIT!
        
        # Bang luu trang thai cac hang
        self.rows: Dict[int, DRAMRowState] = {r: DRAMRowState(row_id=r) for r in range(num_rows)}
        
        # Bang theo doi phan cung Leaky-Bucket Counter (TRR Hardware Table)
        self.trr_activation_table: Dict[int, int] = {}
        self.total_trr_refreshes_issued: int = 0

    def activate_row(self, row_id: int, enable_trr_defense: bool = True) -> Dict[str, any]:
        """
        Kich hoat 1 hang (Aggressor Row).
        Gay ro dien tich len 2 hang nan nhan lien ke (row_id - 1 va row_id + 1).
        Neu bat TRR, tu dong kich hoat lam tuoi khi vuot nguong an toan.
        """
        r = self.rows[row_id]
        r.activation_count += 1
        
        # Cap nhat bo dem Leaky-Bucket
        self.trr_activation_table[row_id] = self.trr_activation_table.get(row_id, 0) + 1

        # Ro ri dien tich len cac hang nan nhan
        victim_rows = []
        if row_id > 0:
            victim_rows.append(row_id - 1)
        if row_id < self.num_rows - 1:
            victim_rows.append(row_id + 1)

        bit_flip_occurred = False
        flipped_rows = []

        for v_id in victim_rows:
            v_row = self.rows[v_id]
            # Ro ri dien dung ky sinh
            v_row.charge_level -= self.leakage_per_hammer
            if v_row.charge_level < self.critical_voltage_threshold:
                # Dien tich tut duoi nguong an toan -> XAY RA LAT BIT!
                bit_flip_occurred = True
                # Lat bit thu 5 cua hang nan nhan
                v_row.data_value ^= (1 << 5)
                flipped_rows.append(v_id)

        trr_triggered = False
        # Co che phong thu Target Row Refresh (TRR)
        if enable_trr_defense:
            if self.trr_activation_table[row_id] >= self.hammer_threshold:
                # Kich hoat TRR: Nap lai 100% dien tich cho cac hang nan nhan
                for v_id in victim_rows:
                    self.rows[v_id].charge_level = 1.0  # Phuc hoi day du
                self.trr_activation_table[row_id] = 0  # Reset bo dem
                self.total_trr_refreshes_issued += 1
                trr_triggered = True

        return {
            "aggressor_row": row_id,
            "activation_count": r.activation_count,
            "trr_triggered": trr_triggered,
            "bit_flip_occurred": bit_flip_occurred,
            "flipped_rows": flipped_rows
        }


def test_ondie_ecc_and_rowhammer_trr():
    """Kiem thu toan dien ma sua sai On-Die ECC va phong thu Rowhammer TRR."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BG (NHOM 46) - BAI 182 (MILESTONE BG.3)")
    print("MA SUA SAI ON-DIE ECC SECDED VA PHONG THU TARGET ROW REFRESH (TRR)")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # PHAN 1: Kiem thu Dong co Ma hoa & Giai ma On-Die ECC SECDED
    # --------------------------------------------------------------------------
    print("\n[PHAN 1] Kiem thu On-Die ECC SECDED (64-bit Data + 8-bit Parity):")
    ecc = OnDieECCEngine()

    original_data = 0xDEADBEEFCAFE1234
    encoded_code = ecc.encode(original_data)
    print(f"  * Du lieu goc (64-bit)         : 0x{original_data:016X}")
    print(f"  * Tu ma da ma hoa (72-bit Code): 0x{encoded_code:018X}")

    # 1.1 Kiem tra du lieu sach khong loi
    dec_data, status, bit_idx = ecc.decode(encoded_code)
    print(f"  * [1.1 Du lieu sach]: Trang thai = {status} | Du lieu = 0x{dec_data:016X}")
    assert status == "NO_ERROR" and dec_data == original_data, "Loi: Giai ma du lieu sach that bai!"

    # 1.2 Kiem tra va sua loi 1-bit (Single-Bit Flip)
    test_flip_bit = 19
    corrupted_1bit = encoded_code ^ (1 << test_flip_bit)
    dec_data_1b, status_1b, corrected_bit = ecc.decode(corrupted_1bit)
    print(f"  * [1.2 Lat bit #{test_flip_bit:2d}]: Trang thai = {status_1b} | Bit sua = #{corrected_bit}")
    print(f"    - Du lieu sau khi tu dong sua: 0x{dec_data_1b:016X}")
    assert status_1b == "CORRECTED_SINGLE_BIT", "Loi: Khong nhan dien duoc loi 1-bit!"
    assert corrected_bit == test_flip_bit, f"Loi: Vi tri bit sua sai ({corrected_bit} != {test_flip_bit})!"
    assert dec_data_1b == original_data, "Loi: Du lieu phuc hoi khong khop voi du lieu goc!"
    print("    -> Ket luan: On-Die ECC phat hien va tu dong sua dung 100% bit loi!")

    # 1.3 Kiem tra va bao dong loi 2-bit (Double-Bit Error Detection)
    corrupted_2bit = encoded_code ^ (1 << 12) ^ (1 << 45)
    dec_data_2b, status_2b, _ = ecc.decode(corrupted_2bit)
    print(f"  * [1.3 Lat 2 bit dong thoi (#12 va #45)]: Trang thai = {status_2b}")
    assert status_2b == "UNCORRECTABLE_DOUBLE_BIT", "Loi: Khong bao dong loi 2-bit!"
    print("    -> Ket luan: He thong phat hien thanh cong loi 2-bit khong the sua (DED Pass)!")

    # --------------------------------------------------------------------------
    # PHAN 2: Kiem thu Tan cong vat ly Rowhammer va Co che phong thu TRR
    # --------------------------------------------------------------------------
    print("\n[PHAN 2] Mo phong tan cong Rowhammer va Kich hoat phong thu Target Row Refresh:")
    aggressor = 512
    victim = 511

    # 2.1 Kich ban KHONG CO PHONG THU TRR (DRAM truyen thong bi lat bit)
    print("  * [Kich ban A]: Tan cong 2,500 lan vao Hang 512 khi TAT phong thu TRR:")
    dram_no_trr = RowhammerTRRDefenseSubsystem(num_rows=1024, hammer_threshold=1000)
    flip_detected = False
    for step in range(2500):
        res = dram_no_trr.activate_row(aggressor, enable_trr_defense=False)
        if res["bit_flip_occurred"]:
            flip_detected = True
            print(f"    -> [NGUY HIEM]: Tai lan kich hoat thu {step + 1}, Hang nan nhan {victim} da BI LAT BIT!")
            print(f"       Dien tich con lai: {dram_no_trr.rows[victim].charge_level * 100:.1f}% (Duoi nguong an toan 40%)")
            break

    assert flip_detected, "Kiem tra: Tan cong Rowhammer phai lam lat bit khi khong co TRR!"

    # 2.2 Kich ban CO PHONG THU TARGET ROW REFRESH (TRR) BAT
    print("\n  * [Kich ban B]: Tan cong 2,500 lan vao Hang 512 khi BAT phong thu TRR (Nguong an toan 800):")
    dram_with_trr = RowhammerTRRDefenseSubsystem(num_rows=1024, hammer_threshold=800)
    flip_occurred_with_trr = False
    for step in range(2500):
        res = dram_with_trr.activate_row(aggressor, enable_trr_defense=True)
        if res["bit_flip_occurred"]:
            flip_occurred_with_trr = True
            break

    print(f"    - Tong so lan bo dieu phoi kich hoat TRR lam tuoi: {dram_with_trr.total_trr_refreshes_issued} lan")
    print(f"    - Dien tich hang nan nhan {victim} hien tai       : {dram_with_trr.rows[victim].charge_level * 100:.1f}%")
    print(f"    - Co bat ky bit nao bi lat khong                 : {flip_occurred_with_trr}")
    assert not flip_occurred_with_trr, "Loi: TRR da bat ma van de xay ra lat bit Rowhammer!"
    print("    -> Ket luan: Co che Target Row Refresh triet tieu 100% nguy co tan cong Rowhammer!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 182: ON-DIE ECC VA TRR HOAN TAT KIEM THU XUAT SAC (PASS)")
    print("=" * 80)


if __name__ == "__main__":
    test_ondie_ecc_and_rowhammer_trr()
