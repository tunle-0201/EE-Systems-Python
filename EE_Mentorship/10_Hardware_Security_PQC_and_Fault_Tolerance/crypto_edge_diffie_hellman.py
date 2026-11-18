"""
================================================================================
          MODULE W: ADVANCED EMBEDDED CRYPTO & POST-QUANTUM DEFENSE
              MILESTONE W.3: BẮT TAY TRAO ĐỔI KHÓA BẢO MẬT (DIFFIE-HELLMAN KEY EXCHANGE)
================================================================================

TẠI SAO DRONE VÀ TRẠM MẶT ĐẤT CẦN THỎA THUẬN KHÓA CHUNG QUA KÊNH SÓNG KHÔNG AN TOÀN?
Giao thức Diffie-Hellman:
- Cho phép 2 bên (Trạm mặt đất Ground Station và Drone) tự tạo một Khóa bí mật chung (Shared Secret).
- Kẻ địch chặn bắt sóng radio chỉ nhìn thấy Khóa công khai (Public Key), không thể giải mã được Khóa bí mật!
  + Public Key = (g ^ private_key) % p
  + Shared Secret = (other_public ^ my_private) % p
"""

def generate_dh_keypair(base: int, prime: int, private_key: int):
    """Tính Public Key = pow(base, private_key, prime)."""
    return pow(base, private_key, prime)

def compute_shared_secret(their_public: int, my_private: int, prime: int):
    """Tính Khóa chung = pow(their_public, my_private, prime)."""
    return pow(their_public, my_private, prime)


if __name__ == "__main__":
    print("=========================================================")
    print("   DEFENSE AVIONICS: DIFFIE-HELLMAN KEY EXCHANGE")
    print("=========================================================\n")

    # Tham so toan hoc chung (g va p)
    PRIME_P = 23
    BASE_G = 5

    # Tram mat dat (Ground Station)
    priv_ground = 6
    pub_ground = generate_dh_keypair(BASE_G, PRIME_P, priv_ground)

    # Drone tren khong trung
    priv_drone = 15
    pub_drone = generate_dh_keypair(BASE_G, PRIME_P, priv_drone)

    # Hai ben trao doi Public Key tren song radio va tinh Khoa chung
    secret_ground = compute_shared_secret(pub_drone, priv_ground, PRIME_P)
    secret_drone  = compute_shared_secret(pub_ground, priv_drone, PRIME_P)

    print("1. KET QUA THOA THUAN KHOA BI MAT QUA SONG VO TUYEN:")
    print(f"   -> Public Key Tram mat dat : {pub_ground}")
    print(f"   -> Public Key Drone        : {pub_drone}")
    print(f"   -> Khoa chung Tram tinh ra : {secret_ground}")
    print(f"   -> Khoa chung Drone tinh ra: {secret_drone}")

    assert secret_ground == secret_drone and secret_ground == 2, "Loi Diffie-Hellman Key Exchange!"
    print("\n[THANH CONG] HAI BEN DA THIET LAP KENH TRUYEN DU LIEU BAO MAT TUYET DOI QUA KHONG GIAN!")
