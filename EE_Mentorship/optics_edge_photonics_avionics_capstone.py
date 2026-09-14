"""
================================================================================
          MODULE AH CAPSTONE FINALE: HỆ THỐNG MẠNG QUANG AVIONICS MÁY BAY THẾ HỆ MỚI
================================================================================

TÍCH HỢP TOÀN BỘ PHOTONICS FLIGHT STACK: PAM4 OPTICAL + FOG SAGNAC + CHROMATIC COMP
"""

from optics_edge_pam4_eye_diagram import encode_bits_to_pam4_symbols, calculate_pam4_eye_heights
from optics_edge_sagnac_fiber_gyro import compute_sagnac_phase_shift
from optics_edge_chromatic_dispersion import calculate_chromatic_pulse_broadening

def run_photonics_avionics_system_cycle():
    # 1. Điều chế quang PAM4 cho mạng dữ liệu máy bay 100Gbps
    bit_data = [1, 0, 0, 1, 1, 1, 0, 0]
    pam4_syms = encode_bits_to_pam4_symbols(bit_data)
    h_low, h_mid, h_high = calculate_pam4_eye_heights(pam4_syms, noise_std=0.1)

    # 2. Con quay quang sợi FOG đo tốc độ góc lượn cánh máy bay (Roll Rate 0.05 rad/s)
    phi_sagnac, beam_intensity = compute_sagnac_phase_shift(omega_rad_s=0.05, fiber_length_m=500.0, coil_radius_m=0.04)

    # 3. Phân tích tán sắc đường cáp quang kết nối từ mũi máy bay về đuôi (0.5km)
    pulse_spread, safe_rate = calculate_chromatic_pulse_broadening(fiber_length_km=0.5, spectral_width_nm=0.05)

    return h_mid, phi_sagnac, safe_rate


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AH CAPSTONE: PHOTONICS FLIGHT AVIONICS ENGINE")
    print("=========================================================\n")

    eye_m, sagnac_rad, link_speed = run_photonics_avionics_system_cycle()

    print("1. KET QUA HOAT DONG TOAN CHUOI PHOTONICS AVIONICS:")
    print(f"   -> Do mo mat quang PAM4 Eye Mid : {eye_m:.2f} V")
    print(f"   -> Do lech pha con quay FOG     : {sagnac_rad:.6f} rad")
    print(f"   -> Toc do truyen quang an toan  : {link_speed:.1f} Gbps")

    assert eye_m > 1.5 and sagnac_rad > 0.0 and link_speed > 100.0, "Loi Capstone Photonics!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AH: PHOTONICS AVIONICS!")
    print("=========================================================")
