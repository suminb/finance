import { NextRequest, NextResponse } from "next/server";
import { getCachedHoldings } from "@/lib/db";

interface OverlapResult {
  etf1: string;
  etf2: string;
  overlapPercentage: number;
  sharedHoldings: Array<{
    symbol: string;
    name: string;
    weight1: number;
    weight2: number;
    overlapContribution: number;
  }>;
  totalSharedHoldings: number;
  uniqueHoldings1: number;
  uniqueHoldings2: number;
}

interface CoreOverlap {
  totalOverlap: number;
  sharedHoldings: Array<{
    symbol: string;
    name: string;
    weights: { [etf: string]: number };
    minWeight: number;
  }>;
  totalSharedHoldings: number;
}

interface OverlapMatrixResponse {
  etfs: string[];
  matrix: number[][];
  details: { [key: string]: OverlapResult };
  coreOverlap: CoreOverlap;
  error?: string;
}

/**
 * Calculate weighted overlap coefficient between two ETFs
 */
function calculateOverlap(
  holdings1: Array<{ symbol: string; name: string; weight: number }>,
  holdings2: Array<{ symbol: string; name: string; weight: number }>
): OverlapResult {
  const map1 = new Map(holdings1.map((h) => [h.symbol, h]));
  const map2 = new Map(holdings2.map((h) => [h.symbol, h]));

  const sharedSymbols = holdings1
    .map((h) => h.symbol)
    .filter((symbol) => map2.has(symbol));

  const sharedHoldings = sharedSymbols.map((symbol) => {
    const h1 = map1.get(symbol)!;
    const h2 = map2.get(symbol)!;
    const overlapContribution = Math.min(h1.weight, h2.weight);

    return {
      symbol,
      name: h1.name || h2.name,
      weight1: h1.weight,
      weight2: h2.weight,
      overlapContribution,
    };
  });

  // Sort by overlap contribution (highest first)
  sharedHoldings.sort((a, b) => b.overlapContribution - a.overlapContribution);

  // Calculate total weighted overlap
  const overlapPercentage = sharedHoldings.reduce(
    (sum, h) => sum + h.overlapContribution,
    0
  );

  return {
    etf1: "",
    etf2: "",
    overlapPercentage,
    sharedHoldings,
    totalSharedHoldings: sharedHoldings.length,
    uniqueHoldings1: holdings1.length - sharedHoldings.length,
    uniqueHoldings2: holdings2.length - sharedHoldings.length,
  };
}

/**
 * Calculate N-way overlap (holdings shared by ALL ETFs)
 */
function calculateCoreOverlap(
  holdingsMap: Map<
    string,
    Array<{ symbol: string; name: string; weight: number }>
  >,
  tickers: string[]
): CoreOverlap {
  if (tickers.length < 2) {
    return { totalOverlap: 0, sharedHoldings: [], totalSharedHoldings: 0 };
  }

  // Get all symbols from first ETF
  const firstETF = holdingsMap.get(tickers[0])!;
  const symbolsMap = new Map(firstETF.map((h) => [h.symbol, h]));

  // Find symbols that appear in ALL ETFs
  const sharedSymbols = firstETF
    .map((h) => h.symbol)
    .filter((symbol) => {
      // Check if this symbol exists in all other ETFs
      return tickers.slice(1).every((ticker) => {
        const holdings = holdingsMap.get(ticker)!;
        return holdings.some((h) => h.symbol === symbol);
      });
    });

  // Build shared holdings data
  const sharedHoldings = sharedSymbols.map((symbol) => {
    const weights: { [etf: string]: number } = {};
    const names: string[] = [];

    tickers.forEach((ticker) => {
      const holdings = holdingsMap.get(ticker)!;
      const holding = holdings.find((h) => h.symbol === symbol);
      if (holding) {
        weights[ticker] = holding.weight;
        names.push(holding.name);
      }
    });

    // Min weight across all ETFs
    const minWeight = Math.min(...Object.values(weights));

    return {
      symbol,
      name: names[0] || symbol, // Use first non-empty name
      weights,
      minWeight,
    };
  });

  // Sort by min weight (highest contribution first)
  sharedHoldings.sort((a, b) => b.minWeight - a.minWeight);

  // Calculate total core overlap
  const totalOverlap = sharedHoldings.reduce((sum, h) => sum + h.minWeight, 0);

  return {
    totalOverlap,
    sharedHoldings,
    totalSharedHoldings: sharedHoldings.length,
  };
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const tickersParam = searchParams.get("tickers");

  if (!tickersParam) {
    return NextResponse.json(
      { error: "tickers parameter is required (comma-separated)" },
      { status: 400 }
    );
  }

  const tickers = tickersParam
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);

  if (tickers.length < 2) {
    return NextResponse.json(
      { error: "At least 2 ETF tickers are required" },
      { status: 400 }
    );
  }

  try {
    // Fetch holdings for all ETFs
    const holdingsMap = new Map<
      string,
      Array<{ symbol: string; name: string; weight: number }>
    >();

    for (const ticker of tickers) {
      const holdings = await getCachedHoldings(ticker, 24);

      if (!holdings || holdings.length === 0) {
        return NextResponse.json(
          {
            error: `No cached holdings found for ${ticker}. Please fetch ${ticker} holdings first.`,
            etfs: tickers,
            matrix: [],
          },
          { status: 404 }
        );
      }

      holdingsMap.set(ticker, holdings);
    }

    // Calculate overlap matrix and store details
    const matrix: number[][] = [];
    const details: { [key: string]: OverlapResult } = {};

    for (let i = 0; i < tickers.length; i++) {
      matrix[i] = [];
      for (let j = 0; j < tickers.length; j++) {
        if (i === j) {
          // Diagonal: self-overlap is 100%
          matrix[i][j] = 100;
        } else {
          const holdings1 = holdingsMap.get(tickers[i])!;
          const holdings2 = holdingsMap.get(tickers[j])!;
          const overlap = calculateOverlap(holdings1, holdings2);
          overlap.etf1 = tickers[i];
          overlap.etf2 = tickers[j];

          matrix[i][j] = Math.round(overlap.overlapPercentage * 100) / 100;

          // Store details with key "ETF1-ETF2"
          const key = `${tickers[i]}-${tickers[j]}`;
          details[key] = overlap;
        }
      }
    }

    // Calculate N-way core overlap (shared by ALL ETFs)
    const coreOverlap = calculateCoreOverlap(holdingsMap, tickers);

    return NextResponse.json({
      etfs: tickers,
      matrix,
      details,
      coreOverlap,
    } as OverlapMatrixResponse);
  } catch (error) {
    console.error("Error calculating overlap:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to calculate overlap",
        etfs: tickers,
        matrix: [],
      },
      { status: 500 }
    );
  }
}
