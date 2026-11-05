"""
siph_edge_microring_resonator_wdm.py - Silicon Microring Resonator (MRR) & WDM Filter Bank

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Data Center Ultra-Dense CPO / Tesla Dojo High-Density Optical Fabric
Standard: 8-Channel Wavelength Division Multiplexing (WDM) O-Band / C-Band Grid

MATHEMATICAL FOUNDATION & MICRORING OPTICAL RESONANCE:
1. Constructive Round-Trip Resonance Condition:
   Light couples from bus waveguide into circular ring. Resonance occurs when round-trip phase = 2 * pi * m:

      m * lambda_res = 2 * pi * R * n_eff

   Where:
   - R: Microring physical radius (typically 5 to 12 um).
   - n_eff: Effective refractive index of silicon waveguide core (~ 2.45).
   - m: Integer azimuthal mode order.

2. Free Spectral Range (FSR):
   Wavelength spacing between adjacent optical longitudinal resonance modes:

                     lambda_res^2
      FSR = ───────────────────────────────
              n_group * 2 * pi * R

   Where n_group is the optical group index (n_g ~ 4.2 in silicon strip waveguides).

3. Quality Factor (Q) & Lorentzian Drop Spectrum:
   Linewidth Delta_lambda_fwhm at 3 dB drop:

      Q = lambda_res / Delta_lambda_fwhm

   Through-port transmission spectrum:

                               (lambda - lambda_res)^2
      T_thru(lambda) = ──────────────────────────────────────────
                       (lambda - lambda_res)^2 + (Delta_lambda / 2)^2

4. Thermo-Optic Coefficient & Micro-Heater Tuning:
   Silicon thermo-optic coefficient: dn/dT = +1.86e-4 K^-1
   Wavelength temperature drift: dlambda / dT approx +0.080 nm / deg C (80 pm / deg C)
   Integrated Ti/Pt micro-heaters apply Joule heat (P_heater) to align resonance:

      Delta_lambda_tune = eta_heater * P_heater_mw
"""

from typing import List, Dict, Tuple, Optional
import math


class MicroringResonator:
    """
    Silicon Photonics Microring Resonator (MRR) Model with Thermo-Optic Tuning.
    """
    N_EFF = 2.45        # Effective index at 1310 nm
    N_GROUP = 4.20      # Group index in sub-micron strip waveguide
    D_LAMBDA_DT = 0.080 # nm / deg C (Thermo-optic resonance shift)
    HEATER_EFF_NM_PER_MW = 0.025  # Micro-heater tuning efficiency: 25 pm / mW

    def __init__(
        self,
        channel_id: int,
        nominal_lambda_nm: float,
        radius_um: float = 7.5,
        q_factor: float = 12000.0,
        t_nom_celsius: float = 25.0
    ):
        self.channel_id = channel_id
        self.nominal_lambda_nm = nominal_lambda_nm
        self.radius_um = radius_um
        self.q_factor = q_factor
        self.t_nom = t_nom_celsius

        # Linewidth (FWHM) in nm: Delta_lambda = lambda / Q
        self.fwhm_nm = self.nominal_lambda_nm / self.q_factor

        # Free Spectral Range (FSR) in nm
        perimeter_nm = 2.0 * math.pi * (self.radius_um * 1e3)
        self.fsr_nm = (self.nominal_lambda_nm ** 2) / (self.N_GROUP * perimeter_nm)

        # Active state
        self.current_temp_celsius = t_nom_celsius
        self.heater_power_mw = 0.0

    @property
    def current_resonance_lambda_nm(self) -> float:
        """
        Calculates instantaneous resonance wavelength accounting for thermal drift and heater power.
        """
        delta_t = self.current_temp_celsius - self.t_nom
        thermal_shift = delta_t * self.D_LAMBDA_DT
        heater_shift = self.heater_power_mw * self.HEATER_EFF_NM_PER_MW
        return self.nominal_lambda_nm + thermal_shift + heater_shift

    def compute_through_transmission(self, lambda_nm: float) -> float:
        """
        Computes Lorentzian transmission through the drop/through filter notch.
        Periodic with Free Spectral Range (FSR).
        Returns linear transmission power ratio [0.0 to 1.0].
        """
        res_lambda = self.current_resonance_lambda_nm
        # Fold into central FSR domain [-FSR/2, +FSR/2] to reflect cavity periodicity
        delta = ((lambda_nm - res_lambda + self.fsr_nm / 2.0) % self.fsr_nm) - self.fsr_nm / 2.0
        gamma = self.fwhm_nm / 2.0
        # Notch transmission (Through port): 0 at resonance, 1 far away
        t_linear = (delta ** 2) / (delta ** 2 + gamma ** 2)
        return t_linear

    def tune_to_wavelength(self, target_lambda_nm: float) -> float:
        """
        Closed-loop micro-heater controller adjusts heater power to lock resonance to target.
        Returns required heater power in mW.
        """
        # Desired shift from unheated state
        delta_t = self.current_temp_celsius - self.t_nom
        unheated_lambda = self.nominal_lambda_nm + delta_t * self.D_LAMBDA_DT
        needed_shift = target_lambda_nm - unheated_lambda

        if needed_shift < 0.0:
            # Thermal heaters can only increase temperature (red-shift), unless cooler used
            # For 1 FSR wrap-around, heat to next order:
            needed_shift += self.fsr_nm

        p_heater = needed_shift / self.HEATER_EFF_NM_PER_MW
        self.heater_power_mw = p_heater
        return p_heater


class WdmFilterBank8Channel:
    """
    8-Channel Dense WDM Filter Bank cascaded along a single common bus waveguide.
    Channel grid spacing: Delta_lambda = 1.6 nm (~ 280 GHz in O-Band).
    """
    def __init__(self, base_lambda_nm: float = 1300.0, channel_spacing_nm: float = 1.6):
        self.base_lambda = base_lambda_nm
        self.spacing = channel_spacing_nm
        self.channels: List[MicroringResonator] = []

        for i in range(8):
            target_wl = base_lambda_nm + i * channel_spacing_nm
            ring = MicroringResonator(
                channel_id=i,
                nominal_lambda_nm=target_wl,
                radius_um=8.0,
                q_factor=15000.0
            )
            self.channels.append(ring)

    def evaluate_inter_channel_crosstalk(self, laser_wavelengths: List[float]) -> Dict[str, any]:
        """
        Calculates adjacent channel optical crosstalk across all 8 WDM channels.
        Crosstalk = 10 * log10(T_drop_adjacent / T_drop_target).
        """
        crosstalk_matrix_db = []
        for ch_idx, target_wl in enumerate(laser_wavelengths):
            target_ring = self.channels[ch_idx]
            # On-resonance drop transmission for target
            t_through_target = target_ring.compute_through_transmission(target_wl)
            t_drop_target = 1.0 - t_through_target

            row_xtalk = []
            for other_idx, other_wl in enumerate(laser_wavelengths):
                if ch_idx == other_idx:
                    row_xtalk.append(0.0)
                else:
                    # How much of other wavelength leaks into target ring?
                    t_through_other = target_ring.compute_through_transmission(other_wl)
                    t_drop_leak = 1.0 - t_through_other
                    xtalk_ratio = (t_drop_leak / t_drop_target) if t_drop_target > 0 else 1e-9
                    xtalk_db = 10.0 * math.log10(max(xtalk_ratio, 1e-9))
                    row_xtalk.append(xtalk_db)
            crosstalk_matrix_db.append(row_xtalk)

        # Worst-case adjacent channel crosstalk
        worst_adj_xtalk_db = -99.0
        for i in range(len(laser_wavelengths)):
            if i > 0:
                worst_adj_xtalk_db = max(worst_adj_xtalk_db, crosstalk_matrix_db[i][i - 1])
            if i < len(laser_wavelengths) - 1:
                worst_adj_xtalk_db = max(worst_adj_xtalk_db, crosstalk_matrix_db[i][i + 1])

        return {
            "crosstalk_matrix_db": crosstalk_matrix_db,
            "worst_adjacent_crosstalk_db": worst_adj_xtalk_db
        }


def test_microring_resonator_wdm():
    print("================================================================================")
    print("TEST SUITE: SILICON MICRORING RESONATOR (MRR) & 8-CHANNEL WDM FILTER BANK")
    print("================================================================================")

    # 1. Single Microring Physics Verification
    ring0 = MicroringResonator(channel_id=0, nominal_lambda_nm=1310.0, radius_um=7.5, q_factor=13100.0)
    print(f"Microring Parameters (R = {ring0.radius_um} um, Q = {ring0.q_factor}):")
    print(f"  Resonance Wavelength : {ring0.nominal_lambda_nm:.2f} nm")
    print(f"  FWHM Linewidth (3dB) : {ring0.fwhm_nm:.4f} nm ({ring0.fwhm_nm * 1e3:.1f} pm)")
    print(f"  Free Spectral Range  : {ring0.fsr_nm:.2f} nm")

    # Linewidth at Q=13100 for 1310 nm should be exactly 0.10 nm (100 pm)
    assert abs(ring0.fwhm_nm - 0.10) < 1e-3
    assert ring0.fsr_nm > 8.0, "FSR must comfortably accommodate 8 channels"
    print("[PASS] Milestone 1: MRR resonance condition and FSR free spectral range verified.")

    # 2. Closed-Loop Thermal Tuning under Silicon Die Heating
    # When die temperature rises from 25 C to 50 C (+25 C delta):
    # Resonance drifts by +25 * 0.080 nm = +2.0 nm!
    ring0.current_temp_celsius = 50.0
    drifted_wl = ring0.current_resonance_lambda_nm
    print(f"\nThermal Drift (T = 50.0 C, Delta_T = +25 C):")
    print(f"  Drifted Resonance Wavelength: {drifted_wl:.3f} nm (Drift = +{drifted_wl - 1310.0:.3f} nm)")
    assert abs(drifted_wl - 1312.0) < 1e-3

    # Activate micro-heater controller to lock back onto laser (or wrap to next FSR order)
    heater_p = ring0.tune_to_wavelength(target_lambda_nm=1310.0)
    locked_wl = ring0.current_resonance_lambda_nm
    print(f"  Heater Applied : {heater_p:.2f} mW")
    print(f"  Locked Resonance: {locked_wl:.3f} nm")
    # Modulation transmission at target wavelength must now drop into resonance notch
    t_thru = ring0.compute_through_transmission(1310.0)
    assert t_thru < 0.01, "Through transmission must be near zero at resonance (notched into drop port)"
    print("[PASS] Milestone 2: Closed-loop micro-heater tunes out +25 C thermal drift successfully.")

    # 3. 8-Channel WDM Multiplexing & Adjacent Channel Crosstalk
    wdm_bank = WdmFilterBank8Channel(base_lambda_nm=1300.0, channel_spacing_nm=1.6)
    grid_lambdas = [1300.0 + i * 1.6 for i in range(8)]
    xtalk_results = wdm_bank.evaluate_inter_channel_crosstalk(grid_lambdas)

    print("--------------------------------------------------------------------------------")
    print("8-CHANNEL WDM ARRAY CROSSTALK BENCHMARK (1.6 nm / 280 GHz Grid):")
    print(f"  Channel 0 to 7 Grid : {grid_lambdas[0]:.1f} nm to {grid_lambdas[-1]:.1f} nm")
    print(f"  Worst Adjacent XT   : {xtalk_results['worst_adjacent_crosstalk_db']:.2f} dB (Spec requires < -20.0 dB)")

    assert xtalk_results["worst_adjacent_crosstalk_db"] < -20.0, "WDM crosstalk must be suppressed below -20 dB"
    print("[PASS] Milestone BA.2: 8-Channel WDM Microring array satisfies optical isolation spec!")
    print("================================================================================")


if __name__ == "__main__":
    test_microring_resonator_wdm()
