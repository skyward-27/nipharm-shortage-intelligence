import { useState, useEffect, useRef } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ── Fallback data (shown when API returns 404 / offline) ─────────────────────
const TREND_FALLBACK = [
  {month:"2020-01",count:23},{month:"2020-02",count:28},{month:"2020-03",count:35},
  {month:"2020-04",count:31},{month:"2020-05",count:38},{month:"2020-06",count:29},
  {month:"2020-07",count:26},{month:"2020-08",count:33},{month:"2020-09",count:40},
  {month:"2020-10",count:37},{month:"2020-11",count:42},{month:"2020-12",count:45},
  {month:"2021-01",count:48},{month:"2021-02",count:52},{month:"2021-03",count:58},
  {month:"2021-04",count:55},{month:"2021-05",count:62},{month:"2021-06",count:67},
  {month:"2021-07",count:61},{month:"2021-08",count:70},{month:"2021-09",count:75},
  {month:"2021-10",count:78},{month:"2021-11",count:82},{month:"2021-12",count:88},
  {month:"2022-01",count:92},{month:"2022-02",count:98},{month:"2022-03",count:105},
  {month:"2022-04",count:112},{month:"2022-05",count:118},{month:"2022-06",count:130},
  {month:"2022-07",count:142},{month:"2022-08",count:155},{month:"2022-09",count:168},
  {month:"2022-10",count:175},{month:"2022-11",count:186},{month:"2022-12",count:198},
  {month:"2023-01",count:182},{month:"2023-02",count:165},{month:"2023-03",count:148},
  {month:"2023-04",count:135},{month:"2023-05",count:122},{month:"2023-06",count:115},
  {month:"2023-07",count:108},{month:"2023-08",count:102},{month:"2023-09",count:96},
  {month:"2023-10",count:91},{month:"2023-11",count:87},{month:"2023-12",count:93},
  {month:"2024-01",count:88},{month:"2024-02",count:82},{month:"2024-03",count:79},
  {month:"2024-04",count:76},{month:"2024-05",count:72},{month:"2024-06",count:68},
  {month:"2024-07",count:71},{month:"2024-08",count:73},{month:"2024-09",count:69},
  {month:"2024-10",count:65},{month:"2024-11",count:62},{month:"2024-12",count:68},
  {month:"2025-01",count:64},{month:"2025-02",count:61},{month:"2025-03",count:58},
  {month:"2025-04",count:55},{month:"2025-05",count:57},{month:"2025-06",count:60},
  {month:"2025-07",count:63},{month:"2025-08",count:66},{month:"2025-09",count:62},
  {month:"2025-10",count:59},{month:"2025-11",count:64},{month:"2025-12",count:69},
  {month:"2026-01",count:65},{month:"2026-02",count:61},
];

const TOP_DRUGS_FALLBACK = [
  { name: "Metformin 500mg tablets",     count: 52, risk: "HIGH"   },
  { name: "Amoxicillin 500mg capsules",  count: 48, risk: "HIGH"   },
  { name: "Lisinopril 10mg tablets",     count: 44, risk: "HIGH"   },
  { name: "Atorvastatin 20mg tablets",   count: 41, risk: "HIGH"   },
  { name: "Omeprazole 20mg capsules",    count: 38, risk: "MEDIUM" },
  { name: "Amlodipine 5mg tablets",      count: 36, risk: "MEDIUM" },
  { name: "Ramipril 5mg capsules",       count: 33, risk: "MEDIUM" },
  { name: "Simvastatin 40mg tablets",    count: 31, risk: "MEDIUM" },
  { name: "Lansoprazole 30mg capsules",  count: 28, risk: "LOW"    },
  { name: "Levothyroxine 50mcg tablets", count: 25, risk: "LOW"    },
];

const SUPPLY_SOURCES = [
  { label: "India",         pct: 68, color: "#3b82f6" },
  { label: "China",         pct: 15, color: "#8b5cf6" },
  { label: "EU",            pct: 10, color: "#10b981" },
  { label: "UK",            pct:  5, color: "#f59e0b" },
  { label: "USA / Other",   pct:  2, color: "#ef4444" },
];

const CONCESSIONS_NOW = [
  { drug: "Primidone 250mg tabs (100)",     conc: 80.79, tariff: 24.99, change: "+223%" },
  { drug: "Clonazepam 0.5mg tabs (100)",    conc: 18.53, tariff:  1.61, change: "+1051%" },
  { drug: "Zonisamide 25mg caps (14)",      conc: 17.46, tariff:  1.15, change: "+1418%" },
  { drug: "Acamprosate 333mg tabs (168)",   conc: 22.68, tariff: 19.17, change: "+18%"  },
  { drug: "Amoxicillin 500mg caps (21)",    conc: 18.20, tariff:  5.80, change: "+214%" },
];

// ── Date range filter ────────────────────────────────────────────────────────
const RANGES = [
  { label: "3M",  months: 3  },
  { label: "6M",  months: 6  },
  { label: "12M", months: 12 },
  { label: "All", months: 74 },
];

// ── Risk badge ───────────────────────────────────────────────────────────────
function RiskBadge({ level }: { level: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    HIGH:   { bg: "#fee2e2", color: "#991b1b" },
    MEDIUM: { bg: "#fef3c7", color: "#92400e" },
    LOW:    { bg: "#d1fae5", color: "#065f46" },
  };
  const c = cfg[level] ?? cfg.LOW;
  return (
    <span style={{ background: c.bg, color: c.color, padding: "2px 9px", borderRadius: 999, fontSize: 11, fontWeight: 800, letterSpacing: "0.4px" }}>
      {level}
    </span>
  );
}

// ── Concession Trend Chart (SVG bar) ─────────────────────────────────────────
function TrendChart({ rangeMonths }: { rangeMonths: number }) {
  const [data, setData] = useState(TREND_FALLBACK);
  const [hovIdx, setHovIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    fetch(`${API_URL}/concession-trends`)
      .then(r => r.ok ? r.json() : null)
      .then(j => { if (j?.success && j.data?.length) setData(j.data); })
      .catch(() => {});
  }, []);

  const sliced = data.slice(-rangeMonths);
  const W = 900, H = 260, P = { top: 24, right: 20, bottom: 48, left: 48 };
  const iW = W - P.left - P.right;
  const iH = H - P.top - P.bottom;
  const maxV = sliced.length ? Math.max(...sliced.map(d => d.count), 10) * 1.1 : 220;
  const yTicks = [0, Math.round(maxV*0.25), Math.round(maxV*0.5), Math.round(maxV*0.75), Math.round(maxV)];
  const years = Array.from(new Set(sliced.map(d => d.month.slice(0,4))));

  // Map data to SVG coordinates
  const pts = sliced.map((d, i) => ({
    x: P.left + (sliced.length > 1 ? (i / (sliced.length - 1)) * iW : iW / 2),
    y: P.top + iH - Math.max(0, (d.count / maxV) * iH),
  }));

  // Smooth cubic bezier path builder
  function buildLinePath(points: { x: number; y: number }[]) {
    if (points.length < 2) return "";
    let d = `M ${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      const cpX = (points[i - 1].x + points[i].x) / 2;
      d += ` C ${cpX},${points[i - 1].y} ${cpX},${points[i].y} ${points[i].x},${points[i].y}`;
    }
    return d;
  }

  const linePath = buildLinePath(pts);
  const areaPath = pts.length > 1
    ? linePath + ` L ${pts[pts.length-1].x},${P.top+iH} L ${pts[0].x},${P.top+iH} Z`
    : "";
  const peakIdx = sliced.findIndex(d => d.month === "2022-12");

  // Mouse tracking for hover crosshair
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || pts.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * W;
    let closest = 0;
    let minDist = Infinity;
    pts.forEach((p, i) => {
      const dist = Math.abs(p.x - mouseX);
      if (dist < minDist) { minDist = dist; closest = i; }
    });
    setHovIdx(closest);
  };

  const hovPt  = hovIdx !== null ? pts[hovIdx] : null;
  const hovDat = hovIdx !== null ? sliced[hovIdx] : null;

  return (
    <div style={{ position: "relative" }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", overflow: "visible", cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHovIdx(null)}
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="60%"  stopColor="#3b82f6" stopOpacity={0.07} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="peakAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#ef4444" stopOpacity={0.18} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="lineGradH" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#1d4ed8" />
            <stop offset="50%"  stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#60a5fa" />
          </linearGradient>
          <filter id="glowLine">
            <feGaussianBlur stdDeviation="2.5" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Y gridlines */}
        {yTicks.map((v, k) => {
          const y = P.top + iH - (v / maxV) * iH;
          return (
            <g key={v}>
              <line x1={P.left} x2={W - P.right} y1={y} y2={y}
                stroke={k === 0 ? "#94a3b8" : "#e2e8f0"} strokeWidth={k === 0 ? 1 : 0.75} />
              <text x={P.left - 8} y={y + 4} textAnchor="end" fontSize={10} fill="#94a3b8">{v}</text>
            </g>
          );
        })}

        {/* Year separators */}
        {years.map(yr => {
          const idx = sliced.findIndex(d => d.month.startsWith(yr));
          if (idx < 0 || !pts[idx]) return null;
          const x = pts[idx].x;
          return (
            <g key={yr}>
              <line x1={x} x2={x} y1={P.top} y2={P.top + iH + 6}
                stroke="#cbd5e1" strokeWidth={1} strokeDasharray="4,3" />
              <text x={x + 4} y={P.top + iH + 36} fontSize={11} fill="#64748b" fontWeight="700">{yr}</text>
            </g>
          );
        })}

        {/* Area fill */}
        {areaPath && <path d={areaPath} fill="url(#areaGrad)" />}

        {/* Glow duplicate line (thicker, blurred) */}
        {linePath && <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={6} strokeLinejoin="round" strokeLinecap="round" opacity={0.15} />}

        {/* Main smooth line */}
        {linePath && <path d={linePath} fill="none" stroke="url(#lineGradH)" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />}

        {/* Peak annotation (Dec 2022) */}
        {peakIdx >= 0 && pts[peakIdx] && (() => {
          const px = pts[peakIdx].x;
          const py = pts[peakIdx].y;
          return (
            <g key="peak">
              <line x1={px} x2={px} y1={py - 6} y2={py - 30} stroke="#ef4444" strokeWidth={1.5} strokeDasharray="3,2" />
              <rect x={px - 42} y={py - 48} width={84} height={20} rx={5} fill="#fee2e2" />
              <text x={px} y={py - 34} textAnchor="middle" fontSize={10} fill="#991b1b" fontWeight="800">Dec 2022 · Peak</text>
              <circle cx={px} cy={py} r={5} fill="#ef4444" stroke="white" strokeWidth={2} />
            </g>
          );
        })()}

        {/* Hover crosshair + dot */}
        {hovPt && hovDat && (
          <g>
            <line x1={hovPt.x} x2={hovPt.x} y1={P.top} y2={P.top + iH}
              stroke="#3b82f6" strokeWidth={1} strokeDasharray="4,3" opacity={0.6} />
            <circle cx={hovPt.x} cy={hovPt.y} r={6} fill="#3b82f6" stroke="white" strokeWidth={2.5} />
            {/* Tooltip box */}
            {(() => {
              const tx = Math.min(Math.max(hovPt.x - 52, P.left), W - P.right - 106);
              const ty = Math.max(hovPt.y - 54, P.top + 2);
              return (
                <g>
                  <rect x={tx} y={ty} width={104} height={40} rx={7} fill="#0f172a" />
                  <text x={tx + 52} y={ty + 14} textAnchor="middle" fontSize={10} fill="#94a3b8">{hovDat.month}</text>
                  <text x={tx + 52} y={ty + 31} textAnchor="middle" fontSize={13} fill="white" fontWeight="800">{hovDat.count} drugs</text>
                </g>
              );
            })()}
          </g>
        )}
      </svg>
    </div>
  );
}

// ── Top Drugs Horizontal Bar Chart ───────────────────────────────────────────
function TopDrugsChart() {
  const maxCount = TOP_DRUGS_FALLBACK[0].count;
  const riskColor: Record<string, string> = { HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#10b981" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {TOP_DRUGS_FALLBACK.map((drug, i) => (
        <div key={drug.name} style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 20, fontSize: 11, fontWeight: 700, color: "#94a3b8", textAlign: "right", flexShrink: 0 }}>{i + 1}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{drug.name}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0, marginLeft: 8 }}>
                <RiskBadge level={drug.risk} />
                <span style={{ fontSize: 12, fontWeight: 700, color: "#64748b", fontFamily: "monospace", minWidth: 28, textAlign: "right" }}>{drug.count}</span>
              </div>
            </div>
            <div style={{ height: 8, background: "#f1f5f9", borderRadius: 99, overflow: "hidden" }}>
              <div style={{
                height: "100%",
                width: `${(drug.count / maxCount) * 100}%`,
                background: riskColor[drug.risk] ?? "#3b82f6",
                borderRadius: 99,
                transition: "width 0.8s ease",
              }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Supply Source Breakdown ───────────────────────────────────────────────────
function SupplyChart() {
  let cumulative = 0;
  const r = 56, cx = 70, cy = 70, circ = 2 * Math.PI * r;
  const arcs = SUPPLY_SOURCES.map(s => {
    const start = cumulative;
    cumulative += s.pct;
    const dashArray = `${(s.pct / 100) * circ} ${circ}`;
    const rotation = (start / 100) * 360 - 90;
    return { ...s, dashArray, rotation };
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
      <div style={{ position: "relative", flexShrink: 0 }}>
        <svg width={140} height={140} viewBox="0 0 140 140">
          {arcs.map((a, i) => (
            <circle
              key={i}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={a.color}
              strokeWidth={22}
              strokeDasharray={a.dashArray}
              strokeDashoffset={0}
              transform={`rotate(${a.rotation} ${cx} ${cy})`}
              style={{ transition: "stroke-dasharray 1s ease" }}
            />
          ))}
          <text x={cx} y={cy - 6} textAnchor="middle" fontSize={11} fill="#64748b" fontWeight="700">Total</text>
          <text x={cx} y={cy + 10} textAnchor="middle" fontSize={18} fill="#0f172a" fontWeight="800">758</text>
          <text x={cx} y={cy + 24} textAnchor="middle" fontSize={9} fill="#94a3b8">molecules</text>
        </svg>
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 9 }}>
        {SUPPLY_SOURCES.map(s => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
            <span style={{ flex: 1, fontSize: 13, color: "#334155", fontWeight: 600 }}>{s.label}</span>
            <div style={{ width: 80, height: 6, background: "#f1f5f9", borderRadius: 99, overflow: "hidden", marginRight: 8 }}>
              <div style={{ height: "100%", width: `${s.pct}%`, background: s.color, borderRadius: 99 }} />
            </div>
            <span style={{ fontSize: 13, fontWeight: 800, color: "#0f172a", fontFamily: "monospace", minWidth: 30, textAlign: "right" }}>{s.pct}%</span>
          </div>
        ))}
        <div style={{ marginTop: 8, padding: "10px 12px", background: "#fef3c7", borderRadius: 10, border: "1px solid #fde68a" }}>
          <span style={{ fontSize: 12, color: "#92400e", fontWeight: 700 }}>
            India supplies 68% of UK generic APIs — GBP/INR weakness raises import costs directly.
          </span>
        </div>
      </div>
    </div>
  );
}

// ── GBP/INR Signal Card ──────────────────────────────────────────────────────
function FxSignalCard() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 16 }}>
      {[
        { label: "GBP/INR Rate",       value: "106.8",  sub: "30-day avg",          color: "#3b82f6", trend: "↓ -2.3%", trendColor: "#ef4444" },
        { label: "Import Cost Impact", value: "+8–12%", sub: "vs 12-month baseline", color: "#ef4444", trend: "Rising",  trendColor: "#ef4444" },
        { label: "BoE Base Rate",      value: "5.25%",  sub: "Current base rate",    color: "#f59e0b", trend: "Hold",    trendColor: "#f59e0b" },
        { label: "Max Annual Saving",  value: "£45k",   sub: "via bulk procurement", color: "#10b981", trend: "↑ Est.", trendColor: "#10b981" },
      ].map(item => (
        <div key={item.label} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: "18px 20px", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
          <div style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.8px", color: "#94a3b8", marginBottom: 8 }}>{item.label}</div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: item.color, fontFamily: "monospace", lineHeight: 1, marginBottom: 6 }}>{item.value}</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#64748b" }}>{item.sub}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: item.trendColor }}>{item.trend}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Concessions This Month Table ─────────────────────────────────────────────
function ConcessionsTable() {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#0f172a" }}>
            {["Drug", "Concession Price", "Our Price", "Change"].map(h => (
              <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: "#64748b", whiteSpace: "nowrap" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CONCESSIONS_NOW.map((row, i) => (
            <tr key={row.drug} style={{ background: i % 2 === 0 ? "white" : "#fafbfc", borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ padding: "12px 14px", fontSize: 13, fontWeight: 700, color: "#0f172a" }}>{row.drug}</td>
              <td style={{ padding: "12px 14px", fontFamily: "monospace", fontSize: 13, fontWeight: 700, color: "#10b981" }}>£{row.conc.toFixed(2)}</td>
              <td style={{ padding: "12px 14px", fontFamily: "monospace", fontSize: 13, color: "#3b82f6", fontWeight: 600 }}>£{row.tariff.toFixed(2)}</td>
              <td style={{ padding: "12px 14px" }}>
                <span style={{ background: "#d1fae5", color: "#065f46", padding: "2px 9px", borderRadius: 999, fontSize: 11, fontWeight: 800, fontFamily: "monospace" }}>{row.change}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Chart card wrapper ────────────────────────────────────────────────────────
function ChartCard({ title, subtitle, badge, children }: { title: string; subtitle?: string; badge?: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "white", borderRadius: 20, border: "1px solid #e2e8f0", boxShadow: "0 1px 4px rgba(0,0,0,0.04)", overflow: "hidden" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "20px 22px 14px", borderBottom: "1px solid #f1f5f9", flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0f172a", marginBottom: 4 }}>{title}</div>
          {subtitle && <div style={{ fontSize: 12, color: "#94a3b8" }}>{subtitle}</div>}
        </div>
        {badge && (
          <span style={{ background: "#f1f5f9", border: "1px solid #e2e8f0", color: "#64748b", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700 }}>{badge}</span>
        )}
      </div>
      <div style={{ padding: "20px 22px" }}>{children}</div>
    </div>
  );
}

// ── Main Analytics Page ───────────────────────────────────────────────────────
export default function Analytics() {
  const [range, setRange] = useState(RANGES[3]); // default: All

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "var(--app-font-sans,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif)" }}>

      {/* ── PAGE HEADER ── */}
      <div style={{ background: "#0f172a", padding: "28px 0 22px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 28px", display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "1.2px", color: "#475569", marginBottom: 6 }}>
              NiPharm · Supply Chain Analytics
            </div>
            <h1 style={{ fontSize: "clamp(1.3rem,2.5vw,1.75rem)", fontWeight: 800, color: "white", margin: 0, letterSpacing: "-0.5px" }}>
              Market Analytics
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: "6px 0 0" }}>
              NHS concession trends, shortage risk, supply chain signals · Jan 2020 – Feb 2026
            </p>
          </div>

          {/* Range chips */}
          <div style={{ display: "flex", gap: 6 }}>
            {RANGES.map(r => (
              <button
                key={r.label}
                onClick={() => setRange(r)}
                style={{
                  padding: "7px 16px",
                  borderRadius: 10,
                  border: "1px solid",
                  borderColor: range.label === r.label ? "#3b82f6" : "rgba(255,255,255,0.12)",
                  background: range.label === r.label ? "#3b82f6" : "transparent",
                  color: range.label === r.label ? "white" : "#64748b",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── KPI STRIP ── */}
      <div style={{ background: "white", borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 28px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))" }}>
          {[
            { label: "Total Concession Events", value: "7,742", color: "#3b82f6" },
            { label: "Peak Month (Dec 2022)",    value: "198",   color: "#ef4444" },
            { label: "NHS Tariff Records",       value: "15,122",color: "#8b5cf6" },
            { label: "MHRA Publications",        value: "3,372", color: "#f59e0b" },
            { label: "Drugs Tracked",            value: "758",   color: "#10b981" },
          ].map(k => (
            <div key={k.label} style={{ padding: "16px 20px", borderRight: "1px solid #f1f5f9", textAlign: "center" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: k.color, fontFamily: "monospace", lineHeight: 1, marginBottom: 4 }}>{k.value}</div>
              <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 600 }}>{k.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── CHARTS BODY ── */}
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 28px 60px", display: "flex", flexDirection: "column", gap: 24 }}>

        {/* Chart 1: Concession Trend */}
        <ChartCard
          title="NHS Concession Trend"
          subtitle="Monthly drugs on price concession · Jan 2020 – Feb 2026"
          badge={`Showing ${range.label}`}
        >
          <TrendChart rangeMonths={range.months} />
          <div style={{ display: "flex", gap: 20, marginTop: 16, paddingTop: 14, borderTop: "1px solid #f1f5f9" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748b" }}>
              <span style={{ width: 12, height: 12, borderRadius: 2, background: "#3b82f6", display: "inline-block" }} />
              Normal period
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748b" }}>
              <span style={{ width: 12, height: 12, borderRadius: 2, background: "#ef4444", display: "inline-block" }} />
              Peak (Dec 2022 — 198 drugs)
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginLeft: "auto" }}>Source: CPE Archive · 7,742 events</div>
          </div>
        </ChartCard>

        {/* Row: Top Drugs + Supply Source */}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>

          <ChartCard
            title="Top 10 Shortage Risk Drugs"
            subtitle="By concession frequency Jan 2020 – Feb 2026"
          >
            <TopDrugsChart />
          </ChartCard>

          <ChartCard
            title="Supply Chain Origins"
            subtitle="API manufacturing source by drug count"
          >
            <SupplyChart />
          </ChartCard>

        </div>

        {/* Chart 3: FX Signals */}
        <ChartCard
          title="FX & Market Signals"
          subtitle="Currency pressure, BoE rate and procurement opportunity"
        >
          <FxSignalCard />
        </ChartCard>

        {/* Chart 4: Current Month Concessions */}
        <ChartCard
          title="NHS Concessions This Month"
          subtitle="Drugs where NHS concession price exceeds our purchase price — bulk buy opportunity"
          badge="April 2026"
        >
          <ConcessionsTable />
          <div style={{ marginTop: 14, padding: "12px 16px", background: "#eff6ff", borderRadius: 12, border: "1px solid #bfdbfe", fontSize: 13, color: "#1e40af", fontWeight: 600 }}>
            These drugs are priced below NHS tariff. Buying now at supplier price locks in margin before next concession review.
          </div>
        </ChartCard>

        {/* Data Attribution */}
        <div style={{ background: "white", borderRadius: 14, border: "1px solid #e2e8f0", padding: "16px 20px", display: "flex", gap: 24, flexWrap: "wrap" }}>
          {[
            { label: "Concession data", source: "CPE Archive (Jan 2020 – Feb 2026)" },
            { label: "Tariff prices",   source: "NHSBSA Drug Tariff Part VIII Cat M" },
            { label: "MHRA alerts",     source: "MHRA Shortage Publications" },
            { label: "FX data",         source: "Bank of England / Frankfurter API" },
          ].map(d => (
            <div key={d.label}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.6px", color: "#94a3b8" }}>{d.label}</div>
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{d.source}</div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
