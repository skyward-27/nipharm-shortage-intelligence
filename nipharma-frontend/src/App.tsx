import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import MarketNews from "./pages/MarketNews";
import Chat from "./pages/Chat";
import Contact from "./pages/Contact";
import Analytics from "./pages/Analytics";
import Calculator from "./pages/Calculator";
import DrugSearch from "./pages/DrugSearch";
import Alerts from "./pages/Alerts";
import WeeklyReport from "./pages/WeeklyReport";
import { healthCheck } from "./api";

export default function App() {
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    // Check backend health on mount
    const checkHealth = async () => {
      try {
        await healthCheck();
        setApiHealthy(true);
      } catch {
        setApiHealthy(false);
      }
    };

    checkHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <div className="app">
        {/* Navigation Header */}
        <header className="navbar">
          <div className="navbar-container">
            <Link to="/" className="navbar-logo">
              💊 Nipharma Tech Stock Intelligence
            </Link>

            <button
              className="nav-toggle"
              onClick={() => setNavOpen(!navOpen)}
              aria-label="Toggle navigation"
            >
              ☰
            </button>

            <nav className={`navbar-menu ${navOpen ? "active" : ""}`}>
              <Link to="/" className="nav-link" onClick={() => setNavOpen(false)}>
                Dashboard
              </Link>
              <Link to="/news" className="nav-link" onClick={() => setNavOpen(false)}>
                Market News
              </Link>
              <Link to="/chat" className="nav-link" onClick={() => setNavOpen(false)}>
                AI Chat
              </Link>
              <Link to="/analytics" className="nav-link" onClick={() => setNavOpen(false)}>
                Analytics
              </Link>
              <Link to="/calculator" className="nav-link" onClick={() => setNavOpen(false)}>
                💰 Calculator
              </Link>
              <Link to="/drugs" className="nav-link" onClick={() => setNavOpen(false)}>
                Drug Search
              </Link>
              <Link
                to="/alerts"
                className="nav-link nav-link-alerts"
                onClick={() => setNavOpen(false)}
              >
                🚨 Alerts
              </Link>
              <Link
                to="/report"
                className="nav-link nav-link-report"
                onClick={() => setNavOpen(false)}
              >
                📊 Weekly Report
              </Link>
              <Link to="/contact" className="nav-link" onClick={() => setNavOpen(false)}>
                Contact Us
              </Link>
            </nav>

            {/* Health Status Indicator */}
            <div className="health-indicator">
              {apiHealthy === null ? (
                <span className="health-status pending">⏳ Checking...</span>
              ) : apiHealthy ? (
                <span className="health-status healthy">🟢 Connected</span>
              ) : (
                <span className="health-status unhealthy">🔴 Offline</span>
              )}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/news" element={<MarketNews />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/calculator" element={<Calculator />} />
            <Route path="/drugs" element={<DrugSearch />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/report" element={<WeeklyReport />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="footer">
          <div className="footer-content">
            <p>&copy; 2026 NPT Intel. Pharmaceutical supply chain intelligence for UK pharmacies.</p>
            <div className="footer-links">
              <Link to="/">Dashboard</Link>
              <Link to="/news">News</Link>
              <Link to="/chat">Chat</Link>
              <a href="https://www.github.com">GitHub</a>
            </div>
          </div>
        </footer>

        <style>{`
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }

          html, body, #root {
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen",
              "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue",
              sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
          }

          .app {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            background: #fafafa;
          }

          /* Navbar */
          .navbar {
            background: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 100;
          }

          .navbar-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 70px;
          }

          .navbar-logo {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1a1a1a;
            text-decoration: none;
            transition: color 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            white-space: nowrap;
          }

          .navbar-logo:hover {
            color: #1976d2;
          }

          .logo-mark {
            background: #1976d2;
            color: white;
            font-size: 0.85rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
          }

          .navbar-menu {
            display: flex;
            gap: 32px;
            align-items: center;
            margin-left: 48px;
          }

          .nav-link {
            color: #666;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
            white-space: nowrap;
          }

          .nav-link:hover {
            color: #1976d2;
          }

          .nav-link:active {
            color: #1565c0;
          }

          .nav-link-alerts {
            color: #d84315 !important;
            font-weight: 700;
          }

          .nav-link-alerts:hover {
            color: #bf360c !important;
          }

          .nav-link-report {
            background: #1976d2;
            color: white !important;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
          }

          .nav-link-report:hover {
            background: #1565c0 !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba(25, 118, 210, 0.35);
          }

          .nav-toggle {
            display: none;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #1a1a1a;
          }

          /* Health Indicator */
          .health-indicator {
            margin-left: auto;
          }

          .health-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
          }

          .health-status.healthy {
            background: #f0f9f0;
            color: #2e7d32;
          }

          .health-status.unhealthy {
            background: #ffebee;
            color: #c62828;
          }

          .health-status.pending {
            background: #fff3e0;
            color: #f57c00;
          }

          /* Main Content */
          .main-content {
            flex: 1;
            width: 100%;
            padding: 20px 0;
          }

          /* Footer */
          .footer {
            background: #1a1a1a;
            color: white;
            padding: 40px 20px;
            margin-top: auto;
          }

          .footer-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }

          .footer-content p {
            margin: 0;
            color: #aaa;
          }

          .footer-links {
            display: flex;
            gap: 24px;
          }

          .footer-links a {
            color: #aaa;
            text-decoration: none;
            transition: color 0.3s ease;
          }

          .footer-links a:hover {
            color: white;
          }

          /* 404 Page */
          .not-found {
            max-width: 1400px;
            margin: 0 auto;
            padding: 60px 20px;
            text-align: center;
          }

          .not-found h1 {
            font-size: 3rem;
            margin-bottom: 16px;
            color: #1a1a1a;
          }

          .not-found p {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 32px;
          }

          .not-found a {
            display: inline-block;
            padding: 12px 24px;
            background: #1976d2;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.3s ease;
          }

          .not-found a:hover {
            background: #1565c0;
          }

          /* Responsive Design */
          @media (max-width: 768px) {
            .navbar-container {
              padding: 0 16px;
            }

            .navbar-logo {
              font-size: 1.1rem;
            }

            .nav-toggle {
              display: block;
            }

            .navbar-menu {
              position: absolute;
              top: 70px;
              left: 0;
              right: 0;
              background: white;
              flex-direction: column;
              gap: 0;
              padding: 16px 0;
              max-height: 0;
              overflow: hidden;
              transition: max-height 0.3s ease;
              gap: 0;
              border-bottom: 1px solid #e0e0e0;
            }

            .navbar-menu.active {
              max-height: 400px;
            }

            .nav-link {
              display: block;
              padding: 12px 20px;
              border-bottom: 1px solid #f0f0f0;
            }

            .health-indicator {
              margin-left: 0;
              margin-top: 8px;
            }

            .footer-content {
              flex-direction: column;
              gap: 20px;
              text-align: center;
            }

            .footer-links {
              flex-wrap: wrap;
              justify-content: center;
            }
          }

          @media (max-width: 480px) {
            .navbar-logo {
              font-size: 1rem;
            }

            .not-found h1 {
              font-size: 2rem;
            }
          }
        `}</style>
      </div>
    </Router>
  );
}

function NotFound() {
  return (
    <div className="not-found">
      <h1>404</h1>
      <p>Page not found</p>
      <Link to="/">← Back to Dashboard</Link>
    </div>
  );
}
