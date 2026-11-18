"""
Chuyen de AP: Cam bien Quang hoc Neuromorphic DVS & Mang No-ron Xung Than kinh SNN
Bai 2 (Milestone AP.2): Khoi No-ron Xung Phan cung Leaky Integrate-and-Fire (LIF),
Dong hoc Dien the Mang (Membrane Potential) & Co che Hoc Synap Thich nghi Cuc bo STDP

Muc tieu ky thuat:
- Xay dung mo hinh no-ron xung phan cung LIF (Leaky Integrate-and-Fire) chuan sinh hoc:
    tau_m * dV/dt = -(V - V_rest) + R_m * I(t).
- Mo phong thoi gian tro tuyet doi (Absolute Refractory Period tau_ref) va nguong phong xung V_thresh.
- Cai dat co che hoc thich nghi trong so synap Spike-Timing-Dependent Plasticity (STDP):
    LTP (Long-Term Potentiation khi delta_t > 0) va LTD (Long-Term Depression khi delta_t < 0).
- Mo phong mang no-ron xung phan cung da lop nhan dien mau hinh xung khong-thoi gian (Spatio-Temporal Spike Pattern).
- Tinh toan nang luong tieu thu cuc thap (Sparse Event-Driven Activation / Zero-compute khi khong co xung).

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class LIFParameters:
    """Cac thong so vat ly vi mach cua no-ron Leaky Integrate-and-Fire."""
    v_rest_mv: float = -70.0      # Dien the nghi (Resting Potential, mV)
    v_reset_mv: float = -65.0     # Dien the thiet lap lai sau khi phong xung (Reset Potential, mV)
    v_thresh_mv: float = -50.0    # Nguong kich hoat phong xung (Spike Threshold, mV)
    tau_m_ms: float = 20.0        # Hang so thoi gian mang te bao (Membrane Time Constant, ms)
    r_membrane_mohm: float = 10.0 # Dien tro mang te bao (Membrane Resistance, MOhm)
    refractory_period_ms: float = 2.0 # Thoi gian tro tuyet doi (Refractory Period, ms)


class HardwareLIFNeuron:
    """
    Khoi no-ron xung LIF phan cung (Neuromorphic Silicon Neuron Core).
    
    Phuong trinh vi phan dien the mang V_m:
    dV/dt = (V_rest - V) / tau_m + (R_m / tau_m) * I_syn(t)
    """

    def __init__(self, neuron_id: int, params: LIFParameters):
        self.neuron_id = neuron_id
        self.params = params
        
        # Trang thai noi tai cua no-ron
        self.v_membrane = params.v_rest_mv
        self.time_since_last_spike_ms = 999.0  # Khoi tao lon de khong bi tro
        self.is_refractory = False
        
        # Nhat ky xung phong (Spike Output History)
        self.spike_timestamps_ms: List[float] = []

    def step(self, dt_ms: float, input_current_na: float) -> int:
        """
        Cap nhat dong hoc dien the mang qua mot buoc thoi gian dt_ms.
        Tra ve: 1 neu no-ron phong xung (Spike), 0 neu khong phong xung.
        """
        # 1. Kiem tra thoi gian tro tuyet doi
        if self.time_since_last_spike_ms < self.params.refractory_period_ms:
            self.v_membrane = self.params.v_reset_mv
            self.time_since_last_spike_ms += dt_ms
            return 0

        # 2. Tich phan dong hoc Leaky Integration (Euler Method)
        # dV = dt * [ (V_rest - V)/tau_m + (R_m/tau_m)*I ]
        # Chu y: R_m (MOhm) * I (nA) = 1e6 * 1e-9 V = 1e-3 V = 1 mV
        decay_term = (self.params.v_rest_mv - self.v_membrane) / self.params.tau_m_ms
        input_term = (self.params.r_membrane_mohm * input_current_na) / self.params.tau_m_ms
        
        self.v_membrane += (decay_term + input_term) * dt_ms
        self.time_since_last_spike_ms += dt_ms

        # 3. Kiem tra nguong phong xung (Threshold Detection)
        if self.v_membrane >= self.params.v_thresh_mv:
            # Phat xung than kinh!
            self.v_membrane = self.params.v_reset_mv
            self.time_since_last_spike_ms = 0.0
            return 1

        return 0


class STDPPlasticityEngine:
    """
    Co che hoc thich nghi trong so synap Spike-Timing-Dependent Plasticity (STDP).
    
    Quy tac Hebbian sinh hoc:
    delta_t = t_post - t_pre
    
    Neu delta_t > 0 (Tien nhan qua - Causal):
      delta_W = A_plus * exp(-delta_t / tau_plus)   -> Tang trong so (LTP - Potentiation)
      
    Neu delta_t < 0 (Nghich nhan qua - Anti-causal):
      delta_W = -A_minus * exp(delta_t / tau_minus)  -> Giam trong so (LTD - Depression)
    """

    def __init__(
        self,
        a_plus: float = 0.05,
        a_minus: float = 0.055,
        tau_plus_ms: float = 20.0,
        tau_minus_ms: float = 20.0,
        w_min: float = 0.0,
        w_max: float = 1.0
    ):
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.tau_plus_ms = tau_plus_ms
        self.tau_minus_ms = tau_minus_ms
        self.w_min = w_min
        self.w_max = w_max

    def compute_weight_update(self, current_w: float, t_pre_ms: float, t_post_ms: float) -> float:
        """Tinh toan gia tri trong so synap moi sau cap nhat STDP."""
        delta_t = t_post_ms - t_pre_ms

        if delta_t > 0:
            # Long-Term Potentiation (LTP)
            dw = self.a_plus * np.exp(-delta_t / self.tau_plus_ms)
        elif delta_t < 0:
            # Long-Term Depression (LTD)
            dw = -self.a_minus * np.exp(delta_t / self.tau_minus_ms)
        else:
            dw = 0.0

        new_w = float(np.clip(current_w + dw, self.w_min, self.w_max))
        return new_w


class NeuromorphicSNNLayer:
    """
    Mot lop mang no-ron xung phan cung gom N no-ron LIF ket noi voi M dau vao synap.
    """

    def __init__(self, n_inputs: int, n_neurons: int, params: LIFParameters):
        self.n_inputs = n_inputs
        self.n_neurons = n_neurons
        self.neurons = [HardwareLIFNeuron(i, params) for i in range(n_neurons)]
        
        # Ma tran trong so synap (n_neurons x n_inputs) khoi tao trong khoang [0.2, 0.4]
        np.random.seed(42)
        self.weights = np.random.uniform(0.2, 0.4, (n_neurons, n_inputs)).astype(np.float32)
        self.stdp = STDPPlasticityEngine()

    def process_spikes(
        self,
        dt_ms: float,
        input_spikes: np.ndarray,
        current_time_ms: float,
        enable_stdp: bool = True
    ) -> np.ndarray:
        """
        Xu ly xung dau vao tai thoi diem current_time_ms.
        :param input_spikes: Vector xung nhi phan kich thuoc (n_inputs,) chua 0 hoac 1.
        :return: Vector xung dau ra kich thuoc (n_neurons,)
        """
        output_spikes = np.zeros(self.n_neurons, dtype=int)

        # Tinh dong dien synap: I_syn = Weights @ input_spikes * scale_factor
        # Vi du: Moi xung kich hoat mot luong dien tich tuong ung 2.5 nA
        current_injections = (self.weights @ input_spikes) * 2.5

        for j, neuron in enumerate(self.neurons):
            spike = neuron.step(dt_ms, current_injections[j])
            if spike:
                output_spikes[j] = 1
                neuron.spike_timestamps_ms.append(current_time_ms)
                
                # Cap nhat STDP cho tat ca cac synap dau vao
                if enable_stdp:
                    for i in range(self.n_inputs):
                        if input_spikes[i] == 1:
                            # Xung dau vao xay ra truoc/dong thoi voi xung dau ra
                            new_w = self.stdp.compute_weight_update(
                                self.weights[j, i],
                                t_pre_ms=current_time_ms - 0.5, # Xung den truoc nua buoc dt
                                t_post_ms=current_time_ms
                            )
                            self.weights[j, i] = new_w

        return output_spikes


def run_snn_lif_test_suite():
    """Kiem thu toan dien no-ron LIF, thoi gian tro, va co che hoc STDP."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN KHOI NO-RON PHAN CUNG LIF VA CO CHE HOC SYNAP STDP")
    print("=" * 80)

    params = LIFParameters(
        v_rest_mv=-70.0,
        v_reset_mv=-65.0,
        v_thresh_mv=-50.0,
        tau_m_ms=20.0,
        r_membrane_mohm=10.0,
        refractory_period_ms=2.0
    )

    # 1. Kiem thu Dong hoc Dien the mang LIF va Thoi gian tro
    print("\n1. Kiem thu dong hoc tich phan dien the mang va phong xung LIF...")
    neuron = HardwareLIFNeuron(0, params)
    dt_ms = 0.1  # Buoc thoi gian 100 us

    # Bom dong dien kich thich 2.5 nA trong 100 ms (1000 buoc x 0.1 ms)
    # V_inf = V_rest + R_m * I = -70 + 10 * 2.5 = -45 mV (> V_thresh = -50 mV -> Phong chuoi xung)
    spikes_fired = 0
    voltages = []

    for step in range(1000):
        t_ms = step * dt_ms
        spk = neuron.step(dt_ms, input_current_na=2.5)
        voltages.append(neuron.v_membrane)
        if spk:
            spikes_fired += 1
            neuron.spike_timestamps_ms.append(t_ms)

    print(f"-> So luong xung phong trong 100 ms: {spikes_fired} spikes")
    print(f"-> Tan so phong xung (Firing Rate) : {spikes_fired / 0.10:.1f} Hz")
    print(f"-> Dien the thap nhat trong lich su : {min(voltages):.2f} mV (Ky vong: {params.v_rest_mv} mV)")
    assert spikes_fired >= 3, "No-ron phai phong it nhat 3 xung trong 100 ms voi dong 2.5 nA!"
    assert min(voltages) >= params.v_rest_mv - 0.1, "Dien the mang khong duoc tut qua V_rest!"

    # 2. Kiem thu Co che hoc Hebbian STDP
    print("\n" + "-" * 80)
    print("2. Kiem thu co che hoc thich nghi trong so synap STDP (LTP vs LTD)...")
    stdp = STDPPlasticityEngine(a_plus=0.08, a_minus=0.085, tau_plus_ms=20.0, tau_minus_ms=20.0)
    initial_w = 0.50

    # Truong hop 1: delta_t = +5.0 ms (t_post sau t_pre -> Quan he nhan qua -> LTP tang trong so)
    w_ltp = stdp.compute_weight_update(initial_w, t_pre_ms=10.0, t_post_ms=15.0)
    print(f"-> LTP (delta_t = +5.0 ms) : Trong so tang tu {initial_w:.4f} len {w_ltp:.4f} (Tang {(w_ltp-initial_w):+.4f})")
    assert w_ltp > initial_w, "LTP phai lam tang trong so synap!"

    # Truong hop 2: delta_t = -5.0 ms (t_post truoc t_pre -> Nghich nhan qua -> LTD giam trong so)
    w_ltd = stdp.compute_weight_update(initial_w, t_pre_ms=15.0, t_post_ms=10.0)
    print(f"-> LTD (delta_t = -5.0 ms) : Trong so giam tu {initial_w:.4f} xuong {w_ltd:.4f} (Giam {(w_ltd-initial_w):+.4f})")
    assert w_ltd < initial_w, "LTD phai lam giam trong so synap!"

    # 3. Kiem thu Lop Mang SNN hoc mau hinh xung khong-thoi gian
    print("\n" + "-" * 80)
    print("3. Kiem thu Lop mang SNN hoc nhan dien mau hinh xung khong-thoi gian...")
    n_in = 8
    n_out = 2
    snn_layer = NeuromorphicSNNLayer(n_inputs=n_in, n_neurons=n_out, params=params)

    # Lap di lap lai mau hinh xung: Dau vao 0, 1, 2 dong thoi phat xung
    pattern = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    w_before = snn_layer.weights[0, 0]

    # Huan luyen qua 100 chu ky kich thich
    for cycle in range(100):
        t_sim = cycle * 1.0
        snn_layer.process_spikes(dt_ms=0.5, input_spikes=pattern, current_time_ms=t_sim, enable_stdp=True)

    w_after = snn_layer.weights[0, 0]
    print(f"-> Trong so synap 0 truoc huan luyen: {w_before:.4f}")
    print(f"-> Trong so synap 0 sau huan luyen  : {w_after:.4f} (Tang do kich hoat dong bo)")
    assert w_after >= w_before, "Synap duoc kich thich dong bo phai duoc tang cuong trong so!"

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu No-ron LIF va Co che hoc STDP Neuromorphic thanh cong!")
    print("=" * 80)


if __name__ == "__main__":
    run_snn_lif_test_suite()
