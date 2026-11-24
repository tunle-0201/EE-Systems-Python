"""EE MENTORSHIP - BAI 235 - MODULE BT.4: LOCKED-ROTOR CURRENT LOOP.

BUOC 1 - HOP CONG CU
  Ghep AFE -> PWM trigger -> two-shunt -> Clarke -> PI alpha/beta -> PWM.
  Rotor dung yen, theta=0, back-EMF=0: i_beta dong vai tro iq tham chieu.
  Mo hinh RL averaged hai truc R=0.4 ohm, L=1 mH, dt=50 us:
    i_next = v/R + (i-v/R)*exp(-R*dt/L)
  PI: u=kp*error+integral, kp=2 V/A, ki=800 V/(A*s), kep +/-6 V/truc.
  Conditional integration: dung tich phan khi saturation va error day u xa
  hon gioi han; cho phep tich phan khi error keo u ve lai mien hop le.
  Inverse Clarke: va=alpha; vb=-alpha/2+sqrt(3)*beta/2;
  vc=-alpha/2-sqrt(3)*beta/2. duty=0.5+vphase/24 V.
  CurrentLoop.step(frame,temp,previous_duties,iq_reference_a) tra duty moi
  hoac None khi fault chot. Mau cua chu ky hien tai phai hop le voi duty CU.

BUOC 2 - BAI TOAN TU LAM
  Tu dong vong dieu khien 20 kHz cho lenh 0 -> 8 -> -5 A, shunt tai 100 degC.
  Thu voltage limit, anti-windup, mat mot cycle, trigger sai va cua so bien mat.

BUOC 3 - PHONG VE
  Do dong co the mo: ADC invalid, trigger sai/blind -> MEASUREMENT; cycle
  lap/mat -> SEQUENCE; bat ky pha do/tai tao >25 A -> OVERCURRENT. Loi chot
  dong cong drive, khong tu clear. Nguong mo phong, khong la comparator bao
  ve ngan mach. Caller phai goi theo cycle; khong co watchdog doc lap neu CPU
  dung. Muc +/-6 V giu duty trong cua so cho demo, khong toi uu bus utilization.
  Plant averaged bo qua ripple, deadtime voltage, skew microsecond trong cycle,
  back-EMF, rotor motion va saturation motor; day KHONG la full PMSM FOC.
  PWM/drive_enabled la du lieu mo phong, khong ghi hardware/STO. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va python -m unittest discover -s tests -v; commit/push BT.4.
  Nguon current acquisition: https://www.ti.com/lit/an/slyt762/slyt762.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from current_edge_pwm_sampling_windows import PwmTiming
from current_edge_shunt_afe_calibration import Calibration, ShuntAFE, calibrate
from current_edge_two_shunt_reconstruction import TwoShuntFrame, reconstruct


class PIController:
    def __init__(self, kp: float = 2, ki: float = 800, limit_v: float = 6) -> None:
        if not all(math.isfinite(v) and v > 0 for v in (kp, ki, limit_v)):
            raise ValueError("PI gains/limit phai huu han, duong")
        self.kp, self.ki, self.limit_v = kp, ki, limit_v
        self.integral = 0.0

    def step(self, error: float, dt: float) -> float:
        if not math.isfinite(error) or not math.isfinite(dt) or dt <= 0:
            raise ValueError("PI error/dt khong hop le")
        raw = self.kp * error + self.integral
        voltage = max(-self.limit_v, min(self.limit_v, raw))
        if abs(raw) <= self.limit_v or (raw > self.limit_v and error < 0) or (raw < -self.limit_v and error > 0):
            self.integral += self.ki * error * dt
        return voltage


@dataclass
class RLPlant:
    alpha: float = 0.0
    beta: float = 0.0
    resistance_ohm: float = 0.4
    inductance_h: float = 0.001

    def __post_init__(self) -> None:
        if (not all(math.isfinite(v) for v in vars(self).values())
                or min(self.resistance_ohm, self.inductance_h) <= 0):
            raise ValueError("RL plant khong hop le")

    def step(self, voltage_alpha: float, voltage_beta: float, dt: float) -> None:
        if not all(math.isfinite(v) for v in (voltage_alpha, voltage_beta, dt)) or dt <= 0:
            raise ValueError("Plant voltage/dt khong hop le")
        decay = math.exp(-self.resistance_ohm * dt / self.inductance_h)
        self.alpha = voltage_alpha / self.resistance_ohm + (self.alpha - voltage_alpha / self.resistance_ohm) * decay
        self.beta = voltage_beta / self.resistance_ohm + (self.beta - voltage_beta / self.resistance_ohm) * decay


class CurrentLoop:
    def __init__(self, cal_a: Calibration, cal_b: Calibration) -> None:
        self.cal_a, self.cal_b = cal_a, cal_b
        self.timing = PwmTiming()
        self.pi_alpha, self.pi_beta = PIController(), PIController()
        self.last_cycle = -1
        self.drive_enabled = False
        self.fault: str | None = None
        self.voltage_alpha_beta = (0.0, 0.0)

    def step(self, frame: TwoShuntFrame, temp_c: float,
             previous_duties: tuple[float, float, float],
             iq_reference_a: float) -> tuple[float, float, float] | None:
        self.drive_enabled = False
        self.voltage_alpha_beta = (0.0, 0.0)
        if self.fault is not None:
            return None
        if not isinstance(frame.cycle, int) or frame.cycle != self.last_cycle + 1:
            self.fault = "SEQUENCE"
            return None
        if not math.isfinite(iq_reference_a):
            self.fault = "INPUT"
            return None
        try:
            currents = reconstruct(frame, self.cal_a, self.cal_b, temp_c, previous_duties, self.timing)
        except ValueError:
            self.fault = "MEASUREMENT"
            return None
        if max(abs(currents.ia), abs(currents.ib), abs(currents.ic)) > 25:
            self.fault = "OVERCURRENT"
            return None
        alpha, beta = currents.alpha_beta
        dt = self.timing.period_us * 1e-6
        va = self.pi_alpha.step(-alpha, dt)
        vb = self.pi_beta.step(iq_reference_a - beta, dt)
        phase_voltages = (va, -va / 2 + math.sqrt(3) * vb / 2,
                          -va / 2 - math.sqrt(3) * vb / 2)
        duties = tuple(0.5 + voltage / 24 for voltage in phase_voltages)
        self.voltage_alpha_beta = (va, vb)
        self.last_cycle = frame.cycle
        self.drive_enabled = True
        return duties


def simulate(cycles: int = 2000) -> tuple[CurrentLoop, RLPlant, list[float]]:
    afe_a, afe_b = ShuntAFE(), ShuntAFE(-70e-6, -0.003)
    loop = CurrentLoop(calibrate(afe_a), calibrate(afe_b))
    plant, duties, tail_errors = RLPlant(), (0.5, 0.5, 0.5), []
    for cycle in range(cycles):
        reference = 0.0 if cycle < 100 else (8.0 if cycle < 1000 else -5.0)
        ia = plant.alpha
        ib = -plant.alpha / 2 + math.sqrt(3) * plant.beta / 2
        window = loop.timing.choose(*duties[:2])
        assert window is not None
        frame = TwoShuntFrame(cycle, window.trigger_us, afe_a.convert(ia, 100), afe_b.convert(ib, 100))
        duties = loop.step(frame, 100, duties, reference)
        assert duties is not None and loop.fault is None
        plant.step(*loop.voltage_alpha_beta, loop.timing.period_us * 1e-6)
        if 800 <= cycle < 1000 or cycle >= 1800:
            tail_errors.append(plant.beta - reference)
    return loop, plant, tail_errors


def demo() -> None:
    loop, plant, errors = simulate()
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    assert rms < 0.03 and abs(plant.beta + 5) < 0.03
    print(f"BT.4: 20 kHz locked-rotor RL, tail RMS={rms:.6f} A, "
          f"final beta={plant.beta:.6f} A, fault={loop.fault}")


if __name__ == "__main__":
    demo()
