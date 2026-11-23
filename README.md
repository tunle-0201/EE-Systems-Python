# 🚀 EE Systems Engineering & Pure Python Architecture

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Domain](https://img.shields.io/badge/Domain-Electrical%20Engineering%20%26%20Systems-green.svg)
![Status](https://img.shields.io/badge/Architecture-From%20Scratch-orange.svg)

Hồ sơ dự án kỹ thuật nền tảng, tập trung vào **Quản lý bộ nhớ RAM**, **Kiến trúc luồng xử lý CPU**, **Lập trình mạng tầng Socket thô**, và **Đa xử lý đa nhân (Concurrency & Parallelism)**.

Tất cả các module được xây dựng thuần bằng **Pure Python** (không sử dụng thư viện black-box cao cấp) để làm chủ bản chất vật lý của hệ thống máy tính.

---

## 🛠️ CẤU TRÚC HỆ THỐNG MODULES

```text
OneDrive/Python Mastering/
├── EE_Mentorship/
│   ├── MISSING_LESSONS_ROADMAP.md                           # Lộ trình đến Bài 231; tổng 239 bài học & 62 chuyên đề
│   ├── MASTER_MENTORSHIP_SYSTEM_PROMPT.md                   # Chuẩn sư phạm Constructivist Bottom-Up
│   ├── drone_system/                                        # Hệ thống điều khiển Drone Core (Module F)
│   ├── 01_Core_Systems_RTOS_and_Firmware/                   # Core Python, Async, Sockets, RTOS, DMA, Bootloader, DSA
│   ├── 02_AI_Accelerators_ML_and_Computer_Vision/           # ML/DL, OpenCV, NPU Systolic Array, TPU, Neuromorphic DVS/SNN
│   ├── 03_Chip_Architecture_Memory_and_Interconnects/       # NoC, UCIe, PCIe Gen4/6, CXL 3.0, SerDes, ADPLL, LPDDR5X/HBM3e, DFT
│   ├── 04_Power_Electronics_VRM_and_Thermal/                # VRM 1000A AVP, PDN Integrity, SiC/GaN 800V, BMS, FOC, Thermal RC
│   ├── 05_RF_Wireless_Radar_and_Satellite_Comms/            # RF/SAR/Phased Array, RF PA CFR/DPD/ET, UWB, GNSS/RTK, Radar, Satcom
│   ├── 06_Optical_Photonics_LiDAR_and_Camera_ISP/           # Silicon Photonics CPO, Starlink FSO, LiDAR OPA/FMCW/SPAD, CMOS ISP, MIPI
│   ├── 07_Mixed_Signal_Audio_and_Precision_Actuators/       # Pt100/RTD, Strain Gauge/Load Cell, Mixed-Signal ADC/DAC, Audio I2S/PDM, DSP, EMC, Haptics LRA & OIS VCM
│   ├── 08_Robotics_Autonomous_Driving_and_Control/          # Robotics DOB/DWA, Encoder ABZ/SinCos/BiSS-C, EtherCAT, MPC, Sensor Fusion, ISO 26262, CAN, TSN
│   ├── 09_Aerospace_Spacecraft_and_Avionics/                # CubeSat ADCS, Strapdown INS/ES-EKF, MIL-STD-1553B/ARINC429, SpaceWire/Fibre, HIL
│   └── 10_Hardware_Security_PQC_and_Fault_Tolerance/        # PQC ML-KEM/NTT/DPA, AES/ECDSA/SHA3, Rad-Hard TMR & Byzantine
├── flight_recorder.py                                       # Milestone Project: Closed-Loop System Architecture
├── CURRICULUM.md                                            # Giáo trình Constructivist 4-Bước
├── .gitignore                                               # Git Shield Configuration
└── README.md                                                # Portfolio Documentation
```

---

## 🔬 TÓM TẮT NĂNG LỰC KỸ THUẬT (TECHNICAL COMPETENCIES)

### 1. Quản Lý Bộ Nhớ & Con Trỏ (RAM & Pointers)
*   **Heap Allocation & Pointers:** Hiểu bản chất biến là con trỏ lưu địa chỉ ô nhớ vật lý (`0x1000`). Phân biệt tác động giữa **Shallow Copy** (`copy()`) và **Deep Copy** (`deepcopy()`) trên cấu trúc dữ liệu lồng nhau.
*   **Hash Maps & Collisions:** Giải mã cơ chế băm dữ liệu trong Dictionary và thuật toán xử lý chập ô nhớ **Open Addressing (Linear Probing)**.

### 2. Lập Trình Bất Đồng Bộ & Luồng Sự Kiện (Event-Driven & Async)
*   **CPU Clock Cycles & Non-blocking:** Loại bỏ cái chết ngắt luồng (`time.sleep`) bằng tư duy đếm xung nhịp và **Event Loop**.
*   **Coroutine & `async/await`:** Giải phóng CPU nhường quyền (`Yield`) cho các tác vụ khác trong lúc chờ I/O thiết bị ngoại vi.

### 3. Giao Tiếp Mạng Tầng Socket (Low-Level Networking)
*   **Bytes & Encoding:** Mã hóa văn bản thành dãy Bytes thô (ASCII/UTF-8) đại diện cho xung điện High (+3.3V) / Low (0V).
*   **TCP/IP Socket Engine:** Tự phát triển máy chủ Multiplayer Real-time sử dụng địa chỉ IP vật lý và phân luồng Cổng mạng (PORT).

### 4. Thiết Kế Hướng Đối Tượng (Hardware OOP & Abstraction)
*   **Class vs Instance:** Phân bổ vùng nhớ RAM giữa bản thiết kế chung (Class) và đối tượng vật lý (Instance).
*   **PWM Duty Cycle Control:** Kế thừa Class và mô phỏng tín hiệu **Điều rộng xung (Pulse Width Modulation)** kiểm soát công suất thiết bị điện.

### 5. Xử Lý Song Song & Đa Nhân (Concurrency & Parallelism)
*   **Multithreading & Mutex Locks:** Quản lý nhiều công nhân dùng chung bộ nhớ Heap, sử dụng `threading.Lock()` triệt tiêu thảm họa tranh chấp RAM **Race Condition**.
*   **Multiprocessing & IPC Queues:** Bẻ gãy xích khóa GIL của Python để vắt kiệt 100% sức mạnh đa nhân CPU, truyền thông điệp liên tiến trình qua **IPC (Inter-Process Communication)**.

---

## ⚡ HƯỚNG DẪN KHỞI CHẠY (QUICK START)

### 1. Khởi tạo môi trường ảo (Virtual Environment)
```bash
python -m venv .venv
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
```

### 2. Chạy thử nghiệm Game Server Multiplayer & AI Boss
```bash
# Khởi động Game Server
python EE_Mentorship/01_Core_Systems_RTOS_and_Firmware/game_server_ai.py

# Mở cửa sổ Terminal mới để kết nối Client vào chơi
python EE_Mentorship/01_Core_Systems_RTOS_and_Firmware/game_client.py
```

---

## 👤 AUTHOR
*   **Lê Đắc Anh Tuấn** - Student of Electrical Engineering (EE)
