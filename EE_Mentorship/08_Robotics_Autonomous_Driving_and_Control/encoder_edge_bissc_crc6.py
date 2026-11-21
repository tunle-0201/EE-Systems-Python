"""EE MENTORSHIP - BAI 222 - MODULE BQ.3: BISS-C SCD & CRC-6.

BUOC 1 - HOP CONG CU
  Day la KENH DU LIEU SCD cua mot encoder single-turn 18-bit:
    [position:18, MSB first] [nError:1] [nWarning:1] [CRC inverted:6]
  nError/nWarning = 1 khi binh thuong, 0 khi co trang thai tuong ung.
  CRC bao phu position VA status. Da thuc P(x) = x^6 + x + 1 = 0x43.
  Thanh ghi 6-bit khoi tao 0; moi bit: feedback = bit_in XOR bit_5;
  dich trai, cat ve 6-bit, XOR 0x03 neu feedback=1; cuoi dao 6 bit CRC.
  crc6(data, width): tinh CRC truoc khi dao, MSB-first, khong reflection.
  encode_scd(position, nerror, nwarning): ghep chinh xac 26 bit.
  decode_scd(bits): xac minh do dai/CRC, tra Sample chua status va goc.

                   position * 360
    angle_deg = --------------------     resolution = 0.00137329 deg
                       2^18

BUOC 2 - BAI TOAN TU LAM
  Tu dong goi goc 90 deg, lat tung bit du lieu/status/CRC. Chon CRC checker
  de chan du lieu hong; KHONG coi CRC hop le dong nghia cam bien khoe.

BUOC 3 - PHONG VE
  Day KHONG la full BiSS master: chua co ACK/Start/CDS, timeout dong bo duong
  day, RS-422, control communication hay BiSS Safety. Profile 18+2+6 la lua
  chon cho bai hoc; encoder that co do dai/CRC tuy datasheet. CRC khong chung
  minh tinh moi: khung cu lap lai van dung CRC. Can timestamp va kenh du phong.
  RAM O(26), CPU O(20)/khung; bit-array tuong ung shift register trong MCU.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo: round-trip va 26 loi single-bit deu bi chan; commit/push BQ.3.
  Nguon giao thuc va CRC:
  https://biss-interface.com/wp-content/uploads/2025/10/BiSS_C_protocol_D2en.pdf
  https://www.rls.si/eng/fileuploader/download/download/?d=0&file=custom%2Fupload%2FCRCD01_01.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

POSITION_BITS = 18
DATA_BITS = POSITION_BITS + 2
FRAME_BITS = DATA_BITS + 6
MODULUS = 1 << POSITION_BITS


def crc6(data: int, width: int) -> int:
    if width < 1 or not 0 <= data < (1 << width):
        raise ValueError("Du lieu vuot do dai CRC")
    crc = 0
    for shift in range(width - 1, -1, -1):
        feedback = ((crc >> 5) ^ (data >> shift)) & 1
        crc = (crc << 1) & 0x3F
        if feedback:
            crc ^= 0x03
    return crc


@dataclass(frozen=True)
class EncoderSample:
    position: int
    nerror: int
    nwarning: int

    @property
    def angle_deg(self) -> float:
        return self.position * 360.0 / MODULUS

    @property
    def healthy(self) -> bool:
        return self.nerror == 1 and self.nwarning == 1


def encode_scd(position: int, nerror: int = 1, nwarning: int = 1) -> tuple[int, ...]:
    if not isinstance(position, int) or not 0 <= position < MODULUS:
        raise ValueError("Position phai la so nguyen 18-bit")
    if nerror not in (0, 1) or nwarning not in (0, 1):
        raise ValueError("Status phai la bit")
    data = (position << 2) | (nerror << 1) | nwarning
    word = (data << 6) | (crc6(data, DATA_BITS) ^ 0x3F)
    return tuple((word >> k) & 1 for k in range(FRAME_BITS - 1, -1, -1))


def decode_scd(bits: Iterable[int]) -> EncoderSample:
    frame = tuple(bits)
    if len(frame) != FRAME_BITS or any(bit not in (0, 1) for bit in frame):
        raise ValueError("Khung SCD phai co dung 26 bit nhi phan")
    word = 0
    for bit in frame:
        word = (word << 1) | bit
    data, wire_crc = word >> 6, word & 0x3F
    if wire_crc != (crc6(data, DATA_BITS) ^ 0x3F):
        raise ValueError("CRC-6 mismatch")
    return EncoderSample(data >> 2, (data >> 1) & 1, data & 1)


def demo() -> None:
    frame = encode_scd(MODULUS // 4)
    sample = decode_scd(frame)
    caught = 0
    for k in range(FRAME_BITS):
        corrupt = list(frame)
        corrupt[k] ^= 1
        try:
            decode_scd(corrupt)
        except ValueError:
            caught += 1
    assert sample.healthy and sample.angle_deg == 90.0 and caught == FRAME_BITS
    assert not decode_scd(encode_scd(0, nerror=0)).healthy
    print(f"BQ.3: angle={sample.angle_deg:.3f} deg, "
          f"single-bit errors caught={caught}/{FRAME_BITS}")


if __name__ == "__main__":
    demo()
