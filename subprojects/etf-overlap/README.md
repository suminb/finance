# ETF Overlap

A Next.js web application for analyzing ETF overlaps.

## Getting Started

### Prerequisites

- Node.js 18+ and npm (or yarn/pnpm)

### Installation

```bash
npm install
```

### Data Source

This app fetches ETF holdings data from [ETFdb.com](https://etfdb.com) using headless browser scraping with Puppeteer. **No API key required!** The data is fetched directly from ETFdb.com's public website by automating a headless Chrome browser.

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

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
├── app/              # Next.js App Router
│   ├── api/          # API routes
│   ├── page.tsx      # Main page component
│   ├── layout.tsx    # Root layout
│   └── globals.css   # Global styles
├── public/           # Static assets
├── next.config.js    # Next.js configuration
└── tsconfig.json     # TypeScript configuration
```

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **React 18** - UI library
- **Puppeteer** - Headless Chrome for web scraping
- **Cheerio** - HTML parsing
- **ETFdb.com** - Free ETF holdings data source (web scraping)

## Features

- Fetch underlying assets for any ETF by ticker symbol
- Display holdings with symbol, name, shares, and weight percentage
- Clean, responsive UI

## Alternative Data Sources

The current implementation scrapes ETFdb.com (free, no API key). Other options:
- **API Ninjas** - Free tier (first 3 holdings only)
- **AInvest API** - Free tier (top 10 holdings only)
- **Alpha Vantage** - Free tier (limited)
- **Intrinio** - Paid, comprehensive
- **Yahoo Finance** - Unofficial, may require scraping

To switch data sources, modify `app/api/etf-holdings/route.ts` with your preferred provider's endpoint and response format.

