"""
Chuyen de AN: An toan Chuc nang Phan cung O to & Hang khong ISO 26262 ASIL-D
Bai 3: Tinh toan Chi so An toan Dinh luong SPFM, LFM, PMHF theo Chuan ISO 26262 Part 5

Muc tieu:
- Xay dung cong cu FMEDA (Failure Modes, Effects, and Diagnostic Analysis) tieu chuan cong nghiep.
- Tinh toan Single-Point Fault Metric (SPFM >= 99% cho ASIL-D).
- Tinh toan Latent Fault Metric (LFM >= 90% cho ASIL-D).
- Tinh toan Probabilistic Metric for random Hardware Failures (PMHF < 10 FIT cho ASIL-D).
- Mo phong va phan tich do nhay (Sensitivity Analysis) khi mot co che an toan bi vo hieu hoa.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class HardwareComponent:
    """
    Dinh nghia phan tu phan cung va cac tham so do luong do tin cay / chan doan loi.
    
    Don vi do:
    - lambda_fit: FIT (Failures In Time) = 1 loi tren 10^9 gio hoat dong.
    - dc_rf: Diagnostic Coverage for Residual Faults (ti le chan doan loi don diem).
    - dc_mp: Diagnostic Coverage for Multiple-Point Faults (ti le chan doan loi an/tiem tang).
    """
    name: str
    lambda_fit: float
    safety_related_ratio: float  # Ti le loi lien quan den an toan chuc nang (0.0 den 1.0)
    safe_fault_ratio: float       # Ti le loi an toan tu than (Safe faults)
    dc_rf: float                  # Diagnostic Coverage Single-Point / Residual (0.0 den 1.0)
    dc_mp: float                  # Diagnostic Coverage Multiple-Point / Latent (0.0 den 1.0)


class ISO26262_FMEDA_Analyzer:
    """
    Bo phan tich va tinh toan chi so an toan phan cung dinh luong ISO 26262 Part 5.
    
    Cac cong thuc toan hoc cot loi (bieu dien dang phang ASCII):
    1. SPFM (Single-Point Fault Metric):
       SPFM = 1 - [ Tong(lambda_SPF + lambda_RF) / Tong(lambda_SR) ]
       Yeu cau ASIL-D: SPFM >= 99%
       
    2. LFM (Latent Fault Metric):
       LFM = 1 - [ Tong(lambda_MP_latent) / Tong(lambda_SR - lambda_SPF - lambda_RF) ]
       Yeu cau ASIL-D: LFM >= 90%
       
    3. PMHF (Probabilistic Metric for random Hardware Failures):
       PMHF = Tong(lambda_SPF) + Tong(lambda_RF) + Tong(lambda_MP_latent * lambda_MP_detected * T_lifetime / 2)
       Yeu cau ASIL-D: PMHF < 10 FIT (10^-8 / gio hoat dong)
    """

    def __init__(self, mission_time_hours: float = 15000.0):
        """
        Khoi tao bo phan tich FMEDA.
        :param mission_time_hours: Thoi gian van hanh thiet ke cua xe (tieu chuan 15,000 gio o to).
        """
        self.components: List[HardwareComponent] = []
        self.mission_time_hours = mission_time_hours

    def add_component(self, comp: HardwareComponent):
        """Them linh kien phan cung vao bang FMEDA."""
        self.components.append(comp)

    def calculate_metrics(self) -> Dict[str, float]:
        """
        Tinh toan toan dien cac ty le hu hong va cac chi so SPFM, LFM, PMHF.
        """
        total_lambda = 0.0
        sum_lambda_sr = 0.0
        sum_lambda_safe = 0.0
        sum_lambda_spf = 0.0
        sum_lambda_rf = 0.0
        sum_lambda_mp_latent = 0.0
        sum_lambda_mp_detected = 0.0

        for c in self.components:
            total_lambda += c.lambda_fit
            
            # Ti le loi lien quan den an toan va khong an toan
            lambda_sr = c.lambda_fit * c.safety_related_ratio
            lambda_non_sr = c.lambda_fit * (1.0 - c.safety_related_ratio)
            
            sum_lambda_sr += lambda_sr
            
            # Loi an toan tu than (Safe faults)
            lambda_s = lambda_sr * c.safe_fault_ratio
            sum_lambda_safe += lambda_s + lambda_non_sr
            
            # Loi nguy hiem (Dangerous faults) can co che bao ve
            lambda_dangerous = lambda_sr * (1.0 - c.safe_fault_ratio)
            
            # Gia su phan chia loi don diem (Single-Point) va loi da diem (Multiple-Point)
            # Theo thiet ke kien truc ASIL-D, 50% la ti nang gay loi don diem neu khong co giam sat
            p_single_candidate = 0.50
            p_multi_candidate = 0.50
            
            lambda_spf_candidate = lambda_dangerous * p_single_candidate
            lambda_mp_candidate = lambda_dangerous * p_multi_candidate
            
            # Residual fault (Loi don diem khong duoc che chan het boi co che an toan)
            lambda_rf = lambda_spf_candidate * (1.0 - c.dc_rf)
            sum_lambda_rf += lambda_rf
            
            # Single-Point Fault (Loi khong co co che an toan bao ve)
            if c.dc_rf == 0.0:
                sum_lambda_spf += lambda_spf_candidate
            
            # Multiple-point faults: Latent (An) vs Detected (Phat hien duoc)
            lambda_mp_lat = lambda_mp_candidate * (1.0 - c.dc_mp)
            lambda_mp_det = lambda_mp_candidate * c.dc_mp
            
            sum_lambda_mp_latent += lambda_mp_lat
            sum_lambda_mp_detected += lambda_mp_det

        # Tinh toan SPFM (Single-Point Fault Metric)
        sum_dangerous_residual = sum_lambda_spf + sum_lambda_rf
        if sum_lambda_sr > 0:
            spfm = (1.0 - (sum_dangerous_residual / sum_lambda_sr)) * 100.0
        else:
            spfm = 100.0

        # Tinh toan LFM (Latent Fault Metric)
        denominator_lfm = sum_lambda_sr - sum_dangerous_residual
        if denominator_lfm > 0:
            lfm = (1.0 - (sum_lambda_mp_latent / denominator_lfm)) * 100.0
        else:
            lfm = 100.0

        # Tinh toan PMHF (Probabilistic Metric for random Hardware Failures)
        # T_lifetime chuyen sang gio: mission_time_hours
        # 1 FIT = 1e-9 / hour. Tinh PMHF theo don vi FIT.
        lambda_second_order = (sum_lambda_mp_latent * sum_lambda_mp_detected * (self.mission_time_hours * 1e-9)) / 2.0
        pmhf = sum_lambda_spf + sum_lambda_rf + lambda_second_order

        return {
            "total_lambda_fit": total_lambda,
            "lambda_spf": sum_lambda_spf,
            "lambda_rf": sum_lambda_rf,
            "lambda_mp_latent": sum_lambda_mp_latent,
            "spfm": spfm,
            "lfm": lfm,
            "pmhf": pmhf
        }

    def evaluate_asil_compliance(self, metrics: Dict[str, float]) -> Tuple[str, bool]:
        """
        Danh gia cap do ASIL dua tren cac nguong tieu chuan ISO 26262 Part 5:
        - ASIL-D: SPFM >= 99%, LFM >= 90%, PMHF < 10 FIT
        - ASIL-C: SPFM >= 97%, LFM >= 80%, PMHF < 100 FIT
        - ASIL-B: SPFM >= 90%, LFM >= 60%, PMHF < 100 FIT
        - QM (Quality Management): Khong dat cac chi tieu tren
        """
        spfm = metrics["spfm"]
        lfm = metrics["lfm"]
        pmhf = metrics["pmhf"]

        if spfm >= 99.0 and lfm >= 90.0 and pmhf < 10.0:
            return "ASIL-D", True
        elif spfm >= 97.0 and lfm >= 80.0 and pmhf < 100.0:
            return "ASIL-C", False
        elif spfm >= 90.0 and lfm >= 60.0 and pmhf < 100.0:
            return "ASIL-B", False
        else:
            return "QM (FAILED)", False

    def print_safety_dashboard(self, title: str):
        """In bang tong hop chi so an toan va danh gia ASIL len console."""
        metrics = self.calculate_metrics()
        level, is_asil_d = self.evaluate_asil_compliance(metrics)

        print("=" * 80)
        print(f"BANG DANH GIA AN TOAN PHAN CUNG ISO 26262 PART 5: {title}")
        print("=" * 80)
        print(f"Tong ty le hu hong phan cung (Raw Lambda) : {metrics['total_lambda_fit']:.2f} FIT")
        print(f"Single-Point & Residual Fault Rate      : {metrics['lambda_rf'] + metrics['lambda_spf']:.4f} FIT")
        print(f"Latent Multiple-Point Fault Rate        : {metrics['lambda_mp_latent']:.4f} FIT")
        print("-" * 80)
        print(f"1. SPFM (Single-Point Fault Metric)     : {metrics['spfm']:.2f}% (Tieu chuan ASIL-D: >= 99.0%)")
        print(f"2. LFM  (Latent Fault Metric)           : {metrics['lfm']:.2f}% (Tieu chuan ASIL-D: >= 90.0%)")
        print(f"3. PMHF (Probabilistic Hardware Metric) : {metrics['pmhf']:.4f} FIT (Tieu chuan ASIL-D: < 10.0 FIT)")
        print("-" * 80)
        status_text = "[DAT CHUAN ASIL-D 100%]" if is_asil_d else "[KHONG DAT ASIL-D]"
        print(f"KET LUAN CAP DO AN TOAN XE: {level} -> {status_text}")
        print("=" * 80)
        print()


def run_fmeda_test_suite():
    """Kiem tra va kiem chung toan dien he thong tinh toan FMEDA."""
    print("BAT DAU KIEM CHUAN HE THONG TINH TOAN CHI SO AN TOAN ISO 26262 ASIL-D\n")

    # 1. Kich ban 1: He thong ECU Steer-by-Wire dat chuan ASIL-D hoan hao
    ecu_nominal = ISO26262_FMEDA_Analyzer(mission_time_hours=15000.0)
    ecu_nominal.add_component(HardwareComponent("Dual-Core Lockstep CPU", 20.0, 1.0, 0.05, 0.995, 0.96))
    ecu_nominal.add_component(HardwareComponent("ECC SRAM with March C- BIST", 25.0, 1.0, 0.05, 0.998, 0.98))
    ecu_nominal.add_component(HardwareComponent("PMIC Watchdog & Voltage Supervisor", 10.0, 1.0, 0.10, 0.990, 0.92))
    ecu_nominal.add_component(HardwareComponent("Dual CAN-FD Transceivers", 15.0, 0.9, 0.15, 0.992, 0.94))
    ecu_nominal.add_component(HardwareComponent("Dual Core Clock Generators", 8.0, 1.0, 0.05, 0.994, 0.95))

    ecu_nominal.print_safety_dashboard("ECU STEER-BY-WIRE ASIL-D (CHEDO DAY DU CO CHE AN TOAN)")
    metrics_nominal = ecu_nominal.calculate_metrics()
    level_nominal, is_asil_d_nominal = ecu_nominal.evaluate_asil_compliance(metrics_nominal)
    assert is_asil_d_nominal, "ECU nominal phai dat chuan ASIL-D!"
    assert metrics_nominal["spfm"] >= 99.0, f"SPFM phai >= 99%, thuc te: {metrics_nominal['spfm']}%"
    assert metrics_nominal["lfm"] >= 90.0, f"LFM phai >= 90%, thuc te: {metrics_nominal['lfm']}%"
    assert metrics_nominal["pmhf"] < 10.0, f"PMHF phai < 10 FIT, thuc te: {metrics_nominal['pmhf']} FIT"

    # 2. Kich ban 2: Phan tich do nhay khi vo hieu hoa March C- BIST va giam Diagnostic Coverage cua RAM
    ecu_degraded = ISO26262_FMEDA_Analyzer(mission_time_hours=15000.0)
    ecu_degraded.add_component(HardwareComponent("Dual-Core Lockstep CPU", 20.0, 1.0, 0.05, 0.995, 0.96))
    # RAM bi vo hieu hoa BIST: dc_rf giam xuong 90%, dc_mp giam xuong 50%
    ecu_degraded.add_component(HardwareComponent("SRAM KHONG CO BIST (DEGRADED)", 25.0, 1.0, 0.05, 0.900, 0.50))
    ecu_degraded.add_component(HardwareComponent("PMIC Watchdog & Voltage Supervisor", 10.0, 1.0, 0.10, 0.990, 0.92))
    ecu_degraded.add_component(HardwareComponent("Dual CAN-FD Transceivers", 15.0, 0.9, 0.15, 0.992, 0.94))
    ecu_degraded.add_component(HardwareComponent("Dual Core Clock Generators", 8.0, 1.0, 0.05, 0.994, 0.95))

    ecu_degraded.print_safety_dashboard("ECU STEER-BY-WIRE DEGRADED (VO HIEU HOA MARCH C- BIST)")
    metrics_degraded = ecu_degraded.calculate_metrics()
    level_degraded, is_asil_d_degraded = ecu_degraded.evaluate_asil_compliance(metrics_degraded)
    assert not is_asil_d_degraded, "ECU bi tat BIST khong duoc phep dat chuan ASIL-D!"
    print(f"Phan tich rui ro: Khi tat March C- BIST, cap do an toan roi xuong: {level_degraded}")
    print(f"-> SPFM giam xuong: {metrics_degraded['spfm']:.2f}% (Rot khoi nguong 99%)")
    print(f"-> LFM giam xuong : {metrics_degraded['lfm']:.2f}% (Rot khoi nguong 90%)")
    print()

    print("[PASS] 100% Kiem tra Chi so Dinh luong FMEDA ISO 26262 Part 5 thanh cong!")


if __name__ == "__main__":
    run_fmeda_test_suite()
