"""
================================================================================
CHUYEN DE AQ: DIEN TU CONG SUAT BANG THONG RONG GAN / SIC & GATE DRIVER SIEU TOC
BAI 2 (MILESTONE AQ.2): MACH KEP ACTIVE MILLER CLAMP VA TANG KICH GATE DRIVER
================================================================================
Chuc nang he thong:
1. Mo hinh hoa dong dien dich chuyen qua tu Miller C_gd khi nua cau dao mach:
      i_disp = C_gd * (dv / dt)
2. Tinh toan dien ap cam ung tren chan Gate cua van dang tat (Low-Side V_gs):
      V_gs_induced = V_drv_off + C_gd * (dv / dt) * R_g_total
3. Mo phong co che hoat dong cua mach kep Miller tich cuc (Active Miller Clamp - AMC):
   - Bo so sanh noi theo doi V_gs.
   - Khi V_gs ha xuong duoi nguong V_clamp_th (~2.0V), switch kẹp AMC (R_clamp < 0.5 Ohm)
     kich hoat, dau tat chan Gate xuong VEE/GND.
   - Triet tieu tro khang duong xa, ha dien ap ky sinh xuong duoi nguong mo V_th.
4. Kiem chung 3 giai phap chong bat nham:
   - Case A: Driver 0V khong co AMC (Bung no Shoot-Through do V_gs vuot V_th).
   - Case B: Driver phan cuc am -4V khong co AMC.
   - Case C: Driver 0V tich hop Active Miller Clamp (AMC thong minh).

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               d V_sw
   i_disp  =  ──────── * C_gd
                 dt

   V_gs    =  V_drv_off + i_disp * (R_g_ext + R_g_int)

   Khi co Active Miller Clamp:
   V_gs_clamp = V_drv_off + i_disp * (R_clamp // (R_g_ext + R_g_int))
================================================================================
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class GateDriverConfig:
    """Cau hinh thong so tang kich Gate Driver."""
    name: str
    v_drv_off: float       # Dien ap phan cuc tat (V), vi du 0V hoac -4V
    v_drv_on: float        # Dien ap phan cuc bat (V), vi du 15V hoac 18V
    r_g_off: float         # Dien tro xa cong ngoai (Ohm)
    r_g_int: float         # Dien tro noi bo chip MOSFET (Ohm)
    has_active_miller_clamp: bool
    v_clamp_threshold: float  # Nguong dien ap kich hoat kẹp Miller (V), thuong 2.0V
    r_clamp: float         # Dien tro dan cua transistor kep AMC (Ohm), thuong 0.3 - 0.5 Ohm


@dataclass
class DeviceMillerParams:
    """Thong so dien dung ky sinh cua van SiC MOSFET."""
    name: str
    v_th: float            # Dien ap nguong mo van (Threshold Voltage, V)
    c_gd: float            # Dien dung Miller Drain-Gate (Farad)
    c_gs: float            # Dien dung Gate-Source (Farad)


@dataclass
class SimulationResult:
    """Ket qua mo phong dap ung dien ap Gate duoi tac dong dv/dt."""
    config_name: str
    dv_dt_v_per_ns: float
    i_disp_peak_a: float
    v_gs_max_v: float
    is_shoot_through: bool
    clamp_activated: bool
    time_series_ns: List[float]
    v_gs_series: List[float]


class ActiveMillerClampSimulator:
    """
    Bo mo phong transient tinh toan dap ung thoi gian thuc cua mach Gate Driver
    chong lai su co bat nham do xung dv/dt cuc lon tu nua cau bien tan.
    """

    def __init__(self, device: DeviceMillerParams):
        self.device = device

    def simulate_dv_dt_transient(
        self,
        driver_cfg: GateDriverConfig,
        v_bus: float,
        dv_dt_v_per_ns: float,
        dt_s: float = 20e-12,     # Buoc thoi gian 20 picoseconds
        t_total_ns: float = 30.0   # Tong thoi gian mo phong 30 nanoseconds
    ) -> SimulationResult:
        """
        Mo phong vi phan qua trinh suon xung dien ap switch-node V_sw tang vot
        voi do doc dv/dt, gay cam ung dien ap tren Gate van duoi.
        """
        # Thoi gian dien ap bus tang tu 0V len V_bus
        t_rise_s = (v_bus / (dv_dt_v_per_ns * 1e9))
        
        steps = int((t_total_ns * 1e-9) / dt_s)
        time_series: List[float] = []
        v_gs_series: List[float] = []

        v_gs = driver_cfg.v_drv_off
        v_sw = 0.0
        clamp_active = False
        v_gs_max = v_gs
        i_disp_peak = 0.0

        for step in range(steps):
            t_current = step * dt_s
            t_ns = t_current * 1e9

            # Tinh toan dien ap Switch Node V_sw va dao ham dv/dt tuc thoi
            if t_current < t_rise_s:
                v_sw = (dv_dt_v_per_ns * 1e9) * t_current
                dv_dt_inst = dv_dt_v_per_ns * 1e9
            else:
                v_sw = v_bus
                dv_dt_inst = 0.0

            # Dong dien dich chuyen qua tu Miller: i_disp = C_gd * (dv_sw / dt - dv_gs / dt)
            # Vi dv_sw >> dv_gs nen xap xi chinh xac: i_disp = C_gd * dv_sw/dt
            i_disp = self.device.c_gd * dv_dt_inst
            if i_disp > i_disp_peak:
                i_disp_peak = i_disp

            # Kiem tra trang thai Active Miller Clamp:
            # Khi van dang tat, neu co AMC va dien ap V_gs bat dau tang hoac da o duoi nguong clamp:
            # Thuc te chip driver: sau khi tat xuong duoi 2.0V thi AMC chot ON giu gate den chu ky bat tiep theo
            if driver_cfg.has_active_miller_clamp:
                # AMC kich hoat va duoc duy tri khi van o che do OFF
                clamp_active = True

            # Tinh tong dien tro thoat dong tai Gate:
            r_driver = driver_cfg.r_g_off + driver_cfg.r_g_int
            if clamp_active:
                # Transistor AMC mac song song voi duong xa cong chinh:
                # 1 / R_eff = 1 / R_clamp + 1 / R_driver
                r_eff = (driver_cfg.r_clamp * r_driver) / (driver_cfg.r_clamp + r_driver)
            else:
                r_eff = r_driver

            # Phuong trinh vi phan dien ap Gate:
            # i_net = i_disp - (v_gs - v_drv_off) / r_eff = C_gs * dv_gs/dt
            # => dv_gs/dt = (i_disp - (v_gs - v_drv_off) / r_eff) / C_gs
            i_discharge = (v_gs - driver_cfg.v_drv_off) / r_eff
            dv_gs_dt = (i_disp - i_discharge) / self.device.c_gs
            
            # Tich phan Euler cap 1
            v_gs += dv_gs_dt * dt_s

            if v_gs > v_gs_max:
                v_gs_max = v_gs

            time_series.append(t_ns)
            v_gs_series.append(v_gs)

        # Kiem tra co xay ra hien tuong ban nham (Shoot-Through) hay khong:
        # Neu v_gs_max vuot qua nguong v_th thi van duoi bi mo dan khi van tren dang mo -> Ngan mach!
        is_shoot_through = (v_gs_max >= self.device.v_th)

        return SimulationResult(
            config_name=driver_cfg.name,
            dv_dt_v_per_ns=dv_dt_v_per_ns,
            i_disp_peak_a=i_disp_peak,
            v_gs_max_v=v_gs_max,
            is_shoot_through=is_shoot_through,
            clamp_activated=clamp_active,
            time_series_ns=time_series,
            v_gs_series=v_gs_series
        )


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AQ - LESSON 2: ACTIVE MILLER CLAMP GATE DRIVER")
    print("=" * 80)

    # Thiet lap thong so van cong suat SiC MOSFET (Wolfspeed Gen 3 1200V)
    # V_th danh dinh thap (2.2V - de bi kich mo nham), C_gd = 40 pF, C_gs = 1800 pF
    sic_device = DeviceMillerParams(
        name="Wolfspeed 1200V SiC MOSFET",
        v_th=2.2,           # V_th cuc nhay 2.2V
        c_gd=40e-12,        # 40 pF Miller capacitance
        c_gs=1800e-12       # 1800 pF Gate-Source capacitance
    )

    # 3 Kich ban mach dieu khien Gate:
    # 1. Unipolar 0V/18V, R_g_off = 4.7 Ohm, KHONG CO AMC
    cfg_unipolar_no_clamp = GateDriverConfig(
        name="Case A: Unipolar 0V Driver (No AMC)",
        v_drv_off=0.0,
        v_drv_on=18.0,
        r_g_off=4.7,
        r_g_int=1.2,
        has_active_miller_clamp=False,
        v_clamp_threshold=2.0,
        r_clamp=0.4
    )

    # 2. Bipolar -5V/18V voi tro xa nho Rg_off = 0.5 Ohm (Giai phap nguon am tieu chuan)
    cfg_bipolar_no_clamp = GateDriverConfig(
        name="Case B: Bipolar -5V Driver (Rg_off=0.5 Ohm)",
        v_drv_off=-5.0,
        v_drv_on=18.0,
        r_g_off=0.5,
        r_g_int=1.2,
        has_active_miller_clamp=False,
        v_clamp_threshold=2.0,
        r_clamp=0.4
    )

    # 3. Unipolar 0V/18V, CO ACTIVE MILLER CLAMP (R_clamp = 0.25 Ohm - TI UCC21750 spec)
    cfg_with_amc = GateDriverConfig(
        name="Case C: Unipolar 0V + Active Miller Clamp (AMC)",
        v_drv_off=0.0,
        v_drv_on=18.0,
        r_g_off=4.7,
        r_g_int=1.2,
        has_active_miller_clamp=True,
        v_clamp_threshold=2.0,
        r_clamp=0.25
    )

    simulator = ActiveMillerClampSimulator(sic_device)
    v_bus_800v = 800.0
    
    # Kiem tra o do doc bien thien dv/dt sieu cao: 100 V/ns (Dac trung nua cau SiC)
    dv_dt_test = 100.0  # 100 V/ns

    print(f"\n[INFO] Dieu kien bien tan: V_bus = {v_bus_800v}V, dv/dt = {dv_dt_test} V/ns")
    print(f"[INFO] Linh kien SiC: V_th = {sic_device.v_th}V, C_gd = {sic_device.c_gd*1e12:.1f}pF, C_gs = {sic_device.c_gs*1e12:.1f}pF")

    res_a = simulator.simulate_dv_dt_transient(cfg_unipolar_no_clamp, v_bus_800v, dv_dt_test)
    res_b = simulator.simulate_dv_dt_transient(cfg_bipolar_no_clamp, v_bus_800v, dv_dt_test)
    res_c = simulator.simulate_dv_dt_transient(cfg_with_amc, v_bus_800v, dv_dt_test)

    print("\n[1] KET QUA MO PHONG TRANSIENT DIEN AP GATE (V_GS):")
    print(f"{'Giai phap Gate Driver':<38} | {'V_off (V)':<10} | {'i_disp (A)':<11} | {'V_gs_max (V)':<12} | {'Trang thai / Rui ro':<20}")
    print("-" * 102)
    for res, cfg in [(res_a, cfg_unipolar_no_clamp), (res_b, cfg_bipolar_no_clamp), (res_c, cfg_with_amc)]:
        status = "NGUY HIEM: BAT NHAM!" if res.is_shoot_through else "AN TOAN (No Shoot-Through)"
        print(f"{cfg.name:<38} | {cfg.v_drv_off:<10.1f} | {res.i_disp_peak_a:<11.2f} | {res.v_gs_max_v:<12.2f} | {status:<20}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Dong dien dich chuyen qua tu Miller voi dv/dt = 100 V/ns phai dat:
    # i_disp = C_gd * (dv/dt) = 40e-12 * 100e9 = 4.0 Amperes!
    expected_idisp = sic_device.c_gd * (dv_dt_test * 1e9)
    assert abs(res_a.i_disp_peak_a - expected_idisp) < 0.01, "Dong dich chuyen Miller i_disp phai la 4.0A"
    print(f"\n[INFO] Dong dien dich chuyen Miller xuyen qua C_gd: {res_a.i_disp_peak_a:.2f} A")

    # 2. Case A (0V khong AMC): V_gs dang len vuot V_th (2.2V) gay nguy co ban nham Shoot-Through
    print(f"[INFO] Case A V_gs dang len: {res_a.v_gs_max_v:.2f}V (Nguong V_th = {sic_device.v_th}V)")
    assert res_a.is_shoot_through, "Case A phai bi phat hien co rui ro bat nham Shoot-Through"

    # 3. Case B (Bipolar -4V): V_gs mac du dang len nhung xuat phat tu -4V nen giu duoi V_th
    assert not res_b.is_shoot_through, "Case B nguon am phai dam bao an toan"
    assert res_b.v_gs_max_v < sic_device.v_th, "Case B V_gs_max phai nho hon V_th"

    # 4. Case C (Active Miller Clamp): Dien ap duoc kep cung duoi 1.5V (an toan hon nguon 0V thong thuong rat nhieu)
    print(f"[INFO] Case C (Co AMC) V_gs dang toi da chi: {res_c.v_gs_max_v:.2f}V (Giam {((res_a.v_gs_max_v - res_c.v_gs_max_v)/res_a.v_gs_max_v)*100:.1f}%)")
    assert not res_c.is_shoot_through, "Case C voi Active Miller Clamp phai an toan 100%"
    assert res_c.v_gs_max_v < 1.5, f"Case C V_gs phai bi kep duoi 1.5V, thuc te={res_c.v_gs_max_v:.2f}V"

    # Kiem tra quet dai dv/dt tu 20 den 150 V/ns cho Active Miller Clamp
    print("\n[2] KIEM CHUNG DO BEN AMC DUOI DAI DV/DT 20 -> 150 V/ns:")
    for sweep_dv_dt in [20.0, 50.0, 80.0, 100.0, 120.0, 150.0]:
        res_sweep = simulator.simulate_dv_dt_transient(cfg_with_amc, v_bus_800v, sweep_dv_dt)
        margin = sic_device.v_th - res_sweep.v_gs_max_v
        print(f"  dv/dt = {sweep_dv_dt:>5.1f} V/ns | V_gs_peak = {res_sweep.v_gs_max_v:>5.2f} V | Margin an toan = {margin:>5.2f} V | Shoot-Through = {res_sweep.is_shoot_through}")
        assert not res_sweep.is_shoot_through, f"AMC phai bao ve an toan o dv/dt={sweep_dv_dt} V/ns"

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: ACTIVE MILLER CLAMP VERIFIED!")


if __name__ == "__main__":
    main()
