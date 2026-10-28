"""
Chuyen de AT: Mach Tin hieu Hon hop Mixed-Signal & Bo chuyen doi ADC/DAC Toc do cao
Bai 129 (Milestone AT.2): Kien truc bo chuyen doi SAR ADC va duong ong Pipeline MDAC 1.5-bit

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Hieu ro nguyen ly chuyen doi A/D tu cap do phan cung: Mang tu phan bo dien tich CDAC,
          thuat toan tim kiem nhi phan Binary Search trong SAR ADC va ky thuat sua loi so
          Digital Error Correction (DEC) trong Pipeline ADC toc do cao.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class CapacitiveSARADC:
    """
    Mo hinh bo chuyen doi ADC xap xi lien tiep (SAR ADC) dung mang tu nhan doi CDAC.
    
    Phan tich toan hoc & vat ly phan cung:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Mang tu nhan doi: C_k = 2^k * C_unit                 │
    │   Tong dien dung:   C_total = 2^N * C_unit             │
    │                                                        │
    │   Giai doan 1 (Lay mau): Q = -C_total * V_in           │
    │                                                        │
    │   Giai doan 2 (Chuyen doi N chu ky Clock):             │
    │                                                        │
    │                  N-1                                   │
    │                  ───   b_k * 2^k                       │
    │   V_DAC(b) = V_ref * ─── ─────────                     │
    │                  k=0      2^N                          │
    │                                                        │
    │   Dien ap nut so sanh: V_comp = V_DAC - V_in           │
    │                                                        │
    │   Neu V_in >= V_DAC => Bit thu i giu nguyen 1          │
    │   Neu V_in <  V_DAC => Bit thu i dat ve 0              │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        num_bits: int = 12,
        v_ref: float = 1.0,
        c_unit_femtofarad: float = 2.0,
        comparator_offset_mv: float = 0.0,
        cap_mismatch_sigma_pct: float = 0.0
    ):
        if num_bits < 2 or num_bits > 16:
            raise ValueError("So bit SAR ADC ho tro tu 2 den 16 bits")
        self.num_bits = num_bits
        self.v_ref = float(v_ref)
        self.c_unit = c_unit_femtofarad * 1e-15
        self.comp_offset = comparator_offset_mv * 1e-3
        self.num_levels = 1 << num_bits
        self.delta = self.v_ref / self.num_levels

        # Khoi tao gia tri dien dung tung bit kem dung sai mismatch neu co
        self.c_array: List[float] = []
        for i in range(num_bits):
            nominal_c = (1 << i) * self.c_unit
            # Mo hinh mismatch dien dung nhe neu co
            mismatch = 1.0 + (cap_mismatch_sigma_pct / 100.0) * math.sin(i * 1.7)
            self.c_array.append(nominal_c * mismatch)
        
        # Tu ket thuc termination dummy capacitor
        self.c_array.append(self.c_unit)
        self.total_capacitance = sum(self.c_array)

    def convert_single_sample(self, v_in: float) -> Tuple[int, List[int], List[float]]:
        """
        Thuc hien chuyen doi xap xi lien tiep qua N chu ky clock.
        Tra ve (ma_so_nguyen, lich_su_bit, lich_su_dien_ap_vdac).
        """
        # Gioi han tin hieu trong dai [0, V_ref]
        v_clamped = max(0.0, min(self.v_ref - 1e-9, v_in))
        
        current_code = 0
        bit_history: List[int] = []
        vdac_history: List[float] = []

        # Thuat toan tim kiem nhi phan tu MSB (bit num_bits - 1) xuong LSB (bit 0)
        for bit_idx in range(self.num_bits - 1, -1, -1):
            # Thu bat bit hien tai len 1
            test_code = current_code | (1 << bit_idx)
            
            # Tinh dien ap phan chia cua CDAC tu dien dung thuc te
            v_dac_test = self._calculate_cdac_voltage(test_code)
            vdac_history.append(v_dac_test)

            # So sanh voi tin hieu vao (kem offset cua comparator)
            # Comparator: output = 1 neu (v_clamped - v_dac_test + comp_offset) >= 0
            if (v_clamped - v_dac_test + self.comp_offset) >= 0.0:
                current_code = test_code
                bit_history.append(1)
            else:
                bit_history.append(0)

        return current_code, bit_history, vdac_history

    def _calculate_cdac_voltage(self, code: int) -> float:
        """Tinh dien ap dau ra cua CDAC dua tren ma nhi phan va dien dung thuc te."""
        switched_charge = 0.0
        for i in range(self.num_bits):
            if (code >> i) & 1:
                switched_charge += self.c_array[i] * self.v_ref
        return switched_charge / self.total_capacitance


class PipelineStage1p5Bit:
    """
    Giai doan duong ong 1.5-bit cua Pipeline ADC (Sub-ADC 2 nguong, Sub-DAC va MDAC khuech dai phan du).
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Nguong so sanh: -V_ref / 4  va  +V_ref / 4           │
    │                                                        │
    │   V_in < -V_ref / 4:       Sub-Code = 0  => V_DAC = -V_ref/2
    │   -V_ref/4 <= V_in <= +V_ref/4: Sub-Code = 1  => V_DAC = 0
    │   V_in > +V_ref / 4:       Sub-Code = 2  => V_DAC = +V_ref/2
    │                                                        │
    │   Dien ap phan du MDAC:                                │
    │   V_residue = 2 * (V_in - V_DAC)                       │
    │                                                        │
    │   V_residue luon bi khoa chat trong [-V_ref/2, +V_ref/2]
    │   => Cho phep sai so comparator toi +/- V_ref/4 ma     │
    │      van duoc sua hoan toan boi Digital Correction!    │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, v_ref: float = 1.0, stage_gain: float = 2.0):
        self.v_ref = float(v_ref)
        self.gain = float(stage_gain)
        self.threshold_low = -self.v_ref / 4.0
        self.threshold_high = self.v_ref / 4.0

    def process_stage(self, v_in: float) -> Tuple[int, float]:
        """
        Xu ly 1 stage: Tra ve (sub_code [0, 1, 2], v_residue).
        v_in nam trong [-V_ref/2, +V_ref/2].
        """
        if v_in < self.threshold_low:
            sub_code = 0
            v_dac = -self.v_ref / 2.0
        elif v_in > self.threshold_high:
            sub_code = 2
            v_dac = self.v_ref / 2.0
        else:
            sub_code = 1
            v_dac = 0.0

        v_residue = self.gain * (v_in - v_dac)
        return sub_code, v_residue


class PipelineADCEngine:
    """
    Dong co Pipeline ADC N-stage hoan chinh voi khoi sua loi so Digital Error Correction (DEC).
    Thong luong (Throughput) dat 1 mau/chu ky sau do tre N chu ky.
    """
    def __init__(self, num_stages: int = 10, v_ref: float = 1.0):
        self.num_stages = num_stages
        self.v_ref = float(v_ref)
        self.stages = [PipelineStage1p5Bit(v_ref=v_ref, stage_gain=2.0) for _ in range(num_stages)]

    def convert_sample(self, v_in: float) -> Tuple[int, List[int], List[float]]:
        """
        Chuyen doi tin hieu vi sai v_in trong dai [-V_ref/2, +V_ref/2].
        Tra ve (final_digital_code, stage_codes, residue_voltages).
        """
        # Gioi han dien ap dau vao
        v_current = max(-self.v_ref / 2.0, min(self.v_ref / 2.0, v_in))
        
        stage_codes: List[int] = []
        residues: List[float] = []

        for stage in self.stages:
            code_i, v_res = stage.process_stage(v_current)
            stage_codes.append(code_i)
            residues.append(v_res)
            v_current = v_res

        # Khoi Digital Error Correction (DEC):
        # Tich luy trong so bang thuat toan shift-and-add
        digital_output = 0
        for code in stage_codes:
            # Shift 1 bit va cong sub_code
            digital_output = (digital_output << 1) + code

        return digital_output, stage_codes, residues


def test_sar_and_pipeline_adc():
    print("================================================================================")
    print("TEST SUITE: KIEN TRUC SAR ADC VA PIPELINE ADC 1.5-BIT VOI DEC")
    print("================================================================================")

    # 1. Kiem tra SAR ADC 10-bit ly tuong
    v_ref = 1.0
    sar_10b = CapacitiveSARADC(num_bits=10, v_ref=v_ref, c_unit_femtofarad=2.0)
    print(f"[1] Khoi tao SAR ADC 10-bit: V_ref={v_ref}V | Delta={sar_10b.delta*1000:.3f} mV")
    print(f"    Tong dien dung mang tu CDAC: {sar_10b.total_capacitance * 1e12:.3f} pF")

    # Thu chuyen doi muc dien ap v_test = 0.625 V (chinh xac 5/8 V_ref = 0b1010000000 = 640)
    v_test = 0.625
    code, bit_hist, vdac_hist = sar_10b.convert_single_sample(v_test)
    expected_code = int(round(v_test / sar_10b.delta))
    print(f"    Chuyen doi v_in={v_test}V -> Code={code} (Ky vong={expected_code})")
    print(f"    Tien trinh ra quyet dinh bit: {bit_hist}")
    assert abs(code - expected_code) <= 1, f"Loi code SAR: thuc te={code}, ky vong={expected_code}"
    assert len(bit_hist) == 10, "SAR ADC 10-bit phai hoan thanh trong 10 chu ky"

    # 2. Kiem tra tinh tuyen tinh tuyet doi cua SAR ADC tren toan dai
    test_voltages = [i * 0.1 for i in range(10)]
    codes = [sar_10b.convert_single_sample(v)[0] for v in test_voltages]
    # Kiem tra tinh don dieu nghiem ngat
    for idx in range(len(codes) - 1):
        assert codes[idx + 1] > codes[idx], "SAR ADC bi mat tinh don dieu"
    print(f"[2] Kiem tra tinh don dieu SAR ADC: 10 diem dien ap deu tang tuyen tinh thanh cong")

    # 3. Kiem tra Pipeline ADC 1.5-bit/stage
    pipe_adc = PipelineADCEngine(num_stages=8, v_ref=1.0)
    print(f"\n[3] Khoi tao Pipeline ADC 8-stage (1.5-bit per stage voi MDAC gain=2.0):")

    # Thu nghiem chuyen doi tin hieu vi sai
    v_pipe_in = 0.1875  # 3/16 V
    pipe_code, stage_codes, residues = pipe_adc.convert_sample(v_pipe_in)
    print(f"    V_in vi sai = {v_pipe_in} V")
    print(f"    Ma giai doan Sub-ADC (0, 1, 2): {stage_codes}")
    print(f"    Dien ap phan du qua cac stage (mV): {[round(r*1000, 2) for r in residues]}")
    print(f"    Tong hop ma so DEC: {pipe_code}")

    # Kiem tra dien ap phan du khong bao gio bi tran vuot ngoai [-V_ref/2, +V_ref/2]
    for r in residues:
        assert abs(r) <= 0.5001, f"Residue vuot nguong MDAC: {r}"
    print("    -> Dien ap phan du tat ca cac stage duoc kiem soat on dinh trong [-0.5V, +0.5V]")

    # 4. So sanh hieu nang kien truc:
    # SAR: Tieu thu cong suat cuc thap, thich hop cho cam bien Sensor Hub Apple AirPods / Tesla IMU
    # Pipeline: Bang thong sieu cao GSPS, thich hop cho Radar FMCW Tesla va SDR Starlink
    print("\n[4] Kiem tra dac tinh so sanh kien truc:")
    print("    - SAR ADC: Do tre N chu ky / 1 mau chuyen doi, dien dung nho, cong suat duoi 1 mW.")
    print("    - Pipeline ADC: Do tre N chu ky ban dau, thong luong 1 mau / 1 chu ky, toc do dat hang tram MSPS.")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AT.2 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_sar_and_pipeline_adc()
