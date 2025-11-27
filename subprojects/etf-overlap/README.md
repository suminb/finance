# ETF Overlap

A Next.js web application for analyzing ETF overlaps.

## Getting Started

### Prerequisites

- Node.js 18+ and npm (or yarn/pnpm)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Set up the database:

```bash
# Copy example environment file
cp .env.example .env.local

# Edit .env.local with your database credentials
# Then run the schema
psql $DATABASE_URL -f db/schema.sql
```

### Data Source

This app fetches ETF holdings data from [ETFdb.com](https://etfdb.com) using headless browser scraping with Puppeteer. **No API key required!** The data is fetched directly from ETFdb.com's public website by automating a headless Chrome browser.

**Caching:** Holdings are cached in PostgreSQL for 24 hours (configurable) to reduce scraping frequency and improve performance.

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### How to Use

1. **Type ETF tickers or names** in the autocomplete input:
   - Start typing and select from suggestions (e.g., "QQQ", "Invesco")
   - Press **Space** or **Enter** to add as a tag
   - Use **Backspace** to remove the last tag
   - Click **×** on tags to remove them
2. **Add 2 or more ETFs** (shown as blue tags)
3. Click **"Calculate Overlap"**
4. View the **heatmap** showing weighted overlap percentages
5. **Click any cell** in the heatmap to see detailed overlapping holdings
6. View the **Core Overlap** section to see holdings shared by ALL selected ETFs

**Note**: The first time you compare ETFs, the app will scrape ETFdb.com for their holdings (takes ~5-15 seconds per ETF). Subsequent comparisons will be instant thanks to PostgreSQL caching.

### Build

Build for production:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## Project Structure

```
etf-overlap/
├── app/                       # Next.js App Router
│   ├── api/                   # API routes
│   │   ├── etf-holdings/      # Fetch ETF holdings (scraping)
│   │   ├── overlap/           # Calculate overlap matrix
│   │   └── search-etfs/       # Search ETFs for autocomplete
│   ├── page.tsx               # Main overlap analysis page
│   ├── layout.tsx             # Root layout
│   └── globals.css            # Global styles
├── components/                # React components
│   └── ETFAutocomplete.tsx    # Autocomplete input with tags
├── lib/                       # Utilities
│   ├── db.ts                  # Database functions
│   └── etf-list.ts            # Popular ETFs list
├── db/                        # Database schema & migrations
├── public/                    # Static assets
├── next.config.js             # Next.js configuration
└── tsconfig.json              # TypeScript configuration
```

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **React 18** - UI library
- **Puppeteer** - Headless Chrome for web scraping
- **Cheerio** - HTML parsing
- **PostgreSQL** - Data caching and persistence
- **ETFdb.com** - Free ETF holdings data source (web scraping)

## Features

- **Smart Autocomplete**: Type-ahead search for ETF tickers and names with tag-based input
- **Overlap Analysis**: Compare multiple ETFs with weighted overlap heatmap
- **Core Overlap View**: See holdings shared by ALL selected ETFs (N-way intersection)
- **Pairwise Details**: Click any heatmap cell to see detailed overlap between two ETFs
- **Weighted Calculation**: Uses portfolio weight percentages for accurate overlap
- **Visual Heatmap**: Color-coded matrix showing overlap intensity
- **Automatic Caching**: PostgreSQL-backed caching for fast comparisons
- **Profile Data**: Stores ETF metadata (issuer, expense ratio, AUM, etc.)
- **Web Scraping**: Fetches data from ETFdb.com using Puppeteer

## Alternative Data Sources

The current implementation scrapes ETFdb.com (free, no API key). Other options:

- **API Ninjas** - Free tier (first 3 holdings only)
- **AInvest API** - Free tier (top 10 holdings only)
- **Alpha Vantage** - Free tier (limited)
- **Intrinio** - Paid, comprehensive
- **Yahoo Finance** - Unofficial, may require scraping

To switch data sources, modify `app/api/etf-holdings/route.ts` with your preferred provider's endpoint and response format.
