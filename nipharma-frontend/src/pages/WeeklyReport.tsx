import { Link } from "react-router-dom";

const SPECIAL_WATCH = [
  { name: "Amoxicillin 500mg Capsules", probability: 78, savings: "22%", reason: "India API disruption · MHRA alert · 3rd consecutive concession" },
  { name: "Amlodipine 10mg Tablets",    probability: 75, savings: "20%", reason: "GBP/INR stress +2.3% · Price +15% YoY · 2 MHRA shortage pubs" },
  { name: "Levothyroxine 100mcg",       probability: 73, savings: "19%", reason: "Demand surge · India sole-source risk · Concession streak 4mo" },
];

const REPORT_DATA = {
  week: "28 March 2026",
  alerts_count: 6,
  savings_opportunity: 2340,
  concessions_count: 3,
  top_alerts: [
    { drug: "Amoxicillin 500mg", severity: "HIGH", action: "Order 3-month stock from Alliance immediately" },
    { drug: "Metformin 1g", severity: "HIGH", action: "Switch to Metformin 500mg x2 — available" },
    { drug: "Furosemide 40mg", severity: "HIGH", action: "Stock up — Indian supplier issues ongoing" },
    { drug: "Amlodipine 5mg", severity: "MEDIUM", action: "Monitor — alternative brands available" },
    { drug: "Lansoprazole 30mg", severity: "MEDIUM", action: "Switch to Omeprazole if needed" },
  ],
  concessions: [
    { drug: "Amoxicillin 500mg x21", conc_price: 1.89, tariff_price: 1.20, profitable: true },
    { drug: "Metformin 500mg x28", conc_price: 0.73, tariff_price: 0.85, profitable: false },
    { drug: "Omeprazole 20mg x28", conc_price: 1.82, tariff_price: 1.50, profitable: true },
  ],
  signals: { gbp_inr: "106.8 ↑", crude: "$82/bbl", india_api: "−8% ⚠️" },
  forecast: [
    "Stock HIGH severity drugs for 4 weeks — Amoxicillin & Furosemide most at risk",
    "GBP/INR window open — lock in pricing on Indian-sourced generics now",
    "Amoxicillin & Omeprazole concessions are profitable — dispense & claim tariff",
  ],
};

const sev = (s: string) => s === "HIGH" ? { bg: "#ffebee", color: "#c62828" } : s === "MEDIUM" ? { bg: "#fff8e1", color: "#e65100" } : { bg: "#e8f5e9", color: "#2e7d32" };

export default function WeeklyReport() {
  return (
    <div className="wr">
      {/* Header */}
      <div className="wr-head">
        <div className="wr-head-left">
          <span className="wr-logo">📊</span>
          <div>
            <div className="wr-title">Weekly Intelligence Brief</div>
            <div className="wr-week">Week of {REPORT_DATA.week}</div>
          </div>
        </div>
        <div className="wr-actions">
          <button className="wr-btn wr-outline" onClick={() => window.print()}>🖨️ Print</button>
        </div>
      </div>

      <div className="wr-body">
        {/* KPI Strip */}
        <div className="wr-kpis">
          <div className="wr-kpi wr-kpi-red">
            <div className="wr-kpi-num">{REPORT_DATA.alerts_count}</div>
            <div className="wr-kpi-label">🚨 MHRA Alerts</div>
          </div>
          <div className="wr-kpi wr-kpi-green">
            <div className="wr-kpi-num">£{REPORT_DATA.savings_opportunity.toLocaleString()}</div>
            <div className="wr-kpi-label">💰 Savings This Week</div>
          </div>
          <div className="wr-kpi wr-kpi-blue">
            <div className="wr-kpi-num">{REPORT_DATA.concessions_count}</div>
            <div className="wr-kpi-label">💊 On Concession</div>
          </div>
          <div className="wr-kpi wr-kpi-amber">
            <div className="wr-kpi-num">{REPORT_DATA.signals.gbp_inr}</div>
            <div className="wr-kpi-label">💱 GBP/INR</div>
          </div>
          <div className="wr-kpi wr-kpi-amber">
            <div className="wr-kpi-num">{REPORT_DATA.signals.india_api}</div>
            <div className="wr-kpi-label">🇮🇳 India API Vol</div>
          </div>
        </div>

        {/* Special Watch Flags */}
        <div className="wr-watch">
          <div className="wr-watch-title">🚨 SPECIAL WATCH — Buy Before Next Month</div>
          <div className="wr-watch-grid">
            {SPECIAL_WATCH.map((d) => (
              <div key={d.name} className="wr-watch-item">
                <div className="wr-watch-top">
                  <span className="wr-watch-tag">BUY NOW</span>
                  <span className="wr-watch-prob">{d.probability}% risk</span>
                  <span className="wr-watch-sav">Save {d.savings}</span>
                </div>
                <div className="wr-watch-name">{d.name}</div>
                <div className="wr-watch-reason">{d.reason}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Two columns */}
        <div className="wr-cols">
          {/* Left: Shortage Alerts */}
          <div className="wr-card">
            <div className="wr-card-head red">
              <span>🚨 Shortage Alerts</span>
              <Link to="/alerts" className="wr-link">View all →</Link>
            </div>
            <table className="wr-table">
              <thead>
                <tr><th>Drug</th><th>Risk</th><th>Action</th></tr>
              </thead>
              <tbody>
                {REPORT_DATA.top_alerts.map((a, i) => (
                  <tr key={i}>
                    <td className="wr-drug">{a.drug}</td>
                    <td>
                      <span className="wr-badge" style={{ background: sev(a.severity).bg, color: sev(a.severity).color }}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="wr-act">{a.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right: Concessions + Forecast */}
          <div className="wr-right-col">
            <div className="wr-card">
              <div className="wr-card-head blue">
                <span>💊 NHS Concessions</span>
                <span className="wr-note">✅ profit &nbsp; ⚠️ loss</span>
              </div>
              <table className="wr-table">
                <thead>
                  <tr><th>Drug</th><th>Conc.</th><th>Tariff</th><th>Diff</th></tr>
                </thead>
                <tbody>
                  {REPORT_DATA.concessions.map((c, i) => {
                    const diff = c.conc_price - c.tariff_price;
                    return (
                      <tr key={i}>
                        <td className="wr-drug">{c.drug}</td>
                        <td>£{c.conc_price.toFixed(2)}</td>
                        <td>£{c.tariff_price.toFixed(2)}</td>
                        <td className={c.profitable ? "wr-profit" : "wr-loss"}>
                          {diff > 0 ? "+" : ""}£{diff.toFixed(2)} {c.profitable ? "✅" : "⚠️"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="wr-card">
              <div className="wr-card-head dark">
                <span>🔮 This Week's Actions</span>
              </div>
              <ul className="wr-forecast">
                {REPORT_DATA.forecast.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media print {
          .wr-actions, .navbar, .footer { display: none !important; }
          .wr { background: white; }
        }

        .wr {
          background: #f4f6f9;
          min-height: 100vh;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        /* HEADER */
        .wr-head {
          background: linear-gradient(135deg, #0d47a1, #1976d2);
          color: white;
          padding: 20px 32px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }
        .wr-head-left { display: flex; align-items: center; gap: 14px; }
        .wr-logo { font-size: 2rem; }
        .wr-title { font-size: 1.4rem; font-weight: 800; }
        .wr-week { font-size: 0.9rem; opacity: 0.8; margin-top: 2px; }
        .wr-actions { display: flex; gap: 10px; }
        .wr-btn {
          padding: 8px 18px; border-radius: 7px; font-size: 0.9rem;
          font-weight: 600; cursor: pointer; border: none; transition: all 0.2s;
        }
        .wr-outline {
          background: transparent; color: white;
          border: 2px solid rgba(255,255,255,0.7);
        }
        .wr-outline:hover { background: rgba(255,255,255,0.15); }
        .wr-white { background: white; color: #0d47a1; }
        .wr-white:hover { background: #e3f2fd; }

        /* BODY */
        .wr-body { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }

        /* KPI STRIP */
        .wr-kpis {
          display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
        }
        .wr-kpi {
          flex: 1; min-width: 140px; background: white; border-radius: 10px;
          padding: 14px 16px; border-top: 3px solid #ddd;
          box-shadow: 0 1px 6px rgba(0,0,0,0.06);
        }
        .wr-kpi-num { font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }
        .wr-kpi-label { font-size: 0.78rem; color: #777; margin-top: 2px; font-weight: 600; }
        .wr-kpi-red { border-top-color: #c62828; }
        .wr-kpi-green { border-top-color: #2e7d32; }
        .wr-kpi-blue { border-top-color: #1976d2; }
        .wr-kpi-amber { border-top-color: #f57c00; }

        /* Special Watch */
        .wr-watch {
          background: #1a0808;
          border: 2px solid #c62828;
          border-radius: 10px;
          padding: 18px 22px;
          margin-bottom: 20px;
        }
        .wr-watch-title {
          color: #ff5252;
          font-size: 0.95rem;
          font-weight: 800;
          letter-spacing: 0.5px;
          margin-bottom: 14px;
          text-transform: uppercase;
        }
        .wr-watch-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 12px;
        }
        .wr-watch-item {
          background: rgba(198,40,40,0.12);
          border: 1px solid rgba(198,40,40,0.35);
          border-radius: 8px;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .wr-watch-top {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .wr-watch-tag {
          background: #c62828;
          color: white;
          font-size: 0.65rem;
          font-weight: 800;
          padding: 2px 8px;
          border-radius: 20px;
          letter-spacing: 0.8px;
        }
        .wr-watch-prob { color: #ff9090; font-size: 0.78rem; font-weight: 700; }
        .wr-watch-sav  { color: #69f0ae; font-size: 0.78rem; font-weight: 700; margin-left: auto; }
        .wr-watch-name { color: white; font-size: 0.9rem; font-weight: 700; }
        .wr-watch-reason { color: rgba(255,255,255,0.6); font-size: 0.76rem; line-height: 1.4; }

        /* TWO COLUMNS */
        .wr-cols {
          display: grid;
          grid-template-columns: 1.4fr 1fr;
          gap: 16px;
          align-items: start;
        }
        .wr-right-col { display: flex; flex-direction: column; gap: 16px; }

        /* CARDS */
        .wr-card {
          background: white; border-radius: 10px;
          box-shadow: 0 1px 6px rgba(0,0,0,0.06); overflow: hidden;
        }
        .wr-card-head {
          display: flex; justify-content: space-between; align-items: center;
          padding: 12px 16px; border-bottom: 1px solid #f0f0f0;
          font-weight: 700; font-size: 0.95rem;
        }
        .red { background: #fff5f5; border-left: 4px solid #c62828; }
        .blue { background: #f0f4ff; border-left: 4px solid #1976d2; }
        .dark { background: #f5f5f5; border-left: 4px solid #37474f; }
        .wr-link {
          color: #1976d2; text-decoration: none; font-size: 0.85rem; font-weight: 600;
        }
        .wr-note { font-size: 0.82rem; color: #888; font-weight: 400; }

        /* TABLE */
        .wr-table { width: 100%; border-collapse: collapse; }
        .wr-table th {
          text-align: left; padding: 8px 12px; font-size: 0.75rem;
          color: #888; text-transform: uppercase; letter-spacing: 0.4px;
          background: #fafafa; border-bottom: 1px solid #eee;
        }
        .wr-table td {
          padding: 9px 12px; border-bottom: 1px solid #f5f5f5;
          font-size: 0.88rem; color: #333;
        }
        .wr-table tr:last-child td { border-bottom: none; }
        .wr-drug { font-weight: 600; color: #1a1a1a; }
        .wr-act { color: #555; font-size: 0.83rem; }
        .wr-badge {
          padding: 2px 8px; border-radius: 10px;
          font-size: 0.72rem; font-weight: 700; white-space: nowrap;
        }
        .wr-profit { color: #2e7d32; font-weight: 700; font-size: 0.88rem; }
        .wr-loss { color: #c62828; font-weight: 700; font-size: 0.88rem; }

        /* FORECAST */
        .wr-forecast {
          margin: 0; padding: 14px 16px 14px 32px; list-style: disc;
        }
        .wr-forecast li {
          font-size: 0.88rem; color: #333; line-height: 1.55;
          padding: 3px 0;
        }

        @media (max-width: 800px) {
          .wr-cols { grid-template-columns: 1fr; }
          .wr-head { padding: 16px 20px; }
          .wr-kpi-num { font-size: 1.2rem; }
        }
      `}</style>
    </div>
  );
}
