"""EE MENTORSHIP - BAI 239 - BU.4: CASCADED SPEED/CURRENT PI.

BUOC 1 - HOP CONG CU
  Vong ngoai 1 kHz: error=omega_ref-omega; iq_ref=clip(kp_w*error+int_w,+/-6 A).
  Conditional integration chi tich phan khi chua saturation hoac dang unwind.
  Vong trong 20 kHz, id_ref=0, iq_ref tu vong toc do:
    vd_raw = kp_i*(-id) + int_d - omega_e*Lq*iq
    vq_raw = kp_i*(iq_ref-iq) + int_q + omega_e*(Ld*id+psi)
  Hai so hang omega_e la feedforward khu ghep va back-EMF, khong phai PI gain.
  Limit vector theo bus truoc khi cap plant. Back-calculation anti-windup:
    int_d += dt*(ki_i*error_d + kaw*(vd_applied-vd_raw))
    int_q += dt*(ki_i*error_q + kaw*(vq_applied-vq_raw))
  SpeedPI.step va CurrentPI.step luu trang thai O(1); CurrentPI tra VoltageVector.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep vong toc do cham hon vong dong 20 lan. Thu yeu cau dong qua lon
  khi bus 12 V; so integral khi co/khong co anti-windup va khi bo lenh qua tai.

BUOC 3 - PHONG VE
  Gains minh hoa, khong tu dam bao on dinh cho motor bat ky. Feedforward
  phu thuoc dung p/L/flux va toc do CO KHI; nham co/dien se nhan sai pole pairs.
  Chua co MTPA, field weakening, thermal derating hay tuning tu dong. Doc idq
  trong capstone la ideal sensor, khong tich hop AFE/PWM BT. Reject nonfinite
  va dt<=0. CPU/RAM O(1); caller quyet dinh tan so hai vong.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo saturation/recovery; commit/push BU.4.
  Nguon dq: https://ntrs.nasa.gov/api/citations/20210025115/downloads/PMSM_v6.pdf
"""

import math

from servo_edge_pmsm_dq_plant import MotorConfig
from servo_edge_voltage_circle_limiter import VoltageVector, limit_voltage


def validate_step(*values: float, dt: float) -> None:
    if not all(math.isfinite(v) for v in (*values,dt)) or dt <= 0:
        raise ValueError("Control inputs/dt khong hop le")


class SpeedPI:
    def __init__(self) -> None:
        self.kp, self.ki, self.limit_a = 0.08,2.0,6.0
        self.integral = 0.0

    def step(self, reference: float, measured: float, dt: float) -> float:
        validate_step(reference,measured,dt=dt)
        error = reference-measured
        raw = self.kp*error+self.integral
        output = max(-self.limit_a,min(self.limit_a,raw))
        if abs(raw) <= self.limit_a or (raw > self.limit_a and error < 0) or (raw < -self.limit_a and error > 0):
            self.integral += self.ki*error*dt
        return output


class CurrentPI:
    def __init__(self, config: MotorConfig | None = None) -> None:
        self.config = config if config is not None else MotorConfig()
        self.kp, self.ki, self.kaw = 2.0,800.0,400.0
        self.integral_d = self.integral_q = 0.0

    def step(self, id_a: float, iq_a: float, iq_ref: float,
             omega_mechanical: float, vbus: float, dt: float) -> VoltageVector:
        validate_step(id_a,iq_a,iq_ref,omega_mechanical,vbus,dt=dt)
        c = self.config
        we = c.pole_pairs*omega_mechanical
        ed, eq = -id_a,iq_ref-iq_a
        vd = self.kp*ed+self.integral_d-we*c.lq*iq_a
        vq = self.kp*eq+self.integral_q+we*(c.ld*id_a+c.flux)
        result = limit_voltage(vd,vq,vbus)
        self.integral_d += dt*(self.ki*ed+self.kaw*(result.vd-vd))
        self.integral_q += dt*(self.ki*eq+self.kaw*(result.vq-vq))
        return result


def demo() -> None:
    pi = CurrentPI()
    for _ in range(10000):
        result = pi.step(0,0,50,0,12,50e-6)
    assert result.saturated and abs(pi.integral_q) < 100
    print(f"BU.4: forced saturation integral_q={pi.integral_q:.6f} V, "
          f"applied={result.vq:.6f} V, speed-loop limit={SpeedPI().limit_a:.1f} A")


if __name__ == "__main__":
    demo()
