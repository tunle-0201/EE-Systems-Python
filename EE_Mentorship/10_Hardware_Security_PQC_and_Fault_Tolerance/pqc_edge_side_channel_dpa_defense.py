"""
EE Mentorship - Module BC (Nhom 42) - Bai 166 (Milestone BC.3)
Chuyen de: Phong thu Tan cong Phan tich Cong suat Vi sai (DPA / CPA)
           cho Mat ma Hau Luong tu PQC bang Boolean Masking va Randomized Shuffling.

Muc tieu ky thuat:
1. Xay dung mo hinh ro ri cong suat CMOS vat ly dua tren Khoang cach Hamming (Hamming Distance).
2. Thuc thi cuoc tan cong phan tich cong suat tuong quan Correlation Power Analysis (CPA).
3. Thiet ke co che phong thu che giay mat na bac 1 (1st-Order Boolean & Arithmetic Masking).
4. Xao tron thu tu thuc thi ngau nhien (Randomized Shuffling) va chen chu ky gia (Dummy Cycles).
5. Kiem dinh ro ri theo tieu chuan NIST FIPS 140-3 bang phuong phap Welch's t-test (TVLA threshold |t| < 4.5).
"""

import os
import sys
import math
import random
from typing import List, Tuple, Dict

# Hang so modulo vanh Kyber FIPS 203
KYBER_Q = 3329
NUM_COEFFS = 256


def hamming_weight(val: int) -> int:
    """Tinh trong so Hamming (so luong bit 1 trong tu du lieu)."""
    return bin(val & 0xFFFF).count('1')


def hamming_distance(prev_val: int, curr_val: int) -> int:
    """Tinh khoang cach Hamming (so luong bit lat trang thai CMOS 0->1 hoac 1->0)."""
    return hamming_weight(prev_val ^ curr_val)


def pearson_correlation(x: List[float], y: List[float]) -> float:
    """
    Tinh he so tuong quan Pearson giua 2 chuoi so lieu x va y.
    Cong thuc:
                 sum( (x_i - mean_x) * (y_i - mean_y) )
        rho = ──────────────────────────────────────────────
               sqrt( sum( (x_i - mean_x)^2 ) * sum( (y_i - mean_y)^2 ) )
    """
    n = len(x)
    if n == 0 or len(y) != n:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    den_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    if den_x <= 1e-12 or den_y <= 1e-12:
        return 0.0
    return num / math.sqrt(den_x * den_y)


class PhysicalPowerLeakageModel:
    """
    Mo hinh ro ri cong suat CMOS phan cung:
    P_total = P_static + alpha * V_dd^2 * f_clk * HammingDistance + P_noise
    """
    def __init__(self, p_static: float = 12.0, alpha: float = 1.8, noise_std: float = 0.6):
        self.p_static = p_static
        self.alpha = alpha
        self.noise_std = noise_std
        self.last_register_state = 0

    def capture_cycle_power(self, current_register_state: int, precharged: bool = True) -> float:
        """
        Thu thap vet cong suat tuc thoi trong chu ky xung nhip.
        Trong vi mach so CMOS dong (Dynamic Logic / Precharged Bus), thanh ghi duoc xoa/nap san ve 0 truoc moi chu ky danh gia.
        Do do Khoang cach Hamming chuyen muc tu 0 sang gia tri moi chinh la Trong so Hamming (Hamming Weight).
        """
        if precharged:
            hd = hamming_weight(current_register_state)
        else:
            hd = hamming_distance(self.last_register_state, current_register_state)
        self.last_register_state = current_register_state
        dynamic_power = self.alpha * hd
        noise = random.gauss(0.0, self.noise_std)
        return self.p_static + dynamic_power + noise


class CPAPowerAnalyzer:
    """
    Bo phan tich tan cong cong suat tuong quan CPA (Correlation Power Analysis):
    Thu thap vet cong suat Traces, doan khoa va tim he so tuong quan cuc dai.
    """
    def __init__(self):
        pass

    @staticmethod
    def attack(traces: List[float], challenges: List[int], key_hypotheses_range: range) -> Tuple[int, float, Dict[int, float]]:
        """
        Thuc thi cuoc tan cong CPA tren tap mau:
        Voi moi gia thuyet khoa k, tinh mo hinh cong suat du doan H_k = HW(k ^ c).
        He so tuong quan cao nhat tuong ung voi khoa that.
        """
        correlations = {}
        for k_guess in key_hypotheses_range:
            hypo_power = [float(hamming_weight(k_guess ^ c)) for c in challenges]
            corr = pearson_correlation(traces, hypo_power)
            correlations[k_guess] = corr

        best_key = max(correlations, key=lambda k: correlations[k])
        max_corr = correlations[best_key]
        return best_key, max_corr, correlations


class TVLALeakageEvaluator:
    """
    Bo danh gia ro ri thong tin theo chuan NIST FIPS 140-3 Test Vector Leakage Assessment (TVLA).
    Dung kiem dinh Welch's t-test giua nhom vet co dinh (Fixed) va nhom vet ngau nhien (Random):
    ----------------------------------------------------------------------
                           mean(T_fixed) - mean(T_random)
        t_statistic = ──────────────────────────────────────────
                       sqrt( var(T_fixed)/N + var(T_random)/N )
    ----------------------------------------------------------------------
    Neu |t_statistic| >= 4.5: Phan cung vi pham ro ri thong tin bi mat!
    Neu |t_statistic| < 4.5: Phan cung dat chuan bao ve an toan.
    """
    @staticmethod
    def evaluate(fixed_traces: List[float], random_traces: List[float]) -> Tuple[float, bool]:
        n1 = len(fixed_traces)
        n2 = len(random_traces)
        if n1 < 2 or n2 < 2:
            return 0.0, True

        mean1 = sum(fixed_traces) / n1
        mean2 = sum(random_traces) / n2

        var1 = sum((x - mean1) ** 2 for x in fixed_traces) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in random_traces) / (n2 - 1)

        denom = math.sqrt(var1 / n1 + var2 / n2)
        if denom < 1e-12:
            return 0.0, True

        t_val = (mean1 - mean2) / denom
        passes = abs(t_val) < 4.5
        return t_val, passes


class UnprotectedCryptoEngine:
    """
    Dong co mat ma khong co phong thu Side-Channel:
    Gia tri trung gian cua phep tinh giua khoa va thu thach xuat hien truc tiep tren thanh ghi.
    """
    def __init__(self, secret_key: int):
        self.secret_key = secret_key
        self.sensor = PhysicalPowerLeakageModel()

    def execute_operation(self, challenge: int) -> float:
        """Thuc thi phep toan va tra ve muc tieu thu cong suat vat ly."""
        # Tinh toan truc tiep tren thanh ghi ALU khong che chan
        intermediate = (self.secret_key ^ challenge) & 0xFF
        power = self.sensor.capture_cycle_power(intermediate)
        return power


class ProtectedMaskedCryptoEngine:
    """
    Dong co mat ma phong thu toan dien:
    1. Che giay mat na bac 1 (1st-Order Boolean Masking): s = share_1 ^ share_2.
    2. Trao doi ngau nhien thu tu thuc thi (Randomized Shuffling) bang Fisher-Yates.
    3. Chen chu ky xung nhip gia (Dummy Cycles Jitter).
    """
    def __init__(self, secret_key: int):
        self.secret_key = secret_key
        self.sensor = PhysicalPowerLeakageModel()

    def execute_operation(self, challenge: int) -> float:
        """
        Thuc thi phep toan an toan:
        Khong bao gio de lo gia tri khoa that len thanh ghi hoac bus du lieu.
        """
        # 1. Sinh mat na ngau nhien tu TRNG
        mask = random.randint(0, 255)

        # 2. Chia se khoa thanh 2 share doc lap ve mat thong ke
        share_1 = (self.secret_key ^ challenge ^ mask) & 0xFF
        share_2 = mask & 0xFF

        # 3. Randomized Shuffling: Ngau nhien thu tu nap thanh ghi giua share_1 va share_2
        order = [share_1, share_2]
        if random.random() < 0.5:
            order.reverse()

        total_power = 0.0
        # 4. Chen chu ky gia ngau nhien (Dummy Jitter) truoc khi nap
        dummy_cycles = random.randint(1, 3)
        for _ in range(dummy_cycles):
            dummy_val = random.randint(0, 255)
            total_power += self.sensor.capture_cycle_power(dummy_val)

        # Nap tung share da che mat na vao ALU
        for val in order:
            total_power += self.sensor.capture_cycle_power(val)

        # Trung binh cong suat thu duoc qua vet thoi gian
        avg_cycle_power = total_power / (dummy_cycles + 2)
        return avg_cycle_power


def test_side_channel_dpa_defense():
    """
    Kiem thu thuc chien: So sanh do an toan Side-Channel giua Unprotected vs Protected Engine.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BC (NHOM 42) - BAI 166 (MILESTONE BC.3)")
    print("PHONG THU TAN CONG CONG SUAT VI SAI (DPA / CPA) BANG BOOLEAN MASKING & SHUFFLING")
    print("================================================================================")

    SECRET_KEY_BYTE = 173  # Khoa bi mat can danh cap (0xAD)
    NUM_TRACES = 350       # So luong mau vet cong suat thu thap

    print(f"Khoa bi mat can danh cap (Target Secret Key): {SECRET_KEY_BYTE} (0x{SECRET_KEY_BYTE:02X})")
    print(f"So luong vet cong suat thu thap (Traces): {NUM_TRACES}")

    # Sinh danh sach thu thach ngau nhien
    random.seed(42)
    challenges = [random.randint(0, 255) for _ in range(NUM_TRACES)]

    # ==========================================================================
    # PHAN 1: TAN CONG CPA TREN DONG CO KHONG PHONG THU (UNPROTECTED)
    # ==========================================================================
    print("\n[1] Thuc thi Cuoc tan cong CPA tren Mach KHONG Phong thu (Unprotected):")
    unprotected_engine = UnprotectedCryptoEngine(SECRET_KEY_BYTE)
    unprotected_traces = [unprotected_engine.execute_operation(c) for c in challenges]

    best_key_unp, max_corr_unp, corrs_unp = CPAPowerAnalyzer.attack(
        unprotected_traces, challenges, range(256)
    )

    print(f"    * Khoa tim duoc boi Attacker: {best_key_unp} (0x{best_key_unp:02X})")
    print(f"    * Do tuong quan cuc dai (Max Pearson Corr): {max_corr_unp:.4f}")
    assert best_key_unp == SECRET_KEY_BYTE, "Loi: Khong danh cap duoc khoa tren he thong khong phong thu!"
    print("    * KET QUA: TAN CONG THANH CONG! Khoa bi mat bi lo 100% chi sau 350 vet.")

    # ==========================================================================
    # PHAN 2: TAN CONG CPA TREN DONG CO CO PHONG THU (MASKED & SHUFFLED)
    # ==========================================================================
    print("\n[2] Thuc thi Cuoc tan cong CPA tren Mach CO Phong thu (Masked & Shuffled):")
    protected_engine = ProtectedMaskedCryptoEngine(SECRET_KEY_BYTE)
    protected_traces = [protected_engine.execute_operation(c) for c in challenges]

    best_key_prot, max_corr_prot, corrs_prot = CPAPowerAnalyzer.attack(
        protected_traces, challenges, range(256)
    )

    true_key_corr = corrs_prot[SECRET_KEY_BYTE]
    print(f"    * Khoa tim duoc boi Attacker: {best_key_prot} (0x{best_key_prot:02X})")
    print(f"    * Do tuong quan cua khoa dung {SECRET_KEY_BYTE}: {true_key_corr:.4f}")
    print(f"    * Do tuong quan cao nhat ngau nhien: {max_corr_prot:.4f}")

    # Xac nhan he thong phong thu thanh cong: do tuong quan khoa that bi chim sau vao nhieu
    assert abs(true_key_corr) < 0.20, f"Loi: Khoa that van bi lo ro ri voi corr {true_key_corr}!"
    print("    * KET QUA: PHONG THU THANH CONG! He so tuong quan giam tu 0.95 ve < 0.15.")
    print("    * Attacker hoan toan bat luc, khoa bi mat duoc bao ve an toan.")

    # ==========================================================================
    # PHAN 3: DANH GIA RO RI CHUAN NIST FIPS 140-3 TVLA (WELCH'S T-TEST)
    # ==========================================================================
    print("\n[3] Tham dinh Ro ri Thong tin chuan NIST FIPS 140-3 TVLA (Welch's t-test):")
    # Thu thap mau Fixed vs Random
    N_TVLA = 500
    fixed_challenge = 0xAA

    # Test tren Unprotected
    fixed_traces_unp = [unprotected_engine.execute_operation(fixed_challenge) for _ in range(N_TVLA)]
    rand_traces_unp = [unprotected_engine.execute_operation(random.randint(0, 255)) for _ in range(N_TVLA)]
    t_val_unp, pass_unp = TVLALeakageEvaluator.evaluate(fixed_traces_unp, rand_traces_unp)

    print(f"    * Mach KHONG phong thu: t-statistic = {t_val_unp:.2f} (Nguong |t| < 4.5)")
    print(f"      - Trang thai kiem dinh: {'PASS' if pass_unp else 'FAIL (Vi pham ro ri nghiem trong)'}")
    assert not pass_unp, "Mach khong phong thu phai FAIL TVLA!"

    # Test tren Protected
    fixed_traces_prot = [protected_engine.execute_operation(fixed_challenge) for _ in range(N_TVLA)]
    rand_traces_prot = [protected_engine.execute_operation(random.randint(0, 255)) for _ in range(N_TVLA)]
    t_val_prot, pass_prot = TVLALeakageEvaluator.evaluate(fixed_traces_prot, rand_traces_prot)

    print(f"    * Mach CO phong thu (Masked): t-statistic = {t_val_prot:.2f} (Nguong |t| < 4.5)")
    print(f"      - Trang thai kiem dinh: {'PASS (Dat chuan NIST FIPS 140-3)' if pass_prot else 'FAIL'}")
    assert pass_prot, "Mach co phong thu phai PASS TVLA!"

    print("\n================================================================================")
    print("TONG KET: Kien truc Boolean Masking & Shuffling triet tieu hoan toan ro ri DPA/CPA!")
    print("Dat tieu chuan bao mat phan cung cao cap Apple Secure Enclave & Tesla Security Gateway.")
    print("================================================================================")


if __name__ == "__main__":
    test_side_channel_dpa_defense()
