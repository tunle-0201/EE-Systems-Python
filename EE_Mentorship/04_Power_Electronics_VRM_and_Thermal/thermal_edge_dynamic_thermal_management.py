"""
Chuyen de AV: Mo phong Nhiet - Dien Tich hop & Quan tri Tan nhiet Phan cung
Bai 138 (Milestone AV.3): Quan tri nhiet dong hoc DTM va Dieu khien quat thich nghi PID

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu he thong giam sat nhiet do on-die thermal diode, bo dieu khien quat PID
          co gioi han Slew Rate chong on am thanh (Acoustic Noise Budgeting), va may trang thai
          ha xung nhiet Thermal DVFS Throttling nhieu cap bao ve chip Apple Silicon va Tesla FSD.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class ThermalSensorFilter:
    """
    Cam bien nhiet do tren chip (On-Die Thermal Diode ADC) kem bo loc so EMA chong nhieu.
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Tin hieu do co nhieu:                               │
    │      T_raw = T_actual + Noise                          │
    │                                                        │
    │   Bo loc so Exponential Moving Average (EMA):          │
    │      T_filt[k] = alpha * T_raw[k] + (1 - alpha)*T_filt │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, alpha: float = 0.2, initial_temp_deg_c: float = 25.0):
        self.alpha = float(alpha)
        self.filtered_temp = float(initial_temp_deg_c)

    def update(self, raw_temp_deg_c: float) -> float:
        self.filtered_temp = self.alpha * raw_temp_deg_c + (1.0 - self.alpha) * self.filtered_temp
        return self.filtered_temp


class AdaptiveFanPIDController:
    """
    Bo dieu khien quat lam mat PID khep kin co gioi han toc do bien thien (Acoustic Slew Rate).
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Sai so nhiet do: e(t) = T_filtered(t) - T_setpoint   │
    │                                                        │
    │   Tin hieu dieu khien PID:                             │
    │      u(t) = Kp * e(t) + Ki * Int(e) + Kd * (de/dt)     │
    │                                                        │
    │   Gioi han bien thien PWM (Acoustic Slew Rate Limiter):│
    │      | dPWM / dt | <= Max_Slew_Rate (% / sec)          │
    │      Giu tieng quat em diu, khong gay tieng rit cho tai│
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        setpoint_temp_deg_c: float = 75.0,
        kp: float = 3.0,
        ki: float = 0.2,
        kd: float = 1.5,
        max_slew_rate_pct_per_sec: float = 15.0
    ):
        self.t_set = float(setpoint_temp_deg_c)
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.max_slew = float(max_slew_rate_pct_per_sec)

        self.integral_error = 0.0
        self.prev_error = 0.0
        self.current_pwm = 20.0  # Quat chay nhe mac dinh 20%

    def compute_fan_pwm(self, current_temp_deg_c: float, dt_sec: float) -> float:
        error = current_temp_deg_c - self.t_set

        # Tich phan sai so co anti-windup
        self.integral_error += error * dt_sec
        self.integral_error = max(-100.0, min(100.0, self.integral_error))

        # Vi phan sai so
        derivative = (error - self.prev_error) / max(1e-4, dt_sec)
        self.prev_error = error

        # Tin hieu PID tho
        pid_target_pwm = 20.0 + (self.kp * error + self.ki * self.integral_error + self.kd * derivative)
        pid_target_pwm = max(0.0, min(100.0, pid_target_pwm))

        # Gioi han toc do thay doi toc do quat (Slew Rate Limiting)
        max_delta = self.max_slew * dt_sec
        pwm_delta = pid_target_pwm - self.current_pwm
        clamped_delta = max(-max_delta, min(max_delta, pwm_delta))

        self.current_pwm += clamped_delta
        self.current_pwm = max(0.0, min(100.0, self.current_pwm))
        return self.current_pwm


class DynamicThermalManagementEngine:
    """
    May trang thai quan tri nhiet DTM ha xung nhiet Thermal Throttling da cap:
    NORMAL -> WARM -> HOT_THROTTLE -> CRITICAL_THROTTLE -> EMERGENCY_SHUTDOWN.
    """
    def __init__(
        self,
        t_warm: float = 80.0,
        t_hot: float = 95.0,
        t_critical: float = 105.0,
        t_trip: float = 115.0,
        nominal_clock_mhz: float = 3200.0,
        nominal_voltage_v: float = 1.10
    ):
        self.t_warm = float(t_warm)
        self.t_hot = float(t_hot)
        self.t_crit = float(t_critical)
        self.t_trip = float(t_trip)

        self.f_nom = float(nominal_clock_mhz)
        self.v_nom = float(nominal_voltage_v)

        self.current_state = "NORMAL"
        self.is_emergency_shutdown = False

    def evaluate_thermal_state(self, temp_deg_c: float) -> Dict[str, any]:
        """
        Danh gia trang thai nhiet va dieu chinh xung nhip/dien ap (DVFS Throttling).
        """
        if temp_deg_c >= self.t_trip:
            self.current_state = "EMERGENCY_SHUTDOWN"
            self.is_emergency_shutdown = True
            f_ratio = 0.0
            v_ratio = 0.0
        elif temp_deg_c >= self.t_crit:
            self.current_state = "CRITICAL_THROTTLE"
            f_ratio = 0.50  # Giam 50% xung nhip
            v_ratio = 0.80  # Giam 20% dien ap
        elif temp_deg_c >= self.t_hot:
            self.current_state = "HOT_THROTTLE"
            f_ratio = 0.75  # Giam 25% xung nhip
            v_ratio = 0.90  # Giam 10% dien ap
        elif temp_deg_c >= self.t_warm:
            self.current_state = "WARM"
            f_ratio = 1.00  # Giu nguyen xung nhip, quat tang toc
            v_ratio = 1.00
        else:
            self.current_state = "NORMAL"
            f_ratio = 1.00
            v_ratio = 1.00

        act_freq = self.f_nom * f_ratio
        act_volt = self.v_nom * v_ratio

        # Cong suat dong ti le voi f * V^2
        # P_ratio = f_ratio * (v_ratio ^ 2)
        power_scaling_factor = f_ratio * (v_ratio ** 2)

        return {
            "state": self.current_state,
            "actual_freq_mhz": act_freq,
            "actual_voltage_v": act_volt,
            "power_scaling_factor": power_scaling_factor,
            "is_emergency_shutdown": self.is_emergency_shutdown
        }


def test_dynamic_thermal_management():
    print("================================================================================")
    print("TEST SUITE: QUAN TRI NHIET DONG HOC DTM VA DIEU KHIEN QUAT PID KHEP KIN")
    print("================================================================================")

    # 1. Kiem tra bo loc cam bien nhiet EMA
    sensor_filter = ThermalSensorFilter(alpha=0.25, initial_temp_deg_c=78.0)
    # Dua vao nhiet do 80 deg C co nhieu +/- 5 deg C
    noisy_readings = [82.0, 77.0, 84.0, 78.0, 81.0, 79.0, 80.0]
    filtered_res = []
    for r in noisy_readings:
        filtered_res.append(sensor_filter.update(r))

    print(f"[1] Loc nhieu cam bien nhiet do On-Die Thermal Diode:")
    print(f"    - Du lieu tho co nhieu: {noisy_readings}")
    print(f"    - Du lieu sau loc EMA: {[round(x, 2) for x in filtered_res]}")
    assert abs(filtered_res[-1] - 80.0) < 3.0, "Bo loc EMA phai hoi tu ve gia tri thuc 80 deg C"

    # 2. Kiem tra bo dieu khien quat PID va gioi han Slew Rate am thanh (Apple Acoustic Spec)
    fan_pid = AdaptiveFanPIDController(setpoint_temp_deg_c=75.0, kp=3.0, ki=0.1, kd=1.0, max_slew_rate_pct_per_sec=20.0)
    
    # Nhiet do dot ngot tang vot len 95 deg C (Chenh lech error = +20 deg C)
    dt = 0.5 # 0.5 giay
    pwm1 = fan_pid.compute_fan_pwm(current_temp_deg_c=95.0, dt_sec=dt)
    
    # Toc do tang toi da trong 0.5s voi max_slew = 20%/s la: 20 * 0.5 = 10%
    # PWM ban dau 20% -> PWM sau 0.5s khong duoc vuot qua 30%!
    print(f"\n[2] Kiem tra bo dieu khien quat PID co gioi han Slew Rate:")
    print(f"    - Nhiet do tang vot len 95 deg C (Delta = +20 deg C)")
    print(f"    - PWM ban dau: 20.0% | PWM sau 0.5s: {pwm1:.1f}% (Gioi han Slew Rate <= 30.0%)")
    assert pwm1 <= 30.01, "Slew rate limiter bi vuot muc gay tieng rit quat"

    # Chay them vai buoc de xem quat tang toc em ai
    pwms = [pwm1]
    for _ in range(8):
        p = fan_pid.compute_fan_pwm(current_temp_deg_c=95.0, dt_sec=dt)
        pwms.append(p)
    print(f"    - Lo trinh tang toc quat qua 4.5s: {[round(x, 1) for x in pwms]}")
    assert pwms[-1] > 80.0, "Sau 4.5s quat phai tang len cong suat cao de lam mat"

    # 3. Kiem tra may trang thai Thermal DVFS Throttling
    dtm = DynamicThermalManagementEngine(
        t_warm=80.0,
        t_hot=95.0,
        t_critical=105.0,
        t_trip=115.0,
        nominal_clock_mhz=3200.0,
        nominal_voltage_v=1.10
    )

    print(f"\n[3] Kiem tra co che ha xung nhiet Thermal DVFS:")
    
    # Test trang thai NORMAL (65 deg C)
    r_norm = dtm.evaluate_thermal_state(65.0)
    print(f"    - 65 deg C: State={r_norm['state']} | Freq={r_norm['actual_freq_mhz']:.0f} MHz | Power={r_norm['power_scaling_factor']*100:.0f}%")
    assert r_norm["state"] == "NORMAL" and r_norm["actual_freq_mhz"] == 3200.0

    # Test trang thai HOT_THROTTLE (98 deg C)
    r_hot = dtm.evaluate_thermal_state(98.0)
    print(f"    - 98 deg C: State={r_hot['state']} | Freq={r_hot['actual_freq_mhz']:.0f} MHz | Power={r_hot['power_scaling_factor']*100:.1f}%")
    assert r_hot["state"] == "HOT_THROTTLE" and r_hot["actual_freq_mhz"] == 2400.0
    # Cong suat tieu thu giam xuong con 0.75 * (0.9^2) = 60.75%
    assert abs(r_hot["power_scaling_factor"] - 0.6075) < 0.01, "Loi tinh giam cong suat DVFS"

    # Test trang thai EMERGENCY_SHUTDOWN (118 deg C)
    r_trip = dtm.evaluate_thermal_state(118.0)
    print(f"    - 118 deg C: State={r_trip['state']} | Ngat toan bo nguon (Shutdown={r_trip['is_emergency_shutdown']})")
    assert r_trip["state"] == "EMERGENCY_SHUTDOWN"
    assert r_trip["is_emergency_shutdown"] is True
    print("    -> Co che Failsafe tu ngat bao ve chip khoi bi chay silicon thanh cong!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AV.3 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_dynamic_thermal_management()
