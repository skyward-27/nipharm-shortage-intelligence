import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

interface TrendPoint { month: string; count: number; }
interface PricePoint  { month: string; price_gbp: number; on_concession: boolean; }
interface ConcPoint   { month: string; concession_price: number; }

/* ── Concession Trend Bar Chart (pure SVG) ─────────────────────────── */
function ConcessionTrendChart() {
  const [data, setData]       = useState<TrendPoint[]>([]);
  const [peak, setPeak]       = useState<{month:string;count:number}|null>(null);
  const [total, setTotal]     = useState(0);
  const [tooltip, setTooltip] = useState<{x:number;y:number;d:TrendPoint}|null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/concession-trends`)
      .then(r => r.json())
      .then(j => {
        if (j.success) {
          setData(j.data);
          setPeak({ month: j.peak_month, count: j.peak_count });
          setTotal(j.total_events);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const W = 900, H = 240, PAD = { top: 20, right: 20, bottom: 50, left: 48 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const maxCount = data.length ? Math.max(...data.map(d => d.count)) : 200;
  const barW = Math.max(1, innerW / (data.length || 74) - 1);

  // Year boundaries for gridlines
  const years = data.length
    ? Array.from(new Set(data.map(d => d.month.slice(0,4)))).sort()
    : [];

  return (
    <div style={{ position: "relative" }}>
      {loading && <div style={{ textAlign:"center", padding: 40, color:"#888" }}>Loading concession data…</div>}
      {!loading && (
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width:"100%", overflow:"visible" }}>
          <defs>
            <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1565c0" />
              <stop offset="100%" stopColor="#42a5f5" />
            </linearGradient>
            <linearGradient id="peakGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#c62828" />
              <stop offset="100%" stopColor="#ef9a9a" />
            </linearGradient>
          </defs>

          {/* Y gridlines */}
          {[0,50,100,150,200].map(v => {
            const y = PAD.top + innerH - (v / maxCount) * innerH;
            return (
              <g key={v}>
                <line x1={PAD.left} x2={W-PAD.right} y1={y} y2={y} stroke="#e8ecf0" strokeWidth={1}/>
                <text x={PAD.left-6} y={y+4} textAnchor="end" fontSize={10} fill="#aaa">{v}</text>
              </g>
            );
          })}

          {/* Year labels + separators */}
          {years.map(yr => {
            const idx = data.findIndex(d => d.month.startsWith(yr));
            if (idx < 0) return null;
            const x = PAD.left + idx * (barW + 1);
            return (
              <g key={yr}>
                <line x1={x} x2={x} y1={PAD.top} y2={PAD.top+innerH+4} stroke="#c8d0d8" strokeWidth={1} strokeDasharray="3,2"/>
                <text x={x + 4} y={PAD.top+innerH+28} fontSize={11} fill="#555" fontWeight="600">{yr}</text>
              </g>
            );
          })}

          {/* Bars */}
          {data.map((d, i) => {
            const isPeak = d.month === peak?.month;
            const bh = (d.count / maxCount) * innerH;
            const x  = PAD.left + i * (barW + 1);
            const y  = PAD.top + innerH - bh;
            return (
              <rect
                key={d.month}
                x={x} y={y} width={barW} height={bh}
                fill={isPeak ? "url(#peakGrad)" : "url(#barGrad)"}
                opacity={0.85}
                rx={1}
                style={{ cursor:"pointer", transition:"opacity 0.1s" }}
                onMouseEnter={e => setTooltip({ x: x + barW/2, y, d })}
                onMouseLeave={() => setTooltip(null)}
              />
            );
          })}

          {/* Peak label */}
          {peak && (() => {
            const pidx = data.findIndex(d => d.month === peak.month);
            if (pidx < 0) return null;
            const px = PAD.left + pidx * (barW + 1) + barW/2;
            const py = PAD.top + innerH - (peak.count/maxCount)*innerH - 6;
            return (
              <g>
                <text x={px} y={py} textAnchor="middle" fontSize={10} fill="#c62828" fontWeight="700">
                  ▲ Peak {peak.count}
                </text>
              </g>
            );
          })()}

          {/* Tooltip */}
          {tooltip && (
            <g>
              <rect x={tooltip.x-42} y={tooltip.y-44} width={84} height={38} rx={5} fill="#1a1a1a" opacity={0.88}/>
              <text x={tooltip.x} y={tooltip.y-28} textAnchor="middle" fontSize={10} fill="#fff" fontWeight="600">{tooltip.d.month}</text>
              <text x={tooltip.x} y={tooltip.y-14} textAnchor="middle" fontSize={11} fill="#64b5f6">{tooltip.d.count} drugs</text>
            </g>
          )}
        </svg>
      )}

      {/* Stats row */}
      {!loading && (
        <div style={{ display:"flex", gap:24, marginTop:12, flexWrap:"wrap" }}>
          {[
            { label:"Total Events", value: total.toLocaleString(), color:"#1565c0" },
            { label:"Peak Month",   value: peak?.month ?? "—",     color:"#c62828" },
            { label:"Peak Count",   value: peak ? `${peak.count} drugs` : "—", color:"#c62828" },
            { label:"Data Range",   value: data.length ? `${data[0].month} – ${data[data.length-1].month}` : "—", color:"#555" },
          ].map(s => (
            <div key={s.label} style={{ background:"#f8fafc", borderRadius:8, padding:"10px 16px", minWidth:120 }}>
              <div style={{ fontSize:"0.78rem", color:"#888", marginBottom:2 }}>{s.label}</div>
              <div style={{ fontSize:"1.05rem", fontWeight:700, color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Drug Lookup Chart (pure SVG) ──────────────────────────────────── */
function DrugLookupChart() {
  const [query, setQuery]     = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showDrop, setShowDrop] = useState(false);
  const [loading, setLoading] = useState(false);
  const [drugData, setDrugData] = useState<{
    drug: string;
    price_history: PricePoint[];
    concession_months: ConcPoint[];
    price_range: { min:number; max:number; latest:number };
    total_concession_events: number;
  } | null>(null);
  const [error, setError] = useState("");
  const [tooltip, setTooltip] = useState<{x:number;y:number;pt:PricePoint}|null>(null);
  const debounceRef = useRef<any>(null);

  const fetchSuggestions = useCallback((q: string) => {
    if (!q || q.length < 2) { setSuggestions([]); return; }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetch(`${API_URL}/drug-list?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(j => { if (j.success) setSuggestions(j.drugs.slice(0,8)); })
        .catch(() => {});
    }, 250);
  }, []);

  const lookupDrug = (name: string) => {
    setQuery(name);
    setSuggestions([]);
    setShowDrop(false);
    setLoading(true);
    setError("");
    setDrugData(null);
    fetch(`${API_URL}/drug-detail?drug=${encodeURIComponent(name)}`)
      .then(r => r.json())
      .then(j => {
        if (j.success) setDrugData(j);
        else setError(j.error || "Not found");
      })
      .catch(() => setError("Failed to load drug data"))
      .finally(() => setLoading(false));
  };

  const W = 860, H = 200, PAD = { top:16, right:20, bottom:40, left:50 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const priceChart = () => {
    if (!drugData || !drugData.price_history.length) return null;
    const pts   = drugData.price_history;
    const prMin = drugData.price_range.min;
    const prMax = drugData.price_range.max;
    const range = prMax - prMin || 1;
    const concSet = new Set(drugData.concession_months.map(c => c.month));

    const xOf = (i: number) => PAD.left + (i / (pts.length - 1)) * innerW;
    const yOf = (v: number) => PAD.top + innerH - ((v - prMin) / range) * innerH;

    const polyPts = pts.map((p,i) => `${xOf(i)},${yOf(p.price_gbp)}`).join(" ");

    // Year tick positions
    const yearTicks: {x:number;yr:string}[] = [];
    pts.forEach((p,i) => {
      const yr = p.month.slice(0,4);
      if (!yearTicks.find(t => t.yr === yr)) yearTicks.push({ x: xOf(i), yr });
    });

    return (
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width:"100%", overflow:"visible" }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1976d2" stopOpacity={0.15}/>
            <stop offset="100%" stopColor="#1976d2" stopOpacity={0}/>
          </linearGradient>
        </defs>

        {/* Concession period shading */}
        {pts.map((p,i) => {
          if (!concSet.has(p.month)) return null;
          return <rect key={p.month} x={xOf(i)-3} y={PAD.top} width={Math.max(6, innerW/pts.length)} height={innerH}
            fill="#fff3e0" opacity={0.8}/>;
        })}

        {/* Y gridlines */}
        {[prMin, (prMin+prMax)/2, prMax].map((v,k) => {
          const y = yOf(v);
          return (
            <g key={k}>
              <line x1={PAD.left} x2={W-PAD.right} y1={y} y2={y} stroke="#e8ecf0" strokeWidth={1}/>
              <text x={PAD.left-6} y={y+4} textAnchor="end" fontSize={10} fill="#aaa">£{v.toFixed(2)}</text>
            </g>
          );
        })}

        {/* Area fill */}
        <polygon
          points={`${PAD.left},${PAD.top+innerH} ${polyPts} ${xOf(pts.length-1)},${PAD.top+innerH}`}
          fill="url(#areaGrad)"
        />

        {/* Price line */}
        <polyline points={polyPts} fill="none" stroke="#1565c0" strokeWidth={2} strokeLinejoin="round"/>

        {/* Data points */}
        {pts.map((p,i) => (
          <circle
            key={p.month}
            cx={xOf(i)} cy={yOf(p.price_gbp)} r={3}
            fill={concSet.has(p.month) ? "#e65100" : "#1565c0"}
            stroke="#fff" strokeWidth={1}
            style={{ cursor:"pointer" }}
            onMouseEnter={() => setTooltip({ x: xOf(i), y: yOf(p.price_gbp), pt: p })}
            onMouseLeave={() => setTooltip(null)}
          />
        ))}

        {/* Year ticks */}
        {yearTicks.map(t => (
          <g key={t.yr}>
            <line x1={t.x} x2={t.x} y1={PAD.top+innerH} y2={PAD.top+innerH+5} stroke="#ccc"/>
            <text x={t.x} y={PAD.top+innerH+18} textAnchor="middle" fontSize={10} fill="#666">{t.yr}</text>
          </g>
        ))}

        {/* Tooltip */}
        {tooltip && (
          <g>
            <rect x={tooltip.x-52} y={tooltip.y-52} width={104} height={44} rx={5} fill="#1a1a1a" opacity={0.88}/>
            <text x={tooltip.x} y={tooltip.y-36} textAnchor="middle" fontSize={10} fill="#fff">{tooltip.pt.month}</text>
            <text x={tooltip.x} y={tooltip.y-22} textAnchor="middle" fontSize={11} fill="#64b5f6" fontWeight="600">
              £{tooltip.pt.price_gbp.toFixed(2)} NHS tariff
            </text>
            {tooltip.pt.on_concession && (
              <text x={tooltip.x} y={tooltip.y-10} textAnchor="middle" fontSize={9} fill="#ffcc02">● On concession</text>
            )}
          </g>
        )}

        {/* Legend */}
        <g transform={`translate(${PAD.left}, ${H-6})`}>
          <rect x={0} y={0} width={10} height={10} fill="#1565c0" rx={2}/>
          <text x={14} y={9} fontSize={10} fill="#555">NHS Tariff price</text>
          <rect x={120} y={0} width={10} height={10} fill="#fff3e0" stroke="#e65100" rx={2}/>
          <text x={134} y={9} fontSize={10} fill="#555">Concession period</text>
        </g>
      </svg>
    );
  };

  return (
    <div>
      {/* Search box */}
      <div style={{ position:"relative", maxWidth:460, marginBottom:24 }}>
        <input
          value={query}
          onChange={e => { setQuery(e.target.value); fetchSuggestions(e.target.value); setShowDrop(true); }}
          onFocus={() => query.length >= 2 && setShowDrop(true)}
          onBlur={() => setTimeout(() => setShowDrop(false), 180)}
          onKeyDown={e => { if (e.key === "Enter" && query) lookupDrug(query); }}
          placeholder="Search drug name, e.g. Amoxicillin 500mg…"
          style={{
            width:"100%", padding:"11px 44px 11px 16px", fontSize:"0.97rem",
            border:"1.5px solid #c8d0da", borderRadius:10, outline:"none",
            background:"#fff", boxShadow:"0 2px 8px rgba(0,0,0,0.06)",
            fontFamily:"inherit", boxSizing:"border-box"
          }}
        />
        <button
          onClick={() => query && lookupDrug(query)}
          style={{
            position:"absolute", right:8, top:"50%", transform:"translateY(-50%)",
            background:"#1565c0", color:"#fff", border:"none", borderRadius:7,
            padding:"6px 12px", cursor:"pointer", fontSize:"0.88rem"
          }}
        >🔍</button>

        {/* Autocomplete dropdown */}
        {showDrop && suggestions.length > 0 && (
          <div style={{
            position:"absolute", top:"calc(100% + 4px)", left:0, right:0,
            background:"#fff", border:"1px solid #dde3ea", borderRadius:8,
            boxShadow:"0 8px 24px rgba(0,0,0,0.12)", zIndex:99, overflow:"hidden"
          }}>
            {suggestions.map(s => (
              <div
                key={s}
                onMouseDown={() => lookupDrug(s)}
                style={{
                  padding:"10px 16px", cursor:"pointer", fontSize:"0.93rem",
                  borderBottom:"1px solid #f5f5f5"
                }}
                onMouseEnter={e => (e.currentTarget.style.background="#f0f5ff")}
                onMouseLeave={e => (e.currentTarget.style.background="#fff")}
              >
                {s}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick-pick popular drugs */}
      <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginBottom:20 }}>
        {["Amoxicillin 500mg capsules","Metformin 500mg tablets","Omeprazole 20mg capsules",
          "Amlodipine 5mg tablets","Atorvastatin 40mg tablets","Gabapentin 300mg capsules"].map(d => (
          <button
            key={d}
            onClick={() => lookupDrug(d)}
            style={{
              padding:"5px 12px", fontSize:"0.82rem", borderRadius:20,
              border:"1px solid #c8d0da", background: query === d ? "#e3f2fd" : "#f8fafc",
              color:"#1565c0", cursor:"pointer", fontWeight: query===d ? 700 : 400
            }}
          >{d}</button>
        ))}
      </div>

      {/* Loading */}
      {loading && <div style={{ textAlign:"center", padding:30, color:"#888" }}>Loading drug data…</div>}

      {/* Error */}
      {error && !loading && (
        <div style={{ background:"#fff3e0", borderRadius:8, padding:"12px 16px", color:"#e65100", fontSize:"0.93rem" }}>
          ⚠️ {error}
        </div>
      )}

      {/* Drug chart */}
      {drugData && !loading && (
        <div>
          {/* Drug header */}
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:16, flexWrap:"wrap", gap:12 }}>
            <div>
              <div style={{ fontSize:"1.1rem", fontWeight:700, color:"#1a1a1a" }}>{drugData.drug}</div>
              <div style={{ fontSize:"0.88rem", color:"#888", marginTop:2 }}>NHS Cat M Tariff price history · hover dots for details</div>
            </div>
            <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
              {[
                { l:"Latest NHS Price", v:`£${drugData.price_range.latest?.toFixed(2)}`, c:"#1565c0" },
                { l:"24-mo Range", v:`£${drugData.price_range.min} – £${drugData.price_range.max}`, c:"#555" },
                { l:"Concession Events", v:`${drugData.total_concession_events} months`, c: drugData.total_concession_events > 10 ? "#c62828" : "#2e7d32" },
              ].map(s => (
                <div key={s.l} style={{ background:"#f8fafc", borderRadius:8, padding:"8px 14px", textAlign:"center" }}>
                  <div style={{ fontSize:"0.75rem", color:"#888" }}>{s.l}</div>
                  <div style={{ fontSize:"0.98rem", fontWeight:700, color:s.c }}>{s.v}</div>
                </div>
              ))}
            </div>
          </div>
          {priceChart()}

          {/* Concession timeline mini-table */}
          {drugData.concession_months.length > 0 && (
            <div style={{ marginTop:16 }}>
              <div style={{ fontSize:"0.85rem", fontWeight:600, color:"#e65100", marginBottom:8 }}>
                🟠 Concession History ({drugData.total_concession_events} events)
              </div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {drugData.concession_months.map(c => (
                  <div key={c.month} style={{
                    background:"#fff3e0", border:"1px solid #ffcc80", borderRadius:6,
                    padding:"4px 10px", fontSize:"0.8rem", color:"#e65100"
                  }}>
                    <span style={{ fontWeight:600 }}>{c.month}</span>
                    <span style={{ color:"#888", marginLeft:6 }}>£{c.concession_price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!drugData && !loading && !error && (
        <div style={{ textAlign:"center", padding:"32px 20px", color:"#aaa", background:"#f8fafc", borderRadius:12, border:"1.5px dashed #dde3ea" }}>
          <div style={{ fontSize:"2rem", marginBottom:8 }}>💊</div>
          <div style={{ fontSize:"0.95rem" }}>Search for a drug above to see its NHS tariff price history and concession periods</div>
        </div>
      )}
    </div>
  );
}

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

      {/* ── CONCESSION TRENDS CHART ─────────────────────────────── */}
      <section style={sectionCard}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", flexWrap:"wrap", gap:8, marginBottom:8 }}>
          <div>
            <h2 style={sectionTitle}>📈 Concession Trends — Jan 2020 to Feb 2026</h2>
            <p style={{ color:"#666", fontSize:"0.93rem", margin:0 }}>
              Monthly count of NHS drugs placed on CPE concessionary pricing · 7,742 events · hover any bar for detail
            </p>
          </div>
          <span style={{ background:"#ffebee", color:"#c62828", borderRadius:20, padding:"4px 12px", fontSize:"0.82rem", fontWeight:700, whiteSpace:"nowrap" }}>
            Peak: Dec 2022 — 198 drugs
          </span>
        </div>
        <ConcessionTrendChart />
      </section>

      {/* ── DRUG LOOKUP CHART ───────────────────────────────────── */}
      <section style={sectionCard}>
        <h2 style={sectionTitle}>🔍 Drug Price & Concession Lookup</h2>
        <p style={{ color:"#666", marginBottom:20, fontSize:"0.93rem" }}>
          Search any of 718 Cat M drugs — see NHS tariff price history and concession periods (Jan 2021–Mar 2026)
        </p>
        <DrugLookupChart />
      </section>

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
