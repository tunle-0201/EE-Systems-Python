"""
================================================================================
          MODULE V: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE V.4: CAPSTONE AUTOMOTIVE 800V EV BMS ENGINE
================================================================================

KIEN TRUC HE THONG BMS XE DIEN CAO AP 800V (AUTOMOTIVE EV BMS ARCHITECTURE):
Trong cac dong sieu xe dien hien dai (Porsche Taycan, Hyundai Ioniq 5/6, Tesla Cybertruck):
- Khoi pin hoat dong o dien ap cuc cao 800V de cho phep sac sieu nhanh 350 kW
  va giam tiet dien day dan dong, giam trong luong xe.
- He thong doi hoi muc do an toan toi cao chuan cong nghiep o to (ISO 26262 ASIL-D).

SO DO MACH DONG CONTACTOR VA TIEN NAP PRE-CHARGE (ASCII CIRCUIT BLOCK):

                          Main (+) Contactor
                      +─────────/ ──────────+
                      |                     |
     [ Battery Pack ]─+   Pre-charge Relay  +───[ Inverter DC-Link ]
     [  192S - 800V ] |   +───/ ──[ R_pre ]─+   [    Capacitor     ]
                      |   |                 |   [     (3000 uF)    ]
                      +───+                 +───+
                      |                         |
                      +─────────/ ──────────────+
                          Main (-) Contactor

QUY TRINH 4 TANG PHONG VE THOI GIAN THUC CUA BMS ENGINE:
1. Chuoi dong tien nap Pre-charge Sequence:
   - Khong bao gio dong thang Contactor chinh vi dong nap xung cua tu bien tan
     se gay ho quang han dinh tiep diem (Contact Welding)!
   - Dong tiep diem Main (-), sau do dong Pre-charge qua dien tro R_pre.
   - Khi dien ap tu dat >= 95% dien ap pack moi dong Main (+) va ngat Pre-charge.

2. Giam sat an toan da lop da kenh (Multi-Cell ASIL-D Safety):
   - Qua ap (Over-Voltage OVP >= 4.25V).
   - Duoi ap (Under-Voltage UVP <= 2.80V).
   - Qua dong (Over-Current OCP >= 450A).
   - Qua nhiet (Over-Temperature OTP >= 60 degC).

3. Giam tai cong suat theo nhiet do (Thermal Derating):
   - Nhiet do tu 45 degC den 60 degC: Giam 50% dong xa cho phep.
   - Nhiet do >= 60 degC: Cat hoan toan va mo Contactor ngat cach ly khoi pin.

4. Danh gia do thoai hoa suc khoe pin State of Health (SOH %):
   - Uoc luong dua tren su gia tang noi tro thuan R0 cua cac cell pin.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np


class ContactorState:
    OPEN = "OPEN"
    PRECHARGING = "PRECHARGING"
    CLOSED_ACTIVE = "CLOSED_ACTIVE"
    EMERGENCY_ISOLATED = "EMERGENCY_ISOLATED"


class AutomotiveEV800VBMS:
    """
    Dong co BMS 800V toan dien cho xe dien the he moi
    Pack cau hinh 192S (192 cell mac noi tiep: 192 * 4.10V ~ 787V - 800V)
    """
    def __init__(self, num_series_cells: int = 192, nominal_cell_ah: float = 75.0):
        self.num_cells = num_series_cells
        self.nominal_ah = nominal_cell_ah
        self.contactor_state = ContactorState.OPEN

        # Cac nguong bao ve an toan tieu chuan o to ASIL-D
        self.ovp_limit = 4.25   # Volt / cell
        self.uvp_limit = 2.80   # Volt / cell
        self.ocp_limit = 450.0  # Ampe
        self.otp_limit = 60.0   # Do C

        # Thong so danh gia thoai hoa suc khoe pin (SOH)
        self.r0_initial = 0.0015  # 1.5 mOhm khi pack moi xuat xuong
        self.r0_current = 0.0018  # Noi tro tang dan sau thoi gian su dung

    def execute_precharge_sequence(self, pack_voltage: float, v_inverter_cap: float) -> str:
        """
        Quy trinh tien nap Pre-charge an toan:
        Chi cho phep dong Contactor chinh khi tu bien tan da nap >= 95% dien ap pack!
        """
        precharge_target = 0.95 * pack_voltage

        if self.contactor_state == ContactorState.EMERGENCY_ISOLATED:
            return str(self.contactor_state)

        if v_inverter_cap < precharge_target:
            self.contactor_state = ContactorState.PRECHARGING
        else:
            self.contactor_state = ContactorState.CLOSED_ACTIVE

        return str(self.contactor_state)

    def evaluate_safety_and_limits(
        self,
        cell_voltages: List[float],
        pack_current_a: float,
        pack_temp_c: float
    ) -> Dict[str, Any]:
        """
        Quet toan dien an toan chu ky 10 ms tren vi dieu khien o to:
        Kiem tra OVP, UVP, OCP, OTP va tinh toan cong suat van hanh an toan.
        """
        v_min = min(cell_voltages)
        v_max = max(cell_voltages)
        v_pack = sum(cell_voltages)

        safety_fault: Optional[str] = None

        # 1. Kiem tra nguong bao ve dien ap cell
        if v_max >= self.ovp_limit:
            safety_fault = "FAULT_OVER_VOLTAGE_OVP"
        elif v_min <= self.uvp_limit:
            safety_fault = "FAULT_UNDER_VOLTAGE_UVP"
        # 2. Kiem tra qua dong xa hoac nap
        elif abs(pack_current_a) >= self.ocp_limit:
            safety_fault = "FAULT_OVER_CURRENT_OCP"
        # 3. Kiem tra nhiet do pack pin
        elif pack_temp_c >= self.otp_limit:
            safety_fault = "FAULT_OVER_TEMPERATURE_OTP"

        # Kich hoat ngat cach ly khau cap neu co bat ky vi pham an toan nao
        if safety_fault is not None:
            self.contactor_state = ContactorState.EMERGENCY_ISOLATED

        # Tinh toan he so giam cong suat do nhiet (Thermal Derating)
        derating_factor = 1.0
        if 45.0 <= pack_temp_c < self.otp_limit:
            derating_factor = 0.5  # Giam 50% dong dien de lam mat
        elif pack_temp_c >= self.otp_limit:
            derating_factor = 0.0  # Ngat dong hoan toan

        # Tinh toan State of Health (SOH %) dua tren muc thoai hoa noi tro R0
        soh_pct = max(0.0, min(100.0, (2.0 - (self.r0_current / self.r0_initial)) * 100.0))

        return {
            "pack_voltage_v": float(v_pack),
            "cell_min_v": float(v_min),
            "cell_max_v": float(v_max),
            "delta_v_mv": float((v_max - v_min) * 1000.0),
            "pack_current_a": float(pack_current_a),
            "pack_power_kw": float((v_pack * pack_current_a) / 1000.0),
            "pack_temp_c": float(pack_temp_c),
            "safety_fault": safety_fault,
            "contactor_state": self.contactor_state,
            "derating_factor": float(derating_factor),
            "soh_pct": float(soh_pct)
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: AUTOMOTIVE 800V EV BATTERY MANAGEMENT ENGINE")
    print("=========================================================\n")

    bms = AutomotiveEV800VBMS(num_series_cells=192, nominal_cell_ah=75.0)

    # 1. Kiem tra quy trinh dong Contactor Pre-charge cao ap 800V
    v_pack_normal = 192 * 4.10  # 787.2 V
    print("1. KIEM TRA QUY TRINH TIEN NAP PRE-CHARGE CAO AP 800V:")
    state_init = bms.execute_precharge_sequence(pack_voltage=v_pack_normal, v_inverter_cap=100.0)
    print(f"   -> Khi V_cap = 100V (< 95%)  : Trang thai Contactor = {state_init}")
    assert state_init == ContactorState.PRECHARGING, "Phai o trang thai Pre-charge de bao ve tiep diem!"

    state_ready = bms.execute_precharge_sequence(pack_voltage=v_pack_normal, v_inverter_cap=760.0)
    print(f"   -> Khi V_cap = 760V (>= 95%) : Trang thai Contactor = {state_ready}")
    assert state_ready == ContactorState.CLOSED_ACTIVE, "Contactor chinh phai duoc dong an toan!"

    # 2. Van hanh xe binh thuong: Dap ga tang toc xa dong 250A tai 35 degC
    cells_normal = [4.10] * 192
    cells_normal[10] = 4.08  # Cell 10 hoi lech nhe 20 mV
    telemetry_drive = bms.evaluate_safety_and_limits(
        cell_voltages=cells_normal,
        pack_current_a=250.0,
        pack_temp_c=35.0
    )

    print("\n2. TELEMETRY VAN HANH XE BINH THUONG (ACCELERATION):")
    print(f"   -> Dien ap Pack Pin            : {telemetry_drive['pack_voltage_v']:.1f} V (He thong 800V)")
    print(f"   -> Cong suat tieu thu Dong co  : {telemetry_drive['pack_power_kw']:.1f} kW (~ 200 kW)")
    print(f"   -> Do lech ap giua cac cell    : {telemetry_drive['delta_v_mv']:.1f} mV")
    print(f"   -> Suc khoe pin (SOH)          : {telemetry_drive['soh_pct']:.1f}%")
    print(f"   -> He so cong suat Derating    : {telemetry_drive['derating_factor'] * 100:.0f}% (100% cong suat)")
    assert telemetry_drive["safety_fault"] is None, "Khong duoc co loi trong van hanh binh thuong!"

    # 3. Kich ban nhiet do tang cao (Thermal Derating tai 50 degC)
    telemetry_warm = bms.evaluate_safety_and_limits(
        cell_voltages=cells_normal,
        pack_current_a=250.0,
        pack_temp_c=50.0
    )
    print("\n3. KIEM SOAT NHIET DO (THERMAL DERATING TAI 50 DEG C):")
    print(f"   -> He so cong suat cho phep    : {telemetry_warm['derating_factor'] * 100:.0f}% (Da giam 50% de bao ve)")
    assert telemetry_warm["derating_factor"] == 0.5, "Phai giam 50% cong suat khi pin nong qua 45 degC!"

    # 4. Kich ban su co ngat khan cap: Qua nhiet 62 degC (Thermal Runaway Hazard)
    telemetry_crit = bms.evaluate_safety_and_limits(
        cell_voltages=cells_normal,
        pack_current_a=250.0,
        pack_temp_c=62.0
    )
    print("\n4. NGAT KHAN CAP KHI XAY RA SU CO NGUY HIEM (EMERGENCY TRIP):")
    print(f"   -> Ma loi an toan phat hien    : {telemetry_crit['safety_fault']}")
    print(f"   -> Trang thai Contactor        : {telemetry_crit['contactor_state']} [CACH LY CAO AP]")
    assert telemetry_crit["contactor_state"] == ContactorState.EMERGENCY_ISOLATED, "BMS phai lap tuc cach ly khoi pin!"

    print("\n[THANH CONG] CAPSTONE AUTOMOTIVE 800V EV BMS ENGINE HOAN TAT XUAT SAC!")
