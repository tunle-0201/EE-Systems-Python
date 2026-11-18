"""
================================================================================
CHUYEN DE AQ: DIEN TU CONG SUAT BANG THONG RONG GAN / SIC & GATE DRIVER SIEU TOC
BAI 1 (MILESTONE AQ.1): DONG HOC CHUYEN MACH QUA DO BAN DAN GAN VA SIC SUB-NANOSECOND
================================================================================
Chuc nang he thong:
1. Mo phong dong hoc phong/nap dien dung ky sinh cong: Ciss, Coss, Crss (Miller).
2. Tinh toan 4 pha chuyen mach Turn-On va Turn-Off:
   - Pha tre td(on), td(off)
   - Pha tang/giam dong dien tri, tfi
   - Pha cao nguyen Miller plateau va tang/giam dien ap tfv, trv
3. Tinh toan ton hao nang luong chuyen mach E_on, E_off va ton hao dan P_cond.
4. So sanh dinh luong hieu suat giua Silicon IGBT vs SiC MOSFET vs GaN HEMT o tan so cao (100 kHz).

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               V_bus * I_load * (t_ri + t_fv)       1
   E_on   =  ─────────────────────────────────  +  ── * C_oss * V_bus^2
                             2                      2

               V_bus * I_load * (t_rv + t_fi)
   E_off  =  ─────────────────────────────────
                             2

   P_cond =  I_rms^2 * R_ds_on

   P_tot  =  (E_on + E_off) * f_sw + P_cond + P_gate
================================================================================
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TransistorParams:
    """Tham so vat ly cua linh kien ban dan cong suat."""
    name: str
    technology: str          # "Si_IGBT", "SiC_MOSFET", "GaN_HEMT"
    v_ds_rated: float        # Dien ap dinh muc danh dinh (V)
    i_d_rated: float         # Dong dien danh dinh lien tuc (A)
    r_ds_on: float           # Dien tro kenh dan khi on o 25C (Ohm)
    v_th: float              # Dien ap nguong mo gate threshold (V)
    v_plateau: float         # Dien ap cao nguyen Miller (V)
    v_drv_on: float          # Dien ap kich gate duong (V)
    v_drv_off: float         # Dien ap khoa gate am/0 (V)
    q_g: float               # Tong dien tich nap gate (Coulomb)
    q_gd: float              # Dien tich nap Miller gate-drain (Coulomb)
    c_iss: float             # Dien dung vao C_gs + C_gd (Farad)
    c_oss: float             # Dien dung ra C_ds + C_gd (Farad)
    c_rss: float             # Dien dung hoi tiep Miller C_gd (Farad)
    r_gate_internal: float   # Dien tro noi bo chip gate (Ohm)
    has_tail_current: bool   # Co dong duoi tail current khi tat khong (Si IGBT)
    tail_loss_factor: float  # He so tang ton hao do dong duoi (1.0 = khong co)


@dataclass
class SwitchingResult:
    """Ket qua phan tich dong hoc chuyen mach qua do."""
    device_name: str
    t_d_on_ns: float
    t_ri_ns: float
    t_fv_ns: float
    t_total_on_ns: float
    t_d_off_ns: float
    t_rv_ns: float
    t_fi_ns: float
    t_total_off_ns: float
    e_on_uJ: float
    e_off_uJ: float
    e_sw_total_uJ: float
    p_cond_w: float
    p_sw_w: float
    p_gate_w: float
    p_total_w: float
    efficiency_pct: float


class SwitchingDynamicsSimulator:
    """
    Bo mo phong dong hoc chuyen mach ban dan cong suat bang thong rong (WBG).
    Mo hinh hoa chinh xac qua trinh nap xa dien dung ky sinh va tinh ton hao.
    """

    def __init__(self, v_bus: float, i_load: float, r_gate_ext: float, f_sw_hz: float, duty_cycle: float = 0.5):
        """
        Khoi tao thong so he thong nguon:
        v_bus: Dien ap DC bus (V)
        i_load: Dong dien tai hieu dung qua van (A)
        r_gate_ext: Dien tro gate ngoai tren bo mach PCB (Ohm)
        f_sw_hz: Tan so dong ngat chuyen mach (Hz)
        duty_cycle: Ty le thoi gian mo van (0.0 den 1.0)
        """
        assert v_bus > 0, "Dien ap bus phai duong"
        assert i_load > 0, "Dong dien tai phai duong"
        assert r_gate_ext >= 0, "Dien tro gate phai khong am"
        assert f_sw_hz > 0, "Tan so chuyen mach phai duong"
        
        self.v_bus = v_bus
        self.i_load = i_load
        self.r_gate_ext = r_gate_ext
        self.f_sw_hz = f_sw_hz
        self.duty_cycle = duty_cycle

    def simulate(self, dev: TransistorParams) -> SwitchingResult:
        """
        Tinh toan dong hoc 4 pha Turn-On va Turn-Off theo mo hinh vat ly.
        """
        r_total_turn_on = dev.r_gate_internal + self.r_gate_ext
        r_total_turn_off = dev.r_gate_internal + self.r_gate_ext

        # -------------------------------------------------------------
        # 1. PHA MO VAN (TURN-ON TRANSIENT)
        # -------------------------------------------------------------
        # Pha 1a: Tre mo t_d(on) - nap V_gs tu V_drv_off den V_th
        # V_gs(t) = V_drv_off + (V_drv_on - V_drv_off) * (1 - exp(-t / (R * C_iss)))
        v_diff_on = dev.v_drv_on - dev.v_drv_off
        ratio_th = (dev.v_drv_on - dev.v_th) / v_diff_on
        ratio_th = max(1e-6, min(0.999999, ratio_th))
        t_d_on = r_total_turn_on * dev.c_iss * (-math.log(ratio_th))

        # Pha 1b: Tang dong t_ri - V_gs tang tu V_th len V_plateau
        ratio_pl = (dev.v_drv_on - dev.v_plateau) / v_diff_on
        ratio_pl = max(1e-6, min(0.999999, ratio_pl))
        t_plateau_reach = r_total_turn_on * dev.c_iss * (-math.log(ratio_pl))
        t_ri = max(0.2e-9, t_plateau_reach - t_d_on)

        # Pha 1c: Giam ap t_fv - V_ds giam tu V_bus xuong V_on tai cao nguyen Miller
        # Dong sac gate tai cao nguyen Miller:
        i_g_on_miller = (dev.v_drv_on - dev.v_plateau) / r_total_turn_on
        i_g_on_miller = max(1e-3, i_g_on_miller)
        t_fv = dev.q_gd / i_g_on_miller

        t_total_on = t_d_on + t_ri + t_fv

        # Ton hao mo van E_on: dien ap * dong dien trong thoi gian (t_ri + t_fv) + sac C_oss
        e_on_vi = 0.5 * self.v_bus * self.i_load * (t_ri + t_fv)
        e_on_coss = 0.5 * dev.c_oss * (self.v_bus ** 2)
        e_on = e_on_vi + e_on_coss

        # -------------------------------------------------------------
        # 2. PHA TAT VAN (TURN-OFF TRANSIENT)
        # -------------------------------------------------------------
        # Pha 2a: Tre tat t_d(off) - V_gs giam tu V_drv_on xuong V_plateau
        ratio_pl_off = (dev.v_plateau - dev.v_drv_off) / v_diff_on
        ratio_pl_off = max(1e-6, min(0.999999, ratio_pl_off))
        t_d_off = r_total_turn_off * dev.c_iss * (-math.log(ratio_pl_off))

        # Pha 2b: Tang ap t_rv - V_ds tang tu V_on len V_bus tai cao nguyen Miller
        # Dong xa gate tai cao nguyen Miller:
        i_g_off_miller = (dev.v_plateau - dev.v_drv_off) / r_total_turn_off
        i_g_off_miller = max(1e-3, i_g_off_miller)
        t_rv = dev.q_gd / i_g_off_miller

        # Pha 2c: Giam dong t_fi - V_gs giam tu V_plateau xuong V_th
        ratio_th_off = (dev.v_th - dev.v_drv_off) / v_diff_on
        ratio_th_off = max(1e-6, min(0.999999, ratio_th_off))
        t_th_reach_off = r_total_turn_off * dev.c_iss * (-math.log(ratio_th_off))
        t_fi = max(0.2e-9, t_th_reach_off - t_d_off)

        # Neu la Si IGBT, dong duoi keo dai thoi gian giam dong gap 3-5 lan
        if dev.has_tail_current:
            t_fi *= dev.tail_loss_factor

        t_total_off = t_d_off + t_rv + t_fi

        # Ton hao tat van E_off:
        e_off = 0.5 * self.v_bus * self.i_load * (t_rv + t_fi)
        if dev.has_tail_current:
            e_off *= dev.tail_loss_factor

        # -------------------------------------------------------------
        # 3. TON HAO DAN P_cond VA TON HAO DIEU KHIEN CONG P_gate
        # -------------------------------------------------------------
        # Dong hieu dung khi dan: I_rms^2 * R_ds_on * duty_cycle
        p_cond = (self.i_load ** 2) * dev.r_ds_on * self.duty_cycle
        p_sw = (e_on + e_off) * self.f_sw_hz
        p_gate = dev.q_g * v_diff_on * self.f_sw_hz

        p_total = p_cond + p_sw + p_gate
        p_delivered = self.v_bus * self.i_load * self.duty_cycle
        efficiency = (p_delivered / (p_delivered + p_total)) * 100.0

        return SwitchingResult(
            device_name=dev.name,
            t_d_on_ns=t_d_on * 1e9,
            t_ri_ns=t_ri * 1e9,
            t_fv_ns=t_fv * 1e9,
            t_total_on_ns=t_total_on * 1e9,
            t_d_off_ns=t_d_off * 1e9,
            t_rv_ns=t_rv * 1e9,
            t_fi_ns=t_fi * 1e9,
            t_total_off_ns=t_total_off * 1e9,
            e_on_uJ=e_on * 1e6,
            e_off_uJ=e_off * 1e6,
            e_sw_total_uJ=(e_on + e_off) * 1e6,
            p_cond_w=p_cond,
            p_sw_w=p_sw,
            p_gate_w=p_gate,
            p_total_w=p_total,
            efficiency_pct=efficiency
        )


def get_benchmark_devices() -> List[TransistorParams]:
    """
    Kho du lieu thong so 3 cong nghe ban dan cong suat chuan cong nghiep:
    1. Si IGBT 1200V 100A (Truyen thong kieu cu)
    2. SiC MOSFET 1200V 100A (The he moi - Tesla Model 3/Y Inverter)
    3. GaN HEMT 650V 60A (Sieu toc e-mode - Apple GaN Fast Charger / Datacenter)
    """
    si_igbt = TransistorParams(
        name="Silicon IGBT 1200V/100A",
        technology="Si_IGBT",
        v_ds_rated=1200.0,
        i_d_rated=100.0,
        r_ds_on=0.035,              # V_ce(sat)/I_c ~ 1.75V / 50A
        v_th=5.5,
        v_plateau=8.5,
        v_drv_on=15.0,
        v_drv_off=-8.0,
        q_g=450e-9,                 # 450 nC
        q_gd=160e-9,                # 160 nC
        c_iss=6200e-12,             # 6200 pF
        c_oss=450e-12,              # 450 pF
        c_rss=180e-12,              # 180 pF
        r_gate_internal=2.5,
        has_tail_current=True,      # Dong duoi do thoi gian song hat tai thieu so
        tail_loss_factor=2.8
    )

    sic_mosfet = TransistorParams(
        name="Wolfspeed SiC MOSFET 1200V/100A",
        technology="SiC_MOSFET",
        v_ds_rated=1200.0,
        i_d_rated=100.0,
        r_ds_on=0.016,              # 16 mOhm
        v_th=2.8,
        v_plateau=6.5,
        v_drv_on=18.0,
        v_drv_off=-4.0,
        q_g=140e-9,                 # 140 nC (giam 68% so voi Si)
        q_gd=42e-9,                 # 42 nC (giam 73%)
        c_iss=2100e-12,             # 2100 pF
        c_oss=140e-12,              # 140 pF
        c_rss=15e-12,               # 15 pF (Miller rat nho)
        r_gate_internal=1.2,
        has_tail_current=False,     # Hat dan da so, khong co dong duoi
        tail_loss_factor=1.0
    )

    gan_hemt = TransistorParams(
        name="GaN Systems HEMT 650V/60A",
        technology="GaN_HEMT",
        v_ds_rated=650.0,
        i_d_rated=60.0,
        r_ds_on=0.010,              # 10 mOhm
        v_th=1.4,
        v_plateau=2.5,
        v_drv_on=6.0,
        v_drv_off=0.0,
        q_g=14e-9,                  # 14 nC (sieu nho, toc do sub-nanosecond)
        q_gd=4.5e-9,                # 4.5 nC
        c_iss=350e-12,              # 350 pF
        c_oss=75e-12,               # 75 pF
        c_rss=3.0e-12,              # 3 pF (cuc ky mien nhiem Miller)
        r_gate_internal=0.4,
        has_tail_current=False,     # 2DEG AlGaN/GaN electron gas
        tail_loss_factor=1.0
    )

    return [si_igbt, sic_mosfet, gan_hemt]


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AQ - LESSON 1: WBG GAN/SIC SWITCHING DYNAMICS")
    print("=" * 80)

    # Thiet lap dieu kien van hanh bien tan 800V DC Bus, tai 50A, tan so 100 kHz
    v_bus_800v = 800.0
    i_load_50a = 50.0
    r_gate_ext = 2.0  # Ohm
    f_sw_100k = 100000.0  # 100 kHz

    sim_800v = SwitchingDynamicsSimulator(
        v_bus=v_bus_800v,
        i_load=i_load_50a,
        r_gate_ext=r_gate_ext,
        f_sw_hz=f_sw_100k,
        duty_cycle=0.5
    )

    devices = get_benchmark_devices()
    
    # Chay so sanh giua Si IGBT va SiC MOSFET o 800V
    res_si = sim_800v.simulate(devices[0])
    res_sic = sim_800v.simulate(devices[1])

    # Chay GaN HEMT o 400V Bus phu hop dinh muc 650V
    sim_400v = SwitchingDynamicsSimulator(
        v_bus=400.0,
        i_load=40.0,
        r_gate_ext=1.0,
        f_sw_hz=200000.0,  # GaN chay o 200 kHz
        duty_cycle=0.5
    )
    res_gan = sim_400v.simulate(devices[2])

    print("\n[1] SO SANH DONG HOC CHUYEN MACH QUA DO (SWITCHING TIMES):")
    print(f"{'Thong so (ns)':<25} | {'Si IGBT (1200V)':<18} | {'SiC MOSFET (1200V)':<18} | {'GaN HEMT (650V)':<18}")
    print("-" * 85)
    print(f"{'Turn-On Delay (t_d_on)':<25} | {res_si.t_d_on_ns:<18.2f} | {res_sic.t_d_on_ns:<18.2f} | {res_gan.t_d_on_ns:<18.2f}")
    print(f"{'Current Rise (t_ri)':<25} | {res_si.t_ri_ns:<18.2f} | {res_sic.t_ri_ns:<18.2f} | {res_gan.t_ri_ns:<18.2f}")
    print(f"{'Voltage Fall (t_fv)':<25} | {res_si.t_fv_ns:<18.2f} | {res_sic.t_fv_ns:<18.2f} | {res_gan.t_fv_ns:<18.2f}")
    print(f"{'TONG THOI GIAN BAT':<25} | {res_si.t_total_on_ns:<18.2f} | {res_sic.t_total_on_ns:<18.2f} | {res_gan.t_total_on_ns:<18.2f}")
    print("-" * 85)
    print(f"{'Turn-Off Delay (t_d_off)':<25} | {res_si.t_d_off_ns:<18.2f} | {res_sic.t_d_off_ns:<18.2f} | {res_gan.t_d_off_ns:<18.2f}")
    print(f"{'Voltage Rise (t_rv)':<25} | {res_si.t_rv_ns:<18.2f} | {res_sic.t_rv_ns:<18.2f} | {res_gan.t_rv_ns:<18.2f}")
    print(f"{'Current Fall (t_fi)':<25} | {res_si.t_fi_ns:<18.2f} | {res_sic.t_fi_ns:<18.2f} | {res_gan.t_fi_ns:<18.2f}")
    print(f"{'TONG THOI GIAN TAT':<25} | {res_si.t_total_off_ns:<18.2f} | {res_sic.t_total_off_ns:<18.2f} | {res_gan.t_total_off_ns:<18.2f}")

    print("\n[2] PHAN TICH NANG LUONG VA CONG SUAT TON HAO:")
    print(f"{'Chi so ton hao':<25} | {'Si IGBT (100kHz)':<18} | {'SiC MOSFET (100kHz)':<18} | {'GaN HEMT (200kHz)':<18}")
    print("-" * 85)
    print(f"{'E_on (micro-Joule)':<25} | {res_si.e_on_uJ:<18.2f} | {res_sic.e_on_uJ:<18.2f} | {res_gan.e_on_uJ:<18.2f}")
    print(f"{'E_off (micro-Joule)':<25} | {res_si.e_off_uJ:<18.2f} | {res_sic.e_off_uJ:<18.2f} | {res_gan.e_off_uJ:<18.2f}")
    print(f"{'E_sw Tong (uJ)':<25} | {res_si.e_sw_total_uJ:<18.2f} | {res_sic.e_sw_total_uJ:<18.2f} | {res_gan.e_sw_total_uJ:<18.2f}")
    print(f"{'Ton hao dan P_cond (W)':<25} | {res_si.p_cond_w:<18.2f} | {res_sic.p_cond_w:<18.2f} | {res_gan.p_cond_w:<18.2f}")
    print(f"{'Ton hao chuyen P_sw (W)':<25} | {res_si.p_sw_w:<18.2f} | {res_sic.p_sw_w:<18.2f} | {res_gan.p_sw_w:<18.2f}")
    print(f"{'TONG TON HAO (W)':<25} | {res_si.p_total_w:<18.2f} | {res_sic.p_total_w:<18.2f} | {res_gan.p_total_w:<18.2f}")
    print(f"{'Hieu suat he thong (%)':<25} | {res_si.efficiency_pct:<18.2f} | {res_sic.efficiency_pct:<18.2f} | {res_gan.efficiency_pct:<18.2f}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Thoi gian tat cua SiC MOSFET phai nhanh hon Si IGBT it nhat 3 lan (do khong co tail current)
    assert res_sic.t_total_off_ns < res_si.t_total_off_ns / 3.0, (
        f"SiC tat {res_sic.t_total_off_ns}ns phai nhanh gap 3 lan Si {res_si.t_total_off_ns}ns"
    )

    # 2. Ton hao chuyen mach E_sw cua SiC phai giam hon 60% so voi Si IGBT o 800V
    reduction_pct = (1.0 - res_sic.e_sw_total_uJ / res_si.e_sw_total_uJ) * 100.0
    print(f"\n[INFO] Ty le cat giam ton hao chuyen mach cua SiC so voi Si: {reduction_pct:.2f}%")
    assert reduction_pct > 60.0, "SiC phai cat giam it nhat 60% ton hao E_sw"

    # 3. GaN HEMT dat toc do sieu toc: tong thoi gian chuyen mach duoi 15 ns
    assert res_gan.t_total_on_ns < 15.0 and res_gan.t_total_off_ns < 15.0, (
        f"GaN phai co toc do sub-15ns: on={res_gan.t_total_on_ns}ns, off={res_gan.t_total_off_ns}ns"
    )

    # 4. Hieu suat bien tan SiC phai vuot troi hon Si IGBT o 100 kHz
    assert res_sic.efficiency_pct > res_si.efficiency_pct, "SiC phai dat hieu suat cao hon Si"
    assert res_sic.efficiency_pct > 95.0, "SiC o 100 kHz phai dat hieu suat > 95%"

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: WBG SWITCHING DYNAMICS VERIFIED!")


if __name__ == "__main__":
    main()
