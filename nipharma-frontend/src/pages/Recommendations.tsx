import { useState, useEffect } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface Summary {
  total_drugs: number;
  bulk_buy_count: number;
  buy_as_you_go_count: number;
  hold_buying_count: number;
  avg_margin_gbp: number;
}

interface RecommendationRow {
  [key: string]: any;
}

interface RecommendationsData {
  success: boolean;
  summary: Summary;
  top_opportunities: RecommendationRow[];
  hold_warnings: RecommendationRow[];
  recommendations: RecommendationRow[];
  message?: string;
}

export default function Recommendations() {
  const [data, setData] = useState<RecommendationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecs = async () => {
      try {
        const res = await fetch(`${API_URL}/recommendations`);
        if (!res.ok) throw new Error("Failed to fetch recommendations");
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message || "Failed to load recommendations");
      } finally {
        setLoading(false);
      }
    };
    fetchRecs();
  }, []);

  // Helper: find a value in a row by trying multiple column names
  const getField = (row: RecommendationRow, ...keys: string[]): any => {
    for (const k of keys) {
      if (row[k] !== undefined && row[k] !== null) return row[k];
    }
    return null;
  };

  const getDrugName = (row: RecommendationRow) =>
    getField(row, "drug_name", "drug", "name", "product", "description") || "Unknown";

  const getRec = (row: RecommendationRow) =>
    (getField(row, "recommendation", "action", "rec", "buying_recommendation") || "").toString().toUpperCase();

  const getMargin = (row: RecommendationRow) =>
    getField(row, "margin_gbp", "margin", "saving_gbp", "savings_gbp");

  const getCurrentPrice = (row: RecommendationRow) =>
    getField(row, "current_price", "price", "unit_price", "our_price");

  const getBestPrice = (row: RecommendationRow) =>
    getField(row, "best_price", "lowest_price", "best_historic_price", "min_price");

  const getTariff = (row: RecommendationRow) =>
    getField(row, "nhs_tariff", "tariff", "tariff_price", "drug_tariff_price");

  const recBadge = (rec: string) => {
    const upper = rec.toUpperCase();
    if (upper === "BULK BUY") return { bg: "#e8f5e9", color: "#2e7d32", border: "#a5d6a7" };
    if (upper === "BUY AS YOU GO") return { bg: "#fff8e1", color: "#e65100", border: "#ffcc02" };
    if (upper === "HOLD BUYING") return { bg: "#ffebee", color: "#c62828", border: "#ef9a9a" };
    return { bg: "#f5f5f5", color: "#666", border: "#e0e0e0" };
  };

  const formatGBP = (val: any) => {
    if (val === null || val === undefined) return "-";
    const num = typeof val === "number" ? val : parseFloat(val);
    if (isNaN(num)) return "-";
    return `\u00a3${num.toFixed(2)}`;
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: 40, textAlign: "center" }}>
        <div style={{ fontSize: "1.2rem", color: "#666" }}>Loading recommendations...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: 40, textAlign: "center" }}>
        <div style={{ fontSize: "1.2rem", color: "#c62828" }}>
          {error || "No data available"}
        </div>
        <p style={{ color: "#666", marginTop: 12 }}>
          Ensure the backend is running and buying_recommendations.csv is available.
        </p>
      </div>
    );
  }

  const { summary, top_opportunities, hold_warnings, recommendations } = data;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 20, fontFamily: "inherit" }}>
      <h1 style={{ fontSize: "2.2rem", color: "#1a1a1a", marginBottom: 6 }}>
        Wholesale Buying Recommendations
      </h1>
      <p style={{ color: "#666", marginBottom: 36, fontSize: "1.05rem" }}>
        Data-driven buying guidance for pharmacy stock procurement — updated from invoice and tariff analysis
      </p>

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <div style={statBox("#e3f2fd", "#1565c0")}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{summary.total_drugs}</div>
          <div style={{ fontSize: "0.85rem", marginTop: 4 }}>Total Drugs Tracked</div>
        </div>
        <div style={statBox("#e8f5e9", "#2e7d32")}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{summary.bulk_buy_count}</div>
          <div style={{ fontSize: "0.85rem", marginTop: 4 }}>BULK BUY</div>
        </div>
        <div style={statBox("#fff8e1", "#e65100")}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{summary.buy_as_you_go_count}</div>
          <div style={{ fontSize: "0.85rem", marginTop: 4 }}>BUY AS YOU GO</div>
        </div>
        <div style={statBox("#ffebee", "#c62828")}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{summary.hold_buying_count}</div>
          <div style={{ fontSize: "0.85rem", marginTop: 4 }}>HOLD BUYING</div>
        </div>
        <div style={statBox("#f3e5f5", "#6a1b9a")}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{formatGBP(summary.avg_margin_gbp)}</div>
          <div style={{ fontSize: "0.85rem", marginTop: 4 }}>Avg Margin</div>
        </div>
      </div>

      {/* Top Savings Opportunities */}
      {top_opportunities.length > 0 && (
        <section style={sectionCard}>
          <h2 style={sectionTitle}>Top Savings Opportunities</h2>
          <p style={{ color: "#666", marginBottom: 20, fontSize: "0.95rem" }}>
            BULK BUY drugs ranked by margin — order these in volume for maximum savings
          </p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 700 }}>
              <thead>
                <tr style={{ background: "#f5f7fa" }}>
                  {["#", "Drug", "Current Price", "Best Price", "NHS Tariff", "Margin", "Recommendation"].map(
                    (h) => (
                      <th key={h} style={tableHeader}>
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {top_opportunities.map((row, idx) => {
                  const rec = getRec(row);
                  const badge = recBadge(rec);
                  return (
                    <tr
                      key={idx}
                      style={{ background: idx % 2 === 0 ? "#fff" : "#fafafa" }}
                    >
                      <td style={tableCell}>{idx + 1}</td>
                      <td style={tableCell}>
                        <span style={{ fontWeight: 600, color: "#1a1a1a" }}>
                          {getDrugName(row)}
                        </span>
                      </td>
                      <td style={tableCell}>{formatGBP(getCurrentPrice(row))}</td>
                      <td style={tableCell}>{formatGBP(getBestPrice(row))}</td>
                      <td style={tableCell}>{formatGBP(getTariff(row))}</td>
                      <td style={tableCell}>
                        <span style={{ fontWeight: 700, color: "#2e7d32" }}>
                          {formatGBP(getMargin(row))}
                        </span>
                      </td>
                      <td style={tableCell}>
                        <span
                          style={{
                            background: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                            borderRadius: 20,
                            padding: "3px 12px",
                            fontSize: "0.8rem",
                            fontWeight: 700,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {rec || "N/A"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Hold Warnings */}
      {hold_warnings.length > 0 && (
        <section
          style={{
            ...sectionCard,
            border: "1px solid #ef9a9a",
            background: "#fff8f8",
          }}
        >
          <h2 style={{ ...sectionTitle, color: "#c62828" }}>
            Hold Warnings
          </h2>
          <p style={{ color: "#c62828", marginBottom: 20, fontSize: "0.95rem" }}>
            These drugs are currently overpriced — avoid bulk purchasing until prices normalise
          </p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 500 }}>
              <thead>
                <tr style={{ background: "#ffebee" }}>
                  {["Drug", "Current Price", "Best Price", "NHS Tariff", "Margin"].map((h) => (
                    <th key={h} style={{ ...tableHeader, color: "#c62828" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {hold_warnings.map((row, idx) => (
                  <tr
                    key={idx}
                    style={{ background: idx % 2 === 0 ? "#fff8f8" : "#ffebee" }}
                  >
                    <td style={tableCell}>
                      <span style={{ fontWeight: 600, color: "#1a1a1a" }}>
                        {getDrugName(row)}
                      </span>
                    </td>
                    <td style={tableCell}>{formatGBP(getCurrentPrice(row))}</td>
                    <td style={tableCell}>{formatGBP(getBestPrice(row))}</td>
                    <td style={tableCell}>{formatGBP(getTariff(row))}</td>
                    <td style={tableCell}>
                      <span style={{ fontWeight: 700, color: "#c62828" }}>
                        {formatGBP(getMargin(row))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Full Recommendations List */}
      {recommendations.length > 0 && (
        <section style={sectionCard}>
          <h2 style={sectionTitle}>All Recommendations</h2>
          <p style={{ color: "#666", marginBottom: 20, fontSize: "0.95rem" }}>
            Complete list of buying recommendations (first 50 shown)
          </p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 700 }}>
              <thead>
                <tr style={{ background: "#f5f7fa" }}>
                  {["Drug", "Current Price", "Best Price", "NHS Tariff", "Margin", "Recommendation"].map(
                    (h) => (
                      <th key={h} style={tableHeader}>
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {recommendations.map((row, idx) => {
                  const rec = getRec(row);
                  const badge = recBadge(rec);
                  return (
                    <tr
                      key={idx}
                      style={{ background: idx % 2 === 0 ? "#fff" : "#fafafa" }}
                    >
                      <td style={tableCell}>
                        <span style={{ fontWeight: 600, color: "#1a1a1a" }}>
                          {getDrugName(row)}
                        </span>
                      </td>
                      <td style={tableCell}>{formatGBP(getCurrentPrice(row))}</td>
                      <td style={tableCell}>{formatGBP(getBestPrice(row))}</td>
                      <td style={tableCell}>{formatGBP(getTariff(row))}</td>
                      <td style={tableCell}>
                        <span
                          style={{
                            fontWeight: 700,
                            color:
                              rec === "HOLD BUYING"
                                ? "#c62828"
                                : rec === "BULK BUY"
                                ? "#2e7d32"
                                : "#e65100",
                          }}
                        >
                          {formatGBP(getMargin(row))}
                        </span>
                      </td>
                      <td style={tableCell}>
                        <span
                          style={{
                            background: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                            borderRadius: 20,
                            padding: "3px 12px",
                            fontSize: "0.8rem",
                            fontWeight: 700,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {rec || "N/A"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* No data message */}
      {!data.success && (
        <section style={sectionCard}>
          <div
            style={{
              textAlign: "center",
              padding: 40,
              color: "#666",
            }}
          >
            <p style={{ fontSize: "1.1rem", marginBottom: 8 }}>
              {data.message || "No recommendations data available yet."}
            </p>
            <p style={{ fontSize: "0.9rem" }}>
              Run the buying recommendations scraper to generate data.
            </p>
          </div>
        </section>
      )}

      {/* Info footer */}
      <div
        style={{
          padding: "14px 18px",
          background: "#e3f2fd",
          borderRadius: 8,
          fontSize: "0.9rem",
          color: "#1565c0",
          marginTop: 8,
        }}
      >
        Recommendations are generated from wholesale invoice analysis combined with NHS Drug Tariff
        pricing. BULK BUY = current wholesale price offers strong margin vs tariff. HOLD = current
        price is above average, wait for better pricing.
      </div>
    </div>
  );
}

const sectionCard: React.CSSProperties = {
  background: "white",
  borderRadius: 12,
  padding: 28,
  marginBottom: 28,
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  border: "1px solid #e8ecf0",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "1.4rem",
  color: "#1a1a1a",
  marginBottom: 8,
  fontWeight: 700,
};

const tableHeader: React.CSSProperties = {
  padding: "12px 16px",
  textAlign: "left",
  fontSize: "0.82rem",
  fontWeight: 700,
  color: "#666",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  borderBottom: "2px solid #e0e0e0",
};

const tableCell: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid #f0f0f0",
  fontSize: "0.93rem",
};

function statBox(bg: string, color: string): React.CSSProperties {
  return {
    background: bg,
    color,
    borderRadius: 10,
    padding: "20px 24px",
    textAlign: "center",
    fontWeight: 600,
  };
}
