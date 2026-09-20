"""
================================================================================
          MODULE AM: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE AM.2: MÔ HÌNH TƯƠNG ĐƯƠNG THEVENIN 1-RC (BATTERY ECM MODEL)
================================================================================

TẠI SAO ĐO ĐIỆN ÁP TRỰC TIẾP KHÔNG THỂ BIẾT CHÍNH XÁC MỨC PIN KHI XE ĐANG CHẠY?
Khi xe tăng tốc hoặc drone bốc đầu:
- Dòng xả lớn (ví dụ 30A) chạy qua pin làm sụt áp tức thời do nội trở thuần R0 (Ohmic Drop: I * R0).
- Sau đó, phản ứng hóa học khuyếch tán ion lithium trong chất điện phân chậm dần (Polarization R1-C1).
- Nếu không có mô hình toán học giải mã, hệ thống sẽ báo pin yếu giả (False Low-Battery Warning)!

MÔ HÌNH TƯƠNG ĐƯƠNG THEVENIN 1-RC (EQUIVALENT CIRCUIT MODEL - ECM):
                  R0               R1
      (+) ───/\/\/\/\───┬────────/\/\/\/\────────┬─── (+)
                        │                        │
                       === C1                   === C_bat (Voc)
                        │                        │
      (-) ──────────────┴────────────────────────┴─── (-)

1. Điện áp cực đầu ra (Terminal Voltage V_t):
        V_t = Voc(SOC) - I_load * R0 - V_p

2. Phương trình vi phân động học phân cực RC (Polarization Voltage V_p):
        d(V_p)     -V_p        I_load
        ─────── = ───────  +  ────────
          dt       R1*C1         C1

   (Với tau = R1 * C1: Hằng số thời gian hồi phục ion hóa học).
"""

import numpy as np

class TheveninBatteryModel:
    def __init__(self, r0_ohm: float = 0.025, r1_ohm: float = 0.015, c1_farad: float = 1200.0):
        """
        - r0_ohm: Nội trở thuần Ohmic (25 mOhm)
        - r1_ohm: Trở kháng phân cực điện hóa (15 mOhm)
        - c1_farad: Điện dung phân cực lớp kép (1200 Farad -> tau = R1*C1 = 18 giay)
        """
        self.r0 = r0_ohm
        self.r1 = r1_ohm
        self.c1 = c1_farad
        self.tau = r1_ohm * c1_farad
        self.v_p = 0.0  # Điện áp phân cực ban đầu

    def get_voc_from_soc(self, soc: float) -> float:
        """Đặc tính điện áp hở mạch OCV phi tuyến theo SOC (3.0V -> 4.2V)"""
        soc = max(0.0, min(1.0, soc))
        return float(3.2 + 0.9 * soc + 0.1 * (soc ** 3))

    def step(self, i_load: float, soc: float, dt_sec: float) -> dict:
        """
        Mô phỏng 1 bước thời gian:
        - i_load: Dòng tải xả (A, giá trị dương = xả dòng)
        - soc: Mức dung lượng hiện tại (0.0 -> 1.0)
        - dt_sec: Chu kỳ lấy mẫu (giây)
        Trả về: dict chứa V_terminal, V_oc, V_p, V_ohmic
        """
        voc = self.get_voc_from_soc(soc)

        # 1. Cập nhật điện áp phân cực V_p theo nghiệm rời rạc vi phân
        # V_p[n+1] = V_p[n] * exp(-dt/tau) + i_load * R1 * (1 - exp(-dt/tau))
        decay = np.exp(-dt_sec / self.tau)
        self.v_p = float(self.v_p * decay + i_load * self.r1 * (1.0 - decay))

        # 2. Sụt áp thuần Ohmic
        v_ohmic = float(i_load * self.r0)

        # 3. Điện áp đo được tại 2 cực pin (Terminal Voltage)
        v_terminal = float(voc - v_ohmic - self.v_p)

        return {
            "v_terminal": v_terminal,
            "v_ocv": voc,
            "v_p": self.v_p,
            "v_ohmic": v_ohmic
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: THEVENIN 1-RC EQUIVALENT CIRCUIT MODEL")
    print("=========================================================\n")

    cell = TheveninBatteryModel(r0_ohm=0.030, r1_ohm=0.020, c1_farad=1000.0)

    # 1. Kiểm tra trạng thái không tải (I = 0A) tại 80% SOC
    soc_test = 0.80
    idle_res = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)
    print(f"1. DIEN AP KHI KHONG TAI (IDLE AT 80% SOC):")
    print(f"   -> Dien ap ho mach (Voc)        : {idle_res['v_ocv']:.3f} V")
    print(f"   -> Dien ap tai cuc (V_terminal) : {idle_res['v_terminal']:.3f} V\n")
    assert abs(idle_res['v_terminal'] - idle_res['v_ocv']) < 1e-4, "Khi I=0, V_terminal phai bang Voc!"

    # 2. Xe đột ngột đạp ga tăng tốc: Xả dòng 10A trong 30 giây
    # Quan sát: Sụt áp tức thời (Ohmic) ngay tại t = 1s, sau đó sụt từ từ do phân cực (RC)
    print("2. DONG HOC SUT AP KHI DAP GA XA TAI NANG (10A DISCHARGE):")
    step1_res = cell.step(i_load=10.0, soc=soc_test, dt_sec=1.0)
    print(f"   -> Giay thu 1  : V_terminal = {step1_res['v_terminal']:.3f} V | Sut ap Ohmic tuc thoi: {step1_res['v_ohmic']:.3f} V")

    # Tiếp tục xả trong 29 giây tiếp theo
    for _ in range(29):
        step_res = cell.step(i_load=10.0, soc=soc_test, dt_sec=1.0)

    print(f"   -> Giay thu 30 : V_terminal = {step_res['v_terminal']:.3f} V | Dien ap phan cuc V_p: {step_res['v_p']:.3f} V")
    assert step_res['v_terminal'] < step1_res['v_terminal'], "Dien ap phai tiep tuc sut do phan cuc hoa hoc!"

    # 3. Xe nhả chân ga (I = 0A): Điện áp hồi phục tức thời phần Ohmic, rồi hồi phục từ từ phần RC
    print("\n3. QUA TRINH NHA GA HOI PHUC DIEN AP (RELAXATION):")
    relax1 = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)
    print(f"   -> Giay nghi dau tien : V_terminal bat tro lai len {relax1['v_terminal']:.3f} V (Hoi phuc Ohmic)")

    # Nghỉ thêm 60 giây để phân cực xả hết
    for _ in range(60):
        relax_final = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)

    print(f"   -> Sau 60 giay nghi   : V_terminal = {relax_final['v_terminal']:.3f} V (Gan nhu tro ve Voc {idle_res['v_ocv']:.3f} V)")
    assert abs(relax_final['v_terminal'] - idle_res['v_ocv']) < 0.05, "Pin phai hoi phuc ve gan Voc khi nghi!"

    print("\n[THANH CONG] MO HINH THEVENIN 1-RC MO PHONG CHINH XAC DONG HOC PIN LITHIUM-ION!")
