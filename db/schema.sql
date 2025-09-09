-- SQLite schema for HouseKeyper
CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  class TEXT,
  type TEXT,
  model TEXT,
  location TEXT,
  last_seen TEXT
);
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT,
  ts TEXT,
  key TEXT,
  value TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT,
  level TEXT,
  code TEXT,
  message TEXT,
  device_id TEXT,
  room TEXT
);
CREATE INDEX IF NOT EXISTS idx_readings_device_ts ON readings(device_id, ts);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts);
