import { useState, useMemo } from "react";

type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

interface Drug {
  name: string;
  category: string;
  risk: RiskLevel;
  bulkDiscount: number;
  shortageProbability: number;
  source: string;
  priceTrend: string;
}

const DRUG_DATABASE: Drug[] = [
  { name: "Amoxicillin 500mg Capsules", category: "Antibiotic", risk: "HIGH", bulkDiscount: 22, shortageProbability: 78, source: "India", priceTrend: "+12%" },
  { name: "Metformin 500mg Tablets", category: "Antidiabetic", risk: "HIGH", bulkDiscount: 18, shortageProbability: 71, source: "China", priceTrend: "+8%" },
  { name: "Amlodipine 5mg Tablets", category: "Calcium Channel Blocker", risk: "HIGH", bulkDiscount: 20, shortageProbability: 69, source: "India", priceTrend: "+15%" },
  { name: "Omeprazole 20mg Capsules", category: "PPI", risk: "MEDIUM", bulkDiscount: 15, shortageProbability: 45, source: "India", priceTrend: "+5%" },
  { name: "Lisinopril 10mg Tablets", category: "ACE Inhibitor", risk: "MEDIUM", bulkDiscount: 14, shortageProbability: 48, source: "India", priceTrend: "+7%" },
  { name: "Ibuprofen 400mg Tablets", category: "NSAID", risk: "MEDIUM", bulkDiscount: 12, shortageProbability: 38, source: "China", priceTrend: "+3%" },
  { name: "Ramipril 5mg Capsules", category: "ACE Inhibitor", risk: "MEDIUM", bulkDiscount: 16, shortageProbability: 42, source: "India", priceTrend: "+6%" },
  { name: "Lansoprazole 30mg Capsules", category: "PPI", risk: "LOW", bulkDiscount: 10, shortageProbability: 22, source: "EU", priceTrend: "stable" },
  { name: "Atorvastatin 40mg Tablets", category: "Statin", risk: "LOW", bulkDiscount: 11, shortageProbability: 18, source: "EU", priceTrend: "stable" },
  { name: "Paracetamol 500mg Tablets", category: "Analgesic", risk: "LOW", bulkDiscount: 8, shortageProbability: 12, source: "UK", priceTrend: "stable" },
  { name: "Simvastatin 40mg Tablets", category: "Statin", risk: "MEDIUM", bulkDiscount: 13, shortageProbability: 35, source: "India", priceTrend: "+4%" },
  { name: "Bisoprolol 5mg Tablets", category: "Beta Blocker", risk: "MEDIUM", bulkDiscount: 15, shortageProbability: 40, source: "India", priceTrend: "+6%" },
  { name: "Sertraline 50mg Tablets", category: "SSRI Antidepressant", risk: "LOW", bulkDiscount: 9, shortageProbability: 20, source: "EU", priceTrend: "stable" },
  { name: "Levothyroxine 50mcg Tablets", category: "Thyroid Hormone", risk: "HIGH", bulkDiscount: 19, shortageProbability: 65, source: "India", priceTrend: "+10%" },
  { name: "Co-amoxiclav 500/125mg Tablets", category: "Antibiotic", risk: "HIGH", bulkDiscount: 21, shortageProbability: 72, source: "India", priceTrend: "+14%" },
];

const riskOrder: Record<RiskLevel, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

export default function DrugSearch() {
  const [query, setQuery] = useState("");
  const [filterRisk, setFilterRisk] = useState<RiskLevel | "ALL">("ALL");

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    return DRUG_DATABASE
      .filter((d) => {
        const matchesQuery =
          q === "" || d.name.toLowerCase().includes(q) || d.category.toLowerCase().includes(q);
        const matchesRisk = filterRisk === "ALL" || d.risk === filterRisk;
        return matchesQuery && matchesRisk;
      })
      .sort((a, b) => riskOrder[a.risk] - riskOrder[b.risk]);
  }, [query, filterRisk]);

  const riskStyle = (risk: RiskLevel) => {
    if (risk === "HIGH") return { background: "#ffebee", color: "#c62828", border: "1px solid #ef9a9a" };
    if (risk === "MEDIUM") return { background: "#fff8e1", color: "#e65100", border: "1px solid #ffcc02" };
    return { background: "#f1f8e9", color: "#2e7d32", border: "1px solid #a5d6a7" };
  };

  const probabilityColor = (p: number) => {
    if (p >= 65) return "#c62828";
    if (p >= 35) return "#e65100";
    return "#2e7d32";
  };

  const counts = {
    HIGH: DRUG_DATABASE.filter((d) => d.risk === "HIGH").length,
    MEDIUM: DRUG_DATABASE.filter((d) => d.risk === "MEDIUM").length,
    LOW: DRUG_DATABASE.filter((d) => d.risk === "LOW").length,
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 20, fontFamily: "inherit" }}>
      <h1 style={{ fontSize: "2.2rem", color: "#1a1a1a", marginBottom: 6 }}>Drug Search</h1>
      <p style={{ color: "#666", marginBottom: 28, fontSize: "1.05rem" }}>
        Search {DRUG_DATABASE.length} UK pharmaceutical products — risk levels, bulk discounts and shortage data
      </p>

      {/* Summary Badges */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["HIGH", "MEDIUM", "LOW"] as RiskLevel[]).map((risk) => {
          const s = riskStyle(risk);
          return (
            <div
              key={risk}
              style={{
                ...s,
                padding: "8px 18px",
                borderRadius: 20,
                fontWeight: 700,
                fontSize: "0.88rem",
                cursor: "pointer",
                opacity: filterRisk !== "ALL" && filterRisk !== risk ? 0.5 : 1,
              }}
              onClick={() => setFilterRisk(filterRisk === risk ? "ALL" : risk)}
            >
              {risk}: {counts[risk]} drugs
            </div>
          );
        })}
      </div>

      {/* Search & Filter Controls */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 24,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <input
          type="text"
          placeholder="Search by drug name or category..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            flex: 1,
            minWidth: 260,
            padding: "12px 16px",
            fontSize: "1rem",
            border: "2px solid #e0e0e0",
            borderRadius: 8,
            outline: "none",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "#1976d2")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "#e0e0e0")}
        />

        <div style={{ display: "flex", gap: 8 }}>
          {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setFilterRisk(r)}
              style={{
                padding: "10px 16px",
                border: "2px solid",
                borderColor: filterRisk === r ? "#1976d2" : "#e0e0e0",
                borderRadius: 8,
                background: filterRisk === r ? "#1976d2" : "white",
                color: filterRisk === r ? "white" : "#555",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: "0.88rem",
                transition: "all 0.2s",
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      <p style={{ color: "#999", fontSize: "0.9rem", marginBottom: 16 }}>
        Showing {filtered.length} of {DRUG_DATABASE.length} drugs
      </p>

      {/* Drug Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 16,
        }}
      >
        {filtered.length === 0 ? (
          <div
            style={{
              gridColumn: "1/-1",
              padding: 40,
              textAlign: "center",
              color: "#999",
              background: "white",
              borderRadius: 12,
              border: "1px solid #e0e0e0",
            }}
          >
            No drugs found matching your search. Try a different term or clear the filter.
          </div>
        ) : (
          filtered.map((drug) => {
            const rs = riskStyle(drug.risk);
            return (
              <div
                key={drug.name}
                style={{
                  background: "white",
                  borderRadius: 12,
                  padding: 20,
                  border: "1px solid #e8ecf0",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
                  transition: "box-shadow 0.2s, transform 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = "0 6px 16px rgba(0,0,0,0.10)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = "0 2px 6px rgba(0,0,0,0.05)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <div style={{ flex: 1, paddingRight: 10 }}>
                    <div style={{ fontWeight: 700, color: "#1a1a1a", fontSize: "1rem", lineHeight: 1.3 }}>
                      {drug.name}
                    </div>
                    <div style={{ color: "#999", fontSize: "0.82rem", marginTop: 3 }}>
                      {drug.category}
                    </div>
                  </div>
                  <span
                    style={{
                      ...rs,
                      borderRadius: 20,
                      padding: "3px 12px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {drug.risk} RISK
                  </span>
                </div>

                {/* Stats row */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 10,
                    marginTop: 14,
                  }}
                >
                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.75rem", marginBottom: 2 }}>
                      BULK DISCOUNT
                    </div>
                    <div style={{ fontWeight: 700, color: "#2e7d32", fontSize: "1.3rem" }}>
                      {drug.bulkDiscount}%
                    </div>
                  </div>

                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.75rem", marginBottom: 2 }}>
                      SHORTAGE PROB.
                    </div>
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: "1.3rem",
                        color: probabilityColor(drug.shortageProbability),
                      }}
                    >
                      {drug.shortageProbability}%
                    </div>
                  </div>

                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.75rem", marginBottom: 2 }}>
                      PRIMARY SOURCE
                    </div>
                    <div style={{ fontWeight: 600, color: "#1a1a1a", fontSize: "0.95rem" }}>
                      {drug.source}
                    </div>
                  </div>

                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.75rem", marginBottom: 2 }}>
                      PRICE TREND
                    </div>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: "0.95rem",
                        color: drug.priceTrend === "stable" ? "#2e7d32" : "#c62828",
                      }}
                    >
                      {drug.priceTrend !== "stable" ? "↑ " : ""}{drug.priceTrend}
                    </div>
                  </div>
                </div>

                {/* Shortage probability bar */}
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontSize: "0.75rem", color: "#999", marginBottom: 5 }}>
                    Shortage Risk Meter
                  </div>
                  <div
                    style={{
                      height: 8,
                      background: "#f0f0f0",
                      borderRadius: 4,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${drug.shortageProbability}%`,
                        height: "100%",
                        background: probabilityColor(drug.shortageProbability),
                        borderRadius: 4,
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

const statCell: React.CSSProperties = {
  background: "#f8f9fa",
  borderRadius: 8,
  padding: "10px 12px",
};
