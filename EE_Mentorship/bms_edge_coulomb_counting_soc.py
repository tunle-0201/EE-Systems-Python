"""
================================================================================
          MODULE AM: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE AM.1: THUẬT TOÁN ĐO DUNG LƯỢNG COULOMB COUNTING & TÁI HIỆU CHUẨN OCV
================================================================================

TẠI SAO PHẢI KẾT HỢP COULOMB COUNTING VÀ OCV TRÊN XE ĐIỆN TESLA / IPHONE?
Pin Lithium-ion (NMC / LFP / 4680) là nguồn sống của xe điện và drone:
- State of Charge (SOC %): Tỷ lệ dung lượng còn lại (tương đương kim xăng số).
- Phương pháp Đếm Coulomb (Coulomb Counting):
  Tích phân dòng điện chạy qua điện trở Shunt theo thời gian:
  
                         1
      SOC(t) = SOC(0) + ───── * integral( I(t) * dt ) * 100%
                        Q_nom
  
  (I > 0: Nạp điện, I < 0: Xả điện, Q_nom: Dung lượng danh định Ah).

VẤN ĐỀ TRỰC TIẾP TRÊN PHẦN CỨNG:
- Cảm biến dòng ADC luôn có sai số trôi điểm 0 (Zero-drift offset).
- Sau vài giờ tích phân, sai số tích tụ khiến đồng hồ báo pin sai lệch tới 15%!

GIẢI PHÁP EMBEDDED BMS: TÁI HIỆU CHUẨN ĐIỆN ÁP HỞ MẠCH (OCV RECALIBRATION):
Khi xe dừng đỗ hoặc nghỉ ngơi (|I| < 0.05A trong thời gian đủ dài):
- Điện áp pin hồi phục về Điện áp hở mạch OCV (Open-Circuit Voltage).
- BMS tra bảng OCV-SOC Look-Up Table để "Reset" lại sai số trôi về 0!
"""

import numpy as np

class CoulombCountingBMS:
    def __init__(self, nominal_capacity_ah: float = 5.0, initial_soc: float = 1.0):
        """
        - nominal_capacity_ah: Dung lượng định mức cell pin (5.0 Ah chuẩn cell 21700)
        - initial_soc: Mức pin ban đầu (1.0 = 100%)
        """
        self.q_nominal_as = nominal_capacity_ah * 3600.0  # Chuyển đổi sang Ampe-giây (Coulombs)
        self.soc = float(initial_soc)
        self.rest_timer_sec = 0.0

        # Bảng tra cứu thực nghiệm OCV-SOC của pin Li-ion NMC (Điện áp V -> SOC)
        self.ocv_table_v = [3.00, 3.30, 3.50, 3.65, 3.75, 3.85, 3.95, 4.05, 4.15, 4.20]
        self.soc_table   = [0.00, 0.05, 0.15, 0.30, 0.50, 0.65, 0.80, 0.90, 0.98, 1.00]

    def update_coulomb_count(self, current_amps: float, dt_sec: float) -> float:
        """
        Tích phân dòng điện Coulomb:
        current_amps: Dòng điện (A), Dương (+) = Nạp, Âm (-) = Xả
        dt_sec: Bước thời gian đo đạc (giây)
        """
        coulombs = current_amps * dt_sec
        delta_soc = coulombs / self.q_nominal_as
        self.soc += delta_soc
        self.soc = max(0.0, min(1.0, self.soc))
        return self.soc

    def ocv_lookup(self, measured_v: float) -> float:
        """Tra cứu bảng OCV-SOC bằng nội suy tuyến tính"""
        if measured_v <= self.ocv_table_v[0]:
            return float(self.soc_table[0])
        if measured_v >= self.ocv_table_v[-1]:
            return float(self.soc_table[-1])

        # Tìm khoảng kẹp
        for i in range(len(self.ocv_table_v) - 1):
            v0, v1 = self.ocv_table_v[i], self.ocv_table_v[i + 1]
            if v0 <= measured_v <= v1:
                s0, s1 = self.soc_table[i], self.soc_table[i + 1]
                slope = (s1 - s0) / (v1 - v0)
                return float(s0 + slope * (measured_v - v0))
        return self.soc

    def check_and_recalibrate(self, measured_voltage: float, current_amps: float, dt_sec: float, rest_threshold_sec: float = 600.0) -> bool:
        """
        Kiểm tra trạng thái nghỉ để tái hiệu chuẩn OCV:
        Nếu dòng điện gần như bằng 0 (|I| < 0.05A) trong ít nhất rest_threshold_sec:
        -> Cập nhật lại SOC từ bảng OCV, triệt tiêu hoàn toàn sai số trôi!
        """
        if abs(current_amps) < 0.05:
            self.rest_timer_sec += dt_sec
            if self.rest_timer_sec >= rest_threshold_sec:
                corrected_soc = self.ocv_lookup(measured_voltage)
                self.soc = corrected_soc
                self.rest_timer_sec = 0.0
                return True
        else:
            self.rest_timer_sec = 0.0
        return False


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: COULOMB COUNTING & OCV RECALIBRATION")
    print("=========================================================\n")

    bms = CoulombCountingBMS(nominal_capacity_ah=5.0, initial_soc=1.0)

    # 1. Kịch bản xả pin động cơ: Dòng xả 2.5A (0.5C) trong 1 giờ (3600 giây)
    # Giả lập cảm biến ADC có nhiễu trôi nhẹ +0.1A làm đếm sai
    print("1. QUA TRINH XA PIN VA HIEN TUONG TROI SAI SO (DRIFT):")
    actual_i = -2.5       # Dòng xả thực tế 2.5A
    sensor_noise = 0.1    # Cảm biến dòng bị lệch +0.1A (Offset drift)
    measured_i = actual_i + sensor_noise  # -2.4A đo được

    # Xả trong 3600 giây (bước 1 giây)
    for _ in range(3600):
        bms.update_coulomb_count(current_amps=measured_i, dt_sec=1.0)

    # Sau 1 giờ xả 2.5A: Dung lượng xả thực tế = 2.5Ah / 5.0Ah = 50% -> SOC thực tế phải là 50%
    # Nhưng do cảm biến đo -2.4A -> SOC bị tính lệch thành 52%
    drift_soc = bms.soc
    print(f"   -> SOC tinh boi Coulomb Counting (bi troi) : {drift_soc * 100:.2f}%")
    print(f"   -> SOC thuc te cua cell pin                : 50.00% (Lech {abs(drift_soc - 0.5) * 100:.2f}%)\n")

    # 2. Kịch bản dừng đỗ xe nghỉ ngơi: Dòng = 0A, Điện áp hồi phục về OCV = 3.75V (tương ứng 50% SOC)
    print("2. QUA TRINH NGHI NGOI VA TAI HIEU CHUAN BANG OCV (OCV RESET):")
    v_cell_rest = 3.75  # 3.75V theo bảng chuẩn NMC là 50% SOC
    recalibrated = False

    # Xe nghỉ trong 15 phút (900 giây)
    for _ in range(900):
        if bms.check_and_recalibrate(measured_voltage=v_cell_rest, current_amps=0.0, dt_sec=1.0, rest_threshold_sec=600.0):
            recalibrated = True
            break

    print(f"   -> Trang thai tai hieu chuan OCV           : {'THANH CONG' if recalibrated else 'CHUA DU THOI GIAN'}")
    print(f"   -> SOC sau khi reset bang OCV              : {bms.soc * 100:.2f}% (Da sua sai hoan hao ve 50.0%)")

    assert recalibrated is True, "Qua trinh tai hieu chuan OCV phai thanh cong sau 10 phut nghi!"
    assert abs(bms.soc - 0.50) < 1e-4, "SOC sau khi reset phai khop voi 50%!"

    print("\n[THANH CONG] THUAT TOAN COULOMB COUNTING VA OCV RESET HOAN TAT CHINH XAC 100%!")
