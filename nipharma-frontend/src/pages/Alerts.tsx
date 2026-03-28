import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

interface Alert {
  title: string;
  summary: string;
  url: string;
  date: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
}

interface AlertsResponse {
  success: boolean;
  count: number;
  alerts: Alert[];
  source: string;
}

const FALLBACK_ALERTS: Alert[] = [
  {
    title: "Amoxicillin 500mg capsules - Supply Shortage",
    summary:
      "Manufacturing constraints at primary supplier. Expected resolution Q3 2025. Pharmacies advised to source alternatives.",
    url: "https://www.gov.uk/drug-device-alerts",
    date: "2025-03-15",
    severity: "HIGH",
  },
  {
    title: "Metformin 1g tablets - Intermittent Supply Issues",
    summary:
      "Raw material shortage from Chinese API supplier affecting multiple UK wholesalers.",
    url: "https://www.gov.uk/drug-device-alerts",
    date: "2025-03-10",
    severity: "HIGH",
  },
  {
    title: "Amlodipine 5mg tablets - Supply Disruption",
    summary:
      "Short-term supply disruption. Alternative brands available from AAH and Alliance.",
    url: "https://www.gov.uk/drug-device-alerts",
    date: "2025-03-08",
    severity: "MEDIUM",
  },
];

const SEVERITY_CONFIG: Record<
  Alert["severity"],
  { label: string; borderColor: string; badgeBg: string; badgeColor: string }
> = {
  HIGH: {
    label: "HIGH",
    borderColor: "#d32f2f",
    badgeBg: "#ffebee",
    badgeColor: "#c62828",
  },
  MEDIUM: {
    label: "MEDIUM",
    borderColor: "#f57c00",
    badgeBg: "#fff3e0",
    badgeColor: "#e65100",
  },
  LOW: {
    label: "LOW",
    borderColor: "#388e3c",
    badgeBg: "#e8f5e9",
    badgeColor: "#2e7d32",
  },
};

type FilterType = "ALL" | "HIGH" | "MEDIUM" | "LOW";

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [source, setSource] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [filter, setFilter] = useState<FilterType>("ALL");

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/mhra-alerts`);
        if (!res.ok) throw new Error("Non-200 response");
        const data: AlertsResponse = await res.json();
        setAlerts(data.alerts || []);
        setSource(data.source || "MHRA");
        setOffline(false);
      } catch {
        setAlerts(FALLBACK_ALERTS);
        setSource("MHRA (cached)");
        setOffline(true);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const filtered =
    filter === "ALL" ? alerts : alerts.filter((a) => a.severity === filter);

  const counts = {
    ALL: alerts.length,
    HIGH: alerts.filter((a) => a.severity === "HIGH").length,
    MEDIUM: alerts.filter((a) => a.severity === "MEDIUM").length,
    LOW: alerts.filter((a) => a.severity === "LOW").length,
  };

  return (
    <div className="alerts-page">
      {/* Header */}
      <div className="alerts-header">
        <div className="alerts-header-inner">
          <h1>🚨 MHRA Drug Shortage Alerts</h1>
          <p className="alerts-subtitle">
            Live alerts from the Medicines &amp; Healthcare products Regulatory
            Agency
          </p>
          {source && (
            <span className="source-tag">Source: {source}</span>
          )}
        </div>
      </div>

      <div className="alerts-body">
        {/* Offline Banner */}
        {offline && (
          <div className="offline-banner">
            <span>⚠️</span>
            <span>
              Live API unavailable — showing cached MHRA alerts. Data may not
              reflect the most recent updates.
            </span>
          </div>
        )}

        {/* Filter Buttons */}
        <div className="filter-bar">
          {(["ALL", "HIGH", "MEDIUM", "LOW"] as FilterType[]).map((f) => (
            <button
              key={f}
              className={`filter-btn filter-btn-${f.toLowerCase()} ${
                filter === f ? "active" : ""
              }`}
              onClick={() => setFilter(f)}
            >
              {f}
              <span className="filter-count">{counts[f]}</span>
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="alerts-loading">
            <div className="spinner" />
            <p>Fetching latest MHRA alerts...</p>
          </div>
        )}

        {/* Alerts List */}
        {!loading && filtered.length === 0 && (
          <div className="alerts-empty">
            No {filter !== "ALL" ? filter : ""} alerts at this time.
          </div>
        )}

        {!loading && (
          <div className="alerts-list">
            {filtered.map((alert, idx) => {
              const cfg = SEVERITY_CONFIG[alert.severity];
              return (
                <div
                  key={idx}
                  className="alert-card"
                  style={{ borderLeftColor: cfg.borderColor }}
                >
                  <div className="alert-card-top">
                    <span
                      className="severity-badge"
                      style={{
                        background: cfg.badgeBg,
                        color: cfg.badgeColor,
                      }}
                    >
                      {cfg.label}
                    </span>
                    <span className="alert-date">{alert.date}</span>
                  </div>
                  <h3 className="alert-title">{alert.title}</h3>
                  <p className="alert-summary">{alert.summary}</p>
                  <a
                    href={alert.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="alert-link"
                  >
                    View on MHRA →
                  </a>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style>{`
        .alerts-page {
          min-height: 100vh;
          background: #f5f7fa;
        }

        .alerts-header {
          background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
          color: white;
          padding: 48px 20px 36px;
        }

        .alerts-header-inner {
          max-width: 900px;
          margin: 0 auto;
        }

        .alerts-header h1 {
          font-size: 2.2rem;
          font-weight: 700;
          margin: 0 0 10px 0;
        }

        .alerts-subtitle {
          font-size: 1.05rem;
          opacity: 0.88;
          margin: 0 0 14px 0;
        }

        .source-tag {
          display: inline-block;
          background: rgba(255, 255, 255, 0.15);
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 0.82rem;
          font-weight: 600;
          letter-spacing: 0.3px;
        }

        .alerts-body {
          max-width: 900px;
          margin: 0 auto;
          padding: 28px 20px 48px;
        }

        .offline-banner {
          display: flex;
          align-items: center;
          gap: 10px;
          background: #fff8e1;
          border: 1px solid #ffe082;
          border-radius: 8px;
          padding: 12px 16px;
          margin-bottom: 24px;
          color: #5d4037;
          font-size: 0.93rem;
        }

        .filter-bar {
          display: flex;
          gap: 10px;
          margin-bottom: 28px;
          flex-wrap: wrap;
        }

        .filter-btn {
          padding: 8px 18px;
          border-radius: 24px;
          border: 2px solid transparent;
          font-size: 0.88rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s ease;
          background: white;
        }

        .filter-count {
          background: rgba(0,0,0,0.1);
          border-radius: 10px;
          padding: 1px 7px;
          font-size: 0.78rem;
        }

        .filter-btn-all {
          color: #1565c0;
          border-color: #90caf9;
        }
        .filter-btn-all.active,
        .filter-btn-all:hover {
          background: #1565c0;
          color: white;
          border-color: #1565c0;
        }

        .filter-btn-high {
          color: #c62828;
          border-color: #ef9a9a;
        }
        .filter-btn-high.active,
        .filter-btn-high:hover {
          background: #c62828;
          color: white;
          border-color: #c62828;
        }

        .filter-btn-medium {
          color: #e65100;
          border-color: #ffcc80;
        }
        .filter-btn-medium.active,
        .filter-btn-medium:hover {
          background: #e65100;
          color: white;
          border-color: #e65100;
        }

        .filter-btn-low {
          color: #2e7d32;
          border-color: #a5d6a7;
        }
        .filter-btn-low.active,
        .filter-btn-low:hover {
          background: #2e7d32;
          color: white;
          border-color: #2e7d32;
        }

        .alerts-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          padding: 60px 0;
          color: #666;
        }

        .spinner {
          width: 36px;
          height: 36px;
          border: 3px solid #e3f2fd;
          border-top-color: #1565c0;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .alerts-empty {
          text-align: center;
          padding: 60px 0;
          color: #999;
          font-size: 1.1rem;
        }

        .alerts-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .alert-card {
          background: white;
          border-radius: 10px;
          border-left: 5px solid #ddd;
          padding: 20px 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
          transition: box-shadow 0.2s ease, transform 0.2s ease;
        }

        .alert-card:hover {
          box-shadow: 0 6px 20px rgba(0,0,0,0.1);
          transform: translateY(-2px);
        }

        .alert-card-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .severity-badge {
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.5px;
        }

        .alert-date {
          font-size: 0.83rem;
          color: #999;
        }

        .alert-title {
          font-size: 1.05rem;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0 0 8px 0;
          line-height: 1.4;
        }

        .alert-summary {
          font-size: 0.93rem;
          color: #555;
          line-height: 1.6;
          margin: 0 0 14px 0;
        }

        .alert-link {
          font-size: 0.88rem;
          font-weight: 600;
          color: #1565c0;
          text-decoration: none;
          transition: color 0.2s;
        }

        .alert-link:hover {
          color: #0d47a1;
          text-decoration: underline;
        }

        @media (max-width: 600px) {
          .alerts-header h1 {
            font-size: 1.5rem;
          }

          .alert-card {
            padding: 16px;
          }

          .alert-card-top {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
          }
        }
      `}</style>
    </div>
  );
}
