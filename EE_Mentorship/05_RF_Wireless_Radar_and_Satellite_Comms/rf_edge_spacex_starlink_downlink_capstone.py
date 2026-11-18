"""
================================================================================
CHUYEN DE AR: XU LY TIN HIEU VO TUYEN SO BASEBAND SDR & DONG BO VE TINH STARLINK
BAI 4 (MILESTONE AR.4 - CAPSTONE PROJECT):
DONG CO THU PHAT VE TINH BANG RONG SPACEX STARLINK KU-BAND SDR DOWNLINK CAPSTONE
================================================================================
Kien truc he thong SDR tich hop toan dien:
1. May phat ve tinh Starlink (TX Engine):
   - Dong goi khung tin tieu chuan vu tru CCSDS voi tu dong bo Frame Sync (0x1ACFFC1D).
   - Dieu che chom sao I/Q Gray-coded QPSK / 16-QAM voi chuan hoa nang luong E_avg = 1.0.
   - Bo loc dinh hinh xung TX Root-Raised Cosine (RRC FIR, beta = 0.25, SPS = 4).
2. Mo phong kenh truyen khong gian vu tru (Satellite Channel):
   - Dich tan Doppler LEO Delta_f len den 40 kHz tai bang Ku (12.5 GHz).
   - Sai lech pha ban dau theta_0 ngau nhien.
   - Suy hao duong truyen va nhieu nhiet trang Gauss AWGN.
3. May thu tram mat dat Starlink Dishy (RX Engine):
   - Bo loc tuong thich RX RRC Matched Filter tang toi da SNR.
   - Dong bo nhip lay mau ky hieu (Symbol Timing Decimation).
   - Vong khoa pha so Costas Loop bac 2 triet tieu Doppler va khoa pha chom sao.
   - Giai dieu che Slicer Gray va khoi phuc dong goi khung Frame Sync.
4. Tinh toan EVM RMS, BER, FER va thong luong truyen dan (Throughput Mbps).

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               1      N
   EVM_rms = ────── * ∑  |s_rx[k] - s_ideal[k]|^2
             P_avg   k=1

   Throughput = Symbol_Rate * Bits_Per_Symbol * (1 - FER)

   Delta_f_doppler = f_carrier * (v_orbital / c) * cos(theta_elevation)
================================================================================
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


@dataclass
class StarlinkLinkSpecs:
    """Thong so he thong truyen dan ve tinh SpaceX Starlink Downlink."""
    carrier_freq_ghz: float     # 12.5 GHz (Ku-Band)
    symbol_rate_msps: float     # 20.0 MSym/s
    modulation: str             # "QPSK" hoac "16QAM"
    rrc_beta: float             # 0.25 (Roll-off factor)
    sps: int                    # 4 samples/symbol
    filter_span: int            # 8 symbols
    snr_db: float               # Ty so tin hieu tren nhieu (dB)
    doppler_freq_khz: float     # Do lech tan so Doppler do quy dao LEO (kHz)
    phase_offset_deg: float     # Do lech pha ban dau (do)


@dataclass
class StarlinkMissionReport:
    """Ket qua danh gia chat luong tuyen truyen dan ve tinh Starlink."""
    mission_name: str
    modulation: str
    snr_db: float
    doppler_khz: float
    raw_data_rate_mbps: float
    effective_throughput_mbps: float
    evm_rms_pct: float
    evm_db: float
    bit_error_rate: float
    frame_sync_detected: bool
    carrier_lock_status: bool
    status_summary: str


class StarlinkSDRTransceiverCapstone:
    """
    Dong co thu phat SDR toan dien cho tuyen xuong ve tinh SpaceX Starlink.
    """

    CCSDS_SYNC_WORD = [0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1]  # 0x1ACFFC1D (32 bits)

    def __init__(self, specs: StarlinkLinkSpecs):
        self.specs = specs
        self.bits_per_symbol = 2 if specs.modulation == "QPSK" else 4
        self.rrc_taps = self._design_rrc_filter()
        self.constellation = self._init_constellation()

    def _init_constellation(self) -> Dict[str, Tuple[float, float]]:
        """Khoi tao ban do chom sao Gray chuan hoa cong suat trung binh = 1.0."""
        if self.specs.modulation == "QPSK":
            norm = 1.0 / math.sqrt(2.0)
            return {
                "00": (-norm, -norm),
                "01": (-norm,  norm),
                "11": ( norm,  norm),
                "10": ( norm, -norm)
            }
        else:
            norm = 1.0 / math.sqrt(10.0)
            axis = {"00": -3.0*norm, "01": -1.0*norm, "11": 1.0*norm, "10": 3.0*norm}
            qam = {}
            for b_i in ["00", "01", "11", "10"]:
                for b_q in ["00", "01", "11", "10"]:
                    qam[b_i + b_q] = (axis[b_i], axis[b_q])
            return qam

    def _design_rrc_filter(self) -> List[float]:
        """Thiet ke bo loc RRC doi xung chuan hoa tong nang luong = 1.0."""
        beta = self.specs.rrc_beta
        sps = self.specs.sps
        span = self.specs.filter_span
        total_taps = span * sps + 1
        taps: List[float] = [0.0] * total_taps
        half = total_taps // 2

        for i in range(total_taps):
            t = (i - half) / float(sps)
            if abs(t) < 1e-9:
                val = 1.0 - beta + (4.0 * beta / math.pi)
            elif abs(abs(t) - 1.0 / (4.0 * beta)) < 1e-6:
                term1 = (1.0 + 2.0 / math.pi) * math.sin(math.pi / (4.0 * beta))
                term2 = (1.0 - 2.0 / math.pi) * math.cos(math.pi / (4.0 * beta))
                val = (beta / math.sqrt(2.0)) * (term1 + term2)
            else:
                num = math.sin(math.pi * t * (1.0 - beta)) + 4.0 * beta * t * math.cos(math.pi * t * (1.0 + beta))
                den = math.pi * t * (1.0 - (4.0 * beta * t) ** 2)
                val = num / den
            taps[i] = val

        energy = math.sqrt(sum(c ** 2 for c in taps))
        return [c / energy for c in taps]

    def run_downlink_simulation(
        self,
        mission_name: str,
        payload_bits_count: int = 4000,
        seed: int = 42
    ) -> StarlinkMissionReport:
        """
        Mo phong toan ven chu trinh truyen dan tu Ve tinh xuong Mat dat.
        """
        random.seed(seed)

        # -------------------------------------------------------------
        # 1. MAY PHAT VE TINH (TX PIPELINE)
        # -------------------------------------------------------------
        # Dong goi khung DVB-S2 / Starlink tieu chuan:
        # [ Acquisition Pilot: 64 ky hieu ] + [ 32 bit CCSDS Sync Word ] + [ Payload Data ]
        num_pilot_symbols = 64
        pilot_bits = [1, 0, 1, 0] * (num_pilot_symbols * self.bits_per_symbol // 4)
        payload = [random.randint(0, 1) for _ in range(payload_bits_count)]
        tx_bits = pilot_bits + self.CCSDS_SYNC_WORD + payload

        # Dieu che I/Q Gray
        k = self.bits_per_symbol
        tx_symbols: List[Tuple[float, float]] = []
        for i in range(0, len(tx_bits), k):
            chunk = "".join(str(b) for b in tx_bits[i:i + k])
            tx_symbols.append(self.constellation[chunk])

        # Upsampling chen 0 va loc phat TX RRC
        sps = self.specs.sps
        tx_upsampled_i = [0.0] * (len(tx_symbols) * sps)
        tx_upsampled_q = [0.0] * (len(tx_symbols) * sps)
        for i, (si, sq) in enumerate(tx_symbols):
            tx_upsampled_i[i * sps] = si
            tx_upsampled_q[i * sps] = sq

        # Tich chap loc TX
        def fir_filter(sig, kernel):
            out = [0.0] * (len(sig) + len(kernel) - 1)
            for m in range(len(sig)):
                if abs(sig[m]) < 1e-12:
                    continue
                for n in range(len(kernel)):
                    out[m + n] += sig[m] * kernel[n]
            return out

        tx_wave_i = fir_filter(tx_upsampled_i, self.rrc_taps)
        tx_wave_q = fir_filter(tx_upsampled_q, self.rrc_taps)

        # -------------------------------------------------------------
        # 2. KENH TRUYEN VE TINH (SATELLITE CHANNEL IMPAIRMENTS)
        # -------------------------------------------------------------
        f_sample = self.specs.symbol_rate_msps * 1e6 * sps
        f_doppler_hz = self.specs.doppler_freq_khz * 1e3
        delta_omega_sample = (2.0 * math.pi * f_doppler_hz) / f_sample
        phase_0_rad = self.specs.phase_offset_deg * (math.pi / 180.0)

        # Nhieu AWGN tren tung mau
        p_noise = 10.0 ** (-self.specs.snr_db / 10.0)
        sigma = math.sqrt((p_noise / float(sps)) / 2.0)

        n_samples = len(tx_wave_i)
        rx_channel_i = [0.0] * n_samples
        rx_channel_q = [0.0] * n_samples

        for n in range(n_samples):
            phi = delta_omega_sample * n + phase_0_rad
            cos_p = math.cos(phi)
            sin_p = math.sin(phi)
            sig_rot_i = tx_wave_i[n] * cos_p - tx_wave_q[n] * sin_p
            sig_rot_q = tx_wave_i[n] * sin_p + tx_wave_q[n] * cos_p

            u1 = max(1e-12, random.random())
            u2 = random.random()
            n_i = sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            n_q = sigma * math.sqrt(-2.0 * math.log(u1)) * math.sin(2.0 * math.pi * u2)

            rx_channel_i[n] = sig_rot_i + n_i
            rx_channel_q[n] = sig_rot_q + n_q

        # -------------------------------------------------------------
        # 3. MAY THU TRAM MAT DAT STARLINK DISHY (RX PIPELINE)
        # -------------------------------------------------------------
        rx_matched_i = fir_filter(rx_channel_i, self.rrc_taps)
        rx_matched_q = fir_filter(rx_channel_q, self.rrc_taps)

        total_delay = len(self.rrc_taps) - 1

        sampled_symbols: List[Tuple[float, float]] = []
        for i in range(len(tx_symbols)):
            sample_idx = total_delay + i * sps
            if sample_idx < len(rx_matched_i):
                sampled_symbols.append((rx_matched_i[sample_idx], rx_matched_q[sample_idx]))

        delta_omega_sym = delta_omega_sample * sps
        
        corrected_symbols: List[Tuple[float, float]] = []
        phase_hat = 0.0
        freq_int = 0.0
        k_p = 0.08
        k_i = 0.003

        norm_qam = 1.0 / math.sqrt(10.0)
        def slice_coord(val):
            if val < -2.0 * norm_qam:
                return -3.0 * norm_qam
            elif val < 0:
                return -1.0 * norm_qam
            elif val < 2.0 * norm_qam:
                return 1.0 * norm_qam
            else:
                return 3.0 * norm_qam

        for r_i, r_q in sampled_symbols:
            cos_v = math.cos(phase_hat)
            sin_v = math.sin(phase_hat)
            i_rot =  r_i * cos_v + r_q * sin_v
            q_rot = -r_i * sin_v + r_q * cos_v
            corrected_symbols.append((i_rot, q_rot))

            # Phase Error Detector
            if self.specs.modulation == "QPSK":
                sgn_i = 1.0 if i_rot >= 0 else -1.0
                sgn_q = 1.0 if q_rot >= 0 else -1.0
                err = sgn_i * q_rot - sgn_q * i_rot
            else:
                hat_i = slice_coord(i_rot)
                hat_q = slice_coord(q_rot)
                err = (hat_i * q_rot - hat_q * i_rot) * 2.5

            freq_int += k_i * err
            freq_est = k_p * err + freq_int
            phase_hat += freq_est
            while phase_hat > math.pi:
                phase_hat -= 2.0 * math.pi
            while phase_hat < -math.pi:
                phase_hat += 2.0 * math.pi

        # -------------------------------------------------------------
        # 4. GIAI QUYET 4-FOLD PHASE AMBIGUITY VOI CCSDS PREAMBLE
        # -------------------------------------------------------------
        sync_bits_needed = len(self.CCSDS_SYNC_WORD)
        sync_syms_needed = (sync_bits_needed + self.bits_per_symbol - 1) // self.bits_per_symbol
        demap_table = [(coord, bit_str) for bit_str, coord in self.constellation.items()]

        best_rot_idx = 0
        best_sync_matches = -1

        for rot_idx in range(4):
            rot_rad = rot_idx * (math.pi / 2.0)
            c_rot = math.cos(-rot_rad)
            s_rot = math.sin(-rot_rad)
            test_bits = []
            # Lay mau tu vi tri num_pilot_symbols (khi Costas Loop da hoi tu)
            for s_idx in range(sync_syms_needed):
                si, sq = corrected_symbols[num_pilot_symbols + s_idx]
                r_si = si * c_rot - sq * s_rot
                r_sq = si * s_rot + sq * c_rot
                min_d = float("inf")
                best_b = ""
                for (pt_i, pt_q), bit_str in demap_table:
                    d = (r_si - pt_i)**2 + (r_sq - pt_q)**2
                    if d < min_d:
                        min_d = d
                        best_b = bit_str
                test_bits.extend([int(c) for c in best_b])
            matches = sum(1 for b1, b2 in zip(test_bits[:sync_bits_needed], self.CCSDS_SYNC_WORD) if b1 == b2)
            if matches > best_sync_matches:
                best_sync_matches = matches
                best_rot_idx = rot_idx

        # Xoay toan bo ky hieu theo goc giai quyet ambiguity
        final_rot_rad = best_rot_idx * (math.pi / 2.0)
        c_final = math.cos(-final_rot_rad)
        s_final = math.sin(-final_rot_rad)
        resolved_symbols = []
        for si, sq in corrected_symbols:
            resolved_symbols.append((si * c_final - sq * s_final, si * s_final + sq * c_final))
        corrected_symbols = resolved_symbols

        # Giai dieu che toan bo chuoi ky hieu
        rx_bits: List[int] = []
        for c_i, c_q in corrected_symbols:
            min_dist = float("inf")
            best_chunk = ""
            for (pt_i, pt_q), bit_str in demap_table:
                d = (c_i - pt_i)**2 + (c_q - pt_q)**2
                if d < min_dist:
                    min_dist = d
                    best_chunk = bit_str
            for char in best_chunk:
                rx_bits.append(int(char))

        # -------------------------------------------------------------
        # 5. TINH TOAN CHI SO HIEN TRANG TREN VUNG DU LIEU PAYLOAD
        # -------------------------------------------------------------
        payload_sym_start = num_pilot_symbols + sync_syms_needed
        payload_bit_start = payload_sym_start * self.bits_per_symbol

        # Tinh toan EVM tren vung Payload
        evm_err = 0.0
        evm_ref = 0.0
        for i in range(payload_sym_start, len(tx_symbols)):
            t_i, t_q = tx_symbols[i]
            c_i, c_q = corrected_symbols[i]
            evm_err += (c_i - t_i)**2 + (c_q - t_q)**2
            evm_ref += t_i**2 + t_q**2

        evm_rms = math.sqrt(evm_err / max(1e-12, evm_ref))
        evm_pct = evm_rms * 100.0
        evm_db = 20.0 * math.log10(max(1e-6, evm_rms))

        # Tinh BER tren vung Payload
        tx_payload_bits = tx_bits[payload_bit_start:]
        rx_payload_bits = rx_bits[payload_bit_start:]
        bit_errors = sum(1 for b1, b2 in zip(tx_payload_bits, rx_payload_bits) if b1 != b2)
        ber = bit_errors / len(tx_payload_bits)

        # Kiem tra dong bo khung CCSDS
        sync_found = (best_sync_matches >= sync_bits_needed - 1)

        # Tinh thong luong truyen dan
        raw_rate_mbps = self.specs.symbol_rate_msps * self.bits_per_symbol
        eff_rate_mbps = raw_rate_mbps * (1.0 - ber)

        lock_status = (abs(freq_int - delta_omega_sym) < 0.015)

        summary = "EXCELLENT LINK (LOS)" if ber < 1e-4 else ("DEGRADED LINK (RAIN FADE)" if ber < 0.02 else "LINK DOWN")

        return StarlinkMissionReport(
            mission_name=mission_name,
            modulation=self.specs.modulation,
            snr_db=self.specs.snr_db,
            doppler_khz=self.specs.doppler_freq_khz,
            raw_data_rate_mbps=raw_rate_mbps,
            effective_throughput_mbps=eff_rate_mbps,
            evm_rms_pct=evm_pct,
            evm_db=evm_db,
            bit_error_rate=ber,
            frame_sync_detected=sync_found,
            carrier_lock_status=lock_status,
            status_summary=summary
        )


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AR - LESSON 4 (CAPSTONE PROJECT)")
    print("SPACEX STARLINK BROADBAND SATELLITE SDR DOWNLINK ENGINE")
    print("=" * 80)

    # -------------------------------------------------------------
    # KICH BAN 1: QUAN LY TRANH THU DICH VU (QPSK CLEAR SKY, DOPPLER +25 KHZ)
    # -------------------------------------------------------------
    specs_qpsk_los = StarlinkLinkSpecs(
        carrier_freq_ghz=12.5,
        symbol_rate_msps=20.0,
        modulation="QPSK",
        rrc_beta=0.25,
        sps=4,
        filter_span=8,
        snr_db=18.0,
        doppler_freq_khz=25.0,     # Doppler +25 kHz
        phase_offset_deg=45.0
    )
    cap_los = StarlinkSDRTransceiverCapstone(specs_qpsk_los)
    rep_los = cap_los.run_downlink_simulation(
        mission_name="Starlink Ku Downlink - Clear Sky LOS (QPSK)",
        payload_bits_count=4000,
        seed=123
    )

    # -------------------------------------------------------------
    # KICH BAN 2: MUA DONG TANG DOI LUU (RAIN FADE, DOPPLER +35 KHZ, SNR = 11 dB)
    # -------------------------------------------------------------
    specs_rain = StarlinkLinkSpecs(
        carrier_freq_ghz=12.5,
        symbol_rate_msps=20.0,
        modulation="QPSK",
        rrc_beta=0.25,
        sps=4,
        filter_span=8,
        snr_db=11.0,
        doppler_freq_khz=35.0,     # Doppler cao +35 kHz
        phase_offset_deg=-60.0
    )
    cap_rain = StarlinkSDRTransceiverCapstone(specs_rain)
    rep_rain = cap_rain.run_downlink_simulation(
        mission_name="Starlink Ku Downlink - Heavy Rain Fade (QPSK)",
        payload_bits_count=4000,
        seed=456
    )

    # -------------------------------------------------------------
    # KICH BAN 3: BANG RONG TOC DO CAO (16-QAM BROADBAND 80 MBPS, SNR = 22 dB)
    # -------------------------------------------------------------
    specs_qam_hi = StarlinkLinkSpecs(
        carrier_freq_ghz=12.5,
        symbol_rate_msps=20.0,
        modulation="16QAM",
        rrc_beta=0.25,
        sps=4,
        filter_span=8,
        snr_db=22.0,
        doppler_freq_khz=0.0,      # Coarse Doppler corrected
        phase_offset_deg=0.0
    )
    cap_qam_hi = StarlinkSDRTransceiverCapstone(specs_qam_hi)
    rep_qam_hi = cap_qam_hi.run_downlink_simulation(
        mission_name="Starlink Ku Downlink - 16-QAM Broadband (80 Mbps)",
        payload_bits_count=4000,
        seed=789
    )

    print("\n[1] BANG TONG KET HIEN TRANG TUYEN TRUYEN DAN VE TINH STARLINK:")
    print(f"{'Kich ban / Nhiem vu':<46} | {'Mod':<6} | {'SNR (dB)':<8} | {'Doppler':<10} | {'Throughput':<12} | {'EVM (%)':<9} | {'BER':<10} | {'Trang thai':<15}")
    print("-" * 128)
    for rep in [rep_los, rep_rain, rep_qam_hi]:
        print(f"{rep.mission_name:<46} | {rep.modulation:<6} | {rep.snr_db:<8.1f} | {rep.doppler_khz:<10.1f} | {rep.effective_throughput_mbps:<12.2f} | {rep.evm_rms_pct:<9.2f} | {rep.bit_error_rate:<10.5e} | {rep.status_summary:<15}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Kich ban 1 (Clear Sky QPSK):
    assert rep_los.raw_data_rate_mbps == 40.0, "QPSK tai 20 MSps phai dat 40 Mbps"
    assert rep_los.evm_rms_pct < 10.0, f"QPSK EVM phai < 10%, thuc te={rep_los.evm_rms_pct:.2f}%"
    assert rep_los.bit_error_rate == 0.0, "QPSK tai 18 dB phai hoan toan khong co loi bit"
    assert rep_los.frame_sync_detected, "Tu dong bo khung CCSDS phai tim thay"
    print(f"\n[INFO] Kich ban 1 (QPSK LOS): EVM={rep_los.evm_rms_pct:.2f}% | BER=0.000000 (KHONG LOI BIT!)")

    # 2. Kich ban 2 (Heavy Rain Fade QPSK 11 dB, Doppler +35 kHz):
    assert rep_rain.evm_rms_pct < 20.0, f"Rain fade EVM phai < 20%, thuc te={rep_rain.evm_rms_pct:.2f}%"
    assert rep_rain.bit_error_rate < 1e-3, f"Rain fade BER phai < 1e-3, thuc te={rep_rain.bit_error_rate}"
    assert rep_rain.frame_sync_detected, "Frame sync phai bat duoc trong mua giong"
    print(f"[INFO] Kich ban 2 (Rain Fade): EVM={rep_rain.evm_rms_pct:.2f}% | Throughput={rep_rain.effective_throughput_mbps:.1f} Mbps (LIEN LAC KHONG BI CAT!)")

    # 3. Kich ban 3 (16-QAM Broadband 80 Mbps):
    assert rep_qam_hi.raw_data_rate_mbps == 80.0, "16-QAM tai 20 MSps phai dat 80 Mbps"
    assert rep_qam_hi.evm_rms_pct < 6.0, f"16-QAM EVM phai < 6.0%, thuc te={rep_qam_hi.evm_rms_pct:.2f}%"
    assert rep_qam_hi.bit_error_rate == 0.0, "16-QAM tai 22 dB phai hoan toan khong co loi bit"
    assert rep_qam_hi.frame_sync_detected, "Frame sync 16-QAM phai tim thay"
    print(f"[INFO] Kich ban 3 (16-QAM 80Mbps): EVM={rep_qam_hi.evm_rms_pct:.2f}% (< 6% dat chuan DVB-S2X) | Throughput={rep_qam_hi.effective_throughput_mbps:.1f} Mbps")

    print("\n>> [PASSED] CAPSTONE PROJECT 100% SUCCESSFUL: STARLINK DOWNLINK SDR VERIFIED!")


if __name__ == "__main__":
    main()
