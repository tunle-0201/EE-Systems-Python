"""EE MENTORSHIP - BAI 258 - BY.2: FORCE SENSOR COUNTS & CALIBRATION.

BUOC 1 - HOP CONG CU
  Mo hinh sensor: V=0.52+0.0202*force_N; ADC unipolar 16-bit, Vref=3.3 V.
  nominal sensor co offset/gain khac thiet ke 0.5 V / 0.02 V/N.
  Hai mau tai chuan 0 va 20 N:
    zero_code=code_at_0; counts_per_N=(code_at_20-code_at_0)/20
    force_hat=(code-zero_code)/counts_per_N
  ForceSensor.sample(force,acquired_at) tra ForceFrame(timestamp,code,clipped).
  ForceCalibration.fit(zero,loaded,known_load) va decode(frame) tra N co dau.

BUOC 2 - BAI TOAN TU LAM
  Tu hieu chuan, thu 7.3 N ngoai tap fit. Chen rail clip va giai thich tai
  sao CRC/timestamp hop le khong du neu analog ADC da saturate.

BUOC 3 - PHONG VE
  Tai chuan biet truoc, zero khi KHONG tiep xuc. Khong auto-tare luc dang ep.
  Chua co noise, drift, cross-axis, ADC/PGA settling hay nonlinear sensor.
  Timestamp la metadata acquisition; freshness duoc kiem tra o BY.7.
  CPU/RAM O(1), hai he so calibration, khong dung black-box fitting.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test held-out force/clip; commit/push BY.2.
  Nguon force sensing: https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html
"""

from dataclasses import dataclass
import math

MAX_CODE=65535


@dataclass(frozen=True)
class ForceFrame:
    acquired_at: float
    code: int
    clipped: bool = False


class ForceSensor:
    def sample(self,force_n: float,acquired_at: float) -> ForceFrame:
        if not all(math.isfinite(v) for v in (force_n,acquired_at)):
            raise ValueError("Sensor inputs phai huu han")
        voltage=0.52+0.0202*force_n
        clipped=not 0<=voltage<=3.3
        code=round(max(0.0,min(3.3,voltage))/3.3*MAX_CODE)
        return ForceFrame(acquired_at,code,clipped)


@dataclass(frozen=True)
class ForceCalibration:
    zero_code: float
    counts_per_n: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.zero_code,self.counts_per_n)) or not 0<=self.zero_code<=MAX_CODE or self.counts_per_n<=0:
            raise ValueError("Force calibration khong hop le")

    @staticmethod
    def validate(frame: ForceFrame):
        if frame.clipped or not isinstance(frame.code,int) or not 0<=frame.code<=MAX_CODE:
            raise ValueError("ADC clip hoac code khong hop le")

    @classmethod
    def fit(cls,zero: ForceFrame,loaded: ForceFrame,known_load: float=20):
        cls.validate(zero)
        cls.validate(loaded)
        if not math.isfinite(known_load) or known_load<=0:
            raise ValueError("Tai chuan phai duong")
        return cls(zero.code,(loaded.code-zero.code)/known_load)

    def decode(self,frame: ForceFrame) -> float:
        self.validate(frame)
        return (frame.code-self.zero_code)/self.counts_per_n


def calibration_fixture(sensor: ForceSensor) -> ForceCalibration:
    return ForceCalibration.fit(sensor.sample(0,0),sensor.sample(20,0))


if __name__=="__main__":
    sensor=ForceSensor()
    estimate=calibration_fixture(sensor).decode(sensor.sample(7.3,0))
    print(f"BY.2: held-out 7.3 N -> calibrated={estimate:.8f} N")
