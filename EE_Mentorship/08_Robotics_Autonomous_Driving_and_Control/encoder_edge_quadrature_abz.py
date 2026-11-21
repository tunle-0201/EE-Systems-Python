"""EE MENTORSHIP - BAI 220 - MODULE BQ.1: QUADRATURE A/B/Z.

BUOC 1 - HOP CONG CU (doc truoc khi xem code)
  A/B la hai tin hieu lech pha; chon chieu duong: 00 -> 01 -> 11 -> 10 -> 00.
  Moi canh hop le chi doi MOT bit. Bang tra cho +1/-1; giu nguyen cho 0.
  Hai bit doi cung luc la mat canh/nhieu: khong duoc doan chieu quay.

                 count * 360                 delta_count * 60
  angle_deg = ------------------   rpm = -------------------------
                4 * lines                  4 * lines * dt_sec

  lines = chu ky A/vong; x4 dem ca bon canh. Z la moc homing, KHONG tu dong
  xoa bo dem da vong. home_at_index() chi goi sau khi xac nhan moc Z ben ngoai.
  __init__(lines, initial_ab): cau hinh do phan giai va muc A/B ban dau.
  sample(a, b): xu ly tung canh; angle_deg: vi tri tuong doi nhieu vong.

BUOC 2 - BAI TOAN TU LAM
  Encoder 1024 lines quay +1 vong roi -1/4 vong. Tu chon bang tra va bo dem,
  tinh goc, chen 00 -> 11 va giai thich vi sao khong the khoi phuc xung da mat.

BUOC 3 - PHONG VE
  Lay mau moi canh, khong chi doc A/B o toc do control-loop 1 kHz. Loi hai bit
  duoc dem va dong bo lai muc A/B, nhung vi tri da mat phai home lai. Nhieu doi
  mot bit van co the giong canh that; can loc phan cung va kenh do du phong.
  RAM O(1), CPU O(1)/canh; day la mo phong logic, khong mo phong metastability.

BUOC 4 - KIEM CHUNG VA GIT
  Chay file nay, doi chieu 3072 counts = 270 deg, sau do commit/push BQ.1.
  Tham khao: https://www.ti.com/lit/pdf/spmu207 (Quadrature Encoder Interface).
"""

from __future__ import annotations


# State = (A << 1) | B. Gia tri None danh dau nhay cheo bat hop le.
TRANSITIONS = (
    (0, 1, -1, None),
    (-1, 0, None, 1),
    (1, None, 0, -1),
    (None, -1, 1, 0),
)
AB_CYCLE = (0, 1, 3, 2)


class QuadratureDecoder:
    def __init__(self, lines: int = 1024, initial_ab: int = 0) -> None:
        if not isinstance(lines, int) or lines <= 0 or initial_ab not in range(4):
            raise ValueError("lines phai nguyen duong; initial_ab trong 0..3")
        self.counts_per_rev = 4 * lines
        self.state = initial_ab
        self.count = 0
        self.invalid_transitions = 0
        self.homed = False

    def sample(self, a: int, b: int) -> int:
        if a not in (0, 1) or b not in (0, 1):
            raise ValueError("A/B phai la bit")
        new_state = (a << 1) | b
        step = TRANSITIONS[self.state][new_state]
        self.state = new_state
        if step is None:
            self.invalid_transitions += 1
            self.homed = False
            return 0
        self.count += step
        return step

    def home_at_index(self) -> None:
        """Lenh homing tu ben ngoai; khong goi moi khi Z len muc cao."""
        self.count = 0
        self.homed = True

    @property
    def angle_deg(self) -> float:
        return self.count * 360.0 / self.counts_per_rev


def feed_edges(decoder: QuadratureDecoder, steps: int) -> None:
    """Nguon kich thich demo: dua tung canh Gray code, ke ca chieu am."""
    phase = AB_CYCLE.index(decoder.state)
    direction = 1 if steps >= 0 else -1
    for _ in range(abs(steps)):
        phase = (phase + direction) % 4
        state = AB_CYCLE[phase]
        decoder.sample(state >> 1, state & 1)


def demo() -> None:
    decoder = QuadratureDecoder()
    decoder.home_at_index()
    feed_edges(decoder, 4096)
    feed_edges(decoder, -1024)
    assert decoder.count == 3072 and decoder.angle_deg == 270.0
    decoder.sample(1, 1)  # 00 -> 11: mat canh, khong tang count.
    assert decoder.invalid_transitions == 1 and not decoder.homed
    print(f"BQ.1: count={decoder.count}, angle={decoder.angle_deg:.3f} deg, "
          f"invalid={decoder.invalid_transitions}, homed={decoder.homed}")


if __name__ == "__main__":
    demo()
