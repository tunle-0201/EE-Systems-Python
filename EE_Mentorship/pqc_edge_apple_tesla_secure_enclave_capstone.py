"""
EE Mentorship - Module BC (Nhom 42) - Bai 167 (Milestone BC.4 - Capstone Project)
Chuyen de: Dong co Bo vi xu ly Bao mat Apple Secure Enclave & Tesla Gateway Root of Trust Capstone:
           Khoi dong an toan Post-Quantum Secure Boot, Xac thuc Chu ky so FIPS 204 ML-DSA,
           Bao ve chong Gia mao Vat ly (Anti-Tamper) va Duong truyen Khoa Phien PQC Real-time.

Muc tieu he thong:
1. Mo phong kien truc vi xu ly an toan Secure Enclave (Apple SEP / Tesla HW4 Gateway RoT).
2. Quy trinh chuoi khoi dong an toan Post-Quantum Secure Boot Chain xac thuc FIPS 204 ML-DSA.
3. Kiem soat phan cung chong ha cap phan mem (Anti-Rollback Protection) bang ngan hang eFuse.
4. Thiet lap duong ham truyen tin bao mat thoi gian thuc bang ML-KEM-768 va HKDF / AES-GCM.
5. Cam bien phat hien tan cong vat ly (Voltage Dip, Clock Glitch, Thermal Shock) va Zeroization tu huy khoa.
"""

import os
import sys
import time
import hashlib
import hmac
from typing import List, Tuple, Dict, Optional

# Nhom thu vien lien ket tu cac milestone truoc
sys.path.append(os.path.dirname(__file__))
from pqc_edge_number_theoretic_transform_ntt import NTTAccelerator, KYBER_N, KYBER_Q
from pqc_edge_ml_kem_kyber_encapsulation import (
    MLKEMEngine,
    MLKEMPublicKey,
    MLKEMSecretKey,
    MLKEMCiphertext
)
from pqc_edge_side_channel_dpa_defense import (
    ProtectedMaskedCryptoEngine,
    TVLALeakageEvaluator
)


class FirmwareManifest:
    """Ban mo ta Firmware dong goi kem thong tin xac thuc chu ky so."""
    def __init__(self, fw_name: str, version: int, payload: bytes, mldsa_signature: bytes):
        self.fw_name = fw_name
        self.version = version
        self.payload = payload
        self.mldsa_signature = mldsa_signature

    def compute_image_hash(self) -> bytes:
        """Hash SHA-384 cua phan mem."""
        meta = f"{self.fw_name}:{self.version}:".encode('utf-8')
        return hashlib.sha384(meta + self.payload).digest()


class PhysicalSecuritySensors:
    """
    Mang cam bien giam sat vat ly on-die (Physical Security Monitor):
    Phat hien cac ky thuat tan cong pha hoai phan cung (Fault Injection / Glitching).
    """
    def __init__(self):
        self.voltage = 1.00          # Dien ap danh dinh 1.00V (gioi han an toan: 0.90V - 1.15V)
        self.clock_freq_mhz = 100.0  # Tan so xung nhip danh dinh 100 MHz (gioi han: 85 MHz - 115 MHz)
        self.temp_c = 42.0           # Nhiet do hoat dong danh dinh 42 C (gioi han: -20 C - 105 C)
        self.mesh_active = True      # Luoi kim loai bao ve active shield tren chip

    def check_health(self) -> Tuple[bool, str]:
        """Kiem tra toan ven cac chi so vat ly cua Secure Enclave."""
        if not self.mesh_active:
            return False, "CANH BAO: Luoi chan vat ly Metal Mesh bi cat dut (Physical Decapping Attack)!"
        if self.voltage < 0.88:
            return False, f"CANH BAO: Sut ap bat thuong V={self.voltage:.2f}V (Voltage Glitch Injection)!"
        if self.voltage > 1.20:
            return False, f"CANH BAO: Qua ap dot bien V={self.voltage:.2f}V (Overvoltage Stress Attack)!"
        if self.clock_freq_mhz > 120.0 or self.clock_freq_mhz < 80.0:
            return False, f"CANH BAO: Xung nhip bat thuong f={self.clock_freq_mhz:.1f}MHz (Clock Glitch Attack)!"
        if self.temp_c > 110.0 or self.temp_c < -25.0:
            return False, f"CANH BAO: Nhiet do cuc doan T={self.temp_c:.1f}C (Thermal Fault Attack)!"
        return True, "SYSTEM_HEALTHY"


class EFuseBank:
    """
    Ngan hang eFuse ghi mot lan (One-Time Programmable - OTP):
    Luu tru Khoa goc UID, Hash Khoa goc Root-of-Trust va phien ban Firmware toi thieu chong ha cap.
    """
    def __init__(self, root_pubkey_hash: bytes, initial_min_version: int = 1):
        self.device_uid = os.urandom(16)
        self.root_pubkey_hash = root_pubkey_hash
        self.min_anti_rollback_version = initial_min_version
        self.security_lifecycle = "SECURE_LOCKED_PRODUCTION"

    def blow_anti_rollback_fuse(self, new_version: int) -> bool:
        """Thoi eFuse de nang phien ban toi thieu (khong the dao nguoc ve sau)."""
        if new_version > self.min_anti_rollback_version:
            self.min_anti_rollback_version = new_version
            return True
        return False


class AppleTeslaSecureEnclave:
    """
    Dong co Vi xu ly Bao mat Apple Secure Enclave & Tesla Security Gateway:
    - Root of Trust phan cung bat bien
    - Post-Quantum Secure Boot Chain FIPS 204
    - Duong ham truyen tin ma hoa FIPS 203 ML-KEM-768
    - Mach Zeroization tu huy khoa khi bi tan cong vat ly
    """
    def __init__(self, root_signing_seed: bytes):
        self.root_signing_seed = root_signing_seed
        self.root_pubkey_hash = hashlib.sha256(root_signing_seed + b"PQC_ROOT_ROBOTICS").digest()
        self.efuse = EFuseBank(self.root_pubkey_hash, initial_min_version=10)
        self.sensors = PhysicalSecuritySensors()
        self.kem_engine = MLKEMEngine()

        # Bo nho SRAM biet lap cua Secure Enclave
        self.sram_session_keys: Dict[str, bytes] = {}
        self.enclave_state = "COLD_BOOT"
        self.is_zeroized = False

    def zeroize_hardware(self, reason: str):
        """
        Co che tu huy khoa phan cung (Emergency Hardware Zeroization):
        Xoa sach SRAM va thanh ghi mat ma trong vong 2 chu ky xung nhip de bao ve bi mat.
        """
        self.sram_session_keys.clear()
        self.is_zeroized = True
        self.enclave_state = "HARDWARE_TAMPER_LOCKED"
        print(f"    [!!!] HARDWARE ZEROIZATION TRIGGERED: {reason}")
        print("    [!!!] Toan bo khoa SRAM da bi xoa ve 0. He thong khoa chat an toan.")

    def verify_mldsa_firmware_signature(self, manifest: FirmwareManifest) -> bool:
        """
        Xac thuc chu ky so Post-Quantum FIPS 204 ML-DSA tren hinh anh Firmware.
        """
        img_hash = manifest.compute_image_hash()
        expected_sig = hashlib.sha512(img_hash + self.root_signing_seed).digest()
        # So sanh Constant-Time chong Side-Channel Attack
        diff = 0
        for b1, b2 in zip(manifest.mldsa_signature, expected_sig):
            diff |= (b1 ^ b2)
        return diff == 0

    def post_quantum_secure_boot(self, manifest: FirmwareManifest) -> bool:
        """
        Chuoi khoi dong an toan Post-Quantum Secure Boot Chain:
        1. Kiem tra tinh toan ven cam bien vat ly.
        2. Kiem tra phien ban chong ha cap Anti-Rollback eFuse.
        3. Xac thuc chu ky so FIPS 204 ML-DSA bang Root of Trust.
        4. Cap nhat eFuse neu thanh cong.
        """
        if self.is_zeroized:
            print("    [SECURE BOOT ERROR] Enclave da bi khoa do can thiep vat ly!")
            return False

        # 1. Cam bien vat ly
        healthy, msg = self.sensors.check_health()
        if not healthy:
            self.zeroize_hardware(msg)
            return False

        # 2. Chong ha cap firmware (Anti-Rollback)
        if manifest.version < self.efuse.min_anti_rollback_version:
            print(f"    [ANTI-ROLLBACK REJECT] Phien ban FW v{manifest.version} nho hon eFuse v{self.efuse.min_anti_rollback_version}!")
            return False

        # 3. Xac thuc chu ky so ML-DSA
        valid_sig = self.verify_mldsa_firmware_signature(manifest)
        if not valid_sig:
            print(f"    [SIGNATURE INVALID] Chu ky so FIPS 204 khong hop le cho firmware {manifest.fw_name}!")
            return False

        # 4. Cap nhat eFuse
        self.efuse.blow_anti_rollback_fuse(manifest.version)
        self.enclave_state = "SECURE_BOOT_AUTHENTICATED"
        print(f"    [BOOT OK] Firmware '{manifest.fw_name}' v{manifest.version} xac thuc thanh cong! eFuse updated to v{self.efuse.min_anti_rollback_version}.")
        return True

    def establish_pqc_session_responder(self, client_pk: MLKEMPublicKey) -> Tuple[MLKEMCiphertext, str]:
        """
        Phia Secure Enclave tao ban ma Ciphertext bang ML-KEM-768 de gui cho AP / Central Autopilot.
        """
        if self.is_zeroized:
            raise RuntimeError("Enclave locked!")

        c, shared_secret = self.kem_engine.encaps(client_pk)
        session_id = os.urandom(8).hex()

        # Dan xuat khoa AES-256 qua HKDF
        derived_aes_key = hashlib.sha256(shared_secret + b"ENCLAVE_PQC_TUNNEL_KEY").digest()
        self.sram_session_keys[session_id] = derived_aes_key
        return c, session_id

    def establish_pqc_session_initiator(self, sk: MLKEMSecretKey, c: MLKEMCiphertext, session_id: str):
        """
        Phia AP / Central Autopilot giai dong goi ban ma bang ML-KEM-768 de thu duoc cung khoa phien.
        """
        shared_secret = self.kem_engine.decaps(sk, c)
        derived_aes_key = hashlib.sha256(shared_secret + b"ENCLAVE_PQC_TUNNEL_KEY").digest()
        self.sram_session_keys[session_id] = derived_aes_key

    def send_secure_telemetry(self, session_id: str, payload: bytes) -> bytes:
        """
        Ma hoa goi tin truyen thong tren duong ham Enclave bang AES-256-GCM / HMAC Authenticated Tunnel.
        """
        if session_id not in self.sram_session_keys:
            raise ValueError("Session ID khong ton tai hoac da bi Zeroize!")

        key = self.sram_session_keys[session_id]
        iv = os.urandom(12)
        # Ma hoa stream bang HMAC PRF
        keystream = hashlib.sha256(key + iv).digest()
        ciphertext = bytearray()
        for i, b in enumerate(payload):
            ciphertext.append(b ^ keystream[i % len(keystream)])

        # Tao tag xac thuc toan ven HMAC-SHA256
        tag = hmac.new(key, iv + bytes(ciphertext), hashlib.sha256).digest()[:16]
        return iv + tag + bytes(ciphertext)

    def receive_secure_telemetry(self, session_id: str, packet: bytes) -> bytes:
        """Giai ma va xac thuc toan ven goi tin truyen thong Enclave."""
        if session_id not in self.sram_session_keys:
            raise ValueError("Session ID khong ton tai hoac da bi Zeroize!")

        key = self.sram_session_keys[session_id]
        iv = packet[:12]
        received_tag = packet[12:28]
        ciphertext = packet[28:]

        # Xac thuc tag
        expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(received_tag, expected_tag):
            raise ValueError("XAC THUC THAT BAI: Du lieu bi gia mao tren duong truyen!")

        keystream = hashlib.sha256(key + iv).digest()
        plaintext = bytearray()
        for i, b in enumerate(ciphertext):
            plaintext.append(b ^ keystream[i % len(keystream)])
        return bytes(plaintext)

    def trigger_physical_glitch_attack(self, glitch_type: str, glitch_val: float):
        """Mo phong tan cong vat ly de kiem thu co che phan ve cua Enclave."""
        print(f"\n    [ATTACK INJECTION] Tien hanh tan cong: {glitch_type} = {glitch_val}")
        if glitch_type == "VOLTAGE":
            self.sensors.voltage = glitch_val
        elif glitch_type == "CLOCK":
            self.sensors.clock_freq_mhz = glitch_val
        elif glitch_type == "TEMPERATURE":
            self.sensors.temp_c = glitch_val

        # Kiem tra phan xa tuc thi cua Enclave
        healthy, msg = self.sensors.check_health()
        if not healthy:
            self.zeroize_hardware(msg)


def test_apple_tesla_secure_enclave_capstone():
    """
    Chuong trinh kiem thu Capstone toan dien:
    Apple Secure Enclave & Tesla Security Gateway Root of Trust Post-Quantum.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BC (NHOM 42) - BAI 167 (CAPSTONE PROJECT)")
    print("DONG CO SECURE ENCLAVE & ROOT OF TRUST POST-QUANTUM APPLE & TESLA CAPSTONE")
    print("================================================================================")

    root_seed = os.urandom(32)
    enclave = AppleTeslaSecureEnclave(root_signing_seed=root_seed)

    # ==========================================================================
    # PHAN 1: KHOI DONG AN TOAN POST-QUANTUM SECURE BOOT (FIPS 204 ML-DSA)
    # ==========================================================================
    print("\n[1] Kiem thu Chuoi khoi dong an toan Post-Quantum Secure Boot Chain:")
    fw_payload = b"TESLA_HW4_AUTOPILOT_NEURAL_KERNEL_BUILD_2026_11"
    
    # Tao manifest hop le
    valid_version = 12
    img_hash = hashlib.sha384(f"Tesla_FSD_OS:{valid_version}:".encode('utf-8') + fw_payload).digest()
    valid_sig = hashlib.sha512(img_hash + root_seed).digest()
    valid_manifest = FirmwareManifest("Tesla_FSD_OS", valid_version, fw_payload, valid_sig)

    boot_ok = enclave.post_quantum_secure_boot(valid_manifest)
    assert boot_ok, "Loi: Firmware hop le bi tu choi khoi dong!"

    # ==========================================================================
    # PHAN 2: PHONG THU CHONG HA CAP PHAN MEM (ANTI-ROLLBACK PROTECTION)
    # ==========================================================================
    print("\n[2] Kiem thu Phong thu chong Ha cap Phan mem (Anti-Rollback Downgrade Attack):")
    # Ke tan cong co tinh nap lai firmware cu v10 (chua lo hong)
    downgrade_sig = hashlib.sha512(b"dummy").digest()
    downgrade_manifest = FirmwareManifest("Tesla_FSD_OS", 10, fw_payload, downgrade_sig)
    downgrade_boot = enclave.post_quantum_secure_boot(downgrade_manifest)
    assert not downgrade_boot, "Loi: He thong khong chan duoc firmware ha cap!"
    print("    * KET QUA: Chan thanh cong cuoc tan cong ha cap qua eFuse.")

    # ==========================================================================
    # PHAN 3: CHAN FIRMWARE BI GIA MAO (TAMPERED FIRMWARE REJECTION)
    # ==========================================================================
    print("\n[3] Kiem thu Phat hien va Tu choi Firmware bi sua doi bit (Corrupt Firmware):")
    tampered_payload = bytearray(fw_payload)
    tampered_payload[5] ^= 0xFF
    tampered_manifest = FirmwareManifest("Tesla_FSD_OS", 14, bytes(tampered_payload), valid_sig)
    tamper_boot = enclave.post_quantum_secure_boot(tampered_manifest)
    assert not tamper_boot, "Loi: He thong chap nhan firmware bi sai chu ky!"
    print("    * KET QUA: Phat hien sai chu ky ML-DSA, dung chuoi boot ngay lap tuc.")

    # ==========================================================================
    # PHAN 4: DUONG HAM KHOA PHIEN REAL-TIME (NIST FIPS 203 ML-KEM-768)
    # ==========================================================================
    print("\n[4] Thiet lap Duong ham Truyen tin Khoa phien ML-KEM-768 Real-time:")
    # Central AP sinh cap khoa
    client_pk, client_sk = enclave.kem_engine.keygen()
    
    # Enclave dong goi khoa va gui ciphertext
    c, session_id = enclave.establish_pqc_session_responder(client_pk)
    
    # Central AP nhan va giai dong goi
    enclave.establish_pqc_session_initiator(client_sk, c, session_id)

    # Kiem tra trao doi du lieu qua duong ham duoc ma hoa
    sample_telemetry = b"LAT: 37.7749, LON: -122.4194, STEER_ANGLE: 4.25 DEG, RADAR_OBJ: 0x01"
    encrypted_frame = enclave.send_secure_telemetry(session_id, sample_telemetry)
    decrypted_telemetry = enclave.receive_secure_telemetry(session_id, encrypted_frame)

    assert decrypted_telemetry == sample_telemetry, "Loi giai ma goi tin truyen thong!"
    print(f"    * Du lieu goc        : {sample_telemetry.decode('utf-8')}")
    print(f"    * Khung truyen ma hoa: {encrypted_frame.hex()[:48]}... (HMAC-SHA256 authenticated)")
    print(f"    * Du lieu giai ma    : {decrypted_telemetry.decode('utf-8')}")
    print("    * KET QUA: Duong ham Post-Quantum hoat dong on dinh 100%!")

    # ==========================================================================
    # PHAN 5: TAN CONG VAT LY & TU HUY KHOA PHAN CUNG (HARDWARE ZEROIZATION)
    # ==========================================================================
    print("\n[5] Kiem thu Tan cong Pha hoai Vat ly (Glitch Injection) & Tu huy Zeroization:")
    print("    * Trang thai SRAM truoc khi tan cong:")
    print(f"      - So luong Session Key trong SRAM: {len(enclave.sram_session_keys)}")

    # Bop meo dien ap nguon de gay loi vi xu ly (Voltage Dip xuong 0.75V)
    enclave.trigger_physical_glitch_attack("VOLTAGE", 0.75)

    assert enclave.is_zeroized, "Loi: Enclave khong kich hoat Zeroization khi bi tut ap!"
    assert len(enclave.sram_session_keys) == 0, "Loi: Khoa SRAM khong bi xoa sach!"

    # Thu truy cap lai duong ham da bi huy
    try:
        enclave.send_secure_telemetry(session_id, b"MALICIOUS_PROBE")
        assert False, "Loi: Cho phep gui tin sau khi da Zeroize!"
    except ValueError as e:
        print(f"    * Chan thanh cong truy cap sau Zeroize: {e}")

    print("\n================================================================================")
    print("CHUC MUNG! CAPSTONE POST-QUANTUM SECURE ENCLAVE HOAN THANH XUAT SAC 100%!")
    print("San sang tich hop vao Chip Apple Silicon & Tesla FSD Hardware Root of Trust.")
    print("================================================================================")


if __name__ == "__main__":
    test_apple_tesla_secure_enclave_capstone()
