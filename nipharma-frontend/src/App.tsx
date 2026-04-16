import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from "react-router-dom";
import { Analytics as VercelAnalytics } from "@vercel/analytics/react";
import Dashboard from "./pages/Dashboard";
import MarketNews from "./pages/MarketNews";
import Chat from "./pages/Chat";
import Contact from "./pages/Contact";
import Analytics from "./pages/Analytics";
import Calculator from "./pages/Calculator";
import DrugSearch from "./pages/DrugSearch";
import Alerts from "./pages/Alerts";
import WeeklyReport from "./pages/WeeklyReport";
import Recommendations from "./pages/Recommendations";
import DataExplorer from "./pages/DataExplorer";
import ChatWidget from "./components/ChatWidget";
import { healthCheck } from "./api";

// ── SVG Nav Icons ────────────────────────────────────────────────────────────
const NavHome   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>;
const NavPulse  = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>;
const NavBag    = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1={3} y1={6} x2={21} y2={6}/><path d="M16 10a4 4 0 01-8 0"/></svg>;
const NavBell   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>;
const NavChart  = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1={18} y1={20} x2={18} y2={10}/><line x1={12} y1={20} x2={12} y2={4}/><line x1={6} y1={20} x2={6} y2={14}/></svg>;
const NavSearch = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx={11} cy={11} r={8}/><line x1={21} y1={21} x2={16.65} y2={16.65}/></svg>;
const NavNews   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6z"/></svg>;
const NavReport = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1={16} y1={13} x2={8} y2={13}/><line x1={16} y1={17} x2={8} y2={17}/></svg>;
const NavCalc   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><rect x={4} y={2} width={16} height={20} rx={2}/><line x1={8} y1={6} x2={16} y2={6}/><line x1={8} y1={10} x2={8} y2={10}/><line x1={12} y1={10} x2={12} y2={10}/><line x1={16} y1={10} x2={16} y2={10}/><line x1={8} y1={14} x2={8} y2={14}/><line x1={12} y1={14} x2={12} y2={14}/><line x1={16} y1={14} x2={16} y2={14}/><line x1={8} y1={18} x2={16} y2={18}/></svg>;
const NavChat   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>;
const NavMail   = () => <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>;
const NavMenuIcon = ({ open }: { open: boolean }) =>
  open ? (
    <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round"><line x1={18} y1={6} x2={6} y2={18}/><line x1={6} y1={6} x2={18} y2={18}/></svg>
  ) : (
    <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round"><line x1={3} y1={6} x2={21} y2={6}/><line x1={3} y1={12} x2={21} y2={12}/><line x1={3} y1={18} x2={21} y2={18}/></svg>
  );

// ── Nav item definition (only the important pages) ──────────────────────────
const NAV_ITEMS: { to: string; label: string; icon: JSX.Element; end?: boolean; cta?: boolean }[] = [
  { to: "/",         label: "Dashboard",       icon: <NavHome    />, end: true },
  { to: "/drugs",    label: "Drug Search",     icon: <NavSearch  />            },
  { to: "/explorer", label: "Concession Lens", icon: <NavPulse   />            },
  { to: "/analytics",label: "Analytics",       icon: <NavChart   />            },
  { to: "/calculator",label: "Calculator",     icon: <NavCalc    />            },
  { to: "/chat",     label: "AI Chat",         icon: <NavChat    />            },
  { to: "/contact",  label: "Support",         icon: <NavMail    />            },
];

export default function App() {
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [navOpen, setNavOpen]       = useState(false);

  useEffect(() => {
    const check = async () => {
      try { await healthCheck(); setApiHealthy(true); }
      catch { setApiHealthy(false); }
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  // Close mobile menu on route change via body click outside
  const closeNav = () => setNavOpen(false);

  return (
    <Router>
      <div className="app">

        {/* ── NAVBAR ─────────────────────────────────────────────────────── */}
        <header className="nb">
          <div className="nb-inner">

            {/* Logo */}
            <Link to="/" className="nb-logo" onClick={closeNav}>
              <div className="nb-logo-mark">
                <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22"/>
                </svg>
              </div>
              <div className="nb-logo-text">
                <div className="nb-wordmark">
                  <span className="nb-ni">Ni</span><span className="nb-pharm">Pharm</span>
                </div>
                <div className="nb-tagline">Stock Intelligence</div>
              </div>
              <span className="nb-live-badge">
                <span className="nb-live-dot" />
                LIVE
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="nb-nav" aria-label="Main navigation">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `nb-link${isActive ? " nb-link-active" : ""}${item.cta ? " nb-link-cta" : ""}`
                  }
                  onClick={closeNav}
                >
                  <span className="nb-link-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </nav>

            {/* Right: status + hamburger */}
            <div className="nb-right">
              <div className="nb-status">
                {apiHealthy === null ? (
                  <span className="nb-pill nb-pill-pending">
                    <span className="nb-dot nb-dot-grey" />
                    Checking
                  </span>
                ) : apiHealthy ? (
                  <span className="nb-pill nb-pill-online">
                    <span className="nb-dot nb-dot-green" />
                    Connected
                  </span>
                ) : (
                  <span className="nb-pill nb-pill-offline">
                    <span className="nb-dot nb-dot-red" />
                    Offline
                  </span>
                )}
              </div>
              <button
                className="nb-hamburger"
                onClick={() => setNavOpen(o => !o)}
                aria-label={navOpen ? "Close navigation" : "Open navigation"}
                aria-expanded={navOpen}
              >
                <NavMenuIcon open={navOpen} />
              </button>
            </div>
          </div>

          {/* Mobile drawer */}
          <div className={`nb-drawer ${navOpen ? "nb-drawer-open" : ""}`} aria-hidden={!navOpen}>
            {NAV_ITEMS.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `nb-drawer-link${isActive ? " nb-drawer-link-active" : ""}`
                }
                onClick={closeNav}
              >
                <span className="nb-drawer-icon">{item.icon}</span>
                {item.label}
                {item.cta && <span className="nb-drawer-cta-badge">New</span>}
              </NavLink>
            ))}
            {/* Status in drawer */}
            <div className="nb-drawer-status">
              <span className="nb-drawer-status-dot" style={{ background: apiHealthy ? "#10b981" : apiHealthy === false ? "#ef4444" : "#64748b" }} />
              Backend: {apiHealthy === null ? "Checking…" : apiHealthy ? "Connected" : "Offline"}
            </div>
          </div>
        </header>

        {/* ── MAIN CONTENT ─────────────────────────────────────────────── */}
        <main className="main-content">
          <Routes>
            <Route path="/"               element={<Dashboard />} />
            <Route path="/news"           element={<MarketNews />} />
            <Route path="/chat"           element={<Chat />} />
            <Route path="/contact"        element={<Contact />} />
            <Route path="/analytics"      element={<Analytics />} />
            <Route path="/calculator"     element={<Calculator />} />
            <Route path="/drugs"          element={<DrugSearch />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/alerts"         element={<Alerts />} />
            <Route path="/explorer"       element={<DataExplorer />} />
            <Route path="/report"         element={<WeeklyReport />} />
            <Route path="*"               element={<NotFound />} />
          </Routes>
        </main>

        {/* ── FOOTER ───────────────────────────────────────────────────── */}
        <footer className="app-footer">
          <div className="app-footer-inner">
            <div className="footer-brand">
              <span className="footer-logo">
                <span className="nb-ni">Ni</span><span style={{ color: "#94a3b8" }}>Pharm</span>
              </span>
              <span className="footer-copy">© 2026 NPT Intel · Pharmaceutical supply chain intelligence for UK pharmacies</span>
            </div>
            <div className="footer-links">
              <Link to="/">Dashboard</Link>
              <Link to="/news">News</Link>
              <Link to="/chat">Chat</Link>
              <Link to="/contact">Contact</Link>
            </div>
          </div>
        </footer>

        <style>{CSS}</style>
      </div>

      <ChatWidget />
      {/* Vercel Analytics — free on Hobby plan, tracks page views + visitors */}
      <VercelAnalytics />
    </Router>
  );
}

function NotFound() {
  return (
    <div style={{ maxWidth: 560, margin: "80px auto", padding: "0 24px", textAlign: "center", fontFamily: "var(--app-font-sans)" }}>
      <div style={{ fontSize: "4rem", fontWeight: 900, color: "#e2e8f0", marginBottom: 16, fontFamily: "monospace" }}>404</div>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a", marginBottom: 10 }}>Page not found</h1>
      <p style={{ color: "#64748b", marginBottom: 28, lineHeight: 1.6 }}>The page you're looking for doesn't exist or has been moved.</p>
      <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "11px 22px", background: "#3b82f6", color: "white", textDecoration: "none", borderRadius: 10, fontWeight: 700, fontSize: 14 }}>
        ← Back to Dashboard
      </Link>
    </div>
  );
}

// ── Global + Navbar CSS ──────────────────────────────────────────────────────
const CSS = `
:root {
  --app-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --nb-height: 60px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #root {
  height: 100%;
  font-family: var(--app-font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f8fafc;
}

.main-content {
  flex: 1;
  width: 100%;
}

/* ── NAVBAR ── */
.nb {
  background: #0f172a;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  position: sticky;
  top: 0;
  z-index: 200;
  height: var(--nb-height);
}

.nb-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
  height: var(--nb-height);
  display: flex;
  align-items: center;
  gap: 20px;
}

/* ── LOGO ── */
.nb-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.nb-logo-mark {
  width: 34px;
  height: 34px;
  background: rgba(59,130,246,0.12);
  border: 1px solid rgba(59,130,246,0.25);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.nb-logo:hover .nb-logo-mark {
  background: rgba(59,130,246,0.2);
}

.nb-logo-text { display: flex; flex-direction: column; }

.nb-wordmark {
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: -0.3px;
  line-height: 1;
}

.nb-ni    { color: #3b82f6; }
.nb-pharm { color: #ffffff; }

.nb-tagline {
  font-size: 0.63rem;
  color: #475569;
  font-weight: 600;
  letter-spacing: 0.4px;
  line-height: 1;
  margin-top: 3px;
  text-transform: uppercase;
}

.nb-live-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 1px;
  color: #10b981;
  background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
  padding: 3px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  flex-shrink: 0;
}

.nb-live-dot {
  width: 5px;
  height: 5px;
  background: #10b981;
  border-radius: 50%;
  flex-shrink: 0;
  animation: nb-pulse 2s infinite;
}

@keyframes nb-pulse {
  0%,100% { opacity:1; box-shadow:0 0 0 0 rgba(16,185,129,0.5); }
  50%      { opacity:0.8; box-shadow:0 0 0 5px rgba(16,185,129,0); }
}

/* ── DESKTOP NAV ── */
.nb-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 0 4px;
}

.nb-nav::-webkit-scrollbar { display: none; }

.nb-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #64748b;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.12s, color 0.12s;
  cursor: pointer;
  border: none;
  background: none;
}

.nb-link:hover {
  background: rgba(255,255,255,0.07);
  color: #e2e8f0;
}

.nb-link-icon {
  display: flex;
  align-items: center;
  opacity: 0.7;
  flex-shrink: 0;
}

.nb-link:hover .nb-link-icon { opacity: 1; }

.nb-link-active {
  color: #3b82f6 !important;
  background: rgba(59,130,246,0.1) !important;
  font-weight: 700 !important;
}

.nb-link-active .nb-link-icon { opacity: 1; color: #3b82f6; }

.nb-link-alert {
  color: #f87171 !important;
}

.nb-link-alert:hover {
  background: rgba(239,68,68,0.1) !important;
  color: #fca5a5 !important;
}

.nb-link-cta {
  background: #3b82f6 !important;
  color: white !important;
  font-weight: 700 !important;
  padding: 6px 12px !important;
  border-radius: 8px;
}

.nb-link-cta:hover {
  background: #2563eb !important;
  color: white !important;
}

.nb-link-cta .nb-link-icon { opacity: 1; }

/* ── RIGHT SIDE ── */
.nb-right {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-shrink: 0;
}

/* Status pill */
.nb-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.2px;
  white-space: nowrap;
  border: 1px solid transparent;
}

.nb-pill-online  { background: rgba(16,185,129,0.1);  color: #34d399;  border-color: rgba(16,185,129,0.25); }
.nb-pill-offline { background: rgba(239,68,68,0.1);   color: #f87171;  border-color: rgba(239,68,68,0.25); }
.nb-pill-pending { background: rgba(100,116,139,0.1); color: #94a3b8;  border-color: rgba(100,116,139,0.2); }

.nb-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.nb-dot-green { background: #10b981; animation: nb-pulse 2s infinite; }
.nb-dot-red   { background: #ef4444; animation: nb-blink 1.5s infinite; }
.nb-dot-grey  { background: #64748b; }

@keyframes nb-blink {
  0%,100% { opacity:1; }
  50%      { opacity:0.35; }
}

/* ── HAMBURGER ── */
.nb-hamburger {
  display: none;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: background 0.12s, color 0.12s;
  line-height: 0;
}

.nb-hamburger:hover {
  background: rgba(255,255,255,0.08);
  color: #e2e8f0;
}

/* ── MOBILE DRAWER ── */
.nb-drawer {
  background: #0f172a;
  border-top: 1px solid rgba(255,255,255,0.07);
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s cubic-bezier(0.4,0,0.2,1);
  position: absolute;
  top: var(--nb-height);
  left: 0;
  right: 0;
  z-index: 199;
  box-shadow: 0 12px 32px rgba(0,0,0,0.4);
}

.nb-drawer-open {
  max-height: 600px;
}

.nb-drawer-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 24px;
  color: #64748b;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  transition: background 0.1s, color 0.1s;
}

.nb-drawer-link:hover {
  background: rgba(255,255,255,0.05);
  color: #e2e8f0;
}

.nb-drawer-link-active {
  color: #3b82f6 !important;
  background: rgba(59,130,246,0.08) !important;
  font-weight: 700 !important;
}

.nb-drawer-link-alert { color: #f87171 !important; }

.nb-drawer-icon {
  display: flex;
  align-items: center;
  opacity: 0.7;
  flex-shrink: 0;
}

.nb-drawer-link-active .nb-drawer-icon { opacity: 1; }

.nb-drawer-cta-badge {
  margin-left: auto;
  background: #3b82f6;
  color: white;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
  letter-spacing: 0.5px;
}

.nb-drawer-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #475569;
}

.nb-drawer-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── FOOTER ── */
.app-footer {
  background: #0f172a;
  border-top: 1px solid rgba(255,255,255,0.07);
  padding: 24px 0;
  margin-top: auto;
}

.app-footer-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.footer-logo {
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.footer-copy {
  font-size: 0.78rem;
  color: #475569;
}

.footer-links {
  display: flex;
  gap: 20px;
  align-items: center;
}

.footer-links a {
  font-size: 0.8rem;
  color: #475569;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.12s;
}

.footer-links a:hover { color: #94a3b8; }

/* ── RESPONSIVE ── */
@media (max-width: 1100px) {
  .nb-link { font-size: 0.76rem; padding: 5px 8px; }
}

@media (max-width: 900px) {
  .nb-nav { display: none; }
  .nb-hamburger { display: flex; }
  .nb-status { display: none; }
}

@media (max-width: 480px) {
  .nb-live-badge { display: none; }
  .nb-logo-text .nb-tagline { display: none; }
  .app-footer-inner { flex-direction: column; align-items: flex-start; gap: 16px; }
  .footer-links { flex-wrap: wrap; }
}

@media (prefers-reduced-motion: reduce) {
  .nb-live-dot, .nb-dot-green, .nb-dot-red { animation: none !important; }
  .nb-drawer { transition: none !important; }
}
`;
