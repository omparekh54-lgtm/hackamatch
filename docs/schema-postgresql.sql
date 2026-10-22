BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 69bc3a790056

CREATE TABLE matching_windows (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    active_slot INTEGER GENERATED ALWAYS AS (CASE WHEN status IN ('scheduled','open','closing','matching','review','failed') THEN 1 ELSE NULL END), 
    opens TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    closes TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    policy JSON NOT NULL, 
    config JSON NOT NULL, 
    frozen_at TIMESTAMP WITHOUT TIME ZONE, 
    published_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    CHECK (closes > opens), 
    UNIQUE (active_slot)
);

CREATE INDEX ix_matching_windows_closes ON matching_windows (closes);

CREATE TABLE rate_buckets (
    key VARCHAR(64) NOT NULL, 
    count INTEGER NOT NULL, 
    expires TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (key)
);

CREATE TABLE settings (
    key VARCHAR(80) NOT NULL, 
    value JSON NOT NULL, 
    PRIMARY KEY (key)
);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    password VARCHAR(300) NOT NULL, 
    verified BOOLEAN NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE audit_logs (
    id SERIAL NOT NULL, 
    actor INTEGER, 
    action VARCHAR(80) NOT NULL, 
    target VARCHAR(100) NOT NULL, 
    reason VARCHAR(500), 
    details JSON NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor) REFERENCES users (id)
);

CREATE TABLE luma_imports (
    id SERIAL NOT NULL, 
    digest VARCHAR(64) NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    actor INTEGER, 
    summary JSON NOT NULL, 
    active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor) REFERENCES users (id), 
    UNIQUE (digest)
);

CREATE TABLE mail_outbox (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    body VARCHAR(3000) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    attempts INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE matching_jobs (
    id SERIAL NOT NULL, 
    window_id INTEGER NOT NULL, 
    key VARCHAR(100) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    attempts INTEGER NOT NULL, 
    error VARCHAR(200), 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(window_id) REFERENCES matching_windows (id), 
    UNIQUE (key), 
    UNIQUE (window_id)
);

CREATE TABLE participant_profiles (
    user_id INTEGER NOT NULL, 
    excluded BOOLEAN NOT NULL, 
    availability_override VARCHAR(20), 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (user_id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE registrations (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    window_id INTEGER NOT NULL, 
    state VARCHAR(30) NOT NULL, 
    eligibility JSON NOT NULL, 
    joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    FOREIGN KEY(window_id) REFERENCES matching_windows (id), 
    UNIQUE (user_id, window_id)
);

CREATE TABLE teams (
    id SERIAL NOT NULL, 
    window_id INTEGER NOT NULL, 
    number INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    score FLOAT NOT NULL, 
    breakdown JSON NOT NULL, 
    algorithm VARCHAR(30) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(window_id) REFERENCES matching_windows (id), 
    UNIQUE (window_id, number)
);

CREATE TABLE tokens (
    digest VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    kind VARCHAR(20) NOT NULL, 
    expires TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (digest), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE dataset_snapshots (
    id SERIAL NOT NULL, 
    window_id INTEGER NOT NULL, 
    import_id INTEGER, 
    pool JSON NOT NULL, 
    policy JSON NOT NULL, 
    config JSON NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(import_id) REFERENCES luma_imports (id), 
    FOREIGN KEY(window_id) REFERENCES matching_windows (id), 
    UNIQUE (window_id)
);

CREATE TABLE luma_attendees (
    id SERIAL NOT NULL, 
    guest_id VARCHAR(200) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    approval VARCHAR(30) NOT NULL, 
    active BOOLEAN NOT NULL, 
    import_id INTEGER NOT NULL, 
    raw JSON NOT NULL, 
    normalized JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(import_id) REFERENCES luma_imports (id), 
    UNIQUE (guest_id)
);

CREATE INDEX ix_luma_attendees_email ON luma_attendees (email);

CREATE TABLE team_members (
    id SERIAL NOT NULL, 
    team_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    window_id INTEGER NOT NULL, 
    assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(team_id) REFERENCES teams (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    FOREIGN KEY(window_id) REFERENCES matching_windows (id), 
    UNIQUE (window_id, user_id)
);

INSERT INTO alembic_version (version_num) VALUES ('69bc3a790056') RETURNING alembic_version.version_num;

-- Running upgrade 69bc3a790056 -> 671185b85bc1

CREATE TABLE luma_import_records (
    id SERIAL NOT NULL, 
    import_id INTEGER NOT NULL, 
    guest_id VARCHAR(200) NOT NULL, 
    raw JSON NOT NULL, 
    normalized JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(import_id) REFERENCES luma_imports (id), 
    UNIQUE (import_id, guest_id)
);

UPDATE alembic_version SET version_num='671185b85bc1' WHERE alembic_version.version_num = '69bc3a790056';

COMMIT;

