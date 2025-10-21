-- Pandora Threat Intelligence Platform
-- Database Initialization Script
-- PostgreSQL 15+

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    daily_quota INTEGER DEFAULT 100,
    scans_used_today INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    quota_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT positive_quota CHECK (daily_quota >= 0),
    CONSTRAINT positive_scans_used CHECK (scans_used_today >= 0)
);

-- Scans Table
CREATE TABLE IF NOT EXISTS scans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scan_type VARCHAR(20) NOT NULL CHECK (scan_type IN ('ip', 'hash')),
    target VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    ip_address VARCHAR(45),
    user_agent TEXT,
    geoip_country VARCHAR(100),
    geoip_city VARCHAR(100),
    geoip_lat DECIMAL(10, 8),
    geoip_lon DECIMAL(11, 8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Scan Results Table
CREATE TABLE IF NOT EXISTS scan_results (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER UNIQUE NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    vt_response JSONB,
    is_malicious BOOLEAN,
    detection_count INTEGER DEFAULT 0,
    total_engines INTEGER DEFAULT 0,
    threat_names TEXT[],
    scan_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT positive_detection CHECK (detection_count >= 0),
    CONSTRAINT positive_engines CHECK (total_engines >= 0)
);

-- Scan Summary (for analytics)
CREATE TABLE IF NOT EXISTS scan_summary (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scan_date DATE NOT NULL,
    total_scans INTEGER DEFAULT 0,
    ip_scans INTEGER DEFAULT 0,
    hash_scans INTEGER DEFAULT 0,
    malicious_found INTEGER DEFAULT 0,
    UNIQUE(user_id, scan_date)
);

-- API Usage Logs
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_target ON scans(target);
CREATE INDEX IF NOT EXISTS idx_scans_scan_type ON scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON scan_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_is_malicious ON scan_results(is_malicious);

CREATE INDEX IF NOT EXISTS idx_scan_summary_user_id ON scan_summary(user_id);
CREATE INDEX IF NOT EXISTS idx_scan_summary_scan_date ON scan_summary(scan_date DESC);

CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at DESC);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_scans_target_trgm ON scans USING gin(target gin_trgm_ops);

-- Function to reset daily quota
CREATE OR REPLACE FUNCTION reset_daily_quota()
RETURNS void AS $$
BEGIN
    UPDATE users
    SET scans_used_today = 0,
        quota_reset_at = NOW()
    WHERE quota_reset_at < NOW() - INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql;

-- Function to update scan summary
CREATE OR REPLACE FUNCTION update_scan_summary()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO scan_summary (user_id, scan_date, total_scans, ip_scans, hash_scans, malicious_found)
    VALUES (
        NEW.user_id,
        DATE(NEW.created_at),
        1,
        CASE WHEN NEW.scan_type = 'ip' THEN 1 ELSE 0 END,
        CASE WHEN NEW.scan_type = 'hash' THEN 1 ELSE 0 END,
        0
    )
    ON CONFLICT (user_id, scan_date)
    DO UPDATE SET
        total_scans = scan_summary.total_scans + 1,
        ip_scans = scan_summary.ip_scans + CASE WHEN NEW.scan_type = 'ip' THEN 1 ELSE 0 END,
        hash_scans = scan_summary.hash_scans + CASE WHEN NEW.scan_type = 'hash' THEN 1 ELSE 0 END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for scan summary
DROP TRIGGER IF EXISTS trigger_update_scan_summary ON scans;
CREATE TRIGGER trigger_update_scan_summary
    AFTER INSERT ON scans
    FOR EACH ROW
    EXECUTE FUNCTION update_scan_summary();

-- Create default admin user (password: Admin123)
-- Password hash for "Admin123" using bcrypt
INSERT INTO users (email, username, password_hash, plan, daily_quota, is_active, is_admin, is_verified)
VALUES (
    'admin@pandora.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5kuOcMJ6SPMqK',
    'enterprise',
    10000,
    true,
    true,
    true
)
ON CONFLICT (email) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Database initialized successfully';
    RAISE NOTICE '✅ Default admin user: admin@pandora.com / Admin123';
    RAISE NOTICE '✅ Tables created: users, scans, scan_results, scan_summary, api_usage_logs';
END $$;

