CREATE TABLE sensor_data (
  id INT AUTO_INCREMENT PRIMARY KEY,
  temp FLOAT,
  humidity FLOAT,
  light INT,
  motion INT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
