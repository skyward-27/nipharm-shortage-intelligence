import { useState, useRef, useCallback, useEffect } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ─── Sample data shown when backend is offline ────────────────────────────────
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
  explanation: "Backend rebuilding — showing sample 2022 data. Live queries will work once Railway finishes deployment.",
};

// ─── Colour palette ───────────────────────────────────────────────────────────
const COLORS = {
  navy:       "#0f172a",
  navyMid:    "#1e293b",
  navyLight:  "#334155",
  blue:       "#3b82f6",
  blueDark:   "#1d4ed8",
  blueLight:  "#dbeafe",
  amber:      "#f59e0b",
  amberDark:  "#d97706",
  amberLight: "#fef3c7",
  emerald:    "#10b981",
  emeraldLight:"#d1fae5",
  rose:       "#ef4444",
  roseLight:  "#ffe4e6",
  violet:     "#7c3aed",
  violetLight:"#ede9fe",
  slate:      "#64748b",
  slateLight: "#f1f5f9",
  white:      "#ffffff",
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

interface ConversationEntry {
  id: number;
  userQuery: string;
  result: QueryResult;
  sql: string;
}

type SortDir = "asc" | "desc" | null;

// ─── SVG Icon components ──────────────────────────────────────────────────────
function FlameIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </svg>
  );
}

function LineChartIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function TagIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" />
      <path d="M7 7h.01" />
    </svg>
  );
}

function BellIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

function LensIcon({ size = 20, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

function SendIcon({ size = 18, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </svg>
  );
}

function BarChartIcon({ size = 16, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" x2="12" y1="20" y2="10" />
      <line x1="18" x2="18" y1="20" y2="4" />
      <line x1="6" x2="6" y1="20" y2="16" />
    </svg>
  );
}

// ─── Category definitions ─────────────────────────────────────────────────────
const CATEGORIES = [
  { id: "2022 Peak", color: COLORS.amber,   light: COLORS.amberLight,   label: "2022 Crisis",  Icon: FlameIcon },
  { id: "Trends",    color: COLORS.blue,    light: COLORS.blueLight,    label: "Trends",       Icon: LineChartIcon },
  { id: "Prices",    color: COLORS.emerald, light: COLORS.emeraldLight, label: "Prices",       Icon: TagIcon },
  { id: "Alerts",    color: COLORS.rose,    light: COLORS.roseLight,    label: "MHRA Alerts",  Icon: BellIcon },
] as const;
type CategoryId = typeof CATEGORIES[number]["id"];

// ─── Quick questions (no emoji) ───────────────────────────────────────────────
const QUICK_QUESTIONS: Record<CategoryId, { label: string; q: string }[]> = {
  "2022 Peak": [
    { label: "Dec 2022 peak — all drugs",         q: "all drugs on concession in December 2022 ordered by concession price descending" },
    { label: "2022 monthly concession count",      q: "how many drugs went on concession each month in 2022?" },
    { label: "First-time concessions in 2022",     q: "drugs that first appeared on concession in 2022 ordered by concession price" },
    { label: "Top 20 priciest in 2022",            q: "top 20 most expensive concession prices in 2022" },
    { label: "2021 vs 2022 totals",                q: "total concession count per year for 2021 and 2022" },
    { label: "Most conceded months in 2022",       q: "drugs with most concession months in 2022" },
  ],
  "Trends": [
    { label: "Year-on-year totals",                q: "how many drugs went on concession each year?" },
    { label: "Winter vs summer concessions",       q: "total concessions in months 11,12,1,2 versus months 5,6,7,8" },
    { label: "Most concession events ever",        q: "which drugs had the most concession events ever?" },
    { label: "2025–2026 recent trend",             q: "total drugs on concession per month for 2025 and 2026" },
    { label: "Longest continuous streaks",         q: "which drugs had the most total concession months?" },
  ],
  "Prices": [
    { label: "Highest concession prices ever",     q: "top 20 highest concession prices ever recorded" },
    { label: "Metformin 500mg price history",      q: "metformin 500mg tablets price history by month" },
    { label: "Omeprazole 20mg price history",      q: "omeprazole 20mg gastro-resistant capsules price history" },
    { label: "NHS tariff over £50",                q: "drugs where price_gbp exceeded 50 in any month" },
    { label: "Insulin concessions history",        q: "all insulin drugs that ever appeared on concession" },
    { label: "Concession price over £100",         q: "drugs where concession price exceeded 100" },
  ],
  "Alerts": [
    { label: "Latest MHRA publications",           q: "most recent 20 MHRA shortage publications ordered by date" },
    { label: "Amoxicillin shortage alerts",        q: "MHRA alerts about amoxicillin shortage" },
    { label: "Insulin supply alerts",              q: "MHRA alerts mentioning insulin shortage" },
    { label: "2023 shortage alerts",               q: "MHRA shortage publications from 2023 ordered by date" },
    { label: "Manufacturing and supply alerts",    q: "MHRA alerts mentioning manufacturing or supply" },
  ],
};

const YEARS = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"];

const INSIGHTS = [
  "Dec 2022 was the worst month in 6 years — 198 drugs conceded at once",
  "Mometasone 0.1% cream was conceded 23 months in 2022 alone",
  "Total concessions rose 340% from Jan 2020 to Dec 2022",
  "3,372 MHRA shortage publications tracked since 2020",
  "Some drugs hit concession prices 10x their NHS tariff price",
  "GBP/INR weakness in 2022 drove a wave of generic price rises",
];

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function Skeleton({ w = "100%", h = 18, r = 6 }: { w?: string | number; h?: number; r?: number }) {
  return (
    <div className="skeleton" style={{ width: w, height: h, borderRadius: r }} />
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
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
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
        <polygon
          points={`${PL},${PT + iH} ${pts} ${xOf(rows.length - 1)},${PT + iH}`}
          fill="url(#lineArea)"
        />
        <polyline points={pts} fill="none" stroke={COLORS.blue} strokeWidth={2.5} strokeLinejoin="round" filter="url(#glow)" />
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
      <div className="table-copy-bar">
        <button
          className="btn-ghost-sm"
          onClick={() => { navigator.clipboard?.writeText(columns.join("\t")); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        >
          {copied ? "Copied!" : "Copy headers"}
        </button>
      </div>
      <div style={{ overflowX: "auto", maxHeight: 480, overflowY: "auto" }}>
        <table className="result-table">
          <thead>
            <tr>
              {columns.map(c => (
                <th
                  key={c}
                  onClick={() => toggleSort(c)}
                  style={{ color: sort.col === c ? "#60a5fa" : "#94a3b8", borderBottomColor: sort.col === c ? COLORS.blue : "#1e293b" }}
                >
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
              <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#f8fafc" }}
                onMouseEnter={e => (e.currentTarget.style.background = "#eff6ff")}
                onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f8fafc")}>
                {columns.map(c => (
                  <td key={c}>{fmtVal(row[c], c)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Insight ticker ───────────────────────────────────────────────────────────
function InsightTicker() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % INSIGHTS.length), 4000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="insight-ticker">
      <span className="ticker-label">DID YOU KNOW</span>
      <span className="ticker-text">{INSIGHTS[idx]}</span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function ConcessionLens() {
  const [question, setQuestion]           = useState("");
  const [sql, setSql]                     = useState("");
  const [result, setResult]               = useState<QueryResult | null>(null);
  const [loading, setLoading]             = useState(false);
  const [mode, setMode]                   = useState<"nl" | "sql">("nl");
  const [activeQ, setActiveQ]             = useState("");
  const [activeYear, setActiveYear]       = useState<string | null>(null);
  const [activeCategory, setActiveCat]    = useState<CategoryId>("2022 Peak");
  const [sqlCopied, setSqlCopied]         = useState(false);
  const [backendStatus, setBackendStatus] = useState<"unknown" | "online" | "offline">("unknown");
  const [conversation, setConversation]   = useState<ConversationEntry[]>([]);
  const inputRef    = useRef<HTMLTextAreaElement>(null);
  const bottomRef   = useRef<HTMLDivElement>(null);
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

  // ── Auto-scroll to latest result ──
  useEffect(() => {
    if (conversation.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [conversation]);

  const runQuery = useCallback(async (opts: { question?: string; sql?: string }) => {
    const userQuery = opts.question || opts.sql || "";
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
      setConversation(prev => [...prev, { id: Date.now(), userQuery, result: data, sql: data.sql || "" }]);
    } catch {
      setBackendStatus("offline");
      const fallback: QueryResult = {
        ...SAMPLE_RESULT,
        explanation: "Backend rebuilding on Railway — showing sample 2022 data. Live AI queries will work once it is back online.",
      };
      setResult(fallback);
      setSql(SAMPLE_RESULT.sql);
      setConversation(prev => [...prev, { id: Date.now(), userQuery, result: fallback, sql: SAMPLE_RESULT.sql }]);
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
  };

  const handleYear = (y: string) => {
    setActiveYear(y); setActiveQ("");
    const q = y === "2022"
      ? "how many drugs went on concession each month in 2022 ordered by month?"
      : `all drugs on concession in ${y} ordered by month and price`;
    setQuestion(q); setMode("nl");
    runQuery({ question: q });
  };

  const exportCSV = (r: QueryResult) => {
    if (!r.rows?.length || !r.columns) return;
    const header = r.columns.join(",");
    const body = r.rows.map(row => r.columns!.map(c => JSON.stringify(row[c] ?? "")).join(",")).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `nipharma_${activeQ || "query"}_${Date.now()}.csv`; a.click();
  };

  const copySQL = (sqlText: string) => {
    navigator.clipboard?.writeText(sqlText);
    setSqlCopied(true); setTimeout(() => setSqlCopied(false), 1500);
  };

  const renderChart = (r: QueryResult) => {
    if (!r.success || !r.rows?.length || !r.columns || r.rows.length < 2) return null;
    if (r.chart_hint === "line") return <LineChart columns={r.columns} rows={r.rows} />;
    if (r.chart_hint === "bar" && r.rows.length <= 40) return <BarChart columns={r.columns} rows={r.rows} />;
    return null;
  };

  return (
    <div className="cl-root">

      {/* ══════════════════════════════════════════════════════════════════════
          LEFT SIDEBAR
      ══════════════════════════════════════════════════════════════════════ */}
      <aside className="cl-sidebar">

        {/* Brand */}
        <div className="sidebar-brand">
          <div className="brand-icon">
            <LensIcon size={18} color={COLORS.blue} />
          </div>
          <span className="brand-name">Concession Lens</span>
        </div>

        {/* Category tabs */}
        <div className="sidebar-section-label">EXPLORE BY</div>
        <nav className="sidebar-categories">
          {CATEGORIES.map(c => {
            const isA = activeCategory === c.id;
            return (
              <button
                key={c.id}
                className={`cat-tab${isA ? " cat-tab--active" : ""}`}
                style={isA ? { borderColor: c.color, background: c.color + "1a", color: c.color } : {}}
                onClick={() => setActiveCat(c.id)}
              >
                <span className="cat-icon" style={{ color: isA ? c.color : "#64748b" }}>
                  <c.Icon size={15} color={isA ? c.color : "#64748b"} />
                </span>
                <span className="cat-label">{c.label}</span>
                {c.id === "2022 Peak" && (
                  <span className="cat-badge" style={{ background: isA ? COLORS.amber + "33" : COLORS.amberLight, color: COLORS.amberDark }}>
                    HOT
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Quick questions for active category */}
        <div className="sidebar-section-label" style={{ marginTop: 20 }}>QUICK QUESTIONS</div>
        <div className="sidebar-pills">
          {QUICK_QUESTIONS[activeCategory].map(({ label, q }) => {
            const isA = activeQ === label;
            return (
              <button
                key={label}
                className={`sidebar-pill${isA ? " sidebar-pill--active" : ""}`}
                style={isA ? { borderColor: cat.color, background: cat.color + "18", color: cat.color } : {}}
                onClick={() => handleQuick(q, label)}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Year jump */}
        <div className="sidebar-section-label" style={{ marginTop: 20 }}>JUMP TO YEAR</div>
        <div className="year-chips">
          {YEARS.map(y => {
            const is22 = y === "2022";
            const isActive = activeYear === y;
            return (
              <button
                key={y}
                className={`year-chip${isActive ? " year-chip--active" : ""}${is22 ? " year-chip--crisis" : ""}`}
                style={isActive
                  ? { background: is22 ? COLORS.amber : COLORS.blue, borderColor: is22 ? COLORS.amber : COLORS.blue, color: "#fff" }
                  : is22
                    ? { borderColor: COLORS.amber + "88", color: COLORS.amberDark, background: COLORS.amberLight }
                    : {}
                }
                onClick={() => handleYear(y)}
              >
                {y}
              </button>
            );
          })}
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Footer stats */}
        <div className="sidebar-footer">
          <div className="footer-stat">6 years of data</div>
          <div className="footer-sep">·</div>
          <div className="footer-stat">758 drugs tracked</div>
        </div>
      </aside>

      {/* ══════════════════════════════════════════════════════════════════════
          RIGHT MAIN AREA
      ══════════════════════════════════════════════════════════════════════ */}
      <div className="cl-main">

        {/* ── Top bar ── */}
        <header className="main-topbar">
          <div className="topbar-left">
            <span className="topbar-title">Concession Lens</span>
            <span className="topbar-sub">NHS drug concession data · 2020–2026</span>
          </div>
          <div className="topbar-right">
            {/* Backend status dot */}
            {backendStatus !== "unknown" && (
              <div className="status-badge">
                <span
                  className="status-dot"
                  style={{ background: backendStatus === "online" ? COLORS.emerald : COLORS.amber }}
                />
                <span className="status-label">
                  {backendStatus === "online" ? "Backend online" : "Backend rebuilding"}
                </span>
              </div>
            )}
            {/* Mode toggle */}
            <div className="mode-toggle">
              <button
                className={`mode-btn${mode === "nl" ? " mode-btn--active" : ""}`}
                onClick={() => setMode("nl")}
              >
                Ask in plain English
              </button>
              <button
                className={`mode-btn${mode === "sql" ? " mode-btn--active" : ""}`}
                onClick={() => setMode("sql")}
              >
                Advanced SQL
              </button>
            </div>
          </div>
        </header>

        {/* ── Insight ticker ── */}
        <InsightTicker />

        {/* ── Conversation area ── */}
        <div className="conversation-area">

          {/* Empty state */}
          {conversation.length === 0 && !loading && (
            <div className="empty-state">
              <div className="empty-icon">
                <LensIcon size={40} color={COLORS.blue} />
              </div>
              <h2 className="empty-title">Ask about NHS concession data</h2>
              <p className="empty-sub">
                7,742 concession events · 15,122 NHS tariff prices · 3,372 MHRA alerts<br />
                The 2022 drug shortage crisis — 198 drugs hit concession in a single month
              </p>
              <div className="empty-chips">
                {[
                  { label: "Show Dec 2022 peak",    q: "all drugs on concession in December 2022 ordered by concession price descending" },
                  { label: "Year-by-year totals",   q: "how many drugs went on concession each year?" },
                  { label: "Most expensive ever",   q: "top 20 highest concession prices ever recorded" },
                ].map(({ label, q }) => (
                  <button key={label} className="empty-chip" onClick={() => handleQuick(q, label)}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Conversation messages */}
          {conversation.map(entry => (
            <div key={entry.id} className="conv-group">
              {/* User bubble (right-aligned) */}
              <div className="conv-user-row">
                <div className="conv-user-bubble">{entry.userQuery}</div>
              </div>

              {/* Result card (left-aligned) */}
              <div className="conv-result-row">
                <div className="conv-result-card">
                  {/* Result header */}
                  {entry.result.success && (
                    <div className="result-header">
                      <div className="result-header-left">
                        <span className="result-rows-badge">
                          {entry.result.row_count?.toLocaleString()} rows
                        </span>
                        {entry.result.chart_hint && entry.result.chart_hint !== "table" && (
                          <span className="result-chart-badge">
                            <BarChartIcon size={12} color="#94a3b8" />
                            {entry.result.chart_hint === "bar" ? "Bar chart" : "Line chart"}
                          </span>
                        )}
                        {entry.result.explanation && (
                          <span className="result-explanation">{entry.result.explanation}</span>
                        )}
                      </div>
                      <div className="result-header-actions">
                        <button className="btn-result-action" onClick={() => copySQL(entry.sql)}>
                          {sqlCopied ? "Copied" : "Copy SQL"}
                        </button>
                        <button className="btn-result-export" onClick={() => exportCSV(entry.result)}>
                          Export CSV
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {!entry.result.success && (
                    <div className="result-error">
                      <div className="result-error-title">{entry.result.error}</div>
                      {entry.result.sql && (
                        <pre className="result-error-sql">{entry.result.sql}</pre>
                      )}
                      <div className="result-error-hint">
                        Try rephrasing your question, or switch to Advanced SQL mode for a direct query.
                        The backend rebuilds on Railway after each deploy — if offline, wait 2 minutes and retry.
                      </div>
                    </div>
                  )}

                  {/* Chart */}
                  {entry.result.success && renderChart(entry.result) && (
                    <div className="result-chart-area">
                      {renderChart(entry.result)}
                    </div>
                  )}

                  {/* SQL viewer */}
                  {entry.result.success && entry.sql && (
                    <details className="sql-details">
                      <summary className="sql-summary">
                        <span className="sql-badge">SQL</span>
                        View generated query
                      </summary>
                      <div className="sql-body">
                        <textarea
                          value={entry.sql}
                          onChange={e => setSql(e.target.value)}
                          rows={4}
                          className="sql-editor"
                        />
                        <button
                          className="btn-rerun"
                          onClick={() => { setMode("sql"); setSql(entry.sql); runQuery({ sql: entry.sql }); }}
                        >
                          Re-run edited SQL
                        </button>
                      </div>
                    </details>
                  )}

                  {/* Table */}
                  {entry.result.success && entry.result.columns && entry.result.rows && (
                    <ResultTable columns={entry.result.columns} rows={entry.result.rows.slice(0, 200)} />
                  )}

                  {entry.result.row_count && entry.result.row_count > 200 && (
                    <div className="result-truncation-note">
                      Showing 200 of {entry.result.row_count.toLocaleString()} rows · Export CSV for complete data
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="conv-group">
              <div className="conv-user-row">
                <div className="conv-user-bubble conv-user-bubble--loading">
                  {mode === "nl" ? question : sql}
                </div>
              </div>
              <div className="conv-result-row">
                <div className="conv-result-card conv-loading-card">
                  <div className="loading-header">
                    <div className="spinner" />
                    <div>
                      <div className="loading-title">Querying the database…</div>
                      <div className="loading-sub">AI is translating your question to SQL</div>
                    </div>
                  </div>
                  <div className="loading-skeletons">
                    <Skeleton w="40%" h={14} />
                    <Skeleton w="100%" h={36} />
                    <Skeleton w="100%" h={36} />
                    <Skeleton w="80%" h={36} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Query input (sticky bottom) ── */}
        <div className="query-input-bar">
          {/* SQL hint */}
          {mode === "sql" && (
            <div className="sql-hint">
              Ctrl+Enter to run · Tables:&nbsp;
              <code>concessions</code>&nbsp;
              <code>prices</code>&nbsp;
              <code>alerts</code>&nbsp;
              <code>trends</code>
            </div>
          )}

          <div className="query-input-inner">
            {mode === "nl" ? (
              <textarea
                ref={inputRef}
                className="query-textarea"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
                placeholder="e.g. which drugs had the most concession months in 2022?  (Enter to run)"
                rows={2}
              />
            ) : (
              <textarea
                className="query-textarea query-textarea--sql"
                value={sql}
                onChange={e => setSql(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleAsk(); }}
                placeholder={"SELECT drug, COUNT(*) AS events\nFROM concessions\nWHERE month LIKE '2022%'\nGROUP BY drug\nORDER BY events DESC\nLIMIT 20"}
                rows={4}
              />
            )}
            <button
              className="query-send-btn"
              onClick={handleAsk}
              disabled={loading || (mode === "nl" ? !question.trim() : !sql.trim())}
              title="Send query"
            >
              {loading
                ? <div className="spinner spinner--sm" />
                : <SendIcon size={18} color="#fff" />
              }
            </button>
          </div>

          {/* Schema reference */}
          <details className="schema-details">
            <summary className="schema-summary">
              <span className="sql-badge">SQL</span>
              Available tables &amp; columns
            </summary>
            <div className="schema-grid">
              {[
                { name: "concessions", rows: "7,742",  color: COLORS.blue,    cols: ["month VARCHAR (YYYY-MM)", "drug VARCHAR", "concession_price DOUBLE"] },
                { name: "prices",      rows: "15,122", color: COLORS.emerald, cols: ["drug VARCHAR", "month VARCHAR (YYYY-MM)", "price_gbp DOUBLE"] },
                { name: "alerts",      rows: "3,372",  color: COLORS.rose,    cols: ["title VARCHAR", "date VARCHAR", "description VARCHAR", "source VARCHAR"] },
                { name: "trends",      rows: "74",     color: COLORS.violet,  cols: ["month VARCHAR (YYYY-MM)", "count INTEGER"] },
              ].map(t => (
                <div key={t.name} className="schema-table" style={{ borderLeftColor: t.color }}>
                  <div className="schema-table-name" style={{ color: t.color }}>
                    {t.name}
                    <span className="schema-table-rows">({t.rows})</span>
                  </div>
                  {t.cols.map(c => (
                    <div key={c} className="schema-col">· {c}</div>
                  ))}
                </div>
              ))}
            </div>
            <div className="schema-hint">
              Use <code>LIKE '2022%'</code> for year filtering · <code>LOWER(drug) LIKE '%keyword%'</code> for drug search
            </div>
          </details>

          {/* Scope notice */}
          <div className="scope-notice">
            <strong>Historical data only:</strong> Jan 2020 – Feb 2026 (archived CPE, NHS tariff, MHRA).
            For current predictions, use{" "}
            <a href="/drugs" className="scope-link">Risk Finder</a>.
          </div>
        </div>
      </div>

      {/* ── CSS ── */}
      <style>{CSS}</style>
    </div>
  );
}

// ─── CSS ──────────────────────────────────────────────────────────────────────
const CSS = `
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes shimmer { 0% { background-position: -400% 0; } 100% { background-position: 400% 0; } }
  @keyframes fadeSlideIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

  /* ── Layout shell ── */
  .cl-root {
    display: flex;
    height: 100vh;
    overflow: hidden;
    font-family: inherit;
    background: #f8fafc;
  }

  /* ══════════════════ SIDEBAR ══════════════════ */
  .cl-sidebar {
    width: 260px;
    min-width: 260px;
    max-width: 260px;
    background: #0f172a;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0 0 16px 0;
    scrollbar-width: thin;
    scrollbar-color: #334155 transparent;
  }
  .cl-sidebar::-webkit-scrollbar { width: 4px; }
  .cl-sidebar::-webkit-scrollbar-track { background: transparent; }
  .cl-sidebar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }

  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 16px 18px;
    border-bottom: 1px solid #1e293b;
  }
  .brand-icon {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: #1e293b;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .brand-name {
    font-size: 0.97rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.01em;
  }

  .sidebar-section-label {
    padding: 16px 16px 6px;
    font-size: 0.67rem;
    font-weight: 700;
    color: #475569;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  /* Category tabs */
  .sidebar-categories {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 0 10px;
  }
  .cat-tab {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 9px 10px;
    border-radius: 8px;
    border: 1px solid transparent;
    background: transparent;
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, color 0.15s;
    width: 100%;
  }
  .cat-tab:hover { background: #1e293b; color: #e2e8f0; }
  .cat-tab--active { font-weight: 600; }
  .cat-icon { display: flex; align-items: center; flex-shrink: 0; }
  .cat-label { flex: 1; }
  .cat-badge {
    font-size: 0.62rem;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 8px;
    letter-spacing: 0.04em;
  }

  /* Quick question pills */
  .sidebar-pills {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 0 10px;
  }
  .sidebar-pill {
    padding: 6px 10px;
    font-size: 0.78rem;
    border-radius: 6px;
    border: 1px solid #1e293b;
    background: transparent;
    color: #94a3b8;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
    line-height: 1.4;
    width: 100%;
  }
  .sidebar-pill:hover { background: #1e293b; color: #e2e8f0; border-color: #334155; }
  .sidebar-pill--active { font-weight: 600; }

  /* Year chips */
  .year-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 0 12px;
  }
  .year-chip {
    padding: 4px 12px;
    font-size: 0.78rem;
    border-radius: 14px;
    border: 1px solid #1e293b;
    background: transparent;
    color: #94a3b8;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.12s;
  }
  .year-chip:hover { background: #1e293b; color: #e2e8f0; }
  .year-chip--active { font-weight: 700; }
  .year-chip--crisis { font-weight: 700; }

  /* Footer */
  .sidebar-footer {
    padding: 12px 16px 0;
    display: flex;
    align-items: center;
    gap: 6px;
    border-top: 1px solid #1e293b;
    margin-top: 12px;
  }
  .footer-stat { font-size: 0.72rem; color: #475569; }
  .footer-sep { color: #334155; font-size: 0.72rem; }

  /* ══════════════════ MAIN AREA ══════════════════ */
  .cl-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  /* Top bar */
  .main-topbar {
    background: #0f172a;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
    border-bottom: 1px solid #1e293b;
  }
  .topbar-left { display: flex; flex-direction: column; gap: 1px; }
  .topbar-title { font-size: 0.97rem; font-weight: 700; color: #f1f5f9; }
  .topbar-sub { font-size: 0.72rem; color: #475569; }
  .topbar-right { display: flex; align-items: center; gap: 14px; }

  .status-badge { display: flex; align-items: center; gap: 6px; }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status-label { font-size: 0.78rem; color: #94a3b8; white-space: nowrap; }

  .mode-toggle {
    display: flex;
    gap: 0;
    border-radius: 8px;
    border: 1px solid #334155;
    overflow: hidden;
  }
  .mode-btn {
    padding: 6px 14px;
    font-size: 0.78rem;
    font-weight: 500;
    border: none;
    background: transparent;
    color: #64748b;
    cursor: pointer;
    transition: all 0.14s;
    white-space: nowrap;
  }
  .mode-btn:hover { background: #1e293b; color: #e2e8f0; }
  .mode-btn--active { background: #3b82f6; color: #fff; font-weight: 700; }

  /* Insight ticker */
  .insight-ticker {
    background: #0f172a;
    padding: 6px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid #1e293b;
    flex-shrink: 0;
  }
  .ticker-label {
    font-size: 0.65rem;
    font-weight: 800;
    color: #f59e0b;
    white-space: nowrap;
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .ticker-text {
    font-size: 0.78rem;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ── Conversation area ── */
  .conversation-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px 24px 12px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
  }
  .conversation-area::-webkit-scrollbar { width: 6px; }
  .conversation-area::-webkit-scrollbar-track { background: transparent; }
  .conversation-area::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

  /* Empty state */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 60px 24px;
    animation: fadeSlideIn 0.3s ease;
  }
  .empty-icon {
    width: 72px;
    height: 72px;
    border-radius: 20px;
    background: #dbeafe;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
  }
  .empty-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 10px;
  }
  .empty-sub {
    font-size: 0.88rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 480px;
    margin: 0 0 24px;
  }
  .empty-chips { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
  .empty-chip {
    padding: 9px 18px;
    border-radius: 22px;
    border: 1.5px solid #bfdbfe;
    background: #dbeafe;
    color: #3b82f6;
    font-size: 0.86rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.14s;
  }
  .empty-chip:hover { background: #bfdbfe; border-color: #93c5fd; }

  /* Conversation groups */
  .conv-group { display: flex; flex-direction: column; gap: 10px; animation: fadeSlideIn 0.25s ease; }
  .conv-user-row { display: flex; justify-content: flex-end; }
  .conv-user-bubble {
    background: #0f172a;
    color: #f1f5f9;
    padding: 10px 16px;
    border-radius: 18px 18px 4px 18px;
    font-size: 0.9rem;
    max-width: 70%;
    line-height: 1.5;
    word-break: break-word;
  }
  .conv-user-bubble--loading { opacity: 0.6; }

  .conv-result-row { display: flex; justify-content: flex-start; }
  .conv-result-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 4px 18px 18px 18px;
    overflow: hidden;
    max-width: 100%;
    width: 100%;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }

  /* Loading card */
  .conv-loading-card { padding: 20px; }
  .loading-header { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
  .loading-title { font-weight: 600; color: #0f172a; margin-bottom: 2px; font-size: 0.9rem; }
  .loading-sub { font-size: 0.78rem; color: #94a3b8; }
  .loading-skeletons { display: flex; flex-direction: column; gap: 10px; }

  /* Result header */
  .result-header {
    background: linear-gradient(90deg, #0f172a 0%, #1e3a5f 100%);
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
  }
  .result-header-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .result-rows-badge {
    background: #10b981;
    color: #fff;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 700;
  }
  .result-chart-badge {
    display: flex;
    align-items: center;
    gap: 5px;
    background: rgba(255,255,255,0.1);
    color: #94a3b8;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 0.73rem;
    font-weight: 600;
  }
  .result-explanation { color: #64748b; font-size: 0.78rem; }
  .result-header-actions { display: flex; gap: 8px; }
  .btn-result-action {
    background: rgba(255,255,255,0.07);
    color: #94a3b8;
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.13s;
  }
  .btn-result-action:hover { background: rgba(255,255,255,0.13); }
  .btn-result-export {
    background: linear-gradient(135deg, #10b981, #059669);
    color: #fff;
    border: none;
    border-radius: 7px;
    padding: 5px 13px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 7px rgba(16,185,129,0.3);
  }

  /* Error */
  .result-error { padding: 18px 20px; }
  .result-error-title { font-weight: 700; color: #9f1239; margin-bottom: 6px; font-size: 0.9rem; }
  .result-error-sql {
    font-size: 0.78rem;
    color: #64748b;
    background: #f8fafc;
    padding: 8px 12px;
    border-radius: 7px;
    overflow-x: auto;
    margin-top: 6px;
    margin-bottom: 0;
  }
  .result-error-hint { margin-top: 10px; font-size: 0.8rem; color: #94a3b8; line-height: 1.6; }

  /* Chart area */
  .result-chart-area {
    padding: 20px 18px 8px;
    border-bottom: 1px solid #f1f5f9;
  }

  /* SQL details */
  .sql-details { border-bottom: 1px solid #f1f5f9; }
  .sql-summary {
    padding: 9px 18px;
    cursor: pointer;
    font-size: 0.78rem;
    color: #94a3b8;
    user-select: none;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .sql-summary::-webkit-details-marker { display: none; }
  .sql-badge {
    background: #f1f5f9;
    border-radius: 5px;
    padding: 2px 8px;
    font-family: monospace;
    color: #334155;
    font-size: 0.72rem;
    font-weight: 700;
  }
  .sql-body { padding: 0 18px 12px; }
  .sql-editor {
    width: 100%;
    padding: 10px 12px;
    font-size: 0.8rem;
    font-family: 'Menlo','Monaco','Courier New',monospace;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #0f172a;
    color: #e2e8f0;
    box-sizing: border-box;
    resize: vertical;
    outline: none;
    line-height: 1.6;
  }
  .btn-rerun {
    margin-top: 8px;
    padding: 6px 16px;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: #fff;
    border: none;
    border-radius: 7px;
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3);
  }

  /* Table */
  .table-copy-bar {
    padding: 0 18px 6px;
    display: flex;
    justify-content: flex-end;
  }
  .btn-ghost-sm {
    font-size: 0.72rem;
    color: #94a3b8;
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 8px;
  }
  .btn-ghost-sm:hover { color: #334155; }
  .result-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .result-table thead tr {
    background: #0f172a;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  .result-table th {
    padding: 9px 15px;
    text-align: left;
    font-weight: 700;
    cursor: pointer;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    user-select: none;
    border-bottom: 2px solid #1e293b;
    transition: color 0.13s;
  }
  .result-table td {
    padding: 8px 15px;
    border-bottom: 1px solid #f1f5f9;
    color: #1e293b;
  }

  .result-truncation-note {
    padding: 9px 18px;
    color: #94a3b8;
    font-size: 0.77rem;
    border-top: 1px solid #f1f5f9;
    text-align: center;
    background: #f8fafc;
  }

  /* ── Query input bar ── */
  .query-input-bar {
    background: #fff;
    border-top: 1px solid #e2e8f0;
    padding: 12px 20px 10px;
    flex-shrink: 0;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.06);
  }
  .sql-hint {
    font-size: 0.73rem;
    color: #94a3b8;
    margin-bottom: 8px;
    padding: 0 4px;
  }
  .sql-hint code {
    background: #f1f5f9;
    border-radius: 4px;
    padding: 1px 5px;
    font-family: monospace;
    color: #334155;
    font-size: 0.72rem;
  }
  .query-input-inner {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 10px 10px 10px 14px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .query-input-inner:focus-within {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
  }
  .query-textarea {
    flex: 1;
    border: none;
    background: transparent;
    font-family: inherit;
    font-size: 0.93rem;
    color: #0f172a;
    resize: none;
    outline: none;
    line-height: 1.55;
    padding: 0;
    min-height: 42px;
  }
  .query-textarea::placeholder { color: #94a3b8; }
  .query-textarea--sql {
    font-family: 'Menlo','Monaco','Courier New',monospace;
    font-size: 0.83rem;
    color: #1e293b;
  }
  .query-send-btn {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: #3b82f6;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: background 0.14s, box-shadow 0.14s;
    box-shadow: 0 2px 8px rgba(59,130,246,0.35);
  }
  .query-send-btn:hover:not(:disabled) { background: #1d4ed8; box-shadow: 0 3px 12px rgba(59,130,246,0.45); }
  .query-send-btn:disabled { background: #94a3b8; cursor: not-allowed; box-shadow: none; }

  /* Spinner */
  .spinner {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2.5px solid rgba(255,255,255,0.35);
    border-top-color: #fff;
    animation: spin 0.7s linear infinite;
  }
  .spinner--sm { width: 18px; height: 18px; }

  /* Skeleton */
  .skeleton {
    background: linear-gradient(90deg,#e2e8f0 25%,#f1f5f9 50%,#e2e8f0 75%);
    background-size: 400% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }

  /* Schema reference */
  .schema-details { margin-top: 10px; }
  .schema-summary {
    padding: 7px 4px;
    cursor: pointer;
    font-size: 0.77rem;
    color: #94a3b8;
    user-select: none;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .schema-summary::-webkit-details-marker { display: none; }
  .schema-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
    padding: 8px 0 4px;
  }
  .schema-table {
    background: #f8fafc;
    border-radius: 8px;
    padding: 10px 14px;
    border-left: 3px solid #e2e8f0;
  }
  .schema-table-name {
    font-family: monospace;
    font-weight: 700;
    font-size: 0.83rem;
    margin-bottom: 5px;
  }
  .schema-table-rows {
    font-weight: 400;
    color: #94a3b8;
    margin-left: 5px;
    font-size: 0.72rem;
  }
  .schema-col {
    font-family: monospace;
    font-size: 0.72rem;
    color: #64748b;
    padding: 1px 0;
  }
  .schema-hint {
    font-size: 0.73rem;
    color: #94a3b8;
    padding: 4px 0;
  }
  .schema-hint code {
    background: #f1f5f9;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 0.72rem;
    color: #334155;
  }

  /* Scope notice */
  .scope-notice {
    margin-top: 8px;
    padding: 8px 12px;
    background: #fef3c7;
    border: 1px solid rgba(245,158,11,0.4);
    border-radius: 8px;
    font-size: 0.77rem;
    color: #92400e;
    line-height: 1.5;
  }
  .scope-link {
    color: #d97706;
    font-weight: 700;
    text-decoration: none;
  }
  .scope-link:hover { text-decoration: underline; }

  /* Responsive: hide sidebar on narrow screens */
  @media (max-width: 680px) {
    .cl-sidebar { display: none; }
    .cl-root { height: auto; min-height: 100vh; }
    .cl-main { height: auto; }
    .conversation-area { height: auto; max-height: none; overflow: visible; }
  }
`;
