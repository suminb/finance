import { NextRequest, NextResponse } from 'next/server'
import puppeteer from 'puppeteer'

interface ETFHolding {
  symbol: string
  name: string
  weight: number
  shares?: number
}

interface ETFHoldingsResponse {
  symbol: string
  holdings: ETFHolding[]
  error?: string
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const ticker = searchParams.get('ticker')

  if (!ticker) {
    return NextResponse.json(
      { error: 'Ticker parameter is required' },
      { status: 400 }
    )
  }

  const normalizedTicker = ticker.toUpperCase().trim()
  let browser = null

  try {
    // Launch headless browser using system Chrome
    // Common Chrome paths on macOS
    const chromePaths = [
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Chromium.app/Contents/MacOS/Chromium',
      '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    ]
    
    let executablePath = undefined
    for (const path of chromePaths) {
      try {
        const fs = await import('fs')
        if (fs.existsSync(path)) {
          executablePath = path
          break
        }
      } catch (e) {
        // Continue checking
      }
    }

    browser = await puppeteer.launch({
      headless: 'new',
      executablePath, // Use system Chrome if found, otherwise use bundled Chromium
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
      ],
    })

    const page = await browser.newPage()

    // Set viewport and user agent
    await page.setViewport({ width: 1920, height: 1080 })
    await page.setUserAgent(
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    // Navigate to ETFdb.com holdings page
    const url = `https://etfdb.com/etf/${normalizedTicker}/#holdings`
    
    try {
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000,
      })
      
      // Wait a bit for any dynamic content to load
      await page.waitForTimeout(2000)
      
      // Try to click on holdings tab if it exists (in case the fragment doesn't work)
      try {
        const holdingsTab = await page.$('a[href*="#holdings"], button[data-tab="holdings"], .tab-holdings')
        if (holdingsTab) {
          await holdingsTab.click()
          await page.waitForTimeout(1000)
        }
      } catch {
        // Tab click not needed or doesn't exist
      }
    } catch (navError) {
      await browser.close()
      return NextResponse.json(
        {
          error: `Failed to load page for ${normalizedTicker}. The ETF may not exist or the page may be unavailable.`,
          symbol: normalizedTicker,
          holdings: []
        },
        { status: 404 }
      )
    }

    // Check if we got a 404 or error page
    const pageTitle = await page.title()
    if (pageTitle.toLowerCase().includes('404') || pageTitle.toLowerCase().includes('not found')) {
      await browser.close()
      return NextResponse.json(
        { error: `ETF "${normalizedTicker}" not found on ETFdb.com` },
        { status: 404 }
      )
    }

    // Wait for holdings table to load (if it exists)
    try {
      await page.waitForSelector('table, .holdings, [data-holdings]', { timeout: 10000 })
    } catch {
      // Table might not exist, continue anyway
    }

    // Get page HTML
    const html = await page.content()
    
    // Debug: Log page title and URL
    const finalUrl = page.url()
    console.log(`Fetched page for ${normalizedTicker}:`, finalUrl)
    console.log(`Page title:`, pageTitle)
    
    await browser.close()

    // Parse HTML with Cheerio
    const cheerioModule = await import('cheerio')
    const cheerio = 'default' in cheerioModule ? cheerioModule.default : cheerioModule
    const $ = cheerio.load(html)

    const holdings: ETFHolding[] = []
    
    // Debug: Check what tables exist
    const allTables = $('table')
    console.log(`Found ${allTables.length} tables on the page`)

    // Strategy 1: Target the specific ETFdb.com structure
    // Table structure: <table id="etf-holdings"> with tbody containing rows
    const holdingsTable = $('#etf-holdings, table[id="etf-holdings"]')
    
    if (holdingsTable.length > 0) {
      console.log('Found etf-holdings table')
      
      holdingsTable.find('tbody tr').each((_, row) => {
        const $row = $(row)
        const cells = $row.find('td')
        
        if (cells.length >= 3) {
          // ETFdb structure: [Symbol, Holding Name, % Assets]
          const symbolCell = $(cells[0])
          const nameCell = $(cells[1])
          const weightCell = $(cells[2])
          
          // Extract symbol from anchor tag or text
          const symbol = symbolCell.find('a').text().trim() || symbolCell.text().trim()
          const name = nameCell.text().trim()
          const weightText = weightCell.text().trim()
          const weight = parseFloat(weightText.replace(/[%,]/g, '')) || 0
          
          if (symbol && /^[A-Z]{1,6}$/.test(symbol)) {
            console.log(`Found holding: ${symbol} - ${name} - ${weight}%`)
            holdings.push({
              symbol: symbol.toUpperCase(),
              name: name || symbol,
              weight,
            })
          }
        }
      })
    } else {
      console.log('etf-holdings table not found, trying alternative selectors')
      
      // Fallback: Try other table structures
      const tables = $('table')
      console.log(`Found ${tables.length} tables total`)
      
      tables.each((_, table) => {
        const $table = $(table)
        $table.find('tbody tr').each((_, row) => {
          const $row = $(row)
          const cells = $row.find('td')
          
          if (cells.length >= 2) {
            const cellTexts = cells.map((_, cell) => $(cell).text().trim()).get()
            
            // Try to identify symbol (first cell, uppercase letters)
            const firstCell = cellTexts[0] || ''
            if (/^[A-Z]{1,6}$/.test(firstCell)) {
              const symbol = firstCell
              const name = cellTexts[1] || symbol
              
              // Look for weight
              const weightCell = cellTexts.find(cell => cell.includes('%'))
              const weight = weightCell ? parseFloat(weightCell.replace(/[%,]/g, '')) : 0
              
              holdings.push({
                symbol: symbol.toUpperCase(),
                name,
                weight,
              })
            }
          }
        })
        
        if (holdings.length > 0) return false // break
      })
    }

    // Strategy 2: Look for JSON data in script tags
    if (holdings.length === 0) {
      $('script').each((_, script) => {
        const scriptContent = $(script).html() || ''
        
        const patterns = [
          /holdings["\s]*[:=]["\s]*(\[[^\]]+\])/i,
          /"holdings"["\s]*:["\s]*(\[[^\]]+\])/i,
          /const\s+holdings\s*=\s*(\[[^\]]+\])/i,
          /var\s+holdings\s*=\s*(\[[^\]]+\])/i,
        ]
        
        for (const pattern of patterns) {
          const match = scriptContent.match(pattern)
          if (match) {
            try {
              const holdingsData = JSON.parse(match[1])
              if (Array.isArray(holdingsData)) {
                holdingsData.forEach((item: any) => {
                  if (item.symbol || item.ticker || item.code) {
                    holdings.push({
                      symbol: (item.symbol || item.ticker || item.code || '').toUpperCase(),
                      name: item.name || item.company || item.title || '',
                      weight: parseFloat(item.weight || item.percentage || item.pct || 0),
                      shares: item.shares ? parseInt(String(item.shares).replace(/,/g, '')) : undefined,
                    })
                  }
                })
                if (holdings.length > 0) return false // break the .each loop
              }
            } catch (e) {
              // Ignore JSON parse errors
            }
          }
        }
      })
    }

    // Remove duplicates based on symbol
    const uniqueHoldings = holdings.filter((holding, index, self) =>
      index === self.findIndex(h => h.symbol === holding.symbol)
    )

    if (uniqueHoldings.length === 0) {
      // Debug: Save HTML to inspect
      console.log(`No holdings found for ${normalizedTicker}`)
      console.log(`HTML length: ${html.length}`)
      console.log(`First 500 chars:`, html.substring(0, 500))
      
      return NextResponse.json(
        { 
          error: `Could not find holdings data for "${normalizedTicker}". The ETF may not exist or the page structure may have changed. Check server logs for details.`,
          symbol: normalizedTicker,
          holdings: []
        },
        { status: 404 }
      )
    }

    return NextResponse.json({
      symbol: normalizedTicker,
      holdings: uniqueHoldings.sort((a, b) => b.weight - a.weight),
    } as ETFHoldingsResponse)
  } catch (error) {
    if (browser) {
      await browser.close()
    }
    console.error('Error fetching ETF holdings:', error)
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : 'Failed to fetch ETF holdings',
        symbol: normalizedTicker,
        holdings: []
      },
      { status: 500 }
    )
  }
}
