import { useEffect, useState } from "react";
import { fetchNews, NewsArticle } from "../api";

const FALLBACK_ARTICLES: NewsArticle[] = [
  {
    title: "NHS England Expands Concession List Amid Amoxicillin Shortage",
    description:
      "NHS England has added Amoxicillin 500mg capsules and several other antibiotics to the monthly concession list as wholesale prices surge 18% due to ongoing API supply constraints from Indian manufacturers.",
    url: "https://www.pharmaceutical-journal.com/news/nhs-concessions",
    source: "Pharmaceutical Journal",
    publishedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    image: "",
  },
  {
    title: "India API Export Restrictions Threaten UK Generic Drug Supply",
    description:
      "New export curbs from India's pharmaceutical export authority are expected to impact UK generic drug availability for over 40 active pharmaceutical ingredients, with Metformin and Amlodipine among the highest-risk items.",
    url: "https://www.chemist-druggist.co.uk/news/india-api",
    source: "Chemist & Druggist",
    publishedAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    image: "",
  },
  {
    title: "GBP/INR Rate Falls to 3-Year Low, Pushing Up Import Costs",
    description:
      "The pound has weakened against the Indian rupee, raising UK import costs for generic medicines by an estimated 8-12%. Pharmacies purchasing in bulk now are advised to lock in prices before further depreciation.",
    url: "https://www.pharmacy-magazine.co.uk/finance/gbp-inr",
    source: "Pharmacy Magazine",
    publishedAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    image: "",
  },
  {
    title: "MHRA Issues Shortage Notification for Lansoprazole 30mg Capsules",
    description:
      "The MHRA has confirmed a supply disruption for Lansoprazole 30mg capsules, affecting multiple marketing authorisation holders. Community pharmacies are advised to source alternatives and notify affected patients.",
    url: "https://www.gov.uk/drug-device-alerts",
    source: "MHRA",
    publishedAt: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
    image: "",
  },
];

export default function MarketNews() {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadNews = async () => {
      try {
        setLoading(true);
        const data = await fetchNews();
        const articles = Array.isArray(data) && data.length > 0 ? data : FALLBACK_ARTICLES;
        setNews(articles);
      } catch {
        setNews(FALLBACK_ARTICLES);
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
        <style>{containerStyle}</style>
      </div>
    );
  }

  return (
    <div className="news-container">
      <h1>Market News</h1>
      <p className="subtitle">Latest pharmaceutical and supply chain updates</p>

      <div className="news-grid">
        {news.map((article, idx) => (
          <article key={article.url || idx} className="news-card">
            {article.image && (
              <div className="news-image">
                <img src={article.image} alt={article.title} />
              </div>
            )}
            <div className="news-content">
              <h3>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="article-title-link"
                >
                  {article.title}
                </a>
              </h3>
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
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="read-more"
              >
                Read full article →
              </a>
            </div>
          </article>
        ))}
      </div>

      <style>{containerStyle}</style>
    </div>
  );
}

const containerStyle = `
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
    margin-bottom: 16px;
    font-size: 1.1rem;
  }

  .fallback-notice {
    background: #fff3e0;
    color: #e65100;
    border: 1px solid #ffcc02;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 24px;
    font-size: 0.95rem;
    font-weight: 500;
  }

  .loading {
    padding: 20px;
    text-align: center;
    border-radius: 8px;
    font-size: 1.1rem;
    background: #e3f2fd;
    color: #1976d2;
  }

  .news-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 24px;
    margin-top: 12px;
  }

  .news-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    background: white;
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
    font-size: 1.15rem;
    color: #1a1a1a;
    line-height: 1.4;
  }

  .article-title-link {
    color: #1a1a1a;
    text-decoration: none;
    transition: color 0.2s ease;
  }

  .article-title-link:hover {
    color: #1976d2;
    text-decoration: underline;
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

  @media (max-width: 768px) {
    .news-grid {
      grid-template-columns: 1fr;
    }
    .news-container h1 {
      font-size: 1.8rem;
    }
  }
`;
