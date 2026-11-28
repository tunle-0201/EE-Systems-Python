"""EE MENTORSHIP - BAI 263 - BY.7: CONTACT DATA/FORCE SUPERVISION.

BUOC 1 - HOP CONG CU
  ForceSupervisor(calibration,started_at=0).check(now,frame,x,velocity):
    now tang, cadence <=3 ms; khong co force frame duoc nhan >=20 ms -> TIMEOUT.
    acquisition phai tang, khong o tuong lai, age<=5 ms; ADC clip -> ADC.
    decoded force<-1 N -> FORCE_RANGE, >25 N -> OVERFORCE.
    x trong [-0.01,0.03] m, |v|<=0.01 m/s. Moi fault deu chot.
  last_acquired tinh theo timestamp luc do, khong theo luc frame duoc nhan.
  frame=None dong cong ngay, nhung co the nhan mau moi truoc deadline.

BUOC 2 - BAI TOAN TU LAM
  Lap lai cung frame moi 1 ms: vi sao cadence tot nhung STALE? Thu frame
  hop le den muon dung 20 ms, offset force am va clip analog.

BUOC 3 - PHONG VE
  Software sampled monitor, caller phai tick khi mat du lieu; khong hardware
  watchdog, STO, collision sensing hay full safety case. Cam bien freeze
  value nhung timestamp van moi khong chac bi phat hien. Encoder x/v ideal.
  Vrange/force nguong do bai hoc chon, khong la rating/con nguoi-safe limit.
  CPU/RAM O(1), fault can reset workflow ben ngoai.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/tests du lieu cu va force fault; commit/push BY.7.
  Nen tang force sensor: https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html
"""

import math
from contact_edge_force_sensor_calibration import ForceCalibration,ForceFrame


class ForceSupervisor:
    def __init__(self,calibration: ForceCalibration,started_at: float=0.0):
        if not math.isfinite(started_at):
            raise ValueError("started_at phai huu han")
        self.calibration,self.started_at=calibration,started_at
        self.last_tick=self.last_acquired=None
        self.force_n=None
        self.fault=None
        self.drive_enabled=False

    def check(self,now: float,frame: ForceFrame | None,position: float,velocity: float) -> bool:
        self.drive_enabled=False
        if self.fault is not None:
            return False
        if not all(math.isfinite(v) for v in (now,position,velocity)):
            self.fault="NONFINITE"
        elif now<self.started_at or (self.last_tick is not None and now<=self.last_tick):
            self.fault="CLOCK"
        elif self.last_tick is not None and now-self.last_tick>0.003+1e-12:
            self.fault="TIMING"
        elif not -0.01<=position<=0.03 or abs(velocity)>0.01+1e-12:
            self.fault="MOTION"
        if self.fault:
            return False
        self.last_tick=now
        reference=self.started_at if self.last_acquired is None else self.last_acquired
        if now-reference>=0.020-1e-12:
            self.fault="TIMEOUT"
            return False
        if frame is None:
            return False
        acquired=frame.acquired_at
        if not math.isfinite(acquired) or acquired>now or acquired<self.started_at:
            self.fault="CLOCK"
            return False
        if now-acquired>0.005+1e-12 or (self.last_acquired is not None and acquired<=self.last_acquired):
            self.fault="STALE"
            return False
        try:
            force=self.calibration.decode(frame)
        except ValueError:
            self.fault="ADC"
            return False
        if force < -1 or force>25:
            self.fault="FORCE_RANGE" if force < -1 else "OVERFORCE"
            return False
        self.force_n,self.last_acquired=force,acquired
        self.drive_enabled=True
        return True


if __name__=="__main__":
    from contact_edge_force_sensor_calibration import ForceSensor,calibration_fixture
    sensor=ForceSensor()
    supervisor=ForceSupervisor(calibration_fixture(sensor))
    frame=sensor.sample(10,0)
    assert supervisor.check(0,frame,0.015,0)
    assert not supervisor.check(0.001,frame,0.015,0)
    print(f"BY.7: replayed frame -> {supervisor.fault}")
