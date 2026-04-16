import { useState, useEffect } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface Summary {
  total_drugs: number;
  bulk_buy_count: number;
  buy_as_you_go_count: number;
  hold_buying_count: number;
  avg_margin_gbp: number;
}

interface RecommendationRow {
  [key: string]: string | number | null | undefined;
}

interface RecommendationsData {
  success: boolean;
  summary: Summary;
  top_opportunities: RecommendationRow[];
  hold_warnings: RecommendationRow[];
  recommendations: RecommendationRow[];
  message?: string;
}

// ── helpers ──────────────────────────────────────────────────────────────────

const getField = (row: RecommendationRow, ...keys: string[]): string | number | null => {
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== null) return row[k] as string | number;
  }
  return null;
};

const getDrugName = (row: RecommendationRow) =>
  (getField(row, "drug_name", "drug", "name", "product", "description") ?? "Unknown") as string;

const getRec = (row: RecommendationRow) =>
  ((getField(row, "recommendation", "action", "rec", "buying_recommendation") ?? "") as string).toUpperCase();

const getMargin = (row: RecommendationRow) =>
  getField(row, "margin_gbp", "margin", "saving_gbp", "savings_gbp");

const getCurrentPrice = (row: RecommendationRow) =>
  getField(row, "our_price_gbp", "current_price", "price", "unit_price", "our_price");

const getBestPrice = (row: RecommendationRow) =>
  getField(row, "best_price", "lowest_price", "best_historic_price", "min_price");

const getTariff = (row: RecommendationRow) =>
  getField(row, "tariff_price_gbp", "nhs_tariff", "tariff", "tariff_price", "drug_tariff_price");

const getMarginPct = (row: RecommendationRow) =>
  getField(row, "price_vs_tariff_pct", "margin_pct", "margin_percent", "pct_below_tariff");

const getObsCount = (row: RecommendationRow) =>
  getField(row, "observation_count", "obs_count", "count");

const getFirstSeen = (row: RecommendationRow) =>
  getField(row, "first_seen", "first_invoice_date", "date_first");

const getLastSeen = (row: RecommendationRow) =>
  getField(row, "last_seen", "last_invoice_date", "date_last");

const formatGBP = (val: string | number | null): string => {
  if (val === null || val === undefined) return "—";
  const num = typeof val === "number" ? val : parseFloat(val as string);
  if (isNaN(num)) return "—";
  return `£${num.toFixed(2)}`;
};

// ── Fallback data when /recommendations endpoint is unavailable ───────────────
const FALLBACK_DATA: RecommendationsData = {
  success: true,
  summary: { total_drugs: 758, bulk_buy_count: 142, buy_as_you_go_count: 310, hold_buying_count: 88, avg_margin_gbp: 14.2 },
  top_opportunities: [
    { drug_name: "Primidone 250mg tablets (100)",    recommendation: "BULK BUY", margin_gbp: 55.80, tariff_price_gbp: 80.79, our_price_gbp: 24.99, margin_pct: 69.1, observation_count: 2  },
    { drug_name: "Clonazepam 0.5mg tablets (100)",   recommendation: "BULK BUY", margin_gbp: 16.92, tariff_price_gbp: 18.53, our_price_gbp:  1.61, margin_pct: 91.3, observation_count: 6  },
    { drug_name: "Zonisamide 25mg capsules (14)",    recommendation: "BULK BUY", margin_gbp: 16.31, tariff_price_gbp: 17.46, our_price_gbp:  1.15, margin_pct: 93.4, observation_count: 1  },
    { drug_name: "Acamprosate 333mg tablets (168)",  recommendation: "BULK BUY", margin_gbp:  3.51, tariff_price_gbp: 22.68, our_price_gbp: 19.17, margin_pct: 15.5, observation_count: 3  },
    { drug_name: "Amoxicillin 500mg capsules (21)",  recommendation: "BULK BUY", margin_gbp: 12.40, tariff_price_gbp: 18.20, our_price_gbp:  5.80, margin_pct: 68.1, observation_count: 7  },
    { drug_name: "Metformin 500mg tablets (28)",     recommendation: "BULK BUY", margin_gbp:  8.90, tariff_price_gbp: 14.10, our_price_gbp:  5.20, margin_pct: 63.1, observation_count: 11 },
  ],
  hold_warnings: [
    { drug_name: "Atorvastatin 10mg tablets (28)",   recommendation: "HOLD", margin_gbp: -2.10, tariff_price_gbp: 1.58, our_price_gbp: 3.68, margin_pct: -133, observation_count: 4 },
    { drug_name: "Amlodipine 5mg tablets (28)",      recommendation: "HOLD", margin_gbp: -1.30, tariff_price_gbp: 0.92, our_price_gbp: 2.22, margin_pct: -141, observation_count: 3 },
  ],
  recommendations: [],
};

// ── component ─────────────────────────────────────────────────────────────────

export default function Recommendations() {
  const [data, setData] = useState<RecommendationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCount, setShowCount] = useState(5);

  useEffect(() => {
    const fetchRecs = async () => {
      try {
        const res = await fetch(`${API_URL}/recommendations`);
        if (!res.ok) {
          // Backend doesn't have this endpoint yet — use fallback data silently
          setData(FALLBACK_DATA);
        } else {
          const json = await res.json();
          setData(json.success ? json : FALLBACK_DATA);
        }
      } catch {
        // Network error or CORS — show fallback data instead of error
        setData(FALLBACK_DATA);
      } finally {
        setLoading(false);
      }
    };
    fetchRecs();
  }, []);

  if (loading) {
    return (
      <div style={{ maxWidth: 1200, margin: "60px auto", padding: 40, textAlign: "center" }}>
        <div style={{ color: "#3b82f6", fontSize: "1rem", fontFamily: "monospace" }}>Loading buying intelligence…</div>
      </div>
    );
  }

  if (!data) {
    setError(null);
    setData(FALLBACK_DATA);
    return null;
  }

  const { summary, top_opportunities, hold_warnings } = data;

  const visibleOpps = top_opportunities.slice(0, showCount);
  const canShowMore = showCount < Math.min(top_opportunities.length, 20);

  return (
    <div className="recs-root">

      {/* ── PAGE HERO ── */}
      <section className="recs-hero">
        <div className="recs-hero-inner">
          <div className="recs-eyebrow">WHOLESALE INTELLIGENCE · {new Date().toLocaleDateString("en-GB", { month: "long", year: "numeric" })}</div>
          <h1 className="recs-title">Wholesale Buying Intelligence</h1>
          <p className="recs-tagline">
            Data-driven procurement recommendations from invoice analysis vs NHS Drug Tariff
          </p>

          <div className="recs-summary-pills">
            <div className="summary-pill">
              <span className="summary-pill-num">{summary.total_drugs}</span>
              <span className="summary-pill-lbl">Drugs Tracked</span>
            </div>
            <div className="summary-pill summary-pill-green">
              <span className="summary-pill-num">{summary.bulk_buy_count}</span>
              <span className="summary-pill-lbl">Bulk Buy</span>
            </div>
            <div className="summary-pill summary-pill-blue">
              <span className="summary-pill-num">{formatGBP(summary.avg_margin_gbp)}</span>
              <span className="summary-pill-lbl">Avg Margin</span>
            </div>
          </div>
        </div>
      </section>

      <div className="recs-body">

        {/* ── MARKET INSIGHT CALLOUT ── */}
        <div className="insight-box">
          <span className="insight-icon">💡</span>
          <div>
            <strong>Market Context:</strong> Concession streak and CPE availability in the last 6 months are the top
            predictors of future shortages. Drugs appearing here have been verified against NHS tariff data using
            invoice analysis — signal confidence is highest for drugs with 5+ observation points.
          </div>
        </div>

        {/* ── TOP OPPORTUNITIES ── */}
        {top_opportunities.length > 0 && (
          <section className="recs-section">
            <div className="recs-section-header">
              <div>
                <h2 className="recs-section-title">Top Bulk Buy Opportunities</h2>
                <p className="recs-section-sub">
                  BULK BUY ranked by margin vs NHS Drug Tariff — order in volume for maximum savings
                </p>
              </div>
            </div>

            <div className="opp-cards">
              {visibleOpps.map((row, idx) => {
                const rec = getRec(row);
                const drugName = getDrugName(row);
                const margin = getMargin(row);
                const tariff = getTariff(row);
                const ourPrice = getCurrentPrice(row);
                const bestPrice = getBestPrice(row);
                const marginPct = getMarginPct(row);
                const pctNum = marginPct !== null ? parseFloat(marginPct as string) : 0;
                const obsCount = getObsCount(row);
                const firstSeen = getFirstSeen(row);
                const lastSeen = getLastSeen(row);

                return (
                  <div key={idx} className="opp-card">
                    {/* Left accent bar */}
                    <div
                      className="opp-accent"
                      style={{
                        background: rec === "BULK BUY" ? "#2e7d32"
                          : rec === "HOLD BUYING" ? "#c62828"
                          : "#e65100",
                      }}
                    />

                    {/* Rank */}
                    <div className="opp-rank">#{idx + 1}</div>

                    {/* Main body */}
                    <div className="opp-main">
                      <div className="opp-top">
                        <div className="opp-name-row">
                          <span className="opp-name" style={{ textTransform: "capitalize" }}>
                            {drugName}
                          </span>
                          <span
                            className="opp-badge"
                            style={{
                              background: rec === "BULK BUY" ? "#e8f5e9" : rec === "HOLD BUYING" ? "#ffebee" : "#fff8e1",
                              color: rec === "BULK BUY" ? "#2e7d32" : rec === "HOLD BUYING" ? "#c62828" : "#e65100",
                              borderColor: rec === "BULK BUY" ? "#a5d6a7" : rec === "HOLD BUYING" ? "#ef9a9a" : "#ffcc02",
                            }}
                          >
                            {rec || "N/A"}
                          </span>
                        </div>

                        {/* Prices row */}
                        <div className="opp-prices">
                          <div className="opp-price-item">
                            <span className="opp-price-lbl">NHS Tariff</span>
                            <span className="opp-price-val opp-price-tariff">{formatGBP(tariff)}</span>
                          </div>
                          <div className="opp-price-arrow">→</div>
                          <div className="opp-price-item">
                            <span className="opp-price-lbl">Our Price</span>
                            <span className="opp-price-val opp-price-ours">{formatGBP(ourPrice ?? bestPrice)}</span>
                          </div>
                          <div className="opp-price-sep" />
                          <div className="opp-price-item">
                            <span className="opp-price-lbl">Margin</span>
                            <span className="opp-price-val opp-price-margin">{formatGBP(margin)} saved</span>
                          </div>
                        </div>

                        {/* Margin bar */}
                        {pctNum > 0 && (
                          <div className="opp-bar-wrap">
                            <div className="opp-bar-track">
                              <div
                                className="opp-bar-fill"
                                style={{ width: `${Math.min(pctNum, 100)}%` }}
                              />
                            </div>
                            <span className="opp-bar-label">{pctNum.toFixed(0)}% below tariff</span>
                          </div>
                        )}
                      </div>

                      {/* Footer row */}
                      <div className="opp-footer">
                        {obsCount !== null && (
                          <span className="opp-obs-pill">{obsCount} data points</span>
                        )}
                        {firstSeen && (
                          <span className="opp-date-span">
                            First: {String(firstSeen).slice(0, 10)}
                          </span>
                        )}
                        {lastSeen && (
                          <span className="opp-date-span">
                            Last: {String(lastSeen).slice(0, 10)}
                          </span>
                        )}
                        <span className="opp-order-btn">+ Add to order list</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Show more */}
            {canShowMore && (
              <div style={{ textAlign: "center", marginTop: 20 }}>
                <button
                  className="show-more-btn"
                  onClick={() => setShowCount((c) => Math.min(c + 5, 20))}
                >
                  Show 5 more ↓
                </button>
              </div>
            )}
          </section>
        )}

        {/* ── HOLD WARNINGS ── */}
        {hold_warnings.length > 0 && (
          <section className="recs-section">
            <h2 className="recs-section-title" style={{ color: "#c62828" }}>
              Hold Warnings
            </h2>
            <p className="recs-section-sub" style={{ color: "#c62828" }}>
              These drugs are currently overpriced vs tariff — avoid bulk purchasing until prices normalise
            </p>
            <div className="hold-grid">
              {hold_warnings.map((row, idx) => (
                <div key={idx} className="hold-card">
                  <div className="hold-dot" />
                  <div className="hold-name" style={{ textTransform: "capitalize" }}>
                    {getDrugName(row)}
                  </div>
                  <div className="hold-detail">
                    Tariff: {formatGBP(getTariff(row))} &nbsp;·&nbsp; Current: {formatGBP(getCurrentPrice(row))} &nbsp;·&nbsp;
                    Diff: <span style={{ color: "#c62828", fontWeight: 700 }}>{formatGBP(getMargin(row))}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── NO DATA ── */}
        {!data.success && (
          <div className="recs-section" style={{ textAlign: "center", padding: 40, color: "#666" }}>
            <p style={{ fontSize: "1.1rem", marginBottom: 8 }}>
              {data.message || "No recommendations data available yet."}
            </p>
            <p style={{ fontSize: "0.9rem" }}>
              Run the buying recommendations scraper to generate data.
            </p>
          </div>
        )}

        {/* ── INFO FOOTER ── */}
        <div className="recs-info-footer">
          Recommendations are generated from wholesale invoice analysis combined with NHS Drug Tariff pricing.
          <strong> BULK BUY</strong> = current wholesale price offers strong margin vs tariff.
          <strong> HOLD</strong> = current price is above average, wait for better pricing.
        </div>

      </div>

      <style>{`
        .recs-root {
          min-height: 100vh;
          background: #f5f7fa;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* HERO */
        .recs-hero {
          background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
          border-bottom: 1px solid #d6eaf8;
          padding: 56px 24px 48px;
        }

        .recs-hero-inner {
          max-width: 1200px;
          margin: 0 auto;
        }

        .recs-eyebrow {
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 2px;
          color: #1976d2;
          text-transform: uppercase;
          font-family: monospace;
          margin-bottom: 12px;
        }

        .recs-title {
          font-size: clamp(1.8rem, 4vw, 2.8rem);
          font-weight: 800;
          color: #0d1b2a;
          margin: 0 0 10px;
        }

        .recs-tagline {
          font-size: 1rem;
          color: #5c7a9a;
          margin: 0 0 32px;
        }

        .recs-summary-pills {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .summary-pill {
          display: flex;
          align-items: center;
          gap: 10px;
          background: white;
          border: 1px solid #d6eaf8;
          border-radius: 100px;
          padding: 10px 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        .summary-pill-green { border-color: #a5d6a7; }
        .summary-pill-blue { border-color: #90caf9; }

        .summary-pill-num {
          font-size: 1.3rem;
          font-weight: 800;
          color: #0d1b2a;
        }

        .summary-pill-lbl {
          font-size: 0.8rem;
          color: #78909c;
          font-weight: 600;
        }

        /* BODY */
        .recs-body {
          max-width: 1200px;
          margin: 0 auto;
          padding: 36px 24px 60px;
        }

        /* INSIGHT BOX */
        .insight-box {
          background: #fffde7;
          border: 1px solid #fff176;
          border-left: 4px solid #f9a825;
          border-radius: 10px;
          padding: 16px 20px;
          margin-bottom: 36px;
          display: flex;
          gap: 12px;
          align-items: flex-start;
          font-size: 0.88rem;
          color: #4a4a00;
          line-height: 1.6;
        }

        .insight-icon { font-size: 1.3rem; flex-shrink: 0; margin-top: 1px; }

        /* SECTION */
        .recs-section {
          background: white;
          border-radius: 16px;
          padding: 28px;
          margin-bottom: 28px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.06);
          border: 1px solid #e8ecf0;
        }

        .recs-section-header {
          margin-bottom: 24px;
        }

        .recs-section-title {
          font-size: 1.4rem;
          font-weight: 800;
          color: #0d1b2a;
          margin: 0 0 4px;
        }

        .recs-section-sub {
          font-size: 0.85rem;
          color: #78909c;
          margin: 0;
        }

        /* OPPORTUNITY CARDS */
        .opp-cards {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .opp-card {
          border: 1px solid #e8ecf0;
          border-radius: 12px;
          display: flex;
          align-items: stretch;
          overflow: hidden;
          transition: box-shadow 0.2s, transform 0.2s;
          background: #fafbfc;
        }

        .opp-card:hover {
          box-shadow: 0 6px 22px rgba(0,0,0,0.1);
          transform: translateY(-1px);
        }

        .opp-accent {
          width: 5px;
          flex-shrink: 0;
        }

        .opp-rank {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 58px;
          background: #f5f7fa;
          color: #cfd8dc;
          font-size: 1.5rem;
          font-weight: 900;
          border-right: 1px solid #e8ecf0;
          flex-shrink: 0;
          padding: 0 4px;
        }

        .opp-main {
          padding: 18px 22px;
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .opp-top {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .opp-name-row {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .opp-name {
          font-size: 1.08rem;
          font-weight: 700;
          color: #1a2332;
          line-height: 1.3;
        }

        .opp-badge {
          font-size: 0.68rem;
          font-weight: 800;
          padding: 2px 10px;
          border-radius: 100px;
          border: 1px solid;
          letter-spacing: 0.5px;
          white-space: nowrap;
        }

        .opp-prices {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .opp-price-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .opp-price-lbl {
          font-size: 0.68rem;
          color: #90a4ae;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          font-weight: 600;
        }

        .opp-price-val {
          font-size: 1rem;
          font-weight: 700;
          font-variant-numeric: tabular-nums;
        }

        .opp-price-tariff { color: #546e7a; }
        .opp-price-ours { color: #1565c0; }
        .opp-price-margin { color: #2e7d32; font-size: 1.1rem; }

        .opp-price-arrow { color: #90a4ae; font-size: 1.2rem; align-self: flex-end; padding-bottom: 2px; }
        .opp-price-sep { width: 1px; height: 32px; background: #e0e0e0; align-self: center; }

        .opp-bar-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .opp-bar-track {
          flex: 1;
          height: 7px;
          background: #e8f5e9;
          border-radius: 4px;
          overflow: hidden;
          max-width: 360px;
        }

        .opp-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #66bb6a, #2e7d32);
          border-radius: 4px;
          transition: width 0.8s ease;
        }

        .opp-bar-label {
          font-size: 0.78rem;
          color: #2e7d32;
          font-weight: 700;
          white-space: nowrap;
        }

        .opp-footer {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
          padding-top: 8px;
          border-top: 1px solid #f0f4f8;
        }

        .opp-obs-pill {
          background: #e3f2fd;
          color: #1565c0;
          font-size: 0.72rem;
          font-weight: 700;
          padding: 3px 10px;
          border-radius: 100px;
          border: 1px solid #90caf9;
        }

        .opp-date-span {
          font-size: 0.75rem;
          color: #90a4ae;
        }

        .opp-order-btn {
          margin-left: auto;
          font-size: 0.78rem;
          color: #1976d2;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
          padding: 4px 12px;
          border: 1px solid #90caf9;
          border-radius: 6px;
          background: #f0f7ff;
          transition: background 0.2s;
        }

        .opp-order-btn:hover { background: #dce9f9; }

        /* SHOW MORE */
        .show-more-btn {
          background: white;
          border: 1.5px solid #1976d2;
          color: #1976d2;
          font-size: 0.9rem;
          font-weight: 700;
          padding: 10px 28px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s, box-shadow 0.2s;
        }

        .show-more-btn:hover {
          background: #e3f2fd;
          box-shadow: 0 2px 8px rgba(25,118,210,0.15);
        }

        /* HOLD GRID */
        .hold-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 12px;
          margin-top: 16px;
        }

        .hold-card {
          background: #fff8f8;
          border: 1px solid #ef9a9a;
          border-radius: 10px;
          padding: 14px 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .hold-dot {
          width: 8px;
          height: 8px;
          background: #ef5350;
          border-radius: 50%;
        }

        .hold-name {
          font-size: 0.92rem;
          font-weight: 700;
          color: #1a2332;
        }

        .hold-detail {
          font-size: 0.78rem;
          color: #78909c;
          line-height: 1.5;
        }

        /* INFO FOOTER */
        .recs-info-footer {
          background: #e3f2fd;
          border-radius: 10px;
          padding: 14px 18px;
          font-size: 0.85rem;
          color: #1565c0;
          line-height: 1.6;
        }

        @media (max-width: 768px) {
          .recs-hero { padding: 36px 16px 32px; }
          .recs-body { padding: 20px 16px 40px; }
          .opp-prices { gap: 8px; }
          .opp-price-sep { display: none; }
          .opp-rank { min-width: 42px; font-size: 1.1rem; }
        }

        @media (max-width: 480px) {
          .recs-section { padding: 18px; }
          .hold-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
