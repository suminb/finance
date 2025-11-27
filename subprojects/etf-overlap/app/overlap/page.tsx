'use client'

import { useState } from 'react'
import Link from 'next/link'

interface OverlapMatrixResponse {
  etfs: string[]
  matrix: number[][]
  error?: string
}

export default function OverlapPage() {
  const [tickers, setTickers] = useState<string[]>([''])
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OverlapMatrixResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const addTickerInput = () => {
    setTickers([...tickers, ''])
  }

  const removeTickerInput = (index: number) => {
    const newTickers = tickers.filter((_, i) => i !== index)
    setTickers(newTickers.length > 0 ? newTickers : [''])
  }

  const updateTicker = (index: number, value: string) => {
    const newTickers = [...tickers]
    newTickers[index] = value.toUpperCase()
    setTickers(newTickers)
  }

  const calculateOverlap = async () => {
    const validTickers = tickers.filter(t => t.trim().length > 0)
    
    if (validTickers.length < 2) {
      setError('Please enter at least 2 ETF tickers')
      return
    }

    setLoading(true)
    setError(null)
    setData(null)

    try {
      const response = await fetch(`/api/overlap?tickers=${validTickers.join(',')}`)
      const result: OverlapMatrixResponse = await response.json()

      if (!response.ok || result.error) {
        setError(result.error || 'Failed to calculate overlap')
        return
      }

      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const getHeatmapColor = (value: number): string => {
    // Color scale: 0% = white, 100% = dark blue
    if (value >= 80) return '#1e3a8a' // dark blue
    if (value >= 60) return '#3b82f6' // blue
    if (value >= 40) return '#60a5fa' // light blue
    if (value >= 20) return '#93c5fd' // lighter blue
    return '#dbeafe' // very light blue
  }

  const getTextColor = (value: number): string => {
    return value >= 60 ? '#ffffff' : '#1f2937'
  }

  return (
    <main style={{ padding: '2rem', minHeight: '100vh', maxWidth: '1400px', margin: '0 auto' }}>
      <h1>ETF Overlap Analysis</h1>
      <p style={{ marginBottom: '2rem', color: '#666' }}>
        Compare multiple ETFs to visualize their weighted overlap
      </p>

      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>Enter ETF Tickers</h3>
        {tickers.map((ticker, index) => (
          <div key={index} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              value={ticker}
              onChange={(e) => updateTicker(index, e.target.value)}
              placeholder={`ETF ${index + 1} (e.g., QQQ)`}
              style={{
                padding: '0.75rem',
                fontSize: '1rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
                minWidth: '200px',
              }}
              disabled={loading}
            />
            {tickers.length > 1 && (
              <button
                onClick={() => removeTickerInput(index)}
                style={{
                  padding: '0.75rem',
                  fontSize: '1rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
                disabled={loading}
              >
                Remove
              </button>
            )}
          </div>
        ))}
        
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button
            onClick={addTickerInput}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            disabled={loading}
          >
            + Add ETF
          </button>
          
          <button
            onClick={calculateOverlap}
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
            {loading ? 'Calculating...' : 'Calculate Overlap'}
          </button>
        </div>
      </div>

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

      {data && data.matrix && data.matrix.length > 0 && (
        <div>
          <h2 style={{ marginBottom: '1rem' }}>Overlap Heatmap</h2>
          <p style={{ marginBottom: '1.5rem', color: '#666' }}>
            Values show weighted overlap percentage (0-100%). Darker colors indicate higher overlap.
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                borderCollapse: 'collapse',
                backgroundColor: 'white',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              <thead>
                <tr>
                  <th
                    style={{
                      padding: '1rem',
                      textAlign: 'left',
                      borderBottom: '2px solid #ddd',
                      backgroundColor: '#f5f5f5',
                      fontWeight: 'bold',
                      minWidth: '100px',
                    }}
                  >
                    ETF
                  </th>
                  {data.etfs.map((etf) => (
                    <th
                      key={etf}
                      style={{
                        padding: '1rem',
                        textAlign: 'center',
                        borderBottom: '2px solid #ddd',
                        backgroundColor: '#f5f5f5',
                        fontWeight: 'bold',
                        minWidth: '100px',
                      }}
                    >
                      {etf}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.etfs.map((etf1, i) => (
                  <tr key={etf1}>
                    <td
                      style={{
                        padding: '1rem',
                        fontWeight: 'bold',
                        backgroundColor: '#f5f5f5',
                        borderRight: '2px solid #ddd',
                      }}
                    >
                      {etf1}
                    </td>
                    {data.matrix[i].map((value, j) => (
                      <td
                        key={j}
                        style={{
                          padding: '1.5rem',
                          textAlign: 'center',
                          backgroundColor: getHeatmapColor(value),
                          color: getTextColor(value),
                          fontWeight: i === j ? 'bold' : 'normal',
                          fontSize: '1.1rem',
                          border: '1px solid #e5e7eb',
                          transition: 'all 0.2s',
                          cursor: 'default',
                        }}
                        title={`${etf1} vs ${data.etfs[j]}: ${value}%`}
                      >
                        {value.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Color legend */}
          <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Legend</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              {[
                { label: '0-20%', color: '#dbeafe' },
                { label: '20-40%', color: '#93c5fd' },
                { label: '40-60%', color: '#60a5fa' },
                { label: '60-80%', color: '#3b82f6' },
                { label: '80-100%', color: '#1e3a8a' },
              ].map(({ label, color }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '20px',
                      backgroundColor: color,
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                    }}
                  />
                  <span style={{ fontSize: '0.875rem' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Interpretation guide */}
          <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem', color: '#1e40af' }}>📊 How to Read This</h3>
            <ul style={{ marginLeft: '1.5rem', color: '#1e40af', lineHeight: '1.6' }}>
              <li><strong>High overlap (60-100%)</strong>: Very similar holdings - minimal diversification benefit</li>
              <li><strong>Medium overlap (30-60%)</strong>: Some shared exposure with room for diversification</li>
              <li><strong>Low overlap (0-30%)</strong>: Different holdings - good diversification potential</li>
              <li><strong>Diagonal (100%)</strong>: Each ETF compared to itself</li>
            </ul>
          </div>
        </div>
      )}
    </main>
  )
}

