import { useEffect, useState } from "react";
import { fetchNews, NewsArticle } from "../api";

export default function MarketNews() {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadNews = async () => {
      try {
        setLoading(true);
        const data = await fetchNews();
        setNews(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load news");
      } finally {
        setLoading(false);
      }
    };

    loadNews();
  }, []);

  if (loading) {
    return (
      <div className="news-container">
        <h1>Market News</h1>
        <div className="loading">Loading latest pharmaceutical news...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="news-container">
        <h1>Market News</h1>
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="news-container">
      <h1>Market News</h1>
      <p className="subtitle">Latest pharmaceutical and supply chain updates</p>

      <div className="news-grid">
        {news.map((article) => (
          <article key={article.url} className="news-card">
            {article.image && (
              <div className="news-image">
                <img src={article.image} alt={article.title} />
              </div>
            )}
            <div className="news-content">
              <h3>{article.title}</h3>
              <p className="description">{article.description}</p>
              <div className="news-meta">
                <span className="source">{article.source}</span>
                <span className="date">
                  {new Date(article.publishedAt).toLocaleDateString("en-GB", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
              <a href={article.url} target="_blank" rel="noopener noreferrer" className="read-more">
                Read full article →
              </a>
            </div>
          </article>
        ))}
      </div>

      <style>{`
        .news-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .news-container h1 {
          font-size: 2.5rem;
          margin-bottom: 10px;
          color: #1a1a1a;
        }

        .subtitle {
          color: #666;
          margin-bottom: 30px;
          font-size: 1.1rem;
        }

        .loading,
        .error {
          padding: 20px;
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

        .news-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 24px;
          margin-top: 30px;
        }

        .news-card {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          overflow: hidden;
          transition: all 0.3s ease;
          display: flex;
          flex-direction: column;
        }

        .news-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
        }

        .news-image {
          width: 100%;
          height: 200px;
          overflow: hidden;
          background: #f5f5f5;
        }

        .news-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .news-content {
          padding: 20px;
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        .news-card h3 {
          margin: 0 0 12px 0;
          font-size: 1.25rem;
          color: #1a1a1a;
          line-height: 1.4;
        }

        .description {
          color: #666;
          margin: 0 0 16px 0;
          flex: 1;
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .news-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
          margin-bottom: 12px;
          font-size: 0.85rem;
        }

        .source {
          background: #f0f0f0;
          padding: 4px 12px;
          border-radius: 20px;
          color: #666;
          font-weight: 500;
        }

        .date {
          color: #999;
        }

        .read-more {
          color: #1976d2;
          text-decoration: none;
          font-weight: 500;
          transition: color 0.3s ease;
        }

        .read-more:hover {
          color: #1565c0;
        }
      `}</style>
    </div>
  );
}
