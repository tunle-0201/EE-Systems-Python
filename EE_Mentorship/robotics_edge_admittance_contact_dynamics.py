"""
Admittance Control & Compliant Contact Dynamics for Humanoid Robot Manipulation
Chuyen de 25: Robotic Joint Impedance Control & Load Torque Observer
Milestone AL.3 - Bai hoc 98 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke bo dieu khien Admittance Control thich nghi voi ngoai luc tuong tac.
- Mo phong dong luc hoc tiep xuc be mat Kelvin-Voigt (Contact Dynamics: K_env, D_env).
- Duy tri luc tiep xuc an toan (Force Regulation) khi robot tiep xuc voi vat the cung.
- Ngan ngua dao dong va dap (Limit-cycle Chattering) khi chuyen tiep Free-to-Contact.
"""

import math
from typing import List, Dict, Tuple


class KelvinVoigtEnvironment:
    """
    Mo hinh tiep xuc moi truong Kelvin-Voigt Contact Model.
    Be mat vat ly nam tai vi tri x_surface.
    Khi dau cong tac cua robot x xuyen qua be mat (x > x_surface):
        F_contact = K_env * (x - x_surface) + D_env * v
    Khi khong tiep xuc (x <= x_surface):
        F_contact = 0
    """
    def __init__(self, surface_position: float = 0.5, stiffness_k: float = 5000.0, damping_d: float = 50.0):
        self.x_surface = surface_position  # Vi tri mat ban / tuong (m)
        self.K_env = stiffness_k           # Do cung be mat (N/m, 5000 N/m la mat nhom/go cung)
        self.D_env = damping_d             # He so can tiep xuc (N*s/m)

    def compute_contact_force(self, x: float, v: float) -> float:
        penetration = x - self.x_surface
        if penetration > 0:
            force_elastic = self.K_env * penetration
            force_damping = self.D_env * v
            # Luc phap tuyen tiep xuc luon chong lai chieu xuyen vao (>= 0)
            f_contact = max(0.0, force_elastic + force_damping)
            return f_contact
        return 0.0


class AdmittanceController:
    """
    Bo dieu khien Admittance Control bac 2:
        M_adm * a_adm + D_adm * (v_adm - v_nom) + K_adm * (x_adm - x_nom) = -F_ext
    Dau vao: Luc do duoc / uoc luong F_ext va quy dao danh dinh (x_nom, v_nom).
    Dau ra: Quy dao thich nghi mui robot (x_adm, v_adm, a_adm) de chap hanh vi tri.
    """
    def __init__(self, mass_m: float = 2.0, damping_d: float = 80.0, stiffness_k: float = 100.0):
        self.M_adm = mass_m      # Khoi luong ao (kg)
        self.D_adm = damping_d    # Giam chan ao (N*s/m)
        self.K_adm = stiffness_k  # Do cung ao (N/m)

        self.x_adm = 0.0         # Vi tri quy dao thich nghi
        self.v_adm = 0.0         # Van toc quy dao thich nghi
        self.a_adm = 0.0         # Gia toc quy dao thich nghi

    def step(self, x_nom: float, v_nom: float, f_ext: float, dt: float) -> Tuple[float, float]:
        """
        Giai phuong trinh vi phan Admittance tai moi chu ky dt:
        a_adm = (-F_ext - D_adm*(v_adm - v_nom) - K_adm*(x_adm - x_nom)) / M_adm
        """
        delta_x = self.x_adm - x_nom
        delta_v = self.v_adm - v_nom

        # Tinh gia toc thich nghi
        self.a_adm = (-f_ext - self.D_adm * delta_v - self.K_adm * delta_x) / self.M_adm
        self.v_adm += self.a_adm * dt
        self.x_adm += self.v_adm * dt

        return self.x_adm, self.v_adm


def test_admittance_contact_dynamics():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN ADMITTANCE CONTROLLER & COMPLIANT CONTACT DYNAMICS")
    print("=" * 80)

    # 1. Thiet lap moi truong vat ly tiep xuc (Mat ban nam tai x = 0.5 m)
    SURFACE_X = 0.5  # m
    env = KelvinVoigtEnvironment(surface_position=SURFACE_X, stiffness_k=6000.0, damping_d=40.0)
    admittance = AdmittanceController(mass_m=2.0, damping_d=90.0, stiffness_k=150.0)

    print(f"Moi truong tiep xuc : Vi tri be mat x_surface = {SURFACE_X:.2f} m | Do cung K_env = {env.K_env:.1f} N/m")
    print(f"Bo dieu khien Admittance: M = {admittance.M_adm:.1f} kg | D = {admittance.D_adm:.1f} N*s/m | K = {admittance.K_adm:.1f} N/m")
    print("-" * 80)

    DT = 0.001  # Chu ky lay mau 1 kHz (1 ms)

    # =========================================================================
    # GIAI DOAN 1: CHUYEN DONG TU DO (FREE MOTION TRUOC KHI VA CHAM)
    # Quy dao danh dinh x_nom di chuyen deu tu 0.2 m toi 0.45 m (chua cham mat ban)
    # =========================================================================
    print("Giai doan 1: Chuyen dong tu do trong khong gian (x = 0.2m den 0.45m)...")
    admittance.x_adm = 0.2
    admittance.v_adm = 0.0

    SIM_TIME_1 = 0.25
    steps_1 = int(SIM_TIME_1 / DT)
    v_target = (0.45 - 0.2) / SIM_TIME_1

    for step in range(steps_1):
        x_nom = 0.2 + v_target * (step * DT)
        f_ext = env.compute_contact_force(admittance.x_adm, admittance.v_adm)
        admittance.step(x_nom, v_target, f_ext, DT)

    print(f"-> Vi tri dat duoc truoc va cham   : x_adm = {admittance.x_adm:.4f} m (x_surface = 0.5000 m)")
    print(f"-> Luc tiep xuc ngoai             : F_ext = {f_ext:.3f} N (Chua cham, F = 0)")
    assert f_ext == 0.0, "Khi chua cham mat ban, luc tiep xuc phai bang 0!"

    # =========================================================================
    # GIAI DOAN 2: VA CHAM VA TIEP XUC MEM DEO (TRANSITION TO CONTACT)
    # Quy dao danh dinh tiep tuc tien toi x_nom = 0.6 m (neu khong co Admittance,
    # tay se dam sau 0.1m vao tuong voi luc K_env * 0.1 = 600 N gay gay robot!)
    # =========================================================================
    print("-" * 80)
    print("Giai doan 2: Va cham va thich nghi tiep xuc mem deo (x_nom tien den 0.60 m)...")
    SIM_TIME_2 = 0.5
    steps_2 = int(SIM_TIME_2 / DT)
    x_nom_final = 0.60  # Vuot qua be mat 0.1 m

    contact_forces = []
    penetrations = []

    for step in range(steps_2):
        progress = min(1.0, step / (steps_2 * 0.5))
        x_nom = 0.45 + (x_nom_final - 0.45) * progress
        v_nom = (x_nom_final - 0.45) / (SIM_TIME_2 * 0.5) if progress < 1.0 else 0.0

        f_ext = env.compute_contact_force(admittance.x_adm, admittance.v_adm)
        admittance.step(x_nom, v_nom, f_ext, DT)

        contact_forces.append(f_ext)
        penetrations.append(max(0.0, admittance.x_adm - SURFACE_X))

    steady_force = contact_forces[-1]
    max_force = max(contact_forces)
    steady_penetration = penetrations[-1]

    # Luc ly thuyet khi can bang Admittance:
    # K_adm * (x_adm - x_nom) = -F_ext va F_ext = K_env * (x_adm - x_surface)
    # => F_ext = (K_env * K_adm / (K_env + K_adm)) * (x_nom - x_surface)
    k_eff = (env.K_env * admittance.K_adm) / (env.K_env + admittance.K_adm)
    expected_force = k_eff * (x_nom_final - SURFACE_X)

    print(f"-> Luc tiep xuc cuc dai khi cham (Peak): {max_force:.2f} N")
    print(f"-> Luc tiep xuc on dinh (Steady Force) : {steady_force:.2f} N (Ly thuyet: {expected_force:.2f} N)")
    print(f"-> Do bien dang xuyen sau vao tuong     : {steady_penetration * 1000:.2f} mm")
    print(f"-> So sanh voi che do CUNG (Stiff)     : Khong Admittance luc se len toi {env.K_env * 0.1:.0f} N (Gay vo khop!)")
    print(f"-> Muc giam xung luc nho Admittance     : Giam {(1.0 - max_force / (env.K_env * 0.1)) * 100:.1f}% xung luc!")

    assert steady_force < 30.0, "Luc tiep xuc phai duoc kiem soat mem deo an toan duoi 30 N!"
    assert abs(steady_force - expected_force) < 1.5, "Luc on dinh phai khop voi tinh toan do cung tuong duong!"

    print("=" * 80)
    print("[PASS] Admittance Controller & Compliant Contact Dynamics: 100% Hoan hao!")


if __name__ == "__main__":
    test_admittance_contact_dynamics()
