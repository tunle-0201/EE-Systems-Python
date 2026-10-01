"""
================================================================================
          MODULE U: EMBEDDED DIGITAL POWER ELECTRONICS & SPACE POWER SYSTEMS
              MILESTONE U.4: CAPSTONE SPACECRAFT & DRONE POWER MANAGEMENT (PMS)
================================================================================

KIEN TRUC HE THONG DIEN TREN VE TINH KHONG GIAN (SPACECRAFT POWER ARCHITECTURE):
Tren cac ve tinh viễn thong quy dao thap (Starlink, CubeSat) va Solar UAV tam cao:
- Nguon nang luong bien thien cuc do: Khi bay qua vung sang mat troi (Sunlight),
  gian pin quang dien phat dien nap vao Main Bus va sac he thong Pin Lithium-Ion.
- Khi bay vao vung khuat toi cua Trai Dat (Eclipse Shadow), pin mat troi ngung phat;
  he thong phai lap tuc dao chieu xa pin Lithium de duy tri nguon cho may tinh bay.

SO DO KHOI PHAN PHOI CONG SUAT THOI GIAN THUC (ASCII TEXT BLOCK):

   [ Solar PV Array ]
          |
          v
   [ MPPT Converter ] (P&O 99% cong suat)
          |
          +====================== [ MAIN 28V BUS ] ======================+
                                         ^                               |
                                         | (Hai chieu Sac/Xa)            |
                                         v                               v
                              [ Battery Management ]          [ eFuse OCP Switch ]
                              [  100Wh Li-ion Pack ]          (Ngat dong < 8.0A)
                                                                         |
                                                 +-----------------------+-----------------------+
                                                 |                                               |
                                                 v                                               v
                                        [ Buck Step-Down ]                              [ Buck Step-Down ]
                                        (28V -> 12V Rail)                               (28V -> 3.3V Rail)
                                                 |                                               |
                                                 v                                               v
                                         [ Payload Sensors ]                            [ Avionics MCU ]
                                         (Camera, Comms RF)                             (Flight Computer)

CAN BANG NANG LUONG HE THONG (ASCII EQUATION):

            P_net = P_solar - (P_avionics + P_payload)

            - Neu P_net > 0: Pin dang duoc nap (Charging mode)
            - Neu P_net < 0: Pin dang xa dien (Discharging mode qua vung toi)
"""

from typing import Tuple, List, Dict, Any
import numpy as np


class ElectronicFuseOCP:
    """
    Mach cau chi dien tu eFuse ngat dong cuc nhanh bang MOSFET (< 10 micro-giay)
    khi dong tai vuot qua nguong gioi han an toan Over-Current Protection.
    """
    def __init__(self, current_limit_amps: float = 8.0):
        self.limit = current_limit_amps
        self.tripped = False

    def check_and_protect(self, current_amps: float) -> bool:
        """Kiem tra va kich hoat chot ngat bao ve neu dong vuot nguong"""
        if current_amps > self.limit:
            self.tripped = True
        return not self.tripped

    def reset(self) -> None:
        """Dat lai trang thai eFuse sau khi xu ly xong su co"""
        self.tripped = False


class DigitalRailController:
    """
    Bo on ap so da kenh dieu tiet dien ap bang bo dieu khien ti le - tich phan (PI)
    """
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
        return float(duty_clamped)


class SpacecraftPowerManagementEngine:
    """
    Dong co dieu hanh he thong nang luong ve tinh va drone (Spacecraft PMS Engine)
    Tich hop quan ly Main Bus 28V, sac/xa pin Lithium, dieu tiet rail va bao ve eFuse.
    """
    def __init__(self):
        self.bus_voltage = 28.0        # Dien ap Main Bus chuan quan su MIL-STD-704
        self.battery_capacity_wh = 100.0
        self.battery_energy_wh = 80.0  # Dung luong khoi dau: 80 Wh (80% SOC)
        self.efuse_payload = ElectronicFuseOCP(current_limit_amps=8.0)
        self.rail_12v = DigitalRailController(target_voltage=12.0, v_bus=28.0)
        self.rail_3v3 = DigitalRailController(target_voltage=3.3, v_bus=28.0)

    def process_power_cycle(
        self,
        solar_power_w: float,
        payload_current_a: float,
        avionics_current_a: float,
        dt_seconds: float
    ) -> Dict[str, Any]:
        """
        Xu ly 1 chu ky phan phoi cong suat thoi gian thuc tren he thong nhung
        """
        # 1. Kiem tra bao ve eFuse cho tai Payload
        payload_safe = self.efuse_payload.check_and_protect(payload_current_a)
        actual_payload_i = payload_current_a if payload_safe else 0.0

        # 2. Tinh toan cong suat tieu thu tren tung Rail
        p_payload = 12.0 * actual_payload_i
        p_avionics = 3.3 * avionics_current_a
        p_total_load = p_payload + p_avionics

        # 3. Can bang nang luong thuan tai Main Bus
        net_power_w = solar_power_w - p_total_load

        # 4. Tich phan cap nhat trang thai sac pin (Battery SOC)
        energy_delta_wh = (net_power_w * dt_seconds) / 3600.0
        self.battery_energy_wh += energy_delta_wh
        self.battery_energy_wh = max(0.0, min(self.battery_capacity_wh, self.battery_energy_wh))
        soc_percent = (self.battery_energy_wh / self.battery_capacity_wh) * 100.0

        return {
            "solar_power_w": float(solar_power_w),
            "load_power_w": float(p_total_load),
            "net_power_w": float(net_power_w),
            "battery_soc_pct": float(soc_percent),
            "is_charging": bool(net_power_w > 0.0),
            "efuse_ok": bool(payload_safe)
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: EMBEDDED SPACECRAFT DIGITAL POWER SYSTEM")
    print("=========================================================\n")

    pms = SpacecraftPowerManagementEngine()

    print("1. KICH BAN MO PHONG QUI DAO VE TINH (ORBIT MISSION SCENARIO):")
    print("   - Giai doan 1 (Vung sang Sunlight) : Mat troi 120W, tai danh dinh -> Sac pin.")
    print("   - Giai doan 2 (Vung toi Eclipse)  : Mat troi 0W -> Xa pin duy tri may tinh bay.")
    print("   - Giai doan 3 (Su co ngan mach)   : Dong vot len 15A -> Kich hoat eFuse ngat mach!\n")

    # Giai doan 1: Vung sang mat troi chieu 120W (10 chu ky, dt = 60s)
    telemetry_day: List[Dict[str, Any]] = []
    for _ in range(10):
        t = pms.process_power_cycle(
            solar_power_w=120.0,
            payload_current_a=2.0,
            avionics_current_a=1.5,
            dt_seconds=60.0
        )
        telemetry_day.append(t)

    print("2. TELEMETRY GIAI DOAN CO MAT TROI (CHARGING PHASE):")
    print(f"   -> Cong suat mat troi thu duoc : {telemetry_day[-1]['solar_power_w']:.1f} W")
    print(f"   -> Cong suat tieu thu toan bo : {telemetry_day[-1]['load_power_w']:.1f} W")
    print(f"   -> Cong suat nap thuan vao pin : +{telemetry_day[-1]['net_power_w']:.1f} W")
    print(f"   -> Dung luong pin (SOC)        : {telemetry_day[-1]['battery_soc_pct']:.2f}% (Tang tu 80.00%)\n")
    assert telemetry_day[-1]["is_charging"] is True, "He thong phai o trang thai nap pin khi du nang luong!"

    # Giai doan 2: Vung toi Eclipse mat troi = 0W (xa pin nuoi may tinh bay)
    t_night = pms.process_power_cycle(
        solar_power_w=0.0,
        payload_current_a=1.0,
        avionics_current_a=1.5,
        dt_seconds=300.0
    )
    print("3. TELEMETRY GIAI DOAN DI VAO VUNG TOI (ECLIPSE DISCHARGING):")
    print(f"   -> Cong suat mat troi         : {t_night['solar_power_w']:.1f} W")
    print(f"   -> Cong suat xa tu pin        : {t_night['net_power_w']:.1f} W")
    print(f"   -> Trang thai pin             : {'DANG SAC' if t_night['is_charging'] else 'DANG XA PIN DUY TRI BAY'}\n")
    assert t_night["is_charging"] is False, "He thong phai tu dong xa pin khi di vao vung toi!"

    # Giai doan 3: Su co cham chap tai Payload dong tang vot 15A
    t_fault = pms.process_power_cycle(
        solar_power_w=50.0,
        payload_current_a=15.0,
        avionics_current_a=1.0,
        dt_seconds=1.0
    )
    print("4. KIEM TRA MACH BAO VE DIEN TU eFuse (OVER-CURRENT PROTECTION):")
    print("   -> Phat hien dong su co       : 15.0 A (Vuot nguong an toan 8.0A)")
    print(f"   -> Trang thai ngat mach eFuse : {'[NGAT DIEN AN TOAN]' if not t_fault['efuse_ok'] else 'LOI'}")
    assert t_fault["efuse_ok"] is False, "eFuse phai lap tuc ngat tai khi dong vuot qua 8A!"

    print("\n[THANH CONG] CAPSTONE HE THONG DIEN TU CONG SUAT VE TINH HOAN TAT XUAT SAC!")
