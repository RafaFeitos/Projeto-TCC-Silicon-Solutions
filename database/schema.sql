CREATE TABLE machines (
    id INTEGER PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    machine_type VARCHAR(80) NOT NULL
);

CREATE TABLE inferences (
    id INTEGER PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id),
    timestamp TIMESTAMP NOT NULL,
    predicted_class VARCHAR(80) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    model_version VARCHAR(80) NOT NULL,
    source VARCHAR(80) NOT NULL,
    signal_value DOUBLE PRECISION NOT NULL,
    rms DOUBLE PRECISION NOT NULL,
    state VARCHAR(40) NOT NULL,
    alert VARCHAR(160),
    severity VARCHAR(30)
);

CREATE INDEX idx_inferences_machine_timestamp ON inferences(machine_id, timestamp);

INSERT INTO machines (id, name, machine_type)
VALUES (1, 'Maquina 01', 'FAN')
ON CONFLICT (id) DO NOTHING;
