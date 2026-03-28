import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchNews, fetchSignals, NewsArticle, Signal } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [signals, setSignals] = useState<Signal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [newsData, signalsData] = await Promise.all([
          fetchNews(),
          fetchSignals(),
        ]);
        setNews(Array.isArray(newsData) ? newsData.slice(0, 3) : []);
        setSignals(signalsData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>📈 Nipharma Tech Stock Intelligence</h1>
        <p className="tagline">
          Save 15-25% on pharmaceutical costs through intelligent bulk coordination
        </p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div
          className="kpi-card highlight kpi-clickable"
          onClick={() => navigate("/analytics")}
          title="Click to view Analytics"
        >
          <div className="kpi-icon">⚠️</div>
          <h3>Drugs at Risk</h3>
          <p className="big-number">{signals?.drugs_at_risk || "12"}</p>
          <p className="kpi-subtitle">Active shortage alerts — click to view →</p>
        </div>

        <div className="kpi-card highlight">
          <div className="kpi-icon">🎯</div>
          <h3>Best Opportunity</h3>
          <p className="big-number" style={{fontSize: "1.4rem"}}>{signals?.best_opportunity || "Amoxicillin 500mg"}</p>
          <p className="kpi-subtitle">
            {signals?.best_discount ? `${signals.best_discount}% bulk discount available` : "18% bulk discount available"}
          </p>
        </div>

        <div
          className="kpi-card alert kpi-clickable"
          onClick={() => navigate("/alerts")}
          title="Click to view all MHRA alerts"
          style={{ cursor: "pointer" }}
        >
          <div className="kpi-icon">📍</div>
          <h3>Market Alert</h3>
          <p className="big-number" style={{fontSize: "1.8rem"}}>{signals?.market_alert || "GBP/INR ↑2.3%"}</p>
          <p className="kpi-subtitle">Click to view all alerts →</p>
        </div>

        <div className="kpi-card success">
          <div className="kpi-icon">💰</div>
          <h3>Savings Potential</h3>
          <p className="big-number">
            {signals?.total_savings_potential
              ? `£${((signals.total_savings_potential) / 1000).toFixed(0)}k`
              : "£12k–£45k"}
          </p>
          <p className="kpi-subtitle">Per pharmacy per year</p>
        </div>

        <div
          className="kpi-card kpi-clickable"
          style={{ borderLeftColor: "#7b1fa2", background: "#faf5ff", cursor: "pointer" }}
          onClick={() => navigate("/calculator")}
          title="Open Bulk Savings Calculator"
        >
          <div className="kpi-icon">🧮</div>
          <h3>Calculate Your Savings</h3>
          <p className="big-number" style={{ fontSize: "1.5rem", color: "#6a1b9a" }}>
            Try Now →
          </p>
          <p className="kpi-subtitle">Interactive bulk savings calculator</p>
        </div>
      </div>

      {/* CTA Buttons */}
      <div className="cta-buttons">
        <button className="btn btn-primary" onClick={() => navigate("/calculator")}>📊 See My Bulk Savings</button>
        <button className="btn btn-secondary" onClick={() => navigate("/contact")}>📅 Book Demo</button>
        <button className="btn btn-outline" onClick={() => navigate("/chat")}>💬 Chat with AI</button>
      </div>

      {/* Weekly Report Banner */}
      <div className="report-banner">
        <div className="report-banner-inner">
          <div className="report-banner-left">
            <span className="report-banner-icon">📊</span>
            <div>
              <div className="report-banner-title">Your Weekly Intelligence Report is Ready</div>
              <div className="report-banner-subtitle">
                Shortage alerts · NHS concessions · Market signals · AI forecast — delivered every Monday
              </div>
            </div>
          </div>
          <Link to="/report" className="report-banner-btn">
            View Report →
          </Link>
        </div>
      </div>

      {/* Latest News Section */}
      <div className="news-section">
        <div className="section-header">
          <h2>Latest Pharma News</h2>
          <Link to="/news" className="view-all">
            View all →
          </Link>
        </div>

        <div className="news-cards">
          {news.map((article) => (
            <div key={article.url} className="news-card">
              {article.image && (
                <div className="news-card-image">
                  <img src={article.image} alt={article.title} />
                </div>
              )}
              <div className="news-card-content">
                <h4>{article.title}</h4>
                <p>{article.description}</p>
                <div className="news-card-footer">
                  <span className="source-badge">{article.source}</span>
                  <span className="date">
                    {new Date(article.publishedAt).toLocaleDateString("en-GB")}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Links */}
      <div className="quick-links">
        <h3>Quick Navigation</h3>
        <div className="links-grid">
          <Link to="/news" className="quick-link">
            📰 Market News
          </Link>
          <Link to="/chat" className="quick-link">
            🤖 AI Chat
          </Link>
          <Link to="/drugs" className="quick-link">
            💊 Drug Search
          </Link>
          <Link to="/analytics" className="quick-link">
            📈 Analytics
          </Link>
          <Link to="/calculator" className="quick-link">
            🧮 Savings Calculator
          </Link>
        </div>
      </div>

      <style>{`
        .dashboard {
          max-width: 1400px;
          margin: 0 auto;
          padding: 20px;
          background: #f9f9f9;
        }

        .dashboard-header {
          margin-bottom: 40px;
          text-align: center;
        }

        .dashboard-header h1 {
          font-size: 2.5rem;
          margin: 0 0 10px 0;
          color: #1a1a1a;
        }

        .tagline {
          font-size: 1.2rem;
          color: #666;
          margin: 0;
        }

        .loading,
        .error {
          padding: 40px 20px;
          text-align: center;
          border-radius: 8px;
          font-size: 1.1rem;
        }

        .loading {
          background: #e3f2fd;
          color: #1976d2;
        }

        .error {
          background: #ffebee;
          color: #c62828;
        }

        /* KPI Grid */
        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 40px;
        }

        .kpi-card {
          background: white;
          padding: 24px;
          border-radius: 12px;
          border-left: 4px solid #ddd;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
        }

        .kpi-card:hover {
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
        }

        .kpi-clickable {
          cursor: pointer;
        }

        .kpi-clickable:hover {
          border-left-color: #1565c0;
          box-shadow: 0 6px 20px rgba(25, 118, 210, 0.18);
        }

        .kpi-card.highlight {
          border-left-color: #1976d2;
        }

        .kpi-card.alert {
          border-left-color: #ff9800;
          background: #fff8e1;
        }

        .kpi-card.success {
          border-left-color: #4caf50;
          background: #f1f8f4;
        }

        .kpi-icon {
          font-size: 2.5rem;
          margin-bottom: 12px;
        }

        .kpi-card h3 {
          margin: 0 0 12px 0;
          color: #666;
          font-size: 0.9rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .big-number {
          margin: 0 0 8px 0;
          font-size: 2.5rem;
          font-weight: 700;
          color: #1a1a1a;
        }

        .kpi-subtitle {
          margin: 0;
          color: #999;
          font-size: 0.9rem;
        }

        /* CTA Buttons */
        .cta-buttons {
          display: flex;
          gap: 16px;
          margin-bottom: 40px;
          flex-wrap: wrap;
        }

        .btn {
          padding: 14px 24px;
          border: none;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .btn-primary {
          background: #1976d2;
          color: white;
        }

        .btn-primary:hover {
          background: #1565c0;
          box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
        }

        .btn-secondary {
          background: #4caf50;
          color: white;
        }

        .btn-secondary:hover {
          background: #45a049;
          box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }

        .btn-outline {
          background: transparent;
          color: #1976d2;
          border: 2px solid #1976d2;
        }

        .btn-outline:hover {
          background: #f0f0f0;
        }

        /* Weekly Report Banner */
        .report-banner {
          background: linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%);
          border-radius: 14px;
          margin-bottom: 40px;
          box-shadow: 0 6px 24px rgba(13, 71, 161, 0.3);
          overflow: hidden;
        }

        .report-banner-inner {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px 32px;
          gap: 20px;
          flex-wrap: wrap;
        }

        .report-banner-left {
          display: flex;
          align-items: center;
          gap: 16px;
          flex: 1;
        }

        .report-banner-icon {
          font-size: 2.5rem;
          flex-shrink: 0;
        }

        .report-banner-title {
          font-size: 1.2rem;
          font-weight: 700;
          color: white;
          margin-bottom: 4px;
        }

        .report-banner-subtitle {
          font-size: 0.9rem;
          color: rgba(255, 255, 255, 0.8);
        }

        .report-banner-btn {
          background: white;
          color: #0d47a1;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 700;
          font-size: 1rem;
          text-decoration: none;
          white-space: nowrap;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          flex-shrink: 0;
        }

        .report-banner-btn:hover {
          background: #e3f2fd;
          transform: translateY(-2px);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
        }

        /* News Section */
        .news-section {
          margin-bottom: 40px;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .section-header h2 {
          margin: 0;
          font-size: 1.8rem;
          color: #1a1a1a;
        }

        .view-all {
          color: #1976d2;
          text-decoration: none;
          font-weight: 600;
          transition: color 0.3s ease;
        }

        .view-all:hover {
          color: #1565c0;
        }

        .news-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 20px;
        }

        .news-card {
          background: white;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
          display: flex;
          flex-direction: column;
        }

        .news-card:hover {
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
          transform: translateY(-4px);
        }

        .news-card-image {
          width: 100%;
          height: 160px;
          background: #f5f5f5;
          overflow: hidden;
        }

        .news-card-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .news-card-content {
          padding: 16px;
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        .news-card h4 {
          margin: 0 0 8px 0;
          font-size: 1rem;
          color: #1a1a1a;
          line-height: 1.4;
        }

        .news-card p {
          margin: 0 0 12px 0;
          color: #666;
          font-size: 0.9rem;
          line-height: 1.4;
          flex: 1;
        }

        .news-card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
        }

        .source-badge {
          background: #f0f0f0;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.8rem;
          color: #666;
          font-weight: 500;
        }

        .date {
          color: #999;
          font-size: 0.85rem;
        }

        /* Quick Links */
        .quick-links {
          background: white;
          padding: 24px;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .quick-links h3 {
          margin: 0 0 16px 0;
          color: #1a1a1a;
        }

        .links-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
        }

        .quick-link {
          padding: 16px;
          text-align: center;
          text-decoration: none;
          background: #f5f5f5;
          border-radius: 8px;
          color: #1976d2;
          font-weight: 600;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .quick-link:hover {
          background: #e3f2fd;
          color: #1565c0;
        }

        @media (max-width: 768px) {
          .dashboard {
            padding: 16px;
          }

          .dashboard-header h1 {
            font-size: 1.8rem;
          }

          .kpi-grid {
            grid-template-columns: 1fr;
          }

          .cta-buttons {
            flex-direction: column;
          }

          .btn {
            width: 100%;
          }

          .section-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }

          .news-cards {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
