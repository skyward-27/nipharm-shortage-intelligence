import { useState, useRef, useCallback, useEffect } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ─── Sample data shown when backend is offline ─────────────────────────────────
const SAMPLE_RESULT = {
  success: true,
  sql: "SELECT drug, COUNT(*) AS events FROM concessions WHERE month LIKE '2022%' GROUP BY drug ORDER BY events DESC LIMIT 10",
  columns: ["drug", "events"],
  rows: [
    { drug: "Mometasone 0.1% cream", events: 23 },
    { drug: "Mometasone 0.1% ointment", events: 21 },
    { drug: "Paracetamol 500mg soluble tablets", events: 16 },
    { drug: "Metformin 500mg tablets", events: 14 },
    { drug: "Amoxicillin 500mg capsules", events: 13 },
    { drug: "Omeprazole 20mg gastro-resistant capsules", events: 12 },
    { drug: "Furosemide 40mg tablets", events: 11 },
    { drug: "Amlodipine 5mg tablets", events: 10 },
    { drug: "Lansoprazole 30mg capsules", events: 9 },
    { drug: "Salbutamol 100mcg inhaler", events: 8 },
  ],
  row_count: 10,
  chart_hint: "bar" as const,
  explanation: "⚠️ Backend rebuilding — showing sample 2022 data. Live queries will work once Railway finishes deployment (~2 min).",
};

// ─── Colour palette ───────────────────────────────────────────────────────────
const COLORS = {
  navy:    "#0f172a",
  navyMid: "#1e293b",
  navyLight:"#334155",
  blue:    "#3b82f6",
  blueDark:"#1d4ed8",
  blueLight:"#dbeafe",
  amber:   "#f59e0b",
  amberDark:"#d97706",
  amberLight:"#fef3c7",
  emerald: "#10b981",
  emeraldLight:"#d1fae5",
  rose:    "#f43f5e",
  roseLight:"#ffe4e6",
  violet:  "#7c3aed",
  violetLight:"#ede9fe",
  slate:   "#64748b",
  slateLight:"#f1f5f9",
  white:   "#ffffff",
};

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

type SortDir = "asc" | "desc" | null;

const CATEGORIES = [
  { id: "2022 Peak", icon: "🔥", color: COLORS.amber,  light: COLORS.amberLight,  label: "2022 Crisis" },
  { id: "Trends",    icon: "📈", color: COLORS.blue,   light: COLORS.blueLight,   label: "Trends" },
  { id: "Prices",    icon: "💊", color: COLORS.emerald,light: COLORS.emeraldLight, label: "Prices" },
  { id: "Alerts",    icon: "🚨", color: COLORS.rose,   light: COLORS.roseLight,   label: "MHRA Alerts" },
] as const;
type CategoryId = typeof CATEGORIES[number]["id"];

const QUICK_QUESTIONS: Record<CategoryId, { label: string; q: string }[]> = {
  "2022 Peak": [
    { label: "🔥 Dec 2022 peak — all drugs",         q: "all drugs on concession in December 2022 ordered by concession price descending" },
    { label: "📊 2022 monthly concession count",      q: "how many drugs went on concession each month in 2022?" },
    { label: "🆕 First-timers in 2022",               q: "drugs that first appeared on concession in 2022 ordered by concession price" },
    { label: "💸 Top 20 priciest — 2022",             q: "top 20 most expensive concession prices in 2022" },
    { label: "📉 2021 vs 2022 totals",                q: "total concession count per year for 2021 and 2022" },
    { label: "🏆 Most conceded in 2022",              q: "drugs with most concession months in 2022" },
  ],
  "Trends": [
    { label: "📅 Year-on-year totals",                q: "how many drugs went on concession each year?" },
    { label: "❄️ Winter vs summer",                   q: "total concessions in months 11,12,1,2 versus months 5,6,7,8" },
    { label: "🚀 Most concession events ever",        q: "which drugs had the most concession events ever?" },
    { label: "📆 2025–2026 recent trend",             q: "total drugs on concession per month for 2025 and 2026" },
    { label: "🔁 Longest continuous streaks",         q: "which drugs had the most total concession months?" },
  ],
  "Prices": [
    { label: "💰 Highest concession prices ever",     q: "top 20 highest concession prices ever recorded" },
    { label: "📊 Metformin 500mg price history",      q: "metformin 500mg tablets price history by month" },
    { label: "🩺 Omeprazole 20mg price history",      q: "omeprazole 20mg gastro-resistant capsules price history" },
    { label: "📈 NHS tariff over £50",                q: "drugs where price_gbp exceeded 50 in any month" },
    { label: "💊 Insulin concessions history",        q: "all insulin drugs that ever appeared on concession" },
    { label: "🔍 Concession price over £100",         q: "drugs where concession price exceeded 100" },
  ],
  "Alerts": [
    { label: "🚨 Latest MHRA publications",           q: "most recent 20 MHRA shortage publications ordered by date" },
    { label: "🔎 Amoxicillin shortage alerts",        q: "MHRA alerts about amoxicillin shortage" },
    { label: "💉 Insulin supply alerts",              q: "MHRA alerts mentioning insulin shortage" },
    { label: "📋 2023 shortage alerts",               q: "MHRA shortage publications from 2023 ordered by date" },
    { label: "🏭 Manufacturing / supply alerts",      q: "MHRA alerts mentioning manufacturing or supply" },
  ],
};

const YEARS = ["2020","2021","2022","2023","2024","2025","2026"];

const INSIGHTS = [
  "🔥 Dec 2022 was the worst month in 6 years — 198 drugs conceded at once",
  "💊 Mometasone 0.1% cream was conceded 23 months in 2022 alone",
  "📈 Total concessions rose 340% from Jan 2020 to Dec 2022",
  "⚠️ 3,372 MHRA shortage publications tracked since 2020",
  "💰 Some drugs hit concession prices 10× their NHS tariff price",
  "🇮🇳 GBP/INR weakness in 2022 drove a wave of generic price rises",
];

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function Skeleton({ w = "100%", h = 18, r = 6 }: { w?: string | number; h?: number; r?: number }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: r,
      background: "linear-gradient(90deg,#e2e8f0 25%,#f1f5f9 50%,#e2e8f0 75%)",
      backgroundSize: "400% 100%",
      animation: "shimmer 1.4s ease-in-out infinite",
    }} />
  );
}

// ─── Bar chart ────────────────────────────────────────────────────────────────
function BarChart({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [hov, setHov] = useState<number | null>(null);
  if (!rows.length || columns.length < 2) return null;
  const lCol = columns[0], vCol = columns[1];
  const vals = rows.map(r => parseFloat(r[vCol]) || 0);
  const maxV = Math.max(...vals, 1);
  const W = 860, BAR_H = 30, GAP = 7, PL = 230, PR = 90;
  const totalH = rows.length * (BAR_H + GAP) + 50;
  const iW = W - PL - PR;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${totalH}`} style={{ width: "100%", display: "block", minWidth: 400 }}>
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={COLORS.blue} />
            <stop offset="100%" stopColor="#60a5fa" />
          </linearGradient>
          <linearGradient id="barGradHov" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={COLORS.blueDark} />
            <stop offset="100%" stopColor={COLORS.blue} />
          </linearGradient>
          <linearGradient id="peakGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={COLORS.amber} />
            <stop offset="100%" stopColor="#fbbf24" />
          </linearGradient>
        </defs>
        {/* Background grid */}
        {[0, 0.25, 0.5, 0.75, 1].map((f, k) => (
          <g key={k}>
            <line x1={PL + f * iW} x2={PL + f * iW} y1={20} y2={totalH - 20}
              stroke="#e2e8f0" strokeWidth={1} strokeDasharray={k === 0 ? "" : "3 3"} />
            <text x={PL + f * iW} y={16} textAnchor="middle" fontSize={9} fill="#94a3b8">
              {f > 0 ? (maxV * f % 1 !== 0 ? `£${(maxV * f).toFixed(0)}` : Math.round(maxV * f)) : "0"}
            </text>
          </g>
        ))}
        {rows.map((row, i) => {
          const val = vals[i];
          const bW = Math.max((val / maxV) * iW, 2);
          const y = i * (BAR_H + GAP) + 30;
          const isHov = hov === i;
          const label = String(row[lCol] ?? "").slice(0, 34);
          const isPeak = String(row[lCol] ?? "").includes("2022-12");
          const fillId = isPeak ? "peakGrad" : (isHov ? "barGradHov" : "barGrad");
          return (
            <g key={i} onMouseEnter={() => setHov(i)} onMouseLeave={() => setHov(null)} style={{ cursor: "pointer" }}>
              {isHov && <rect x={PL - 4} y={y - 2} width={iW + 8} height={BAR_H + 4} rx={6} fill="#f0f9ff" opacity={0.7} />}
              <text x={PL - 10} y={y + BAR_H / 2 + 4} textAnchor="end" fontSize={11}
                fill={isHov ? COLORS.blue : COLORS.navyLight} fontWeight={isHov ? 700 : 400}>
                {label}
              </text>
              <rect x={PL} y={y} width={bW} height={BAR_H} rx={5} fill={`url(#${fillId})`} opacity={isHov ? 1 : 0.88} />
              {isPeak && <text x={PL + bW + 8} y={y + BAR_H / 2 + 4} fontSize={9} fill={COLORS.amber} fontWeight={700}>PEAK</text>}
              <text x={PL + bW + (isPeak ? 44 : 8)} y={y + BAR_H / 2 + 4} fontSize={11} fill={COLORS.slate} fontWeight={600}>
                {val % 1 !== 0 ? `£${val.toFixed(2)}` : val.toLocaleString()}
              </text>
              {isHov && (
                <rect x={PL + bW - 60} y={y - 28} width={68} height={22} rx={5} fill={COLORS.navy} opacity={0.92} />
              )}
              {isHov && (
                <text x={PL + bW - 26} y={y - 12} textAnchor="middle" fontSize={11} fill="#fff" fontWeight={700}>
                  {val % 1 !== 0 ? `£${val.toFixed(2)}` : val.toLocaleString()}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Line chart ───────────────────────────────────────────────────────────────
function LineChart({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [hov, setHov] = useState<number | null>(null);
  if (rows.length < 2 || columns.length < 2) return null;
  const xCol = columns[0], yCol = columns[1];
  const vals = rows.map(r => parseFloat(r[yCol]) || 0);
  const minV = Math.min(...vals), maxV = Math.max(...vals, minV + 1);
  const range = maxV - minV;
  const W = 860, H = 240, PL = 60, PR = 30, PT = 40, PB = 44;
  const iW = W - PL - PR, iH = H - PT - PB;
  const xOf = (i: number) => PL + (i / (rows.length - 1)) * iW;
  const yOf = (v: number) => PT + iH - ((v - minV) / range) * iH;
  const pts = rows.map((_, i) => `${xOf(i)},${yOf(vals[i])}`).join(" ");
  const peakIdx = vals.indexOf(maxV);
  const tickEvery = Math.max(1, Math.floor(rows.length / 12));

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", overflow: "visible", minWidth: 400 }}>
        <defs>
          <linearGradient id="lineArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={COLORS.blue} stopOpacity={0.2} />
            <stop offset="100%" stopColor={COLORS.blue} stopOpacity={0} />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((f, k) => {
          const v = minV + range * (1 - f);
          return (
            <g key={k}>
              <line x1={PL} x2={W - PR} y1={PT + f * iH} y2={PT + f * iH}
                stroke={k === 4 ? "#94a3b8" : "#e2e8f0"} strokeWidth={k === 4 ? 1.5 : 1} />
              <text x={PL - 8} y={PT + f * iH + 4} textAnchor="end" fontSize={10} fill="#94a3b8">
                {v % 1 !== 0 ? `£${v.toFixed(0)}` : Math.round(v)}
              </text>
            </g>
          );
        })}
        {/* Area fill */}
        <polygon
          points={`${PL},${PT + iH} ${pts} ${xOf(rows.length - 1)},${PT + iH}`}
          fill="url(#lineArea)"
        />
        {/* Line */}
        <polyline points={pts} fill="none" stroke={COLORS.blue} strokeWidth={2.5} strokeLinejoin="round" filter="url(#glow)" />
        {/* Peak annotation */}
        {peakIdx >= 0 && (
          <g>
            <line x1={xOf(peakIdx)} x2={xOf(peakIdx)} y1={PT} y2={yOf(vals[peakIdx]) - 10}
              stroke={COLORS.amber} strokeWidth={1.5} strokeDasharray="4 3" />
            <circle cx={xOf(peakIdx)} cy={yOf(vals[peakIdx])} r={8}
              fill={COLORS.amber} stroke="#fff" strokeWidth={2.5} />
            <rect x={Math.min(xOf(peakIdx) - 38, W - PR - 80)} y={PT - 4} width={80} height={22} rx={5} fill={COLORS.amber} />
            <text x={Math.min(xOf(peakIdx) + 2, W - PR - 38)} y={PT + 12} textAnchor="middle" fontSize={10} fill="#fff" fontWeight={800}>
              PEAK · {vals[peakIdx]}
            </text>
          </g>
        )}
        {/* Interactive dots */}
        {rows.map((r, i) => (
          <circle key={i} cx={xOf(i)} cy={yOf(vals[i])} r={hov === i ? 6 : 3.5}
            fill={hov === i ? COLORS.blue : "#fff"}
            stroke={hov === i ? COLORS.blueDark : COLORS.blue}
            strokeWidth={hov === i ? 2.5 : 2}
            style={{ cursor: "pointer", transition: "r 0.1s" }}
            onMouseEnter={() => setHov(i)}
            onMouseLeave={() => setHov(null)}
          />
        ))}
        {/* Hover tooltip */}
        {hov !== null && (() => {
          const tx = Math.min(Math.max(xOf(hov), PL + 50), W - PR - 50);
          return (
            <g>
              <rect x={tx - 52} y={yOf(vals[hov]) - 54} width={104} height={44}
                rx={8} fill={COLORS.navy} opacity={0.95} />
              <text x={tx} y={yOf(vals[hov]) - 36} textAnchor="middle" fontSize={10} fill="#94a3b8">
                {String(rows[hov][xCol]).slice(0, 14)}
              </text>
              <text x={tx} y={yOf(vals[hov]) - 18} textAnchor="middle" fontSize={13} fill="#60a5fa" fontWeight={800}>
                {vals[hov] % 1 !== 0 ? `£${vals[hov].toFixed(2)}` : vals[hov].toLocaleString()}
              </text>
            </g>
          );
        })()}
        {/* X-axis labels */}
        {rows.map((r, i) => {
          if (i % tickEvery !== 0 && i !== rows.length - 1) return null;
          return (
            <text key={i} x={xOf(i)} y={H - 6} textAnchor="middle" fontSize={9} fill="#94a3b8">
              {String(r[xCol]).slice(0, 7)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Result table with sorting ────────────────────────────────────────────────
function ResultTable({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  const [sort, setSort] = useState<{ col: string; dir: SortDir }>({ col: "", dir: null });
  const [copied, setCopied] = useState(false);

  const sorted = [...rows].sort((a, b) => {
    if (!sort.dir || !sort.col) return 0;
    const va = a[sort.col], vb = b[sort.col];
    const n = (typeof va === "number" && typeof vb === "number")
      ? va - vb
      : String(va ?? "").localeCompare(String(vb ?? ""));
    return sort.dir === "asc" ? n : -n;
  });

  const toggleSort = (col: string) => {
    setSort(s => s.col === col
      ? { col, dir: s.dir === "asc" ? "desc" : s.dir === "desc" ? null : "asc" }
      : { col, dir: "asc" }
    );
  };

  const fmtVal = (v: any, col: string) => {
    if (v === null || v === undefined) return <span style={{ color: "#cbd5e1" }}>—</span>;
    const c = col.toLowerCase();
    if ((c.includes("price") || c.includes("gbp") || c === "concession_price") && typeof v === "number") {
      return <span style={{ fontFamily: "monospace", color: COLORS.emerald, fontWeight: 700 }}>£{v.toFixed(2)}</span>;
    }
    if (c.includes("month") && typeof v === "string" && /^\d{4}-\d{2}$/.test(v)) {
      const [y, m] = v.split("-");
      const mon = new Date(+y, +m - 1).toLocaleString("default", { month: "short" });
      return <span style={{ fontFamily: "monospace", color: COLORS.slate }}>{mon} {y}</span>;
    }
    if (typeof v === "number") {
      return <span style={{ fontFamily: "monospace" }}>{v.toLocaleString()}</span>;
    }
    return <span>{String(v)}</span>;
  };

  return (
    <div>
      <div style={{ padding: "0 20px 8px", display: "flex", justifyContent: "flex-end" }}>
        <button onClick={() => { navigator.clipboard?.writeText(columns.join("\t")); setCopied(true); setTimeout(() => setCopied(false), 1500); }} style={{
          fontSize: "0.75rem", color: "#94a3b8", background: "none", border: "none", cursor: "pointer"
        }}>
          {copied ? "✅ Copied!" : "📋 Copy headers"}
        </button>
      </div>
      <div style={{ overflowX: "auto", maxHeight: 480, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.87rem" }}>
          <thead>
            <tr style={{ background: COLORS.navy, position: "sticky", top: 0, zIndex: 1 }}>
              {columns.map(c => (
                <th key={c}
                  onClick={() => toggleSort(c)}
                  style={{
                    padding: "10px 16px", textAlign: "left", fontWeight: 700, cursor: "pointer",
                    color: sort.col === c ? "#60a5fa" : "#94a3b8",
                    fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.05em",
                    whiteSpace: "nowrap", userSelect: "none",
                    borderBottom: `2px solid ${sort.col === c ? COLORS.blue : "#1e293b"}`,
                    transition: "color 0.15s",
                  }}>
                  {c.replace(/_/g, " ")}
                  <span style={{ marginLeft: 4, opacity: sort.col === c ? 1 : 0.3 }}>
                    {sort.col === c && sort.dir === "asc" ? "↑" : sort.col === c && sort.dir === "desc" ? "↓" : "↕"}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={i}
                style={{ background: i % 2 === 0 ? "#fff" : "#f8fafc", transition: "background 0.1s" }}
                onMouseEnter={e => (e.currentTarget.style.background = "#eff6ff")}
                onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f8fafc")}>
                {columns.map(c => (
                  <td key={c} style={{ padding: "9px 16px", borderBottom: "1px solid #f1f5f9", color: "#1e293b" }}>
                    {fmtVal(row[c], c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Rotating insight ticker ──────────────────────────────────────────────────
function InsightTicker() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % INSIGHTS.length), 4000);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{
      background: COLORS.navy, color: "#94a3b8", padding: "8px 20px",
      fontSize: "0.82rem", display: "flex", alignItems: "center", gap: 10, overflow: "hidden"
    }}>
      <span style={{ color: COLORS.amber, fontWeight: 700, whiteSpace: "nowrap", fontSize: "0.75rem", letterSpacing: "0.06em" }}>
        💡 DID YOU KNOW
      </span>
      <span style={{ transition: "opacity 0.4s", color: "#cbd5e1" }}>{INSIGHTS[idx]}</span>
    </div>
  );
}

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ icon, value, label, color }: { icon: string; value: string; label: string; color: string }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 12, padding: "16px 20px",
      border: `1px solid #e2e8f0`, display: "flex", alignItems: "center", gap: 14,
      boxShadow: "0 1px 6px rgba(0,0,0,0.06)", flex: "1 1 160px"
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 10, background: color + "18",
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.3rem", flexShrink: 0
      }}>{icon}</div>
      <div>
        <div style={{ fontSize: "1.2rem", fontWeight: 800, color: COLORS.navy, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: "0.76rem", color: COLORS.slate, marginTop: 3 }}>{label}</div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function ConcessionLens() {
  const [question, setQuestion]         = useState("");
  const [sql, setSql]                   = useState("");
  const [result, setResult]             = useState<QueryResult | null>(null);
  const [loading, setLoading]           = useState(false);
  const [mode, setMode]                 = useState<"nl" | "sql">("nl");
  const [activeQ, setActiveQ]           = useState("");
  const [activeYear, setActiveYear]     = useState<string | null>(null);
  const [activeCategory, setActiveCat]  = useState<CategoryId>("2022 Peak");
  const [sqlCopied, setSqlCopied]       = useState(false);
  const [backendStatus, setBackendStatus] = useState<"unknown" | "online" | "offline">("unknown");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const cat = CATEGORIES.find(c => c.id === activeCategory)!;

  // ── Check backend health on mount ──
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API_URL}/ping`, { signal: AbortSignal.timeout(5000) });
        setBackendStatus(r.ok ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);

  const runQuery = useCallback(async (opts: { question?: string; sql?: string }) => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opts),
        signal: AbortSignal.timeout(20000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: QueryResult = await res.json();
      setBackendStatus("online");
      setResult(data);
      if (data.sql) setSql(data.sql);
    } catch {
      setBackendStatus("offline");
      // Show sample data so the page isn't a blank error
      setResult({ ...SAMPLE_RESULT, explanation: "⚠️ Backend rebuilding on Railway — showing sample 2022 data. Live AI queries will work once it's back online (~2 min after deploy)." });
      setSql(SAMPLE_RESULT.sql);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAsk = () => {
    if (mode === "nl" && question.trim()) runQuery({ question });
    else if (mode === "sql" && sql.trim()) runQuery({ sql });
  };

  const handleQuick = (q: string, label: string) => {
    setQuestion(q); setActiveQ(label); setActiveYear(null); setMode("nl");
    runQuery({ question: q });
    inputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const handleYear = (y: string) => {
    setActiveYear(y); setActiveQ("");
    const q = y === "2022"
      ? "how many drugs went on concession each month in 2022 ordered by month?"
      : `all drugs on concession in ${y} ordered by month and price`;
    setQuestion(q); setMode("nl");
    runQuery({ question: q });
  };

  const exportCSV = () => {
    if (!result?.rows?.length || !result.columns) return;
    const header = result.columns.join(",");
    const body = result.rows.map(r => result.columns!.map(c => JSON.stringify(r[c] ?? "")).join(",")).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `nipharma_${activeQ || "query"}_${Date.now()}.csv`; a.click();
  };

  const copySQL = () => {
    if (!result?.sql) return;
    navigator.clipboard?.writeText(result.sql);
    setSqlCopied(true); setTimeout(() => setSqlCopied(false), 1500);
  };

  const chart = (() => {
    if (!result?.success || !result.rows?.length || !result.columns || result.rows.length < 2) return null;
    if (result.chart_hint === "line") return <LineChart columns={result.columns} rows={result.rows} />;
    if (result.chart_hint === "bar" && result.rows.length <= 40) return <BarChart columns={result.columns} rows={result.rows} />;
    return null;
  })();

  return (
    <div style={{ fontFamily: "inherit", background: "#f8fafc", minHeight: "100vh" }}>

      {/* ── Hero header ── */}
      <div style={{
        background: `linear-gradient(135deg, ${COLORS.navy} 0%, #1e3a5f 60%, #0f2942 100%)`,
        padding: "32px 24px 0",
      }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 24 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                <span style={{ fontSize: "2rem" }}>🔍</span>
                <h1 style={{ fontSize: "1.9rem", fontWeight: 800, color: "#fff", margin: 0 }}>
                  Concession Lens
                </h1>
                <span style={{
                  background: COLORS.amber + "22", color: COLORS.amber, border: `1px solid ${COLORS.amber}55`,
                  borderRadius: 20, padding: "3px 12px", fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.04em"
                }}>
                  HISTORICAL · 2020–2026
                </span>
              </div>
              <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: 0, maxWidth: 520 }}>
                Ask anything in plain English. AI translates to SQL and queries 25,000+ NHS drug records instantly.
              </p>
            </div>
          </div>

          {/* Stat cards */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: -20, paddingBottom: 20 }}>
            <StatCard icon="💊" value="7,742"  label="Concession events"   color={COLORS.blue} />
            <StatCard icon="💷" value="15,122" label="NHS tariff records"  color={COLORS.emerald} />
            <StatCard icon="🚨" value="3,372"  label="MHRA publications"   color={COLORS.rose} />
            <StatCard icon="🔥" value="198"    label="Peak drugs (Dec '22)" color={COLORS.amber} />
          </div>
        </div>
      </div>

      {/* ── Backend status banner ── */}
      {backendStatus === "offline" && (
        <div style={{
          background: "#fef3c7", borderBottom: "1px solid #fde68a",
          padding: "10px 24px", display: "flex", alignItems: "center", gap: 10,
          fontSize: "0.84rem", color: "#92400e"
        }}>
          <span>⚠️</span>
          <span>
            <strong>Backend rebuilding on Railway</strong> — AI queries will return sample data until it's back online.
            Usually takes 2–3 min after a deploy. <a href={`${API_URL}/ping`} target="_blank" rel="noreferrer"
              style={{ color: "#d97706", fontWeight: 700 }}>Check status ↗</a>
          </span>
          <button onClick={async () => {
            try {
              const r = await fetch(`${API_URL}/ping`, { signal: AbortSignal.timeout(4000) });
              setBackendStatus(r.ok ? "online" : "offline");
            } catch { setBackendStatus("offline"); }
          }} style={{
            marginLeft: "auto", padding: "4px 12px", borderRadius: 8,
            border: "1px solid #d97706", background: "#fff", color: "#d97706",
            fontSize: "0.78rem", cursor: "pointer", fontWeight: 600,
          }}>↺ Retry</button>
        </div>
      )}
      {backendStatus === "online" && (
        <div style={{
          background: "#d1fae5", borderBottom: "1px solid #a7f3d0",
          padding: "6px 24px", display: "flex", alignItems: "center", gap: 8,
          fontSize: "0.8rem", color: "#065f46"
        }}>
          <span>🟢</span>
          <span><strong>Backend online</strong> — AI query engine ready. Ask anything.</span>
        </div>
      )}

      {/* ── Insight ticker ── */}
      <InsightTicker />

      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "28px 20px" }}>

        {/* ── Year jump ── */}
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontSize: "0.72rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8, fontWeight: 600 }}>
            🗓️ JUMP TO YEAR
          </div>
          <div style={{ display: "flex", gap: 7, flexWrap: "wrap", alignItems: "center" }}>
            {YEARS.map(y => {
              const is22 = y === "2022";
              const isActive = activeYear === y;
              return (
                <button key={y} onClick={() => handleYear(y)} style={{
                  padding: "6px 16px", borderRadius: 20, border: "1.5px solid",
                  borderColor: isActive ? (is22 ? COLORS.amber : COLORS.blue) : (is22 ? COLORS.amber + "55" : "#e2e8f0"),
                  background: isActive ? (is22 ? COLORS.amber : COLORS.blue) : (is22 ? COLORS.amberLight : "#fff"),
                  color: isActive ? "#fff" : (is22 ? COLORS.amberDark : COLORS.navyLight),
                  fontSize: "0.85rem", fontWeight: isActive ? 700 : (is22 ? 700 : 500),
                  cursor: "pointer", transition: "all 0.15s",
                  boxShadow: isActive ? `0 4px 12px ${is22 ? COLORS.amber : COLORS.blue}44` : "none",
                }}>
                  {is22 ? "🔥 2022" : y}
                </button>
              );
            })}
            <span style={{ fontSize: "0.75rem", color: "#94a3b8", marginLeft: 4 }}>
              ← Crisis peak year
            </span>
          </div>
        </div>

        {/* ── Category tabs + question chips ── */}
        <div style={{
          background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0",
          padding: 20, marginBottom: 20, boxShadow: "0 2px 12px rgba(0,0,0,0.05)"
        }}>
          {/* Category tabs */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            {CATEGORIES.map(c => {
              const isA = activeCategory === c.id;
              return (
                <button key={c.id} onClick={() => setActiveCat(c.id)} style={{
                  padding: "8px 18px", borderRadius: 24, border: "1.5px solid",
                  borderColor: isA ? c.color : "#e2e8f0",
                  background: isA ? c.color : "#f8fafc",
                  color: isA ? "#fff" : COLORS.slate,
                  fontWeight: isA ? 700 : 500, fontSize: "0.87rem",
                  cursor: "pointer", transition: "all 0.2s",
                  display: "flex", alignItems: "center", gap: 6,
                  boxShadow: isA ? `0 4px 14px ${c.color}44` : "none",
                  transform: isA ? "translateY(-1px)" : "none",
                }}>
                  <span>{c.icon}</span>
                  <span>{c.label}</span>
                  {c.id === "2022 Peak" && (
                    <span style={{
                      background: isA ? "rgba(255,255,255,0.28)" : COLORS.amberLight,
                      color: isA ? "#fff" : COLORS.amberDark,
                      borderRadius: 10, padding: "1px 7px", fontSize: "0.68rem", fontWeight: 800
                    }}>HOT</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Question chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {QUICK_QUESTIONS[activeCategory].map(({ label, q }) => {
              const isA = activeQ === label;
              return (
                <button key={label} onClick={() => handleQuick(q, label)} style={{
                  padding: "7px 15px", fontSize: "0.82rem", borderRadius: 20,
                  border: "1.5px solid",
                  borderColor: isA ? cat.color : "#e2e8f0",
                  background: isA ? cat.light : "#fff",
                  color: isA ? cat.color : COLORS.navyLight,
                  fontWeight: isA ? 700 : 400,
                  cursor: "pointer", transition: "all 0.15s",
                  boxShadow: isA ? `0 2px 8px ${cat.color}33` : "0 1px 3px rgba(0,0,0,0.05)",
                }}>{label}</button>
              );
            })}
          </div>
        </div>

        {/* ── Query input ── */}
        <div style={{
          background: "#fff", borderRadius: 16, border: "1.5px solid #e2e8f0",
          padding: 20, marginBottom: 20,
          boxShadow: "0 4px 20px rgba(0,0,0,0.07)"
        }}>
          {/* Mode toggle */}
          <div style={{ display: "flex", gap: 6, marginBottom: 16, alignItems: "center" }}>
            {(["nl", "sql"] as const).map(m => (
              <button key={m} onClick={() => setMode(m)} style={{
                padding: "7px 18px", borderRadius: 22, border: "1.5px solid",
                borderColor: mode === m ? COLORS.blue : "#e2e8f0",
                background: mode === m ? COLORS.blue : "#f8fafc",
                color: mode === m ? "#fff" : COLORS.slate,
                fontWeight: mode === m ? 700 : 500, fontSize: "0.85rem", cursor: "pointer",
                transition: "all 0.15s",
                boxShadow: mode === m ? "0 3px 10px rgba(59,130,246,0.35)" : "none",
              }}>
                {m === "nl" ? "💬 Plain English" : "🛢️ SQL Editor"}
              </button>
            ))}
            {mode === "sql" && (
              <span style={{ fontSize: "0.76rem", color: "#94a3b8", marginLeft: 6 }}>
                Ctrl+Enter to run · Tables: <code style={{ background: "#f1f5f9", padding: "1px 5px", borderRadius: 4 }}>concessions</code> <code style={{ background: "#f1f5f9", padding: "1px 5px", borderRadius: 4 }}>prices</code> <code style={{ background: "#f1f5f9", padding: "1px 5px", borderRadius: 4 }}>alerts</code> <code style={{ background: "#f1f5f9", padding: "1px 5px", borderRadius: 4 }}>trends</code>
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
                placeholder="e.g. which drugs had the most concession months in 2022?   (Enter to run)"
                rows={2}
                style={{
                  width: "100%", padding: "14px 130px 14px 18px", fontSize: "0.97rem",
                  border: `1.5px solid #e2e8f0`, borderRadius: 12, outline: "none",
                  fontFamily: "inherit", resize: "none", boxSizing: "border-box",
                  lineHeight: 1.5, color: COLORS.navy, background: "#f8fafc",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                }}
                onFocus={e => { e.target.style.borderColor = COLORS.blue; e.target.style.boxShadow = `0 0 0 3px ${COLORS.blue}22`; }}
                onBlur={e => { e.target.style.borderColor = "#e2e8f0"; e.target.style.boxShadow = "none"; }}
              />
              <button onClick={handleAsk} disabled={loading || !question.trim()} style={{
                position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
                background: loading ? "#94a3b8" : `linear-gradient(135deg, ${COLORS.blue}, ${COLORS.blueDark})`,
                color: "#fff", border: "none", borderRadius: 10,
                padding: "9px 20px", cursor: loading ? "wait" : "pointer",
                fontWeight: 700, fontSize: "0.9rem", whiteSpace: "nowrap",
                boxShadow: loading ? "none" : "0 4px 12px rgba(59,130,246,0.4)",
                transition: "all 0.15s",
              }}>
                {loading ? "⏳ …" : "Ask →"}
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
                  width: "100%", padding: "14px 16px", fontSize: "0.88rem",
                  border: "1.5px solid #e2e8f0", borderRadius: 12, outline: "none",
                  fontFamily: "'Menlo','Monaco','Courier New',monospace",
                  resize: "vertical", boxSizing: "border-box", lineHeight: 1.7,
                  background: COLORS.navy, color: "#e2e8f0",
                }}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}>
                <button onClick={handleAsk} disabled={loading || !sql.trim()} style={{
                  background: loading ? "#94a3b8" : `linear-gradient(135deg, ${COLORS.blue}, ${COLORS.blueDark})`,
                  color: "#fff", border: "none", borderRadius: 10, padding: "9px 22px",
                  cursor: loading ? "wait" : "pointer", fontWeight: 700, fontSize: "0.9rem",
                  boxShadow: "0 4px 12px rgba(59,130,246,0.4)",
                }}>
                  {loading ? "⏳ Running…" : "▶ Run SQL"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Loading skeleton ── */}
        {loading && (
          <div style={{
            background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0",
            padding: 24, boxShadow: "0 2px 12px rgba(0,0,0,0.05)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 32, height: 32, borderRadius: "50%",
                border: `3px solid ${COLORS.blue}`, borderTopColor: "transparent",
                animation: "spin 0.8s linear infinite", flexShrink: 0,
              }} />
              <div>
                <div style={{ fontWeight: 600, color: COLORS.navy, marginBottom: 2 }}>Querying the database…</div>
                <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>AI is translating your question to SQL</div>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <Skeleton w="40%" h={14} />
              <Skeleton w="100%" h={36} />
              <Skeleton w="100%" h={36} />
              <Skeleton w="80%" h={36} />
            </div>
            <style>{`
              @keyframes spin { to { transform: rotate(360deg); } }
              @keyframes shimmer { 0% { background-position: -400% 0; } 100% { background-position: 400% 0; } }
            `}</style>
          </div>
        )}

        {/* ── Error (only shown for real backend errors, not offline fallback) ── */}
        {result && !result.success && !loading && (
          <div style={{
            background: "#fff", border: `1.5px solid ${COLORS.rose}55`, borderRadius: 16,
            padding: 20, boxShadow: "0 2px 12px rgba(0,0,0,0.05)"
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <span style={{ fontSize: "1.4rem", lineHeight: 1 }}>⚠️</span>
              <div>
                <div style={{ fontWeight: 700, color: "#9f1239", marginBottom: 4 }}>{result.error}</div>
                {result.sql && (
                  <pre style={{ fontSize: "0.8rem", color: COLORS.slate, background: "#f8fafc", padding: "8px 12px", borderRadius: 8, overflowX: "auto", marginTop: 8 }}>
                    {result.sql}
                  </pre>
                )}
                <div style={{ marginTop: 8, fontSize: "0.82rem", color: "#94a3b8" }}>
                  💡 Try rephrasing your question, or switch to SQL mode for a direct query.
                  <br />The backend rebuilds on Railway after each deploy — if "Offline" wait ~2 min and retry.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Result panel ── */}
        {result?.success && !loading && (
          <div style={{
            background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0",
            overflow: "hidden", boxShadow: "0 4px 20px rgba(0,0,0,0.07)"
          }}>
            {/* Result header */}
            <div style={{
              padding: "14px 20px",
              background: `linear-gradient(90deg, ${COLORS.navy} 0%, #1e3a5f 100%)`,
              display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{
                  background: COLORS.emerald, color: "#fff", borderRadius: 20,
                  padding: "3px 12px", fontSize: "0.82rem", fontWeight: 700
                }}>
                  ✓ {result.row_count?.toLocaleString()} rows
                </span>
                {result.chart_hint && result.chart_hint !== "table" && (
                  <span style={{
                    background: "#fff2", color: "#94a3b8", borderRadius: 12,
                    padding: "3px 10px", fontSize: "0.75rem", fontWeight: 600
                  }}>
                    {result.chart_hint === "bar" ? "📊 Bar chart" : "📈 Line chart"}
                  </span>
                )}
                {result.explanation && (
                  <span style={{ color: "#64748b", fontSize: "0.82rem" }}>{result.explanation}</span>
                )}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={copySQL} style={{
                  background: "#fff1", color: "#94a3b8", border: "1px solid #ffffff22",
                  borderRadius: 8, padding: "5px 12px", fontSize: "0.78rem", cursor: "pointer",
                }}>
                  {sqlCopied ? "✅ Copied" : "📋 Copy SQL"}
                </button>
                <button onClick={exportCSV} style={{
                  background: `linear-gradient(135deg, ${COLORS.emerald}, #059669)`,
                  color: "#fff", border: "none", borderRadius: 8,
                  padding: "5px 14px", fontSize: "0.82rem", cursor: "pointer", fontWeight: 600,
                  boxShadow: "0 2px 8px rgba(16,185,129,0.35)",
                }}>
                  ⬇ Export CSV
                </button>
              </div>
            </div>

            {/* Chart */}
            {chart && (
              <div style={{ padding: "24px 20px 8px", borderBottom: "1px solid #f1f5f9" }}>
                {chart}
              </div>
            )}

            {/* SQL viewer (collapsible) */}
            {result.sql && (
              <details style={{ borderBottom: "1px solid #f1f5f9" }}>
                <summary style={{
                  padding: "10px 20px", cursor: "pointer", fontSize: "0.8rem",
                  color: "#94a3b8", userSelect: "none", listStyle: "none",
                  display: "flex", alignItems: "center", gap: 6,
                }}>
                  <span style={{
                    background: "#f1f5f9", borderRadius: 6, padding: "2px 8px",
                    fontFamily: "monospace", color: COLORS.navyLight, fontSize: "0.75rem"
                  }}>SQL</span>
                  <span>View generated query</span>
                </summary>
                <div style={{ padding: "0 20px 14px" }}>
                  <div style={{ position: "relative" }}>
                    <textarea
                      value={sql}
                      onChange={e => setSql(e.target.value)}
                      rows={4}
                      style={{
                        width: "100%", padding: "12px 14px", fontSize: "0.82rem",
                        fontFamily: "monospace", border: "1px solid #e2e8f0", borderRadius: 10,
                        background: COLORS.navy, color: "#e2e8f0", boxSizing: "border-box", resize: "vertical",
                      }}
                    />
                    <button
                      onClick={() => { setMode("sql"); runQuery({ sql }); }}
                      style={{
                        marginTop: 8, padding: "7px 18px",
                        background: `linear-gradient(135deg, ${COLORS.blue}, ${COLORS.blueDark})`,
                        color: "#fff", border: "none", borderRadius: 8,
                        cursor: "pointer", fontSize: "0.84rem", fontWeight: 600,
                        boxShadow: "0 3px 10px rgba(59,130,246,0.35)",
                      }}>
                      ▶ Re-run edited SQL
                    </button>
                  </div>
                </div>
              </details>
            )}

            {/* Table */}
            {result.columns && result.rows && (
              <ResultTable columns={result.columns} rows={result.rows.slice(0, 200)} />
            )}

            {result.row_count && result.row_count > 200 && (
              <div style={{
                padding: "10px 20px", color: "#94a3b8", fontSize: "0.8rem",
                borderTop: "1px solid #f1f5f9", textAlign: "center", background: "#f8fafc"
              }}>
                Showing 200 of {result.row_count.toLocaleString()} rows · Export CSV for complete data
              </div>
            )}
          </div>
        )}

        {/* ── Empty state ── */}
        {!result && !loading && (
          <div style={{
            background: "#fff", borderRadius: 16, border: "1.5px dashed #e2e8f0",
            padding: "48px 24px", textAlign: "center",
            boxShadow: "0 2px 12px rgba(0,0,0,0.04)"
          }}>
            <div style={{ fontSize: "3rem", marginBottom: 16 }}>🔍</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: COLORS.navy, marginBottom: 8 }}>
              Explore the full UK drug concession history
            </div>
            <div style={{ fontSize: "0.88rem", color: COLORS.slate, marginBottom: 24, lineHeight: 1.7 }}>
              7,742 concession events · 15,122 NHS tariff prices · 3,372 MHRA alerts<br />
              <strong style={{ color: COLORS.amber }}>🔥 The 2022 drug shortage crisis — 198 drugs hit concession in a single month</strong>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
              {[
                { label: "🔥 Show Dec 2022 peak",  q: "all drugs on concession in December 2022 ordered by concession price descending" },
                { label: "📈 Year-by-year totals",  q: "how many drugs went on concession each year?" },
                { label: "💰 Most expensive ever", q: "top 20 highest concession prices ever recorded" },
              ].map(({ label, q }) => (
                <button key={label} onClick={() => handleQuick(q, label)} style={{
                  padding: "10px 20px", borderRadius: 22,
                  border: `1.5px solid ${COLORS.blue}44`,
                  background: COLORS.blueLight, color: COLORS.blue,
                  fontSize: "0.88rem", cursor: "pointer", fontWeight: 600,
                  boxShadow: "0 2px 8px rgba(59,130,246,0.12)",
                  transition: "all 0.15s",
                }}>{label}</button>
              ))}
            </div>
          </div>
        )}

        {/* ── Schema reference ── */}
        <details style={{ marginTop: 20, background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0" }}>
          <summary style={{
            padding: "13px 20px", cursor: "pointer", fontWeight: 600,
            fontSize: "0.86rem", color: COLORS.slate, listStyle: "none",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ background: "#f1f5f9", borderRadius: 6, padding: "2px 8px", fontFamily: "monospace", fontSize: "0.75rem" }}>SQL</span>
            Available tables &amp; columns
          </summary>
          <div style={{ padding: "8px 20px 20px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
            {[
              { name: "concessions", rows: "7,742", color: COLORS.blue,    cols: ["month VARCHAR (YYYY-MM)", "drug VARCHAR", "concession_price DOUBLE"] },
              { name: "prices",      rows: "15,122", color: COLORS.emerald, cols: ["drug VARCHAR", "month VARCHAR (YYYY-MM)", "price_gbp DOUBLE"] },
              { name: "alerts",      rows: "3,372",  color: COLORS.rose,    cols: ["title VARCHAR", "date VARCHAR", "description VARCHAR", "source VARCHAR"] },
              { name: "trends",      rows: "74",     color: COLORS.violet,  cols: ["month VARCHAR (YYYY-MM)", "count INTEGER"] },
            ].map(t => (
              <div key={t.name} style={{ background: "#f8fafc", borderRadius: 10, padding: "12px 16px", borderLeft: `3px solid ${t.color}` }}>
                <div style={{ fontFamily: "monospace", fontWeight: 700, color: t.color, marginBottom: 6 }}>
                  {t.name}
                  <span style={{ fontWeight: 400, color: "#94a3b8", marginLeft: 6, fontSize: "0.75rem" }}>({t.rows})</span>
                </div>
                {t.cols.map(c => (
                  <div key={c} style={{ fontFamily: "monospace", fontSize: "0.76rem", color: COLORS.slate, padding: "2px 0" }}>· {c}</div>
                ))}
              </div>
            ))}
          </div>
          <div style={{ padding: "0 20px 14px", fontSize: "0.78rem", color: "#94a3b8" }}>
            Use <code>LIKE '2022%'</code> for year filtering · <code>LOWER(drug) LIKE '%keyword%'</code> for drug search
          </div>
        </details>

        {/* ── Scope notice ── */}
        <div style={{
          marginTop: 16, padding: "12px 18px",
          background: COLORS.amberLight, border: `1px solid ${COLORS.amber}66`,
          borderRadius: 12, fontSize: "0.82rem", color: "#92400e",
          display: "flex", gap: 10, alignItems: "flex-start"
        }}>
          <span style={{ fontSize: "1rem", flexShrink: 0 }}>📌</span>
          <span>
            <strong>Historical data only:</strong> Jan 2020 – Feb 2026 (archived CPE, NHS tariff, MHRA).
            Live data integration is on the roadmap. For current predictions, use{" "}
            <a href="/drugs" style={{ color: COLORS.amberDark, fontWeight: 700 }}>Risk Finder</a>.
          </span>
        </div>
      </div>
    </div>
  );
}
