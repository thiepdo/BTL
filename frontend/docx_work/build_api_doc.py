from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = r"E:\dowload\frontend\API_Docs_Smart_Home_IoT.docx"
NAVY = "17365D"
BLUE = "D9EAF7"
GRAY = "F3F5F7"

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.27)
sec.page_height = Inches(11.7)
sec.top_margin = Inches(0.75)
sec.bottom_margin = Inches(0.7)
sec.left_margin = Inches(0.9)
sec.right_margin = Inches(0.75)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Times New Roman"
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15
for name, size in (("Title", 21), ("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11.5)):
    style = styles[name]
    style.font.name = "Times New Roman"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = RGBColor.from_string(NAVY if name != "Title" else "000000")
    style.paragraph_format.keep_with_next = True
    style.paragraph_format.space_before = Pt(10 if name != "Title" else 0)
    style.paragraph_format.space_after = Pt(5)

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)

def set_cell_text(cell, value, bold=False, color=None, size=9.5):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(value))
    r.bold = bold
    r.font.name = "Times New Roman"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def add_table(headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, title in enumerate(headers):
        shade(table.rows[0].cells[i], NAVY)
        set_cell_text(table.rows[0].cells[i], title, bold=True, color="FFFFFF", size=9)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            if len(table.rows) % 2 == 0:
                shade(cells[i], "F5F8FB")
            set_cell_text(cells[i], value, size=9)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table

def para(text, bold_prefix=None):
    p = doc.add_paragraph()
    if bold_prefix and text.startswith(bold_prefix):
        p.add_run(bold_prefix).bold = True
        p.add_run(text[len(bold_prefix):])
    else:
        p.add_run(text)
    return p

def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.add_run(text)
    return p

def code(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.right_indent = Inches(0.12)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.line_spacing = 1.0
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), GRAY)
    p_pr.append(shd)
    r = p.add_run(text.strip())
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    r.font.size = Pt(8.5)
    return p

title = doc.add_paragraph(style="Title")
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.add_run("TÀI LIỆU API SMART HOME IoT")
subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("Đặc tả REST API và giao tiếp MQTT")
run.italic = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor.from_string("526579")
doc.add_paragraph()

doc.add_heading("1. Tổng quan", level=1)
para("Tài liệu mô tả API của hệ thống Smart Home IoT sử dụng Backend Flask, MySQL, MQTT và vi điều khiển ESP8266. Dashboard gọi REST API qua HTTP/JSON để đọc dữ liệu cảm biến, trạng thái LED và lịch sử; Backend dùng MQTT để trao đổi dữ liệu với ESP8266.")
add_table(["Thông tin", "Giá trị"], [
    ("Base URL", "http://localhost:3000/api"),
    ("Định dạng trao đổi", "application/json; UTF-8"),
    ("Tài liệu tương tác", "http://localhost:3000/api/docs (Swagger Editor)"),
    ("Bảng điều khiển", "http://localhost:3000/api/console"),
    ("Đặc tả OpenAPI", "http://localhost:3000/api/openapi.yaml"),
])

doc.add_heading("2. Xác thực", level=1)
para("Các API GET để xem dữ liệu là công khai. Riêng lệnh điều khiển LED và endpoint kiểm tra mật khẩu yêu cầu header X-API-Password. Mật khẩu mặc định là B23DCCN787; Backend có thể đổi giá trị này qua biến môi trường API_ACCESS_PASSWORD.")
code("X-API-Password: B23DCCN787")
para("Trong Swagger Editor, chọn Authorize và nhập mật khẩu. Trong API Console hoặc Dashboard, mật khẩu chỉ được hỏi khi người dùng gửi lệnh điều khiển.")

doc.add_heading("3. Danh sách endpoint", level=1)
add_table(["Method", "Endpoint", "Mục đích", "Xác thực"], [
    ("GET", "/api", "Thông tin và danh sách endpoint", "Không"),
    ("GET", "/api/health", "Kiểm tra MySQL, MQTT, cảm biến", "Không"),
    ("GET", "/api/sensors/latest", "Đọc mẫu cảm biến mới nhất", "Không"),
    ("GET", "/api/sensors", "Tra cứu lịch sử cảm biến", "Không"),
    ("GET", "/api/history", "Tra cứu lịch sử điều khiển", "Không"),
    ("GET", "/api/devices", "Đọc trạng thái LED", "Không"),
    ("GET", "/api/auth/verify", "Kiểm tra mật khẩu API", "Có"),
    ("POST", "/api/devices/{device_id}", "Gửi lệnh bật/tắt LED", "Có"),
    ("GET", "/api/docs", "Mở Swagger Editor", "Không"),
    ("GET", "/api/console", "Mở bảng điều khiển tổng hợp", "Không"),
])

doc.add_heading("4. Đặc tả endpoint", level=1)
doc.add_heading("4.1. Khám phá API", level=2)
para("GET /api trả về thông tin API và các đường dẫn hữu ích. Không yêu cầu xác thực.")
code('''{
  "name": "Smart Home IoT API",
  "docs": "/api/docs",
  "console": "/api/console",
  "openapi": "/api/openapi.yaml",
  "endpoints": ["/api/health", "/api/sensors/latest", "/api/sensors",
                "/api/history", "/api/devices", "/api/devices/{device_id}"]
}''')

doc.add_heading("4.2. Kiểm tra trạng thái hệ thống", level=2)
para("GET /api/health kiểm tra MySQL, trạng thái kết nối MQTT và thời điểm nhận mẫu cảm biến cuối cùng. sensorOnline là true khi Backend nhận đủ dữ liệu cảm biến trong vòng 15 giây gần nhất.")
code('''{
  "ok": true,
  "mqttConnected": true,
  "sensorOnline": true,
  "lastSensorAt": "2026-11-11T09:00:00+00:00"
}''')
para("Mã phản hồi: 200 khi kiểm tra được trạng thái; 503 khi MySQL không khả dụng.")

doc.add_heading("4.3. Xác thực mật khẩu API", level=2)
para("GET /api/auth/verify xác nhận header X-API-Password có giá trị đúng. Endpoint này dùng để kiểm tra mật khẩu trước khi gửi lệnh điều khiển.")
code('''GET /api/auth/verify
X-API-Password: B23DCCN787

200 OK
{"authenticated": true}''')
para("Thiếu hoặc nhập sai mật khẩu sẽ trả 401 Unauthorized với trường error mô tả nguyên nhân.")

doc.add_heading("4.4. Lấy mẫu cảm biến mới nhất", level=2)
para("GET /api/sensors/latest trả nhiệt độ, độ ẩm, ánh sáng và thời gian của mẫu mới nhất. Không yêu cầu xác thực. Giá trị light là ADC trong khoảng 0–1023, không phải lux đã hiệu chuẩn.")
code('''{
  "temp": 25.1,
  "hum": 60.0,
  "light": 700,
  "time": "2026-11-11 16:00:00"
}''')
para("Nếu chưa có đủ dữ liệu của ba loại cảm biến, API trả 404 Not Found.")

doc.add_heading("4.5. Tra cứu lịch sử cảm biến", level=2)
para("GET /api/sensors trả các bản ghi theo thứ tự mới nhất trước. Mỗi bản ghi gồm id, tên cảm biến, loại đo, giá trị, đơn vị và thời gian.")
add_table(["Tham số", "Kiểu", "Mặc định", "Mô tả"], [
    ("page", "integer", "1", "Trang bắt đầu từ 1; giá trị nhỏ hơn 1 được đưa về 1."),
    ("limit", "integer", "50", "Số lượng yêu cầu; được giới hạn trong khoảng 1–100."),
])
code('''GET /api/sensors?page=1&limit=50

{
  "data": [
    {"id": 21, "sensor": "DHT11 Nhiệt độ", "type": "Nhiệt độ",
     "value": 25.1, "unit": "°C", "time": "2026-11-11 16:00:00"}
  ],
  "total": 150,
  "page": 1,
  "limit": 50
}''')

doc.add_heading("4.6. Tra cứu lịch sử điều khiển", level=2)
para("GET /api/history trả các thao tác LED đã ghi nhận, sắp xếp theo thời gian mới nhất trước. Các trường gồm id, device, action, desc, status và time.")
code('''GET /api/history?page=1&limit=50

{
  "data": [
    {"id": 8, "device": "LED1", "action": "BẬT",
     "desc": "LED1_ON", "status": "Thành công",
     "time": "2026-11-11 16:00:00"}
  ],
  "total": 8,
  "page": 1,
  "limit": 50
}''')

doc.add_heading("4.7. Lấy trạng thái thiết bị", level=2)
para("GET /api/devices trả danh sách LED và trạng thái hiện tại. Endpoint không yêu cầu xác thực.")
code('''[
  {"id": 1, "name": "LED1", "state": "OFF", "on": false},
  {"id": 2, "name": "LED2", "state": "ON", "on": true}
]''')

doc.add_heading("4.8. Gửi lệnh bật hoặc tắt LED", level=2)
para("POST /api/devices/{device_id} nhận lệnh điều khiển LED1 hoặc LED2. Request yêu cầu header X-API-Password và JSON body có trường on kiểu boolean.")
code('''POST /api/devices/1
Content-Type: application/json
X-API-Password: B23DCCN787

{"on": true}''')
code('''202 Accepted
{"deviceId": 1, "state": "ON", "status": "PENDING"}''')
para("HTTP 202 cho biết lệnh đã được Backend chấp nhận để gửi qua MQTT; trạng thái vật lý được cập nhật sau phản hồi từ ESP8266.")
add_table(["Mã HTTP", "Ý nghĩa"], [
    ("400", "Thiếu trường on, trường on không phải boolean hoặc device_id không hợp lệ."),
    ("401", "Thiếu hoặc sai mật khẩu API."),
    ("404", "Không tìm thấy thiết bị tương ứng trong cơ sở dữ liệu."),
    ("503", "MQTT chưa kết nối hoặc lệnh không gửi được."),
])

doc.add_heading("5. Giao tiếp MQTT với ESP8266", level=1)
para("HTTP API kết nối Dashboard với Backend. ESP8266 trao đổi dữ liệu với Backend qua MQTT theo ba topic sau:")
add_table(["Topic", "Hướng truyền", "Nội dung"], [
    ("sensor/data", "ESP8266 → Backend", "JSON gồm temperature, humidity và light; gửi khoảng 2 giây/lần."),
    ("device/control", "Backend → ESP8266", "Lệnh văn bản 1_ON, 1_OFF, 2_ON hoặc 2_OFF."),
    ("device/status", "ESP8266 → Backend", "JSON xác nhận deviceId, state và status."),
])
code('''// sensor/data
{"temperature": 25.1, "humidity": 60.0, "light": 700}

// device/status
{"deviceId": 1, "status": "SUCCESS", "state": "ON"}''')
para("Backend lưu dữ liệu cảm biến và phản hồi điều khiển vào MySQL. Giá trị ánh sáng do firmware gửi là số ADC đảo chiều trong khoảng 0–1023.")

doc.add_heading("6. Tài liệu và giao diện thao tác", level=1)
bullet("Swagger Editor và preview API: http://localhost:3000/api/docs")
bullet("Bảng điều khiển API tổng hợp: http://localhost:3000/api/console")
bullet("Tải đặc tả OpenAPI: http://localhost:3000/api/openapi.yaml")

footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.add_run("Smart Home IoT API  |  Trang ")
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), "PAGE")
footer._p.append(fld)

doc.core_properties.title = "Tài liệu API Smart Home IoT"
doc.core_properties.subject = "Đặc tả REST API và MQTT"
doc.core_properties.author = "Smart Home IoT Project"
doc.save(OUT)
print(OUT)
