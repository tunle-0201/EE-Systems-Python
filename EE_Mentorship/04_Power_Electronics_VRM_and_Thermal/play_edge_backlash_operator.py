"""EE MENTORSHIP - BAI 254 - BX.2: BACKLASH PLAY OPERATOR.

BUOC 1 - HOP CONG CU
  Giu output y trong khoang [input-h,input+h], h=0.01 rad la NUA do ro:
    y_new=max(input-h,min(input+h,y_old))
  Dang tang: y=input-h khi an rang. Dao chieu: y giu nguyen cho toi khi
  input di nguoc 2*h, roi y=input+h. Backlash.push(input) co state y,
  khac deadzone tinh max(0,input-h). Dau vao/ra la rad, khong phai torque.

BUOC 2 - BAI TOAN TU LAM
  Tu lap bang input 0 -> 0.1 -> 0.095 -> 0.085 -> 0.07. Tim doan load
  khong doi va chieu an rang. Thu input am, shift origin va h=0.

BUOC 3 - PHONG VE
  Day la SIGNAL MODEL cua output hysteresis, KHONG la contact/gear dynamics.
  Khong truyen reaction torque, luu elastic energy hay mo phong impact.
  Capstone ghep sau motor de nghien cuu tracking, khong dung de tinh tooth
  forces hay inertia load khi an rang. CPU/RAM O(1), mot state output.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test reversal memory; commit/push BX.2.
  Nguon: https://www.mathworks.com/help/simulink/slref/backlash.html
"""

import math


class Backlash:
    def __init__(self,half_gap: float=0.01,initial_output: float=0.0):
        if not math.isfinite(half_gap) or half_gap<0 or not math.isfinite(initial_output):
            raise ValueError("Backlash gap/output khong hop le")
        self.half_gap,self.output=half_gap,initial_output

    def push(self,position: float) -> float:
        if not math.isfinite(position):
            raise ValueError("Backlash position phai huu han")
        self.output=max(position-self.half_gap,min(position+self.half_gap,self.output))
        return self.output


if __name__=="__main__":
    play=Backlash()
    values=[play.push(x) for x in (0,0.1,0.095,0.085,0.07)]
    print(f"BX.2: load outputs={values}; full reversal gap=0.02 rad")
