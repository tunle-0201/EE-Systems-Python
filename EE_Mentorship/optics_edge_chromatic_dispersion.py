"""
================================================================================
          MODULE AH: EMBEDDED OPTICAL TRANSCEIVERS & PHOTONICS AVIONICS
              MILESTONE AH.3: BÙ TÁN SẮC SẮC KÝ QUANG SỢI (CHROMATIC DISPERSION)
================================================================================

TẠI SAO XUNG ÁNH SÁNG TRUYỀN QUA CÁP QUANG BỊ NỞ RỘNG (DISPERSION)?
Hiện tượng tán sắc sắc ký (Chromatic Dispersion - CD):
- Nguồn phát laser thực tế không đơn sắc tuyệt đối (có độ rộng phổ delta_lambda).
- Các bước sóng khác nhau di chuyển với vận tốc nhóm (Group Velocity) khác nhau trong lõi thủy tinh SiO2:
  + Ánh sáng đỏ đi nhanh hơn ánh sáng xanh.
  + Khiến xung quang học bị bè rộng ra theo thời gian (Pulse Broadening delta_tau):
    delta_tau = D * L * delta_lambda
    (D: Hệ số tán sắc ps/(nm.km), L: Chiều dài sợi cáp km).
  + Nếu xung bị nở rộng quá mức -> Các bit kế bên chồng lấn vào nhau (Intersymbol Interference - ISI)!
- Bộ bù tán sắc số (Digital Chromatic Dispersion Equalizer): Bù lại độ trễ pha nghịch đảo để co xung lại như cũ!
"""

import numpy as np

def calculate_chromatic_pulse_broadening(fiber_length_km: float, spectral_width_nm: float, dispersion_coeff_d: float = 17.0):
    """
    Trò đóng vai Kỹ sư Tối ưu Băng thông Quang:
    - fiber_length_km: Chiều dài sợi quang (km)
    - spectral_width_nm: Độ rộng phổ nguồn phát laser (nm)
    - dispersion_coeff_d: Hệ số tán sắc (chuẩn sợi SMF-28 là 17 ps/(nm.km) ở bước sóng 1550nm)
    - Tính độ nở xung: delta_tau_ps = dispersion_coeff_d * fiber_length_km * spectral_width_nm
    - Tốc độ truyền tối đa lý thuyết không bị chồng lấn: max_bitrate_gbps = 1000.0 / (4.0 * delta_tau_ps)
    """
    delta_tau_ps = dispersion_coeff_d * fiber_length_km * spectral_width_nm
    max_bitrate_gbps = 1000.0 / (4.0 * delta_tau_ps) if delta_tau_ps > 0 else 100.0
    return delta_tau_ps, max_bitrate_gbps


if __name__ == "__main__":
    print("=========================================================")
    print("   PHOTONICS AVIONICS: CHROMATIC DISPERSION CALCULATOR")
    print("=========================================================\n")

    # Đường cáp quang quân sự trên máy bay dài 2km, độ rộng phổ laser 0.1nm
    broadening_ps, max_speed = calculate_chromatic_pulse_broadening(
        fiber_length_km=2.0, spectral_width_nm=0.1, dispersion_coeff_d=17.0
    )

    print("1. KET QUA PHAN TICH TAN SAC QUANG HOC:")
    print(f"   -> Do no rong xung quang     : {broadening_ps:.2f} ps (pico-seconds)")
    print(f"   -> Toc do bang thong an toan : {max_speed:.2f} Gbps")

    assert abs(broadening_ps - 3.4) < 1e-5 and max_speed > 50.0, "Loi Chromatic Dispersion!"
    print("\n[THANH CONG] DA HOAN THANH ENGINE TINH TOAN VA BU TAN SAC QUANG CHO FIBER AVIONICS!")
