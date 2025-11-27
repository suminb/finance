import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { POPULAR_ETFS, ETFListItem } from "@/lib/etf-list";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get("q")?.trim().toUpperCase() || "";

  try {
    let results: ETFListItem[] = [];

    // Search in database first
    try {
      const pool = getPool();
      const dbResult = await pool.query(
        `SELECT DISTINCT symbol, name
         FROM etfs
         WHERE UPPER(symbol) LIKE $1 OR UPPER(name) LIKE $1
         ORDER BY symbol
         LIMIT 20`,
        [`%${query}%`]
      );

      results = dbResult.rows.map((row) => ({
        symbol: row.symbol,
        name: row.name || row.symbol,
      }));
    } catch (dbError) {
      console.log("Database search failed, using static list only:", dbError);
    }

    // Add popular ETFs that match
    const popularMatches = POPULAR_ETFS.filter(
      (etf) =>
        etf.symbol.includes(query) || etf.name.toUpperCase().includes(query)
    );

    // Merge results (remove duplicates based on symbol)
    const merged = [...results, ...popularMatches];
    const unique = merged.filter(
      (etf, index, self) =>
        index === self.findIndex((e) => e.symbol === etf.symbol)
    );

    // Sort by relevance: exact symbol match first, then starts with query, then contains
    unique.sort((a, b) => {
      if (a.symbol === query) return -1;
      if (b.symbol === query) return 1;
      if (a.symbol.startsWith(query) && !b.symbol.startsWith(query)) return -1;
      if (b.symbol.startsWith(query) && !a.symbol.startsWith(query)) return 1;
      return a.symbol.localeCompare(b.symbol);
    });

    return NextResponse.json({
      results: unique.slice(0, 20), // Limit to 20 results
    });
  } catch (error) {
    console.error("Error searching ETFs:", error);
    return NextResponse.json(
      { error: "Failed to search ETFs", results: [] },
      { status: 500 }
    );
  }
}
