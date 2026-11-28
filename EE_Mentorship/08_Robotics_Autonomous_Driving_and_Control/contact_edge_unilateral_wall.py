"""EE MENTORSHIP - BAI 257 - BY.1: UNILATERAL KELVIN-VOIGT WALL.

BUOC 1 - HOP CONG CU
  Truc x duong huong VAO tuong; surface=0.01 m. penetration=max(0,x-surface).
  Khi x>surface: reaction=max(0,k*penetration+d*velocity), don vi N.
  Khi x<=surface: reaction=0. Reaction la DO LON duong, force tren robot la
  -reaction. Clamp zero khong cho tuong "hut" robot khi rut nhanh.
  Wall.force(x,v) tra N; stored_energy(x)=k*penetration^2/2 tra J.

BUOC 2 - BAI TOAN TU LAM
  k=2000 N/m, d=20 Ns/m, penetration=0.005 m, v=0.001 m/s. Tu tinh luc,
  nang luong va thu v=-1 m/s. Phan biet contact stiffness voi virtual stiffness.

BUOC 3 - PHONG VE
  Tuong penalty 1D, khong Hertzian contact, friction tangential, adhesion
  hay impact restitution. Clipped damper la mo hinh don gian; khong suy
  safety tu luc clamp. Chua co robot inertia trong khoi nay. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test sign va separation; commit/push BY.1.
  Nguon contact/force: https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-6-hybrid-motion-force-control/
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Wall:
    surface: float = 0.01
    stiffness: float = 2000.0
    damping: float = 20.0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in vars(self).values()) or self.stiffness<=0 or self.damping<0:
            raise ValueError("Wall k>0, d>=0, inputs huu han")

    def force(self,position: float,velocity: float) -> float:
        if not all(math.isfinite(v) for v in (position,velocity)):
            raise ValueError("Wall x/v phai huu han")
        if position<=self.surface:
            return 0.0
        return max(0.0,self.stiffness*(position-self.surface)+self.damping*velocity)

    def stored_energy(self,position: float) -> float:
        if not math.isfinite(position):
            raise ValueError("Wall x phai huu han")
        return self.stiffness*max(0.0,position-self.surface)**2/2


if __name__=="__main__":
    wall=Wall()
    print(f"BY.1: 5 mm penetration -> F={wall.force(0.015,0.001):.6f} N, "
          f"stored={wall.stored_energy(0.015):.6f} J")
