// Static list of popular ETFs for autocomplete
// This will be supplemented by ETFs stored in the database

export interface ETFListItem {
  symbol: string;
  name: string;
}

export const POPULAR_ETFS: ETFListItem[] = [
  // Large Cap / Broad Market
  { symbol: "SPY", name: "SPDR S&P 500 ETF Trust" },
  { symbol: "VOO", name: "Vanguard S&P 500 ETF" },
  { symbol: "IVV", name: "iShares Core S&P 500 ETF" },
  { symbol: "QQQ", name: "Invesco QQQ Trust" },
  { symbol: "VTI", name: "Vanguard Total Stock Market ETF" },
  { symbol: "DIA", name: "SPDR Dow Jones Industrial Average ETF" },
  { symbol: "IWM", name: "iShares Russell 2000 ETF" },
  { symbol: "VTV", name: "Vanguard Value ETF" },
  { symbol: "VUG", name: "Vanguard Growth ETF" },

  // Technology
  { symbol: "VGT", name: "Vanguard Information Technology ETF" },
  { symbol: "XLK", name: "Technology Select Sector SPDR Fund" },
  { symbol: "SOXX", name: "iShares Semiconductor ETF" },
  { symbol: "SMH", name: "VanEck Semiconductor ETF" },
  { symbol: "ARKK", name: "ARK Innovation ETF" },
  { symbol: "WCLD", name: "WisdomTree Cloud Computing Fund" },

  // Financials
  { symbol: "XLF", name: "Financial Select Sector SPDR Fund" },
  { symbol: "VFH", name: "Vanguard Financials ETF" },

  // Healthcare
  { symbol: "XLV", name: "Health Care Select Sector SPDR Fund" },
  { symbol: "VHT", name: "Vanguard Health Care ETF" },
  { symbol: "IBB", name: "iShares Biotechnology ETF" },

  // Energy
  { symbol: "XLE", name: "Energy Select Sector SPDR Fund" },
  { symbol: "VDE", name: "Vanguard Energy ETF" },

  // Consumer
  { symbol: "XLY", name: "Consumer Discretionary Select Sector SPDR Fund" },
  { symbol: "XLP", name: "Consumer Staples Select Sector SPDR Fund" },
  { symbol: "VCR", name: "Vanguard Consumer Discretionary ETF" },

  // International
  { symbol: "EFA", name: "iShares MSCI EAFE ETF" },
  { symbol: "VEA", name: "Vanguard FTSE Developed Markets ETF" },
  { symbol: "VWO", name: "Vanguard FTSE Emerging Markets ETF" },
  { symbol: "EEM", name: "iShares MSCI Emerging Markets ETF" },

  // Bonds
  { symbol: "AGG", name: "iShares Core U.S. Aggregate Bond ETF" },
  { symbol: "BND", name: "Vanguard Total Bond Market ETF" },
  { symbol: "LQD", name: "iShares iBoxx Investment Grade Corporate Bond ETF" },
  { symbol: "TLT", name: "iShares 20+ Year Treasury Bond ETF" },

  // Commodities
  { symbol: "GLD", name: "SPDR Gold Shares" },
  { symbol: "SLV", name: "iShares Silver Trust" },
  { symbol: "USO", name: "United States Oil Fund" },

  // Real Estate
  { symbol: "VNQ", name: "Vanguard Real Estate ETF" },
  { symbol: "IYR", name: "iShares U.S. Real Estate ETF" },

  // Dividend
  { symbol: "SCHD", name: "Schwab U.S. Dividend Equity ETF" },
  { symbol: "VYM", name: "Vanguard High Dividend Yield ETF" },
  { symbol: "JEPI", name: "JPMorgan Equity Premium Income ETF" },
  { symbol: "JEPQ", name: "JPMorgan Nasdaq Equity Premium Income ETF" },
];
