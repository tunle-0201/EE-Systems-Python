# 📁 EE Mentorship — Danh Mục Phân Loại 10 Thư Mục Chuyên Ngành

Tài liệu lộ trình chi tiết từng bài (`Bài 1 -> Bài 227`, **235 bài học & 61 chuyên đề**): xem [MISSING_LESSONS_ROADMAP.md](MISSING_LESSONS_ROADMAP.md).

| Thư mục | Phạm vi Kỹ thuật (Engineering Domain) | Các phân hệ tiêu biểu (Prefixes) | Số file |
| :--- | :--- | :--- | :---: |
| [`01_Core_Systems_RTOS_and_Firmware/`](01_Core_Systems_RTOS_and_Firmware/) | Lập trình hệ thống thuần Python, OOP phần cứng, FreeRTOS, DMA/SPI/NVIC, Dual-Bank Bootloader OTA, Bộ nhớ nhúng & DSA | `milestone_*`, `game_*`, `smart_*`, `rtos_*`, `dma_*`, `boot_*`, `dsa_*`, `mem_edge_*allocator/pool*` | 41 |
| [`02_AI_Accelerators_ML_and_Computer_Vision/`](02_AI_Accelerators_ML_and_Computer_Vision/) | Machine Learning, Deep Learning Autograd, OpenCV, NPU Systolic Array, TPU INT4/INT8 & Thị giác sự kiện Neuromorphic DVS/SNN | `ml_*`, `cv_*`, `npu_*`, `tpu_*`, `hw_*`, `dvs_*`, `snn_*`, `neuromorphic_*` | 61 |
| [`03_Chip_Architecture_Memory_and_Interconnects/`](03_Chip_Architecture_Memory_and_Interconnects/) | Kiến trúc SoC 2D NoC MESI & UCIe, PCIe Gen4/Gen6 PAM4 Flit, CXL 3.0, SerDes 64G DFE, ADPLL, LPDDR5X/HBM3e, DFT JTAG Shmoo & HFT | `noc_*`, `pcie_*`, `pcie6_*`, `cxl_*`, `serdes_*`, `adpll_*`, `lpddr5_*`, `mem_edge_lpddr5x*`, `dft_*`, `hft_*` | 36 |
| [`04_Power_Electronics_VRM_and_Thermal/`](04_Power_Electronics_VRM_and_Thermal/) | Nguồn đa pha 1000A VRM & AVP, PDN Integrity & DVFS, USB-PD 3.1 EPR 240W & 4-Switch Buck-Boost, SiC/GaN 800V Inverter & MPPT, 800V EV BMS, FOC/MTPA & Quản lý nhiệt RC | `vrm_*`, `pdn_*`, `usbpd_*`, `power_*`, `bms_*`, `foc_*`, `thermal_*` | 36 |
| [`05_RF_Wireless_Radar_and_Satellite_Comms/`](05_RF_Wireless_Radar_and_Satellite_Comms/) | Viễn thông vô tuyến SDR/Smith/TDR/SAR, RF PA CFR/DPD/Envelope Tracking, UWB IEEE 802.15.4z, GNSS L1/L5 & RTK Centimet, Radar & Satcom | `rf_*`, `rfpa_*`, `uwb_*`, `gnss_*`, `radar_*`, `track_*`, `satcom_*` | 36 |
| [`06_Optical_Photonics_LiDAR_and_Camera_ISP/`](06_Optical_Photonics_LiDAR_and_Camera_ISP/) | Silicon Photonics MZM/MRR/CPO, Quang không gian Starlink FSO, LiDAR OPA/FMCW/SPAD, Cảm biến CMOS 4T-PPD & ISP 5-Line, MIPI CSI-2 | `siph_*`, `fso_*`, `optics_*`, `lidar_*`, `isp_*`, `mipi_*` | 28 |
| [`07_Mixed_Signal_Audio_and_Precision_Actuators/`](07_Mixed_Signal_Audio_and_Precision_Actuators/) | Strain Gauge/Load Cell, ADC ratiometric & hiệu chuẩn nhiệt, ADC/DAC Tín hiệu hỗn hợp, Cảm ứng điện dung PCAP I/Q & Water Rejection, Âm thanh I2S/PDM-CIC/Beamforming, DSP FIR/FFT/ANC, EMC, Haptics LRA Back-EMF & OIS VCM | `strain_*`, `mixed_*`, `touch_*`, `audio_*`, `dsp_*`, `emc_*`, `haptic_*` | 32 |
| [`08_Robotics_Autonomous_Driving_and_Control/`](08_Robotics_Autonomous_Driving_and_Control/) | Điều khiển Robot Ackermann/Admittance/DOB, Encoder A/B/Z & Sin/Cos, BiSS-C SCD CRC-6, EtherCAT DC, MPC Starship/FSD, Sensor Fusion, Mapping, ISO 26262 ASIL-D, CAN-FD & TSN | `robotics_*`, `encoder_*`, `ethercat_*`, `mpc_*`, `fusion_*`, `grid_*`, `safety_*`, `can_*`, `tsn_*` | 46 |
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
