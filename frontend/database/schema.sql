CREATE DATABASE IF NOT EXISTS smart_home_iot
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_home_iot;

CREATE TABLE IF NOT EXISTS `user` (
  user_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NULL UNIQUE,
  role VARCHAR(20) NOT NULL DEFAULT 'user'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS device (
  device_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_name VARCHAR(100) NOT NULL,
  device_type VARCHAR(50) NOT NULL,
  status TINYINT(1) NOT NULL DEFAULT 0,
  location VARCHAR(100) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sensor (
  sensor_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_id INT NOT NULL,
  sensor_name VARCHAR(100) NOT NULL,
  sensor_type VARCHAR(50) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  status TINYINT(1) NOT NULL DEFAULT 1,
  INDEX idx_sensor_device (device_id),
  CONSTRAINT fk_sensor_device FOREIGN KEY (device_id)
    REFERENCES device(device_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS data_sensor (
  data_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  sensor_id INT NOT NULL,
  value DECIMAL(10,2) NOT NULL,
  recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_data_sensor_time (sensor_id, recorded_at),
  CONSTRAINT fk_data_sensor_sensor FOREIGN KEY (sensor_id)
    REFERENCES sensor(sensor_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS history (
  history_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  device_id INT NOT NULL,
  action VARCHAR(50) NOT NULL,
  old_status TINYINT(1) NOT NULL,
  new_status TINYINT(1) NOT NULL,
  action_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_history_time (action_time),
  INDEX idx_history_user (user_id),
  CONSTRAINT fk_history_user FOREIGN KEY (user_id)
    REFERENCES `user`(user_id) ON UPDATE CASCADE ON DELETE SET NULL
  -- Deliberately no foreign key from history.device_id to device.device_id.
) ENGINE=InnoDB;

INSERT INTO device (device_id, device_name, device_type, status, location)
SELECT 1, 'LED1', 'LED', 0, 'Phòng khách'
WHERE NOT EXISTS (SELECT 1 FROM device WHERE device_id = 1);
INSERT INTO device (device_id, device_name, device_type, status, location)
SELECT 2, 'LED2', 'LED', 0, 'Phòng ngủ'
WHERE NOT EXISTS (SELECT 1 FROM device WHERE device_id = 2);

INSERT INTO sensor (device_id, sensor_name, sensor_type, unit, status)
SELECT 1, 'DHT11 Nhiệt độ', 'temperature', '°C', 1
WHERE NOT EXISTS (SELECT 1 FROM sensor WHERE sensor_type = 'temperature');
INSERT INTO sensor (device_id, sensor_name, sensor_type, unit, status)
SELECT 1, 'DHT11 Độ ẩm', 'humidity', '%', 1
WHERE NOT EXISTS (SELECT 1 FROM sensor WHERE sensor_type = 'humidity');
INSERT INTO sensor (device_id, sensor_name, sensor_type, unit, status)
SELECT 1, 'LDR Ánh sáng', 'light', 'ADC', 1
WHERE NOT EXISTS (SELECT 1 FROM sensor WHERE sensor_type = 'light');
