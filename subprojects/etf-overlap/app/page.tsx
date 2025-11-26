'use client'

import { useState } from 'react'

interface ETFHolding {
  asset: string
  name: string
  symbol: string
  shares: number
  weight: number
}

interface ETFHoldingsResponse {
  symbol: string
  holdings: ETFHolding[]
  error?: string
}

export default function Home() {
  const [ticker, setTicker] = useState('')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ETFHoldingsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchHoldings = async () => {
    if (!ticker.trim()) {
      setError('Please enter an ETF ticker')
      return
    }

    setLoading(true)
    setError(null)
    setData(null)

    try {
      const response = await fetch(`/api/etf-holdings?ticker=${encodeURIComponent(ticker.trim())}`)
      const result: ETFHoldingsResponse = await response.json()

      if (!response.ok || result.error) {
        setError(result.error || 'Failed to fetch ETF holdings')
        return
      }

      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    fetchHoldings()
  }

  return (
    <main style={{ padding: '2rem', minHeight: '100vh', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>ETF Overlap</h1>
      <p style={{ marginBottom: '2rem', color: '#666' }}>
        Enter an ETF ticker symbol to view its underlying holdings
      </p>

      <form onSubmit={handleSubmit} style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="e.g., SPY, VOO, QQQ"
            style={{
              padding: '0.75rem',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              minWidth: '200px',
            }}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              backgroundColor: '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Loading...' : 'Get Holdings'}
          </button>
        </div>
      </form>

      {error && (
        <div
          style={{
            padding: '1rem',
            backgroundColor: '#fee',
            border: '1px solid #fcc',
            borderRadius: '4px',
            color: '#c33',
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
      )}

      {data && data.holdings && (
        <div>
          <h2 style={{ marginBottom: '1rem' }}>
            Holdings for {data.symbol}
            {data.holdings.length > 0 && (
              <span style={{ fontSize: '0.9rem', fontWeight: 'normal', color: '#666', marginLeft: '0.5rem' }}>
                ({data.holdings.length} holdings)
              </span>
            )}
          </h2>

          {data.holdings.length === 0 ? (
            <p>No holdings found for this ETF.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  backgroundColor: 'white',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                }}
              >
                <thead>
                  <tr style={{ backgroundColor: '#f5f5f5' }}>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>
                      Symbol
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>
                      Name
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'right', borderBottom: '2px solid #ddd' }}>
                      Shares
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'right', borderBottom: '2px solid #ddd' }}>
                      Weight (%)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.holdings.map((holding, index) => (
                    <tr
                      key={index}
                      style={{
                        borderBottom: '1px solid #eee',
                      }}
                    >
                      <td style={{ padding: '0.75rem', fontWeight: '500' }}>
                        {holding.symbol || holding.asset}
                      </td>
                      <td style={{ padding: '0.75rem' }}>{holding.name || '-'}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        {holding.shares ? holding.shares.toLocaleString() : '-'}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        {holding.weight ? `${holding.weight.toFixed(2)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: '3rem', padding: '1rem', backgroundColor: '#f9f9f9', borderRadius: '4px', fontSize: '0.9rem', color: '#666' }}>
        <p style={{ marginBottom: '0.5rem', fontWeight: '500' }}>Data Source:</p>
        <p style={{ margin: 0 }}>
          This app fetches ETF holdings data from{' '}
          <a href="https://etfdb.com" target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>
            ETFdb.com
          </a>
          {' '}using headless browser scraping (Puppeteer). No API key required! Data is fetched by automating a headless Chrome browser.
        </p>
      </div>
    </main>
  )
}
