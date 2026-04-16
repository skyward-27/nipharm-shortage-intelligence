import { useState, useRef, useCallback } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface QueryResult {
  success: boolean;
  sql?: string;
  columns?: string[];
  rows?: Record<string, any>[];
  row_count?: number;
  chart_hint?: "bar" | "line" | "table";
  explanation?: string;
  error?: string;
}

type QuestionCategory = "2022 Peak" | "Trends" | "Prices" | "Alerts";

const QUESTION_CATEGORIES: { id: QuestionCategory; icon: string; desc: string }[] = [
  { id: "2022 Peak", icon: "🔥", desc: "The year 198 drugs were conceded at once" },
  { id: "Trends",    icon: "📈", desc: "Monthly & yearly patterns" },
  { id: "Prices",    icon: "💊", desc: "NHS tariff & concession prices" },
  { id: "Alerts",    icon: "🚨", desc: "MHRA shortage publications" },
];

const QUICK_QUESTIONS: Record<QuestionCategory, { label: string; q: string }[]> = {
  "2022 Peak": [
    { label: "🔥 Dec 2022 — peak month drugs",    q: "all drugs on concession in December 2022 ordered by price descending" },
    { label: "📊 2022 monthly count",              q: "how many drugs went on concession each month in 2022?" },
    { label: "🆕 New in 2022 (never seen before)", q: "drugs that first appeared on concession in 2022" },
    { label: "💸 Most expensive 2022 concessions", q: "top 20 most expensive concession prices in 2022" },
    { label: "📉 2022 vs 2021 comparison",         q: "total concession count per year for 2021 and 2022" },
    { label: "💊 Which categories spiked 2022?",   q: "drug names that had the most concession months in 2022" },
  ],
  "Trends": [
    { label: "📅 Year-on-year totals",             q: "how many drugs went on concession each year?" },
    { label: "❄️ Winter vs summer seasonality",    q: "average concession count for winter months (11,12,1,2) vs summer (5,6,7,8)" },
    { label: "🚀 Fastest growing drugs",           q: "drugs with more than 12 concession events between 2020 and 2026" },
    { label: "🔁 Longest concession streaks",      q: "which drugs had the most total concession months?" },
    { label: "📆 2025 vs 2026 so far",             q: "total drugs on concession per month for 2025 and 2026" },
  ],
  "Prices": [
    { label: "💰 Highest concession prices ever",  q: "top 20 highest concession prices ever recorded" },
    { label: "📊 Metformin 500mg price history",   q: "metformin 500mg tablets price history by month" },
    { label: "🩺 Omeprazole 20mg history",         q: "omeprazole 20mg gastro-resistant capsules price history" },
    { label: "📈 Biggest price jumps (tariff)",    q: "drugs where price_gbp exceeded 50 in any month" },
    { label: "💊 Insulin concessions ever",        q: "all insulin drugs that ever appeared on concession" },
    { label: "🔍 Compare concession vs tariff",    q: "drugs where concession price exceeded 100" },
  ],
  "Alerts": [
    { label: "🚨 Latest MHRA alerts",              q: "most recent 20 MHRA shortage publications ordered by date" },
    { label: "🔎 Amoxicillin alerts",              q: "MHRA alerts about amoxicillin" },
    { label: "💉 Insulin shortage alerts",         q: "MHRA alerts mentioning insulin shortage" },
    { label: "📋 Alerts in 2023",                  q: "MHRA shortage publications from 2023 ordered by date" },
    { label: "🏭 Manufacturing alerts",            q: "MHRA alerts mentioning manufacturing or supply" },
  ],
};

const YEAR_FILTERS = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"];

/* ── Mini bar chart (pure SVG) ────────────────────────────────────── */
function BarChart({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  if (rows.length === 0 || columns.length < 2) return null;

  const labelCol = columns[0];
  const valueCol = columns[1];
  const values   = rows.map(r => parseFloat(r[valueCol]) || 0);
  const maxVal   = Math.max(...values, 1);
  const W = 860, BAR_H = 28, GAP = 6, PAD_L = 220, PAD_R = 80;
  const totalH   = rows.length * (BAR_H + GAP) + 40;
  const innerW   = W - PAD_L - PAD_R;

  return (
    <svg viewBox={`0 0 ${W} ${totalH}`} style={{ width: "100%", overflow: "visible", display: "block" }}>
      {rows.map((row, i) => {
        const val  = values[i];
        const barW = (val / maxVal) * innerW;
        const y    = i * (BAR_H + GAP) + 20;
        const isHov = hovered === i;
        const label = String(row[labelCol] ?? "").slice(0, 32);
        const isPeak = String(row[labelCol] ?? "").includes("2022-12") || String(row[labelCol] ?? "").includes("Dec 2022");
        const barColor = isPeak ? "#e53935" : (isHov ? "#1565c0" : "#42a5f5");
        return (
          <g key={i} style={{ cursor: "default" }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}>
            <text x={PAD_L - 8} y={y + BAR_H / 2 + 4} textAnchor="end"
              fontSize={11} fill={isHov ? "#1565c0" : "#444"}
              fontWeight={isHov ? "700" : "400"}>
              {label}
            </text>
            <rect x={PAD_L} y={y} width={Math.max(barW, 2)} height={BAR_H}
              rx={4} fill={barColor} opacity={isHov ? 1 : 0.82} />
            <text x={PAD_L + barW + 6} y={y + BAR_H / 2 + 4}
              fontSize={11} fill="#555" fontWeight="600">
              {typeof val === "number" && val % 1 !== 0 ? `£${val.toFixed(2)}` : val.toLocaleString()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ── Mini line chart (pure SVG) ──────────────────────────────────── */
function LineChart({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  if (rows.length < 2 || columns.length < 2) return null;

  const xCol  = columns[0];
  const yCol  = columns[1];
  const vals  = rows.map(r => parseFloat(r[yCol]) || 0);
  const minV  = Math.min(...vals);
  const maxV  = Math.max(...vals, minV + 1);
  const range = maxV - minV;

  const W = 860, H = 220, PL = 60, PR = 20, PT = 20, PB = 40;
  const iW = W - PL - PR, iH = H - PT - PB;

  const xOf = (i: number) => PL + (i / (rows.length - 1)) * iW;
  const yOf = (v: number) => PT + iH - ((v - minV) / range) * iH;
  const pts = rows.map((r, i) => `${xOf(i)},${yOf(vals[i])}`).join(" ");

  // Find peak index
  const peakIdx = vals.indexOf(Math.max(...vals));

  const tickEvery = Math.max(1, Math.floor(rows.length / 10));
  const ticks = rows.filter((_, i) => i % tickEvery === 0 || i === rows.length - 1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", overflow: "visible" }}>
      <defs>
        <linearGradient id="lg2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1565c0" stopOpacity={0.18} />
          <stop offset="100%" stopColor="#1565c0" stopOpacity={0} />
        </linearGradient>
      </defs>
      {/* grid */}
      {[minV, (minV + maxV) / 2, maxV].map((v, k) => (
        <g key={k}>
          <line x1={PL} x2={W - PR} y1={yOf(v)} y2={yOf(v)} stroke="#e8ecf0" strokeWidth={1} />
          <text x={PL - 6} y={yOf(v) + 4} textAnchor="end" fontSize={10} fill="#aaa">
            {v % 1 !== 0 ? `£${v.toFixed(2)}` : Math.round(v)}
          </text>
        </g>
      ))}
      {/* area */}
      <polygon points={`${PL},${PT + iH} ${pts} ${xOf(rows.length - 1)},${PT + iH}`} fill="url(#lg2)" />
      {/* line */}
      <polyline points={pts} fill="none" stroke="#1565c0" strokeWidth={2.5} strokeLinejoin="round" />
      {/* peak marker */}
      {peakIdx >= 0 && (
        <g>
          <line x1={xOf(peakIdx)} x2={xOf(peakIdx)} y1={PT} y2={yOf(vals[peakIdx]) - 8}
            stroke="#e53935" strokeWidth={1.5} strokeDasharray="3 3" />
          <circle cx={xOf(peakIdx)} cy={yOf(vals[peakIdx])} r={6}
            fill="#e53935" stroke="#fff" strokeWidth={2} />
          <rect x={xOf(peakIdx) - 36} y={PT - 2} width={72} height={18} rx={4} fill="#e53935" opacity={0.9} />
          <text x={xOf(peakIdx)} y={PT + 12} textAnchor="middle" fontSize={10} fill="#fff" fontWeight="700">
            PEAK: {vals[peakIdx]}
          </text>
        </g>
      )}
      {/* dots */}
      {rows.map((r, i) => (
        <circle key={i} cx={xOf(i)} cy={yOf(vals[i])} r={hovered === i ? 5 : 3}
          fill={hovered === i ? "#1565c0" : "#fff"} stroke="#1565c0" strokeWidth={2}
          style={{ cursor: "pointer" }}
          onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
          <title>{`${r[xCol]}: ${vals[i]}`}</title>
        </circle>
      ))}
      {/* hover tooltip */}
      {hovered !== null && (
        <g>
          <rect x={Math.min(xOf(hovered) - 52, W - 120)} y={yOf(vals[hovered]) - 48} width={104} height={36}
            rx={5} fill="#1a1a1a" opacity={0.88} />
          <text x={Math.min(xOf(hovered), W - 66)} y={yOf(vals[hovered]) - 30} textAnchor="middle" fontSize={10} fill="#ccc">
            {String(rows[hovered][xCol]).slice(0, 14)}
          </text>
          <text x={Math.min(xOf(hovered), W - 66)} y={yOf(vals[hovered]) - 16} textAnchor="middle" fontSize={12} fill="#64b5f6" fontWeight="700">
            {vals[hovered] % 1 !== 0 ? `£${vals[hovered].toFixed(2)}` : vals[hovered].toLocaleString()}
          </text>
        </g>
      )}
      {/* x-axis ticks */}
      {ticks.map((r, i) => {
        const origIdx = rows.indexOf(r);
        return (
          <text key={i} x={xOf(origIdx)} y={H - 4} textAnchor="middle" fontSize={9} fill="#888">
            {String(r[xCol]).slice(0, 7)}
          </text>
        );
      })}
    </svg>
  );
}

/* ── Result table ─────────────────────────────────────────────────── */
function ResultTable({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const fmt = (v: any, col: string) => {
    if (v === null || v === undefined) return <span style={{ color: "#bbb" }}>—</span>;
    const colL = col.toLowerCase();
    if ((colL.includes("price") || colL.includes("gbp") || colL === "concession_price") && typeof v === "number") {
      return <span style={{ fontFamily: "monospace", color: "#1565c0", fontWeight: 600 }}>£{v.toFixed(2)}</span>;
    }
    if (colL.includes("month") && typeof v === "string" && v.match(/^\d{4}-\d{2}$/)) {
      const [y, m] = v.split("-");
      const month = new Date(parseInt(y), parseInt(m) - 1).toLocaleString("default", { month: "short" });
      return <span style={{ fontFamily: "monospace" }}>{month} {y}</span>;
    }
    if (typeof v === "number") return v.toLocaleString();
    return String(v);
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
        <thead>
          <tr style={{ background: "#f0f5ff", position: "sticky", top: 0 }}>
            {columns.map(c => (
              <th key={c} style={{
                padding: "9px 14px", textAlign: "left", fontWeight: 700,
                color: "#1565c0", borderBottom: "2px solid #c8d8f5",
                whiteSpace: "nowrap", fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.04em"
              }}>{c.replace(/_/g, " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#f8fafc", transition: "background 0.1s" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#eef4ff")}
              onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f8fafc")}>
              {columns.map(c => (
                <td key={c} style={{ padding: "8px 14px", borderBottom: "1px solid #f0f0f0", color: "#333" }}>
                  {fmt(row[c], c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Year filter quick-fire ───────────────────────────────────────── */
function YearFilter({ onYear }: { onYear: (year: string) => void }) {
  const [active, setActive] = useState<string | null>(null);
  const handle = (y: string) => {
    setActive(y);
    onYear(y);
  };
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: "0.75rem", color: "#aaa", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 8 }}>
        🗓️ Jump to year
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {YEAR_FILTERS.map(y => (
          <button key={y} onClick={() => handle(y)} style={{
            padding: "5px 14px", borderRadius: 16, border: "1.5px solid",
            borderColor: active === y ? "#e53935" : "#dde3ea",
            background: active === y ? "#ffebee" : (y === "2022" ? "#fff8e1" : "#f8fafc"),
            color: active === y ? "#c62828" : (y === "2022" ? "#e65100" : "#555"),
            fontSize: "0.84rem", fontWeight: active === y ? 700 : (y === "2022" ? 600 : 400),
            cursor: "pointer", transition: "all 0.15s",
          }}>
            {y === "2022" ? "🔥 2022" : y}
          </button>
        ))}
        <span style={{ fontSize: "0.75rem", color: "#bbb", alignSelf: "center", marginLeft: 4 }}>
          ← 2022 = peak crisis year (198 drugs conceded in Dec)
        </span>
      </div>
    </div>
  );
}

/* ── Main page ────────────────────────────────────────────────────── */
export default function ConcessionLens() {
  const [question, setQuestion]         = useState("");
  const [sql, setSql]                   = useState("");
  const [result, setResult]             = useState<QueryResult | null>(null);
  const [loading, setLoading]           = useState(false);
  const [mode, setMode]                 = useState<"nl" | "sql">("nl");
  const [activeQ, setActiveQ]           = useState("");
  const [activeCategory, setActiveCategory] = useState<QuestionCategory>("2022 Peak");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const runQuery = useCallback(async (opts: { question?: string; sql?: string }) => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opts),
      });
      const data: QueryResult = await res.json();
      setResult(data);
      if (data.sql) setSql(data.sql);
    } catch {
      setResult({ success: false, error: "Failed to connect to backend — the AI query engine may be loading. Try again in a moment." });
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAsk = () => {
    if (mode === "nl" && question.trim()) runQuery({ question });
    else if (mode === "sql" && sql.trim()) runQuery({ sql });
  };

  const handleQuick = (q: string, label: string) => {
    setQuestion(q);
    setActiveQ(label);
    setMode("nl");
    runQuery({ question: q });
  };

  const handleYear = (year: string) => {
    const q = `all drugs on concession in ${year} with their prices, ordered by month`;
    setQuestion(q);
    setActiveQ("");
    setMode("nl");
    runQuery({ question: q });
  };

  const exportCSV = () => {
    if (!result?.rows?.length || !result.columns) return;
    const header = result.columns.join(",");
    const body = result.rows.map(r =>
      result.columns!.map(c => JSON.stringify(r[c] ?? "")).join(",")
    ).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `nipharma_${Date.now()}.csv`;
    a.click();
  };

  const renderChart = () => {
    if (!result?.success || !result.rows?.length || !result.columns) return null;
    if (result.rows.length < 2) return null;
    if (result.chart_hint === "line") return <LineChart columns={result.columns} rows={result.rows} />;
    if (result.chart_hint === "bar" && result.rows.length <= 40) return <BarChart columns={result.columns} rows={result.rows} />;
    return null;
  };

  const chart = renderChart();

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: "24px 20px", fontFamily: "inherit" }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.9rem", fontWeight: 800, color: "#1a1a1a", margin: 0 }}>
            🔍 Concession Lens
          </h1>
          <span style={{
            background: "#fff8e1", color: "#e65100", border: "1px solid #ffe082",
            borderRadius: 20, padding: "3px 12px", fontSize: "0.78rem", fontWeight: 700
          }}>
            Historical data · Jan 2020 – Feb 2026
          </span>
        </div>
        <p style={{ color: "#666", fontSize: "0.97rem", margin: "6px 0 0" }}>
          Explore 7,742 concession events and 15k NHS tariff prices in plain English — no SQL knowledge needed.
        </p>
      </div>

      {/* ── How it works (compact) ── */}
      <div style={{
        background: "linear-gradient(135deg, #e8f4fd 0%, #f0f8ff 100%)",
        border: "1px solid #bbdefb", borderRadius: 12, padding: "14px 20px",
        marginBottom: 24, display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center"
      }}>
        {[
          { icon: "💬", text: "Type any question in plain English" },
          { icon: "🤖", text: "AI converts to a database query" },
          { icon: "📊", text: "Results shown as chart or table" },
          { icon: "⬇", text: "Export CSV for your records" },
        ].map(({ icon, text }) => (
          <div key={text} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: "0.85rem", color: "#1565c0" }}>
            <span style={{ fontSize: "1.1rem" }}>{icon}</span>
            <span>{text}</span>
          </div>
        ))}
      </div>

      {/* ── Year filter ── */}
      <YearFilter onYear={handleYear} />

      {/* ── Question categories + chips ── */}
      <div style={{ marginBottom: 24 }}>
        {/* Category tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
          {QUESTION_CATEGORIES.map(cat => (
            <button key={cat.id} onClick={() => setActiveCategory(cat.id)} style={{
              padding: "7px 16px", borderRadius: 22, border: "1.5px solid",
              borderColor: activeCategory === cat.id ? "#1565c0" : "#dde3ea",
              background: activeCategory === cat.id ? "#1565c0" : "#f8fafc",
              color: activeCategory === cat.id ? "#fff" : "#555",
              fontWeight: activeCategory === cat.id ? 700 : 500,
              fontSize: "0.84rem", cursor: "pointer", transition: "all 0.15s",
              display: "flex", alignItems: "center", gap: 5,
            }}>
              <span>{cat.icon}</span>
              <span>{cat.id}</span>
              {cat.id === "2022 Peak" && (
                <span style={{
                  background: activeCategory === cat.id ? "rgba(255,255,255,0.25)" : "#ffebee",
                  color: activeCategory === cat.id ? "#fff" : "#c62828",
                  borderRadius: 10, padding: "1px 6px", fontSize: "0.72rem", fontWeight: 700
                }}>HOT</span>
              )}
            </button>
          ))}
          <span style={{ fontSize: "0.78rem", color: "#bbb", alignSelf: "center", marginLeft: 4 }}>
            {QUESTION_CATEGORIES.find(c => c.id === activeCategory)?.desc}
          </span>
        </div>

        {/* Question chips */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {QUICK_QUESTIONS[activeCategory].map(({ label, q }) => (
            <button key={label} onClick={() => handleQuick(q, label)} style={{
              padding: "6px 14px", fontSize: "0.83rem", borderRadius: 20,
              border: "1.5px solid",
              borderColor: activeQ === label ? "#1565c0" : "#dde3ea",
              background: activeQ === label ? "#e3f2fd" : "#fff",
              color: activeQ === label ? "#1565c0" : "#444",
              fontWeight: activeQ === label ? 700 : 400,
              cursor: "pointer", transition: "all 0.15s", boxShadow: activeQ === label ? "none" : "0 1px 3px rgba(0,0,0,0.06)"
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* ── Query box ── */}
      <div style={{
        background: "#fff", borderRadius: 14, border: "1.5px solid #dde3ea",
        padding: 20, marginBottom: 20, boxShadow: "0 2px 12px rgba(0,0,0,0.06)"
      }}>
        {/* Mode toggle */}
        <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
          {(["nl", "sql"] as const).map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: "6px 16px", borderRadius: 20, border: "1.5px solid",
              borderColor: mode === m ? "#1565c0" : "#dde3ea",
              background: mode === m ? "#1565c0" : "#f8fafc",
              color: mode === m ? "#fff" : "#555",
              fontWeight: mode === m ? 700 : 400, fontSize: "0.85rem", cursor: "pointer"
            }}>
              {m === "nl" ? "💬 Plain English" : "🛢️ SQL Editor"}
            </button>
          ))}
          {mode === "sql" && (
            <span style={{ fontSize: "0.78rem", color: "#aaa", alignSelf: "center", marginLeft: 4 }}>
              Ctrl+Enter to run · Tables: concessions · prices · alerts · trends
            </span>
          )}
        </div>

        {mode === "nl" ? (
          <div style={{ position: "relative" }}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
              placeholder="e.g. which drugs had the most concession months in 2022?   (Press Enter to run)"
              rows={2}
              style={{
                width: "100%", padding: "12px 130px 12px 16px", fontSize: "0.97rem",
                border: "1.5px solid #c8d0da", borderRadius: 10, outline: "none",
                fontFamily: "inherit", resize: "none", boxSizing: "border-box",
                lineHeight: 1.5, color: "#1a1a1a", transition: "border-color 0.15s"
              }}
              onFocus={e => (e.target.style.borderColor = "#1565c0")}
              onBlur={e => (e.target.style.borderColor = "#c8d0da")}
            />
            <button onClick={handleAsk} disabled={loading || !question.trim()} style={{
              position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
              background: loading ? "#90a4ae" : "#1565c0", color: "#fff", border: "none",
              borderRadius: 8, padding: "8px 18px", cursor: loading ? "wait" : "pointer",
              fontWeight: 700, fontSize: "0.9rem", whiteSpace: "nowrap", transition: "background 0.15s"
            }}>
              {loading ? "⏳ Running…" : "Ask →"}
            </button>
          </div>
        ) : (
          <div>
            <textarea
              value={sql}
              onChange={e => setSql(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleAsk(); }}
              placeholder={"SELECT drug, COUNT(*) AS events\nFROM concessions\nWHERE month LIKE '2022%'\nGROUP BY drug\nORDER BY events DESC\nLIMIT 20"}
              rows={6}
              style={{
                width: "100%", padding: "12px 16px", fontSize: "0.88rem",
                border: "1.5px solid #c8d0da", borderRadius: 10, outline: "none",
                fontFamily: "'Menlo', 'Monaco', 'Courier New', monospace",
                resize: "vertical", boxSizing: "border-box", lineHeight: 1.6,
                background: "#f8fafc", color: "#1a1a1a"
              }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={handleAsk} disabled={loading || !sql.trim()} style={{
                background: loading ? "#90a4ae" : "#1565c0", color: "#fff", border: "none",
                borderRadius: 8, padding: "8px 20px", cursor: loading ? "wait" : "pointer",
                fontWeight: 700, fontSize: "0.9rem"
              }}>
                {loading ? "⏳ Running…" : "▶ Run SQL"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div style={{ textAlign: "center", padding: "48px 20px", color: "#888" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12, display: "inline-block", animation: "pulse 1.2s ease-in-out infinite" }}>🔍</div>
          <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: 4 }}>Querying 7,742 concession records…</div>
          <div style={{ fontSize: "0.82rem", color: "#bbb" }}>AI is translating your question to SQL</div>
          <style>{`@keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.6; transform:scale(1.1); } }`}</style>
        </div>
      )}

      {/* ── Error ── */}
      {result && !result.success && !loading && (
        <div style={{ background: "#fff3e0", border: "1px solid #ffcc80", borderRadius: 10, padding: "14px 18px", color: "#e65100" }}>
          <strong>⚠️ {result.error}</strong>
          {result.sql && (
            <pre style={{ marginTop: 8, fontSize: "0.82rem", color: "#555", background: "#fff8f0", padding: "8px 12px", borderRadius: 6, overflowX: "auto" }}>
              {result.sql}
            </pre>
          )}
          <div style={{ marginTop: 8, fontSize: "0.82rem", color: "#888" }}>
            Tip: Try rephrasing, or switch to SQL mode and write the query directly.
          </div>
        </div>
      )}

      {/* ── Result panel ── */}
      {result?.success && !loading && (
        <div style={{
          background: "#fff", borderRadius: 14, border: "1.5px solid #dde3ea",
          overflow: "hidden", boxShadow: "0 2px 12px rgba(0,0,0,0.06)"
        }}>

          {/* Result header */}
          <div style={{
            padding: "14px 20px", background: "#f8fafc", borderBottom: "1px solid #eef0f4",
            display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8
          }}>
            <div>
              <span style={{ fontWeight: 700, color: "#1a1a1a", fontSize: "0.97rem" }}>
                ✅ {result.row_count?.toLocaleString()} row{result.row_count !== 1 ? "s" : ""} returned
              </span>
              {result.explanation && (
                <span style={{ color: "#888", fontSize: "0.84rem", marginLeft: 10 }}>{result.explanation}</span>
              )}
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {result.chart_hint && result.chart_hint !== "table" && (
                <span style={{ background: "#e3f2fd", color: "#1565c0", borderRadius: 12, padding: "3px 10px", fontSize: "0.78rem", fontWeight: 600 }}>
                  {result.chart_hint === "bar" ? "📊 Bar chart" : "📈 Line chart"}
                </span>
              )}
              <button onClick={exportCSV} style={{
                background: "#fff", border: "1px solid #c8d0da", borderRadius: 8,
                padding: "5px 12px", fontSize: "0.82rem", cursor: "pointer", color: "#555",
                display: "flex", alignItems: "center", gap: 5, fontWeight: 500
              }}>⬇ Export CSV</button>
            </div>
          </div>

          {/* Chart */}
          {chart && (
            <div style={{ padding: "20px 20px 8px" }}>
              {chart}
            </div>
          )}

          {/* Generated SQL (collapsible) */}
          {result.sql && (
            <details style={{ borderTop: chart ? "1px solid #eef0f4" : "none", borderBottom: "1px solid #eef0f4" }}>
              <summary style={{
                padding: "8px 20px", cursor: "pointer", fontSize: "0.82rem",
                color: "#888", userSelect: "none", listStyle: "none"
              }}>
                🛢️ View SQL used — click to inspect or edit
              </summary>
              <div style={{ padding: "0 20px 12px" }}>
                <textarea
                  value={sql}
                  onChange={e => setSql(e.target.value)}
                  rows={4}
                  style={{
                    width: "100%", padding: "10px 12px", fontSize: "0.82rem",
                    fontFamily: "monospace", border: "1px solid #dde3ea", borderRadius: 8,
                    background: "#f8fafc", boxSizing: "border-box", resize: "vertical"
                  }}
                />
                <button
                  onClick={() => { setMode("sql"); runQuery({ sql }); }}
                  style={{
                    marginTop: 6, padding: "6px 16px", background: "#1565c0", color: "#fff",
                    border: "none", borderRadius: 7, cursor: "pointer", fontSize: "0.85rem", fontWeight: 600
                  }}>
                  ▶ Re-run edited SQL
                </button>
              </div>
            </details>
          )}

          {/* Table */}
          {result.columns && result.rows && (
            <ResultTable columns={result.columns} rows={result.rows.slice(0, 200)} />
          )}

          {result.row_count && result.row_count > 200 && (
            <div style={{ padding: "10px 20px", color: "#aaa", fontSize: "0.82rem", borderTop: "1px solid #f0f0f0", textAlign: "center" }}>
              Showing first 200 of {result.row_count.toLocaleString()} rows · use Export CSV for full results
            </div>
          )}
        </div>
      )}

      {/* ── Empty state ── */}
      {!result && !loading && (
        <div style={{
          textAlign: "center", padding: "52px 20px", color: "#aaa",
          background: "#f8fafc", borderRadius: 14, border: "1.5px dashed #dde3ea"
        }}>
          <div style={{ fontSize: "3rem", marginBottom: 14 }}>🔍</div>
          <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#555", marginBottom: 8 }}>
            Explore the full concession history
          </div>
          <div style={{ fontSize: "0.88rem", marginBottom: 20, lineHeight: 1.6 }}>
            7,742 concession events · 15,122 tariff price records · 3,372 MHRA alerts<br />
            <strong style={{ color: "#e65100" }}>🔥 2022 had 198 drugs conceded in a single month (Dec)</strong>
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            {[
              { label: "🔥 Show 2022 peak", q: "all drugs on concession in December 2022 ordered by price descending" },
              { label: "📈 Year totals", q: "how many drugs went on concession each year?" },
              { label: "💰 Most expensive ever", q: "top 20 highest concession prices ever recorded" },
            ].map(({ label, q }) => (
              <button key={label} onClick={() => handleQuick(q, label)} style={{
                padding: "8px 18px", borderRadius: 20, border: "1.5px solid #c8d0da",
                background: "#fff", color: "#444", fontSize: "0.85rem", cursor: "pointer",
                fontWeight: 500, boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
              }}>{label}</button>
            ))}
          </div>
        </div>
      )}

      {/* ── Schema reference ── */}
      <details style={{ marginTop: 24, background: "#fff", borderRadius: 12, border: "1px solid #eef0f4" }}>
        <summary style={{ padding: "12px 18px", cursor: "pointer", fontWeight: 600, fontSize: "0.88rem", color: "#555", listStyle: "none" }}>
          📖 Available tables &amp; columns (SQL mode reference)
        </summary>
        <div style={{ padding: "8px 18px 16px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
          {[
            { name: "concessions", rows: "7,742", cols: ["month VARCHAR (YYYY-MM)", "drug VARCHAR", "concession_price DOUBLE"] },
            { name: "prices",      rows: "15,122", cols: ["drug VARCHAR", "month VARCHAR (YYYY-MM)", "price_gbp DOUBLE"] },
            { name: "alerts",      rows: "3,372",  cols: ["title VARCHAR", "date VARCHAR", "description VARCHAR", "source VARCHAR"] },
            { name: "trends",      rows: "74",     cols: ["month VARCHAR (YYYY-MM)", "count INTEGER"] },
          ].map(t => (
            <div key={t.name} style={{ background: "#f8fafc", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ fontFamily: "monospace", fontWeight: 700, color: "#1565c0", marginBottom: 4 }}>
                {t.name}
                <span style={{ fontWeight: 400, color: "#aaa", marginLeft: 6, fontSize: "0.78rem" }}>({t.rows} rows)</span>
              </div>
              {t.cols.map(c => (
                <div key={c} style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "#666", padding: "1px 0" }}>· {c}</div>
              ))}
            </div>
          ))}
        </div>
        <div style={{ padding: "0 18px 14px", fontSize: "0.8rem", color: "#aaa" }}>
          All month values are 'YYYY-MM' strings. Use <code>LIKE '2022%'</code> for year filtering.
          Use <code>LOWER(drug) LIKE '%keyword%'</code> for drug name search.
        </div>
      </details>

      {/* ── Data scope notice ── */}
      <div style={{
        marginTop: 16, padding: "12px 18px", background: "#fff8e1",
        border: "1px solid #ffe082", borderRadius: 10, fontSize: "0.82rem", color: "#795548"
      }}>
        <strong>📌 Historical data only:</strong> This lens covers Jan 2020 – Feb 2026 (archived CPE concessions, NHS drug tariff, MHRA publications).
        Live concession data integration is on the roadmap. For current month predictions, use the <strong>Risk Finder</strong>.
      </div>
    </div>
  );
}
