-- ETF Holdings Database Schema

-- Table to store ETF metadata
CREATE TABLE IF NOT EXISTS etfs (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    
    -- Profile Information
    issuer VARCHAR(255),
    brand VARCHAR(255),
    structure VARCHAR(50),
    expense_ratio DECIMAL(5, 4),  -- e.g., 0.0020 for 0.20%
    inception_date DATE,
    index_tracked VARCHAR(255),
    home_page TEXT,
    
    -- Classification
    category VARCHAR(255),
    asset_class VARCHAR(100),
    asset_class_size VARCHAR(50),
    asset_class_style VARCHAR(50),
    sector_general VARCHAR(100),
    sector_specific VARCHAR(100),
    region_general VARCHAR(100),
    region_specific VARCHAR(100),
    
    -- Trading Data
    aum BIGINT,  -- Assets Under Management in dollars
    shares_outstanding BIGINT,
    
    -- Metadata
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Table to store individual holdings
CREATE TABLE IF NOT EXISTS etf_holdings (
    id SERIAL PRIMARY KEY,
    etf_id INTEGER NOT NULL REFERENCES etfs(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(255) NOT NULL,
    weight DECIMAL(10, 4) NOT NULL,
    shares BIGINT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(etf_id, symbol)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_etfs_symbol ON etfs(symbol);
CREATE INDEX IF NOT EXISTS idx_etfs_last_updated ON etfs(last_updated);
CREATE INDEX IF NOT EXISTS idx_holdings_etf_id ON etf_holdings(etf_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON etf_holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_holdings_weight ON etf_holdings(weight DESC);

-- Table to store historical snapshots of holdings
CREATE TABLE IF NOT EXISTS etf_holdings_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    etf_id INTEGER NOT NULL REFERENCES etfs(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(255) NOT NULL,
    weight DECIMAL(10, 4) NOT NULL,
    shares BIGINT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, etf_id, symbol)
);

-- Indexes for snapshots table
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON etf_holdings_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_etf_date ON etf_holdings_snapshots(etf_id, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON etf_holdings_snapshots(symbol);

-- Comments
COMMENT ON TABLE etfs IS 'Stores ETF metadata, profile information, and last update timestamp for cache invalidation';
COMMENT ON TABLE etf_holdings IS 'Stores current/latest holdings for each ETF (cache)';
COMMENT ON TABLE etf_holdings_snapshots IS 'Stores historical snapshots of ETF holdings for tracking changes over time';
COMMENT ON COLUMN etfs.expense_ratio IS 'Annual expense ratio as a decimal (e.g., 0.0020 for 0.20%)';
COMMENT ON COLUMN etfs.aum IS 'Assets Under Management in dollars';
COMMENT ON COLUMN etf_holdings.weight IS 'Percentage of total assets (e.g., 5.5 for 5.5%)';
COMMENT ON COLUMN etf_holdings_snapshots.weight IS 'Percentage of total assets (e.g., 5.5 for 5.5%)';
COMMENT ON COLUMN etf_holdings_snapshots.snapshot_date IS 'Date of the snapshot (typically the date holdings were scraped)';

