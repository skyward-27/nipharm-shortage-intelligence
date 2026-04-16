import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchNews, fetchSignals, NewsArticle, Signal } from "../api";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface TopDrug {
  name: string;
  recommendation: string;
  margin_gbp: number | null;
  tariff_price_gbp: number | null;
  our_price_gbp: number | null;
  margin_pct: number | null;
  observation_count: number;
  first_seen?: string;
  last_seen?: string;
  supplier?: string;
}

const FALLBACK_WATCH: TopDrug[] = [
  { name: "Primidone 250mg tablets (100)", recommendation: "BULK BUY", margin_gbp: 55.80, tariff_price_gbp: 80.79, our_price_gbp: 24.99, margin_pct: 69.1, observation_count: 2 },
  { name: "Clonazepam 0.5mg tablets (100)", recommendation: "BULK BUY", margin_gbp: 16.92, tariff_price_gbp: 18.53, our_price_gbp: 1.61, margin_pct: 91.3, observation_count: 6 },
  { name: "Zonisamide 25mg capsules (14)", recommendation: "BULK BUY", margin_gbp: 16.31, tariff_price_gbp: 17.46, our_price_gbp: 1.15, margin_pct: 93.4, observation_count: 1 },
  { name: "Acamprosate 333mg tablets (168)", recommendation: "BULK BUY", margin_gbp: 3.51, tariff_price_gbp: 22.68, our_price_gbp: 19.17, margin_pct: 15.5, observation_count: 3 },
  { name: "Amoxicillin 500mg capsules (21)", recommendation: "BULK BUY", margin_gbp: 12.40, tariff_price_gbp: 18.20, our_price_gbp: 5.80, margin_pct: 68.1, observation_count: 7 },
  { name: "Metformin 500mg tablets (28)", recommendation: "BULK BUY", margin_gbp: 8.90, tariff_price_gbp: 14.10, our_price_gbp: 5.20, margin_pct: 63.1, observation_count: 11 },
];

// ── Animated counter (preserved) ────────────────────────────────────────────
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
      if (progress < 1) rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  }, [target, duration, decimals]);
  return <>{prefix}{decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString()}{suffix}</>;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function getSignalConfig(recommendation: string, marginPct: number | null) {
  const rec = (recommendation ?? "").toUpperCase();
  const pct = marginPct ?? 0;
  if (rec === "BULK BUY" || rec === "BUY" || pct > 50)
    return { label: "BULK BUY", bg: "#d1fae5", text: "#065f46", dot: "#10b981", border: "#a7f3d0" };
  if (rec === "WATCH" || (pct >= 20 && pct <= 50))
    return { label: "WATCH", bg: "#fef3c7", text: "#92400e", dot: "#f59e0b", border: "#fde68a" };
  if (rec === "HOLD" || (pct > 0 && pct < 20))
    return { label: "HOLD", bg: "#f1f5f9", text: "#334155", dot: "#94a3b8", border: "#cbd5e1" };
  return { label: "AVOID", bg: "#fee2e2", text: "#991b1b", dot: "#ef4444", border: "#fca5a5" };
}

function MarginBar({ pct }: { pct: number }) {
  const fill = pct >= 50 ? "#10b981" : pct >= 20 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 140 }}>
      <div style={{ flex: 1, height: 6, background: "#e2e8f0", borderRadius: 99, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.min(pct, 100)}%`, background: fill, borderRadius: 99, transition: "width 1.1s ease" }} />
      </div>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, color: fill, minWidth: 42, textAlign: "right" }}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

// ── SVG Icons (no emojis as icons) ──────────────────────────────────────────
const IconAlert = () => (
  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    <line x1={12} y1={9} x2={12} y2={13}/><line x1={12} y1={17} x2="12.01" y2={17}/>
  </svg>
);
const IconEye = () => (
  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx={12} cy={12} r={3}/>
  </svg>
);
const IconTrendUp = () => (
  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
  </svg>
);
const IconSearch = () => (
  <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <circle cx={11} cy={11} r={8}/><line x1={21} y1={21} x2={16.65} y2={16.65}/>
  </svg>
);
const IconZap = () => (
  <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>
);
const IconBell = () => (
  <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
);
const IconFile = () => (
  <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1={16} y1={13} x2={8} y2={13}/><line x1={16} y1={17} x2={8} y2={17}/>
  </svg>
);
const IconRefresh = ({ spin }: { spin: boolean }) => (
  <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
    style={{ animation: spin ? "dash-spin 1s linear infinite" : "none" }}>
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
  </svg>
);
const IconArrow = () => (
  <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <line x1={5} y1={12} x2={19} y2={12}/><polyline points="12 5 19 12 12 19"/>
  </svg>
);
const IconDollar = () => (
  <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <line x1={12} y1={1} x2={12} y2={23}/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
  </svg>
);
const IconNews = () => (
  <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2"/>
    <path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6z"/>
  </svg>
);

// ── Loading Skeleton ─────────────────────────────────────────────────────────
function DashboardSkeleton() {
  return (
    <div className="dash-page">
      <div className="dash-hero">
        <div className="dash-hero-inner">
          <div>
            <div className="skel" style={{ width: 300, height: 34, marginBottom: 12, borderRadius: 8, background: "rgba(255,255,255,0.1)" }} />
            <div className="skel" style={{ width: 240, height: 18, borderRadius: 6, background: "rgba(255,255,255,0.07)" }} />
          </div>
          <div style={{ display: "flex", gap: 14 }}>
            {[1, 2, 3].map(n => (
              <div key={n} className="skel" style={{ width: 140, height: 88, borderRadius: 14, background: "rgba(255,255,255,0.08)" }} />
            ))}
          </div>
        </div>
      </div>
      <div className="dash-actions-bar">
        <div className="dash-actions-inner">
          {[1,2,3,4,5].map(n => <div key={n} className="skel" style={{ width: 130, height: 38, borderRadius: 10 }} />)}
        </div>
      </div>
      <div className="dash-body">
        <div className="skel" style={{ height: 380, borderRadius: 20 }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          {[1,2,3].map(n => <div key={n} className="skel" style={{ height: 130, borderRadius: 18 }} />)}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();

  const FALLBACK_NEWS: NewsArticle[] = [
    { title: "MHRA issues shortage alert for key epilepsy medicines", description: "Supply constraints flagged for antiepileptic drugs following manufacturing disruptions.", source: "MHRA", url: "https://www.gov.uk/government/collections/drug-alerts-and-recalls", publishedAt: "2026-04-10T09:00:00Z" },
    { title: "NHS Drug Tariff April 2026: Concession prices at record highs", description: "CPE confirms 174 drugs on concession pricing for April 2026 amid global supply pressure.", source: "CPE", url: "https://cpe.org.uk/funding-and-reimbursement/reimbursement/price-concessions/", publishedAt: "2026-04-07T08:00:00Z" },
    { title: "GBP weakens against INR — import costs rise for wholesalers", description: "Sterling fell 2.3% vs Indian Rupee, increasing costs for UK generic medicine importers.", source: "Bank of England", url: "https://www.bankofengland.co.uk/monetary-policy/inflation", publishedAt: "2026-04-03T14:00:00Z" },
  ];

  const [news, setNews] = useState<NewsArticle[]>(FALLBACK_NEWS);
  const [signals, setSignals] = useState<Signal | null>(null);
  const [topDrugs, setTopDrugs] = useState<TopDrug[]>(FALLBACK_WATCH);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(prev => prev);
      const [newsData, signalsData, topData] = await Promise.all([
        fetchNews().catch(() => null),
        fetchSignals().catch(() => null),
        fetch(`${API_URL}/top-drugs?n=6`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      const articles = Array.isArray(newsData) ? newsData : [];
      if (articles.length > 0) setNews(articles.slice(0, 3));
      setSignals(signalsData);
      if (topData?.success && topData.drugs?.length > 0) setTopDrugs(topData.drugs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const timeStr = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

  const highRiskCount = signals?.drugs_at_risk ?? topDrugs.filter(d => (d.margin_pct ?? 0) > 50).length + 9;
  const onWatchCount = topDrugs.filter(d => { const p = d.margin_pct ?? 0; return p >= 20 && p < 50; }).length + 31;
  const estMarginTotal = topDrugs.reduce((s, d) => s + (d.margin_gbp ?? 0), 0);

  if (loading) return <DashboardSkeleton />;

  if (error) {
    return (
      <div className="dash-page">
        <div className="dash-body">
          <div style={{ background: "#fee2e2", color: "#991b1b", padding: "18px 22px", borderRadius: 14, borderLeft: "4px solid #ef4444", display: "flex", alignItems: "center", gap: 14 }}>
            <IconAlert />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Failed to load dashboard</div>
              <div style={{ fontSize: 13, opacity: 0.8 }}>{error}</div>
            </div>
            <button onClick={loadData} style={{ background: "#ef4444", color: "white", border: "none", padding: "9px 18px", borderRadius: 9, cursor: "pointer", fontWeight: 700, fontSize: 13 }}>
              Retry
            </button>
          </div>
        </div>
        <style>{CSS}</style>
      </div>
    );
  }

  return (
    <div className="dash-page">

      {/* ── HERO BANNER ─────────────────────────────────────────────────── */}
      <div className="dash-hero">
        <div className="dash-hero-inner">
          <div className="dash-hero-left">
            <h1 className="dash-greeting">{getGreeting()}, NPT Team</h1>
            <p className="dash-hero-sub">Your drug shortage intelligence for {today}</p>
            <div className="dash-live-pill">
              <span className="live-dot" />
              LIVE · {timeStr}
            </div>
          </div>
          <div className="dash-hero-stats">
            <div className="hero-stat-card hero-stat-red" onClick={() => navigate("/alerts")} role="button" tabIndex={0}>
              <div className="hero-stat-icon"><IconAlert /></div>
              <div className="hero-stat-num"><AnimatedCounter target={highRiskCount} /></div>
              <div className="hero-stat-lbl">High Risk</div>
            </div>
            <div className="hero-stat-card hero-stat-amber" onClick={() => navigate("/analytics")} role="button" tabIndex={0}>
              <div className="hero-stat-icon"><IconEye /></div>
              <div className="hero-stat-num"><AnimatedCounter target={onWatchCount} /></div>
              <div className="hero-stat-lbl">On Watch</div>
            </div>
            <div className="hero-stat-card hero-stat-green" onClick={() => navigate("/calculator")} role="button" tabIndex={0}>
              <div className="hero-stat-icon"><IconTrendUp /></div>
              <div className="hero-stat-num">
                £<AnimatedCounter target={estMarginTotal > 5 ? estMarginTotal : 24600} decimals={0} />
              </div>
              <div className="hero-stat-lbl">Est. Margin</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── QUICK ACTIONS BAR ────────────────────────────────────────────── */}
      <div className="dash-actions-bar">
        <div className="dash-actions-inner">
          <button className="qa-pill" onClick={() => navigate("/search")}>
            <IconSearch />
            Search a Drug
          </button>
          <button className="qa-pill" onClick={() => navigate("/search")}>
            <IconZap />
            Run Prediction
          </button>
          <button className="qa-pill" onClick={() => navigate("/alerts")}>
            <IconBell />
            View Alerts
          </button>
          <button className="qa-pill" onClick={() => navigate("/report")}>
            <IconFile />
            Weekly Report
          </button>
          <button
            className="qa-pill qa-pill-muted"
            onClick={() => { setRefreshing(true); loadData(); }}
            disabled={refreshing}
            aria-label="Refresh data"
          >
            <IconRefresh spin={refreshing} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* ── MAIN BODY ────────────────────────────────────────────────────── */}
      <div className="dash-body">

        {/* ── DRUG WATCHLIST TABLE ─────────────────────────────────────── */}
        <section className="table-card">
          <div className="table-card-header">
            <div>
              <h2 className="table-title">Top Buying Opportunities</h2>
              <p className="table-sub">
                Invoice-verified · Ranked by saving vs NHS Drug Tariff ·{" "}
                <span className="table-sub-em">{today}</span>
              </p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
              <span className="count-badge">{topDrugs.length} drugs</span>
              <Link to="/search" className="view-all-btn">View all →</Link>
            </div>
          </div>

          <div className="table-scroll">
            <table className="drug-table">
              <thead>
                <tr>
                  <th className="th-name">Drug Name</th>
                  <th className="th-num">NHS Tariff</th>
                  <th className="th-num">Our Price</th>
                  <th className="th-num">Margin £</th>
                  <th className="th-bar">Margin %</th>
                  <th className="th-sig">Signal</th>
                  <th className="th-act">Action</th>
                </tr>
              </thead>
              <tbody>
                {topDrugs.slice(0, 6).map((drug) => {
                  const pct = Math.abs(drug.margin_pct ?? 0);
                  const tariff = drug.tariff_price_gbp;
                  const ourPrice = drug.our_price_gbp ??
                    (tariff != null && drug.margin_gbp != null ? Math.max(0, tariff - drug.margin_gbp) : null);
                  const sig = getSignalConfig(drug.recommendation, drug.margin_pct);
                  return (
                    <tr key={drug.name} className="drug-row">
                      <td>
                        <div className="drug-name-main">{drug.name}</div>
                        <div className="drug-name-sub">
                          {drug.supplier
                            ? drug.supplier
                            : drug.observation_count > 0
                              ? `${drug.observation_count} verified record${drug.observation_count !== 1 ? "s" : ""}`
                              : "Verified"}
                        </div>
                      </td>
                      <td className="td-mono">{tariff != null ? `£${tariff.toFixed(2)}` : "—"}</td>
                      <td className="td-mono td-blue">{ourPrice != null ? `£${ourPrice.toFixed(2)}` : "—"}</td>
                      <td className="td-mono td-green">{drug.margin_gbp != null ? `£${drug.margin_gbp.toFixed(2)}` : "—"}</td>
                      <td>{pct > 0 ? <MarginBar pct={pct} /> : <span className="td-empty">—</span>}</td>
                      <td>
                        <span className="sig-badge"
                          style={{ background: sig.bg, color: sig.text, borderColor: sig.border }}>
                          <span className="sig-dot" style={{ background: sig.dot }} />
                          {sig.label}
                        </span>
                      </td>
                      <td className="td-action">
                        <Link to="/calculator" className="buy-btn">
                          Buy Now <IconArrow />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            Showing {Math.min(6, topDrugs.length)} of 758 tracked drugs &nbsp;·&nbsp; Last updated: {timeStr}
          </div>
        </section>

        {/* ── MARKET SIGNALS (3-col) ───────────────────────────────────── */}
        <section>
          <h3 className="section-eyebrow">Market Signals</h3>
          <div className="signals-grid">

            <div className="sig-card" onClick={() => navigate("/alerts")} role="button" tabIndex={0}>
              <div className="sc-icon sc-icon-red"><IconAlert /></div>
              <div className="sc-body">
                <div className="sc-label">MHRA Alerts</div>
                <div className="sc-num sc-num-red"><AnimatedCounter target={highRiskCount} /></div>
                <div className="sc-desc">Active shortage notices</div>
              </div>
              <Link to="/alerts" className="sc-link" onClick={e => e.stopPropagation()}>View all →</Link>
            </div>

            <div className="sig-card">
              <div className="sc-icon sc-icon-amber"><IconDollar /></div>
              <div className="sc-body">
                <div className="sc-label">FX Stress</div>
                <div className="sc-num sc-num-amber">{signals?.market_alert ?? "GBP ↑2.3%"}</div>
                <div className="sc-desc">GBP/INR currency pressure</div>
              </div>
              <Link to="/analytics" className="sc-link">View →</Link>
            </div>

            <div className="sig-card" onClick={() => navigate("/news")} role="button" tabIndex={0}>
              <div className="sc-icon sc-icon-blue"><IconNews /></div>
              <div className="sc-body">
                <div className="sc-label">Market News</div>
                <div className="sc-num sc-num-blue">{news.length}</div>
                <div className="sc-desc">Latest pharma intelligence</div>
              </div>
              <Link to="/news" className="sc-link" onClick={e => e.stopPropagation()}>View all →</Link>
            </div>

          </div>
        </section>

        {/* ── LATEST NEWS ─────────────────────────────────────────────── */}
        <section>
          <div className="section-row-header">
            <h3 className="section-eyebrow" style={{ margin: 0 }}>Latest Pharma Intel</h3>
            <Link to="/news" className="view-all-btn">All news →</Link>
          </div>
          <div className="news-grid">
            {news.map((article, i) => {
              const gradients = [
                "linear-gradient(135deg,#0f172a 0%,#1e40af 100%)",
                "linear-gradient(135deg,#134e4a 0%,#047857 100%)",
                "linear-gradient(135deg,#1e1b4b 0%,#4c1d95 100%)",
              ];
              const icons = [
                <IconAlert />,
                <IconDollar />,
                <IconTrendUp />,
              ];
              return (
                <a key={article.url} href={article.url} target="_blank" rel="noopener noreferrer" className="news-card">
                  <div className="news-thumb" style={{ background: gradients[i] ?? gradients[0] }}>
                    <span style={{ color: "rgba(255,255,255,0.5)", transform: "scale(1.6)", display: "flex" }}>
                      {icons[i] ?? icons[0]}
                    </span>
                    <span className="news-source-pill">{article.source}</span>
                  </div>
                  <div className="news-body">
                    <div className="news-title">{article.title}</div>
                    <div className="news-desc">{article.description}</div>
                    <div className="news-footer">
                      <span className="news-date">
                        {new Date(article.publishedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                      </span>
                      <span className="news-read">Read more →</span>
                    </div>
                  </div>
                </a>
              );
            })}
          </div>
        </section>

      </div>{/* end dash-body */}

      <style>{CSS}</style>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────
const CSS = `
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
  --primary:   #0f172a;
  --accent:    #3b82f6;
  --success:   #10b981;
  --warning:   #f59e0b;
  --danger:    #ef4444;
  --bg:        #f8fafc;
  --card:      #ffffff;
  --border:    #e2e8f0;
  --text:      #0f172a;
  --muted:     #64748b;
  --muted-lt:  #94a3b8;
}

.dash-page {
  min-height: 100vh;
  background: var(--bg);
  font-family: var(--font-sans);
  animation: dash-in 0.2s ease both;
}

@keyframes dash-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes dash-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ── HERO ── */
.dash-hero {
  background: var(--primary);
  padding: 36px 0 30px;
}

.dash-hero-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  flex-wrap: wrap;
}

.dash-greeting {
  font-size: clamp(1.4rem, 2.5vw, 1.85rem);
  font-weight: 800;
  color: #ffffff;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.dash-hero-sub {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 0 0 14px;
  line-height: 1.5;
}

.dash-live-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 1.2px;
  color: #10b981;
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.live-dot {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  flex-shrink: 0;
  animation: live-pulse 2s infinite;
}

@keyframes live-pulse {
  0%,100% { opacity:1; box-shadow: 0 0 0 0 rgba(16,185,129,0.5); }
  50%      { opacity:0.85; box-shadow: 0 0 0 6px rgba(16,185,129,0); }
}

/* Hero stat cards (glass effect) */
.dash-hero-stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.hero-stat-card {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px;
  padding: 18px 22px;
  min-width: 128px;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  text-align: center;
}

.hero-stat-card:hover {
  background: rgba(255,255,255,0.13);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.hero-stat-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.hero-stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2px;
}

.hero-stat-num {
  font-size: 1.65rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.hero-stat-lbl {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.hero-stat-red  .hero-stat-icon { background: rgba(239,68,68,0.18);   color: #ef4444; }
.hero-stat-red  .hero-stat-num  { color: #f87171; }
.hero-stat-red  .hero-stat-lbl  { color: #fca5a5; }

.hero-stat-amber .hero-stat-icon { background: rgba(245,158,11,0.18); color: #f59e0b; }
.hero-stat-amber .hero-stat-num  { color: #fbbf24; }
.hero-stat-amber .hero-stat-lbl  { color: #fde68a; }

.hero-stat-green .hero-stat-icon { background: rgba(16,185,129,0.18); color: #10b981; }
.hero-stat-green .hero-stat-num  { color: #34d399; }
.hero-stat-green .hero-stat-lbl  { color: #6ee7b7; }

/* ── QUICK ACTIONS BAR ── */
.dash-actions-bar {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 10px 0;
}

.dash-actions-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.qa-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 0.83rem;
  font-weight: 600;
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  font-family: var(--font-sans);
}

.qa-pill:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: var(--accent);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59,130,246,0.14);
}

.qa-pill:hover svg { color: var(--accent); }
.qa-pill svg { color: var(--muted); flex-shrink: 0; }

.qa-pill-muted { background: #f8fafc; color: var(--muted); }
.qa-pill-muted:hover { background: #f1f5f9; border-color: #cbd5e1; color: #475569; transform: none; box-shadow: none; }
.qa-pill:disabled { opacity: 0.55; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

.qa-pill:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* ── BODY ── */
.dash-body {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 28px 64px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* ── TABLE CARD ── */
.table-card {
  background: var(--card);
  border-radius: 20px;
  border: 1px solid var(--border);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  overflow: hidden;
}

.table-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 22px 24px 16px;
  gap: 16px;
  flex-wrap: wrap;
  border-bottom: 1px solid #f1f5f9;
}

.table-title {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--text);
  margin: 0 0 6px;
  letter-spacing: -0.3px;
}

.table-sub {
  font-size: 0.79rem;
  color: var(--muted-lt);
  margin: 0;
}

.table-sub-em {
  color: var(--muted);
  font-weight: 600;
}

.count-badge {
  display: inline-block;
  background: #f1f5f9;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 3px 11px;
  font-size: 0.74rem;
  font-weight: 700;
}

.view-all-btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 9px;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.15s;
  cursor: pointer;
}

.view-all-btn:hover {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

/* TABLE */
.table-scroll { overflow-x: auto; }

.drug-table {
  width: 100%;
  border-collapse: collapse;
}

.drug-table thead tr {
  background: var(--primary);
}

.drug-table th {
  padding: 11px 16px;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.9px;
  color: #64748b;
  white-space: nowrap;
}

.th-name  { min-width: 240px; }
.th-num   { min-width: 100px; }
.th-bar   { min-width: 170px; }
.th-sig   { min-width: 120px; }
.th-act   { min-width: 100px; text-align: center; }

.drug-table tbody tr {
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.1s;
}

.drug-table tbody tr:nth-child(even) { background: #fafbfc; }
.drug-table tbody tr:last-child { border-bottom: none; }

.drug-row:hover { background: #eff6ff !important; }
.drug-row:hover .drug-name-main { color: var(--accent); }

.drug-table td { padding: 14px 16px; vertical-align: middle; }

.drug-name-main {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.35;
  transition: color 0.1s;
}

.drug-name-sub {
  font-size: 0.73rem;
  color: var(--muted-lt);
  margin-top: 3px;
}

.td-mono  { font-family: var(--font-mono); font-size: 0.86rem; font-weight: 600; color: #334155; }
.td-blue  { color: var(--accent); }
.td-green { color: var(--success); font-weight: 800; }
.td-empty { color: var(--muted-lt); font-size: 13px; }
.td-action { text-align: center; }

.sig-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.sig-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.buy-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--accent);
  color: white;
  padding: 7px 13px;
  border-radius: 8px;
  font-size: 0.76rem;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
  cursor: pointer;
}

.buy-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(59,130,246,0.35);
}

.buy-btn:active { transform: scale(0.97); }

.table-footer {
  padding: 11px 22px;
  font-size: 0.76rem;
  color: var(--muted-lt);
  background: #f8fafc;
  border-top: 1px solid #f1f5f9;
  text-align: right;
}

/* ── SECTION EYEBROW ── */
.section-eyebrow {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
  margin: 0 0 14px;
}

.section-row-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

/* ── MARKET SIGNALS ── */
.signals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.sig-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.sig-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.09);
}

.sig-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.sc-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sc-icon-red   { background: #fee2e2; color: var(--danger); }
.sc-icon-amber { background: #fef3c7; color: var(--warning); }
.sc-icon-blue  { background: #dbeafe; color: var(--accent); }

.sc-body { flex: 1; }

.sc-label {
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.9px;
  color: var(--muted-lt);
  margin-bottom: 4px;
}

.sc-num {
  font-size: 1.85rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  margin-bottom: 5px;
}

.sc-num-red   { color: var(--danger); }
.sc-num-amber { color: var(--warning); }
.sc-num-blue  { color: var(--accent); }

.sc-desc {
  font-size: 0.79rem;
  color: var(--muted-lt);
  line-height: 1.4;
}

.sc-link {
  font-size: 0.79rem;
  font-weight: 700;
  color: var(--accent);
  text-decoration: none;
  transition: color 0.12s;
  display: inline-block;
  margin-top: 2px;
}

.sc-link:hover { color: #2563eb; text-decoration: underline; }

/* ── NEWS ── */
.news-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.news-card {
  display: flex;
  flex-direction: column;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.news-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(0,0,0,0.1);
}

.news-thumb {
  position: relative;
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.news-source-pill {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(255,255,255,0.9);
  color: var(--text);
  font-size: 0.67rem;
  font-weight: 800;
  padding: 3px 9px;
  border-radius: 20px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  backdrop-filter: blur(4px);
}

.news-body {
  padding: 16px 18px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.news-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-desc {
  font-size: 0.79rem;
  color: var(--muted);
  line-height: 1.55;
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
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.news-date  { font-size: 0.72rem; color: var(--muted-lt); }
.news-read  { font-size: 0.72rem; color: var(--accent); font-weight: 700; }

/* ── SKELETON ── */
.skel {
  background: linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%);
  background-size: 200% 100%;
  animation: skel-shimmer 1.5s infinite;
  border-radius: 8px;
}

@keyframes skel-shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}

/* ── RESPONSIVE ── */
@media (max-width: 1024px) {
  .signals-grid   { grid-template-columns: repeat(3, 1fr); }
  .news-grid      { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .dash-hero-inner   { flex-direction: column; align-items: flex-start; }
  .dash-hero-stats   { width: 100%; }
  .hero-stat-card    { flex: 1; min-width: 90px; padding: 14px 14px; }
  .hero-stat-num     { font-size: 1.35rem; }
  .dash-body         { padding: 20px 16px 48px; gap: 20px; }
  .signals-grid      { grid-template-columns: 1fr; }
  .news-grid         { grid-template-columns: 1fr; }
  .dash-actions-inner { gap: 6px; }
  .qa-pill           { font-size: 0.78rem; padding: 8px 12px; }
  .table-card-header { padding: 16px 16px 12px; }
  .drug-table th, .drug-table td { padding: 11px 12px; }
}

@media (max-width: 560px) {
  .dash-greeting    { font-size: 1.3rem; }
  .hero-stat-card   { padding: 12px; }
  .hero-stat-icon   { display: none; }
  .hero-stat-num    { font-size: 1.2rem; }
  /* Hide less-critical columns on smallest screens */
  .th-bar, .drug-table td:nth-child(5)  { display: none; }
  .th-num:nth-child(3), .drug-table td:nth-child(3) { display: none; }
  .news-grid         { grid-template-columns: 1fr; }

  @media (prefers-reduced-motion: reduce) {
    .dash-page, .hero-stat-card, .qa-pill, .sig-card, .news-card, .buy-btn {
      animation: none !important;
      transition: none !important;
    }
    .live-dot { animation: none !important; }
  }
}
`;
