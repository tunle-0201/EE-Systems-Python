"""EE MENTORSHIP - BAI 260 - BY.4: FORCE PI TO VELOCITY COMMAND.

BUOC 1 - HOP CONG CU
  Reaction F duong; muon ep manh hon thi tang x, nen error=Fref-Fmeasured.
    velocity=clip(kp*error+integral,+/-0.01 m/s)
    integral += ki*error*dt khi chua saturate hoac error dang unwind.
  kp=0.001 m/(N*s), ki=0.0005 m/(N*s^2). step(target,measured,dt) tra m/s.
  reset(velocity,error) dat integral=velocity-kp*error de dau ra ban dau
  khop voi velocity tiep can (bumpless transfer trong dieu kien chua limit).

BUOC 2 - BAI TOAN TU LAM
  Luc do 1 N, muc tieu 10 N, approach=0.005 m/s. Tu tinh integral reset,
  so voi reset integral=0. Thu sensor clip va yeu cau force rat lon.

BUOC 3 - PHONG VE
  PI can velocity actuator/servo ben trong, khong tu dieu khien motor.
  Gains phu thuoc do cung, delay, noise va contact dynamics; khong dam bao
  stability moi tuong. Clamp velocity khong la gioi han force hardware.
  CPU/RAM O(1); step reject dt/nonfinite truoc mutate.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test sign/anti-windup/reset; commit/push BY.4.
  Nguon force control: https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-5-force-control/
"""

import math


class ForcePI:
    def __init__(self,kp=0.001,ki=0.0005,velocity_limit=0.01):
        if not all(math.isfinite(v) and v>0 for v in (kp,ki,velocity_limit)):
            raise ValueError("PI gains/limit phai huu han, duong")
        self.kp,self.ki,self.velocity_limit=kp,ki,velocity_limit
        self.integral=0.0

    def reset(self,velocity: float,error: float):
        if not all(math.isfinite(v) for v in (velocity,error)) or abs(velocity)>self.velocity_limit:
            raise ValueError("Bumpless reset khong hop le")
        self.integral=velocity-self.kp*error

    def step(self,target: float,measured: float,dt: float) -> float:
        if not all(math.isfinite(v) for v in (target,measured,dt)) or target<0 or dt<=0:
            raise ValueError("Force PI inputs khong hop le")
        error=target-measured
        raw=self.kp*error+self.integral
        limited=max(-self.velocity_limit,min(self.velocity_limit,raw))
        if abs(raw)<=self.velocity_limit or (raw>self.velocity_limit and error<0) or (raw < -self.velocity_limit and error>0):
            self.integral+=self.ki*error*dt
        return limited


if __name__=="__main__":
    pi=ForcePI()
    pi.reset(0.005,9)
    print(f"BY.4: bumpless contact transition velocity={pi.step(10,1,0.001):.8f} m/s")
