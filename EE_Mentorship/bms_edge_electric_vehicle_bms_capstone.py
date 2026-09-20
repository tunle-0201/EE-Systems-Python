"""
================================================================================
          MODULE AM: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE AM.4: CAPSTONE FULL AUTOMOTIVE 800V EV BMS ENGINE
================================================================================

KIẾN TRÚC TRỌNG TÂM: BỘ ĐIỀU HÀNH PIN XE ĐIỆN CAO ÁP 800V (AUTOMOTIVE EV BMS ENGINE)
Trong các siêu xe điện hiện đại (Porsche Taycan, Hyundai Ioniq, Tesla Cybertruck):
- Khối pin hoạt động ở điện áp cực cao 800V (để sạc siêu nhanh 350 kW và giảm kích thước dây dẫn).
- Đòi hỏi chuẩn an toàn tối cao chuẩn công nghiệp xe hơi (ISO 26262 ASIL-D).

ĐỘNG CƠ BMS CAPSTONE TÍCH HỢP 4 TẦNG PHÒNG VỆ THỜI GIAN THỰC:
1. Chuỗi đóng rơ-le nạp tiền nạp (Pre-charge Sequence):
   - Không được đóng thẳng rơ-le chính vì dòng nạp tụ biến tần (Inverter DC-Link) sẽ
     gây phóng tia lửa hàn dính tiếp điểm (Contact Welding)!
   - Đóng tiếp điểm âm (-) -> Đóng rơ-le Pre-charge qua điện trở -> Khi tụ đạt 95% áp
     mới đóng tiếp điểm chính (+) và ngắt Pre-charge.
2. Giám sát an toàn đa tế bào (Multi-Cell Monitoring):
   - Quá áp (Over-Voltage OVP > 4.25V).
   - Dưới áp (Under-Voltage UVP < 2.80V).
   - Quá dòng (Over-Current OCP > 450A).
3. Giảm tải công suất theo nhiệt độ (Thermal Derating):
   - T > 45°C: Giảm 50% công suất sạc/xả.
   - T > 60°C: Ngắt khẩn cấp rơ-le cao áp để ngăn ngừa cháy nổ nhiệt (Thermal Runaway).
4. Đánh giá độ thoái hóa sức khỏe pin State of Health (SOH %):
   - Theo dõi sự gia tăng nội trở R0 và suy giảm dung lượng theo thời gian.
"""

import numpy as np

class ContactorState:
    OPEN = "OPEN"
    PRECHARGING = "PRECHARGING"
    CLOSED_ACTIVE = "CLOSED_ACTIVE"
    EMERGENCY_ISOLATED = "EMERGENCY_ISOLATED"


class AutomotiveEV800VBMS:
    """
    Động cơ BMS 800V hoàn chỉnh cho xe điện
    Pack cấu hình 192S (192 cells nối tiếp: 192 * 4.16V ~ 800V)
    """
    def __init__(self, num_series_cells: int = 192, nominal_cell_ah: float = 75.0):
        self.num_cells = num_series_cells
        self.nominal_ah = nominal_cell_ah
        self.contactor_state = ContactorState.OPEN

        # Trạng thái an toàn
        self.ovp_limit = 4.25
        self.uvp_limit = 2.80
        self.ocp_limit = 450.0  # Ampe
        self.otp_limit = 60.0   # Độ C

        # Đánh giá độ chai pin (SOH)
        self.r0_initial = 0.0015  # 1.5 mOhm cell mới
        self.r0_current = 0.0018  # Nội trở tăng theo thời gian

    def execute_precharge_sequence(self, pack_voltage: float, v_inverter_cap: float) -> str:
        """
        Quy trình tiền nạp Pre-charge an toàn:
        Chỉ đóng Contactor chính khi tụ điện biến tần đã nạp >= 95% điện áp pack!
        """
        precharge_target = 0.95 * pack_voltage

        if self.contactor_state == ContactorState.EMERGENCY_ISOLATED:
            return self.contactor_state

        if v_inverter_cap < precharge_target:
            self.contactor_state = ContactorState.PRECHARGING
        else:
            self.contactor_state = ContactorState.CLOSED_ACTIVE

        return self.contactor_state

    def evaluate_safety_and_limits(self, cell_voltages: list, pack_current_a: float, pack_temp_c: float) -> dict:
        """
        Quét an toàn thời gian thực chu kỳ 10 ms:
        Kiểm tra OVP, UVP, OCP, OTP và tính toán công suất xả tối đa cho phép
        """
        v_min = min(cell_voltages)
        v_max = max(cell_voltages)
        v_pack = sum(cell_voltages)

        safety_fault = None

        # 1. Kiểm tra giới hạn điện áp cell
        if v_max >= self.ovp_limit:
            safety_fault = "FAULT_OVER_VOLTAGE_OVP"
        elif v_min <= self.uvp_limit:
            safety_fault = "FAULT_UNDER_VOLTAGE_UVP"
        # 2. Kiểm tra quá dòng
        elif abs(pack_current_a) >= self.ocp_limit:
            safety_fault = "FAULT_OVER_CURRENT_OCP"
        # 3. Kiểm tra quá nhiệt
        elif pack_temp_c >= self.otp_limit:
            safety_fault = "FAULT_OVER_TEMPERATURE_OTP"

        # Nếu có lỗi an toàn: Ngắt lập tức rơ-le cao áp cách ly khối pin!
        if safety_fault is not None:
            self.contactor_state = ContactorState.EMERGENCY_ISOLATED

        # Tính toán Thermal Derating (Giảm công suất khi pin nóng)
        derating_factor = 1.0
        if 45.0 <= pack_temp_c < self.otp_limit:
            derating_factor = 0.5  # Giảm 50% dòng điện cho phép
        elif pack_temp_c >= self.otp_limit:
            derating_factor = 0.0  # Cắt hoàn toàn

        # Tính State of Health (SOH %) dựa trên mức tăng nội trở
        # SOH = (2.0 - (R_current / R_initial)) * 100%
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

    # 1. Kiểm tra quy trình đóng Contactor Pre-charge cao áp 800V
    v_pack_normal = 192 * 4.10  # 787.2 V
    print("1. KIEM TRA QUY TRINH PRE-CHARGE CAO AP 800V:")
    # Tụ biến tần lúc đầu 0V -> Phải ở trạng thái PRECHARGING
    state_init = bms.execute_precharge_sequence(pack_voltage=v_pack_normal, v_inverter_cap=100.0)
    print(f"   -> Khi V_cap = 100V (< 95%) : Trang thai Contactor = {state_init}")
    assert state_init == ContactorState.PRECHARGING, "Phai o trang thai Pre-charge!"

    # Khi tụ biến tần nạp đạt 760V (> 95% của 787.2V) -> Đóng Contactor chính
    state_ready = bms.execute_precharge_sequence(pack_voltage=v_pack_normal, v_inverter_cap=760.0)
    print(f"   -> Khi V_cap = 760V (>= 95%) : Trang thai Contactor = {state_ready}")
    assert state_ready == ContactorState.CLOSED_ACTIVE, "Contactor chinh phai duoc dong an toan!"

    # 2. Vận hành xe bình thường: Đạp ga xả dòng 250A tại 35 độ C
    cells_normal = [4.10] * 192
    cells_normal[10] = 4.08  # Cell 10 hơi lệch nhẹ
    telemetry_drive = bms.evaluate_safety_and_limits(cell_voltages=cells_normal, pack_current_a=250.0, pack_temp_c=35.0)

    print("\n2. TELEMETRY VAN HANH XE BINH THUONG (ACCELERATION):")
    print(f"   -> Dien ap Pack Pin            : {telemetry_drive['pack_voltage_v']:.1f} V (He thong 800V)")
    print(f"   -> Cong suat tieu thu Dong co  : {telemetry_drive['pack_power_kw']:.1f} kW (Sieu xe ~ 200 kW)")
    print(f"   -> Do lech ap giua cac cell    : {telemetry_drive['delta_v_mv']:.1f} mV")
    print(f"   -> Suc khoe pin (SOH)          : {telemetry_drive['soh_pct']:.1f}%")
    print(f"   -> He so cong suat Derating    : {telemetry_drive['derating_factor'] * 100:.0f}% (100% cong suat)")
    assert telemetry_drive['safety_fault'] is None, "Khong duoc co loi trong van hanh binh thuong!"

    # 3. Kịch bản nhiệt độ tăng cao (Thermal Derating tại 50 độ C)
    telemetry_warm = bms.evaluate_safety_and_limits(cell_voltages=cells_normal, pack_current_a=250.0, pack_temp_c=50.0)
    print("\n3. KIEM SOAT NHIET DO (THERMAL DERATING TAI 50 DEG C):")
    print(f"   -> He so cong suat cho phep    : {telemetry_warm['derating_factor'] * 100:.0f}% (Da giam 50% de bao ve pin)")
    assert telemetry_warm['derating_factor'] == 0.5, "Phai giam 50% cong suat khi pin qua 45 do!"

    # 4. Kịch bản sự cố ngắt khẩn cấp: Quá nhiệt 62 độ C (Thermal Runaway Danger)
    telemetry_crit = bms.evaluate_safety_and_limits(cell_voltages=cells_normal, pack_current_a=250.0, pack_temp_c=62.0)
    print("\n4. NGAT KHAN CAP KHI XAY RA SU CO NGUY HIEM (EMERGENCY TRIP):")
    print(f"   -> Ma loi an toan phat hien    : {telemetry_crit['safety_fault']}")
    print(f"   -> Trang thai Contactor        : {telemetry_crit['contactor_state']} [CACH LY CAO AP]")
    assert telemetry_crit['contactor_state'] == ContactorState.EMERGENCY_ISOLATED, "BMS phai ngat cach ly khoi pin ngay lap tuc!"

    print("\n[THANH CONG] CAPSTONE AUTOMOTIVE 800V EV BMS ENGINE HOAN TAT XUAT SAC!")
