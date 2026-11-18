"""
================================================================================
          MODULE AA: ROBOTIC KINODYNAMICS & AUTONOMOUS MOTION PLANNING
          MILESTONE AA.3: JERK-BOUNDED 7-SEGMENT S-CURVE MOTION PROFILER
================================================================================

TAI SAO PROFILE VAN TOC HINH THANG (TRAPEZOIDAL) BI CAM TRONG CO DIEN TU CHINH XAC?
- Profile hinh thang thong thuong co gia toc thay doi dot ngot (buoc nhay bac thang).
- Dao ham cua gia toc chinh la do giat (Jerk = da/dt).
- Khi gia toc nhay tu 0 len a_max trong thoi gian dt -> 0:
  Jerk = vo cung (infinity)!
- Tac hai thuc te tren xe tu hanh Tesla va tay may robot cong nghiep:
  1. Xung luc giat manh lam mon va vo banh rang hop so giam toc (gearbox backlash).
  2. Kich thich dao dong cong huong co hoc (mechanical resonance vibration).
  3. Banh xe bi truot tren mat duong, gay sai so dinh vi truyen dong (odometry drift).

SO DO 7 GIAI DOAN S-CURVE PROFILE TRIET TIEU JERK (ASCII DIAGRAM):

   Gia toc a(t)
        ^
  +a_max|      +───────+  (Phase 2: Const Accel)
        |     /         \
        |    /           \ (Phase 3: Ramp Down)
       0+───+             +─────────────────────+             +───> Thoi gian t
            | (Phase 1)   (Phase 4: Cruise)      \           /
            | Ramp Up                             \         / (Phase 7: Ramp to 0)
  -a_max|                                          +───────+
        |                                          (Phase 6: Const Decel)
        |                                 (Phase 5: Ramp Down Decel)

7 GIAI DOAN QUY DAO S-CURVE (ASCII MATH BLOCKS):

Giai doan 1 (T_j) : Jerk = +J_max       -> a tang tu 0 len +a_max
Giai doan 2 (T_a) : Jerk = 0            -> a = +a_max (Gia toc khong doi)
Giai doan 3 (T_j) : Jerk = -J_max       -> a giam tu +a_max ve 0 (Dat van toc v_max)
Giai doan 4 (T_v) : Jerk = 0, a = 0     -> v = v_max (Chay deu hanh trinh on dinh)
Giai doan 5 (T_j) : Jerk = -J_max       -> a giam tu 0 xuong -a_max (Bat dau ham phanh)
Giai doan 6 (T_a) : Jerk = 0            -> a = -a_max (Giam toc khong doi)
Giai doan 7 (T_j) : Jerk = +J_max       -> a tang tu -a_max ve 0 (Dung han em ai tai dich)

TOAN HOC QUAN HE THOI GIAN VA QUANG DUONG (ASCII MATH BLOCKS):

1. Thoi gian tang giat (Jerk Phase Time T_j):
         a_max
   T_j = ─────
         J_max

2. Thoi gian giu gia toc khong doi (Constant Accel Phase Time T_a):
         v_max - a_max * T_j
   T_a = ───────────────────
                a_max

3. Quang duong tang toc va giam toc (Doi xung):
            v_max * T_acc
   S_acc = ──────────────,   voi T_acc = 2 * T_j + T_a
                  2
   S_dec = S_acc

4. Quang duong va thoi gian chay deu (Cruise Phase):
   S_cruise = D_total - (S_acc + S_dec)

              S_cruise
   T_cruise = ────────
               v_max
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class SCurveProfile:
    """
    Bo tao quy dao S-Curve 7 doan voi do giat Jerk co gioi han (Jerk-Bounded).
    Dam bao gia toc va van toc hoan toan lien tuc C^2 khong gay xung luc co hoc.
    """

    def __init__(self, target_dist: float, v_max: float = 2.0, a_max: float = 1.0, j_max: float = 2.0):
        self.target_dist = float(target_dist)
        self.v_max = float(v_max)
        self.a_max = float(a_max)
        self.j_max = float(j_max)

        # 1. Tinh toan thoi gian jerk phase T_j
        self.tj = self.a_max / self.j_max
        dv_jerk = self.a_max * self.tj

        # Neu van toc cuc dai dat duoc truoc khi dat a_max
        if self.v_max < dv_jerk:
            self.tj = math.sqrt(self.v_max / self.j_max)
            self.a_max = self.tj * self.j_max
            self.ta = 0.0
        else:
            self.ta = (self.v_max - dv_jerk) / self.a_max

        self.t_acc = 2.0 * self.tj + self.ta
        self.s_acc = (self.v_max * self.t_acc) / 2.0
        self.s_dec = self.s_acc

        # 2. Kiem tra quang duong cruise
        if self.target_dist >= (self.s_acc + self.s_dec):
            self.s_cruise = self.target_dist - (self.s_acc + self.s_dec)
            self.t_cruise = self.s_cruise / self.v_max
        else:
            # Hanh trinh ngan, khong kip dat v_max
            # Tinh lai van toc thuc te dat duoc
            scale = math.sqrt(self.target_dist / (self.s_acc + self.s_dec))
            self.v_max *= scale
            self.a_max *= scale
            self.tj = self.a_max / self.j_max
            self.ta = 0.0
            self.t_acc = 2.0 * self.tj
            self.s_acc = self.target_dist / 2.0
            self.s_dec = self.s_acc
            self.s_cruise = 0.0
            self.t_cruise = 0.0

        # Cac moc thoi gian chuyen phase
        self.t1 = self.tj
        self.t2 = self.t1 + self.ta
        self.t3 = self.t2 + self.tj
        self.t4 = self.t3 + self.t_cruise
        self.t5 = self.t4 + self.tj
        self.t6 = self.t5 + self.ta
        self.t7 = self.t6 + self.tj

        self.total_duration = self.t7

    def sample(self, t: float) -> Tuple[float, float, float, float]:
        """
        Lay mau trang thai quy dao tai thoi diem t:
        Tra ve (vi tri s, van toc v, gia toc a, do giat j).
        """
        if t <= 0.0:
            return 0.0, 0.0, 0.0, 0.0
        if t >= self.total_duration:
            return self.target_dist, 0.0, 0.0, 0.0

        # Xac dinh do giat j(t) tai thoi diem t
        if t < self.t1:
            j = self.j_max
        elif t < self.t2:
            j = 0.0
        elif t < self.t3:
            j = -self.j_max
        elif t < self.t4:
            j = 0.0
        elif t < self.t5:
            j = -self.j_max
        elif t < self.t6:
            j = 0.0
        elif t < self.t7:
            j = self.j_max
        else:
            j = 0.0

        # Tinh toan gia toc, van toc, vi tri bang cong thuc giai tich lien tuc
        # Giai doan 1: 0 <= t < t1 (Jerk = +J_max)
        if t < self.t1:
            tau = t
            a = self.j_max * tau
            v = 0.5 * self.j_max * (tau ** 2)
            s = (1.0 / 6.0) * self.j_max * (tau ** 3)
            return s, v, a, j

        # Tinh trang thai tai moc t1
        s1 = (1.0 / 6.0) * self.j_max * (self.tj ** 3)
        v1 = 0.5 * self.j_max * (self.tj ** 2)
        a1 = self.a_max

        # Giai doan 2: t1 <= t < t2 (a = a_max)
        if t < self.t2:
            tau = t - self.t1
            a = a1
            v = v1 + a1 * tau
            s = s1 + v1 * tau + 0.5 * a1 * (tau ** 2)
            return s, v, a, j

        # Tinh trang thai tai moc t2
        s2 = s1 + v1 * self.ta + 0.5 * a1 * (self.ta ** 2)
        v2 = v1 + a1 * self.ta
        a2 = self.a_max

        # Giai doan 3: t2 <= t < t3 (Jerk = -J_max)
        if t < self.t3:
            tau = t - self.t2
            a = a2 - self.j_max * tau
            v = v2 + a2 * tau - 0.5 * self.j_max * (tau ** 2)
            s = s2 + v2 * tau + 0.5 * a2 * (tau ** 2) - (1.0 / 6.0) * self.j_max * (tau ** 3)
            return s, v, a, j

        # Tinh trang thai tai moc t3 (Hoan tat tang toc len v_max)
        s3 = self.s_acc
        v3 = self.v_max
        a3 = 0.0

        # Giai doan 4: t3 <= t < t4 (Chay deu v = v_max)
        if t < self.t4:
            tau = t - self.t3
            a = 0.0
            v = self.v_max
            s = s3 + self.v_max * tau
            return s, v, a, j

        # Tinh trang thai tai moc t4 (Bat dau giam toc)
        s4 = s3 + self.s_cruise
        v4 = self.v_max
        a4 = 0.0

        # Giai doan 5: t4 <= t < t5 (Jerk = -J_max)
        if t < self.t5:
            tau = t - self.t4
            a = -self.j_max * tau
            v = v4 - 0.5 * self.j_max * (tau ** 2)
            s = s4 + v4 * tau - (1.0 / 6.0) * self.j_max * (tau ** 3)
            return s, v, a, j

        # Tinh trang thai tai moc t5
        s5 = s4 + v4 * self.tj - (1.0 / 6.0) * self.j_max * (self.tj ** 3)
        v5 = v4 - 0.5 * self.j_max * (self.tj ** 2)
        a5 = -self.a_max

        # Giai doan 6: t5 <= t < t6 (a = -a_max)
        if t < self.t6:
            tau = t - self.t5
            a = a5
            v = v5 + a5 * tau
            s = s5 + v5 * tau + 0.5 * a5 * (tau ** 2)
            return s, v, a, j

        # Tinh trang thai tai moc t6
        s6 = s5 + v5 * self.ta + 0.5 * a5 * (self.ta ** 2)
        v6 = v5 + a5 * self.ta
        a6 = -self.a_max

        # Giai doan 7: t6 <= t < t7 (Jerk = +J_max, a ve 0)
        tau = t - self.t6
        a = a6 + self.j_max * tau
        v = v6 + a6 * tau + 0.5 * self.j_max * (tau ** 2)
        s = s6 + v6 * tau + 0.5 * a6 * (tau ** 2) + (1.0 / 6.0) * self.j_max * (tau ** 3)
        return s, v, a, j


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EDGE: 7-SEGMENT S-CURVE MOTION PROFILER")
    print("=========================================================\n")

    # 1. Khoi tao hanh trinh 10m voi gioi han v_max=2 m/s, a_max=1 m/s^2, j_max=2 m/s^3
    distance = 10.0
    profiler = SCurveProfile(target_dist=distance, v_max=2.0, a_max=1.0, j_max=2.0)

    print("1. THONG SO PHAN TICH THOI GIAN 7 GIAI DOAN S-CURVE:")
    print(f"   -> Tong quang duong muc tieu (D) : {profiler.target_dist:.2f} m")
    print(f"   -> Van toc toi da (v_max)        : {profiler.v_max:.2f} m/s")
    print(f"   -> Gia toc toi da (a_max)        : {profiler.a_max:.2f} m/s^2")
    print(f"   -> Do giat toi da (j_max)        : {profiler.j_max:.2f} m/s^3")
    print(f"   -> Thoi gian tang giat (T_j)     : {profiler.tj:.2f} s")
    print(f"   -> Thoi gian gia toc deu (T_a)   : {profiler.ta:.2f} s")
    print(f"   -> Thoi gian chay deu (T_cruise) : {profiler.t_cruise:.2f} s")
    print(f"   -> Tong thoi gian hanh trinh     : {profiler.total_duration:.2f} s\n")

    assert abs(profiler.total_duration - 7.5) < 1e-3, "Tong thoi gian hanh trinh phai dung bang 7.5 giay!"

    # 2. Kiem tra lay mau tai cac moc quan trong
    print("2. KIEM TRA CAC MOC TRANG THAI CHUYEN PHASE:")
    s_mid, v_mid, a_mid, _ = profiler.sample(profiler.t3)
    print(f"   -> Tai t = {profiler.t3:.2f}s (Cuoi tang toc) : s={s_mid:.2f}m, v={v_mid:.2f}m/s, a={a_mid:.2f}m/s^2")
    assert abs(v_mid - 2.0) < 1e-4, "Sau giai doan tang toc van toc phai dat dung v_max=2.0 m/s!"

    s_cruise, v_cruise, a_cruise, _ = profiler.sample(profiler.t3 + 1.0)
    print(f"   -> Tai t = {(profiler.t3 + 1.0):.2f}s (Chay deu)      : s={s_cruise:.2f}m, v={v_cruise:.2f}m/s, a={a_cruise:.2f}m/s^2")
    assert abs(v_cruise - 2.0) < 1e-4 and abs(a_cruise) < 1e-4

    s_end, v_end, a_end, _ = profiler.sample(profiler.total_duration)
    print(f"   -> Tai t = {profiler.total_duration:.2f}s (Cap ben dich) : s={s_end:.2f}m, v={v_end:.2f}m/s, a={a_end:.2f}m/s^2")
    assert abs(s_end - 10.0) < 1e-3, "Quang duong cuoi cung phai dung bang 10.0m!"
    assert abs(v_end) < 1e-3, "Van toc khi cap ben phai triet tieu hoan toan ve 0 m/s!"

    # 3. Kiem tra toan bo hanh trinh: Khong bao gio vi pham gioi han Jerk va Accel
    print("\n3. KIEM TRA DO AN TOAN CO HOC TOAN BO HANH TRINH (SAMPLE DT=0.05S):")
    dt = 0.05
    steps = int(profiler.total_duration / dt)
    max_observed_jerk = 0.0
    max_observed_accel = 0.0

    for i in range(steps + 1):
        t_sample = i * dt
        _, _, a_s, j_s = profiler.sample(t_sample)
        if abs(j_s) > max_observed_jerk:
            max_observed_jerk = abs(j_s)
        if abs(a_s) > max_observed_accel:
            max_observed_accel = abs(a_s)

    print(f"   -> Jerk lon nhat ghi nhan        : {max_observed_jerk:.2f} m/s^3 (Gioi han <= {profiler.j_max:.2f})")
    print(f"   -> Gia toc lon nhat ghi nhan     : {max_observed_accel:.2f} m/s^2 (Gioi han <= {profiler.a_max:.2f})")
    assert max_observed_jerk <= profiler.j_max + 1e-4
    assert max_observed_accel <= profiler.a_max + 1e-4

    print("\n[THANH CONG] DA HOAN THANH BO TAO QUY DAO S-CURVE 7 DOAN GIAM XOC CO HOC CHO ROBOT!")
