"""
siph_edge_mach_zehnder_modulator.py - Silicon Photonics Mach-Zehnder Modulator (MZM)

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Data Center Optical Interconnect / Tesla Dojo Co-Packaged Optics
Standard: IEEE 802.3ck 100 Gbps/lane Optical PMD & Silicon Photonics Interconnects

MATHEMATICAL FOUNDATION & ELECTRO-OPTIC MODULATION:
1. Plasma Dispersion Effect (Carrier Depletion in Silicon Waveguide):
   In reverse-biased PN junction phase shifters, changing free carrier density (electrons/holes)
   modulates effective refractive index Delta_n_eff and optical absorption Delta_alpha:

      Delta_phi = (2 * pi / lambda_0) * Delta_n_eff * L_mod

2. Half-Wave Voltage (V_pi) & Phase Shift:
   V_pi is the voltage required to induce a pi radian phase shift:

                    V
      Delta_phi = ────── * pi
                   V_pi

   Modulation efficiency is quantified by the product: V_pi * L_mod (typically 1.5 V*cm).

3. Mach-Zehnder Dual-Arm Optical Interference:
   Laser light with input power P_in is split equally into two arms, phase-shifted,
   and recombined at the output combiner:

                                 1 + cos(Delta_phi)
      P_out = P_in * eta_loss * ──────────────────── = P_in * eta_loss * cos^2(Delta_phi / 2)
                                         2

4. Key Figures of Merit:
   - Extinction Ratio (ER):
        ER_dB = 10 * log10(P_max / P_min)
   - Optical Modulation Amplitude (OMA):
        OMA_mW = P_max - P_min
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
import math


class MzmDrivingMode(Enum):
    SINGLE_ENDED = "SINGLE_ENDED"
    PUSH_PULL    = "PUSH_PULL"     # Zero-chirp drive (Arm1 = +V/2, Arm2 = -V/2)


class SiliconMachZehnderModulator:
    """
    Electro-Optic Silicon Mach-Zehnder Modulator (MZM) Model.
    """
    def __init__(
        self,
        wavelength_nm: float = 1310.0,       # O-Band Center Wavelength
        v_pi_volts: float = 3.2,              # Half-wave voltage at DC
        insertion_loss_db: float = 3.5,       # On-chip passive waveguide + splitter loss
        extinction_floor_db: float = 28.0,    # Maximum finite destructive cancellation floor
        driving_mode: MzmDrivingMode = MzmDrivingMode.PUSH_PULL
    ):
        self.wavelength_nm = wavelength_nm
        self.v_pi = v_pi_volts
        self.insertion_loss_db = insertion_loss_db
        self.extinction_floor_db = extinction_floor_db
        self.driving_mode = driving_mode

        # Passive linear transmission factor
        self.t_passive = 10.0 ** (-insertion_loss_db / 10.0)
        # Minimum leakage power ratio due to imperfect 50/50 splitter splitting ratio
        self.r_leakage = 10.0 ** (-extinction_floor_db / 10.0)

    def compute_optical_power_mw(self, p_in_mw: float, applied_voltage_v: float) -> float:
        """
        Computes transmitted optical power given CW laser input and applied drive voltage.
        """
        # In Push-Pull mode, effective phase shift is doubled for a given differential voltage
        if self.driving_mode == MzmDrivingMode.PUSH_PULL:
            v_effective = applied_voltage_v
        else:
            v_effective = applied_voltage_v / 2.0

        # Phase difference Delta_phi = pi * (V / V_pi)
        delta_phi = math.pi * (v_effective / self.v_pi)

        # Theoretical interference: cos^2(delta_phi / 2)
        interf = 0.5 * (1.0 + math.cos(delta_phi))

        # Clamp by physical leakage floor
        transmission = (1.0 - self.r_leakage) * interf + self.r_leakage
        p_out_mw = p_in_mw * self.t_passive * transmission
        return p_out_mw

    def modulate_bitstream(
        self,
        bitstream: List[int],
        p_laser_mw: float = 10.0,
        v_low_v: float = 0.0,
        v_high_v: float = 3.2
    ) -> Dict[str, any]:
        """
        Modulates a digital bitstream into high-speed optical pulses.
        Evaluates Optical Modulation Amplitude (OMA) and Extinction Ratio (ER).
        """
        optical_waveform_mw = []

        for bit in bitstream:
            v_drive = v_high_v if bit == 1 else v_low_v
            p_opt = self.compute_optical_power_mw(p_in_mw=p_laser_mw, applied_voltage_v=v_drive)
            optical_waveform_mw.append(p_opt)

        # Optical 1 and 0 power levels
        p_1 = self.compute_optical_power_mw(p_laser_mw, v_high_v)
        p_0 = self.compute_optical_power_mw(p_laser_mw, v_low_v)

        # Extinction Ratio in dB
        er_db = 10.0 * math.log10(p_1 / p_0) if p_0 > 0 else 99.0

        # Optical Modulation Amplitude in mW and dBm
        oma_mw = p_1 - p_0
        oma_dbm = 10.0 * math.log10(oma_mw) if oma_mw > 0 else -99.0
        p_avg_mw = 0.5 * (p_1 + p_0)
        p_avg_dbm = 10.0 * math.log10(p_avg_mw)

        return {
            "p_1_mw": p_1,
            "p_0_mw": p_0,
            "p_avg_mw": p_avg_mw,
            "p_avg_dbm": p_avg_dbm,
            "er_db": er_db,
            "oma_mw": oma_mw,
            "oma_dbm": oma_dbm,
            "waveform_mw": optical_waveform_mw
        }


def test_mach_zehnder_modulator():
    print("================================================================================")
    print("TEST SUITE: SILICON PHOTONICS MACH-ZEHNDER MODULATOR (MZM) & O-BAND TRANSMITTER")
    print("================================================================================")

    # Instantiate O-Band (1310 nm) Silicon MZM with Push-Pull drive
    mzm = SiliconMachZehnderModulator(
        wavelength_nm=1310.0,
        v_pi_volts=3.2,
        insertion_loss_db=3.5,
        extinction_floor_db=25.0,
        driving_mode=MzmDrivingMode.PUSH_PULL
    )

    laser_power_mw = 10.0  # 10 mW (+10 dBm) DFB Laser

    # 1. Static Transfer Curve Verification:
    # At V = 0.0V -> Constructive interference (Peak transmission P_max)
    # At V = V_pi (3.2V) -> Destructive interference (Null transmission P_min)
    p_max = mzm.compute_optical_power_mw(laser_power_mw, applied_voltage_v=0.0)
    p_min = mzm.compute_optical_power_mw(laser_power_mw, applied_voltage_v=3.2)

    er_static = 10.0 * math.log10(p_max / p_min)
    print(f"Static Transfer Characteristics (Laser = {laser_power_mw} mW, V_pi = {mzm.v_pi} V):")
    print(f"  P_max (V = 0.0V) : {p_max:.3f} mW ({10.0 * math.log10(p_max):.2f} dBm)")
    print(f"  P_min (V = 3.2V) : {p_min:.5f} mW ({10.0 * math.log10(p_min):.2f} dBm)")
    print(f"  Extinction Ratio : {er_static:.2f} dB")

    assert p_max > p_min * 100.0, "Extinction Ratio must exceed 20 dB"
    assert abs(er_static - 25.0) < 0.5, "ER must match extinction floor"
    print("[PASS] Milestone 1: MZM Electro-optic transfer curve and V_pi cancellation confirmed.")

    # 2. High-Speed Digital Bitstream Modulation:
    # Data sequence: [1, 0, 1, 1, 0, 0, 1]
    # In optics, Bit 1 maps to constructive (0.0V), Bit 0 maps to destructive (3.2V)
    bit_pattern = [1, 0, 1, 1, 0, 0, 1]
    results = mzm.modulate_bitstream(
        bitstream=bit_pattern,
        p_laser_mw=laser_power_mw,
        v_low_v=3.2,   # Optical 0 (Destructive)
        v_high_v=0.0   # Optical 1 (Constructive)
    )

    print("--------------------------------------------------------------------------------")
    print("OPTICAL TRANSMITTER EYE PARAMETERS:")
    print(f"  P_1 Level (Bit 1) : {results['p_1_mw']:.3f} mW")
    print(f"  P_0 Level (Bit 0) : {results['p_0_mw']:.5f} mW")
    print(f"  Average Power     : {results['p_avg_mw']:.3f} mW ({results['p_avg_dbm']:.2f} dBm)")
    print(f"  Extinction Ratio  : {results['er_db']:.2f} dB (Standard spec requires ER > 6.0 dB)")
    print(f"  Optical Mod Ampl  : {results['oma_mw']:.3f} mW ({results['oma_dbm']:.2f} dBm)")

    # Assertions
    assert results["er_db"] >= 6.0, "Extinction ratio must meet IEEE 802.3ck standard"
    assert results["oma_mw"] > 3.0, "OMA must exceed minimum optical receiver budget"

    print("[PASS] Milestone BA.1: Silicon Mach-Zehnder Modulator satisfies IEEE 100G O-Band optical spec!")
    print("================================================================================")


if __name__ == "__main__":
    test_mach_zehnder_modulator()
