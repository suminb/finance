-- Migration: Add ETF profile fields to etfs table
-- Run this on existing databases to add the new columns

-- Add profile fields
ALTER TABLE etfs 
ADD COLUMN IF NOT EXISTS issuer VARCHAR(255),
ADD COLUMN IF NOT EXISTS brand VARCHAR(255),
ADD COLUMN IF NOT EXISTS structure VARCHAR(50),
ADD COLUMN IF NOT EXISTS expense_ratio DECIMAL(5, 4),
ADD COLUMN IF NOT EXISTS inception_date DATE,
ADD COLUMN IF NOT EXISTS index_tracked VARCHAR(255),
ADD COLUMN IF NOT EXISTS home_page TEXT;

-- Add classification fields
ALTER TABLE etfs
ADD COLUMN IF NOT EXISTS category VARCHAR(255),
ADD COLUMN IF NOT EXISTS asset_class VARCHAR(100),
ADD COLUMN IF NOT EXISTS asset_class_size VARCHAR(50),
ADD COLUMN IF NOT EXISTS asset_class_style VARCHAR(50),
ADD COLUMN IF NOT EXISTS sector_general VARCHAR(100),
ADD COLUMN IF NOT EXISTS sector_specific VARCHAR(100),
ADD COLUMN IF NOT EXISTS region_general VARCHAR(100),
ADD COLUMN IF NOT EXISTS region_specific VARCHAR(100);

-- Add trading data fields
ALTER TABLE etfs
ADD COLUMN IF NOT EXISTS aum BIGINT,
ADD COLUMN IF NOT EXISTS shares_outstanding BIGINT;

-- Update comments
COMMENT ON TABLE etfs IS 'Stores ETF metadata, profile information, and last update timestamp for cache invalidation';
COMMENT ON COLUMN etfs.expense_ratio IS 'Annual expense ratio as a decimal (e.g., 0.0020 for 0.20%)';
COMMENT ON COLUMN etfs.aum IS 'Assets Under Management in dollars';

