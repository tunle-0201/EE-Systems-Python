"""EE MENTORSHIP - BAI 241 - BU.6: ROTATING PMSM AXIS DRIVE CAPSTONE.

BUOC 1 - HOP CONG CU
  Plant PMSM dq quay -> encoder 16-bit -> speed LPF -> speed PI 1 kHz ->
  current PI 20 kHz + back-EMF feedforward -> voltage circle -> plant.
  Cong suat inverter 1.5*(vd*id+vq*iq) ghep DCLink va brake chopper.
  simulate() chay lich 1.5 s, tra DriveResult co RMS toc do
  on dinh, bus peak, dong peak, nang luong brake va loi guard.
  Gioi han slew lenh 400 rad/s^2, iq_ref +/-6 A. Idq ideal doc truc tiep tu
  plant; encoder chi uoc luong toc do. Chua co abc/Park acquisition hay PWM.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 5 bai: 0 -> +100 -> -60 -> 0 rad/s, them load torque 0.02 Nm.
  Quan sat omega CO KHI, omega DIEN, iq va bus khi ham. Thu brake failure
  hoac encoder diagnostic false va du doan cong drive se dong luc nao.

BUOC 3 - PHONG VE
  DriveGuard.check: cycle phai lien tiep; sensor_ok, bus [24,60] V, current
  magnitude <=8 A, |speed|<=200 rad/s. Fault chot, khong tu re-enable.
  Guard la Boolean logic, caller phai tick; khong watchdog/hardware STO.
  Plant averaged, sensors idq ideal, param dung chinh xac trong feedforward;
  RMS mo phong khong la ket qua hardware. Nguon diode khong gioi han cong
  suat, chopper averaged; khong the dung de dinh co linh kien/cong bo an toan.
  Co the kiem tra hoi tu RK4 bang dt nho hon trong tests, khong tang do
  chinh xac cam bien that. CPU O(cycles), state O(1), chi giu metrics.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va python -m unittest discover -s tests -v; commit/push BU.6.
  Nguon PMSM: https://ntrs.nasa.gov/api/citations/20210025115/downloads/PMSM_v6.pdf
"""

from dataclasses import dataclass
import math

from servo_edge_cascaded_pi_controller import CurrentPI, SpeedPI
from servo_edge_encoder_speed_estimator import SpeedEstimator, encoder_code
from servo_edge_pmsm_dq_plant import PMSM
from servo_edge_regenerative_dc_link import DCLink


class DriveGuard:
    def __init__(self) -> None:
        self.last_cycle = -1
        self.fault: str | None = None
        self.drive_enabled = False

    def check(self, cycle: int, bus: float, id_a: float, iq_a: float,
              speed: float, sensor_ok: bool = True) -> bool:
        self.drive_enabled = False
        if self.fault is not None:
            return False
        if not isinstance(cycle,int) or cycle != self.last_cycle+1:
            self.fault = "SEQUENCE"
        elif not sensor_ok:
            self.fault = "ENCODER"
        elif not all(math.isfinite(v) for v in (bus,id_a,iq_a,speed)):
            self.fault = "NONFINITE"
        elif not 24 <= bus <= 60:
            self.fault = "BUS"
        elif math.hypot(id_a,iq_a) > 8:
            self.fault = "OVERCURRENT"
        elif abs(speed) > 200:
            self.fault = "OVERSPEED"
        else:
            self.last_cycle = cycle
            self.drive_enabled = True
        return self.drive_enabled


@dataclass(frozen=True)
class DriveResult:
    speed_rms: float
    final_speed: float
    max_bus_v: float
    max_current_a: float
    brake_energy_j: float
    fault: str | None
    cycles: int


def simulate(duration_sec: float = 1.5, brake_available: bool = True,
             encoder_fault_cycle: int | None = None) -> DriveResult:
    if not math.isfinite(duration_sec) or duration_sec < 1.45:
        raise ValueError("Duration >=1.45 s de co day du cac doan kiem tra")
    motor, bus, estimator = PMSM(),DCLink(),SpeedEstimator()
    speed_pi, current_pi, guard = SpeedPI(),CurrentPI(),DriveGuard()
    dt = 50e-6
    ramp = iq_ref = error_squared = 0.0
    count = executed = 0
    max_bus, max_current = bus.voltage,0.0
    for cycle in range(round(duration_sec/dt)):
        now = cycle*dt
        omega = estimator.update(encoder_code(motor.theta),dt)
        if not guard.check(cycle,bus.voltage,motor.id,motor.iq,omega,
                           sensor_ok=cycle != encoder_fault_cycle):
            break
        target = 0.0 if now < 0.05 else (100.0 if now < 0.5 else (-60.0 if now < 1.0 else 0.0))
        if cycle % 20 == 0:
            ramp += max(-0.4,min(0.4,target-ramp))
            iq_ref = speed_pi.step(ramp,omega,0.001)
        applied = current_pi.step(motor.id,motor.iq,iq_ref,omega,bus.voltage,dt)
        previous_d, previous_q = motor.id,motor.iq
        load = 0.02 if 0.25 <= now < 0.9 else 0.0
        motor.step(applied.vd,applied.vq,load,dt)
        ac_power = 1.5*(applied.vd*(previous_d+motor.id)/2 + applied.vq*(previous_q+motor.iq)/2)
        bus.step(ac_power,dt,brake_available)
        max_bus = max(max_bus,bus.voltage)
        max_current = max(max_current,math.hypot(motor.id,motor.iq))
        if 0.4 <= now < 0.48 or 0.95 <= now < 0.99 or 1.4 <= now:
            error_squared += (motor.omega-target)**2
            count += 1
        executed += 1
    rms = math.sqrt(error_squared/count) if count else math.inf
    return DriveResult(rms,motor.omega,max_bus,max_current,bus.brake_energy_j,guard.fault,executed)


def demo() -> None:
    result = simulate()
    assert result.fault is None and result.speed_rms < 2
    assert result.max_bus_v < 60 and result.max_current_a < 8
    bad_encoder = simulate(encoder_fault_cycle=100)
    assert bad_encoder.fault == "ENCODER" and bad_encoder.cycles == 100
    print(f"BU.6: speed RMS={result.speed_rms:.6f} rad/s, final={result.final_speed:.6f} rad/s, "
          f"bus peak={result.max_bus_v:.6f} V, current peak={result.max_current_a:.6f} A, "
          f"brake energy={result.brake_energy_j:.6f} J, fault={result.fault}")
    print(f"BU.6 injected: encoder fault latched at cycle {bad_encoder.cycles}")


if __name__ == "__main__":
    demo()
