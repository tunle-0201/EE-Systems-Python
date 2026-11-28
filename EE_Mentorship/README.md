# 📁 EE Mentorship — Danh Mục Phân Loại 10 Thư Mục Chuyên Ngành

Tài liệu lộ trình chi tiết từng bài (`Bài 1 -> Bài 264`, **272 bài học & 68 chuyên đề**): xem [MISSING_LESSONS_ROADMAP.md](MISSING_LESSONS_ROADMAP.md).

| Thư mục | Phạm vi Kỹ thuật (Engineering Domain) | Các phân hệ tiêu biểu (Prefixes) | Số file |
| :--- | :--- | :--- | :---: |
| [`01_Core_Systems_RTOS_and_Firmware/`](01_Core_Systems_RTOS_and_Firmware/) | Lập trình hệ thống thuần Python, OOP phần cứng, FreeRTOS, DMA/SPI/NVIC, Dual-Bank Bootloader OTA, Bộ nhớ nhúng & DSA | `milestone_*`, `game_*`, `smart_*`, `rtos_*`, `dma_*`, `boot_*`, `dsa_*`, `mem_edge_*allocator/pool*` | 41 |
| [`02_AI_Accelerators_ML_and_Computer_Vision/`](02_AI_Accelerators_ML_and_Computer_Vision/) | Machine Learning, Deep Learning Autograd, OpenCV, NPU Systolic Array, TPU INT4/INT8 & Thị giác sự kiện Neuromorphic DVS/SNN | `ml_*`, `cv_*`, `npu_*`, `tpu_*`, `hw_*`, `dvs_*`, `snn_*`, `neuromorphic_*` | 61 |
| [`03_Chip_Architecture_Memory_and_Interconnects/`](03_Chip_Architecture_Memory_and_Interconnects/) | Kiến trúc SoC 2D NoC MESI & UCIe, PCIe Gen4/Gen6 PAM4 Flit, CXL 3.0, SerDes 64G DFE, ADPLL, LPDDR5X/HBM3e, DFT JTAG Shmoo & HFT | `noc_*`, `pcie_*`, `pcie6_*`, `cxl_*`, `serdes_*`, `adpll_*`, `lpddr5_*`, `mem_edge_lpddr5x*`, `dft_*`, `hft_*` | 36 |
| [`04_Power_Electronics_VRM_and_Thermal/`](04_Power_Electronics_VRM_and_Thermal/) | Ma sát/backlash, Trục đàn hồi/cộng hưởng, Servo vị trí/homing, Servo PMSM d–q & DC bus tái sinh, Đo dòng shunt AFE & cửa sổ PWM, Nguồn đa pha 1000A VRM & AVP, PDN Integrity & DVFS, USB-PD 3.1 EPR 240W & 4-Switch Buck-Boost, SiC/GaN 800V Inverter & MPPT, 800V EV BMS, FOC/MTPA & Quản lý nhiệt RC | `play_*`, `flex_*`, `axis_*`, `servo_*`, `current_*`, `vrm_*`, `pdn_*`, `usbpd_*`, `power_*`, `bms_*`, `foc_*`, `thermal_*` | 61 |
| [`05_RF_Wireless_Radar_and_Satellite_Comms/`](05_RF_Wireless_Radar_and_Satellite_Comms/) | Viễn thông vô tuyến SDR/Smith/TDR/SAR, RF PA CFR/DPD/Envelope Tracking, UWB IEEE 802.15.4z, GNSS L1/L5 & RTK Centimet, Radar & Satcom | `rf_*`, `rfpa_*`, `uwb_*`, `gnss_*`, `radar_*`, `track_*`, `satcom_*` | 36 |
| [`06_Optical_Photonics_LiDAR_and_Camera_ISP/`](06_Optical_Photonics_LiDAR_and_Camera_ISP/) | Silicon Photonics MZM/MRR/CPO, Quang không gian Starlink FSO, LiDAR OPA/FMCW/SPAD, Cảm biến CMOS 4T-PPD & ISP 5-Line, MIPI CSI-2 | `siph_*`, `fso_*`, `optics_*`, `lidar_*`, `isp_*`, `mipi_*` | 28 |
| [`07_Mixed_Signal_Audio_and_Precision_Actuators/`](07_Mixed_Signal_Audio_and_Precision_Actuators/) | Pt100/RTD 3-wire & tự nung, Strain Gauge/Load Cell, ADC ratiometric & hiệu chuẩn nhiệt, ADC/DAC Tín hiệu hỗn hợp, Cảm ứng điện dung PCAP I/Q & Water Rejection, Âm thanh I2S/PDM-CIC/Beamforming, DSP FIR/FFT/ANC, EMC, Haptics LRA Back-EMF & OIS VCM | `rtd_*`, `strain_*`, `mixed_*`, `touch_*`, `audio_*`, `dsp_*`, `emc_*`, `haptic_*` | 36 |
| [`08_Robotics_Autonomous_Driving_and_Control/`](08_Robotics_Autonomous_Driving_and_Control/) | Điều khiển lực tiếp xúc/BE admittance, Robot Ackermann/Admittance/DOB, Encoder A/B/Z & Sin/Cos, BiSS-C SCD CRC-6, EtherCAT DC, MPC Starship/FSD, Sensor Fusion, Mapping, ISO 26262 ASIL-D, CAN-FD & TSN | `contact_*`, `robotics_*`, `encoder_*`, `ethercat_*`, `mpc_*`, `fusion_*`, `grid_*`, `safety_*`, `can_*`, `tsn_*` | 54 |
| [`09_Aerospace_Spacecraft_and_Avionics/`](09_Aerospace_Spacecraft_and_Avionics/) | Điều khiển tư thế vệ tinh CubeSat ADCS, Định vị quán tính 6-DOF INS/ES-EKF, MIL-STD-1553B & ARINC 429, SpaceWire/SpaceFibre, HIL | `adcs_*`, `ins_*`, `avionics_*`, `spacewire_*`, `spacefibre_*`, `hil_*` | 20 |
| [`10_Hardware_Security_PQC_and_Fault_Tolerance/`](10_Hardware_Security_PQC_and_Fault_Tolerance/) | Mật mã hậu lượng tử PQC FIPS 203 ML-KEM/NTT/DPA, Bảo mật AES-GCM/ECDSA/SHA3 & Máy tính bay chống bức xạ TMR Byzantine | `pqc_*`, `crypto_*`, `tmr_*` | 16 |
| [`drone_system/`](drone_system/) | Gói phần mềm điều khiển Drone hoàn chỉnh (Module F & Kiem thu Pytest) | `engine.py`, `protocol.py`, `flight_controller_capstone.py` | 7 |

> **Lưu ý khi chạy các bài Capstone có `import` chéo:** Tất cả các module phụ thuộc nhau đã được xếp chung trong cùng một thư mục chuyên ngành, nên bạn chạy trực tiếp bằng `python EE_Mentorship/<Thu_muc>/<ten_file>.py` là hoạt động ngay 100%!

## Chuyên đề BQ — Encoder & phản hồi góc khớp robot (20/11/2026)

Học theo thứ tự hộp công cụ, bài tập tự làm, phân tích lỗi và demo trong từng file:

1. [Bài 220 — A/B/Z quadrature x4](08_Robotics_Autonomous_Driving_and_Control/encoder_edge_quadrature_abz.py): đếm đa vòng, đảo chiều, homing và phát hiện mất cạnh.
2. [Bài 221 — Hiệu chuẩn sin/cos](08_Robotics_Autonomous_Driving_and_Control/encoder_edge_sincos_calibration.py): bù offset/gain, `atan2`, kiểm tra biên độ và unwrap qua 360 deg.
3. [Bài 222 — BiSS-C SCD CRC-6](08_Robotics_Autonomous_Driving_and_Control/encoder_edge_bissc_crc6.py): profile dữ liệu 18-bit + status + CRC đảo, kiểm tra lỗi từng bit. Mô phỏng kênh SCD, chưa triển khai full BiSS master.
4. [Bài 223 — Robot joint feedback capstone](08_Robotics_Autonomous_Driving_and_Control/encoder_edge_robot_joint_feedback_capstone.py): so sánh hai kênh tại 1 kHz, chặn mẫu lỗi, watchdog 5 ms và chốt lỗi encoder kẹt/mất cạnh.

Chạy capstone từ thư mục gốc repo:

```bash
python EE_Mentorship/08_Robotics_Autonomous_Driving_and_Control/encoder_edge_robot_joint_feedback_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BQ](../tests/test_encoder_bq.py) dùng thư viện chuẩn Python; kiểm tra CRC bằng phép chia đa thức độc lập, đảo chiều/qua vòng và các tình huống lỗi. Các kết quả là mô phỏng; cổng torque Boolean chưa phải cơ chế STO phần cứng.

## Chuyên đề BR — Strain gauge & cảm biến lực kẹp robot (21/11/2026)

Mỗi bài bắt đầu bằng hộp công cụ và phép tính, sau đó là bài tập tự làm, phân tích lỗi và demo chạy được:

1. [Bài 224 — Cầu Wheatstone full-bridge](07_Mixed_Signal_Audio_and_Precision_Actuators/strain_edge_wheatstone_bridge.py): gauge factor, điện trở 350 ohm, strain và độ nhạy 2 mV/V ở 100 N.
2. [Bài 225 — ADC ratiometric & bộ lọc 50/60 Hz](07_Mixed_Signal_Audio_and_Precision_Actuators/strain_edge_ratiometric_adc_filter.py): lượng tử hóa bipolar 24-bit lý tưởng, PGA x128, hai FIR moving average và trễ nhóm 17.5 ms.
3. [Bài 226 — Hiệu chuẩn zero/span theo nhiệt](07_Mixed_Signal_Audio_and_Precision_Actuators/strain_edge_temperature_calibration.py): tải chuẩn 0/80 N ở 20/50 degC, nội suy zero và span riêng, kiểm tra tải chưa dùng để fit.
4. [Bài 227 — Robot gripper force capstone](07_Mixed_Signal_Audio_and_Precision_Actuators/strain_edge_robot_gripper_force_capstone.py): pipeline RAW 1200 Hz -> kết quả 100 Hz, nhánh kiểm tra quá tải trước FIR, phát hiện bão hòa ADC, diagnostic cảm biến và watchdog 5 ms.

```bash
python EE_Mentorship/07_Mixed_Signal_Audio_and_Precision_Actuators/strain_edge_robot_gripper_force_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BR](../tests/test_strain_br.py) có **25 tests**, cùng 23 tests BQ tạo thành **48 tests**. Mô hình lý tưởng chỉ minh họa vật lý và xử lý tín hiệu; chưa mô phỏng nhiễu thực của ADC, cơ cấu kẹp hay mạch STO. Tài liệu gốc: [TI Bridge Measurements](https://www.ti.com/lit/an/sbaa532a/sbaa532a.pdf), [NI Full-Bridge Type I](https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/full1.html).

## Chuyên đề BS — Pt100/RTD & giám sát nhiệt cuộn dây robot (22/11/2026)

Mỗi bài có hộp công cụ và phép tính trước code, bài tập tự làm, phân tích biên và demo:

1. [Bài 228 — Pt100 Callendar–Van Dusen](07_Mixed_Signal_Audio_and_Precision_Actuators/rtd_edge_pt100_callendar_van_dusen.py): đặc tính danh định -200..850 degC, số hạng bổ sung khi nhiệt độ âm và nghịch đảo bằng chia đôi.
2. [Bài 229 — RTD 3-wire ratiometric](07_Mixed_Signal_Audio_and_Precision_Actuators/rtd_edge_three_wire_ratiometric.py): mô hình MUX hai pha, bù điện trở dây cân bằng, sai số dây lệch và tham chiếu điện trở.
3. [Bài 230 — Tự nung & dòng kích xung](07_Mixed_Signal_Audio_and_Precision_Actuators/rtd_edge_self_heating_pulsed_excitation.py): mô hình RC nhiệt, công suất I^2*R, duty 10% và sai số cuối khoảng ON.
4. [Bài 231 — Robot winding thermal capstone](07_Mixed_Signal_Audio_and_Precision_Actuators/rtd_edge_robot_winding_thermal_capstone.py): đo 10 Hz, hysteresis giảm dòng 90/85 degC, chốt quá nhiệt 120 degC, timestamp lúc đo, phát hiện replay và watchdog 250 ms.

```bash
python EE_Mentorship/07_Mixed_Signal_Audio_and_Precision_Actuators/rtd_edge_robot_winding_thermal_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BS](../tests/test_rtd_bs.py) bổ sung **28 tests**, tổng **76 tests BQ+BR+BS**. Sai số số học/ADC trong demo không đại diện độ chính xác Pt100 thực; mô hình chưa có diagnostic đứt dây phần cứng, FOC, hotspot cuộn dây hay STO. Nguồn: [TI RTD Measurements](https://www.ti.com/lit/an/sbaa275a/sbaa275a.pdf), [ADI CN-0383](https://www.analog.com/media/en/reference-design-documentation/reference-designs/cn0383.pdf).

## Chuyên đề BT — Shunt current AFE & vòng dòng rotor đứng yên (23/11/2026)

Mỗi bài đi từ hộp công cụ và công thức đến bài tập tự làm, phân tích biên rồi demo:

1. [Bài 232 — Shunt AFE & hiệu chuẩn](04_Power_Electronics_VRM_and_Thermal/current_edge_shunt_afe_calibration.py): shunt 1 milliohm, khuếch đại x50, ADC 12-bit bipolar qua bias giữa thang, hiệu chuẩn gain/offset và bù TCR.
2. [Bài 233 — Cửa sổ lấy mẫu PWM](04_Power_Electronics_VRM_and_Thermal/current_edge_pwm_sampling_windows.py): tính trigger cho hai shunt low-side, xét deadtime, amplifier settling và aperture ADC tại 20 kHz.
3. [Bài 234 — Dựng dòng pha thứ ba](04_Power_Electronics_VRM_and_Thermal/current_edge_two_shunt_reconstruction.py): `ic=-ia-ib`, Clarke alpha/beta, kiểm tra cửa sổ/ADC. Tổng ba dòng bằng 0 sau phép dựng không phải phép kiểm tra sensor độc lập.
4. [Bài 235 — Current-loop capstone](04_Power_Electronics_VRM_and_Thermal/current_edge_motor_current_loop_capstone.py): PI có anti-windup trên plant RL hai trục, lệnh `0 -> 8 -> -5 A`, fault chốt khi sai cửa sổ, mất cycle hoặc quá dòng.

```bash
python EE_Mentorship/04_Power_Electronics_VRM_and_Thermal/current_edge_motor_current_loop_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BT](../tests/test_current_bt.py) bổ sung **24 tests**, tổng **100 tests BQ+BR+BS+BT**. Capstone dùng plant averaged khi rotor đứng yên, chưa có back-EMF, rotor motion, ripple, full PMSM FOC hay comparator bảo vệ phần cứng. Nguồn: [TI Current Sensing](https://www.ti.com/lit/an/slyt762/slyt762.pdf), [Microchip AN1299](https://ww1.microchip.com/downloads/en/AppNotes/01299A.pdf).

## Chuyên đề BU — Servo PMSM quay & năng lượng tái sinh (24/11/2026)

Bộ mở rộng hôm nay gồm **5 bài nền tảng + 1 capstone**, mỗi bài có hộp công cụ, bài tập tự làm, tình huống biên và demo:

1. [Bài 236 — Plant PMSM d–q](04_Power_Electronics_VRM_and_Thermal/servo_edge_pmsm_dq_plant.py): phương trình điện–cơ, back-EMF, torque, pole pairs, tích phân RK4 và năng lượng lưu trữ.
2. [Bài 237 — Giới hạn vector điện áp](04_Power_Electronics_VRM_and_Thermal/servo_edge_voltage_circle_limiter.py): vòng tròn điện áp phụ thuộc bus, giữ hướng vector thay vì kẹp riêng từng trục.
3. [Bài 238 — Tốc độ từ encoder](04_Power_Electronics_VRM_and_Thermal/servo_edge_encoder_speed_estimator.py): mã góc 16-bit, wrap hai chiều, đạo hàm góc và LPF, kiểm tra giới hạn lấy mẫu.
4. [Bài 239 — PI tốc độ/dòng nhiều vòng](04_Power_Electronics_VRM_and_Thermal/servo_edge_cascaded_pi_controller.py): vòng tốc độ 1 kHz, dòng 20 kHz, feedforward và anti-windup sau giới hạn vector.
5. [Bài 240 — DC link tái sinh](04_Power_Electronics_VRM_and_Thermal/servo_edge_regenerative_dc_link.py): năng lượng tụ, nguồn chỉ cấp điện, chopper điện trở có hysteresis và tình huống brake hỏng.
6. [Bài 241 — Robot axis drive capstone](04_Power_Electronics_VRM_and_Thermal/servo_edge_robot_axis_drive_capstone.py): tăng tốc, đảo chiều, tải thay đổi, hãm tái sinh, giới hạn dòng và lỗi chốt.

```bash
python EE_Mentorship/04_Power_Electronics_VRM_and_Thermal/servo_edge_robot_axis_drive_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BU](../tests/test_servo_bu.py) có **27 tests mới**, tổng **127 tests BQ–BU**. Đây là mô hình averaged d–q với id/iq lý tưởng; chưa triển khai lấy mẫu abc/Park, gate PWM, sensorless observer, field weakening hay STO phần cứng. Nguồn: [NASA PMSM model](https://ntrs.nasa.gov/api/citations/20210025115/downloads/PMSM_v6.pdf), [TI Motor Control Compendium](https://www.ti.com/download/trng/docs/c2000/TI_MotorControlCompendium_2010.pdf).

## Chuyên đề BV — Servo vị trí, homing & quỹ đạo quintic (25/11/2026)

**5 bài nền tảng + 1 capstone**, tiếp nối plant và các vòng PI của BU. Mỗi bài có hộp công cụ, bài tập, phân tích biên và demo:

1. [Bài 242 — Quỹ đạo quintic](04_Power_Electronics_VRM_and_Thermal/axis_edge_quintic_motion_profile.py): rest-to-rest, đạo hàm giải tích và chọn thời gian để giữ giới hạn vận tốc/gia tốc/jerk.
2. [Bài 243 — Homing state machine](04_Power_Electronics_VRM_and_Thermal/axis_edge_homing_state_machine.py): seek, backoff, tiếp cận chậm, debounce, offset encoder, timeout và giới hạn hành trình raw.
3. [Bài 244 — Vòng vị trí](04_Power_Electronics_VRM_and_Thermal/axis_edge_position_velocity_cascade.py): P vị trí cộng velocity feedforward, tạo lệnh cho vòng tốc độ và clamp đơn vị rad/s.
4. [Bài 245 — Bù mô-men](04_Power_Electronics_VRM_and_Thermal/axis_edge_acceleration_feedforward.py): quán tính, ma sát nhớt, tải ước lượng và đổi torque sang dòng iq.
5. [Bài 246 — Motion supervisor](04_Power_Electronics_VRM_and_Thermal/axis_edge_motion_supervisor.py): homing bắt buộc, soft limits, following error kéo dài, thời gian settling và lỗi chốt.
6. [Bài 247 — Robot positioning capstone](04_Power_Electronics_VRM_and_Thermal/axis_edge_robot_positioning_capstone.py): home bằng fixture động học, rồi điều khiển PMSM tới `+0.6` và `-0.4 rad`; so sánh bù mô-men và thử kẹt trục lý tưởng.

```bash
python EE_Mentorship/04_Power_Electronics_VRM_and_Thermal/axis_edge_robot_positioning_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BV](../tests/test_axis_bv.py) bổ sung **22 tests**, tổng **149 tests BQ–BV**. Homing là fixture động học; plant PMSM chỉ chạy sau homing. Chưa có geartrain, contact mechanics, AFE/PWM, brake hoặc STO phần cứng. Nguồn: [Modern Robotics time scaling](https://modernrobotics.northwestern.edu/nu-gm-book-resource/9-1-and-9-2-point-to-point-trajectories-part-2-of-2/), [Beckhoff homing](https://download.beckhoff.com/download/document/automation/twincat3/TF5200_homing_en.pdf).

## Chuyên đề BW — Trục đàn hồi & cộng hưởng cơ học (26/11/2026)

**4 bài nền tảng + 1 capstone**, đi từ plant đến nhận dạng, lọc và feedback:

1. [Bài 248 — Plant hai quán tính](04_Power_Electronics_VRM_and_Thermal/flex_edge_two_inertia_plant.py): motor/load, trục lò xo–damper, RK4, tần số mode và năng lượng.
2. [Bài 249 — Nhận dạng ringdown](04_Power_Electronics_VRM_and_Thermal/flex_edge_ringdown_identification.py): trích đỉnh rung tắt dần để ước lượng tần số và damping ratio.
3. [Bài 250 — Bộ lọc notch](04_Power_Electronics_VRM_and_Thermal/flex_edge_notch_filter.py): biquad RBJ, gain DC, tần số notch, đáp ứng sai tần số và state của IIR.
4. [Bài 251 — Giảm rung hai encoder](04_Power_Electronics_VRM_and_Thermal/flex_edge_dual_encoder_damping.py): feedback vận tốc tương đối, clamp torque và guard chốt lỗi xoắn/cảm biến/cycle.
5. [Bài 252 — Flexible transmission capstone](04_Power_Electronics_VRM_and_Thermal/flex_edge_robot_transmission_capstone.py): so baseline với notch kết hợp relative damping và chèn lỗi offset encoder load.

```bash
python EE_Mentorship/04_Power_Electronics_VRM_and_Thermal/flex_edge_robot_transmission_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BW](../tests/test_flex_bw.py) bổ sung **17 tests**, tổng **166 tests BQ–BW**. Torque sinusoid tại mode cộng hưởng là tín hiệu chèn có chủ đích; so sánh thay đổi cả notch và relative damping. Chưa có PMSM, backlash, gear ratio, delay hay STO phần cứng. Nguồn: [W3C Audio EQ Cookbook](https://www.w3.org/TR/audio-eq-cookbook/), [Kollmorgen resonance tuning](https://www.kollmorgen.com/sites/default/files/AKD%20Tuning%20Guide.pdf).

## Chuyên đề BX — Ma sát, backlash & trục đảo chiều (27/11/2026)

**3 bài nền tảng + 1 capstone**, mỗi bài có hộp công cụ, bài tập tự làm, phân tích biên và demo:

1. [Bài 253 — Plant stick-slip](04_Power_Electronics_VRM_and_Thermal/play_edge_stick_slip_axis.py): static/Coulomb/viscous friction, nghiệm trượt giải tích và xử lý sự kiện dừng hoặc đổi chiều trong một bước thời gian.
2. [Bài 254 — Backlash play operator](04_Power_Electronics_VRM_and_Thermal/play_edge_backlash_operator.py): độ rơ có nhớ, giữ đầu ra khi đảo chiều và phân biệt với deadzone tĩnh.
3. [Bài 255 — Bù đảo chiều](04_Power_Electronics_VRM_and_Thermal/play_edge_reversal_compensator.py): offset bù backlash có giới hạn tốc độ, giữ hướng khi dừng và friction feedforward mượt.
4. [Bài 256 — Reversing-axis capstone](04_Power_Electronics_VRM_and_Thermal/play_edge_reversing_axis_capstone.py): theo quỹ đạo `0 -> +0.3 -> -0.2 rad`, so baseline/bù kết hợp và chèn lỗi encoder tải.

```bash
python EE_Mentorship/04_Power_Electronics_VRM_and_Thermal/play_edge_reversing_axis_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BX](../tests/test_play_bx.py) bổ sung **15 tests**, tổng **181 tests BQ–BX**. Backlash là mô hình tín hiệu massless, chưa có truyền mô-men phản lực, contact energy, gear tooth forces hay PMSM/STO. Bù kết hợp không đảm bảo sai số bằng 0 hoặc cải thiện trên mọi phần cứng. Nguồn: [MathWorks rotational friction](https://www.mathworks.com/help/simscape/ref/rotationalfriction.html), [MathWorks backlash](https://www.mathworks.com/help/simulink/slref/backlash.html), [Kollmorgen feedforward](https://webhelp.kollmorgen.com/essentials/English/Content/Tuning/Determining-FeedForwards.htm).

## Chuyên đề BY — Tiếp cận bề mặt & giữ lực tiếp xúc (28/11/2026)

**7 bài nền tảng + 1 capstone**, bổ sung phiên bản mô-đun có kiểm chứng rời rạc cho các bài admittance trước đây:

1. [Bài 257 — Unilateral wall](08_Robotics_Autonomous_Driving_and_Control/contact_edge_unilateral_wall.py): Kelvin–Voigt 1D, dấu reaction force, separation và năng lượng đàn hồi.
2. [Bài 258 — Cảm biến lực](08_Robotics_Autonomous_Driving_and_Control/contact_edge_force_sensor_calibration.py): ADC 16-bit, hai điểm hiệu chuẩn, clipping và timestamp lúc đo.
3. [Bài 259 — Contact FSM](08_Robotics_Autonomous_Driving_and_Control/contact_edge_contact_state_machine.py): approach/regulate, hai ngưỡng hysteresis, dwell khi chạm hoặc mất tiếp xúc.
4. [Bài 260 — PI lực ra vận tốc](08_Robotics_Autonomous_Driving_and_Control/contact_edge_force_pi_velocity.py): dấu feedback, velocity clamp, conditional anti-windup và bumpless reset.
5. [Bài 261 — Backward Euler admittance](08_Robotics_Autonomous_Driving_and_Control/contact_edge_backward_euler_admittance.py): giải đồng thời mass/damper/spring rời rạc, không clamp nội bộ.
6. [Bài 262 — Discrete energy observer](08_Robotics_Autonomous_Driving_and_Control/contact_edge_discrete_energy_observer.py): input work, storage change, damping vật lý và numerical dissipation của virtual BE subsystem.
7. [Bài 263 — Force supervisor](08_Robotics_Autonomous_Driving_and_Control/contact_edge_force_supervisor.py): tuổi mẫu, replay, timeout, ADC clip và ngưỡng force/travel/velocity.
8. [Bài 264 — Surface-force capstone](08_Robotics_Autonomous_Driving_and_Control/contact_edge_robot_surface_force_capstone.py): tiếp cận rồi giữ 10 N bằng PI hoặc admittance; đổi độ cứng và chèn frame cũ.

```bash
python EE_Mentorship/08_Robotics_Autonomous_Driving_and_Control/contact_edge_robot_surface_force_capstone.py
python -m unittest discover -s tests -v
```

[Bộ kiểm thử BY](../tests/test_contact_by.py) bổ sung **29 tests**, tổng **210 tests BQ–BY**. Actuator vận tốc lý tưởng, chưa có motor inertia/servo lag, 6D hybrid projection hay STO. Energy identity chỉ áp dụng virtual BE trước clamp, không là chứng nhận passivity của toàn robot. Nguồn: [Modern Robotics force control](https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-5-force-control/), [ROS 2 admittance](https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html).
