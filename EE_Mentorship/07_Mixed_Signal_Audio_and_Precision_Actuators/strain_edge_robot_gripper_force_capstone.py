"""EE MENTORSHIP - BAI 227 - MODULE BR.4: ROBOT GRIPPER FORCE AFE CAPSTONE.

BUOC 1 - HOP CONG CU
  Pipeline: full bridge -> ADC/PGA ratiometric -> thermal calibration -> FIR
  50/60 Hz -> ket qua 100 Hz. Nhanh RAW cung so sanh qua tai 80 N truoc FIR.
  GripperForceMonitor(calibration) luu tinh trang warmup, force va fault.
  update(now, sample, temp_c, sensor_ok=True): goi moi 1/1200 s; sample=None
  bao mat conversion. Tra drive_enabled, False khi warmup/mat mau/co loi.
  filtered_n la luc loc; measurement_time = now - 17.5 ms tai tick xuat FIR.
  last_valid la thoi diem nhan RAW hop le, khong phai timestamp mau loc.

BUOC 2 - BAI TOAN TU LAM
  Kep vat 40 N, nhiet tang 20 -> 50 degC, excitation dao dong 4.6..5.4 V,
  co nhieu 50/60 Hz. Tu ghep 3 bai va thu mot xung luc 90 N chi dai 1 mau.
  Tai sao kiem tra qua tai SAU FIR se bo sot xung ngan nay?

BUOC 3 - PHONG VE
  Loi OVERLOAD, ADC_CLIP, SENSOR, TEMPERATURE, CLOCK, TIMING hoac TIMEOUT
  duoc chot, khong tu clear. Deadline 5 ms kiem tra truoc khi nhan mau moi.
  Mat mau: dong cong drive, reset FIR, doi warmup lai; khong chen zero vao
  filter. Cadence RAW hop le sai >1% -> TIMING de bao ve tan so notch.
  sensor_ok la chan diagnostic tu ben ngoai; cau dut day khong nhat thiet
  lam ADC clip. Chua mo phong mach burnout/open-wire hay watchdog doc lap.
  drive_enabled chi la Boolean mo phong, khong phai torque command hay STO.
  Nhanh RAW nhay voi nhieu hon FIR; nguong/diagnostic cua san pham that can
  duoc thiet ke rieng. Khong co plant/control loop co khi trong bai nay.
  RAM O(44), CPU O(1) moi mau; chua co rang buoc hard real-time cua MCU.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va python -m unittest discover -s tests -v; commit/push BR.4.
  Nen tang AFE: https://www.ti.com/lit/an/sbaa532a/sbaa532a.pdf
"""

from __future__ import annotations

import math

from strain_edge_ratiometric_adc_filter import AdcReading, MainsRejector, RatiometricADC
from strain_edge_temperature_calibration import TemperatureCalibration, lab_calibration
from strain_edge_wheatstone_bridge import FullBridge


class GripperForceMonitor:
    SAMPLE_PERIOD_SEC = 1 / 1200
    TIMEOUT_SEC = 0.005
    OVERLOAD_N = 80.0

    def __init__(self, calibration: TemperatureCalibration, started_at: float = 0.0) -> None:
        if not math.isfinite(started_at):
            raise ValueError("started_at phai huu han")
        self.calibration = calibration
        self.started_at = started_at
        self.last_tick: float | None = None
        self.last_valid: float | None = None
        self.fir = MainsRejector()
        self.raw_n: float | None = None
        self.filtered_n: float | None = None
        self.measurement_time: float | None = None
        self.fault: str | None = None
        self.drive_enabled = False

    def update(self, now: float, sample: AdcReading | None,
               temp_c: float, sensor_ok: bool = True) -> bool:
        self.drive_enabled = False
        if self.fault is not None:
            return False
        if (not math.isfinite(now) or now < self.started_at
                or (self.last_tick is not None and now <= self.last_tick)):
            self.fault = "CLOCK"
            return False
        self.last_tick = now
        reference = self.started_at if self.last_valid is None else self.last_valid
        if now - reference >= self.TIMEOUT_SEC - 1e-12:
            self.fault = "TIMEOUT"
            return False
        if not sensor_ok:
            self.fault = "SENSOR"
            return False
        if sample is None:
            self.fir = MainsRejector()
            self.filtered_n = self.measurement_time = None
            return False
        if self.last_valid is not None and self.fir.samples:
            if abs(now - self.last_valid - self.SAMPLE_PERIOD_SEC) > self.SAMPLE_PERIOD_SEC * 0.01:
                self.fault = "TIMING"
                return False
        if sample.clipped:
            self.fault = "ADC_CLIP"
            return False
        if not math.isfinite(sample.ratio):
            self.fault = "SENSOR"
            return False
        try:
            force = self.calibration.force(sample.ratio, temp_c)
        except ValueError:
            self.fault = "TEMPERATURE"
            return False
        self.raw_n = force
        if abs(force) > self.OVERLOAD_N:
            self.fault = "OVERLOAD"
            return False
        self.last_valid = now
        filtered = self.fir.push(force)
        if filtered is not None:
            self.filtered_n = filtered
            self.measurement_time = now - self.fir.GROUP_DELAY_SEC
        self.drive_enabled = self.filtered_n is not None
        return self.drive_enabled


def demo() -> None:
    bridge, adc = FullBridge(), RatiometricADC()
    calibration = lab_calibration(bridge, adc)
    monitor = GripperForceMonitor(calibration)
    errors = []
    previous_measurement = None
    for k in range(2400):
        now = k / 1200
        temp = 20 + 30 * k / 2399
        excitation = 5 + 0.4 * math.sin(2 * math.pi * 0.5 * now)
        interference_n = math.sin(2 * math.pi * 50 * now) + 0.7 * math.sin(2 * math.pi * 60 * now)
        reading = bridge.sample(40 + interference_n, temp, excitation)
        sample = adc.quantize(reading.differential_v, excitation)
        monitor.update(now, sample, temp)
        assert monitor.fault is None
        if monitor.measurement_time != previous_measurement:
            errors.append(monitor.filtered_n - 40)
            previous_measurement = monitor.measurement_time
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    assert rms < 0.0001 and monitor.drive_enabled
    print(f"BR.4 nominal: outputs={len(errors)}, RMS={rms:.8f} N, temp=20..50 degC")

    # Xung qua tai chi mot mau: nhanh RAW phai dong cong ngay, truoc FIR.
    overload = bridge.sample(90, 50)
    assert not monitor.update(2.0, adc.quantize(overload.differential_v, 5), 50)
    assert monitor.fault == "OVERLOAD"
    assert not monitor.update(2 + 1/1200, sample, 50)

    missing = GripperForceMonitor(calibration)
    nominal = bridge.sample(40, 20)
    assert not missing.update(0, adc.quantize(nominal.differential_v, 5), 20)
    assert not missing.update(0.005, None, 20) and missing.fault == "TIMEOUT"
    print(f"BR.4 injected: pulse={monitor.fault}, lost_data={missing.fault}, drive gates closed")


if __name__ == "__main__":
    demo()
