# 📋 DANH SÁCH BÀI HỌC VÀ KHÁI NIỆM CẦN BÙ ĐẮP (DEEP-DIVE ROADMAP)

File này ghi nhận toàn bộ các bài học, thuật toán và bản chất toán học/phần cứng mà người học sẽ được Sư phụ **MỔ XẺ CẶN KẼ 100% VÀO THỨ 5 VÀ CUỐI TUẦN (MAKE-UP DAY)**:

---

## 👁️ MODULE C, G & H: COMPUTER VISION & CNN HARDWARE ACCELERATION
- [ ] **Phép cuộn ma trận 2D Convolution (`cv_edge_convolution_2d.py`):** Bản chất con dấu Kernel trượt khắp ảnh trích xuất cạnh (Edge Detection).
- [ ] **Phép nén không gian Max Pooling (`cv_edge_max_pooling.py`):** Giảm 75% kích thước ma trận khung hình giữ lại đặc trưng mạnh nhất.
- [ ] **Hàm chuẩn hóa xác suất Softmax (`cv_edge_soft_max.py`):** Phép tính $e^{z_i} / \sum e^{z_j}$ chuyển đổi đa lớp thành xác suất %.
- [ ] **Lucas-Kanade Optical Flow:** Định vị vị trí và giữ tọa độ Drone khi không có GPS (GPS-Denied Environment).
- [ ] **ArUco Marker Precision Landing:** Thuật toán căn chỉnh hạ cánh chính xác milimet xuống trạm sạc tự động.
- [ ] **Stereo Vision Disparity Map:** Tính bản đồ độ sâu 3D (3D Depth Map) từ 2 camera song song để né vật cản.

---

## 🧠 MODULE D: DEEP LEARNING (BÙ TOÁN HỌC & ĐẠO HÀM)
- [ ] **Bản chất Trọng số $W$, Bias $b$ và Sigmoid:** Tại sao $1 / (1 + e^{-Z})$ ép tín hiệu về xác suất 0..1.
- [ ] **ReLU $\max(0, Z)$ ở Lớp Ẩn:** Định lý Xấp xỉ Vạn năng (Universal Approximation Theorem) và tại sao ReLU thắng Sigmoid.
- [ ] **Đạo hàm Lan truyền ngược Backpropagation:** Công thức Chain Rule $\frac{\partial L}{\partial W} = 2 \cdot (\hat{y} - y) \cdot X$.
- [ ] **Hàm Loss MSE vs BCE:** Phép phạt hóc hiểm của $-\log(\hat{y})$ trong bài toán phân loại.
- [ ] **Thuật toán Mini-Batch Gradient Descent:** Tại sao chia Lô $B = 20$ giúp tối ưu RAM GPU và phép nhân ma trận chuyển vị $X^T$.
- [ ] **PyTorch Autograd & Computational Graph:** Cơ chế lật ngược sổ nhật ký `loss.backward()` tính `W.grad`.

---

## ⚡ MODULE E & F: EDGE AI & REAL-TIME EMBEDDED FLIGHT CONTROL
- [ ] **Nén mô hình Int8 Quantization:** Nén Float32 (4 bytes) xuống Int8 (1 byte) tiết kiệm 75% RAM.
- [ ] **Tỉa nhánh Weight Pruning:** Triệt tiêu trọng số nhỏ hơn 0.1 tăng tốc 300%.
- [ ] **Xuất mảng C-Header (`const float W[]`):** Nhúng trực tiếp mô hình AI vào bộ nhớ Flash ROM của ESP32/STM32.
- [ ] **Closed-Loop PID Controller:** Phản ứng 3 thành phần P, I, D giữ cân bằng Drone trước gió cuộn.
- [ ] **Ring Buffer UART DMA FIFO:** Quản lý vòng đệm tròn tránh tràn RAM khi nhận dữ liệu telemetry 100Hz.
- [ ] **Failsafe Watchdog Protection:** Tự động chuyển chế độ hạ cánh khẩn cấp khi mất kết nối tay cầm.
