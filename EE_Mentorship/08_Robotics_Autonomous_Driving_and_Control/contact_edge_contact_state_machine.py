"""EE MENTORSHIP - BAI 259 - BY.3: APPROACH/REGULATE CONTACT FSM.

BUOC 1 - HOP CONG CU
  APPROACH khi chua cham, lenh toc do 0.005 m/s huong vao tuong.
  F>=1 N lien tuc 3 mau -> REGULATE. REGULATE chi ve APPROACH khi
  F<=0.3 N lien tuc 10 mau. Hai nguong khac nhau la hysteresis.
  ContactFSM.update(force) tra state; moi call la MOT sample 1 kHz trong
  capstone. Counter khong thay duoc kiem tra cadence/timestamp BY.7.

BUOC 2 - BAI TOAN TU LAM
  Chen luc 0.99/1.01 N xen ke, sau do 3 mau >1 N; thu contact loss 5 va
  10 mau. Tai sao threshold don khong dwell de gay chattering?

BUOC 3 - PHONG VE
  Day la chuyen mode theo thoi gian, khong la phep project hybrid force/
  motion theo cac truc trong ly thuyet 6D. Chua co collision classification.
  Khong tu dua ra motor command; capstone quyet dinh reset/bumpless transfer.
  CPU/RAM O(1), chi hai counters. Force am co the la noise sensor nhung
  gioi han force hop ly duoc kiem tra rieng o supervisor.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test thresholds/dwell; commit/push BY.3.
  Nguon: https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-6-hybrid-motion-force-control/
"""

import math


class ContactFSM:
    def __init__(self):
        self.state="APPROACH"
        self.on_samples=self.off_samples=0

    def update(self,force: float) -> str:
        if not math.isfinite(force):
            raise ValueError("Contact force phai huu han")
        if self.state=="APPROACH":
            self.on_samples=self.on_samples+1 if force>=1.0 else 0
            if self.on_samples>=3:
                self.state="REGULATE"
                self.off_samples=0
        else:
            self.off_samples=self.off_samples+1 if force<=0.3 else 0
            if self.off_samples>=10:
                self.state="APPROACH"
                self.on_samples=0
        return self.state


if __name__=="__main__":
    state=ContactFSM()
    for _ in range(3):
        state.update(1.1)
    print(f"BY.3: three consecutive contact samples -> {state.state}")
