"""Flask API and MQTT bridge for the ESP8266 Smart Home dashboard."""

from __future__ import annotations

import json
import hmac
import logging
import os
import threading
from functools import wraps
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import mysql.connector
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from mysql.connector.pooling import MySQLConnectionPool

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("smart-home")

app = Flask(__name__)
API_ACCESS_PASSWORD = os.getenv("API_ACCESS_PASSWORD", "B23DCCN787")
default_origins = [
    "http://localhost:5500", "http://127.0.0.1:5500",
    "http://localhost:5501", "http://127.0.0.1:5501",
]
configured_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "").split(",") if origin.strip()]
CORS(app, origins=list(dict.fromkeys(default_origins + configured_origins)))
db_pool = MySQLConnectionPool(
    pool_name="smart_home_pool", pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "smart_home_iot"), time_zone=os.getenv("DB_TIME_ZONE", "+07:00"),
)

last_sensor_at: datetime | None = None
sensor_lock = threading.Lock()
pending_lock = threading.Lock()
# Runtime-only command map; the database history table follows the supplied ERD.
pending_commands: dict[int, dict] = {}


def require_auth(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("X-API-Password", "")
        if not supplied or not hmac.compare_digest(supplied.encode("utf-8"), API_ACCESS_PASSWORD.encode("utf-8")):
            return jsonify(error="Thiếu hoặc sai mật khẩu API", code="unauthorized"), 401
        return handler(*args, **kwargs)
    return wrapped


@app.get("/api/auth/verify")
@require_auth
def verify_api_password():
    return jsonify(authenticated=True)


def query(sql: str, params: tuple = (), *, one: bool = False, write: bool = False):
    connection = db_pool.get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        if write:
            connection.commit()
            return cursor.lastrowid
        return cursor.fetchone() if one else cursor.fetchall()
    except Exception:
        if write:
            connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def time_text(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else str(value)


def on_connect(client, _userdata, _flags, reason_code, _properties=None):
    # Paho MQTT 2 passes a ReasonCode object, not an int.
    if not reason_code.is_failure:
        logger.info("Connected to MQTT broker")
        client.subscribe([("sensor/data", 0), ("device/status", 1)])
    else:
        logger.error("MQTT connection failed: %s", reason_code)


def save_device_ack(device_id: int, state: str, success: bool):
    actual_status = int(state == "ON")
    query("UPDATE device SET status=%s WHERE device_id=%s", (actual_status, device_id), write=True)
    with pending_lock:
        commands = pending_commands.get(device_id, [])
        pending = commands.pop(0) if commands else None
        if not commands:
            pending_commands.pop(device_id, None)
    if pending:
        query(
            "INSERT INTO history (user_id, device_id, action, old_status, new_status, action_time) "
            "VALUES (%s, %s, %s, %s, %s, NOW())",
            (pending.get("user_id"), device_id, f"LED{device_id}_{'ON' if success else 'FAILED'}",
             pending["old"], actual_status),
            write=True,
        )


def ensure_sensor_ids():
    """Ensure the three MQTT values have active rows in the user's sensor table."""
    definitions = {
        "temperature": ("DHT11 Nhiệt độ", "°C"),
        "humidity": ("DHT11 Độ ẩm", "%"),
        "light": ("LDR Ánh sáng", "ADC"),
    }
    device = query("SELECT device_id FROM device ORDER BY device_id LIMIT 1", one=True)
    if device:
        sensor_device_id = device["device_id"]
    else:
        sensor_device_id = query(
            "INSERT INTO device (device_name, device_type, status, location) "
            "VALUES ('ESP8266 Gateway', 'ESP8266', 1, 'Gateway')",
            write=True,
        )
    sensors = query("SELECT sensor_id, sensor_type FROM sensor WHERE status=1")
    ids = {row["sensor_type"]: row["sensor_id"] for row in sensors}
    for sensor_type, (name, unit) in definitions.items():
        if sensor_type not in ids:
            query(
                "INSERT INTO sensor (device_id, sensor_name, sensor_type, unit, status) "
                "VALUES (%s, %s, %s, %s, 1)",
                (sensor_device_id, name, sensor_type, unit), write=True,
            )
    sensors = query("SELECT sensor_id, sensor_type FROM sensor WHERE status=1")
    return {row["sensor_type"]: row["sensor_id"] for row in sensors}


def on_message(_client, _userdata, message):
    global last_sensor_at
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        if message.topic == "sensor/data":
            values = {
                "temperature": float(payload["temperature"]),
                "humidity": float(payload["humidity"]),
                "light": float(payload["light"]),
            }
            limits = {"temperature": (-20, 80), "humidity": (0, 100), "light": (0, 1023)}
            if any(not limits[key][0] <= value <= limits[key][1] for key, value in values.items()):
                raise ValueError("Sensor value is outside the accepted range")
            sensor_ids = ensure_sensor_ids()
            sample_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None, microsecond=0)
            for sensor_type, value in values.items():
                if sensor_type in sensor_ids:
                    query(
                        "INSERT INTO data_sensor (sensor_id, value, recorded_at) VALUES (%s, %s, %s)",
                        (sensor_ids[sensor_type], value, sample_time), write=True,
                    )
            if all(sensor_type in sensor_ids for sensor_type in values):
                with sensor_lock:
                    last_sensor_at = datetime.now(timezone.utc)
                logger.info("Saved sensor/data: temperature=%s humidity=%s light=%s", values["temperature"], values["humidity"], values["light"])
        elif message.topic == "device/status":
            device_id = int(payload["deviceId"])
            state = payload.get("state")
            if device_id in (1, 2) and state in ("ON", "OFF"):
                save_device_ack(device_id, state, payload.get("status") == "SUCCESS")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("Invalid MQTT message on %s: %s", message.topic, exc)
    except Exception:
        logger.exception("Could not process MQTT message on %s", message.topic)


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smart-home-backend")
mqtt_client.username_pw_set(os.getenv("MQTT_USERNAME") or None, os.getenv("MQTT_PASSWORD") or None)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)


def start_mqtt():
    mqtt_client.connect_async(os.getenv("MQTT_HOST", "127.0.0.1"), int(os.getenv("MQTT_PORT", "1883")), 60)
    mqtt_client.loop_start()


def page_params():
    try:
        page = max(1, int(request.args.get("page", "1")))
        limit = min(100, max(1, int(request.args.get("limit", "50"))))
        return page, limit
    except ValueError:
        return 1, 50


@app.get("/api/health")
def health():
    try:
        query("SELECT 1", one=True)
        with sensor_lock:
            seen = last_sensor_at
        online = bool(seen and (datetime.now(timezone.utc) - seen).total_seconds() < 15)
        return jsonify(ok=True, mqttConnected=mqtt_client.is_connected(), sensorOnline=online,
                       lastSensorAt=seen.isoformat() if seen else None)
    except mysql.connector.Error:
        return jsonify(ok=False, mqttConnected=mqtt_client.is_connected(), sensorOnline=False), 503


@app.get("/api")
def api_index():
    """Small discovery response for the API base URL."""
    return jsonify(
        name="Smart Home IoT API",
        docs="/api/docs",
        console="/api/console",
        openapi="/api/openapi.yaml",
        endpoints=[
            "/api/docs", "/api/console", "/api/health",
            "/api/auth/verify",
            "/api/sensors/latest", "/api/sensors",
            "/api/history", "/api/devices", "/api/devices/{device_id}",
        ],
    )


@app.get("/api/console")
def api_console():
    """Serve the single-page IoT API control panel."""
    return send_from_directory(app.root_path, "api-console.html")


@app.get("/api/docs")
def swagger_docs():
    """Swagger Editor with a live API preview for the published specification."""
    return render_template_string("""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Smart Home API Editor</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-editor-dist@4.14.8/swagger-editor.css">
  <style>html,body,#swagger-editor{margin:0;width:100%;height:100%;overflow:hidden}</style>
</head>
<body>
  <div id="swagger-editor"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-editor-dist@4.14.8/swagger-editor-bundle.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/swagger-editor-dist@4.14.8/swagger-editor-standalone-preset.js"></script>
  <script>
    window.onload = () => SwaggerEditorBundle({
      url: '/api/openapi.yaml', dom_id: '#swagger-editor',
      layout: 'StandaloneLayout', presets: [SwaggerEditorStandalonePreset],
      tryItOutEnabled: true, persistAuthorization: true
    });
  </script>
</body>
</html>""")


@app.get("/api/openapi.yaml")
def openapi_spec():
    return send_from_directory(app.root_path, "openapi.yaml", mimetype="application/yaml")


@app.get("/api/sensors/latest")
def latest_sensor():
    rows = query("""SELECT s.sensor_type, d.value, d.recorded_at
        FROM sensor s JOIN data_sensor d ON d.sensor_id=s.sensor_id
        WHERE d.data_id=(SELECT MAX(d2.data_id) FROM data_sensor d2 WHERE d2.sensor_id=s.sensor_id)""")
    values = {row["sensor_type"]: row for row in rows}
    if not all(key in values for key in ("temperature", "humidity", "light")):
        return jsonify(error="Chưa có đủ dữ liệu cảm biến"), 404
    latest_time = max(row["recorded_at"] for row in values.values())
    return jsonify(temp=float(values["temperature"]["value"]), hum=float(values["humidity"]["value"]),
                   light=int(values["light"]["value"]), time=time_text(latest_time))


@app.get("/api/sensors")
def sensor_history():
    page, limit = page_params()
    rows = query("""SELECT d.data_id AS id, s.sensor_name, s.sensor_type, s.unit,
        d.value, d.recorded_at AS time FROM data_sensor d
        JOIN sensor s ON s.sensor_id=d.sensor_id
        ORDER BY d.data_id DESC LIMIT %s OFFSET %s""", (limit * 3, (page - 1) * limit * 3))
    count = query("SELECT COUNT(*) AS total FROM data_sensor", one=True)["total"]
    labels = {"temperature": "Nhiệt độ", "humidity": "Độ ẩm", "light": "Ánh sáng"}
    data = [{"id": row["id"], "sensor": row["sensor_name"], "type": labels.get(row["sensor_type"], row["sensor_type"]),
             "value": float(row["value"]), "unit": row["unit"], "time": time_text(row["time"])} for row in rows]
    return jsonify(data=data, total=int(count), page=page, limit=limit)


@app.get("/api/history")
def history_list():
    page, limit = page_params()
    rows = query("SELECT history_id AS id, device_id, action, old_status, new_status, action_time AS time "
                 "FROM history ORDER BY history_id DESC LIMIT %s OFFSET %s", (limit, (page - 1) * limit))
    total = query("SELECT COUNT(*) AS total FROM history", one=True)["total"]
    data = []
    with pending_lock:
        pending_ids = {item["history_id"] for item in pending_commands.values() if "history_id" in item}
    for row in rows:
        action = row["action"]
        data.append({"id": row["id"], "device": f"LED{row['device_id']}",
                     "action": "BẬT" if row["new_status"] else "TẮT", "desc": action,
                     "status": "Đang chờ" if row["id"] in pending_ids else "Thành công",
                     "time": time_text(row["time"])})
    return jsonify(data=data, total=int(total), page=page, limit=limit)


@app.get("/api/devices")
def devices_list():
    rows = query("SELECT device_id AS id, device_name AS name, status FROM device WHERE device_type='LED' ORDER BY device_id")
    return jsonify([{"id": row["id"], "name": row["name"], "state": "ON" if row["status"] else "OFF",
                     "on": bool(row["status"])} for row in rows])


@app.post("/api/devices/<int:device_id>")
@require_auth
def set_device(device_id):
    body = request.get_json(silent=True) or {}
    desired = body.get("on")
    if device_id not in (1, 2) or not isinstance(desired, bool):
        return jsonify(error="Thiết bị hoặc trạng thái không hợp lệ"), 400
    if not mqtt_client.is_connected():
        return jsonify(error="MQTT broker chưa kết nối"), 503
    device = query("SELECT status FROM device WHERE device_id=%s AND device_type='LED'", (device_id,), one=True)
    if not device:
        return jsonify(error="Không tìm thấy thiết bị"), 404
    state = "ON" if desired else "OFF"
    with pending_lock:
        pending_commands.setdefault(device_id, []).append({"old": int(device["status"]), "user_id": None})
    result = mqtt_client.publish("device/control", f"{device_id}_{state}", qos=1)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        with pending_lock:
            commands = pending_commands.get(device_id, [])
            if commands:
                commands.pop()
            if not commands:
                pending_commands.pop(device_id, None)
        return jsonify(error="Không gửi được lệnh MQTT"), 503
    return jsonify(deviceId=device_id, state=state, status="PENDING"), 202


@app.errorhandler(HTTPException)
def handle_http_error(error):
    return jsonify(error=error.name, message=error.description), error.code


@app.errorhandler(Exception)
def handle_error(error):
    logger.exception("API request failed", exc_info=error)
    return jsonify(error="Lỗi máy chủ"), 500


if __name__ == "__main__":
    start_mqtt()
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "3000")), debug=False)
