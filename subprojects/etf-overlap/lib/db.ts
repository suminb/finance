import { Pool } from "pg";

// Create a connection pool
let pool: Pool | null = null;

export function getPool(): Pool {
  if (!pool) {
    const databaseUrl = process.env.DATABASE_URL || process.env.SBF_DB_URL;

    if (!databaseUrl) {
      throw new Error(
        "DATABASE_URL or SBF_DB_URL environment variable is not set"
      );
    }

    pool = new Pool({
      connectionString: databaseUrl,
      // Connection pool settings
      max: 20, // Maximum number of clients in the pool
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    });

    // Error handling
    pool.on("error", (err) => {
      console.error("Unexpected error on idle client", err);
    });
  }

  return pool;
}

export interface ETF {
  id: number;
  symbol: string;
  name: string | null;
  issuer: string | null;
  brand: string | null;
  structure: string | null;
  expense_ratio: number | null;
  inception_date: Date | null;
  index_tracked: string | null;
  home_page: string | null;
  category: string | null;
  asset_class: string | null;
  asset_class_size: string | null;
  asset_class_style: string | null;
  sector_general: string | null;
  sector_specific: string | null;
  region_general: string | null;
  region_specific: string | null;
  aum: number | null;
  shares_outstanding: number | null;
  last_updated: Date;
  created_at: Date;
}

export interface ETFProfile {
  name?: string;
  issuer?: string;
  brand?: string;
  structure?: string;
  expense_ratio?: number;
  inception_date?: Date;
  index_tracked?: string;
  home_page?: string;
  category?: string;
  asset_class?: string;
  asset_class_size?: string;
  asset_class_style?: string;
  sector_general?: string;
  sector_specific?: string;
  region_general?: string;
  region_specific?: string;
  aum?: number;
  shares_outstanding?: number;
}

export interface ETFHolding {
  id: number;
  etf_id: number;
  symbol: string;
  name: string;
  weight: number;
  shares: number | null;
  created_at: Date;
}

export interface ETFHoldingInsert {
  symbol: string;
  name: string;
  weight: number;
  shares?: number;
}

/**
 * Get cached ETF holdings from database
 * @param ticker ETF symbol
 * @param maxAgeHours Maximum age of cache in hours (default: 24)
 * @returns Holdings array or null if cache miss or expired
 */
export async function getCachedHoldings(
  ticker: string,
  maxAgeHours: number = 24
): Promise<ETFHoldingInsert[] | null> {
  const pool = getPool();

  try {
    // Check if we have recent data for this ETF
    const etfResult = await pool.query<ETF>(
      `SELECT id, symbol, name, last_updated, created_at
       FROM etfs
       WHERE UPPER(symbol) = UPPER($1)
       AND last_updated > NOW() - INTERVAL '${maxAgeHours} hours'`,
      [ticker]
    );

    if (etfResult.rows.length === 0) {
      return null; // Cache miss or expired
    }

    const etf = etfResult.rows[0];

    // Fetch holdings
    const holdingsResult = await pool.query<ETFHolding>(
      `SELECT id, etf_id, symbol, name, weight, shares, created_at
       FROM etf_holdings
       WHERE etf_id = $1
       ORDER BY weight DESC`,
      [etf.id]
    );

    return holdingsResult.rows.map((row) => ({
      symbol: row.symbol,
      name: row.name,
      weight: Number(row.weight),
      shares: row.shares || undefined,
    }));
  } catch (error) {
    console.error("Error fetching cached holdings:", error);
    return null;
  }
}

/**
 * Save ETF holdings to database
 * @param ticker ETF symbol
 * @param holdings Array of holdings to save
 * @param profile Optional ETF profile information
 */
export async function saveHoldings(
  ticker: string,
  holdings: ETFHoldingInsert[],
  profile?: ETFProfile
): Promise<void> {
  const pool = getPool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    // Insert or update ETF with profile data
    let etfResult;
    if (profile && Object.keys(profile).length > 0) {
      const fields: string[] = ["symbol"];
      const values: any[] = [ticker.toUpperCase()];
      let paramCount = 1;

      const updates: string[] = ["last_updated = NOW()"];

      if (profile.name) {
        paramCount++;
        fields.push("name");
        values.push(profile.name);
        updates.push(`name = $${paramCount}`);
      }
      if (profile.issuer) {
        paramCount++;
        fields.push("issuer");
        values.push(profile.issuer);
        updates.push(`issuer = $${paramCount}`);
      }
      if (profile.brand) {
        paramCount++;
        fields.push("brand");
        values.push(profile.brand);
        updates.push(`brand = $${paramCount}`);
      }
      if (profile.structure) {
        paramCount++;
        fields.push("structure");
        values.push(profile.structure);
        updates.push(`structure = $${paramCount}`);
      }
      if (profile.expense_ratio !== undefined) {
        paramCount++;
        fields.push("expense_ratio");
        values.push(profile.expense_ratio);
        updates.push(`expense_ratio = $${paramCount}`);
      }
      if (profile.inception_date) {
        paramCount++;
        fields.push("inception_date");
        values.push(profile.inception_date);
        updates.push(`inception_date = $${paramCount}`);
      }
      if (profile.index_tracked) {
        paramCount++;
        fields.push("index_tracked");
        values.push(profile.index_tracked);
        updates.push(`index_tracked = $${paramCount}`);
      }
      if (profile.home_page) {
        paramCount++;
        fields.push("home_page");
        values.push(profile.home_page);
        updates.push(`home_page = $${paramCount}`);
      }
      if (profile.category) {
        paramCount++;
        fields.push("category");
        values.push(profile.category);
        updates.push(`category = $${paramCount}`);
      }
      if (profile.asset_class) {
        paramCount++;
        fields.push("asset_class");
        values.push(profile.asset_class);
        updates.push(`asset_class = $${paramCount}`);
      }
      if (profile.asset_class_size) {
        paramCount++;
        fields.push("asset_class_size");
        values.push(profile.asset_class_size);
        updates.push(`asset_class_size = $${paramCount}`);
      }
      if (profile.asset_class_style) {
        paramCount++;
        fields.push("asset_class_style");
        values.push(profile.asset_class_style);
        updates.push(`asset_class_style = $${paramCount}`);
      }
      if (profile.sector_general) {
        paramCount++;
        fields.push("sector_general");
        values.push(profile.sector_general);
        updates.push(`sector_general = $${paramCount}`);
      }
      if (profile.sector_specific) {
        paramCount++;
        fields.push("sector_specific");
        values.push(profile.sector_specific);
        updates.push(`sector_specific = $${paramCount}`);
      }
      if (profile.region_general) {
        paramCount++;
        fields.push("region_general");
        values.push(profile.region_general);
        updates.push(`region_general = $${paramCount}`);
      }
      if (profile.region_specific) {
        paramCount++;
        fields.push("region_specific");
        values.push(profile.region_specific);
        updates.push(`region_specific = $${paramCount}`);
      }
      if (profile.aum !== undefined) {
        paramCount++;
        fields.push("aum");
        values.push(profile.aum);
        updates.push(`aum = $${paramCount}`);
      }
      if (profile.shares_outstanding !== undefined) {
        paramCount++;
        fields.push("shares_outstanding");
        values.push(profile.shares_outstanding);
        updates.push(`shares_outstanding = $${paramCount}`);
      }

      const placeholders = fields.map((_, i) => `$${i + 1}`).join(", ");
      etfResult = await client.query<ETF>(
        `INSERT INTO etfs (${fields.join(", ")}, last_updated)
         VALUES (${placeholders}, NOW())
         ON CONFLICT (symbol)
         DO UPDATE SET ${updates.join(", ")}
         RETURNING id`,
        values
      );
    } else {
      // No profile data, just update timestamp
      etfResult = await client.query<ETF>(
        `INSERT INTO etfs (symbol, last_updated)
         VALUES (UPPER($1), NOW())
         ON CONFLICT (symbol)
         DO UPDATE SET last_updated = NOW()
         RETURNING id`,
        [ticker]
      );
    }

    const etfId = etfResult.rows[0].id;

    // Delete old holdings
    await client.query("DELETE FROM etf_holdings WHERE etf_id = $1", [etfId]);

    // Insert new holdings
    if (holdings.length > 0) {
      const values = holdings
        .map((holding, idx) => {
          const offset = idx * 5; // 5 parameters per holding (etf_id, symbol, name, weight, shares)
          return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5})`;
        })
        .join(",");

      const params: any[] = [];
      holdings.forEach((holding) => {
        params.push(
          etfId,
          holding.symbol,
          holding.name,
          holding.weight,
          holding.shares !== undefined ? holding.shares : null
        );
      });

      await client.query(
        `INSERT INTO etf_holdings (etf_id, symbol, name, weight, shares)
         VALUES ${values}`,
        params
      );
    }

    await client.query("COMMIT");
    console.log(`Saved ${holdings.length} holdings for ${ticker}`);
  } catch (error) {
    await client.query("ROLLBACK");
    console.error("Error saving holdings:", error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Save a snapshot of ETF holdings for historical tracking
 * @param ticker ETF symbol
 * @param holdings Array of holdings to snapshot
 * @param snapshotDate Date of the snapshot (defaults to today)
 */
export async function saveSnapshot(
  ticker: string,
  holdings: ETFHoldingInsert[],
  snapshotDate: Date = new Date()
): Promise<void> {
  const pool = getPool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    // Get ETF ID
    const etfResult = await client.query<ETF>(
      "SELECT id FROM etfs WHERE UPPER(symbol) = UPPER($1)",
      [ticker]
    );

    if (etfResult.rows.length === 0) {
      throw new Error(
        `ETF ${ticker} not found in database. Save holdings first.`
      );
    }

    const etfId = etfResult.rows[0].id;
    const dateStr = snapshotDate.toISOString().split("T")[0]; // YYYY-MM-DD

    // Check if snapshot already exists for this date
    const existingSnapshot = await client.query(
      "SELECT COUNT(*) FROM etf_holdings_snapshots WHERE etf_id = $1 AND snapshot_date = $2",
      [etfId, dateStr]
    );

    if (parseInt(existingSnapshot.rows[0].count) > 0) {
      console.log(`Snapshot already exists for ${ticker} on ${dateStr}`);
      await client.query("ROLLBACK");
      return;
    }

    // Insert snapshot
    if (holdings.length > 0) {
      const values = holdings
        .map((holding, idx) => {
          const offset = idx * 6;
          return `($1, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6})`;
        })
        .join(",");

      const params = [dateStr];
      holdings.forEach((holding) => {
        params.push(
          etfId,
          holding.symbol,
          holding.name,
          holding.weight,
          holding.shares || null
        );
      });

      await client.query(
        `INSERT INTO etf_holdings_snapshots (snapshot_date, etf_id, symbol, name, weight, shares)
         VALUES ${values}`,
        params
      );
    }

    await client.query("COMMIT");
    console.log(
      `Saved snapshot of ${holdings.length} holdings for ${ticker} on ${dateStr}`
    );
  } catch (error) {
    await client.query("ROLLBACK");
    console.error("Error saving snapshot:", error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Get historical snapshots for an ETF
 * @param ticker ETF symbol
 * @param startDate Optional start date
 * @param endDate Optional end date
 * @returns Array of snapshots grouped by date
 */
export async function getSnapshots(
  ticker: string,
  startDate?: Date,
  endDate?: Date
): Promise<{ date: string; holdings: ETFHoldingInsert[] }[]> {
  const pool = getPool();

  try {
    let query = `
      SELECT s.snapshot_date, s.symbol, s.name, s.weight, s.shares
      FROM etf_holdings_snapshots s
      JOIN etfs e ON e.id = s.etf_id
      WHERE UPPER(e.symbol) = UPPER($1)
    `;
    const params: any[] = [ticker];

    if (startDate) {
      params.push(startDate.toISOString().split("T")[0]);
      query += ` AND s.snapshot_date >= $${params.length}`;
    }

    if (endDate) {
      params.push(endDate.toISOString().split("T")[0]);
      query += ` AND s.snapshot_date <= $${params.length}`;
    }

    query += " ORDER BY s.snapshot_date DESC, s.weight DESC";

    const result = await pool.query(query, params);

    // Group by date
    const snapshotMap = new Map<string, ETFHoldingInsert[]>();

    result.rows.forEach((row) => {
      const date = row.snapshot_date;
      if (!snapshotMap.has(date)) {
        snapshotMap.set(date, []);
      }
      snapshotMap.get(date)!.push({
        symbol: row.symbol,
        name: row.name,
        weight: Number(row.weight),
        shares: row.shares || undefined,
      });
    });

    return Array.from(snapshotMap.entries()).map(([date, holdings]) => ({
      date,
      holdings,
    }));
  } catch (error) {
    console.error("Error fetching snapshots:", error);
    return [];
  }
}

/**
 * Close the database connection pool
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
