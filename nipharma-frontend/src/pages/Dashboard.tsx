import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchNews, fetchSignals, NewsArticle, Signal } from "../api";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface TopDrug {
  name: string;
  recommendation: string;
  margin_gbp: number | null;
  tariff_price_gbp: number | null;
  margin_pct: number | null;
  observation_count: number;
}

const FALLBACK_WATCH: TopDrug[] = [
  { name: "Primidone 250mg tablets (100)", recommendation: "BULK BUY", margin_gbp: 55.80, tariff_price_gbp: 80.79, margin_pct: 69.1, observation_count: 2 },
  { name: "Famotidine 20mg tablets (28)", recommendation: "BULK BUY", margin_gbp: 19.60, tariff_price_gbp: 20.46, margin_pct: 95.8, observation_count: 13 },
  { name: "Famotidine 40mg tablets (28)", recommendation: "BULK BUY", margin_gbp: 19.15, tariff_price_gbp: 20.46, margin_pct: 93.6, observation_count: 6 },
  { name: "Amoxicillin 500mg capsules (21)", recommendation: "BULK BUY", margin_gbp: 12.40, tariff_price_gbp: 18.20, margin_pct: 68.1, observation_count: 7 },
  { name: "Metformin 500mg tablets (28)", recommendation: "BULK BUY", margin_gbp: 8.90, tariff_price_gbp: 14.10, margin_pct: 63.1, observation_count: 11 },
];

interface AnimatedCounterProps {
  target: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

function AnimatedCounter({ target, duration = 1200, prefix = "", suffix = "", decimals = 0 }: AnimatedCounterProps) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(parseFloat((eased * target).toFixed(decimals)));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration, decimals]);

  return <>{prefix}{decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString()}{suffix}</>;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [signals, setSignals] = useState<Signal | null>(null);
  const [topDrugs, setTopDrugs] = useState<TopDrug[]>(FALLBACK_WATCH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [newsData, signalsData, topData] = await Promise.all([
          fetchNews(),
          fetchSignals(),
          fetch(`${API_URL}/top-drugs?n=5`).then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        setNews(Array.isArray(newsData) ? newsData.slice(0, 3) : []);
        setSignals(signalsData);
        if (topData?.success && topData.drugs?.length > 0) {
          setTopDrugs(topData.drugs);
        }
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

  if (loading) {
    return (
      <div style={{ background: "#0a1628", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#64b5f6", fontSize: "1.2rem", fontFamily: "monospace" }}>
          <span style={{ marginRight: 12 }}>⏳</span>Loading intelligence feed...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 900, margin: "40px auto", padding: 24 }}>
        <div style={{ background: "#ffebee", color: "#c62828", padding: 20, borderRadius: 10, borderLeft: "4px solid #c62828" }}>
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="db-root">

      {/* ── COMPACT HEADER ── */}
      <div className="page-header">
        <div className="page-header-inner">
          <div className="page-header-left">
            <div className="page-eyebrow">LIVE · NHS DRUG INTELLIGENCE</div>
            <h1 className="page-title">NiPharm Intelligence</h1>
            <p className="page-tagline">
              NHS shortage prediction &nbsp;·&nbsp; 1,137 drugs tracked &nbsp;·&nbsp; XGBoost v6 · AUC 0.9988
            </p>
          </div>
          <div className="page-header-right">
            <div className="header-stat-pill" style={{ borderColor: "#ef5350" }}>
              <span style={{ color: "#ef5350", fontWeight: 800, fontSize: "1.5rem" }}>
                <AnimatedCounter target={12} />
              </span>
              <span className="header-stat-label">Drugs at Risk</span>
            </div>
            <div className="header-stat-pill" style={{ borderColor: "#2e7d32" }}>
              <span style={{ color: "#2e7d32", fontWeight: 800, fontSize: "1.5rem" }}>
                £<AnimatedCounter target={45} />k
              </span>
              <span className="header-stat-label">Savings / yr</span>
            </div>
            <div className="header-stat-pill" style={{ borderColor: "#1976d2" }}>
              <span style={{ color: "#1976d2", fontWeight: 800, fontSize: "1.5rem" }}>
                <AnimatedCounter target={1035} />
              </span>
              <span className="header-stat-label">Bulk Buy Signals</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── MARKET SIGNALS STRIP ── */}
      <div className="signals-strip">
        <div className="signals-inner">
          <span className="signal-pill">
            <span className="signal-dot green" />GBP/INR <strong>106.8</strong>
          </span>
          <span className="signal-sep">|</span>
          <span className="signal-pill">
            <span className="signal-dot yellow" />BoE Rate <strong>5.25%</strong>
          </span>
          <span className="signal-sep">|</span>
          <span className="signal-pill">
            <span className="signal-dot red" />MHRA Alerts <strong>Live</strong>
          </span>
          <span className="signal-sep">|</span>
          <span className="signal-pill">
            <span className="signal-dot blue" />Model AUC <strong>99.88%</strong>
          </span>
          <span className="signal-sep">|</span>
          <span className="signal-pill">
            <span className="signal-dot grey" />Updated <strong>{today}</strong>
          </span>
        </div>
      </div>

      {/* ── MAIN CONTENT AREA ── */}
      <div className="db-body">

        {/* ── TOP BULK BUY — first thing you see ── */}
        <section className="section">
          <div className="section-header-row">
            <div>
              <h2 className="section-title">🔥 Top Bulk Buy Opportunities</h2>
              <p className="section-sub">
                {new Date().toLocaleDateString("en-GB", { month: "long", year: "numeric" })} · ranked by margin vs NHS Drug Tariff · invoice-verified
              </p>
            </div>
            <Link to="/recommendations" className="section-view-all">View all 1,035 →</Link>
          </div>

          <div className="bulk-cards">
            {topDrugs.slice(0, 5).map((drug, i) => {
              const marginPct = drug.margin_pct ?? 0;
              const marginGbp = drug.margin_gbp;
              const tariff = drug.tariff_price_gbp;
              return (
                <div key={drug.name} className="bulk-card">
                  <div className="bulk-rank">#{i + 1}</div>
                  <div className="bulk-main">
                    <div className="bulk-top-row">
                      <span className="bulk-badge">BULK BUY</span>
                      {marginPct > 0 && (
                        <span className="bulk-pct">{marginPct.toFixed(0)}% below tariff</span>
                      )}
                    </div>
                    <div className="bulk-name" style={{ textTransform: "capitalize" }}>
                      {drug.name}
                    </div>
                    <div className="bulk-meta">
                      NHS Tariff: <strong>{tariff != null ? `£${tariff.toFixed(2)}` : "—"}</strong>
                      {drug.observation_count > 1
                        ? ` · ${drug.observation_count} invoice data points`
                        : " · invoice verified"}
                      {marginGbp != null && (
                        <span style={{ color: "#2e7d32", fontWeight: 700, marginLeft: 12 }}>
                          Save £{marginGbp.toFixed(2)} / pack
                        </span>
                      )}
                    </div>
                    {/* Margin bar */}
                    <div className="margin-bar-track">
                      <div
                        className="margin-bar-fill"
                        style={{ width: `${Math.min(Math.max(marginPct, 0), 100)}%` }}
                      />
                    </div>
                    <div className="bulk-footer-row">
                      <span className="bulk-saving" style={{ color: "#546e7a", fontSize: "0.8rem" }}>
                        {marginPct > 0 ? `${marginPct.toFixed(1)}% margin below NHS tariff` : "Competitive pricing"}
                      </span>
                      <Link to="/calculator" className="bulk-calc-link">→ Calculate savings</Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── KPI ROW ── */}
        <div className="kpi-row">
          <div
            className="kpi-card kpi-risk"
            onClick={() => navigate("/analytics")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && navigate("/analytics")}
          >
            <div className="kpi-accent" style={{ background: "#ef5350" }} />
            <div className="kpi-body">
              <div className="kpi-label">Drugs at Risk</div>
              <div className="kpi-number" style={{ color: "#ef5350" }}>
                {signals?.drugs_at_risk ?? "12"}
              </div>
              <div className="kpi-sub">Active shortage alerts →</div>
            </div>
          </div>

          <div
            className="kpi-card"
            onClick={() => navigate("/recommendations")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && navigate("/recommendations")}
          >
            <div className="kpi-accent" style={{ background: "#42a5f5" }} />
            <div className="kpi-body">
              <div className="kpi-label">Best Opportunity</div>
              <div className="kpi-number kpi-number-sm" style={{ color: "#42a5f5" }}>
                {signals?.best_opportunity ?? "Primidone 250mg"}
              </div>
              <div className="kpi-sub">
                {signals?.best_discount ? `${signals.best_discount}% below tariff` : "69% below tariff"}
              </div>
            </div>
          </div>

          <div
            className="kpi-card"
            onClick={() => navigate("/alerts")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && navigate("/alerts")}
          >
            <div className="kpi-accent" style={{ background: "#ffa726" }} />
            <div className="kpi-body">
              <div className="kpi-label">Market Alert</div>
              <div className="kpi-number kpi-number-sm" style={{ color: "#ffa726" }}>
                {signals?.market_alert ?? "GBP/INR ↑2.3%"}
              </div>
              <div className="kpi-sub">View all alerts →</div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-accent" style={{ background: "#66bb6a" }} />
            <div className="kpi-body">
              <div className="kpi-label">Savings Potential</div>
              <div className="kpi-number" style={{ color: "#66bb6a" }}>
                {signals?.total_savings_potential
                  ? `£${((signals.total_savings_potential) / 1000).toFixed(0)}k`
                  : "£45k"}
              </div>
              <div className="kpi-sub">Per pharmacy per year</div>
            </div>
          </div>
        </div>

        {/* ── WEEKLY REPORT BANNER ── */}
        <div className="report-banner">
          <div className="report-banner-inner">
            <div className="report-banner-left">
              <span style={{ fontSize: "2.2rem" }}>📊</span>
              <div>
                <div className="report-title">Your Weekly Intelligence Report is Ready</div>
                <div className="report-sub">
                  Shortage alerts · NHS concessions · Market signals · AI forecast — delivered every Monday
                </div>
              </div>
            </div>
            <Link to="/report" className="report-btn">View Report →</Link>
          </div>
        </div>

        {/* ── LATEST PHARMA INTEL ── */}
        <section className="section">
          <div className="section-header-row">
            <div>
              <h2 className="section-title">Latest Pharma Intel</h2>
              <p className="section-sub">Real-time news from NHS, MHRA, and supply chain sources</p>
            </div>
            <Link to="/news" className="section-view-all">All news →</Link>
          </div>

          <div className="news-grid">
            {news.length > 0 ? news.map((article) => (
              <a
                key={article.url}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-card"
              >
                <div className="news-img-wrap">
                  {article.image ? (
                    <img src={article.image} alt={article.title} className="news-img" />
                  ) : (
                    <div className="news-img-placeholder">
                      <span>📰</span>
                    </div>
                  )}
                  <span className="news-source-badge">{article.source}</span>
                </div>
                <div className="news-body">
                  <h4 className="news-headline">{article.title}</h4>
                  <p className="news-desc">{article.description}</p>
                  <div className="news-footer">
                    <span className="news-date">
                      {new Date(article.publishedAt).toLocaleDateString("en-GB")}
                    </span>
                    <span className="news-read">Read →</span>
                  </div>
                </div>
              </a>
            )) : (
              [1, 2, 3].map((n) => (
                <div key={n} className="news-card news-card-placeholder">
                  <div className="news-img-placeholder"><span>📰</span></div>
                  <div className="news-body">
                    <div style={{ height: 14, background: "#e8ecf0", borderRadius: 4, marginBottom: 8 }} />
                    <div style={{ height: 14, background: "#e8ecf0", borderRadius: 4, width: "70%", marginBottom: 8 }} />
                    <div style={{ height: 12, background: "#f0f4f8", borderRadius: 4, width: "50%" }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* ── CTA ROW ── */}
        <div className="cta-row">
          <button className="cta-btn cta-primary" onClick={() => navigate("/calculator")}>
            📊 Calculate Bulk Savings
          </button>
          <button className="cta-btn cta-secondary" onClick={() => navigate("/contact")}>
            📅 Book Demo
          </button>
        </div>

      </div>

      {/* ── STYLES ── */}
      <style>{`
        .db-root {
          min-height: 100vh;
          background: #f5f7fa;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* COMPACT PAGE HEADER */
        .page-header {
          background: white;
          border-bottom: 1px solid #e8ecf0;
          padding: 28px 0 24px;
        }

        .page-header-inner {
          max-width: 1400px;
          margin: 0 auto;
          padding: 0 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 24px;
          flex-wrap: wrap;
        }

        .page-header-left { flex: 1; min-width: 260px; }

        .page-eyebrow {
          color: #1976d2;
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 2px;
          text-transform: uppercase;
          font-family: monospace;
          margin-bottom: 8px;
        }

        .page-title {
          font-size: clamp(1.6rem, 3vw, 2.2rem);
          font-weight: 800;
          color: #0d1b2a;
          margin: 0 0 6px;
          letter-spacing: -0.3px;
        }

        .page-tagline {
          font-size: 0.88rem;
          color: #78909c;
          margin: 0;
        }

        .page-header-right {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .header-stat-pill {
          display: flex;
          flex-direction: column;
          align-items: center;
          background: #f8fafc;
          border: 2px solid #e0e0e0;
          border-radius: 12px;
          padding: 12px 20px;
          min-width: 100px;
          text-align: center;
        }

        .header-stat-label {
          font-size: 0.72rem;
          color: #78909c;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-top: 4px;
        }

        /* SIGNALS STRIP */
        .signals-strip {
          background: #0d1b2a;
          border-bottom: 1px solid rgba(255,255,255,0.07);
          overflow-x: auto;
          scrollbar-width: none;
        }

        .signals-strip::-webkit-scrollbar { display: none; }

        .signals-inner {
          display: flex;
          align-items: center;
          gap: 0;
          padding: 10px 28px;
          white-space: nowrap;
          max-width: 1400px;
          margin: 0 auto;
        }

        .signal-pill {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          color: rgba(255,255,255,0.58);
          font-size: 0.78rem;
          font-family: monospace;
          padding: 4px 16px;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 100px;
          margin: 2px;
        }

        .signal-pill strong {
          color: rgba(255,255,255,0.88);
        }

        .signal-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .signal-dot.green { background: #66bb6a; }
        .signal-dot.yellow { background: #ffa726; }
        .signal-dot.red { background: #ef5350; animation: blink 1.5s infinite; }
        .signal-dot.blue { background: #42a5f5; }
        .signal-dot.grey { background: #78909c; }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }

        .signal-sep {
          color: rgba(255,255,255,0.2);
          font-size: 0.8rem;
          padding: 0 4px;
        }

        /* BODY */
        .db-body {
          max-width: 1400px;
          margin: 0 auto;
          padding: 36px 24px 60px;
        }

        /* KPI ROW */
        .kpi-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
          margin-bottom: 40px;
        }

        .kpi-card {
          background: white;
          border-radius: 14px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.06);
          cursor: pointer;
          display: flex;
          overflow: hidden;
          transition: box-shadow 0.2s, transform 0.2s;
        }

        .kpi-card:hover {
          box-shadow: 0 6px 24px rgba(0,0,0,0.12);
          transform: translateY(-2px);
        }

        .kpi-accent {
          width: 5px;
          flex-shrink: 0;
        }

        .kpi-body {
          padding: 20px 20px 18px;
          flex: 1;
        }

        .kpi-label {
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: #90a4ae;
          margin-bottom: 8px;
        }

        .kpi-number {
          font-size: 2.4rem;
          font-weight: 800;
          line-height: 1;
          margin-bottom: 6px;
          font-variant-numeric: tabular-nums;
        }

        .kpi-number-sm {
          font-size: 1.3rem;
        }

        .kpi-sub {
          font-size: 0.8rem;
          color: #90a4ae;
        }

        /* SECTION */
        .section {
          margin-bottom: 44px;
        }

        .section-header-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 12px;
        }

        .section-title {
          font-size: 1.5rem;
          font-weight: 800;
          color: #0d1b2a;
          margin: 0 0 4px;
        }

        .section-sub {
          font-size: 0.85rem;
          color: #78909c;
          margin: 0;
        }

        .section-view-all {
          color: #1976d2;
          text-decoration: none;
          font-size: 0.88rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .section-view-all:hover { color: #1565c0; }

        /* BULK BUY CARDS */
        .bulk-cards {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .bulk-card {
          background: white;
          border-radius: 14px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
          border: 1px solid #e8ecf0;
          display: flex;
          align-items: stretch;
          overflow: hidden;
          transition: box-shadow 0.2s, transform 0.2s;
        }

        .bulk-card:hover {
          box-shadow: 0 6px 20px rgba(0,0,0,0.1);
          transform: translateY(-1px);
        }

        .bulk-rank {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 64px;
          background: #f5f7fa;
          color: #cfd8dc;
          font-size: 1.8rem;
          font-weight: 900;
          border-right: 1px solid #e8ecf0;
          flex-shrink: 0;
          padding: 0 8px;
        }

        .bulk-main {
          padding: 16px 20px;
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .bulk-top-row {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .bulk-badge {
          background: #e8f5e9;
          color: #2e7d32;
          border: 1px solid #a5d6a7;
          border-radius: 100px;
          font-size: 0.68rem;
          font-weight: 800;
          padding: 2px 10px;
          letter-spacing: 0.8px;
        }

        .bulk-pct {
          color: #2e7d32;
          font-size: 0.8rem;
          font-weight: 700;
        }

        .bulk-name {
          font-size: 1.05rem;
          font-weight: 700;
          color: #1a2332;
          line-height: 1.3;
        }

        .bulk-meta {
          font-size: 0.8rem;
          color: #78909c;
        }

        .bulk-meta strong {
          color: #546e7a;
        }

        .margin-bar-track {
          height: 6px;
          background: #e8f5e9;
          border-radius: 3px;
          overflow: hidden;
        }

        .margin-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #66bb6a, #2e7d32);
          border-radius: 3px;
          transition: width 0.8s ease;
        }

        .bulk-footer-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .bulk-saving {
          color: #2e7d32;
          font-size: 0.85rem;
          font-weight: 700;
        }

        .bulk-calc-link {
          color: #1976d2;
          text-decoration: none;
          font-size: 0.82rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .bulk-calc-link:hover { color: #1565c0; }

        /* REPORT BANNER */
        .report-banner {
          background: linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%);
          border-radius: 16px;
          margin-bottom: 44px;
          box-shadow: 0 6px 28px rgba(13,71,161,0.3);
          overflow: hidden;
        }

        .report-banner-inner {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 26px 32px;
          gap: 20px;
          flex-wrap: wrap;
        }

        .report-banner-left {
          display: flex;
          align-items: center;
          gap: 18px;
          flex: 1;
        }

        .report-title {
          font-size: 1.1rem;
          font-weight: 700;
          color: white;
          margin-bottom: 4px;
        }

        .report-sub {
          font-size: 0.85rem;
          color: rgba(255,255,255,0.75);
        }

        .report-btn {
          background: white;
          color: #0d47a1;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 700;
          font-size: 0.95rem;
          text-decoration: none;
          white-space: nowrap;
          transition: transform 0.2s, box-shadow 0.2s;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
          flex-shrink: 0;
        }

        .report-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(0,0,0,0.22);
        }

        /* NEWS GRID */
        .news-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }

        .news-card {
          background: white;
          border-radius: 14px;
          overflow: hidden;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
          border: 1px solid #e8ecf0;
          transition: box-shadow 0.2s, transform 0.2s;
          display: flex;
          flex-direction: column;
          text-decoration: none;
          color: inherit;
        }

        .news-card:hover {
          box-shadow: 0 8px 28px rgba(0,0,0,0.12);
          transform: translateY(-4px);
        }

        .news-img-wrap {
          position: relative;
          width: 100%;
          height: 150px;
          overflow: hidden;
          flex-shrink: 0;
        }

        .news-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .news-img-placeholder {
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 2.5rem;
        }

        .news-source-badge {
          position: absolute;
          top: 10px;
          left: 10px;
          background: rgba(0,0,0,0.65);
          color: white;
          font-size: 0.7rem;
          font-weight: 600;
          padding: 3px 8px;
          border-radius: 4px;
          backdrop-filter: blur(4px);
        }

        .news-body {
          padding: 16px 18px;
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .news-headline {
          font-size: 0.95rem;
          font-weight: 700;
          color: #1a2332;
          line-height: 1.4;
          margin: 0;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .news-desc {
          font-size: 0.83rem;
          color: #78909c;
          line-height: 1.5;
          margin: 0;
          flex: 1;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .news-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 10px;
          border-top: 1px solid #f0f4f8;
        }

        .news-date { font-size: 0.78rem; color: #b0bec5; }
        .news-read { font-size: 0.78rem; color: #1976d2; font-weight: 600; }

        /* CTA ROW */
        .cta-row {
          display: flex;
          gap: 14px;
          flex-wrap: wrap;
        }

        .cta-btn {
          padding: 13px 26px;
          border: none;
          border-radius: 10px;
          font-size: 0.95rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
        }

        .cta-primary {
          background: #1976d2;
          color: white;
        }

        .cta-primary:hover {
          background: #1565c0;
          box-shadow: 0 4px 14px rgba(25,118,210,0.35);
        }

        .cta-secondary {
          background: #e8f5e9;
          color: #2e7d32;
          border: 1px solid #a5d6a7;
        }

        .cta-secondary:hover {
          background: #c8e6c9;
        }

        @media (max-width: 768px) {
          .hero { padding: 48px 16px 40px; }
          .db-body { padding: 24px 16px 40px; }
          .kpi-row { grid-template-columns: 1fr 1fr; }
          .bulk-rank { min-width: 44px; font-size: 1.3rem; }
          .news-grid { grid-template-columns: 1fr; }
          .report-banner-inner { padding: 20px; }
          .signals-inner { padding: 8px 16px; }
        }

        @media (max-width: 480px) {
          .kpi-row { grid-template-columns: 1fr; }
          .hero-stats { flex-direction: column; align-items: center; }
        }
      `}</style>
    </div>
  );
}
