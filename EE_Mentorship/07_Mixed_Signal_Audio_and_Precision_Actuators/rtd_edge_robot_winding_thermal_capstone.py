"""EE MENTORSHIP - BAI 231 - MODULE BS.4: ROBOT WINDING THERMAL MONITOR.

BUOC 1 - HOP CONG CU
  Pt100 thermal RC -> excitation 0.5 mA ON 10/100 ms -> 2-phase 3-wire AFE
  -> CVD inverse -> gioi han dong dien Boolean/ratio theo nhiet do do duoc.
  TemperatureFrame(acquired_at, reading) giu timestamp luc do, KHAC luc nhan.
  WindingThermalMonitor(started_at=0).update(now, frame, sensor_ok=True):
    T >= 90 degC -> current_limit_ratio=0.5; T <= 85 -> tro lai 1.0
    T >= 120 degC -> OVER_TEMPERATURE chot, current_limit_ratio=0
  rate = abs(Tnew-Told)/(t_acq_new-t_acq_old); >10 degC/s -> SLEW chot.
  Day la nguong minh hoa do nguoi thiet ke chon, khong la rating dong co.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 3 bai de do nhiet cuon day. Thu 89 -> 91 -> 88 -> 84 degC va
  giai thich hysteresis. Chen lai khung cu moi 100 ms: tai sao timestamp
  luc nhan khong du de phat hien cam bien khong cap nhat?

BUOC 3 - PHONG VE
  Mat mau: dong cong ngay; mau moi hop le co the mo lai truoc deadline.
  Qua 250 ms tinh tu acquisition cuoi -> TIMEOUT chot, check truoc mau moi.
  Frame cu >150 ms, timestamp lap/giam -> STALE; future timestamp -> CLOCK.
  SENSOR, ADC_CLIP, SENSOR_RANGE, SLEW va OVER_TEMPERATURE deu chot.
  sensor_ok la diagnostic ben ngoai, chua co burnout circuit. Loi R hop le
  nhung cam bien ket tai mot gia tri van co the khong bi phat hien; can kenh
  nhiet du phong. Nhiet do Pt100 co thermal lag, chua phai hotspot winding.
  current_limit_ratio chi la de xuat mo phong, khong co FOC/plant/STO that.
  Caller phai goi update ca khi frame=None; watchdog khong chay nen doc lap.
  Mo hinh nhiet coi RTD co dong suot 10 ms ON; chua tach thoi gian MUX hai
  pha, nen cong suat RTD duoc mo hinh bao thu so voi phase B->C khong qua RTD.
  RAM O(1), CPU O(48) cho CVD moi frame 10 Hz; chua chung minh real-time MCU.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va python -m unittest discover -s tests -v; commit/push BS.4.
  Nen tang: https://www.ti.com/lit/an/sbaa275a/sbaa275a.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from rtd_edge_pt100_callendar_van_dusen import resistance, temperature
from rtd_edge_self_heating_pulsed_excitation import ThermalRTD, excitation_on
from rtd_edge_three_wire_ratiometric import RTDReading, ThreeWireAFE


@dataclass(frozen=True)
class TemperatureFrame:
    acquired_at: float
    reading: RTDReading


class WindingThermalMonitor:
    TIMEOUT_SEC = 0.250
    MAX_AGE_SEC = 0.150
    MAX_SLEW_C_PER_SEC = 10.0

    def __init__(self, started_at: float = 0.0) -> None:
        if not math.isfinite(started_at):
            raise ValueError("started_at phai huu han")
        self.started_at = started_at
        self.last_tick: float | None = None
        self.last_acquired: float | None = None
        self.temperature_c: float | None = None
        self.derated = False
        self.drive_enabled = False
        self.current_limit_ratio = 0.0
        self.fault: str | None = None

    def update(self, now: float, frame: TemperatureFrame | None,
               sensor_ok: bool = True) -> bool:
        self.drive_enabled = False
        self.current_limit_ratio = 0.0
        if self.fault is not None:
            return False
        if (not math.isfinite(now) or now < self.started_at
                or (self.last_tick is not None and now <= self.last_tick)):
            self.fault = "CLOCK"
            return False
        self.last_tick = now
        reference = self.started_at if self.last_acquired is None else self.last_acquired
        if now - reference >= self.TIMEOUT_SEC - 1e-12:
            self.fault = "TIMEOUT"
            return False
        if not sensor_ok:
            self.fault = "SENSOR"
            return False
        if frame is None:
            return False
        acquired = frame.acquired_at
        if not math.isfinite(acquired) or acquired > now or acquired < self.started_at:
            self.fault = "CLOCK"
            return False
        if (now - acquired > self.MAX_AGE_SEC + 1e-12
                or (self.last_acquired is not None and acquired <= self.last_acquired)):
            self.fault = "STALE"
            return False
        if frame.reading.clipped:
            self.fault = "ADC_CLIP"
            return False
        try:
            measured = temperature(frame.reading.resistance_ohm)
        except ValueError:
            self.fault = "SENSOR_RANGE"
            return False
        if measured >= 120:
            self.fault = "OVER_TEMPERATURE"
            return False
        if self.last_acquired is not None:
            rate = abs(measured - self.temperature_c) / (acquired - self.last_acquired)
            if rate > self.MAX_SLEW_C_PER_SEC:
                self.fault = "SLEW"
                return False
        if measured >= 90:
            self.derated = True
        elif measured <= 85:
            self.derated = False
        self.temperature_c = measured
        self.last_acquired = acquired
        self.current_limit_ratio = 0.5 if self.derated else 1.0
        self.drive_enabled = True
        return True


def demo() -> None:
    sensor, afe, monitor = ThermalRTD(80), ThreeWireAFE(), WindingThermalMonitor()
    errors = []
    for tick in range(10000):
        environment = 80 + 0.5 * (tick + 1) / 1000
        on = excitation_on(tick)
        sensed = sensor.step(environment, 0.0005 if on else 0, 0.001)
        if tick % 100 == 9:
            now = (tick + 1) / 1000
            frame = TemperatureFrame(now, afe.convert(resistance(sensed)))
            assert monitor.update(now, frame)
            errors.append(monitor.temperature_c - sensed)
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    assert rms < 0.0002 and monitor.fault is None
    print(f"BS.4: frames={len(errors)}, AFE/CVD RMS={rms:.8f} degC, "
          f"sensor={sensor.sensor_temp_c:.4f} degC, environment={environment:.4f} degC")

    hot = WindingThermalMonitor()
    assert not hot.update(0, TemperatureFrame(0, RTDReading(resistance(125))))
    assert hot.fault == "OVER_TEMPERATURE"
    replay = WindingThermalMonitor()
    frame = TemperatureFrame(0, afe.convert(resistance(80)))
    assert replay.update(0, frame)
    assert not replay.update(0.1, frame) and replay.fault == "STALE"
    print(f"BS.4 injected: hot={hot.fault}, replay={replay.fault}, drive gates closed")


if __name__ == "__main__":
    demo()
