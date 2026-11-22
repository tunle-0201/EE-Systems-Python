"""EE MENTORSHIP - BAI 225 - MODULE BR.2: RATIOMETRIC ADC & 50/60 HZ FIR.

BUOC 1 - HOP CONG CU
  ADC bipolar 24-bit ly tuong + PGA gain=128, Vref cung nguon voi Vexc:
    normalized = gain * Vdiff / Vref
    code = round(normalized * 2^23), kep vao [-2^23, 2^23-1]
    ratio_hat = code / (2^23 * gain), neu Vref=Vexc.
  Quantize(vdiff, vref) tra AdcReading(ratio, clipped). PGA/ADC ly tuong;
  day khong la mo phong modulator delta-sigma hay 24-bit do chinh xac that.

  Moving average N mau: y[k] = (x[k]+...+x[k-N+1])/N.
  Fs=1200 Hz: N=24 co zero tai 50 Hz, N=20 co zero tai 60 Hz.
  Noi tiep hai FIR -> zeros ca hai tan so, DC gain=1, group delay:
    delay = ((24-1)+(20-1)) / (2*1200) = 0.0175 sec
  MainsRejector.push(ratio): tra None khi chua du 43 mau, sau do tra mean
  moi 12 mau (100 Hz). Khong zero-pad de tranh sai luc luc khoi dong.

BUOC 2 - BAI TOAN TU LAM
  Tin hieu 40 N co nhieu 50 Hz 1 N va 60 Hz 0.7 N. Tu chon Vref va hai
  cua so FIR. So RMS truoc/sau, thu 49 Hz de thay gioi han notch co dinh.

BUOC 3 - PHONG VE
  ADC clip phai bao loi, khong dung ket qua kep nhu phep do hop le. Doi
  Vref khong dong bo voi Vexc se mat tinh ratiometric. Loc so khong thay
  anti-alias analog; notch chi chinh xac tai Fs/tan so gia dinh. Tre 17.5 ms
  co the che qua tai ngan: can nhanh bao ve doc RAW truoc bo loc.
  RAM O(24+20); running sums/deque cho CPU O(1) moi mau.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, so RMS va excitation drift; commit/push BR.2.
  Nguon ratiometric: https://www.ti.com/lit/an/sbaa532a/sbaa532a.pdf
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AdcReading:
    ratio: float
    clipped: bool


class RatiometricADC:
    def __init__(self, bits: int = 24, gain: float = 128.0) -> None:
        if not isinstance(bits, int) or not 2 <= bits <= 32:
            raise ValueError("bits phai trong 2..32")
        if not math.isfinite(gain) or gain <= 0:
            raise ValueError("PGA gain phai duong va huu han")
        self.scale = 1 << (bits - 1)
        self.gain = gain

    def quantize(self, differential_v: float, reference_v: float) -> AdcReading:
        if not all(math.isfinite(v) for v in (differential_v, reference_v)) or reference_v <= 0:
            raise ValueError("Dien ap phai huu han, reference > 0")
        normalized = differential_v / reference_v * self.gain
        if not math.isfinite(normalized):
            raise ValueError("Ty so ADC tran")
        clipped = normalized < -1 or normalized > (self.scale - 1) / self.scale
        code = max(-self.scale, min(self.scale - 1, round(normalized * self.scale)))
        return AdcReading(code / (self.scale * self.gain), clipped)


class MovingAverage:
    def __init__(self, length: int) -> None:
        if not isinstance(length, int) or length < 1:
            raise ValueError("Window length phai nguyen duong")
        self.length = length
        self.values: deque[float] = deque()
        self.total = 0.0

    def push(self, value: float) -> float | None:
        if not math.isfinite(value):
            raise ValueError("Khong dua NaN/inf vao bo loc")
        if len(self.values) == self.length:
            self.total -= self.values.popleft()
        self.values.append(value)
        self.total += value
        return self.total / self.length if len(self.values) == self.length else None


class MainsRejector:
    SAMPLE_RATE_HZ = 1200
    OUTPUT_RATE_HZ = 100
    GROUP_DELAY_SEC = 0.0175

    def __init__(self) -> None:
        self.first = MovingAverage(24)
        self.second = MovingAverage(20)
        self.samples = 0

    def push(self, ratio: float) -> float | None:
        first = self.first.push(ratio)
        self.samples += 1
        if first is None:
            return None
        second = self.second.push(first)
        return second if self.samples % 12 == 0 else None


def demo() -> None:
    adc, fir = RatiometricADC(), MainsRejector()
    raw_errors, filtered_errors = [], []
    for k in range(2400):
        t = k / fir.SAMPLE_RATE_HZ
        noise_n = math.sin(2 * math.pi * 50 * t) + 0.7 * math.sin(2 * math.pi * 60 * t)
        ratio = (40 + noise_n) * 0.002 / 100
        excitation = 5 + 0.4 * math.sin(2 * math.pi * 0.5 * t)
        sample = adc.quantize(ratio * excitation, excitation)
        assert not sample.clipped
        raw_errors.append(sample.ratio * 100 / 0.002 - 40)
        filtered = fir.push(sample.ratio)
        if filtered is not None:
            filtered_errors.append(filtered * 100 / 0.002 - 40)
    rms = lambda errors: math.sqrt(sum(e * e for e in errors) / len(errors))
    assert rms(filtered_errors) < 0.0001
    print(f"BR.2: RMS raw={rms(raw_errors):.6f} N, filtered={rms(filtered_errors):.8f} N, "
          f"outputs={len(filtered_errors)}, delay={fir.GROUP_DELAY_SEC * 1000:.1f} ms")


if __name__ == "__main__":
    demo()
