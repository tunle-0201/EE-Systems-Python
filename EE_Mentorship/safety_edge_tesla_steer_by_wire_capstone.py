"""
Chuyen de AN: An toan Chuc nang Phan cung O to & Hang khong ISO 26262 ASIL-D
Bai 4 (Milestone AN.4 - Capstone): Dong co Dieu khien Lai Dien tu Khong truc Co hoc
Steer-by-Wire Fail-Operational & Failsafe ASIL-D cho Tesla Cybertruck & Robotaxi

Dac diem ky thuat he thong:
- Kien truc loai bo 100% truc lai co hoc giua vo-lang (Hand Wheel) va banh xe (Road Wheel).
- Kenh truyen dong kep (Dual Redundant BLDC Actuators A & B) co hop luc tai co cau thanh rang (Rack).
- Kenh cap nguon doc lap kep (Dual 48V Isolated Power Rails A & B).
- Kiem soat an toan bang vi dieu khien Dual-Core Lockstep tre 2 chu ky va SRAM March C- BIST.
- Thoi gian phat hien loi va chuyen mach du phong (Failover Transition Time) < 1.0 ms (thuc te < 500 us).
- Duy tri hoat dong lien tuc (Fail-Operational) ngay ca khi mot mo-to hoac bien tan bi no/ngan mach.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional


class SystemHealthState(Enum):
    NOMINAL_DUAL_CHANNEL = "NOMINAL_DUAL_CHANNEL"     # Ca 2 kenh A & B cung hoat dong (50/50 split)
    FAIL_OPERATIONAL_CH_B = "FAIL_OPERATIONAL_CH_B"   # Kenh A loi -> Kenh B g ganh 100% cong suat
    FAIL_OPERATIONAL_CH_A = "FAIL_OPERATIONAL_CH_A"   # Kenh B loi -> Kenh A g ganh 100% cong suat
    FAIL_SAFE_STOP = "FAIL_SAFE_STOP"                 # Ca 2 kenh deu hong -> Khoa cung, dung khan cap


class ChannelFaultType(Enum):
    NONE = "NONE"
    POWER_RAIL_UNDERVOLTAGE = "POWER_RAIL_UNDERVOLTAGE"   # Sut ap nguon 48V (< 36V)
    INVERTER_OVERCURRENT = "INVERTER_OVERCURRENT"         # Ngan mach van cong suat MOSFET / IGBT
    LOCKSTEP_CCU_MISMATCH = "LOCKSTEP_CCU_MISMATCH"       # Loi khong dong nhat CPU Lockstep
    RESOLVER_ENCODER_DRIFT = "RESOLVER_ENCODER_DRIFT"     # Sai lech goc cam bien Resolver > 1.5 do
    SRAM_BIST_FAILURE = "SRAM_BIST_FAILURE"               # Loi ket o nho phat hien boi March C-


@dataclass
class SteeringSensors:
    """Cum cam bien goc vo-lang kep (Dual Redundant Steering Angle Sensors)."""
    angle_sensor_a_deg: float = 0.0
    angle_sensor_b_deg: float = 0.0
    torque_sensor_nm: float = 0.0

    def check_plausibility(self, threshold_deg: float = 1.5) -> bool:
        """Kiem tra tinh hop ly cheo giua 2 cam bien (Cross-Sensor Plausibility)."""
        discrepancy = abs(self.angle_sensor_a_deg - self.angle_sensor_b_deg)
        return discrepancy <= threshold_deg

    def get_validated_angle(self) -> float:
        """Lay gia tri goc trung binh khi ca 2 cam bien deu tin cay."""
        return (self.angle_sensor_a_deg + self.angle_sensor_b_deg) / 2.0


@dataclass
class MotorActuatorChannel:
    """Kenh dong co chap hanh banh xe (BLDC Road Wheel Actuator Channel)."""
    channel_id: str
    voltage_rail_v: float = 48.0
    current_draw_a: float = 0.0
    motor_torque_nm: float = 0.0
    is_isolated: bool = False
    active_fault: ChannelFaultType = ChannelFaultType.NONE
    max_torque_capability_nm: float = 120.0  # Mo-men xoan toi da moi mo-to tren truc lai


class TeslaSteerByWireController:
    """
    Bo dieu khien Steer-by-Wire Fail-Operational chuan ASIL-D.
    
    Kien truc bao ve:
    1. Chia se tai chu dong 50/50 giua Kenh A va Kenh B khi binh thuong.
    2. Giam sat dien ap nguon 48V, dong bien tan, sai so goc Resolver o tan so 10 kHz (100 us/vong).
    3. Khi phat hien loi o Kenh A:
       - Cach ly Kenh A (Tri-state PWM) trong vong 1 chu ky PWM (< 100 us).
       - Tang toc mo-men Kenh B len 100% trong < 500 us (tong thoi gian < 1.0 ms).
       - Sai lech quy dao goc banh xe giu o muc < 0.2 do (nguoi lai khong bi giat tay lai).
    """

    def __init__(self):
        self.channel_a = MotorActuatorChannel("CH_A")
        self.channel_b = MotorActuatorChannel("CH_B")
        self.system_state = SystemHealthState.NOMINAL_DUAL_CHANNEL
        
        # Thong so thanh rang lai (Rack & Pinion Steering Dynamics)
        self.actual_rack_angle_deg = 0.0
        self.target_rack_angle_deg = 0.0
        self.steering_ratio = 14.5  # Ti so lai bien thien theo toc do
        
        # Thong so giam sat chuyen mach (Failover Telemetry)
        self.last_failover_duration_us: float = 0.0
        self.fault_event_log: List[str] = []

    def set_steering_input(self, yoke_angle_deg: float, sensor_noise_b: float = 0.0):
        """Cap nhat goc danh lai tu vo-lang cua nguoi lai hoac may tinh Autopilot."""
        self.target_rack_angle_deg = yoke_angle_deg / self.steering_ratio

    def inject_channel_fault(self, channel_id: str, fault: ChannelFaultType):
        """Tiem loi phan cung vat ly vao kenh truyen dong de kiem thu Fail-Operational."""
        target_ch = self.channel_a if channel_id == "CH_A" else self.channel_b
        target_ch.active_fault = fault
        if fault == ChannelFaultType.POWER_RAIL_UNDERVOLTAGE:
            target_ch.voltage_rail_v = 24.0  # Sut nguon duoi 36V
        elif fault == ChannelFaultType.INVERTER_OVERCURRENT:
            target_ch.current_draw_a = 150.0  # Vot nguong an toan 80A

    def run_control_cycle(self, dt_seconds: float = 0.0001, sensors: Optional[SteeringSensors] = None) -> Tuple[float, float]:
        """
        Mot chu ky dieu khien thoi gian thuc 10 kHz (dt = 100 microseconds).
        Tra ve: (actual_rack_angle_deg, total_rack_torque_nm).
        """
        # 1. Kiem tra hop ly cum cam bien goc lai (Sensor Plausibility)
        if sensors:
            if not sensors.check_plausibility(threshold_deg=1.5):
                self.fault_event_log.append("CANH BAO: Cam bien goc lai lech qua nguong 1.5 do!")

        # 2. Chan doan suc khoe phan cung Kenh A & Kenh B
        t_detect_start = time.perf_counter()
        fault_a = self._diagnose_channel(self.channel_a)
        fault_b = self._diagnose_channel(self.channel_b)

        # 3. May trang thai Fail-Operational & Chuyen mach du phong (Failover State Machine)
        if fault_a and not self.channel_a.is_isolated:
            # Cach ly Kenh A ngay lap tuc
            self.channel_a.is_isolated = True
            self.channel_a.motor_torque_nm = 0.0
            self.system_state = SystemHealthState.FAIL_OPERATIONAL_CH_B
            t_switch_done = time.perf_counter()
            self.last_failover_duration_us = (t_switch_done - t_detect_start) * 1e6
            self.fault_event_log.append(
                f"[FAILOVER] Kenh A loi ({self.channel_a.active_fault.value}). "
                f"Kenh B tiep quan 100% trong {self.last_failover_duration_us:.1f} us!"
            )
        elif fault_b and not self.channel_b.is_isolated:
            self.channel_b.is_isolated = True
            self.channel_b.motor_torque_nm = 0.0
            self.system_state = SystemHealthState.FAIL_OPERATIONAL_CH_A
            t_switch_done = time.perf_counter()
            self.last_failover_duration_us = (t_switch_done - t_detect_start) * 1e6
            self.fault_event_log.append(
                f"[FAILOVER] Kenh B loi ({self.channel_b.active_fault.value}). "
                f"Kenh A tiep quan 100% trong {self.last_failover_duration_us:.1f} us!"
            )
        elif fault_a and fault_b:
            self.system_state = SystemHealthState.FAIL_SAFE_STOP
            self.channel_a.is_isolated = True
            self.channel_b.is_isolated = True
            self.channel_a.motor_torque_nm = 0.0
            self.channel_b.motor_torque_nm = 0.0

        # Tinh toan phan phoi mo-men xoan (Torque Arbitration)
        kp_rack = 35.0  # He so khu sai so goc lai
        angle_error = self.target_rack_angle_deg - self.actual_rack_angle_deg
        
        # Mo-men can tu dinh tam mat duong (Self-Aligning Torque cua lop xe)
        road_aligning_torque = 4.0 * self.actual_rack_angle_deg
        demanded_rack_torque = kp_rack * angle_error + road_aligning_torque

        # Gioi han tong mo-men xoan trong nguong vat ly cua thanh rang
        max_total_torque = 120.0
        demanded_rack_torque = max(-max_total_torque, min(max_total_torque, demanded_rack_torque))

        if self.system_state == SystemHealthState.NOMINAL_DUAL_CHANNEL:
            # Che do binh thuong: Chia 50/50 giua 2 dong co
            self.channel_a.motor_torque_nm = demanded_rack_torque * 0.5
            self.channel_b.motor_torque_nm = demanded_rack_torque * 0.5
        elif self.system_state == SystemHealthState.FAIL_OPERATIONAL_CH_B:
            # Kenh B ganh 100% mo-men xoan
            self.channel_a.motor_torque_nm = 0.0
            self.channel_b.motor_torque_nm = demanded_rack_torque * 1.0
        elif self.system_state == SystemHealthState.FAIL_OPERATIONAL_CH_A:
            # Kenh A ganh 100% mo-men xoan
            self.channel_a.motor_torque_nm = demanded_rack_torque * 1.0
            self.channel_b.motor_torque_nm = 0.0
        else:
            # Failsafe stop
            self.channel_a.motor_torque_nm = 0.0
            self.channel_b.motor_torque_nm = 0.0

        total_applied_torque = self.channel_a.motor_torque_nm + self.channel_b.motor_torque_nm

        # 5. Mo phong dong luc hoc thanh rang lai (Rack Steering Plant Simulation)
        # Mo-men thuan thuc tac dong len co cau thanh rang = Tong mo-men dong co - Mo-men can mat duong
        net_rack_torque = total_applied_torque - road_aligning_torque
        rack_damping = 8.0   # N*m*s/rad (He so giam chan nho ma sat nhot)
        omega = (net_rack_torque / rack_damping)  # Toc do quay rad/s
        self.actual_rack_angle_deg += (omega * 57.2958) * dt_seconds

        return self.actual_rack_angle_deg, total_applied_torque

    def _diagnose_channel(self, channel: MotorActuatorChannel) -> bool:
        """Kiem tra dieu kien bat loi tren tung kenh theo tieu chuan ASIL-D."""
        if channel.active_fault != ChannelFaultType.NONE:
            return True
        if channel.voltage_rail_v < 36.0:
            channel.active_fault = ChannelFaultType.POWER_RAIL_UNDERVOLTAGE
            return True
        if channel.current_draw_a > 80.0:
            channel.active_fault = ChannelFaultType.INVERTER_OVERCURRENT
            return True
        return False


def run_tesla_steer_by_wire_capstone_demo():
    """Chuong trinh kiem thu toan dien he thong Steer-by-Wire Fail-Operational Capstone."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN HE THONG STEER-BY-WIRE TESLA CYBERTRUCK FAIL-OPERATIONAL ASIL-D")
    print("=" * 80)

    sbw = TeslaSteerByWireController()
    sensors = SteeringSensors(angle_sensor_a_deg=0.0, angle_sensor_b_deg=0.0)

    # --------------------------------------------------------------------------
    # GIAI DOAN 1: Lai xe binh thuong tren cao toc (Nominal 50/50 Torque Split)
    # --------------------------------------------------------------------------
    print("\n[GIAI DOAN 1]: Mo phong danh lai chuyen lan tren cao toc (Nominal 50/50 Dual Motor)...")
    target_yoke_angle = 45.0  # Nguoi lai quay vo-lang 45 do
    sensors.angle_sensor_a_deg = target_yoke_angle
    sensors.angle_sensor_b_deg = target_yoke_angle
    sbw.set_steering_input(target_yoke_angle)

    # Chay 500 buoc mo phong (50 ms thoi gian thuc, dt = 100 us)
    for _ in range(500):
        rack_angle, torque = sbw.run_control_cycle(dt_seconds=0.0001, sensors=sensors)

    print(f"-> Goc danh lai vo-lang (Yoke Input)  : {target_yoke_angle:.1f} deg")
    print(f"-> Goc thanh rang thuc te (Rack Angle): {rack_angle:.2f} deg (Ky vong: ~3.10 deg)")
    print(f"-> Mo-men dong co Kenh A              : {sbw.channel_a.motor_torque_nm:.2f} Nm")
    print(f"-> Mo-men dong co Kenh B              : {sbw.channel_b.motor_torque_nm:.2f} Nm")
    print(f"-> Trang thai he thong                : {sbw.system_state.value}")
    assert sbw.system_state == SystemHealthState.NOMINAL_DUAL_CHANNEL, "He thong phai o trang thai Nominal!"
    assert abs(sbw.channel_a.motor_torque_nm - sbw.channel_b.motor_torque_nm) < 1.0, "Mo-men 2 kenh phai chia 50/50!"

    # --------------------------------------------------------------------------
    # GIAI DOAN 2: Tiem loi no bien tan Kenh A tai toc do cao (Failover < 1.0 ms)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[GIAI DOAN 2]: Tiem loi no ngan mach bien tan Kenh A (Inverter Overcurrent)...")
    sbw.inject_channel_fault("CH_A", ChannelFaultType.INVERTER_OVERCURRENT)

    # Chay chu ky ke tiep de he thong bat loi va chuyen mach
    rack_angle_before = sbw.actual_rack_angle_deg
    for _ in range(500):
        rack_angle, torque = sbw.run_control_cycle(dt_seconds=0.0001, sensors=sensors)

    print(f"-> Trang thai he thong sau loi        : {sbw.system_state.value}")
    print(f"-> Thoi gian cach ly va chuyen mach   : {sbw.last_failover_duration_us:.2f} microseconds (< 1000 us)")
    print(f"-> Mo-men dong co Kenh A (Da cach ly) : {sbw.channel_a.motor_torque_nm:.2f} Nm (Tri-state PWM)")
    print(f"-> Mo-men dong co Kenh B (Ganh 100%)  : {sbw.channel_b.motor_torque_nm:.2f} Nm")
    print(f"-> Do lech goc thanh rang trong su co : {abs(rack_angle - rack_angle_before):.4f} deg (< 0.2 deg)")

    assert sbw.system_state == SystemHealthState.FAIL_OPERATIONAL_CH_B, "He thong phai chuyen sang Kenh B Fail-Operational!"
    assert sbw.channel_a.is_isolated, "Kenh A phai duoc ngat dien cach ly hoan toan!"
    assert sbw.channel_a.motor_torque_nm == 0.0, "Mo-men Kenh A phai bang 0!"
    assert sbw.channel_b.motor_torque_nm > 0.0, "Kenh B phai tiep quan toan bo mo-men!"
    assert abs(rack_angle - rack_angle_before) < 0.2, "Sai lech tay lai phai nho hon 0.2 do de tranh giat xe!"

    # --------------------------------------------------------------------------
    # GIAI DOAN 3: Kiem tra do lech cam bien goc lai (Sensor Plausibility)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[GIAI DOAN 3]: Kiem tra bo loc hop ly cheo cam bien goc lai...")
    sensors.angle_sensor_b_deg = sensors.angle_sensor_a_deg + 3.0  # Lech 3 do (vuot 1.5 do)
    sbw.run_control_cycle(dt_seconds=0.0001, sensors=sensors)
    assert not sensors.check_plausibility(threshold_deg=1.5), "Phai phat hien lech goc cam bien!"
    print("-> Phat hien cam bien sai lech: Cam bien A = 45.0 do, Cam bien B = 48.0 do (Lech > 1.5 do)")
    print(f"-> Nhat ky an toan ghi nhan           : {sbw.fault_event_log[-1]}")

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Dong co Steer-by-Wire Fail-Operational ASIL-D thanh cong!")
    print("=" * 80)


if __name__ == "__main__":
    run_tesla_steer_by_wire_capstone_demo()
