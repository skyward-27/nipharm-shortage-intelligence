import { Link } from "react-router-dom";

const REPORT_DATA = {
  week: "28 March 2026",
  pharmacy: "Your Pharmacy",
  alerts_count: 6,
  savings_opportunity: 2340,
  concessions_count: 3,
  news_count: 12,
  top_alerts: [
    { drug: "Amoxicillin 500mg", severity: "HIGH", action: "Order 3-month stock from Alliance immediately" },
    { drug: "Metformin 1g", severity: "HIGH", action: "Switch to Metformin 500mg x2 - available" },
    { drug: "Furosemide 40mg", severity: "HIGH", action: "Stock up - Indian supplier issues ongoing" },
    { drug: "Amlodipine 5mg", severity: "MEDIUM", action: "Monitor - alternative brands available" },
    { drug: "Lansoprazole 30mg", severity: "MEDIUM", action: "Switch to Omeprazole if needed" },
  ],
  concessions: [
    { drug: "Amoxicillin 500mg x21", conc_price: 1.89, tariff_price: 1.20, profitable: true },
    { drug: "Metformin 500mg x28", conc_price: 0.73, tariff_price: 0.85, profitable: false },
    { drug: "Omeprazole 20mg x28", conc_price: 1.82, tariff_price: 1.50, profitable: true },
  ],
  market_signals: {
    gbp_inr: 106.8,
    brent_crude: 82,
    india_api_volume_change: -8,
  },
  bulk_opportunities: [
    { drug: "Amoxicillin 500mg", monthly_saving: 340, annual_saving: 4080 },
    { drug: "Omeprazole 20mg", monthly_saving: 180, annual_saving: 2160 },
    { drug: "Metformin 500mg", monthly_saving: 120, annual_saving: 1440 },
  ],
};

export default function WeeklyReport() {
  const severityColor = (sev: string) => {
    if (sev === "HIGH") return "#c62828";
    if (sev === "MEDIUM") return "#f57c00";
    return "#2e7d32";
  };

  const severityBg = (sev: string) => {
    if (sev === "HIGH") return "#ffebee";
    if (sev === "MEDIUM") return "#fff8e1";
    return "#f1f8e9";
  };

  return (
    <div className="wr-page">
      {/* ── REPORT HEADER ── */}
      <div className="wr-header">
        <div className="wr-header-inner">
          <div className="wr-logo-row">
            <span className="wr-logo-icon">📊</span>
            <div>
              <h1 className="wr-title">NIPHARMA WEEKLY INTELLIGENCE REPORT</h1>
              <p className="wr-subtitle">
                Week of {REPORT_DATA.week} &nbsp;•&nbsp; For: {REPORT_DATA.pharmacy}
              </p>
            </div>
          </div>
          <div className="wr-header-actions">
            <button className="wr-btn wr-btn-outline" onClick={() => window.print()}>
              🖨️ Print Report
            </button>
          </div>
        </div>
      </div>

      {/* ── SUMMARY STATS ── */}
      <div className="wr-container">
        <div className="wr-stats-grid">
          <div className="wr-stat-card wr-stat-red">
            <div className="wr-stat-icon">🚨</div>
            <div className="wr-stat-number">{REPORT_DATA.alerts_count}</div>
            <div className="wr-stat-label">New MHRA Alerts</div>
          </div>
          <div className="wr-stat-card wr-stat-green">
            <div className="wr-stat-icon">💰</div>
            <div className="wr-stat-number">£{REPORT_DATA.savings_opportunity.toLocaleString()}</div>
            <div className="wr-stat-label">Savings Opportunity</div>
          </div>
          <div className="wr-stat-card wr-stat-blue">
            <div className="wr-stat-icon">📦</div>
            <div className="wr-stat-number">{REPORT_DATA.concessions_count}</div>
            <div className="wr-stat-label">Drugs on Concession</div>
          </div>
          <div className="wr-stat-card wr-stat-purple">
            <div className="wr-stat-icon">📰</div>
            <div className="wr-stat-number">{REPORT_DATA.news_count}</div>
            <div className="wr-stat-label">News Articles</div>
          </div>
        </div>

        {/* ── SECTION 1: CRITICAL SHORTAGE ALERTS ── */}
        <div className="wr-section">
          <div className="wr-section-header wr-section-header-red">
            <h2>🚨 Critical Shortage Alerts This Week</h2>
            <Link to="/alerts" className="wr-view-all">View all alerts →</Link>
          </div>
          <div className="wr-table-wrap">
            <table className="wr-table">
              <thead>
                <tr>
                  <th>Drug</th>
                  <th>Severity</th>
                  <th>Recommended Action</th>
                </tr>
              </thead>
              <tbody>
                {REPORT_DATA.top_alerts.map((alert, i) => (
                  <tr key={i}>
                    <td className="wr-drug-name">{alert.drug}</td>
                    <td>
                      <span
                        className="wr-badge"
                        style={{
                          background: severityBg(alert.severity),
                          color: severityColor(alert.severity),
                          border: `1px solid ${severityColor(alert.severity)}33`,
                        }}
                      >
                        {alert.severity}
                      </span>
                    </td>
                    <td className="wr-action">{alert.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── SECTION 2: NHS CONCESSIONS ── */}
        <div className="wr-section">
          <div className="wr-section-header wr-section-header-blue">
            <h2>💊 NHS Concessions This Month</h2>
            <span className="wr-note">Green = profitable, Red = loss vs tariff</span>
          </div>
          <div className="wr-table-wrap">
            <table className="wr-table">
              <thead>
                <tr>
                  <th>Drug</th>
                  <th>Concession Price</th>
                  <th>Drug Tariff Price</th>
                  <th>Saving per Pack</th>
                </tr>
              </thead>
              <tbody>
                {REPORT_DATA.concessions.map((c, i) => {
                  const diff = c.conc_price - c.tariff_price;
                  return (
                    <tr key={i} className={c.profitable ? "wr-row-green" : "wr-row-red"}>
                      <td className="wr-drug-name">{c.drug}</td>
                      <td>£{c.conc_price.toFixed(2)}</td>
                      <td>£{c.tariff_price.toFixed(2)}</td>
                      <td className={c.profitable ? "wr-profit" : "wr-loss"}>
                        {diff > 0 ? "+" : ""}£{diff.toFixed(2)}
                        <span className="wr-icon-inline">{c.profitable ? " ✅" : " ⚠️"}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="wr-footnote">
            ✅ Profitable concessions: buy at concession price, dispense, and claim the higher tariff price.
            ⚠️ Loss concessions: you dispense at lower reimbursement — minimise dispensing where possible.
          </p>
        </div>

        {/* ── SECTION 3: MARKET SIGNALS ── */}
        <div className="wr-section">
          <div className="wr-section-header wr-section-header-orange">
            <h2>📈 Market Signals</h2>
            <span className="wr-note">Key economic indicators affecting drug costs</span>
          </div>
          <div className="wr-signals-grid">
            <div className="wr-signal-card">
              <div className="wr-signal-icon">💱</div>
              <div className="wr-signal-label">GBP / INR</div>
              <div className="wr-signal-value">
                {REPORT_DATA.market_signals.gbp_inr} <span className="wr-up">↑</span>
              </div>
              <div className="wr-signal-note">Good for UK imports · Higher Indian API cost risk</div>
            </div>
            <div className="wr-signal-card">
              <div className="wr-signal-icon">🛢️</div>
              <div className="wr-signal-label">Brent Crude</div>
              <div className="wr-signal-value">${REPORT_DATA.market_signals.brent_crude}/barrel</div>
              <div className="wr-signal-note">Moderate transport cost pressure on supply chain</div>
            </div>
            <div className="wr-signal-card">
              <div className="wr-signal-icon">🇮🇳</div>
              <div className="wr-signal-label">India API Export Volume</div>
              <div className="wr-signal-value">
                {REPORT_DATA.market_signals.india_api_volume_change}%{" "}
                <span className="wr-down">↓</span>
              </div>
              <div className="wr-signal-note wr-risk">Risk signal — expect tighter stock on Indian APIs</div>
            </div>
          </div>
        </div>

        {/* ── SECTION 4: BULK BUYING OPPORTUNITIES ── */}
        <div className="wr-section">
          <div className="wr-section-header wr-section-header-green">
            <h2>💰 Bulk Buying Opportunities</h2>
            <Link to="/calculator" className="wr-view-all">Open Calculator →</Link>
          </div>
          <div className="wr-bulk-grid">
            {REPORT_DATA.bulk_opportunities.map((opp, i) => (
              <div key={i} className="wr-bulk-card">
                <div className="wr-bulk-rank">#{i + 1}</div>
                <div className="wr-bulk-drug">{opp.drug}</div>
                <div className="wr-bulk-savings">
                  <div className="wr-bulk-figure">£{opp.monthly_saving}/mo</div>
                  <div className="wr-bulk-annual">£{opp.annual_saving.toLocaleString()}/year</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── SECTION 5: AI FORECAST ── */}
        <div className="wr-section wr-section-ai">
          <div className="wr-section-header wr-section-header-dark">
            <h2>🔮 AI Forecast — Next 2 Weeks</h2>
            <span className="wr-badge wr-badge-ai">Powered by Nipharma AI</span>
          </div>
          <div className="wr-forecast-body">
            <p>
              Based on current supply chain signals, expect continued pressure on{" "}
              <strong>Amoxicillin</strong> and <strong>Furosemide</strong> stocks over the next
              fortnight. Indian API export volumes are down 8%, which historically precedes a 3–6
              week lag in UK wholesaler shortages. The GBP/INR rate has strengthened slightly,
              offering a brief window to lock in favourable pricing on Indian-sourced generics —
              particularly Metformin and Omeprazole.
            </p>
            <p>
              <strong>Recommended action:</strong> Increase 4-week buffer stock on HIGH severity
              drugs this week. Review NHS concession list for profitable arbitrage opportunities —
              Amoxicillin 500mg and Omeprazole 20mg are currently profitable concessions.
            </p>
            <p className="wr-forecast-disclaimer">
              * This forecast is generated using supply chain data, MHRA alerts, and market signals.
              Always verify with your wholesaler before making large stock orders.
            </p>
          </div>
        </div>

        {/* ── CTA: CONTACT ── */}
        <div className="wr-subscribe">
          <div className="wr-subscribe-inner">
            <h2>📅 Want a Personalised Report for Your Pharmacy?</h2>
            <p>
              Contact our team to receive a customised weekly intelligence report tailored to your
              pharmacy's dispensing data and stock profile.
            </p>
            <Link to="/contact" className="wr-btn wr-btn-white">
              Contact Us →
            </Link>
          </div>
        </div>
      </div>

      <style>{`
        @media print {
          .wr-header-actions,
          .wr-subscribe,
          .navbar,
          .footer { display: none !important; }
          .wr-page { background: white; }
        }

        .wr-page {
          background: #f5f7fa;
          min-height: 100vh;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif;
        }

        /* HEADER */
        .wr-header {
          background: linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%);
          color: white;
          padding: 32px 20px;
          box-shadow: 0 4px 16px rgba(13,71,161,0.3);
        }

        .wr-header-inner {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 24px;
          flex-wrap: wrap;
        }

        .wr-logo-row {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .wr-logo-icon {
          font-size: 3rem;
        }

        .wr-title {
          font-size: 1.8rem;
          font-weight: 800;
          margin: 0;
          letter-spacing: -0.5px;
        }

        .wr-subtitle {
          margin: 4px 0 0;
          opacity: 0.85;
          font-size: 1rem;
        }

        .wr-header-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .wr-btn {
          padding: 10px 20px;
          border-radius: 8px;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          text-decoration: none;
          display: inline-block;
          transition: all 0.2s ease;
          border: none;
        }

        .wr-btn-outline {
          background: transparent;
          color: white;
          border: 2px solid rgba(255,255,255,0.7);
        }

        .wr-btn-outline:hover {
          background: rgba(255,255,255,0.15);
          border-color: white;
        }

        .wr-btn-white {
          background: white;
          color: #0d47a1;
        }

        .wr-btn-white:hover {
          background: #e3f2fd;
          transform: translateY(-1px);
        }

        .wr-btn-primary {
          background: #0d47a1;
          color: white;
        }

        .wr-btn-primary:hover {
          background: #0a3d8f;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(13,71,161,0.3);
        }

        /* CONTAINER */
        .wr-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 32px 20px;
        }

        /* STATS GRID */
        .wr-stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
          margin-bottom: 40px;
        }

        .wr-stat-card {
          background: white;
          border-radius: 12px;
          padding: 24px;
          text-align: center;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
          border-top: 4px solid transparent;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .wr-stat-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }

        .wr-stat-red { border-top-color: #c62828; }
        .wr-stat-green { border-top-color: #2e7d32; }
        .wr-stat-blue { border-top-color: #1976d2; }
        .wr-stat-purple { border-top-color: #6a1b9a; }

        .wr-stat-icon { font-size: 2rem; margin-bottom: 8px; }
        .wr-stat-number { font-size: 2rem; font-weight: 800; color: #1a1a1a; margin-bottom: 4px; }
        .wr-stat-label { font-size: 0.85rem; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

        /* SECTIONS */
        .wr-section {
          background: white;
          border-radius: 12px;
          margin-bottom: 28px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
          overflow: hidden;
        }

        .wr-section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 18px 24px;
          border-bottom: 1px solid #f0f0f0;
          flex-wrap: wrap;
          gap: 8px;
        }

        .wr-section-header h2 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 700;
          color: #1a1a1a;
        }

        .wr-section-header-red { background: #fff5f5; border-left: 4px solid #c62828; }
        .wr-section-header-blue { background: #f0f4ff; border-left: 4px solid #1976d2; }
        .wr-section-header-orange { background: #fffbf0; border-left: 4px solid #f57c00; }
        .wr-section-header-green { background: #f0faf0; border-left: 4px solid #2e7d32; }
        .wr-section-header-dark { background: #f5f5f5; border-left: 4px solid #37474f; }

        .wr-view-all {
          color: #1976d2;
          text-decoration: none;
          font-size: 0.9rem;
          font-weight: 600;
        }

        .wr-view-all:hover { color: #0d47a1; text-decoration: underline; }

        .wr-note {
          font-size: 0.85rem;
          color: #888;
        }

        /* TABLE */
        .wr-table-wrap {
          overflow-x: auto;
          padding: 0 24px 16px;
        }

        .wr-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 16px;
        }

        .wr-table th {
          text-align: left;
          padding: 10px 12px;
          background: #f8f9fa;
          color: #555;
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 2px solid #e0e0e0;
        }

        .wr-table td {
          padding: 12px 12px;
          border-bottom: 1px solid #f0f0f0;
          font-size: 0.95rem;
          vertical-align: middle;
        }

        .wr-table tr:last-child td {
          border-bottom: none;
        }

        .wr-drug-name {
          font-weight: 600;
          color: #1a1a1a;
        }

        .wr-action {
          color: #555;
          font-size: 0.9rem;
        }

        .wr-badge {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.5px;
          display: inline-block;
        }

        .wr-badge-ai {
          background: #ede7f6;
          color: #4a148c;
          border: 1px solid #ce93d833;
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .wr-row-green { background: #fafff9; }
        .wr-row-red { background: #fffafa; }

        .wr-profit { color: #2e7d32; font-weight: 700; }
        .wr-loss { color: #c62828; font-weight: 700; }
        .wr-icon-inline { font-size: 0.85rem; }

        .wr-footnote {
          padding: 12px 24px 20px;
          font-size: 0.85rem;
          color: #777;
          line-height: 1.5;
          background: #fafafa;
          border-top: 1px solid #f0f0f0;
          margin: 0;
        }

        /* MARKET SIGNALS */
        .wr-signals-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
          padding: 24px;
        }

        .wr-signal-card {
          background: #fafafa;
          border: 1px solid #e8e8e8;
          border-radius: 10px;
          padding: 20px;
          text-align: center;
        }

        .wr-signal-icon { font-size: 1.8rem; margin-bottom: 8px; }

        .wr-signal-label {
          font-size: 0.8rem;
          color: #888;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 6px;
          font-weight: 600;
        }

        .wr-signal-value {
          font-size: 1.6rem;
          font-weight: 800;
          color: #1a1a1a;
          margin-bottom: 8px;
        }

        .wr-up { color: #2e7d32; }
        .wr-down { color: #c62828; }

        .wr-signal-note {
          font-size: 0.82rem;
          color: #777;
          line-height: 1.4;
        }

        .wr-risk { color: #c62828 !important; font-weight: 600; }

        /* BULK BUYING */
        .wr-bulk-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 16px;
          padding: 24px;
        }

        .wr-bulk-card {
          background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
          border: 1px solid #c8e6c9;
          border-radius: 12px;
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          transition: transform 0.2s ease;
        }

        .wr-bulk-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(46,125,50,0.15);
        }

        .wr-bulk-rank {
          font-size: 1.6rem;
          font-weight: 800;
          color: #1b5e20;
          min-width: 36px;
        }

        .wr-bulk-drug {
          flex: 1;
          font-weight: 600;
          color: #1a1a1a;
          font-size: 1rem;
        }

        .wr-bulk-savings { text-align: right; }

        .wr-bulk-figure {
          font-size: 1.25rem;
          font-weight: 800;
          color: #2e7d32;
        }

        .wr-bulk-annual {
          font-size: 0.82rem;
          color: #4caf50;
          font-weight: 600;
        }

        /* AI FORECAST */
        .wr-section-ai {}

        .wr-forecast-body {
          padding: 24px;
          line-height: 1.7;
          color: #333;
        }

        .wr-forecast-body p {
          margin: 0 0 14px;
        }

        .wr-forecast-body p:last-child {
          margin-bottom: 0;
        }

        .wr-forecast-disclaimer {
          font-size: 0.85rem !important;
          color: #999 !important;
          border-top: 1px solid #f0f0f0;
          padding-top: 12px;
          margin-top: 4px;
        }

        /* SUBSCRIBE */
        .wr-subscribe {
          background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%);
          border-radius: 16px;
          margin-top: 12px;
          overflow: hidden;
        }

        .wr-subscribe-inner {
          padding: 48px 32px;
          text-align: center;
          color: white;
        }

        .wr-subscribe-inner h2 {
          font-size: 1.8rem;
          margin: 0 0 12px;
          font-weight: 800;
        }

        .wr-subscribe-inner p {
          font-size: 1.05rem;
          opacity: 0.9;
          margin: 0 0 28px;
          max-width: 540px;
          margin-left: auto;
          margin-right: auto;
        }

        .wr-subscribe-form {
          display: flex;
          gap: 12px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .wr-email-input {
          padding: 14px 18px;
          border-radius: 8px;
          border: none;
          font-size: 1rem;
          width: 300px;
          max-width: 100%;
          outline: none;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }

        .wr-email-input:focus {
          box-shadow: 0 0 0 3px rgba(255,255,255,0.3);
        }

        .wr-success {
          background: rgba(255,255,255,0.15);
          border: 2px solid rgba(255,255,255,0.5);
          color: white;
          padding: 18px 28px;
          border-radius: 10px;
          font-size: 1.1rem;
          font-weight: 600;
          display: inline-block;
        }

        /* RESPONSIVE */
        @media (max-width: 768px) {
          .wr-title { font-size: 1.2rem; }
          .wr-header-inner { flex-direction: column; align-items: flex-start; }
          .wr-stats-grid { grid-template-columns: 1fr 1fr; }
          .wr-table-wrap { padding: 0 12px 12px; }
          .wr-table td, .wr-table th { padding: 8px; font-size: 0.85rem; }
          .wr-signals-grid { grid-template-columns: 1fr; }
          .wr-bulk-grid { grid-template-columns: 1fr; }
          .wr-subscribe-inner { padding: 32px 20px; }
          .wr-email-input { width: 100%; }
          .wr-subscribe-form { flex-direction: column; align-items: center; }
        }

        @media (max-width: 480px) {
          .wr-stats-grid { grid-template-columns: 1fr; }
          .wr-title { font-size: 1rem; }
        }
      `}</style>
    </div>
  );
}
