# Xe ESP32 điều khiển bằng điện thoại

## Linh kiện

- ESP32 DevKit (ESP-WROOM-32)
- Mạch cầu H L298N
- 2 động cơ DC + khung xe
- Cảm biến siêu âm HC-SR04
- Servo SG90
- Màn hình OLED SSD1306 128x64 (I2C)
- Pin

## Chức năng của xe

- **Điều khiển bằng điện thoại**: ESP32 tự phát Wi-Fi, mở trình duyệt là có giao diện tay cầm, không cần Internet.
- **Di chuyển**: tiến, lùi, xoay trái, xoay phải tại chỗ, vòng cua trái, vòng cua phải.
- **3 mức tốc độ**: chậm, vừa, nhanh.
- **Tự lái tránh vật cản**: gặp vật cản thì dừng, quét trái phải bằng servo rồi rẽ về phía thoáng hơn.
- **Phanh khẩn cấp**: tự dừng khi đang lái tay tiến vào vật cản gần.
- **An toàn**: mất kết nối Wi-Fi thì xe tự dừng.
- **Màn hình OLED**: hiển thị trạng thái xe, khoảng cách vật cản và tốc độ, có 3 trang đổi được từ giao diện web.
