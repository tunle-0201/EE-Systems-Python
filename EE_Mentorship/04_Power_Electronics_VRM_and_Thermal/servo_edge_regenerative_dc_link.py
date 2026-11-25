"""EE MENTORSHIP - BAI 240 - BU.5: REGENERATIVE DC LINK ENERGY.

BUOC 1 - HOP CONG CU
  Tu DC bus C=2 mF co nang luong E=0.5*C*V^2 [J]. Quy uoc P_ac>0 khi
  inverter CAP nang luong cho motor, P_ac<0 khi motor tra nang luong ve bus.
    E_next = E + source_energy - (P_ac+Pbrake)*dt
    V_next = sqrt(2*E_next/C)
  Nguon diode ly tuong 48 V chi CAP, khong hut nang luong. Neu E_next thap
  hon E48, nguon cap phan thieu. Chopper ON >=50.5 V, OFF <=49 V, R=22 ohm:
    Pbrake = V^2/R khi ON. Energy bookkeeping theo J, khong cong truc tiep V.
  DCLink.step(ac_power_w,dt,brake_available=True) luu bus va ba dong nang
  luong: source_energy_j, inverter_energy_j (co dau), brake_energy_j.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh nang luong tra ve can de bus 48 -> 54 V. Thu P_ac=-50 W trong
  200 ms voi/co mat braking resistor. Vi sao nguon 48 V khong kep bus khi ham?

BUOC 3 - PHONG VE
  Nguon khong gioi han cong suat, khong co ESR, supply impedance hay switching
  chopper ripple; Pbrake duoc giu trong mot dt. Chua dinh co resistor that:
  can xem peak power, duty, thermal limits va hardware overvoltage rieng.
  brake_available=False mo phong mach brake bi hong, khong tu bao loi o day.
  Gioi han dt<=1 ms; E balance chinh xac cho phep cap nhat roi rac nay.
  CPU/RAM O(1), luu nang luong tich luy thay vi log day mau.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, doi chieu nang luong va bus; commit/push BU.5.
  Nguon: https://www.ti.com/download/trng/docs/c2000/TI_MotorControlCompendium_2010.pdf
"""

import math


class DCLink:
    def __init__(self, capacitance_f: float = 0.002, source_v: float = 48,
                 brake_ohm: float = 22) -> None:
        if not all(math.isfinite(v) and v > 0 for v in (capacitance_f,source_v,brake_ohm)):
            raise ValueError("C, source V, brake R phai huu han va duong")
        if source_v >= 49:
            raise ValueError("Nguon phai duoi nguong OFF 49 V cua bai hoc")
        self.capacitance_f, self.source_v, self.brake_ohm = capacitance_f,source_v,brake_ohm
        self.voltage = source_v
        self.chopper_on = False
        self.source_energy_j = self.inverter_energy_j = self.brake_energy_j = 0.0

    @property
    def energy_j(self) -> float:
        return 0.5*self.capacitance_f*self.voltage**2

    def step(self, ac_power_w: float, dt: float, brake_available: bool = True) -> float:
        if not math.isfinite(ac_power_w) or not math.isfinite(dt) or not 0 < dt <= 0.001:
            raise ValueError("DC-link power/dt khong hop le")
        on = self.chopper_on
        if self.voltage >= 50.5:
            on = True
        elif self.voltage <= 49:
            on = False
        brake_power = self.voltage**2/self.brake_ohm if on and brake_available else 0.0
        floor = 0.5*self.capacitance_f*self.source_v**2
        candidate = self.energy_j-(ac_power_w+brake_power)*dt
        supplied = max(0.0,floor-candidate)
        energy = candidate+supplied
        if not math.isfinite(energy) or energy <= 0:
            raise ValueError("DC-link energy tran")
        voltage = math.sqrt(2*energy/self.capacitance_f)
        self.chopper_on, self.voltage = on,voltage
        self.source_energy_j += supplied
        self.inverter_energy_j += ac_power_w*dt
        self.brake_energy_j += brake_power*dt
        return voltage


def demo() -> None:
    good, failed = DCLink(),DCLink()
    for _ in range(4000):
        good.step(-50,50e-6)
        failed.step(-50,50e-6,brake_available=False)
    assert good.voltage < 51 and failed.voltage > 100
    print(f"BU.5: -50 W x 0.2 s, bus good={good.voltage:.6f} V, "
          f"brake failed={failed.voltage:.6f} V, resistor energy={good.brake_energy_j:.6f} J")


if __name__ == "__main__":
    demo()
