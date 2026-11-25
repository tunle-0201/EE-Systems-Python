"""EE MENTORSHIP - BAI 238 - BU.3: ENCODER SPEED & WRAP.

BUOC 1 - HOP CONG CU
  Encoder absolute 16-bit MOT vong co: code=round(theta/(2*pi)*65536) modulo 65536.
    delta_count = (new-old+N/2) modulo N - N/2
    omega_raw = delta_count * 2*pi/(N*dt) [rad/s co khi]
    alpha = 1-exp(-2*pi*cutoff_hz*dt)
    omega_filtered += alpha*(omega_raw-omega_filtered)
  SpeedEstimator.update(code,dt) luu code va tra toc do loc. Mau dau chi khoi
  tao, tra 0. Toi da 500 rad/s; reject dt neu max_speed*dt >= pi vi wrap mo ho.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh omega khi encoder 65530 -> 4, dt=1 ms. Quay thuan/nguoc qua 0
  nhieu lan; thu giam bits de thay nhieu luong tu cua phep dao ham.

BUOC 3 - PHONG VE
  Filter tao phase lag, khong lam tang do phan giai that. Gioi han toc do la
  gia dinh can co truoc; mat nguyen vong khong tu phat hien tu code wrapped.
  Validate dt/code truoc mutate. Chua co timestamp/replay check trong estimator;
  capstone quan ly cycle, sensor_ok. CPU/RAM O(1), khong giu lich su dai.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, so sai so toc do on dinh; commit/push BU.3.
  Nguon encoder: https://www.ti.com/lit/pdf/spmu207 (QEI position/velocity).
"""

import math


def encoder_code(theta: float, bits: int = 16) -> int:
    if not math.isfinite(theta) or not isinstance(bits,int) or not 2 <= bits <= 24:
        raise ValueError("Encoder theta/bits khong hop le")
    modulus = 1 << bits
    return round((theta % math.tau)/math.tau*modulus) % modulus


class SpeedEstimator:
    def __init__(self, bits: int = 16, cutoff_hz: float = 100, max_speed: float = 500) -> None:
        if not isinstance(bits,int) or not 2 <= bits <= 24:
            raise ValueError("bits phai trong 2..24")
        if not all(math.isfinite(v) and v > 0 for v in (cutoff_hz,max_speed)):
            raise ValueError("cutoff/max_speed phai duong")
        self.modulus = 1 << bits
        self.cutoff_hz, self.max_speed = cutoff_hz,max_speed
        self.previous: int | None = None
        self.speed = 0.0

    def update(self, code: int, dt: float) -> float:
        if not isinstance(code,int) or not 0 <= code < self.modulus:
            raise ValueError("Code encoder khong hop le")
        if not math.isfinite(dt) or dt <= 0 or self.max_speed*dt >= math.pi:
            raise ValueError("dt khong hop le hoac wrap co the mo ho")
        if self.previous is None:
            self.previous = code
            return self.speed
        delta = (code-self.previous+self.modulus//2) % self.modulus-self.modulus//2
        radians = delta*math.tau/self.modulus
        # Cho phep mot count luong tu tren gioi han vat ly.
        if abs(radians) > self.max_speed*dt + math.tau/self.modulus:
            raise ValueError("Encoder jump vuot gioi han toc do")
        alpha = -math.expm1(-math.tau*self.cutoff_hz*dt)
        self.speed += alpha*(radians/dt-self.speed)
        self.previous = code
        return self.speed


def demo() -> None:
    estimator = SpeedEstimator()
    dt, truth = 50e-6, 100.0
    for cycle in range(4000):
        estimator.update(encoder_code(truth*cycle*dt),dt)
    assert abs(estimator.speed-truth) < 0.1
    print(f"BU.3: mechanical truth=100 rad/s, estimated={estimator.speed:.6f} rad/s")


if __name__ == "__main__":
    demo()
