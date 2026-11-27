"""EE MENTORSHIP - BAI 250 - BW.3: BIQUAD NOTCH IN TORQUE PATH.

BUOC 1 - HOP CONG CU
  Theo RBJ notch: w0=2*pi*f0/fs, alpha=sin(w0)/(2*Q).
  b=(1,-2*cos(w0),1); a=(1+alpha,-2*cos(w0),1-alpha).
  Chia tat ca he so cho a0; y=b0*x+b1*x1+b2*x2-a1*y1-a2*y2.
  Notch(f0,fs=4000,q=2).push(x) xu ly tung torque sample; gain(f) tinh
  |H(exp(j*2*pi*f/fs))|. DC gain=1, null tai f0; Q lon -> notch hep.

BUOC 2 - BAI TOAN TU LAM
  Dung fn nhan dang BW.2; so sinusoid dung f0 va f0*1.2, DC command.
  Tai sao dat sai notch frequency co the khong giam duoc resonance?

BUOC 3 - PHONG VE
  IIR co phase lag/transient; notch trong loop khong tu dam bao stability.
  Fixed fs va f0: khong adaptive auto-tuning. Chua co quantization/fixed-point,
  overflow register hay bumpless state reset. Reject nonfinite truoc mutate.
  CPU/RAM O(1), chi 4 state delays.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test response; commit/push BW.3.
  Nguon cong thuc: https://www.w3.org/TR/audio-eq-cookbook/
"""

import cmath
import math


class Notch:
    def __init__(self,f0: float,fs: float=4000,q: float=2):
        if not all(math.isfinite(v) for v in (f0,fs,q)) or not 0<f0<fs/2 or q<=0:
            raise ValueError("Notch can 0<f0<fs/2, Q>0")
        self.fs=fs
        w=math.tau*f0/fs
        alpha=math.sin(w)/(2*q)
        a0=1+alpha
        self.b0,self.b1,self.b2=1/a0,-2*math.cos(w)/a0,1/a0
        self.a1,self.a2=-2*math.cos(w)/a0,(1-alpha)/a0
        self.x1=self.x2=self.y1=self.y2=0.0

    def push(self,x: float) -> float:
        if not math.isfinite(x):
            raise ValueError("Filter input phai huu han")
        y=self.b0*x+self.b1*self.x1+self.b2*self.x2-self.a1*self.y1-self.a2*self.y2
        if not math.isfinite(y):
            raise ValueError("Filter overflow")
        self.x2,self.x1,self.y2,self.y1=self.x1,x,self.y1,y
        return y

    def gain(self,frequency: float) -> float:
        if not math.isfinite(frequency) or not 0<=frequency<=self.fs/2:
            raise ValueError("Frequency ngoai [0,Nyquist]")
        z=cmath.exp(-1j*math.tau*frequency/self.fs)
        return abs((self.b0+self.b1*z+self.b2*z*z)/(1+self.a1*z+self.a2*z*z))


if __name__=="__main__":
    n=Notch(11.25)
    print(f"BW.3: DC gain={n.gain(0):.8f}, notch gain={n.gain(11.25):.3e}")
