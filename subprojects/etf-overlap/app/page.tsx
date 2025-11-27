"use client";

import { useState } from "react";
import ETFAutocomplete from "@/components/ETFAutocomplete";

interface SharedHolding {
  symbol: string;
  name: string;
  weight1: number;
  weight2: number;
  overlapContribution: number;
}

interface OverlapDetail {
  etf1: string;
  etf2: string;
  overlapPercentage: number;
  sharedHoldings: SharedHolding[];
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
  details: { [key: string]: OverlapDetail };
  coreOverlap: CoreOverlap;
  error?: string;
}

function DonutChart({ overlap, total }: { overlap: number; total: number }) {
  const percentage = (overlap / total) * 100;
  const radius = 80;
  const strokeWidth = 40;
  const normalizedRadius = radius - strokeWidth / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1rem",
      }}
    >
      <svg
        height={radius * 2}
        width={radius * 2}
        style={{ transform: "rotate(-90deg)" }}
      >
        {/* Background circle */}
        <circle
          stroke="#e5e7eb"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        {/* Overlap arc */}
        <circle
          stroke="#0070f3"
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        {/* Center text */}
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dy=".3em"
          style={{
            fontSize: "28px",
            fontWeight: "bold",
            fill: "#0070f3",
            transform: "rotate(90deg)",
            transformOrigin: "center",
          }}
        >
          {overlap.toFixed(1)}%
        </text>
      </svg>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
          Core Overlap
        </div>
        <div
          style={{
            fontSize: "0.75rem",
            color: "#9ca3af",
            marginTop: "0.25rem",
          }}
        >
          Holdings in ALL {Math.round(total / 100)} ETFs
        </div>
      </div>
    </div>
  );
}

export default function OverlapPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OverlapMatrixResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<OverlapDetail | null>(
    null
  );

  const calculateOverlap = async () => {
    if (tickers.length < 2) {
      setError("Please enter at least 2 ETF tickers");
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch(`/api/overlap?tickers=${tickers.join(",")}`);
      const result: OverlapMatrixResponse = await response.json();

      if (!response.ok || result.error) {
        setError(result.error || "Failed to calculate overlap");
        return;
      }

      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred"
      );
    } finally {
      setLoading(false);
    }
  };

  const getHeatmapColor = (value: number): string => {
    // Color scale: 0% = white, 100% = dark blue
    if (value >= 80) return "#1e3a8a"; // dark blue
    if (value >= 60) return "#3b82f6"; // blue
    if (value >= 40) return "#60a5fa"; // light blue
    if (value >= 20) return "#93c5fd"; // lighter blue
    return "#dbeafe"; // very light blue
  };

  const getTextColor = (value: number): string => {
    return value >= 60 ? "#ffffff" : "#1f2937";
  };

  const handleCellClick = (etf1: string, etf2: string) => {
    if (etf1 === etf2) return; // Skip diagonal

    const key = `${etf1}-${etf2}`;
    const detail = data?.details[key];

    if (detail) {
      setSelectedDetail(detail);
      // Scroll to details section
      setTimeout(() => {
        document
          .getElementById("overlap-details")
          ?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  return (
    <main
      style={{
        padding: "2rem",
        minHeight: "100vh",
        maxWidth: "1400px",
        margin: "0 auto",
      }}
    >
      <h1>ETF Overlap Analysis</h1>
      <p style={{ marginBottom: "2rem", color: "#666" }}>
        Compare multiple ETFs to visualize their weighted overlap
      </p>

      <div style={{ marginBottom: "2rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Enter ETF Tickers</h3>

        <ETFAutocomplete
          selectedETFs={tickers}
          onChange={setTickers}
          disabled={loading}
        />

        <div style={{ marginTop: "1rem" }}>
          <button
            onClick={calculateOverlap}
            disabled={loading || tickers.length < 2}
            style={{
              padding: "0.75rem 1.5rem",
              fontSize: "1rem",
              backgroundColor: "#0070f3",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: loading || tickers.length < 2 ? "not-allowed" : "pointer",
              opacity: loading || tickers.length < 2 ? 0.6 : 1,
            }}
          >
            {loading ? "Calculating..." : "Calculate Overlap"}
          </button>
          {tickers.length < 2 && tickers.length > 0 && (
            <span
              style={{
                marginLeft: "1rem",
                color: "#9ca3af",
                fontSize: "0.875rem",
              }}
            >
              Add at least 2 ETFs to compare
            </span>
          )}
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: "1rem",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#c33",
            marginBottom: "1rem",
          }}
        >
          {error}
        </div>
      )}

      {data && data.matrix && data.matrix.length > 0 && (
        <div>
          {/* Core Overlap Section - Holdings in ALL ETFs */}
          {data.coreOverlap && data.etfs.length >= 2 && (
            <div
              style={{
                marginBottom: "3rem",
                padding: "2rem",
                backgroundColor: "#f0f9ff",
                borderRadius: "12px",
                border: "2px solid #0070f3",
              }}
            >
              <h2 style={{ marginBottom: "1.5rem", color: "#0070f3" }}>
                Core Overlap - Holdings in ALL {data.etfs.length} ETFs
              </h2>

              <div
                style={{
                  display: "flex",
                  gap: "3rem",
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                {/* Donut Chart */}
                <div>
                  <DonutChart
                    overlap={data.coreOverlap.totalOverlap}
                    total={100}
                  />
                </div>

                {/* Statistics */}
                <div style={{ flex: "1", minWidth: "300px" }}>
                  <div style={{ display: "grid", gap: "1rem" }}>
                    <div>
                      <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                        Total Core Overlap
                      </div>
                      <div
                        style={{
                          fontSize: "2rem",
                          fontWeight: "bold",
                          color: "#0070f3",
                        }}
                      >
                        {data.coreOverlap.totalOverlap.toFixed(2)}%
                      </div>
                      <div
                        style={{
                          fontSize: "0.875rem",
                          color: "#6b7280",
                          marginTop: "0.25rem",
                        }}
                      >
                        of portfolio weight is shared across all ETFs
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                        Shared Holdings
                      </div>
                      <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                        {data.coreOverlap.totalSharedHoldings} stocks
                      </div>
                      <div
                        style={{
                          fontSize: "0.875rem",
                          color: "#6b7280",
                          marginTop: "0.25rem",
                        }}
                      >
                        appear in all selected ETFs
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Table of shared holdings */}
              {data.coreOverlap.sharedHoldings.length > 0 && (
                <div style={{ marginTop: "2rem" }}>
                  <h3 style={{ marginBottom: "1rem" }}>
                    Holdings Shared by All {data.etfs.length} ETFs
                  </h3>
                  <div
                    style={{
                      overflowX: "auto",
                      backgroundColor: "white",
                      borderRadius: "8px",
                      padding: "1rem",
                    }}
                  >
                    <table
                      style={{ width: "100%", borderCollapse: "collapse" }}
                    >
                      <thead>
                        <tr style={{ backgroundColor: "#f5f5f5" }}>
                          <th
                            style={{
                              padding: "0.75rem",
                              textAlign: "left",
                              borderBottom: "2px solid #ddd",
                            }}
                          >
                            Symbol
                          </th>
                          <th
                            style={{
                              padding: "0.75rem",
                              textAlign: "left",
                              borderBottom: "2px solid #ddd",
                            }}
                          >
                            Name
                          </th>
                          {data.etfs.map((etf) => (
                            <th
                              key={etf}
                              style={{
                                padding: "0.75rem",
                                textAlign: "right",
                                borderBottom: "2px solid #ddd",
                              }}
                            >
                              {etf} %
                            </th>
                          ))}
                          <th
                            style={{
                              padding: "0.75rem",
                              textAlign: "right",
                              borderBottom: "2px solid #ddd",
                              backgroundColor: "#eff6ff",
                            }}
                          >
                            Min %
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.coreOverlap.sharedHoldings.map(
                          (holding, index) => (
                            <tr
                              key={holding.symbol}
                              style={{ borderBottom: "1px solid #eee" }}
                            >
                              <td
                                style={{
                                  padding: "0.75rem",
                                  fontWeight: "500",
                                }}
                              >
                                {holding.symbol}
                              </td>
                              <td style={{ padding: "0.75rem" }}>
                                {holding.name}
                              </td>
                              {data.etfs.map((etf) => (
                                <td
                                  key={etf}
                                  style={{
                                    padding: "0.75rem",
                                    textAlign: "right",
                                  }}
                                >
                                  {holding.weights[etf]?.toFixed(2)}%
                                </td>
                              ))}
                              <td
                                style={{
                                  padding: "0.75rem",
                                  textAlign: "right",
                                  backgroundColor:
                                    index < 10 ? "#eff6ff" : "transparent",
                                  fontWeight: index < 5 ? "bold" : "normal",
                                }}
                              >
                                {holding.minWeight.toFixed(2)}%
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                      <tfoot>
                        <tr
                          style={{
                            backgroundColor: "#f5f5f5",
                            fontWeight: "bold",
                          }}
                        >
                          <td
                            colSpan={2 + data.etfs.length}
                            style={{ padding: "0.75rem", textAlign: "right" }}
                          >
                            Total Core Overlap:
                          </td>
                          <td
                            style={{
                              padding: "0.75rem",
                              textAlign: "right",
                              color: "#0070f3",
                              fontSize: "1.1rem",
                            }}
                          >
                            {data.coreOverlap.totalOverlap.toFixed(2)}%
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

              {data.coreOverlap.sharedHoldings.length === 0 && (
                <div
                  style={{
                    marginTop: "2rem",
                    padding: "1.5rem",
                    backgroundColor: "#fff3cd",
                    borderRadius: "8px",
                    border: "1px solid #ffc107",
                  }}
                >
                  <p style={{ margin: 0, color: "#856404" }}>
                    ⚠️ No holdings are shared across all {data.etfs.length}{" "}
                    ETFs. They have completely different portfolios.
                  </p>
                </div>
              )}
            </div>
          )}

          <h2 style={{ marginBottom: "1rem" }}>Pairwise Overlap Heatmap</h2>
          <p style={{ marginBottom: "1.5rem", color: "#666" }}>
            Values show weighted overlap percentage (0-100%). Darker colors
            indicate higher overlap. Click any cell for details.
          </p>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                borderCollapse: "collapse",
                backgroundColor: "white",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              }}
            >
              <thead>
                <tr>
                  <th
                    style={{
                      padding: "1rem",
                      textAlign: "left",
                      borderBottom: "2px solid #ddd",
                      backgroundColor: "#f5f5f5",
                      fontWeight: "bold",
                      minWidth: "100px",
                    }}
                  >
                    ETF
                  </th>
                  {data.etfs.map((etf) => (
                    <th
                      key={etf}
                      style={{
                        padding: "1rem",
                        textAlign: "center",
                        borderBottom: "2px solid #ddd",
                        backgroundColor: "#f5f5f5",
                        fontWeight: "bold",
                        minWidth: "100px",
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
                        padding: "1rem",
                        fontWeight: "bold",
                        backgroundColor: "#f5f5f5",
                        borderRight: "2px solid #ddd",
                      }}
                    >
                      {etf1}
                    </td>
                    {data.matrix[i].map((value, j) => (
                      <td
                        key={j}
                        onClick={() => handleCellClick(etf1, data.etfs[j])}
                        style={{
                          padding: "1.5rem",
                          textAlign: "center",
                          backgroundColor: getHeatmapColor(value),
                          color: getTextColor(value),
                          fontWeight: i === j ? "bold" : "normal",
                          fontSize: "1.1rem",
                          border: "1px solid #e5e7eb",
                          transition: "all 0.2s",
                          cursor: i === j ? "default" : "pointer",
                        }}
                        title={
                          i === j
                            ? `${etf1}: 100%`
                            : `Click to see ${etf1} vs ${data.etfs[j]} overlap details`
                        }
                        onMouseEnter={(e) => {
                          if (i !== j) {
                            e.currentTarget.style.transform = "scale(1.05)";
                            e.currentTarget.style.boxShadow =
                              "0 4px 8px rgba(0,0,0,0.2)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = "scale(1)";
                          e.currentTarget.style.boxShadow = "none";
                        }}
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
          <div
            style={{
              marginTop: "2rem",
              padding: "1rem",
              backgroundColor: "#f9fafb",
              borderRadius: "8px",
            }}
          >
            <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>Legend</h3>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                flexWrap: "wrap",
              }}
            >
              {[
                { label: "0-20%", color: "#dbeafe" },
                { label: "20-40%", color: "#93c5fd" },
                { label: "40-60%", color: "#60a5fa" },
                { label: "60-80%", color: "#3b82f6" },
                { label: "80-100%", color: "#1e3a8a" },
              ].map(({ label, color }) => (
                <div
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <div
                    style={{
                      width: "40px",
                      height: "20px",
                      backgroundColor: color,
                      border: "1px solid #ddd",
                      borderRadius: "4px",
                    }}
                  />
                  <span style={{ fontSize: "0.875rem" }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Interpretation guide */}
          <div
            style={{
              marginTop: "2rem",
              padding: "1rem",
              backgroundColor: "#eff6ff",
              borderRadius: "8px",
              border: "1px solid #bfdbfe",
            }}
          >
            <h3
              style={{
                marginBottom: "0.5rem",
                fontSize: "1rem",
                color: "#1e40af",
              }}
            >
              📊 How to Read This
            </h3>
            <ul
              style={{
                marginLeft: "1.5rem",
                color: "#1e40af",
                lineHeight: "1.6",
              }}
            >
              <li>
                <strong>High overlap (60-100%)</strong>: Very similar holdings -
                minimal diversification benefit
              </li>
              <li>
                <strong>Medium overlap (30-60%)</strong>: Some shared exposure
                with room for diversification
              </li>
              <li>
                <strong>Low overlap (0-30%)</strong>: Different holdings - good
                diversification potential
              </li>
              <li>
                <strong>Diagonal (100%)</strong>: Each ETF compared to itself
              </li>
              <li>
                <strong>💡 Click any cell</strong> to see detailed overlapping
                holdings
              </li>
            </ul>
          </div>

          {/* Detailed overlap view */}
          {selectedDetail && (
            <div
              id="overlap-details"
              style={{
                marginTop: "3rem",
                padding: "2rem",
                backgroundColor: "#ffffff",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1.5rem",
                }}
              >
                <h2>
                  {selectedDetail.etf1} ↔ {selectedDetail.etf2} Overlap Details
                </h2>
                <button
                  onClick={() => setSelectedDetail(null)}
                  style={{
                    padding: "0.5rem 1rem",
                    fontSize: "0.875rem",
                    backgroundColor: "#6b7280",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Close
                </button>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "1rem",
                  marginBottom: "2rem",
                }}
              >
                <div
                  style={{
                    padding: "1rem",
                    backgroundColor: "#f9fafb",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                    Total Overlap
                  </div>
                  <div
                    style={{
                      fontSize: "1.5rem",
                      fontWeight: "bold",
                      color: "#0070f3",
                    }}
                  >
                    {selectedDetail.overlapPercentage.toFixed(2)}%
                  </div>
                </div>
                <div
                  style={{
                    padding: "1rem",
                    backgroundColor: "#f9fafb",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                    Shared Holdings
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {selectedDetail.totalSharedHoldings}
                  </div>
                </div>
                <div
                  style={{
                    padding: "1rem",
                    backgroundColor: "#f9fafb",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                    Unique to {selectedDetail.etf1}
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {selectedDetail.uniqueHoldings1}
                  </div>
                </div>
                <div
                  style={{
                    padding: "1rem",
                    backgroundColor: "#f9fafb",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", color: "#6b7280" }}>
                    Unique to {selectedDetail.etf2}
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {selectedDetail.uniqueHoldings2}
                  </div>
                </div>
              </div>

              <h3 style={{ marginBottom: "1rem" }}>Overlapping Holdings</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f5f5f5" }}>
                      <th
                        style={{
                          padding: "0.75rem",
                          textAlign: "left",
                          borderBottom: "2px solid #ddd",
                        }}
                      >
                        Symbol
                      </th>
                      <th
                        style={{
                          padding: "0.75rem",
                          textAlign: "left",
                          borderBottom: "2px solid #ddd",
                        }}
                      >
                        Name
                      </th>
                      <th
                        style={{
                          padding: "0.75rem",
                          textAlign: "right",
                          borderBottom: "2px solid #ddd",
                        }}
                      >
                        {selectedDetail.etf1} Weight
                      </th>
                      <th
                        style={{
                          padding: "0.75rem",
                          textAlign: "right",
                          borderBottom: "2px solid #ddd",
                        }}
                      >
                        {selectedDetail.etf2} Weight
                      </th>
                      <th
                        style={{
                          padding: "0.75rem",
                          textAlign: "right",
                          borderBottom: "2px solid #ddd",
                          backgroundColor: "#eff6ff",
                        }}
                      >
                        Overlap Contribution
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedDetail.sharedHoldings.map((holding, index) => (
                      <tr
                        key={holding.symbol}
                        style={{ borderBottom: "1px solid #eee" }}
                      >
                        <td style={{ padding: "0.75rem", fontWeight: "500" }}>
                          {holding.symbol}
                        </td>
                        <td style={{ padding: "0.75rem" }}>{holding.name}</td>
                        <td style={{ padding: "0.75rem", textAlign: "right" }}>
                          {holding.weight1.toFixed(2)}%
                        </td>
                        <td style={{ padding: "0.75rem", textAlign: "right" }}>
                          {holding.weight2.toFixed(2)}%
                        </td>
                        <td
                          style={{
                            padding: "0.75rem",
                            textAlign: "right",
                            backgroundColor:
                              index < 10 ? "#eff6ff" : "transparent",
                            fontWeight: index < 5 ? "bold" : "normal",
                          }}
                        >
                          {holding.overlapContribution.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr
                      style={{ backgroundColor: "#f5f5f5", fontWeight: "bold" }}
                    >
                      <td
                        colSpan={4}
                        style={{ padding: "0.75rem", textAlign: "right" }}
                      >
                        Total Weighted Overlap:
                      </td>
                      <td
                        style={{
                          padding: "0.75rem",
                          textAlign: "right",
                          color: "#0070f3",
                        }}
                      >
                        {selectedDetail.overlapPercentage.toFixed(2)}%
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
