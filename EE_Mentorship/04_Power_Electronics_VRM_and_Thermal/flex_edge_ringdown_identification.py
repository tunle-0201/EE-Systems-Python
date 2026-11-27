"""EE MENTORSHIP - BAI 249 - BW.2: RINGDOWN IDENTIFICATION.

BUOC 1 - HOP CONG CU
  Tha twist ban dau, do r=theta_m-theta_l. Tu cac dinh DUONG lien tiep:
    fd=1/mean(peak_time_difference)
    delta=ln(first_peak/last_peak)/(number_of_intervals)
    zeta=delta/sqrt((2*pi)^2+delta^2); fn=fd/sqrt(1-zeta^2).
  identify(config) mo phong 2 s tai 4 kHz; tra Identification(fn,fd,zeta).
  Day la measurement tu trace, khong tra thang fn cua config.

BUOC 2 - BAI TOAN TU LAM
  Tu trich dinh 3 diem, so fn suy ra voi cong thuc BW.1. Doi stiffness
  +20% va damping; phan biet tan so dao dong fd voi fn chua damping.

BUOC 3 - PHONG VE
  Phuong phap can mode underdamped, nhieu nho, khong co torque kich trong
  luc do. Reject zeta>=1, thieu dinh va amplitude khong giam. Chua xu ly
  multi-mode, noise hay peak interpolation. CPU O(N), RAM O(so dinh), trace
  khong duoc luu toan bo. Khong tu dong kich motor that.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, test thay doi model; commit/push BW.2.
  Nguon resonance tuning: https://www.kollmorgen.com/sites/default/files/AKD%20Tuning%20Guide.pdf
"""

from dataclasses import dataclass
import math
from flex_edge_two_inertia_plant import FlexibleShaft,ShaftConfig


@dataclass(frozen=True)
class Identification:
    natural_hz: float
    damped_hz: float
    zeta: float


def identify(config: ShaftConfig | None = None) -> Identification:
    plant=FlexibleShaft(config)
    if not 0<plant.config.zeta<1:
        raise ValueError("Can mode underdamped voi damping duong")
    plant.tm=0.01
    dt=0.00025
    peaks=[]
    older,previous=0.01,0.01
    for k in range(1,8001):
        plant.step(0,0,dt)
        current=plant.tm-plant.tl
        if previous>0 and previous>older and previous>=current:
            peaks.append(((k-1)*dt,previous))
        older,previous=previous,current
    if len(peaks)<3 or not peaks[0][1]>peaks[-1][1]>0:
        raise ValueError("Khong du dinh ringdown hop le")
    intervals=len(peaks)-1
    period=(peaks[-1][0]-peaks[0][0])/intervals
    decrement=math.log(peaks[0][1]/peaks[-1][1])/intervals
    zeta=decrement/math.hypot(math.tau,decrement)
    fd=1/period
    return Identification(fd/math.sqrt(1-zeta*zeta),fd,zeta)


if __name__=="__main__":
    r=identify()
    print(f"BW.2: identified fn={r.natural_hz:.6f} Hz, fd={r.damped_hz:.6f} Hz, zeta={r.zeta:.6f}")
