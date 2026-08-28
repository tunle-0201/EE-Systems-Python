# 📋 SỔ THEO DÕI TIẾN ĐỘ & DANH MỤC BÀI HỌC CẦN BÙ (DEEP-DIVE ROADMAP)

Bản cập nhật ngày: **27/08/2026**  
Kho mã nguồn: **https://github.com/tunle-0201/EE-Systems-Python**

---

## 🏆 CÁC MODULE ĐÃ HOÀN THÀNH VÀ THẤU SUỐT 100% (COMPLETED ✅)

1. [x] **Module 1-5 (Core Systems):** RAM Pointers, Async Event Loop, Sockets, Hardware OOP, Multithreading & Multiprocessing.
2. [x] **Module 6 (Binary Protocol):** Struct Pack/Unpack, Endianness, Giao thức Drone Telemetry 16-Bytes.
3. [x] **Module B (Machine Learning Core):** NumPy Tensors, Slicing X/y, Decision Trees, StandardScaler Z-Score.
4. [x] **Module C (Computer Vision Core):** 3D Image Tensors, BGR vs Grayscale, Thresholding, Contours, Bounding Boxes, Gaussian Blur, Aspect Ratio, HSV, Morphology.
5. [x] **Module E (Edge AI Core):**
   - [x] Milestone E.1: `ml_edge_quantization.py` (Int8 Quantization nén 75% RAM)
   - [x] Milestone E.2: `ml_edge_pruning.py` (Weight Pruning tỉa nhánh tăng tốc 300%)
   - [x] Milestone E.3: `ml_edge_c_header_export.py` (Xuất mảng C-Header nhúng Flash STM32/ESP32)
   - [x] Milestone E.4: `ml_edge_drone_telemetry_ai.py` (Bộ não Edge AI Telemetry Real-time)
6. [x] **Module F (Drone Flight Control Core):**
   - [x] Milestone F.1: `pid_controller.py` (Bộ điều khiển hồi tiếp kín Closed-Loop PID)
   - [x] Milestone F.2: `ring_buffer_uart.py` (Vòng đệm tròn UART DMA FIFO)
   - [x] Milestone F.3: `failsafe_watchdog.py` (Mạch phòng vệ Watchdog & Hạ cánh Failsafe)
   - [x] Milestone F.4: `flight_controller_capstone.py` (Động cơ bay thời gian thực Flight Engine)

---

## 📚 TỔNG HỢP CÁC BÀI HỌC CẦN BÙ ĐẮP CHIỀU SÂU (MISSING LESSONS TO MAKE UP)

Tổng cộng trò có **4 Nhóm chuyên đề lớn** cần bù đắp theo đúng phương pháp Bottom-Up:

### 🧠 NHÓM 1: TOÁN HỌC DEEP LEARNING & ĐẠO HÀM (MODULE D - 6 BÀI)
- [ ] **Bài 1:** `ml_dl_perceptron.py` -> Bản chất Trọng số W, Bias b và hàm kích hoạt Sigmoid.
- [ ] **Bài 2:** `ml_dl_forward_pass.py` -> Mạng 2 lớp & Hàm ReLU xấp xỉ vạn năng.
- [ ] **Bài 3:** `ml_dl_backprop.py` -> Đạo hàm lan truyền ngược Backpropagation (Chain Rule dL/dW).
- [ ] **Bài 4:** `ml_dl_loss_functions.py` -> So sánh hàm mất mát MSE vs Binary Cross-Entropy.
- [ ] **Bài 5:** `ml_dl_minibatch.py` -> Thuật toán Mini-Batch Gradient Descent (Batch size = 20, X.T).
- [ ] **Bài 6:** `ml_dl_pytorch_autograd.py` -> Đồ thị tính toán PyTorch Computational Graph & `loss.backward()`.

### 👁️ NHÓM 2: THỊ GIÁC MÁY TÍNH & CNN TRÍ TUỆ NHÂN TẠO (MODULE G & H - 6 BÀI)
- [ ] **Bài 7:** `cv_edge_convolution_2d.py` -> Phép nhân chập ma trận 2D Convolution trích xuất cạnh.
- [ ] **Bài 8:** `cv_edge_max_pooling.py` -> Phép nén không gian Max Pooling 2x2.
- [ ] **Bài 9:** `cv_edge_soft_max.py` -> Hàm chuẩn hóa xác suất đa lớp Softmax.
- [ ] **Bài 10:** `cv_edge_optical_flow.py` -> Lucas-Kanade Optical Flow giữ tọa độ Drone không có GPS.
- [ ] **Bài 11:** `cv_edge_aruco_landing.py` -> ArUco Marker Precision Landing hạ cánh chính xác trạm sạc.
- [ ] **Bài 12:** `cv_edge_stereo_depth.py` -> Stereo Vision Disparity Map đo độ sâu 3D né vật cản.

### 🎯 NHÓM 3: PHÁT HIỆN VẬT THỂ & KHUNG BAO OBJECT DETECTION (MODULE I - 3 BÀI)
- [ ] **Bài 13:** `cv_edge_iou_calculator.py` -> Tỷ lệ giao nhau Intersection over Union (IoU).
- [ ] **Bài 14:** `cv_edge_non_max_suppression.py` -> Thuật toán khử trùng lặp khung NMS.
- [ ] **Bài 15:** `cv_edge_yolo_drone_detector.py` -> Kiến trúc phát hiện mục tiêu YOLO cho Drone.

### ⚡ NHÓM 4: CÁC CHUYÊN ĐỀ PHẦN CỨNG & HỆ THỐNG CAO CẤP (MODULE J -> Q - 8 CHUYÊN ĐỀ)
- [ ] **Chuyên đề J:** Kiến trúc chip NPU (Khối MAC, Mảng Systolic Array, Vector SIMD 128-bit).
- [ ] **Chuyên đề K:** Hệ điều hành thời gian thực FreeRTOS (Task Scheduler, Mutex, Message Queue).
- [ ] **Chuyên đề L:** Xử lý tín hiệu số DSP (Mạch lọc FIR, Phân tích phổ FFT cánh quạt, Mạch IIR).
- [ ] **Chuyên đề M:** Mạng truyền thông xe hơi CAN-Bus (11-bit ID, Bit Stuffing, Bitwise Arbitration).
- [ ] **Chuyên đề N:** Dung hợp cảm biến Sensor Fusion (Complementary Filter, Kalman Filter 1D).
- [ ] **Chuyên đề O:** An ninh mạng nhúng Cybersecurity (HMAC-SHA256, AES-128, Secure Boot).
- [ ] **Chuyên đề P:** Động học Robot & Điều hướng (Đại số 4D Quaternion, Quỹ đạo bậc 3, Forward Kinematics).
- [ ] **Chuyên đề Q:** Hệ thống giao dịch siêu tốc Low-Latency (Limit Order Book, FIX Protocol, VWAP).
