# Database Setup

This directory contains database schema and migration files for the ETF Overlap application.

## Initial Setup

### 1. Create the database tables

**For new databases**, run the schema file:

```bash
psql $DATABASE_URL -f db/schema.sql
```

**For existing databases**, run the migration to add profile fields:

```bash
psql $DATABASE_URL -f db/migrations/001_add_etf_profile_fields.sql
```

Or if using `SBF_DB_URL`:

```bash
psql $SBF_DB_URL -f db/schema.sql
# or for existing databases:
psql $SBF_DB_URL -f db/migrations/001_add_etf_profile_fields.sql
```

### 2. Verify the tables were created

```bash
psql $DATABASE_URL -c "\dt"
```

You should see:

- `etfs` - Stores ETF metadata and last update timestamps
- `etf_holdings` - Stores individual stock holdings for each ETF

## Schema Overview

### `etfs` table

Stores ETF metadata, profile information, and tracks when holdings were last updated.

| Column                  | Type         | Description                                   |
| ----------------------- | ------------ | --------------------------------------------- |
| id                      | SERIAL       | Primary key                                   |
| symbol                  | VARCHAR(10)  | ETF ticker symbol (unique)                    |
| name                    | VARCHAR(255) | ETF name                                      |
| **Profile Information** |              |                                               |
| issuer                  | VARCHAR(255) | ETF issuer company                            |
| brand                   | VARCHAR(255) | ETF brand name                                |
| structure               | VARCHAR(50)  | Fund structure (e.g., UIT, ETP)               |
| expense_ratio           | DECIMAL(5,4) | Annual expense ratio (e.g., 0.0020 for 0.20%) |
| inception_date          | DATE         | Date the ETF was launched                     |
| index_tracked           | VARCHAR(255) | Name of tracked index                         |
| home_page               | TEXT         | ETF home page URL                             |
| **Classification**      |              |                                               |
| category                | VARCHAR(255) | ETFdb category                                |
| asset_class             | VARCHAR(100) | Asset class (e.g., Equity)                    |
| asset_class_size        | VARCHAR(50)  | Size classification (e.g., Large-Cap)         |
| asset_class_style       | VARCHAR(50)  | Style (e.g., Growth, Value)                   |
| sector_general          | VARCHAR(100) | General sector                                |
| sector_specific         | VARCHAR(100) | Specific sector                               |
| region_general          | VARCHAR(100) | General region                                |
| region_specific         | VARCHAR(100) | Specific region/country                       |
| **Trading Data**        |              |                                               |
| aum                     | BIGINT       | Assets Under Management (dollars)             |
| shares_outstanding      | BIGINT       | Total shares outstanding                      |
| **Metadata**            |              |                                               |
| last_updated            | TIMESTAMP    | Last time data was updated                    |
| created_at              | TIMESTAMP    | When the ETF was first added                  |

### `etf_holdings` table

Stores current/latest holdings for each ETF (cache).

| Column     | Type          | Description                      |
| ---------- | ------------- | -------------------------------- |
| id         | SERIAL        | Primary key                      |
| etf_id     | INTEGER       | Foreign key to etfs table        |
| symbol     | VARCHAR(10)   | Stock ticker symbol              |
| name       | VARCHAR(255)  | Company/stock name               |
| weight     | DECIMAL(10,4) | Percentage of total assets       |
| shares     | BIGINT        | Number of shares held (optional) |
| created_at | TIMESTAMP     | When the holding was added       |

### `etf_holdings_snapshots` table

Stores historical snapshots of ETF holdings for tracking changes over time.

| Column        | Type          | Description                      |
| ------------- | ------------- | -------------------------------- |
| id            | BIGSERIAL     | Primary key                      |
| snapshot_date | DATE          | Date of the snapshot             |
| etf_id        | INTEGER       | Foreign key to etfs table        |
| symbol        | VARCHAR(10)   | Stock ticker symbol              |
| name          | VARCHAR(255)  | Company/stock name               |
| weight        | DECIMAL(10,4) | Percentage of total assets       |
| shares        | BIGINT        | Number of shares held (optional) |
| created_at    | TIMESTAMP     | When the snapshot was created    |

## Cache Invalidation

The cache automatically expires based on the `CACHE_MAX_AGE_HOURS` environment variable (default: 24 hours). When holdings are older than this threshold, the API will re-scrape the data.

## Maintenance

### Clear cache for a specific ETF

```sql
DELETE FROM etf_holdings WHERE etf_id = (SELECT id FROM etfs WHERE symbol = 'QQQ');
DELETE FROM etfs WHERE symbol = 'QQQ';
```

### View cached ETFs

```sql
SELECT symbol, name, last_updated,
       EXTRACT(EPOCH FROM (NOW() - last_updated))/3600 as hours_old
FROM etfs
ORDER BY last_updated DESC;
```

### View holdings for an ETF

```sql
SELECT h.symbol, h.name, h.weight
FROM etf_holdings h
JOIN etfs e ON e.id = h.etf_id
WHERE e.symbol = 'QQQ'
ORDER BY h.weight DESC
LIMIT 10;
```

### Clean up old cache entries

```sql
-- Delete ETFs not updated in the last 30 days
DELETE FROM etfs WHERE last_updated < NOW() - INTERVAL '30 days';
```

## Historical Snapshots

### Save a snapshot (via code)

```typescript
import { saveSnapshot } from "@/lib/db";

// Save today's holdings as a snapshot
await saveSnapshot("QQQ", holdings);

// Save with specific date
await saveSnapshot("QQQ", holdings, new Date("2024-01-15"));
```

### View snapshots for an ETF

```sql
-- Get all snapshots for QQQ
SELECT s.snapshot_date, COUNT(*) as holdings_count,
       SUM(s.weight) as total_weight
FROM etf_holdings_snapshots s
JOIN etfs e ON e.id = s.etf_id
WHERE e.symbol = 'QQQ'
GROUP BY s.snapshot_date
ORDER BY s.snapshot_date DESC;

-- Get specific snapshot
SELECT symbol, name, weight
FROM etf_holdings_snapshots s
JOIN etfs e ON e.id = s.etf_id
WHERE e.symbol = 'QQQ'
AND s.snapshot_date = '2024-01-15'
ORDER BY weight DESC
LIMIT 10;
```

### Compare holdings over time

```sql
-- Compare top holdings between two dates
WITH current_holdings AS (
  SELECT symbol, weight
  FROM etf_holdings_snapshots s
  JOIN etfs e ON e.id = s.etf_id
  WHERE e.symbol = 'QQQ'
  AND s.snapshot_date = '2024-01-15'
),
previous_holdings AS (
  SELECT symbol, weight
  FROM etf_holdings_snapshots s
  JOIN etfs e ON e.id = s.etf_id
  WHERE e.symbol = 'QQQ'
  AND s.snapshot_date = '2024-01-01'
)
SELECT
  COALESCE(c.symbol, p.symbol) as symbol,
  p.weight as previous_weight,
  c.weight as current_weight,
  c.weight - p.weight as weight_change
FROM current_holdings c
FULL OUTER JOIN previous_holdings p ON c.symbol = p.symbol
ORDER BY ABS(c.weight - p.weight) DESC NULLS LAST
LIMIT 20;
```

### Archive old snapshots

```sql
-- Delete snapshots older than 1 year
DELETE FROM etf_holdings_snapshots
WHERE snapshot_date < CURRENT_DATE - INTERVAL '1 year';

-- Or export to CSV first
COPY (
  SELECT * FROM etf_holdings_snapshots
  WHERE snapshot_date < CURRENT_DATE - INTERVAL '1 year'
) TO '/tmp/old_snapshots.csv' WITH CSV HEADER;
```
