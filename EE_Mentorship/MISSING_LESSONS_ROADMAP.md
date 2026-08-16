# 📋 DANH SÁCH BÀI HỌC VÀ KHÁI NIỆM CẦN BÙ ĐẮP (DEEP-DIVE ROADMAP)

File này ghi nhận toàn bộ các bài học, thuật toán và bản chất toán học/phần cứng mà người học sẽ được Sư phụ **MỔ XẺ CẶN KẼ 100%** khi quay trở lại sau đợt bận rộn:

---

## 👁️ MODULE C: COMPUTER VISION (BÙ LÝ THUYẾT & MỔ XẺ CODE)
- [ ] **Khái niệm OpenCV Channels & BGR vs RGB:** Tại sao `bgr[:, :, 1]` rút kênh màu Xanh lá?
- [ ] **Mạch lọc mờ Gaussian Blur (`cv2.GaussianBlur`):** Phép toán Convolution ma trận $5 \times 5$ triệt tiêu nhiễu hạt.
- [ ] **Thuật toán Contours & Bounding Box (`cv2.findContours`, `cv2.boundingRect`):** Thuật toán tìm 4 cực trị $x_{min}, y_{min}, x_{max}, y_{max}$.
- [ ] **Bộ lọc phòng vệ Aspect Ratio ($W/H$):** Triệt tiêu 100% vết bẩn nhòe dính trên ống kính.
- [ ] **Không gian màu HSV (Hue - Saturation - Value):** Tại sao góc $H$ độc lập 100% với nắng/bóng râm ngoài trời.
- [ ] **Bộ đôi Phép toán Hình thái học (`cv2.erode`, `cv2.dilate`):** Bản chất con dấu Kernel $5 \times 5$ dọn rác ti ti và vá lỗ hổng rỗng.

---

## 🧠 MODULE D: DEEP LEARNING (BÙ TOÁN HỌC & ĐẠO HÀM)
- [ ] **Bản chất Trọng số $W$, Bias $b$ và Sigmoid:** Tại sao $1 / (1 + e^{-Z})$ ép tín hiệu về xác suất 0..1.
- [ ] **ReLU $\max(0, Z)$ ở Lớp Ẩn:** Định lý Xấp xỉ Vạn năng (Universal Approximation Theorem) và tại sao ReLU thắng Sigmoid.
- [ ] **Đạo hàm Lan truyền ngược Backpropagation:** Công thức Chain Rule $\frac{\partial L}{\partial W} = 2 \cdot (\hat{y} - y) \cdot X$.
- [ ] **Hàm Loss MSE vs BCE:** Phép phạt hóc hiểm của $-\log(\hat{y})$ trong bài toán phân loại.
- [ ] **Thuật toán Mini-Batch Gradient Descent:** Tại sao chia Lô $B = 20$ giúp tối ưu RAM GPU và phép nhân ma trận chuyển vị $X^T$.
- [ ] **PyTorch Autograd & Computational Graph:** Cơ chế lật ngược sổ nhật ký `loss.backward()` tính `W.grad`.

---

## ⚡ MODULE E: EDGE AI & EE HARDWARE EMBEDDED
- [ ] **Nén mô hình Int8 Quantization:** Nén Float32 (4 bytes) xuống Int8 (1 byte) tiết kiệm 75% RAM.
- [ ] **Tỉa nhánh Weight Pruning:** Triệt tiêu trọng số nhỏ hơn 0.1 tăng tốc 300%.
- [ ] **Xuất mảng C-Header (`const float W[]`):** Nhúng trực tiếp mô hình AI vào bộ nhớ Flash ROM của ESP32/STM32.
- [ ] **Sensor Fusion & Kalman Filter:** Kết hợp cảm biến Gia tốc + AI cho Drone.
