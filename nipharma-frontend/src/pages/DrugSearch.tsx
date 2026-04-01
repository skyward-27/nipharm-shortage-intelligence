import { useState, useMemo } from "react";

type RiskLevel = "HIGH" | "MEDIUM" | "LOW";
type ActionTag = "BUY NOW" | "BUFFER" | "MONITOR";
type BNFCategory = "CV" | "GI" | "CNS" | "Respiratory" | "Endocrine" | "Antibiotic" | "Analgesic" | "Immunology" | "Urology" | "Dermatology";

interface Drug {
  name: string;
  category: string;
  bnfCategory: BNFCategory;
  risk: RiskLevel;
  bulkDiscount: number;
  shortageProbability: number;
  source: string;
  priceTrend: string;
  alternative: string;
}

const DRUG_DATABASE: Drug[] = [
  { name: "Amoxicillin 500mg Capsules", category: "Antibiotic", bnfCategory: "Antibiotic", risk: "HIGH", bulkDiscount: 22, shortageProbability: 78, source: "India", priceTrend: "+12%", alternative: "Co-amoxiclav 500/125mg or Clarithromycin 500mg" },
  { name: "Metformin 1g Tablets", category: "Antidiabetic", bnfCategory: "Endocrine", risk: "HIGH", bulkDiscount: 18, shortageProbability: 71, source: "China", priceTrend: "+8%", alternative: "Metformin 500mg ×2 tablets (same dose)" },
  { name: "Metformin 500mg Tablets", category: "Antidiabetic", bnfCategory: "Endocrine", risk: "HIGH", bulkDiscount: 16, shortageProbability: 68, source: "China", priceTrend: "+8%", alternative: "Sitagliptin 100mg or Empagliflozin 10mg" },
  { name: "Amlodipine 10mg Tablets", category: "Calcium Channel Blocker", bnfCategory: "CV", risk: "HIGH", bulkDiscount: 20, shortageProbability: 75, source: "India", priceTrend: "+15%", alternative: "Felodipine 10mg or Nifedipine MR 30mg" },
  { name: "Amlodipine 5mg Tablets", category: "Calcium Channel Blocker", bnfCategory: "CV", risk: "HIGH", bulkDiscount: 19, shortageProbability: 69, source: "India", priceTrend: "+15%", alternative: "Felodipine 5mg or Lercanidipine 10mg" },
  { name: "Levothyroxine 100mcg Tablets", category: "Thyroid Hormone", bnfCategory: "Endocrine", risk: "HIGH", bulkDiscount: 19, shortageProbability: 73, source: "India", priceTrend: "+10%", alternative: "Levothyroxine 50mcg ×2 (same dose, same drug)" },
  { name: "Co-amoxiclav 500/125mg Tablets", category: "Antibiotic", bnfCategory: "Antibiotic", risk: "HIGH", bulkDiscount: 21, shortageProbability: 72, source: "India", priceTrend: "+14%", alternative: "Clarithromycin 500mg or Doxycycline 100mg" },
  { name: "Furosemide 40mg Tablets", category: "Loop Diuretic", bnfCategory: "CV", risk: "HIGH", bulkDiscount: 17, shortageProbability: 70, source: "India", priceTrend: "+11%", alternative: "Bumetanide 1mg (1mg ≈ furosemide 40mg)" },
  { name: "Ramipril 10mg Capsules", category: "ACE Inhibitor", bnfCategory: "CV", risk: "HIGH", bulkDiscount: 16, shortageProbability: 66, source: "India", priceTrend: "+9%", alternative: "Lisinopril 10mg or Enalapril 10mg" },
  { name: "Sertraline 50mg Tablets", category: "SSRI Antidepressant", bnfCategory: "CNS", risk: "HIGH", bulkDiscount: 18, shortageProbability: 67, source: "India", priceTrend: "+9%", alternative: "Citalopram 20mg or Fluoxetine 20mg" },
  { name: "Omeprazole 20mg Capsules", category: "Proton Pump Inhibitor", bnfCategory: "GI", risk: "MEDIUM", bulkDiscount: 15, shortageProbability: 52, source: "India", priceTrend: "+5%", alternative: "Lansoprazole 30mg or Pantoprazole 20mg" },
  { name: "Lisinopril 10mg Tablets", category: "ACE Inhibitor", bnfCategory: "CV", risk: "MEDIUM", bulkDiscount: 14, shortageProbability: 48, source: "India", priceTrend: "+7%", alternative: "Ramipril 5mg or Perindopril 4mg" },
  { name: "Atorvastatin 40mg Tablets", category: "Statin", bnfCategory: "CV", risk: "MEDIUM", bulkDiscount: 13, shortageProbability: 55, source: "EU", priceTrend: "+6%", alternative: "Rosuvastatin 20mg or Simvastatin 40mg" },
  { name: "Bisoprolol 5mg Tablets", category: "Beta Blocker", bnfCategory: "CV", risk: "MEDIUM", bulkDiscount: 15, shortageProbability: 50, source: "India", priceTrend: "+6%", alternative: "Atenolol 50mg or Carvedilol 6.25mg" },
  { name: "Lansoprazole 30mg Capsules", category: "Proton Pump Inhibitor", bnfCategory: "GI", risk: "MEDIUM", bulkDiscount: 12, shortageProbability: 44, source: "EU", priceTrend: "+4%", alternative: "Omeprazole 20mg or Pantoprazole 20mg" },
  { name: "Ibuprofen 400mg Tablets", category: "NSAID", bnfCategory: "Analgesic", risk: "MEDIUM", bulkDiscount: 12, shortageProbability: 38, source: "China", priceTrend: "+3%", alternative: "Naproxen 250mg or Diclofenac 50mg" },
  { name: "Ramipril 5mg Capsules", category: "ACE Inhibitor", bnfCategory: "CV", risk: "MEDIUM", bulkDiscount: 14, shortageProbability: 42, source: "India", priceTrend: "+6%", alternative: "Lisinopril 5mg or Enalapril 5mg" },
  { name: "Simvastatin 40mg Tablets", category: "Statin", bnfCategory: "CV", risk: "MEDIUM", bulkDiscount: 13, shortageProbability: 40, source: "India", priceTrend: "+4%", alternative: "Atorvastatin 20mg or Rosuvastatin 10mg" },
  { name: "Naproxen 500mg Tablets", category: "NSAID", bnfCategory: "Analgesic", risk: "MEDIUM", bulkDiscount: 11, shortageProbability: 36, source: "India", priceTrend: "+3%", alternative: "Ibuprofen 400mg or Diclofenac 50mg" },
  { name: "Citalopram 20mg Tablets", category: "SSRI Antidepressant", bnfCategory: "CNS", risk: "MEDIUM", bulkDiscount: 13, shortageProbability: 45, source: "EU", priceTrend: "+5%", alternative: "Sertraline 50mg or Fluoxetine 20mg" },
  { name: "Salbutamol 100mcg Inhaler", category: "Beta2 Agonist", bnfCategory: "Respiratory", risk: "MEDIUM", bulkDiscount: 10, shortageProbability: 48, source: "EU", priceTrend: "+7%", alternative: "Terbutaline 500mcg inhaler (Bricanyl)" },
  { name: "Atorvastatin 20mg Tablets", category: "Statin", bnfCategory: "CV", risk: "LOW", bulkDiscount: 11, shortageProbability: 22, source: "EU", priceTrend: "stable", alternative: "Rosuvastatin 10mg or Simvastatin 40mg" },
  { name: "Paracetamol 500mg Tablets", category: "Analgesic", bnfCategory: "Analgesic", risk: "LOW", bulkDiscount: 8, shortageProbability: 12, source: "UK", priceTrend: "stable", alternative: "Ibuprofen 400mg (if tolerated)" },
  { name: "Sertraline 100mg Tablets", category: "SSRI Antidepressant", bnfCategory: "CNS", risk: "LOW", bulkDiscount: 9, shortageProbability: 20, source: "EU", priceTrend: "stable", alternative: "Citalopram 40mg or Fluoxetine 40mg" },
  { name: "Levothyroxine 50mcg Tablets", category: "Thyroid Hormone", bnfCategory: "Endocrine", risk: "LOW", bulkDiscount: 10, shortageProbability: 28, source: "India", priceTrend: "+3%", alternative: "No direct alternative — dose adjustment only" },
  { name: "Omeprazole 40mg Capsules", category: "Proton Pump Inhibitor", bnfCategory: "GI", risk: "LOW", bulkDiscount: 10, shortageProbability: 25, source: "EU", priceTrend: "stable", alternative: "Pantoprazole 40mg or Esomeprazole 40mg" },
];

const getAction = (p: number): ActionTag => {
  if (p >= 65) return "BUY NOW";
  if (p >= 35) return "BUFFER";
  return "MONITOR";
};

const bnfCategoryColor: Record<BNFCategory, { bg: string; color: string }> = {
  CV:         { bg: "#fce4ec", color: "#880e4f" },
  GI:         { bg: "#e8f5e9", color: "#1b5e20" },
  CNS:        { bg: "#ede7f6", color: "#4a148c" },
  Respiratory:{ bg: "#e3f2fd", color: "#0d47a1" },
  Endocrine:  { bg: "#fff8e1", color: "#e65100" },
  Antibiotic: { bg: "#fbe9e7", color: "#bf360c" },
  Analgesic:  { bg: "#f3e5f5", color: "#6a1b9a" },
  Immunology: { bg: "#e0f7fa", color: "#006064" },
  Urology:    { bg: "#f1f8e9", color: "#33691e" },
  Dermatology:{ bg: "#fafafa", color: "#424242" },
};

const actionStyle = (a: ActionTag) => {
  if (a === "BUY NOW") return { background: "#c62828", color: "white", border: "none" };
  if (a === "BUFFER")  return { background: "#e65100", color: "white", border: "none" };
  return { background: "#2e7d32", color: "white", border: "none" };
};

const riskOrder: Record<RiskLevel, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

export default function DrugSearch() {
  const [query, setQuery]         = useState("");
  const [filterRisk, setFilterRisk] = useState<RiskLevel | "ALL">("ALL");
  const [filterBNF, setFilterBNF]   = useState<BNFCategory | "ALL">("ALL");

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    return DRUG_DATABASE
      .filter((d) => {
        const matchesQuery = q === "" || d.name.toLowerCase().includes(q) || d.category.toLowerCase().includes(q) || d.alternative.toLowerCase().includes(q);
        const matchesRisk  = filterRisk === "ALL" || d.risk === filterRisk;
        const matchesBNF   = filterBNF === "ALL" || d.bnfCategory === filterBNF;
        return matchesQuery && matchesRisk && matchesBNF;
      })
      .sort((a, b) => riskOrder[a.risk] - riskOrder[b.risk]);
  }, [query, filterRisk, filterBNF]);

  const riskStyle = (risk: RiskLevel) => {
    if (risk === "HIGH")   return { background: "#ffebee", color: "#c62828", border: "1px solid #ef9a9a" };
    if (risk === "MEDIUM") return { background: "#fff8e1", color: "#e65100", border: "1px solid #ffcc02" };
    return { background: "#f1f8e9", color: "#2e7d32", border: "1px solid #a5d6a7" };
  };

  const probabilityColor = (p: number) => {
    if (p >= 65) return "#c62828";
    if (p >= 35) return "#e65100";
    return "#2e7d32";
  };

  const counts = {
    HIGH:   DRUG_DATABASE.filter((d) => d.risk === "HIGH").length,
    MEDIUM: DRUG_DATABASE.filter((d) => d.risk === "MEDIUM").length,
    LOW:    DRUG_DATABASE.filter((d) => d.risk === "LOW").length,
  };

  const bnfCategories: BNFCategory[] = ["CV", "GI", "CNS", "Respiratory", "Endocrine", "Antibiotic", "Analgesic"];

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 20, fontFamily: "inherit" }}>
      <h1 style={{ fontSize: "2.2rem", color: "#1a1a1a", marginBottom: 6 }}>Drug Search</h1>
      <p style={{ color: "#666", marginBottom: 20, fontSize: "1.05rem" }}>
        {DRUG_DATABASE.length} UK pharmaceutical products — shortage risk, BNF category, bulk discounts & alternatives
      </p>

      {/* Risk Summary Badges */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        {(["HIGH", "MEDIUM", "LOW"] as RiskLevel[]).map((risk) => {
          const s = riskStyle(risk);
          return (
            <div key={risk} style={{ ...s, padding: "7px 16px", borderRadius: 20, fontWeight: 700, fontSize: "0.85rem", cursor: "pointer", opacity: filterRisk !== "ALL" && filterRisk !== risk ? 0.45 : 1 }}
              onClick={() => setFilterRisk(filterRisk === risk ? "ALL" : risk)}>
              {risk}: {counts[risk]} drugs
            </div>
          );
        })}
      </div>

      {/* BNF Category Filter Pills */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        <button onClick={() => setFilterBNF("ALL")} style={{ padding: "6px 14px", borderRadius: 20, border: "2px solid", borderColor: filterBNF === "ALL" ? "#1976d2" : "#ddd", background: filterBNF === "ALL" ? "#1976d2" : "white", color: filterBNF === "ALL" ? "white" : "#555", fontWeight: 600, fontSize: "0.82rem", cursor: "pointer" }}>ALL</button>
        {bnfCategories.map((cat) => {
          const cs = bnfCategoryColor[cat];
          const active = filterBNF === cat;
          return (
            <button key={cat} onClick={() => setFilterBNF(filterBNF === cat ? "ALL" : cat)}
              style={{ padding: "6px 14px", borderRadius: 20, border: `2px solid ${cs.color}`, background: active ? cs.color : cs.bg, color: active ? "white" : cs.color, fontWeight: 600, fontSize: "0.82rem", cursor: "pointer" }}>
              {cat}
            </button>
          );
        })}
      </div>

      {/* Search & Risk Filter */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <input type="text" placeholder="Search drug name, category or alternative..." value={query} onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1, minWidth: 260, padding: "12px 16px", fontSize: "1rem", border: "2px solid #e0e0e0", borderRadius: 8, outline: "none" }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "#1976d2")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "#e0e0e0")} />
        <div style={{ display: "flex", gap: 8 }}>
          {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((r) => (
            <button key={r} onClick={() => setFilterRisk(r)}
              style={{ padding: "10px 16px", border: "2px solid", borderColor: filterRisk === r ? "#1976d2" : "#e0e0e0", borderRadius: 8, background: filterRisk === r ? "#1976d2" : "white", color: filterRisk === r ? "white" : "#555", fontWeight: 600, cursor: "pointer", fontSize: "0.88rem" }}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <p style={{ color: "#999", fontSize: "0.9rem", marginBottom: 16 }}>Showing {filtered.length} of {DRUG_DATABASE.length} drugs</p>

      {/* Drug Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
        {filtered.length === 0 ? (
          <div style={{ gridColumn: "1/-1", padding: 40, textAlign: "center", color: "#999", background: "white", borderRadius: 12, border: "1px solid #e0e0e0" }}>
            No drugs found. Try a different search term or clear the filter.
          </div>
        ) : (
          filtered.map((drug) => {
            const rs  = riskStyle(drug.risk);
            const action = getAction(drug.shortageProbability);
            const as  = actionStyle(action);
            const bnf = bnfCategoryColor[drug.bnfCategory];
            return (
              <div key={drug.name}
                style={{ background: "white", borderRadius: 12, padding: 20, border: "1px solid #e8ecf0", boxShadow: "0 2px 6px rgba(0,0,0,0.05)", transition: "box-shadow 0.2s, transform 0.2s" }}
                onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 6px 16px rgba(0,0,0,0.10)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 2px 6px rgba(0,0,0,0.05)"; e.currentTarget.style.transform = "translateY(0)"; }}>

                {/* Header row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div style={{ flex: 1, paddingRight: 8 }}>
                    <div style={{ fontWeight: 700, color: "#1a1a1a", fontSize: "1rem", lineHeight: 1.3 }}>{drug.name}</div>
                    <div style={{ display: "flex", gap: 6, marginTop: 5, flexWrap: "wrap" }}>
                      <span style={{ ...bnf, borderRadius: 12, padding: "2px 10px", fontSize: "0.75rem", fontWeight: 700 }}>{drug.bnfCategory}</span>
                      <span style={{ color: "#999", fontSize: "0.78rem", padding: "2px 0" }}>{drug.category}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5 }}>
                    <span style={{ ...rs, borderRadius: 20, padding: "3px 12px", fontSize: "0.75rem", fontWeight: 700, whiteSpace: "nowrap" }}>{drug.risk} RISK</span>
                    <span style={{ ...as, borderRadius: 20, padding: "3px 12px", fontSize: "0.75rem", fontWeight: 800, whiteSpace: "nowrap" }}>{action}</span>
                  </div>
                </div>

                {/* Stats grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.72rem", marginBottom: 2 }}>BULK DISCOUNT</div>
                    <div style={{ fontWeight: 700, color: "#2e7d32", fontSize: "1.2rem" }}>{drug.bulkDiscount}%</div>
                  </div>
                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.72rem", marginBottom: 2 }}>SHORTAGE PROB.</div>
                    <div style={{ fontWeight: 700, fontSize: "1.2rem", color: probabilityColor(drug.shortageProbability) }}>{drug.shortageProbability}%</div>
                  </div>
                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.72rem", marginBottom: 2 }}>PRIMARY SOURCE</div>
                    <div style={{ fontWeight: 600, color: "#1a1a1a", fontSize: "0.9rem" }}>{drug.source}</div>
                  </div>
                  <div style={statCell}>
                    <div style={{ color: "#999", fontSize: "0.72rem", marginBottom: 2 }}>PRICE TREND</div>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: drug.priceTrend === "stable" ? "#2e7d32" : "#c62828" }}>
                      {drug.priceTrend !== "stable" ? "↑ " : ""}{drug.priceTrend}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: "0.72rem", color: "#999", marginBottom: 4 }}>Shortage Risk Meter</div>
                  <div style={{ height: 7, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${drug.shortageProbability}%`, height: "100%", background: probabilityColor(drug.shortageProbability), borderRadius: 4 }} />
                  </div>
                </div>

                {/* Alternative drug */}
                <div style={{ marginTop: 12, padding: "8px 12px", background: "#f0f4ff", borderRadius: 8, borderLeft: "3px solid #1976d2" }}>
                  <div style={{ fontSize: "0.72rem", color: "#1976d2", fontWeight: 700, marginBottom: 2 }}>ALTERNATIVE IF UNAVAILABLE</div>
                  <div style={{ fontSize: "0.85rem", color: "#333", fontWeight: 500 }}>{drug.alternative}</div>
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
