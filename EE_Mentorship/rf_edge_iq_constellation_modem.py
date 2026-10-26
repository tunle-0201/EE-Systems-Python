"""
================================================================================
CHUYEN DE AR: XU LY TIN HIEU VO TUYEN SO BASEBAND SDR & DONG BO VE TINH STARLINK
BAI 1 (MILESTONE AR.1): DIEU CHE GIAI DIEU CHE I/Q CHOM SAO QPSK VA 16-QAM
================================================================================
Chuc nang he thong:
1. Mo hinh hoa khong gian tin hieu I/Q (In-phase & Quadrature):
      s(t) = I * cos(2*pi*f_c*t) - Q * sin(2*pi*f_c*t)
2. Anh xa chom sao QPSK (2 bits/symbol) va 16-QAM (4 bits/symbol) voi ma hoa Gray:
   - Dam bao 2 diem chom sao lan can chi khac nhau dung 1 bit (Hamming distance = 1).
   - Chuan hoa cong suat trung binh cua chom sao ve 1.0 (Average Symbol Energy = 1.0).
3. Giai dieu che hop ly cuc dai Minimum Euclidean Distance (SDR Slicer).
4. Do luong Vector do lech loi EVM (Error Vector Magnitude):
   - EVM RMS (%) va EVM (dB).
   - Xac dinh ty le loi bit BER va ty le loi ky hieu SER duoi kenh nhieu AWGN.

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
              ┌───────────────────────────────────────────────┐
              │          1   N                            2   │
              │         ── * ∑  |s_ideal[k] - s_meas[k]|      │
              │          N  k=1                               │
   EVM_rms =  │ ──────────────────────────────────────────────│
              │          1   N                     2          │
              │         ── * ∑  |s_ideal[k]|^2                │
              │          N  k=1                               │
              └───────────────────────────────────────────────┘
   EVM_percent = EVM_rms * 100%
   EVM_dB      = 20 * log10(EVM_rms)
================================================================================
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class ModulationPerformance:
    """Chi so hieu nang truyen dan chòm sao I/Q."""
    mod_scheme: str
    total_bits: int
    total_symbols: int
    snr_db: float
    bit_errors: int
    symbol_errors: int
    ber: float
    ser: float
    evm_rms_pct: float
    evm_db: float


class IQConstellationModem:
    """
    Bo dieu che va giai dieu che so bang tan goc (Digital Baseband I/Q Modem).
    Ho tro QPSK va 16-QAM voi ma hoa Gray chuan viễn thông DVB-S2X / 5G / Starlink.
    """

    def __init__(self, scheme: str = "QPSK"):
        assert scheme in ["QPSK", "16QAM"], "Che do dieu che phai la QPSK hoac 16QAM"
        self.scheme = scheme
        self.bits_per_symbol = 2 if scheme == "QPSK" else 4
        
        # Bang ma hoa Gray va diem toa do I/Q tuong ung
        self.constellation_map: Dict[str, Tuple[float, float]] = {}
        self.demap_table: List[Tuple[Tuple[float, float], str]] = []
        self._build_constellation()

    def _build_constellation(self):
        """Xay dung toa do chom sao chuan hoa cong suat = 1.0."""
        if self.scheme == "QPSK":
            # QPSK: 4 diem toa do (+-1, +-1) / sqrt(2)
            # He so chuan hoa: norm = 1.0 / sqrt(2) ~ 0.7071
            norm = 1.0 / math.sqrt(2.0)
            gray_qpsk = {
                "00": (-norm, -norm),
                "01": (-norm,  norm),
                "11": ( norm,  norm),
                "10": ( norm, -norm)
            }
            self.constellation_map = gray_qpsk
        else:
            # 16-QAM: 16 diem toa do tren luoi (+-1, +-3)
            # Cong suat trung binh E_avg = (2 * (1^2 + 3^2) / 4) * 2 = 10.0
            # He so chuan hoa: norm = 1.0 / sqrt(10.0) ~ 0.3162
            norm = 1.0 / math.sqrt(10.0)
            # Anh xa Gray 2-bit cho tung truc: 00 -> -3, 01 -> -1, 11 -> +1, 10 -> +3
            axis_map = {
                "00": -3.0 * norm,
                "01": -1.0 * norm,
                "11":  1.0 * norm,
                "10":  3.0 * norm
            }
            gray_16qam = {}
            for b_i in ["00", "01", "11", "10"]:
                for b_q in ["00", "01", "11", "10"]:
                    bit_str = b_i + b_q
                    gray_16qam[bit_str] = (axis_map[b_i], axis_map[b_q])
            self.constellation_map = gray_16qam

        self.demap_table = [(coord, bit_str) for bit_str, coord in self.constellation_map.items()]

    def modulate(self, bit_stream: List[int]) -> List[Tuple[float, float]]:
        """
        Dieu che chuoi bit nhi phan thanh cac ky hieu I/Q phuc.
        """
        assert len(bit_stream) % self.bits_per_symbol == 0, (
            f"Do dai bit_stream phai chia het cho {self.bits_per_symbol}"
        )
        symbols: List[Tuple[float, float]] = []
        k = self.bits_per_symbol

        for i in range(0, len(bit_stream), k):
            chunk = bit_stream[i:i + k]
            bit_str = "".join(str(b) for b in chunk)
            symbols.append(self.constellation_map[bit_str])

        return symbols

    def demodulate(self, rx_symbols: List[Tuple[float, float]]) -> List[int]:
        """
        Giai dieu che hop ly cuc dai Minimum Euclidean Distance (Hard-decision Slicer).
        """
        rx_bits: List[int] = []
        for rx_i, rx_q in rx_symbols:
            min_dist_sq = float("inf")
            best_bits = ""
            for (c_i, c_q), bit_str in self.demap_table:
                dist_sq = (rx_i - c_i) ** 2 + (rx_q - c_q) ** 2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    best_bits = bit_str
            for char in best_bits:
                rx_bits.append(int(char))
        return rx_bits

    def calculate_evm(
        self,
        ideal_symbols: List[Tuple[float, float]],
        rx_symbols: List[Tuple[float, float]]
    ) -> Tuple[float, float]:
        """
        Tinh toan EVM RMS (%) va EVM (dB) giua tin hieu thu va tin hieu ly tuong.
        """
        assert len(ideal_symbols) == len(rx_symbols), "So ky hieu phai bang nhau"
        n = len(ideal_symbols)
        err_pwr_sum = 0.0
        ref_pwr_sum = 0.0

        for (i_id, q_id), (i_rx, q_rx) in zip(ideal_symbols, rx_symbols):
            err_pwr_sum += (i_rx - i_id) ** 2 + (q_rx - q_id) ** 2
            ref_pwr_sum += i_id ** 2 + q_id ** 2

        evm_rms = math.sqrt(err_pwr_sum / max(1e-12, ref_pwr_sum))
        evm_pct = evm_rms * 100.0
        evm_db = 20.0 * math.log10(max(1e-6, evm_rms))
        return evm_pct, evm_db


def apply_awgn_channel(
    symbols: List[Tuple[float, float]],
    snr_db: float,
    seed: int = 42
) -> List[Tuple[float, float]]:
    """
    Mô phỏng kênh truyền vô tuyến nhiễu trắng cộng Gauss (AWGN Channel).
    Nhiễu I và Q độc lập: N_I, N_Q ~ Normal(0, sigma^2).
    """
    random.seed(seed)
    # SNR = P_signal / P_noise. Vi P_signal = 1.0 nen P_noise = 10^(-SNR_dB / 10)
    # P_noise = 2 * sigma^2 (cho ca truc I va Q) => sigma = sqrt(P_noise / 2)
    p_noise = 10.0 ** (-snr_db / 10.0)
    sigma = math.sqrt(p_noise / 2.0)

    noisy_symbols: List[Tuple[float, float]] = []
    for s_i, s_q in symbols:
        # Box-Muller transform tao 2 bien ngau nhien phan phoi chuan
        u1 = max(1e-12, random.random())
        u2 = random.random()
        n_i = sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        n_q = sigma * math.sqrt(-2.0 * math.log(u1)) * math.sin(2.0 * math.pi * u2)
        noisy_symbols.append((s_i + n_i, s_q + n_q))

    return noisy_symbols


def run_modem_benchmark(
    scheme: str,
    snr_db: float,
    num_symbols: int = 10000,
    seed: int = 123
) -> ModulationPerformance:
    """
    Chay danh gia toan dien hieu nang BER, SER va EVM cua Modem.
    """
    modem = IQConstellationModem(scheme)
    random.seed(seed)
    total_bits = num_symbols * modem.bits_per_symbol
    tx_bits = [random.randint(0, 1) for _ in range(total_bits)]

    # Dieu che I/Q
    tx_symbols = modem.modulate(tx_bits)

    # Truyen qua kenh AWGN
    rx_symbols = apply_awgn_channel(tx_symbols, snr_db, seed=seed)

    # Giai dieu che
    rx_bits = modem.demodulate(rx_symbols)

    # Tinh toan loi bit va ky hieu
    bit_errors = sum(1 for b_tx, b_rx in zip(tx_bits, rx_bits) if b_tx != b_rx)
    ber = bit_errors / total_bits

    symbol_errors = 0
    k = modem.bits_per_symbol
    for i in range(0, total_bits, k):
        if tx_bits[i:i + k] != rx_bits[i:i + k]:
            symbol_errors += 1
    ser = symbol_errors / num_symbols

    # Tinh EVM
    evm_pct, evm_db = modem.calculate_evm(tx_symbols, rx_symbols)

    return ModulationPerformance(
        mod_scheme=scheme,
        total_bits=total_bits,
        total_symbols=num_symbols,
        snr_db=snr_db,
        bit_errors=bit_errors,
        symbol_errors=symbol_errors,
        ber=ber,
        ser=ser,
        evm_rms_pct=evm_pct,
        evm_db=evm_db
    )


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AR - LESSON 1: DIGITAL I/Q MODEM (QPSK & 16-QAM)")
    print("=" * 80)

    # 1. Kiem tra tinh toan chom sao va tinh chat ma hoa Gray
    modem_qpsk = IQConstellationModem("QPSK")
    modem_16qam = IQConstellationModem("16QAM")

    print("\n[1] CHOM SAO VA BANG AN XA MA HOA GRAY (GRAY CODING MAP):")
    print("QPSK (4 diem, E_avg = 1.0):")
    for b_str, (ci, cq) in modem_qpsk.constellation_map.items():
        print(f"  Bit '{b_str}' -> I = {ci:>7.4f}, Q = {cq:>7.4f} | R = {math.sqrt(ci**2 + cq**2):.4f}")

    print("\n16-QAM (16 diem, 4 diem goc tieu bieu, E_avg = 1.0):")
    for sample_key in ["0000", "0101", "1111", "1010"]:
        ci, cq = modem_16qam.constellation_map[sample_key]
        print(f"  Bit '{sample_key}' -> I = {ci:>7.4f}, Q = {cq:>7.4f} | Pwr = {ci**2 + cq**2:.4f}")

    # 2. Chay danh gia hieu nang QPSK tren kenh AWGN qua cac muc SNR
    print("\n[2] DANH GIA HIEU NANG QPSK DUOI CAC MUC SNR KHAC NHAU (10,000 SYMBOLS):")
    print(f"{'SNR (dB)':<10} | {'Bit Errors':<12} | {'BER':<12} | {'SER':<12} | {'EVM RMS (%)':<14} | {'EVM (dB)':<10}")
    print("-" * 80)
    
    qpsk_snr_list = [4.0, 7.0, 10.0, 13.0, 16.0]
    perf_qpsk_10db = None
    for snr in qpsk_snr_list:
        perf = run_modem_benchmark("QPSK", snr, num_symbols=10000, seed=42)
        if snr == 10.0:
            perf_qpsk_10db = perf
        print(f"{perf.snr_db:<10.1f} | {perf.bit_errors:<12} | {perf.ber:<12.5e} | {perf.ser:<12.5e} | {perf.evm_rms_pct:<14.2f} | {perf.evm_db:<10.2f}")

    # 3. Chay danh gia hieu nang 16-QAM tren kenh AWGN qua cac muc SNR
    print("\n[3] DANH GIA HIEU NANG 16-QAM DUOI CAC MUC SNR KHAC NHAU (10,000 SYMBOLS):")
    print(f"{'SNR (dB)':<10} | {'Bit Errors':<12} | {'BER':<12} | {'SER':<12} | {'EVM RMS (%)':<14} | {'EVM (dB)':<10}")
    print("-" * 80)

    qam_snr_list = [10.0, 14.0, 18.0, 22.0, 26.0]
    perf_qam_22db = None
    for snr in qam_snr_list:
        perf = run_modem_benchmark("16QAM", snr, num_symbols=10000, seed=42)
        if snr == 22.0:
            perf_qam_22db = perf
        print(f"{perf.snr_db:<10.1f} | {perf.bit_errors:<12} | {perf.ber:<12.5e} | {perf.ser:<12.5e} | {perf.evm_rms_pct:<14.2f} | {perf.evm_db:<10.2f}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Cong suat trung binh cua chom sao phai dung bang 1.0 (sai so < 1e-6)
    p_avg_qpsk = sum(i**2 + q**2 for i, q in modem_qpsk.constellation_map.values()) / len(modem_qpsk.constellation_map)
    p_avg_16qam = sum(i**2 + q**2 for i, q in modem_16qam.constellation_map.values()) / len(modem_16qam.constellation_map)
    assert abs(p_avg_qpsk - 1.0) < 1e-6, f"P_avg QPSK phai bang 1.0, thuc te={p_avg_qpsk}"
    assert abs(p_avg_16qam - 1.0) < 1e-6, f"P_avg 16QAM phai bang 1.0, thuc te={p_avg_16qam}"
    print("\n[INFO] Chuan hoa cong suat chom sao P_avg = 1.0: PASSED!")

    # 2. Tai SNR = 10 dB, QPSK phai co BER < 1.5e-3 (ly thuyet Q(sqrt(10)) ~ 7.8e-4) va EVM < 35%
    assert perf_qpsk_10db.ber < 1.5e-3, f"QPSK tai 10dB BER phai < 1.5e-3, thuc te={perf_qpsk_10db.ber}"
    assert perf_qpsk_10db.evm_rms_pct < 35.0, f"QPSK EVM phai < 35%, thuc te={perf_qpsk_10db.evm_rms_pct:.2f}%"

    # 3. Tai SNR = 22 dB, 16-QAM phai dat tieu chuan 5G / Starlink: EVM < 8.5% va BER = 0
    assert perf_qam_22db.ber == 0.0, f"16-QAM tai 22dB phai khong co loi bit, thuc te BER={perf_qam_22db.ber}"
    assert perf_qam_22db.evm_rms_pct < 8.5, f"16-QAM EVM phai < 8.5%, thuc te={perf_qam_22db.evm_rms_pct:.2f}%"
    print(f"[INFO] 16-QAM tai 22dB: EVM={perf_qam_22db.evm_rms_pct:.2f}% (< 8.5% dat tieu chuan 3GPP/Starlink)")

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: DIGITAL I/Q MODEM VERIFIED!")


if __name__ == "__main__":
    main()
