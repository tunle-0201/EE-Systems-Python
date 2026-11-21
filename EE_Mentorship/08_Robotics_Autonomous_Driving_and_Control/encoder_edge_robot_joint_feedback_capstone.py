"""EE MENTORSHIP - BAI 223 - MODULE BQ.4: ROBOT JOINT FEEDBACK CAPSTONE.

BUOC 1 - HOP CONG CU
  Pipeline 1 kHz: sin/cos -> calibration -> 18-bit -> BiSS SCD -> CRC/status
  -> so sanh voi encoder quadrature da home cung moc -> cong cho phep torque.
  feed_edges() mo phong NGOAI VI dem moi canh, khong doc A/B chi moi 1 ms.
  |signed_delta(abs_angle, relative_angle)| <= tolerance_deg (0.4 deg).
  1 count = 360/4096 = 0.08789 deg; tolerance > sai so luong tu hai kenh.
  JointFeedbackMonitor(decoder, started_at, timeout_sec, tolerance_deg,
  mismatch_limit): watchdog 5 ms, 3 khung lech de chot DISAGREEMENT.
  update(now, frame): moi lan lay mau; frame=None khi khong nhan duoc.
  torque_enabled chi True khi MAU HIEN TAI hop le va chua co fault chot.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 3 bai: theo doi khop quay qua 360 deg va dao chieu. Chen bit hong,
  ABS bi ket, A/B mat canh, dut link; du doan khi nao cong torque bi dong.

BUOC 3 - PHONG VE
  CRC/status sai: bo mau, dong cong torque ngay; chi mau khoe tiep theo moi
  duoc mo lai. Qua 5 ms khong co mau duoc chap nhan -> TIMEOUT chot.
  Lech goc: dong cong ngay, 3 mau lech -> DISAGREEMENT chot. A/B nhay cheo
  -> QUADRATURE chot. Loi chot KHONG tu clear khi du lieu khoe tro lai.
  Homing la tien dieu kien; timestamp phai huu han, tang nghiem ngat.
  Hai cam bien duoc gia dinh doc lap, dong thoi va cung truc; khong mo hinh
  gear backlash, delay compensation, loi chung hay phanh co khi. Cong torque
  la Boolean mo phong, KHONG phai STO hay chung nhan an toan san pham.
  Khong co cam bien da vong: sai khac dung nguyen 360 deg khong phat hien.
  RAM O(1) cho monitor; CPU O(frame_bits) moi tick, O(edges) tai ngoai vi.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va tests/test_encoder_bq.py; cap nhat roadmap, commit/push BQ.4.
  Nguyen ly kenh SCD: https://biss-interface.com/wp-content/uploads/2025/10/BiSS_C_protocol_D2en.pdf
"""

from __future__ import annotations

import math
from typing import Iterable

from encoder_edge_bissc_crc6 import MODULUS, decode_scd, encode_scd
from encoder_edge_quadrature_abz import QuadratureDecoder, feed_edges
from encoder_edge_sincos_calibration import (
    SinCosCalibration, sensor_sample, signed_delta,
)


class JointFeedbackMonitor:
    def __init__(self, decoder: QuadratureDecoder, started_at: float = 0.0,
                 timeout_sec: float = 0.005, tolerance_deg: float = 0.4,
                 mismatch_limit: int = 3) -> None:
        if not decoder.homed:
            raise ValueError("Phai home encoder tai cung moc voi ABS truoc")
        if not all(math.isfinite(v) for v in (started_at, timeout_sec, tolerance_deg)):
            raise ValueError("Tham so phai huu han")
        if timeout_sec <= 0 or not 0 < tolerance_deg < 180:
            raise ValueError("Watchdog > 0; tolerance trong (0,180)")
        if not isinstance(mismatch_limit, int) or mismatch_limit < 1:
            raise ValueError("mismatch_limit phai nguyen duong")
        self.decoder = decoder
        self.started_at = started_at
        self.timeout_sec = timeout_sec
        self.tolerance_deg = tolerance_deg
        self.mismatch_limit = mismatch_limit
        self.initial_invalid = decoder.invalid_transitions
        self.previous_tick: float | None = None
        self.last_good: float | None = None
        self.angle_deg: float | None = None
        self.fault: str | None = None
        self.torque_enabled = False
        self.rejected_frames = 0
        self.mismatches = 0

    def update(self, now: float, frame: Iterable[int] | None) -> bool:
        self.torque_enabled = False
        if self.fault is not None:
            return False
        if (not math.isfinite(now) or now < self.started_at
                or (self.previous_tick is not None and now <= self.previous_tick)):
            self.fault = "CLOCK"
            return False
        self.previous_tick = now
        if not self.decoder.homed or self.decoder.invalid_transitions != self.initial_invalid:
            self.fault = "QUADRATURE"
            return False
        # Kiem tra deadline TRUOC mau moi: du lieu den muon khong xoa watchdog.
        reference = self.started_at if self.last_good is None else self.last_good
        if now - reference >= self.timeout_sec - 1e-12:
            self.fault = "TIMEOUT"
            return False
        if frame is None:
            return False
        try:
            sample = decode_scd(frame)
        except ValueError:
            self.rejected_frames += 1
            return False
        if not sample.healthy:
            self.rejected_frames += 1
            return False
        error = abs(signed_delta(sample.angle_deg, self.decoder.angle_deg))
        if error > self.tolerance_deg:
            self.mismatches += 1
            if self.mismatches >= self.mismatch_limit:
                self.fault = "DISAGREEMENT"
            return False
        self.mismatches = 0
        self.last_good = now
        self.angle_deg = sample.angle_deg
        self.torque_enabled = True
        return True


def make_monitor() -> JointFeedbackMonitor:
    decoder = QuadratureDecoder()
    decoder.home_at_index()  # Fixture demo bat dau chinh xac o moc ABS=0.
    return JointFeedbackMonitor(decoder)


def demo() -> None:
    cal = SinCosCalibration.calibrate(sensor_sample(k) for k in range(360))
    monitor = make_monitor()
    errors = []
    for tick in range(1000):
        # 0 -> 450 -> 0 deg: qua bien 360 theo ca hai chieu.
        truth = 450.0 * (1.0 - math.cos(2 * math.pi * tick / 1000)) / 2
        target = round(truth * monitor.decoder.counts_per_rev / 360)
        feed_edges(monitor.decoder, target - monitor.decoder.count)
        measured = cal.angle(*sensor_sample(truth))
        frame = list(encode_scd(round(measured * MODULUS / 360) % MODULUS))
        if tick == 250:
            frame[7] ^= 1
        enabled = monitor.update(tick * 0.001, frame)
        assert enabled == (tick != 250) and monitor.fault is None
        if enabled:
            errors.append(signed_delta(monitor.angle_deg, truth))
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    print(f"BQ.4 nominal: samples={len(errors)}, rejected={monitor.rejected_frames}, "
          f"RMS={rms:.6f} deg, fault={monitor.fault}")

    stuck = make_monitor()
    assert stuck.update(0.0, encode_scd(0))
    for tick in range(1, 4):
        feed_edges(stuck.decoder, 10)
        assert not stuck.update(tick * 0.001, encode_scd(0))
    assert stuck.fault == "DISAGREEMENT"
    assert not stuck.update(0.004, encode_scd(0))

    lost = make_monitor()
    assert lost.update(0.0, encode_scd(0))
    assert not lost.update(0.005, None) and lost.fault == "TIMEOUT"
    print(f"BQ.4 injected: stuck={stuck.fault}, lost_link={lost.fault}, "
          "torque gates closed")


if __name__ == "__main__":
    demo()
