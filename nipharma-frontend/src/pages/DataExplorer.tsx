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

const QUICK_QUESTIONS = [
  { label: "🏆 Top conceded drugs", q: "which drugs had the most concession events ever?" },
  { label: "📅 2022 concession surge", q: "how many drugs went on concession each month in 2022?" },
  { label: "💰 Most expensive concessions", q: "top 20 highest concession prices ever" },
  { label: "❄️ Winter patterns", q: "compare total concessions in winter months vs summer months" },
  { label: "📈 Year-on-year trend", q: "how many drugs went on concession each year?" },
  { label: "🔍 MHRA amoxicillin", q: "MHRA alerts mentioning amoxicillin" },
  { label: "💊 Metformin history", q: "show metformin 500mg price history by month" },
  { label: "⚠️ Price spikes", q: "drugs where concession price is more than 3 times the tariff price" },
];

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
              rx={4} fill={isHov ? "#1565c0" : "#42a5f5"} opacity={isHov ? 1 : 0.82} />
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

  const W = 860, H = 200, PL = 60, PR = 20, PT = 20, PB = 36;
  const iW = W - PL - PR, iH = H - PT - PB;

  const xOf = (i: number) => PL + (i / (rows.length - 1)) * iW;
  const yOf = (v: number) => PT + iH - ((v - minV) / range) * iH;
  const pts = rows.map((r, i) => `${xOf(i)},${yOf(vals[i])}`).join(" ");

  // Sample x-axis ticks (every ~6 points)
  const tickEvery = Math.max(1, Math.floor(rows.length / 10));
  const ticks = rows.filter((_, i) => i % tickEvery === 0 || i === rows.length - 1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", overflow: "visible" }}>
      <defs>
        <linearGradient id="lg2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1565c0" stopOpacity={0.15} />
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
      <polyline points={pts} fill="none" stroke="#1565c0" strokeWidth={2} strokeLinejoin="round" />
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
          <rect x={xOf(hovered) - 52} y={yOf(vals[hovered]) - 44} width={104} height={36}
            rx={5} fill="#1a1a1a" opacity={0.88} />
          <text x={xOf(hovered)} y={yOf(vals[hovered]) - 28} textAnchor="middle" fontSize={10} fill="#ccc">
            {String(rows[hovered][xCol]).slice(0, 14)}
          </text>
          <text x={xOf(hovered)} y={yOf(vals[hovered]) - 14} textAnchor="middle" fontSize={11} fill="#64b5f6" fontWeight="600">
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
  const fmt = (v: any) => {
    if (v === null || v === undefined) return <span style={{ color: "#bbb" }}>—</span>;
    if (typeof v === "number" && v % 1 !== 0) return `£${v.toFixed(2)}`;
    return String(v);
  };
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
        <thead>
          <tr style={{ background: "#f0f5ff" }}>
            {columns.map(c => (
              <th key={c} style={{
                padding: "9px 14px", textAlign: "left", fontWeight: 700,
                color: "#1565c0", borderBottom: "2px solid #c8d8f5",
                whiteSpace: "nowrap", fontSize: "0.83rem", textTransform: "uppercase", letterSpacing: "0.04em"
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#f8fafc" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#eef4ff")}
              onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f8fafc")}>
              {columns.map(c => (
                <td key={c} style={{ padding: "8px 14px", borderBottom: "1px solid #f0f0f0", color: "#333" }}>
                  {fmt(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Main page ────────────────────────────────────────────────────── */
export default function DataExplorer() {
  const [question, setQuestion] = useState("");
  const [sql, setSql]           = useState("");
  const [result, setResult]     = useState<QueryResult | null>(null);
  const [loading, setLoading]   = useState(false);
  const [mode, setMode]         = useState<"nl" | "sql">("nl");
  const [activeQ, setActiveQ]   = useState("");
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
      setResult({ success: false, error: "Failed to connect to backend" });
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

  const exportCSV = () => {
    if (!result?.rows?.length || !result.columns) return;
    const header = result.columns.join(",");
    const body = result.rows.map(r => result.columns!.map(c => JSON.stringify(r[c] ?? "")).join(",")).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "nipharma_query.csv"; a.click();
  };

  const renderChart = () => {
    if (!result?.success || !result.rows?.length || !result.columns) return null;
    if (result.rows.length < 2) return null;
    if (result.chart_hint === "line") return <LineChart columns={result.columns} rows={result.rows} />;
    if (result.chart_hint === "bar" && result.rows.length <= 40) return <BarChart columns={result.columns} rows={result.rows} />;
    return null;
  };

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: "24px 20px", fontFamily: "inherit" }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.9rem", fontWeight: 800, color: "#1a1a1a", marginBottom: 6 }}>
          🔬 Data Explorer
        </h1>
        <p style={{ color: "#666", fontSize: "0.97rem", margin: 0 }}>
          Ask questions in plain English or write SQL — query 7,742 concession events, 15k price records and 3,372 MHRA alerts.
        </p>
      </div>

      {/* Query box */}
      <div style={{ background: "#fff", borderRadius: 14, border: "1.5px solid #dde3ea", padding: 20, marginBottom: 20, boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>

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
              {m === "nl" ? "💬 Ask in plain English" : "🛢️ Write SQL"}
            </button>
          ))}
        </div>

        {mode === "nl" ? (
          <div style={{ position: "relative" }}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
              placeholder="e.g. which drugs had the most concession events in 2023?"
              rows={2}
              style={{
                width: "100%", padding: "12px 110px 12px 16px", fontSize: "0.97rem",
                border: "1.5px solid #c8d0da", borderRadius: 10, outline: "none",
                fontFamily: "inherit", resize: "none", boxSizing: "border-box",
                lineHeight: 1.5, color: "#1a1a1a"
              }}
            />
            <button onClick={handleAsk} disabled={loading || !question.trim()} style={{
              position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
              background: loading ? "#90a4ae" : "#1565c0", color: "#fff", border: "none",
              borderRadius: 8, padding: "8px 18px", cursor: loading ? "wait" : "pointer",
              fontWeight: 700, fontSize: "0.9rem", whiteSpace: "nowrap"
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
              placeholder={"SELECT drug, COUNT(*) as events\nFROM concessions\nGROUP BY drug\nORDER BY events DESC\nLIMIT 10"}
              rows={5}
              style={{
                width: "100%", padding: "12px 16px", fontSize: "0.88rem",
                border: "1.5px solid #c8d0da", borderRadius: 10, outline: "none",
                fontFamily: "'Menlo', 'Monaco', 'Courier New', monospace",
                resize: "vertical", boxSizing: "border-box", lineHeight: 1.6,
                background: "#f8fafc", color: "#1a1a1a"
              }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
              <span style={{ fontSize: "0.8rem", color: "#aaa" }}>
                Tables: <code>concessions</code> · <code>prices</code> · <code>alerts</code> · <code>trends</code> · Ctrl+Enter to run
              </span>
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

      {/* Quick questions */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: "0.78rem", color: "#aaa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Quick questions</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {QUICK_QUESTIONS.map(({ label, q }) => (
            <button key={label} onClick={() => handleQuick(q, label)} style={{
              padding: "6px 14px", fontSize: "0.83rem", borderRadius: 20,
              border: "1.5px solid", cursor: "pointer",
              borderColor: activeQ === label ? "#1565c0" : "#dde3ea",
              background: activeQ === label ? "#e3f2fd" : "#f8fafc",
              color: activeQ === label ? "#1565c0" : "#444",
              fontWeight: activeQ === label ? 700 : 400, transition: "all 0.15s"
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: "48px 20px", color: "#888" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12, animation: "spin 1s linear infinite", display: "inline-block" }}>⚙️</div>
          <div style={{ fontSize: "0.95rem" }}>Translating to SQL and querying data…</div>
        </div>
      )}

      {/* Error */}
      {result && !result.success && !loading && (
        <div style={{ background: "#fff3e0", border: "1px solid #ffcc80", borderRadius: 10, padding: "14px 18px", color: "#e65100" }}>
          <strong>⚠️ {result.error}</strong>
          {result.sql && (
            <pre style={{ marginTop: 8, fontSize: "0.82rem", color: "#555", background: "#fff8f0", padding: "8px 12px", borderRadius: 6, overflowX: "auto" }}>
              {result.sql}
            </pre>
          )}
        </div>
      )}

      {/* Result */}
      {result?.success && !loading && (
        <div style={{ background: "#fff", borderRadius: 14, border: "1.5px solid #dde3ea", overflow: "hidden", boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>

          {/* Result header */}
          <div style={{ padding: "14px 20px", background: "#f8fafc", borderBottom: "1px solid #eef0f4", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div>
              <span style={{ fontWeight: 700, color: "#1a1a1a", fontSize: "0.97rem" }}>
                {result.row_count?.toLocaleString()} rows
              </span>
              {result.explanation && (
                <span style={{ color: "#888", fontSize: "0.85rem", marginLeft: 10 }}>{result.explanation}</span>
              )}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {result.chart_hint && result.chart_hint !== "table" && (
                <span style={{ background: "#e3f2fd", color: "#1565c0", borderRadius: 12, padding: "3px 10px", fontSize: "0.78rem", fontWeight: 600 }}>
                  {result.chart_hint === "bar" ? "📊 Bar chart" : "📈 Line chart"}
                </span>
              )}
              <button onClick={exportCSV} style={{
                background: "#fff", border: "1px solid #c8d0da", borderRadius: 8,
                padding: "4px 12px", fontSize: "0.82rem", cursor: "pointer", color: "#555"
              }}>⬇ CSV</button>
            </div>
          </div>

          {/* Generated SQL (collapsible) */}
          {result.sql && (
            <details style={{ borderBottom: "1px solid #eef0f4" }}>
              <summary style={{ padding: "8px 20px", cursor: "pointer", fontSize: "0.82rem", color: "#888", userSelect: "none" }}>
                🛢️ SQL used — click to view &amp; edit
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

          {/* Chart */}
          {renderChart() && (
            <div style={{ padding: "20px 20px 8px" }}>
              {renderChart()}
            </div>
          )}

          {/* Table */}
          {result.columns && result.rows && (
            <div style={{ padding: result.chart_hint !== "table" && result.rows.length <= 40 ? "0 0 4px" : "0" }}>
              <ResultTable columns={result.columns} rows={result.rows.slice(0, 200)} />
            </div>
          )}

          {result.row_count && result.row_count > 200 && (
            <div style={{ padding: "10px 20px", color: "#aaa", fontSize: "0.82rem", borderTop: "1px solid #f0f0f0", textAlign: "center" }}>
              Showing first 200 of {result.row_count.toLocaleString()} rows · export CSV for full results
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div style={{ textAlign: "center", padding: "48px 20px", color: "#aaa", background: "#f8fafc", borderRadius: 14, border: "1.5px dashed #dde3ea" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🔬</div>
          <div style={{ fontSize: "1rem", fontWeight: 600, color: "#666", marginBottom: 6 }}>Ask anything about the drug data</div>
          <div style={{ fontSize: "0.88rem" }}>
            7,742 concession events · 15,122 tariff price records · 3,372 MHRA alerts · Jan 2020 – Feb 2026
          </div>
        </div>
      )}

      {/* Schema reference */}
      <details style={{ marginTop: 24, background: "#fff", borderRadius: 12, border: "1px solid #eef0f4" }}>
        <summary style={{ padding: "12px 18px", cursor: "pointer", fontWeight: 600, fontSize: "0.88rem", color: "#555" }}>
          📖 Available tables &amp; columns (for SQL mode)
        </summary>
        <div style={{ padding: "0 18px 16px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
          {[
            { name: "concessions", rows: "7,742", cols: ["month VARCHAR (YYYY-MM)", "drug VARCHAR", "concession_price DOUBLE"] },
            { name: "prices", rows: "15,122", cols: ["drug VARCHAR", "month VARCHAR (YYYY-MM)", "price_gbp DOUBLE"] },
            { name: "alerts", rows: "3,372", cols: ["title VARCHAR", "date VARCHAR", "description VARCHAR", "source VARCHAR"] },
            { name: "trends", rows: "74", cols: ["month VARCHAR (YYYY-MM)", "count INTEGER"] },
          ].map(t => (
            <div key={t.name} style={{ background: "#f8fafc", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ fontFamily: "monospace", fontWeight: 700, color: "#1565c0", marginBottom: 4 }}>
                {t.name}
                <span style={{ fontWeight: 400, color: "#aaa", marginLeft: 6, fontSize: "0.8rem" }}>({t.rows} rows)</span>
              </div>
              {t.cols.map(c => (
                <div key={c} style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "#666", padding: "1px 0" }}>· {c}</div>
              ))}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
