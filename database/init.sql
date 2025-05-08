-- Create weather_logs table
CREATE TABLE IF NOT EXISTS weather_logs (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    temperature NUMERIC(5,2),
    humidity NUMERIC(5,2),
    pressure NUMERIC(7,2),
    wind_speed NUMERIC(5,2),
    wind_direction VARCHAR(10),
    precipitation NUMERIC(5,2),
    solar_radiation NUMERIC(7,2),
    battery_level NUMERIC(5,2),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT temperature_range CHECK (temperature IS NULL OR (temperature >= -80 AND temperature <= 60)),
    CONSTRAINT humidity_range CHECK (humidity IS NULL OR (humidity >= 0 AND humidity <= 100)),
    CONSTRAINT pressure_range CHECK (pressure IS NULL OR (pressure >= 800 AND pressure <= 1200)),
    CONSTRAINT wind_speed_range CHECK (wind_speed IS NULL OR (wind_speed >= 0 AND wind_speed <= 200)),
    CONSTRAINT precipitation_range CHECK (precipitation IS NULL OR (precipitation >= 0 AND precipitation <= 500)),
    CONSTRAINT battery_level_range CHECK (battery_level IS NULL OR (battery_level >= 0 AND battery_level <= 100))
);

-- Create index for faster queries
CREATE INDEX idx_weather_logs_station_id ON weather_logs(station_id);
CREATE INDEX idx_weather_logs_timestamp ON weather_logs(timestamp);
CREATE INDEX idx_weather_logs_status ON weather_logs(status);

-- Create view for latest readings per station
CREATE OR REPLACE VIEW latest_station_readings AS
SELECT DISTINCT ON (station_id)
    id,
    station_id,
    timestamp,
    temperature,
    humidity,
    pressure,
    wind_speed,
    wind_direction,
    precipitation,
    solar_radiation,
    battery_level,
    status
FROM weather_logs
ORDER BY station_id, timestamp DESC;

-- Create alerts table
CREATE TABLE IF NOT EXISTS weather_alerts (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    alert_message TEXT NOT NULL,
    alert_value NUMERIC,
    threshold_value NUMERIC,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'NEW',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create index for alerts
CREATE INDEX idx_weather_alerts_station_id ON weather_alerts(station_id);
CREATE INDEX idx_weather_alerts_status ON weather_alerts(status);
CREATE INDEX idx_weather_alerts_timestamp ON weather_alerts(timestamp);

-- Create alert configurations table
CREATE TABLE IF NOT EXISTS alert_configurations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    operator VARCHAR(10) NOT NULL,
    threshold_value NUMERIC NOT NULL,
    severity VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_alert_config UNIQUE (field_name, operator, threshold_value)
);

-- Insert default alert configurations
INSERT INTO alert_configurations (name, field_name, operator, threshold_value, severity)
VALUES 
    ('High Temperature', 'temperature', '>', 35, 'WARNING'),
    ('Low Temperature', 'temperature', '<', -10, 'WARNING'),
    ('High Humidity', 'humidity', '>', 90, 'WARNING'),
    ('Low Battery', 'battery_level', '<', 20, 'CRITICAL'),
    ('Extreme Wind', 'wind_speed', '>', 50, 'CRITICAL'),
    ('Heavy Precipitation', 'precipitation', '>', 25, 'WARNING');

-- Create stations table
CREATE TABLE IF NOT EXISTS stations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    elevation NUMERIC(7,2),
    type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create function to update stations table when new data arrives
CREATE OR REPLACE FUNCTION update_station_info()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update station information
    INSERT INTO stations (id, latitude, longitude, elevation, status, updated_at)
    VALUES (
        NEW.station_id,
        (NEW.metadata->>'latitude')::NUMERIC,
        (NEW.metadata->>'longitude')::NUMERIC,
        (NEW.metadata->>'elevation')::NUMERIC,
        NEW.status,
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        elevation = EXCLUDED.elevation,
        status = EXCLUDED.status,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for station updates
CREATE TRIGGER station_update_trigger
BEFORE INSERT ON weather_logs
FOR EACH ROW
EXECUTE FUNCTION update_station_info();
