"""
================================================================================
CHUYEN DE AF: HARDWARE AUDIO DSP & I2S / PDM MICROPHONE BEAMFORMING
BAI 2: BO LOC SUY GIAM CIC DECIMATION FILTER CHUYEN DOI PDM SANG PCM CHO MICRO MEMS
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Xu ly tin hieu Micro MEMS Apple AirPods / HomePod / Tesla Optimus
Ngon ngu: Python 3 thuan tuy, thiet ke bo loc CIC Multiplierless khong phep nhan
================================================================================
"""

import math
from typing import List, Tuple

# ------------------------------------------------------------------------------
# 1. MO PHONG BO DIEU CHE SIGMA-DELTA (PDM MODULATOR - PHAN CUNG MICRO MEMS)
# ------------------------------------------------------------------------------

class SigmaDeltaModulator1stOrder:
    """
    Bo dieu che Sigma-Delta bac 1 tich hop trong dau thu micro MEMS so:
    Bien doi tin hieu am thanh tuong tu (Analog Audio) sang luong bit 1-bit PDM
    o tan so lay mau cuc cao (Oversampling).
    """
    def __init__(self):
        self.integrator = 0.0

    def step(self, analog_sample: float) -> int:
        """
        analog_sample: gia tri trong khoang [-1.0, +1.0]
        Tra ve bit 1 hoac 0
        """
        # Trừ phản hồi 1-bit DAC
        dac_feedback = 1.0 if self.integrator >= 0.0 else -1.0
        delta = analog_sample - dac_feedback
        self.integrator += delta

        # Bo so sanh Quantizer 1-bit
        pdm_bit = 1 if self.integrator >= 0.0 else 0
        return pdm_bit

# ------------------------------------------------------------------------------
# 2. BO LOC SUY GIAM CIC DECIMATION FILTER (HOGENAUER ARCHITECTURE)
# ------------------------------------------------------------------------------

class CICDecimator3rdOrder:
    """
    Bo loc suy giam Cascaded Integrator-Comb (CIC) bac 3:
    - N = 3 (3 tang Tich luy, 3 tang Vi phan Comb)
    - R = 64 (Ty le suy giam Decimation Factor: 3.072 MHz -> 48 kHz)
    - M = 1 (Do tre vi phan Differential Delay)
    
    Dac diem tuyet voi cua CIC:
    - KHONG DUNG PHEP NHAN (Multiplierless): Chi dung phep cong va tru so nguyen!
    - Do loi DC Gain cua bo loc: G = (R * M)^N = (64 * 1)^3 = 262,144.
    """
    def __init__(self, R: int = 64, N: int = 3, M: int = 1):
        self.R = R
        self.N = N
        self.M = M
        self.dc_gain = (R * M) ** N  # 64^3 = 262,144

        # Bo dem trang thai cho N tang Integrator (chay o tan so PDM cao)
        self.integrators = [0] * N

        # Bo dem trang thai cho N tang Comb (chay o tan so PCM thap)
        # Moi tang Comb can luu tru gia tri tre M mau
        self.comb_delays = [[0] * M for _ in range(N)]

        self.decimation_counter = 0

    def process_pdm_sample(self, pdm_bit: int) -> Tuple[bool, int]:
        """
        Xu ly 1 bit PDM tu micro MEMS:
        - pdm_bit: 1 (dai dien cho +1) hoac 0 (dai dien cho -1)
        Tra ve: (has_pcm_output, pcm_sample_16bit)
        """
        # Chuyen doi bit {0, 1} sang tin hieu luong cuc phan cung {-1, +1}
        x = 1 if pdm_bit == 1 else -1

        # --- GIAI DOAN 1: N TANG TICH LUY (INTEGRATORS) ---
        # y_I1[n] = y_I1[n-1] + x[n]
        self.integrators[0] += x
        for i in range(1, self.N):
            self.integrators[i] += self.integrators[i - 1]

        self.decimation_counter += 1

        # --- GIAI DOAN 2: DECIMATION (LAY MAU 1 TRONG R CHU KY) ---
        if self.decimation_counter >= self.R:
            self.decimation_counter = 0

            # Lay gia tri tu tang Integrator cuoi cung dua sang khau Comb
            comb_input = self.integrators[self.N - 1]

            # --- GIAI DOAN 3: N TANG VI PHAN (COMB STAGES) ---
            current_val = comb_input
            for i in range(self.N):
                # y_C[k] = x_C[k] - x_C[k - M]
                delayed_val = self.comb_delays[i][0]
                diff = current_val - delayed_val

                # Cap nhat bo dem tre
                self.comb_delays[i][0] = current_val
                current_val = diff

            # --- GIAI DOAN 4: CHUAN HOA VE 16-BIT PCM ---
            # Do loi la G = (R*M)^N = 262,144
            # Gia tri am thanh PCM 16-bit co dai [-32768, +32767]
            # normalized = (current_val / G) * 32767
            scaled_pcm = int((current_val / self.dc_gain) * 32767.0)
            # Kep bien do (Saturate)
            scaled_pcm = max(-32768, min(32767, scaled_pcm))

            return (True, scaled_pcm)

        return (False, 0)

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG KHOI PHUC SONG AM THANH
# ------------------------------------------------------------------------------

def test_pdm_to_pcm_conversion():
    """
    Kiem tra toan chuoi PDM -> CIC Decimation:
    - Phat song sin tan so 1000 Hz (Am chuan 1 kHz) voi bien do 0.75
    - Tan so PDM: 3.072 MHz (Fs_pcm = 48 kHz, R = 64)
    - So luong mau PCM can tao: 240 mau (5 ms am thanh)
    - So luong bit PDM can tao: 240 * 64 = 15,360 bits
    """
    fs_pcm = 48000
    r_decim = 64
    fs_pdm = fs_pcm * r_decim # 3,072,000 Hz
    num_pcm_samples = 240
    total_pdm_bits = num_pcm_samples * r_decim

    modulator = SigmaDeltaModulator1stOrder()
    cic = CICDecimator3rdOrder(R=r_decim, N=3, M=1)

    recovered_pcm: List[int] = []

    for bit_idx in range(total_pdm_bits):
        t = bit_idx / fs_pdm
        # Song sin 1000 Hz
        analog_in = 0.75 * math.sin(2.0 * math.pi * 1000.0 * t)

        # 1. PDM Modulation
        pdm_bit = modulator.step(analog_in)

        # 2. CIC Decimation Filtering
        has_out, pcm_val = cic.process_pdm_sample(pdm_bit)
        if has_out:
            recovered_pcm.append(pcm_val)

    assert len(recovered_pcm) == num_pcm_samples, (
        f"Loi: So luong mau PCM thu duoc {len(recovered_pcm)} != {num_pcm_samples}"
    )

    # Bo qua 20 mau dau tien de bo loc CIC vuot qua trang thai xac lap ban dau (Transient response)
    steady_pcm = recovered_pcm[30:]
    max_amp = max(abs(s) for s in steady_pcm)
    expected_peak = 0.75 * 32767.0 # ~24,575

    # Tinh sai so bien do dinh
    amp_error_ratio = abs(max_amp - expected_peak) / expected_peak

    print("--------------------------------------------------------------------------------")
    print("KET QUA KHOI PHUC TIN HIEU AM THANH TU MICRO MEMS PDM QUA CIC DECIMATOR:")
    print(f"-> Tong so bit PDM xu ly     : {total_pdm_bits} bits @ 3.072 MHz")
    print(f"-> So mau PCM 16-bit thu duoc: {len(recovered_pcm)} samples @ 48 kHz")
    print(f"-> Bien do dinh ly thuyet     : {expected_peak:.1f}")
    print(f"-> Bien do dinh thuc te do    : {max_amp} (Sai lech: {amp_error_ratio * 100:.2f}%)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Bien do dinh khong lech qua 12% so voi tin hieu sin goc
    assert amp_error_ratio < 0.12, f"Loi: Bien do sau bo loc CIC lech qua nhieu: {amp_error_ratio}"
    # 2. Tin hieu khong bi tat nghen hoac tran so
    assert max_amp > 18000, "Loi: Tin hieu bi suy hao nang nề!"
    print("[PASS] Test CIC Decimation: Giai dieu che PDM thanh PCM 16-bit 48 kHz thanh cong ruc ro!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO PDM MICROPHONE MEMS & HARDWARE CIC DECIMATION FILTER")
    print("================================================================================")
    test_pdm_to_pcm_conversion()
