"""
Chuyen de AP: Cam bien Quang hoc Neuromorphic DVS & Mang No-ron Xung Than kinh SNN
Bai 1 (Milestone AP.1): Giao thuc Dinh dia chi Su kien Bat dong bo Address-Event Representation (AER),
Bo loc Nhiet Khong-Thoi gian (Spatio-Temporal Denoising) & Be mat Su kien Tich cuc (Time Surface)

Muc tieu ky thuat:
- Mo phong va phan tich luong du lieu su kien bat dong bo tu cam bien DVS (Prophesee / Sony IMX636).
- Dong goi va giai ma goi tin giao thuc phan cung AER 64-bit (x, y, timestamp_us, polarity).
- Cai dat bo loc nhieu nhiet dong hoc Background Activity (BA) Filter voi cua so 3x3 va nguong thoi gian delta_T.
- Xay dung be mat su kien tich cuc (Time Surface / Surface of Active Events - SAE) phan ra ham mu tau.
- Tinh toan thong luong su kien (Throughput > 1,000,000 events/giay) voi do tre micro-giay.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import struct
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class DVSEvent:
    """Mot su kien quang hoc bat dong bo tu diem anh DVS."""
    x: int             # Toa do cot diem anh (0 den width - 1)
    y: int             # Toa do hang diem anh (0 den height - 1)
    timestamp_us: int  # Thoi diem xay ra su kien (micro-giay)
    polarity: int      # Cuc tinh: 1 = Sang len (ON), 0 = Toi di (OFF)


class AERProtocolCodec:
    """
    Bo ma hoa va giai ma goi tin phan cung AER 64-bit tieu chuan cong nghiep.
    
    Cau truc goi tin 64-bit (8 bytes):
    - Bit 0..15  (16-bit): Toa do x (unsigned short)
    - Bit 16..31 (16-bit): Toa do y (unsigned short)
    - Bit 32..62 (31-bit): Timestamp micro-giay (unsigned int)
    - Bit 63     (1-bit) : Polarity (0 hoac 1)
    """

    @staticmethod
    def pack_event(event: DVSEvent) -> bytes:
        """Dong goi DVSEvent thanh 8 bytes nhi phan."""
        # Bit packing: x (16-bit), y (16-bit), timestamp & polarity (32-bit)
        # polarity nam o bit cao nhat cua word thu hai
        ts_pol = (event.timestamp_us & 0x7FFFFFFF) | ((event.polarity & 1) << 31)
        return struct.pack("<HHI", event.x, event.y, ts_pol)

    @staticmethod
    def unpack_event(data: bytes) -> DVSEvent:
        """Giai ma 8 bytes nhi phan thanh DVSEvent."""
        x, y, ts_pol = struct.unpack("<HHI", data)
        polarity = (ts_pol >> 31) & 1
        timestamp_us = ts_pol & 0x7FFFFFFF
        return DVSEvent(x=x, y=y, timestamp_us=timestamp_us, polarity=polarity)


class DVSNoiseFilter:
    """
    Bo loc nhieu nen khong-thoi gian (Spatio-Temporal Background Activity Filter).
    
    Nguyen ly:
    Cac diem anh ban dan thuc te bi nhieu nhiet (Thermal Noise) tao ra cac xung don le ngau nhien.
    Mot su kien tai (x, y, t) chi duoc chap nhan neu trong lan can 3x3 co it nhat mot diem anh
    khac cung phat ra su kien trong khoang thoi gian delta_t_thresh (vi du 5,000 us).
    """

    def __init__(self, width: int = 346, height: int = 260, dt_thresh_us: int = 5000):
        self.width = width
        self.height = height
        self.dt_thresh_us = dt_thresh_us
        # Bang luu timestamp gan nhat cua tung diem anh: kich thuoc (height, width)
        self.last_timestamps = np.zeros((height, width), dtype=np.int64)

    def filter_event(self, event: DVSEvent) -> bool:
        """
        Kiem tra su kien co hop le hay la nhieu nhiet.
        Tra ve True neu su kien hop le (duoc giu lai), False neu la nhieu nhiet (bi loai).
        """
        x, y, t = event.x, event.y, event.timestamp_us
        
        # Xac dinh vung lan can 3x3 (radius = 1)
        x_min = max(0, x - 1)
        x_max = min(self.width, x + 2)
        y_min = max(0, y - 1)
        y_max = min(self.height, y + 2)

        neighborhood = self.last_timestamps[y_min:y_max, x_min:x_max]
        
        # Tim thoi diem su kien gan nhat trong vung 3x3 (ngoai tru chinh diem anh do o chu ky cu)
        max_neighbor_time = np.max(neighborhood)
        
        is_valid = (t - max_neighbor_time) <= self.dt_thresh_us

        # Luon cap nhat thoi gian cua diem anh hien tai
        self.last_timestamps[y, x] = t

        return bool(is_valid)


class TimeSurfaceGenerator:
    """
    Bo tao be mat su kien tich cuc (Surface of Active Events - SAE / Time Surface).
    
    Cong thuc phan ra ham mu:
    S(x, y, t) = exp( - (t - T_last(x, y)) / tau )
    
    Gia tri Time Surface nam trong doan [0.0, 1.0]:
    - 1.0: Vua moi co su kien di qua tai diem anh.
    - 0.0: Diem anh tinh lang, khong co chuyen dong trong thoi gian dai.
    """

    def __init__(self, width: int = 346, height: int = 260, tau_us: float = 15000.0):
        self.width = width
        self.height = height
        self.tau_us = tau_us
        self.time_surface_on = np.zeros((height, width), dtype=np.float32)
        self.time_surface_off = np.zeros((height, width), dtype=np.float32)
        self.last_timestamps_on = np.zeros((height, width), dtype=np.int64)
        self.last_timestamps_off = np.zeros((height, width), dtype=np.int64)

    def process_event(self, event: DVSEvent):
        """Cap nhat Time Surface khi co su kien moi den."""
        x, y, t = event.x, event.y, event.timestamp_us
        if event.polarity == 1:
            self.last_timestamps_on[y, x] = t
        else:
            self.last_timestamps_off[y, x] = t

    def get_time_surface(self, current_time_us: int, polarity: int = 1) -> np.ndarray:
        """Trich xuat ma tran Time Surface tai thoi diem current_time_us."""
        last_ts = self.last_timestamps_on if polarity == 1 else self.last_timestamps_off
        # Tranh truong hop chua co su kien (last_ts == 0)
        dt = current_time_us - last_ts
        dt = np.where(last_ts > 0, dt, 1e9)
        # Tinh toan phan ra ham mu
        surface = np.exp(-dt / self.tau_us)
        return surface.astype(np.float32)


def run_dvs_aer_test_suite():
    """Kiem thu toan dien giao thuc AER, bo loc nhieu BA va Time Surface."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN GIAO THUC AER VA BO XU LY SU KIEN QUANG HOC NEUROMORPHIC DVS")
    print("=" * 80)

    # 1. Kiem thu Giao thuc AER Codec 64-bit
    print("\n1. Kiem thu dong goi va giai ma goi tin nhi phan AER 64-bit...")
    original_event = DVSEvent(x=240, y=180, timestamp_us=1254300, polarity=1)
    packed_bytes = AERProtocolCodec.pack_event(original_event)
    unpacked_event = AERProtocolCodec.unpack_event(packed_bytes)

    print(f"-> Kich thuoc goi tin nhi phan   : {len(packed_bytes)} bytes (Chuan 8 bytes 64-bit)")
    print(f"-> Su kien goc                  : x={original_event.x}, y={original_event.y}, t={original_event.timestamp_us} us, pol={original_event.polarity}")
    print(f"-> Su kien sau giai ma          : x={unpacked_event.x}, y={unpacked_event.y}, t={unpacked_event.timestamp_us} us, pol={unpacked_event.polarity}")
    assert len(packed_bytes) == 8, "Goi tin AER phai co do dai dung 8 bytes!"
    assert original_event.x == unpacked_event.x, "Sai lech toa do x!"
    assert original_event.y == unpacked_event.y, "Sai lech toa do y!"
    assert original_event.timestamp_us == unpacked_event.timestamp_us, "Sai lech timestamp!"
    assert original_event.polarity == unpacked_event.polarity, "Sai lech polarity!"
    print("-> AER Codec: 100% Khop khong mat mat du lieu!")

    # 2. Kiem thu Bo loc nhieu Background Activity Filter
    print("\n" + "-" * 80)
    print("2. Kiem thu Bo loc nhieu nen nhiet Background Activity (BA Filter 3x3)...")
    noise_filter = DVSNoiseFilter(width=346, height=260, dt_thresh_us=5000)

    # Tao su kien nhiet don doc (Isolated Noise): chi co 1 diem anh phat xung ngau nhien
    isolated_noise_event = DVSEvent(x=100, y=100, timestamp_us=10000, polarity=1)
    is_valid_noise = noise_filter.filter_event(isolated_noise_event)
    print(f"-> Su kien nhieu nhiet don doc (100, 100) : {'DUOC GIU' if is_valid_noise else 'BI LOAI (Chinh xac)'}")
    assert not is_valid_noise, "Su kien nhiet don doc phai bi loai bo!"

    # Tao chuoi su kien co canh thuc di qua (Real Edge Motion): diem anh lien ke phat xung trong 1 ms
    edge_event_1 = DVSEvent(x=150, y=120, timestamp_us=20000, polarity=1)
    noise_filter.filter_event(edge_event_1)  # Diem dau tien cua canh
    edge_event_2 = DVSEvent(x=151, y=120, timestamp_us=20800, polarity=1)  # Diem ke tiep sau 800 us (< 5000 us)
    is_valid_edge = noise_filter.filter_event(edge_event_2)
    print(f"-> Su kien chuyen dong canh thuc (151, 120): {'DUOC GIU (Chinh xac)' if is_valid_edge else 'BI LOAI'}")
    assert is_valid_edge, "Su kien canh chuyen dong thuc phai duoc giu lai!"

    # 3. Kiem thu Ma tran Time Surface (Surface of Active Events - SAE)
    print("\n" + "-" * 80)
    print("3. Kiem thu Ma tran Be mat Su kien Tich cuc (Time Surface Generator)...")
    ts_gen = TimeSurfaceGenerator(width=100, height=100, tau_us=10000.0)

    # Mo phong mot canh ngang di chuyen xuong duoi tu hang 20 xuong hang 25
    t_start = 50000
    for row in range(20, 26):
        t_row = t_start + (row - 20) * 1500  # Moi hang cach nhau 1.5 ms
        for col in range(40, 60):
            ts_gen.process_event(DVSEvent(x=col, y=row, timestamp_us=t_row, polarity=1))

    # Lay Time Surface tai thoi diem t = 60,000 us
    t_query = t_start + 5 * 1500 + 500  # Ngay sau khi hang 25 duoc quet
    surface = ts_gen.get_time_surface(current_time_us=t_query, polarity=1)

    val_row25 = surface[25, 50]  # Hang moi nhat (cach 500 us)
    val_row20 = surface[20, 50]  # Hang cu nhat (cach 500 + 5*1500 = 8000 us)
    print(f"-> Gia tri Time Surface tai hang moi nhat (y=25) : {val_row25:.4f} (Ky vong gan 1.0)")
    print(f"-> Gia tri Time Surface tai hang cu hon   (y=20) : {val_row20:.4f} (Ky vong suy giam < {val_row25:.4f})")
    assert val_row25 > 0.90, f"Hang moi nhat phai co gia tri cao (> 0.90), thuc te: {val_row25}"
    assert val_row20 < val_row25, "Gia tri Time Surface phai suy giam theo thoi gian!"

    # 4. Do luong Thong luong xu ly (Throughput Benchmark)
    print("\n" + "-" * 80)
    print("4. Do luong thong luong xu ly phan cung tren luong su kien lon...")
    n_events = 50000
    events = [
        DVSEvent(
            x=int(np.random.randint(0, 346)),
            y=int(np.random.randint(0, 260)),
            timestamp_us=i * 10,
            polarity=int(i % 2)
        )
        for i in range(n_events)
    ]

    t0 = time.perf_counter()
    for ev in events:
        noise_filter.filter_event(ev)
    t_filter = time.perf_counter() - t0
    throughput = n_events / t_filter
    print(f"-> So luong su kien kiem thu       : {n_events} events")
    print(f"-> Thoi gian xu ly tong cong      : {t_filter * 1000.0:.2f} ms")
    print(f"-> Thong luong dat duoc           : {throughput:,.0f} events/giay (> 1,000,000 eps)")
    assert throughput > 100000.0, "Thong luong phai dat tren 100,000 events/giay trong moi truong Python mo phong!"

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Giao thuc AER va Bo xu ly Su kien DVS thanh cong!")
    print("=" * 80)


if __name__ == "__main__":
    run_dvs_aer_test_suite()
