import { useEffect, useState } from "react";
import { fetchNews, fetchSignals, NewsArticle, Signal } from "../api";

export default function Dashboard() {
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
        setNews(newsData.slice(0, 3));
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
        <h1>💊 Nipharma Intelligence</h1>
        <p className="tagline">
          Save 15-25% on pharmaceutical costs through intelligent bulk coordination
        </p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card highlight">
          <div className="kpi-icon">⚠️</div>
          <h3>Drugs at Risk</h3>
          <p className="big-number">{signals?.drugs_at_risk || "12"}</p>
          <p className="kpi-subtitle">Shortage alerts in pipeline</p>
        </div>

        <div className="kpi-card highlight">
          <div className="kpi-icon">🎯</div>
          <h3>Best Opportunity</h3>
          <p className="big-number">{signals?.best_opportunity || "Paracetamol"}</p>
          <p className="kpi-subtitle">
            {signals?.best_discount || "15"}% bulk discount
          </p>
        </div>

        <div className="kpi-card alert">
          <div className="kpi-icon">📍</div>
          <h3>Market Alert</h3>
          <p className="big-number">India API</p>
          <p className="kpi-subtitle">Risk ↑{signals?.alert_severity || "5%"}</p>
        </div>

        <div className="kpi-card success">
          <div className="kpi-icon">💰</div>
          <h3>Savings Potential</h3>
          <p className="big-number">
            £{((signals?.total_savings_potential || 245000) / 1000).toFixed(0)}k
          </p>
          <p className="kpi-subtitle">Next 90 days</p>
        </div>
      </div>

      {/* CTA Buttons */}
      <div className="cta-buttons">
        <button className="btn btn-primary">📊 See My Bulk Savings</button>
        <button className="btn btn-secondary">📅 Book Demo</button>
        <button className="btn btn-outline">💬 Chat with AI</button>
      </div>

      {/* Latest News Section */}
      <div className="news-section">
        <div className="section-header">
          <h2>Latest Pharma News</h2>
          <a href="/news" className="view-all">
            View all →
          </a>
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
          <a href="/news" className="quick-link">
            📰 Market News
          </a>
          <a href="/chat" className="quick-link">
            🤖 AI Chat
          </a>
          <a href="/drugs" className="quick-link">
            💊 Drug Search
          </a>
          <a href="/analytics" className="quick-link">
            📈 Analytics
          </a>
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
