-- Eliminar el trigger existente
DROP TRIGGER IF EXISTS station_update_trigger ON weather_logs;
DROP FUNCTION IF EXISTS update_station_info();

-- Crear una nueva función que no dependa del campo metadata
CREATE OR REPLACE FUNCTION update_station_info()
RETURNS TRIGGER AS $$
BEGIN
    -- Insertar o actualizar station information sin usar metadata
    INSERT INTO stations (id, status, updated_at)
    VALUES (
        NEW.station_id,
        NEW.status,
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        status = EXCLUDED.status,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para station updates
CREATE TRIGGER station_update_trigger
BEFORE INSERT ON weather_logs
FOR EACH ROW
EXECUTE FUNCTION update_station_info();
