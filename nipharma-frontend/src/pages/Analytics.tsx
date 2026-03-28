export default function Analytics() {
  const supplySourceData = [
    { country: "India", percent: 68, color: "#1976d2", detail: "APIs & generics" },
    { country: "China", percent: 15, color: "#ff9800", detail: "Raw materials" },
    { country: "EU", percent: 10, color: "#4caf50", detail: "Branded & specialist" },
    { country: "UK/Local", percent: 5, color: "#9c27b0", detail: "OTC & domestic" },
    { country: "USA", percent: 2, color: "#f44336", detail: "Biologics & niche" },
  ];

  const shortageRiskDrugs = [
    { name: "Amoxicillin 500mg", risk: "HIGH", source: "India", trend: "+12%", trendDir: "up" },
    { name: "Metformin 500mg", risk: "HIGH", source: "China", trend: "+8%", trendDir: "up" },
    { name: "Omeprazole 20mg", risk: "MEDIUM", source: "India", trend: "+5%", trendDir: "up" },
    { name: "Lisinopril 10mg", risk: "MEDIUM", source: "India", trend: "+7%", trendDir: "up" },
    { name: "Atorvastatin 40mg", risk: "LOW", source: "EU", trend: "stable", trendDir: "stable" },
    { name: "Paracetamol 500mg", risk: "LOW", source: "UK", trend: "stable", trendDir: "stable" },
    { name: "Ibuprofen 400mg", risk: "MEDIUM", source: "China", trend: "+3%", trendDir: "up" },
    { name: "Amlodipine 5mg", risk: "HIGH", source: "India", trend: "+15%", trendDir: "up" },
    { name: "Ramipril 5mg", risk: "MEDIUM", source: "India", trend: "+6%", trendDir: "up" },
    { name: "Lansoprazole 30mg", risk: "LOW", source: "EU", trend: "stable", trendDir: "stable" },
  ];

  const nhsConcessions = [
    { drug: "Amoxicillin 500mg caps x 21", price: "£2.89", prevPrice: "£1.45" },
    { drug: "Metformin 500mg tabs x 28", price: "£1.96", prevPrice: "£0.98" },
    { drug: "Omeprazole 20mg caps x 28", price: "£2.14", prevPrice: "£1.07" },
    { drug: "Amlodipine 5mg tabs x 28", price: "£3.40", prevPrice: "£1.70" },
    { drug: "Lansoprazole 30mg caps x 28", price: "£3.22", prevPrice: "£1.61" },
  ];

  const riskColor = (risk: string) => {
    if (risk === "HIGH") return { bg: "#ffebee", color: "#c62828", border: "#ef9a9a" };
    if (risk === "MEDIUM") return { bg: "#fff8e1", color: "#e65100", border: "#ffcc02" };
    return { bg: "#f1f8e9", color: "#2e7d32", border: "#a5d6a7" };
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 20, fontFamily: "inherit" }}>
      <h1 style={{ fontSize: "2.2rem", color: "#1a1a1a", marginBottom: 6 }}>
        Supply Chain Analytics
      </h1>
      <p style={{ color: "#666", marginBottom: 36, fontSize: "1.05rem" }}>
        UK pharmaceutical supply chain intelligence — March 2026
      </p>

      {/* Section 1: Supply Source by Country */}
      <section style={sectionCard}>
        <h2 style={sectionTitle}>Supply Source by Country</h2>
        <p style={{ color: "#666", marginBottom: 24, fontSize: "0.95rem" }}>
          Proportion of UK pharmaceutical supply originating from each region
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {supplySourceData.map((item) => (
            <div key={item.country}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontWeight: 600, color: "#1a1a1a" }}>
                  {item.country}
                  <span style={{ color: "#999", fontWeight: 400, marginLeft: 8, fontSize: "0.88rem" }}>
                    {item.detail}
                  </span>
                </span>
                <span style={{ fontWeight: 700, color: item.color }}>{item.percent}%</span>
              </div>
              <div
                style={{
                  height: 22,
                  background: "#f0f4f8",
                  borderRadius: 11,
                  overflow: "hidden",
                  border: "1px solid #e0e0e0",
                }}
              >
                <div
                  style={{
                    width: `${item.percent}%`,
                    height: "100%",
                    background: item.color,
                    borderRadius: 11,
                    transition: "width 0.6s ease",
                    display: "flex",
                    alignItems: "center",
                    paddingLeft: item.percent > 10 ? 10 : 0,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 20,
            padding: "12px 16px",
            background: "#e3f2fd",
            borderRadius: 8,
            fontSize: "0.9rem",
            color: "#1565c0",
          }}
        >
          83% of UK pharmaceutical supply originates from India and China, creating significant
          geopolitical and currency risk for UK pharmacies.
        </div>
      </section>

      {/* Section 2: Shortage Risk Table */}
      <section style={{ ...sectionCard, overflowX: "auto" }}>
        <h2 style={sectionTitle}>Top 10 Drugs at Shortage Risk</h2>
        <p style={{ color: "#666", marginBottom: 20, fontSize: "0.95rem" }}>
          Based on supply chain signals, NHS concession history and import cost trends
        </p>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
          <thead>
            <tr style={{ background: "#f5f7fa" }}>
              {["Drug Name", "Risk Level", "Primary Source", "Price Trend"].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "12px 16px",
                    textAlign: "left",
                    fontSize: "0.82rem",
                    fontWeight: 700,
                    color: "#666",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    borderBottom: "2px solid #e0e0e0",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shortageRiskDrugs.map((drug, idx) => {
              const rc = riskColor(drug.risk);
              return (
                <tr
                  key={drug.name}
                  style={{ background: idx % 2 === 0 ? "#fff" : "#fafafa" }}
                >
                  <td style={tableCell}>
                    <span style={{ fontWeight: 600, color: "#1a1a1a" }}>{drug.name}</span>
                  </td>
                  <td style={tableCell}>
                    <span
                      style={{
                        background: rc.bg,
                        color: rc.color,
                        border: `1px solid ${rc.border}`,
                        borderRadius: 20,
                        padding: "3px 12px",
                        fontSize: "0.8rem",
                        fontWeight: 700,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {drug.risk}
                    </span>
                  </td>
                  <td style={tableCell}>
                    <span style={{ color: "#555" }}>{drug.source}</span>
                  </td>
                  <td style={tableCell}>
                    <span
                      style={{
                        color:
                          drug.trendDir === "up"
                            ? "#c62828"
                            : "#2e7d32",
                        fontWeight: 600,
                      }}
                    >
                      {drug.trendDir === "up" ? "↑ " : ""}
                      {drug.trend}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* Section 3: GBP/INR Exchange Impact */}
      <section style={sectionCard}>
        <h2 style={sectionTitle}>GBP/INR Exchange Rate Impact</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 16,
            marginBottom: 20,
          }}
        >
          <div style={statBox("#e3f2fd", "#1565c0")}>
            <div style={{ fontSize: "2rem", fontWeight: 700 }}>107.3</div>
            <div style={{ fontSize: "0.9rem", marginTop: 4 }}>Current GBP/INR Rate</div>
          </div>
          <div style={statBox("#ffebee", "#c62828")}>
            <div style={{ fontSize: "2rem", fontWeight: 700 }}>-2.3%</div>
            <div style={{ fontSize: "0.9rem", marginTop: 4 }}>30-Day GBP Change</div>
          </div>
          <div style={statBox("#fff8e1", "#e65100")}>
            <div style={{ fontSize: "2rem", fontWeight: 700 }}>+8–12%</div>
            <div style={{ fontSize: "0.9rem", marginTop: 4 }}>Estimated Import Cost Increase</div>
          </div>
          <div style={statBox("#f1f8e9", "#2e7d32")}>
            <div style={{ fontSize: "2rem", fontWeight: 700 }}>£45k</div>
            <div style={{ fontSize: "0.9rem", marginTop: 4 }}>Max Annual Savings via Bulk Buy</div>
          </div>
        </div>
        <div
          style={{
            padding: "14px 18px",
            background: "#fff8e1",
            border: "1px solid #ffcc02",
            borderRadius: 8,
            fontSize: "0.93rem",
            color: "#795548",
            lineHeight: 1.6,
          }}
        >
          <strong>Impact Analysis:</strong> A weakening pound against the Indian rupee directly
          increases the landed cost of generic APIs and finished dose forms imported from India.
          Pharmacies that lock in bulk purchase agreements now — before further depreciation — can
          hedge against 6-12 months of price increases and secure discounts of 15-25% versus spot
          buying.
        </div>
      </section>

      {/* Section 4: NHS Concessions This Month */}
      <section style={sectionCard}>
        <h2 style={sectionTitle}>NHS Concessions This Month</h2>
        <p style={{ color: "#666", marginBottom: 20, fontSize: "0.95rem" }}>
          Drugs granted concessionary pricing by NHS England — March 2026
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {nhsConcessions.map((c) => (
            <div
              key={c.drug}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 18px",
                background: "#f8f9fa",
                border: "1px solid #e0e0e0",
                borderRadius: 8,
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              <span style={{ fontWeight: 600, color: "#1a1a1a", flex: 1, minWidth: 200 }}>
                {c.drug}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <span
                  style={{ color: "#999", textDecoration: "line-through", fontSize: "0.9rem" }}
                >
                  {c.prevPrice}
                </span>
                <span
                  style={{
                    background: "#e3f2fd",
                    color: "#1565c0",
                    fontWeight: 700,
                    padding: "4px 14px",
                    borderRadius: 20,
                    fontSize: "0.95rem",
                  }}
                >
                  {c.price}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 16,
            padding: "10px 16px",
            background: "#f1f8e9",
            borderRadius: 8,
            fontSize: "0.88rem",
            color: "#33691e",
          }}
        >
          Concession prices are set monthly by NHS England. Pharmacies should verify current prices
          on the Drug Tariff before ordering.
        </div>
      </section>
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
