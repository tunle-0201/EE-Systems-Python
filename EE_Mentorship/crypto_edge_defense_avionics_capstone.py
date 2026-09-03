"""
================================================================================
          MODULE W CAPSTONE FINALE: HỆ THỐNG MẬT MÃ AVIONICS QUÂN SỰ CHO DRONE
================================================================================

TÍCH HỢP TOÀN BỘ DEFENSE CRYPTO PIPELINE: SHA-3 KECCAK + CHACHA20 + DIFFIE-HELLMAN
"""

from crypto_edge_sha3_keccak import generate_telemetry_sha3_256
from crypto_edge_chacha20_stream import chacha20_quarter_round
from crypto_edge_diffie_hellman import generate_dh_keypair, compute_shared_secret

def run_defense_avionics_crypto_suite():
    # 1. Thỏa thuận khóa đối xứng bí mật qua Diffie-Hellman
    P, G = 23, 5
    priv_g, priv_d = 6, 15
    pub_g = generate_dh_keypair(G, P, priv_g)
    pub_d = generate_dh_keypair(G, P, priv_d)
    shared_key = compute_shared_secret(pub_d, priv_g, P)

    # 2. Băm toàn vẹn gói chỉ lệnh bằng SHA-3 Keccak
    raw_cmd = b"SECURE_TAKEOFF_MISSION_ALPHA"
    cmd_hash = generate_telemetry_sha3_256(raw_cmd)

    # 3. Mã hóa dòng ChaCha20 bảo vệ payload
    w1, w2, w3, w4 = chacha20_quarter_round(shared_key, 0x12345678, 0x9ABCDEF0, 0xCAFEBABE)

    return shared_key, cmd_hash, w1


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE W CAPSTONE: DEFENSE AVIONICS CRYPTO SUITE")
    print("=========================================================\n")

    key, sha3_dg, enc_block = run_defense_avionics_crypto_suite()

    print("1. KET QUA HOAT DONG TOAN CHUOI DEFENSE CRYPTO SUITE:")
    print(f"   -> Khoa chung Thoa thuan   : {key}")
    print(f"   -> SHA-3 Digest Toan ven   : {sha3_dg[:16]}... (Full 64 hex)")
    print(f"   -> ChaCha20 State Block 1  : 0x{enc_block:08X}")

    assert key == 2 and len(sha3_dg) == 64 and enc_block != 0, "Loi Capstone Defense Crypto!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE W: DEFENSE AVIONICS CRYPTOGRAPHY!")
    print("=========================================================")
