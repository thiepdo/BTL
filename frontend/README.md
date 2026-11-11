# Smart Home IoT

Frontend dashboard vanilla JavaScript, backend Python Flask REST API, MySQL và MQTT cho firmware ESP8266 trong `iot.ino`. Database dùng các bảng `device`, `sensor`, `data_sensor`, `history`, `user` theo sơ đồ.

## Luồng hoạt động

```text
DHT11 + LDR + ESP8266 -- MQTT sensor/data --> Backend -- MySQL
Dashboard -- HTTP REST --> Backend -- MQTT device/control --> ESP8266
ESP8266 -- MQTT device/status --> Backend -- MySQL
```

Các topic được dùng đúng theo firmware:

- `sensor/data`: JSON `{ "temperature": 25.1, "humidity": 60.0, "light": 700 }`, mỗi 2 giây.
- `device/control`: `1_ON`, `1_OFF`, `2_ON`, `2_OFF`, `ALL_ON`, `ALL_OFF`.
- `device/status`: JSON phản hồi trạng thái LED.

## Cài đặt

Yêu cầu Python 3.10+, MySQL 8+ và MQTT broker mà cả ESP8266 lẫn máy chạy backend cùng truy cập được.

1. Tạo database và bảng:

   ```sh
   mysql -u root -p < database/schema.sql
   ```

2. Sao chép `.env.example` thành `.env`. Điền thông tin MySQL và thông tin broker MQTT trùng với firmware. Không đưa `.env` hoặc mật khẩu vào frontend hay kho mã nguồn.

   ```env
   PORT=3000
   API_ACCESS_PASSWORD=B23DCCN787
   FRONTEND_ORIGIN=http://localhost:5500
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=mat_khau_mysql
   DB_NAME=smart_home_iot
   DB_TIME_ZONE=+07:00
   MQTT_HOST=DIA_CHI_BROKER
   MQTT_PORT=2005
   MQTT_USERNAME=ten_tai_khoan_mqtt
   MQTT_PASSWORD=mat_khau_mqtt
   ```

3. Cài Python 3.10+; tạo môi trường ảo, cài thư viện và chạy backend:

   ```sh
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```

4. Mở frontend qua Live Server tại `http://localhost:5500` (hoặc một static web server khác). Mặc định frontend gọi API ở `http://localhost:3000/api`; sửa `API_BASE` ở đầu `app.js` nếu backend ở máy/port khác.

5. Kiểm tra `http://localhost:3000/api/health`. Dashboard hiện ESP8266 online khi backend nhận được mẫu cảm biến trong 15 giây gần nhất; MQTT hiển thị theo kết nối backend tới broker.

## API docs

- Đặc tả OpenAPI 3.0 đầy đủ: [`openapi.yaml`](openapi.yaml).
- Dashboard ở `http://localhost:5500` hiển thị dữ liệu và trạng thái công khai, không cần đăng nhập. Mở **`http://localhost:3000/api/console`** để xem bảng điều khiển gộp và nhập mật khẩu nếu cần bật/tắt đèn.
- Mở **`http://localhost:3000/api/docs`** để dùng Swagger Editor và preview API tương tác. Bấm **Authorize**, nhập `B23DCCN787`, rồi gọi endpoint điều khiển.
- `http://localhost:3000/api/openapi.yaml` trả đặc tả OpenAPI thô.
- Có thể import `openapi.yaml` vào Swagger Editor, Swagger UI hoặc Postman để duyệt tài liệu và tạo request.
- **Authentication:** dashboard và các API đọc là công khai. Chỉ `POST /api/devices/{device_id}` cần mật khẩu qua header `X-API-Password`. Mặc định là `B23DCCN787`; có thể đổi bằng `API_ACCESS_PASSWORD` trong `.env`. Swagger Editor dùng nút **Authorize** để nhập mật khẩu một lần; API Console cũng có ô nhập mật khẩu. CORS vẫn được giới hạn theo `FRONTEND_ORIGIN` và các origin localhost mặc định.

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | `/api` | Thông tin và danh sách endpoint |
| GET | `/api/auth/verify` | Kiểm tra mật khẩu API (cần `X-API-Password`) |
| GET | `/api/docs` | Swagger Editor cùng preview thao tác API |
| GET | `/api/console` | Bảng điều khiển tổng hợp cơ bản |
| GET | `/api/openapi.yaml` | Tải OpenAPI YAML |
| GET | `/api/health` | Kiểm tra MySQL, MQTT và độ mới của mẫu cảm biến |
| GET | `/api/sensors/latest` | Mẫu mới nhất `{ temp, hum, light, time }` (công khai) |
| GET | `/api/sensors?page=1&limit=50` | Lịch sử cảm biến dạng dòng bảng (công khai) |
| GET | `/api/history?page=1&limit=50` | Lịch sử điều khiển LED (công khai) |
| GET | `/api/devices` | Trạng thái LED1 và LED2 (công khai) |
| POST | `/api/devices/{device_id}` | Gửi lệnh bật/tắt; yêu cầu `X-API-Password` |

Danh sách cảm biến và lịch sử dùng phân trang `page` (bắt đầu từ 1) và `limit` (mặc định 50, tối đa 100). Lệnh điều khiển trả `202 PENDING` khi backend chấp nhận gửi lệnh MQTT; trạng thái thực tế được cập nhật sau phản hồi từ thiết bị trên topic `device/status`. Chi tiết schema, ví dụ thành công/lỗi và mã HTTP nằm trong `openapi.yaml`.

Mỗi lần nhận MQTT, backend lưu nhiệt độ, độ ẩm và ánh sáng vào `data_sensor` theo các loại sensor đã khai báo trong `sensor`. Khi nhận `device/status`, backend cập nhật `device.status` và thêm một dòng `history`. Theo yêu cầu sơ đồ, `history.device_id` không có khóa ngoại đến `device`; quan hệ khóa ngoại chỉ nối `device`–`sensor`, `sensor`–`data_sensor`, và `history`–`user`. Firmware gửi `light` trong khoảng 0–1023; đây là giá trị ADC đảo chiều, không phải phép đo lux đã hiệu chuẩn.

## Cấu hình firmware

Địa chỉ Wi-Fi, broker, port, username và password cần khớp với cấu hình mạng thực tế. Firmware hiện có thông tin truy cập được ghi trực tiếp trong `iot.ino`; thay bằng thông tin của bạn trước khi chia sẻ hoặc triển khai, sau đó đặt cùng thông tin broker vào `.env` của backend. Không kết nối MQTT trực tiếp từ trình duyệt vì sẽ làm lộ thông tin xác thực.
