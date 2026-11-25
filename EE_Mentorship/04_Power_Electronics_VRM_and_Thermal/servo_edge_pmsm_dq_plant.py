"""EE MENTORSHIP - BAI 236 - BU.1: ROTATING PMSM D-Q PLANT.

BUOC 1 - HOP CONG CU
  theta_e = pole_pairs * theta_m; omega_e = pole_pairs * omega_m.
  Amplitude-invariant dq, flux psi [Wb], L [H], R [ohm], J [kg*m^2]:
    did/dt = (vd - R*id + omega_e*Lq*iq)/Ld
    diq/dt = (vq - R*iq - omega_e*(Ld*id + psi))/Lq
    torque = 1.5*p*(psi*iq + (Ld-Lq)*id*iq)
    domega/dt = (torque - load_torque - friction*omega)/J
    dtheta/dt = omega
  MotorConfig giu tham so; PMSM.step(vd,vq,load_nm,dt) tich phan ca bon
  trang thai bang RK4, khong cap nhat lan luot lam sai ghep dien-co.
  Electrical input power = 1.5*(vd*id+vq*iq), khong phai chi vd*id+vq*iq.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh torque voi id=0, iq=2 A va back-EMF tai omega_m=100 rad/s.
  Thu vq=0 khi rotor dang quay: vi sao iq tro thanh am, tao torque ham?

BUOC 3 - PHONG VE
  Plant averaged, chua co PWM ripple, saturation, cogging, iron loss, gear
  backlash hay FOC firmware that. Tham so minh hoa, khong gan nhan motor cu
  the. RK4 van can dt du nho; gioi han buoc mo phong <=50 us. Chan nonfinite
  truoc khi mutate state. CPU/RAM O(1) moi buoc, 4 lan tinh derivative.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va doi chieu he so torque; commit/push BU.1.
  Nguon: https://www.mathworks.com/help/mcb/ref/pmsmtorqueestimator.html
  https://ntrs.nasa.gov/api/citations/20210025115/downloads/PMSM_v6.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MotorConfig:
    resistance: float = 0.4
    ld: float = 0.001
    lq: float = 0.001
    flux: float = 0.02
    pole_pairs: int = 4
    inertia: float = 0.0002
    friction: float = 0.0001

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in vars(self).values()):
            raise ValueError("Motor config phai huu han")
        if min(self.resistance, self.ld, self.lq, self.flux, self.inertia) <= 0 or self.friction < 0:
            raise ValueError("R/L/flux/J > 0 va friction >= 0")
        if not isinstance(self.pole_pairs, int) or self.pole_pairs < 1:
            raise ValueError("pole_pairs phai nguyen duong")


class PMSM:
    def __init__(self, config: MotorConfig | None = None) -> None:
        self.config = config if config is not None else MotorConfig()
        self.id = self.iq = self.omega = self.theta = 0.0

    def torque(self, id_a: float | None = None, iq_a: float | None = None) -> float:
        d = self.id if id_a is None else id_a
        q = self.iq if iq_a is None else iq_a
        c = self.config
        return 1.5 * c.pole_pairs * (c.flux * q + (c.ld - c.lq) * d * q)

    def _derivative(self, state: tuple[float, ...], vd: float, vq: float,
                    load: float) -> tuple[float, ...]:
        d, q, omega, _ = state
        c = self.config
        we = c.pole_pairs * omega
        return ((vd - c.resistance*d + we*c.lq*q)/c.ld,
                (vq - c.resistance*q - we*(c.ld*d + c.flux))/c.lq,
                (self.torque(d, q) - load - c.friction*omega)/c.inertia,
                omega)

    def step(self, vd: float, vq: float, load_nm: float, dt: float) -> None:
        state = (self.id, self.iq, self.omega, self.theta)
        if not all(math.isfinite(v) for v in (*state, vd, vq, load_nm, dt)) or not 0 < dt <= 50e-6:
            raise ValueError("Plant inputs phai huu han, 0 < dt <= 50 us")
        k1 = self._derivative(state, vd, vq, load_nm)
        k2 = self._derivative(tuple(s + dt*k/2 for s,k in zip(state,k1)), vd,vq,load_nm)
        k3 = self._derivative(tuple(s + dt*k/2 for s,k in zip(state,k2)), vd,vq,load_nm)
        k4 = self._derivative(tuple(s + dt*k for s,k in zip(state,k3)), vd,vq,load_nm)
        updated = tuple(s + dt*(a+2*b+2*c+d)/6 for s,a,b,c,d in zip(state,k1,k2,k3,k4))
        if not all(math.isfinite(v) for v in updated):
            raise ValueError("Plant state tran")
        self.id, self.iq, self.omega, self.theta = updated

    @property
    def stored_energy_j(self) -> float:
        c = self.config
        return 0.75*(c.ld*self.id**2 + c.lq*self.iq**2) + 0.5*c.inertia*self.omega**2


def demo() -> None:
    motor = PMSM()
    assert math.isclose(motor.torque(0, 2), 0.24)
    motor.omega = 100
    motor.step(0, 0, 0, 50e-6)
    assert motor.iq < 0
    print(f"BU.1: torque(2 A)=0.240 Nm, shorted spinning rotor iq={motor.iq:.6f} A")


if __name__ == "__main__":
    demo()
