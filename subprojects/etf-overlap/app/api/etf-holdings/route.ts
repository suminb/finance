import { NextRequest, NextResponse } from "next/server";
import puppeteer from "puppeteer";
import { getCachedHoldings, saveHoldings, ETFProfile } from "@/lib/db";

interface ETFHolding {
  symbol: string;
  name: string;
  weight: number;
  shares?: number;
}

interface ETFHoldingsResponse {
  symbol: string;
  holdings: ETFHolding[];
  cached?: boolean;
  error?: string;
}

function extractProfileData($: any): ETFProfile {
  const profile: ETFProfile = {};

  // Extract from Vitals section
  $(".ticker-assets .row").each((_: any, row: any) => {
    const $row = $(row);
    const label = $row.find("span:first-child").text().trim();
    const value = $row.find("span:last-child").text().trim();

    switch (label) {
      case "Issuer":
        profile.issuer = value;
        break;
      case "Brand":
        profile.brand = value;
        break;
      case "Structure":
        profile.structure = value;
        break;
      case "Expense Ratio":
        const expenseMatch = value.match(/(\d+\.?\d*)%/);
        if (expenseMatch) {
          profile.expense_ratio = parseFloat(expenseMatch[1]) / 100; // Convert to decimal
        }
        break;
      case "Inception":
        try {
          profile.inception_date = new Date(value);
        } catch (e) {
          // Invalid date
        }
        break;
      case "Index Tracked":
        profile.index_tracked = value;
        break;
    }
  });

  // Extract home page
  const homePageLink = $(
    '.ticker-assets .row:contains("ETF Home Page") a'
  ).attr("href");
  if (homePageLink) {
    profile.home_page = homePageLink;
  }

  // Extract ETF Database Themes
  $('h3.h4:contains("ETF Database Themes")')
    .parent()
    .find(".ticker-assets .row")
    .each((_: any, row: any) => {
      const $row = $(row);
      const label = $row.find("span:first-child").text().trim();
      const value = $row.find("span:last-child").text().trim();

      switch (label) {
        case "Category":
          profile.category = value;
          break;
        case "Asset Class":
          profile.asset_class = value;
          break;
        case "Asset Class Size":
          profile.asset_class_size = value;
          break;
        case "Asset Class Style":
          profile.asset_class_style = value;
          break;
        case "Sector (General)":
          profile.sector_general = value;
          break;
        case "Sector (Specific)":
          profile.sector_specific = value;
          break;
        case "Region (General)":
          profile.region_general = value;
          break;
        case "Region (Specific)":
          profile.region_specific = value;
          break;
      }
    });

  // Extract trading data
  $(".trading-data li, ul.list-unstyled li").each((_: any, li: any) => {
    const $li = $(li);
    const label = $li.find("span:first-child").text().trim();
    const value = $li.find("span:last-child").text().trim();

    switch (label) {
      case "AUM":
        // Parse values like "$382,989.0 M"
        const aumMatch = value.match(/\$?([\d,]+\.?\d*)\s*([MBK])?/);
        if (aumMatch) {
          let aum = parseFloat(aumMatch[1].replace(/,/g, ""));
          const unit = aumMatch[2];
          if (unit === "M") aum *= 1000000;
          if (unit === "B") aum *= 1000000000;
          if (unit === "K") aum *= 1000;
          profile.aum = Math.round(aum);
        }
        break;
      case "Shares":
        // Parse values like "654.1 M"
        const sharesMatch = value.match(/([\d,]+\.?\d*)\s*([MBK])?/);
        if (sharesMatch) {
          let shares = parseFloat(sharesMatch[1].replace(/,/g, ""));
          const unit = sharesMatch[2];
          if (unit === "M") shares *= 1000000;
          if (unit === "B") shares *= 1000000000;
          if (unit === "K") shares *= 1000;
          profile.shares_outstanding = Math.round(shares);
        }
        break;
    }
  });

  return profile;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const ticker = searchParams.get("ticker");

  if (!ticker) {
    return NextResponse.json(
      { error: "Ticker parameter is required" },
      { status: 400 }
    );
  }

  const normalizedTicker = ticker.toUpperCase().trim();

  // Check cache first (24 hour TTL by default)
  const cacheMaxAgeHours = parseInt(process.env.CACHE_MAX_AGE_HOURS || "24");

  try {
    console.log(`Checking cache for ${normalizedTicker}...`);
    const cachedHoldings = await getCachedHoldings(
      normalizedTicker,
      cacheMaxAgeHours
    );

    if (cachedHoldings && cachedHoldings.length > 0) {
      console.log(
        `✓ Cache hit for ${normalizedTicker} (${cachedHoldings.length} holdings)`
      );
      return NextResponse.json({
        symbol: normalizedTicker,
        holdings: cachedHoldings,
        cached: true,
      } as ETFHoldingsResponse);
    }

    console.log(
      `✗ Cache miss for ${normalizedTicker}, proceeding to scrape...`
    );
  } catch (cacheError) {
    console.error("✗ Cache error, falling back to scraping:", cacheError);
    console.error(
      "Database URL set?",
      !!(process.env.DATABASE_URL || process.env.SBF_DB_URL)
    );
  }

  // Cache miss or error - proceed with scraping
  let browser = null;

  try {
    // Launch headless browser using system Chrome
    // Common Chrome paths on macOS
    const chromePaths = [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
      "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ];

    let executablePath = undefined;
    for (const path of chromePaths) {
      try {
        const fs = await import("fs");
        if (fs.existsSync(path)) {
          executablePath = path;
          break;
        }
      } catch (e) {
        // Continue checking
      }
    }

    browser = await puppeteer.launch({
      headless: "new",
      executablePath, // Use system Chrome if found, otherwise use bundled Chromium
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
      ],
    });

    const page = await browser.newPage();

    // Set viewport and user agent
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    );

    // Navigate to ETFdb.com holdings page
    const url = `https://etfdb.com/etf/${normalizedTicker}/#holdings`;

    try {
      await page.goto(url, {
        waitUntil: "networkidle2",
        timeout: 30000,
      });

      // Wait a bit for any dynamic content to load
      await page.waitForTimeout(2000);

      // Try to click on holdings tab if it exists (in case the fragment doesn't work)
      try {
        const holdingsTab = await page.$(
          'a[href*="#holdings"], button[data-tab="holdings"], .tab-holdings'
        );
        if (holdingsTab) {
          await holdingsTab.click();
          await page.waitForTimeout(1000);
        }
      } catch {
        // Tab click not needed or doesn't exist
      }
    } catch (navError) {
      await browser.close();
      return NextResponse.json(
        {
          error: `Failed to load page for ${normalizedTicker}. The ETF may not exist or the page may be unavailable.`,
          symbol: normalizedTicker,
          holdings: [],
        },
        { status: 404 }
      );
    }

    // Check if we got a 404 or error page
    const pageTitle = await page.title();
    if (
      pageTitle.toLowerCase().includes("404") ||
      pageTitle.toLowerCase().includes("not found")
    ) {
      await browser.close();
      return NextResponse.json(
        { error: `ETF "${normalizedTicker}" not found on ETFdb.com` },
        { status: 404 }
      );
    }

    // Wait for holdings table to load (if it exists)
    try {
      await page.waitForSelector("table, .holdings, [data-holdings]", {
        timeout: 10000,
      });
    } catch {
      // Table might not exist, continue anyway
    }

    // Get page HTML
    const html = await page.content();

    // Debug: Log page title and URL
    const finalUrl = page.url();
    console.log(`Fetched page for ${normalizedTicker}:`, finalUrl);
    console.log(`Page title:`, pageTitle);

    await browser.close();

    // Parse HTML with Cheerio
    const cheerioModule = await import("cheerio");
    const cheerio =
      "default" in cheerioModule ? cheerioModule.default : cheerioModule;
    const $ = cheerio.load(html);

    // Extract profile data
    const profile = extractProfileData($);
    console.log(
      `Extracted profile for ${normalizedTicker}:`,
      Object.keys(profile).length,
      "fields"
    );

    const holdings: ETFHolding[] = [];

    // Debug: Check what tables exist
    const allTables = $("table");
    console.log(`Found ${allTables.length} tables on the page`);

    // Strategy 1: Target the specific ETFdb.com structure
    // Table structure: <table id="etf-holdings"> with tbody containing rows
    const holdingsTable = $('#etf-holdings, table[id="etf-holdings"]');

    if (holdingsTable.length > 0) {
      console.log("Found etf-holdings table");

      holdingsTable.find("tbody tr").each((_, row) => {
        const $row = $(row);
        const cells = $row.find("td");

        if (cells.length >= 3) {
          // ETFdb structure: [Symbol, Holding Name, % Assets]
          const symbolCell = $(cells[0]);
          const nameCell = $(cells[1]);
          const weightCell = $(cells[2]);

          // Extract symbol from anchor tag or text
          const symbol =
            symbolCell.find("a").text().trim() || symbolCell.text().trim();
          const name = nameCell.text().trim();
          const weightText = weightCell.text().trim();
          const weight = parseFloat(weightText.replace(/[%,]/g, "")) || 0;

          if (symbol && /^[A-Z]{1,6}$/.test(symbol)) {
            console.log(`Found holding: ${symbol} - ${name} - ${weight}%`);
            holdings.push({
              symbol: symbol.toUpperCase(),
              name: name || symbol,
              weight,
            });
          }
        }
      });
    } else {
      console.log("etf-holdings table not found, trying alternative selectors");

      // Fallback: Try other table structures
      const tables = $("table");
      console.log(`Found ${tables.length} tables total`);

      tables.each((_, table) => {
        const $table = $(table);
        $table.find("tbody tr").each((_, row) => {
          const $row = $(row);
          const cells = $row.find("td");

          if (cells.length >= 2) {
            const cellTexts = cells
              .map((_, cell) => $(cell).text().trim())
              .get();

            // Try to identify symbol (first cell, uppercase letters)
            const firstCell = cellTexts[0] || "";
            if (/^[A-Z]{1,6}$/.test(firstCell)) {
              const symbol = firstCell;
              const name = cellTexts[1] || symbol;

              // Look for weight
              const weightCell = cellTexts.find((cell) => cell.includes("%"));
              const weight = weightCell
                ? parseFloat(weightCell.replace(/[%,]/g, ""))
                : 0;

              holdings.push({
                symbol: symbol.toUpperCase(),
                name,
                weight,
              });
            }
          }
        });

        if (holdings.length > 0) return false; // break
      });
    }

    // Strategy 2: Look for JSON data in script tags
    if (holdings.length === 0) {
      $("script").each((_, script) => {
        const scriptContent = $(script).html() || "";

        const patterns = [
          /holdings["\s]*[:=]["\s]*(\[[^\]]+\])/i,
          /"holdings"["\s]*:["\s]*(\[[^\]]+\])/i,
          /const\s+holdings\s*=\s*(\[[^\]]+\])/i,
          /var\s+holdings\s*=\s*(\[[^\]]+\])/i,
        ];

        for (const pattern of patterns) {
          const match = scriptContent.match(pattern);
          if (match) {
            try {
              const holdingsData = JSON.parse(match[1]);
              if (Array.isArray(holdingsData)) {
                holdingsData.forEach((item: any) => {
                  if (item.symbol || item.ticker || item.code) {
                    holdings.push({
                      symbol: (
                        item.symbol ||
                        item.ticker ||
                        item.code ||
                        ""
                      ).toUpperCase(),
                      name: item.name || item.company || item.title || "",
                      weight: parseFloat(
                        item.weight || item.percentage || item.pct || 0
                      ),
                      shares: item.shares
                        ? parseInt(String(item.shares).replace(/,/g, ""))
                        : undefined,
                    });
                  }
                });
                if (holdings.length > 0) return false; // break the .each loop
              }
            } catch (e) {
              // Ignore JSON parse errors
            }
          }
        }
      });
    }

    // Remove duplicates based on symbol
    const uniqueHoldings = holdings.filter(
      (holding, index, self) =>
        index === self.findIndex((h) => h.symbol === holding.symbol)
    );

    if (uniqueHoldings.length === 0) {
      // Debug: Save HTML to inspect
      console.log(`No holdings found for ${normalizedTicker}`);
      console.log(`HTML length: ${html.length}`);
      console.log(`First 500 chars:`, html.substring(0, 500));

      return NextResponse.json(
        {
          error: `Could not find holdings data for "${normalizedTicker}". The ETF may not exist or the page structure may have changed. Check server logs for details.`,
          symbol: normalizedTicker,
          holdings: [],
        },
        { status: 404 }
      );
    }

    const sortedHoldings = uniqueHoldings.sort((a, b) => b.weight - a.weight);

    // Save to cache with profile data
    try {
      console.log(
        `Attempting to save ${sortedHoldings.length} holdings for ${normalizedTicker} to database...`
      );
      await saveHoldings(normalizedTicker, sortedHoldings, profile);
      console.log(
        `✓ Successfully cached ${sortedHoldings.length} holdings and profile for ${normalizedTicker}`
      );
    } catch (saveError) {
      console.error("✗ Error saving to cache:", saveError);
      console.error(
        "Full error:",
        saveError instanceof Error ? saveError.stack : saveError
      );
      // Continue anyway - we still have the scraped data
    }

    return NextResponse.json({
      symbol: normalizedTicker,
      holdings: sortedHoldings,
      cached: false,
    } as ETFHoldingsResponse);
  } catch (error) {
    if (browser) {
      await browser.close();
    }
    console.error("Error fetching ETF holdings:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch ETF holdings",
        symbol: normalizedTicker,
        holdings: [],
      },
      { status: 500 }
    );
  }
}
