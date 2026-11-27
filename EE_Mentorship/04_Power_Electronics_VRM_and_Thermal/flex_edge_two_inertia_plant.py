"""EE MENTORSHIP - BAI 248 - BW.1: TWO-INERTIA FLEXIBLE SHAFT.

BUOC 1 - HOP CONG CU
  Motor va load noi bang lo xo xoan k [Nm/rad], damper c [Nm*s/rad]:
    twist=theta_m-theta_l; tau_s=k*twist+c*(omega_m-omega_l)
    Jm*domega_m/dt=tau_motor-tau_s
    Jl*domega_l/dt=tau_s-tau_load; dtheta/dt=omega
  Jm=0.0002, Jl=0.0008 kg*m^2, k=0.8, c=0.002.
  Mode relative co wn=sqrt(k*(1/Jm+1/Jl)), zeta=c*(1/Jm+1/Jl)/(2*wn).
  FlexibleShaft.step(torque,load,dt) dung RK4; energy=Jm*wm^2/2+Jl*wl^2/2
  +k*twist^2/2. Mat cong suat tren damper=c*(wm-wl)^2.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh tan so tu nhien va damping ratio. Khoi tao twist=0.01 rad, tha
  tu do; vi sao hai encoder khong cung goc du motor va load noi cung truc?

BUOC 3 - PHONG VE
  Direct-drive, khong gear ratio/backlash, friction voi dat, cogging hay
  motor dien. Torque actuator ly tuong; mode rigid-body khong bi kep vao dat.
  dt<=0.25 ms cho model minh hoa; RK4 khong dam bao moi tham so deu on dinh.
  Validate truoc mutate; CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va kiem tra energy; commit/push BW.1.
  Nguon co hoc: https://www.kollmorgen.com/sites/default/files/AKD%20Tuning%20Guide.pdf
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ShaftConfig:
    jm: float = 0.0002
    jl: float = 0.0008
    stiffness: float = 0.8
    damping: float = 0.002

    def __post_init__(self):
        if not all(math.isfinite(v) for v in vars(self).values()) or min(self.jm,self.jl,self.stiffness)<=0 or self.damping<0:
            raise ValueError("J/k >0, damping>=0, tat ca huu han")

    @property
    def natural_hz(self):
        return math.sqrt(self.stiffness*(1/self.jm+1/self.jl))/math.tau

    @property
    def zeta(self):
        return self.damping*(1/self.jm+1/self.jl)/(2*math.tau*self.natural_hz)


class FlexibleShaft:
    def __init__(self, config: ShaftConfig | None = None):
        self.config = config if config is not None else ShaftConfig()
        self.tm=self.wm=self.tl=self.wl=0.0

    def derivative(self,state,torque,load):
        tm,wm,tl,wl=state
        c=self.config
        shaft=c.stiffness*(tm-tl)+c.damping*(wm-wl)
        return wm,(torque-shaft)/c.jm,wl,(shaft-load)/c.jl

    def step(self,torque,load,dt):
        state=(self.tm,self.wm,self.tl,self.wl)
        if not all(math.isfinite(v) for v in (*state,torque,load,dt)) or not 0<dt<=0.00025:
            raise ValueError("Shaft input khong hop le, dt<=0.25 ms")
        a=self.derivative(state,torque,load)
        b=self.derivative(tuple(s+dt*k/2 for s,k in zip(state,a)),torque,load)
        c=self.derivative(tuple(s+dt*k/2 for s,k in zip(state,b)),torque,load)
        d=self.derivative(tuple(s+dt*k for s,k in zip(state,c)),torque,load)
        new=tuple(s+dt*(i+2*j+2*k+l)/6 for s,i,j,k,l in zip(state,a,b,c,d))
        if not all(math.isfinite(v) for v in new):
            raise ValueError("Shaft state tran")
        self.tm,self.wm,self.tl,self.wl=new

    @property
    def energy(self):
        c=self.config
        return (c.jm*self.wm**2+c.jl*self.wl**2+c.stiffness*(self.tm-self.tl)**2)/2


if __name__=="__main__":
    c=ShaftConfig()
    print(f"BW.1: natural={c.natural_hz:.6f} Hz, zeta={c.zeta:.6f}")
