"""EE MENTORSHIP - BAI 242 - BV.1: QUINTIC REST-TO-REST MOTION.

BUOC 1 - HOP CONG CU
  q(t)=q0+D*s(u), u=t/T, D=q1-q0, s=10*u^3-15*u^4+6*u^5.
  Dao ham theo THOI GIAN: v=D*s'(u)/T, a=D*s''(u)/T^2,
  jerk=D*s'''(u)/T^3. Hai dau co v=a=0.
  Cuc dai tren u trong [0,1]: |s'|=1.875, |s''|=10/sqrt(3), |s'''|=60.
  Chon T >= max(1.875*|D|/vmax, sqrt((10/sqrt(3))*|D|/amax),
                 cbrt(60*|D|/jmax)). Day la du thoi gian, KHONG time-optimal.
  QuinticMove(start,target,vmax,amax,jmax).sample(t) tra MotionPoint(q,v,a,j).

BUOC 2 - BAI TOAN TU LAM
  Tu tinh T de di -0.2 -> 0.6 rad voi vmax=1.5 rad/s, amax=6 rad/s^2,
  jmax=60 rad/s^3. Thu D am va D=0; so giai tich voi quet mau day.

BUOC 3 - PHONG VE
  Jerk huu han nhung co buoc nhay tai bien khi noi voi doan dung; khong C3.
  Khong replan giua luc dang chay tu v/a khac zero. Ngoai [0,T] giu vi tri
  dau/cuoi; D=0 tra doan dung voi T=0. Khong tinh torque, collision hay
  constraints motor. CPU/RAM O(1), khong luu mang quang duong.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test dao ham/bien/gioi han; commit/push BV.1.
  Nguon time scaling: https://modernrobotics.northwestern.edu/nu-gm-book-resource/9-1-and-9-2-point-to-point-trajectories-part-2-of-2/
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MotionPoint:
    position: float
    velocity: float = 0.0
    acceleration: float = 0.0
    jerk: float = 0.0


class QuinticMove:
    def __init__(self, start: float, target: float, vmax: float = 1.5,
                 amax: float = 6.0, jmax: float = 60.0) -> None:
        if not all(math.isfinite(v) for v in (start,target,vmax,amax,jmax)) or min(vmax,amax,jmax) <= 0:
            raise ValueError("Profile inputs phai huu han, limits >0")
        self.start, self.target, self.distance = start,target,target-start
        distance = abs(self.distance)
        self.duration = max(1.875*distance/vmax,
                            math.sqrt(10/math.sqrt(3)*distance/amax),
                            (60*distance/jmax)**(1/3)) if distance else 0.0

    def sample(self, time_sec: float) -> MotionPoint:
        if not math.isfinite(time_sec):
            raise ValueError("Time phai huu han")
        if self.duration == 0 or time_sec > self.duration:
            return MotionPoint(self.target)
        if time_sec < 0:
            return MotionPoint(self.start)
        u = time_sec/self.duration
        d, t = self.distance,self.duration
        return MotionPoint(self.start+d*(10*u**3-15*u**4+6*u**5),
                           d*(30*u**2-60*u**3+30*u**4)/t,
                           d*(60*u-180*u**2+120*u**3)/t**2,
                           d*(60-360*u+360*u**2)/t**3)


def demo() -> None:
    move = QuinticMove(-0.2,0.6)
    points = [move.sample(move.duration*k/1000) for k in range(1001)]
    peaks = tuple(max(abs(getattr(p,name)) for p in points) for name in
                  ("velocity","acceleration","jerk"))
    assert all(peak <= limit+1e-10 for peak,limit in zip(peaks,(1.5,6,60)))
    print(f"BV.1: T={move.duration:.6f} s, peaks v/a/j={peaks}")


if __name__ == "__main__":
    demo()
