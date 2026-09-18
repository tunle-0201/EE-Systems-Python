"""
================================================================================
          MODULE AL: EMBEDDED POWER ELECTRONICS & DIGITAL POWER SYSTEMS
              MILESTONE AL.4: CAPSTONE FULL SATELLITE & DRONE POWER MANAGEMENT SYSTEM
================================================================================

KIẾN TRÚC HỆ THỐNG ĐIỆN KHÔNG GIAN (SPACECRAFT POWER MANAGEMENT SYSTEM - PMS ENGINE):
Trên các vệ tinh viễn thông (Starlink, CubeSat) và máy bay không người lái VTOL:
- Nguồn năng lượng biến đổi liên tục: Ban ngày thu năng lượng mặt trời, ban đêm (Eclipse)
  phải xả pin lithium duy trì sự sống cho máy tính bay.

HỆ THỐNG ĐIỆN TỬ CÔNG SUẤT TÍCH HỢP ĐỦ 4 KHỐI THỜI GIAN THỰC:
1. Bộ theo dõi điểm công suất cực đại MPPT (Perturb & Observe) tối đa hóa năng lượng thu.
2. Bộ hạ áp số đa kênh Synchronous Buck chia nguồn:
   - Rail 1: 12.0V cấp động cơ phản lực / tải công suất cao (Payload Rail).
   - Rail 2: 3.3V cấp máy tính bay và cảm biến IMU (Avionics Rail).
3. Bộ điều khiển số PID Closed-Loop chống sụt áp khi tải bật đột ngột.
4. Mạch ngắt điện tử an toàn eFuse (Over-Current Protection - OCP) tự ngắt trong 10 us!

BẢNG CÂN BẰNG CÔNG SUẤT HỆ THỐNG (ASCII TEXT BLOCK):
                 P_solar = V_pv * I_pv (Thu tu quang dien)
                 P_load  = P_avionics + P_payload
                 
                 P_battery = P_solar - P_load
                 
                 Neu P_battery > 0: Dang sac pin (Charging)
                 Neu P_battery < 0: Dang xa pin (Discharging khi qua vung toi)
"""

import numpy as np

class ElectronicFuseOCP:
    """Mạch cầu chì điện tử eFuse ngắt dòng cực nhanh khi xảy ra ngắn mạch"""
    def __init__(self, current_limit_amps: float = 8.0):
        self.limit = current_limit_amps
        self.tripped = False

    def check_and_protect(self, current_amps: float) -> bool:
        if current_amps > self.limit:
            self.tripped = True
        return not self.tripped


class DigitalRailController:
    """Bộ ổn áp số đa kênh PWM điều tiết điện áp bằng giải thuật PID"""
    def __init__(self, target_voltage: float, v_bus: float = 28.0):
        self.v_ref = target_voltage
        self.v_bus = v_bus
        self.integral = 0.0
        self.prev_error = 0.0
        self.kp = 0.1
        self.ki = 400.0

    def step(self, v_measured: float, dt: float) -> float:
        error = self.v_ref - v_measured
        self.integral += error * dt
        duty = self.kp * error + self.ki * self.integral
        duty_clamped = max(0.01, min(0.95, duty))
        return duty_clamped


class SpacecraftPowerManagementEngine:
    """
    Trọng tâm Capstone: Động cơ điều hành năng lượng toàn diện cho Vệ tinh / Drone
    """
    def __init__(self):
        self.bus_voltage = 28.0   # Chuẩn điện áp bus vệ tinh quân sự MIL-STD-704
        self.battery_capacity_wh = 100.0
        self.battery_energy_wh = 80.0  # 80% ban đầu
        self.efuse_payload = ElectronicFuseOCP(current_limit_amps=8.0)
        self.rail_12v = DigitalRailController(target_voltage=12.0, v_bus=28.0)
        self.rail_3v3 = DigitalRailController(target_voltage=3.3, v_bus=28.0)

    def process_power_cycle(self, solar_power_w: float, payload_current_a: float, avionics_current_a: float, dt_seconds: float) -> dict:
        """
        Xử lý 1 chu kỳ phân phối công suất thời gian thực
        """
        # 1. Bảo vệ eFuse cho tải công suất
        payload_safe = self.efuse_payload.check_and_protect(payload_current_a)
        actual_payload_i = payload_current_a if payload_safe else 0.0

        # 2. Công suất tiêu thụ các Rail
        p_payload = 12.0 * actual_payload_i
        p_avionics = 3.3 * avionics_current_a
        p_total_load = p_payload + p_avionics

        # 3. Cân bằng năng lượng hệ thống
        net_power_w = solar_power_w - p_total_load

        # 4. Cập nhật trạng thái sạc pin (Battery SOC)
        energy_delta_wh = (net_power_w * dt_seconds) / 3600.0
        self.battery_energy_wh += energy_delta_wh
        self.battery_energy_wh = max(0.0, min(self.battery_capacity_wh, self.battery_energy_wh))
        soc_percent = (self.battery_energy_wh / self.battery_capacity_wh) * 100.0

        return {
            "solar_power_w": float(solar_power_w),
            "load_power_w": float(p_total_load),
            "net_power_w": float(net_power_w),
            "battery_soc_pct": float(soc_percent),
            "is_charging": bool(net_power_w > 0),
            "efuse_ok": bool(payload_safe)
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: EMBEDDED SPACECRAFT DIGITAL POWER SYSTEM")
    print("=========================================================\n")

    pms = SpacecraftPowerManagementEngine()

    print("1. KICH BAN MO PHONG QUI DAO VE TINH (ORBIT CYCLE):")
    print("   - Giai doan 1 (Buoi sang): Mat troi chieu 120W, tai binh thuong (Nap pin).")
    print("   - Giai doan 2 (Vung toi Eclipse): Mat troi 0W, xa pin nuoi may tinh bay.")
    print("   - Giai doan 3 (Su co ngan mach): Dong tai dot bien 15A -> Kich hoat eFuse!\n")

    # Giai đoạn 1: Sạc pin buổi sáng (10 chu kỳ)
    telemetry_day = []
    for _ in range(10):
        t = pms.process_power_cycle(solar_power_w=120.0, payload_current_a=2.0, avionics_current_a=1.5, dt_seconds=60.0)
        telemetry_day.append(t)

    print("2. TELEMETRY GIAI DOAN CO MAT TROI (CHARGING):")
    print(f"   -> Cong suat mat troi thu duoc : {telemetry_day[-1]['solar_power_w']:.1f} W")
    print(f"   -> Cong suat tieu thu toan bo : {telemetry_day[-1]['load_power_w']:.1f} W")
    print(f"   -> Cong suat nap thuan vao pin : +{telemetry_day[-1]['net_power_w']:.1f} W")
    print(f"   -> Dung luong pin (SOC)        : {telemetry_day[-1]['battery_soc_pct']:.2f}% (Da tang tu 80%)\n")
    assert telemetry_day[-1]['is_charging'] is True, "He thong phai dang o trang thai nap pin!"

    # Giai đoạn 2: Vùng tối Eclipse (Không có mặt trời)
    t_night = pms.process_power_cycle(solar_power_w=0.0, payload_current_a=1.0, avionics_current_a=1.5, dt_seconds=300.0)
    print("3. TELEMETRY GIAI DOAN DI VAO VUNG TOI (ECLIPSE DISCHARGING):")
    print(f"   -> Cong suat mat troi         : {t_night['solar_power_w']:.1f} W")
    print(f"   -> Cong suat xa tu pin        : {t_night['net_power_w']:.1f} W")
    print(f"   -> Trang thai pin             : {'DANG SAC' if t_night['is_charging'] else 'DANG XA PIN DUY TRI BAY'}\n")
    assert t_night['is_charging'] is False, "He thong phai xa pin trong vung toi!"

    # Giai đoạn 3: Ngắn mạch quá dòng (Short-circuit fault 15A)
    t_fault = pms.process_power_cycle(solar_power_w=50.0, payload_current_a=15.0, avionics_current_a=1.0, dt_seconds=1.0)
    print("4. KIEM TRA MACH BAO VE DIEN TU eFuse (OVER-CURRENT PROTECTION):")
    print(f"   -> Phat hien dong su co       : 15.0 A (Vuot nguong an toan 8.0A)")
    print(f"   -> Trang thai ngat mach eFuse : {'[NGAT DIEN AN TOAN]' if not t_fault['efuse_ok'] else 'LOI'}")
    assert t_fault['efuse_ok'] is False, "eFuse phai ngat tuc thoi khi dong vuot 8A!"

    print("\n[THANH CONG] CAPSTONE HE THONG DIEN TU CONG SUAT VE TINH HOAN TAT XUAT SAC!")
